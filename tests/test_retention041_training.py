"""Matched041 stages over real tiny torch graphs, never a pretrained model."""
from copy import deepcopy
import json
import shutil
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch.utils.checkpoint import checkpoint as torch_checkpoint

from test_task_control_training import TinyDataset, tiny_policy, tiny_reference


def sources(tmp_path, monkeypatch):
    from egrs.task_control.oft import install
    from egrs.task_control.adapter import save_adapter
    from egrs.retention041 import adapter
    base = tiny_policy(); policy = deepcopy(base); install(policy)
    initial = tmp_path/'initial040'; teacher = tmp_path/'teacher039'
    calls = {'train': 8000, 'dev': 0, 'total': 8000, 'budget': 9024}
    with torch.no_grad():
        for name, p in policy.model.named_parameters():
            if name.startswith('task_control.') or name.endswith(('.lora_A', '.lora_B')):
                p.fill_(.02)
    init = save_adapter(policy, initial, arm='c1', update=1000, index_identity=adapter.INDEX_IDENTITY,
                        reference_calls=calls)
    with torch.no_grad():
        for name, p in policy.model.named_parameters():
            if name.startswith('task_control.') or name.endswith(('.lora_A', '.lora_B')):
                p.fill_(.07)
    old = save_adapter(policy, teacher, arm='c1', update=1000, index_identity=adapter.TEACHER_INDEX_IDENTITY,
                       reference_calls=calls)
    monkeypatch.setattr(adapter, 'INITIALIZATION_SHA256', init['adapter_sha256'])
    monkeypatch.setattr(adapter, 'TEACHER_SHA256', old['adapter_sha256'])
    return base, initial, teacher


class Dataset(TinyDataset):
    def __init__(self, split='train', *, eligible=True):
        from egrs.retention041.adapter import INDEX_IDENTITY
        super().__init__(split)
        self.identity = INDEX_IDENTITY
        for row in self.rows:
            row.update(source_id=row['pool']+'|old003|'+row['task_key'], split=split)
        self.old10_source_ids = {r['source_id'] for r in self.rows if r['pool']=='ten'} if eligible else set()


def predict(policy, item, *, modules=None):
    from egrs.task_control.oft import Prediction, decode
    assert set(item) == {'images', 'proprio', 'instruction'}
    x = torch.as_tensor(item['proprio'][:3]).reshape(1, 3)
    if torch.is_grad_enabled() and policy.model.language_model.gradient_checkpointing:
        hidden = torch_checkpoint(policy.model, x, use_reentrant=False)
    else:
        hidden = policy.model(x)
    h = hidden.reshape(1, 1, 3).expand(1, 56, 3)
    context = policy.model.task_control if modules is None else modules
    z = context.encode_context(h[:, :2], h[:, 2:4])
    encoded = Prediction(None, h, z, torch.as_tensor(item['proprio']).reshape(1, 8), context.count_head(z))
    encoded.actions = decode(policy, encoded, modules=context)
    return encoded


def config(initial, teacher, experiment_arm, *, updates=1):
    from egrs.task_control.training import PRESET
    return {'experiment_arm': experiment_arm, 'initial_adapter': str(initial),
            'teacher_adapter': str(teacher) if experiment_arm=='r1' else None,
            'training_recipe': dict(PRESET, updates=updates, save_every=1)}


def test_masked_old10_loss_has_exact_valid_scalar_mean_and_detached_teacher():
    from egrs.retention041.training import masked_old10_l1
    student = torch.arange(56, dtype=torch.float32).reshape(1, 8, 7).requires_grad_()
    teacher = torch.zeros_like(student, requires_grad=True)
    loss = masked_old10_l1(student, teacher, [True, False, False, False, False, False, False, False])
    assert loss.item() == 3.
    loss.backward()
    assert teacher.grad is None
    assert torch.allclose(student.grad[0, 0, 1:], torch.full((6,), 1/7))
    assert not student.grad[:, 1:].any()
    with pytest.raises(ValueError, match='mask|valid'):
        masked_old10_l1(student, teacher, [False]*8)


