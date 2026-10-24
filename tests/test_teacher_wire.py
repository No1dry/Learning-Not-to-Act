"""Task018 synthetic wire fixtures only; no real research raw, images or model."""
import copy
import json
import pytest

from tests.test_data_training import example, FakeProcessor
from tests.test_offline_pipeline import FakeBackend, unknown, prepared_fixture


@pytest.mark.parametrize('wrap,strategy', [
    ('{}', 'bare_json'), (' \n```json\n{}\n```\t\n', 'fenced_json'),
    ('```\r\n{}\r\n```', 'fenced_untyped')])
def test_exact_outer_wrapper_preserves_raw_and_answer(wrap, strategy):
    from egrs.offline.parsing import parse_teacher_output
    row = example()
    raw = wrap.format(json.dumps(row['answer']))
    before = raw
    result = parse_teacher_output(raw, payload=row['payload'])
    assert result['answer'] == row['answer'] and raw == before
    assert result['strategy'] == strategy
    assert result['stages'] == dict.fromkeys(('wrapper', 'json', 'schema'), 'passed')
    assert result['failure_stage'] is None


@pytest.mark.parametrize('raw', [
    'Explanation\n```json\n{}\n```', '```json\n{}\n```\nDone.',
    '```json\n{}\n```\n```json\n{}\n```', '```json\n{}',
    '```python\n{}\n```', '```json\n```\n{}\n```', '```json {} ```'])
def test_non_outer_multiple_or_truncated_fences_rejected(raw):
    from egrs.offline.parsing import parse_teacher_output
    result = parse_teacher_output(raw, payload=example()['payload'])
    assert result['answer'] is None and result['failure_stage'] == 'wrapper'
    assert result['stages'] == {'wrapper': 'failed', 'json': 'not_run', 'schema': 'not_run'}


@pytest.mark.parametrize('raw', ['{"query_id":', '{}{}', 'Here is {"query_id":1}', '```json\n{"query_id":\n```'])
def test_json_failure_is_distinct_from_wrapper_and_schema(raw):
    from egrs.offline.parsing import parse_teacher_output
    result = parse_teacher_output(raw, payload=example()['payload'])
    assert result['answer'] is None and result['failure_stage'] == 'json'
    assert result['stages'] == {'wrapper': 'passed', 'json': 'failed', 'schema': 'not_run'}


@pytest.mark.parametrize('change,category', [
    ('release', 'release_kind'), ('identifier', 'entity_identifier'),
    ('goals', 'fixed_goal_set'), ('unbound', 'bound_evidence'),
    ('role', 'role_enum'), ('association', 'entity_association'),
    ('supports', 'evidence_supports')])
def test_reported_semantic_errors_remain_strictly_invalid(change, category):
    from egrs.offline.parsing import parse_teacher_output
    row = example()
    goal = row['answer']['goals'][0]
    if change == 'release': goal['release'] = 'NOT_APPLICABLE'
    elif change == 'identifier': goal['entity_ref'] = 'white bowl'
    elif change == 'goals': row['answer']['goals'] = []
    elif change == 'unbound':
        row['answer'] = unknown(1)
        row['answer']['goals'][0]['role'] = 'TARGET'
    elif change == 'role': goal['role'] = 'DESTINATION'
    elif change == 'association': goal['association'] = 'UNKNOWN'
    elif change == 'supports': goal['evidence'][0]['supports'] = ['destination']
    raw = '```json\n' + json.dumps(row['answer']) + '\n```'
    result = parse_teacher_output(raw, payload=row['payload'])
    assert result['answer'] is None and result['failure_stage'] == 'schema'
    assert result['stages']['json'] == 'passed'
    assert result['schema_category'] == category and result['errors']['schema']


