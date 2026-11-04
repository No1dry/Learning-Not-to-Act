"""036: one final retention adapter,180 entirely new model episodes.

Reuses035 strict bridges/proxy coordination and original core runners/readers.
Only final verification scans all artifacts; progress never fabricates SR.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from egrs.augmentation.dependencies import activate_core,activate_reporting
from egrs.augmentation.evaluation import _read,_hash,check_method_identity
from egrs.trajectory_augmentation import evaluation as previous

SCHEMA='task036-retention-eval-v1'
GROUP='policy_retention_distillation'
FACTORY='egrs.augmentation.evaluation:make_policy'


def validate_adapter(value):
    from egrs.augmentation.adapter_identity import validate_retention_recipe_identity
    validate_retention_recipe_identity(value)
    if value['update']!=1000 or value['final_update']!=1000:
        raise ValueError('036 evaluation requires the fixed final1000 retention adapter')


def build_plan(config_path):
    from egrs.augmentation.adapter_identity import read_adapter_identity
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,binding_for,coordination_identity
    path=Path(config_path).resolve();cfg=_read(path)
    fields={'schema_version','group','benchmark_root','reporting_root','base_runtime','adapter',
        'legacy_sources_10','legacy_sources_00','new_sources_10','new_sources_00','environment_dispatch'}
    if set(cfg)!=fields or cfg['schema_version']!=SCHEMA or cfg['group']!=GROUP:
        raise ValueError('explicit036 new-model evaluation configuration required; no continuation or inherited results')
    def resolve(value):
        p=Path(value).expanduser();return str((path.parent/p).resolve())
    for key in fields-{'schema_version','group','legacy_sources_10','environment_dispatch'}:cfg[key]=resolve(cfg[key])
    if set(cfg['environment_dispatch'])!={'legacy_root'}:raise ValueError('explicit legacy dependency required')
    cfg['environment_dispatch']['legacy_root']=resolve(cfg['environment_dispatch']['legacy_root'])
    core_ref=activate_core(cfg['benchmark_root']);report_ref=activate_reporting(cfg['reporting_root'])
    from benchmark.remaining_goals.headless import planning,nine_planning,scoped_planning,scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    runtime=nine_planning.load_runtime(cfg['base_runtime']);adapter=read_adapter_identity(cfg['adapter']);validate_adapter(adapter)
    if set(cfg['legacy_sources_10'])!=set(REUSE_TASKS):raise ValueError('original six legacy sources required')
    tasks=[]
    for task in REUSE_TASKS:
        origin={k:resolve(v) for k,v in cfg['legacy_sources_10'][task].items()}
        cfg['legacy_sources_10'][task]=origin
        source=planning.source_plan(task,origin,acceptance=planning.MASK10_ACCEPTANCE)
        tasks.append({'key':'10_'+task,'condition':'10','scoped':False,'source':source})
    expected={'10':nine_planning.expected_episodes('nine-mask10'),'00':nine_planning.expected_episodes('nine-normal00')}
    _,old=scoped_planning.read_composite(cfg['legacy_sources_00'],'normal00-control')
    for bits,protocol in (('10','nine-mask10'),('00','nine-normal00')):
        _,new=nine_planning.read_sources(cfg['new_sources_'+bits],protocol)
        for episode in expected[bits]:
            task,index=episode['task_id'],episode['initial_state_index']
            if bits=='10' and task in REUSE_TASKS:continue
            source=scoped_sources.resolve_source('normal00-control' if task in REUSE_TASKS else protocol,
                task,index,(old if task in REUSE_TASKS else new).get((task,index)))
            tasks.append({'key':episode['episode_id'],'condition':bits,'scoped':True,'source':source})
    dispatch=describe_dispatch(cfg['environment_dispatch']['legacy_root'],cfg['benchmark_root'])
    for item in tasks:item['environment_binding']=binding_for(item['source']['environment_config']['environment'],dispatch)
    plan={'schema_version':SCHEMA,'config':cfg,'base_runtime':runtime,'adapter_identity':adapter,
        'core_revision':core_ref,'reporting_revision':report_ref,'tasks':tasks,'expected':expected,
        'environment_dispatch':dispatch,'proxy_coordination':coordination_identity(),
        'simulation_created':False,'weights_loaded':False,
        'budget':{'10':90,'00':90,'total':180,'policy_seed':7,'max_chunk_steps':8,'horizon':520,
            'video':'all','raw_queries_actions':'all'},'new_model_execution_only':True}
    previous._validate_population(plan,adapter_validator=validate_adapter,group=GROUP)
    plan['plan_sha256']=_hash(plan)
    return plan


def _read_task(directory,item,plan,model_identity):
    from benchmark.remaining_goals.headless import workflow
    directory=Path(directory)
    metadata,results=workflow._read_task(directory,scoped=item['scoped'],batch_identity=plan['plan_sha256'],
        runtime=plan['base_runtime'],sources=[item['source']],model_identity=model_identity)
    check_method_identity(metadata,plan['adapter_identity'])
    state=plan['_batch_tasks'][item['key']]
    previous._verify_environment_record(directory,item,plan,state.get('environment_dispatch_sha256'),metadata)
    if _read(directory/'environment_dispatch.json').get('proxy_coordination')!=plan['proxy_coordination']:
        raise ValueError('036 proxy coordination lineage differs')
    return metadata,results


def make_report(records,adapter,issues=None):
    report=previous.make_report(records,adapter,issues)
    report.update(schema_version=SCHEMA,group=GROUP,new_model_execution_only=True)
    for bits,numerator in (('10',49),('00',66)):
        item=report['conditions'][bits];rate=item['formal_SR']
        item['previous035']={'numerator':numerator,'denominator':90,'percent':100*numerator/90}
        item['delta_from035_percentage_points']=rate['percent']-100*numerator/90 if rate else None
    return report


def inspect_run(directory,*,progress=None):
    from egrs.trajectory_augmentation.environment_dispatch import validate_dispatch,coordination_identity
    directory=Path(directory).resolve();plan=_read(directory/'plan.json');batch=_read(directory/'batch.json')
    if (plan.get('schema_version')!=SCHEMA or batch.get('schema_version')!=SCHEMA
        or plan.get('plan_sha256')!=_hash({k:v for k,v in plan.items() if k!='plan_sha256'})
        or batch.get('plan_sha256')!=plan['plan_sha256'] or not plan.get('new_model_execution_only')
        or 'continuation' in plan or any(v.get('status')=='inherited' for v in batch['tasks'].values())):
        raise ValueError('036 frozen plan/batch identity differs or attempts inherited model results')
    activate_core(plan['config']['benchmark_root']);activate_reporting(plan['config']['reporting_root'])
    previous._validate_population(plan,adapter_validator=validate_adapter,group=GROUP)
    validate_dispatch(plan['environment_dispatch'])
    if plan['proxy_coordination']!=coordination_identity():raise ValueError('036 coordination source differs')
    from benchmark.remaining_goals.headless import workflow,planning
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    records={'10':{},'00':{}};issues={'10':[],'00':[]};environments=[];checked=0
    reader_plan=dict(plan,_batch_tasks=batch['tasks'])
    for item in plan['tasks']:
        folder=directory/'tasks'/item['key']
        if folder.exists():
            try:
                if 'loaded_base_identity' not in batch:raise ValueError('executed task lacks loaded model identity')
                metadata,raws=_read_task(folder,item,reader_plan,batch['loaded_base_identity'])
                if metadata.get('status')=='technical_pause':
                    issues[item['condition']].extend({'episode_id':name,'phase':metadata.get('phase'),
                        'error':metadata.get('error')} for name in metadata.get('missing',[]))
                episodes={e['episode_id']:e for e in item['source']['episodes']}
                for raw in raws:
                    name=raw['episode_id']
                    records[item['condition']][name]=score_verified_result(episodes[name],raw,condition=item['condition'],source={
                        'model_identity':workflow._model_identity(metadata),'original_protocol':metadata['protocol_version'],
                        'input_evidence_level':'verified_raw_execution_video_and_source_archive','run_path':str(directory),
                        'verified_files':[{'path':str(folder/'task_run.json'),'sha256':planning.file_sha(folder/'task_run.json')}],
                        'new_execution':True})
                if (folder/'environment_dispatch.json').exists():environments.append({'task_id':item['key'],
                    'record':_read(folder/'environment_dispatch.json')})
            except (OSError,ValueError,KeyError,TypeError) as error:
                issues[item['condition']].extend({'episode_id':e['episode_id'],'error':f'{type(error).__name__}: {error}'}
                    for e in item['source']['episodes'])
        elif item['key'] in batch['tasks']:
            issues[item['condition']].append({'task_id':item['key'],'error':batch['tasks'][item['key']]})
        checked+=len(item['source']['episodes'])
        message={'phase':'verification','checked':checked,'expected':180,'percent':100*checked/180}
        if progress is not None:progress(message)
    report=make_report(records,plan['adapter_identity'],issues)
    report['environment_dispatch']={'identity':plan['environment_dispatch']['identity'],'verified_task_records':environments}
    report['model_completed']=sum(sum(row['primary'].get('execution_status')=='completed' for row in pool.values()) for pool in records.values())
    report['formal_complete']=all(report['conditions'][bits]['formal_SR'] is not None for bits in ('10','00'))
    return report


def _execute_task(folder,item,plan,bind,policy):
    return previous._run_dispatched_task(folder,item,plan,bind,policy)


def run(config,output):
    plan=build_plan(config);output=Path(output).resolve()
    if output.exists():raise FileExistsError('036 requires a new output; no old model results may be reused')
    protected=[Path(plan['config'][k]) for k in ('benchmark_root','reporting_root','base_runtime','adapter',
        'legacy_sources_00','new_sources_10','new_sources_00')]+[Path(plan['config']['environment_dispatch']['legacy_root'])]
    protected.extend(Path(v).parent for t in plan['tasks'] for k,v in t['source']['source'].items()
        if k in {'manifest','candidate_replay','initialization','rgb_certificate'})
    if any(output==p or p in output.parents or output in p.parents for p in protected):raise ValueError('036 output overlaps protected input')
    from benchmark.remaining_goals.headless import workflow,planning
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    output.mkdir(parents=True);workflow.write_json(output/'plan.json',plan)
    batch={'schema_version':SCHEMA,'plan_sha256':plan['plan_sha256'],'tasks':{}}
    workflow.write_json(output/'batch.json',batch)
    completed={'10':set(),'00':set()}
    def log(value):
        print(json.dumps(value),flush=True)
        workflow.write_json(output/'progress.json',value,update=(output/'progress.json').exists())
    def bind(actual):
        if batch.get('loaded_base_identity',actual)!=actual:raise ValueError('036 actual loaded base components changed')
        batch['loaded_base_identity']=actual;workflow.write_json(output/'batch.json',batch,update=True)
    worker=dict(deepcopy(plan['base_runtime']),policy_factory=FACTORY,method_adapter=plan['config']['adapter'])
    policy=None;execution_error=None;cleanup_error=None;ledger_error=None;report=None
    try:
        policy=SubprocessPolicy(worker);check_method_identity({'model_runtime':policy.provenance},plan['adapter_identity'])
        for item in plan['tasks']:
            folder=output/'tasks'/item['key'];batch['tasks'][item['key']]={'status':'running'}
            workflow.write_json(output/'batch.json',batch,update=True)
            result=_execute_task(folder,item,plan,bind,policy)
            batch['tasks'][item['key']]={'status':result['status'],'error':result['error'],
                'environment_dispatch_sha256':planning.file_sha(folder/'environment_dispatch.json')}
            workflow.write_json(output/'batch.json',batch,update=True)
            expected={e['episode_id'] for e in item['source']['episodes']}
            for ref in result.get('results',[]):
                raw_path=workflow._contained(folder,ref['path'])
                if planning.file_sha(raw_path)!=ref['sha256']:raise ValueError('new unit raw changed before progress')
                raw=_read(raw_path)
                if raw['episode_id'] not in expected:raise ValueError('foreign new036 episode')
                if raw['status']=='completed':completed[item['condition']].add(raw['episode_id'])
            n=sum(map(len,completed.values()))
            log({'phase':'execution','model_completed':n,'expected':180,'percent':100*n/180,
                'conditions':{bits:{'completed':len(completed[bits]),'expected':90,'percent':100*len(completed[bits])/90}
                    for bits in ('10','00')},'formal_SR':'pending final artifact verification'})
            print(f'036 model {n}/180 ({100*n/180:.2f}%)',flush=True)
            if result['status']!='completed':raise RuntimeError(result['error'] or '036 technical pause')
    except BaseException as error:execution_error=error
    finally:
        try:
            if policy is not None:policy.close()
        except BaseException as error:cleanup_error=error
        batch.update(execution_error=None if execution_error is None else f'{type(execution_error).__name__}: {execution_error}',
            cleanup_warning=None if cleanup_error is None else f'{type(cleanup_error).__name__}: {cleanup_error}')
        try:workflow.write_json(output/'batch.json',batch,update=True)
        except BaseException as error:ledger_error=error
        try:
            report=inspect_run(output,progress=log)
            report.update(execution_error=batch['execution_error'],cleanup_warning=batch['cleanup_warning'],
                ledger_warning=None if ledger_error is None else f'{type(ledger_error).__name__}: {ledger_error}',
                software_exit='execution_error' if execution_error is not None else 'ledger_error' if ledger_error is not None else
                    'cleanup_warning' if cleanup_error is not None else
                    'success' if report['formal_complete'] else 'verification_incomplete')
            previous._save_report(output,report)
            log({'phase':'final','status':'completed' if report['formal_complete'] else 'incomplete',
                'model_completed':report['model_completed'],'expected':180,'percent':100*report['model_completed']/180,
                'cleanup_warning':report['cleanup_warning'],'software_exit':report['software_exit']})
            for bits in ('10','00'):
                value=report['conditions'][bits]['formal_SR']
                print(f"036 condition={bits} formal_SR="+(f"{value['percent']:.2f}% ({value['numerator']}/90)" if value else 'N/A'),flush=True)
        except BaseException as verification_error:
            diagnostics={'error':f'{type(verification_error).__name__}: {verification_error}',
                'execution_error':batch['execution_error'],'cleanup_warning':batch['cleanup_warning'],
                'ledger_warning':None if ledger_error is None else f'{type(ledger_error).__name__}: {ledger_error}'}
            try:workflow.write_json(output/'verification_error.json',diagnostics)
            except BaseException as storage_error:
                print(json.dumps({**diagnostics,'diagnostic_write_error':f'{type(storage_error).__name__}: {storage_error}'}),flush=True)
            if execution_error is not None:raise execution_error from verification_error
            raise
    if execution_error is not None:raise execution_error
    if not report['formal_complete']:raise RuntimeError('036 final evidence incomplete; formal results unavailable')
    if ledger_error is not None:raise ledger_error
    if cleanup_error is not None:raise cleanup_error
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('plan','run'):
        p=sub.add_parser(name);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('report');p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    if args.command=='run':run(args.config,args.out)
    elif args.command=='plan':
        plan=build_plan(args.config)
        with Path(args.out).open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)
    else:
        original=Path(args.run).resolve();output=Path(args.out).resolve()
        if output==original or output in original.parents or original in output.parents:raise ValueError('separate036 report output required')
        report=inspect_run(original,progress=lambda value:print(json.dumps(value),flush=True))
        batch=_read(original/'batch.json');report.update(cleanup_warning=batch.get('cleanup_warning'),execution_error=batch.get('execution_error'))
        output.mkdir(parents=True,exist_ok=False);previous._save_report(output,report)


if __name__=='__main__':main()
