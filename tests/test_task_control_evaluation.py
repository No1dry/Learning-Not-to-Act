"""Task038 plans retain strict legacy/scoped readers without loading a model."""
from copy import deepcopy
import json

import pytest

from test_trajectory_evaluation import core, ready_config
from test_retention_evaluation import config036


def adapter038(arm='c0'):
    return {'schema_version':'task038-oft-adapter-v1', 'group':'task_control_factorization',
            'recipe':'task_control_factorization', 'arm':arm, 'update':1000,
            'final_update':1000, 'adapter_sha256':'a'*64, 'index_identity':'b'*64}


@pytest.fixture
def config038(config036, monkeypatch):
    from egrs.task_control import evaluation as ev
    value=json.loads(config036.read_text())
    value.update(schema_version=ev.SCHEMA, group=ev.GROUP, arm='c0')
    config036.write_text(json.dumps(value))
    monkeypatch.setattr(ev, 'read_adapter_identity', lambda _:adapter038(value['arm']))
    return config036


def test_two_arms_plan_360_new_episodes_and_new_shared_policy(config038, monkeypatch):
    from egrs.task_control import evaluation as ev
    plans=[]
    for arm in ('c0','c1'):
        config=json.loads(config038.read_text());config['arm']=arm
        config038.write_text(json.dumps(config))
        monkeypatch.setattr(ev, 'read_adapter_identity', lambda _, arm=arm:adapter038(arm))
        plan=ev.build_plan(config038,arm=arm);plans.append(plan)
        assert plan['config']['arm']==arm
        assert plan['policy_factory']=='egrs.task_control.policy:make_policy'
        assert plan['budget']=={'10':90,'00':90,'total':180,'policy_seed':7,
            'max_chunk_steps':8,'horizon':520,'video':'all','raw_queries_actions':'all'}
        assert not plan['simulation_created'] and not plan['weights_loaded']
        assert plan['new_model_execution_only'] is True and 'continuation' not in plan
        assert {item['source']['protocol'] for item in plan['tasks'] if item['condition']=='00'}=={
            'normal00-control','nine-normal00'}
    assert sum(len(item['source']['episodes']) for plan in plans for item in plan['tasks'])==360
    assert plans[0]['plan_sha256']!=plans[1]['plan_sha256']


@pytest.mark.parametrize('change',[{'arm':'c1'},{'update':750},{'final_update':3000},
    {'group':'policy_retention_distillation'},{'schema_version':'task036-oft-adapter-v1'}])
def test_wrong_arm_or_nonfinal_adapter_rejected(config038,monkeypatch,change):
    from egrs.task_control import evaluation as ev
    monkeypatch.setattr(ev,'read_adapter_identity',lambda _:{**adapter038(),**change})
    with pytest.raises(ValueError,match='adapter|arm|1000'):
        ev.build_plan(config038,arm='c0')


def test_cli_arm_cannot_relabel_another_plan(config038):
    from egrs.task_control import evaluation as ev
    with pytest.raises(ValueError,match='arm'):
        ev.build_plan(config038,arm='c1')


