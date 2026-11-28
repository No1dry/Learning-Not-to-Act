"""Task057 counterfactual probe: evaluate Base only on the fixed 60 probe sources.

This is a capability probe, not a method result. It reuses the original headless
rollout, evidence chain and binary score; no training data is produced here.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid

from .contracts import _path, digest, read, sha, write
from .catalog import MODEL_ORDER, PROTOCOL_VERSION, TASK_SUITE
from .source import adapt, archive, make_environment, validate_archive

SCHEMA = 'task057-composition-probe-eval-v1'
RUN_SCHEMA = 'task057-probe-source-run-v1'
FIELDS = {'schema_version', 'source_bank', 'base_runtime', 'reporting_root', 'protected_roots'}
EXPECTED_READY = 60


def load_config(path):
    path = Path(path).resolve()
    cfg = read(path)
    if (not isinstance(cfg, dict) or set(cfg) != FIELDS or cfg['schema_version'] != SCHEMA
            or not isinstance(cfg['protected_roots'], list) or not cfg['protected_roots']):
        raise ValueError('Exact057 probe evaluation configuration required')
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
        raise FileExistsError('057 probe requires a fresh output')
    roots = [Path(cfg['source_bank']), Path(cfg['base_runtime']),
             Path(__file__).resolve().parents[2], Path(config_path).resolve(),
             *[Path(p) for p in cfg['protected_roots']]]
    if any(target == p or p in target.parents or target in p.parents for p in roots):
        raise ValueError('057 output overlaps protected bank, model, code or old results')
    return target


def plan(cfg, model):
    if model not in MODEL_ORDER:
        raise ValueError('057 probe only evaluates the original base policy')
    from .preparation import read_bank

    bank_path = Path(cfg['source_bank']).resolve()
    bank = read_bank(bank_path)
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    if (not bank['complete'] or bank['ready'] != EXPECTED_READY or bank['failed']
            or bank.get('pending') or len(bank['rows']) != EXPECTED_READY):
        raise ValueError('057 requires a complete immutable 60-source probe bank')
    sources = [adapt(row['source_manifest'], row) for row in bank['rows']]
    runtime = load_runtime(cfg['base_runtime'])
    value = {
        'schema_version': SCHEMA,
        'config': cfg,
        'source_config': bank['snapshot']['config'],
        'model': model,
        'runtime': runtime,
        'method_adapter': None,
        'adapter_identity': None,
        'expected': [deepcopy(source['episodes'][0]) for source in sources],
        'sources': sources,
        'source_bank_sha256': sha(bank_path / 'sources.json'),
        'preparation_identity': bank['preparation_identity'],
        'evaluation_scope': 'task057-counterfactual-capability-probe',
        'implementation': implementation_identity(),
        'source_generation': 0,
        'ordinary_episodes': 0,
        'training': False,
        'diagnostic_only': True,
    }
    value['plan_sha256'] = digest(value)
    return value


def worker(frozen):
    cfg = deepcopy(frozen['runtime'])
    if frozen['model'] != 'base':
        raise ValueError('057 probe never loads a research adapter')
    return cfg


def verify_model(frozen, provenance):
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata

    validate_policy_metadata(frozen['runtime'], provenance['policy_metadata'])
    if provenance['policy_metadata'].get('method_adapter') != frozen['adapter_identity']:
        raise ValueError('057 loaded model/adapter identity differs from frozen plan')


def write_raw_result(folder, result, episode):
    folder = Path(folder)
    path = folder / 'raw' / (episode['episode_id'] + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, result)
    return path


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
        raw_path = write_raw_result(folder, result, episode)
        metadata.update(phase='verification', missing=[], results=[{
            'episode_id': episode['episode_id'],
            'path': raw_path.relative_to(folder).as_posix(),
            'sha256': sha(raw_path),
        }])
        if result.get('interrupted') or result.get('status') != 'completed':
            raise RuntimeError('057 probe technical pause: ' + str(result.get('error', result.get('status'))))
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
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    from egrs.remain053 import validation
    from .catalog import register

    register(source, Path(source['source']['manifest']).parent)
    folder = Path(folder)
    metadata = read(folder / 'task_run.json')
    episode = source['episodes'][0]
    if (metadata.get('schema_version') != RUN_SCHEMA
            or metadata.get('status') != 'completed' or metadata.get('cleanup_errors')
            or metadata['source_plan'] != source or metadata['batch_identity_sha256'] != frozen['plan_sha256']
            or metadata['runtime_config'] != frozen['runtime'] or metadata['missing']
            or metadata['attempts'] != [episode['episode_id']] or len(metadata['results']) != 1):
        raise ValueError('Incomplete/mismatched 057 probe episode cannot be scored')
    verify_model(frozen, metadata['model_runtime'])
    row = next(row for row in frozen['source_config_population'] if row['episode_id'] == episode['episode_id'])
    verified = validate_archive(folder, source, row, frozen['source_config'])
    if verified['episode_id'] != episode['episode_id']:
        raise ValueError('057 archived source episode differs')
    if read(folder / 'environment.json')['actual_environment'] != source['environment_config']['environment']:
        raise ValueError('057 actual bridge environment differs')
    reference = metadata['results'][0]
    path = workflow._contained(folder, reference['path'])
    if sha(path) != reference['sha256']:
        raise ValueError('057 raw bytes changed')
    raw = read(path)
    identity = workflow.evidence_identity(metadata, episode)
    validation.validate_protocol_result(raw, episode, identity)
    if raw.get('model_identity') != workflow._model_identity(metadata):
        raise ValueError('057 raw loaded model identity differs')
    checked = validation.validate_evidence(folder, raw, episode, identity)
    if checked.get('verified') is False or raw['status'] != 'completed':
        raise ValueError('057 incomplete evidence cannot become a policy failure')
    video = raw['video']
    if video['status'] != 'saved' or sha(workflow._contained(folder, video['path'])) != video['sha256']:
        raise ValueError('057 probe requires full video for each completed episode')
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
            raise ValueError('Duplicate 057 completed probe episode')
        single = map_verified_results([episode], {name: record})
        if single['integrity_errors'] or single['counts']['completed'] != 1:
            raise ValueError('057 live scoring failed original binary mapper')
        self.records[name] = record
        self.outcomes[name] = single['episodes'][0]['success']
        n, successes = len(self.outcomes), sum(self.outcomes.values())
        task = episode['task_id']
        task_names = [e['episode_id'] for e in self.population
                      if e['task_id'] == task and e['episode_id'] in self.outcomes]
        task_successes = sum(self.outcomes[key] for key in task_names)
        value = {
            'schema_version': SCHEMA, 'phase': 'probe', 'model': self.model,
            'completed': n, 'expected': EXPECTED_READY, 'percent': 100 * n / EXPECTED_READY,
            'successes': successes, 'live_compliant_SR_percent': 100 * successes / n,
            'task_id': task, 'task_completed': len(task_names),
            'task_successes': task_successes,
            'task_SR_percent': 100 * task_successes / len(task_names),
            'episode_id': name, 'episode_success': self.outcomes[name],
            'elapsed_seconds': time.monotonic() - self.started,
        }
        write(self.output / 'progress.json', value)
        print(f"[057][{self.model}] completed={n}/{EXPECTED_READY} ({value['percent']:.2f}%) "
              f"task={task} ep={episode['initial_state_index'] + 1}/15 "
              f"result={'SUCCESS' if self.outcomes[name] else 'FAILURE'} "
              f"task_SR={value['task_SR_percent']:.2f}% ({task_successes}/{len(task_names)}) "
              f"overall_SR={value['live_compliant_SR_percent']:.2f}% ({successes}/{n})", flush=True)


def run(config_path, output, model='base'):
    cfg = load_config(config_path)
    if model not in MODEL_ORDER:
        raise ValueError('057 probe only evaluates the original base policy')
    output = protect(cfg, output, config_path)
    frozen = plan(cfg, model)
    frozen['source_config_population'] = read(Path(cfg['source_bank']) / 'sources.json')['rows']
    from egrs.augmentation.dependencies import activate_core
    activate_core(Path(frozen['source_config']['benchmark_root']))
    output.mkdir(parents=True)
    write(output / 'plan.json', frozen)
    from egrs.augmentation.dependencies import activate_reporting
    activate_reporting(Path(cfg['reporting_root']))
    live = Live(output, model, frozen['expected'])
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    from libero_remain_reporting import map_verified_results, render_report

    policy = None
    errors = []
    new_count = 0
    try:
        policy = SubprocessPolicy(worker(frozen))
        verify_model(frozen, policy.provenance)
        for source in frozen['sources']:
            episode = source['episodes'][0]
            folder = output / 'episodes' / episode['episode_id']
            record = execute_episode(folder, source, frozen, policy)
            new_count += 1
            live.add(episode, record)
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
                      diagnostic_only=True,
                      ordinary_episodes=0, source_generation=0,
                      new_execution_attempts=new_count,
                      software_exit='success' if report['counts']['formal_SR'] else 'incomplete',
                      execution_errors=errors, plan_sha256=frozen['plan_sha256'])
        if report['counts']['successes'] != sum(live.outcomes.values()):
            raise ValueError('057 live/final scoring discrepancy; preserve run for inspection')
        write(output / 'summary.json', report)
        (output / 'report.md').write_text(render_report(report), encoding='utf-8')
    if not report['counts']['formal_SR']:
        raise RuntimeError('057 probe not formally complete')
    print(f"[057][{model}] COMPLETE compliant_SR={report['counts']['formal_SR']['percent']:.2f}%", flush=True)
    return report
