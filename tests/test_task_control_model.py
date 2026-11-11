"""CPU-only contracts at the pinned OFT boundary; never load a checkpoint."""
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

from test_augmentation_training import Tiny, policy as original_policy


class Inputs(dict):
    def to(self, *args, **kwargs):
        return self


class Tokenizer:
    def __call__(self, prompt, **kwargs):
        start = prompt.index('move cup')
        return {'input_ids': [[1, 4, 5, 6, 7, 8, 0]],
                'offset_mapping': [[(0, 0), (0, start), (start, start+4),
                                    (start+5, start+8), (start+8, start+9),
                                    (start+9, len(prompt)), (0, 0)]]}


class Processor:
    tokenizer = Tokenizer()
    def __call__(self, prompt, image):
        assert prompt == 'In: What action should the robot take to move cup?\nOut:'
        return Inputs(input_ids=torch.tensor([[1, 4, 5, 6, 7, 8, 0]]),
                      attention_mask=torch.tensor([[1, 1, 1, 1, 1, 1, 0]]),
                      pixel_values=torch.tensor([image]).reshape(1, 1, 1, 1))


class Backbone(Tiny):
    def __init__(self):
        super().__init__()
        self.llm_dim = 3
        self.calls = 0
        self.vision_backbone.get_num_patches = lambda: 2
        self.vision_backbone.get_num_images_in_input = lambda: 2
    def _prepare_input_for_action_prediction(self, ids, attention):
        return (torch.cat([ids, torch.ones(1, 56, dtype=torch.long), torch.tensor([[2]])], 1),
                torch.cat([attention, torch.ones(1, 57, dtype=attention.dtype)], 1))
    def _prepare_labels_for_action_prediction(self, labels, ids):
        return torch.cat([labels, torch.full((1, 56), 32001), torch.tensor([[2]])], 1)
    def _process_action_masks(self, labels):
        return labels == 32001
    def forward(self, **kwargs):
        self.calls += 1
        self.seen = kwargs
        # Actual inserted sequence: BOS, 4 image patches, proprio, input[1:].
        length = kwargs['input_ids'].shape[1] + 5
        value = torch.arange(length * 3, dtype=torch.float32).reshape(1, length, 3) / 100
        return SimpleNamespace(hidden_states=[super().forward(value)],
                               projector_features=torch.zeros(1, 5, 3))


class Head(nn.Linear):
    def predict_action(self, h):
        self.seen = h
        return self(h).reshape(1, 8, 7)


def tiny_policy(monkeypatch):
    helper = ModuleType('experiments.robot.openvla_utils')
    helper.resize_image_for_policy = lambda image, size: image
    helper.prepare_images_for_vla = lambda images, cfg: images
    monkeypatch.setitem(sys.modules, 'experiments.robot.openvla_utils', helper)
    p = original_policy()
    p.model, p.action_head = Backbone(), Head(3, 1)
    p.processor, p.cfg, p.resize_size = Processor(), SimpleNamespace(), 224
    from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
    p.metadata['dataset_statistics_sha256'] = RETENTION_STATS_SHA
    return p


def sensors():
    return {'images': [10, 20], 'instruction': 'Move cup', 'proprio': np.arange(8) / 8}