def test_two_arms_keep_same_batches_references_first22_student_and_c1_losses(tmp_path, monkeypatch):
    from egrs.retention041 import training, adapter
    base, initial, teacher = sources(tmp_path, monkeypatch)
    traces = []; states = []; metrics = []
    for arm in ('r0', 'r1'):
        events = []
        def student(policy, item):
            events.append(('student', tuple(item['proprio'])))
            return predict(policy, item)
        def reference(policy, item):
            events.append(('base', tuple(item['proprio'])))
            return tiny_reference(policy, item)
        def old(policy, item, *, modules):
            events.append(('old10', tuple(item['proprio'])))
            return predict(policy, item, modules=modules)
        train, dev = Dataset(), Dataset('dev')
        result = training._run_loaded(SimpleNamespace(output_dir=tmp_path/arm, resume=None),
            config(initial, teacher, arm), train, dev, deepcopy(base),
            predict=student, reference_predict=reference, teacher_predict=old)
        assert result['update'] == 1
        assert result['reference_calls']['train'] == 8 and result['student_calls']['train'] == 22
        assert result['old10_calls']['train'] == (4 if arm=='r1' else 0)
        assert json.loads((tmp_path/arm/'old10_budget.json').read_text()) == result['old10_calls']
        first_student = next(i for i, e in enumerate(events) if e[0]=='student')
        assert first_student == (12 if arm=='r1' else 8)
        assert all(e[0] != 'student' for e in events[:first_student])
        assert [e[0] for e in events[first_student:first_student+22]] == ['student']*22
        traces.append([e for e in events if e[0]=='student'])
        saved = adapter.read_adapter_identity(tmp_path/arm/'update-000001')
        assert saved['arm'] == 'c1' and saved['experiment_arm'] == arm
        assert saved['index_identity'] == train.identity
        metrics.append(json.loads((tmp_path/arm/'metrics.jsonl').read_text().splitlines()[0]))
        states.append(saved)
    assert traces[0] == traces[1]
    assert states[0]['stage_identity']['initialization_identity'] == states[1]['stage_identity']['initialization_identity']
    for key in ('weighted_l1', 'pool_l1', 'count', 'self', 'swap', 'align'):
        assert metrics[0][key] == metrics[1][key]
    assert metrics[0]['old10_loss'] == 0 and metrics[1]['old10_loss'] > 0


def test_zero_selected_old10_makes_r1_exact_r0_without_teacher_calls(tmp_path, monkeypatch):
    from egrs.retention041 import training
    base, initial, teacher = sources(tmp_path, monkeypatch)
    states = []
    for arm in ('r0', 'r1'):
        result = training._run_loaded(SimpleNamespace(output_dir=tmp_path/arm, resume=None),
            config(initial, teacher, arm), Dataset(eligible=False), Dataset('dev', eligible=False), deepcopy(base),
            predict=predict, reference_predict=tiny_reference,
            teacher_predict=lambda *args, **kw: pytest.fail('zero selected must not run old039'))
        assert result['old10_calls']['total'] == 0
        # New041 payload reader chooses its explicit nested/common path.
        from egrs.retention041.adapter import read_adapter_identity
        saved = read_adapter_identity(tmp_path/arm/'update-000001')
        states.append(saved['student_identity']['tensor_sha256'])
    assert states[0] == states[1]


def test_less_than_four_averages_actual_count_and_does_not_replace_bc(tmp_path, monkeypatch):
    from egrs.retention041 import training
    base, initial, teacher = sources(tmp_path, monkeypatch)
    monkeypatch.setattr(training, 'select_old10_positions', lambda *a, **kw: ([0, 1], 2))
    targets = []; predictions = []
    def old(policy, item, *, modules):
        result = predict(policy, item, modules=modules)
        targets.append(result.actions.detach().clone())
        return result
    def student(policy, item):
        result = predict(policy, item)
        predictions.append(result.actions.detach().clone())
        return result
    train = Dataset()
    sampler = training.TaskControlSampler(train.rows, train.pairs, seed=7)
    indices, _ = sampler.draw_batch()
    training._run_loaded(SimpleNamespace(output_dir=tmp_path/'r1', resume=None), config(initial, teacher, 'r1'),
        train, Dataset('dev'), deepcopy(base), predict=student, teacher_predict=old, reference_predict=tiny_reference)
    expected = sum(training.masked_old10_l1(predictions[i], targets[i], train[indices[i]]['action_mask']).item()
                   for i in range(2))/2
    metrics = json.loads((tmp_path/'r1/metrics.jsonl').read_text().splitlines()[0])
    assert metrics['old10_selected'] == 2 and metrics['old10_loss'] == pytest.approx(expected)
    assert metrics['old10_weighted_loss'] == pytest.approx(.10*expected)
    assert metrics['student_calls']['train'] == 22 and metrics['old10_calls']['train'] == 2


