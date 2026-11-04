"""Method-only dispatch wiring; native and model boundaries stay fake."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_trajectory_evaluation import core,ready_config,adapter


def test_v2_plan_binds_full_queue_120_old_and60_new(ready_config,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev,environment_dispatch as dispatch
    from benchmark.remaining_goals.headless import planning,scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    old,scoped=planning.source_plan,scoped_sources.resolve_source
    def add_environment(source,legacy):
        source['environment_config']={'environment':{'name':'libero','fingerprint':'old' if legacy else 'new','lock':{}}}
        source['source_plan_sha256']=planning.canonical_hash({k:v for k,v in source.items() if k!='source_plan_sha256'})
        return source
    monkeypatch.setattr(planning,'source_plan',lambda task,*a,**kw:add_environment(old(task,*a,**kw),True))
    monkeypatch.setattr(scoped_sources,'resolve_source',lambda protocol,task,*a:add_environment(scoped(protocol,task,*a),task in REUSE_TASKS))
    monkeypatch.setattr(dispatch,'describe_dispatch',lambda *a:{'identity':'d'*64})
    monkeypatch.setattr(dispatch,'binding_for',lambda environment,descriptor:{
        'implementation':environment['fingerprint'],'expected_environment':deepcopy(environment)})
    cfg=json.loads(ready_config.read_text());cfg.update(schema_version=ev.SCHEMA_V2,
        environment_dispatch={'legacy_root':str(tmp_path/'old')})
    ready_config.write_text(json.dumps(cfg))
    plan=ev.build_plan(ready_config)
    assert sum(len(t['source']['episodes']) for t in plan['tasks'] if t['environment_binding']['implementation']=='old')==120
    assert sum(len(t['source']['episodes']) for t in plan['tasks'] if t['environment_binding']['implementation']=='new')==60
    assert len(plan['tasks'])==126 and plan['budget']['total']==180
    assert plan['adapter_identity']==adapter()
    from benchmark.remaining_goals import isolated_policy
    policies=[];calls=[]
    class Policy:
        def __init__(self,cfg):
            assert not {'condition','environment_dispatch'}&cfg.keys()
            self.provenance={'policy_metadata':{'method_adapter':adapter()}};policies.append(self)
        def close(self):pass
    def execute(directory,item,plan,bind,policy):
        calls.append((item,policy));Path(directory).mkdir(parents=True)
        (Path(directory)/'environment_dispatch.json').write_text('{}')
        return {'status':'completed','error':None}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(ev,'_run_dispatched_task',execute)
    monkeypatch.setattr(ev,'inspect_run',lambda _: {})
    monkeypatch.setattr(ev,'_save_report',lambda *a:None)
    ev.run(ready_config,tmp_path/'new-eval')
    assert len(calls)==126 and len(policies)==1 and all(p is policies[0] for _,p in calls)
    assert sum(len(t['source']['episodes']) for t,_ in calls)==180


def test_dispatch_factory_is_local_and_actual_identity_is_archived(core,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev,environment_dispatch as dispatch
    from benchmark.remaining_goals.headless import workflow
    expected={'name':'libero','fingerprint':'fixed','lock':{'synthetic':True}}
    binding={'implementation':'old','expected_environment':expected}
    monkeypatch.setattr(dispatch,'binding_for',lambda *a:binding)
    monkeypatch.setattr(dispatch,'make_environment',lambda config,descriptor:SimpleNamespace(identity=deepcopy(expected)))
    def run_task(directory,source,runtime,batch_identity,bind_model,*,scoped=False,shared_policy=None):
        Path(directory).mkdir()
        # Deliberately resolved from this function's globals, exactly like core.
        env=make_environment(source['environment_config'])
        assert env.identity==expected
        return {'status':'completed','error':None}
    monkeypatch.setattr(workflow,'_run_task',run_task)
    original_factory=workflow.make_environment
    source={'environment_config':{'environment':expected},'source_plan_sha256':'s'*64}
    item={'source':source,'scoped':False,'environment_binding':binding}
    plan={'environment_dispatch':{'identity':'d'*64},'plan_sha256':'p'*64,'base_runtime':{}}
    folder=tmp_path/'task'
    result=ev._run_dispatched_task(folder,item,plan,lambda _:None,object())
    assert result['status']=='completed' and workflow.make_environment is original_factory
    record=json.loads((folder/'environment_dispatch.json').read_text())
    assert record['status']=='constructed' and record['actual_environment']==expected
    digest=ev._file_sha(folder/'environment_dispatch.json')
    ev._verify_environment_record(folder,item,plan,digest,result)
    record['binding']['implementation']='new'
    (folder/'environment_dispatch.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='dispatch'):
        ev._verify_environment_record(folder,item,plan,ev._file_sha(folder/'environment_dispatch.json'),result)


def test_old_v1_zero_action_initialization_error_stays_unresolved(ready_config,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev
    plan=ev.build_plan(ready_config);root=tmp_path/'old-eval001';root.mkdir()
    (root/'plan.json').write_text(json.dumps(plan))
    (root/'batch.json').write_text(json.dumps({'schema_version':ev.SCHEMA,'plan_sha256':plan['plan_sha256'],
        'tasks':{},'loaded_base_identity':{'synthetic':True}}))
    item=plan['tasks'][0];(root/'tasks'/item['key']).mkdir(parents=True)
    monkeypatch.setattr(ev,'_read_task',lambda *a,**kw:({'status':'technical_pause',
        'phase':'environment_initialize','error':'ValueError: runtime LIBERO fingerprint differs from the frozen manifest',
        'missing':[e['episode_id'] for e in item['source']['episodes']]},[]))
    report=ev.inspect_run(root)
    assert report['conditions']['10']['formal_SR'] is None
    issues=[e['detail'] for e in report['conditions']['10']['report']['integrity_errors'] if e['code']=='artifact_error']
    assert len(issues)==10 and all(i['phase']=='environment_initialize' for i in issues)
    assert all('fingerprint differs' in i['error'] for i in issues)
