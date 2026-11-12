"""Tiny CPU SDPA/autograd tests; no Transformers import or real model loading."""
from copy import deepcopy
import hashlib
import importlib
import json
import sys
from types import SimpleNamespace, ModuleType

import pytest
import torch
from torch import nn
from torch.utils.checkpoint import checkpoint


def implementation():
    try:
        return importlib.import_module('egrs.tcif042.attention')
    except ModuleNotFoundError as exc:
        pytest.fail(f'Task042 attention implementation is missing: {exc}')


def rotate_half(x):
    left, right = x.chunk(2, dim=-1)
    return torch.cat((-right, left), dim=-1)


def apply_rope(q, k, cos, sin):
    return (q * cos.unsqueeze(1) + rotate_half(q) * sin.unsqueeze(1),
            k * cos.unsqueeze(1) + rotate_half(k) * sin.unsqueeze(1))


def repeat_kv(x, groups):
    return x.repeat_interleave(groups, dim=1)


class Rotary(nn.Module):
    def forward(self, value, positions):
        phase = positions.to(value.dtype).unsqueeze(-1).expand(-1, -1, 2) / 7
        return phase.cos(), phase.sin()


class TinyAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.num_heads, self.num_key_value_heads = 2, 1
        self.head_dim, self.hidden_size = 2, 4
        self.num_key_value_groups, self.layer_idx = 2, 0
        self.attention_dropout = 0.0
        self.q_proj, self.k_proj = nn.Linear(4, 4), nn.Linear(4, 2)
        self.v_proj, self.o_proj = nn.Linear(4, 2), nn.Linear(4, 4)
        self.rotary_emb = Rotary()

    def forward(self, *args, **kwargs):
        raise AssertionError('The original fake attention must be adapted')


class TinyLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.self_attn = TinyAttention()

    def forward(self, hidden, attention_mask, position_ids, past_key_value=None,
                output_attentions=False, use_cache=False, cache_position=None):
        value = self.self_attn(hidden, attention_mask, position_ids,
                               past_key_value, output_attentions, use_cache, cache_position)[0]
        return (hidden + value,)


class TinyDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.ModuleList([TinyLayer(), TinyLayer(), TinyLayer()])
        self.gradient_checkpointing = True
        self.config = SimpleNamespace(_attn_implementation='sdpa', use_cache=False,
                                      output_attentions=False)

    def _update_causal_mask(self, *args):
        raise AssertionError('The upstream causal conversion must be bypassed')

    def forward(self, *, inputs_embeds, attention_mask=None, **kwargs):
        length = inputs_embeds.shape[1]
        positions = torch.arange(length).unsqueeze(0)
        mask = self._update_causal_mask(attention_mask, inputs_embeds, positions[0], 0)
        value = inputs_embeds
        for layer in self.layers:
            if self.gradient_checkpointing and self.training:
                value = checkpoint(layer, value, mask, positions, None, False, False,
                                   positions[0], use_reentrant=True)[0]
            else:
                value = layer(value, mask, positions)[0]
        return SimpleNamespace(hidden_states=(value,))


class TinyLanguageModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = TinyDecoder()
        self.config = self.model.config

    def forward(self, **kwargs):
        return self.model(**kwargs)


def tiny_policy(monkeypatch, arm='f0'):
    policy = make_policy(monkeypatch)
    controller = implementation().install_attention(policy, arm)
    return policy, controller


