"""One new recovery round: reuse405; build42, replay45, no model calls.

Keep the original450 population and all failure evidence. Three pot candidates
already passed construction and therefore receive replay only. The other42
source builds retain their original bounded candidate search. No retries inside
this recovery round and no tolerance changes, even for two-level RGB failures.
"""
from copy import deepcopy
from pathlib import Path

from egrs.remain049 import sources as old
from egrs.remain049 import preparation as preparation
from . import scope

PARENT_SHA='2b34a4f34bf9fae699098d34f39a277ee01ea3a2cd65dc987e8087198b6829e9'
REPLAY_ONLY={'two_pots_s011_10','two_pots_s036_10','two_pots_s045_10'}
BUILD_FAILURES={'stove_s021_10','two_pots_s034_10'} | {
    f'mug_microwave_close_s{i:03d}_10' for i in range(10,50)}
FAILED=BUILD_FAILURES|REPLAY_ONLY


def parent_report(path, cfg):
    path=Path(path).resolve();report_path=path/'sources.json'
    if old.sha(report_path)!=PARENT_SHA:raise ValueError('051 original049 report changed')
    parent=old.read(report_path)
    if (parent.get('ready')!=405 or parent.get('failed')!=45 or parent.get('processed')!=450
            or parent.get('complete') is not False or parent.get('expected')!=old.expected()
            or [r['episode_id'] for r in parent['rows']]!=[r['episode_id'] for r in old.expected()]
            or {r['episode_id'] for r in parent['rows'] if r['status']=='failed'}!=FAILED
            or any(r['status'] not in ('ready','failed') for r in parent['rows'])
            or {k:v for k,v in parent['config'].items() if k!='source_bank'}!=
               {k:v for k,v in cfg.items() if k!='source_bank'}):
        raise ValueError('051 requires unchanged original405/45 population and configuration')
    return parent


def resolve(scoped,task,index,origin):return old.resolve(scoped,task,index,origin)


def generate(row,root,dispatch,scoped,save):
    namespace=old._namespace(preparation)
    namespace.update(producers=scope.producers,extension_identity=scope.extension_identity,resolve=resolve)
    return namespace['_generate'](row,root,dispatch,scoped,save)


def _rows(parent):
    rows=deepcopy(parent['rows'])
    for row in rows:
        row['parent_status']=row['status']
        if row['status']=='ready':
            row['recovery_action']='reuse_only'
            continue
        row['original_failure']={k:deepcopy(row.get(k)) for k in ('status','stage','error','origin')}
        for k in ('error','source_plan_sha256','build_control_ledger_sha256','replay_control_ledger_sha256'):
            row.pop(k,None)
        row['status']='pending'
        if row['episode_id'] in REPLAY_ONLY:
            row['recovery_action']='replay_only';row['stage']='independent_replay'
            for key in ('candidate_replay','replay_sha256'):row['origin'].pop(key,None)
        else:
            row['recovery_action']='build_and_replay';row['stage']='construction';row['origin']=None
    return rows


