"""Continue a new run from11 immutable completed052 raw episodes, never replay.

The original052450-source plan, worker, rollout, video and034 binary scoring
remain. This only fixes private result/evidence index admission and adds explicit
read-only parent inheritance. The user starts every real model evaluation.
"""
from copy import deepcopy
from pathlib import Path

from egrs.remain049 import evaluation as original, sources as old
from egrs.remain052 import evaluation as previous, scope
from . import validation

PARENT_PLAN_SHA='68a4e754f398c5abaaff96dc9f4f84aa3692ba7e08adae2d2fbdcf74f5c6a0d4'
PARENT_SUMMARY_SHA='05b388fd112f5644811da6895252c2be3d18bf3a0362ea7a5f73dcec5266f7d4'
BANK_SHA='54a225330e43bb88cd6299109798885ee2ac6af06d9492f8d5639f2d62e29747'
INHERITED=tuple(f'basket_s{i:03d}_10' for i in range(11))

load_config=previous.load_config
compare=previous.compare


def engine():
    namespace=previous.engine()
    namespace['verify_episode']=validation.verifier(namespace)
    return namespace


def closed_record(folder,source,frozen,row):
    """Keep an already accepted score; verify bytes, not its closed trace again."""
    from benchmark.remaining_goals.headless import workflow
    record=deepcopy(row['diagnostics']);episode=source['episodes'][0]
    metadata=old.read(folder/'task_run.json')
    if (metadata.get('status')!='completed' or metadata.get('cleanup_errors')
            or metadata['source_plan']!=source or metadata['batch_identity_sha256']!=frozen['plan_sha256']
            or metadata['runtime_config']!=frozen['runtime'] or metadata['missing']
            or metadata['attempts']!=[episode['episode_id']] or len(metadata['results'])!=1
            or record['source']['model_identity']!=workflow._model_identity(metadata)):
        raise ValueError('053 closed parent metadata differs')
    original._verify_model(frozen,metadata['model_runtime'])
    wanted={str((folder/'task_run.json').resolve())}
    ref=metadata['results'][0];raw_path=workflow._contained(folder,ref['path']);wanted.add(str(raw_path))
    references=record['source']['verified_files']
    if {str(Path(r['path']).resolve()) for r in references}!=wanted:
        raise ValueError('053 closed record must bind its exact original metadata/raw')
    for r in references:
        if old.sha(r['path'])!=r['sha256']:raise ValueError('053 closed parent file changed')
    if old.sha(raw_path)!=ref['sha256']:raise ValueError('053 closed parent raw changed')
    raw=old.read(raw_path)
    if raw.get('status')!='completed' or raw.get('episode_id')!=episode['episode_id']:
        raise ValueError('053 closed parent execution incomplete')
    video=raw['video']
    if video.get('status')!='saved' or old.sha(workflow._contained(folder,video['path']))!=video['sha256']:
        raise ValueError('053 closed parent video changed')
    evidence=raw['execution_evidence'];ep=workflow._contained(folder,evidence['path'])
    if old.sha(ep)!=evidence['sha256']:raise ValueError('053 closed input evidence changed')
    inputs=old.read(ep)
    for reference in [inputs['initial_observation']]+[q['observation'] for q in inputs['queries']]:
        if old.sha(workflow._contained(ep.parent,reference['path']))!=reference['sha256']:
            raise ValueError('053 closed input image/proprio bytes changed')
    for item in source['source_acceptance']['selected_files']:
        target=workflow._contained(folder,f"source/{item['root']}_files/{item['path']}")
        if old.sha(target)!=item['sha256']:raise ValueError('053 closed source snapshot changed')
    record['source']['inheritance_verification']='original accepted score plus immutable raw/video/input/source bytes; no trace regrading'
    return record