def test_r1_interrupted_continuation_restores_all_three_budgets_and_tensors(tmp_path, monkeypatch):
    from egrs.retention041 import training, checkpoint, adapter
    base, initial, teacher = sources(tmp_path, monkeypatch)
    cfg = config(initial, teacher, 'r1', updates=2)
    args = SimpleNamespace(output_dir=tmp_path/'resumed', resume=None)
    save = checkpoint.save_training_state
    def stop(*a, **kw):
        result = save(*a, **kw)
        if kw['update'] == 1:
            raise RuntimeError('synthetic interruption after complete checkpoint')
        return result
    monkeypatch.setattr(checkpoint, 'save_training_state', stop)
    with pytest.raises(RuntimeError, match='synthetic interruption'):
        training._run_loaded(args, cfg, Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
                             reference_predict=tiny_reference, teacher_predict=predict)
    monkeypatch.setattr(checkpoint, 'save_training_state', save)
    args.resume = tmp_path/'resumed/update-000001'
    resumed = training._run_loaded(args, cfg, Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
                                  reference_predict=tiny_reference, teacher_predict=predict)
    assert resumed['reference_calls']['train'] == 16
    assert resumed['student_calls']['train'] == 44 and resumed['old10_calls']['train'] == 8
    training._run_loaded(SimpleNamespace(output_dir=tmp_path/'whole', resume=None), cfg,
        Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
        reference_predict=tiny_reference, teacher_predict=predict)
    a = adapter.read_adapter_identity(tmp_path/'resumed/update-000002')
    b = adapter.read_adapter_identity(tmp_path/'whole/update-000002')
    assert a['student_identity']['tensor_sha256'] == b['student_identity']['tensor_sha256']
    for name in ('reference_calls', 'student_calls', 'old10_calls'):
        assert a[name] == b[name]
    with pytest.raises(ValueError, match='complete'):
        training._run_loaded(SimpleNamespace(output_dir=tmp_path/'whole', resume=tmp_path/'whole/update-000002'), cfg,
            Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
            reference_predict=tiny_reference, teacher_predict=predict)


def test_copied_checkpoint_cannot_redirect_same_stage_to_another_run(tmp_path, monkeypatch):
    from egrs.retention041 import training, checkpoint
    base, initial, teacher = sources(tmp_path, monkeypatch)
    cfg = config(initial, teacher, 'r1', updates=2)
    save = checkpoint.save_training_state
    def stop(*a, **kw):
        result = save(*a, **kw)
        raise RuntimeError('synthetic stop')
    monkeypatch.setattr(checkpoint, 'save_training_state', stop)
    with pytest.raises(RuntimeError, match='synthetic stop'):
        training._run_loaded(SimpleNamespace(output_dir=tmp_path/'original', resume=None), cfg,
            Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
            reference_predict=tiny_reference, teacher_predict=predict)
    monkeypatch.setattr(checkpoint, 'save_training_state', save)
    shutil.copytree(tmp_path/'original', tmp_path/'copied')
    with pytest.raises(ValueError, match='configuration|config|run'):
        training._run_loaded(SimpleNamespace(output_dir=tmp_path/'copied', resume=tmp_path/'copied/update-000001'), cfg,
            Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
            reference_predict=tiny_reference, teacher_predict=predict)


def test_teacher_failure_spends_before_forward_without_student_or_refund(tmp_path, monkeypatch):
    from egrs.retention041 import training
    base, initial, teacher = sources(tmp_path, monkeypatch)
    out = tmp_path/'failed-r1'
    def failure(*a, **kw): raise RuntimeError('synthetic teacher forward failure')
    with pytest.raises(RuntimeError, match='synthetic teacher'):
        training._run_loaded(SimpleNamespace(output_dir=out, resume=None), config(initial, teacher, 'r1'),
            Dataset(), Dataset('dev'), deepcopy(base), predict=predict,
            reference_predict=tiny_reference, teacher_predict=failure)
    assert json.loads((out/'reference_budget.json').read_text())['train'] == 8
    assert json.loads((out/'old10_budget.json').read_text())['train'] == 1
    assert json.loads((out/'student_budget.json').read_text())['train'] == 0
    with pytest.raises(FileExistsError):
        training._run_loaded(SimpleNamespace(output_dir=out, resume=None), config(initial, teacher, 'r1'),
            Dataset(), Dataset('dev'), deepcopy(base), predict=predict, reference_predict=tiny_reference)
