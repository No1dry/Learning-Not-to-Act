"""CPU/fake recovery tests, including the formerly missed inner R7 path."""
from copy import deepcopy
import importlib
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def core():
    from egrs.augmentation.dependencies import activate_core,activate_reporting
    activate_core(os.environ['EGRS049_CORE']);activate_reporting(os.environ['EGRS049_REPORTING'])


def episode(index=49):
    from benchmark.remaining_goals import stability as s
    from benchmark.remaining_goals.nine_catalog import get_task,episode_fields
    p=get_task('mug_microwave_close');joint={'id':0,'name':s.OBJECT+'_joint0','type':0,
        'qpos_adr':0,'qpos_dim':7,'dof_adr':0,'dof_dim':6}
    binding={'schema_version':s.BINDING_SCHEMA,'model_xml_sha256':'a'*64,'object_name':s.OBJECT,
        'state_layout':{'nq':7,'nv':6,'na':0,'qpos_start':1,'qvel_start':8,'state_size':14},
        'joint_layout':[joint],'active_joint':joint}
    return {'episode_id':f'mug_microwave_close_s{index:03d}_10','task_id':'mug_microwave_close',
        'suite':'libero_10','task_name':p['name'],'libero_task_id':p['official_task_id'],
        **episode_fields('mug_microwave_close'),'initial_state_index':index,'initial_mask':[True,False],
        'stability_profile':s.PROFILE,'observation_profile':'named-uint8-rgb-one-level-v6',
        'model_xml_sha256':'a'*64,'construction':{'protocol':'nine-mask10'},
        'reference_robot_qpos':[0.]*9,'stability_binding':binding}


def test051_r7_accepts49_but_canonical_still_rejects_it():
    from egrs.remain051.scope import package
    from benchmark.remaining_goals import stability as original,validation,libero_env,libero_compat
    e=episode();private=package()
    with pytest.raises(ValueError,match='0..9'):original.validate_scope(e)
    assert private.stability.validate_scope(e)==e['stability_binding']
    assert private.validation is not validation
    assert private.libero_env is libero_env and private.libero_compat is libero_compat
    assert original.validate_scope.__globals__ is vars(original)
    assert private.stability.validate_scope.__globals__ is vars(private.stability)
    with pytest.raises(ValueError,match='0..9'):original.validate_scope(e)


@pytest.mark.parametrize('index',[0,9,10,21,49])
def test051_full_index_domain_through_r7_and_reader(index):
    from egrs.remain051.scope import package,helpers
    e=episode(index);private=package()
    assert private.stability.validate_scope(e)==e['stability_binding']
    assert private.headless.rgb_revalidation.stability_identity(e)==e['stability_binding']
    helpers()['_identity']('mug_microwave_close',index,'nine-mask10')


@pytest.mark.parametrize('change',[
    {'initial_state_index':50},{'initial_state_index':-1},{'initial_state_index':True},
    {'initial_mask':[False,True]},{'task_id':'two_pots'},{'observation_profile':'invented'},
    {'stability_binding':{}},{'reference_robot_qpos':[0.]*8}])
def test051_r7_other_scope_and_physics_binding_checks_are_not_relaxed(change):
    from egrs.remain051.scope import package
    e=episode();e.update(change)
    with pytest.raises(ValueError):package().stability.validate_scope(e)


def test051_nested_validation_reaches_restore_without_native_and_keeps_limits():
    from egrs.remain051.scope import package
    private=package();e=episode();calls=[]
    def restore(ep):calls.append(ep);raise RuntimeError('FAKE_RESTORE_REACHED')
    env=SimpleNamespace(restore_candidate=restore)
    out=private.validation.validate_candidate(env,e,steps=150,hold_action=[0,0,0,0,0,0,-1.],
        stability_profile=e['stability_profile'],observation_profile=e['observation_profile'])
    assert len(calls)==1 and out['technical_acceptance'] is False and 'FAKE_RESTORE_REACHED' in str(out['error'])
    with pytest.raises(ValueError,match='frozen physical'):
        private.validation.validate_candidate(env,e,steps=150,hold_action=[0,0,0,0,0,0,-1.],
            stability_profile=e['stability_profile'],observation_profile=e['observation_profile'],position_tolerance=.01)


