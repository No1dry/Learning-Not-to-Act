"""Targeted CPU/fake tests, never a pretrained policy or native simulator."""
from copy import deepcopy
import ast
import inspect
import json
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def fixed_core():
    from egrs.augmentation.dependencies import activate_core, activate_reporting
    activate_core(os.environ['EGRS049_CORE'])
    activate_reporting(os.environ['EGRS049_REPORTING'])


def test_population_450_distinct_fixed_indices_and_original90_unchanged():
    from egrs.remain049.sources import expected
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    rows = expected()
    assert len(rows) == len({r['episode_id'] for r in rows}) == 450
    assert len({r['task_id'] for r in rows}) == 9
    assert {r['libero_task_id'] for r in rows} == {0,1,2,3,4,6,7,8,9}
    for task in {r['task_id'] for r in rows}:
        assert [r['initial_state_index'] for r in rows if r['task_id'] == task] == list(range(50))
    for old, new in zip(expected_episodes('nine-mask10'), [r for r in rows if r['initial_state_index'] < 10]):
        assert all(new[k] == v for k,v in old.items())
    assert all(r['initial_mask'] == [True,False] and r['policy_seed'] == 7 for r in rows)


@pytest.mark.parametrize('entry', ['build', 'replay', '_identity'])
def test_private_guard_changes_only_one_ast_constant_originals_unmodified(entry):
    from egrs.remain049.sources import extend_index_guard, helpers
    from benchmark.remaining_goals import selected_build, selected_replay
    from benchmark.remaining_goals.headless import scoped_sources
    module = {'build': selected_build, 'replay': selected_replay, '_identity': scoped_sources}[entry]
    original = getattr(module, entry)
    before = inspect.getsource(original)
    result = extend_index_guard(original, dict(vars(module)))
    assert result is not original and inspect.getsource(original) == before
    assert 50 in result.__code__.co_consts
    if entry == '_identity':
        result('two_pots', 49, 'nine-mask10')
        with pytest.raises(ValueError): original('two_pots', 49, 'nine-mask10')
        with pytest.raises(ValueError): result('two_pots', 50, 'nine-mask10')
    assert helpers()['_identity'] is not scoped_sources._identity


@pytest.mark.parametrize('index', [-1, 50, True, '10'])
def test_bad_indices_rejected_without_io(index):
    from egrs.remain049.sources import resolve
    with pytest.raises(ValueError): resolve({}, 'basket', index, {})


def test_new50_legacy_source_guard_does_not_change_old_scoped_catalogue():
    from egrs.remain049.sources import helpers
    from benchmark.remaining_goals.headless import scoped_sources
    private = helpers()
    private['_identity']('basket', 49, 'selected-mask10')
    with pytest.raises(ValueError): scoped_sources._identity('basket', 9, 'selected-mask10')
    with pytest.raises(ValueError): private['_identity']('missing', 49, 'selected-mask10')


def _record(episode, path, classification='success'):
    from egrs.remain049.sources import sha
    fields = ('episode_id','task_id','suite','initial_state_index','initial_mask')
    return {'primary': {**{k:episode[k] for k in fields}, 'execution_status':'completed',
                        'classification':classification}, 'source': {
        'model_identity': {'policy_metadata': {'checkpoint_source': 'fake-fixed'}},
        'input_evidence_level': 'synthetic_test_only', 'run_path': str(path.parent),
        'verified_files': [{'path':str(path),'sha256':sha(path)}]}}


