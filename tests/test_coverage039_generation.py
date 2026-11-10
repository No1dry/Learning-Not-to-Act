"""039 production orchestration contracts using synthetic metadata and fake sessions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from test_trajectory_generation import FakeSession, source, config


def prepared_039(tmp_path):
    from egrs.augmentation.data import load_scope, file_sha256
    from egrs.trajectory_augmentation.cli import RECIPE
    from test_trajectory_data import seed_manifest
    manifest = seed_manifest(tmp_path, count=20)
    manifest['data_root'] = str(tmp_path/'raw')
    template = manifest['sources'][0]
    manifest['sources'] = []
    (tmp_path/'raw').mkdir()
    bindings = {}
    for task in load_scope()['tasks']:
        (tmp_path/'raw'/f"{task['key']}.hdf5").write_bytes(task['key'].encode())
        bindings[task['key']] = {**{k: deepcopy(task[k]) for k in
            ('official_task_name', 'active_goals', 'invariant_predicates')},
            'orientation': 'opengl', 'state_field': 'states',
            'state_alignment_basis': 'synthetic source contract',
            'alignment': {'rule': 'same_state', 'orientation': 'identity',
                          'state_offset': 0, 'observation_offset': 0, 'action_offset': 0}}
        for i in range(20):
            row = deepcopy(template)
            wanted_dev = len(manifest['sources']) >= 136
            for salt in range(1000):
                sid = f"{task['key']}-{i}-{salt}"
                if (int(hashlib.sha256(('7|'+sid).encode()).hexdigest(), 16)%5 == 0) == wanted_dev:
                    break
            row.update(source_id=sid, task_key=task['key'],
                       episode=f'data/demo_{i}', demo_index=i, file=f"{task['key']}.hdf5")
            row['file_sha256'] = file_sha256(tmp_path/'raw'/row['file'])
            row.update({k: deepcopy(task[k]) for k in
                        ('official_task_name', 'active_goals', 'invariant_predicates')})
            manifest['sources'].append(row)
    stats = tmp_path/'stats.json'; stats.write_text('{}', encoding='utf-8')
    digest = file_sha256(stats)
    for row in manifest['sources']:
        for field in ('action_normalization', 'proprio_normalization'):
            row['mapping'][field]['stats_sha256'] = digest
    (tmp_path/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    cfg = {'format': 'task035-generation-config-v1', 'manifest': 'manifest.json',
           'benchmark_root': 'unopened-core', 'stats_path': 'stats.json', 'stats_sha256': digest,
           'unnorm_key': 'libero_10', 'recipe': RECIPE,
           'native_backend': {'kind': 'native', 'historical_root': 'unopened-history',
                              'python': 'venv/bin/python'}, 'bindings': bindings}
    (tmp_path/'035.json').write_text(json.dumps(cfg), encoding='utf-8')
    (tmp_path/'old003').mkdir(); (tmp_path/'old-index').mkdir()
    _write_old_metadata(tmp_path)
    new = {'format': 'task039-coverage-recovery-config-v1', 'generation_config': '035.json',
           'old003_export': 'old003', 'old_retention_index': 'old-index'}
    path = tmp_path/'039.json'; path.write_text(json.dumps(new), encoding='utf-8')
    return path, manifest


def _write_old_metadata(tmp_path):
    """Full public221/75/180 metadata with tiny opaque files, never real HDF/RGB."""
    from egrs.augmentation.data import identity, file_sha256
    from egrs.trajectory_augmentation.cli import build_plan
    from egrs.retention import data as retention
    parents = build_plan(tmp_path/'035.json')['sources']
    old = tmp_path/'old003'; oldroot = tmp_path/'old-artifacts'; oldroot.mkdir()
    for name in ('recording.hdf5', 'audit.json', 'lineage.json', 'qualification.json', 'journal.jsonl'):
        (oldroot/name).write_bytes(b'opaque synthetic archive bytes')
    groups = {split: sorted([p for p in parents if p['task_key'] not in
        ('stove', 'mug_pudding', 'two_pots') and p['split'] == split],
        key=lambda p: (p['demo_index'], p['task_key'])) for split in ('train', 'dev')}
    sources = {}; rows = []
    for domain, split, count in (('10', 'train', 161), ('10', 'dev', 60),
                                  ('normal', 'train', 55), ('normal', 'dev', 20)):
        pool = groups[split]
        for i in range(count):
            parent = pool[i//3] if domain == '10' else pool[i]
            sid = parent['source_id']+f'__{domain}__v{i%3 if domain == "10" else "normal"}__a0'
            row = {k: deepcopy(parent[k]) for k in ('parent_demo_id', 'source_group', 'task_key',
                'split', 'instruction', 'physical_ancestry', 'mapping')}
            row.update(source_id=sid, domain=domain, qualified=True, status='completed',
                qualification={'accepted': True}, parent_file_sha256=parent['file_sha256'],
                file='recording.hdf5', file_sha256=file_sha256(oldroot/'recording.hdf5'),
                episode='data/demo_0', length=1, variant=i%3 if domain == '10' else 'normal', attempt=0,
                audit_path='audit.json', lineage_path='lineage.json', qualification_path='qualification.json',
                journal_path='journal.jsonl', provenance='counterfactual_generated_from_demo' if domain == '10' else 'ordinary_reexecuted')
            sources[sid] = row
            rows.append({**{k: row[k] for k in ('source_id', 'parent_demo_id', 'source_group',
                'task_key', 'split', 'instruction', 'domain', 'variant')}, 'start': 0, 'stop': 1,
                'action_mask': [True]+[False]*7})
    content = ''.join(json.dumps(r)+'\n' for r in rows)
    (old/'windows.jsonl').write_text(content, encoding='utf-8')
    exported = {'format': 'task035-generated-trajectories-v1', 'data_root': str(oldroot.resolve()),
                'sources': sources, 'parents': parents}
    exported['identity'] = identity(exported)
    report = {'data_kind': exported['format'], 'sources_identity': exported['identity'],
        'windows_sha256': file_sha256(old/'windows.jsonl'),
        'counts_by_domain': {'10': {'trajectories': 221}, 'normal': {'trajectories': 75}}}
    report['identity'] = identity(report)
    for name, value in (('sources.json', exported), ('report.json', report)):
        (old/name).write_text(json.dumps(value), encoding='utf-8')
    kept = {}; kept_rows = []
    for row in list(sources.values())+parents:
        raw = row in parents; pool = 'raw' if raw else 'ten' if row['domain'] == '10' else 'fresh'
        sid = pool+'|'+row['source_id']
        record = {k: deepcopy(row[k]) for k in ('file', 'file_sha256', 'episode', 'parent_demo_id',
            'source_group', 'task_key', 'split', 'instruction', 'physical_ancestry')}
        record.update(source_id=sid, pool=pool, root_key='raw' if raw else 'generated',
                      observation_count=1 if raw else 2, variant=row.get('variant', 'recorded'))
        if pool == 'ten': record['original_source'] = deepcopy(row)
        kept[sid] = record
        for index in range(1 if pool == 'ten' else record['observation_count']):
            kept_rows.append({**{k: record[k] for k in ('source_id', 'pool', 'task_key', 'parent_demo_id',
                'source_group', 'variant', 'split', 'instruction')}, 'observation_index': index,
                'observation_count': record['observation_count'], 'prefix': index == 0})
    directory = tmp_path/'old-index'
    (directory/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in kept_rows), encoding='utf-8')
    fields = ('source_id', 'parent_demo_id', 'source_group', 'split', 'task_key', 'file',
              'file_sha256', 'episode', 'instruction', 'physical_ancestry')
    index = {'format': retention.DATA_KIND, 'data_roots': {'raw': str((tmp_path/'raw').resolve()),
        'generated': str(oldroot.resolve())}, 'parents': {p['source_id']: {k: p[k] for k in fields} for p in parents},
        'sources': kept, 'inputs': {str((old/name).resolve()): file_sha256(old/name)
            for name in ('sources.json', 'report.json', 'windows.jsonl')},
        'statistics': {'key': retention.STATS_KEY, 'sha256': retention.STATS_SHA}}
    index['inputs'][str((tmp_path/'manifest.json').resolve())] = file_sha256(tmp_path/'manifest.json')
    index['identity'] = identity(index)
    report = {'data_kind': retention.DATA_KIND, 'sources_identity': index['identity'],
        'rows_sha256': file_sha256(directory/'rows.jsonl'), 'pool_counts': retention.EXPECTED_COUNTS,
        'rows': len(kept_rows)}
    report['identity'] = identity(report)
    for name, value in (('sources.json', index), ('report.json', report)):
        (directory/name).write_text(json.dumps(value), encoding='utf-8')


def cfg039():
    from egrs.trajectory_augmentation.native import TEACHER_V2
    cfg = config(); cfg['teacher_policy'] = TEACHER_V2
    return cfg


def test_plan_selects_exact_first_twenty_of_three_tasks_without_opening_hdf(tmp_path, monkeypatch):
    from egrs.coverage039.plan import build_plan
    path, manifest = prepared_039(tmp_path)
    monkeypatch.setattr(h5py, 'File', lambda *a, **k: pytest.fail('plan opened an HDF'))
    plan = build_plan(path)
    assert len(plan['parents']) == 180
    assert len(plan['sources']) == 60
    assert {s['task_key'] for s in plan['sources']} == {'stove', 'mug_pudding', 'two_pots'}
    assert plan['population']['max_normal_replays'] == 60
    assert plan['population']['max_10_attempts'] == 360
    assert plan['population']['max_robot_starts'] == 180
    assert all(s['file'] == f"{s['task_key']}.hdf5" for s in plan['parents'])
    assert all(s['parent_demo_id'] == s['source_id'] for s in plan['sources'])
    for task in ('stove', 'mug_pudding', 'two_pots'):
        assert sorted(s['demo_index'] for s in plan['sources'] if s['task_key'] == task) == list(range(20))
    assert not plan['simulation_created'] and not plan['model_loaded']


@pytest.mark.parametrize('broken', ['old_windows', 'retention_rows', 'missing_hdf', 'generated_root'])
def test_plan_rejects_unusable_old_references_before_new_attempts(tmp_path, broken):
    from egrs.coverage039.plan import build_plan
    from egrs.augmentation.data import identity
    path, _ = prepared_039(tmp_path)
    if broken == 'old_windows':
        with (tmp_path/'old003/windows.jsonl').open('a') as stream: stream.write('{}\n')
    elif broken == 'retention_rows':
        with (tmp_path/'old-index/rows.jsonl').open('a') as stream: stream.write('{}\n')
    elif broken == 'missing_hdf':
        (tmp_path/'old-artifacts/recording.hdf5').unlink()
    else:
        directory = tmp_path/'old-index'
        manifest = json.loads((directory/'sources.json').read_text())
        manifest['data_roots']['generated'] = str(tmp_path/'different-root')
        manifest['identity'] = identity(manifest)
        (directory/'sources.json').write_text(json.dumps(manifest))
        report = json.loads((directory/'report.json').read_text())
        report['sources_identity'] = manifest['identity']; report['identity'] = identity(report)
        (directory/'report.json').write_text(json.dumps(report))
    with pytest.raises((ValueError, FileNotFoundError)):
        build_plan(path)


def test_attempt_ledger_consumes_before_initialization_and_never_refunds(tmp_path):
    from egrs.coverage039.generation import AttemptLedger
    path = tmp_path/'ledger.json'; ledger = AttemptLedger(path)
    for i in range(60):
        ledger.reserve(f'parent-{i}', 'normal', 'normal', 0)
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert saved['normal_attempts'] == 60
    with pytest.raises(ValueError, match='budget'):
        ledger.reserve('extra', 'normal', 'normal', 0)
    with pytest.raises(ValueError, match='already'):
        AttemptLedger(path).reserve('parent-0', 'normal', 'normal', 0)
    for i in range(60):
        for v in range(3):
            for n in range(2): ledger.reserve(f'parent-{i}', '10', v, n)
    assert json.loads(path.read_text(encoding='utf-8'))['ten_attempts'] == 360
    with pytest.raises(ValueError, match='budget'):
        ledger.reserve('extra', '10', 0, 0)


def test_interruption_keeps_reserved_slot_and_requested_action(tmp_path):
    from egrs.coverage039.generation import generate_session
    session = FakeSession()
    def interrupted(action): raise KeyboardInterrupt('synthetic power loss')
    session.step = interrupted
    with pytest.raises(KeyboardInterrupt):
        generate_session(session, source(), cfg039(), tmp_path)
    ledger = json.loads((tmp_path/'attempt_ledger.json').read_text(encoding='utf-8'))
    assert ledger['normal_attempts'] == 1
    meta = json.loads((tmp_path/'normal_vnormal_a0/metadata.json').read_text(encoding='utf-8'))
    assert meta['qualified'] is False
    assert meta['generator_algorithm'] == 'physical_release_clearance_v3'
    journal = [json.loads(row) for row in (tmp_path/'normal_vnormal_a0/journal.jsonl').read_text().splitlines()]
    assert journal[-1]['event'] == 'action_requested'
    assert journal[0]['initialization_transform']['kind'] == 'identity'


class ClosureSession(FakeSession):
    def capture(self):
        f = super().capture()
        # Only real additional executed controls release this synthetic object.
        f['facts']['released'] = len(self.steps) >= 5
        f['hand_open'] = not f['facts']['official_success'] or len(self.steps) >= 5
        return f

    def qualify(self, frames, domain):
        streak = 0
        for frame in frames:
            streak = streak + 1 if frame['facts']['official_success'] and frame['facts']['released'] is True else 0
        ok = streak >= 5 and (domain != '10' or frames[0]['facts']['goals'] == [True, False])
        return {'qualified': ok, 'failure_reason': None if ok else 'release_unconfirmed',
                'core_release_confirmation_streak': streak,
                'core_analysis': {'confirmed_events': []}}


def test_closure_is_supervised_and_ten_replays_normal_closure_targets(tmp_path):
    from egrs.coverage039.generation import generate_session
    result = generate_session(ClosureSession(), source(), cfg039(), tmp_path)
    assert len(result['attempts']) == 4
    assert all(a['qualified'] for a in result['attempts'])
    normal = result['attempts'][0]
    assert normal['length'] == 9
    assert normal['teacher_policy'] == 'table-drop-unknown-diagnostic-v2'
    assert normal['initialization_transform']['kind'] == 'identity'
    for a in result['attempts']:
        with h5py.File(tmp_path/a['file']) as h:
            g = h['data/demo_0']
            assert len(g['actions']) == a['length']
            assert len(g['states']) == a['length'] + 1
            assert len(g['obs/agentview_rgb']) == a['length'] + 1
            assert len(g['controller_goal_pos']) == a['length']
        audit = json.loads((tmp_path/a['audit_path']).read_text())
        assert not audit['confirmation_frames']
        assert all(not s['audit_only'] for s in audit['steps'])
        if a['domain'] == '10':
            # Handoff index1, all eight subsequent normal targets include six new closure targets.
            assert sum(s['phase'] == 'continuation' for s in audit['steps']) == 8
            assert audit['frames'][0]['facts']['goals'] == [True, False]


def test_failed_bridges_consume_six_slots_and_keep_complete_prefix_files(tmp_path):
    from egrs.coverage039.generation import generate_session
    session = ClosureSession(); restore = session.restore
    def fail_after_normal(state):
        restore(state)
        if len(session.restores) > 1: session.failure = True
    session.restore = fail_after_normal
    result = generate_session(session, source(), cfg039(), tmp_path)
    assert len(result['attempts']) == 7
    assert sum(a['qualified'] for a in result['attempts']) == 1
    assert json.loads((tmp_path/'attempt_ledger.json').read_text())['ten_attempts'] == 6
    for a in result['attempts'][1:]:
        assert a['qualified'] is False and a['file']
        with h5py.File(tmp_path/a['file']) as h:
            assert len(h['data/demo_0/states']) == len(h['data/demo_0/actions']) + 1


def test_generate_consumes_all_sixty_normal_initialization_failures_and_exports_full_parents(tmp_path):
    from egrs.coverage039.generation import generate
    path, manifest = prepared_039(tmp_path)
    calls = []
    def failed_native(source, config, data_root, directory):
        spent = json.loads(Path(config['_budget_ledger']).read_text())
        assert spent['normal_attempts'] == len(calls) + 1
        assert (directory/'normal_vnormal_a0/metadata.json').exists()
        calls.append(source['source_id'])
        raise ValueError('synthetic native initializer failure')
    result = generate(path, tmp_path/'new039', source_generator=failed_native)
    assert len(calls) == 60
    assert result['spent']['normal_attempts'] == 60
    assert result['spent']['ten_attempts'] == 0
    assert result['data']['attempts'] == 60 and result['data']['failed_attempts'] == 60
    assert result['actual_qualified_10'] == result['actual_new_train_10'] == 0
    exported = json.loads((Path(result['export'])/'sources.json').read_text())
    assert len(exported['parents']) == 180
    assert exported['sources'] == {}
    assert all(s['file'] == f"{s['task_key']}.hdf5" for s in exported['parents'])
    assert {s['file_sha256'] for s in exported['parents']} == {s['file_sha256'] for s in manifest['sources']}


def test_generate_rejects_output_overlapping_any_old_or_raw_root(tmp_path):
    from egrs.coverage039.generation import generate
    path, manifest = prepared_039(tmp_path)
    for root in ('raw', 'old003', 'old-index'):
        with pytest.raises(ValueError, match='overlap'):
            generate(path, tmp_path/root/'new039', source_generator=lambda *a: pytest.fail('native invoked'))


def test_new_worker_preserves_interpreter_entry_and_counts_launch_failure(tmp_path, monkeypatch):
    from egrs.coverage039.generation import generate_source
    entry = tmp_path/'venv/bin/python'; entry.parent.mkdir(parents=True); entry.touch()
    resolve = Path.resolve
    def simulated_symlink(candidate, *args, **kwargs):
        return Path('C:/base/python.exe') if candidate == entry else resolve(candidate, *args, **kwargs)
    monkeypatch.setattr(Path, 'resolve', simulated_symlink)
    commands = []
    def unavailable(command, **kwargs):
        commands.append(command)
        request = json.loads(Path(command[-1]).read_text())
        ledger = json.loads(Path(request['config']['_budget_ledger']).read_text())
        assert ledger['normal_attempts'] == 1
        raise FileNotFoundError('synthetic worker unavailable')
    monkeypatch.setattr('egrs.coverage039.generation.subprocess.Popen', unavailable)
    cfg = cfg039(); cfg['native_backend'] = {'python': str(entry)}
    result = generate_source(source(), cfg, tmp_path, tmp_path/'new-worker')
    assert commands[0][0] == str(entry)
    assert commands[0][1:4] == ['-m', 'egrs.coverage039.native', '--request']
    assert len(result['attempts']) == 1
    assert result['attempts'][0]['teacher_policy'] == 'table-drop-unknown-diagnostic-v2'
    assert 'FileNotFoundError' in result['attempts'][0]['failure_reason']


def test_worker_initialization_failure_uses_reserved_normal_once(tmp_path, monkeypatch):
    from egrs.coverage039.generation import AttemptLedger
    from egrs.coverage039.native import worker
    path = tmp_path/'attempt_ledger.json'
    AttemptLedger(path).reserve('parent', 'normal', 'normal', 0)
    def unavailable(*args): raise ValueError('synthetic missing native dependency')
    monkeypatch.setattr('egrs.coverage039.native.NativeSession', unavailable)
    cfg = cfg039(); cfg.update(_normal_pre_reserved=True, _budget_ledger=str(path))
    request = {'source': source(), 'config': cfg, 'data_root': str(tmp_path), 'output_dir': str(tmp_path)}
    (tmp_path/'request.json').write_text(json.dumps(request))
    result = worker(tmp_path/'request.json')
    assert json.loads(path.read_text())['normal_attempts'] == 1
    assert len(result['attempts']) == 1 and not result['attempts'][0]['qualified']
    assert 'missing native dependency' in result['attempts'][0]['failure_reason']


def test_process_context_hashes_new_hdf_once_across_persist_and_export(tmp_path):
    from egrs.coverage039.generation import generate_session
    from egrs.coverage039.io import HashContext
    from egrs.trajectory_augmentation.data import export_generated
    from test_trajectory_data import mapping as full_mapping
    p = source(); p.update(source_group='parent', physical_ancestry='unknown', mapping=full_mapping())
    session = ClosureSession(); capture = session.capture
    def full_observation():
        frame = capture()
        frame['observation']['obs/ee_states'] = np.r_[frame['position'], np.zeros(3)]
        frame['observation']['obs/gripper_states'] = np.array([.04, -.04])
        return frame
    session.capture = full_observation
    context = HashContext()
    result = generate_session(session, p, cfg039(), tmp_path, context=context)
    assert context.files_read == 4
    bytes_before = context.bytes_read
    exported = export_generated([p], result['attempts'], tmp_path, tmp_path/'export', context=context)
    assert exported['qualified_trajectories'] == 4
    assert context.files_read == 4 and context.bytes_read == bytes_before
    for row in result['attempts']:
        meta = json.loads((tmp_path/row['lineage_path']).read_text())
        assert meta['generator_algorithm'] == 'physical_release_clearance_v3'
        assert meta['recipe']['initialization_transform'] == row['initialization_transform']
        assert row['generation_context']['initialization_transform'] == row['initialization_transform']


def test_native_worker_heartbeat_remains_visible_during_wait(tmp_path, monkeypatch):
    from egrs.coverage039 import generation
    from egrs.coverage039.io import Progress
    events = []
    monkeypatch.setattr(generation, 'Progress',
                        lambda stage, **kwargs: Progress(stage, callback=events.append, interval=0))
    class FakeWorker:
        count = 0
        def wait(self, timeout=None):
            self.count += 1
            if self.count == 1:
                (tmp_path/'worker/heartbeat.json').write_text(json.dumps(
                    {'source': 'parent', 'attempt': '10/v1/a0', 'phase': 'bridge', 'controls': 27}))
                raise generation.subprocess.TimeoutExpired('fake', timeout)
            (tmp_path/'worker/result.json').write_text(json.dumps(
                {'source_id': 'parent', 'attempts': [], 'error': None}))
            return 0
    monkeypatch.setattr(generation.subprocess, 'Popen', lambda *a, **kw: FakeWorker())
    cfg = cfg039(); cfg['native_backend'] = {'python': 'unopened-python'}
    generation.generate_source(source(), cfg, tmp_path, tmp_path/'worker')
    assert any(e.get('attempt') == '10/v1/a0' and e.get('phase') == 'bridge' and e.get('controls') == 27
               for e in events)


def test_worker_loss_after_ten_reservation_preserves_both_attempt_denominators(tmp_path):
    from egrs.coverage039.generation import AttemptLedger, initialization_failure, _recover_source
    from egrs.trajectory_augmentation.data import export_generated
    ledger = AttemptLedger(tmp_path/'attempt_ledger.json')
    p = source(); p.update(source_group='parent', physical_ancestry='unknown')
    ledger.reserve('parent', 'normal', 'normal', 0)
    initialization_failure(p, tmp_path, 'normal_prefix_already_rejected')
    # Power loss occurs after durable spend but before the first ten metadata write.
    ledger.reserve('parent', '10', 2, 1)
    result = _recover_source(p, tmp_path, 'synthetic worker power loss')
    assert len(result['attempts']) == 2
    ten = next(row for row in result['attempts'] if row['domain'] == '10')
    assert ten['variant'] == 2 and ten['attempt'] == 1
    assert ten['qualified'] is False and ten['file'] is None
    assert 'power loss' in ten['failure_reason']
    assert (tmp_path/'10_v2_a1/metadata.json').is_file()
    report = export_generated([p], result['attempts'], tmp_path, tmp_path/'export')
    assert report['attempts'] == report['failed_attempts'] == 2
    assert report['task_split_domain']['basket|train|10']['attempts'] == 1
    assert ledger.read()['ten_attempts'] == 1


@pytest.mark.parametrize('kind', ['duplicate', 'foreign'])
def test_recovery_rejects_duplicate_or_foreign_metadata_slots(tmp_path, kind):
    from egrs.coverage039.generation import AttemptLedger, initialization_failure, _recover_source
    ledger = AttemptLedger(tmp_path/'attempt_ledger.json'); ledger.reserve('parent', 'normal', 'normal', 0)
    row = initialization_failure(source(), tmp_path, 'known failed normal')
    extra = tmp_path/'extra'; extra.mkdir()
    if kind == 'foreign': row['parent_demo_id'] = 'unplanned-other-parent'
    (extra/'metadata.json').write_text(json.dumps(row))
    with pytest.raises(ValueError, match='duplicate|foreign|unreserved'):
        _recover_source(source(), tmp_path, 'worker interrupted')

