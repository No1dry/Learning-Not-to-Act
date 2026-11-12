"""041 retains original180 sources/scoring while loading one041 student only."""
from copy import deepcopy
import json
import sys
from types import ModuleType

import pytest

from test_trajectory_evaluation import core,ready_config
from test_retention_evaluation import config036
from test_retention041_identity import stage_sources,calls


@pytest.fixture
def config041(config036,stage_sources,tmp_path):
    from egrs.retention041 import adapter,evaluation
    policy,_,_,stage=stage_sources
    paths={}
    for arm in ('r0','r1'):
        paths[arm]=tmp_path/('final-'+arm)
        adapter.save_adapter(policy,paths[arm],experiment_arm=arm,update=1000,
            index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
            reference_calls=calls(8000,1024),student_calls=calls(22000,2560,24560),
            old10_calls=calls(40 if arm=='r1' else 0,budget=4000 if arm=='r1' else 0))
    def write(arm):
        cfg=json.loads(config036.read_text())
        cfg.update(schema_version=evaluation.SCHEMA,group=evaluation.GROUP,
            arm='c1',experiment_arm=arm,adapter=str(paths[arm]))
        config036.write_text(json.dumps(cfg));return config036
    return write,paths


@pytest.mark.parametrize('arm',['r0','r1'])
def test041_plan_keeps_original_180_population_and_single_student_worker(config041,arm):
    from egrs.retention041 import evaluation
    write,_=config041
    plan=evaluation.build_plan(write(arm),experiment_arm=arm)
    assert plan['arm']=='c1' and plan['experiment_arm']==arm
    assert plan['policy_factory']=='egrs.retention041.policy:make_policy'
    assert plan['budget']=={'10':90,'00':90,'total':180,'policy_seed':7,
        'max_chunk_steps':8,'horizon':520,'video':'all','raw_queries_actions':'all'}
    assert not plan['simulation_created'] and not plan['weights_loaded']
    assert sum(len(x['source']['episodes']) for x in plan['tasks'])==180
    with pytest.raises(ValueError,match='arm'):
        evaluation.build_plan(write(arm),experiment_arm='r1' if arm=='r0' else 'r0')


def test041_policy_uses_new_reader_one_base_and_original_predict(stage_sources,tmp_path,monkeypatch):
    from egrs.retention041 import adapter,policy as new
    from egrs.task_control.policy import TaskControlPolicy
    policy,_,_,stage=stage_sources
    directory=tmp_path/'final'
    identity=adapter.save_adapter(policy,directory,experiment_arm='r1',update=1000,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('r1'),
        reference_calls=calls(8000),student_calls=calls(22000,budget=24560),old10_calls=calls(0,budget=4000))
    policy.close=lambda:None
    created=[]
    loader=ModuleType('benchmark.remaining_goals.adapters.openvla_oft')
    def factory(config):created.append(config);return policy
    loader.OpenVLAOFTPolicy=factory
    monkeypatch.setitem(sys.modules,loader.__name__,loader)
    transfer=ModuleType('benchmark.remaining_goals.adapters.oft_transfer');transfer.FACTORY='original:loader'
    monkeypatch.setitem(sys.modules,transfer.__name__,transfer)
    wrapper=new.make_policy({'method_adapter':str(directory),'task_control_arm':'c1','experiment_arm':'r1'})
    assert len(created)==1 and created[0]=={'policy_factory':'original:loader'}
    assert wrapper.metadata['method_adapter']==identity
    assert wrapper.metadata['task_control_arm']=='c1' and wrapper.metadata['experiment_arm']=='r1'
    assert new.Retention041Policy.predict is TaskControlPolicy.predict
    assert not any(p.requires_grad for p in policy.model.parameters())


@pytest.mark.parametrize('arm',['r0','r1'])
def test_fake041_execution_verifies_180_and_binary_scoring_without_teacher(config041,tmp_path,monkeypatch,arm):
    from egrs.retention041 import evaluation as ev,adapter
    from egrs.retention import evaluation as engine
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring,planning,workflow
    write,paths=config041;config=write(arm);identity=adapter.read_adapter_identity(paths[arm])
    workers=[];executed=[]
    class Policy:
        def __init__(self,config):
            assert config['policy_factory']=='egrs.retention041.policy:make_policy'
            assert config['task_control_arm']=='c1' and config['experiment_arm']==arm
            assert not {'teacher_adapter','teacher_identity','condition','task_id','source_id'}&set(config)
            self.provenance={'policy_metadata':{'method_adapter':identity,'unnorm_key':'libero_10_no_noops'}}
            workers.append(self)
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        assert policy is workers[0]
        executed.extend(item['source']['episodes']);folder.mkdir(parents=True)
        refs=[]
        for i,e in enumerate(item['source']['episodes']):
            raw={'episode_id':e['episode_id'],'status':'completed'}
            path=folder/f'{i}.json';path.write_text(json.dumps(raw))
            refs.append({'path':path.name,'sha256':planning.file_sha(path)})
        meta={'status':'completed','error':None,'results':refs,'model_runtime':policy.provenance,
            'runtime_config':plan['base_runtime'],'protocol_version':'remaining-headless-normal00-control-v1'}
        (folder/'task_run.json').write_text(json.dumps(meta))
        (folder/'environment_dispatch.json').write_text('{}');bind({'actual':'pinned base'})
        return meta
    def read(folder,*args):
        meta=json.loads((folder/'task_run.json').read_text())
        return meta,[json.loads((folder/r['path']).read_text()) for r in meta['results']]
    def score(episode,raw,*,condition,source):
        row={**episode,'execution_status':'completed','classification':'unknown' if condition=='10' else 'success',
            'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
        return {'condition':condition,'primary':row,'legacy':dict(row),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(engine,'_execute_task',execute);monkeypatch.setattr(engine,'_read_task',read)
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    def write_json(path,value,*,update=False):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w' if update else 'x',encoding='utf-8') as stream:json.dump(value,stream,allow_nan=False)
    monkeypatch.setattr(workflow,'write_json',write_json)
    out=tmp_path/('run-'+arm)
    result=ev.run(config,out,experiment_arm=arm)
    assert len(workers)==1 and len(executed)==180 and result['formal_complete']
    assert result['arm']=='c1' and result['experiment_arm']==arm
    assert result['conditions']['10']['formal_SR']['numerator']==0
    assert result['conditions']['00']['formal_SR']['numerator']==90
    with pytest.raises(FileExistsError):ev.run(config,out,experiment_arm=arm)
