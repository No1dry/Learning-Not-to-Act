"""CPU/fake sparse RGB, recorded-source reader and exact447+3 regressions."""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import re
import sys

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def core():
    from egrs.augmentation.dependencies import activate_core, activate_reporting
    activate_core(os.environ['EGRS049_CORE']); activate_reporting(os.environ['EGRS049_REPORTING'])


def images(count=1,error=2):
    a={'agentview_image':np.zeros((256,256,3),np.uint8),'robot0_joint_pos':np.zeros(1)}
    b=deepcopy(a);b['agentview_image'].reshape(-1,3)[:count,0]=error
    return a,b


@pytest.mark.parametrize('count,error,expected',[(0,0,True),(1,2,True),(6,2,True),(7,2,False),(1,3,False)])
def test052_exact_sparse_bounds_and_canonical_one_level_unchanged(count,error,expected):
    from egrs.remain052 import scope,policy
    from benchmark.remaining_goals import validation as canonical
    private=scope.package().validation;a,b=images(count,error)
    result=private.compare_observations(a,b,observation_profile=policy.PROFILE,
        refresh_state_unchanged=True,require_non_rgb_exact=True)
    assert result['matches'] is expected
    assert result['max_abs_error']==error
    assert private.observation_profile_config(policy.PROFILE)['limits']==policy.LIMITS
    old=canonical.compare_observations(a,b,**canonical.RGB_QUANTIZATION_AUDIT,refresh_state_unchanged=True)
    if error==2:assert old['matches'] is False
    assert canonical.RGB_QUANTIZATION_AUDIT['rgb_max_abs_error']==1


@pytest.mark.parametrize('bad_state',[False,None])
def test052_no_sparse_allowance_without_bit_exact_nonstepping_state(bad_state):
    from egrs.remain052 import scope,policy
    a,b=images()
    assert scope.package().validation.compare_observations(a,b,observation_profile=policy.PROFILE,
        refresh_state_unchanged=bad_state)['matches'] is False


def test052_does_not_relax_non_rgb_or_unknown_profile():
    from egrs.remain052 import scope,policy
    m=scope.package().validation;a,b=images()
    b['robot0_joint_pos'][0]=1e-10
    assert not m.compare_observations(a,b,atol=0,observation_profile=policy.PROFILE,
        refresh_state_unchanged=True,require_non_rgb_exact=True)['matches']
    with pytest.raises(ValueError):m.observation_profile_config('invented')
    with pytest.raises(ValueError):m.compare_observations(a,b,rgb_max_abs_error=3,rgb_max_changed_fraction=.0001)


def test052_actual_legacy_and_current_producer_namespaces_keep_native_bridges():
    from egrs.remain049.sources import activate
    from egrs.remain052 import scope
    from egrs.trajectory_augmentation import environment_dispatch as ed
    from benchmark.remaining_goals import libero_env,libero_compat,validation
    dispatch=activate({'benchmark_root':os.environ['EGRS049_CORE'],
        'reporting_root':os.environ['EGRS049_REPORTING'],'legacy_root':os.environ['EGRS052_LEGACY']})
    legacy=scope.legacy_package(dispatch);current=scope.package()
    native=ed._legacy_environment(dispatch).__module__.rsplit('.headless.environment',1)[0]
    assert legacy.libero_env is sys.modules[native+'.libero_env']
    assert legacy.libero_compat is sys.modules[native+'.libero_compat']
    assert current.libero_env is libero_env and current.libero_compat is libero_compat
    assert current.validation is not validation
    a,b=images()
    assert legacy.validation.compare_observations(a,b,**legacy.validation.RGB_QUANTIZATION_AUDIT,
        refresh_state_unchanged=True)['matches']
    assert validation.RGB_QUANTIZATION_RULE['max_abs_channel_error']==1


def test052_mixed_reader_routes_only_explicit_three(monkeypatch):
    from egrs.remain052 import scope
    from egrs.remain051 import scope as previous
    revised=scope.package().headless.scoped_sources;calls=[]
    strict={'resolve_source':lambda *a:calls.append('strict'),
            'archive_source':lambda *a:calls.append('strict_archive'),
            'validate_snapshot':lambda *a:calls.append('strict_snapshot')}
    monkeypatch.setattr(previous,'helpers',lambda:strict)
    monkeypatch.setattr(revised,'resolve_source',lambda *a:calls.append('revised'))
    monkeypatch.setattr(revised,'archive_source',lambda *a:calls.append('revised_archive'))
    monkeypatch.setattr(revised,'validate_snapshot',lambda *a:calls.append('revised_snapshot'))
    h=scope.helpers()
    for task,index in [('stove',21),('two_pots',11),('two_pots',45),('stove',20),('two_pots',34)]:
        h['resolve_source']('nine-mask10',task,index,{})
    h['archive_source']('fake',{'episodes':[{'episode_id':'two_pots_s011_10'}]})
    h['validate_snapshot']('fake',{'episodes':[{'episode_id':'mug_microwave_close_s049_10'}]})
    assert calls==['revised','revised','revised','strict','strict','revised_archive','strict_snapshot']


