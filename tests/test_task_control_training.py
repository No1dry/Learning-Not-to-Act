"""Synthetic CPU acceptance for paired losses, sampling and training state."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

from test_retention_data import prepared
from test_task_control_index import control_sources


def rows():
    return [dict(pool=pool, task_key=task, source_group=task + '/parent', variant=v,
                 action_mask=[True] * 8, prefix=prefix)
            for pool in ('ten', 'fresh', 'raw') for task in ('a', 'b')
            for v in ('v1', 'v2') for prefix in (True, False)]


def pairs():
    return [dict(task_key=t, source_group=t + '/p', parent_demo_id=t + '/p', variant=v)
            for t in ('a', 'b') for v in ('v1', 'v2')]


def test_sampling_is_identical_between_arms_and_resume_keeps_next_observations():
    from egrs.task_control.sampling import TaskControlSampler, dev_pair_indices
    c0 = TaskControlSampler(rows(), pairs(), seed=7)
    c1 = TaskControlSampler(rows(), pairs(), seed=7)
    for _ in range(7):
        main, pair = c0.draw_batch()
        assert (main, pair) == c1.draw_batch()
        assert Counter(rows()[i]['pool'] for i in main) == {'ten': 12, 'fresh': 4, 'raw': 4}
        assert c0.main.last_bins == ['expert'] * 12 + ['prefix'] * 2 + ['all'] * 2 + ['prefix'] * 2 + ['all'] * 2
    restored = TaskControlSampler(rows(), pairs(), seed=7)
    restored.load_state_dict(c0.state_dict())
    assert [restored.draw_batch() for _ in range(20)] == [c0.draw_batch() for _ in range(20)]
    assert sorted(dev_pair_indices(pairs())) == [0, 1, 2, 3]
    with pytest.raises(ValueError, match='pair'):
        TaskControlSampler(rows(), [])


def test_count_ce_means_each_present_class_and_masks_missing_labels():
    from egrs.task_control.training import count_weights, count_loss
    logits = torch.tensor([[2., 0., 0.], [0., 1., 0.], [0., 0., 3.], [9., 0., 0.]], requires_grad=True)
    labels = [0, 0, 2, None]
    scales = count_weights(labels)
    assert scales == [.25, .25, .5, 0.]
    loss = count_loss(logits, labels)
    ce = torch.nn.functional.cross_entropy(logits[:3], torch.tensor([0, 0, 2]), reduction='none')
    assert torch.allclose(loss, .25 * ce[0] + .25 * ce[1] + .5 * ce[2])
    loss.backward()
    assert not logits.grad[3].any()


def test_swap_changes_only_z_uses_each_target_and_backpropagates_both_sides():
    from egrs.task_control.training import pair_losses, total_loss
    u = SimpleNamespace(h=torch.full((1, 8, 7), 1.), z=torch.tensor([[1., 2.]], requires_grad=True),
                        proprio=torch.tensor([[3.]]), actions=torch.full((1, 8, 7), 8.))
    v = SimpleNamespace(h=torch.full((1, 8, 7), 10.), z=torch.tensor([[4., 1.]], requires_grad=True),
                        proprio=torch.tensor([[5.]]), actions=torch.full((1, 8, 7), 20.))
    calls = []
    def decode(policy, encoded, z=None):
        calls.append((encoded.h, encoded.proprio, z))
        return encoded.h + encoded.proprio.reshape(1, 1, 1) + z.sum().reshape(1, 1, 1)
    a = {'actions': np.full((8, 7), 2.), 'action_mask': [True] + [False] * 7}
    b = {'actions': np.full((8, 7), 30.), 'action_mask': [True] * 8}
    losses = pair_losses(None, u, v, a, b, arm='c1', decode=decode)
    assert losses['self'].item() == 8.
    # u receives z_v: 1+3+5 vs own target2; v receives z_u: 10+5+3 vs own target30.
    assert losses['swap'].item() == 9.5
    assert calls[0] == (u.h, u.proprio, v.z)
    assert calls[1] == (v.h, v.proprio, u.z)
    expected_align = ((torch.nn.functional.normalize(u.z, dim=-1, eps=1e-6)
                       - torch.nn.functional.normalize(v.z, dim=-1, eps=1e-6)) ** 2).mean()
    assert torch.allclose(losses['align'], expected_align)
    loss = total_loss(torch.tensor(2.), torch.tensor(3.), losses, arm='c1')
    assert torch.allclose(loss, 2. + .3 + .05 * losses['self'] + .05 * losses['swap'] + .01 * expected_align)
    loss.backward()
    assert u.z.grad.abs().sum() > 0 and v.z.grad.abs().sum() > 0
    assert total_loss(torch.tensor(2.), torch.tensor(3.), losses, arm='c0').item() == pytest.approx(3.1)


def test_public_preset_rejects_shortened_or_extended_budget():
    from egrs.task_control.training import PRESET, validate_config
    validate_config(deepcopy(PRESET))
    for key, value in [('updates', 1), ('updates', 1001), ('seed', 8), ('save_every', 100), ('learning_rate', 1e-4)]:
        with pytest.raises(ValueError, match='preset'):
            validate_config(dict(PRESET, **{key: value}))


class TinyDataset:
    def __init__(self, split='train'):
        self.rows = rows()
        self.pairs = pairs()
        self.identity = 'f' * 64
        self.report = {'data_kind': 'task038-task-control-data-v1'}
        self.validation = []
    def __getitem__(self, index):
        row = self.rows[index]
        item = {'images': [np.zeros((2, 2, 3), dtype=np.uint8)] * 2,
                'proprio': np.arange(8, dtype=np.float32) / 8 + index / 100,
                'instruction': 'original complete instruction',
                'count_label': None if row['pool'] == 'raw' else index % 3}
        if row['pool'] == 'ten':
            item.update(actions=np.zeros((8, 7), dtype=np.float32), action_mask=row['action_mask'])
        return item
    def get_pair(self, index):
        u, v = self[index], self[index + 4]
        for offset, item in enumerate((u, v)):
            item.update(actions=np.full((8, 7), offset + index / 10, dtype=np.float32),
                        action_mask=[True] * (8 - offset) + [False] * offset)
        return u, v
    def validate_normalization(self, *args):
        self.validation.append(args)


def tiny_policy():
    from test_augmentation_training import policy
    from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
    p = policy()
    p.model.llm_dim = 3
    p.model.language_model.config = SimpleNamespace(hidden_size=3, use_cache=True)
    p.model.language_model.gradient_checkpointing = False
    def enable(**kwargs):
        p.model.language_model.gradient_checkpointing = True
    p.model.language_model.gradient_checkpointing_enable = enable
    class Head(nn.Linear):
        def predict_action(self, h):
            return self(h.float()).mean(1).reshape(1, 1, 1).expand(1, 8, 7)
    p.action_head = Head(3, 1)
    p.metadata['dataset_statistics_sha256'] = RETENTION_STATS_SHA
    p.cfg = SimpleNamespace(unnorm_key='libero_10_no_noops')
    p.model.norm_stats = {'synthetic': 'already validated boundary'}
    return p


def tiny_prediction(policy, item):
    from egrs.task_control.oft import Prediction, decode
    assert set(item) == {'images', 'proprio', 'instruction'}
    x = torch.as_tensor(item['proprio'][:3]).reshape(1, 3)
    h = policy.model(x).reshape(1, 1, 3).expand(1, 56, 3)
    p = torch.as_tensor(item['proprio']).reshape(1, 8)
    context = policy.model.task_control
    z = context.encode_context(h[:, :2], h[:, 2:4])
    result = Prediction(None, h, z, p, context.count_head(z))
    result.actions = decode(policy, result)
    return result


def tiny_reference(policy, item):
    assert set(item) == {'images', 'proprio', 'instruction'}
    x = torch.as_tensor(item['proprio'][:3]).reshape(1, 3)
    h = policy.model(x).reshape(1, 1, 3).expand(1, 56, 3)
    return policy.action_head.predict_action(h)


def test_tiny_loop_reference_first_22_student_calls_and_strict_checkpoint(tmp_path):
    from egrs.task_control import training
    from egrs.task_control.adapter import read_adapter_identity
    p = tiny_policy()
    events = []
    def student(policy, item):
        events.append(('student', policy.model.task_control.enabled))
        return tiny_prediction(policy, item)
    def reference(policy, item):
        events.append(('reference', policy.model.task_control.enabled))
        return tiny_reference(policy, item)
    config = dict(training.PRESET, updates=1, save_every=1)
    args = SimpleNamespace(output_dir=tmp_path / 'run', resume=None, arm='c1')
    train, dev = TinyDataset(), TinyDataset('dev')
    result = training._run_loaded(args, config, train, dev, p, predict=student, reference_predict=reference)
    assert events[:8] == [('reference', False)] * 8
    assert events[8:30] == [('student', True)] * 22
    assert result['student_calls']['train'] == 22 and result['reference_calls']['train'] == 8
    assert train.validation and dev.validation
    identity = read_adapter_identity(tmp_path / 'run/update-000001')
    assert identity['arm'] == 'c1' and identity['reference_calls']['train'] == 8
    assert identity['final_update'] == 1000
    assert all(v.grad is None for v in p.action_head.parameters())
    assert any(v.grad is not None for n, v in p.model.named_parameters() if n.endswith('lora_B'))
    assert (tmp_path / 'run/update-000001/training_state.pt').exists()


def test_checkpoint_resume_preserves_exact_draws_optimizer_rng_and_spent_budget(tmp_path, monkeypatch):
    from egrs.task_control import training, checkpoint
    config = dict(training.PRESET, updates=2, save_every=1)
    original = checkpoint.save_training_state
    def interrupt_after_first(*args, **kwargs):
        value = original(*args, **kwargs)
        if kwargs['update'] == 1:
            raise RuntimeError('synthetic interruption')
        return value
    source = tiny_policy()
    args = SimpleNamespace(output_dir=tmp_path / 'run', resume=None, arm='c0')
    monkeypatch.setattr(checkpoint, 'save_training_state', interrupt_after_first)
    with pytest.raises(RuntimeError, match='synthetic interruption'):
        training._run_loaded(args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                             predict=tiny_prediction, reference_predict=tiny_reference)
    monkeypatch.setattr(checkpoint, 'save_training_state', original)
    args.resume = tmp_path / 'run/update-000001'
    result = training._run_loaded(args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                                  predict=tiny_prediction, reference_predict=tiny_reference)
    assert result['update'] == 2
    assert result['reference_calls']['train'] == 16 and result['student_calls']['train'] == 44
    state = torch.load(tmp_path / 'run/update-000002/training_state.pt', weights_only=False)
    assert state['sampler']['pair']['draws'] == 2
    assert state['sampler']['main']['counts'] == {'ten': 24, 'fresh': 8, 'raw': 8}
    assert state['optimizer']['state'] and state['scheduler']['last_epoch'] == 2
    uninterrupted_args = SimpleNamespace(output_dir=tmp_path / 'whole', resume=None, arm='c0')
    training._run_loaded(uninterrupted_args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                         predict=tiny_prediction, reference_predict=tiny_reference)
    whole = torch.load(tmp_path / 'whole/update-000002/adapter.pt', weights_only=True)
    resumed = torch.load(tmp_path / 'run/update-000002/adapter.pt', weights_only=True)
    assert all(torch.equal(whole[key], resumed[key]) for key in whole)
    args.arm = 'c1'
    with pytest.raises(ValueError, match='arm'):
        training._run_loaded(args, config, TinyDataset(), TinyDataset(), tiny_policy(),
                             predict=tiny_prediction, reference_predict=tiny_reference)


def test_c0_c1_actual_loop_loads_identical_observations_and_no_extra_backbone(tmp_path):
    from egrs.task_control import training
    source = tiny_policy()
    sequences = []
    for arm in ('c0', 'c1'):
        calls = []
        def predict(policy, item):
            calls.append(float(item['proprio'][0]))
            return tiny_prediction(policy, item)
        args = SimpleNamespace(output_dir=tmp_path / arm, resume=None, arm=arm)
        training._run_loaded(args, dict(training.PRESET, updates=1, save_every=1),
            TinyDataset(), TinyDataset(), deepcopy(source), predict=predict, reference_predict=tiny_reference)
        sequences.append(calls)
    assert sequences[0] == sequences[1]
    assert len(sequences[0]) == 62  # train22 + dev32 ordinary + four pairs*2


def test_dev_zero_pairs_remains_available_and_reports_missing_diagnostics(tmp_path):
    from egrs.task_control import training
    dev = TinyDataset()
    dev.pairs = []
    args = SimpleNamespace(output_dir=tmp_path / 'run', resume=None, arm='c0')
    training._run_loaded(args, dict(training.PRESET, updates=1, save_every=1),
        TinyDataset(), dev, tiny_policy(), predict=tiny_prediction, reference_predict=tiny_reference)
    import json
    metrics = json.loads((tmp_path / 'run/metrics.jsonl').read_text().splitlines()[-1])
    assert metrics['dev']['pair_count'] == 0
    assert metrics['dev']['paired_diagnostics']['swap'] is None


def test_training_checkpoint_rejects_corruption_and_advanced_durable_ledger(tmp_path):
    from egrs.task_control import training
    import json
    source = tiny_policy()
    args = SimpleNamespace(output_dir=tmp_path / 'run', resume=None, arm='c0')
    config = dict(training.PRESET, updates=1, save_every=1)
    training._run_loaded(args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                         predict=tiny_prediction, reference_predict=tiny_reference)
    args.resume = tmp_path / 'run/update-000001'
    path = args.resume / 'training_state.pt'
    saved = path.read_bytes()
    path.write_bytes(saved + b'corrupt')
    with pytest.raises(ValueError, match='hash'):
        training._run_loaded(args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                             predict=tiny_prediction, reference_predict=tiny_reference)
    path.write_bytes(saved)
    ledger = tmp_path / 'run/reference_budget.json'
    counts = json.loads(ledger.read_text())
    counts['train'] += 1
    counts['total'] += 1
    ledger.write_text(json.dumps(counts))
    with pytest.raises(ValueError, match='older than spent'):
        training._run_loaded(args, config, TinyDataset(), TinyDataset(), deepcopy(source),
                             predict=tiny_prediction, reference_predict=tiny_reference)


def test_synthetic_recorded_index_connects_to_training_without_pair_target_relabeling(control_sources, tmp_path):
    from egrs.task_control import index, data, training
    from egrs.task_control.adapter import read_adapter_identity
    from egrs.retention.data import STATS_KEY
    export, retention = control_sources
    index.build_index(export, retention, tmp_path / 'control')
    train = data.TaskControlDataset(tmp_path / 'control', 'train')
    dev = data.TaskControlDataset(tmp_path / 'control', 'dev')
    mapping = next(iter(train.manifest['qualified_sources'].values()))['mapping']
    p = tiny_policy()
    p.model.norm_stats = {STATS_KEY: {kind: {key: mapping[kind + '_normalization'][key]
        for key in ('q01', 'q99', 'mask')} for kind in ('action', 'proprio')}}
    u, v = train.get_pair(0)
    assert u['actions'][0, 0] != v['actions'][0, 0]
    args = SimpleNamespace(output_dir=tmp_path / 'run', resume=None, arm='c1')
    result = training._run_loaded(args, dict(training.PRESET, updates=1, save_every=1), train, dev, p,
                                 predict=tiny_prediction, reference_predict=tiny_reference)
    identity = read_adapter_identity(result['selected_checkpoint'])
    assert identity['index_identity'] == train.identity
    assert result['student_calls']['train'] == 22 and result['reference_calls']['train'] == 8