def test051_replay_inner_r7_resolves_to_private_guard(tmp_path,monkeypatch):
    from egrs.remain051.scope import package
    private=package();e=episode();seen=[]
    def artifact(*a,**k):seen.append(True);raise RuntimeError('FAKE_ARTIFACT_REACHED')
    monkeypatch.setattr(private.replay_candidates,'load_observation_artifact',artifact)
    e['initial_observation']={'synthetic':'only'}
    wrapper=private.replay_candidates.ReplayAuditEnv(SimpleNamespace(),np.zeros(14),'b'*64,
        frames_dir=tmp_path,manifest_dir=tmp_path,observation_profile=e['observation_profile'],stability_profile=e['stability_profile'])
    with pytest.raises(RuntimeError,match='FAKE_ARTIFACT_REACHED'):wrapper.restore_candidate(e)
    assert seen==[True]


def test051_builder_inner_r7_resolves_to_private_guard(monkeypatch):
    from egrs.remain051.scope import package
    private=package();e=episode();calls=[]
    monkeypatch.setattr(private.build,'model_xml_hash',lambda env:'a'*64)
    monkeypatch.setattr(private.stability,'binding_from_model',lambda *a:e['stability_binding'])
    def restore(*a):calls.append(True);raise RuntimeError('FAKE_NATIVE_RESTORE_REACHED')
    monkeypatch.setattr(private.build,'restore_raw_state',restore)
    wrapper=private.build.CandidateAuditEnv.__new__(private.build.CandidateAuditEnv)
    wrapper.stability_profile=e['stability_profile'];wrapper.candidate=np.zeros(14)
    wrapper.env=SimpleNamespace(env=SimpleNamespace(),sim=SimpleNamespace(model=object()))
    with pytest.raises(RuntimeError,match='FAKE_NATIVE_RESTORE_REACHED'):wrapper.restore_candidate(e)
    assert calls==[True]


def test051_rgb_two_level_difference_is_still_rejected():
    from egrs.remain051.scope import package
    private=package();x=np.zeros((3,3,3),dtype=np.uint8);y=x.copy();y[0,0,0]=2
    first={'robot0_eye_in_hand_image':x,'proprio':np.zeros(8)}
    second={'robot0_eye_in_hand_image':y,'proprio':np.zeros(8)}
    check=private.validation.compare_observations(first,second,require_non_rgb_exact=True,
        observation_profile='named-uint8-rgb-one-level-v6',refresh_state_unchanged=True)
    assert check['matches'] is False and check['max_abs_error']==2
    assert private.stability.POSITION_LIMIT==.005 and private.stability.ORIENTATION_LIMIT_DEG==1.
    assert private.stability.VELOCITY_LIMIT==.01


def parent(cfg):
    from egrs.remain049.sources import expected,SCHEMA
    from egrs.remain051.recovery import FAILED,REPLAY_ONLY
    rows=[]
    for e in expected():
        fail=e['episode_id'] in FAILED
        rows.append({**e,'status':'failed' if fail else 'ready','stage':'independent_replay' if e['episode_id'] in REPLAY_ONLY else 'construction' if fail else 'complete',
            'error':'old failure' if fail else None,'origin':{'manifest':'fixed-manifest','candidate_replay':'old-replay','replay_sha256':'f'*64},
            **({} if fail else {'source_plan_sha256':'c'*64})})
    return {'schema_version':SCHEMA,'config':cfg,'expected':expected(),'rows':rows,
        'ready':405,'failed':45,'processed':450,'complete':False}


def test051_exact405_reuse_42_build_and3_replay_only(tmp_path,monkeypatch,capsys):
    from egrs.remain051 import recovery as r
    from egrs.remain049 import sources as old,evaluation as ev
    cfg={'source_bank':str(tmp_path/'new')};p=parent(cfg)
    monkeypatch.setattr(r,'parent_report',lambda *a:p)
    monkeypatch.setattr(old,'activate',lambda *a:{'fake':'dispatch'})
    monkeypatch.setattr(r.scope,'helpers',lambda:{})
    monkeypatch.setattr(ev,'protect_output',lambda *a,**k:None)
    monkeypatch.setattr(old,'sha',lambda *a:r.PARENT_SHA)
    calls=[]
    def generate(row,*args):
        calls.append((row['episode_id'],row['recovery_action'],deepcopy(row['origin'])))
        row.update(status='ready',source_plan_sha256='d'*64)
    monkeypatch.setattr(r,'generate',generate)
    report=r.recover(cfg,tmp_path/'original',cfg['source_bank'])
    assert report['ready']==450 and report['failed']==0 and report['complete']
    assert len(calls)==45 and sum(a=='build_and_replay' for _,a,_ in calls)==42
    assert sum(a=='replay_only' for _,a,_ in calls)==3
    assert all(origin=={'manifest':'fixed-manifest'} for _,action,origin in calls if action=='replay_only')
    for before,after in zip(p['rows'],report['rows']):
        if before['status']=='ready':assert after=={**before,'parent_status':'ready','recovery_action':'reuse_only'}
    with pytest.raises(FileExistsError):r.recover(cfg,tmp_path/'original',cfg['source_bank'])
    r.recover(cfg,tmp_path/'original',cfg['source_bank'],continuation=True)
    assert len(calls)==45


