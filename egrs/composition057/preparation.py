"""One durable attempt for each fixed057 probe source. No normal bank or model route."""
from copy import deepcopy
from pathlib import Path

from . import catalog
from .contracts import (SCHEMA,CORE_REVISION,contained,digest,implementation_identity,input_identity,
                        load_config,protect_output,read,sha,write)


class CheckpointStorageError(OSError):
    """A spent operation cannot proceed without its durable ledger."""


def activate(cfg):
    from egrs.augmentation.dependencies import activate_core
    revision=activate_core(cfg['benchmark_root'])
    if revision!=CORE_REVISION:raise ValueError('057 fixed core revision differs')
    return revision


def build_source(cfg,row,output,checkpoint):
    from .native import build_source as native_build
    return native_build(cfg,row,output,checkpoint)


def inspect_source(path,row,cfg):
    from .native import inspect_source as native_inspect
    return native_inspect(path,row,cfg)


def _counts(report):
    rows=report['rows'];task_counts={}
    for task in catalog.TASK_ORDER:
        group=[r for r in rows if r['task_id']==task]
        counts={s:sum(r['status']==s for r in group) for s in ('ready','failed','pending','running')}
        counts.update(expected=15,ready_percent=100*counts['ready']/15)
        task_counts[task]=counts
    for status in ('ready','failed','pending','running'):
        report[status]=sum(r['status']==status for r in rows)
    report.update(expected=60,processed=report['ready']+report['failed'],
        attempted=sum(r['status']!='pending' for r in rows),complete=report['ready']==60,
        ready_percent=100*report['ready']/60,processed_percent=100*(report['ready']+report['failed'])/60,
        per_task=task_counts)
    return report


