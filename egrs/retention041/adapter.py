"""Strict041 stage envelope around a genuine complete task-control student payload."""
from copy import deepcopy
import json
from pathlib import Path

from egrs.task_control import adapter as common

SCHEMA = 'task041-old10-retention-adapter-v1'
GROUP = 'old10_behavior_retention'
INITIALIZATION_SHA256 = 'a51f9062fc5a54982233ffdb93f7fa164eaf78b6dbdc097721db9d7f87f57b12'
TEACHER_SHA256 = '6d340e99186090bab6739f173ecb118d03eb1bf574ae96d5f1c34241b02d644e'
INDEX_IDENTITY = '8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe'
TEACHER_INDEX_IDENTITY = 'b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c'


def _validate_source(identity, role, index_identity=None):
    common._validate(identity)
    if role not in ('initialization', 'teacher'):
        raise ValueError('041 source role must be initialization or teacher')
    digest = INITIALIZATION_SHA256 if role == 'initialization' else TEACHER_SHA256
    index = INDEX_IDENTITY if role == 'initialization' else TEACHER_INDEX_IDENTITY
    if identity['arm'] != 'c1' or identity['update'] != 1000 or identity['final_update'] != 1000:
        raise ValueError('041 '+role+' requires the complete C1 fixed final1000 adapter')
    if identity['adapter_sha256'] != digest:
        raise ValueError('041 '+role+' source adapter SHA differs from the fixed source')
    if identity['index_identity'] != index or (index_identity is not None and index_identity != index):
        raise ValueError('041 '+role+' source index identity differs')


def read_source_identity(directory, role, index_identity=None):
    """Read fixed old metadata and verify bytes, without importing model libraries."""
    identity = common.read_adapter_identity(directory)
    _validate_source(identity, role, index_identity)
    return identity


def load_source_state(policy, directory, identity):
    """Validate the whole flat payload before returning it; never mutate the student."""
    import torch
    common._validate(identity)
    directory = Path(directory)
    if common.sha256(directory/'adapter.pt') != identity['adapter_sha256']:
        raise ValueError('041 source adapter byte hash mismatch')
    if identity['base_lineage'] != common._lineage(policy):
        raise ValueError('041 source base lineage mismatch')
    state = torch.load(directory/'adapter.pt', map_location='cpu', weights_only=True)
    actual = common._state(policy.model)
    shapes = identity['trainable_parameters']
    if not isinstance(state, dict) or set(state) != set(shapes) or set(actual) != set(shapes):
        raise ValueError('041 source tensor inventory mismatch')
    for name, value in state.items():
        if (not isinstance(value, torch.Tensor) or list(value.shape) != shapes[name]
                or list(actual[name].shape) != shapes[name]
                or str(value.dtype) != identity['tensor_dtypes'][name]
                or common._tensor_hash(value) != identity['tensor_sha256'][name]
                or not torch.isfinite(value).all()):
            raise ValueError('041 source tensor shape, dtype or hash mismatch: '+name)
    return state


def _copy_student(policy, state):
    import torch
    parameters = dict(policy.model.named_parameters())
    with torch.no_grad():
        for name, value in state.items():
            parameters[name].copy_(value)
    for module in policy.model.modules():
        if hasattr(module, 'enabled') and (module is policy.model.task_control or hasattr(module, 'lora_A')):
            module.enabled = True


def initialize_from040(policy, directory, index_identity):
    identity = read_source_identity(directory, 'initialization', index_identity)
    state = load_source_state(policy, directory, identity)
    _copy_student(policy, state)
    return identity


def validate_stage_identity(stage, experiment_arm=None, index_identity=None):
    fields = {'format','experiment_arm','initialization_identity','teacher_identity',
              'index_identity','ancestor_updates','additional_updates'}
    if (not isinstance(stage, dict) or set(stage) != fields
            or stage.get('format') != 'task041-stage-inputs-v1'
            or stage.get('experiment_arm') not in ('r0','r1')
            or stage.get('index_identity') != INDEX_IDENTITY
            or type(stage.get('ancestor_updates')) is not int or stage['ancestor_updates'] != 1000
            or type(stage.get('additional_updates')) is not int or stage['additional_updates'] != 1000):
        raise ValueError('Invalid041 stage identity or update ancestry')
    if (experiment_arm is not None and stage['experiment_arm'] != experiment_arm
            or index_identity is not None and stage['index_identity'] != index_identity):
        raise ValueError('041 stage experiment arm or index identity differs')
    initial = stage['initialization_identity']
    _validate_source(initial, 'initialization', stage['index_identity'])
    teacher = stage['teacher_identity']
    if stage['experiment_arm'] == 'r0':
        if teacher is not None:
            raise ValueError('041 r0 stage must not bind a teacher')
    else:
        _validate_source(teacher, 'teacher')
        if teacher['base_lineage'] != initial['base_lineage']:
            raise ValueError('041 teacher and initialization base lineage differs')


def _calls(value, *, train_limit, dev_limit, exact_train=None):
    if (not isinstance(value, dict) or set(value) != {'train','dev','total','budget'}
            or any(type(v) is not int for v in value.values())
            or not 0 <= value['train'] <= train_limit or not 0 <= value['dev'] <= dev_limit
            or value['total'] != value['train']+value['dev']
            or value['budget'] != train_limit+dev_limit
            or exact_train is not None and value['train'] != exact_train):
        raise ValueError('Invalid041 observation budget counters')


