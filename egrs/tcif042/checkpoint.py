"""Same042 run continuation with two durable forward ledgers and full RNG state."""
from copy import deepcopy
import json
from pathlib import Path
import random

import numpy as np
import torch

from egrs.augmentation.adapter_identity import sha256
from .adapter import save_adapter,read_adapter_identity,restore_adapter_weights,validate_stage_identity

SCHEMA = 'task042-training-state-v1'


def _same_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected,dict):
        return actual.keys() == expected.keys() and all(_same_value(actual[k],v) for k,v in expected.items())
    if isinstance(expected,(list,tuple)):
        return len(actual) == len(expected) and all(_same_value(a,b) for a,b in zip(actual,expected))
    return actual == expected


def _validate_state(state, identity, config, experiment_arm, index_identity, stage_identity,
                    reference_budget, student_budget):
    fields = {'schema_version','update','config','experiment_arm','index_identity','stage_identity',
        'optimizer','scheduler','sampler','reference_budget','student_budget',
        'python_rng','numpy_rng','torch_rng','cuda_rng'}
    if not isinstance(state,dict) or set(state) != fields or state['schema_version'] != SCHEMA:
        raise ValueError('042 training state has missing, extra or invalid fields')
    for key,expected in (('config',config),('experiment_arm',experiment_arm),
        ('index_identity',index_identity),('stage_identity',stage_identity)):
        if not _same_value(state[key],expected):
            raise ValueError('042 resume configuration, arm, index or stage identity changed: '+key)
    if (type(state['update']) is not int or not 1 <= state['update'] <= config.get('updates',1000)
            or state['update'] != identity['update']):
        raise ValueError('042 resume adapter and training state update differs')
    for key,adapter_key,budget in (('reference_budget','reference_calls',reference_budget),
                                   ('student_budget','student_calls',student_budget)):
        type(budget)._validated(state[key])
        if state[key] != identity[adapter_key]:
            raise ValueError('042 resume adapter and training state budget differs: '+key)
    update = state['update']
    try:
        consistent = (state['reference_budget']['train'] == 8*update
            and state['student_budget']['train'] == 22*update
            and state['sampler']['pair']['draws'] == update
            and state['sampler']['main']['counts'] == {'ten':12*update,'fresh':4*update,'raw':4*update})
    except (KeyError,TypeError):
        consistent = False
    if not consistent:
        raise ValueError('042 resume observation budgets or sample sequence do not match the update')


def save_training_state(directory, policy, optimizer, scheduler, sampler, *, update,
                        config, experiment_arm, index_identity, stage_identity,
                        reference_budget, student_budget):
    validate_stage_identity(stage_identity,experiment_arm,index_identity)
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('A new042 checkpoint directory is required')
    state = {'schema_version':SCHEMA,'update':update,'config':deepcopy(config),
        'experiment_arm':experiment_arm,'index_identity':index_identity,'stage_identity':deepcopy(stage_identity),
        'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'sampler':sampler.state_dict(),
        'reference_budget':reference_budget.state_dict(),'student_budget':student_budget.state_dict(),
        'python_rng':random.getstate(),'numpy_rng':np.random.get_state(),'torch_rng':torch.get_rng_state(),
        'cuda_rng':torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None}
    # Reject inconsistent progress before creating even an adapter-only root.
    preview = {'update':update,'reference_calls':reference_budget.report(),'student_calls':student_budget.report()}
    _validate_state(state,preview,config,experiment_arm,index_identity,stage_identity,reference_budget,student_budget)
    identity = save_adapter(policy,directory,experiment_arm=experiment_arm,update=update,
        index_identity=index_identity,stage_identity=stage_identity,
        reference_calls=reference_budget.report(),student_calls=student_budget.report())
    _validate_state(state,identity,config,experiment_arm,index_identity,stage_identity,reference_budget,student_budget)
    torch.save(state,directory/'training_state.pt')
    (directory/'training_state.sha256').write_text(sha256(directory/'training_state.pt')+'\n',encoding='ascii')
    return identity


def _check_spent(budget, saved):
    reports = [budget.report()]
    path = getattr(budget,'ledger_path',None)
    if path is not None and Path(path).exists():
        disk = json.loads(Path(path).read_text(encoding='utf-8'))
        type(budget)._validated(disk)
        reports.append(disk)
    if any(report[split] > saved[split] for report in reports for split in ('train','dev')):
        raise ValueError('042 resume checkpoint is older than spent forward budget; exact continuation is unavailable')


def load_training_state(directory, policy, optimizer, scheduler, sampler, *, config,
                        experiment_arm, index_identity, stage_identity, reference_budget, student_budget):
    validate_stage_identity(stage_identity,experiment_arm,index_identity)
    directory = Path(directory)
    identity = read_adapter_identity(directory)
    if (identity['experiment_arm'] != experiment_arm or identity['index_identity'] != index_identity
            or identity['stage_identity'] != stage_identity):
        raise ValueError('042 resume adapter arm, index or stage identity changed')
    if sha256(directory/'training_state.pt') != (directory/'training_state.sha256').read_text().strip():
        raise ValueError('042 resume training state byte hash mismatch')
    # This trusted local same-run file includes Python and NumPy RNG objects.
    state = torch.load(directory/'training_state.pt',map_location='cpu',weights_only=False)
    _validate_state(state,identity,config,experiment_arm,index_identity,stage_identity,reference_budget,student_budget)
    budgets = ((reference_budget,'reference_budget'),(student_budget,'student_budget'))
    for budget,key in budgets:
        _check_spent(budget,state[key])
    restore_adapter_weights(policy,directory,identity)
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    sampler.load_state_dict(state['sampler'])
    for budget,key in budgets:
        budget.load_state_dict(state[key])
        if budget.report() != state[key]:
            raise ValueError('042 resume checkpoint is older than spent forward budget; exact continuation is unavailable')
    random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
    torch.set_rng_state(state['torch_rng'])
    if state['cuda_rng'] is not None:
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['update']
