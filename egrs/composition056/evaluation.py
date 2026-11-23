"""Evaluate Base/H0/H1 on the frozen055 sources with the original binary score."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid

from egrs.composition055.contracts import _path, digest, read, sha, write
from .catalog import (ADAPTER_SHA256, BANK_SHA256, MODEL_ORDER, PREPARATION_IDENTITY,
                      PROTOCOL_VERSION, TASK_SUITE)
from .source import adapt, archive, make_environment, validate_archive

SCHEMA = 'task056-composition-eval-v1'
RUN_SCHEMA = 'task056-composition-source-run-v1'
FIELDS = {'schema_version', 'source_bank', 'base_runtime', 'adapter_h0', 'adapter_h1', 'protected_roots'}


def load_config(path):
    path = Path(path).resolve()
    cfg = read(path)
    if (not isinstance(cfg, dict) or set(cfg) != FIELDS or cfg['schema_version'] != SCHEMA
            or not isinstance(cfg['protected_roots'], list) or not cfg['protected_roots']):
        raise ValueError('Exact056 evaluation configuration required')
    for key in FIELDS - {'schema_version', 'protected_roots'}:
        cfg[key] = _path(cfg[key], path.parent)
    cfg['protected_roots'] = list(dict.fromkeys(_path(p, path.parent) for p in cfg['protected_roots']))
    return cfg


def implementation_identity():
    root = Path(__file__).parent
    return {'schema_version': SCHEMA, 'files': {p.name: sha(p) for p in sorted(root.glob('*.py'))}}


def protect(cfg, output, config_path):
    target = Path(output).expanduser().resolve()
    if target.exists():
        raise FileExistsError('056 evaluation requires a fresh output')
    roots = [Path(cfg['source_bank']), Path(cfg['base_runtime']),
             Path(cfg['adapter_h0']), Path(cfg['adapter_h1']),
             Path(__file__).resolve().parents[2], Path(config_path).resolve(),
             *[Path(p) for p in cfg['protected_roots']]]
    if any(target == p or p in target.parents or target in p.parents for p in roots):
        raise ValueError('056 output overlaps protected bank, model, code or old results')
    return target


def adapter_identity(directory, model):
    from egrs.hint043.adapter import read_adapter_identity
    from egrs.hint043.evaluation import validate_final

    value = read_adapter_identity(directory)
    validate_final(value, 3000)
    if value['arm'] != model or value['adapter_sha256'] != ADAPTER_SHA256[model]:
        raise ValueError(f'056 requires the frozen045 {model}@3000 adapter')
    return value


def plan(cfg, model):
    if model not in MODEL_ORDER:
        raise ValueError('056 model must be base, h0 or h1')
    from egrs.composition055.preparation import read_bank

    bank_path = Path(cfg['source_bank']).resolve()
    bank = read_bank(bank_path)
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    if not bank['complete'] or bank['ready'] != 150 or bank['failed'] or sha(bank_path / 'sources.json') != BANK_SHA256:
        raise ValueError('056 requires the complete immutable055 150-source bank')
    if bank['preparation_identity'] != PREPARATION_IDENTITY:
        raise ValueError('056 source preparation identity differs')
    sources = [adapt(row['source_manifest'], row) for row in bank['rows']]
    runtime = load_runtime(cfg['base_runtime'])
    identity = None if model == 'base' else adapter_identity(cfg['adapter_' + model], model)
    value = {
        'schema_version': SCHEMA,
        'config': cfg,
        'source_config': bank['snapshot']['config'],
        'model': model,
        'runtime': runtime,
        'method_adapter': None if model == 'base' else cfg['adapter_' + model],
        'adapter_identity': identity,
        'expected': [deepcopy(source['episodes'][0]) for source in sources],
        'sources': sources,
        'source_bank_sha256': BANK_SHA256,
        'preparation_identity': PREPARATION_IDENTITY,
        'evaluation_scope': 'task056-three-model-composition150',
        'implementation': implementation_identity(),
        'source_generation': 0,
        'ordinary_episodes': 0,
        'training': False,
    }
    value['plan_sha256'] = digest(value)
    return value


def worker(frozen):
    cfg = deepcopy(frozen['runtime'])
    model = frozen['model']
    if model != 'base':
        cfg.update(policy_factory='egrs.hint043.policy:make_policy',
                   method_adapter=frozen['method_adapter'], hint043_arm=model,
                   hint043_checkpoint_step=3000)
    return cfg


def verify_model(frozen, provenance):
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata

    validate_policy_metadata(frozen['runtime'], provenance['policy_metadata'])
    if provenance['policy_metadata'].get('method_adapter') != frozen['adapter_identity']:
        raise ValueError('056 loaded model/adapter identity differs from frozen plan')


def execute_episode(folder, source, frozen, policy):
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.runner import run_episode
    from benchmark.remaining_goals.headless.evidence import HeadlessEvidence

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    archived = archive(folder, source)
    episode = source['episodes'][0]
    metadata = {
        'schema_version': RUN_SCHEMA,
        'protocol_version': PROTOCOL_VERSION,
        'run_id': uuid.uuid4().hex,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'batch_identity_sha256': frozen['plan_sha256'],
        'source_plan': source,
        'runtime_config': frozen['runtime'],
        'model_runtime': deepcopy(policy.provenance),
        'status': 'running', 'phase': 'initialization', 'error': None,
        'cleanup_errors': [], 'attempts': [episode['episode_id']], 'results': [],
        'missing': [episode['episode_id']],
    }
    write(folder / 'task_run.json', metadata)
    verify_model(frozen, policy.provenance)
    env = recorder = None
    result = None
    try:
        env, registration = make_environment(source, archived)
        write(folder / 'environment.json', {
            'actual_environment': env.identity,
            'composition_registration': registration,
        })
        identity = workflow.evidence_identity(metadata, episode)
        recorder = workflow.make_recorder(folder / 'videos' / (episode['episode_id'] + '.mp4'), episode)
        evidence = HeadlessEvidence(folder / 'evidence' / episode['episode_id'], identity)
        metadata['phase'] = 'rollout'
        write(folder / 'task_run.json', metadata)
        result = run_episode(env, policy, episode, horizon=520, confirmation_steps=4,
                             max_chunk_steps=8, recorder=recorder, evidence=evidence, identity=identity)
        if result.get('video', {}).get('status') == 'saved':
            path = 'videos/' + episode['episode_id'] + '.mp4'
            result['video'].update(path=path, sha256=sha(folder / path))
        raw_path = folder / 'raw' / (episode['episode_id'] + '.json')
        write(raw_path, result)
        metadata.update(phase='verification', missing=[], results=[{
            'episode_id': episode['episode_id'],
            'path': raw_path.relative_to(folder).as_posix(),
            'sha256': sha(raw_path),
        }])
        if result.get('interrupted') or result.get('status') != 'completed':
            raise RuntimeError('056 technical pause: ' + str(result.get('error', result.get('status'))))
        metadata.update(status='completed', phase='complete')
    except BaseException as error:
        metadata.update(status='technical_pause', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        for item in (env, recorder if result is None else None):
            if item is not None:
                try:
                    item.close()
                except BaseException as error:
                    metadata['cleanup_errors'].append(f'{type(error).__name__}: {error}')
                    metadata['status'] = 'technical_pause'
        write(folder / 'task_run.json', metadata)
    return verify_episode(folder, source, frozen)


def verify_episode(folder, source, frozen):
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.schema import validate_protocol_result
    from benchmark.remaining_goals.headless.evidence import validate_evidence
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result

    folder = Path(folder)
    metadata = read(folder / 'task_run.json')
    episode = source['episodes'][0]
    if (metadata.get('schema_version') != RUN_SCHEMA
            or metadata.get('status') != 'completed' or metadata.get('cleanup_errors')
            or metadata['source_plan'] != source or metadata['batch_identity_sha256'] != frozen['plan_sha256']
            or metadata['runtime_config'] != frozen['runtime'] or metadata['missing']
            or metadata['attempts'] != [episode['episode_id']] or len(metadata['results']) != 1):
        raise ValueError('Incomplete/mismatched056 episode cannot be scored')
    verify_model(frozen, metadata['model_runtime'])
    row = next(row for row in frozen['source_config_population'] if row['episode_id'] == episode['episode_id'])
    verified = validate_archive(folder, source, row, frozen['source_config'])
    if verified['episode_id'] != episode['episode_id']:
        raise ValueError('056 archived source episode differs')
    if read(folder / 'environment.json')['actual_environment'] != source['environment_config']['environment']:
        raise ValueError('056 actual bridge environment differs')
    reference = metadata['results'][0]
    path = workflow._contained(folder, reference['path'])
    if sha(path) != reference['sha256']:
        raise ValueError('056 raw bytes changed')
    raw = read(path)
    identity = workflow.evidence_identity(metadata, episode)
    validate_protocol_result(raw, episode, identity)
    if raw.get('model_identity') != workflow._model_identity(metadata):
        raise ValueError('056 raw loaded model identity differs')
    checked = validate_evidence(folder, raw, episode, identity)
    if checked.get('verified') is False or raw['status'] != 'completed':
        raise ValueError('056 incomplete evidence cannot become a policy failure')
    video = raw['video']
    if video['status'] != 'saved' or sha(workflow._contained(folder, video['path'])) != video['sha256']:
        raise ValueError('056 requires full video for each completed episode')
    return score_verified_result(episode, raw, condition='10', source={
        'model_identity': workflow._model_identity(metadata),
        'original_protocol': metadata['protocol_version'],
        'input_evidence_level': 'verified_raw_execution_video_and_source_archive',
        'run_path': str(folder),
        'verified_files': [
            {'path': str(folder / 'task_run.json'), 'sha256': sha(folder / 'task_run.json')},
            {'path': str(path), 'sha256': reference['sha256']},
        ],
        'new_execution': True,
    })


class Live:
    def __init__(self, output, model, population):
        self.output, self.model = Path(output), model
        self.population = population
        self.records, self.outcomes = {}, {}
        self.started = time.monotonic()

    def add(self, episode, record):
        from libero_remain_reporting import map_verified_results

        name = episode['episode_id']
        if name in self.records:
            raise ValueError('Duplicate056 completed episode')
        single = map_verified_results([episode], {name: record})
        if single['integrity_errors'] or single['counts']['completed'] != 1:
            raise ValueError('056 live scoring failed original binary mapper')
        self.records[name] = record
        self.outcomes[name] = single['episodes'][0]['success']
        n, successes = len(self.outcomes), sum(self.outcomes.values())
        task = episode['task_id']
        task_names = [e['episode_id'] for e in self.population
                      if e['task_id'] == task and e['episode_id'] in self.outcomes]
        task_successes = sum(self.outcomes[key] for key in task_names)
        value = {
            'schema_version': SCHEMA, 'phase': 'evaluation', 'model': self.model,
            'completed': n, 'expected': 150, 'percent': 100 * n / 150,
            'successes': successes, 'live_compliant_SR_percent': 100 * successes / n,
            'task_id': task, 'task_completed': len(task_names),
            'task_successes': task_successes,
            'task_SR_percent': 100 * task_successes / len(task_names),
            'episode_id': name, 'episode_success': self.outcomes[name],
            'elapsed_seconds': time.monotonic() - self.started,
        }
        write(self.output / 'progress.json', value)
        print(f"[056][{self.model}] completed={n}/150 ({value['percent']:.2f}%) "
              f"task={task} ep={episode['initial_state_index'] + 1}/50 "
              f"result={'SUCCESS' if self.outcomes[name] else 'FAILURE'} "
              f"task_SR={value['task_SR_percent']:.2f}% ({task_successes}/{len(task_names)}) "
              f"overall_SR={value['live_compliant_SR_percent']:.2f}% ({successes}/{n})", flush=True)


def run(config_path, output, model):
    cfg = load_config(config_path)
    output = protect(cfg, output, config_path)
    frozen = plan(cfg, model)
    frozen['source_config_population'] = read(Path(cfg['source_bank']) / 'sources.json')['rows']
    output.mkdir(parents=True)
    write(output / 'plan.json', frozen)
    live = Live(output, model, frozen['expected'])
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    from libero_remain_reporting import map_verified_results, render_report

    policy = None
    errors = []
    try:
        policy = SubprocessPolicy(worker(frozen))
        verify_model(frozen, policy.provenance)
        for source in frozen['sources']:
            episode = source['episodes'][0]
            folder = output / 'episodes' / episode['episode_id']
            record = execute_episode(folder, source, frozen, policy)
            live.add(episode, record)
    except BaseException as error:
        errors.append({'phase': 'execution', 'error': f'{type(error).__name__}: {error}'})
        raise
    finally:
        if policy is not None:
            try:
                policy.close()
            except BaseException as error:
                errors.append({'phase': 'cleanup', 'error': f'{type(error).__name__}: {error}'})
        report = map_verified_results(frozen['expected'], live.records, artifact_issues=errors)
        report.update(schema_version=SCHEMA, model=model,
                      source_bank_sha256=frozen['source_bank_sha256'],
                      preparation_identity=frozen['preparation_identity'],
                      evaluation_scope=frozen['evaluation_scope'],
                      ordinary_episodes=0, source_generation=0,
                      software_exit='success' if report['counts']['formal_SR'] else 'incomplete',
                      execution_errors=errors, plan_sha256=frozen['plan_sha256'])
        if report['counts']['successes'] != sum(live.outcomes.values()):
            raise ValueError('056 live/final scoring discrepancy; preserve run for inspection')
        write(output / 'summary.json', report)
        (output / 'report.md').write_text(render_report(report), encoding='utf-8')
    if not report['counts']['formal_SR']:
        raise RuntimeError('056 not formally complete; next model is not started')
    print(f"[056][{model}] COMPLETE compliant_SR={report['counts']['formal_SR']['percent']:.2f}%", flush=True)
    return report


def _paired(left, right, *, native=False):
    def success(row):
        if native:
            return bool(row['diagnostics']['primary']['official_goals_achieved'])
        return row['success']

    both = gains = losses = neither = 0
    for a, b in zip(left, right):
        x, y = success(a), success(b)
        both += x and y
        gains += not x and y
        losses += x and not y
        neither += not x and not y
    return {'both_success': both, 'gains': gains, 'losses': losses,
            'both_unsuccessful': neither, 'net_successes': gains - losses,
            'delta_pp': 100 * (gains - losses) / len(left)}


def compare(base_path, h0_path, h1_path, output):
    paths = {'base': Path(base_path), 'h0': Path(h0_path), 'h1': Path(h1_path)}
    reports = {name: read(path / 'summary.json') for name, path in paths.items()}
    for name, report in reports.items():
        if (report.get('schema_version') != SCHEMA or report['model'] != name
                or report['source_bank_sha256'] != BANK_SHA256
                or report['preparation_identity'] != PREPARATION_IDENTITY
                or report['counts']['completed'] != 150 or not report['counts']['formal_SR']
                or report['integrity_errors'] or report['execution_errors']):
            raise ValueError(f'056 requires a complete verified {name} report')
    populations = [[row['episode_id'] for row in report['episodes']] for report in reports.values()]
    if any(rows != populations[0] for rows in populations[1:]):
        raise ValueError('056 three-model population/order differs')
    rows = {name: report['episodes'] for name, report in reports.items()}
    pair_specs = (('base', 'h0', 'base_to_h0'), ('h0', 'h1', 'h0_to_h1'), ('base', 'h1', 'base_to_h1'))
    paired = {key: _paired(rows[left], rows[right]) for left, right, key in pair_specs}
    native = {key: _paired(rows[left], rows[right], native=True) for left, right, key in pair_specs}
    task_ids = list(dict.fromkeys(row['task_id'] for row in rows['base']))
    tasks = []
    for task in task_ids:
        group = {name: [row for row in values if row['task_id'] == task] for name, values in rows.items()}
        entry = {'task_id': task}
        for name, report in reports.items():
            summary = next(item for item in report['tasks'] if item['task_id'] == task)
            entry[name] = summary['formal_SR']
        entry['paired'] = {key: _paired(group[left], group[right]) for left, right, key in pair_specs}
        tasks.append(entry)
    diagnostics = {}
    for name, values in rows.items():
        failure, unknown = Counter(), Counter()
        native_success = 0
        for row in values:
            primary = row['diagnostics']['primary']
            failure.update(primary.get('failure_reasons', []))
            unknown.update(primary.get('unknown_reasons', []))
            native_success += bool(primary.get('official_goals_achieved'))
        diagnostics[name] = {
            'native_full_goal_attainment': {'successes': native_success, 'total': 150,
                                            'percent': 100 * native_success / 150},
            'failure_reasons_overlapping': dict(sorted(failure.items())),
            'unknown_reasons_overlapping': dict(sorted(unknown.items())),
        }
    value = {
        'schema_version': 'task056-three-model-comparison-v1',
        'source_bank_sha256': BANK_SHA256,
        'preparation_identity': PREPARATION_IDENTITY,
        'rates': {name: report['counts']['formal_SR'] for name, report in reports.items()},
        'paired': paired,
        'native_goal_paired': native,
        'tasks': tasks,
        'diagnostics': diagnostics,
        'verification': {
            'all_reports_complete': True,
            'all_episode_identities_paired': True,
            'ordinary_episodes': 0,
            'source_generation': 0,
            'reported_only_no_new_model_physics_or_scoring': True,
        },
    }
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('056 comparison output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, value)
    return value