def test_actual_inserted_layout_excludes_bos_proprio_boilerplate_padding_and_future_actions(monkeypatch):
    from egrs.task_control.oft import install, prediction
    p = tiny_policy(monkeypatch)
    install(p)
    seen = []
    handle = p.model.task_control.context.register_forward_pre_hook(lambda module, args: seen.append(args[0]))
    result = prediction(p, dict(sensors(), actions='GT', task_id='GT', completion_count=2))
    handle.remove()
    assert p.model.calls == 1
    assert result.actions.shape == (1, 8, 7) and result.h.shape == (1, 56, 3)
    assert result.z.shape == (1, 128) and result.count_logits.shape == (1, 3)
    assert set(p.model.seen) == {'input_ids', 'attention_mask', 'pixel_values', 'labels', 'proprio',
        'proprio_projector', 'use_film', 'output_hidden_states', 'output_projector_features', 'return_dict', 'use_cache'}
    assert p.model.seen['input_ids'][0, :7].tolist() == [1, 4, 5, 6, 7, 8, 29871]
    # Padding is removed, then empty token appended: P=7 and inserted slots=5.
    # Original instruction tokens 2,3 map to hidden 7,8; images map to 1..4.
    a = p.model.language_model.model.layers[0].self_attn
    def hidden(indices):
        x = torch.tensor(indices, dtype=torch.float32).reshape(1, -1, 1)*3
        x = (x + torch.arange(3)) / 100
        for layer in a.children(): x = layer(x)
        return x
    assert torch.allclose(seen[0], torch.cat([hidden([1,2,3,4]).mean(1), hidden([7,8]).mean(1)], -1))
    assert torch.allclose(result.h[:, :1], hidden([11]))
    assert torch.equal(result.actions, p.action_head.predict_action(result.h))


def test_decode_swaps_only_z_without_backbone_and_initialization_is_exact(monkeypatch):
    from egrs.task_control.oft import install, prediction, decode
    p = tiny_policy(monkeypatch); install(p)
    a = prediction(p, sensors())
    b = prediction(p, dict(sensors(), proprio=np.ones(8)))
    assert torch.equal(decode(p, a, b.z), a.actions)
    with torch.no_grad(): p.model.task_control.W_out.weight.fill_(.01)
    h, proprio = a.h.clone(), a.proprio.clone()
    own, swap = decode(p, a), decode(p, a, a.z + 2)
    assert p.model.calls == 2
    assert torch.equal(a.h, h) and torch.equal(a.proprio, proprio)
    assert not torch.equal(own, swap)


def test_nonzero_output_branch_reaches_every_module_and_lora_with_frozen_base(monkeypatch):
    from egrs.task_control.oft import install, prediction
    p = tiny_policy(monkeypatch); install(p)
    with torch.no_grad():
        p.model.task_control.W_out.weight.fill_(.01)
        for name, parameter in p.model.named_parameters():
            if name.endswith('lora_B'): parameter.fill_(.01)
    result = prediction(p, sensors())
    (result.actions.square().mean() + result.count_logits.square().mean()).backward()
    for name, parameter in p.model.named_parameters():
        if parameter.requires_grad:
            assert parameter.grad is not None and parameter.grad.abs().sum() > 0, name
        else: assert parameter.grad is None, name
    assert all(parameter.grad is None for parameter in p.action_head.parameters())
    assert all(parameter.grad is None for parameter in p.proprio_projector.parameters())


def test_disabled_reference_bypasses_context_residual_and_counter(monkeypatch):
    from egrs.task_control.oft import install, prediction
    p = tiny_policy(monkeypatch); install(p)
    p.model.task_control.enabled = False
    p.model.task_control.register_forward_pre_hook(lambda *a: pytest.fail('student module in reference'))
    p.model.task_control.context.register_forward_pre_hook(lambda *a: pytest.fail('student context in reference'))
    from egrs.augmentation import oft
    monkeypatch.setattr(oft, 'training_prediction', lambda policy, item: torch.ones(1,8,7))
    result = prediction(p, sensors())
    assert torch.equal(result.actions, torch.ones(1,8,7)) and p.model.calls == 0