def test_new_report_preserves_binary10_and_official00_denominators(core,tmp_path):
    from egrs.task_control import evaluation as ev
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.planning import file_sha
    proof=tmp_path/'proof.json';proof.write_text('synthetic verified evidence')
    records={'10':{},'00':{}}
    for bits in ('10','00'):
        for episode in expected_episodes('nine-mask10' if bits=='10' else 'nine-normal00'):
            row={**episode,'execution_status':'completed','classification':'unknown' if bits=='10' else 'success',
                'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
            records[bits][episode['episode_id']]={'condition':bits,'primary':row,
                'legacy':{**row,'classification':'failure'},'source':{
                    'model_identity':{'policy_metadata':{'method_adapter':adapter038('c1'),
                        'unnorm_key':'libero_10_no_noops'}},
                    'verified_files':[{'path':str(proof),'sha256':file_sha(proof)}],
                    'input_evidence_level':'synthetic verified fixture',
                    'original_protocol':'remaining-headless-normal00-control-v1'}}
    report=ev.make_report(records,adapter038('c1'))
    assert report['schema_version']==ev.SCHEMA and report['arm']=='c1'
    assert report['conditions']['10']['formal_SR']['denominator']==90
    assert report['conditions']['10']['formal_SR']['numerator']==0
    assert report['conditions']['00']['formal_SR']['denominator']==90
    assert report['conditions']['00']['formal_SR']['numerator']==90


def test_old_output_is_not_opened_or_overwritten(config038,tmp_path):
    from egrs.task_control import evaluation as ev
    previous=tmp_path/'old035';previous.mkdir()
    marker=previous/'summary.json';marker.write_text('preserved old failure and success')
    with pytest.raises(FileExistsError):
        ev.run(config038,previous,arm='c0')
    assert marker.read_text()=='preserved old failure and success'


@pytest.mark.parametrize('arm',['c0','c1'])
def test_fake_execution_keeps_shared_adapter_factory_and_verifies_180(config038,tmp_path,monkeypatch,arm):
    from egrs.task_control import evaluation as ev
    from egrs.retention import evaluation as engine
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring,planning,workflow
    cfg=json.loads(config038.read_text());cfg['arm']=arm;config038.write_text(json.dumps(cfg))
    monkeypatch.setattr(ev,'read_adapter_identity',lambda _:adapter038(arm))
    workers=[];executed=[]
    class Policy:
        def __init__(self,config):
            assert config['policy_factory']=='egrs.task_control.policy:make_policy'
            assert config['task_control_arm']==arm
            assert not {'condition','initial_mask','pair','labels','task_id','source_id'}&set(config)
            self.provenance={'policy_metadata':{'method_adapter':adapter038(arm),
                'unnorm_key':'libero_10_no_noops'}}
            workers.append(self)
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        assert policy is workers[0]
        executed.extend(item['source']['episodes']);folder.mkdir(parents=True)
        raws=[{'episode_id':e['episode_id'],'status':'completed'} for e in item['source']['episodes']]
        refs=[]
        for i,raw in enumerate(raws):
            path=folder/f'{i}.json';path.write_text(json.dumps(raw))
            refs.append({'path':path.name,'sha256':planning.file_sha(path)})
        metadata={'status':'completed','error':None,'results':refs,'model_runtime':policy.provenance,
                  'runtime_config':plan['base_runtime'],
                  'protocol_version':'remaining-headless-normal00-control-v1'}
        (folder/'task_run.json').write_text(json.dumps(metadata))
        (folder/'environment_dispatch.json').write_text('{}')
        bind({'actual':'unchanged pinned base'})
        return metadata
    def read(folder,*args):
        value=json.loads((folder/'task_run.json').read_text())
        return value,[json.loads((folder/r['path']).read_text()) for r in value['results']]
    def score(episode,raw,*,condition,source):
        row={**episode,'execution_status':'completed','classification':'success',
             'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
        return {'condition':condition,'primary':row,'legacy':dict(row),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(engine,'_execute_task',execute)
    monkeypatch.setattr(engine,'_read_task',read)
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    # This test covers our orchestration/identity/scoring, not the frozen core's
    # atomic-rename primitive (which can encounter WinError5 on this host).
    # Retain actual files and exclusive-new/update semantics at that boundary.
    def write_json(path,value,*,update=False):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w' if update else 'x',encoding='utf-8') as stream:
            json.dump(value,stream,allow_nan=False)
    monkeypatch.setattr(workflow,'write_json',write_json)
    result=ev.run(config038,tmp_path/'new038',arm=arm)
    assert len(workers)==1 and len(executed)==180
    assert result['arm']==arm and result['model_completed']==180 and result['formal_complete']
    assert result['conditions']['10']['formal_SR']['numerator']==90
    assert result['conditions']['00']['formal_SR']['numerator']==90
    assert (tmp_path/'new038/report.md').read_text(encoding='utf-8').startswith(f'# Task038 {arm}:')
