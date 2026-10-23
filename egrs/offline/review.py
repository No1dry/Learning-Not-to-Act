"""Portable human review and strict frozen-manifest imports; audit stays separate."""
import copy
import json
import math
import re
from collections import Counter, defaultdict, deque
from importlib.resources import files

from egrs.data import export_annotations, import_annotations, build_dataset, write_json
from .common import verify, seal, digest, new_output, save

FIELDS = {'entity_ref', 'association', 'role', 'relation', 'release', 'interaction'}


def review_queue(samples):
    tasks = defaultdict(lambda: defaultdict(deque))
    for sample in samples:
        tasks[sample.get('task_group', 'unclassified')][sample['source_id']].append(sample['sample_id'])
    queues = {}
    for task, sources in sorted(tasks.items()):
        q = deque()
        while any(sources.values()):
            for source in sorted(sources):
                if sources[source]:
                    q.append(sources[source].popleft())
        queues[task] = q
    result = []
    while any(queues.values()):
        for q in queues.values():
            if q:
                result.append(q.popleft())
    return result


def rereview_suggestion(samples, splits):
    from egrs.selector.supervision import prepare_answer
    strata = defaultdict(set)
    for sample in samples:
        if sample.get('answer') and prepare_answer(sample['answer'], sample.get('provenance', {}))[1]:
            strata[(sample.get('task_group', 'unclassified'), splits[sample['source_id']])].add((sample['source_id'], sample['window_id']))
    result = []
    for (task, split), windows in sorted(strata.items()):
        ordered = sorted(windows, key=digest)
        result.extend({'task_group': task, 'split': split, 'source_id': s, 'window_id': w} for s, w in ordered[:max(1, math.ceil(len(ordered) * .1))])
    return result


def _target(answer, pointer):
    match = re.fullmatch(r'/goals/(0|[1-9][0-9]*)/(entity_ref|association|role|relation|release|interaction|evidence/(0|[1-9][0-9]*))', pointer)
    if not match:
        raise ValueError('confirm one label field or one complete evidence item')
    try:
        goal = answer['goals'][int(match[1])]
        value = goal['evidence'][int(match[3])] if match[3] is not None else goal[match[2]]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError('confirmation pointer does not exist') from exc
    # Every semantic claim is reviewed with its identity and complete supporting regions.
    dependencies = {'goal_ref': goal['goal_ref'], 'entity_ref': goal['entity_ref'], 'association': goal['association'], 'evidence': goal['evidence']}
    return value, dependencies


def _actor(value):
    if not isinstance(value.get('reviewer'), str) or not value['reviewer'].strip():
        raise ValueError('explicit reviewer identity required; never auto-sign')
    elapsed = value.get('elapsed_ms')
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('observed nonnegative UI elapsed_ms required')


def confirmation(answer, pointer, reviewer, elapsed_ms):
    value, dependencies = _target(answer, pointer)
    result = {'value': copy.deepcopy(value), 'dependencies': copy.deepcopy(dependencies), 'reviewer': reviewer, 'elapsed_ms': elapsed_ms}
    _actor(result)
    return result


def new_session(manifest):
    verify(manifest, 'egrs.candidates.v1')
    return {'format': 'egrs.review-session.v1', 'manifest_id': manifest['identity'],
        'annotations': export_annotations(manifest['samples']), 'confirmations': {}, 'events': [],
        'synthetic': manifest.get('synthetic', manifest.get('teacher', {}).get('synthetic_backend', False))}


def new_registry_session(manifest):
    verify(manifest, 'egrs.registry-candidates.v1')
    return {'format': 'egrs.registry-review-session.v1', 'manifest_id': manifest['identity'],
        'registries': {key: copy.deepcopy(row['registry']) for key, row in manifest['registries'].items()},
        'confirmations': {}, 'events': [], 'synthetic': manifest.get('teacher', {}).get('synthetic_backend', False)}


def _session(manifest, session, format):
    verify(manifest)
    if session.get('format') != format or session.get('manifest_id') != manifest['identity']:
        raise ValueError('review session immutable manifest identity mismatch')
    expected_synthetic = manifest.get('synthetic', manifest.get('teacher', {}).get('synthetic_backend', False))
    if session.get('synthetic') is not expected_synthetic:
        raise ValueError('synthetic fixture designation changed')
    if not isinstance(session.get('events'), list):
        raise ValueError('review events must be a list')
    for event in session['events']:
        _actor(event)


