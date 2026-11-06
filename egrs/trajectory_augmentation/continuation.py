"""Explicit file-only inheritance of the fixed eval003 sixty completed episodes.

No score cache is serialized. Public verification rereads the parent's original
artifacts and readers; the old zero-step technical attempt is never inherited
as a model failure or converted into a completed episode.
"""
from copy import deepcopy
from pathlib import Path

from egrs.augmentation.data import identity,file_sha256,read_json

SCHEMA='task035-eval003-continuation-v1'
PARENT_PLAN_SHA='48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b'
ADAPTER_SHA='21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8'


def _require(value,message):
    if not value:raise ValueError('continuation '+message)


def _contract(plan):
    """Immutable evaluation semantics, independent of child code/plan identity."""
    return {'adapter_identity':plan['adapter_identity'],'base_runtime':plan['base_runtime'],
        'expected':plan['expected'],'budget':plan['budget'],
        'config':{k:v for k,v in plan['config'].items() if k!='schema_version'},
        'core_revision':plan['core_revision'],'reporting_revision':plan['reporting_revision'],
        'environment_dispatch':plan['environment_dispatch'],
        'tasks':[{k:deepcopy(t[k]) for k in ('key','condition','scoped','source')} for t in plan['tasks']]}


def _snapshot(root,keys):
    paths=[root/name for name in ('plan.json','batch.json','summary.json','report.md')]
    for key in keys:
        directory=(root/'tasks'/key).resolve()
        _require(directory.is_relative_to(root) and directory.is_dir(),'parent task directory missing or escaped')
        paths.extend(p for p in directory.rglob('*') if p.is_file())
    result={}
    for path in paths:
        resolved=path.resolve()
        _require(resolved.is_relative_to(root) and resolved.is_file(),'parent artifact missing or escaped')
        result[path.relative_to(root).as_posix()]={'sha256':file_sha256(resolved),'bytes':resolved.stat().st_size}
    return dict(sorted(result.items()))