def test_fixed_multigoal_transport_mechanism_unknown_and_evidence_bindings():
    from egrs.offline.parsing import parse_teacher_output
    row = example()
    registry = row['payload']['context']['registry']
    instruction = 'put bowl in drawer and close drawer'
    registry['instruction'] = row['payload']['context']['instruction'] = instruction
    registry['goals'].append({'goal_ref': 'g1', 'source_text': 'close drawer', 'actor_text': 'close drawer',
                             'target': 'drawer', 'destination': None, 'kind': 'mechanism'})
    mechanism = dict(unknown(1)['goals'][0], goal_ref='g1', release='NOT_APPLICABLE')
    row['answer']['goals'].append(mechanism)
    assert parse_teacher_output(json.dumps(row['answer']), payload=row['payload'])['answer'] == row['answer']
    for field, value in [('release', 'UNKNOWN'), ('goal_ref', 'g0')]:
        bad = copy.deepcopy(row['answer'])
        bad['goals'][1][field] = value
        assert parse_teacher_output(json.dumps(bad), payload=row['payload'])['failure_stage'] == 'schema'
    for field, value in [('entity_ref', 'another_entity'), ('goal_ref', 'g1'), ('query_id', 2),
                         ('snapshot_id', 'q2'), ('camera', 'overhead'), ('bbox', [0, 0, 0, 0])]:
        bad = copy.deepcopy(row['answer'])
        bad['goals'][0]['evidence'][0][field] = value
        assert parse_teacher_output(json.dumps(bad), payload=row['payload'])['failure_stage'] == 'schema'


def test_teacher_records_stage_errors_raw_and_no_retry():
    from egrs.offline.teacher import OfflineTeacher
    registry = example()['payload']['context']['registry']
    raw = '```json\n' + json.dumps(registry) + '\n```'
    backend = FakeBackend([raw, '```json\n{\n```'])
    teacher = OfflineTeacher(loader=lambda config: backend)
    first = teacher.registry(registry['instruction'])
    second = teacher.registry(registry['instruction'])
    assert first['answer'] == registry and first['raw'] == raw
    assert first['parsing']['strategy'] == 'fenced_json'
    assert second['parsing']['failure_stage'] == 'json' and second['answer'] is None
    assert teacher.calls == len(backend.messages) == 2
    assert first['parsing']['protocol'] == teacher.metadata['parse_protocol']


def test_teacher_examples_validate_and_supplement_is_audited_without_student_changes(tmp_path):
    from egrs.offline.teacher import OfflineTeacher
    from egrs.offline.teacher_prompt import PREDICTION_EXAMPLES, PROMPT_VERSION, build_teacher_messages
    from egrs.contracts import validate_prediction
    from egrs.selector.prompt import build_messages
    _, prepared = prepared_fixture(tmp_path)
    payload = prepared['windows'][0]['samples'][0]['payload']
    for answer in PREDICTION_EXAMPLES:
        validate_prediction(answer, example()['payload']['context']['registry'], 1, example()['payload']['sensor'])
    assert PREDICTION_EXAMPLES[0]['goals'][0]['entity_ref'] is None
    assert PREDICTION_EXAMPLES[1]['goals'][0]['evidence'][0]['bbox'] is not None
    original = copy.deepcopy(payload)
    shared = build_messages(payload)
    teacher_messages = build_teacher_messages(payload)
    assert teacher_messages[1:] == shared[1:] and payload == original
    assert teacher_messages[0]['content'].startswith(shared[0]['content'])
    backend = FakeBackend([unknown(1)])
    teacher = OfflineTeacher(loader=lambda config: backend)
    result = teacher.predict(payload)
    assert result['answer'] == unknown(1)
    assert result['messages'] == teacher_messages == backend.messages[0]
    assert teacher.metadata['prompt_version'] == PROMPT_VERSION
    assert build_messages(payload) == shared


def test_augmented_teacher_prompt_still_obeys_existing_encoder_budget():
    from egrs.offline.teacher import _Backend, resolve_config
    from egrs.offline.teacher_prompt import build_teacher_messages
    backend = _Backend.__new__(_Backend)
    backend.config = resolve_config({'device': 'cpu'})
    backend.processor = FakeProcessor()
    class NeverGenerate:
        def generate(self, **kwargs):
            pytest.fail('over-budget augmented prompt must fail before forward')
    backend.model = NeverGenerate()
    payload = example()['payload']
    payload['context']['instruction'] = 'x' * 3500
    audit = {'generation_attempted': False}
    from PIL import Image
    with pytest.raises(ValueError, match='length'):
        backend.generate(build_teacher_messages(payload), [Image.new('RGB', (4, 4)) for _ in range(2)], audit)
    assert audit['generation_attempted'] is False


