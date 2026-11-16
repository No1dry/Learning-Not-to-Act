"""Independent LoRA-only043 identity; planning stays torch-free."""
from copy import deepcopy
from pathlib import Path

from egrs.augmentation.adapter_identity import (
    BASE_SOURCE, OFT_REVISION, LINEAGE_KEYS, TARGET, RETENTION_STATS_SHA, _lineage)
from .contracts import (ADAPTER_FORMAT, EXTENDED_ADAPTER_FORMAT, GROUP, INDEX_IDENTITY, RECIPE,
                        require, read_json, write_json, sha, same, training_recipe)
from .budget import ModelBudget, ReferenceBudget


def valid_digest(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def validate(identity):
    v = identity
    target = v.get('final_update')
    recipe = training_recipe(target)
    require(v.get('schema_version') == (ADAPTER_FORMAT if target == 1000 else EXTENDED_ADAPTER_FORMAT) and v.get('group') == GROUP
        and v.get('arm') in ('h0','h1') and type(v.get('update')) is int and 1 <= v['update'] <= target
        and v.get('index_identity') == INDEX_IDENTITY
        and valid_digest(v.get('sidecar_identity')) and same(v.get('training_recipe'),recipe)
        and v.get('initialization') == 'original_sog10_research_update_zero'
        and v.get('deployment_input_fields') == ['images','instruction','proprio']
        and v.get('deployment_hint') is False, 'Invalid043 adapter recipe/inputs')
    lineage = v.get('base_lineage',{})
    require(set(lineage) == set(LINEAGE_KEYS) and lineage['repo_commit'] == OFT_REVISION
        and lineage['checkpoint_source'] == BASE_SOURCE and lineage['dataset_statistics_sha256'] == RETENTION_STATS_SHA
        and lineage['unnorm_key'] == 'libero_10_no_noops'
        and valid_digest(lineage['normalization_statistics_sha256'])
        and len(lineage['component_checkpoint_sha256']) == 2
        and all(valid_digest(h) for h in lineage['component_checkpoint_sha256'].values()), 'Invalid original043 lineage')
    targets = v.get('target_modules',[])
    require(bool(targets) and targets == sorted(set(targets)) and all(TARGET.fullmatch(n) for n in targets)
        and (v.get('rank'),v.get('alpha'),v.get('dropout')) == (16,32,0.0), 'Invalid043 native LoRA inventory')
    for layer in {n.rsplit('.',1)[0] for n in targets}:
        require({n.rsplit('.',1)[1] for n in targets if n.startswith(layer+'.')} == {'q_proj','k_proj','v_proj','o_proj'}, 'Incomplete q/k/v/o')
    shapes = v.get('trainable_parameters',{})
    expected = {t+s for t in targets for s in ('.lora_A','.lora_B')}
    require(set(shapes) == expected and all(isinstance(s,list) and len(s)==2
        and all(type(d) is int and d>0 for d in s)
        and (s[0]==16 if n.endswith('.lora_A') else s[1]==16) for n,s in shapes.items()), 'Non-LoRA parameter or shape')
    require(v.get('tensor_dtypes') == {n:'torch.float32' for n in shapes}
        and set(v.get('tensor_sha256',{})) == expected
        and all(valid_digest(h) for h in v['tensor_sha256'].values()) and valid_digest(v.get('adapter_sha256')), 'Invalid tensor identities')
    # Structural reference validation stays free of torch/model imports.
    calls = v.get('reference_calls',{})
    ReferenceBudget.validated(calls, target_updates=target)
    require(calls['train']==8*v['update'],
        'Invalid reference counters')
    forward = ModelBudget.validated(v.get('model_calls'), target_updates=target)
    require(forward['main_train']==20*v['update'] and forward['aux_train']<=4*v['update'], 'Model counters differ from update')
    if target > 1000:
        parent = v.get('continuation_parent',{})
        require(v['update'] > 1000 and set(parent) == {'update','arm','adapter_sha256','training_state_sha256','identity_sha256','run_config_sha256'}
            and parent['update'] == 1000 and parent['arm'] == v['arm']
            and all(valid_digest(parent[k]) for k in ('adapter_sha256','training_state_sha256','identity_sha256','run_config_sha256')),
            'Extended043 requires exact original1000 parent provenance')


def read_adapter_identity(directory):
    v = read_json(Path(directory)/'identity.json')
    validate(v)
    require(sha(Path(directory)/'adapter.pt') == v['adapter_sha256'], '043 adapter bytes differ')
    return v


def tensor_sha(tensor):
    import hashlib
    import torch
    return hashlib.sha256(tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def state(policy):
    return {n:p.detach().cpu().contiguous().clone() for n,p in policy.model.named_parameters()
            if n.endswith(('.lora_A','.lora_B'))}


def install(policy):
    from egrs.augmentation.oft import inject_language_lora, LoRALinear
    require(not hasattr(policy.model,'task_control') and not hasattr(policy,'_tcif042')
        and not any(isinstance(m,LoRALinear) for m in policy.model.modules()), '043 requires original base, no historical research adapter')
    return inject_language_lora(policy)


def save_adapter(policy,directory,*,arm,update,sidecar_identity,reference_calls,model_calls,
                 target_updates=1000,continuation_parent=None):
    import torch
    p = Path(directory)
    require(not p.exists(), 'Checkpoint already exists')
    tensors = state(policy)
    v = {'schema_version':ADAPTER_FORMAT if target_updates == 1000 else EXTENDED_ADAPTER_FORMAT,
        'group':GROUP,'arm':arm,'update':update,'final_update':target_updates,
        'index_identity':INDEX_IDENTITY,'sidecar_identity':sidecar_identity,'training_recipe':training_recipe(target_updates),
        'initialization':'original_sog10_research_update_zero','base_lineage':_lineage(policy),
        'deployment_input_fields':['images','instruction','proprio'],'deployment_hint':False,
        'rank':16,'alpha':32,'dropout':0.0,
        'target_modules':sorted(n.rsplit('.',1)[0] for n in tensors if n.endswith('.lora_A')),
        'trainable_parameters':{n:list(t.shape) for n,t in tensors.items()},
        'tensor_dtypes':{n:str(t.dtype) for n,t in tensors.items()},
        'tensor_sha256':{n:tensor_sha(t) for n,t in tensors.items()},
        'reference_calls':reference_calls,'model_calls':model_calls,'adapter_sha256':'0'*64}
    if target_updates > 1000:
        v['continuation_parent'] = deepcopy(continuation_parent)
    require(tensors and all(torch.isfinite(t).all() for t in tensors.values()), 'No finite LoRA state')
    validate(v)
    p.mkdir(parents=True)
    torch.save(tensors,p/'adapter.pt')
    v['adapter_sha256'] = sha(p/'adapter.pt')
    write_json(p/'identity.json',v)
    return v


def restore(policy,directory,v=None):
    import torch
    v = read_adapter_identity(directory) if v is None else v
    validate(v)
    require(sha(Path(directory)/'adapter.pt') == v['adapter_sha256'] and _lineage(policy) == v['base_lineage'], 'Original base/adapter changed')
    tensors = torch.load(Path(directory)/'adapter.pt',map_location='cpu',weights_only=True)
    params = dict(policy.model.named_parameters())
    require(set(tensors)==set(v['trainable_parameters'])==set(state(policy)), 'Adapter tensor inventory differs')
    for n,t in tensors.items():
        require(list(t.shape)==v['trainable_parameters'][n]==list(params[n].shape)
            and str(t.dtype)==v['tensor_dtypes'][n] and tensor_sha(t)==v['tensor_sha256'][n]
            and torch.isfinite(t).all().item(), 'Invalid adapter tensor: '+n)
    with torch.no_grad():
        for n,t in tensors.items(): params[n].copy_(t)
    return v


def attach(policy,directory,arm,*,checkpoint_step=1000):
    v = read_adapter_identity(directory)
    require(type(checkpoint_step) is int and checkpoint_step >= 1000 and checkpoint_step % 1000 == 0
            and v['arm']==arm and v['update']==checkpoint_step, 'Requested043 checkpoint step/arm differs')
    targets = install(policy)
    require(targets==v['target_modules'], 'Loaded LoRA target inventory differs')
    restore(policy,directory,v)
    policy.model.requires_grad_(False)
    policy.model.eval()
    return v
