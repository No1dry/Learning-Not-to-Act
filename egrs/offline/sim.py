"""Immutable, explicitly invoked simulator annotation and selector export stages.

Truth-bearing requests/events/audits are operational sidecars. Only answer and
provenance are attached to copies of frozen samples. Importing this module does
not inspect HDF, import a native simulator, launch a worker, or load a model.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

from egrs.data import ATTESTATION_KEYS, validate_sample, write_json, build_dataset
from .common import digest, new_output, read, seal, verify
from .sim_contract import load_goal_map, mapping_for, validate_frame_facts
from .sim_labels import build_answer
from .sim_identity import code_identity
from .sim_worker import EVENT_FORMAT, RESPONSE_FORMAT, WorkerFailure, run_isolated, validate_request

REAL_IDENTITIES = {
    'dataset': 'yifengzhu-hf/LIBERO-datasets',
    'revision': '147fa5eb607bb696dd922c3518084a90954cd2f3',
    'inventory': '3f550e7736ba5428dad789a307e2c18b32f25ec51dcc763e1fb8e65db563bb33',
    'windows': 'bb453b047946179eb1ec68eb4c9ab884f9b2564b5173e849836a5caa56988cdd',
    'registries': 'ec058064453e996175bebfca449d427b240d762a08d33c01f383164dc16a8095',
}
STATE_FIELDS = ('relation', 'interaction', 'release')
FIELDS = ('entity_ref', 'association', 'role', *STATE_FIELDS)
ARTIFACT_FILES = {'inventory.json', 'registries.json', 'backend-config.json', 'image-bindings.json',
                  'requests.jsonl', 'events.jsonl', 'audit.jsonl',
                  'annotations.partial.jsonl', 'annotations.jsonl', 'progress.json', 'coverage.json'}


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def _backend(config):
    if (not isinstance(config, dict) or set(config) - {'format', 'identity_scope', 'synthetic_basis', 'expected', 'worker', 'native'}
            or config.get('format') != 'egrs.sim.backend.v1'):
        raise ValueError('invalid simulator backend configuration')
    scope = config.get('identity_scope')
    if scope not in {'production', 'synthetic'} or set(config.get('expected', {})) != set(REAL_IDENTITIES):
        raise ValueError('explicit production or synthetic expected identities required')
    if scope == 'production' and config['expected'] != REAL_IDENTITIES:
        raise ValueError('production frozen identities cannot change')
    if scope == 'synthetic' and (not config.get('synthetic_basis') or config['expected']['dataset'] == REAL_IDENTITIES['dataset']):
        raise ValueError('synthetic fixtures require a distinct dataset and explicit basis')
    worker = config.get('worker', {})
    if set(worker) != {'python', 'module_paths', 'timeout_seconds'}:
        raise ValueError('explicit worker python, module_paths and timeout_seconds required')
    if not isinstance(worker['python'], str) or not Path(worker['python']).is_absolute():
        raise ValueError('worker interpreter must be an absolute file path')
    if not isinstance(worker['module_paths'], list) or any(not isinstance(x, str) or not Path(x).is_absolute() for x in worker['module_paths']):
        raise ValueError('worker module paths must be explicit absolute directory paths')
    timeout = worker['timeout_seconds']
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError('source timeout must be finite, positive and <=86400')
    # This pure validator imports numpy but no native simulator or source file.
    from .sim_native import validate_config
    native = validate_config(config.get('native'))
    return deepcopy(worker), native


def _worker_available(worker):
    """Label-only launch prerequisite; export retains these as historical paths."""
    if not Path(worker['python']).is_file():
        raise ValueError('worker interpreter must be an existing absolute file')
    if any(not Path(path).is_dir() for path in worker['module_paths']):
        raise ValueError('worker module paths must be existing absolute directories')


def _aliases(planned, splits):
    aliases = {}
    for source in planned:
        sid = source['source_id']
        if splits.get(sid) not in {'train', 'dev'}: raise ValueError('source missing frozen split')
        for group in source.get('group_ids', []):
            if not isinstance(group, str) or not group: raise ValueError('invalid source group')
            if group in aliases and aliases[group] != splits[sid]: raise ValueError('known alias crosses frozen split')
            aliases[group] = splits[sid]


def _image_descriptors(observation):
    aliases = {'agentview': ('agentview_image', 'image'), 'wrist': ('robot0_eye_in_hand_image', 'wrist_image')}
    nested = observation.get('images', {})
    if set(nested) - {'agentview', 'wrist', 'robot0_eye_in_hand'}: raise ValueError('extra original camera')
    result = {}
    from PIL import Image
    for camera, names in aliases.items():
        values = [observation[n] for n in names if n in observation]
        values += [nested[n] for n in ((camera,) if camera == 'agentview' else ('wrist', 'robot0_eye_in_hand')) if n in nested]
        if not values or any(not isinstance(x, str) for x in values) or len(set(values)) != 1:
            raise ValueError('missing/conflicting original image paths')
        try:
            path = Path(values[0]).resolve(strict=True)
            with Image.open(path) as image:
                if image.mode != 'RGB' or image.format != 'PNG': raise ValueError('original RGB PNG required')
                width, height = image.size
        except OSError as exc: raise ValueError('original image unavailable') from exc
        result[camera] = {'path': str(path), 'width': width, 'height': height}
    return result


def _inputs(inventory, windows, registries, config, *, require_worker_runtime=True):
    verify(inventory, 'egrs.inventory.v1'); verify(windows, 'egrs.windows.v1')
    verify(registries, 'egrs.registries.confirmed.v1')
    worker, native = _backend(config)
    if require_worker_runtime: _worker_available(worker)
    actual = dict(dataset=inventory['dataset'], revision=inventory['revision'], inventory=inventory['identity'],
                  windows=windows['identity'], registries=registries['identity'])
    if actual != config['expected']: raise ValueError('frozen input identities disagree with backend expected identities')
    if windows['inventory_id'] != inventory['identity'] or registries['inventory_id'] != inventory['identity']:
        raise ValueError('inventory binding mismatch')
    splits = inventory['source_splits']
    if windows['source_splits'] != splits or windows['planned_sources'] != inventory['planned_sources']:
        raise ValueError('original planned sources/fixed source splits changed')
    _aliases(inventory['planned_sources'], splits)
    planned = {x['source_id']: x for x in inventory['planned_sources']}
    sources = {x['source_id']: x for x in inventory['sources']}
    if len(planned) != len(inventory['planned_sources']) or len(sources) != len(inventory['sources']):
        raise ValueError('duplicate source descriptors')
    if set(splits) != set(planned): raise ValueError('frozen split table differs from planned source set')
    for sid, source in sources.items():
        if sid not in planned or any(source.get(k) != v for k, v in planned[sid].items()):
            raise ValueError('source differs from planned source descriptor')
        if source['split'] != splits[sid]: raise ValueError('inventory source split mismatch')
        entry = registries['registries'].get(source['instruction_id'], {})
        registry = entry.get('registry')
        if entry.get('confirmed') is not True or not entry.get('reviewer') or not isinstance(registry, dict):
            raise ValueError('existing confirmed registry required')
        if digest(source['instruction']) != source['instruction_id'] or registry['instruction'] != source['instruction']:
            raise ValueError('source/registry instruction binding mismatch')
        mapping_for(registry)
    samples, bindings, requests, images, window_ids = [], {}, {}, {}, set()
    for window in windows['windows']:
        sid = window['source_id']; source = sources.get(sid)
        if source is None: raise ValueError('window source absent from inventory')
        wid = (sid, window['window_id'])
        if wid in window_ids: raise ValueError('duplicate source/window')
        window_ids.add(wid)
        if window['split'] != splits[sid] or window['orientation'] != source['orientation'] or window['cameras'] != ['agentview', 'wrist']:
            raise ValueError('window source/split/orientation/camera binding mismatch')
        frames = window['frames']
        if (not isinstance(frames, list) or not 1 <= len(frames) <= 3 or frames != sorted(set(frames))
                or any(type(f) is not int or not 0 <= f < source['T'] for f in frames)
                or len(window['samples']) != len(frames)):
            raise ValueError('invalid frozen window frame/query bindings')
        registry = registries['registries'][source['instruction_id']]['registry']
        for q, sample in enumerate(window['samples'], 1):
            validate_sample(sample)
            key = sample['sample_id']; context = sample['payload']['context']
            if key in bindings or sample['source_id'] != sid or sample['window_id'] != window['window_id']:
                raise ValueError('duplicate or mismatched sample/source/window binding')
            if any(sample.get(k) != source.get(k) for k in ('group_ids', 'task_group', 'ancestry_known')):
                raise ValueError('sample source group/ancestry binding mismatch')
            if context['query_id'] != q or context['instruction'] != source['instruction'] or context['registry'] != registry:
                raise ValueError('sample query/registry binding mismatch')
            sensors = sample['payload']['sensor']
            if ([s['query_id'] for s in sensors] != list(range(1, q + 1)) or
                    any(s['snapshot_id'] != f'q{s["query_id"]}' for s in sensors)):
                raise ValueError('original chronological snapshot binding mismatch')
            for sensor in sensors:
                frame = frames[sensor['query_id'] - 1]
                descriptor = _image_descriptors(sensor['observation'])
                physical = (sid, frame)
                if physical in images and images[physical] != descriptor:
                    raise ValueError('physical source/frame image binding changed across queries/windows')
                images[physical] = descriptor
            bindings[key] = (sid, frames[q - 1]); samples.append(sample)
        if sid not in requests:
            requests[sid] = dict(format='egrs.sim.request.v1', request_id='source-' + digest(sid),
                source_root=str(Path(inventory['root']).resolve()), source=deepcopy(source), registry=deepcopy(registry),
                frames=[], config=deepcopy(native))
    for sid, request in requests.items():
        request['frames'] = [dict(frame=f, images=images[(sid, f)]) for s, f in sorted(images) if s == sid]
        validate_request(request)
    if config['identity_scope'] == 'production':
        counts = (len(sources), len(windows['windows']), len(samples), len(registries['registries']),
                  sum(len(x['registry']['goals']) for x in registries['registries'].values()),
                  Counter(splits.values()))
        if counts != (200, 1200, 3200, 20, 21, Counter(train=160, dev=40)):
            raise ValueError('production workload differs from frozen 20/200/1200/3200/21 allocation')
    return worker, requests, samples, bindings


def _unknown(source_id, frame, registry):
    return dict(format='egrs.sim.frame.v1', source_id=source_id, frame=frame,
        alignment=dict(format='egrs.sim.alignment.v1', accepted=False, rule=None, basis=[],
            orientation='identity', boundary_policy='gap', threshold=.03, comparisons=[], reason='missing_or_failed_frame'),
        goals=[dict(goal_ref=g['goal_ref'], kind=g['kind'], entity_ref=None, native_truth=None,
                    grasp='unknown', evidence=[]) for g in registry['goals']])


def _image_lock(requests):
    hashes, records = {}, []
    for sid, request in requests.items():
        for frame in request['frames']:
            for camera, image in frame['images'].items():
                path = image['path']
                if path not in hashes: hashes[path] = sha256_file(path)
                records.append(dict(source_id=sid, frame=frame['frame'], camera=camera,
                                    **image, sha256=hashes[path]))
    return {'format':'egrs.sim.images.v1', 'images':records}


def _coverage(samples, annotations, details, inventory, windows):
    from egrs.selector.supervision import prepare_answer
    def bucket():
        return dict(planned=0, processed=0, supervised=0, gap=0, unknown=0, unknown_fields=0,
                    field_supervision={}, field_planned={}, label_counts={}, history_available=0)
    total, tasks, splits = bucket(), {}, {k: bucket() for k in ('train', 'dev')}
    source_sets = {k: set() for k in ('planned', 'processed', 'supervised')}
    for sample in samples:
        key = sample['sample_id']; sid = sample['source_id']; row = annotations.get(key)
        part = inventory['source_splits'][sid]; task = sample.get('task_group', 'unclassified')
        bins = [total, tasks.setdefault(task, bucket()), splits[part]]
        source_sets['planned'].add(sid)
        processed = details.get(key, {}).get('processed', False)
        if processed: source_sets['processed'].add(sid)
        fields = prepare_answer(row['answer'], row['provenance'])[1] if row else set()
        state = {f'/goals/{i}/{f}' for i in range(len(sample['payload']['context']['registry']['goals'])) for f in STATE_FIELDS}
        supervised = bool(fields & state)
        if supervised: source_sets['supervised'].add(sid)
        missing = details.get(key, {}).get('gaps', [])
        unknown = sum(g[f] == 'UNKNOWN' for g in row['answer']['goals'] for f in STATE_FIELDS) if row else sum(
            2 if g['kind'] == 'mechanism' else 3 for g in sample['payload']['context']['registry']['goals'])
        for b in bins:
            b['planned'] += 1; b['processed'] += int(processed); b['supervised'] += int(supervised)
            b['gap'] += int(not row or bool(missing)); b['unknown'] += int(unknown > 0); b['unknown_fields'] += unknown
            b['history_available'] += int(bool(sample['payload']['context'].get('history')))
            for i, goal in enumerate(sample['payload']['context']['registry']['goals']):
                for f in FIELDS:
                    if f == 'release' and goal['kind'] == 'mechanism': continue
                    b['field_planned'][f] = b['field_planned'].get(f, 0) + 1
                    if f'/goals/{i}/{f}' in fields:
                        b['field_supervision'][f] = b['field_supervision'].get(f, 0) + 1
                if row:
                    for f in FIELDS:
                        value = row['answer']['goals'][i][f]
                        counts = b['label_counts'].setdefault(f, {})
                        label = 'null' if value is None else value
                        counts[label] = counts.get(label, 0) + 1
    for b in [total, *tasks.values(), *splits.values()]:
        b['processed_percent'] = 100 * b['processed'] / b['planned'] if b['planned'] else 0.
        b['supervised_percent'] = 100 * b['supervised'] / b['planned'] if b['planned'] else 0.
    return dict(total=total, tasks=tasks, splits=splits,
        sources={**{k: len(v) for k, v in source_sets.items()}, 'inventory_planned': len(inventory['planned_sources']),
                 'without_windows': sorted(set(inventory['source_splits']) - source_sets['planned'])},
        input_gaps=dict(inventory=inventory['gaps'], windows=windows['gaps']))


def _write_progress(path, value):
    temporary = path.with_suffix('.tmp')
    write_json(temporary, value)
    temporary.replace(path)


def label_sim(inventory, windows, registries, backend_config, output, *, worker_runner=None):
    """Validate the whole frozen workload before launching one worker per source."""
    worker, requests, samples, bindings = _inputs(inventory, windows, registries, backend_config)
    implementation = code_identity()
    runner = worker_runner or run_isolated
    output = new_output(output)
    write_json(output/'inventory.json', inventory); write_json(output/'registries.json', registries)
    write_json(output/'backend-config.json', backend_config)
    write_json(output/'image-bindings.json', _image_lock(requests))
    annotations, details, source_results = {}, {}, []
    by_frame = defaultdict(list)
    for sample in samples: by_frame[bindings[sample['sample_id']]].append(sample)
    streams = {name: (output/name).open('x', encoding='utf-8') for name in (
        'requests.jsonl', 'events.jsonl', 'audit.jsonl', 'annotations.partial.jsonl')}
    def append(name, value):
        streams[name].write(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
        streams[name].flush()
    def progress():
        value = dict(format='egrs.sim.progress.v1', coverage=_coverage(samples, annotations, details, inventory, windows))
        _write_progress(output/'progress.json', value)
        total = value['coverage']['total']
        print(json.dumps({'sim_progress': {k: total[k] for k in (
            'planned','processed','processed_percent','supervised','supervised_percent','gap','unknown')}},
            ensure_ascii=False), file=sys.stderr, flush=True)
        return value['coverage']
    def annotate(fact, processed):
        sid, frame = fact['source_id'], fact['frame']
        for sample in by_frame[(sid, frame)]:
            result = build_answer(sample, fact, frame=frame)
            copied = deepcopy(sample); copied.update(answer=result['answer'], provenance=result['provenance'])
            annotations[sample['sample_id']] = copied
            details[sample['sample_id']] = dict(processed=processed, gaps=result['gaps'])
            append('annotations.partial.jsonl', copied)
            append('audit.jsonl', dict(type='query_coverage', sample_id=sample['sample_id'],
                source_id=sid, frame=frame, processed=processed, gaps=result['gaps'],
                supervised_state_query=result['supervised_state_query'],
                history_available=bool(sample['payload']['context']['history'])))
    try:
        progress()
        for sid, request in requests.items():
            append('requests.jsonl', request)
            events, received, result_event, protocol_errors = [], {}, [], []
            def on_event(event):
                append('events.jsonl', event)  # Retain even a rejected protocol record.
                try:
                    if (not isinstance(event, dict) or set(event) != {'format','request_id','source_id','sequence','type','data'}
                            or event['format'] != EVENT_FORMAT or event['request_id'] != request['request_id']
                            or event['source_id'] != sid or type(event['sequence']) is not int or event['sequence'] != len(events)
                            or event['type'] not in {'inspection','stage','alignment','frame','audit','progress','error','result'}
                            or result_event):
                        raise ValueError('worker event identity/order/schema mismatch')
                    events.append(deepcopy(event))
                    kind, data = event['type'], event['data']
                    append('audit.jsonl', dict(type='worker_'+kind, source_id=sid, sequence=event['sequence'], data=data))
                    if kind == 'stage' and (not isinstance(data,dict) or set(data) != {'stage','phase'} or
                            not isinstance(data['stage'], str) or data['phase'] not in {'begin','complete'}):
                        raise ValueError('invalid initialization stage event')
                    if kind == 'frame':
                        fact = validate_frame_facts(data)
                        if fact['source_id'] != sid or fact['frame'] not in {f['frame'] for f in request['frames']} or fact['frame'] in received:
                            raise ValueError('unsolicited, duplicate or misbound frame fact')
                        # Build all query labels before admitting this fact.
                        for sample in by_frame[(sid, fact['frame'])]: build_answer(sample, fact, frame=fact['frame'])
                        received[fact['frame']] = fact
                        annotate(fact, True)
                    if kind == 'result': result_event.append(deepcopy(data))
                    if kind in {'frame','error','progress','stage','inspection'}: progress()
                except Exception as error:
                    protocol_errors.append(str(error))
                    append('audit.jsonl', dict(type='controller_protocol_error', source_id=sid, reason=str(error)))
                    raise
            failure = None
            try:
                response = runner(deepcopy(request), **worker, on_event=on_event,
                                  expected_code_identity=implementation['identity'])
                if (response.get('format') != RESPONSE_FORMAT or response.get('request_id') != request['request_id']
                        or response.get('source_id') != sid or response.get('status') not in {'complete','partial','failed'}
                        or result_event != [response] or response.get('frames') != list(received.values())
                        or (response['status'] == 'complete' and set(received) != {f['frame'] for f in request['frames']})):
                    raise ValueError('worker result disagrees with streamed source/frame facts')
            except WorkerFailure as error:
                failure = dict(type='worker_failure', source_id=sid, error_type=type(error).__name__,
                               reason=str(error), stderr=error.stderr)
                append('audit.jsonl', failure); append('events.jsonl', dict(format='egrs.sim.controller-event.v1', **failure))
                if protocol_errors: raise ValueError(protocol_errors[-1]) from error
                response = dict(status='partial' if received else 'failed', errors=[failure])
            except Exception as error:
                append('audit.jsonl', dict(type='controller_failure', source_id=sid, reason=str(error)))
                raise
            for item in request['frames']:
                if item['frame'] not in received: annotate(_unknown(sid, item['frame'], request['registry']), False)
            source_results.append(dict(source_id=sid, status=response['status'], planned_frames=len(request['frames']),
                                       processed_frames=len(received), errors=response.get('errors', [])))
            progress()
    finally:
        for stream in streams.values(): stream.close()
    with (output/'annotations.jsonl').open('x', encoding='utf-8') as stream:
        for sample in samples: stream.write(json.dumps(annotations[sample['sample_id']], ensure_ascii=False, allow_nan=False) + '\n')
    coverage = _coverage(samples, annotations, details, inventory, windows)
    write_json(output/'coverage.json', coverage)
    ready = (bool(samples) and coverage['total']['supervised'] == len(samples) and not coverage['total']['gap']
             and not inventory['gaps'] and not windows['gaps'] and not coverage['sources']['without_windows']
             and all(r['status'] == 'complete' for r in source_results))
    if code_identity() != implementation:
        raise ValueError('annotation implementation identity changed during labeling')
    manifest = seal(dict(format='egrs.sim.annotations.v1', inputs=deepcopy(backend_config['expected']),
        config_identity=digest(backend_config), mapping_identity=digest(load_goal_map()), code=implementation,
        source_splits=deepcopy(inventory['source_splits']), source_results=source_results, coverage=coverage,
        ready=ready, usable=coverage['total']['supervised'] > 0,
        files={name: sha256_file(output/name) for name in sorted(ARTIFACT_FILES)}))
    write_json(output/'manifest.json', manifest)
    return manifest


def _jsonl(path):
    with path.open(encoding='utf-8') as stream: return [json.loads(line) for line in stream if line.strip()]


def export_sim(annotations, windows, attestation, output):
    """Verify sealed artifacts and original samples; export usable subset only."""
    path = Path(annotations).resolve(strict=True)
    manifest = verify(read(path), 'egrs.sim.annotations.v1'); root = path.parent
    if set(manifest.get('files', {})) != ARTIFACT_FILES: raise ValueError('incomplete sealed artifact file set')
    for name, checksum in manifest['files'].items():
        if sha256_file(root/name) != checksum: raise ValueError('artifact file hash mismatch: ' + name)
    if manifest['code'] != code_identity() or manifest['mapping_identity'] != digest(load_goal_map()):
        raise ValueError('annotation/export implementation or mapping identity changed')
    inventory, registries, config = read(root/'inventory.json'), read(root/'registries.json'), read(root/'backend-config.json')
    _, requests, originals, bindings = _inputs(inventory, windows, registries, config, require_worker_runtime=False)
    if (manifest['inputs'] != config['expected'] or manifest['config_identity'] != digest(config)
            or manifest['source_splits'] != inventory['source_splits']):
        raise ValueError('sealed input/config/fixed split binding mismatch')
    if _jsonl(root/'requests.jsonl') != list(requests.values()): raise ValueError('operational source/frame request changed')
    if read(root/'image-bindings.json') != _image_lock(requests): raise ValueError('original image byte binding changed')
    records = _jsonl(root/'annotations.jsonl')
    if len(records) != len(originals): raise ValueError('missing/extra annotations')
    for row, original in zip(records, originals):
        if {k:v for k,v in row.items() if k not in {'answer','provenance'}} != {
                k:v for k,v in original.items() if k not in {'answer','provenance'}}:
            raise ValueError('annotation changed original payload/group/history/ancestry/order binding')
        validate_sample(row)
        if set(row.get('provenance', {}).values()) - {'sim_supervised'}:
            raise ValueError('simulator export cannot fabricate human confirmation')
    # Recompute labels from retained frame events rather than trusting coverage claims.
    facts, details, reconstructed = {}, {}, {}
    for event in _jsonl(root/'events.jsonl'):
        if event.get('format') == EVENT_FORMAT and event.get('type') == 'frame':
            fact = validate_frame_facts(event['data']); key = (fact['source_id'], fact['frame'])
            if key in facts or fact['source_id'] not in requests or fact['frame'] not in {x['frame'] for x in requests[fact['source_id']]['frames']}:
                raise ValueError('duplicate/unsolicited audit frame')
            facts[key] = fact
    for row, original in zip(records, originals):
        sid, frame = bindings[row['sample_id']]
        fact = facts.get((sid, frame), _unknown(sid, frame, original['payload']['context']['registry']))
        expected = build_answer(original, fact, frame=frame)
        if row['answer'] != expected['answer'] or row['provenance'] != expected['provenance']:
            raise ValueError('annotation differs from observable retained frame facts')
        details[row['sample_id']] = dict(processed=(sid, frame) in facts, gaps=expected['gaps'])
        reconstructed[row['sample_id']] = row
    coverage = _coverage(originals, reconstructed, details, inventory, windows)
    if coverage != manifest['coverage'] or coverage != read(root/'coverage.json'):
        raise ValueError('annotation coverage disagrees with sealed facts')
    if not coverage['total']['supervised']: raise ValueError('no meaningful state supervision; all-UNKNOWN/evidence-only export refused')
    if not all(attestation.get(k) is True for k in ATTESTATION_KEYS):
        raise ValueError('original three-boolean exclusion attestation required')
    if Path(output).exists(): raise FileExistsError(str(output))
    report = build_dataset(records, output, attestation=attestation, seed=inventory.get('seed', 0),
                           fixed_source_splits=inventory['source_splits'])
    report.update(format='egrs.sim.export.v1', annotation_identity=manifest['identity'],
                  windows_identity=windows['identity'], coverage=coverage,
                  ready=bool(report['ready'] and manifest['ready']), usable=sum(report['splits'].values()) > 0,
                  source_splits=manifest['source_splits'], source_results=manifest['source_results'])
    write_json(Path(output)/'report.json', report)
    write_json(Path(output)/'export-manifest.json', seal(dict(format='egrs.sim.export-manifest.v1',
        annotations=manifest['identity'], windows=windows['identity'], attestation=deepcopy(attestation),
        files={name:sha256_file(Path(output)/name) for name in ('train.jsonl','dev.jsonl','report.json')})))
    return report
