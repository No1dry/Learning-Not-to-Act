"""Reuse old90 bytes; construct only official indices10..49, without a VLA.

Legacy six retain their pinned matched-all-mask builder (companion masks are
technical construction byproducts, not model episodes). Only10 is replayed and
evaluated. New three retain selected-A methods, RGB v6 and microwave pose v7.
Failed sources are retained, never replaced based on model success.
"""
from copy import deepcopy
from pathlib import Path

from .sources import (SCHEMA, activate, digest, expected, extension_identity, helpers,
                      original_origins, producers, protocol, read, resolve, sha, write)


def _origin(path):
    manifest = Path(path) / 'manifest.candidates.json'
    return {'manifest': str(manifest.resolve()), 'manifest_sha256': sha(manifest),
            'content_hash': read(manifest)['content_hash']}


def _options(task):
    from benchmark.remaining_goals.validation import V6_PROFILE
    from benchmark.remaining_goals.stability import PROFILE
    if task == 'mug_microwave_close':
        return {'construction_method': 'microwave_gravity_support_pose_transplant_v3',
                'observation_profile': V6_PROFILE, 'stability_profile': PROFILE}
    if task == 'bowl_drawer_close':
        return {'construction_method': 'selected_A_only_bounded_settle_component_transplant_v2',
                'observation_profile': V6_PROFILE}
    if task == 'two_pots':
        return {'observation_profile': V6_PROFILE}
    return {}


def _generate(row, root, dispatch, scoped, save):
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from benchmark.remaining_goals.headless.selected_preparation import _run_counted
    task, index = row['task_id'], row['initial_state_index']
    backend, selected_build, selected_replay, replay_backend, coordinate = producers(task, dispatch, scoped)
    destination = root / 'new' / row['episode_id']
    options = _options(task)
    if not row.get('origin'):
        coordinate()
        build_dir = destination / 'candidate'
        row['stage'] = 'construction'
        save()
        if task in REUSE_TASKS:
            function = lambda: backend.build(build_dir, tasks=task, scenes=1, start_index=index, split='test')
        else:
            function = lambda: selected_build(build_dir, task=task, index=index, protocol='nine-mask10', **options)
        result, ledger = _run_counted(function, backend, '_step', destination / 'build.control.json',
                                       {'operation': 'build', 'task_id': task, 'initial_state_index': index,
                                        'task049_extension': extension_identity()})
        # Preserve a failed report even when it contains an accepted other mask.
        accepted = (result.get('complete_groups') == 1 if task in REUSE_TASKS else result.get('complete') is True)
        if not accepted:
            raise ValueError('Construction failed; inspect candidate/construction_report.json')
        row['origin'] = _origin(build_dir)
        row['build_control_ledger_sha256'] = sha(destination / 'build.control.json')
        save()
    if not row['origin'].get('candidate_replay'):
        coordinate()
        row['stage'] = 'independent_replay'
        save()
        replay_dir = destination / 'replay'
        replay_options = {k: v for k, v in options.items() if k != 'construction_method'}
        function = lambda: selected_replay(row['origin']['manifest'], replay_dir, task=task, index=index,
                                           protocol=protocol(task), **replay_options)
        result, ledger = _run_counted(function, replay_backend.ReplayAuditEnv, 'step',
                                       destination / 'replay.control.json',
                                       {'operation': 'replay', 'task_id': task, 'initial_state_index': index,
                                        'task049_extension': extension_identity()})
        replay_path = replay_dir / 'replay_report.json'
        row['origin'].update(candidate_replay=str(replay_path.resolve()), replay_sha256=sha(replay_path))
        row['replay_control_ledger_sha256'] = sha(destination / 'replay.control.json')
        save()
        if result.get('technical_acceptance') is not True:
            raise ValueError('Independent replay failed; inspect replay/replay_report.json')
    source = resolve(scoped, task, index, row['origin'])
    row.update(status='ready', stage='complete', source_plan_sha256=source['source_plan_sha256'])


def prepare(cfg, output, *, continuation=False):
    dispatch = activate(cfg)
    scoped = helpers()
    root = Path(output).resolve()
    from egrs.remain049.evaluation import protect_output
    protect_output(cfg, root, allow_existing=continuation)
    snapshot = {'schema_version': SCHEMA, 'config': cfg, 'extension': extension_identity(),
                'expected': expected(), 'new_indices': [10, 49], 'new_sources_limit': 360,
                'model_rollouts': 0, 'dispatch': dispatch}
    identity = digest(snapshot)
    if root.exists():
        if not continuation:
            raise FileExistsError('049 preparation requires a fresh directory or explicit --continue')
        report = read(root / 'sources.json')
        if report['preparation_identity'] != identity:
            raise ValueError('Cannot continue changed049 source recipe/configuration')
    else:
        root.mkdir(parents=True)
        old = original_origins(cfg)
        rows = []
        for episode in expected():
            task, index = episode['task_id'], episode['initial_state_index']
            rows.append({**episode, 'origin': deepcopy(old.get((task, index))), 'status': 'pending',
                         'stage': 'reuse_validation' if index < 10 else 'construction',
                         'source_kind': 'original_bytes' if index < 10 else 'new_official_index'})
        report = {**snapshot, 'preparation_identity': identity, 'rows': rows, 'complete': False}
    def save():
        report['ready'] = sum(row['status'] == 'ready' for row in report['rows'])
        report['failed'] = sum(row['status'] == 'failed' for row in report['rows'])
        report['processed'] = sum(row['status'] in ('ready', 'failed') for row in report['rows'])
        report['complete'] = report['ready'] == 450
        write(root / 'sources.json', report)
    save()
    for row in report['rows']:
        # No implicit retries or replacement of failed initial states.
        if row['status'] in ('ready', 'failed'):
            if row['status'] == 'ready':
                source = resolve(scoped, row['task_id'], row['initial_state_index'], row['origin'])
                if source['source_plan_sha256'] != row['source_plan_sha256']:
                    raise ValueError('Ready049 source changed during continuation')
            continue
        try:
            if row['initial_state_index'] < 10:
                source = resolve(scoped, row['task_id'], row['initial_state_index'], row['origin'])
                row.update(status='ready', stage='complete', source_plan_sha256=source['source_plan_sha256'])
            else:
                _generate(row, root, dispatch, scoped, save)
        except Exception as error:
            row.update(status='failed', error=f'{type(error).__name__}: {error}')
        finally:
            save()
        print(f"[049][prepare] processed={report['processed']}/450 ({report['processed']/4.5:.2f}%) "
              f"ready={report['ready']}/450 ({report['ready']/4.5:.2f}%) failed={report['failed']} "
              f"last={row['episode_id']}:{row['status']}", flush=True)
    return report
