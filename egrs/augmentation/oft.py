"""Pinned OFT integration and a new, language-only native LoRA adapter.

The published SOG10 checkpoint is already merged. Its original processor,
statistics, action head and proprio projector come from the accepted core loader.
No published adapter is reapplied. This module never downloads a checkpoint.
"""
import json
from pathlib import Path

import torch
from torch import nn

from .adapter_identity import (OFT_REVISION, BASE_SOURCE, LINEAGE_KEYS, TARGET,
                               sha256, _lineage, read_adapter_identity, validate_recipe_identity,
                               validate_retention_recipe_identity,validate_retention_lineage)

def language_targets(model):
    targets = sorted(name for name, module in model.named_modules()
                     if TARGET.fullmatch(name) and isinstance(module, nn.Linear))
    layers = {name.rsplit('.', 1)[0] for name in targets}
    if not targets or any(sum(n.startswith(layer + '.') for n in targets) != 4 for layer in layers):
        raise ValueError('Expected complete language transformer q/k/v/o linear target paths')
    expected_layers = len(model.language_model.model.layers)
    if len(layers) != expected_layers:
        raise ValueError('Language target inventory omits transformer layers')
    return targets


class LoRALinear(nn.Module):
    """W(x) + (alpha / rank) B(A(x)); Gaussian A, zero B, no dropout."""
    def __init__(self, base, rank=16, alpha=32):
        super().__init__()
        self.base_layer = base
        self.rank, self.alpha = rank, alpha
        self.enabled = True
        self.lora_A = nn.Parameter(torch.empty(rank, base.in_features, device=base.weight.device,
                                                dtype=torch.float32))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, rank, device=base.weight.device,
                                                dtype=torch.float32))
        nn.init.normal_(self.lora_A, std=1 / rank)
        self.base_layer.requires_grad_(False)

    @property
    def weight(self):
        return self.base_layer.weight

    @property
    def bias(self):
        return self.base_layer.bias

    def forward(self, value):
        if not self.enabled:return self.base_layer(value)
        delta = torch.nn.functional.linear(torch.nn.functional.linear(value.float(), self.lora_A), self.lora_B)
        return self.base_layer(value) + delta.to(value.dtype) * (self.alpha / self.rank)


def inject_language_lora(policy, target_modules=None):
    model = policy.model
    actual = language_targets(model)
    if target_modules is not None and list(target_modules) != actual:
        raise ValueError('Adapter target inventory differs from original language model')
    for module in (model, policy.action_head, policy.proprio_projector):
        module.requires_grad_(False)
    for name in actual:
        parent_name, child = name.rsplit('.', 1)
        parent = model.get_submodule(parent_name)
        setattr(parent, child, LoRALinear(getattr(parent, child)))
    return actual


def adapter_state(model):
    return {name: value.detach().cpu() for name, value in model.named_parameters()
            if name.endswith(('.lora_A', '.lora_B'))}


def save_adapter(policy, directory, group, metadata=None):
    if group not in {'raw_control', 'progress_aug', 'robot_rewind_mix', 'policy_retention_distillation'}:
        raise ValueError('Adapter group must be raw_control or progress_aug')
    if group == 'robot_rewind_mix':
        if not isinstance(metadata, dict) or set(metadata) != {
            'recipe', 'data_kind', 'update', 'final_update', 'export_identity'}:
            raise ValueError('task035 adapter requires exact recipe metadata fields')
        recipe_identity = dict(metadata or {}, schema_version='task035-oft-adapter-v1', group=group)
        validate_recipe_identity(recipe_identity)
    elif group == 'policy_retention_distillation':
        fields={'recipe','data_kind','update','final_update','export_identity','reference_view',
                'reference_base','training_recipe','reference_calls'}
        if not isinstance(metadata,dict) or set(metadata)!=fields:
            raise ValueError('task036 adapter requires exact recipe/reference metadata fields')
        recipe_identity=dict(metadata,schema_version='task036-oft-adapter-v1',group=group)
        validate_retention_recipe_identity(recipe_identity)
        validate_retention_lineage(_lineage(policy))
    elif metadata is not None:
        raise ValueError('task030 adapter identity does not accept recipe metadata')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    state = adapter_state(policy.model)
    if not state:
        raise ValueError('No new adapter parameters to save')
    path = directory / 'adapter.pt'
    torch.save(state, path)
    identity = {'schema_version': 'task030-oft-adapter-v1', 'group': group, 'base_lineage': _lineage(policy),
        'implementation': 'native-linear-lora', 'rank': 16, 'alpha': 32, 'dropout': 0,
        'target_modules': sorted(n.rsplit('.', 1)[0] for n in state if n.endswith('.lora_A')),
        'trainable_parameters': {n: list(v.shape) for n, v in sorted(state.items())},
        'adapter_sha256': sha256(path)}
    if group in {'robot_rewind_mix','policy_retention_distillation'}:
        identity.update(recipe_identity)
    (directory / 'identity.json').write_text(json.dumps(identity, sort_keys=True, indent=2), encoding='utf-8')
    return identity