def test_strict_adapter_roundtrip_hash_inventory_shapes_recipe_and_stdlib_reader(monkeypatch, tmp_path):
    from egrs.task_control.oft import install, prediction
    from egrs.task_control.adapter import save_adapter, read_adapter_identity, attach_trained_adapter
    p = tiny_policy(monkeypatch); fresh = deepcopy(p); install(p)
    with torch.no_grad(): p.model.task_control.W_out.weight.fill_(.05)
    identity = save_adapter(p,tmp_path,arm='c1',update=1000,index_identity='e'*64,
        reference_calls={'train':8000,'dev':1024,'total':9024,'budget':9024})
    from egrs.task_control.training import PRESET, validate_config
    config = deepcopy(PRESET)
    validate_config(config)
    observations = sum(config['pool_samples'].values()) + 2 * config['pairs_per_update']
    saved_identity = read_adapter_identity(tmp_path)
    assert saved_identity['training_recipe']['gradient_accumulation'] == config['gradient_accumulation'] == observations
    assert identity['schema_version'] == 'task038-oft-adapter-v1'
    assert any(name.startswith('task_control.') for name in identity['trainable_parameters'])
    attach_trained_adapter(fresh,tmp_path,arm='c1')
    assert torch.equal(prediction(p,sensors()).actions, prediction(fresh,sensors()).actions)
    script = """
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','transformers'}:raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
from egrs.task_control.adapter import read_adapter_identity
print(read_adapter_identity(sys.argv[1])['arm'])
"""
    run = subprocess.run([sys.executable,'-c',script,str(tmp_path)],capture_output=True,text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == 'c1'
    with pytest.raises(ValueError,match='arm'): attach_trained_adapter(deepcopy(fresh),tmp_path,arm='c0')
    state = torch.load(tmp_path/'adapter.pt',weights_only=True)
    state.pop('task_control.W_out.weight')
    torch.save(state,tmp_path/'adapter.pt')
    identity['adapter_sha256'] = hashlib.sha256((tmp_path/'adapter.pt').read_bytes()).hexdigest()
    (tmp_path/'identity.json').write_text(json.dumps(identity))
    with pytest.raises(ValueError,match='inventory|tensor'): attach_trained_adapter(tiny_policy(monkeypatch),tmp_path)
    identity['training_recipe']['z_dim'] = 7
    (tmp_path/'identity.json').write_text(json.dumps(identity))
    with pytest.raises(ValueError,match='recipe'): read_adapter_identity(tmp_path)


def test_eval_calls_same_prediction_then_original_unnormalization_and_gripper(monkeypatch, tmp_path):
    from egrs.task_control.oft import install, prediction
    from egrs.task_control.adapter import save_adapter
    p = tiny_policy(monkeypatch)
    p.cfg.unnorm_key = 'libero_10_no_noops'
    p.model.norm_stats = {'libero_10_no_noops': {'proprio': {'fake':'stats'}}}
    p.model._unnormalize_actions = lambda values, key: values + 3
    p.reset = lambda: None
    p.close = lambda: None
    # Core extraction functions receive only original raw observation fields.
    api = SimpleNamespace(get_libero_image=lambda raw: raw['agentview_image'],
        get_libero_wrist_image=lambda raw: raw['robot0_eye_in_hand_image'],
        quat2axisangle=lambda quat: quat[:3])
    p.api, p.torch = api, torch
    install(p)
    with torch.no_grad(): p.model.task_control.W_out.weight.fill_(.03)
    save_adapter(p,tmp_path,arm='c0',update=1000,index_identity='e'*64,
        reference_calls={'train':8000,'dev':0,'total':8000,'budget':9024})
    # Return the already-installed CPU policy from the core loader seam.
    loader = ModuleType('benchmark.remaining_goals.adapters.openvla_oft')
    loader.OpenVLAOFTPolicy = lambda config: p
    monkeypatch.setitem(sys.modules, loader.__name__, loader)
    core = ModuleType('benchmark.remaining_goals.adapters.openvla')
    core._raw_observation = lambda obs, **kwargs: {key:obs[key] for key in (
        'agentview_image','robot0_eye_in_hand_image','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos')}
    core._instruction = lambda value:value
    core._action_array = lambda value, **kwargs: np.asarray(value)
    core._decode_action = lambda api, values, **kwargs: values * 2
    monkeypatch.setitem(sys.modules,core.__name__,core)
    transfer = ModuleType('benchmark.remaining_goals.adapters.oft_transfer')
    transfer.FACTORY = 'original:loader'
    monkeypatch.setitem(sys.modules,transfer.__name__,transfer)
    helper = sys.modules['experiments.robot.openvla_utils']
    helper.normalize_proprio = lambda proprio, stats: proprio
    from egrs.task_control.policy import TaskControlPolicy
    evaluation = TaskControlPolicy({'method_adapter':str(tmp_path),'task_control_arm':'c0'})
    expected = prediction(p,sensors()).actions.detach().numpy()[0]
    before = p.model.calls
    result = evaluation.predict({'agentview_image':10,'robot0_eye_in_hand_image':20,
        'robot0_eef_pos':np.arange(3)/8,'robot0_eef_quat':np.arange(3,7)/8,
        'robot0_gripper_qpos':np.arange(6,8)/8,'completion_count':2,'task_id':'GT'},'Move cup')
    assert p.model.calls == before + 1
    assert np.allclose(result,(expected+3)*2)


def test_identity_rejects_malformed_nested_records_as_value_errors(monkeypatch, tmp_path):
    from egrs.task_control.oft import install
    from egrs.task_control.adapter import save_adapter, read_adapter_identity
    p = tiny_policy(monkeypatch); install(p)
    identity = save_adapter(p,tmp_path,arm='c0',update=1,index_identity='e'*64,
        reference_calls={'train':8,'dev':0,'total':8,'budget':9024})
    for field,value in [('base_lineage',None),('target_modules',[3]),
                        ('tensor_sha256',None),('trainable_parameters',None),('arm',[])]:
        changed = dict(identity,**{field:value})
        (tmp_path/'identity.json').write_text(json.dumps(changed))
        with pytest.raises(ValueError): read_adapter_identity(tmp_path)


def test_unverified_token_map_and_changed_actual_prefix_fail_before_feature_use(monkeypatch):
    from egrs.task_control.oft import install, prediction
    p = tiny_policy(monkeypatch); install(p)
    p.processor.tokenizer = lambda *args,**kwargs: {'input_ids':[[1]],'offset_mapping':[[(0,0)]]}
    with pytest.raises(ValueError,match='offset'): prediction(p,sensors())
    assert p.model.calls == 0
    p.processor = Processor()
    p.model.vision_backbone.get_num_patches = lambda:3
    with pytest.raises(ValueError,match='layout'): prediction(p,sensors())


def test_first_action_gradient_opens_only_zero_output_projection(monkeypatch):
    from egrs.task_control.oft import install, prediction
    p = tiny_policy(monkeypatch); install(p)
    module = p.model.task_control
    assert module.W_h.weight.abs().sum() > 0 and module.W_z.weight.abs().sum() > 0
    assert module.W_p.weight.abs().sum() > 0 and module.W_out.weight.count_nonzero() == 0
    prediction(p,sensors()).actions.square().mean().backward()
    assert module.W_out.weight.grad.abs().sum() > 0
    assert module.W_h.weight.grad.count_nonzero() == 0
    assert module.W_z.weight.grad.count_nonzero() == 0
    assert module.W_p.weight.grad.count_nonzero() == 0


@pytest.mark.parametrize('mutation', ['missing','extra','shape','value','dtype'])
def test_adapter_rejects_every_forged_tensor_change_before_partial_restore(monkeypatch,tmp_path,mutation):
    from egrs.task_control.oft import install
    from egrs.task_control.adapter import save_adapter, attach_trained_adapter
    p = tiny_policy(monkeypatch); install(p)
    identity = save_adapter(p,tmp_path,arm='c0',update=1,index_identity='e'*64,
        reference_calls={'train':8,'dev':0,'total':8,'budget':9024})
    state = torch.load(tmp_path/'adapter.pt',weights_only=True)
    key = 'task_control.W_out.weight'
    if mutation == 'missing': del state[key]
    elif mutation == 'extra': state['task_control.unexpected'] = torch.ones(1)
    elif mutation == 'shape': state[key] = state[key][:1]
    elif mutation == 'value': state[key].fill_(1)
    else: state[key] = state[key].double()
    torch.save(state,tmp_path/'adapter.pt')
    identity['adapter_sha256'] = hashlib.sha256((tmp_path/'adapter.pt').read_bytes()).hexdigest()
    (tmp_path/'identity.json').write_text(json.dumps(identity))
    with pytest.raises(ValueError,match='inventory|tensor'): attach_trained_adapter(tiny_policy(monkeypatch),tmp_path)
