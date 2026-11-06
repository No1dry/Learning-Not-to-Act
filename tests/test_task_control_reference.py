"""Tiny CPU checks for original-base targets and durable observation budgets."""
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from egrs.augmentation.oft import LoRALinear


def tiny_reference_policy():
    model = nn.Module()
    model.language_model = nn.Module()
    model.language_model.layer = LoRALinear(nn.Linear(3, 3))
    model.language_model.gradient_checkpointing = True
    model.language_model.config = SimpleNamespace(use_cache=False)
    model.task_control = nn.Linear(3, 3)
    model.task_control.enabled = True
    return SimpleNamespace(model=model, action_head=nn.Linear(3, 1),
                           proprio_projector=nn.Linear(8, 3))


def test_reference_bypasses_lora_task_control_and_tagged_hooks_and_restores_exception():
    from egrs.task_control.reference import shared_base_reference
    p = tiny_reference_policy()
    p.model.train()
    p.action_head.eval()
    p.model.task_control.eval()
    def added_hook(module, inputs, output):
        return output + 100
    added_hook._task_control_hook = True
    handle = p.action_head.register_forward_hook(added_hook)
    modules = list(p.model.modules()) + list(p.action_head.modules()) + list(p.proprio_projector.modules())
    flags = [m.training for m in modules]
    with pytest.raises(RuntimeError, match='synthetic failure'):
        with shared_base_reference(p):
            assert not p.model.task_control.enabled
            assert not p.model.language_model.layer.enabled
            assert not p.model.language_model.gradient_checkpointing
            assert not any(m.training for m in modules)
            assert not torch.is_grad_enabled()
            assert not p.action_head._forward_hooks
            raise RuntimeError('synthetic failure')
    assert [m.training for m in modules] == flags
    assert p.model.task_control.enabled and p.model.language_model.layer.enabled
    assert p.model.language_model.gradient_checkpointing
    assert p.model.language_model.config.use_cache is False
    assert len(p.action_head._forward_hooks) == 1
    handle.remove()


def test_reference_outputs_plain_base_and_does_not_alias_student_storage():
    from egrs.task_control.reference import reference_prediction
    p = tiny_reference_policy()
    with torch.no_grad():
        p.model.language_model.layer.lora_B.fill_(.4)
    def prediction(policy, item):
        x = policy.model.language_model.layer(torch.ones(1, 3))
        if policy.model.task_control.enabled:
            x = x + policy.model.task_control(x)
        return policy.action_head(x).reshape(1, 1, 1).expand(1, 8, 7)
    expected = p.action_head(p.model.language_model.layer.base_layer(torch.ones(1, 3))).detach()
    value = reference_prediction(p, {}, predict=prediction)
    assert torch.allclose(value, expected.reshape(1, 1, 1).expand(1, 8, 7))
    assert not value.requires_grad
    assert not torch.equal(value, prediction(p, {}))


@pytest.mark.parametrize('kind,limit', [('reference', 8000), ('student', 22000)])
def test_durable_budget_resume_never_rewinds_or_calls_after_exhaustion(tmp_path, kind, limit):
    from egrs.task_control.reference import ReferenceBudget, StudentBudget
    cls = ReferenceBudget if kind == 'reference' else StudentBudget
    path = tmp_path / (kind + '.json')
    budget = cls(path)
    budget.consume('train', limit - 1)
    saved = budget.state_dict()
    budget.consume('train')
    resumed = cls(path)
    resumed.load_state_dict(saved)
    assert resumed.report()['train'] == limit
    with pytest.raises(ValueError, match='budget exhausted'):
        resumed.consume('train')
    assert cls(path).report()['train'] == limit


def test_reference_restoration_allows_nonreentrant_checkpoint_student_backward():
    from torch.utils.checkpoint import checkpoint
    from egrs.task_control.reference import reference_prediction
    p = tiny_reference_policy()
    def predict(policy, item):
        x = policy.model.language_model.layer(item['x'])
        if policy.model.task_control.enabled:
            x = x + policy.model.task_control(x)
        return policy.action_head(x).reshape(1, 1, 1).expand(1, 8, 7)
    item = {'x': torch.ones(1, 3)}
    target = reference_prediction(p, item, predict=predict)
    student = checkpoint(lambda x: predict(p, {'x': x}), item['x'], use_reentrant=False)
    (student - target + 1).square().mean().backward()
    assert p.model.task_control.weight.grad.abs().sum() > 0
    assert p.model.language_model.layer.lora_B.grad.abs().sum() > 0
    assert p.model.language_model.gradient_checkpointing
