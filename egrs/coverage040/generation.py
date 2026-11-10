"""040 train-only orchestration around the accepted039 physical recorder."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from egrs.augmentation.data import _require, identity, read_json
from egrs.coverage039.generation import (AttemptLedger, Heartbeat, _recover_source,
    _relative_attempt, durable_write, initialization_failure, reconcile_attempts)
from egrs.coverage039.io import HashContext, Progress
from egrs.coverage039.recipe import generation_context
from egrs.trajectory_augmentation.data import export_generated
from egrs.trajectory_augmentation.native import TEACHER_V2
from .plan import build_plan


class WorkerCleanupFailure(BaseException):
    """Abort without sealing/exporting when worker termination is unconfirmed."""


def generate_source(source,config,data_root,output_dir):
    """Launch unchanged039 native recording, reaping before any failure recovery."""
    directory=Path(output_dir).resolve();directory.mkdir(parents=True,exist_ok=True)
    config=deepcopy(config);config['teacher_policy']=TEACHER_V2
    ledger=AttemptLedger(config.get('_budget_ledger',directory/'attempt_ledger.json'))
    if not config.get('_normal_pre_reserved'):
        ledger.reserve(source['source_id'],'normal','normal',0)
    elif not ledger.contains(source['source_id'],'normal','normal',0):
        raise ValueError('parent normal reservation missing')
    config.update(_budget_ledger=str(ledger.path.resolve()),_normal_pre_reserved=True)
    initialization_failure(source,directory,'native_initialization_interrupted')
    request=directory/'request.json';response=directory/'result.json'
    durable_write(request,{'source':source,'config':config,'data_root':str(Path(data_root).resolve()),
                          'output_dir':str(directory)})
    backend=config['native_backend'];python=backend.get('python',sys.executable)
    # Preserve the literal venv entry, even when it is a symlink to a base Python.
    command=[python,'-m','egrs.coverage039.native','--request',str(request)]
    timeout=backend.get('source_timeout_seconds',7200)
    if type(timeout) not in (int,float) or not 1<=timeout<=86400:
        raise ValueError('source timeout must be1..86400 seconds')
    progress=Progress('generation_worker');started=time.monotonic();process=None
    try:
        with (directory/'worker.stdout.log').open('wb') as out,(directory/'worker.stderr.log').open('wb') as err:
            process=subprocess.Popen(command,cwd=str(Path(__file__).resolve().parents[2]),stdout=out,stderr=err)
            while True:
                fields={'source':source['source_id'],'attempt':'native_initialization',
                        'elapsed_source_seconds':round(time.monotonic()-started,3)}
                if (directory/'heartbeat.json').exists():fields.update(read_json(directory/'heartbeat.json'))
                progress.update(**fields)
                remaining=timeout-(time.monotonic()-started)
                if remaining<=0:raise subprocess.TimeoutExpired(command,timeout)
                try:
                    code=process.wait(timeout=min(30,remaining))
                    if code!=0:raise RuntimeError('native worker exited '+str(code))
                    return read_json(response)
                except subprocess.TimeoutExpired:
                    if time.monotonic()-started>=timeout:raise
    except BaseException as error:
        if process is not None:
            try:
                # A second parent SIGINT must not skip reaping the first worker.
                while True:
                    try:
                        if process.poll() is None:process.kill()
                        process.wait()
                        break
                    except KeyboardInterrupt:
                        continue
            except BaseException as cleanup_error:
                # The top-level ordinary failure path may recover only after
                # the child can no longer mutate its ledger/metadata files.
                raise WorkerCleanupFailure('native worker cleanup unconfirmed: '+str(cleanup_error)) from cleanup_error
        if not isinstance(error,Exception):raise
        result=_recover_source(source,directory,f'{type(error).__name__}: {error}',ledger)
        durable_write(response,result);return result


class GenerationHeartbeat(Heartbeat):
    """Keep overall completion and live spent counters visible during a worker."""
    def __init__(self,directory,source_id,ledger,*,completed,total):
        super().__init__(directory,source_id,filename='parent_heartbeat.json')
        self.ledger=ledger
        self.fields.update(completed=completed,total=total,percent=100*completed/max(1,total),
                           max_normal_replays=60,max_10_attempts=360)

    def _emit(self):
        worker=self.directory/'heartbeat.json'
        latest=read_json(worker) if worker.exists() else {}
        spent=self.ledger.read()
        with self.lock:
            self.fields.update({key:latest[key] for key in ('phase','controls','attempt') if key in latest})
            self.fields.update(normal_attempts=spent['normal_attempts'],ten_attempts=spent['ten_attempts'])
        super()._emit()


def _output(out,plan):
    output=Path(out).expanduser().resolve()
    protected=[*plan.get('protected_paths',[]),plan['data_root']]
    protected.extend(plan['config'][key] for key in
        ('generation_config','old_task_control_index','old_retention_index','old_merged_export'))
    for value in protected:
        root=Path(value).resolve()
        _require(output!=root and not output.is_relative_to(root) and not root.is_relative_to(output),
                 'new040 output must not overlap any old input/artifact root')
    if output.exists(): raise FileExistsError('new040 generation output required; spent slots cannot be refunded')
    return output


def _binding(plan,output,context):
    plan_path=output/'generation_plan.json';ledger_path=output/'attempt_ledger.json'
    return {'format':'task040-generation-binding-v1','plan_identity':plan['identity'],
        'plan_path':str(plan_path),'plan_sha256':context.sha256(plan_path),
        'ledger_path':str(ledger_path),'ledger_sha256':context.sha256(ledger_path),
        'candidates':deepcopy(plan['candidates']),
        'selected_train_parent_ids':[p['source_id'] for p in plan['sources']],
        'tasks':list(plan['tasks']),'source_range':deepcopy(plan['source_range']),
        'train_only':True,'newnormal_role':'pair_only'}


def _bind_attempt(attempt,directory,binding):
    """Add stage provenance after recording; preserve every039 control fact."""
    attempt=deepcopy(attempt)
    ctx=deepcopy(attempt.get('generation_context',{}));ctx['coverage040']=deepcopy(binding)
    attempt['generation_context']=ctx
    recipe=deepcopy(attempt.get('recipe',{}));recipe['coverage040']=deepcopy(binding)
    attempt['recipe']=recipe;attempt['recipe_identity']=identity(recipe)
    for field in ('lineage_path','qualification_path','audit_path'):
        if attempt.get(field):
            path=(directory/attempt[field]).resolve()
            _require(path.is_relative_to(directory.resolve()),'040 sidecar escapes source directory')
            value=read_json(path);value['generation_context']=deepcopy(ctx)
            if field=='lineage_path': value.update(recipe=deepcopy(recipe),recipe_identity=attempt['recipe_identity'])
            durable_write(path,value)
            if field=='qualification_path' and isinstance(attempt.get('qualification'),dict):
                # The recorder's metadata adds accepted=True; its raw qualifier
                # sidecar deliberately does not carry that export admission key.
                attempt['qualification']['generation_context']=deepcopy(ctx)
    if attempt.get('journal_path'):
        path=(directory/attempt['journal_path']).resolve()
        _require(path.is_relative_to(directory.resolve()),'040 journal escapes source directory')
        with path.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'event':'coverage040_generation_binding','generation_context':ctx},allow_nan=False)+'\n')
            stream.flush();os.fsync(stream.fileno())
    metadata=directory/f"{attempt['domain']}_v{attempt['variant']}_a{attempt['attempt']}"/'metadata.json'
    durable_write(metadata,attempt)
    return attempt


def generate(config_path,out,*,source_generator=None,context=None,plan=None):
    context=context if context is not None else HashContext()
    plan=build_plan(config_path,context=context) if plan is None else deepcopy(plan)
    _require(plan.get('format')=='task040-parent-coverage-plan-v1' and identity(plan)==plan.get('identity'),
             'sealed040 plan required')
    selected=plan['sources'];candidate_ids={p['source_id']:p for p in plan['candidates']}
    _require(len(candidate_ids)==60 and len(plan['parents'])==240
             and plan['parents'][180:]==plan['candidates']
             and selected==[p for p in plan['candidates'] if p['selection_reason']=='selected_new_train']
             and len({p['source_id'] for p in selected})==len(selected)
             and all(candidate_ids.get(p['source_id'])==p and p['split']=='train'
                     and p['selection_reason']=='selected_new_train' for p in selected),
             '040 generation must use only fixed new train representatives')
    output=_output(out,plan);cfg=plan['execution_config']
    for path,digest in plan['old_dependencies']['metadata_inputs'].items():context.verify(path,digest)
    context.verify(cfg['stats_path'],cfg['stats_sha256'])
    for source in selected:
        context.verify(Path(plan['data_root'])/source['file'],source['file_sha256'])
    output.mkdir(parents=True);durable_write(output/'generation_plan.json',plan)
    ledger=AttemptLedger(output/'attempt_ledger.json')
    durable_write(ledger.path,ledger.read())
    source_generator=source_generator or generate_source
    reports=[];errors=0;progress=Progress('generation040_sources');interruption=None
    for index,source in enumerate(selected):
        directory=output/'artifacts'/f'source-{index:03d}';directory.mkdir(parents=True)
        source_cfg=deepcopy(cfg);source_cfg.update(_budget_ledger=str(ledger.path),_normal_pre_reserved=True,
            _plan_identity=plan['identity'],save_video=source['demo_index']==20)
        ledger.reserve(source['source_id'],'normal','normal',0)
        initialization_failure(source,directory,'native_initialization_interrupted')
        spent=ledger.read()
        progress.update(source=source['source_id'],completed=index,total=len(selected),phase='starting_source',
            normal_attempts=spent['normal_attempts'],max_normal_replays=60,
            ten_attempts=spent['ten_attempts'],max_10_attempts=360)
        try:
            with GenerationHeartbeat(directory,source['source_id'],ledger,completed=index,total=len(selected)):
                result=source_generator(deepcopy(source),source_cfg,Path(plan['data_root']),directory)
            _require(result.get('source_id')==source['source_id'] and isinstance(result.get('attempts'),list),
                     '040 generator source/attempt contract differs')
            errors+=int(bool(result.get('error')))
        except (Exception,KeyboardInterrupt) as error:
            errors+=1;result=_recover_source(source,directory,f'{type(error).__name__}: {error}',ledger)
            if isinstance(error,KeyboardInterrupt): interruption=error
        result['attempts']=reconcile_attempts(source,directory,ledger,'attempt_interrupted_before_metadata_persist')
        reports.append(result);durable_write(directory/'source_report.json',result)
        durable_write(output/'generation_progress.json',{'plan_identity':plan['identity'],
            'processed_sources':len(reports),'planned_sources':len(selected),
            'completion_percent':100*len(reports)/max(1,len(selected)),'spent':ledger.read()})
        spent=ledger.read()
        progress.update(completed=len(reports),total=len(selected),source=source['source_id'],
            normal_attempts=spent['normal_attempts'],ten_attempts=spent['ten_attempts'],phase='source_completed')
        if interruption is not None: break
    # The ledger is now immutable. Hash it once with the same live production context.
    binding=_binding(plan,output,context);attempts=[]
    for index,result in enumerate(reports):
        source=selected[index];directory=output/'artifacts'/f'source-{index:03d}'
        rows=reconcile_attempts(source,directory,ledger,'attempt_interrupted_before_export')
        rows=[_bind_attempt(row,directory,binding) for row in rows]
        result['attempts']=rows;durable_write(directory/'source_report.json',result)
        attempts.extend(_relative_attempt(row,directory,output) for row in rows)
    spent=ledger.read();declared=generation_context(plan['identity'],normal_attempts=spent['normal_attempts'],
                                                ten_attempts=spent['ten_attempts'])
    declared['coverage040']=binding
    data=export_generated(plan['parents'],attempts,output,output/'export',generation_context=declared,context=context)
    manifest=read_json(output/'export/sources.json')
    added=sum(s['domain']=='10' and s['split']=='train' for s in manifest['sources'].values())
    result={'format':'task040-generation-report-v1','plan_identity':plan['identity'],'export':str(output/'export'),
        'population':plan['population'],'source_reports':reports,'source_errors':errors,'data':data,
        'generation_context':declared,'actual_new_train_10':added,
        'actual_qualified_10':data['counts_by_domain']['10']['trajectories'],
        'actual_qualified_normal':data['counts_by_domain']['normal']['trajectories'],'spent':spent,
        'processed_sources':len(reports),'planned_sources':len(selected),
        'completion_percent':100*len(reports)/max(1,len(selected)) if selected else 100.,
        'status':'interrupted' if interruption else 'completed_with_source_gaps' if errors or data['failed_attempts'] else 'completed',
        'model_loaded':False}
    result['identity']=identity(result);durable_write(output/'generation_report.json',result)
    progress.finish(completed=len(reports),total=len(selected),normal_attempts=spent['normal_attempts'],
                    ten_attempts=spent['ten_attempts'])
    if interruption is not None: raise interruption
    return result
