"""041 config/source queues use only metadata and synthetic recorded fixtures."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import random

import numpy as np
import pytest
import torch

from egrs.task_control.training import PRESET
from test_retention_data import prepared
from test_task_control_index import control_sources
from test_coverage039_data import coverage_inputs
from test_coverage040_data import delta_inputs, build, selected_keys


def module(name):
    try:
        return importlib.import_module('egrs.retention041.' + name)
    except ModuleNotFoundError as exc:
        if exc.name in ('egrs.retention041', 'egrs.retention041.' + name):
            pytest.fail('041 ' + name + ' API is not implemented')
        raise


def config(arm='r0'):
    return {'format': 'task041-old10-retention-training-v1', 'experiment_arm': arm,
            'training_recipe': deepcopy(PRESET), 'index_dir': './index',
            'initial_adapter': './040', 'teacher_adapter': './039' if arm == 'r1' else None,
            'benchmark_root': './benchmark', 'runtime': './runtime.json'}


def write_config(tmp_path, value):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.mark.parametrize('arm', ['r0', 'r1'])
def test_config_has_explicit_arm_original_preset_and_resolved_inputs(tmp_path, arm):
    cfg = module('config').load_config(write_config(tmp_path, config(arm)))
    assert cfg['experiment_arm'] == arm
    assert cfg['training_recipe'] == PRESET
    for key in ('index_dir', 'initial_adapter', 'benchmark_root', 'runtime'):
        assert Path(cfg[key]).is_absolute()
    assert cfg['index_dir'] == str((tmp_path / 'index').resolve())
    assert cfg['teacher_adapter'] == (str((tmp_path / '039').resolve()) if arm == 'r1' else None)


def test_config_expands_both_environment_syntaxes_and_home(tmp_path, monkeypatch):
    monkeypatch.setenv('T41_INPUT', str(tmp_path / 'inputs'))
    cfg = config('r1')
    cfg.update(index_dir='${T41_INPUT}/index', initial_adapter='$T41_INPUT/040',
               teacher_adapter='%T41_INPUT%/039', benchmark_root='~/benchmark')
    result = module('config').load_config(write_config(tmp_path, cfg))
    assert result['index_dir'] == str((tmp_path / 'inputs/index').resolve())
    assert result['teacher_adapter'] == str((tmp_path / 'inputs/039').resolve())
    assert result['benchmark_root'] == str((Path.home() / 'benchmark').resolve())


@pytest.mark.parametrize('change', [
    lambda c: c.update(extra=1), lambda c: c.pop('runtime'),
    lambda c: c.update(format='task040-training-v1'), lambda c: c.update(experiment_arm='c1'),
    lambda c: c['training_recipe'].update(updates=999),
    lambda c: c['training_recipe'].update(seed=True),
    lambda c: c['training_recipe'].update(updates=1000.0),
    lambda c: c.update(teacher_adapter='./039'),
    lambda c: c.update(index_dir='$T41_UNDEFINED/index'),
    lambda c: c.update(runtime='%T41_UNDEFINED%/runtime.json'),
    lambda c: c.update(initial_adapter='<fixed040>'), lambda c: c.update(benchmark_root=''),
    lambda c: c.update(runtime={}),
])
def test_config_rejects_stage_drift_and_unresolved_inputs(tmp_path, monkeypatch, change):
    monkeypatch.delenv('T41_UNDEFINED', raising=False)
    cfg = config(); change(cfg)
    with pytest.raises(ValueError):
        module('config').load_config(write_config(tmp_path, cfg))


def test_r1_requires_teacher_and_duplicate_fields_are_rejected(tmp_path):
    cfg = config('r1'); cfg['teacher_adapter'] = None
    with pytest.raises(ValueError, match='teacher'):
        module('config').load_config(write_config(tmp_path, cfg))
    path = tmp_path / 'duplicate.json'
    path.write_text('{"format":"one","format":"two"}', encoding='utf-8')
    with pytest.raises(ValueError, match='duplicate'):
        module('config').load_config(path)


def source_fixture():
    qualified = {}; sources = {}; new = {}
    for name, release, split, task in [
        ('old', 'old003', 'train', 'basket'), ('dev', 'old003', 'dev', 'basket'),
        ('new039', 'new039', 'train', 'basket'), ('other', 'old003', 'train', 'stove')]:
        original = {'source_id': name, 'domain': '10', 'parent_demo_id': name + '-parent',
                    'source_group': name + '-group', 'split': split, 'task_key': task,
                    'file': name + '.hdf5', 'file_sha256': 'a' * 64, 'variant': 0}
        gid = release + '|' + name
        record = {**deepcopy(original), 'source_id': gid, 'file': release + '/' + original['file'],
                  'coverage039_origin': {'release': release, 'source_id': name,
                                         'original_source': deepcopy(original)}}
        qualified[gid] = record
        sid = 'ten|' + gid
        sources[sid] = {**deepcopy(record), 'source_id': sid, 'pool': 'ten',
                        'original_source': deepcopy(record)}
    record = {'source_id': 'added040', 'domain': '10', 'parent_demo_id': 'new-parent',
              'source_group': 'new-group', 'split': 'train', 'task_key': 'basket',
              'file': 'new040.hdf5', 'file_sha256': 'b' * 64, 'variant': 0}
    sid = 'ten|new040|added040'; new[sid] = record
    sources[sid] = {**deepcopy(record), 'source_id': sid, 'pool': 'ten',
                    'original_source': deepcopy(record)}
    sources['raw'] = {'source_id': 'raw', 'pool': 'raw'}
    sources['fresh'] = {'source_id': 'fresh', 'pool': 'fresh'}
    return {'qualified_sources': qualified, 'new_sources': new, 'pair_sources': {}}, sources


def test_old_queue_requires_explicit_old003_chain_and_excludes_new_and_dev():
    manifest, sources = source_fixture()
    assert module('data').old10_source_ids(manifest, sources) == {'ten|old003|old'}


@pytest.mark.parametrize('task', ['basket', 'basket_cheese_butter', 'bowl_drawer_close',
                                 'dual_mugs', 'basket_soup_cheese', 'mug_microwave_close'])
def test_all_six_historical_tasks_use_evidence_instead_of_task_or_path_guess(task):
    manifest, sources = source_fixture()
    retained = sources['ten|old003|old']; qualified = retained['original_source']
    retained['task_key'] = qualified['task_key'] = qualified['coverage039_origin']['original_source']['task_key'] = task
    # The qualified map remains the exact same evidence rather than a task-only lookup.
    manifest['qualified_sources'][qualified['source_id']] = deepcopy(qualified)
    assert module('data').old10_source_ids(manifest, sources) == {'ten|old003|old'}


@pytest.mark.parametrize('field,value', [('split','dev'), ('source_group','wrong'),
                                       ('parent_demo_id','wrong'), ('file_sha256','c'*64),
                                       ('source_id','wrong'), ('domain','normal')])
def test_original_ancestry_is_checked_even_when_qualified_map_agrees(field, value):
    manifest, sources = source_fixture()
    qualified = sources['ten|old003|old']['original_source']
    qualified['coverage039_origin']['original_source'][field] = value
    manifest['qualified_sources'][qualified['source_id']] = deepcopy(qualified)
    with pytest.raises(ValueError, match='ten\\|old003\\|old'):
        module('data').old10_source_ids(manifest, sources)


@pytest.mark.parametrize('change', [
    lambda m,s: s['ten|old003|old']['original_source'].pop('coverage039_origin'),
    lambda m,s: s['ten|old003|old']['original_source']['coverage039_origin'].update(release='unknown'),
    lambda m,s: s['ten|old003|old'].update(file_sha256='c' * 64),
    lambda m,s: s['ten|old003|old']['original_source']['coverage039_origin']['original_source'].update(split='dev'),
    lambda m,s: s['ten|old003|old']['original_source']['coverage039_origin']['original_source'].update(parent_demo_id='other'),
    lambda m,s: s['ten|old003|old']['original_source']['coverage039_origin'].update(source_id='other'),
    lambda m,s: m['qualified_sources'].pop('old003|old'),
    lambda m,s: s['ten|new040|added040']['original_source'].update(coverage039_origin={'release':'old003'}),
])
def test_old_queue_rejects_unknown_or_conflicting_ancestry_with_source_id(change):
    manifest, sources = source_fixture(); change(manifest, sources)
    with pytest.raises(ValueError, match='ten\\|old003\\|old|ten\\|new040\\|added040'):
        module('data').old10_source_ids(manifest, sources)


def test_selection_keeps_original_positions_duplicates_and_rng():
    rows = [dict(source_id=s, pool=p, split=split) for s,p,split in
            [('old','ten','train'), ('new','ten','train'), ('old','ten','dev'),
             ('old','fresh','train'), ('old','raw','train'), ('old','ten','train')]]
    rows.append({'source_id':'old','pool':'ten','split':'train','role':'pair_only'})
    before_py = random.getstate(); before_np = np.random.get_state(); before_torch = torch.get_rng_state().clone()
    positions, count = module('data').select_old10_positions(rows, [1,0,2,0,3,5,0,4,0,6], {'old'})
    assert positions == [1,3,5,6] and count == 5
    assert random.getstate() == before_py
    assert np.array_equal(np.random.get_state()[1], before_np[1])
    assert torch.equal(torch.get_rng_state(), before_torch)


@pytest.mark.parametrize('indices,eligible,positions,count', [
    ([0,0], {'old'}, [0,1], 2), ([0], set(), [], 0), ([], {'old'}, [], 0)])
def test_selection_less_than_four_and_empty(indices, eligible, positions, count):
    assert module('data').select_old10_positions(
        [{'source_id':'old','pool':'ten','split':'train'}], indices, eligible) == (positions,count)


@pytest.mark.parametrize('indices,limit', [([1],4), ([-1],4), ([True],4), ([0],5), ([0],-1)])
def test_selection_rejects_invalid_address_or_limit(indices, limit):
    with pytest.raises(ValueError):
        module('data').select_old10_positions([{'source_id':'old','pool':'ten','split':'train'}], indices, {'old'}, limit)


def test_stage_reuses040_items_and_preserves_dev_selection(delta_inputs, tmp_path, monkeypatch):
    result = build(delta_inputs, tmp_path, monkeypatch)
    from egrs.coverage040.data import CoverageTaskControlDataset
    mod = module('data')
    previous = CoverageTaskControlDataset(result['task_control'], 'dev')
    monkeypatch.setattr(mod, '_INDEX_IDENTITY', previous.identity)
    monkeypatch.setattr(mod, '_POOL_COUNTS', {p:{'train':2 if p=='ten' else 1,'dev':1} for p in ('ten','fresh','raw')})
    monkeypatch.setattr(mod, '_PAIR_COUNTS', {'train':2,'dev':1})
    monkeypatch.setattr(mod, '_ROW_COUNT', previous.report['rows'])
    stage = mod.StageDataset(result['task_control'], 'dev')
    assert isinstance(stage, CoverageTaskControlDataset)
    assert stage.rows == previous.rows and stage.pairs == previous.pairs and stage.sources == previous.sources
    assert selected_keys(stage) == selected_keys(previous)
    assert stage.old10_source_ids == set()  # Fixture's old003 sources are dev only.
    ten_index = next(i for i, row in enumerate(stage.rows) if row['pool'] == 'ten')
    assert set(stage[ten_index]) == set(previous[ten_index])
    for key in ('proprio','actions','action_mask'):
        np.testing.assert_array_equal(stage[ten_index][key], previous[ten_index][key])


def test_stage_production_anchor_rejects_unapproved040_index(delta_inputs, tmp_path, monkeypatch):
    result = build(delta_inputs, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='040.*identity'):
        module('data').StageDataset(result['task_control'])


@pytest.mark.parametrize('anchor', ['pools','pairs','rows'])
def test_stage_fixed_population_anchors_cannot_drift(delta_inputs, tmp_path, monkeypatch, anchor):
    result = build(delta_inputs, tmp_path, monkeypatch)
    from egrs.coverage040.data import CoverageTaskControlDataset
    previous = CoverageTaskControlDataset(result['task_control'], 'train')
    mod = module('data')
    monkeypatch.setattr(mod, '_INDEX_IDENTITY', previous.identity)
    monkeypatch.setattr(mod, '_POOL_COUNTS', {p:{'train':2 if p=='ten' else 1,'dev':1} for p in ('ten','fresh','raw')})
    monkeypatch.setattr(mod, '_PAIR_COUNTS', {'train':2,'dev':1})
    monkeypatch.setattr(mod, '_ROW_COUNT', previous.report['rows'])
    if anchor == 'pools':
        monkeypatch.setattr(mod, '_POOL_COUNTS', {p:{'train':1,'dev':1} for p in ('ten','fresh','raw')})
    elif anchor == 'pairs':
        monkeypatch.setattr(mod, '_PAIR_COUNTS', {'train':1,'dev':1})
    else:
        monkeypatch.setattr(mod, '_ROW_COUNT', previous.report['rows'] + 1)
    with pytest.raises(ValueError, match='counts|row count'):
        mod.StageDataset(result['task_control'])