def diagnostic_rows():
    rows = []
    for index, answer in enumerate([example()['answer'], unknown(1), example()['answer'], None, None, None]):
        sample = example()
        sample.update(sample_id=f's{index}', answer=None, provenance={})
        if index == 2:
            answer['goals'][0]['release'] = 'NOT_APPLICABLE'
        raw = '```json\n' + json.dumps(answer) + '\n```' if answer is not None else None
        if index == 3: raw = 'Here is JSON\n```json\n{}\n```'
        attempt = {'sample_id': sample['sample_id'], 'attempted': index != 5,
                   'raw': raw, 'answer': None, 'error': 'original error retained',
                   'generation_attempted': index < 4}
        rows.append({'sample': sample, 'attempt': attempt})
    return rows


def test_diagnose_journal_preserves_snapshot_and_reports_actual_coverage(tmp_path):
    from egrs.offline.diagnostics import diagnose
    import hashlib
    path = tmp_path / 'candidates.partial.jsonl'
    rows = diagnostic_rows()
    data = ''.join(json.dumps(row) + '\n' for row in rows).encode()
    path.write_bytes(data)
    report = diagnose(path, tmp_path / 'derived')
    assert path.read_bytes() == data and report['source']['sha256'] == hashlib.sha256(data).hexdigest()
    assert report['counts'] == {'records': 6, 'attempted': 5, 'unattempted': 1, 'attempted_without_raw': 1,
        'wrapper_passed': 3, 'json_passed': 3, 'schema_passed': 2, 'input_errors': 0}
    assert report['first_errors'] == {'wrapper': 1, 'release_kind': 1}
    assert report['coverage']['valid_predictions'] == 2
    assert report['coverage']['all_unknown_predictions'] == 1
    assert report['coverage']['evidence_non_unknown_predictions'] == 1
    assert report['coverage']['non_unknown_fields'] == {'association': 1, 'role': 1, 'relation': 1, 'release': 1, 'interaction': 1}
    assert report['new_model_calls'] == 0 and report['supervision_ready'] is False
    assert report['original_generation'] == {'yes': 4, 'no': 1, 'unknown': 0}
    derived = [json.loads(line) for line in (tmp_path / 'derived/records.jsonl').read_text().splitlines()]
    assert [row['raw'] for row in derived] == [row['attempt']['raw'] for row in rows]
    assert all(row['original_error'] == 'original error retained' for row in derived)
    assert derived[-1]['status'] == 'unattempted' and derived[-1]['parsing'] is None
    assert len(derived) == 6  # No manufactured later queries/history.
    with pytest.raises(FileExistsError):
        diagnose(path, tmp_path / 'derived')


def test_diagnose_final_manifest_and_registry_do_not_rewrite_old_success_counts(tmp_path):
    from egrs.offline.diagnostics import diagnose
    from egrs.offline.common import seal
    rows = diagnostic_rows()[:3]
    manifest = seal({'format': 'egrs.candidates.v1', 'samples': [r['sample'] for r in rows],
        'attempts': [r['attempt'] for r in rows], 'teacher': {'prompt_sha256': 'original-prompt'},
        'counts': {'attempted': 3, 'failed': 3, 'succeeded': 0, 'unattempted': 0}})
    path = tmp_path / 'candidates.json'
    path.write_text(json.dumps(manifest))
    original = path.read_bytes()
    report = diagnose(path, tmp_path / 'predictions')
    assert report['counts']['schema_passed'] == 2
    assert report['source']['original_counts']['succeeded'] == 0
    assert report['source']['teacher'] == manifest['teacher'] and path.read_bytes() == original
    registry = example()['payload']['context']['registry']
    reg_manifest = seal({'format': 'egrs.registry-candidates.v1', 'registries': {'text0': {'instruction': registry['instruction']}},
        'attempts': [{'instruction_id': 'text0', 'attempted': True, 'raw': '```\n' + json.dumps(registry) + '\n```',
                      'answer': None, 'error': 'old JSON error'}], 'calls': 1})
    reg_path = tmp_path / 'registries.json'
    reg_path.write_text(json.dumps(reg_manifest))
    reg_report = diagnose(reg_path, tmp_path / 'registry-diagnosis')
    assert reg_report['counts']['schema_passed'] == 1
    assert reg_report['coverage']['valid_predictions'] == 0
    assert reg_report['source']['original_calls'] == 1


