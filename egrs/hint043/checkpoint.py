"""Full same-run resume; no refund of durable spent forward allocations."""
from pathlib import Path
import random

import numpy as np
import torch

from . import adapter
from .contracts import sha, require, write_json, read_json, RECIPE, training_recipe


def save(directory,policy,optimizer,scheduler,sampler,*,update,config,sidecar_identity,reference_budget,model_budget):
    v = adapter.save_adapter(policy,directory,arm=config['arm'],update=update,sidecar_identity=sidecar_identity,
        reference_calls=reference_budget.report(),model_calls=model_budget.report(),
        target_updates=config['training_recipe']['updates'],continuation_parent=config.get('continuation_parent'))
    state = {'format':'task043-training-state-v1' if config['training_recipe']['updates']==1000 else 'task043-training-state-v2','update':update,'config':config,
        'sidecar_identity':sidecar_identity,'adapter_sha256':v['adapter_sha256'],
        'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'sampler':sampler.state_dict(),
        'reference_budget':reference_budget.report(),'model_budget':model_budget.report(),
        'python_rng':random.getstate(),'numpy_rng':np.random.get_state(),'torch_rng':torch.get_rng_state(),
        'cuda_rng':torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None}
    p = Path(directory)/'training_state.pt'
    torch.save(state,p)
    write_json(Path(directory)/'training_state_hash.json', {'sha256':sha(p)})
    return v


def load(directory,policy,optimizer,scheduler,sampler,*,config,sidecar_identity,reference_budget,model_budget):
    root = Path(directory)
    v = adapter.read_adapter_identity(root)
    p = root/'training_state.pt'
    require(sha(p)==read_json(root/'training_state_hash.json')['sha256'], 'Full training state bytes differ')
    # Trusted, user-created resume artifact, not a downloaded arbitrary pickle.
    s = torch.load(p,map_location='cpu',weights_only=False)
    require(s.get('format')==('task043-training-state-v1' if config['training_recipe']['updates']==1000 else 'task043-training-state-v2') and s['config']==config
        and s['sidecar_identity']==sidecar_identity==v['sidecar_identity']
        and s['adapter_sha256']==v['adapter_sha256'] and s['update']==v['update']
        and v['arm']==config['arm'] and s['reference_budget']==v['reference_calls']
        and s['model_budget']==v['model_calls'], 'Resume config/arm/data/checkpoint identity differs')
    require(s['sampler']['counts']=={'ten':12*s['update'],'fresh':4*s['update'],'raw':4*s['update']}, 'Sampler update mismatch')
    reference_budget.load_state_dict(s['reference_budget'])
    model_budget.load_state_dict(s['model_budget'])
    require(reference_budget.report()==s['reference_budget'] and model_budget.report()==s['model_budget'],
            'Checkpoint older than spent forwards; exact resume cannot refund or replay')
    adapter.restore(policy,root,v)
    optimizer.load_state_dict(s['optimizer']);scheduler.load_state_dict(s['scheduler']);sampler.load_state_dict(s['sampler'])
    random.setstate(s['python_rng']);np.random.set_state(s['numpy_rng']);torch.set_rng_state(s['torch_rng'])
    if s['cuda_rng'] is not None: torch.cuda.set_rng_state_all(s['cuda_rng'])
    return s['update']


def parent_binding(directory):
    """Read immutable parent identities, never reset the parent ledger."""
    root=Path(directory).resolve();v=adapter.read_adapter_identity(root)
    require(v['update']==v['final_update']==1000, 'Continuation must begin at the fixed original1000')
    state_sha=sha(root/'training_state.pt')
    require(state_sha==read_json(root/'training_state_hash.json')['sha256'], 'Parent full training state bytes differ')
    require(read_json(root.parent/'reference_budget.json')==v['reference_calls']
            and read_json(root.parent/'model_budget.json')==v['model_calls'],
            'Parent has spend beyond its checkpoint; do not refund/replay')
    return {'update':1000,'arm':v['arm'],'adapter_sha256':v['adapter_sha256'],
        'training_state_sha256':state_sha,'identity_sha256':sha(root/'identity.json'),
        'run_config_sha256':sha(root.parent/'run_config.json')}


def extend_from(directory,policy,optimizer,scheduler,sampler,*,config,sidecar_identity,reference_budget,model_budget):
    root=Path(directory).resolve();binding=parent_binding(root)
    require(config['continuation_parent']==binding and binding['arm']==config['arm'], 'Wrong continuation parent/arm')
    v=adapter.read_adapter_identity(root)
    s=torch.load(root/'training_state.pt',map_location='cpu',weights_only=False)
    require(s.get('format')=='task043-training-state-v1' and s['update']==1000
        and s['adapter_sha256']==v['adapter_sha256'] and s['sidecar_identity']==sidecar_identity==v['sidecar_identity']
        and s['reference_budget']==v['reference_calls'] and s['model_budget']==v['model_calls']
        and s['config']==read_json(root.parent/'run_config.json') and s['config']['training_recipe']==RECIPE,
        'Original1000 full state/identity/config differs')
    for key in ('arm','index_dir','sidecar_dir','benchmark_root','runtime','dev_selection','initialization'):
        require(s['config'].get(key)==config.get(key), 'Continuation changes original data/runtime/selection: '+key)
    require(s['sampler']['counts']=={'ten':12000,'fresh':4000,'raw':4000}, 'Parent sampler count differs')
    selection=s['config']['dev_selection']
    ref_views=sum(len(selection[p][b]) for p in ('fresh','raw') for b in ('prefix','all'))
    require(s['reference_budget']['train']==8000 and s['reference_budget']['dev']==4*ref_views
        and s['model_budget']['main_train']==20000 and s['model_budget']['main_dev']==4*(len(selection['ten'])+ref_views)
        and s['model_budget']['aux_dev']<=4*len(selection['ten']) and s['scheduler']['last_epoch']==1000,
        'Original1000 is not the completed dev/scheduler endpoint')
    adapter.restore(policy,root,v)
    optimizer.load_state_dict(s['optimizer']);scheduler.load_state_dict(s['scheduler']);sampler.load_state_dict(s['sampler'])
    reference_budget.inherit(s['reference_budget']);model_budget.inherit(s['model_budget'])
    random.setstate(s['python_rng']);np.random.set_state(s['numpy_rng']);torch.set_rng_state(s['torch_rng'])
    if s['cuda_rng'] is not None:torch.cuda.set_rng_state_all(s['cuda_rng'])
    return 1000
