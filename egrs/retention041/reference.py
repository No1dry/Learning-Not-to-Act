"""Independent039 learned references on one frozen original SOG10 backbone.

Install only before constructing student graphs. Reference calls are likewise a
precomputation phase: no student parameter or live module is ever overwritten
with teacher weights. The training loop owns forward ordering and durable
budget allocation before calling either prediction helper.
"""
from contextlib import contextmanager
from copy import deepcopy
import random

import numpy as np
import torch
from torch import nn

from egrs.augmentation.oft import LoRALinear
from egrs.task_control.model import TaskControlModules
from egrs.task_control.reference import ObservationBudget, policy_modules, reference_prediction


@contextmanager
def preserve_rng():
    """Isolate Python, NumPy and torch streams without initializing CUDA."""
    python_state = random.getstate()
    numpy_state = np.random.get_state()
    cpu_state = torch.get_rng_state()
    cuda_states = torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None
    try:
        yield
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)
        torch.set_rng_state(cpu_state)
        if cuda_states is not None:
            torch.cuda.set_rng_state_all(cuda_states)


class _TeacherLoRALinear(LoRALinear):
    """Keep student Parameters in place, routing only the independent delta."""

    def __init__(self, student, teacher_a, teacher_b):
        nn.Module.__init__(self)
        self.base_layer = student.base_layer
        self.rank, self.alpha = student.rank, student.alpha
        self.enabled = student.enabled
        self.training = student.training
        self.lora_A, self.lora_B = student.lora_A, student.lora_B
        self.register_buffer('_old10_a', teacher_a.detach().to(
            device=self.lora_A.device, dtype=self.lora_A.dtype).clone(), persistent=False)
        self.register_buffer('_old10_b', teacher_b.detach().to(
            device=self.lora_B.device, dtype=self.lora_B.dtype).clone(), persistent=False)
        self.old10_enabled = False
        # Any existing hook belongs to the same layer after installation. Keep
        # its actual table object so pre-existing RemovableHandles stay valid.
        for name in ('_forward_hooks', '_forward_pre_hooks', '_backward_hooks',
                     '_backward_pre_hooks', '_forward_hooks_with_kwargs',
                     '_forward_hooks_always_called', '_forward_pre_hooks_with_kwargs'):
            if hasattr(student, name):
                setattr(self, name, getattr(student, name))
        self._is_full_backward_hook = student._is_full_backward_hook

    def forward(self, value):
        if not self.enabled or not self.old10_enabled:
            return super().forward(value)
        delta = torch.nn.functional.linear(
            torch.nn.functional.linear(value.float(), self._old10_a), self._old10_b)
        return self.base_layer(value) + delta.to(value.dtype) * (self.alpha / self.rank)


@contextmanager
def _reference_environment(policy, context=None):
    """Restore exact mixed modes and execution switches, including failures."""
    roots = policy_modules(policy) + ([] if context is None else list(context.modules()))
    modules = list({id(module): module for module in roots}.values())
    modes = [(module, module.training) for module in modules]
    parameters = {id(value): value for module in modules for value in module.parameters(recurse=False)}
    gradients = [(value, value.requires_grad) for value in parameters.values()]
    checkpoints = [(module, module.gradient_checkpointing) for module in modules
                   if isinstance(getattr(module, 'gradient_checkpointing', None), bool)]
    configs = {id(module.config): module.config for module in modules
               if getattr(module, 'config', None) is not None and hasattr(module.config, 'use_cache')}
    caches = [(config, config.use_cache) for config in configs.values()]
    switches = [(module, attribute, getattr(module, attribute)) for module in modules
                for attribute in ('enabled', 'old10_enabled')
                if hasattr(module, attribute)]
    hook_tables = []
    for module in modules:
        for name in ('_forward_hooks', '_forward_pre_hooks', '_backward_hooks', '_backward_pre_hooks'):
            table = getattr(module, name, None)
            if table is None:
                continue
            tagged = {key for key, hook in table.items() if getattr(hook, '_task_control_hook', False)}
            hook_tables.append((table, table.copy(), tagged))
            # PyTorch stores options separately from the actual hook table.
            for metadata in ({'_forward_hooks': ('_forward_hooks_with_kwargs', '_forward_hooks_always_called'),
                              '_forward_pre_hooks': ('_forward_pre_hooks_with_kwargs',)}.get(name, ())):
                options = getattr(module, metadata, None)
                if options is not None:
                    hook_tables.append((options, options.copy(), tagged))
    with preserve_rng():
        try:
            for module, _ in modes:
                module.training = False
            for value, _ in gradients:
                value.requires_grad_(False)
            for module, _ in checkpoints:
                module.gradient_checkpointing = False
            for config, _ in caches:
                config.use_cache = False
            for table, _, tagged in hook_tables:
                for key in tagged:
                    table.pop(key, None)
            with torch.no_grad():
                yield
        finally:
            for table, saved, _ in reversed(hook_tables):
                table.clear()
                table.update(saved)
            for module, attribute, value in switches:
                setattr(module, attribute, value)
            for config, value in caches:
                config.use_cache = value
            for module, value in checkpoints:
                module.gradient_checkpointing = value
            for value, enabled in gradients:
                value.requires_grad_(enabled)
            for module, training in modes:
                module.training = training


