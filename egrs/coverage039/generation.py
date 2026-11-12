"""Bounded039 generation with durable slots and a separate, pinned native worker."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np

from egrs.augmentation.data import identity, read_json
from egrs.trajectory_augmentation.control import rewind_state
from egrs.trajectory_augmentation.data import export_generated
from egrs.trajectory_augmentation.generation import (
    Attempt, _json, initialization_failure as original_initialization_failure, safe_handoff)
from egrs.trajectory_augmentation.native import TEACHER_V2
from .io import HashContext, Progress
from .plan import build_plan
from .recipe import ALGORITHM, BUDGET, RECIPE_VERSION, generation_context, recipe_for


def durable_write(path, value):
    """Publish a complete journal snapshot after flushing its bytes to storage."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, default=_json, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    # Windows file indexers may briefly open the just-published destination
    # without FILE_SHARE_DELETE. Retry only publication of these same flushed
    # bytes; no simulator call or budget reservation is retried.
    for number in range(8):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if os.name != 'nt' or number == 7: raise
            time.sleep(.01*(number+1))
    if os.name != 'nt':
        descriptor = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)


class AttemptLedger:
    """A spent slot survives failure, interruption, and reopening; no refund API."""
    def __init__(self, path): self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return {'format': 'task039-attempt-ledger-v1', 'normal_attempts': 0,
                    'ten_attempts': 0, 'slots': []}
        ledger = read_json(self.path)
        slots = ledger.get('slots', [])
        if (ledger.get('format') != 'task039-attempt-ledger-v1'
                or ledger.get('normal_attempts') != sum(s['domain'] == 'normal' for s in slots)
                or ledger.get('ten_attempts') != sum(s['domain'] == '10' for s in slots)
                or ledger['normal_attempts'] > 60 or ledger['ten_attempts'] > 360
                or len({(s['source_id'], s['domain'], str(s['variant']), s['attempt']) for s in slots}) != len(slots)):
            raise ValueError('invalid039 durable attempt ledger')
        return ledger

    def contains(self, source_id, domain, variant, number):
        return any((s['source_id'], s['domain'], s['variant'], s['attempt']) ==
                   (source_id, domain, variant, number) for s in self.read()['slots'])

    def reserve(self, source_id, domain, variant, number):
        if (domain not in ('normal', '10') or
                (domain == 'normal' and (variant != 'normal' or number != 0)) or
                (domain == '10' and (type(variant) is not int or variant not in range(3)
                                     or type(number) is not int or number not in range(2)))):
            raise ValueError('invalid bounded039 attempt slot')
        ledger = self.read()
        if self.contains(source_id, domain, variant, number):
            raise ValueError('attempt slot already consumed; implicit retry forbidden')
        counter, limit = ('normal_attempts', 60) if domain == 'normal' else ('ten_attempts', 360)
        if ledger[counter] >= limit: raise ValueError('039 attempt budget exhausted')
        if domain == '10' and not self.contains(source_id, 'normal', 'normal', 0):
            raise ValueError('normal slot must be consumed before a10 attempt')
        ledger['slots'].append({'source_id': source_id, 'domain': domain, 'variant': variant,
                                'attempt': number, 'status': 'spent_before_initialization',
                                'reserved_unix_seconds': time.time()})
        ledger[counter] += 1
        durable_write(self.path, ledger)
        return ledger


class Heartbeat:
    """Visible source/attempt progress even while a native call is blocked."""
    def __init__(self, directory, source_id, interval=30, filename='heartbeat.json'):
        self.directory = Path(directory); self.interval = min(30, float(interval))
        self.filename = filename
        self.progress = Progress('generation', interval=self.interval)
        self.fields = {'source': source_id, 'phase': 'initialization', 'attempt': 'normal'}
        self.lock = threading.Lock(); self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self): self._emit(); self.thread.start(); return self
    def __exit__(self, *exc): self.stop.set(); self.thread.join(timeout=1)
    def update(self, **fields):
        with self.lock: self.fields.update(fields)
        self.progress.update(**fields)

    def _emit(self):
        with self.lock: fields = dict(self.fields)
        durable_write(self.directory/self.filename, {**fields, 'unix_seconds': time.time()})
        self.progress.update(**fields)

    def _run(self):
        while not self.stop.wait(self.interval): self._emit()


