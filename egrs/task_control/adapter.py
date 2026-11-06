"""Task038 strict adapter identity; planning imports only the standard library."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from egrs.augmentation.adapter_identity import (
    OFT_REVISION, BASE_SOURCE, LINEAGE_KEYS, TARGET, RETENTION_STATS_SHA,
    RETENTION_RECIPE, _lineage, sha256,
)

SCHEMA = 'task038-oft-adapter-v1'
TRAINING_RECIPE = dict(deepcopy(RETENTION_RECIPE), z_dim=128, context_hidden=256,
    residual_bottleneck=256, pair_observations=2, student_observations_per_update=22,
    gradient_accumulation=22, photometric_probability=0.,
    lora_rank=16, lora_alpha=32, learning_rate=2e-5, warmup_updates=50, precision='bf16',
    save_every=250, checkpoint_selection='fixed_final_1000',
    input_fields=['images', 'instruction', 'proprio'],
    losses={'c0': {'main':1., 'count':.1, 'self':.1, 'swap':0., 'align':0.},
            'c1': {'main':1., 'count':.1, 'self':.05, 'swap':.05, 'align':.01}},
    align_epsilon=1e-6, reference_view='original_base_without_all_new_modules')


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _module_shapes(dim):
    return {'task_control.'+name:shape for name,shape in {
        'context.0.weight':[256,2*dim], 'context.0.bias':[256],
        'context.2.weight':[128,256], 'context.2.bias':[128],
        'norm.weight':[dim], 'norm.bias':[dim], 'W_h.weight':[256,dim],
        'W_z.weight':[256,128], 'W_p.weight':[256,8], 'W_out.weight':[dim,256],
        'count_head.weight':[3,128], 'count_head.bias':[3]}.items()}


def _validate(identity):
    if not isinstance(identity,dict):
        raise ValueError('Task038 identity must be a JSON object')
    if (identity.get('schema_version') != SCHEMA or identity.get('group') != 'task_control_factorization'
            or identity.get('recipe') != 'task_control_factorization'
            or identity.get('data_kind') != 'task038-task-control-data-v1'
            or identity.get('arm') not in ('c0','c1')
            or type(identity.get('update')) is not int or not 1 <= identity['update'] <= 1000
            or identity.get('final_update') != 1000
            or identity.get('training_recipe') != TRAINING_RECIPE
            or not _digest(identity.get('index_identity'))):
        raise ValueError('Invalid task038 recipe, arm, update or data index identity')
    calls = identity.get('reference_calls', {})
    if (not isinstance(calls, dict) or set(calls) != {'train','dev','total','budget'}
            or any(type(value) is not int for value in calls.values())
            or calls['train'] != 8 * identity['update'] or not 0 <= calls['dev'] <= 1024
            or calls['total'] != calls['train'] + calls['dev'] or calls['budget'] != 9024
            or calls['total'] > 9024):
        raise ValueError('Invalid task038 reference budget counters')
    lineage = identity.get('base_lineage', {})
    if not isinstance(lineage,dict):
        raise ValueError('Invalid task038 original base/statistics lineage')
    components = lineage.get('component_checkpoint_sha256', {})
    if (set(lineage) != set(LINEAGE_KEYS) or lineage.get('repo_commit') != OFT_REVISION
            or lineage.get('checkpoint_source') != BASE_SOURCE
            or lineage.get('dataset_statistics_sha256') != RETENTION_STATS_SHA
            or not _digest(lineage.get('normalization_statistics_sha256'))
            or lineage.get('unnorm_key') != 'libero_10_no_noops'
            or not isinstance(components, dict) or len(components) != 2
            or not all(_digest(value) for value in components.values())
            or not all(sum(part in name for name in components) == 1
                       for part in ('action_head','proprio_projector'))):
        raise ValueError('Invalid task038 original base/statistics lineage')
    if (identity.get('implementation') != 'native-linear-lora-task-control'
            or (identity.get('rank'),identity.get('alpha'),identity.get('dropout')) != (16,32,0)):
        raise ValueError('Invalid task038 adapter implementation')
    targets = identity.get('target_modules', [])
    if (not isinstance(targets,list) or not targets or not all(isinstance(name,str) for name in targets)
            or targets != sorted(set(targets))
            or any(not TARGET.fullmatch(name) for name in targets)):
        raise ValueError('Invalid task038 LoRA inventory')
    parents = {name.rsplit('.',1)[0] for name in targets}
    if any({name.rsplit('.',1)[1] for name in targets if name.startswith(parent+'.')}
           != {'q_proj','k_proj','v_proj','o_proj'} for parent in parents):
        raise ValueError('Incomplete task038 language q/k/v/o inventory')
    dim = identity.get('hidden_dim')
    if type(dim) is not int or dim < 1:
        raise ValueError('Invalid task038 hidden dimension')
    shapes = identity.get('trainable_parameters', {})
    expected = _module_shapes(dim)
    expected.update({target+suffix:([16,dim] if suffix=='.lora_A' else [dim,16])
                     for target in targets for suffix in ('.lora_A','.lora_B')})
    if shapes != expected:
        raise ValueError('Task038 parameter inventory or shapes mismatch')
    if (not isinstance(identity.get('tensor_sha256'),dict)
            or set(identity['tensor_sha256']) != set(shapes)
            or not all(_digest(value) for value in identity['tensor_sha256'].values())
            or identity.get('tensor_dtypes') != {name:'torch.float32' for name in shapes}
            or not _digest(identity.get('adapter_sha256'))):
        raise ValueError('Invalid task038 tensor hashes or dtypes')


def read_adapter_identity(directory):
    """Validate complete metadata and byte hash without importing model libraries."""
    directory = Path(directory)
    identity = json.loads((directory/'identity.json').read_text(encoding='utf-8'))
    _validate(identity)
    if sha256(directory/'adapter.pt') != identity['adapter_sha256']:
        raise ValueError('Task038 adapter byte hash mismatch')
    return identity


def _state(model):
    return {name:value.detach().cpu().contiguous() for name,value in model.named_parameters()
            if name.startswith('task_control.') or name.endswith(('.lora_A','.lora_B'))}


def _tensor_hash(value):
    import torch
    return hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def save_adapter(policy, directory, *, arm, update, index_identity, reference_calls):
    import torch
    if not hasattr(policy.model,'task_control'):
        raise ValueError('Task038 modules must be installed before saving')
    state = _state(policy.model)
    identity = {'schema_version':SCHEMA, 'group':'task_control_factorization',
        'recipe':'task_control_factorization', 'data_kind':'task038-task-control-data-v1',
        'arm':arm, 'update':update, 'final_update':1000, 'index_identity':index_identity,
        'reference_calls':dict(reference_calls), 'training_recipe':deepcopy(TRAINING_RECIPE),
        'base_lineage':_lineage(policy), 'implementation':'native-linear-lora-task-control',
        'rank':16, 'alpha':32, 'dropout':0,
        'target_modules': sorted(name.rsplit('.',1)[0] for name in state if name.endswith('.lora_A')),
        'hidden_dim':policy.model.task_control.hidden_dim,
        'trainable_parameters':{name:list(value.shape) for name,value in sorted(state.items())},
        'tensor_dtypes':{name:str(value.dtype) for name,value in sorted(state.items())},
        'tensor_sha256':{name:_tensor_hash(value) for name,value in sorted(state.items())},
        'adapter_sha256':'0'*64}
    _validate(identity)
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    torch.save(state,directory/'adapter.pt')
    identity['adapter_sha256'] = sha256(directory/'adapter.pt')
    (directory/'identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2),encoding='utf-8')
    return identity


def restore_adapter_weights(policy, directory, identity=None):
    """Restore an installed student without altering training/optimizer flags."""
    import torch
    identity = read_adapter_identity(directory) if identity is None else identity
    _validate(identity)
    if sha256(Path(directory)/'adapter.pt') != identity['adapter_sha256']:
        raise ValueError('Task038 adapter byte hash mismatch')
    if identity['base_lineage'] != _lineage(policy):
        raise ValueError('Task038 adapter base lineage mismatch')
    state = torch.load(Path(directory)/'adapter.pt',map_location='cpu',weights_only=True)
    actual, expected = _state(policy.model), identity['trainable_parameters']
    if not isinstance(state,dict) or set(state) != set(expected) or set(actual) != set(expected):
        raise ValueError('Task038 adapter tensor inventory mismatch')
    # Validate every tensor before copying any value into the live student.
    for name,value in state.items():
        if (not isinstance(value,torch.Tensor) or list(value.shape) != expected[name]
                or list(actual[name].shape) != expected[name]
                or str(value.dtype) != identity['tensor_dtypes'][name]
                or _tensor_hash(value) != identity['tensor_sha256'][name]
                or not torch.isfinite(value).all()):
            raise ValueError('Task038 adapter tensor shape, dtype or hash mismatch: '+name)
    params = dict(policy.model.named_parameters())
    with torch.no_grad():
        for name,value in state.items(): params[name].copy_(value)
    for module in policy.model.modules():
        if hasattr(module,'enabled') and (module is policy.model.task_control or hasattr(module,'lora_A')):
            module.enabled = True
    return identity


def attach_trained_adapter(policy, directory, arm=None):
    from .oft import install
    identity = read_adapter_identity(directory)
    if arm is not None and identity['arm'] != arm:
        raise ValueError('Task038 adapter arm differs from requested arm')
    if identity['base_lineage'] != _lineage(policy):
        raise ValueError('Task038 adapter base lineage mismatch')
    if not hasattr(policy.model,'task_control'):
        actual_targets = install(policy)
    else:
        actual_targets = sorted(name.rsplit('.',1)[0] for name in _state(policy.model) if name.endswith('.lora_A'))
    if actual_targets != identity['target_modules']:
        raise ValueError('Task038 loaded language target inventory differs')
    restore_adapter_weights(policy,directory,identity)
    policy.model.requires_grad_(False)
    policy.model.eval()
    return identity