def validate_recovery(report,cfg):
    if (report.get('schema_version')!=old.SCHEMA or report.get('extension')!=scope.extension_identity()
            or report.get('config')!=cfg or report.get('expected')!=old.expected()
            or report.get('recovery',{}).get('format')!=scope.REPAIR):
        raise ValueError('051 recovery source identity differs')
    binding=report['recovery'];parent=parent_report(binding['parent_bank'],cfg)
    if binding.get('parent_sources_sha256')!=PARENT_SHA:
        raise ValueError('051 parent report binding differs')
    previous={r['episode_id']:r for r in parent['rows']}
    if [r['episode_id'] for r in report['rows']]!=[r['episode_id'] for r in old.expected()]:
        raise ValueError('051 population changed')
    if (any(r['status'] not in ('ready','failed','pending') for r in report['rows'])
            or report.get('ready')!=sum(r['status']=='ready' for r in report['rows'])
            or report.get('failed')!=sum(r['status']=='failed' for r in report['rows'])
            or report.get('complete') is not (report['ready']==450)):
        raise ValueError('051 source readiness counters differ')
    for row in report['rows']:
        before=previous[row['episode_id']]
        if any(row[k]!=before[k] for k in old.expected()[0]):
            raise ValueError('051 source index/task/mask changed')
        if before['status']=='ready':
            allowed={**before,'parent_status':'ready','recovery_action':'reuse_only'}
            if row!=allowed:raise ValueError('051 original ready source must remain unchanged')
        else:
            action='replay_only' if row['episode_id'] in REPLAY_ONLY else 'build_and_replay'
            if (row.get('parent_status')!='failed' or row.get('recovery_action')!=action
                    or row.get('original_failure')!={k:deepcopy(before.get(k)) for k in ('status','stage','error','origin')}):
                raise ValueError('051 failed-source recovery selection differs')
    return parent


def recover(cfg,parent_bank,output,*,continuation=False):
    dispatch=old.activate(cfg);scoped=scope.helpers();parent=parent_report(parent_bank,cfg)
    root=Path(output).resolve();parent_bank=Path(parent_bank).resolve()
    from egrs.remain049.evaluation import protect_output
    protect_output(cfg,root,allow_existing=continuation)
    if (root!=Path(cfg['source_bank']).resolve() or root==parent_bank
            or root in parent_bank.parents or parent_bank in root.parents):
        raise ValueError('051 requires a new independent configured bank')
    if root.exists():
        if not continuation:raise FileExistsError('051 recovery exists; use explicit --continue, never overwrite')
        report=old.read(root/'sources.json');validate_recovery(report,cfg)
    else:
        root.mkdir(parents=True)
        report={'schema_version':old.SCHEMA,'config':cfg,'extension':scope.extension_identity(),
                'expected':old.expected(),'rows':_rows(parent),'model_rollouts':0,'dispatch':dispatch,
                'recovery':{'format':scope.REPAIR,'parent_bank':str(parent_bank),
                    'parent_sources_sha256':PARENT_SHA,'original_ready_reused':405,
                    'new_source_builds_limit':42,'new_independent_source_replays_limit':45,
                    'failure_sources_limit':45,'original_candidate_bounds_unchanged':True,
                    'RGB_and_physical_limits_unchanged':True,'no_model_rollouts':True}}
    def save():
        report['ready']=sum(r['status']=='ready' for r in report['rows'])
        report['failed']=sum(r['status']=='failed' for r in report['rows'])
        report['processed']=sum(r['status'] in ('ready','failed') for r in report['rows'])
        report['complete']=report['ready']==450
        report['recovery_processed']=sum(r['parent_status']=='failed' and r['status'] in ('ready','failed') for r in report['rows'])
        old.write(root/'sources.json',report)
    save()
    print('[051] START: reuse405 unchanged; one bounded recovery round for45 sources (42 builds, 3 replay-only); RGB/physics unchanged',flush=True)
    for row in report['rows']:
        if row['status'] in ('ready','failed'):
            # No duplicate full405 qualification pass here. Exact original row
            # binding is checked above; the unchanged eval planner rechecks all
            # source evidence/hashes before creating its VLA worker.
            continue
        try:generate(row,root,dispatch,scoped,save)
        except Exception as error:row.update(status='failed',error=f'{type(error).__name__}: {error}')
        finally:save()
        print(f"[051] recovery={report['recovery_processed']}/45 ({report['recovery_processed']/45*100:.2f}%) "
              f"ready={report['ready']}/450 ({report['ready']/450*100:.2f}%) failed={report['failed']} "
              f"last={row['episode_id']}:{row['status']}",flush=True)
    validate_recovery(report,cfg)
    if old.sha(parent_bank/'sources.json')!=PARENT_SHA:raise ValueError('051 parent report changed during recovery')
    return report
