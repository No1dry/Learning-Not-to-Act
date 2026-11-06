import copy
from contextlib import nullcontext
import json
import random
import sys
import subprocess
import types
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

from egrs.augmentation.oft import (inject_language_lora, language_targets,
    save_adapter, attach_trained_adapter, training_prediction, read_adapter_identity)
from egrs.augmentation.training import (masked_l1, BalancedSampler, photometric,
    save_training_state, load_training_state)


class Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        attn = nn.Module()
        for name in ('q_proj', 'k_proj', 'v_proj', 'o_proj'):
            setattr(attn, name, nn.Linear(3, 3))
        layer = nn.Module()
        layer.self_attn = attn
        self.language_model = nn.Module()
        self.language_model.model = nn.Module()
        self.language_model.model.layers = nn.ModuleList([layer])
        self.vision_backbone = copy.deepcopy(attn)

    def forward(self, value):
        for module in self.language_model.model.layers[0].self_attn.children():
            value = module(value)
        return value


def policy():
    return SimpleNamespace(model=Tiny(), action_head=nn.Linear(3, 1),
        proprio_projector=nn.Linear(8, 3), metadata={
        'repo_commit': 'e4287e94541f459edc4feabc4e181f537cd569a8',
        'checkpoint_source': {'repository': 'moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10',
            'revision': '638918f3d1c2e43a39a8a20772bdb8b91835e4b7'},
        'dataset_statistics_sha256': 'a'*64, 'normalization_statistics_sha256': 'b'*64,
        'component_checkpoint_sha256': {'action_head': 'c'*64, 'proprio_projector': 'd'*64},
        'unnorm_key': 'libero_10_no_noops'})


def test_only_full_language_attention_paths_train_and_frozen_head_keeps_gradient():
    p = policy()
    targets = inject_language_lora(p)
    assert len(targets) == 4
    assert all(name.startswith('language_model.model.layers.0.self_attn.') for name in targets)
    loss = p.action_head(p.model(torch.ones(2, 3))).square().mean()
    loss.backward()
    trainable = [(n, v) for n, v in p.model.named_parameters() if v.requires_grad]
    assert len(trainable) == 8
    assert any(v.grad is not None and v.grad.abs().sum() > 0 for n, v in trainable if 'lora_B' in n)
    assert all(v.grad is None for v in p.action_head.parameters())
    assert all(not v.requires_grad for v in p.proprio_projector.parameters())
    assert all(not v.requires_grad for v in p.model.vision_backbone.parameters())


def test_masked_loss_counts_valid_scalars_and_ignores_padding():
    pred = torch.tensor([[[1., 3.], [100., 100.]]], requires_grad=True)
    loss = masked_l1(pred, torch.zeros_like(pred), torch.tensor([[True, False]]))
    assert loss.item() == 2
    loss.backward()
    assert pred.grad.tolist() == [[[.5, .5], [0., 0.]]]
    with pytest.raises(ValueError, match='valid'):
        masked_l1(pred, pred, torch.zeros(1, 2, dtype=torch.bool))


def test_sampling_balances_stage_task_source_and_empty_pools_are_honest():
    rows = [dict(view='RAW', task_key='a', source_id='s1') for _ in range(100)]
    rows += [dict(view='RAW', task_key='b', source_id='s2')]
    sampler = BalancedSampler(rows, {'RAW': .5, 'PROGRESS': .25, 'ATOMIC': .25}, seed=7)
    picks = [rows[sampler.draw()] for _ in range(3000)]
    assert 1300 < sum(r['task_key'] == 'b' for r in picks) < 1700
    assert sampler.report()['actual_views'] == {'RAW': 1.0}
    assert sampler.report()['augmentation_available'] is False
    assert sampler.report()['unavailable_views'] == ['ATOMIC', 'PROGRESS']


def test_missing_source_augmentation_falls_back_raw_and_progress_balances_real_stages():
    rows = [dict(view='RAW', task_key='a', source_id='s1'),
            dict(view='RAW', task_key='a', source_id='s2')]
    rows += [dict(view='PROGRESS', task_key='a', source_id='s1', progress_stage='both') for _ in range(100)]
    rows += [dict(view='PROGRESS', task_key='a', source_id='s1', progress_stage='b')]
    sampler = BalancedSampler(rows, {'RAW': .5, 'PROGRESS': .5}, seed=7)
    picks = [rows[sampler.draw()] for _ in range(4000)]
    progress = [row for row in picks if row['view'] == 'PROGRESS']
    assert 850 < len(progress) < 1150
    assert 400 < sum(row['progress_stage'] == 'b' for row in progress) < 600
    assert 1800 < sum(row['source_id'] == 's2' for row in picks) < 2200


def test_photometric_uses_same_factors_for_both_views():
    image = np.full((4, 4, 3), 100, dtype=np.uint8)
    a, b = photometric([image, image.copy()], random.Random(1), probability=1)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, image)


