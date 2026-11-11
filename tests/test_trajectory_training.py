"""CPU-only task035 weighting, pool and checkpoint integration contracts."""
from contextlib import nullcontext
import json
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType

import numpy as np
import pytest
import torch

from test_augmentation_training import policy
from egrs.augmentation.oft import inject_language_lora, save_adapter, read_adapter_identity


def recipe():
    from egrs.trajectory_augmentation import training
    return training


def use_dataset(monkeypatch, dataset):
    module = ModuleType('egrs.trajectory_augmentation.data')
    module.GeneratedTrajectoryDataset = dataset
    monkeypatch.setitem(sys.modules, module.__name__, module)


def rows():
    return [dict(domain=d, task_key=t, parent_demo_id=p, variant=v, source_id=p+v,
                 start=i, stop=i+1, action_mask=[True]+[False]*7)
            for d in ('10', 'normal') for t in ('a', 'b')
            for p in (t+'1', t+'2') for v in ('v1', 'v2') for i in range(3)]


def test_batch_weights_preserve_domain_gradient_with_unequal_padding():
    training = recipe()
    items = [dict(action_mask=np.array([True]+[False]*7)),
             dict(action_mask=np.ones(8, dtype=bool)),
             dict(action_mask=np.ones(8, dtype=bool))]
    domains = ['10', '10', 'normal']
    weights, metrics = training.batch_weights(items, domains)
    prediction = torch.ones(3,8,7, requires_grad=True)
    losses = [training.base.masked_l1(prediction[i:i+1], torch.zeros(1,8,7),
                                    torch.as_tensor(item['action_mask']).unsqueeze(0))
              for i,item in enumerate(items)]
    sum(value * weight for value, weight in zip(losses, weights)).backward()
    assert prediction.grad[0,0].tolist() == pytest.approx([.7/63]*7)
    assert prediction.grad[1,0].tolist() == pytest.approx([.7/63]*7)
    assert prediction.grad[2,0].tolist() == pytest.approx([.3/56]*7)
    assert torch.equal(prediction.grad[0,1:], torch.zeros(7,7))
    assert metrics['valid_scalars'] == {'10': 63, 'normal': 56}
    assert metrics['valid_scalar_fraction']['10'] == pytest.approx(63/119)


def test_sampler_fixed_batch_balances_hierarchy_and_restores_rng():
    training = recipe()
    population = rows()
    population += [population[0].copy() for _ in range(1000)]
    sampler = training.DomainBalancedSampler(population, seed=7)
    picked = []
    for _ in range(400):
        batch = sampler.draw_batch()
        assert [population[index]['domain'] for index in batch] == ['10']*12+['normal']*4
        picked.extend(population[index] for index in batch[:12])
    assert 2200 < sum(row['task_key'] == 'a' for row in picked) < 2600
    assert 1000 < sum(row['parent_demo_id'] == 'a1' for row in picked) < 1400
    assert 1900 < sum(row['variant'] == 'v1' for row in picked) < 2900
    state = sampler.state_dict()
    want = sampler.draw_batch()
    sampler.load_state_dict(state)
    assert sampler.draw_batch() == want
    with pytest.raises(ValueError, match='normal'):
        training.DomainBalancedSampler([row for row in population if row['domain'] == '10'])


def test_dev_selection_bounded_unique_balanced_and_deterministic():
    training = recipe()
    population = rows()
    population += [dict(population[0], start=i+10) for i in range(1000)]
    chosen = training.dev_indices(population, limit=256)
    assert chosen == training.dev_indices(population, limit=256)
    assert len(chosen['10']) == 256
    assert len(chosen['normal']) == 24
    assert len(set(chosen['10'])) == 256
    assert {population[i]['task_key'] for i in chosen['10'][:2]} == {'a', 'b'}