def parent(cfg):
    from egrs.remain049 import sources
    from egrs.remain052 import scope
    rows=[]
    for e in sources.expected():
        failed=e['episode_id'] in scope.FAILED
        rows.append({**e,'status':'failed' if failed else 'ready','stage':'construction' if e['task_id']=='stove' and failed else 'independent_replay' if failed else 'complete',
            'error':'preserved old RGB2 failure' if failed else None,
            'origin':None if e['task_id']=='stove' and failed else {'manifest':'fixed','candidate_replay':'old','replay_sha256':'f'*64},
            **({} if failed else {'source_plan_sha256':'a'*64})})
    return {'rows':rows,'ready':447,'failed':3,'expected':sources.expected(),'config':cfg}


@pytest.mark.parametrize('new_fail',[False,True])
def test052_exact447_reuse_build1_replay3_and_no_implicit_retry(tmp_path,monkeypatch,new_fail):
    from egrs.remain052 import recovery as r
    from egrs.remain049 import sources as old,evaluation
    cfg={'source_bank':str(tmp_path/'new')};p=parent(cfg);calls=[]
    monkeypatch.setattr(r,'parent_report',lambda *a:p)
    monkeypatch.setattr(old,'activate',lambda *a:{})
    monkeypatch.setattr(old,'sha',lambda *a:r.PARENT_SHA)
    monkeypatch.setattr(r.scope,'helpers',lambda:{})
    monkeypatch.setattr(evaluation,'protect_output',lambda *a,**k:None)
    def generate(row,*a):
        calls.append((row['episode_id'],row['task052_action'],deepcopy(row['origin'])))
        if new_fail:raise ValueError('new failure retained')
        row.update(status='ready',source_plan_sha256='b'*64)
    monkeypatch.setattr(r,'generate',generate)
    out=r.recover(cfg,tmp_path/'parent',cfg['source_bank'])
    assert len(calls)==3 and sum(a=='build_and_replay' for _,a,_ in calls)==1
    assert sum(a=='replay_only' for _,a,_ in calls)==2
    assert all(origin=={'manifest':'fixed'} for _,a,origin in calls if a=='replay_only')
    assert out['ready']==(447 if new_fail else 450) and out['failed']==(3 if new_fail else 0)
    assert out['model_rollouts']==0
    for before,after in zip(p['rows'],out['rows']):
        if before['status']=='ready':assert after=={**before,'task052_parent_status':'ready','task052_action':'reuse_only'}
        else:assert after['task052_original_failure']['error']=='preserved old RGB2 failure'
    r.recover(cfg,tmp_path/'parent',cfg['source_bank'],continuation=True)
    assert len(calls)==3
    with pytest.raises(FileExistsError):r.recover(cfg,tmp_path/'parent',cfg['source_bank'])


