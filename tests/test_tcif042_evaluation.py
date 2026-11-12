"""042 keeps original180 population and one current-frame student worker."""
from copy import deepcopy
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from test_trajectory_evaluation import core,ready_config
from test_retention_evaluation import config036
from test_tcif042_identity import source042,stage_sources,calls


@pytest.fixture
def config042(config036,source042,tmp_path):
    from egrs.tcif042 import adapter,evaluation
    policy,_,stage=source042;paths={}
    for arm in ('f0','f1'):
        paths[arm]=tmp_path/('final-'+arm)
        adapter.save_adapter(policy,paths[arm],experiment_arm=arm,update=1000,
            index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
            reference_calls=calls(8000,1024),student_calls=calls(22000,2560,24560))
    def write(arm):
        cfg=json.loads(config036.read_text())
        cfg.update(schema_version=evaluation.SCHEMA,group=evaluation.GROUP,
            arm='c1',experiment_arm=arm,adapter=str(paths[arm]))
        config036.write_text(json.dumps(cfg));return config036
    return write,paths


@pytest.mark.parametrize('arm',['f0','f1'])
def test_plan_preserves_fixed180_budget_sources_and_rejects_wrong_arm(config042,arm):
    from egrs.tcif042 import evaluation
    write,_=config042;plan=evaluation.build_plan(write(arm),experiment_arm=arm)
    assert plan['arm']=='c1' and plan['experiment_arm']==arm
    assert plan['policy_factory']=='egrs.tcif042.policy:make_policy'
    assert plan['budget']=={'10':90,'00':90,'total':180,'policy_seed':7,
        'max_chunk_steps':8,'horizon':520,'video':'all','raw_queries_actions':'all'}
    assert sum(len(t['source']['episodes']) for t in plan['tasks'])==180
    assert not plan['simulation_created'] and not plan['weights_loaded']
    with pytest.raises(ValueError,match='arm'):
        evaluation.build_plan(write(arm),experiment_arm='f1' if arm=='f0' else 'f0')


@pytest.mark.parametrize('arm',['f0','f1'])
def test_policy_loads_one_complete_student_installs_recorded_attention_and_uses042_prediction(source042,tmp_path,monkeypatch,core,arm):
    from egrs.tcif042 import adapter,policy as new
    from egrs.tcif042 import attention,oft
    from egrs.task_control.policy import TaskControlPolicy
    p,_,stage=source042;directory=tmp_path/('policy-'+arm)
    identity=adapter.save_adapter(p,directory,experiment_arm=arm,update=1000,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
        reference_calls=calls(8000),student_calls=calls(22000,budget=24560))
    p.close=lambda:None;created=[]
    loader=ModuleType('benchmark.remaining_goals.adapters.openvla_oft')
    def factory(config):created.append(config);return p
    loader.OpenVLAOFTPolicy=factory;monkeypatch.setitem(sys.modules,loader.__name__,loader)
    transfer=ModuleType('benchmark.remaining_goals.adapters.oft_transfer');transfer.FACTORY='original:loader'
    monkeypatch.setitem(sys.modules,transfer.__name__,transfer)
    def install(policy,experiment_arm):
        controller=SimpleNamespace(contract=deepcopy(stage(experiment_arm)['attention_contract']),
            runtime={'actual_attention_class':'CPU fake only','torch_version':'fixture'})
        policy._tcif042=controller;return controller
    monkeypatch.setattr(attention,'install_attention',install)
    wrapper=new.make_policy({'method_adapter':str(directory),'task_control_arm':'c1','experiment_arm':arm})
    assert len(created)==1 and created[0]=={'policy_factory':'original:loader'}
    assert wrapper.metadata['method_adapter']==identity and wrapper.metadata['experiment_arm']==arm
    assert wrapper.metadata['attention_runtime']['actual_attention_class']=='CPU fake only'
    assert wrapper.base._tcif042.contract==identity['attention_contract']
    assert not any(value.requires_grad for value in p.model.parameters())
    assert new.TCIF042Policy.predict is not TaskControlPolicy.predict
    # A normal prediction executes the042 preparation path, never old hardcodedoft.
    from benchmark.remaining_goals.adapters import openvla
    api=SimpleNamespace(get_libero_image=lambda raw:'front',get_libero_wrist_image=lambda raw:'wrist',
        quat2axisangle=lambda q:[0,0,0])
    p.api=api;p.torch=__import__('torch');p.reset=lambda:None
    p.model.norm_stats={'libero_10_no_noops':{'proprio':{}}}
    p.model._unnormalize_actions=lambda value,key:value
    raw={'robot0_eef_pos':[0,0,0],'robot0_eef_quat':[0,0,0,1],'robot0_gripper_qpos':[0,0]}
    monkeypatch.setattr(openvla,'_raw_observation',lambda *a,**k:raw)
    monkeypatch.setattr(openvla,'_instruction',lambda text:text)
    monkeypatch.setattr(openvla,'_action_array',lambda value,**kwargs:value)
    monkeypatch.setattr(openvla,'_decode_action',lambda api,value,**kwargs:value)
    utils=ModuleType('experiments.robot.openvla_utils');utils.normalize_proprio=lambda p,s:p
    monkeypatch.setitem(sys.modules,utils.__name__,utils)
    seen=[]
    def prediction(policy,item):
        import torch
        seen.append(item)
        return SimpleNamespace(actions=torch.zeros(1,8,7))
    monkeypatch.setattr(oft,'prediction',prediction)
    assert wrapper.predict({},'full original instruction').shape==(8,7)
    assert len(seen)==1 and set(seen[0])=={'images','instruction','proprio'}