def import_review(manifest, session, output=None):
    _session(manifest, session, 'egrs.review-session.v1')
    annotations = copy.deepcopy(session['annotations'])
    originals = {r['sample_id']: r for r in manifest['samples']}
    if set(session['confirmations']) - set(originals):
        raise ValueError('confirmation for unknown sample')
    confirmations, corrections = 0, 0
    for row in annotations['samples']:
        original = originals.get(row['sample_id'])
        if original is None:
            raise ValueError('unknown review sample')
        for key in set(original) | set(row):
            if key not in {'answer', 'provenance'} and row.get(key) != original.get(key):
                raise ValueError('review changed immutable sample: ' + key)
        row['provenance'] = {'': 'weak'} if row.get('answer') is not None else {}
        if row.get('answer') != original.get('answer'):
            corrections += 1
        for pointer, confirmed in session['confirmations'].get(row['sample_id'], {}).items():
            _actor(confirmed)
            value, dependencies = _target(row['answer'], pointer)
            if value != confirmed.get('value') or dependencies != confirmed.get('dependencies'):
                raise ValueError('stale confirmation: changed value/entity/evidence requires re-review')
            row['provenance'][pointer] = 'human' if original.get('answer') is None else 'reviewed_candidate'
            confirmations += 1
    records = import_annotations(manifest['samples'], annotations)
    audit = {'confirmed_fields_or_items': confirmations, 'corrections': corrections,
        'observed_ui_elapsed_ms': sum(e['elapsed_ms'] for e in session['events']),
        'elapsed_basis': 'recorded UI event intervals; not estimated labor or verified human identity',
        'events': copy.deepcopy(session['events']), 'confirmations': copy.deepcopy(session['confirmations']),
        'synthetic': session.get('synthetic', False)}
    result = seal({'format': 'egrs.reviewed.v1', 'manifest_id': manifest['identity'], 'samples': records, 'audit': audit})
    if output is not None:
        output = new_output(output)
        save(output / 'reviewed.json', result)
        write_json(output / 'audit.json', audit)
        write_json(output / 'session.json', session)
    return result


def import_registry_review(manifest, session, output=None):
    from egrs.contracts import validate_registry
    from .inventory import instruction_id
    _session(manifest, session, 'egrs.registry-review-session.v1')
    if set(session['registries']) != set(manifest['registries']) or set(session['confirmations']) - set(manifest['registries']):
        raise ValueError('registry keys changed')
    result = {'format': 'egrs.registries.confirmed.v1', 'inventory_id': manifest['inventory_id'],
              'candidate_id': manifest['identity'], 'registries': {}}
    for key, confirmed in session['confirmations'].items():
        _actor(confirmed)
        registry = session['registries'][key]
        instruction = manifest['registries'][key]['instruction']
        if instruction_id(instruction) != key or registry != confirmed.get('value'):
            raise ValueError('stale registry confirmation')
        registry = validate_registry(registry, instruction)
        result['registries'][key] = {'registry': registry, 'confirmed': True, 'reviewer': confirmed['reviewer']}
    if output is not None:
        output = new_output(output)
        save(output / 'registries-confirmed.json', result)
        write_json(output / 'audit.json', session)
    return seal(result)