def validate_adapter_identity(identity):
    fields = {'schema_version','group','recipe','data_kind','arm','experiment_arm','update',
        'final_update','index_identity','stage_identity','student_identity','reference_calls',
        'student_calls','old10_calls','adapter_sha256'}
    if (not isinstance(identity, dict) or set(identity) != fields
            or identity.get('schema_version') != SCHEMA or identity.get('group') != GROUP
            or identity.get('recipe') != GROUP or identity.get('data_kind') != 'task041-existing040-data-v1'
            or identity.get('arm') != 'c1' or identity.get('experiment_arm') not in ('r0','r1')
            or type(identity.get('update')) is not int or not 1 <= identity['update'] <= 1000
            or identity.get('final_update') != 1000):
        raise ValueError('Invalid041 adapter schema, recipe, arm or update')
    validate_stage_identity(identity['stage_identity'], identity['experiment_arm'], identity['index_identity'])
    nested = identity['student_identity']
    common._validate(nested)  # A genuine common payload, never a relabeled041 dictionary.
    for key in ('arm','update','final_update','index_identity','reference_calls','adapter_sha256'):
        if nested[key] != identity[key]:
            raise ValueError('041 student payload differs from outer '+key)
    if nested['base_lineage'] != identity['stage_identity']['initialization_identity']['base_lineage']:
        raise ValueError('041 student and initialization base lineage differs')
    update = identity['update']
    _calls(identity['reference_calls'], train_limit=8000, dev_limit=1024, exact_train=8*update)
    _calls(identity['student_calls'], train_limit=22000, dev_limit=2560, exact_train=22*update)
    _calls(identity['old10_calls'], train_limit=4000 if identity['experiment_arm']=='r1' else 0, dev_limit=0)
    if identity['old10_calls']['train'] > 4*update:
        raise ValueError('041 old10 calls exceed actual update bound')


def read_adapter_identity(directory):
    directory = Path(directory)
    identity = json.loads((directory/'identity.json').read_text(encoding='utf-8'))
    validate_adapter_identity(identity)
    if common.sha256(directory/'adapter.pt') != identity['adapter_sha256']:
        raise ValueError('041 adapter byte hash mismatch')
    return identity


def save_adapter(policy, directory, *, experiment_arm, update, index_identity,
                 stage_identity, reference_calls, student_calls, old10_calls):
    import torch
    validate_stage_identity(stage_identity, experiment_arm, index_identity)
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('A new041 adapter directory is required')
    if not hasattr(policy.model, 'task_control'):
        raise ValueError('041 student modules must be installed before saving')
    state = common._state(policy.model)
    # Build the genuine common student payload in memory. No old identity is
    # ever written at the041 root, including when validation or saving fails.
    nested = {'schema_version':common.SCHEMA,'group':'task_control_factorization',
        'recipe':'task_control_factorization','data_kind':'task038-task-control-data-v1',
        'arm':'c1','update':update,'final_update':1000,'index_identity':index_identity,
        'reference_calls':dict(reference_calls),'training_recipe':deepcopy(common.TRAINING_RECIPE),
        'base_lineage':common._lineage(policy),'implementation':'native-linear-lora-task-control',
        'rank':16,'alpha':32,'dropout':0,
        'target_modules':sorted(n.rsplit('.',1)[0] for n in state if n.endswith('.lora_A')),
        'hidden_dim':policy.model.task_control.hidden_dim,
        'trainable_parameters':{n:list(v.shape) for n,v in sorted(state.items())},
        'tensor_dtypes':{n:str(v.dtype) for n,v in sorted(state.items())},
        'tensor_sha256':{n:common._tensor_hash(v) for n,v in sorted(state.items())},
        'adapter_sha256':'0'*64}
    identity = {'schema_version':SCHEMA,'group':GROUP,'recipe':GROUP,
        'data_kind':'task041-existing040-data-v1','arm':'c1','experiment_arm':experiment_arm,
        'update':update,'final_update':1000,'index_identity':index_identity,
        'stage_identity':deepcopy(stage_identity),'student_identity':nested,
        'reference_calls':dict(reference_calls),'student_calls':dict(student_calls),
        'old10_calls':dict(old10_calls),'adapter_sha256':nested['adapter_sha256']}
    validate_adapter_identity(identity)
    directory.mkdir(parents=True,exist_ok=False)
    torch.save(state,directory/'adapter.pt')
    nested['adapter_sha256'] = common.sha256(directory/'adapter.pt')
    identity['adapter_sha256'] = nested['adapter_sha256']
    (directory/'identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2),encoding='utf-8')
    return identity


def restore_adapter_weights(policy, directory, identity=None):
    identity = read_adapter_identity(directory) if identity is None else identity
    validate_adapter_identity(identity)
    state = load_source_state(policy, directory, identity['student_identity'])
    _copy_student(policy, state)
    return identity


def attach_trained_adapter(policy, directory, experiment_arm=None):
    from egrs.task_control.oft import install
    identity = read_adapter_identity(directory)
    if experiment_arm is not None and identity['experiment_arm'] != experiment_arm:
        raise ValueError('041 adapter experiment arm differs from requested arm')
    if identity['student_identity']['base_lineage'] != common._lineage(policy):
        raise ValueError('041 adapter base lineage mismatch')
    if not hasattr(policy.model, 'task_control'):
        targets = install(policy)
    else:
        targets = sorted(n.rsplit('.',1)[0] for n in common._state(policy.model) if n.endswith('.lora_A'))
    if targets != identity['student_identity']['target_modules']:
        raise ValueError('041 loaded language target inventory differs')
    restore_adapter_weights(policy, directory, identity)
    policy.model.requires_grad_(False)
    policy.model.eval()
    return identity
