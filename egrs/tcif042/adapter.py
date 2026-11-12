"""Strict042 envelope around the complete041R0 student parameter payload.

Metadata readers deliberately import only the standard library. Historical
readers and base lineage retain their original identities;042 execution has a
separate, mandatory attention contract.
"""
from copy import deepcopy
import json
from pathlib import Path

from egrs.task_control import adapter as common
from egrs.retention041 import adapter as previous
from .contract import contract_for, validate_contract

SCHEMA = 'task042-tcif-adapter-v1'
GROUP = 'task_control_information_firewall'
DATA_KIND = 'task042-existing040-data-v1'
INITIALIZATION_SHA256 = 'd4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397'
INDEX_IDENTITY = '8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe'


def _validate_source(identity, index_identity=None):
    previous.validate_adapter_identity(identity)
    if (identity['arm'] != 'c1' or identity['experiment_arm'] != 'r0'
            or identity['update'] != 1000 or identity['final_update'] != 1000):
        raise ValueError('042 initialization requires the complete041 R0 fixed final1000 student')
    if identity['adapter_sha256'] != INITIALIZATION_SHA256:
        raise ValueError('042 initialization source adapter SHA differs from fixed041 R0')
    if identity['index_identity'] != INDEX_IDENTITY or (index_identity is not None and index_identity != INDEX_IDENTITY):
        raise ValueError('042 initialization source index identity differs')
    source_stage = identity['stage_identity']
    if (source_stage['ancestor_updates'] != 1000 or source_stage['additional_updates'] != 1000
            or source_stage['teacher_identity'] is not None or identity['old10_calls']['total'] != 0):
        raise ValueError('042 initialization requires041 R0 with2000 ancestral updates and no old10 teacher')


def read_source_identity(directory, index_identity=None):
    """Verify genuine041 root metadata/bytes before constructing any model."""
    identity = previous.read_adapter_identity(directory)
    _validate_source(identity, index_identity)
    return identity


def initialize_from041(policy, directory, index_identity):
    """Copy every validated student tensor, without old optimizer/RNG/ledgers."""
    identity = read_source_identity(directory, index_identity)
    state = previous.load_source_state(policy, directory, identity['student_identity'])
    previous._copy_student(policy, state)
    return identity


def validate_stage_identity(stage, experiment_arm=None, index_identity=None):
    fields = {'format','arm','experiment_arm','initialization_identity','index_identity',
              'ancestor_updates','additional_updates','attention_contract'}
    if (not isinstance(stage,dict) or set(stage) != fields
            or stage.get('format') != 'task042-stage-inputs-v1' or stage.get('arm') != 'c1'
            or stage.get('experiment_arm') not in ('f0','f1')
            or stage.get('index_identity') != INDEX_IDENTITY
            or type(stage.get('ancestor_updates')) is not int or stage['ancestor_updates'] != 2000
            or type(stage.get('additional_updates')) is not int or stage['additional_updates'] != 1000):
        raise ValueError('Invalid042 stage identity, base arm or update ancestry')
    if ((experiment_arm is not None and stage['experiment_arm'] != experiment_arm)
            or (index_identity is not None and stage['index_identity'] != index_identity)):
        raise ValueError('042 stage experiment arm or index identity differs')
    _validate_source(stage['initialization_identity'], stage['index_identity'])
    validate_contract(stage['attention_contract'], stage['experiment_arm'])


def _runtime(value):
    if not isinstance(value,dict) or not value:
        raise ValueError('042 observed attention runtime must be a nonempty JSON object')
    try:
        encoded = json.dumps(value, sort_keys=True, allow_nan=False)
        if json.loads(encoded) != value:
            raise ValueError('Non-JSON042 attention runtime')
    except (TypeError,ValueError) as error:
        raise ValueError('042 observed attention runtime must contain finite JSON values') from error


def _check_execution(policy, stage_identity, runtime=None):
    controller = getattr(policy,'_tcif042',None)
    if controller is None or controller.contract != stage_identity['attention_contract']:
        raise ValueError('042 installed attention contract differs from saved stage contract')
    validate_contract(controller.contract, stage_identity['experiment_arm'])
    _runtime(controller.runtime)
    if runtime is not None and controller.runtime != runtime:
        raise ValueError('042 observed attention runtime/backend differs from saved adapter')
    return deepcopy(controller.runtime)