@pytest.mark.parametrize('classification,success', [('success', True), ('failure',False), ('unknown',False)])
def test_per_episode_live_sr_is_original_binary_mapping(tmp_path, classification, success, capsys):
    from egrs.remain049.evaluation import Live
    from egrs.remain049.sources import expected
    episode = expected()[0]
    raw = tmp_path/'raw.json';raw.write_text('{}')
    live = Live(tmp_path, 'base', expected())
    live.add(episode, _record(episode,raw,classification))
    assert live.outcomes[episode['episode_id']] is success
    progress = json.loads((tmp_path/'progress.json').read_text())
    assert progress['completed'] == 1 and progress['successes'] == int(success)
    assert progress['live_compliant_SR_percent'] == (100 if success else 0)
    assert 'overall_SR=' in capsys.readouterr().out
    with pytest.raises(ValueError, match='Duplicate'):live.add(episode,_record(episode,raw))


def test_corrupted_raw_never_counted_as_failure(tmp_path):
    from egrs.remain049.evaluation import Live
    from egrs.remain049.sources import expected
    episode = expected()[0];raw=tmp_path/'raw.json';raw.write_text('{}')
    record = _record(episode,raw);raw.write_text('changed')
    live = Live(tmp_path,'base',expected())
    with pytest.raises(ValueError,match='mapper'):live.add(episode,record)
    assert not live.records and not live.outcomes


def test_native_worker_gets_no_status_hint_no_oracle():
    from egrs.remain049.evaluation import _worker
    frozen = {'model':'base','runtime': {'policy_factory':'original:factory'},'config':{'adapter':'fixed-h1'}}
    assert _worker(frozen) == frozen['runtime']
    frozen['model']='h1';worker=_worker(frozen)
    assert worker['hint043_checkpoint_step'] == 3000 and worker['hint043_arm'] == 'h1'
    assert not {'initial_mask','goals','status','hint','remaining_goals','source_bank'} & worker.keys()
    assert frozen['runtime'] == {'policy_factory':'original:factory'}


@pytest.mark.parametrize('model', ['base','h1'])
def test_full450_one_shared_fake_worker_immediate450_updates(tmp_path, monkeypatch, model, capsys):
    from egrs.remain049 import evaluation as ev
    from egrs.remain049.sources import expected,write
    from benchmark.remaining_goals import isolated_policy
    population = expected()
    frozen={'schema_version':ev.SCHEMA,'model':model,'expected':population,
            'sources':[{'episodes':[e]} for e in population], 'runtime':{},'adapter_identity':None,
            'source_bank_sha256':'a'*64,'plan_sha256':'b'*64,'config':{'adapter':'fake'}}
    monkeypatch.setattr(ev,'protect_output',lambda *a,**k:None)
    monkeypatch.setattr(ev,'plan',lambda *a:deepcopy(frozen))
    monkeypatch.setattr(ev,'helpers',lambda:{})
    monkeypatch.setattr(ev,'_verify_model',lambda *a:None)
    workers=[];calls=[]
    class Policy:
        def __init__(self,cfg):self.provenance={};self.closed=False;workers.append(self)
        def close(self):self.closed=True
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    def execute(folder,source,frozen,policy,scoped):
        folder.mkdir(parents=True);raw=folder/'raw.json';raw.write_text('{}')
        episode=source['episodes'][0];calls.append((episode['episode_id'],policy))
        return _record(episode,raw,'success' if episode['initial_state_index']%2==0 else 'failure')
    monkeypatch.setattr(ev,'execute_episode',execute)
    result=ev.run({'source_bank':str(tmp_path/'bank')},tmp_path/'eval',model)
    assert result['counts']['formal_SR']=={'numerator':225,'denominator':450,'percent':50.0}
    assert len(workers)==1 and workers[0].closed and len(calls)==450
    assert all(p is workers[0] for _,p in calls)
    assert capsys.readouterr().out.count('overall_SR=')==450
    assert len(result['tasks'])==9 and all(t['formal_SR']['denominator']==50 for t in result['tasks'])


