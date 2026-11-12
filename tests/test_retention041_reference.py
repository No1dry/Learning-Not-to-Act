"""Tiny real-autograd checks; no real model, dataset or simulator is loaded."""
from copy import deepcopy
import random
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from test_task_control_model import tiny_policy, sensors
from egrs.task_control.adapter import _state
from egrs.task_control.oft import install, prediction, decode


def installed_policy(monkeypatch):
    policy = tiny_policy(monkeypatch)
    targets = install(policy)
    policy.model.language_model.config = SimpleNamespace(use_cache=False)
    with torch.no_grad():
        for name, parameter in policy.model.named_parameters():
            if name.endswith('.lora_B'):
                parameter.fill_(.01)
        policy.model.task_control.W_out.weight.fill_(.01)
    state = {name: value.clone() for name, value in _state(policy.model).items()}
    for value in state.values():
        value.fill_(.03)
    identity = {'hidden_dim': 3, 'target_modules': targets}
    return policy, state, identity


def rng_state():
    return random.getstate(), np.random.get_state(), torch.get_rng_state().clone()


def assert_same_rng(left, right):
    assert left[0] == right[0]
    assert left[1][0] == right[1][0]
    assert np.array_equal(left[1][1], right[1][1])
    assert left[1][2:] == right[1][2:]
    assert torch.equal(left[2], right[2])


def test_teacher_is_distinct_and_preserves_student_parameter_objects_and_rng(monkeypatch):
    # Catches accidental student self-prediction, shared learned storage, or a
    # randomly initialized replacement of any part of the complete039 branch.
    from egrs.retention041.reference import Old10Teacher, original_reference_prediction
    policy, state, identity = installed_policy(monkeypatch)
    parameters = dict(policy.model.named_parameters())
    values = {name: value.detach().clone() for name, value in parameters.items()}
    before_rng = rng_state()
    teacher = Old10Teacher(policy, state, identity)
    assert_same_rng(before_rng, rng_state())
    assert not teacher.training
    assert dict(policy.model.named_parameters()).keys() == parameters.keys()
    for name, parameter in policy.model.named_parameters():
        assert parameter is parameters[name]
        assert torch.equal(parameter, values[name])
    assert not any(value.requires_grad for value in teacher.parameters())
    for name, value in teacher.context.state_dict().items():
        assert torch.equal(value, state['task_control.' + name])
        assert value.data_ptr() != state['task_control.' + name].data_ptr()
        assert value.data_ptr() != policy.model.task_control.state_dict()[name].data_ptr()
    plain = original_reference_prediction(policy, sensors())
    old10 = teacher.predict(policy, sensors())
    student = prediction(policy, sensors()).actions
    assert not torch.equal(plain, old10)
    assert not torch.equal(old10, student)
    assert not torch.equal(plain, student)
    assert old10.shape == (1, 8, 7) and not old10.requires_grad
    with torch.no_grad():
        for value in state.values():
            value.zero_()
    assert torch.equal(old10, teacher.predict(policy, sensors()))


def test_oft_explicit_modules_controls_context_counter_and_decode(monkeypatch):
    # Catches a teacher context being used only by decode while its z/count are
    # still taken from the student, and protects unchanged default calls.
    policy, _, _ = installed_policy(monkeypatch)
    other = deepcopy(policy.model.task_control)
    with torch.no_grad():
        other.W_out.weight.fill_(.1)
        other.count_head.bias.fill_(4.)
    original = prediction(policy, sensors())
    handle = policy.model.task_control.context.register_forward_pre_hook(
        lambda *args: pytest.fail('student context reached in teacher prediction'))
    try:
        alternate = prediction(policy, sensors(), modules=other)
    finally:
        handle.remove()
    assert torch.equal(alternate.actions, decode(policy, alternate, modules=other))
    assert torch.equal(alternate.count_logits, other.count_head(alternate.z))
    assert not torch.equal(alternate.actions, original.actions)
    assert torch.equal(original.actions, decode(policy, original))


@pytest.mark.parametrize('kind', ['original', 'old10'])
def test_reference_exception_restores_mixed_modes_hooks_flags_and_rng(monkeypatch, kind):
    # Catches any reference effect leaking into later dropout/checkpoint graphs.
    from egrs.retention041.reference import Old10Teacher, original_reference_prediction
    from egrs.task_control.reference import policy_modules
    policy, state, identity = installed_policy(monkeypatch)
    teacher = Old10Teacher(policy, state, identity)
    policy.model.train()
    policy.action_head.eval()
    policy.model.task_control.context.eval()
    policy.model.language_model.gradient_checkpointing = True
    policy.model.language_model.config.use_cache = True
    def hook(module, args, output):
        return output + 100
    hook._task_control_hook = True
    handle = policy.action_head.register_forward_hook(hook, always_call=True)
    modules = policy_modules(policy) + list(teacher.context.modules())
    flags = [module.training for module in modules]
    grad_flags = [value.requires_grad for value in policy.model.parameters()]
    hooks = policy.action_head._forward_hooks.copy()
    hook_options = policy.action_head._forward_hooks_always_called.copy()
    before_rng = rng_state()
    def broken(policy, item, *, modules=None):
        assert not torch.is_grad_enabled()
        assert not any(module.training for module in policy_modules(policy))
        assert not policy.model.language_model.gradient_checkpointing
        assert policy.model.language_model.config.use_cache is False
        assert not policy.action_head._forward_hooks
        assert not any(value.requires_grad for value in policy.model.parameters())
        if kind == 'old10':
            assert modules is teacher.context
        random.random(); np.random.random(); torch.rand(2)
        policy.model.task_control.eval()
        raise RuntimeError('reference failed')
    with pytest.raises(RuntimeError, match='reference failed'):
        if kind == 'old10':
            teacher.predict(policy, sensors(), predict=broken)
        else:
            original_reference_prediction(policy, sensors(), predict=broken)
    assert [module.training for module in modules] == flags
    assert [value.requires_grad for value in policy.model.parameters()] == grad_flags
    assert policy.model.language_model.gradient_checkpointing
    assert policy.model.language_model.config.use_cache is True
    assert policy.action_head._forward_hooks == hooks
    assert policy.action_head._forward_hooks_always_called == hook_options
    assert_same_rng(before_rng, rng_state())
    handle.remove()


