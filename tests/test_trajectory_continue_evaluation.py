"""Only the remaining120 are scheduled; parent lineage is never rewritten."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from test_trajectory_evaluation import core,ready_config,adapter


@pytest.mark.parametrize('parent_changed',[False,True])
def test_explicit_continue_runs120_with_one_policy_and_keeps60(ready_config,tmp_path,monkeypatch,parent_changed):
    from egrs.trajectory_augmentation import evaluation as ev,continuation
    from benchmark.remaining_goals import isolated_policy
    plan=ev.build_plan(ready_config);plan['schema_version']=ev.SCHEMA_V3
    plan['proxy_coordination']={'protocol':'fake-verified-coordination'}
    plan['config']['environment_dispatch']={'legacy_root':str(tmp_path/'old-bridge')}
    inherited=[t['key'] for t in plan['tasks'][:6]]
    state={'inherited_task_keys':inherited,'remaining_task_keys':[t['key'] for t in plan['tasks'][6:]],
        'inherited_episode_ids':[e['episode_id'] for t in plan['tasks'][:6] for e in t['source']['episodes']],
        'remaining_episode_ids':[e['episode_id'] for t in plan['tasks'][6:] for e in t['source']['episodes']],
        'records':{'10':{},'00':{}},'environment_records':[], 'loaded_base_identity':{'fixed':'base'}}
    descriptor={'identity':'d'*64,'parent_run':str(tmp_path/'parent003'),
        'inherited_task_keys':inherited,'remaining_task_keys':state['remaining_task_keys'],
        'loaded_base_identity':state['loaded_base_identity']}
    monkeypatch.setattr(ev,'build_plan',lambda _:deepcopy(plan))
    monkeypatch.setattr(continuation,'prepare_continuation',lambda *a:deepcopy(descriptor))
    monkeypatch.setattr(continuation,'verify_continuation',lambda *a:deepcopy(state))
    calls=[];policies=[];inspections=[]
    class Policy:
        def __init__(self,cfg):
            assert not {'continue_from','continuation','initial_mask'}&cfg.keys()
            self.provenance={'policy_metadata':{'method_adapter':adapter()}};policies.append(self)
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        calls.append((item,policy));Path(folder).mkdir(parents=True)
        (Path(folder)/'environment_dispatch.json').write_text('{}')
        bind({'fixed':'base'})
        return {'status':'completed','error':None}
    def inspect(directory,**kwargs):
        inspections.append(kwargs)
        if parent_changed:raise ValueError('parent artifact changed during execution')
        return {'synthetic':'live report'}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(ev,'_run_dispatched_task',execute)
    monkeypatch.setattr(ev,'inspect_run',inspect)
    saved=[]
    monkeypatch.setattr(ev,'_save_report',lambda *a:saved.append(a))
    out=tmp_path/'eval004'
    if parent_changed:
        with pytest.raises(ValueError,match='parent artifact changed'):
            ev.run(ready_config,out,continue_from=tmp_path/'parent003')
        assert saved==[]  # No cached formal summary survives failed final verification.
    else:
        ev.run(ready_config,out,continue_from=tmp_path/'parent003')
        assert len(saved)==1
    assert len(calls)==120 and len(policies)==1 and all(p is policies[0] for _,p in calls)
    assert sum(t['condition']=='10' for t,_ in calls)==30
    assert sum(t['condition']=='00' for t,_ in calls)==90
    assert not set(inherited)&{t['key'] for t,_ in calls}
    batch=json.loads((out/'batch.json').read_text())
    assert all(batch['tasks'][key]['status']=='inherited' for key in inherited)
    assert batch['loaded_base_identity']=={'fixed':'base'}
    # Final independent verification must not use the in-process live cache.
    assert inspections==[{}]
    frozen=json.loads((out/'plan.json').read_text())
    assert frozen['continuation']==descriptor and frozen['budget']['total']==180


def test_continued_output_protection_uses_verified_expanded_parent(ready_config,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev,continuation
    plan=ev.build_plan(ready_config);plan['schema_version']=ev.SCHEMA_V3
    descriptor={'identity':'d'*64,'parent_run':str(tmp_path/'parent003'),
        'inherited_task_keys':[],'remaining_task_keys':[],'loaded_base_identity':{'fixed':'base'}}
    monkeypatch.setattr(ev,'build_plan',lambda _:plan)
    monkeypatch.setattr(continuation,'prepare_continuation',lambda *a:descriptor)
    with pytest.raises(ValueError,match='parent run'):
        ev.run(ready_config,tmp_path/'parent003/nested',continue_from='~/different-spelling/parent003')
    assert not (tmp_path/'parent003/nested').exists()


def test_v3_cannot_silently_run180_without_parent(ready_config,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev
    plan=ev.build_plan(ready_config);plan['schema_version']=ev.SCHEMA_V3
    monkeypatch.setattr(ev,'build_plan',lambda _:plan)
    with pytest.raises(ValueError,match='continue-from'):
        ev.run(ready_config,tmp_path/'fresh')
    assert not (tmp_path/'fresh').exists()


def test_inherited60_and_new120_use_original_full90_metrics(tmp_path,core):
    from egrs.trajectory_augmentation import evaluation as ev
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.planning import file_sha
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    proof=tmp_path/'proof.json';proof.write_text('verified synthetic record')
    records={'10':{},'00':{}};inherited=[]
    for bits,protocol in (('10','nine-mask10'),('00','nine-normal00')):
        for ep in expected_episodes(protocol):
            old=bits=='10' and ep['task_id'] in REUSE_TASKS
            if old:inherited.append(ep['episode_id'])
            success=(bits=='00') or (old and ep['initial_state_index']%2==0)
            row={**ep,'execution_status':'completed','classification':'success' if success else 'failure',
                 'official_goals_achieved':success,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
            records[bits][ep['episode_id']]={'condition':bits,'primary':row,
                'legacy':{**row,'classification':'failure'},'source':{'new_execution':not old,
                    'model_identity':{'policy_metadata':{'method_adapter':adapter(),'unnorm_key':'libero_10_no_noops'}},
                    'verified_files':[{'path':str(proof),'sha256':file_sha(proof)}],
                    'input_evidence_level':'verified synthetic parent or new artifact',
                    'original_protocol':'remaining-headless-normal00-control-v1'}}
    assert len(inherited)==60 and sum(r['source']['new_execution'] for pool in records.values() for r in pool.values())==120
    report=ev.make_report(records,adapter())
    assert report['conditions']['10']['formal_SR']=={'numerator':30,'denominator':90,'percent':100/3}
    assert report['conditions']['00']['formal_SR']['numerator']==90
    assert report['conditions']['00']['report']['conditions']['00']['compliant_task_SR'] is None
    missing=next(key for key in records['10'] if key not in inherited)
    records['10'].pop(missing)
    assert ev.make_report(records,adapter())['conditions']['10']['formal_SR'] is None
    paused=ev.make_report(records,adapter(),{'10':[{'episode_id':missing,'error':'technical_pause'}],'00':[]})
    assert paused['conditions']['10']['formal_SR'] is None