def test_adapter_roundtrip_preserves_outputs_and_rejects_lineage(tmp_path):
    torch.manual_seed(1)
    p = policy()
    base = copy.deepcopy(p)
    inject_language_lora(p)
    for name, value in p.model.named_parameters():
        if 'lora_B' in name:
            value.data.fill_(.2)
    save_adapter(p, tmp_path, group='progress_aug')
    attach_trained_adapter(base, tmp_path)
    assert torch.equal(base.model(torch.ones(1, 3)), p.model(torch.ones(1, 3)))
    bad = policy()
    bad.metadata['dataset_statistics_sha256'] = 'f'*64
    with pytest.raises(ValueError, match='lineage'):
        attach_trained_adapter(bad, tmp_path)


def test_adapter_manifest_rejects_incomplete_lineage_before_loading_model(tmp_path):
    p = policy()
    inject_language_lora(p)
    identity = save_adapter(p, tmp_path, group='progress_aug')
    del identity['base_lineage']['dataset_statistics_sha256']
    (tmp_path/'identity.json').write_text(json.dumps(identity),encoding='utf-8')
    with pytest.raises(ValueError, match='lineage'):
        read_adapter_identity(tmp_path)


def test_identity_reader_runs_without_torch_numpy_or_transformers(tmp_path):
    p = policy()
    inject_language_lora(p)
    save_adapter(p, tmp_path, group='progress_aug')
    script = '''
import importlib.abc
import sys
class BlockModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'numpy', 'transformers'}:
            raise AssertionError('planning imported model dependency: ' + fullname)
sys.meta_path.insert(0, BlockModels())
from egrs.augmentation.adapter_identity import read_adapter_identity
print(read_adapter_identity(sys.argv[1])['group'])
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'progress_aug'


def test_resume_restores_optimizer_scheduler_and_all_cpu_rng(tmp_path):
    p = policy()
    inject_language_lora(p)
    params = [v for v in p.model.parameters() if v.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=.01)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: (s+1)/10)
    p.model(torch.ones(1, 3)).sum().backward()
    optimizer.step()
    scheduler.step()
    sampler = BalancedSampler([dict(view='RAW', task_key='a', source_id='s')], {'RAW': 1})
    save_training_state(tmp_path, p, optimizer, scheduler, sampler, update=3, best_dev=.4, config={'name':'raw_control'})
    want = (random.random(), np.random.rand(), torch.rand(1), sampler.draw())
    load_training_state(tmp_path, p, optimizer, scheduler, sampler, config={'name':'raw_control'})
    got = (random.random(), np.random.rand(), torch.rand(1), sampler.draw())
    assert got[0:2] == want[0:2]
    assert torch.equal(got[2], want[2])
    assert got[3] == want[3]
    assert scheduler.last_epoch == 1
    assert optimizer.state


def test_training_input_path_keeps_two_views_proprio_and_shifted_56_action_states(monkeypatch):
    # CPU seam for the external, source-verified OFT interfaces. The marker states
    # make an off-by-one patch/prompt shift observable at the frozen action head.
    helper = types.ModuleType('experiments.robot.openvla_utils')
    resized = []
    def resize(image, size):
        assert size == 224
        resized.append(image)
        return image
    def prepare(images, cfg):
        assert resized == [10,20]
        return images
    helper.resize_image_for_policy = resize
    helper.prepare_images_for_vla = prepare
    monkeypatch.setitem(sys.modules, 'experiments.robot.openvla_utils', helper)

    class Inputs(dict):
        def to(self, *args, **kwargs):
            return self

    class Processor:
        def __call__(self, prompt, image):
            assert prompt == 'In: What action should the robot take to move cup?\nOut:'
            return Inputs(input_ids=torch.tensor([[1, 4]]), attention_mask=torch.ones(1, 2),
                          pixel_values=torch.as_tensor(image).reshape(1, 1, 1, 1))

    class ForwardTiny(Tiny):
        def __init__(self):
            super().__init__()
            self.vision_backbone.get_num_patches = lambda: 2
            self.vision_backbone.get_num_images_in_input = lambda: 2

        def _prepare_input_for_action_prediction(self, ids, mask):
            return (torch.cat([ids, torch.ones(1, 56, dtype=torch.long), torch.tensor([[2]])], 1),
                    torch.cat([mask, torch.ones(1, 57)], 1))

        def _prepare_labels_for_action_prediction(self, labels, ids):
            return torch.cat([labels, torch.full((1, 56), 32001), torch.tensor([[2]])], 1)

        def _process_action_masks(self, labels):
            return labels == 32001

        def forward(self, **kwargs):
            assert kwargs['pixel_values'].flatten().tolist() == [10, 20]
            assert kwargs['proprio'].shape == (1, 8)
            assert kwargs['input_ids'][0, 2] == 29871
            assert kwargs['attention_mask'].shape == kwargs['input_ids'].shape
            states = torch.arange(65.).reshape(1, 65, 1).expand(1, 65, 3)
            return SimpleNamespace(hidden_states=[super().forward(states)])

    class Head(nn.Linear):
        def predict_action(self, hidden):
            assert hidden.shape == (1, 56, 3)
            self.seen = hidden
            return self(hidden).reshape(1, 8, 7)

    p = policy()
    p.model, p.action_head = ForwardTiny(), Head(3, 1)
    p.processor, p.cfg, p.resize_size = Processor(), SimpleNamespace(), 224
    inject_language_lora(p)
    item = {'instruction': 'Move cup', 'images': [10, 20], 'proprio': np.zeros(8)}
    prediction = training_prediction(p, item)
    prediction.square().mean().backward()
    assert any(v.grad is not None and v.grad.abs().sum() > 0 for n,v in p.model.named_parameters() if 'lora_B' in n)
    # 5 patch/proprio tokens + 2 shifted prompt positions = source hidden index7.
    expected = p.model.language_model.model.layers[0].self_attn
    value = torch.full((3,), 7.)
    for module in expected.children():
        value = module(value)
    assert torch.allclose(p.action_head.seen[0, 0], value)


def test_tiny_training_entry_selects_raw_dev_and_resume_matches_uninterrupted(tmp_path, monkeypatch):
    from egrs.augmentation import training, data
    export = tmp_path / 'export'
    export.mkdir()
    for name in ('sources.json', 'windows.jsonl', 'report.json'):
        (export / name).write_text('{}', encoding='utf-8')
    config = {'name':'raw_control', 'view_weights':{'RAW':1.}, 'photometric_probability':0.,
        'seed':7, 'updates':2, 'save_every':1, 'learning_rate':.01, 'warmup_updates':2,
        'gradient_accumulation':2, 'microbatch':1, 'precision':'bf16', 'gradient_checkpointing':True}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(config), encoding='utf-8')
    seen_splits = []

    class Dataset:
        def __init__(self, directory, split, views):
            seen_splits.append((split, views))
            self.rows = [dict(view='RAW', task_key='a', source_id='s')]
        def __len__(self):
            return 1
        def __getitem__(self, index):
            if index >= 1:
                raise IndexError(index)
            return dict(images=[np.zeros((2,2,3),dtype=np.uint8)]*2, actions=np.ones((8,7)),
                action_mask=np.array([True,True,False,False,False,False,False,False]), proprio=np.zeros(8))
        def validate_normalization(self, stats, unnorm_key, digest):
            assert stats == {'libero_10_no_noops':{}}

    def load(*args):
        p = policy()
        p.model.norm_stats = {'libero_10_no_noops':{}}
        p.model.language_model.config = SimpleNamespace(use_cache=True)
        p.model.language_model.gradient_checkpointing_enable = lambda **kwargs: None
        p.cfg = SimpleNamespace(unnorm_key='libero_10_no_noops')
        p.close = lambda: None
        return p

    def predict(p, item, images=None):
        return p.action_head(p.model(torch.ones(56,3))).reshape(1,8,7)

    monkeypatch.setattr(data, 'AugmentationDataset', Dataset)
    monkeypatch.setattr(training, 'load_policy', load)
    # The production presets retain1000 updates; this test exercises only the
    # entry's tiny CPU loop without authorizing a real configuration override.
    monkeypatch.setattr(training, 'validate_config', lambda config: None)
    monkeypatch.setattr(training, 'training_prediction', predict)
    monkeypatch.setattr(training.torch, 'autocast', lambda *args, **kwargs: nullcontext())
    output = tmp_path / 'run'
    args = SimpleNamespace(config=config_file, export_dir=export, output_dir=output,
        resume=None, benchmark_root='unused', oft_root='unused', checkpoint='unused')
    training.run(args)
    uninterrupted = torch.load(output/'update-000002'/'adapter.pt',weights_only=True)
    assert ('dev',['RAW']) in seen_splits
    selected = json.loads((output/'best_checkpoint.json').read_text())
    assert selected['selection'] == 'minimum valid-scalar L1 on shared RAW dev'
    args.resume = output/'update-000001'
    training.run(args)
    resumed = torch.load(output/'update-000002'/'adapter.pt',weights_only=True)
    assert set(uninterrupted) == set(resumed)
    assert all(torch.equal(uninterrupted[name], resumed[name]) for name in uninterrupted)


@pytest.mark.parametrize('name', ['raw_control', 'progress_aug'])
def test_formal_presets_reject_changed_budget_or_condition(name):
    from pathlib import Path
    from egrs.augmentation.training import validate_config
    config = json.loads((Path(__file__).parents[1]/'configs'/'augmentation'/f'{name}.json').read_text())
    validate_config(config)
    for key, value in [('updates',2), ('gradient_accumulation',1), ('learning_rate',.001),
                       ('view_weights',{'RAW':1}), ('photometric_probability',.2)]:
        changed = copy.deepcopy(config)
        changed[key] = value
        with pytest.raises(ValueError, match='preset'):
            validate_config(changed)