class TinyVision(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Linear(1, 4)
        self.calls = 0

    def get_num_patches(self):
        return 1

    def get_num_images_in_input(self):
        return 2

    def forward(self, images):
        self.calls += 1
        return self.features(images.float().reshape(images.shape[0], 2, -1).mean(-1, keepdim=True))


class TinyProprio(nn.Linear):
    def __init__(self):
        super().__init__(8, 4)
        self.calls = 0

    def forward(self, value):
        self.calls += 1
        return super().forward(value.to(self.weight.dtype))


class TinyFusion(nn.Module):
    def __init__(self):
        super().__init__()
        self.llm_dim = 4
        self.embed_tokens = nn.Embedding(33010, 4)
        self.vision_backbone, self.projector = TinyVision(), nn.Linear(4, 4)
        self.language_model = TinyLanguageModel()
        self.calls = 0

    def get_input_embeddings(self):
        return self.embed_tokens

    def _prepare_input_for_action_prediction(self, ids, attention):
        return (torch.cat((ids, ids.new_full((1, 56), 32001), ids.new_full((1, 1), 2)), 1),
                torch.cat((attention, attention.new_ones((1, 57))), 1))

    def _prepare_labels_for_action_prediction(self, labels, ids):
        return torch.cat((labels, labels.new_full((1, 56), 32001), labels.new_full((1, 1), 2)), 1)

    def _process_action_masks(self, labels):
        return labels == 32001

    def forward(self, *, input_ids, attention_mask, pixel_values, labels, proprio,
                proprio_projector, use_cache=False, **kwargs):
        self.calls += 1
        inputs = self.embed_tokens(input_ids)
        inputs = inputs * ~self._process_action_masks(labels).unsqueeze(-1)
        visual = self.projector(self.vision_backbone(pixel_values))
        projected = torch.cat((visual, proprio_projector(proprio).unsqueeze(1)), dim=1)
        fused = torch.cat((inputs[:, :1], projected, inputs[:, 1:]), dim=1)
        padding = torch.cat((attention_mask[:, :1], attention_mask.new_ones((1, 3)),
                             attention_mask[:, 1:]), dim=1)
        output = self.language_model(inputs_embeds=fused, attention_mask=padding, use_cache=use_cache)
        return SimpleNamespace(hidden_states=output.hidden_states, projector_features=projected)


class TinyHead(nn.Linear):
    def __init__(self):
        super().__init__(4, 1)

    def predict_action(self, value):
        return self(value).reshape(1, 8, 7)


def make_policy(monkeypatch, *, install=False, arm='f0'):
    """Reusable original-shaped CPU policy; caller supplies processor/metadata."""
    module = implementation()
    torch.manual_seed(9)
    policy = SimpleNamespace(model=TinyFusion(), action_head=TinyHead(),
                             proprio_projector=TinyProprio())
    monkeypatch.setattr(module, '_inspect_runtime', lambda policy: (
        {'transformers_version': '4.40.1', 'torch_version': '2.4.1+cu121',
         'attention_class': 'tiny.LlamaSdpaAttention', 'dtype': 'torch.float32',
         'source_sha256': '3aac24cec583a6ef5f60b6ec634a8bd3c8377784c5c63c8cc14cb6790554c52e'},
        apply_rope, repeat_kv))
    if install:
        module.install_attention(policy, arm)
    return policy


def native_formula(attention, hidden, padding):
    batch, length, _ = hidden.shape
    q = attention.q_proj(hidden).view(batch, length, 2, 2).transpose(1, 2)
    k = attention.k_proj(hidden).view(batch, length, 1, 2).transpose(1, 2)
    v = attention.v_proj(hidden).view(batch, length, 1, 2).transpose(1, 2)
    positions = torch.arange(length).unsqueeze(0)
    cos, sin = attention.rotary_emb(v, positions)
    q, k = apply_rope(q, k, cos, sin)
    k, v = repeat_kv(k, 2), repeat_kv(v, 2)
    # Independent native causal construction followed by the audited last-row copy.
    old = torch.full((batch, 1, length, length), float('-inf')).triu(1)
    old = old.masked_fill(~padding[:, None, None, :].bool(), float('-inf'))
    final = old[:, :, -1:, :].expand(-1, -1, length, -1)
    out = torch.nn.functional.scaled_dot_product_attention(q, k, v, attn_mask=final,
                                                          dropout_p=0.0, is_causal=False)
    return attention.o_proj(out.transpose(1, 2).contiguous().view(batch, length, 4))


def test_contract_strict_arm_types_and_no_shared_mutation():
    try:
        module = importlib.import_module('egrs.tcif042.contract')
    except ModuleNotFoundError as exc:
        pytest.fail(f'Task042 execution contract is missing: {exc}')
    f0, f1 = module.contract_for('f0'), module.contract_for('f1')
    assert f0 != f1
    module.validate_contract(f0, 'f0')
    for bad in ({**f0, 'extra': True}, {**f0, 'experiment_arm': 'f1'},
                {**f0, 'use_cache': 0}, None):
        with pytest.raises(ValueError):
            module.validate_contract(bad, 'f0')
    f0['experiment_arm'] = 'changed'
    assert module.contract_for('f0')['experiment_arm'] == 'f0'


def test_f0_matches_audited_native_output_and_gradients_without_new_parameter_paths(monkeypatch):
    policy, controller = tiny_policy(monkeypatch)
    model = policy.model.language_model.model
    attention = model.layers[0].self_attn
    original = deepcopy(attention)
    params = dict(policy.model.named_parameters())
    x = torch.randn(2, 5, 4, requires_grad=True)
    y = x.detach().clone().requires_grad_()
    padding = torch.tensor([[1, 1, 1, 0, 0], [1, 1, 1, 1, 1]])
    mask = model._update_causal_mask(padding, x, torch.arange(5), 0)
    actual = attention(x, mask, torch.arange(5).unsqueeze(0))[0]
    expected = native_formula(original, y, padding)
    torch.testing.assert_close(actual, expected)
    actual.square().sum().backward()
    expected.square().sum().backward()
    torch.testing.assert_close(x.grad, y.grad)
    for name, parameter in attention.named_parameters():
        torch.testing.assert_close(parameter.grad, dict(original.named_parameters())[name].grad)
    assert dict(policy.model.named_parameters()).keys() == params.keys()
    assert all(dict(policy.model.named_parameters())[key] is value for key, value in params.items())
    assert policy._tcif042 is controller


def test_final_sdpa_keeps_query_specific_mask_and_training_dropout(monkeypatch):
    policy, _ = tiny_policy(monkeypatch, 'f1')
    attention = policy.model.language_model.model.layers[0].self_attn
    mask = torch.zeros(1, 1, 4, 4)
    mask[:, :, :2, 2:] = float('-inf')
    observed = []
    primitive = torch.nn.functional.scaled_dot_product_attention

    def capture(*args, **kwargs):
        observed.append((kwargs['attn_mask'].clone(), kwargs['dropout_p'], kwargs['is_causal']))
        return primitive(*args, **kwargs)

    monkeypatch.setattr(torch.nn.functional, 'scaled_dot_product_attention', capture)
    attention.attention_dropout = 0.1
    attention(torch.randn(1, 4, 4), mask, torch.arange(4).unsqueeze(0))
    attention.eval()
    attention(torch.randn(1, 4, 4), mask, torch.arange(4).unsqueeze(0))
    assert observed[0][1:] == (0.1, False)
    assert observed[1][1:] == (0.0, False)
    assert torch.equal(observed[0][0], mask)


def test_checkpoint_pair_masks_survive_another_length_and_native_reference(monkeypatch):
    policy, _ = tiny_policy(monkeypatch, 'f1')
    model = policy.model.language_model
    model.train()
    u, v = torch.randn(1, 4, 4, requires_grad=True), torch.randn(1, 6, 4, requires_grad=True)
    umask, vmask = torch.zeros(1, 1, 4, 4), torch.zeros(1, 1, 6, 6)
    umask[:, :, :2, 2:], vmask[:, :, :3, 3:] = float('-inf'), float('-inf')
    uu = model(inputs_embeds=u, attention_mask=umask, use_cache=False).hidden_states[-1]
    vv = model(inputs_embeds=v, attention_mask=vmask, use_cache=False).hidden_states[-1]
    with torch.no_grad():
        model.eval()
        model(inputs_embeds=torch.randn(1, 5, 4), attention_mask=torch.ones(1, 5), use_cache=False)
        model.train()
    (uu[:, :2].sum() + vv[:, :3].sum()).backward()
    assert torch.count_nonzero(u.grad[:, 2:]) == 0
    assert torch.count_nonzero(v.grad[:, 3:]) == 0
    assert torch.count_nonzero(u.grad[:, :2]) > 0


@pytest.mark.parametrize('kwargs', [{'use_cache': True}, {'past_key_value': object()},
                                  {'output_attentions': True}])
def test_attention_rejects_cache_and_eager_fallback(monkeypatch, kwargs):
    policy, _ = tiny_policy(monkeypatch)
    attention = policy.model.language_model.model.layers[0].self_attn
    with pytest.raises(ValueError):
        attention(torch.zeros(1, 3, 4), torch.zeros(1, 1, 3, 3),
                  torch.arange(3).unsqueeze(0), **kwargs)


def test_install_is_per_instance_and_runtime_rejects_unverified_fake():
    module = implementation()
    policy = SimpleNamespace(model=nn.Module())
    policy.model.language_model = TinyLanguageModel()
    with pytest.raises(ValueError, match='[Cc]lass|[Ss]ource|[Vv]ersion|[Tt]ransformers'):
        module.install_attention(policy, 'f0')


def model_inputs(policy, extra=0, proprio=None):
    prefix = torch.tensor([[1, 5, 6, 7] + [8] * extra])
    ids, padding = policy.model._prepare_input_for_action_prediction(prefix, torch.ones_like(prefix))
    labels = policy.model._prepare_labels_for_action_prediction(torch.full_like(prefix, -100), ids)
    return {'input_ids': ids, 'attention_mask': padding, 'labels': labels,
            'pixel_values': torch.tensor([[[[1.]], [[2.]]]]),
            'proprio': torch.zeros(1, 8) if proprio is None else proprio,
            'proprio_projector': policy.proprio_projector, 'use_cache': False,
            'output_hidden_states': True, 'output_projector_features': True}, torch.tensor([[False, True, True, False] + [False] * extra])


def test_controller_single_original_fusion_noninterference_and_control_access(monkeypatch):
    policy, controller = tiny_policy(monkeypatch, 'f1')
    policy.model.eval()
    kwargs, instruction = model_inputs(policy)
    observed = []
    primitive = torch.nn.functional.scaled_dot_product_attention

    def capture(*args, **kw):
        observed.append(kw['attn_mask'].detach().clone())
        return primitive(*args, **kw)

    monkeypatch.setattr(torch.nn.functional, 'scaled_dot_product_attention', capture)
    before = dict(policy.model.named_parameters())
    first = controller.forward(policy.model, instruction_mask=instruction, **kwargs).hidden_states[-1]
    assert (policy.model.calls, policy.model.vision_backbone.calls, policy.proprio_projector.calls) == (1, 1, 1)
    assert len(observed) == 3
    # Native layout: BOS, V,V,P, raw1,raw2,raw3(first shifted A), 56 slots, stop.
    assert observed[0][0, 0, 1, 3].isneginf()
    assert observed[0][0, 0, 6, 3] == 0
    assert all(torch.equal(observed[0], value) for value in observed)
    kwargs['proprio'] = torch.ones(1, 8)
    second = controller.forward(policy.model, instruction_mask=instruction, **kwargs).hidden_states[-1]
    torch.testing.assert_close(first[:, [0, 1, 2, 4, 5]], second[:, [0, 1, 2, 4, 5]], rtol=0, atol=0)
    assert not torch.allclose(first[:, 6:], second[:, 6:])
    assert not policy.proprio_projector._forward_hooks
    # Only the permanent stateless flag guard survives the scoped student call.
    assert len(policy.model.language_model._forward_pre_hooks) == 1
    assert all(dict(policy.model.named_parameters())[key] is value for key, value in before.items())
    assert not torch.cuda.is_initialized()


def test_controller_variable_pair_checkpoint_then_reference_uses_each_saved_mask(monkeypatch):
    policy, controller = tiny_policy(monkeypatch, 'f1')
    p = torch.randn(1, 8, requires_grad=True)
    q = torch.randn(1, 8, requires_grad=True)
    uk, ui = model_inputs(policy, proprio=p)
    vk, vi = model_inputs(policy, extra=3, proprio=q)
    u = controller.forward(policy.model, instruction_mask=ui, **uk).hidden_states[-1]
    v = controller.forward(policy.model, instruction_mask=vi, **vk).hidden_states[-1]
    with torch.no_grad():
        policy.model.eval()
        native = policy.model(**uk).hidden_states[-1]
        policy.model.train()
    assert not torch.allclose(native[:, 1:3], u[:, 1:3])
    (u[:, 1:3].sum() + v[:, 1:3].sum()).backward()
    assert torch.count_nonzero(p.grad) == 0
    assert torch.count_nonzero(q.grad) == 0
    # A native F0 graph leaks proprio through control in multiple layers.
    policy.model.zero_grad()
    native = policy.model(**uk).hidden_states[-1]
    native[:, 1:3].sum().backward()
    assert torch.count_nonzero(p.grad) > 0


def test_runtime_source_and_version_guards_are_strict_and_json_recorded(monkeypatch, tmp_path):
    module = implementation()
    canonical = 'transformers.models.llama.modeling_llama'
    fake_module = ModuleType(canonical)
    fake_module.__file__ = str(tmp_path / 'synthetic_llama.py')
    for name, base in [('LlamaForCausalLM', TinyLanguageModel), ('LlamaModel', TinyDecoder),
                       ('LlamaSdpaAttention', TinyAttention)]:
        setattr(fake_module, name, type(name, (base,), {'__module__': canonical}))
    fake_module.apply_rotary_pos_emb, fake_module.repeat_kv = apply_rope, repeat_kv
    monkeypatch.setitem(sys.modules, canonical, fake_module)
    policy = SimpleNamespace(model=nn.Module())
    policy.model.language_model = fake_module.LlamaForCausalLM()
    policy.model.language_model.model = fake_module.LlamaModel()
    for layer in policy.model.language_model.model.layers:
        layer.self_attn = fake_module.LlamaSdpaAttention()
    path = tmp_path / 'synthetic_llama.py'
    path.write_text('synthetic audited fixture\n', encoding='utf-8')
    monkeypatch.setattr(module, 'AUDITED_SOURCE_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(module.metadata, 'version', lambda name: '4.40.1')
    monkeypatch.setattr(torch, '__version__', '2.4.1+cu121')
    runtime, _, _ = module._inspect_runtime(policy)
    assert json.loads(json.dumps(runtime)) == runtime
    assert runtime['attention_layer_count'] == 3
    path.write_text('different installed source\n', encoding='utf-8')
    with pytest.raises(ValueError, match='SHA'):
        module._inspect_runtime(policy)
    path.write_text('synthetic audited fixture\n', encoding='utf-8')
    monkeypatch.setattr(module.metadata, 'version', lambda name: '4.41.0')
    with pytest.raises(ValueError, match='versions'):
        module._inspect_runtime(policy)


def test_install_preserves_existing_lora_objects_freezing_and_other_instances(monkeypatch):
    from egrs.task_control.oft import install
    from egrs.augmentation.oft import LoRALinear
    policy = make_policy(monkeypatch)
    install(policy)
    other = TinyLanguageModel()
    other_forward = other.model.layers[0].self_attn.forward.__func__
    parameters = dict(policy.model.named_parameters())
    trained = {name: value.requires_grad for name, value in parameters.items()}
    loras = [value for value in policy.model.modules() if isinstance(value, LoRALinear)]
    implementation().install_attention(policy, 'f1')
    assert len(loras) == 12
    assert [value for value in policy.model.modules() if isinstance(value, LoRALinear)] == loras
    assert set(dict(policy.model.named_parameters())) == set(parameters)
    assert all(dict(policy.model.named_parameters())[key] is value for key, value in parameters.items())
    assert {name: value.requires_grad for name, value in parameters.items()} == trained
    assert other.model.layers[0].self_attn.forward.__func__ is other_forward
    assert '_update_causal_mask' not in other.model.__dict__
    with pytest.raises(ValueError, match='already installed'):
        implementation().install_attention(policy, 'f0')


def test_blocking_only_proprio_still_leaks_through_other_control_tokens(monkeypatch):
    policy, _ = tiny_policy(monkeypatch, 'f1')
    model = policy.model.language_model
    model.eval()
    hidden = torch.randn(1, 5, 4, requires_grad=True)
    p_only = torch.zeros(1, 1, 5, 5)
    p_only[:, :, :2, 2] = float('-inf')
    leaked = model(inputs_embeds=hidden, attention_mask=p_only, use_cache=False).hidden_states[-1]
    leaked[:, :2].sum().backward()
    assert torch.count_nonzero(hidden.grad[:, 2]) > 0
    hidden.grad.zero_()
    firewall = torch.zeros(1, 1, 5, 5)
    firewall[:, :, :2, 2:] = float('-inf')
    clean = model(inputs_embeds=hidden, attention_mask=firewall, use_cache=False).hidden_states[-1]
    clean[:, :2].sum().backward(retain_graph=True)
    assert torch.count_nonzero(hidden.grad[:, 2:]) == 0
    hidden.grad.zero_()
    clean[:, 4].sum().backward()
    assert torch.count_nonzero(hidden.grad[:, 2]) > 0


@pytest.mark.parametrize('mask', [torch.full((1, 1, 3, 3), float('-inf')),
                                 torch.full((1, 1, 3, 3), float('nan')),
                                 torch.zeros(1, 1, 3, 3, dtype=torch.float64),
                                 torch.zeros(1, 3)])
def test_invalid_final_mask_is_rejected_instead_of_unmasked(monkeypatch, mask):
    policy, _ = tiny_policy(monkeypatch)
    attention = policy.model.language_model.model.layers[0].self_attn
    with pytest.raises(ValueError, match='mask|key'):
        attention(torch.randn(1, 3, 4), mask, torch.arange(3).unsqueeze(0))


def test_failed_fused_forward_removes_sample_hooks_and_next_reference_is_native(monkeypatch):
    policy, controller = tiny_policy(monkeypatch, 'f1')
    kwargs, instruction = model_inputs(policy)
    decoder = policy.model.language_model.model
    original = decoder.forward

    def fail(**kwargs):
        raise RuntimeError('synthetic downstream failure')

    with monkeypatch.context() as context:
        context.setattr(decoder, 'forward', fail)
        with pytest.raises(RuntimeError, match='downstream failure'):
            controller.forward(policy.model, instruction_mask=instruction, **kwargs)
    assert decoder.forward == original
    assert not policy.proprio_projector._forward_hooks
    assert len(policy.model.language_model._forward_pre_hooks) == 1
    observed = []
    primitive = torch.nn.functional.scaled_dot_product_attention

    def capture(*args, **kw):
        observed.append(kw['attn_mask'].clone())
        return primitive(*args, **kw)

    monkeypatch.setattr(torch.nn.functional, 'scaled_dot_product_attention', capture)
    policy.model.eval()
    with torch.no_grad():
        policy.model(**kwargs)
    assert len(observed) == 3
    assert all(torch.count_nonzero(mask) == 0 for mask in observed)


def test_unsupported_model_structure_reports_a_compatibility_error():
    policy = SimpleNamespace(model=SimpleNamespace(language_model=nn.Linear(4, 4)))
    with pytest.raises(ValueError, match='structure|classes'):
        implementation().install_attention(policy, 'f0')


def test_public_contract_snapshot_cannot_switch_the_fixed_policy_arm(monkeypatch):
    policy, controller = tiny_policy(monkeypatch, 'f1')
    snapshot = controller.contract
    snapshot['experiment_arm'] = 'f0'
    assert controller.contract['experiment_arm'] == 'f1'
    runtime = controller.runtime
    runtime['dtype'] = 'changed'
    assert controller.runtime['dtype'] == 'torch.float32'
