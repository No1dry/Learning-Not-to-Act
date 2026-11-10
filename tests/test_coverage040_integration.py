"""Executed fake039 controls -> actual040 export/index -> unchanged038 C1 CPU."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import torch

from test_retention_data import prepared
from test_task_control_index import control_sources
from test_coverage039_data import coverage_inputs
from test_coverage040_data import delta_inputs, build
from test_task_control_training import tiny_policy, tiny_prediction, tiny_reference


def test_recorded040_pair_only_normal_c1_resume_and_adapter_contract(delta_inputs, tmp_path, monkeypatch):
    from egrs.augmentation.data import identity, read_json
    from egrs.coverage039.io import HashContext
    from egrs.coverage039.recipe import generation_context
    from egrs.coverage040.generation import _binding, _bind_attempt, durable_write
    from egrs.coverage040.data import CoverageTaskControlDataset
    from egrs.trajectory_augmentation.data import export_generated
    from egrs.trajectory_augmentation.native import TEACHER_V2
    from egrs.task_control import training, checkpoint
    from egrs.task_control.adapter import read_adapter_identity
    from egrs.task_control.evaluation import validate_adapter
    old_index, fixture_delta, old_manifest, old_report = delta_inputs
    previous = read_json(fixture_delta/'sources.json')
    fixture_binding = previous['generation_context']['coverage040']
    plan = read_json(fixture_binding['plan_path'])
    plan.update(tasks=['stove', 'mug_pudding', 'two_pots'], source_range={'start': 20, 'stop': 40})
    plan['identity'] = identity(plan)
    parent = plan['sources'][0]
    normal = next(s for s in previous['sources'].values() if s['domain'] == 'normal')
    layout = read_json(fixture_delta.parent/normal['lineage_path'])['native']['joint_layout']
    root = tmp_path/'executed040'; root.mkdir()
    config = {'teacher_policy': TEACHER_V2, 'recipe': {'horizon': 30, 'bridge_stage_steps': 2},
              'save_video': False, '_plan_identity': plan['identity'],
              '_budget_ledger': str(root/'attempt_ledger.json'),
              'stats_sha256': parent['mapping']['action_normalization']['stats_sha256'],
              'unnorm_key': 'libero_10_no_noops'}
    request = tmp_path/'recording-request.json'; response = tmp_path/'recording-response.json'
    request.write_text(json.dumps({'parent': parent, 'layout': layout, 'config': config,
                                   'root': str(root), 'result': str(response)}), encoding='utf-8')
    # NumPy-only fake world, no NativeSession, MuJoCo or real teacher/model.
    subprocess.run([sys.executable, str(Path(__file__).with_name('coverage039_recorded_worker.py')), str(request)],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True, text=True)
    recorded = read_json(response)
    assert len(recorded['attempts']) == 4 and all(a['qualified'] for a in recorded['attempts'])
    durable_write(root/'generation_plan.json', plan)
    context = HashContext(); binding = _binding(plan, root, context)
    attempts = [_bind_attempt(a, root, binding) for a in recorded['attempts']]
    declared = generation_context(plan['identity'], normal_attempts=1, ten_attempts=3)
    declared['coverage040'] = binding
    export_generated(plan['parents'], attempts, root, root/'export', generation_context=declared, context=context)
    result = build((old_index, root/'export', old_manifest, old_report), tmp_path, monkeypatch)
    train = CoverageTaskControlDataset(result['task_control'], 'train', context=context)
    dev = CoverageTaskControlDataset(result['task_control'], 'dev', context=context)
    assert train.identity == dev.identity != old_manifest['identity']
    assert train.report['coverage040']['new_qualified_train10'] == 3
    assert not set(train.manifest['pair_sources']) & {r['source_id'] for r in train.rows}
    assert len(train.pairs) == 4 and len(dev.pairs) == 1
    # Keep the genuine seed7 sampler and verify that it actually draws a new pair.
    pair_items = []
    original_get_pair = train.get_pair
    def get_pair(i):
        pair_items.append(i)
        return original_get_pair(i)
    train.get_pair = get_pair
    policy = tiny_policy(); mapping = parent['mapping']
    policy.model.norm_stats = {'libero_10_no_noops': {kind: {key: mapping[kind+'_normalization'][key]
        for key in ('q01', 'q99', 'mask')} for kind in ('action', 'proprio')}}
    cfg = dict(training.PRESET, updates=2, save_every=1)  # private CPU test only, public preset stays1000
    args = SimpleNamespace(arm='c1', output_dir=tmp_path/'resumed', resume=None)
    original_save = checkpoint.save_training_state
    def interrupt(*a, **kw):
        value = original_save(*a, **kw)
        if kw['update'] == 1:
            raise RuntimeError('synthetic stop after durable checkpoint')
        return value
    monkeypatch.setattr(checkpoint, 'save_training_state', interrupt)
    with pytest.raises(RuntimeError, match='synthetic stop'):
        training._run_loaded(args, cfg, train, dev, deepcopy(policy), predict=tiny_prediction,
                             reference_predict=tiny_reference, compact_logging=True)
    monkeypatch.setattr(checkpoint, 'save_training_state', original_save)
    args.resume = tmp_path/'resumed/update-000001'
    resumed = training._run_loaded(args, cfg, train, dev, deepcopy(policy), predict=tiny_prediction,
                                   reference_predict=tiny_reference, compact_logging=True)
    assert resumed['student_calls']['train'] == 44 and resumed['reference_calls']['train'] == 16
    assert len(pair_items) == 2 and any(i > 0 for i in pair_items)
    saved = read_adapter_identity(tmp_path/'resumed/update-000002')
    assert saved['arm'] == 'c1' and saved['index_identity'] == train.identity
    saved_state = torch.load(tmp_path/'resumed/update-000002/training_state.pt', weights_only=False)
    assert saved_state['student_budget']['train'] == 44 and saved['reference_calls']['train'] == 16
    # Reloaded full C1 modules/optimizer/sampler must give the identical continuation.
    args = SimpleNamespace(arm='c1', output_dir=tmp_path/'whole', resume=None)
    training._run_loaded(args, cfg, train, dev, deepcopy(policy), predict=tiny_prediction,
                         reference_predict=tiny_reference, compact_logging=True)
    assert pair_items[:2] == pair_items[2:]
    whole = torch.load(tmp_path/'whole/update-000002/adapter.pt', weights_only=True)
    reloaded = torch.load(tmp_path/'resumed/update-000002/adapter.pt', weights_only=True)
    assert set(whole) == set(reloaded) and all(torch.equal(whole[k], reloaded[k]) for k in whole)
    with pytest.raises(ValueError, match='1000'):
        validate_adapter(saved)  # never admit this intentionally shortened checkpoint to real eval
