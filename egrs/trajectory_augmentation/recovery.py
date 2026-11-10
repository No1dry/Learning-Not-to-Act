"""Explicit user-started teacher-v2 recovery; imports and plan are file-only."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil

from egrs.augmentation.data import _require, file_sha256, identity, read_json
from .data import DOMAINS, export_generated
from .recovery_plan import build_recovery_plan

TEACHER_V1='strict-event-unknown-v1'
TEACHER_V2='table-drop-unknown-diagnostic-v2'
ARTIFACT_FIELDS=('file','audit','video','qualification_file','audit_path','lineage_path',
                 'qualification_path','journal_path')


def _write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def _inside(root,relative):
    _require(isinstance(relative,str) and not Path(relative).is_absolute(),'relative recovery artifact required')
    path=(root/relative).resolve()
    _require(path.is_relative_to(root.resolve()),'recovery artifact escapes archive root')
    return path


def _reuse(plan,output):
    """Copy byte-bound v1 artifacts, never requalify or execute their parents."""
    legacy=Path(plan['legacy_root']);references={r['source_id']:r for r in plan['evidence']['reused_sources']}
    rows=[]
    for original in plan['reused_sources']:
        row=deepcopy(original);ref=references[row['source_id']]
        _require(not {k for k in ARTIFACT_FIELDS if isinstance(row.get(k),str)}-set(ref['files']),
                 'reused artifact has no approved byte reference')
        for key,binding in ref['files'].items():
            source=_inside(legacy,binding['relative_path'])
            _require(source.stat().st_size==binding['bytes'] and file_sha256(source)==binding['sha256'],
                     'reused artifact identity changed before copy')
            relative=(Path('reused/generated002')/binding['relative_path']).as_posix()
            destination=_inside(output,relative);destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
            _require(not destination.is_symlink() and destination.stat().st_size==binding['bytes']
                and file_sha256(destination)==binding['sha256'],'reused copied artifact identity differs')
            row[key]=relative
        row['teacher_policy']=TEACHER_V1
        row['reused_from_generated002']={'source_id':original['source_id'],'new_execution':False,
            'original_export_sources_sha256':plan['evidence']['reused_export_sources']['sha256'],
            'files':deepcopy(ref['files'])}
        rows.append(row)
    _write(output/'reuse_manifest.json',{'teacher_policy':TEACHER_V1,'new_execution':False,'sources':rows})
    return rows


def _summary(rows):
    failed=Counter(r.get('failure_reason','unreported') for r in rows if not r['qualified'])
    qualified=[r for r in rows if r['qualified']]
    return {'attempts':len(rows),'qualified_trajectories':len(qualified),
        'failed_attempts':len(rows)-len(qualified),'failure_reasons':dict(failed),
        'counts_by_domain':{d:sum(r['domain']==d for r in qualified) for d in DOMAINS},
        'parent_sources':len({r['parent_demo_id'] for r in rows}),
        'diagnostic_events':dict(Counter(e['event'] for r in rows
            for e in r.get('qualification',{}).get('diagnostic_events',[])))}


def _pools(sources):
    result={}
    for split in ('train','dev'):
        for domain in DOMAINS:
            rows=[s for s in sources.values() if s['split']==split and s['domain']==domain]
            result[split+'|'+domain]={'trajectories':len(rows),'windows':sum(s['length'] for s in rows),
                'parent_sources':len({s['parent_demo_id'] for s in rows}),
                'parent_groups':len({s['source_group'] for s in rows})}
    return result


def recover(config_path,output,*,source_generator=None):
    """Validate the full original plan, reuse eight, execute only approved73."""
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('new recovery output directory required')
    plan=build_recovery_plan(config_path)
    legacy=Path(plan['legacy_root']).resolve()
    _require(not output.is_relative_to(legacy) and not legacy.is_relative_to(output),
             'new recovery output must be separate from legacy run')
    original=plan['original_plan'];config=deepcopy(original['config'])
    _require(file_sha256(config['stats_path'])==config['stats_sha256'],'original statistics bytes changed')
    config['teacher_policy']=TEACHER_V2
    if source_generator is None:
        from .generation import generate_source
        source_generator=generate_source
    output.mkdir(parents=True)
    _write(output/'recovery_plan.json',plan)
    reused=_reuse(plan,output);new=[];reports=[];errors=0
    first={}
    for parent in plan['sources']:first.setdefault(parent['task_key'],parent['source_id'])
    for index,parent in enumerate(plan['sources']):
        folder=output/'artifacts'/f'source-{index:03d}';folder.mkdir(parents=True)
        cfg=deepcopy(config);cfg['save_video']=parent['source_id']==first[parent['task_key']]
        try:
            report=source_generator(deepcopy(parent),cfg,Path(original['data_root']),folder)
            _require(report.get('source_id')==parent['source_id'] and isinstance(report.get('attempts'),list),
                     'recovery worker source/attempt contract differs')
            prepared=[]
            for attempt in report['attempts']:
                row=deepcopy(attempt)
                _require(row.get('parent_demo_id')==parent['source_id'] and row.get('teacher_policy')==TEACHER_V2,
                         'recovery attempt parent/teacher policy differs')
                for field in ARTIFACT_FIELDS:
                    if isinstance(row.get(field),str):
                        row[field]=_inside(folder,row[field]).relative_to(output).as_posix()
                prepared.append(row)
            new.extend(prepared)
            if report.get('error'):errors+=1
        except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
            errors+=1
            report={'source_id':parent['source_id'],'attempts':[],
                'error':type(error).__name__+': '+str(error),'gaps':['source_technical_error_no_success_claim']}
        reports.append(report);_write(folder/'source_report.json',report)
        progress={'processed_sources':len(reports),'planned_sources':len(plan['sources']),
            'completion_percent':100*len(reports)/len(plan['sources']),'source_errors':errors,
            'new_qualified_normal':sum(r['qualified'] and r['domain']=='normal' for r in new),
            'new_qualified_10':sum(r['qualified'] and r['domain']=='10' for r in new),
            'reused_trajectories':len(reused),'new_actual_attempts':len(new)}
        _write(output/'recovery_progress.json',{**progress,'source_reports':reports,'plan_identity':plan['identity']})
        print(json.dumps(progress),flush=True)
    context={'teacher_policy':TEACHER_V2,'recovery_plan_identity':plan['identity'],
        'approval_evidence_identity':plan['evidence']['identity'],
        'reused_teacher_policy':TEACHER_V1,'new_execution_attempts':len(new),'reused_trajectories':len(reused)}
    data=export_generated(original['sources'],reused+new,output,output/'export',generation_context=context)
    manifest=read_json(output/'export/sources.json');pools=_pools(manifest['sources'])
    result={'format':'task035-teacher-v2-recovery-report-v1','teacher_policy':TEACHER_V2,
        'plan_identity':plan['identity'],'population':plan['population'],
        'new_execution':_summary(new),'reused':{'trajectories':len(reused),
            'parent_sources':len({r['parent_demo_id'] for r in reused}),
            'counts_by_domain':{d:sum(r['domain']==d for r in reused) for d in DOMAINS},'new_execution':False},
        'merged_data':data,'pools':pools,'training_ready':all(p['windows']>0 for p in pools.values()),
        'processed_sources':len(reports),'completion_percent':100.,'source_errors':errors,
        'source_reports':reports,'model_loaded':False,'training_started':False,
        'status':'completed_with_source_gaps' if errors else 'completed'}
    result['identity']=identity(result);_write(output/'recovery_report.json',result)
    print(json.dumps({**progress,'training_ready':result['training_ready'],'pools':pools}),flush=True)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('plan','recover','generate'))
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if args.command=='plan':
        plan=build_recovery_plan(args.config)
        with Path(args.output).open('x',encoding='utf-8') as stream:
            json.dump(plan,stream,ensure_ascii=False,indent=2,allow_nan=False)
        print(json.dumps(plan['population']),flush=True)
    else:recover(args.config,args.output)


if __name__=='__main__':main()
