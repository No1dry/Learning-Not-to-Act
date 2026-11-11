"""040 candidate metadata and immutable old-parent contracts, with tiny HDFs."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from egrs.augmentation.data import file_sha256, identity, load_scope, read_json
from test_trajectory_data import seed_manifest


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False)+'\n', encoding='utf-8')


def prepared040(tmp_path, monkeypatch):
    from egrs.coverage040 import plan as module
    from egrs.trajectory_augmentation.cli import RECIPE, build_plan
    template = seed_manifest(tmp_path, count=1)['sources'][0]
    manifest = seed_manifest(tmp_path, count=0); manifest['data_root'] = 'raw'
    stats = tmp_path/'stats.json'; write(stats, {})
    bindings = {}
    for task in load_scope()['tasks']:
        relative = f"libero_10/{task['official_task_name']}_demo.hdf5"
        target = tmp_path/'raw'/relative; target.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(target, 'w') as h:
            h.require_group('data').attrs['language'] = template['instruction']
            for i in range(50):
                g = h.create_group(f'data/demo_{i}')
                g['actions'] = np.zeros((2, 7), dtype=np.float32)
                g['obs/agentview_rgb'] = np.zeros((2, 1, 1, 3), dtype=np.uint8)
                g['obs/eye_in_hand_rgb'] = np.zeros((2, 1, 1, 3), dtype=np.uint8)
                g['obs/ee_states'] = np.zeros((2, 6), dtype=np.float32)
                g['obs/gripper_states'] = np.zeros((2, 2), dtype=np.float32)
        for i in range(20):
            row = deepcopy(template)
            row.update(source_id=relative+f'#demo_{i}', file=relative,
                       file_sha256=file_sha256(target), task_key=task['key'],
                       episode=f'data/demo_{i}', demo_index=i, length=2)
            row.update({k: deepcopy(task[k]) for k in
                        ('official_task_name', 'active_goals', 'invariant_predicates')})
            for key in ('action_normalization', 'proprio_normalization'):
                row['mapping'][key]['stats_sha256'] = file_sha256(stats)
            manifest['sources'].append(row)
        bindings[task['key']] = {**{k: deepcopy(task[k]) for k in
            ('official_task_name', 'active_goals', 'invariant_predicates')},
            'orientation': 'opengl', 'state_field': 'states',
            'state_alignment_basis': 'synthetic metadata',
            'alignment': {'rule': 'same_state', 'orientation': 'identity',
                          'state_offset': 0, 'observation_offset': 0, 'action_offset': 0}}
    write(tmp_path/'seeds.json', manifest)
    write(tmp_path/'035.json', {'format':'task035-generation-config-v1', 'manifest':'seeds.json',
        'benchmark_root':'unopened-core', 'stats_path':'stats.json', 'stats_sha256':file_sha256(stats),
        'unnorm_key':'libero_10', 'recipe':RECIPE, 'native_backend':{'kind':'native',
            'historical_root':'unopened-native', 'python':'venv/bin/python'}, 'bindings':bindings})
    old = build_plan(tmp_path/'035.json')['sources']
    raw = {p['source_id']: {k: deepcopy(p[k]) for k in ('source_id', 'parent_demo_id',
        'source_group', 'split', 'task_key', 'file', 'file_sha256', 'episode', 'instruction', 'physical_ancestry')}
        for p in old}
    counts = {'ten': {'train':1,'dev':0}, 'fresh':{'train':1,'dev':0},
              'raw':dict(Counter(p['split'] for p in old))}
    ret = {'format':'task039-retention-data-v1', 'data_roots':{'raw':str((tmp_path/'raw').resolve()),
        'generated':str(tmp_path.resolve())}, 'allowed_generated_roots':{
            'old003':str((tmp_path/'old-artifacts').resolve()), 'new039':str((tmp_path/'new039-artifacts').resolve())},
        'parents':raw, 'sources':{}, 'inputs':{}, 'expected_pool_counts':counts}
    for key in ('old-artifacts', 'new039-artifacts'): (tmp_path/key).mkdir()
    for p in old:
        ret['sources']['raw|'+p['source_id']] = dict(raw[p['source_id']], pool='raw')
    for pool in ('ten','fresh'): ret['sources'][pool+'|old'] = {'pool':pool,'split':'train'}
    ret['identity'] = identity(ret); write(tmp_path/'old-retention/sources.json', ret)
    (tmp_path/'old-retention/rows.jsonl').write_text('', encoding='utf-8')
    rr = {'data_kind':ret['format'], 'sources_identity':ret['identity'], 'pool_counts':counts,
          'rows_sha256':file_sha256(tmp_path/'old-retention/rows.jsonl')}
    rr['identity'] = identity(rr); write(tmp_path/'old-retention/report.json', rr)
    merged = {'format':'task035-generated-trajectories-v1', 'parents':old,
              'data_root':str(tmp_path.resolve()), 'sources':{}}
    merged['identity'] = identity(merged); write(tmp_path/'old-merged/sources.json', merged)
    mr = {'sources_identity':merged['identity']}; mr['identity']=identity(mr)
    write(tmp_path/'old-merged/report.json', mr)
    tc = {'format':'task039-task-control-sources-v1', 'retention_index':str((tmp_path/'old-retention').resolve()),
        'retention_identity':ret['identity'], 'generated_export':str((tmp_path/'old-merged').resolve()),
        'merged_export_identity':merged['identity'], 'inputs':{}, 'labels_sha256':hashlib.sha256(b'').hexdigest(),
        'pairs_sha256':hashlib.sha256(b'').hexdigest()}
    tc['identity'] = identity(tc)
    report = {'data_kind':'task038-task-control-data-v1', 'sources_identity':tc['identity'],
              'labels_sha256':tc['labels_sha256'], 'pairs_sha256':tc['pairs_sha256']}
    report['identity']=identity(report)
    for name,value in (('sources.json',tc),('report.json',report),('identity.json',{
        'format':'task039-index-identity-v1','sources_identity':tc['identity'],'report_identity':report['identity']})):
        write(tmp_path/'old-control'/name,value)
    for name in ('labels','pairs'): (tmp_path/f'old-control/{name}.jsonl').write_text('',encoding='utf-8')
    monkeypatch.setattr(module, '_BASE_INDEX_IDENTITY', tc['identity'])
    monkeypatch.setattr(module, '_BASE_REPORT_IDENTITY', report['identity'])
    monkeypatch.setattr(module, '_BASE_POOL_COUNTS', counts)
    path=tmp_path/'040.json'; write(path, {'format':'task040-parent-coverage-config-v1',
        'generation_config':'035.json','old_task_control_index':'old-control'})
    return path, old


def test_exact_candidates_train_only_and_old_parents_unchanged(tmp_path, monkeypatch):
    from egrs.coverage040.plan import build_plan
    path, old = prepared040(tmp_path, monkeypatch)
    plan=build_plan(path)
    assert plan['parents'][:180] == old
    assert len(plan['parents']) == 240 and len(plan['candidates']) == 60
    assert {p['task_key'] for p in plan['candidates']} == {'stove','mug_pudding','two_pots'}
    for task in ('stove','mug_pudding','two_pots'):
        rows=[p for p in plan['candidates'] if p['task_key']==task]
        assert [p['demo_index'] for p in rows] == list(range(20,40))
    assert plan['sources'] and all(p['split']=='train' for p in plan['sources'])
    assert all(p['source_id']==p['file']+'#'+p['episode'].split('/')[-1] for p in plan['candidates'])
    assert all(p['physical_ancestry']=='unknown' for p in plan['candidates'])
    assert plan['identity'] == identity(plan)
    assert str(tmp_path.resolve()) not in plan['protected_paths']
    assert str((tmp_path/'old-artifacts').resolve()) in plan['protected_paths']


def test_group_aliases_inherit_anchors_conflicts_reject_only_new(tmp_path, monkeypatch):
    from egrs.coverage040.plan import assign_candidates
    def row(sid, group, split=None):
        return {'source_id':sid,'file_sha256':'a'*64,'episode':'data/'+sid,
                'group_ids':group, **({'split':split,'source_group':sid+'-old'} if split else {})}
    old=[row('old-train',['train-alias'],'train'),row('old-dev',['dev-alias'],'dev')]
    candidates=[row('new-20',['train-alias']),row('new-21',['train-alias']),
                row('new-22',['train-alias','dev-alias']),row('new-23',[]),row('new-24',[])]
    original=deepcopy(old)
    # A cross-split bridge rejects the affected new component, retaining old anchors.
    assigned, selected=assign_candidates(old,candidates)
    assert old==original
    assert all(p['selection_reason']=='old_split_conflict' for p in assigned[:3])
    assert all(p['source_id'] not in {'new-20','new-21','new-22'} for p in selected)
    assigned, selected=assign_candidates(old,candidates[:2]+candidates[3:])
    assert assigned[0]['split']==assigned[1]['split']=='train'
    assert assigned[0]['source_group']=='old-train-old'
    assert assigned[0]['selection_reason']==assigned[1]['selection_reason']=='known_old_duplicate'
    assert all(p['source_id'] not in {'new-20','new-21'} for p in selected)
    a,b=assign_candidates([], [row('new-30',['dupe']),row('new-2',['dupe'])])
    assert a[0]['source_group']==a[1]['source_group']
    assert a[0]['representative_id']==a[1]['representative_id']=='new-2'
    expected=hashlib.sha256(b'7|new-2|new-30').hexdigest()
    assert a[0]['source_group']==expected


@pytest.mark.parametrize('mutation',['unresolved','missing_key','wrong_instruction','changed_anchor'])
def test_plan_rejects_bad_paths_missing_candidates_and_wrong_binding(tmp_path,monkeypatch,mutation):
    from egrs.coverage040.plan import build_plan
    path,_=prepared040(tmp_path,monkeypatch)
    if mutation=='unresolved':
        cfg=read_json(path);cfg['generation_config']='$LNA_UNSET_040/035.json';write(path,cfg)
    elif mutation=='changed_anchor':
        tc=read_json(tmp_path/'old-control/sources.json');tc['identity']='0'*64;write(tmp_path/'old-control/sources.json',tc)
    else:
        raw=next((tmp_path/'raw').rglob('*stove*demo.hdf5'))
        with h5py.File(raw,'a') as h:
            if mutation=='missing_key': del h['data/demo_39']
            else: h['data'].attrs['language']='wrong instruction'
    with pytest.raises((ValueError,KeyError)): build_plan(path)


def test_old_035_entry_still_rejects_new_range(tmp_path):
    from egrs.trajectory_augmentation.data import validate_seeds
    manifest=seed_manifest(tmp_path,count=1)
    manifest['sources'][0].update(demo_index=20,episode='data/demo_20')
    with pytest.raises(ValueError,match='firstN'): validate_seeds(manifest)


def test_environment_paths_expand_in040_and_original_config(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    path,_=prepared040(tmp_path,monkeypatch)
    monkeypatch.setenv('LNA_040_FIXTURE',str(tmp_path))
    cfg=read_json(path);cfg['generation_config']='${LNA_040_FIXTURE}/035.json';write(path,cfg)
    original=read_json(tmp_path/'035.json');original['manifest']='$LNA_040_FIXTURE/seeds.json'
    original['native_backend']['python']='$LNA_040_FIXTURE/venv/bin/python';write(tmp_path/'035.json',original)
    plan=build_plan(path)
    assert plan['config']['generation_config']==str((tmp_path/'035.json').resolve())
    assert plan['execution_config']['manifest']==str((tmp_path/'seeds.json').resolve())
    assert plan['execution_config']['native_backend']['python']==str(tmp_path/'venv/bin/python')


def test_mapping_tamper_cannot_reuse_frozen_old_anchor(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    path,_=prepared040(tmp_path,monkeypatch)
    manifest=read_json(tmp_path/'seeds.json')
    for source in manifest['sources']: source['mapping']['processor_id']='changed-original-processor'
    write(tmp_path/'seeds.json',manifest)
    with pytest.raises(ValueError,match='parent|binding'): build_plan(path)