def validate_adapter_identity(identity):
    fields = {'schema_version','group','recipe','data_kind','arm','experiment_arm','update',
        'final_update','index_identity','stage_identity','student_identity','reference_calls',
        'student_calls','adapter_sha256','ancestor_updates','additional_updates',
        'total_ancestral_updates','attention_contract','attention_runtime'}
    if (not isinstance(identity,dict) or set(identity) != fields
            or identity.get('schema_version') != SCHEMA or identity.get('group') != GROUP
            or identity.get('recipe') != GROUP or identity.get('data_kind') != DATA_KIND
            or identity.get('arm') != 'c1' or identity.get('experiment_arm') not in ('f0','f1')
            or type(identity.get('update')) is not int or not 1 <= identity['update'] <= 1000
            or type(identity.get('final_update')) is not int or identity['final_update'] != 1000):
        raise ValueError('Invalid042 adapter schema, recipe, arm or update')
    validate_stage_identity(identity['stage_identity'],identity['experiment_arm'],identity['index_identity'])
    update = identity['update']
    if (type(identity['ancestor_updates']) is not int or identity['ancestor_updates'] != 2000
            or type(identity['additional_updates']) is not int or identity['additional_updates'] != update
            or type(identity['total_ancestral_updates']) is not int or identity['total_ancestral_updates'] != 2000+update):
        raise ValueError('Invalid042 adapter update ancestry')
    validate_contract(identity['attention_contract'],identity['experiment_arm'])
    if identity['attention_contract'] != identity['stage_identity']['attention_contract']:
        raise ValueError('042 adapter attention contract differs from stage')
    _runtime(identity['attention_runtime'])
    nested = identity['student_identity']
    common._validate(nested)
    for key in ('arm','update','final_update','index_identity','reference_calls','adapter_sha256'):
        if nested[key] != identity[key]:
            raise ValueError('042 student payload differs from outer '+key)
    initial = identity['stage_identity']['initialization_identity']['student_identity']
    if nested['base_lineage'] != initial['base_lineage']:
        raise ValueError('042 student and041 R0 initialization base lineage differs')
    previous._calls(identity['reference_calls'],train_limit=8000,dev_limit=1024,exact_train=8*update)
    previous._calls(identity['student_calls'],train_limit=22000,dev_limit=2560,exact_train=22*update)


def read_adapter_identity(directory):
    directory = Path(directory)
    identity = json.loads((directory/'identity.json').read_text(encoding='utf-8'))
    validate_adapter_identity(identity)
    if common.sha256(directory/'adapter.pt') != identity['adapter_sha256']:
        raise ValueError('042 adapter byte hash mismatch')
    return identity


def save_adapter(policy, directory, *, experiment_arm, update, index_identity,
                 stage_identity, reference_calls, student_calls):
    import torch
    validate_stage_identity(stage_identity,experiment_arm,index_identity)
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('A new042 adapter directory is required')
    if not hasattr(policy.model,'task_control'):
        raise ValueError('042 complete student modules must be installed before saving')
    runtime = _check_execution(policy,stage_identity)
    state = common._state(policy.model)
    if any(not torch.isfinite(value).all() for value in state.values()):
        raise ValueError('042 student tensors must be finite before saving')
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
    identity = {'schema_version':SCHEMA,'group':GROUP,'recipe':GROUP,'data_kind':DATA_KIND,
        'arm':'c1','experiment_arm':experiment_arm,'update':update,'final_update':1000,
        'index_identity':index_identity,'stage_identity':deepcopy(stage_identity),'student_identity':nested,
        'reference_calls':dict(reference_calls),'student_calls':dict(student_calls),'adapter_sha256':'0'*64,
        'ancestor_updates':2000,'additional_updates':update,'total_ancestral_updates':2000+update,
        'attention_contract':deepcopy(stage_identity['attention_contract']),'attention_runtime':runtime}
    validate_adapter_identity(identity)
    directory.mkdir(parents=True,exist_ok=False)
    torch.save(state,directory/'adapter.pt')
    identity['adapter_sha256'] = nested['adapter_sha256'] = common.sha256(directory/'adapter.pt')
    (directory/'identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2),encoding='utf-8')
    return identity


def restore_adapter_weights(policy, directory, identity=None):
    identity = read_adapter_identity(directory) if identity is None else identity
    validate_adapter_identity(identity)
    _check_execution(policy,identity['stage_identity'],identity['attention_runtime'])
    state = previous.load_source_state(policy,directory,identity['student_identity'])
    previous._copy_student(policy,state)
    return identity


def attach_trained_adapter(policy, directory, experiment_arm=None):
    from egrs.task_control.oft import install
    from .attention import install_attention
    identity = read_adapter_identity(directory)
    if experiment_arm is not None and identity['experiment_arm'] != experiment_arm:
        raise ValueError('042 adapter experiment arm differs from requested arm')
    nested = identity['student_identity']
    if nested['base_lineage'] != common._lineage(policy):
        raise ValueError('042 adapter base lineage mismatch')
    if not hasattr(policy.model,'task_control'):
        targets = install(policy)
    else:
        targets = sorted(n.rsplit('.',1)[0] for n in common._state(policy.model) if n.endswith('.lora_A'))
    if targets != nested['target_modules']:
        raise ValueError('042 loaded language target inventory differs')
    controller = install_attention(policy,identity['experiment_arm'])
    policy._tcif042 = controller
    _check_execution(policy,identity['stage_identity'],identity['attention_runtime'])
    restore_adapter_weights(policy,directory,identity)
    policy.model.requires_grad_(False)
    policy.model.eval()
    return identity