def parent(cfg,path,namespace):
    old.activate(cfg)
    path=Path(path).resolve()
    if old.sha(path/'plan.json')!=PARENT_PLAN_SHA:
        raise ValueError('053 parent plan changed; preserve the exact052 run')
    print('[053] Reading frozen parent plan; file-only checks, no model or physics',flush=True)
    frozen=old.read(path/'plan.json')
    if (frozen.get('model')!='base' or frozen.get('config')!=cfg
            or frozen.get('expected')!=old.expected() or frozen.get('extension')!=scope.extension_identity()
            or frozen.get('source_bank_sha256')!=BANK_SHA
            or old.sha(Path(cfg['source_bank'])/'sources.json')!=BANK_SHA):
        raise ValueError('053 parent model/config/population/source bank differs')
    dirs={p.name for p in (path/'episodes').iterdir() if p.is_dir()}
    if dirs!=set(INHERITED):
        raise ValueError('053 requires exactly11 recorded parent episodes, no hidden repeat or partial episode')
    if old.sha(path/'summary.json')!=PARENT_SUMMARY_SHA:
        raise ValueError('053 original partial summary changed')
    summary=old.read(path/'summary.json')
    if (summary.get('software_exit')!='incomplete' or summary['counts']['completed']!=10
            or summary.get('plan_sha256')!=frozen['plan_sha256']
            or summary.get('execution_errors')!=[{'phase':'execution',
                'error':'ValueError: task011 sources are official indices zero through nine'}]):
        raise ValueError('053 parent failure is not the pinned index-admission interruption')
    scoped=scope.helpers();records={};files=[];loaded=None
    from benchmark.remaining_goals.headless.workflow import shared_model_identity
    for source,name in zip(frozen['sources'],INHERITED):
        print(f'[053] Verifying inherited {len(records)+1}/11: {name}; no new actions',flush=True)
        if source['episodes'][0]['episode_id']!=name:
            raise ValueError('053 inherited episodes are not the exact original prefix')
        folder=path/'episodes'/name
        index=len(records)
        record=(closed_record(folder,source,frozen,summary['episodes'][index]) if index<10
                else namespace['verify_episode'](folder,source,frozen,scoped))
        metadata=old.read(folder/'task_run.json')
        current=shared_model_identity(metadata['model_runtime'])
        if loaded is not None and loaded!=current:
            raise ValueError('053 parent loaded model changed across episodes')
        loaded=current
        record['source'].update(new_execution=False, inherited_from=str(path),
            validation_extension=validation.identity(), old_run_formally_completed=False)
        records[name]=record
        print(f'[053] Verified inherited {len(records)}/11 ({len(records)/11*100:.2f}%)',flush=True)
        files.extend(deepcopy(record['source']['verified_files']))
    for row in summary['episodes'][:10]:
        name=row['episode_id']
        from libero_remain_reporting import map_verified_results
        wanted=next(e for e in frozen['expected'] if e['episode_id']==name)
        new=map_verified_results([wanted],{name:records[name]})
        if new['integrity_errors'] or new['episodes'][0]['success'] is not row['success']:
            raise ValueError('053 must preserve all prior10 reported outcomes, including failures')
    receipt={'format':'task053-immutable-parent-continuation-v1','parent_run':str(path),
        'parent_plan_sha256':PARENT_PLAN_SHA,'source_bank_sha256':BANK_SHA,
        'inherited_episode_ids':list(INHERITED),'inherited_executed':11,'old_formally_reported':10,
        'recovered_complete_raw_without_new_actions':1,'new_base_execution_limit':439,
        'new_h1_execution_limit':450,'original_total_execution_limit':900,
        'validation_extension':validation.identity(),'verified_parent_files':files,
        'parent_summary_sha256':PARENT_SUMMARY_SHA,'old_failure_kept':True,
        'already_closed_trace_revalidation':False,'complete_raw_reverification_count':1}
    receipt['identity']=old.digest(receipt)
    return frozen,records,loaded,receipt


def run(cfg,output,model,*,continue_from=None):
    output=Path(output).resolve()
    original.protect_output(cfg,output)
    if (model=='base')!=(continue_from is not None):
        raise ValueError('053 base requires explicit parent; H1 must be a fresh450 run')
    namespace=engine();records={};loaded=None
    receipt={'format':'task053-fresh-h1-v1','new_execution_limit':450,
             'validation_extension':validation.identity()}
    if continue_from is not None:
        parent_path=Path(continue_from).resolve()
        if output==parent_path or output in parent_path.parents or parent_path in output.parents:
            raise ValueError('053 output must not overlap immutable parent')
        frozen,records,loaded,receipt=parent(cfg,parent_path,namespace)
        namespace['plan']=lambda cfg,model:frozen
    original_verify=namespace['_verify_model']
    def verify_model(plan,provenance):
        original_verify(plan,provenance)
        if loaded is not None:
            from benchmark.remaining_goals.headless.workflow import shared_model_identity
            if shared_model_identity(provenance)!=loaded:
                raise ValueError('053 continued worker has different loaded base assets/statistics')
    namespace['_verify_model']=verify_model
    execute=namespace['execute_episode'];used=set();new_calls=[]
    def execute_or_inherit(folder,source,plan,policy,scoped):
        name=source['episodes'][0]['episode_id']
        if name in records:
            if name in used or Path(folder).exists():
                raise ValueError('053 inherited episode must never be re-executed')
            used.add(name)
            print(f'[053][base] inherited={len(used)}/11 episode={name}; no new actions',flush=True)
            return deepcopy(records[name])
        new_calls.append(name)
        if len(new_calls)>(439 if model=='base' else 450) or len(set(new_calls))!=len(new_calls):
            raise ValueError('053 new execution budget or uniqueness exceeded')
        return execute(folder,source,plan,policy,scoped)
    namespace['execute_episode']=execute_or_inherit
    write=namespace['write']
    def write_with_lineage(path,value):
        path=Path(path)
        if path==output/'summary.json':
            value={**value,'continuation':deepcopy(receipt),'inherited_completed':len(used),
                'new_execution_attempts':len(new_calls),'validation_extension':validation.identity()}
        write(path,value)
        if path==output/'plan.json':
            write(output/'continuation.json',receipt)
    namespace['write']=write_with_lineage
    result=namespace['run'](cfg,output,model)
    if used!=set(records):
        raise ValueError('053 completed report omitted inherited episodes')
    return old.read(output/'summary.json')