def initialization_failure(source, directory, reason, *, transform=None):
    meta = original_initialization_failure(source, directory, reason, teacher_policy=TEACHER_V2)
    folder = Path(directory)/'normal_vnormal_a0'
    extra = {'generator_algorithm': ALGORITHM,
             'initialization_transform': transform or {'kind': 'pending', 'timing': 'before_normal_first_capture'}}
    extra['recipe'] = {'version': RECIPE_VERSION, **deepcopy(extra)}
    extra['generation_context'] = generation_context(None)
    extra['generation_context']['initialization_transform'] = deepcopy(extra['initialization_transform'])
    meta.update(extra)
    lineage = read_json(folder/'lineage.json'); lineage.update(extra)
    durable_write(folder/'lineage.json', lineage); durable_write(folder/'metadata.json', meta)
    return meta


class CoverageAttempt(Attempt):
    """035 transition recorder with039 closure and initialization provenance."""
    def __init__(self, *args, initialization_transform=None, heartbeat=None, context=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.teacher_policy != TEACHER_V2: raise ValueError('039 requires accepted teacher V2 admission')
        self.recipe = recipe_for(self.config)
        self.initialization_transform = deepcopy(initialization_transform)
        self.heartbeat = heartbeat
        self.closure_summary = None
        self.context = context if context is not None else HashContext()

    def journal(self, event, **values):
        self.folder.mkdir(parents=True, exist_ok=True)
        with (self.folder/'journal.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'event': event, **values}, default=_json, allow_nan=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())

    def begin(self, state):
        self.persist({'qualified': False, 'failure_reason': 'attempt_interrupted_before_finalization'})
        self.journal('initial_state_requested', state=state, rewind=self.rewind,
                     initialization_transform=self.initialization_transform)
        self.session.restore(np.asarray(state).copy())
        self.frames.append(self.session.capture())
        self.journal('initial_observation', frame={k: v for k, v in self.frames[0].items() if k != 'observation'})
        if self.domain == 'normal':
            from .permutation import validate_initial
            validate_initial(self.frames[0], self.source, self.initialization_transform)
        elif not safe_handoff(self.frames[0]):
            raise ValueError('invalid_rewound_initial_state')
        if self.domain == '10':
            from egrs.trajectory_augmentation.generation import _guard
            _guard(self.frames[0], 'bridge')

    def step(self, raw, phase, reference=None, *, audit_only=False):
        if audit_only: raise ValueError('039 closure observations must be supervised transitions')
        if self.heartbeat:
            self.heartbeat.update(attempt=f'{self.domain}/v{self.variant}/a{self.number}',
                                  phase=phase, controls=len(self.steps))
        return super().step(raw, phase, reference, audit_only=False)

    def finish(self):
        from .teacher import finish_attempt
        return finish_attempt(self)

    def persist(self, qualification):
        self.recipe['initialization_transform'] = deepcopy(self.initialization_transform)
        meta = super().persist(qualification, context=self.context)
        extra = {'generator_algorithm': ALGORITHM, 'initialization_transform': deepcopy(self.initialization_transform),
                 'closure_summary': deepcopy(self.closure_summary)}
        extra['generation_context'] = generation_context(self.config.get('_plan_identity'))
        extra['generation_context']['initialization_transform'] = deepcopy(self.initialization_transform)
        meta.update(extra)
        lineage_path = self.directory/meta['lineage_path']
        lineage = read_json(lineage_path); lineage.update(extra, recipe=deepcopy(self.recipe))
        durable_write(lineage_path, lineage); durable_write(self.folder/'metadata.json', meta)
        return meta


def _finish(attempt):
    try: return attempt.finish()
    except Exception as error:
        attempt.error = f'{type(error).__name__}: {error}'
        return attempt.persist({'qualified': False, 'failure_reason': attempt.error})


def _generate_session(session, source, config, output_dir, ledger, heartbeat, context):
    from .permutation import prepare_initial
    result = {'source_id': source['source_id'], 'attempts': [], 'gaps': [], 'error': None,
              'generator_algorithm': ALGORITHM}
    recipe = recipe_for(config)
    normal = CoverageAttempt(session, source, config, output_dir, 'normal', 'normal', 0,
                             heartbeat=heartbeat, context=context)
    try:
        state, evidence = prepare_initial(session, source)
        normal.initialization_transform = deepcopy(evidence)
        # Evidence and requested transformed state are durable before restore/capture.
        durable_write(Path(output_dir)/'initialization_transform.json', evidence)
        normal.begin(state)
        for action in session.source_actions: normal.step(action, 'source_replay')
    except Exception as error: normal.error = f'{type(error).__name__}: {error}'
    normal_meta = _finish(normal); result['attempts'].append(normal_meta)
    result['initialization_transform'] = deepcopy(normal.initialization_transform)
    if not normal_meta['qualified']:
        result['gaps'].append('normal_replay_unqualified'); return result
    eligible = [i for i, frame in enumerate(normal.frames[:-1]) if safe_handoff(frame)]
    if not eligible:
        result['gaps'].append('no_safe_handoff'); return result
    index = min(eligible, key=lambda i: (float(np.linalg.norm(normal.frames[i]['position']-normal.frames[0]['position'])), i))
    handoff = normal.frames[index]; target = handoff['position'], handoff['rotation']
    rng = np.random.default_rng(7); joints = len(session.layout['arm_qpos'])
    perturbations = [np.zeros(joints)]+[rng.uniform(-recipe['joint_perturbation_rad'],
        recipe['joint_perturbation_rad'], joints) for _ in range(2)]
    # Robot rewind uses the transformed normal initial state as its nominal
    # robot reference. All nonrobot coordinates remain those of the new handoff.
    nominal = normal.frames[0]['state']
    for variant, delta in enumerate(perturbations):
        for number in (0, 1):
            ledger.reserve(source['source_id'], '10', variant, number)
            current = CoverageAttempt(session, source, config, output_dir, '10', variant, number,
                initialization_transform=normal.initialization_transform, heartbeat=heartbeat, context=context)
            current.handoff = {'normal_state_index': index,
                'selection': 'nearest nominal initial controlled site; earliest tie',
                'reference': 'new039_normal_recorded_state'}
            # A reserved initialization slot gets metadata even if rewind fails.
            current.persist({'qualified': False, 'failure_reason': 'attempt_interrupted_before_initialization'})
            try:
                state, current.rewind = rewind_state(handoff['state'], nominal, session.layout, delta)
                current.begin(state); current.bridge(target, lift=number == 1)
                for reference in normal.targets[index:]:
                    current.track((np.asarray(reference['position']), np.asarray(reference['rotation'])),
                                  reference['gripper'], 'continuation')
            except Exception as error: current.error = f'{type(error).__name__}: {error}'
            meta = _finish(current); result['attempts'].append(meta)
            if meta['qualified']: break
    if not any(a['qualified'] and a['domain'] == '10' for a in result['attempts']):
        result['gaps'].append('no_qualified_10')
    return result


def generate_session(session, source, config, output_dir, *, context=None):
    """The native session is the sole fake boundary; execute no model here."""
    config = deepcopy(config); config['teacher_policy'] = TEACHER_V2
    directory = Path(output_dir); directory.mkdir(parents=True, exist_ok=True)
    ledger = AttemptLedger(config.get('_budget_ledger', directory/'attempt_ledger.json'))
    if config.get('_normal_pre_reserved'):
        if not ledger.contains(source['source_id'], 'normal', 'normal', 0):
            raise ValueError('parent normal reservation missing before worker initialization')
    else: ledger.reserve(source['source_id'], 'normal', 'normal', 0)
    initialization_failure(source, directory, 'native_initialization_interrupted')
    with Heartbeat(directory, source['source_id']) as heartbeat:
        result = _generate_session(session, source, config, directory, ledger, heartbeat,
                                   context if context is not None else HashContext())
    result['attempts'] = reconcile_attempts(source, directory, ledger,
                                           'attempt_interrupted_before_metadata_persist')
    return result


def _slot_key(row):
    domain, variant, number = row.get('domain'), row.get('variant'), row.get('attempt')
    if not ((domain == 'normal' and variant == 'normal' and number == 0) or
            (domain == '10' and type(variant) is int and variant in range(3)
             and type(number) is int and number in range(2))):
        raise ValueError('foreign or invalid039 metadata attempt slot')
    return domain, variant, number


def _missing_slot(source, directory, slot, reason):
    domain, variant, number = _slot_key(slot)
    folder = Path(directory)/f'{domain}_v{variant}_a{number}'; folder.mkdir(parents=True, exist_ok=True)
    evidence_path = Path(directory)/'initialization_transform.json'
    transform = read_json(evidence_path) if evidence_path.exists() else {'kind': 'unavailable_after_interruption'}
    qualification = {'accepted': False, 'qualified': False, 'failure_reason': reason,
                     'teacher_policy': TEACHER_V2, 'diagnostic_events': []}
    prefix = 'recovery_'  # Preserve any orphaned original audit/HDF/qualification bytes.
    mapping = deepcopy(source['mapping']); mapping.update(observation_offset=0, action_offset=0)
    context_record = generation_context(None); context_record['initialization_transform'] = transform
    row = {'source_id': f"{source['source_id']}__{domain}__v{variant}__a{number}",
        'parent_demo_id': source['parent_demo_id'], 'task_key': source['task_key'], 'split': source['split'],
        'domain': domain, 'variant': variant, 'attempt': number, 'qualified': False, 'status': 'rejected',
        'failure_reason': reason, 'qualification': qualification, 'teacher_policy': TEACHER_V2,
        'provenance': 'ordinary_reexecuted' if domain == 'normal' else 'counterfactual_generated_from_demo',
        'file': None, 'episode': 'data/demo_0', 'length': 0, 'attempt_steps': 0,
        'mapping': mapping, 'instruction': source['instruction'], 'parent_file_sha256': source['file_sha256'],
        'generator_algorithm': ALGORITHM, 'initialization_transform': transform,
        'recipe': {'version': RECIPE_VERSION, 'generator_algorithm': ALGORITHM, 'initialization_transform': transform},
        'generation_context': context_record, 'recovered_from_spent_slot': True,
        'recovery_basis': 'durable reservation exists; no final metadata was published; outcome remains rejected',
        'audit_path': f'{folder.name}/{prefix}audit.json',
        'qualification_path': f'{folder.name}/{prefix}qualification.json',
        'lineage_path': f'{folder.name}/{prefix}lineage.json'}
    durable_write(folder/(prefix+'audit.json'), {'steps': [], 'frames': [], 'error': reason,
        'spent_slot': slot, 'orphaned_artifacts_preserved': sorted(p.name for p in folder.iterdir() if p.is_file())})
    durable_write(folder/(prefix+'qualification.json'), qualification)
    durable_write(folder/(prefix+'lineage.json'), {'source': source, 'spent_slot': slot,
        'generator_algorithm': ALGORITHM, 'teacher_policy': TEACHER_V2,
        'initialization_transform': transform, 'generation_context': context_record,
        'recipe': row['recipe'], 'recovery_basis': row['recovery_basis']})
    durable_write(folder/'metadata.json', row)
    return row


def reconcile_attempts(source, directory, ledger, reason):
    """Every spent slot has exactly one outcome; missing outcomes stay rejected."""
    slots = [slot for slot in ledger.read()['slots'] if slot['source_id'] == source['source_id']]
    expected = {_slot_key(slot): slot for slot in slots}
    if not expected: raise ValueError('unreserved039 source has no durable ordinary attempt')
    found = {}
    for path in sorted(Path(directory).glob('*/metadata.json')):
        row = read_json(path); key = _slot_key(row)
        if (key not in expected or row.get('parent_demo_id') != source['parent_demo_id']
                or row.get('source_id') != f"{source['source_id']}__{key[0]}__v{key[1]}__a{key[2]}"
                or any(row.get(k) != source[k] for k in ('task_key', 'split'))
                or row.get('parent_file_sha256') != source['file_sha256']):
            raise ValueError('foreign or unreserved039 metadata attempt')
        if key in found: raise ValueError('duplicate039 metadata attempt slot')
        found[key] = row
    return [found.get(_slot_key(slot)) or _missing_slot(source, directory, slot, reason) for slot in slots]


def _recover_source(source, directory, reason, ledger=None):
    directory = Path(directory)
    if ledger is None:
        request_path = directory/'request.json'
        ledger_path = read_json(request_path).get('config', {}).get('_budget_ledger') if request_path.exists() else None
        ledger = AttemptLedger(ledger_path or directory/'attempt_ledger.json')
    attempts = reconcile_attempts(source, directory, ledger, reason)
    if any(row.get('failure_reason') == 'native_initialization_interrupted' for row in attempts):
        initialization_failure(source, directory, reason)
        attempts = reconcile_attempts(source, directory, ledger, reason)
    return {'source_id': source['source_id'], 'attempts': attempts,
            'error': reason, 'gaps': ['native_initialization_or_execution_failure'],
            'generator_algorithm': ALGORITHM}


def generate_source(source, config, data_root, output_dir):
    """Launch the chosen interpreter verbatim; never resolve its venv symlink."""
    directory = Path(output_dir).resolve(); directory.mkdir(parents=True, exist_ok=True)
    config = deepcopy(config); config['teacher_policy'] = TEACHER_V2
    ledger = AttemptLedger(config.get('_budget_ledger', directory/'attempt_ledger.json'))
    if not config.get('_normal_pre_reserved'):
        ledger.reserve(source['source_id'], 'normal', 'normal', 0)
    elif not ledger.contains(source['source_id'], 'normal', 'normal', 0):
        raise ValueError('parent normal reservation missing')
    config.update(_budget_ledger=str(ledger.path.resolve()), _normal_pre_reserved=True)
    initialization_failure(source, directory, 'native_initialization_interrupted')
    request = directory/'request.json'; response = directory/'result.json'
    durable_write(request, {'source': source, 'config': config, 'data_root': str(Path(data_root).resolve()),
                            'output_dir': str(directory)})
    backend = config['native_backend']; python = backend.get('python', sys.executable)
    command = [python, '-m', 'egrs.coverage039.native', '--request', str(request)]
    timeout = backend.get('source_timeout_seconds', 7200)
    if type(timeout) not in (int, float) or not 1 <= timeout <= 86400:
        raise ValueError('source timeout must be1..86400 seconds')
    progress = Progress('generation_worker'); started = time.monotonic(); process = None
    try:
        with (directory/'worker.stdout.log').open('wb') as out, (directory/'worker.stderr.log').open('wb') as err:
            process = subprocess.Popen(command, cwd=str(Path(__file__).resolve().parents[2]), stdout=out, stderr=err)
            while True:
                fields = {'source': source['source_id'], 'attempt': 'native_initialization',
                          'elapsed_source_seconds': round(time.monotonic()-started, 3)}
                if (directory/'heartbeat.json').exists():
                    fields.update(read_json(directory/'heartbeat.json'))
                progress.update(**fields)
                remaining = timeout-(time.monotonic()-started)
                if remaining <= 0: raise subprocess.TimeoutExpired(command, timeout)
                try:
                    code = process.wait(timeout=min(30, remaining))
                    if code != 0: raise RuntimeError('native worker exited '+str(code))
                    return read_json(response)
                except subprocess.TimeoutExpired:
                    if time.monotonic()-started >= timeout: raise
    except Exception as error:
        if process is not None and process.poll() is None:
            process.kill(); process.wait()
        result = _recover_source(source, directory, f'{type(error).__name__}: {error}', ledger)
        durable_write(response, result); return result


def _safe_output(output, plan):
    output = Path(output).expanduser().resolve()
    protected = [plan['data_root'], plan['config']['old003_export'], plan['config']['old_retention_index']]
    protected.extend(plan.get('old_dependencies', {}).get('data_roots', {}).values())
    for value in protected:
        root = Path(value).resolve()
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise ValueError('new039 output must not overlap any original input or old data root')
    return output


def _relative_attempt(attempt, directory, output):
    row = deepcopy(attempt)
    for key in ('file', 'audit', 'video', 'qualification_file', 'audit_path', 'lineage_path',
                'qualification_path', 'journal_path'):
        if isinstance(row.get(key), str):
            child = (directory/row[key]).resolve()
            if not child.is_relative_to(directory.resolve()): raise ValueError('attempt artifact escapes source directory')
            row[key] = child.relative_to(output).as_posix()
    return row


def generate(config_path, out, *, source_generator=None, context=None):
    """Generate only new039 attempts; old221/75 are reused by the merge stage."""
    context = context if context is not None else HashContext()
    if Path(out).exists(): raise FileExistsError('new039 generation output required')
    plan = build_plan(config_path, context=context); output = _safe_output(out, plan)
    cfg = plan['execution_config']; context.verify(cfg['stats_path'], cfg['stats_sha256'])
    source_generator = source_generator or generate_source
    output.mkdir(parents=True); durable_write(output/'generation_plan.json', plan)
    ledger = AttemptLedger(output/'attempt_ledger.json')
    reports = []; attempts = []; errors = 0; progress = Progress('generation_sources')
    for index, source in enumerate(plan['sources']):
        directory = output/'artifacts'/f'source-{index:03d}'; directory.mkdir(parents=True)
        source_cfg = deepcopy(cfg); source_cfg.update(save_video=source['demo_index'] == 0,
            _budget_ledger=str(ledger.path), _normal_pre_reserved=True, _plan_identity=plan['identity'])
        # This is the parent process denominator, flushed before child creation.
        ledger.reserve(source['source_id'], 'normal', 'normal', 0)
        initialization_failure(source, directory, 'native_initialization_interrupted')
        progress.update(source=source['source_id'], completed=index, total=60, phase='starting_source')
        try:
            with Heartbeat(directory, source['source_id'], filename='parent_heartbeat.json'):
                result = source_generator(deepcopy(source), source_cfg, Path(plan['data_root']), directory)
            if result.get('source_id') != source['source_id'] or not isinstance(result.get('attempts'), list):
                raise ValueError('generator source/attempt contract differs')
            if result.get('error'): errors += 1
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            errors += 1; result = _recover_source(source, directory, f'{type(error).__name__}: {error}', ledger)
        # A child may fail before touching its initial placeholder; still retain
        # the spent ordinary attempt, rather than silently dropping its denominator.
        if not result['attempts']:
            result = _recover_source(source, directory, result.get('error') or 'source_returned_no_attempts', ledger)
        result['attempts'] = reconcile_attempts(source, directory, ledger,
                                               'attempt_interrupted_before_metadata_persist')
        attempts.extend(_relative_attempt(row, directory, output) for row in result['attempts'])
        reports.append(result); durable_write(directory/'source_report.json', result)
        durable_write(output/'generation_progress.json', {'plan_identity': plan['identity'],
            'processed_sources': len(reports), 'planned_sources': 60,
            'completion_percent': 100*len(reports)/60, 'spent': ledger.read()})
        progress.update(source=source['source_id'], completed=len(reports), total=60, phase='source_completed')
    # Reconcile once more immediately before export so its failure denominator
    # is exactly the durable spent slots, including a worker lost before persist.
    attempts = []
    for index, source in enumerate(plan['sources']):
        directory = output/'artifacts'/f'source-{index:03d}'
        reconciled = reconcile_attempts(source, directory, ledger, 'attempt_interrupted_before_export')
        reports[index]['attempts'] = reconciled
        attempts.extend(_relative_attempt(row, directory, output) for row in reconciled)
    spent = ledger.read(); context_record = generation_context(plan['identity'],
        normal_attempts=spent['normal_attempts'], ten_attempts=spent['ten_attempts'])
    # The complete180 parent list intentionally keeps the original raw file and
    # SHA. Generated HDF files live under this new run's own explicit data root.
    data = export_generated(plan['parents'], attempts, output, output/'export',
                            generation_context=context_record, context=context)
    manifest = read_json(output/'export/sources.json')
    train_ten = sum(s['domain'] == '10' and s['split'] == 'train' for s in manifest['sources'].values())
    coverage = {}
    for source in plan['sources']:
        for domain in ('normal', '10'):
            key = '|'.join((source['task_key'], source['split'], domain))
            coverage.setdefault(key, {'attempts': 0, 'qualified': 0, 'windows': 0,
                'valid_actions': 0, 'new_qualified': 0, 'reused_qualified': 0, 'failure_reasons': {}})
    for row in attempts:
        key = '|'.join((row['task_key'], row['split'], row['domain']))
        bucket = coverage[key]; bucket['attempts'] += 1
        bucket['qualified'] += int(row['qualified']); bucket['new_qualified'] += int(row['qualified'])
        if not row['qualified']:
            reason = row['failure_reason']
            bucket['failure_reasons'][reason] = bucket['failure_reasons'].get(reason, 0)+1
    for key, bucket in coverage.items():
        detail = data['task_split_domain'].get(key, {})
        bucket.update(windows=detail.get('windows', 0), valid_actions=detail.get('valid_actions', 0))
    result = {'format': 'task039-generation-report-v1', 'plan_identity': plan['identity'],
        'population': plan['population'], 'source_reports': reports, 'source_errors': errors,
        'data': data, 'export': str(output/'export'), 'generation_context': context_record,
        'actual_qualified_10': data['counts_by_domain']['10']['trajectories'],
        'actual_qualified_normal': data['counts_by_domain']['normal']['trajectories'],
        'actual_new_train_10': train_ten, 'spent': spent, 'coverage_by_task_split_domain': coverage,
        'status': 'completed_with_source_gaps' if errors or data['failed_attempts'] else 'completed',
        'processed_sources': len(reports), 'completion_percent': 100., 'model_loaded': False}
    result['identity'] = identity(result); durable_write(output/'generation_report.json', result)
    progress.finish(completed=60, total=60)
    return result