def _collect(parent_dir,new_plan):
    from . import evaluation as ev
    from .environment_dispatch import validate_dispatch
    root=Path(parent_dir).expanduser().resolve()
    parent=read_json(root/'plan.json');batch=read_json(root/'batch.json')
    _require(parent.get('schema_version')==ev.SCHEMA_V2 and parent.get('plan_sha256')==PARENT_PLAN_SHA
        and ev._hash({k:v for k,v in parent.items() if k!='plan_sha256'})==PARENT_PLAN_SHA,
        'parent must be the frozen eval003 v2 plan')
    _require(batch.get('schema_version')==ev.SCHEMA_V2 and batch.get('plan_sha256')==PARENT_PLAN_SHA,
        'parent batch identity differs')
    _require(parent['adapter_identity'].get('adapter_sha256')==ADAPTER_SHA,
        'parent final adapter SHA differs')
    ev.validate_adapter(parent['adapter_identity']);ev.validate_adapter(new_plan['adapter_identity'])
    _require(_contract(parent)==_contract(new_plan),
        'parent/child adapter, runtime, source, endpoint or population contract differs')
    ev.activate_core(parent['config']['benchmark_root']);ev.activate_reporting(parent['config']['reporting_root'])
    ev._validate_population(parent);ev._validate_population(new_plan)
    validate_dispatch(parent['environment_dispatch'])
    loaded=batch.get('loaded_base_identity')
    _require(isinstance(loaded,dict) and bool(loaded),'parent lacks its actual loaded model identity')
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    items=parent['tasks']
    inherited=[t for t in items if t['condition']=='10' and not t['scoped']]
    _require(len(inherited)==6 and {t['key'] for t in inherited}=={'10_'+t for t in REUSE_TASKS},
        'requires all six original completed ten-source tasks')
    inherited_keys=[t['key'] for t in inherited]
    remaining=[t for t in items if t['key'] not in set(inherited_keys)]
    _require(items[:6]==inherited and len(remaining)==120
        and sum(len(t['source']['episodes']) for t in remaining if t['condition']=='10')==30
        and sum(len(t['source']['episodes']) for t in remaining if t['condition']=='00')==90,
        'remaining population must be original ordered30 mask10 plus90 normal00')
    technical=remaining[0]
    _require(technical['key']=='bowl_drawer_close_s000_10','unexpected original zero-step technical item')
    keys=inherited_keys+[technical['key']]
    _require(set(batch.get('tasks',{}))==set(keys),'parent has missing or additional attempted task groups')
    before=_snapshot(root,keys)
    records={'10':{},'00':{}};environment_records=[];technical_attempts=[]
    for item in inherited+[technical]:
        key=item['key'];state=batch['tasks'][key]
        metadata,rows=ev._read_task(root/'tasks'/key,item,parent,loaded,
            environment_record_sha256=state.get('environment_dispatch_sha256'))
        expected={e['episode_id']:e for e in item['source']['episodes']}
        if key in inherited_keys:
            _require(state.get('status')=='completed' and metadata.get('status')=='completed'
                and metadata.get('missing')==[] and len(rows)==10
                and {r['episode_id'] for r in rows}==set(expected)
                and all(r.get('status')=='completed' for r in rows),
                'all60 successful and failed completed episodes must verify; no outcome selection')
            for raw in rows:
                name=raw['episode_id']
                source={'model_identity':workflow._model_identity(metadata),
                    'original_protocol':metadata['protocol_version'],
                    'input_evidence_level':'verified_parent_raw_execution_video_and_source_archive',
                    'run_path':str(root),'new_execution':False,
                    'inherited_from':{'parent_run':str(root),'plan_sha256':PARENT_PLAN_SHA,'task_key':key},
                    'verified_files':[{'path':str(root/name_),'sha256':before[name_]['sha256']}
                        for name_ in ('plan.json','batch.json',f'tasks/{key}/task_run.json',f'tasks/{key}/environment_dispatch.json')]}
                records['10'][name]=score_verified_result(expected[name],raw,condition='10',source=source)
            environment_records.append({'task_id':key,'condition':'10',
                'record':read_json(root/'tasks'/key/'environment_dispatch.json'),
                'new_execution':False,'inherited_from':{'parent_run':str(root),'plan_sha256':PARENT_PLAN_SHA}})
        else:
            _require(state.get('status')=='technical_pause' and metadata.get('status')=='technical_pause'
                and len(rows)==1 and rows[0].get('episode_id')==technical['key']
                and rows[0].get('n_steps')==0 and not rows[0].get('executed_actions')
                and rows[0].get('status')!='completed',
                'known parent zero-step attempt is not a completed inherited result')
            technical_attempts.append({'task_key':key,'episode_id':rows[0]['episode_id'],
                'status':rows[0]['status'],'n_steps':0,'error':metadata.get('error'),
                'inherited_as_result':False,'parent_run':str(root)})
    _require(_snapshot(root,keys)==before,'parent artifacts changed while being verified')
    names=[e['episode_id'] for t in inherited for e in t['source']['episodes']]
    _require(len(names)==60 and len(set(names))==60,'exact60 distinct inherited episodes required')
    descriptor={'schema_version':SCHEMA,'parent_run':str(root),'parent_plan_sha256':PARENT_PLAN_SHA,
        'parent_plan_file_sha256':before['plan.json']['sha256'],'parent_batch_sha256':before['batch.json']['sha256'],
        'adapter_sha256':ADAPTER_SHA,'semantic_contract_sha256':identity(_contract(parent)),
        'loaded_base_identity':deepcopy(loaded),'inherited_task_keys':inherited_keys,'inherited_episode_ids':names,
        'remaining_task_keys':[t['key'] for t in remaining],
        'remaining_episode_ids':[e['episode_id'] for t in remaining for e in t['source']['episodes']],
        'new_execution_budget':{'10':30,'00':90,'total':120},
        'technical_attempts':technical_attempts,'frozen_files':before,
        'new_execution':False,'simulation_created':False,'weights_loaded':False}
    descriptor['identity']=identity(descriptor)
    return descriptor,{'records':records,'environment_records':environment_records,
        'loaded_base_identity':deepcopy(loaded),'inherited_task_keys':inherited_keys,
        'inherited_episode_ids':names,'remaining_task_keys':descriptor['remaining_task_keys'],
        'remaining_episode_ids':descriptor['remaining_episode_ids'],'technical_attempts':technical_attempts}


def prepare_continuation(parent_dir,new_plan):
    """Read/verify old60 and seal their original artifacts without copying raw."""
    return _collect(parent_dir,new_plan)[0]


def verify_continuation(descriptor,new_plan):
    """Independently reverify original artifacts; never trust stored scores."""
    _require(isinstance(descriptor,dict) and descriptor.get('schema_version')==SCHEMA
        and identity(descriptor)==descriptor.get('identity'),'descriptor identity differs')
    actual,verified=_collect(descriptor['parent_run'],new_plan)
    _require(actual==descriptor,'parent references or artifacts differ from frozen inheritance')
    return verified