def test_padded_only_windows_fail_pool_validation():
    training = recipe()
    population = rows()
    population[0]['action_mask'] = [False]*8
    with pytest.raises(ValueError, match='valid action'):
        training.DomainBalancedSampler(population)
    with pytest.raises(ValueError, match='valid action'):
        training.dev_indices(population)


def test_official_recipe_rejects_budget_weights_and_data_kind_overrides():
    training = recipe()
    config = json.loads((Path(__file__).parents[1]/'configs'/'trajectory_augmentation'/'robot_rewind_mix.json').read_text())
    training.validate_config(config)
    for key, value in [('updates',2), ('data_kind','ordinary_expert_demo'),
                       ('domain_weights',{'10':1.,'normal':0.}),
                       ('domain_samples',{'10':16,'normal':0}),
                       ('dev_limit_per_domain',1000), ('checkpoint_selection','minimum_dev')]:
        with pytest.raises(ValueError, match='preset'):
            training.validate_config(dict(config, **{key:value}))


def test_035_adapter_identity_requires_recipe_and_export_binding(tmp_path):
    p = policy()
    inject_language_lora(p)
    metadata = dict(recipe='robot_rewind_mix', data_kind='task035-generated-trajectories-v1',
                    update=1000, final_update=1000,
                    export_identity={name:'a'*64 for name in ('sources.json','windows.jsonl','report.json')})
    identity = save_adapter(p, tmp_path, group='robot_rewind_mix', metadata=metadata)
    assert identity['schema_version'] == 'task035-oft-adapter-v1'
    assert read_adapter_identity(tmp_path)['update'] == 1000
    for key, value in [('data_kind','task030'), ('recipe','progress_aug'), ('final_update',500), ('update',1001)]:
        bad = dict(identity, **{key:value})
        (tmp_path/'identity.json').write_text(json.dumps(bad))
        with pytest.raises(ValueError, match='recipe'):
            read_adapter_identity(tmp_path)


@pytest.mark.parametrize('missing_split,missing_domain', [('train','10'), ('train','normal'), ('dev','10'), ('dev','normal')])
def test_presets_require_both_train_and_dev_domains_before_model_load(tmp_path, monkeypatch, missing_split, missing_domain):
    training = recipe()
    config = json.loads((Path(__file__).parents[1]/'configs'/'trajectory_augmentation'/'robot_rewind_mix.json').read_text())
    config_file = tmp_path/'config.json'
    config_file.write_text(json.dumps(config))
    class Dataset:
        def __init__(self, export, split=None, domains=None):
            self.rows = [row for row in rows() if split != missing_split or row['domain'] != missing_domain]
            self.report = {'data_kind':'task035-generated-trajectories-v1'}
    use_dataset(monkeypatch, Dataset)
    monkeypatch.setattr(training.base, 'load_policy', lambda *args: pytest.fail('model load before pool validation'))
    args = SimpleNamespace(config=config_file, output_dir=tmp_path/'run', export_dir=tmp_path,
                           resume=None, benchmark_root='unused', oft_root='unused', checkpoint='unused')
    with pytest.raises(ValueError, match=missing_split+'.*'+missing_domain):
        training.run(args)


