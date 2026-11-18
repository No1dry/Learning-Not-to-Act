"""Native official SOG10, two informed language diagnostics, only original90 ten.

The accepted core still owns source archival, environment execution, evidence,
video and full-task scoring. No research adapter or fabricated00 population is
used to enter the former dual-condition engine.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re

from egrs.augmentation.dependencies import activate_core, activate_reporting
from egrs.trajectory_augmentation import evaluation as previous

SCHEMA='task044-prompt-eval-v1'
FACTORY='egrs.prompt044.policy:make_policy'
PROMPT_MANIFEST_SHA256='e648ef202c31e6e99e14478f6ec36952a1791d2187bf023a224b25974f669566'
REFERENCE_PLAN_SHA256='bafc7238da1ed94e8a1b6d4b98ce7f9d41bb59bad887be2d7de9e1d2ce5d68df'
EXPECTED10_SHA256='b53418726b09cf533bff06a162a2407bd6316bc0df6e909a4801bac72e73c7a5'
DECLARED_TEN_PROJECTION_SHA256='ed9b5027fbaf09099d5197549d68e31b3f0766d2cb3dfcd3a302a207e4a10551'
CORE_REVISION='d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9'
REPORTING_REVISION='d2afce4eb074b777364daddea2c08bd70731865f'
BUDGET={'10':90,'00':0,'total':90,'policy_seed':7,'max_chunk_steps':8,'horizon':520,
        'model_predict_calls':5850,'video':'all','raw_queries_actions':'all'}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def projection_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                    ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate044 JSON field: '+key)
        result[key]=value
    return result


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_object)


def _path(value,base):
    if not isinstance(value,str) or not value.strip():raise ValueError('044 requires explicit nonempty paths')
    value=os.path.expanduser(os.path.expandvars(value))
    if re.search(r'\$[A-Za-z_{]|%[^%]+%|[<>]',value):raise ValueError('Unresolved044 path or placeholder')
    path=Path(value)
    return str((base/path).resolve() if not path.is_absolute() else path.resolve())


def load_config(path):
    path=Path(path).resolve();cfg=_read(path)
    fields={'schema_version','variant','prompt_manifest','reference_plan','benchmark_root',
            'reporting_root','base_runtime','environment_dispatch'}
    if (not isinstance(cfg,dict) or set(cfg)!=fields or cfg['schema_version']!=SCHEMA
            or cfg['variant'] not in ('p1','p2')
            or not isinstance(cfg['environment_dispatch'],dict)
            or set(cfg['environment_dispatch'])!={'legacy_root'}):
        raise ValueError('Exact044 native ten-only configuration and p1/p2 required')
    for key in fields-{'schema_version','variant','environment_dispatch'}:cfg[key]=_path(cfg[key],path.parent)
    cfg['environment_dispatch']['legacy_root']=_path(cfg['environment_dispatch']['legacy_root'],path.parent)
    return cfg


def _input_paths(cfg,reference):
    """Protect immutable file roots and their enclosing data banks, without IO."""
    roots=[Path(cfg[k]) for k in ('benchmark_root','reporting_root')]
    roots += [Path(cfg['environment_dispatch']['legacy_root'])]
    roots += [Path(cfg[k]).parent for k in ('reference_plan','prompt_manifest')]
    roots += [Path(cfg['base_runtime'])]
    names={'manifest','candidate_replay','initialization','rgb_certificate','manifest_dir',
           'checkpoint','repo_path','data_root','source_root','root'}
    def visit(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in names and isinstance(item,str) and Path(item).is_absolute():
                    p=Path(item).resolve()
                    roots.append(p if key.endswith(('root','dir','path')) or key=='checkpoint' else p.parent)
                    roots.extend(a for a in p.parents if a.name.lower()=='data')
                else:visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit([t for t in reference.get('tasks',[]) if t.get('condition')=='10'])
    visit(reference.get('base_runtime',{}))
    return list({str(p.resolve()):p.resolve() for p in roots}.values())


def validate_output_paths(config,output):
    """Pure path preflight for the explicit launcher; never constructs a model."""
    target=Path(output).expanduser().resolve()
    if target.exists():raise FileExistsError('044 requires new output; existing attempts are never overwritten or resumed')
    reference=_read(config['reference_plan'])
    if any(target==p or p in target.parents or target in p.parents for p in _input_paths(config,reference)):
        raise ValueError('044 output overlaps protected input or data root')
    return target


def _validate_population(plan,manifest):
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.planning import canonical_hash
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from .prompts import prompt_record
    expected=expected_episodes('nine-mask10')
    if plan.get('expected')!={'10':expected} or len(plan['tasks'])!=36 or plan['budget']!=BUDGET:
        raise ValueError('044 requires only the fixed original36 units/90 ten episodes and budget')
    lookup={e['episode_id']:e for e in expected};seen=set();keys=set()
    for task in plan['tasks']:
        if task['condition']!='10' or task['key'] in keys:raise ValueError('Foreign or duplicate044 unit')
        keys.add(task['key']);source=task['source']
        if source['source_plan_sha256']!=canonical_hash({k:v for k,v in source.items() if k!='source_plan_sha256'}):
            raise ValueError('044 original source hash differs')
        for ep in source['episodes']:
            name=ep['episode_id']
            if name not in lookup or name in seen or any(ep.get(k)!=lookup[name][k] for k in previous.IDENTITY_FIELDS):
                raise ValueError('044 source population differs from original90 ten')
            seen.add(name)
            record=prompt_record(manifest,plan['config']['variant'],ep['instruction'])
            if record['task_id']!=ep['task_id'] or record['official_task_id']!=lookup[name]['libero_task_id']:
                raise ValueError('044 exact instruction conflicts with original task identity')
            if ep['task_id'] in REUSE_TASKS:
                if task['scoped'] or len(source['episodes'])!=10:raise ValueError('044 legacy ten source grouping differs')
            elif not task['scoped'] or len(source['episodes'])!=1 or source['protocol']!='nine-mask10':
                raise ValueError('044 new three ten source protocol differs')
    if seen!=set(lookup):raise ValueError('044 missing original ten episode')


def build_plan(config_path):
    from .prompts import load_manifest,validate_native_runtime
    cfg=load_config(config_path);manifest=load_manifest(cfg['prompt_manifest'])
    if file_sha(cfg['reference_plan'])!=REFERENCE_PLAN_SHA256:raise ValueError('044 frozen reference plan byte SHA differs')
    reference=_read(cfg['reference_plan'])
    core=activate_core(cfg['benchmark_root']);reporting=activate_reporting(cfg['reporting_root'])
    if core!=reference['core_revision'] or core!=CORE_REVISION or reporting!=reference['reporting_revision'] or reporting!=REPORTING_REVISION:
        raise ValueError('044 actual core/reporting revisions differ from reference metadata')
    from benchmark.remaining_goals.headless import nine_planning,planning,scoped_sources
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,binding_for,coordination_identity
    runtime=nine_planning.load_runtime(cfg['base_runtime']);validate_native_runtime(runtime)
    if runtime!=reference['base_runtime']:raise ValueError('044 original base runtime differs from frozen reference')
    expected=deepcopy(reference['expected']['10'])
    if projection_hash(expected)!=EXPECTED10_SHA256:raise ValueError('044 fixed expected10 projection differs')
    tasks=deepcopy([t for t in reference['tasks'] if t['condition']=='10'])
    dispatch=describe_dispatch(cfg['environment_dispatch']['legacy_root'],cfg['benchmark_root'])
    if dispatch!=reference['environment_dispatch']:raise ValueError('044 bridge dependency differs from reference')
    for item in tasks:
        source=item['source'];first=source['episodes'][0]
        actual=(scoped_sources.resolve_source('nine-mask10',first['task_id'],first['initial_state_index'],source['source'])
                if item['scoped'] else planning.source_plan(first['task_id'],source['source'],acceptance=planning.MASK10_ACCEPTANCE))
        if actual!=source:raise ValueError('044 current original source differs from frozen reference')
        binding=binding_for(source['environment_config']['environment'],dispatch)
        if item['environment_binding']!=binding:raise ValueError('044 source bridge binding differs')
    coordination=coordination_identity()
    if coordination!=reference['proxy_coordination']:raise ValueError('044 proxy coordination differs')
    actual_projection=projection_hash(tasks)
    plan={'schema_version':SCHEMA,'config':cfg,'base_runtime':runtime,'core_revision':core,'reporting_revision':reporting,
        'reference_plan_sha256':REFERENCE_PLAN_SHA256,'expected':{'10':expected},'tasks':tasks,
        'environment_dispatch':dispatch,'proxy_coordination':coordination,'policy_factory':FACTORY,
        'prompt_manifest_sha256':PROMPT_MANIFEST_SHA256,'budget':deepcopy(BUDGET),
        'simulation_created':False,'weights_loaded':False,'new_native_execution_only':True,
        'source_projection':{'actual_full_ten_tasks_sha256':actual_projection,
            'approved_projection_sha256':DECLARED_TEN_PROJECTION_SHA256,
            'matches_approved_projection':actual_projection==DECLARED_TEN_PROJECTION_SHA256,
            'binding':'complete reference file byte SHA plus exact source reconstruction and expected10 hash',
            'note':'Approval does not specify the ten-task projection field selection; no guessed projection gate replaces full-file binding.'}}
    _validate_population(plan,manifest)
    plan['plan_sha256']=projection_hash(plan)
    return plan


def check_policy(plan,provenance):
    from .policy import check_metadata
    metadata=provenance.get('policy_metadata')
    check_metadata(plan['base_runtime'],metadata)
    if (metadata.get('prompt_variant')!=plan['config']['variant']
            or metadata.get('prompt_manifest_sha256')!=PROMPT_MANIFEST_SHA256
            or metadata.get('deployment_initial_semantic_information') is not True
            or any(k in metadata for k in ('method_adapter','hint043_arm','task_control_arm','attention_contract'))):
        raise ValueError('044 loaded native/prompt metadata differs')


def _execute_task(folder,item,plan,bind,policy):
    return previous._run_dispatched_task(folder,item,plan,bind,policy)


def _read_task(folder,item,plan,model_identity,batch):
    from benchmark.remaining_goals.headless import workflow
    metadata,raws=workflow._read_task(folder,scoped=item['scoped'],batch_identity=plan['plan_sha256'],
        runtime=plan['base_runtime'],sources=[item['source']],model_identity=model_identity)
    check_policy(plan,metadata['model_runtime'])
    previous._verify_environment_record(folder,item,plan,batch['tasks'][item['key']].get('environment_dispatch_sha256'),metadata)
    if _read(Path(folder)/'environment_dispatch.json').get('proxy_coordination')!=plan['proxy_coordination']:
        raise ValueError('044 environment proxy coordination differs')
    return metadata,raws


def verify_audit(path,plan,provenance,attempts,raws):
    from .prompts import load_manifest,prompt_record
    rows=[json.loads(line,object_pairs_hook=_object) for line in Path(path).read_text(encoding='utf-8').splitlines()]
    if (not rows or any(not isinstance(row,dict) or row.get('schema_version')!='task044-prompt-audit-v1' for row in rows)
            or rows[0].get('event')!='initialized' or rows[0].get('metadata')!=provenance['policy_metadata']
            or rows[0].get('budget')!={'episodes':90,'predict_calls':5850,'predict_calls_per_episode':65}):
        raise ValueError('044 prompt audit initial native identity differs')
    manifest=load_manifest(plan['config']['prompt_manifest'])
    episodes={ep['episode_id']:ep for task in plan['tasks'] for ep in task['source']['episodes']}
    ordinal=sequence=query=0;queries={};results=set();pending=None;bindings=[];failed=set()
    if len(set(attempts))!=len(attempts):raise ValueError('044 duplicate attempted episode')
    for row in rows[1:]:
        event=row.get('event')
        if event=='episode_reset':
            ordinal+=1;query=0
            if type(row.get('episode_ordinal')) is not int or row['episode_ordinal']!=ordinal or ordinal>len(attempts) or ordinal>90 or pending is not None:
                raise ValueError('044 prompt reset/order differs from actual episode attempts')
            name=attempts[ordinal-1];queries[name]=0
            bindings.append({'episode_id':name,'episode_ordinal':ordinal,
                **prompt_record(manifest,plan['config']['variant'],episodes[name]['instruction'])})
        elif event=='predict':
            sequence+=1;query+=1
            if (any(type(row.get(k)) is not int for k in ('sequence','episode_ordinal','episode_query'))
                    or ordinal<1 or pending is not None or row.get('sequence')!=sequence or row.get('episode_ordinal')!=ordinal
                    or row.get('episode_query')!=query or sequence>5850 or query>65):
                raise ValueError('044 prompt prediction budget or sequence differs')
            name=attempts[ordinal-1];expected=prompt_record(manifest,plan['config']['variant'],episodes[name]['instruction'])
            if any(row.get(k)!=v for k,v in expected.items()):raise ValueError('044 actual prompt language or hash differs')
            queries[name]+=1;pending=sequence
        elif event=='predict_result':
            if (any(type(row.get(k)) is not int for k in ('sequence','episode_ordinal','episode_query'))
                    or row.get('sequence')!=pending or row.get('episode_ordinal')!=ordinal or row.get('episode_query')!=query
                    or pending in results or row.get('status') not in ('returned','error')):
                raise ValueError('044 prompt prediction result binding differs')
            if row['status']=='error':failed.add(attempts[ordinal-1])
            results.add(pending);pending=None
        else:raise ValueError('044 unknown prompt audit event')
    if ordinal!=len(attempts):raise ValueError('044 prompt audit is missing episode resets')
    for name,raw in raws.items():
        if queries.get(name)!=raw['policy_queries'] or len(raw['queries'])!=raw['policy_queries']:
            raise ValueError('044 prompt audit query count differs from original raw')
        if raw['status']=='completed' and (pending is not None or name in failed):
            raise ValueError('044 completed raw has unfinished or failed prompt call')
    return {'predict_calls':sequence,'limit':5850,'episode_resets':ordinal,'bindings':bindings,
            'file_sha256':file_sha(path),'pending_call':pending,'failed_calls_not_refunded':True}


def make_report(records,plan,issues=None):
    from libero_remain_reporting import map_verified_results
    binary=map_verified_results(plan['expected']['10'],records,artifact_issues=issues or [])
    rate=binary['counts']['formal_SR']
    p0={'comparison':'aggregate-only','rate':{'numerator':22,'denominator':90,'percent':100*22/90},
        'source':'historical original official SOG10 P0; not H0; no baseline rerun',
        'paired_episode_evidence':'not supplied or fabricated; aggregate reference only'}
    return {'schema_version':SCHEMA,'variant':plan['config']['variant'],'budget':deepcopy(BUDGET),
        'formal_SR':rate,'formal_complete':rate is not None,'model_completed':binary['counts']['completed'],
        'binary_report':binary,'p0':p0,'delta_from_p0_percentage_points':None if rate is None else rate['percent']-p0['rate']['percent'],
        'deployment_initial_semantic_information':True,'prompt_manifest_sha256':PROMPT_MANIFEST_SHA256,
        'note':'Informed initial-semantic diagnostic, not autonomous RGB inference or a theoretical upper bound. Full original A+B and A protection remain scored.'}


def inspect_run(directory,*,progress=None):
    from .prompts import load_manifest
    from egrs.trajectory_augmentation.environment_dispatch import validate_dispatch,coordination_identity
    directory=Path(directory);plan=_read(directory/'plan.json');batch=_read(directory/'batch.json')
    if (plan.get('schema_version')!=SCHEMA or batch.get('schema_version')!=SCHEMA
            or plan.get('plan_sha256')!=projection_hash({k:v for k,v in plan.items() if k!='plan_sha256'})
            or batch.get('plan_sha256')!=plan['plan_sha256'] or not plan.get('new_native_execution_only')
            or 'continuation' in plan or 'adapter_identity' in plan
            or any(t.get('status')=='inherited' for t in batch['tasks'].values())):
        raise ValueError('044 frozen plan/batch identity differs or inherited/research results requested')
    activate_core(plan['config']['benchmark_root']);activate_reporting(plan['config']['reporting_root'])
    _validate_population(plan,load_manifest(plan['config']['prompt_manifest']))
    validate_dispatch(plan['environment_dispatch'])
    if plan['proxy_coordination']!=coordination_identity():raise ValueError('044 proxy source differs')
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    records={};raws={};issues=[];attempts=[];checked=0
    for item in plan['tasks']:
        folder=directory/'tasks'/item['key']
        if folder.exists():
            try:
                if 'loaded_base_identity' not in batch:raise ValueError('044 executed task lacks loaded native identity')
                metadata,values=_read_task(folder,item,plan,batch['loaded_base_identity'],batch)
                allowed=[ep['episode_id'] for ep in item['source']['episodes']]
                actual=metadata['attempts']
                if actual!=allowed[:len(actual)]:raise ValueError('044 original episode attempt order differs')
                attempts.extend(actual)
                if metadata['status']=='technical_pause':issues.append({'task_id':item['key'],'error':metadata.get('error')})
                episodes={ep['episode_id']:ep for ep in item['source']['episodes']}
                for raw in values:
                    name=raw['episode_id']
                    if name in raws:raise ValueError('044 duplicate raw episode')
                    raws[name]=raw
                    records[name]=score_verified_result(episodes[name],raw,condition='10',source={
                        'model_identity':workflow._model_identity(metadata),'original_protocol':metadata['protocol_version'],
                        'input_evidence_level':'verified_raw_execution_video_and_source_archive',
                        'run_path':str(directory),'new_execution':True,
                        'verified_files':[{'path':str(folder/'task_run.json'),'sha256':file_sha(folder/'task_run.json')}]})
            except (OSError,ValueError,KeyError,TypeError) as error:
                issues.append({'task_id':item['key'],'error':f'{type(error).__name__}: {error}'})
        checked+=len(item['source']['episodes'])
        if progress:progress({'phase':'verification','checked':checked,'expected':90,'percent':100*checked/90,'formal_complete':False})
    audit=None
    try:
        check_policy(plan,batch['policy_provenance'])
        audit=verify_audit(directory/'prompt_audit.jsonl',plan,batch['policy_provenance'],attempts,raws)
        if batch.get('prompt_audit_sha256')!=audit['file_sha256']:raise ValueError('044 prompt audit bytes differ from closed worker ledger')
    except (OSError,ValueError,KeyError,TypeError) as error:issues.append({'phase':'prompt_audit','error':f'{type(error).__name__}: {error}'})
    report=make_report(records,plan,issues);report['prompt_audit']=audit
    report['loaded_base_identity']=batch.get('loaded_base_identity')
    report['policy_provenance']=batch.get('policy_provenance')
    report['source_projection']=plan['source_projection']
    return report


def _save_report(directory,report):
    from benchmark.remaining_goals.headless.workflow import write_json
    from libero_remain_reporting import render_report
    directory=Path(directory)
    write_json(directory/'summary.json',report,update=(directory/'summary.json').exists())
    header=f"# Task044 {report['variant']}: official SOG10 initial-semantic diagnostic\n\n"
    header+='P0: historical22/90 (24.44%), aggregate-only; no paired baseline evidence claimed. Original complete task and A protection remain scored.\n\n'
    (directory/'report.md').write_text(header+render_report(report['binary_report']),encoding='utf-8')


def run(config,output):
    cfg=load_config(config);output=validate_output_paths(cfg,output)
    plan=build_plan(config)
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    output.mkdir(parents=True,exist_ok=False);workflow.write_json(output/'plan.json',plan)
    batch={'schema_version':SCHEMA,'plan_sha256':plan['plan_sha256'],'tasks':{}}
    workflow.write_json(output/'batch.json',batch)
    completed=set();started=[]
    def log(value):
        print(json.dumps(value),flush=True)
        workflow.write_json(output/'progress.json',value,update=(output/'progress.json').exists())
    def bind(actual):
        if batch.get('loaded_base_identity',actual)!=actual:raise ValueError('044 actual loaded native model changed')
        batch['loaded_base_identity']=actual;workflow.write_json(output/'batch.json',batch,update=True)
    class ProgressPolicy:
        def __init__(self,policy):self.policy=policy;self.provenance=policy.provenance
        def reset(self):
            self.policy.reset()
            sequence=[ep['episode_id'] for task in plan['tasks'] for ep in task['source']['episodes']]
            if len(started)>=90:raise ValueError('044 reset budget exceeded')
            started.append(sequence[len(started)])
            log({'phase':'episode_started','episode_id':started[-1],'started':len(started),
                'model_completed':len(completed),'expected':90,'percent':100*len(completed)/90,'formal_complete':False})
        def predict(self,observation,instruction):return self.policy.predict(observation,instruction)
    worker=dict(deepcopy(plan['base_runtime']),policy_factory=FACTORY,prompt_variant=cfg['variant'],
                prompt_manifest=cfg['prompt_manifest'],prompt_audit_path=str(output/'prompt_audit.jsonl'))
    policy=None;error=None;cleanup=None;ledger=None;report=None
    try:
        policy=SubprocessPolicy(worker);check_policy(plan,policy.provenance)
        batch['policy_provenance']=deepcopy(policy.provenance);workflow.write_json(output/'batch.json',batch,update=True)
        monitored=ProgressPolicy(policy)
        for item in plan['tasks']:
            folder=output/'tasks'/item['key'];batch['tasks'][item['key']]={'status':'running'}
            workflow.write_json(output/'batch.json',batch,update=True)
            result=_execute_task(folder,item,plan,bind,monitored)
            batch['tasks'][item['key']]={'status':result['status'],'error':result.get('error'),
                'environment_dispatch_sha256':file_sha(folder/'environment_dispatch.json')}
            workflow.write_json(output/'batch.json',batch,update=True)
            names={ep['episode_id'] for ep in item['source']['episodes']}
            for ref in result.get('results',[]):
                raw_path=workflow._contained(folder,ref['path'])
                if file_sha(raw_path)!=ref['sha256']:raise ValueError('044 raw bytes changed before progress')
                raw=_read(raw_path)
                if raw['episode_id'] not in names:raise ValueError('044 foreign raw episode')
                if raw['status']=='completed':completed.add(raw['episode_id'])
            log({'phase':'execution','model_completed':len(completed),'expected':90,'percent':100*len(completed)/90,
                 'formal_complete':False,'formal_SR':'pending original final artifact verification'})
            if result['status']!='completed':raise RuntimeError(result.get('error') or '044 technical pause')
    except BaseException as exc:error=exc
    finally:
        try:
            if policy is not None:policy.close()
        except BaseException as exc:cleanup=exc
        batch.update(execution_error=None if error is None else f'{type(error).__name__}: {error}',
                     cleanup_warning=None if cleanup is None else f'{type(cleanup).__name__}: {cleanup}')
        try:
            if (output/'prompt_audit.jsonl').is_file():batch['prompt_audit_sha256']=file_sha(output/'prompt_audit.jsonl')
            workflow.write_json(output/'batch.json',batch,update=True)
        except BaseException as exc:ledger=exc
        try:
            report=inspect_run(output,progress=log)
            report.update(execution_error=batch['execution_error'],cleanup_warning=batch['cleanup_warning'],
                ledger_warning=None if ledger is None else f'{type(ledger).__name__}: {ledger}',
                software_exit='execution_error' if error else 'ledger_error' if ledger else 'cleanup_warning' if cleanup else
                    'success' if report['formal_complete'] else 'verification_incomplete')
            _save_report(output,report)
            log({'phase':'final','model_completed':report['model_completed'],'expected':90,
                'percent':100*report['model_completed']/90,'formal_complete':report['formal_complete'],
                'formal_SR':report['formal_SR'],'software_exit':report['software_exit']})
        except BaseException as exc:
            workflow.write_json(output/'verification_error.json',{'error':f'{type(exc).__name__}: {exc}',
                'execution_error':batch['execution_error'],'cleanup_warning':batch['cleanup_warning']})
            if error is not None:raise error from exc
            raise
    if error is not None:raise error
    if ledger is not None:raise ledger
    if cleanup is not None:raise cleanup
    if not report['formal_complete']:raise RuntimeError('044 formal evidence incomplete; do not retry automatically')
    return report
