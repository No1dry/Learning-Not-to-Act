"""036 creates180 new episodes and verifies the whole population once."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from test_trajectory_evaluation import core,ready_config


def adapter036():
    from egrs.augmentation.adapter_identity import BASE_SOURCE,RETENTION_RECIPE
    return {'schema_version':'task036-oft-adapter-v1','group':'policy_retention_distillation',
        'recipe':'policy_retention_distillation','data_kind':'task036-retention-data-v1',
        'update':1000,'final_update':1000,'adapter_sha256':'a'*64,
        'export_identity':{key:'b'*64 for key in ('sources.json','rows.jsonl','report.json')},
        'reference_view':'shared_frozen_base_without_added_lora','reference_base':BASE_SOURCE,
        'training_recipe':deepcopy(RETENTION_RECIPE),
        'reference_calls':{'train':8000,'dev':1024,'total':9024,'budget':9024}}


@pytest.fixture
def config036(ready_config,tmp_path,monkeypatch):
    from egrs.retention import evaluation as ev
    from egrs.trajectory_augmentation import environment_dispatch as dispatch
    from egrs.augmentation import adapter_identity
    from benchmark.remaining_goals.headless import planning,scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    old,scoped=planning.source_plan,scoped_sources.resolve_source
    def environment(source,legacy):
        source['environment_config']={'environment':{'name':'libero','fingerprint':'old' if legacy else 'new','lock':{}}}
        source['source_plan_sha256']=planning.canonical_hash({k:v for k,v in source.items() if k!='source_plan_sha256'})
        return source
    monkeypatch.setattr(planning,'source_plan',lambda task,*a,**kw:environment(old(task,*a,**kw),True))
    monkeypatch.setattr(scoped_sources,'resolve_source',lambda protocol,task,*a:environment(scoped(protocol,task,*a),task in REUSE_TASKS))
    monkeypatch.setattr(dispatch,'describe_dispatch',lambda *a:{'identity':'d'*64})
    monkeypatch.setattr(dispatch,'validate_dispatch',lambda *a:None)
    monkeypatch.setattr(dispatch,'binding_for',lambda environment,descriptor:{'implementation':environment['fingerprint'],
        'expected_environment':deepcopy(environment)})
    monkeypatch.setattr(adapter_identity,'read_adapter_identity',lambda _:adapter036())
    cfg=json.loads(ready_config.read_text());cfg.update(schema_version=ev.SCHEMA,group=ev.GROUP,
        environment_dispatch={'legacy_root':str(tmp_path/'old')})
    ready_config.write_text(json.dumps(cfg))
    return ready_config


def test_new036_identity_plan_population_and_no_inheritance(config036):
    from egrs.retention import evaluation as ev
    plan=ev.build_plan(config036)
    assert plan['schema_version']==ev.SCHEMA and plan['adapter_identity']==adapter036()
    assert plan['budget']['total']==180 and len(plan['tasks'])==126
    assert sum(len(t['source']['episodes']) for t in plan['tasks'] if t['environment_binding']['implementation']=='old')==120
    assert sum(len(t['source']['episodes']) for t in plan['tasks'] if t['environment_binding']['implementation']=='new')==60
    assert 'continuation' not in plan
    from egrs.trajectory_augmentation.evaluation import validate_adapter as old_validator
    with pytest.raises(ValueError):old_validator(adapter036())
    bad=adapter036();bad['update']=750
    with pytest.raises(ValueError):ev.validate_adapter(bad)
    with pytest.raises(SystemExit):ev.main(['run','--config',str(config036),'--out','unused','--continue-from','old035'])


@pytest.mark.parametrize('mode',['complete','close_warning','pause','pause_close','pause_ledger'])
def test_new180_final_reader_once_progress_and_errors(config036,tmp_path,monkeypatch,capsys,mode):
    from egrs.retention import evaluation as ev
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring
    from egrs.augmentation.data import file_sha256
    policies=[];executed=[];read=[]
    class Policy:
        def __init__(self,cfg):
            assert not {'reference_view','condition','initial_mask','continuation'}&cfg.keys()
            self.provenance={'policy_metadata':{'method_adapter':adapter036(),'unnorm_key':'libero_10_no_noops'}}
            policies.append(self)
        def close(self):
            if mode in ('close_warning','pause_close'):raise RuntimeError('worker exited -15 during close')
    def execute(folder,item,plan,bind,policy):
        assert policy is policies[0]
        executed.append(item);folder=Path(folder);(folder/'raw').mkdir(parents=True)
        pause=mode in ('pause','pause_close','pause_ledger')
        rows=[];refs=[]
        for index,episode in enumerate(item['source']['episodes']):
            raw={'episode_id':episode['episode_id'],'status':'runtime_error' if pause else 'completed'}
            target=folder/'raw'/f'{index}.json';target.write_text(json.dumps(raw))
            refs.append({'episode_id':episode['episode_id'],'path':f'raw/{index}.json','sha256':file_sha256(target)})
            rows.append(raw)
            if pause:break
        metadata={'status':'technical_pause' if pause else 'completed','error':'inference failed' if pause else None,
            'phase':'episode_setup' if pause else 'completed','results':refs,
            'missing':[e['episode_id'] for e in item['source']['episodes'] if e['episode_id'] not in {r['episode_id'] for r in rows}],
            'model_runtime':policy.provenance,'runtime_config':plan['base_runtime'],
            'protocol_version':'remaining-headless-normal00-control-v1'}
        (folder/'task_run.json').write_text(json.dumps(metadata))
        (folder/'environment_dispatch.json').write_text('{}')
        bind({'actual':'same-base'})
        return metadata
    def reader(folder,item,plan,model_identity):
        read.append(item['key']);folder=Path(folder)
        metadata=json.loads((folder/'task_run.json').read_text())
        return metadata,[json.loads((folder/r['path']).read_text()) for r in metadata['results']]
    def score(episode,raw,*,condition,source):
        row={**episode,'execution_status':raw['status'],
            'classification':'success' if condition=='00' or episode['initial_state_index']%2==0 else 'failure',
            'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
        return {'condition':condition,'primary':row,'legacy':{**row,'classification':'failure'},'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(ev,'_execute_task',execute)
    monkeypatch.setattr(ev,'_read_task',reader)
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    if mode=='pause_ledger':
        from benchmark.remaining_goals.headless import workflow
        write=workflow.write_json
        def final_ledger_error(path,value,**kwargs):
            if Path(path).name=='batch.json' and 'execution_error' in value:
                raise OSError('final ledger unavailable')
            return write(path,value,**kwargs)
        monkeypatch.setattr(workflow,'write_json',final_ledger_error)
    out=tmp_path/'eval036'
    if mode=='complete':ev.run(config036,out)
    else:
        with pytest.raises(RuntimeError,match='inference failed' if mode.startswith('pause') else 'close'):
            ev.run(config036,out)
    assert len(policies)==1
    expected=1 if mode.startswith('pause') else 126
    assert len(executed)==expected and len(read)==expected and len(set(read))==expected
    report=json.loads((out/'summary.json').read_text());progress=json.loads((out/'progress.json').read_text())
    if mode.startswith('pause'):
        assert progress['status']!='completed' and report['conditions']['10']['formal_SR'] is None
        assert report['execution_error'] and report['conditions']['00']['formal_SR'] is None
    else:
        assert sum(len(t['source']['episodes']) for t in executed)==180
        assert report['conditions']['10']['formal_SR']['numerator']==45
        assert report['conditions']['00']['formal_SR']['numerator']==90
        assert progress['status']=='completed' and progress['model_completed']==180
        assert '100.00%' in capsys.readouterr().out
    if mode in ('close_warning','pause_close'):assert '-15' in report['cleanup_warning']
    if mode=='pause_ledger':assert 'final ledger unavailable' in report['ledger_warning']


def test_actual036_reader_reuses_original_archive_query_action_and_video_validation(tmp_path,monkeypatch,core):
    from egrs.retention import evaluation as ev
    from egrs.trajectory_augmentation import environment_dispatch as dispatch
    from benchmark.remaining_goals.headless import workflow,planning
    from tests.test_headless_workflow import configuration,execution
    from tests.test_headless_source_acceptance import make_source
    from tests.test_headless_runner import synthetic_measurement_validator
    synthetic_measurement_validator.__wrapped__(monkeypatch)
    runtime=planning.read_json(planning.read_json(configuration(tmp_path,monkeypatch))['runtime_config'])
    mp,rp,_,_=make_source(tmp_path/'source')
    source=planning.source_plan('basket',{'manifest':str(mp),'candidate_replay':str(rp)},acceptance=planning.MASK10_ACCEPTANCE)
    execution(monkeypatch);policy=workflow.make_policy(runtime)
    policy.provenance['policy_metadata']['method_adapter']=adapter036()
    plan={'schema_version':ev.SCHEMA,'plan_sha256':'c'*64,'base_runtime':runtime,'adapter_identity':adapter036(),
        'environment_dispatch':{'identity':'d'*64},'proxy_coordination':dispatch.coordination_identity()}
    folder=tmp_path/'executed'
    metadata=workflow._run_task(folder,source,runtime,plan['plan_sha256'],lambda _:None,shared_policy=policy)
    assert metadata['status']=='completed',metadata['error']
    binding={'implementation':'fake-env-boundary','expected_environment':source['environment_config']['environment']}
    item={'key':'10_basket','source':source,'scoped':False,'environment_binding':binding}
    monkeypatch.setattr(dispatch,'binding_for',lambda *a:deepcopy(binding))
    record={'schema_version':'task035-environment-dispatch-record-v1','plan_sha256':plan['plan_sha256'],
        'source_plan_sha256':source['source_plan_sha256'],'binding':binding,'status':'constructed',
        'actual_environment':binding['expected_environment'],'proxy_coordination':plan['proxy_coordination']}
    (folder/'environment_dispatch.json').write_text(json.dumps(record))
    plan['_batch_tasks']={'10_basket':{'environment_dispatch_sha256':planning.file_sha(folder/'environment_dispatch.json')}}
    _,results=ev._read_task(folder,item,plan,workflow.shared_model_identity(metadata['model_runtime']))
    assert len(results)==10 and all(r['queries'] and r['executed_actions'] for r in results)
    path=folder/results[0]['video']['path'];path.write_bytes(path.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='video'):
        ev._read_task(folder,item,plan,workflow.shared_model_identity(metadata['model_runtime']))