def test_technical_pause_retains_completed_and_no_fake450_score(tmp_path,monkeypatch):
    from egrs.remain049 import evaluation as ev
    from egrs.remain049.sources import expected
    from benchmark.remaining_goals import isolated_policy
    population=expected();frozen={'schema_version':ev.SCHEMA,'model':'base','expected':population,
        'sources':[{'episodes':[e]} for e in population],'runtime':{},'adapter_identity':None,
        'source_bank_sha256':'a'*64,'plan_sha256':'b'*64,'config':{}}
    monkeypatch.setattr(ev,'protect_output',lambda *a,**k:None);monkeypatch.setattr(ev,'plan',lambda *a:frozen)
    monkeypatch.setattr(ev,'helpers',lambda:{});monkeypatch.setattr(ev,'_verify_model',lambda *a:None)
    class Policy:
        provenance={}
        def __init__(self,cfg):pass
        def close(self):pass
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    def execute(folder,source,*args):
        if source['episodes'][0]['initial_state_index']==1:raise RuntimeError('synthetic pause')
        folder.mkdir(parents=True);p=folder/'raw.json';p.write_text('{}');return _record(source['episodes'][0],p)
    monkeypatch.setattr(ev,'execute_episode',execute)
    with pytest.raises(RuntimeError,match='synthetic pause'):ev.run({'source_bank':str(tmp_path/'bank')},tmp_path/'eval','base')
    report=json.loads((tmp_path/'eval/summary.json').read_text())
    assert report['counts']['completed']==1 and report['counts']['formal_SR'] is None
    assert report['counts']['live_completed_SR']['percent']==100
    assert report['software_exit']=='incomplete'


def test_options_keep_frozen_three_recipes():
    from egrs.remain049.preparation import _options
    assert _options('basket')=={}
    assert _options('bowl_drawer_close')['construction_method'].endswith('_v2')
    assert 'construction_method' not in _options('two_pots')
    assert _options('mug_microwave_close')['construction_method'].endswith('_v3')
    assert 'stability_profile' in _options('mug_microwave_close')


def test_prepare_reuses90_only_generates360_and_no_implicit_retries(tmp_path,monkeypatch):
    from egrs.remain049 import preparation as prep
    from egrs.remain049 import evaluation as ev
    monkeypatch.setattr(prep,'activate',lambda cfg:{'synthetic':True});monkeypatch.setattr(prep,'helpers',lambda:{})
    monkeypatch.setattr(ev,'protect_output',lambda *a,**k:None)
    population=prep.expected();old={(r['task_id'],r['initial_state_index']):{'original':'fixed'} for r in population if r['initial_state_index']<10}
    monkeypatch.setattr(prep,'original_origins',lambda cfg:old)
    monkeypatch.setattr(prep,'resolve',lambda *a:{'source_plan_sha256':'c'*64})
    calls=[]
    def generate(row,root,dispatch,scoped,save):
        assert row['initial_state_index']>=10;calls.append(row['episode_id'])
        if row['initial_state_index']==49 and row['task_id']=='basket':raise ValueError('retained fail')
        row.update(status='ready',source_plan_sha256='c'*64,origin={'new':'fixed'})
    monkeypatch.setattr(prep,'_generate',generate)
    report=prep.prepare({},tmp_path/'bank')
    assert len(calls)==360 and report['ready']==449 and report['failed']==1 and not report['complete']
    assert report['model_rollouts']==0
    report2=prep.prepare({},tmp_path/'bank',continuation=True)
    assert len(calls)==360 and report2['failed']==1


def test_compare_requires_same_paired_source_bank(tmp_path):
    from egrs.remain049.evaluation import compare,SCHEMA
    from egrs.remain049.sources import write
    def report(model):return {'schema_version':SCHEMA,'model':model,'source_bank_sha256':'a'*64,
        'counts':{'completed':450,'formal_SR':{'numerator':1,'denominator':450,'percent':100/450}},
        'episodes':[{'episode_id':'fixed','success':True}],'tasks':[]}
    for model in ('base','h1'):write(tmp_path/model/'summary.json',report(model))
    assert compare(tmp_path/'base',tmp_path/'h1',tmp_path/'comparison.json')['delta_pp']==0
    changed=report('h1');changed['source_bank_sha256']='b'*64;write(tmp_path/'h1/summary.json',changed)
    with pytest.raises(ValueError,match='paired'):compare(tmp_path/'base',tmp_path/'h1',tmp_path/'bad.json')


