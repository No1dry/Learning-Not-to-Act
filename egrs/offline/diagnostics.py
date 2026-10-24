"""CPU-only derived analysis of existing raw outputs; never replay or relabel."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from egrs.contracts import integer, validate_registry
from .common import new_output, save, seal, verify
from .parsing import PARSE_PROTOCOL, parse_teacher_output

DIAGNOSTIC_PROTOCOL = 'egrs.teacher-diagnostics.v1'


def _prediction_pair(sample, attempt):
    if not isinstance(sample, dict) or not isinstance(attempt, dict):
        raise ValueError('record needs original sample and attempt objects')
    if sample.get('sample_id') != attempt.get('sample_id') or not sample.get('sample_id'):
        raise ValueError('attempt/sample identity mismatch')
    payload = sample['payload']
    if not isinstance(payload, dict) or not isinstance(payload.get('context'), dict):
        raise ValueError('original prediction payload/context missing')
    context = payload['context']
    validate_registry(context['registry'], context.get('instruction'))
    query = integer(context['query_id'], 'original query_id')
    snapshots = payload.get('sensor')
    if not isinstance(snapshots, list) or not 1 <= len(snapshots) <= 3:
        raise ValueError('original sensor needs 1..3 snapshot references')
    ids = []
    for shot in snapshots:
        if not isinstance(shot, dict):
            raise ValueError('original snapshot reference must be an object')
        q = integer(shot['query_id'], 'original snapshot query')
        if q > query or shot['snapshot_id'] != f'q{q}':
            raise ValueError('original snapshot reference is future/invalid')
        ids.append(q)
    if ids != sorted(set(ids)) or ids[-1] != query:
        raise ValueError('original snapshots must be ordered, unique and end at current query')
    if attempt.get('payload') is not None and attempt['payload'] != payload:
        raise ValueError('attempt actual payload differs from sample; cannot choose context silently')
    return {'sample_id': sample['sample_id'], 'kind': 'prediction', 'payload': payload, 'attempt': attempt}


def _records(data, path, source, errors):
    if path.suffix.lower() == '.jsonl':
        source['format'] = 'candidate-journal-snapshot'
        # A live byte snapshot may cut a multibyte character in its final row.
        # Decode each newline-framed record strictly; never replace corrupt bytes.
        for line_number, raw_line in enumerate(data.split(b'\n'), 1):
            try:
                line = raw_line.decode('utf-8-sig' if line_number == 1 else 'utf-8')
                if not line.strip():
                    continue
                row = json.loads(line)
                record = _prediction_pair(row['sample'], row['attempt'])
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({'line': line_number, 'error': f'{type(exc).__name__}: {exc}'})
                continue
            yield dict(record, source_record=line_number)
        return
    manifest = json.loads(data.decode('utf-8-sig'))
    verify(manifest)
    source.update(format=manifest['format'], manifest_id=manifest['identity'],
                  teacher=manifest.get('teacher'), original_counts=manifest.get('counts'),
                  original_calls=manifest.get('calls'))
    attempts = manifest['attempts']
    if manifest['format'] == 'egrs.candidates.v1':
        samples = {row['sample_id']: row for row in manifest['samples']}
        if len(samples) != len(manifest['samples']):
            raise ValueError('duplicate source sample identity')
        for index, attempt in enumerate(attempts):
            try:
                record = _prediction_pair(samples[attempt['sample_id']], attempt)
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({'index': index, 'error': f'{type(exc).__name__}: {exc}'})
                continue
            yield dict(record, source_record=index)
    elif manifest['format'] == 'egrs.registry-candidates.v1':
        for index, attempt in enumerate(attempts):
            try:
                key = attempt['instruction_id']
                instruction = manifest['registries'][key]['instruction']
                if not isinstance(instruction, str) or not instruction:
                    raise ValueError('original instruction missing')
                if attempt.get('instruction') is not None and attempt['instruction'] != instruction:
                    raise ValueError('attempt instruction differs from original registry source')
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({'index': index, 'error': f'{type(exc).__name__}: {exc}'})
                continue
            yield {'instruction_id': key, 'kind': 'registry', 'instruction': instruction,
                   'attempt': attempt, 'source_record': index}
    else:
        raise ValueError('diagnose accepts only candidate/registry manifests or candidate JSONL journals')


def _add_coverage(answer, coverage):
    coverage['valid_predictions'] += 1
    informative = False
    for goal in answer['goals']:
        coverage['goals'] += 1
        supported = set()
        for evidence in goal['evidence']:
            if evidence['bbox'] is not None and goal['entity_ref'] is not None:
                supported.update(evidence['supports'])
        for field in coverage['non_unknown_fields']:
            support = 'entity' if field == 'association' else field
            if goal[field] not in {'UNKNOWN', 'NOT_APPLICABLE'} and support in supported:
                coverage['non_unknown_fields'][field] += 1
                informative = True
    coverage['evidence_non_unknown_predictions' if informative else 'all_unknown_predictions'] += 1


def diagnose(input_path, output):
    """Read once, preserve source bytes, and write only independent audit artifacts."""
    path = Path(input_path)
    data = path.read_bytes()
    source = {'name': path.name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
              'snapshot_only': True, 'teacher': None, 'original_counts': None, 'original_calls': None}
    errors = []
    records = list(_records(data, path, source, errors))
    output = new_output(output)
    counts = dict.fromkeys(('records', 'attempted', 'unattempted', 'attempted_without_raw',
                           'wrapper_passed', 'json_passed', 'schema_passed', 'input_errors'), 0)
    coverage = {'valid_predictions': 0, 'goals': 0, 'all_unknown_predictions': 0,
                'evidence_non_unknown_predictions': 0,
                'non_unknown_fields': dict.fromkeys(('association', 'role', 'relation', 'release', 'interaction'), 0)}
    first_errors = Counter()
    original_generation = dict.fromkeys(('yes', 'no', 'unknown'), 0)
    with (output / 'records.jsonl').open('x', encoding='utf-8') as stream:
        for record in records:
            attempt = record['attempt']
            if type(attempt.get('attempted')) is not bool:
                errors.append({'source_record': record['source_record'], 'error': 'explicit attempted boolean missing'})
                continue
            counts['records'] += 1
            if attempt['attempted']:
                generated = attempt.get('generation_attempted')
                original_generation['yes' if generated is True else 'no' if generated is False else 'unknown'] += 1
            row = {key: value for key, value in record.items() if key in {'sample_id', 'instruction_id', 'kind', 'source_record'}}
            row.update(raw=attempt.get('raw'), original_error=attempt.get('error'),
                       original_answer=attempt.get('answer'), original_parsing=attempt.get('parsing'),
                       original_generation_attempted=attempt.get('generation_attempted'), parsing=None,
                       derived_answer=None, provenance='weak')
            if not attempt['attempted']:
                counts['unattempted'] += 1
                row['status'] = 'unattempted'
            elif attempt.get('raw') is None:
                counts['attempted'] += 1
                counts['attempted_without_raw'] += 1
                row['status'] = 'attempted_without_raw'
            else:
                counts['attempted'] += 1
                context = {'payload': record['payload']} if record['kind'] == 'prediction' else {'instruction': record['instruction']}
                parsed = parse_teacher_output(attempt['raw'], **context)
                row['derived_answer'] = parsed['answer']
                row['parsing'] = {k: v for k, v in parsed.items() if k != 'answer'}
                row['status'] = 'schema_valid' if parsed['error'] is None else 'invalid'
                for stage, status in parsed['stages'].items():
                    if status == 'passed':
                        counts[stage + '_passed'] += 1
                if parsed['error'] is not None:
                    first_errors[parsed['schema_category'] or parsed['failure_stage']] += 1
                elif record['kind'] == 'prediction':
                    _add_coverage(parsed['answer'], coverage)
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    counts['input_errors'] = len(errors)
    report = {'format': DIAGNOSTIC_PROTOCOL, 'parse_protocol': PARSE_PROTOCOL, 'source': source,
              'counts': counts, 'first_errors': dict(first_errors), 'coverage': coverage,
              'input_errors': errors, 'original_generation': original_generation,
              'new_model_calls': 0, 'supervision_ready': False,
              'coverage_basis': 'strict-valid predictions and bound non-UNKNOWN fields; not visual truth or human supervision',
              'scope': 'derived byte snapshot only; original answers/counts/history unchanged; later queries not inferred'}
    save(output / 'report.json', report)
    return seal(report)