def test051_retains_new_failures_no_retry_no_model_eval(tmp_path,monkeypatch):
    from egrs.remain051 import recovery as r
    from egrs.remain049 import sources as old,evaluation as ev
    cfg={'source_bank':str(tmp_path/'new')};p=parent(cfg)
    monkeypatch.setattr(r,'parent_report',lambda *a:p);monkeypatch.setattr(old,'activate',lambda *a:{})
    monkeypatch.setattr(r.scope,'helpers',lambda:{});monkeypatch.setattr(ev,'protect_output',lambda *a,**k:None)
    monkeypatch.setattr(old,'sha',lambda *a:r.PARENT_SHA);calls=[]
    def fail(row,*a):calls.append(row['episode_id']);raise ValueError('same strict RGB rejection')
    monkeypatch.setattr(r,'generate',fail)
    out=r.recover(cfg,tmp_path/'original',cfg['source_bank'])
    assert out['ready']==405 and out['failed']==45 and not out['complete'] and out['model_rollouts']==0
    r.recover(cfg,tmp_path/'original',cfg['source_bank'],continuation=True)
    assert len(calls)==45 and all(row['original_failure']['error']=='old failure' for row in out['rows'] if row['parent_status']=='failed')


def test051_eval_reuses_original_runner_and_scorer_not_new_judge():
    from egrs.remain051.evaluation import engine
    from egrs.remain049 import evaluation as old
    new=engine()
    assert new['run'].__code__ is old.run.__code__
    assert new['verify_episode'].__code__ is old.verify_episode.__code__
    assert new['execute_episode'].__code__ is old.execute_episode.__code__
    assert new['Live'] is old.Live and new['helpers'] is not old.helpers


def test051_complete_fake450_runs_through_repaired_coordinator(tmp_path,monkeypatch,capsys):
    from egrs.remain051 import evaluation as new,recovery,scope
    from egrs.remain049 import evaluation as old,sources
    from benchmark.remaining_goals import isolated_policy
    from test_remain049 import _record
    cfg={'source_bank':str(tmp_path/'bank')};sources.write(tmp_path/'bank/sources.json',{'fake':'bank'})
    population=sources.expected();frozen={'model':'base','runtime':{},'expected':population,
        'sources':[{'episodes':[e]} for e in population],'source_bank_sha256':'a'*64,
        'plan_sha256':'b'*64,'config':cfg,'adapter_identity':None}
    monkeypatch.setattr(sources,'activate',lambda *a:{})
    validations=[];monkeypatch.setattr(recovery,'validate_recovery',lambda *a:validations.append(True))
    monkeypatch.setattr(old,'plan',lambda *a:frozen)
    monkeypatch.setattr(old,'protect_output',lambda *a,**k:None)
    monkeypatch.setattr(old,'_verify_model',lambda *a:None)
    monkeypatch.setattr(scope,'helpers',lambda:{})
    policies=[];calls=[]
    class Policy:
        def __init__(self,cfg):self.provenance={};policies.append(self)
        def close(self):pass
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    def execute(folder,source,*args):
        folder.mkdir(parents=True);p=folder/'fake_raw.json';p.write_text('{}');calls.append(source)
        return _record(source['episodes'][0],p)
    monkeypatch.setattr(old,'execute_episode',execute)
    result=new.run(cfg,tmp_path/'model','base')
    assert len(policies)==1 and len(calls)==450 and validations==[True]
    assert result['counts']['formal_SR']=={'numerator':450,'denominator':450,'percent':100.0}
    assert capsys.readouterr().out.count('overall_SR=')==450
