"""Full same-run resume; no refund of durable spent forward allocations."""
from pathlib import Path
import random

import numpy as np
import torch

from . import adapter
from .contracts import sha, require, write_json


def save(directory,policy,optimizer,scheduler,sampler,*,update,config,sidecar_identity,reference_budget,model_budget):
    v = adapter.save_adapter(policy,directory,arm=config['arm'],update=update,sidecar_identity=sidecar_identity,
        reference_calls=reference_budget.report(),model_calls=model_budget.report())
    state = {'format':'task043-training-state-v1','update':update,'config':config,
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
    from .contracts import read_json
    root = Path(directory)
    v = adapter.read_adapter_identity(root)
    p = root/'training_state.pt'
    require(sha(p)==read_json(root/'training_state_hash.json')['sha256'], 'Full training state bytes differ')
    # Trusted, user-created resume artifact, not a downloaded arbitrary pickle.
    s = torch.load(p,map_location='cpu',weights_only=False)
    require(s.get('format')=='task043-training-state-v1' and s['config']==config
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