def export_review(manifest, output):
    verify(manifest)
    output = new_output(output)
    registry_mode = manifest['format'] == 'egrs.registry-candidates.v1'
    session = new_registry_session(manifest) if registry_mode else new_session(manifest)
    images = {}
    if not registry_mode:
        from egrs.selector.prompt import IMAGE_KEYS
        for sample in manifest['samples']:
            q = sample['payload']['context']['query_id']
            for snap in sample['payload']['sensor']:
                if snap['query_id'] > q:
                    raise ValueError('future review view forbidden')
                for key in IMAGE_KEYS:
                    path = snap['observation'][key]
                    if path not in images:
                        from PIL import Image
                        target = 'images/' + digest(path) + '.png'
                        (output / 'images').mkdir(exist_ok=True)
                        with Image.open(path) as image:
                            image.convert('RGB').save(output / target)
                        images[path] = target
    package = {'manifest': manifest, 'session': session, 'images': images,
               'queue': list(manifest['registries']) if registry_mode else review_queue(manifest['samples']),
               'registry_mode': registry_mode}
    template = files('egrs.offline').joinpath('assets/review.html').read_text(encoding='utf-8')
    embedded = json.dumps(package, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('&', '\\u0026')
    (output / 'index.html').write_text(template.replace('__REVIEW_DATA__', embedded), encoding='utf-8')
    write_json(output / 'session.json', session)
    return package


def build_reviewed(manifest, session, output, *, attestation):
    from egrs.selector.supervision import prepare_answer, source_for, CONFIRMED
    reviewed = import_review(manifest, session)
    if not isinstance(attestation.get('basis'), str) or not attestation['basis'].strip():
        raise ValueError('external exclusion attestation basis required; unknown ancestry remains disclosed')
    # Check aliases against the full source inventory, including unreviewed/gap sources.
    aliases = {}
    for row in manifest['planned_sources']:
        part = manifest['source_splits'][row['source_id']]
        for group in row.get('group_ids', []):
            if group in aliases and aliases[group] != part:
                raise ValueError('known alias crosses frozen split')
            aliases[group] = part
    report = build_dataset(reviewed['samples'], output, attestation=attestation, fixed_source_splits=manifest['source_splits'])
    from pathlib import Path
    output = Path(output)
    unreviewed = [r['sample_id'] for r in reviewed['samples'] if r.get('answer') is None or not prepare_answer(r['answer'], r['provenance'])[1]]
    incomplete = []
    distributions = {kind: {field: Counter() for field in sorted(FIELDS)} for kind in ('candidate', 'confirmed')}
    for kind, rows in (('candidate', manifest['samples']), ('confirmed', reviewed['samples'])):
        for row in rows:
            if row.get('answer') is None:
                continue
            missing = []
            for i, goal in enumerate(row['answer']['goals']):
                prefix = f'/goals/{i}/'
                for field in sorted(FIELDS):
                    confirmed = source_for(prefix + field, row.get('provenance', {})) in CONFIRMED
                    if kind == 'candidate' or confirmed:
                        distributions[kind][field][json.dumps(goal[field], ensure_ascii=False) if goal[field] is None else goal[field]] += 1
                    if not confirmed:
                        missing.append(prefix + field)
                missing.extend(prefix + f'evidence/{j}' for j in range(len(goal['evidence']))
                               if source_for(prefix + f'evidence/{j}', row.get('provenance', {})) not in CONFIRMED)
            if kind == 'confirmed' and missing:
                incomplete.append({'sample_id': row['sample_id'], 'pointers': missing})
    candidate_split_counts = {}
    for split in ('train', 'dev'):
        rows = [r for r in manifest['samples'] if manifest['source_splits'][r['source_id']] == split]
        candidate_split_counts[split] = {'sources': len({r['source_id'] for r in rows}),
            'windows': len({(r['source_id'], r['window_id']) for r in rows}), 'queries': len(rows)}
    report.update(manifest_id=manifest['identity'], source_gaps=manifest['gaps'],
        planned_sources=len(manifest['source_splits']), unreviewed_queries=len(unreviewed),
        candidate_split_counts=candidate_split_counts, label_distributions=distributions,
        unconfirmed_fields_or_items=incomplete,
        supervision_coverage={'sources': len({r['source_id'] for r in reviewed['samples'] if r['sample_id'] not in unreviewed}),
            'candidate_sources': len({r['source_id'] for r in reviewed['samples']})},
        audit=reviewed['audit'], rereview_suggestion=rereview_suggestion(reviewed['samples'], manifest['source_splits']))
    report['ready'] = report['ready'] and not manifest['gaps'] and not unreviewed and not incomplete
    write_json(output / 'all-candidates.json', manifest)
    write_json(output / 'all-reviewed.json', reviewed)
    write_json(output / 'unreviewed.json', {'sample_ids': unreviewed, 'unconfirmed_fields_or_items': incomplete, 'source_gaps': manifest['gaps']})
    write_json(output / 'audit.json', reviewed['audit'])
    write_json(output / 'report.json', report)
    return report
