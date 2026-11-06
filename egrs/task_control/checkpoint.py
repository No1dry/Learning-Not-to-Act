"""Strict task038 optimizer/RNG/sampler/ledger checkpoints, never old adapters."""
import json
from pathlib import Path
import random

import numpy as np
import torch

from egrs.augmentation.adapter_identity import sha256


def save_training_state(directory, policy, optimizer, scheduler, sampler, *, update,
                        config, arm, index_identity, reference_budget, student_budget):
    from .adapter import save_adapter
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('A new task038 checkpoint directory is required')
    identity = save_adapter(policy, directory, arm=arm, update=update,
                            index_identity=index_identity, reference_calls=reference_budget.report())
    state = {'update': update, 'config': config, 'arm': arm, 'index_identity': index_identity,
        'optimizer': optimizer.state_dict(), 'scheduler': scheduler.state_dict(),
        'sampler': sampler.state_dict(), 'reference_budget': reference_budget.state_dict(),
        'student_budget': student_budget.state_dict(), 'python_rng': random.getstate(),
        'numpy_rng': np.random.get_state(), 'torch_rng': torch.get_rng_state(),
        'cuda_rng': torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None}
    torch.save(state, directory / 'training_state.pt')
    (directory / 'training_state.sha256').write_text(sha256(directory / 'training_state.pt') + '\n', encoding='ascii')
    return identity


def load_training_state(directory, policy, optimizer, scheduler, sampler, *, config,
                        arm, index_identity, reference_budget, student_budget):
    from .adapter import read_adapter_identity, restore_adapter_weights
    directory = Path(directory)
    identity = read_adapter_identity(directory)
    if identity['arm'] != arm:
        raise ValueError('Resume arm differs from the saved task038 adapter')
    if identity['index_identity'] != index_identity:
        raise ValueError('Resume task038 index identity changed')
    if sha256(directory / 'training_state.pt') != (directory / 'training_state.sha256').read_text().strip():
        raise ValueError('Resume training state byte hash mismatch')
    # This is a local user-created checkpoint containing Python/NumPy RNG state.
    state = torch.load(directory / 'training_state.pt', map_location='cpu', weights_only=False)
    required = {'update', 'config', 'arm', 'index_identity', 'optimizer', 'scheduler', 'sampler',
                'reference_budget', 'student_budget', 'python_rng', 'numpy_rng', 'torch_rng', 'cuda_rng'}
    if not isinstance(state, dict) or set(state) != required:
        raise ValueError('Resume training state has missing or extra fields')
    if state['arm'] != arm or state['index_identity'] != index_identity or state['config'] != config:
        raise ValueError('Resume arm, configuration or task038 index identity changed')
    if (type(state['update']) is not int or not 0 < state['update'] <= config['updates']
            or state['update'] != identity['update']
            or state['reference_budget'] != identity['reference_calls']):
        raise ValueError('Resume adapter update or reference budget differs from optimizer state')
    Reference = type(reference_budget)
    Student = type(student_budget)
    Reference._validated(state['reference_budget'])
    Student._validated(state['student_budget'])
    if (state['reference_budget']['train'] != 8 * state['update']
            or state['student_budget']['train'] != 22 * state['update']
            or state['sampler']['pair']['draws'] != state['update']
            or state['sampler']['main']['counts'] != {'ten': 12 * state['update'],
                'fresh': 4 * state['update'], 'raw': 4 * state['update']}):
        raise ValueError('Resume observation budgets or sample sequence do not match the update')
    restore_adapter_weights(policy, directory, identity=identity)
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    sampler.load_state_dict(state['sampler'])
    reference_budget.load_state_dict(state['reference_budget'])
    student_budget.load_state_dict(state['student_budget'])
    # Advanced durable ledgers cannot be silently replayed against an older
    # sampler checkpoint, which would change the promised same-sample sequence.
    if (reference_budget.report() != state['reference_budget']
            or student_budget.report() != state['student_budget']):
        raise ValueError('Resume checkpoint is older than spent forward budget; exact continuation is unavailable')
    random.setstate(state['python_rng'])
    np.random.set_state(state['numpy_rng'])
    torch.set_rng_state(state['torch_rng'])
    if state['cuda_rng'] is not None:
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['update']