def test_mixed_tiny_loop_fixed_selection_and_resume_exactness(tmp_path, monkeypatch):
    training = recipe()
    export = tmp_path/'export'
    export.mkdir()
    for name in ('sources.json','windows.jsonl','report.json'):
        (export/name).write_text('{}')
    config = json.loads((Path(__file__).parents[1]/'configs'/'trajectory_augmentation'/'robot_rewind_mix.json').read_text())
    # Only the CPU test seam changes budget; public validation rejects this.
    config.update(updates=2, save_every=1)
    config_file = tmp_path/'config.json'
    config_file.write_text(json.dumps(config))

    class Dataset:
        def __init__(self, directory, split=None, domains=None):
            self.rows = rows()
            self.report = {'data_kind':'task035-generated-trajectories-v1'}
        def __getitem__(self, index):
            row = self.rows[index]
            valid = 1 if row['domain']=='10' else 8
            return dict(images=[np.zeros((2,2,3),dtype=np.uint8)]*2,
                        instruction='Move cup', proprio=np.zeros(8),
                        actions=np.ones((8,7)), action_mask=np.arange(8)<valid)
        def validate_normalization(self, *args):
            pass

    def load(*args):
        p = policy()
        p.model.norm_stats = {'libero_10_no_noops':{}}
        p.model.language_model.config = SimpleNamespace(use_cache=True)
        p.model.language_model.gradient_checkpointing_enable = lambda **kwargs: None
        p.cfg = SimpleNamespace(unnorm_key='libero_10_no_noops')
        p.close = lambda: None
        return p

    use_dataset(monkeypatch, Dataset)
    monkeypatch.setattr(training, 'validate_config', lambda value: None)
    monkeypatch.setattr(training.base, 'load_policy', load)
    monkeypatch.setattr(training.base, 'training_prediction', lambda p,item,images=None:
                        p.action_head(p.model(torch.ones(56,3))).reshape(1,8,7))
    monkeypatch.setattr(training.base.torch, 'autocast', lambda *args, **kwargs: nullcontext())
    # A worsening dev curve proves checkpoint selection is independent of dev.
    def evaluate(p, items):
        previous = getattr(p, 'dev_seen', 0)
        p.dev_seen = previous+1
        return 1. if previous < 2 else 2.
    monkeypatch.setattr(training.base, 'evaluate_dev', evaluate)
    output = tmp_path/'run'
    args = SimpleNamespace(config=config_file, output_dir=output, export_dir=export,
                           resume=None, benchmark_root='unused', oft_root='unused', checkpoint='unused')
    training.run(args)
    uninterrupted = torch.load(output/'update-000002'/'adapter.pt',weights_only=True)
    selected = json.loads((output/'selected_checkpoint.json').read_text())
    assert selected['checkpoint'] == 'update-000002'
    assert not (output/'best_checkpoint.json').exists()
    metrics = [json.loads(line) for line in (output/'metrics.jsonl').read_text().splitlines()]
    assert [row['selected'] for row in metrics] == [False, True]
    assert metrics[1]['dev']['weighted_l1'] > metrics[0]['dev']['weighted_l1']
    assert metrics[0]['batch']['sample_counts'] == {'10':12,'normal':4}
    assert metrics[0]['batch']['valid_scalars'] == {'10':84,'normal':224}
    args.resume = output/'update-000001'
    training.run(args)
    resumed = torch.load(output/'update-000002'/'adapter.pt',weights_only=True)
    assert all(torch.equal(uninterrupted[name],resumed[name]) for name in uninterrupted)
    # Resume cannot silently bind changed exported bytes.
    (export/'windows.jsonl').write_text('{"changed":true}')
    with pytest.raises(ValueError, match='dataset identity changed'):
        training.run(args)


