# coding=utf-8
# Copyright 2022 EleutherAI and the HuggingFace Inc. team. All rights reserved.
#
# This code is based on EleutherAI's GPT-NeoX library and the HuggingFace
# GPT-Neo and OPT implementations in this library. It has been modified from
# its original forms to accommodate minor architectural differences compared
# to GPT-NeoX and OPT used by the Meta AI team that trained the model.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Per-instance audited OFT SDPA; no package edits or mutable sample routing.

The adapted attention mathematics follows LlamaSdpaAttention in the audited
Transformers4.40.1 OFT file. The upstream last-row expansion is deliberately
absent: each decoder/checkpoint receives this observation's complete mask.
"""
from copy import deepcopy
import hashlib
from importlib import metadata
import inspect
from pathlib import Path
import sys
from types import MethodType

import torch

from .contract import (AUDITED_SOURCE_SHA256, TORCH_VERSION,
                       TRANSFORMERS_VERSION, contract_for)


def _class_path(value):
    return f'{type(value).__module__}.{type(value).__name__}'


def _inspect_runtime(policy):
    """Inspect the already-loaded instance and installed source, without a forward."""
    try:
        model = policy.model.language_model
        decoder = model.model
        attentions = [layer.self_attn for layer in decoder.layers]
        if not attentions:
            raise AttributeError('no decoder layers')
    except (AttributeError, TypeError) as exc:
        raise ValueError('Task042 requires the audited language/decoder/attention structure') from exc
    canonical = 'transformers.models.llama.modeling_llama'
    if (_class_path(model) != canonical + '.LlamaForCausalLM'
            or _class_path(decoder) != canonical + '.LlamaModel'
            or any(_class_path(layer.self_attn) != canonical + '.LlamaSdpaAttention'
                   for layer in decoder.layers)):
        raise ValueError('Task042 requires audited LlamaForCausalLM/LlamaModel/LlamaSdpaAttention classes')
    module = sys.modules.get(canonical)
    if (module is None or type(model) is not getattr(module, 'LlamaForCausalLM', None)
            or type(decoder) is not getattr(module, 'LlamaModel', None)
            or any(type(layer.self_attn) is not getattr(module, 'LlamaSdpaAttention', None)
                   for layer in decoder.layers)):
        raise ValueError('Task042 attention class ownership differs from the audited module')
    try:
        transformer_version = metadata.version('transformers')
        source_file = inspect.getsourcefile(type(decoder))
        source_sha = hashlib.sha256(Path(source_file).read_bytes()).hexdigest()
    except (metadata.PackageNotFoundError, OSError, TypeError) as exc:
        raise ValueError('Task042 cannot verify the installed Transformers source/version') from exc
    if transformer_version != TRANSFORMERS_VERSION or str(torch.__version__) != TORCH_VERSION:
        raise ValueError('Task042 requires audited Transformers4.40.1 and Torch2.4.1+cu121 versions')
    if source_sha != AUDITED_SOURCE_SHA256:
        raise ValueError('Task042 installed Llama source SHA differs from the audited OFT source')
    apply_rotary = getattr(module, 'apply_rotary_pos_emb', None)
    repeat = getattr(module, 'repeat_kv', None)
    if not callable(apply_rotary) or not callable(repeat):
        raise ValueError('Task042 audited RoPE/GQA helpers are unavailable')
    runtime = {
        'transformers_version': transformer_version,
        'torch_version': str(torch.__version__),
        'language_model_class': _class_path(model),
        'decoder_class': _class_path(decoder),
        'attention_class': _class_path(decoder.layers[0].self_attn),
        'attention_layer_count': len(decoder.layers),
        'source_sha256': source_sha,
        'dtype': str(next(model.parameters()).dtype),
        'backend': 'torch.nn.functional.scaled_dot_product_attention',
    }
    return runtime, apply_rotary, repeat


def _check_flags(config, values):
    for name in ('use_cache', 'output_attentions'):
        value = values.get(name)
        value = getattr(config, name, False) if value is None else value
        if type(value) is not bool or value:
            raise ValueError(f'Task042 requires {name}=False; cache/eager fallback is unsupported')
    if values.get('past_key_values') is not None or values.get('past_key_value') is not None:
        raise ValueError('Task042 prohibits past key/value caches')


def _guard_language_input(module, args, kwargs):
    if args:
        raise ValueError('Task042 language model requires explicit keyword inputs')
    _check_flags(module.config, kwargs)


def _validate_final_mask(mask, hidden):
    batch, length, _ = hidden.shape
    if (not isinstance(mask, torch.Tensor) or mask.shape != (batch, 1, length, length)
            or not torch.is_floating_point(mask) or mask.device != hidden.device
            or mask.dtype != hidden.dtype or mask.requires_grad):
        raise ValueError('Task042 requires an explicit same-dtype Bx1xSxS additive mask')
    if not bool(((mask == 0) | torch.isneginf(mask)).all()):
        raise ValueError('Task042 mask entries must be zero or negative infinity')
    if not bool((mask == 0).any(dim=-1).all()):
        raise ValueError('Task042 mask contains a query with no legal key')
    return mask


def _update_causal_mask(self, attention_mask, input_tensor, cache_position, past_seen_tokens):
    """Explicit research masks pass through; original references get native padding."""
    if past_seen_tokens != 0:
        raise ValueError('Task042 does not support cached prefix tokens')
    batch, length, _ = input_tensor.shape
    if batch < 1 or length < 1 or not torch.is_floating_point(input_tensor):
        raise ValueError('Task042 needs nonempty floating language embeddings')
    if isinstance(attention_mask, torch.Tensor) and attention_mask.ndim == 4:
        return _validate_final_mask(attention_mask, input_tensor)
    if attention_mask is None:
        valid = torch.ones((batch, length), dtype=torch.bool, device=input_tensor.device)
    else:
        if (not isinstance(attention_mask, torch.Tensor) or attention_mask.shape != (batch, length)
                or attention_mask.device != input_tensor.device
                or not bool(((attention_mask == 0) | (attention_mask == 1)).all())):
            raise ValueError('Task042 native padding mask must be a BxS zero/one tensor')
        valid = attention_mask.bool()
    if not bool(valid.any(dim=-1).all()):
        raise ValueError('Task042 native mask has no valid key')
    # Both F0 and F1 use a materialized dense tensor; never select a None shortcut.
    mask = input_tensor.new_zeros((batch, 1, length, length))
    return mask.masked_fill(~valid[:, None, None, :], float('-inf'))


def _attention_forward(apply_rotary_pos_emb, repeat_kv):
    # Mathematical sequence adapted from audited Transformers LlamaSdpaAttention.
    # Copyright 2022 EleutherAI and Hugging Face; Apache License 2.0.
    # https://www.apache.org/licenses/LICENSE-2.0
    def forward(self, hidden_states, attention_mask=None, position_ids=None,
                past_key_value=None, output_attentions=False, use_cache=False,
                cache_position=None):
        if output_attentions or use_cache or past_key_value is not None or getattr(self, 'past_key_value', None) is not None:
            raise ValueError('Task042 prohibits cache and output_attentions/eager fallback')
        mask = _validate_final_mask(attention_mask, hidden_states)
        batch, length, _ = hidden_states.size()
        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)
        query_states = query_states.view(batch, length, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(batch, length, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(batch, length, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        cos, sin = self.rotary_emb(value_states, position_ids)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)
        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)
        if query_states.device.type == 'cuda':
            query_states, key_states, value_states = (query_states.contiguous(),
                                                      key_states.contiguous(), value_states.contiguous())
        attn_output = torch.nn.functional.scaled_dot_product_attention(
            query_states, key_states, value_states, attn_mask=mask,
            dropout_p=self.attention_dropout if self.training else 0.0, is_causal=False)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch, length, self.hidden_size)
        return self.o_proj(attn_output), None, None
    return forward


class _AttentionController:
    def __init__(self, policy, contract, runtime):
        self._policy = policy
        self._contract = deepcopy(contract)
        self._runtime = deepcopy(runtime)
        self._experiment_arm = contract['experiment_arm']

    @property
    def contract(self):
        return deepcopy(self._contract)

    @property
    def runtime(self):
        return deepcopy(self._runtime)

    def forward(self, model, *, instruction_mask, **model_kwargs):
        from .layout import prepare_layout, build_layout, final_attention_mask, validate_output
        if model is not self._policy.model:
            raise ValueError('Task042 controller belongs to a different policy instance')
        _check_flags(model.language_model.config, model_kwargs)
        prepared = prepare_layout(model, model_kwargs.get('input_ids'),
                                  model_kwargs.get('labels'), instruction_mask)
        projector = model_kwargs.get('proprio_projector')
        if projector is None or projector is not self._policy.proprio_projector:
            raise ValueError('Task042 requires the original policy proprio projector')
        projected, layouts = [], []

        def capture_proprio(module, args, output):
            if projected:
                raise ValueError('Task042 observed more than one proprio projection')
            projected.append(output)

        def route_language(module, args, kwargs):
            if args or layouts or len(projected) != 1:
                raise ValueError('Task042 requires one language call after one proprio projection')
            layout = build_layout(prepared, kwargs.get('inputs_embeds'),
                                  kwargs.get('attention_mask'), projected[0])
            layouts.append(layout)
            routed = dict(kwargs)
            routed['attention_mask'] = final_attention_mask(
                layout, self._experiment_arm, kwargs['inputs_embeds'].dtype)
            return args, routed

        proprio_hook = projector.register_forward_hook(capture_proprio)
        language_hook = model.language_model.register_forward_pre_hook(route_language, with_kwargs=True)
        try:
            output = model(**model_kwargs)
            if len(layouts) != 1 or len(projected) != 1:
                raise ValueError('Task042 did not observe the original single fused forward')
            validate_output(layouts[0], output)
            return output
        finally:
            language_hook.remove()
            proprio_hook.remove()


def install_attention(policy, experiment_arm):
    contract = contract_for(experiment_arm)
    if hasattr(policy, '_tcif042'):
        raise ValueError('Task042 attention is already installed on this policy')
    runtime, rotary, repeat = _inspect_runtime(policy)
    language = policy.model.language_model
    decoder = language.model
    if not decoder.layers or decoder.config._attn_implementation != 'sdpa':
        raise ValueError('Task042 requires the audited SDPA decoder backend')
    for layer in decoder.layers:
        attn = layer.self_attn
        if (not all(callable(getattr(attn, name, None)) for name in
                    ('q_proj', 'k_proj', 'v_proj', 'o_proj', 'rotary_emb'))
                or attn.num_heads != attn.num_key_value_heads * attn.num_key_value_groups
                or attn.hidden_size != attn.num_heads * attn.head_dim
                or getattr(attn, 'past_key_value', None) is not None):
            raise ValueError('Task042 attention projections/head layout/cache differ from the audited contract')
    controller = _AttentionController(policy, contract, runtime)
    adapted = _attention_forward(rotary, repeat)
    for layer in decoder.layers:
        layer.self_attn.forward = MethodType(adapted, layer.self_attn)
    decoder._update_causal_mask = MethodType(_update_causal_mask, decoder)
    # This permanent guard carries no observation state and also protects references.
    controller._guard_handle = language.register_forward_pre_hook(_guard_language_input, with_kwargs=True)
    policy._tcif042 = controller
    return controller
