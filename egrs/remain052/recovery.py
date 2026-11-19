"""One versioned round: reuse447 unchanged; build stove21, replay three sources."""
from copy import deepcopy
from pathlib import Path

from egrs.remain049 import sources as old, preparation, evaluation
from egrs.remain051 import recovery as previous, scope as previous_scope
from . import scope, policy

PARENT_SHA = '8657805313b12d384d6252011b46fb3008eedda45706d3db60a712339deb1eef'


def parent_report(path, cfg):
    path = Path(path).resolve()
    if old.sha(path/'sources.json') != PARENT_SHA:
        raise ValueError('052 original051 report changed')
    report = old.read(path/'sources.json')
    parent_cfg = {**cfg, 'source_bank': str(path)}
    previous.validate_recovery(report, parent_cfg)
    if (report.get('ready') != 447 or report.get('failed') != 3 or report.get('processed') != 450
            or report.get('complete') is not False or report.get('model_rollouts') != 0
            or {r['episode_id'] for r in report['rows'] if r['status']=='failed'} != scope.FAILED):
        raise ValueError('052 requires exact447 ready /3 RGB-only failures, before policy evaluation')
    return report


def _rows(parent):
    rows = deepcopy(parent['rows'])
    for row in rows:
        row['task052_parent_status'] = row['status']
        if row['status'] == 'ready':
            row['task052_action'] = 'reuse_only'
            continue
        row['task052_original_failure'] = deepcopy({k: row.get(k) for k in ('status','stage','error','origin')})
        for key in ('error','source_plan_sha256','build_control_ledger_sha256','replay_control_ledger_sha256'):
            row.pop(key, None)
        row['status'] = 'pending'
        row['task052_action'] = 'build_and_replay' if row['task_id']=='stove' else 'replay_only'
        if row['task_id']=='stove':
            row.update(origin=None, stage='construction')
        else:
            row['stage'] = 'independent_replay'
            for key in ('candidate_replay','replay_sha256'):
                row['origin'].pop(key, None)
    return rows


def generate(row, root, dispatch, scoped, save):
    if row['episode_id'] not in scope.FAILED:
        raise ValueError('052 must never regenerate a ready source')
    namespace = old._namespace(preparation)
    namespace.update(producers=scope.producers, extension_identity=scope.extension_identity)
    original_options = preparation._options
    namespace['_options'] = lambda task: ({'observation_profile': policy.PROFILE}
                                         if task=='two_pots' else original_options(task))
    return namespace['_generate'](row, root, dispatch, scoped, save)


def validate_recovery(report, cfg):
    if (report.get('schema_version') != old.SCHEMA or report.get('extension') != scope.extension_identity()
            or report.get('config') != cfg or report.get('expected') != old.expected()
            or report.get('recovery',{}).get('format') != scope.REPAIR):
        raise ValueError('052 version/configuration differs')
    binding = report['recovery']
    if binding.get('parent_sources_sha256') != PARENT_SHA:
        raise ValueError('052 parent SHA differs')
    parent = parent_report(binding['parent_bank'], cfg)
    if ([r['episode_id'] for r in report['rows']] != [r['episode_id'] for r in parent['rows']]
            or any(r['status'] not in ('ready','failed','pending') for r in report['rows'])
            or report.get('ready') != sum(r['status']=='ready' for r in report['rows'])
            or report.get('failed') != sum(r['status']=='failed' for r in report['rows'])
            or report.get('complete') is not (report['ready']==450)):
        raise ValueError('052 population/status counters differ')
    population_fields = tuple(old.expected()[0])
    for before, after in zip(parent['rows'], report['rows']):
        if any(after[k] != before[k] for k in population_fields):
            raise ValueError('052 cannot change task/index/mask/instruction population')
        if before['status']=='ready':
            expected = {**before, 'task052_parent_status':'ready', 'task052_action':'reuse_only'}
            if after != expected:
                raise ValueError('052 original447 source bytes/origin/plan must stay unchanged')
        else:
            action = 'build_and_replay' if before['task_id']=='stove' else 'replay_only'
            if (after.get('task052_parent_status') != 'failed' or after.get('task052_action') != action
                    or after.get('task052_original_failure') != {k:before.get(k) for k in ('status','stage','error','origin')}):
                raise ValueError('052 failed-source lineage/action differs')
    return parent


def recover(cfg, parent_bank, output, *, continuation=False):
    dispatch = old.activate(cfg)
    parent_bank, root = Path(parent_bank).resolve(), Path(output).resolve()
    parent = parent_report(parent_bank, cfg)
    evaluation.protect_output(cfg, root, allow_existing=continuation)
    if (root != Path(cfg['source_bank']).resolve() or root==parent_bank
            or root in parent_bank.parents or parent_bank in root.parents):
        raise ValueError('052 requires a new independent bank')
    if root.exists():
        if not continuation:
            raise FileExistsError('052 exists; explicit --continue only, no overwrite or failed retries')
        report = old.read(root/'sources.json')
        validate_recovery(report,cfg)
    else:
        root.mkdir(parents=True)
        report = {'schema_version':old.SCHEMA, 'config':cfg, 'extension':scope.extension_identity(),
            'expected':old.expected(), 'rows':_rows(parent), 'model_rollouts':0, 'dispatch':dispatch,
            'recovery':{'format':scope.REPAIR, 'parent_bank':str(parent_bank), 'parent_sources_sha256':PARENT_SHA,
                'original_ready_reused':447, 'new_source_builds_limit':1,
                'new_independent_source_replays_limit':3, 'RGB_admission_revision':policy.identity(),
                'physical_and_scoring_limits_unchanged':True, 'no_model_rollouts':True}}
    def save():
        report['ready'] = sum(r['status']=='ready' for r in report['rows'])
        report['failed'] = sum(r['status']=='failed' for r in report['rows'])
        report['processed'] = sum(r['status'] in ('ready','failed') for r in report['rows'])
        report['complete'] = report['ready']==450
        report['recovery_processed'] = sum(r['task052_parent_status']=='failed' and r['status'] in ('ready','failed') for r in report['rows'])
        old.write(root/'sources.json', report)
    save()
    scoped = scope.helpers()
    print('[052] START: reuse447 unchanged; build1/replay3; sparse RGB<=2 and <=6pixels at256x256; physics/score unchanged',flush=True)
    for row in report['rows']:
        if row['status'] in ('ready','failed'):
            continue
        try:
            generate(row,root,dispatch,scoped,save)
        except Exception as error:
            row.update(status='failed',error=f'{type(error).__name__}: {error}')
        finally:
            save()
        print(f"[052] recovery={report['recovery_processed']}/3 ({report['recovery_processed']/3*100:.2f}%) "
              f"ready={report['ready']}/450 ({report['ready']/4.5:.2f}%) failed={report['failed']} "
              f"last={row['episode_id']}:{row['status']}",flush=True)
    validate_recovery(report,cfg)
    if old.sha(parent_bank/'sources.json') != PARENT_SHA:
        raise ValueError('052 parent changed during recovery')
    return report
