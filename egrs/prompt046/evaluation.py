"""Trained045 H1@3000, fixed044 text, same original90 ten.

The accepted core still owns source archival, environment execution, evidence,
video and full-task scoring. No fabricated00 population is
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

SCHEMA='task046-prompt-eval-v1'
FACTORY='egrs.prompt046.policy:make_policy'
PROMPT_MANIFEST_SHA256='e648ef202c31e6e99e14478f6ec36952a1791d2187bf023a224b25974f669566'
REFERENCE_PLAN_SHA256='1d1c79e0147c2758dbabaa0b9cf171c8095e437486dde6bd015785b60b23a9eb'
P0_SUMMARY_SHA256='4e745dbeba93f0a5f16fc637c90dbe19a816c10f7915d1ae6f0d4a4a381107f4'
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
    if not isinstance(value,str) or not value.strip():raise ValueError('046 requires explicit nonempty paths')
    value=os.path.expanduser(os.path.expandvars(value))
    if re.search(r'\$[A-Za-z_{]|%[^%]+%|[<>]',value):raise ValueError('Unresolved044 path or placeholder')
    path=Path(value)
    return str((base/path).resolve() if not path.is_absolute() else path.resolve())


def load_config(path):
    path=Path(path).resolve();cfg=_read(path)
    fields={'schema_version','variant','prompt_manifest','reference_plan','p0_summary','method_adapter','benchmark_root',
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
    roots += [Path(cfg[k]).parent for k in ('reference_plan','prompt_manifest','p0_summary')]
    roots += [Path(cfg['base_runtime']),Path(cfg['method_adapter'])]
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
    if target.exists():raise FileExistsError('046 requires new output; existing attempts are never overwritten or resumed')
    reference=_read(config['reference_plan'])
    if any(target==p or p in target.parents or target in p.parents for p in _input_paths(config,reference)):
        raise ValueError('044 output overlaps protected input or data root')
    return target


def _validate_population(plan,manifest):
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.planning import canonical_hash
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from egrs.prompt044.prompts import prompt_record
    expected=expected_episodes('nine-mask10')
    if plan.get('expected')!={'10':expected} or len(plan['tasks'])!=36 or plan['budget']!=BUDGET:
        raise ValueError('046 requires only the fixed original36 units/90 ten episodes and budget')
    lookup={e['episode_id']:e for e in expected};seen=set();keys=set()
    for task in plan['tasks']:
        if task['condition']!='10' or task['key'] in keys:raise ValueError('Foreign or duplicate044 unit')
        keys.add(task['key']);source=task['source']
        if source['source_plan_sha256']!=canonical_hash({k:v for k,v in source.items() if k!='source_plan_sha256'}):
            raise ValueError('046 original source hash differs')
        for ep in source['episodes']:
            name=ep['episode_id']
            if name not in lookup or name in seen or any(ep.get(k)!=lookup[name][k] for k in previous.IDENTITY_FIELDS):
                raise ValueError('046 source population differs from original90 ten')
            seen.add(name)
            record=prompt_record(manifest,plan['config']['variant'],ep['instruction'])
            if record['task_id']!=ep['task_id'] or record['official_task_id']!=lookup[name]['libero_task_id']:
                raise ValueError('044 exact instruction conflicts with original task identity')
            if ep['task_id'] in REUSE_TASKS:
                if task['scoped'] or len(source['episodes'])!=10:raise ValueError('044 legacy ten source grouping differs')
            elif not task['scoped'] or len(source['episodes'])!=1 or source['protocol']!='nine-mask10':
                raise ValueError('044 new three ten source protocol differs')
    if seen!=set(lookup):raise ValueError('046 missing original ten episode')


def build_plan(config_path):
    from egrs.prompt044.prompts import load_manifest,validate_native_runtime
    cfg=load_config(config_path);manifest=load_manifest(cfg['prompt_manifest'])
    if file_sha(cfg['reference_plan'])!=REFERENCE_PLAN_SHA256:raise ValueError('046 frozen reference plan byte SHA differs')
    reference=_read(cfg['reference_plan'])
    core=activate_core(cfg['benchmark_root']);reporting=activate_reporting(cfg['reporting_root'])
    if core!=reference['core_revision'] or core!=CORE_REVISION or reporting!=reference['reporting_revision'] or reporting!=REPORTING_REVISION:
        raise ValueError('046 actual core/reporting revisions differ from reference metadata')
    from benchmark.remaining_goals.headless import nine_planning,planning,scoped_sources
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,binding_for,coordination_identity
    runtime=nine_planning.load_runtime(cfg['base_runtime']);validate_native_runtime(runtime)
    if runtime!=reference['base_runtime']:raise ValueError('046 original base runtime differs from frozen reference')
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
        if item['environment_binding']!=binding:raise ValueError('046 source bridge binding differs')
    coordination=coordination_identity()
    if coordination!=reference['proxy_coordination']:raise ValueError('044 proxy coordination differs')
    actual_projection=projection_hash(tasks)
    plan={'schema_version':SCHEMA,'config':cfg,'base_runtime':runtime,'core_revision':core,'reporting_revision':reporting,
        'reference_plan_sha256':REFERENCE_PLAN_SHA256,'expected':{'10':expected},'tasks':tasks,
        'environment_dispatch':dispatch,'proxy_coordination':coordination,'policy_factory':FACTORY,
        'prompt_manifest_sha256':PROMPT_MANIFEST_SHA256,'budget':deepcopy(BUDGET),
        'simulation_created':False,'weights_loaded':False,'new_model_execution_only':True,
        'source_projection':{'actual_full_ten_tasks_sha256':actual_projection,
            'approved_projection_sha256':DECLARED_TEN_PROJECTION_SHA256,
            'matches_approved_projection':actual_projection==DECLARED_TEN_PROJECTION_SHA256,
            'binding':'complete reference file byte SHA plus exact source reconstruction and expected10 hash',
            'note':'Approval does not specify the ten-task projection field selection; no guessed projection gate replaces full-file binding.'}}
    from .policy import read_bound_adapter
    identity=read_bound_adapter(cfg['method_adapter'])
    plan.update(adapter_identity=identity,research_adapter_loaded=True,
        deployment_initial_semantic_information=True,checkpoint_step=3000,arm='h1',
        p0=read_p0(cfg,reference,identity))
    _validate_population(plan,manifest)
    plan['plan_sha256']=projection_hash(plan)
    return plan


def check_policy(plan,provenance):
    from .policy import check_metadata
    metadata=provenance.get('policy_metadata',{})
    check_metadata(plan['base_runtime'],metadata)
    if (metadata.get('prompt_variant')!=plan['config']['variant']
            or metadata.get('prompt_manifest_sha256')!=PROMPT_MANIFEST_SHA256
            or metadata.get('method_adapter')!=plan['adapter_identity']
            or metadata.get('prompt_fact_time')!='episode_initial_only'
            or metadata.get('prompt_fixed_during_episode') is not True):
        raise ValueError('046 actual trained model/prompt identity differs')


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
    from egrs.prompt044.prompts import load_manifest,prompt_record
    rows=[json.loads(line,object_pairs_hook=_object) for line in Path(path).read_text(encoding='utf-8').splitlines()]
    if (not rows or any(not isinstance(row,dict) or row.get('schema_version')!='task044-prompt-audit-v1' for row in rows)
            or rows[0].get('event')!='initialized' or rows[0].get('metadata')!=provenance['policy_metadata']
            or rows[0].get('budget')!={'episodes':90,'predict_calls':5850,'predict_calls_per_episode':65}):
        raise ValueError('046 prompt audit initial native identity differs')
    manifest=load_manifest(plan['config']['prompt_manifest'])
    episodes={ep['episode_id']:ep for task in plan['tasks'] for ep in task['source']['episodes']}
    ordinal=sequence=query=0;queries={};results=set();pending=None;bindings=[];failed=set()
    if len(set(attempts))!=len(attempts):raise ValueError('046 duplicate attempted episode')
    for row in rows[1:]:
        event=row.get('event')
        if event=='episode_reset':
            ordinal+=1;query=0
            if type(row.get('episode_ordinal')) is not int or row['episode_ordinal']!=ordinal or ordinal>len(attempts) or ordinal>90 or pending is not None:
                raise ValueError('046 prompt reset/order differs from actual episode attempts')
            name=attempts[ordinal-1];queries[name]=0
            bindings.append({'episode_id':name,'episode_ordinal':ordinal,
                **prompt_record(manifest,plan['config']['variant'],episodes[name]['instruction'])})
        elif event=='predict':
            sequence+=1;query+=1
            if (any(type(row.get(k)) is not int for k in ('sequence','episode_ordinal','episode_query'))
                    or ordinal<1 or pending is not None or row.get('sequence')!=sequence or row.get('episode_ordinal')!=ordinal
                    or row.get('episode_query')!=query or sequence>5850 or query>65):
                raise ValueError('046 prompt prediction budget or sequence differs')
            name=attempts[ordinal-1];expected=prompt_record(manifest,plan['config']['variant'],episodes[name]['instruction'])
            if any(row.get(k)!=v for k,v in expected.items()):raise ValueError('046 actual prompt language or hash differs')
            queries[name]+=1;pending=sequence
        elif event=='predict_result':
            if (any(type(row.get(k)) is not int for k in ('sequence','episode_ordinal','episode_query'))
                    or row.get('sequence')!=pending or row.get('episode_ordinal')!=ordinal or row.get('episode_query')!=query
                    or pending in results or row.get('status') not in ('returned','error')):
                raise ValueError('046 prompt prediction result binding differs')
            if row['status']=='error':failed.add(attempts[ordinal-1])
            results.add(pending);pending=None
        else:raise ValueError('044 unknown prompt audit event')
    if ordinal!=len(attempts):raise ValueError('046 prompt audit is missing episode resets')
    for name,raw in raws.items():
        if queries.get(name)!=raw['policy_queries'] or len(raw['queries'])!=raw['policy_queries']:
            raise ValueError('046 prompt audit query count differs from original raw')
        if raw['status']=='completed' and (pending is not None or name in failed):
            raise ValueError('044 completed raw has unfinished or failed prompt call')
    return {'predict_calls':sequence,'limit':5850,'episode_resets':ordinal,'bindings':bindings,
            'file_sha256':file_sha(path),'pending_call':pending,'failed_calls_not_refunded':True}


def read_p0(cfg,reference,identity):
    if file_sha(cfg['p0_summary'])!=P0_SUMMARY_SHA256:
        raise ValueError('046 reused P0 summary byte SHA differs')
    summary=_read(cfg['p0_summary'])
    if (summary.get('arm')!='h1' or summary.get('checkpoint_step')!=3000
            or summary.get('method_adapter')!=identity or reference.get('adapter_identity')!=identity
            or reference.get('arm')!='h1' or reference.get('checkpoint_step')!=3000
            or summary.get('deployment_hint') is not False or reference.get('deployment_hint') is not False
            or summary.get('formal_complete') is not True or summary.get('model_completed')!=180
            or summary.get('software_exit')!='success'
            or any(summary.get(k) is not None for k in ('execution_error','cleanup_warning','ledger_warning'))):
        raise ValueError('046 P0 must be the completed unhinted same H1@3000, not original-model P0')
    report=summary['conditions']['10']['report']
    expected={e['episode_id']:e for e in reference['expected']['10']}
    rows=report['episodes'];small=[];seen=set()
    if report.get('integrity_errors') or report.get('model_aggregation_compatible') is not True:
        raise ValueError('046 P0 report has integrity issues')
    for row in rows:
        eid=row['episode_id']
        if (eid in seen or eid not in expected or row['task_id']!=expected[eid]['task_id']
                or type(row['success']) is not bool or row['execution_status']!='completed'):
            raise ValueError('046 P0 episode population or outcome differs')
        seen.add(eid);small.append({'episode_id':eid,'task_id':row['task_id'],'success':row['success']})
    rate={'numerator':62,'denominator':90,'percent':100*62/90}
    if (seen!=set(expected) or len(rows)!=90 or sum(x['success'] for x in small)!=62
            or summary['conditions']['10']['formal_SR']!=rate):
        raise ValueError('046 P0 must preserve the actual62of90 outcome table')
    return {'comparison':'paired_same_model_historical_reference','rate':rate,
            'source_run':'task045-h1-step3000-eval-001','summary_sha256':P0_SUMMARY_SHA256,
            'plan_sha256':REFERENCE_PLAN_SHA256,'new_execution':False,'episodes':small}


def paired_results(left,right):
    a={x['episode_id']:x for x in left};b={x['episode_id']:x for x in right}
    if len(a)!=90 or len(b)!=90 or set(a)!=set(b):
        raise ValueError('046 paired comparison requires the same90 complete episodes')
    gained=[];lost=[];both=neither=0
    for eid,x in a.items():
        y=b[eid]
        if x['task_id']!=y['task_id'] or type(x['success']) is not bool or type(y['success']) is not bool:
            raise ValueError('046 paired task or binary outcome differs')
        if x['success'] and y['success']:both+=1
        elif y['success']:gained.append(eid)
        elif x['success']:lost.append(eid)
        else:neither+=1
    return {'counts':{'both':both,'gained':len(gained),'lost':len(lost),'neither':neither},
            'gained':sorted(gained),'lost':sorted(lost)}


def make_report(records,plan,issues=None):
    from libero_remain_reporting import map_verified_results
    binary=map_verified_results(plan['expected']['10'],records,artifact_issues=issues or [])
    rate=binary['counts']['formal_SR'];p0=deepcopy(plan['p0'])
    pairs=paired_results(p0['episodes'],binary['episodes']) if rate is not None else None
    return {'schema_version':SCHEMA,'variant':plan['config']['variant'],'budget':deepcopy(BUDGET),
        'formal_SR':rate,'formal_complete':rate is not None,'model_completed':binary['counts']['completed'],
        'binary_report':binary,'p0':p0,'paired_vs_p0':pairs,
        'delta_from_p0_percentage_points':None if rate is None else rate['percent']-p0['rate']['percent'],
        'method_adapter':deepcopy(plan['adapter_identity']),'arm':'h1','checkpoint_step':3000,
        'research_adapter_loaded':True,'deployment_initial_semantic_information':True,
        'prompt_manifest_sha256':PROMPT_MANIFEST_SHA256,
        'note':'Same trained H1@3000; P0 reuses completed045. P1/P2 are informed initial-semantic diagnostics. Full original A+B/A protection remain scored; no new00 or AVG.'}


def inspect_run(directory,*,progress=None):
    from egrs.prompt044.prompts import load_manifest
    from egrs.trajectory_augmentation.environment_dispatch import validate_dispatch,coordination_identity
    directory=Path(directory);plan=_read(directory/'plan.json');batch=_read(directory/'batch.json')
    if (plan.get('schema_version')!=SCHEMA or batch.get('schema_version')!=SCHEMA
            or plan.get('plan_sha256')!=projection_hash({k:v for k,v in plan.items() if k!='plan_sha256'})
            or batch.get('plan_sha256')!=plan['plan_sha256'] or not plan.get('new_model_execution_only')
            or 'continuation' in plan
            or any(t.get('status')=='inherited' for t in batch['tasks'].values())):
        raise ValueError('046 frozen plan/batch identity differs or inherited/research results requested')
    from .policy import read_bound_adapter
    cfg=plan['config']
    if file_sha(cfg['reference_plan'])!=REFERENCE_PLAN_SHA256:
        raise ValueError('046 frozen P0 plan changed')
    identity=read_bound_adapter(cfg['method_adapter'])
    if identity!=plan.get('adapter_identity') or read_p0(cfg,_read(cfg['reference_plan']),identity)!=plan.get('p0'):
        raise ValueError('046 frozen adapter or P0 reference changed')
    activate_core(cfg['benchmark_root']);activate_reporting(cfg['reporting_root'])
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
                if actual!=allowed[:len(actual)]:raise ValueError('046 original episode attempt order differs')
                attempts.extend(actual)
                if metadata['status']=='technical_pause':issues.append({'task_id':item['key'],'error':metadata.get('error')})
                episodes={ep['episode_id']:ep for ep in item['source']['episodes']}
                for raw in values:
                    name=raw['episode_id']
                    if name in raws:raise ValueError('046 duplicate raw episode')
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
        if batch.get('prompt_audit_sha256')!=audit['file_sha256']:raise ValueError('046 prompt audit bytes differ from closed worker ledger')
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
    header=f"# Task046 {report['variant']}: H1@3000 prompt diagnostic\n\n"
    header+='P0: reused same H1@3000 62/90 (68.89%), no new P0 execution. Full original A+B/A protection remain scored.\n\n'
    if report.get('paired_vs_p0') is not None:
        p=report['paired_vs_p0']['counts'];header+=f"Paired vs P0: gained{p['gained']} / lost{p['lost']} / both{p['both']} / neither{p['neither']}.\n\n"
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
        if batch.get('loaded_base_identity',actual)!=actual:raise ValueError('046 actual loaded native model changed')
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
                prompt_manifest=cfg['prompt_manifest'],prompt_audit_path=str(output/'prompt_audit.jsonl'),
                method_adapter=cfg['method_adapter'],hint043_arm='h1',hint043_checkpoint_step=3000)
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