def original_reference_prediction(policy, item, predict=None):
    """Original ordinary SOG10 target with all training state/RNG isolated."""
    with _reference_environment(policy):
        return reference_prediction(policy, item, predict=predict)


class Old10Teacher(nn.Module):
    """A complete frozen039 branch; only original frozen base weights are shared.

    ``verified_state`` must first pass the strict source reader's complete
    identity/hash/lineage checks. This boundary additionally validates every
    tensor's inventory/shape/dtype/finiteness before installing any wrapper.
    ``predict`` seams accept ``modules=`` and may return Prediction or Tensor.
    """

    def __init__(self, policy, verified_state, identity):
        super().__init__()
        student = getattr(policy.model, 'task_control', None)
        if not isinstance(student, TaskControlModules):
            raise ValueError('Old10 teacher requires an installed complete task_control student')
        actual = {name: value for name, value in policy.model.named_parameters()
                  if name.startswith('task_control.') or name.endswith(('.lora_A', '.lora_B'))}
        targets = sorted(name.rsplit('.', 1)[0] for name in actual if name.endswith('.lora_A'))
        if (not isinstance(identity, dict) or identity.get('hidden_dim') != student.hidden_dim
                or identity.get('target_modules') != targets or not targets):
            raise ValueError('Old10 teacher identity dimension or target inventory mismatch')
        if not isinstance(verified_state, dict) or set(verified_state) != set(actual):
            raise ValueError('Old10 teacher tensor inventory mismatch')
        for name, value in verified_state.items():
            if (not isinstance(value, torch.Tensor) or value.shape != actual[name].shape
                    or value.dtype != actual[name].dtype or not torch.is_floating_point(value)
                    or not torch.isfinite(value).all()):
                raise ValueError('Old10 teacher tensor shape, dtype or finiteness mismatch: ' + name)
        layers = [(name, policy.model.get_submodule(name)) for name in targets]
        if any(not isinstance(layer, LoRALinear) or isinstance(layer, _TeacherLoRALinear)
               for _, layer in layers):
            raise ValueError('Old10 teacher requires each native student LoRA exactly once')
        # Finish allocations/loading before mutating the live student tree.
        with preserve_rng():
            context = TaskControlModules(student.hidden_dim).to(
                device=next(student.parameters()).device, dtype=next(student.parameters()).dtype)
            context.load_state_dict({name[len('task_control.'):]: value
                                     for name, value in verified_state.items()
                                     if name.startswith('task_control.')}, strict=True)
            context.requires_grad_(False)
            context.eval()
            replacements = [(name, _TeacherLoRALinear(layer,
                verified_state[name + '.lora_A'], verified_state[name + '.lora_B']))
                for name, layer in layers]
        self.context = context
        self.eval()
        self.identity = deepcopy(identity)
        self._model_id = id(policy.model)
        # A plain tuple deliberately does not register shared student Parameters
        # in teacher.parameters()/state_dict(), or in the optimizer inventory.
        self._layers = tuple(layer for _, layer in replacements)
        for name, layer in replacements:
            parent, child = name.rsplit('.', 1)
            setattr(policy.model.get_submodule(parent), child, layer)

    def predict(self, policy, item, predict=None):
        if id(policy.model) != self._model_id:
            raise ValueError('Old10 teacher is bound to a different shared backbone')
        if predict is None:
            from egrs.task_control.oft import prediction
            predict = prediction
        with _reference_environment(policy, self.context):
            for layer in self._layers:
                layer.enabled = True
                layer.old10_enabled = True
            self.context.enabled = True
            output = predict(policy, item, modules=self.context)
            output = output.actions if hasattr(output, 'actions') else output
            if (not isinstance(output, torch.Tensor) or tuple(output.shape) != (1, 8, 7)
                    or not torch.is_floating_point(output) or not torch.isfinite(output).all()):
                raise ValueError('Old10 reference must produce finite normalized actions with shape 1x8x7')
            return output.detach().clone()


class Old10Budget(ObservationBudget):
    LIMITS = {'train': 4000, 'dev': 0}
    NAME = 'old10 reference'


class NoOld10Budget(ObservationBudget):
    LIMITS = {'train': 0, 'dev': 0}
    NAME = 'disabled old10 reference'