def test_diagnose_partial_outer_record_is_input_error_not_model_json_failure(tmp_path):
    from egrs.offline.diagnostics import diagnose
    path = tmp_path / 'partial.jsonl'
    path.write_text(json.dumps(diagnostic_rows()[0]) + '\n{"sample":')
    report = diagnose(path, tmp_path / 'diagnosis')
    assert report['counts']['input_errors'] == 1 and report['counts']['schema_passed'] == 1
    assert report['counts']['attempted'] == 1 and report['first_errors'] == {}
    assert report['source']['snapshot_only'] is True
    assert report['input_errors'][0]['line'] == 2


@pytest.mark.parametrize('tail', [b'{"raw":"\xe4\xb8', b'\xef\xbb\xbf{}'])
def test_diagnose_partial_utf8_and_late_bom_preserve_prior_rows(tmp_path, tail):
    from egrs.offline.diagnostics import diagnose
    import hashlib
    path = tmp_path / 'partial.jsonl'
    data = b'\xef\xbb\xbf' + json.dumps(diagnostic_rows()[0]).encode('utf-8') + b'\n' + tail
    path.write_bytes(data)
    report = diagnose(path, tmp_path / 'diagnosis')
    assert report['counts']['records'] == report['counts']['attempted'] == report['counts']['schema_passed'] == 1
    assert report['counts']['input_errors'] == 1 and report['first_errors'] == {}
    assert report['input_errors'][0]['line'] == 2
    assert path.read_bytes() == data and report['source']['sha256'] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize('damage', ['registry', 'query', 'snapshot_type', 'snapshot_query',
                                   'snapshot_id', 'duplicate', 'future', 'missing_current'])
def test_diagnose_corrupt_context_is_input_error_not_model_failure(tmp_path, damage):
    from egrs.offline.diagnostics import diagnose
    row = diagnostic_rows()[1]  # Legal all-UNKNOWN raw must not hide invalid source metadata.
    payload = row['sample']['payload']
    if damage == 'registry': payload['context']['registry'] = None
    elif damage == 'query': payload['context']['query_id'] = True
    elif damage == 'snapshot_type': payload['sensor'][0] = None
    elif damage == 'snapshot_query': payload['sensor'][0]['query_id'] = '1'
    elif damage == 'snapshot_id': payload['sensor'][0]['snapshot_id'] = 'wrong'
    elif damage == 'duplicate': payload['sensor'].append(copy.deepcopy(payload['sensor'][0]))
    elif damage == 'future': payload['sensor'][0].update(query_id=2, snapshot_id='q2')
    elif damage == 'missing_current': payload['sensor'] = []
    path = tmp_path / 'partial.jsonl'
    path.write_text(json.dumps(diagnostic_rows()[0]) + '\n' + json.dumps(row), encoding='utf-8')
    report = diagnose(path, tmp_path / 'diagnosis')
    assert report['counts']['records'] == report['counts']['attempted'] == report['counts']['schema_passed'] == 1
    assert report['counts']['input_errors'] == 1 and report['first_errors'] == {}
    assert report['input_errors'][0]['line'] == 2
    assert report['original_generation'] == {'yes': 1, 'no': 0, 'unknown': 0}


def test_diagnostic_cli_never_imports_models_or_reads_images(tmp_path):
    import subprocess
    import sys
    path = tmp_path / 'journal.jsonl'
    path.write_text(json.dumps(diagnostic_rows()[0]) + '\n')
    # Frame paths in the synthetic record do not exist; diagnosis needs only context, not pixels.
    script = "import sys; from egrs.offline.cli import main; main(sys.argv[1:]); assert not any(n in sys.modules for n in ('torch','transformers','h5py','egrs.offline.teacher','PIL.Image'))"
    process = subprocess.run([sys.executable, '-c', script, 'diagnose', '--input', str(path), '--output', str(tmp_path / 'out')],
                             capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)['counts']['schema_passed'] == 1