def _summary(root,report):
    lines=['# Task057 counterfactual probe source construction','',
        f"Ready: {report['ready_percent']:.2f}% ({report['ready']}/60); failed={report['failed']}; pending={report['pending']}.",
        '', '| Task | Ready / 15 | Failed | Pending | Ready % |','|---|---:|---:|---:|---:|']
    for task,c in report['per_task'].items():
        lines.append(f"| {task} | {c['ready']} | {c['failed']} | {c['pending']} | {c['ready_percent']:.2f}% |")
    lines.extend(['','Only precompleted states; no ordinary-state bank, training or model rollouts.',
        'Technical readiness does not prove remaining-task feasibility or model generalization.',
        'All failures remain; a fresh directory is not permission to repeat spent sources.'])
    (root/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def _failure_artifacts(root,row):
    source=root/'sources'/row['episode_id']
    return {p.relative_to(root).as_posix():sha(contained(source,p))
        for p in sorted(source.rglob('*')) if p.is_file()}


def prepare(config_path,output):
    cfg=load_config(config_path);root=protect_output(cfg,output,config_path)
    inputs=input_identity(cfg)
    activate(cfg)  # Before any native/helper imports, including in a fresh CLI.
    expected=catalog.expected();catalog.validate_population(expected)
    snapshot={'schema_version':SCHEMA,'config':cfg,'config_sha256':sha(config_path),
        'inputs':inputs,'implementation':implementation_identity(),'expected':expected,
        'source_limit':60,'ordinary_state_count':0,'model_rollouts':0,'eligible_for_training':False}
    root.mkdir(parents=True,exist_ok=False)
    (root/'controls').mkdir()
    report={'schema_version':SCHEMA,'snapshot':snapshot,'preparation_identity':digest(snapshot),
        'rows':[{**deepcopy(row),'status':'pending'} for row in expected],'status':'running',
        'ordinary_state_count':0,'model_rollouts':0,'eligible_for_training':False}
    def save():
        _counts(report);write(root/'sources.json',report)
    save()
    for identity,row in zip(expected,report['rows']):
        row['status']='running';save()  # Spend before any native work; never refund.
        checkpoint_failed=[]
        def checkpoint(event):
            if not isinstance(event,dict):raise ValueError('057 native checkpoint must be an object')
            old=row.get('native_accounting',{})
            for key in ('attempted_control_steps','completed_control_steps','failed_control_steps'):
                if type(event.get(key)) is not int or event[key]<old.get(key,0):
                    raise ValueError('057 native accounting must be integer and monotonic')
            if event['completed_control_steps']+event['failed_control_steps']>event['attempted_control_steps']:
                raise ValueError('057 native accounting exceeds spent calls')
            control=root/'controls'/(identity['episode_id']+'.json')
            try:write(control,event)
            except OSError as error:
                failure=CheckpointStorageError('057 durable native checkpoint failed: '+str(error))
                checkpoint_failed.append(failure)
                raise failure from error
            row.update(native_accounting=deepcopy(event),control_ledger=str(control),control_ledger_sha256=sha(control))
        try:
            result=build_source(cfg,deepcopy(identity),root/'sources'/identity['episode_id'],checkpoint)
            if checkpoint_failed:raise checkpoint_failed[0]
            if result.get('status')!='ready':raise ValueError(result.get('error') or '057 native evidence not ready')
            source=contained(root,result['source_manifest'])
            verified=inspect_source(source,identity,cfg)
            if any(verified.get(k)!=identity[k] for k in ('task_id','initial_state_index','episode_id')):
                raise ValueError('057 verified source identity differs')
            row.update(status='ready',source_manifest=str(source),source_manifest_sha256=sha(source))
        except (KeyboardInterrupt,SystemExit,CheckpointStorageError) as error:
            row.update(status='failed',error=f'{type(error).__name__}: {error}',
                failure_artifacts=_failure_artifacts(root,row))
            report['status']='interrupted';save();_summary(root,report)
            raise
        except Exception as error:
            if checkpoint_failed:raise checkpoint_failed[0] from error
            row.update(status='failed',error=f'{type(error).__name__}: {error}',
                failure_artifacts=_failure_artifacts(root,row))
        save()
        print(f"[057] processed={report['processed']}/60 ({report['processed_percent']:.2f}%) "
            f"ready={report['ready']}/60 ({report['ready_percent']:.2f}%) failed={report['failed']} "
            f"last={identity['episode_id']}:{row['status']}",flush=True)
    report['status']='complete' if report['complete'] else 'incomplete';save();_summary(root,report)
    return report


def read_bank(directory):
    """Offline integrity read only; never reconstruct/retry a missing source."""
    root=Path(directory).resolve();report=read(root/'sources.json')
    snapshot=report['snapshot'];cfg=snapshot['config']
    if (report.get('schema_version')!=SCHEMA or snapshot.get('schema_version')!=SCHEMA
            or report['preparation_identity']!=digest(snapshot) or snapshot['expected']!=catalog.expected()
            or snapshot['inputs']!=input_identity(cfg) or snapshot['implementation']!=implementation_identity()
            or snapshot['source_limit']!=60 or report.get('ordinary_state_count')!=0
            or report.get('model_rollouts')!=0 or report.get('eligible_for_training') is not False):
        raise ValueError('057 frozen construction identity differs')
    catalog.validate_population(report['rows']);activate(cfg)
    for identity,row in zip(catalog.expected(),report['rows']):
        if row.get('status') not in ('ready','failed','pending','running'):raise ValueError('057 invalid source status')
        if row['status']=='failed' and not row.get('error'):raise ValueError('057 missing failure evidence')
        if row['status']=='failed' and row.get('failure_artifacts')!=_failure_artifacts(root,row):
            raise ValueError('057 retained failure artifact inventory or SHA differs')
        if row['status']=='ready' or 'native_accounting' in row:
            control=contained(root,row['control_ledger'])
            expected_control=root/'controls'/(identity['episode_id']+'.json')
            if (control!=expected_control or sha(control)!=row['control_ledger_sha256']
                    or read(control)!=row['native_accounting']):
                raise ValueError('057 native control ledger changed')
        if row['status']=='ready':
            source=contained(root,row['source_manifest'])
            if (source!=root/'sources'/identity['episode_id']/'source.json'
                    or sha(source)!=row['source_manifest_sha256']):
                raise ValueError('057 source manifest identity or SHA differs')
            verified=inspect_source(source,identity,cfg)
            if any(verified.get(k)!=identity[k] for k in ('task_id','initial_state_index','episode_id')):
                raise ValueError('057 source population differs')
    actual=_counts(deepcopy(report))
    keys=('ready','failed','pending','running','attempted','complete','expected','per_task','processed')
    if any(actual[key]!=report[key] for key in keys):raise ValueError('057 stored readiness counts differ from evidence')
    return actual
