"""One-model original SOG10 reference view and durable observation ledgers."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

import torch

from egrs.augmentation.oft import LoRALinear, training_prediction


def policy_modules(policy):
    return list({id(module): module
                 for root in (policy.model, policy.action_head, policy.proprio_projector)
                 for module in root.modules()}.values())


@contextmanager
def shared_base_reference(policy):
    """Bypass every added branch before any student graph is constructed.

    Direct restoration preserves deliberately mixed train/eval subtrees and
    checkpoint flags. New integration normally has no hooks; explicitly tagged
    task-control hooks are also suspended, including hooks installed on the head.
    """
    modules = policy_modules(policy)
    context = getattr(policy.model, 'task_control', None)
    loras = [m for m in modules if isinstance(m, LoRALinear)]
    if context is None or not hasattr(context, 'enabled') or not loras:
        raise ValueError('Original-base reference requires installed task_control and native LoRA')
    modes = [(m, m.training) for m in modules]
    adapters = [(m, m.enabled) for m in loras] + [(context, context.enabled)]
    checkpoints = [(m, m.gradient_checkpointing) for m in modules
                   if isinstance(getattr(m, 'gradient_checkpointing', None), bool)]
    caches = list({id(m.config): m.config for m in modules
                   if getattr(m, 'config', None) is not None and hasattr(m.config, 'use_cache')}.values())
    cache_flags = [(config, config.use_cache) for config in caches]
    hook_tables = []
    for module in modules:
        for name in ('_forward_hooks', '_forward_pre_hooks', '_backward_hooks', '_backward_pre_hooks'):
            table = getattr(module, name, None)
            if table is not None and any(getattr(h, '_task_control_hook', False) for h in table.values()):
                hook_tables.append((table, table.copy()))
    try:
        for module, _ in modes:
            module.training = False
        for module, _ in adapters:
            module.enabled = False
        for module, _ in checkpoints:
            module.gradient_checkpointing = False
        for config, _ in cache_flags:
            config.use_cache = False
        for table, _ in hook_tables:
            for key, hook in list(table.items()):
                if getattr(hook, '_task_control_hook', False):
                    del table[key]
        with torch.no_grad():
            yield
    finally:
        for table, saved in hook_tables:
            table.clear()
            table.update(saved)
        for config, flag in cache_flags:
            config.use_cache = flag
        for module, flag in checkpoints:
            module.gradient_checkpointing = flag
        for module, enabled in adapters:
            module.enabled = enabled
        for module, training in modes:
            module.training = training


def reference_prediction(policy, item, predict=None):
    # The original OFT function reads only original action hidden states. It
    # cannot accidentally execute the new context/count/residual computation.
    with shared_base_reference(policy):
        output = (training_prediction if predict is None else predict)(policy, item)
        if (not isinstance(output, torch.Tensor) or tuple(output.shape) != (1, 8, 7)
                or not torch.is_floating_point(output) or not torch.isfinite(output).all()):
            raise ValueError('Reference must produce finite normalized actions with shape 1x8x7')
        return output.detach().clone()


class ObservationBudget:
    """Allocate durably before a forward; loading a checkpoint never refunds."""
    LIMITS = {}
    NAME = 'observation'

    def __init__(self, ledger_path=None):
        self.ledger_path = Path(ledger_path) if ledger_path is not None else None
        self.counts = {key: 0 for key in self.LIMITS}
        if self.ledger_path is not None and self.ledger_path.exists():
            self.counts = self._validated(json.loads(self.ledger_path.read_text(encoding='utf-8')))

    @classmethod
    def _validated(cls, value):
        if (not isinstance(value, dict) or set(value) != {'train', 'dev', 'total', 'budget'}
                or type(value.get('budget')) is not int or value['budget'] != sum(cls.LIMITS.values())
                or any(type(value.get(key)) is not int or not 0 <= value[key] <= limit
                       for key, limit in cls.LIMITS.items())
                or type(value.get('total')) is not int
                or value['total'] != value['train'] + value['dev']):
            raise ValueError(f'{cls.NAME} budget state is invalid')
        return {key: value[key] for key in cls.LIMITS}

    def report(self):
        return {**self.counts, 'total': sum(self.counts.values()), 'budget': sum(self.LIMITS.values())}

    def state_dict(self):
        return self.report()

    def _persist(self):
        if self.ledger_path is not None:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.ledger_path.with_suffix(self.ledger_path.suffix + '.tmp')
            temporary.write_text(json.dumps(self.report(), sort_keys=True) + '\n', encoding='utf-8')
            os.replace(temporary, self.ledger_path)

    def consume(self, split, count=1):
        if split not in self.LIMITS or type(count) is not int or count <= 0:
            raise ValueError(f'{self.NAME} budget requires train/dev and a positive observation count')
        if self.counts[split] + count > self.LIMITS[split]:
            raise ValueError(f'{self.NAME} budget exhausted; no extra forward authorized')
        self.counts[split] += count
        self._persist()

    def load_state_dict(self, state):
        counts = self._validated(state)
        if self.ledger_path is not None and self.ledger_path.exists():
            disk = self._validated(json.loads(self.ledger_path.read_text(encoding='utf-8')))
            counts = {key: max(counts[key], disk[key]) for key in self.LIMITS}
        self.counts = {key: max(counts[key], self.counts[key]) for key in self.LIMITS}
        self._validated(self.report())
        self._persist()


class ReferenceBudget(ObservationBudget):
    LIMITS = {'train': 8000, 'dev': 1024}
    NAME = 'reference'


class StudentBudget(ObservationBudget):
    LIMITS = {'train': 22000, 'dev': 2560}
    NAME = 'student'