def restore_adapter_weights(model, directory, identity=None):
    identity = identity or read_adapter_identity(directory)
    state = torch.load(Path(directory) / 'adapter.pt', map_location='cpu', weights_only=True)
    params = dict(model.named_parameters())
    if set(state) != set(identity['trainable_parameters']):
        raise ValueError('Adapter tensor inventory mismatch')
    with torch.no_grad():
        for name, value in state.items():
            if list(value.shape) != identity['trainable_parameters'][name] or name not in params or params[name].shape != value.shape:
                raise ValueError('Adapter tensor shape mismatch')
            params[name].copy_(value)
    for module in model.modules():
        if isinstance(module,LoRALinear):module.enabled=True


def attach_trained_adapter(policy, directory):
    identity = read_adapter_identity(directory)
    if identity['base_lineage'] != _lineage(policy):
        raise ValueError('Adapter base lineage differs from loaded original OFT')
    inject_language_lora(policy, identity['target_modules'])
    restore_adapter_weights(policy.model, directory, identity)
    policy.model.requires_grad_(False)
    policy.model.eval()
    return identity


def load_trained_adapter(policy, directory):
    """Attach to an already loaded accepted plain OFT policy; return identity."""
    return attach_trained_adapter(policy, directory)


def training_prediction(policy, item, images=None):
    """Differentiable equivalent of pinned L1 inference, before unnormalization.

    Uses official input/label helpers and the official shifted hidden-state
    selection. Placeholder action tokens are zeroed by the official forward;
    padding target actions never enter the model and affect only the loss mask.
    """
    from experiments.robot.openvla_utils import prepare_images_for_vla, resize_image_for_policy
    model = policy.model
    device = next(model.parameters()).device
    # prepare_observation always performs the original JPEG/Lanczos resize,
    # including224x224 input. prepare_images_for_vla alone would skip that case.
    # Dataset mapping already resolves camera orientation exactly once.
    images = [resize_image_for_policy(image, policy.resize_size)
              for image in (item['images'] if images is None else images)]
    images = prepare_images_for_vla(images, policy.cfg)
    prompt = f"In: What action should the robot take to {item['instruction'].lower()}?\nOut:"
    inputs = policy.processor(prompt, images[0]).to(device, dtype=torch.bfloat16)
    wrist = policy.processor(prompt, images[1]).to(device, dtype=torch.bfloat16)
    pixel_values = torch.cat([inputs['pixel_values'], wrist['pixel_values']], dim=1)
    ids, attention = inputs['input_ids'], inputs['attention_mask']
    if not torch.all(ids[:, -1] == 29871):
        ids = torch.cat([ids, ids.new_full((1, 1), 29871)], dim=1)
        attention = torch.cat([attention, attention.new_ones((1, 1))], dim=1)
    labels = torch.full_like(ids, -100)
    ids, attention = model._prepare_input_for_action_prediction(ids, attention)
    labels = model._prepare_labels_for_action_prediction(labels, ids)
    proprio = torch.as_tensor(item['proprio'], device=device, dtype=torch.bfloat16).reshape(1, 8)
    output = model(input_ids=ids, attention_mask=attention, pixel_values=pixel_values,
        labels=labels, proprio=proprio, proprio_projector=policy.proprio_projector,
        use_film=False, output_hidden_states=True, return_dict=True, use_cache=False)
    patches = model.vision_backbone.get_num_patches() * model.vision_backbone.get_num_images_in_input() + 1
    mask = model._process_action_masks(labels[:, 1:])
    hidden = output.hidden_states[-1][:, patches:-1][mask].reshape(1, 56, -1)
    return policy.action_head.predict_action(hidden)