def test_reference_restores_hook_routing_added_by_failing_prediction(monkeypatch):
    # Hooks created as a predictor side effect must not route later student
    # forwards through reference-only behavior, even on previously empty tables.
    from egrs.retention041.reference import Old10Teacher
    policy, state, identity = installed_policy(monkeypatch)
    teacher = Old10Teacher(policy, state, identity)
    table = policy.model._forward_pre_hooks
    assert not table
    def broken(policy, item, *, modules):
        policy.model.register_forward_pre_hook(lambda *args: None, with_kwargs=True)
        raise RuntimeError('hook setup failed')
    with pytest.raises(RuntimeError, match='hook setup failed'):
        teacher.predict(policy, sensors(), predict=broken)
    assert not policy.model._forward_pre_hooks
    assert not policy.model._forward_pre_hooks_with_kwargs


@pytest.mark.parametrize('value', [torch.zeros(1, 7, 7), torch.ones(1, 8, 7, dtype=torch.int64),
                                 torch.full((1, 8, 7), float('inf'))])
def test_teacher_rejects_malformed_normalized_actions_and_restores_route(monkeypatch, value):
    from egrs.retention041.reference import Old10Teacher
    policy, state, identity = installed_policy(monkeypatch)
    teacher = Old10Teacher(policy, state, identity)
    expected = prediction(policy, sensors()).actions.detach()
    with pytest.raises(ValueError, match='finite normalized actions'):
        teacher.predict(policy, sensors(), predict=lambda policy, item, *, modules: value)
    assert torch.equal(prediction(policy, sensors()).actions, expected)


def test_references_finish_before_checkpointed_student_backward_and_do_not_leak(monkeypatch):
    # A real checkpoint recomputation must keep the student route and leave all
    # teacher tensors unchanged after an actual optimizer update.
    from torch.utils.checkpoint import checkpoint
    from egrs.retention041.reference import Old10Teacher, original_reference_prediction
    policy, state, identity = installed_policy(monkeypatch)
    teacher = Old10Teacher(policy, state, identity)
    plain = original_reference_prediction(policy, sensors())
    old10 = teacher.predict(policy, sensors())
    frozen = {name: value.clone() for name, value in teacher.context.state_dict().items()}
    optimizer = torch.optim.SGD([p for p in policy.model.parameters() if p.requires_grad], lr=.01)
    student = checkpoint(lambda x: prediction(policy, sensors()).actions * x,
                         torch.ones(()), use_reentrant=False)
    (student - old10 + .2 * plain).square().mean().backward()
    assert policy.model.task_control.W_out.weight.grad.abs().sum() > 0
    assert any(parameter.grad is not None and parameter.grad.abs().sum() > 0
               for name, parameter in policy.model.named_parameters() if name.endswith('.lora_B'))
    assert all(parameter.grad is None for parameter in teacher.parameters())
    assert all(parameter.grad is None for parameter in policy.model.parameters() if not parameter.requires_grad)
    optimizer.step()
    assert torch.equal(old10, teacher.predict(policy, sensors()))
    for name, value in teacher.context.state_dict().items():
        assert torch.equal(value, frozen[name])


def test_invalid_source_is_rejected_without_partial_installation(monkeypatch):
    # Even an already-verified payload is checked at the installation boundary;
    # one missing tensor must not mutate the live module tree or RNG.
    from egrs.retention041.reference import Old10Teacher
    policy, state, identity = installed_policy(monkeypatch)
    original = list(policy.model.named_modules())
    del state['task_control.count_head.bias']
    before_rng = rng_state()
    with pytest.raises(ValueError, match='inventory'):
        Old10Teacher(policy, state, identity)
    assert list(policy.model.named_modules()) == original
    assert_same_rng(before_rng, rng_state())


def test_reference_rng_helper_is_exception_safe():
    from egrs.retention041.reference import preserve_rng
    before = rng_state()
    with pytest.raises(RuntimeError):
        with preserve_rng():
            random.random(); np.random.random(); torch.rand(2)
            raise RuntimeError('failed')
    assert_same_rng(before, rng_state())


@pytest.mark.parametrize('cls_name,limit', [('Old10Budget', 4000), ('NoOld10Budget', 0)])
def test_explicit_old10_budgets_are_durable_train_only(tmp_path, cls_name, limit):
    from egrs.retention041 import reference
    cls = getattr(reference, cls_name)
    path = tmp_path / 'old10.json'
    budget = cls(path)
    before = budget.state_dict()
    if limit:
        budget.consume('train', limit)
        resumed = cls(path)
        resumed.load_state_dict(before)
        assert resumed.report()['train'] == limit
    with pytest.raises(ValueError, match='budget exhausted'):
        budget.consume('train')
    with pytest.raises(ValueError, match='budget exhausted'):
        budget.consume('dev')
