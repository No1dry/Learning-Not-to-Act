"""Strict explicit continuation with fake parent readers, never native/model."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from test_trajectory_evaluation import core,ready_config,adapter


def _write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


@pytest.fixture
def parent003(ready_config,tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev,continuation as module
    from egrs.augmentation.data import file_sha256
    from egrs.trajectory_augmentation import environment_dispatch
    plan=ev.build_plan(ready_config)
    plan['schema_version']=ev.SCHEMA_V2;plan['config']['schema_version']=ev.SCHEMA_V2
    plan['environment_dispatch']={'synthetic':True}
    plan['adapter_identity']['adapter_sha256']='a'*64
    plan['plan_sha256']=ev._hash({k:v for k,v in plan.items() if k!='plan_sha256'})
    monkeypatch.setattr(module,'PARENT_PLAN_SHA',plan['plan_sha256'])
    monkeypatch.setattr(module,'ADAPTER_SHA','a'*64)
    monkeypatch.setattr(environment_dispatch,'validate_dispatch',lambda value:value)
    parent=tmp_path/'eval003';parent.mkdir()
    _write(parent/'plan.json',plan)
    loaded={'actual_model_components':'fixed'}
    batch={'schema_version':ev.SCHEMA_V2,'plan_sha256':plan['plan_sha256'],'loaded_base_identity':loaded,'tasks':{}}
    for index,item in enumerate(plan['tasks'][:7]):
        complete=index<6;folder=parent/'tasks'/item['key'];folder.mkdir(parents=True)
        raw=[]
        for i,ep in enumerate(item['source']['episodes']):
            result={'episode_id':ep['episode_id'],'status':'completed' if complete else 'runtime_error',
                'n_steps':5 if complete else 0,'executed_actions':[{}]*5 if complete else [],
                'synthetic_success':bool(i%2)}
            _write(folder/'raw'/f'{i}.json',result);raw.append(result)
        metadata={'status':'completed' if complete else 'technical_pause','missing':[],
            'protocol_version':'synthetic-original-protocol','error':None if complete else 'proxy transition',
            'model_runtime':{'policy_metadata':{'method_adapter':adapter()}},'results':raw,
            'runtime_config':plan['base_runtime']}
        _write(folder/'task_run.json',metadata)
        _write(folder/'environment_dispatch.json',{'actual_original_implementation':True})
        (folder/'video.mp4').write_bytes(b'fake video bytes')
        (folder/'source').mkdir();(folder/'source/original.json').write_bytes(b'fixed source archive')
        batch['tasks'][item['key']]={'status':metadata['status'],'error':metadata['error'],
            'environment_dispatch_sha256':file_sha256(folder/'environment_dispatch.json')}
    _write(parent/'batch.json',batch)
    _write(parent/'summary.json',{'historical_stage_successes':30,'completed':60})
    (parent/'report.md').write_text('Original parent stage report',encoding='utf-8')
    calls=[]
    def reader(folder,item,parent_plan,model_identity=None,**kwargs):
        assert parent_plan['plan_sha256']==plan['plan_sha256'] and model_identity==loaded
        assert kwargs['environment_record_sha256']==batch['tasks'][item['key']]['environment_dispatch_sha256']
        calls.append(item['key'])
        value=json.loads((Path(folder)/'task_run.json').read_text())
        return value,value['results']
    monkeypatch.setattr(ev,'_read_task',reader)
    from benchmark.remaining_goals.headless import offline_scoring
    def score(episode,raw,*,condition,source):
        return {'condition':condition,'primary':{'episode_id':episode['episode_id'],
            'classification':'success' if raw['synthetic_success'] else 'failure'},'source':deepcopy(source)}
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    new=deepcopy(plan);new['schema_version']='task035-dual-condition-eval-v3'
    new['config']['schema_version']=new['schema_version'];new['proxy_coordination']={'new_method_protocol':True}
    return parent,new,calls


def test_all60_success_and_failure_inherited_remaining120_in_order(parent003):
    from egrs.trajectory_augmentation.continuation import prepare_continuation,verify_continuation
    parent,new,calls=parent003
    descriptor=prepare_continuation(parent,new)
    new['continuation']=descriptor;new['plan_sha256']='new-child-hash-is-not-parent-hash'
    checked=verify_continuation(descriptor,new)
    assert len(checked['records']['10'])==60 and checked['records']['00']=={}
    assert sum(r['primary']['classification']=='success' for r in checked['records']['10'].values())==30
    assert all(r['source']['new_execution'] is False for r in checked['records']['10'].values())
    assert len(descriptor['inherited_task_keys'])==6 and len(descriptor['inherited_episode_ids'])==60
    assert descriptor['remaining_task_keys']==[t['key'] for t in new['tasks'][6:]]
    assert len(descriptor['remaining_episode_ids'])==120
    assert descriptor['new_execution_budget']=={'10':30,'00':90,'total':120}
    assert len(descriptor['technical_attempts'])==1
    assert descriptor['technical_attempts'][0]['n_steps']==0
    assert len(calls)==14  # Both file-only passes use each original reader, including the zero-step error.


@pytest.mark.parametrize('changed',['adapter','runtime','source','video','sidecar','summary','batch'])
def test_continuation_rejects_incompatible_or_changed_parent(parent003,changed):
    from egrs.trajectory_augmentation.continuation import prepare_continuation,verify_continuation
    parent,new,_=parent003
    descriptor=prepare_continuation(parent,new)
    if changed=='adapter':new['adapter_identity']['adapter_sha256']='b'*64
    elif changed=='runtime':new['base_runtime']['new_component']='foreign'
    elif changed=='source':new['tasks'][0]['source']['episodes'][0]['instruction']='changed'
    else:
        path={'video':parent/'tasks'/new['tasks'][0]['key']/'video.mp4',
            'sidecar':parent/'tasks'/new['tasks'][0]['key']/'environment_dispatch.json',
            'summary':parent/'summary.json','batch':parent/'batch.json'}[changed]
        path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):verify_continuation(descriptor,new)


def test_wrong_parent_plan_and_additional_completed_population_rejected(parent003,monkeypatch):
    from egrs.trajectory_augmentation import continuation as module
    parent,new,_=parent003
    monkeypatch.setattr(module,'PARENT_PLAN_SHA','f'*64)
    with pytest.raises(ValueError,match='parent'):module.prepare_continuation(parent,new)


@pytest.mark.parametrize('changed',['missing_completed','extra_completed','technical_action'])
def test_partial_or_additional_parent_execution_is_not_silently_selected(parent003,changed):
    from egrs.trajectory_augmentation.continuation import prepare_continuation
    parent,new,_=parent003
    index=0 if changed=='missing_completed' else 6
    item=new['tasks'][index];path=parent/'tasks'/item['key']/'task_run.json'
    metadata=json.loads(path.read_text())
    if changed=='missing_completed':metadata['results'].pop()
    elif changed=='extra_completed':
        metadata['status']='completed';metadata['results'][0]['status']='completed'
    else:
        metadata['results'][0].update(n_steps=1,executed_actions=[{}])
    _write(path,metadata)
    with pytest.raises(ValueError):prepare_continuation(parent,new)