def test_producer_dependencies_are_exact_legacy_six_and_current_new_three():
    from egrs.remain049.sources import producers,helpers
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch
    dispatch=describe_dispatch(os.environ['EGRS049_LEGACY'],os.environ['EGRS049_CORE'])
    old=producers('basket',dispatch,helpers())
    new=producers('two_pots',dispatch,helpers())
    assert Path(old[0].__file__).resolve().is_relative_to(Path(os.environ['EGRS049_LEGACY']).resolve())
    assert Path(new[0].__file__).resolve().is_relative_to(Path(os.environ['EGRS049_CORE']).resolve())
    assert old[2].__globals__['_backend']() is old[3]
    assert new[2].__globals__['_backend']() is new[3]


@pytest.mark.parametrize('protocol,execution_protocol',[('selected-mask10','mask10'),('nine-mask10','nine-mask10')])
def test_one_episode_calls_original_rollout_limits_and_preserves_video(tmp_path,monkeypatch,protocol,execution_protocol):
    from types import SimpleNamespace
    from egrs.remain049 import evaluation as ev
    from egrs.remain049.sources import expected,sha
    from benchmark.remaining_goals.headless import workflow,runner,evidence
    from egrs.trajectory_augmentation import environment_dispatch
    episode=expected()[0];source={'episodes':[episode],'protocol':protocol,'protocol_version':'same-core-version',
        'environment_config':{'environment':{'fake':'exact'}},'source_plan_sha256':'s'*64}
    frozen={'runtime':{},'plan_sha256':'p'*64,'dispatch':{},'proxy_coordination':{},'adapter_identity':None}
    env=SimpleNamespace(identity={'fake':'exact'},closed=False)
    def close():env.closed=True
    env.close=close
    monkeypatch.setattr(ev,'_verify_model',lambda *a:None)
    monkeypatch.setattr(workflow,'evidence_identity',lambda *a:{'same':'identity'})
    monkeypatch.setattr(workflow,'make_recorder',lambda *a:SimpleNamespace(close=lambda:None))
    monkeypatch.setattr(evidence,'HeadlessEvidence',lambda *a:object())
    monkeypatch.setattr(environment_dispatch,'make_environment',lambda *a:env)
    calls=[]
    def rollout(actual,policy,e,**kw):
        assert actual is env and e==episode
        assert {k:kw[k] for k in ('horizon','confirmation_steps','max_chunk_steps','protocol')}=={
            'horizon':520,'confirmation_steps':4,'max_chunk_steps':8,'protocol':execution_protocol}
        folder=tmp_path/'episode';p=folder/'videos'/(e['episode_id']+'.mp4');p.parent.mkdir();p.write_bytes(b'fake video')
        calls.append(kw)
        return {'status':'completed','video':{'status':'saved'}}
    monkeypatch.setattr(runner,'run_episode',rollout)
    checked=[]
    monkeypatch.setattr(ev,'verify_episode',lambda *a:checked.append(a) or {'original':'score'})
    scoped={'archive_source':lambda folder,source:folder/'source'}
    result=ev.execute_episode(tmp_path/'episode',source,frozen,SimpleNamespace(provenance={}),scoped)
    assert result=={'original':'score'} and len(calls)==1 and len(checked)==1 and env.closed
    metadata=json.loads((tmp_path/'episode/task_run.json').read_text())
    assert metadata['status']=='completed' and not metadata['missing']
    raw=json.loads((tmp_path/'episode'/metadata['results'][0]['path']).read_text())
    assert raw['video']['sha256']==sha(tmp_path/'episode'/raw['video']['path'])