def test_attention_contract_mismatch_fails_before_student_prediction(source042,tmp_path,monkeypatch):
    from egrs.tcif042 import adapter,attention
    p,_,stage=source042;target=tmp_path/'contract'
    adapter.save_adapter(p,target,experiment_arm='f1',update=1000,index_identity=adapter.INDEX_IDENTITY,
        stage_identity=stage('f1'),reference_calls=calls(8000),student_calls=calls(22000,budget=24560))
    monkeypatch.setattr(attention,'install_attention',lambda policy,arm:SimpleNamespace(contract={'backend':'wrong'},runtime={}))
    with pytest.raises(ValueError,match='contract'):adapter.attach_trained_adapter(p,target,experiment_arm='f1')


@pytest.mark.parametrize('arm',['f0','f1'])
def test_fake180_execution_keeps_one_student_no_reference_and_original_binary_reports(config042,tmp_path,monkeypatch,arm):
    from egrs.tcif042 import evaluation as ev,adapter
    from egrs.retention import evaluation as engine
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring,planning,workflow
    write,paths=config042;config=write(arm);identity=adapter.read_adapter_identity(paths[arm])
    workers=[];executed=[]
    class Policy:
        def __init__(self,config):
            assert config['policy_factory']=='egrs.tcif042.policy:make_policy'
            assert config['task_control_arm']=='c1' and config['experiment_arm']==arm
            assert not {'teacher_adapter','teacher_identity','reference_view','condition','task_id','source_id'}&set(config)
            self.provenance={'policy_metadata':{'method_adapter':identity,'unnorm_key':'libero_10_no_noops'}}
            workers.append(self)
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        assert policy is workers[0]
        executed.extend(item['source']['episodes']);folder.mkdir(parents=True);refs=[]
        for i,e in enumerate(item['source']['episodes']):
            raw={'episode_id':e['episode_id'],'status':'completed'};path=folder/f'{i}.json'
            path.write_text(json.dumps(raw));refs.append({'path':path.name,'sha256':planning.file_sha(path)})
        meta={'status':'completed','error':None,'results':refs,'model_runtime':policy.provenance,
            'runtime_config':plan['base_runtime'],'protocol_version':'remaining-headless-normal00-control-v1'}
        (folder/'task_run.json').write_text(json.dumps(meta));(folder/'environment_dispatch.json').write_text('{}')
        bind({'actual':'pinned base'});return meta
    def read(folder,*args):
        meta=json.loads((folder/'task_run.json').read_text())
        return meta,[json.loads((folder/r['path']).read_text()) for r in meta['results']]
    def score(episode,raw,*,condition,source):
        row={**episode,'execution_status':'completed','classification':'unknown' if condition=='10' else 'success',
            'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
        return {'condition':condition,'primary':row,'legacy':dict(row),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy);monkeypatch.setattr(engine,'_execute_task',execute)
    monkeypatch.setattr(engine,'_read_task',read);monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    def write_json(path,value,*,update=False):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w' if update else 'x',encoding='utf-8') as stream:json.dump(value,stream,allow_nan=False)
    monkeypatch.setattr(workflow,'write_json',write_json)
    output=tmp_path/('run-'+arm);report=ev.run(config,output,experiment_arm=arm)
    assert len(workers)==1 and len(executed)==180 and report['formal_complete']
    assert report['arm']=='c1' and report['experiment_arm']==arm
    assert report['conditions']['10']['formal_SR']['numerator']==0
    assert report['conditions']['00']['formal_SR']['numerator']==90
    assert (output/'report.md').read_text().startswith(f'# Task042 {arm} (base c1)')
    with pytest.raises(FileExistsError):ev.run(config,output,experiment_arm=arm)