def test_real_generated_export_feeds_tiny_mixed_training_with_original_stats(tmp_path, monkeypatch):
    """Catch mismatched real dataset API, transition indexing or doubled normalization."""
    import hashlib
    from test_trajectory_data import seed_manifest, attempts_for
    from egrs.trajectory_augmentation.data import (validate_seeds, export_generated,
                                                  GeneratedTrajectoryDataset)
    training = recipe()
    parents = validate_seeds(seed_manifest(tmp_path))
    assert {parent['split'] for parent in parents} == {'train', 'dev'}
    export = tmp_path/'export'
    export_generated(parents, attempts_for(tmp_path, parents, T=10), tmp_path, export)
    for split in ('train', 'dev'):
        dataset = GeneratedTrajectoryDataset(export, split=split)
        assert {row['domain'] for row in dataset.rows} == {'10', 'normal'}
        # T=10 transitions consume observations0..9; the recorded terminal o10
        # remains available for transition verification, never a target action.
        assert max(row['start'] for row in dataset.rows) == 9
        tail_index = next(index for index,row in enumerate(dataset.rows) if row['start']==9)
        tail = dataset[tail_index]
        assert int(tail['images'][0][0,0,0]) == 9
        assert tail['action_mask'].tolist() == [True]+[False]*7
        assert np.array_equal(tail['actions'][0], [0,0,0,0,0,0,1])
        assert np.count_nonzero(tail['actions'][1:]) == 0

    config = json.loads((Path(__file__).parents[1]/'configs'/'trajectory_augmentation'/'robot_rewind_mix.json').read_text())
    config.update(updates=2, save_every=1)  # Tiny local test seam only.
    config_file = tmp_path/'config.json'
    config_file.write_text(json.dumps(config))
    stats = {'libero_10': {
        'action': {'q01':[-2]*6+[0], 'q99':[4]*6+[1], 'mask':[True]*6+[False]},
        'proprio': {'q01':[-2]*8, 'q99':[4]*8, 'mask':[True]*8}}}
    normalized = []
    actual_validate = GeneratedTrajectoryDataset.validate_normalization
    def validate(dataset, supplied_stats, key, digest):
        normalized.append((set(row['split'] for row in dataset.rows), key, digest))
        actual_validate(dataset, supplied_stats, key, digest)
    monkeypatch.setattr(GeneratedTrajectoryDataset, 'validate_normalization', validate)

    def load(*args):
        p = policy()
        p.model.norm_stats = stats
        p.metadata['unnorm_key'] = 'libero_10'
        p.model.language_model.config = SimpleNamespace(use_cache=True)
        p.model.language_model.gradient_checkpointing_enable = lambda **kwargs: None
        p.cfg = SimpleNamespace(unnorm_key='libero_10')
        p.close = lambda: None
        return p

    observed_frames = []
    def predict(p, item, images=None):
        assert set(item) == {'images','proprio','actions','action_mask','instruction'}
        assert item['instruction'] == 'exact full instruction'
        assert np.count_nonzero(item['proprio']) == 0
        valid = item['action_mask']
        assert np.count_nonzero(item['actions'][valid,:6]) == 0
        assert np.all(item['actions'][valid,6] == 1)
        observed_frames.append(int(item['images'][0][0,0,0]))
        return p.action_head(p.model(torch.ones(56,3))).reshape(1,8,7)

    monkeypatch.setattr(training, 'validate_config', lambda value: None)
    monkeypatch.setattr(training.base, 'load_policy', load)
    monkeypatch.setattr(training.base, 'training_prediction', predict)
    monkeypatch.setattr(training.base.torch, 'autocast', lambda *args, **kwargs: nullcontext())
    output = tmp_path/'run'
    args = SimpleNamespace(config=config_file, output_dir=output, export_dir=export,
                           resume=None, benchmark_root='unused', oft_root='unused', checkpoint='unused')
    training.run(args)
    assert normalized == [({'train'},'libero_10','a'*64), ({'dev'},'libero_10','a'*64)]
    assert set(observed_frames) == set(range(10))
    identity = read_adapter_identity(output/'update-000002')
    assert identity['schema_version'] == 'task035-oft-adapter-v1'
    assert identity['group'] == identity['recipe'] == 'robot_rewind_mix'
    assert identity['data_kind'] == 'task035-generated-trajectories-v1'
    assert identity['update'] == 2 and identity['final_update'] == 1000
    assert identity['export_identity'] == {name:hashlib.sha256((export/name).read_bytes()).hexdigest()
                                          for name in ('sources.json','windows.jsonl','report.json')}
    # The real normalization binder must reject a different loaded checkpoint.
    stats['libero_10']['action']['q99'][0] = 5
    args.output_dir = tmp_path/'mismatched-stats'
    with pytest.raises(ValueError, match='action.q99 differs from original checkpoint'):
        training.run(args)
