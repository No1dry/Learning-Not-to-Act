"""Task017 synthetic fixtures only; never research annotations or real model runs."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

from tests.test_data_training import example


def synthetic_file(root, *, instruction='put bowl in drawer', lengths=(25, 25), episodes=(0, 1, 10)):
    catalog = json.loads(Path('data/catalog.json').read_text())
    entry = catalog['files'][0]
    path = root / entry['suite'] / entry['file']
    path.parent.mkdir(parents=True)
    with h5py.File(path, 'w') as f:
        data = f.create_group('data')
        if instruction is not None:
            data.attrs['problem_info'] = json.dumps({'language_instruction': instruction}).encode()
        data.attrs['macros_image_convention'] = 'opengl'
        for i in episodes:
            obs = data.create_group(f'demo_{i}/obs')
            for key, n in zip(('agentview_rgb', 'eye_in_hand_rgb'), lengths):
                obs.create_dataset(key, data=np.zeros((n, 4, 5, 3), dtype=np.uint8))
    return path


def test_inventory_fixed_numeric_selection_exact_instruction_and_gaps(tmp_path):
    from egrs.offline.inventory import inventory
    synthetic_file(tmp_path, instruction='  put bowl in drawer  ')
    result = inventory(tmp_path)
    assert len(result['sources']) == 2
    assert len(result['gaps']) == 198
    assert {s['episode'] for s in result['sources']} == {'demo_0', 'demo_1'}
    assert {s['instruction'] for s in result['sources']} == {'  put bowl in drawer  '}
    assert all(s['T'] == 25 and s['orientation'] == 'opengl' for s in result['sources'])
    assert len(result['source_splits']) == 200


@pytest.mark.parametrize('instruction,lengths,reason', [(None, (4, 4), 'instruction'), ('put bowl in drawer', (4, 3), 'length'), ('put bowl in drawer', (0, 0), 'nonempty')])
def test_inventory_rejects_missing_instruction_mismatch_and_empty(tmp_path, instruction, lengths, reason):
    from egrs.offline.inventory import inventory
    synthetic_file(tmp_path, instruction=instruction, lengths=lengths)
    result = inventory(tmp_path)
    assert not result['sources']
    assert any(reason in x['reason'] for x in result['gaps'])


def test_missing_instruction_only_uses_explicit_mapping(tmp_path):
    from egrs.offline.inventory import inventory
    path = synthetic_file(tmp_path, instruction=None)
    rel = path.relative_to(tmp_path).as_posix()
    result = inventory(tmp_path, instruction_map={rel: {'instruction': 'put bowl in drawer', 'reviewer': 'SYNTHETIC', 'basis': 'fixture'}})
    assert len(result['sources']) == 2
    assert result['sources'][0]['instruction_origin'] == 'explicit_human_mapping'


def test_sampling_clamped_deduplicated_and_prepare_requires_confirmation(tmp_path):
    from egrs.offline.inventory import inventory, instruction_id
    from egrs.offline.windows import window_frames, prepare
    assert window_frames(1) == [[0]]
    assert window_frames(3) == [[0], [0, 1], [0, 2]]
    assert window_frames(25) == [[0], [0, 4], [0, 1, 9], [0, 6, 14], [3, 11, 19], [8, 16, 24]]
    synthetic_file(tmp_path)
    inv = inventory(tmp_path)
    reg = example()['payload']['context']['registry']
    with pytest.raises(ValueError, match='confirmed'):
        prepare(inv, {'registries': {}}, tmp_path / 'bad')
    from egrs.offline.common import seal
    confirmed = {'format': 'egrs.registries.confirmed.v1', 'inventory_id': inv['identity'], 'registries': {instruction_id(reg['instruction']): {'registry': reg, 'confirmed': True, 'reviewer': 'SYNTHETIC'}}}
    confirmed = seal(confirmed)
    result = prepare(inv, confirmed, tmp_path / 'prepared')
    assert len(result['windows']) == 12
    for window in result['windows']:
        for i, s in enumerate(window['samples'], 1):
            assert s['payload']['context']['query_id'] == i
            assert s['payload']['context']['commands'] == []
            assert s['payload']['context']['history'] == []
            assert [x['query_id'] for x in s['payload']['sensor']] == list(range(1, i + 1))
            assert s['answer'] is None


def test_fixed_source_split_survives_partial_review_and_rejects_alias_leak(tmp_path):
    from egrs.data import build_dataset, grouped_split
    rows = [dict(example(), sample_id=f's{i}', source_id=f'src{i}', group_ids=['same'] if i < 2 else []) for i in range(8)]
    splits = grouped_split(rows)
    source_splits = {r['source_id']: splits[r['sample_id']] for r in rows}
    dev = [r for r in rows if source_splits[r['source_id']] == 'dev']
    attest = dict.fromkeys(('six_composites_excluded', 'semantic_equivalents_excluded', 'eval_sources_excluded'), True)
    report = build_dataset(dev, tmp_path / 'subset', attestation=attest, fixed_source_splits=source_splits)
    assert report['splits']['dev'] == len(dev) and report['splits']['train'] == 0
    source_splits['src0'], source_splits['src1'] = 'train', 'dev'
    with pytest.raises(ValueError, match='alias'):
        build_dataset(rows, tmp_path / 'leak', attestation=attest, fixed_source_splits=source_splits)


def test_plan_is_static_and_help_available():
    code = "import sys; from egrs.offline.cli import main; main(['plan']); assert not any(x in sys.modules for x in ['h5py','torch','transformers','benchmark'])"
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['actual_verified_sources'] == 0
    assert plan['budget_only']['queries_max'] == 3600


class FakeBackend:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []
        self.closed = 0

    def generate(self, messages, images, audit):
        self.messages.append(copy.deepcopy(messages))
        value = next(self.responses)
        if isinstance(value, BaseException):
            raise value
        return json.dumps(value) if isinstance(value, dict) else value

    def close(self):
        self.closed += 1


def prepared_fixture(tmp_path):
    from egrs.offline.inventory import inventory, instruction_id
    from egrs.offline.windows import prepare
    synthetic_file(tmp_path)
    inv = inventory(tmp_path)
    reg = example()['payload']['context']['registry']
    from egrs.offline.common import seal
    confirmed = {'format': 'egrs.registries.confirmed.v1', 'inventory_id': inv['identity'], 'registries': {instruction_id(reg['instruction']): {'registry': reg, 'confirmed': True, 'reviewer': 'SYNTHETIC'}}}
    return inv, prepare(inv, seal(confirmed), tmp_path / 'prepared')


def unknown(q):
    return {'query_id': q, 'goals': [{'goal_ref': 'g0', 'entity_ref': None, 'association': 'UNKNOWN', 'role': 'UNKNOWN', 'relation': 'UNKNOWN', 'release': 'UNKNOWN', 'interaction': 'UNKNOWN', 'evidence': []}]}


def test_candidates_one_load_chronological_memory_raw_failure_and_skip(tmp_path):
    from egrs.offline.teacher import OfflineTeacher
    from egrs.offline.candidates import candidates
    from egrs.offline.common import seal
    _, prepared = prepared_fixture(tmp_path)
    prepared['windows'] = [prepared['windows'][2], prepared['windows'][3]]
    prepared = seal(prepared)
    backend = FakeBackend([unknown(1), 'malformed raw', unknown(1), unknown(2), unknown(3)])
    loads = []
    def loader(config):
        loads.append(config)
        return backend
    result = candidates(prepared, tmp_path / 'candidates', teacher_factory=lambda: OfflineTeacher(loader=loader))
    assert len(loads) == 1 and backend.closed == 1
    assert result['counts'] == {'attempted': 5, 'succeeded': 4, 'failed': 1, 'unattempted': 1}
    assert result['attempts'][1]['raw'] == 'malformed raw'
    assert result['samples'][1]['answer'] is None and result['samples'][2]['answer'] is None
    assert 'preceding' in result['attempts'][2]['error']
    assert result['samples'][1]['payload']['context']['history'][0]['query_id'] == 1
    assert result['samples'][1]['history_provenance'] == {'1': 'model_prediction'}
    assert result['samples'][3]['payload']['context']['history'] == []
    assert all(s['provenance'] == {'': 'weak'} for s in result['samples'] if s['answer'])
    assert 'demo_' not in json.dumps(backend.messages)
    assert 'frame' not in json.dumps(backend.messages)


def test_teacher_failure_no_retry_and_student_pin_is_separate(tmp_path):
    from egrs.offline.teacher import OfflineTeacher, resolve_config
    from egrs.selector.model import resolve_config as student
    backend = FakeBackend([RuntimeError('synthetic OOM'), 'not JSON'])
    teacher = OfflineTeacher(loader=lambda c: backend)
    first = teacher.registry('put bowl in drawer')
    second = teacher.registry('put bowl in drawer')
    assert first['answer'] is None and 'synthetic OOM' in first['error']
    assert second['raw'] == 'not JSON' and second['answer'] is None
    assert teacher.calls == 2
    with pytest.raises(ValueError, match='pinned'):
        student({'model_id': resolve_config()['model_id']})
    with pytest.raises(ValueError):
        resolve_config({'revision': 'other'})
    with pytest.raises(ValueError):
        resolve_config({'adapter': 'forbidden'})


def test_registry_candidates_deduplicate_exact_instruction_without_confirmation(tmp_path):
    from egrs.offline.teacher import OfflineTeacher
    from egrs.offline.candidates import registry_candidates
    from egrs.offline.inventory import inventory
    synthetic_file(tmp_path)
    inv = inventory(tmp_path)
    backend = FakeBackend([example()['payload']['context']['registry']])
    result = registry_candidates(inv, tmp_path / 'registries', teacher_factory=lambda: OfflineTeacher(loader=lambda c: backend))
    assert len(result['registries']) == 1
    row = next(iter(result['registries'].values()))
    assert row['confirmed'] is False and row['provenance'] == 'weak'
    assert result['calls'] == 1 and backend.closed == 1


def test_prepare_rejects_mutated_confirmed_registry_envelope(tmp_path):
    from egrs.offline.inventory import inventory, instruction_id
    from egrs.offline.windows import prepare
    from egrs.offline.common import seal
    synthetic_file(tmp_path)
    inv = inventory(tmp_path)
    reg = example()['payload']['context']['registry']
    registries = seal({'format': 'egrs.registries.confirmed.v1', 'inventory_id': inv['identity'], 'registries': {
        instruction_id(reg['instruction']): {'registry': reg, 'confirmed': True, 'reviewer': 'SYNTHETIC'}}})
    registries['registries'][instruction_id(reg['instruction'])]['registry']['goals'][0]['target'] = 'drawer'
    with pytest.raises(ValueError, match='identity'):
        prepare(inv, registries, tmp_path / 'prepared')


def test_production_encoder_budget_fails_without_model_forward_or_payload_trim():
    from egrs.offline.teacher import _Backend, resolve_config
    from tests.test_data_training import FakeProcessor
    backend = _Backend.__new__(_Backend)
    backend.config = resolve_config({'device': 'cpu'})
    backend.processor = FakeProcessor()
    class NeverModel:
        def generate(self, **kwargs):
            pytest.fail('over-budget input must not reach model forward')
    backend.model = NeverModel()
    audit = {'generation_attempted': False}
    with pytest.raises(ValueError, match='length'):
        backend.generate([{'role': 'user', 'content': 'x' * 3500}], [], audit)
    assert audit['generation_attempted'] is False


def test_corrupt_file_and_non_rgb_camera_are_gaps(tmp_path):
    from egrs.offline.inventory import inventory
    path = synthetic_file(tmp_path)
    with h5py.File(path, 'a') as f:
        del f['data/demo_0/obs/agentview_rgb']
        f['data/demo_0/obs'].create_dataset('agentview_rgb', data=np.zeros((25, 4, 5, 4), dtype=np.uint8))
    result = inventory(tmp_path)
    assert len(result['sources']) == 1 and result['sources'][0]['episode'] == 'demo_1'
    assert any('RGB' in g['reason'] for g in result['gaps'])
    path.write_bytes(b'SYNTHETIC CORRUPT FILE')
    assert len(inventory(tmp_path)['gaps']) == 200


def test_complete_synthetic_pipeline_registry_to_review_build(tmp_path):
    from egrs.offline.inventory import inventory
    from egrs.offline.candidates import registry_candidates, candidates
    from egrs.offline.teacher import OfflineTeacher
    from egrs.offline.windows import prepare
    from egrs.offline.review import new_registry_session, import_registry_review, new_session, confirmation, build_reviewed
    synthetic_file(tmp_path, lengths=(1, 1), episodes=(0, 1))
    inv = inventory(tmp_path)
    reg = example()['payload']['context']['registry']
    rc = registry_candidates(inv, tmp_path / 'rc', teacher_factory=lambda: OfflineTeacher(loader=lambda c: FakeBackend([reg])))
    rs = new_registry_session(rc)
    key = next(iter(rs['registries']))
    rs['confirmations'][key] = {'value': reg, 'reviewer': 'SYNTHETIC TEST ONLY', 'elapsed_ms': 5}
    confirmed = import_registry_review(rc, rs)
    windows = prepare(inv, confirmed, tmp_path / 'windows')
    cs = candidates(windows, tmp_path / 'cs', teacher_factory=lambda: OfflineTeacher(loader=lambda c: FakeBackend([unknown(1), unknown(1)])))
    session = new_session(cs)
    row = session['annotations']['samples'][0]
    session['confirmations'][row['sample_id']] = {'/goals/0/relation': confirmation(row['answer'], '/goals/0/relation', 'SYNTHETIC TEST ONLY', 3)}
    attestation = dict.fromkeys(('six_composites_excluded', 'semantic_equivalents_excluded', 'eval_sources_excluded'), True)
    attestation['basis'] = 'SYNTHETIC ONLY'
    report = build_reviewed(cs, session, tmp_path / 'build', attestation=attestation)
    assert report['planned_sources'] == 200 and report['unreviewed_queries'] == 1
    assert report['supervision_coverage']['sources'] == 1
    assert len(report['source_gaps']) == 198 and report['ready'] is False


def test_interrupted_candidate_run_keeps_append_only_partial_records(tmp_path):
    from egrs.offline.candidates import candidates
    from egrs.offline.teacher import OfflineTeacher
    _, windows = prepared_fixture(tmp_path)
    backend = FakeBackend([unknown(1), KeyboardInterrupt('synthetic interruption')])
    with pytest.raises(KeyboardInterrupt):
        candidates(windows, tmp_path / 'interrupted', teacher_factory=lambda: OfflineTeacher(loader=lambda c: backend))
    journal = tmp_path / 'interrupted/candidates.partial.jsonl'
    assert journal.is_file()
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]['sample']['answer']['query_id'] == 1
    assert backend.closed == 1