def test052_reader_accepts_complete_new_sparse2_audits_and_archives(tmp_path,monkeypatch):
    """Actual codecs,150-frame arithmetic,2 replay files and portable archive; no native."""
    from egrs.remain052 import scope
    from egrs.remain049 import sources as old
    from benchmark.remaining_goals.schema import manifest_hash
    from benchmark.remaining_goals.task_catalog import TASKS
    core=Path(os.environ['EGRS049_CORE'])
    path=core/'tests/test_headless_source_acceptance.py'
    spec=importlib.util.spec_from_file_location('_task052_source_fixture',path)
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    private=scope.package();v=private.validation
    original=fixture.SyntheticAudit
    class Sparse(original):
        def validation_snapshot(self):
            snap=super().validation_snapshot();snap['fresh_observation']['agentview_image'][0,0,0]+=2
            return snap
    monkeypatch.setattr(fixture,'SyntheticAudit',Sparse)
    monkeypatch.setattr(fixture,'validate_candidate',v.validate_candidate)
    monkeypatch.setattr(fixture,'compare_observations',v.compare_observations)
    monkeypatch.setattr(fixture,'RGB_QUANTIZATION_AUDIT',v.RGB_QUANTIZATION_AUDIT)
    monkeypatch.setattr(fixture,'RGB_QUANTIZATION_RULE',v.RGB_QUANTIZATION_RULE)
    mp,rp,manifest,report=fixture.make_source(tmp_path,'stove')
    for e in manifest['episodes']:
        e['instruction']=re.split(r'SCENE\d+_',TASKS['stove']['name'],maxsplit=1)[1].replace('_',' ')
    manifest['content_hash']=manifest_hash(manifest);fixture.write(mp,manifest)
    report.update(source_manifest_sha256=old.sha(mp),source_content_hash=manifest['content_hash'])
    fixture.write(rp,report)
    origin={'manifest':str(mp),'manifest_sha256':old.sha(mp),'content_hash':manifest['content_hash'],
        'candidate_replay':str(rp),'replay_sha256':old.sha(rp)}
    reader=private.headless.scoped_sources
    plan=reader.resolve_source('selected-mask10','stove',0,origin)
    evidence=plan['source_acceptance']['episodes'][0]
    assert evidence['construction']['limits']['rgb_max_abs_error']==2 and len(evidence['replays'])==2
    archive=tmp_path/'archive';reader.archive_source(archive,plan);reader.validate_snapshot(archive,plan)
    # Exact same bytes fail under the old one-level reader; old files aren't regraded.
    from egrs.remain051 import scope as strict
    with pytest.raises(ValueError):strict.helpers()['resolve_source']('selected-mask10','stove',0,origin)


def test052_keeps_original_rollout_and_binary_scorer():
    from egrs.remain052.evaluation import engine
    from egrs.remain049 import evaluation as old
    n=engine()
    assert n['run'].__code__ is old.run.__code__ and n['Live'] is old.Live
    assert n['execute_episode'].__code__ is old.execute_episode.__code__
    assert n['verify_episode'].__code__ is old.verify_episode.__code__


def test052_old_v6_pot_construction_new_v8_replay_and_archive(tmp_path):
    import json
    from egrs.remain052 import scope,policy
    from egrs.remain049 import sources as old
    from benchmark.remaining_goals.nine_catalog import get_task,episode_fields,read_goal_facts
    from benchmark.remaining_goals.schema import manifest_hash
    from benchmark.remaining_goals.observation_artifact import save_observation_artifact
    from benchmark.remaining_goals import validation as canonical
    m=scope.package();state=np.array([0.,.4,1.,0.]);p=get_task('two_pots');fields=episode_fields('two_pots')
    def obs():return {'agentview_image':np.zeros((256,256,3),np.uint8),'robot0_joint_pos':np.array([.4])}
    class Fake:
        def __init__(self,error=0):self.error=error
        def restore_candidate(self,e):self.state=state.copy();return obs()
        def step(self,a):self.state[0]+=.05;return obs()
        def validation_snapshot(self):
            fresh=obs();fresh['agentview_image'][0,0,0]=self.error
            facts=read_goal_facts(lambda p:p[0]=='turnon' or p[1]=='moka_pot_1',False,fields['task_semantics'])
            return {'state':self.state.copy(),'state_before_refresh':self.state.copy(),'qvel':[0.],
                'robot_qpos':[.4],'object_positions':{'a':[1.,0.,0.],'b':[0.,0.,0.]},
                'penetrations':[],'fresh_observation':fresh,**facts}
    root=tmp_path/'candidate';root.mkdir();np.save(root/'state.npy',state)
    instruction=re.split(r'SCENE\d+_',p['name'],maxsplit=1)[1].replace('_',' ')
    e={'episode_id':'two_pots_s011_10','task_id':'two_pots','suite':'libero_10','task_name':p['name'],
        'libero_task_id':8,'instruction':instruction,**fields,'initial_mask':[True,False],
        'source_id':'two_pots_official_11','initial_state_index':11,'seed':11,'split':'test','pose_id':'fake',
        'horizon':520,'retention_steps':150,'state_path':'state.npy','state_sha256':old.sha(root/'state.npy'),
        'bddl_sha256':'a'*64,'model_xml_sha256':'b'*64,'reference_robot_qpos':[.4],
        'observation_profile':canonical.V6_PROFILE,
        'construction':{'legal':False,'method':'synthetic fixture','reviewed_by':'synthetic-only','technical_audit':'audit.json'}}
    e['initial_observation']=save_observation_artifact(root,'initial.npz',obs())
    hold=[0.,0.,0.,0.,0.,0.,-1.]
    construction=canonical.validate_candidate(Fake(),e,steps=150,hold_action=hold,observation_profile=canonical.V6_PROFILE)
    assert construction['technical_acceptance']
    old.write(root/'audit.json',construction)
    manifest={'schema_version':'remaining-goals-v0.1','environment':{'name':'libero','fingerprint':'fake'},
        'observation_profile':canonical.V6_PROFILE,'episodes':[e]}
    manifest['content_hash']=manifest_hash(manifest);mp=root/'manifest.json';old.write(mp,manifest)
    replay=tmp_path/'replay';rp=replay/'replay.json'
    report={'kind':'candidate_formal_adapter_replay','protocol':'nine-mask10','policy_called':False,
        'release_authorized':False,'source_manifest_sha256':old.sha(mp),'source_content_hash':manifest['content_hash'],
        'steps':150,'repeats':2,'hold_action':hold,'technical_acceptance':True,'error':None,'episodes':[],
        'observation_profile':policy.PROFILE,'observation_audit_rule':m.validation.RGB_QUANTIZATION_RULE,
        'observation_audit_limits':policy.LIMITS}
    for repeat in range(2):
        audit=m.validation.validate_candidate(Fake(2),e,steps=150,hold_action=hold,observation_profile=policy.PROFILE)
        assert audit['technical_acceptance']
        relative=f'repeat_{repeat}/audit.json';folder=replay/f'repeat_{repeat}'
        artifact=save_observation_artifact(folder,'initial.npz',obs())
        comp=m.validation.compare_observations(obs(),obs(),atol=0,require_non_rgb_exact=True,
            refresh_state_unchanged=True,observation_profile=policy.PROFILE)
        reset={'saved_state_exact':True,'initial_mask_exact':True,'construction_observation_matches':True,'initial_non_rgb_exact':True}
        audit.update(formal_reset_checks=reset,reset_observation_comparison=comp,reset_initial_observation=artifact,
            post_restore_model_xml_sha256='c'*64,expected_reset_model_xml_sha256=e['model_xml_sha256'])
        old.write(replay/relative,audit)
        report['episodes'].append({'episode_id':e['episode_id'],'repetition':repeat,'initial_mask':[True,False],
            'source_legal':False,'technical_acceptance':True,'reset_checks':reset,'checks':audit['checks'],
            'error':None,'audit_path':relative})
    old.write(rp,report)
    origin={'manifest':str(mp),'manifest_sha256':old.sha(mp),'content_hash':manifest['content_hash'],
        'candidate_replay':str(rp),'replay_sha256':old.sha(rp)}
    h=scope.helpers();plan=h['resolve_source']('nine-mask10','two_pots',11,origin)
    evidence=plan['source_acceptance']['episodes'][0]
    assert evidence['construction']['limits']['rgb_max_abs_error']==1
    assert all(r['limits']['rgb_max_abs_error']==2 for r in evidence['replays'])
    archive=tmp_path/'archive';h['archive_source'](archive,plan);h['validate_snapshot'](archive,plan)
    bad=old.read(replay/'repeat_1/audit.json');bad['task052_admission']['limits']['rgb_max_abs_error']=3
    old.write(replay/'repeat_1/audit.json',bad)
    with pytest.raises(ValueError,match='binding'):h['resolve_source']('nine-mask10','two_pots',11,origin)


def test052_complete_fake450_retains_live_SR_and_single_model_worker(tmp_path,monkeypatch,capsys):
    from egrs.remain052 import evaluation as new,recovery,scope
    from egrs.remain049 import evaluation as old,sources
    from benchmark.remaining_goals import isolated_policy
    from test_remain049 import _record
    cfg={'source_bank':str(tmp_path/'bank')};sources.write(tmp_path/'bank/sources.json',{'fake':'bank'})
    population=sources.expected();frozen={'model':'base','runtime':{},'expected':population,
        'sources':[{'episodes':[e]} for e in population],'source_bank_sha256':'a'*64,
        'plan_sha256':'b'*64,'config':cfg,'adapter_identity':None}
    monkeypatch.setattr(sources,'activate',lambda *a:{})
    monkeypatch.setattr(recovery,'validate_recovery',lambda *a:None)
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
    assert len(policies)==1 and len(calls)==450
    assert result['counts']['formal_SR']=={'numerator':450,'denominator':450,'percent':100.}
    assert capsys.readouterr().out.count('overall_SR=')==450
