"""Same core rollout/endpoint/scorer, now450 paired sources and immediate SR.

This module coordinates artifacts and population size, not policy control or
judgement. Original run_episode, evidence/schema validators, offline scorer and
034 binary mapper are called directly. No online facts enter the policy.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid

from .sources import (SCHEMA, activate, digest, expected, extension_identity, helpers,
                      read, resolve, sha, write)

ADAPTER_SHA = '78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d'
FIELDS = {'schema_version', 'benchmark_root', 'reporting_root', 'legacy_root',
          'reference_config', 'base_runtime', 'adapter', 'source_bank'}


def load_config(path):
    path = Path(path).resolve()
    cfg = read(path)
    if set(cfg) != FIELDS or cfg['schema_version'] != SCHEMA:
        raise ValueError('Exact049 configuration required')
    for key in FIELDS - {'schema_version'}:
        if not isinstance(cfg[key], str) or not cfg[key].strip():
            raise ValueError('Explicit049 path required: ' + key)
        cfg[key] = str((path.parent / cfg[key]).resolve())
    return cfg


def protect_output(cfg, output, *, allow_existing=False):
    output = Path(output).resolve()
    if output.exists() and not allow_existing:
        raise FileExistsError('Never overwrite a049 run or old evidence')
    protected = [Path(cfg[k]).resolve() for k in FIELDS - {'schema_version', 'source_bank'}]
    for parent in (Path(cfg['reference_config']).parent, Path(cfg['base_runtime']).parent):
        protected.append(parent)
    # Bank may be an output only in explicit preparation, not eval (below).
    if any(output == p or output in p.parents or p in output.parents for p in protected):
        raise ValueError('049 output overlaps protected dependencies or weights')


def _adapter(cfg):
    from egrs.hint043.adapter import read_adapter_identity
    from egrs.hint043.evaluation import validate_final
    value = read_adapter_identity(cfg['adapter'])
    validate_final(value, 3000)
    if value['arm'] != 'h1' or value['adapter_sha256'] != ADAPTER_SHA:
        raise ValueError('049 requires the fixed045 H1@3000 adapter')
    return value


def plan(cfg, model):
    if model not in ('base', 'h1'):
        raise ValueError('049 model must be base or h1')
    dispatch = activate(cfg)
    scoped = helpers()
    bank = read(Path(cfg['source_bank']) / 'sources.json')
    if (bank.get('schema_version') != SCHEMA or bank.get('complete') is not True
            or bank.get('ready') != 450 or bank.get('failed') != 0
            or bank.get('expected') != expected() or bank.get('config') != cfg
            or bank.get('extension') != extension_identity()):
        raise ValueError('049 requires all450 unchanged accepted sources, not a reduced/easier subset')
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    runtime = load_runtime(cfg['base_runtime'])
    rows = bank['rows']
    if [r['episode_id'] for r in rows] != [r['episode_id'] for r in expected()]:
        raise ValueError('049 source order/unique fixed indices differ')
    sources = []
    fields = ('episode_id', 'task_id', 'suite', 'initial_state_index', 'initial_mask', 'policy_seed', 'evaluation_track')
    for row, wanted in zip(rows, expected()):
        source = resolve(scoped, row['task_id'], row['initial_state_index'], row['origin'])
        if (source['source_plan_sha256'] != row['source_plan_sha256']
                or any(source['episodes'][0].get(k) != wanted[k] for k in fields)):
            raise ValueError('049 population/source binding differs')
        sources.append(source)
    from egrs.trajectory_augmentation.environment_dispatch import binding_for, coordination_identity
    for source in sources:
        binding_for(source['environment_config']['environment'], dispatch)
    value = {'schema_version': SCHEMA, 'config': cfg, 'model': model, 'runtime': runtime,
             'expected': expected(), 'source_bank_sha256': sha(Path(cfg['source_bank']) / 'sources.json'),
             'sources': sources, 'dispatch': dispatch, 'proxy_coordination': coordination_identity(),
             'extension': extension_identity(), 'adapter_identity': _adapter(cfg) if model == 'h1' else None,
             'budget': {'episodes': 450, 'tasks': 9, 'per_task': 50, 'policy_seed': 7,
                        'horizon': 520, 'confirmation_steps': 4, 'chunk': 8, 'video': 'all'},
             'prompt': 'unchanged original full task instruction', 'training': False}
    value['plan_sha256'] = digest(value)
    return value


def _worker(plan):
    cfg = deepcopy(plan['runtime'])
    if plan['model'] == 'h1':
        cfg.update(policy_factory='egrs.hint043.policy:make_policy',
                   method_adapter=plan['config']['adapter'], hint043_arm='h1', hint043_checkpoint_step=3000)
    return cfg


def _verify_model(plan, provenance):
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata
    validate_policy_metadata(plan['runtime'], provenance['policy_metadata'])
    actual = provenance['policy_metadata'].get('method_adapter')
    if actual != plan['adapter_identity']:
        raise ValueError('049 loaded base/H1 identity differs from frozen plan')


def execute_episode(folder, source, plan, policy, scoped):
    """Same core workflow steps, with an immutable one-episode metadata file."""
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.runner import run_episode
    from benchmark.remaining_goals.headless.evidence import HeadlessEvidence
    from benchmark.remaining_goals.headless.scoped_planning import runtime_protocol
    from egrs.trajectory_augmentation.environment_dispatch import make_environment
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    episode = source['episodes'][0]
    archived = scoped['archive_source'](folder, source)
    metadata = {'schema_version': 'remaining-headless-scoped-source-run-v1',
                'protocol_version': source['protocol_version'], 'run_id': uuid.uuid4().hex,
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'batch_identity_sha256': plan['plan_sha256'], 'source_plan': source,
                'runtime_config': plan['runtime'], 'model_runtime': deepcopy(policy.provenance),
                'status': 'running', 'phase': 'initialization', 'error': None,
                'cleanup_errors': [], 'attempts': [episode['episode_id']], 'results': [],
                'missing': [episode['episode_id']]}
    write(folder / 'task_run.json', metadata)
    _verify_model(plan, policy.provenance)
    config = deepcopy(source['environment_config'])
    config.update(manifest_dir=str(archived), protocol=runtime_protocol(source['protocol']))
    env = recorder = None
    result = None
    try:
        env = make_environment(config, plan['dispatch'])
        write(folder / 'environment.json', {'actual_environment': env.identity,
                                           'proxy_coordination': plan['proxy_coordination']})
        identity = workflow.evidence_identity(metadata, episode)
        recorder = workflow.make_recorder(folder / 'videos' / (episode['episode_id'] + '.mp4'), episode)
        evidence = HeadlessEvidence(folder / 'evidence' / episode['episode_id'], identity)
        metadata['phase'] = 'rollout'
        write(folder / 'task_run.json', metadata)
        result = run_episode(env, policy, episode, horizon=520, confirmation_steps=4,
                             max_chunk_steps=8, recorder=recorder, evidence=evidence, identity=identity,
                             protocol=runtime_protocol(source['protocol']))
        if result.get('video', {}).get('status') == 'saved':
            path = 'videos/' + episode['episode_id'] + '.mp4'
            result['video'].update(path=path, sha256=sha(folder / path))
        raw_path = folder / 'raw' / (episode['episode_id'] + '.json')
        write(raw_path, result)
        metadata.update(phase='verification', missing=[], results=[{'episode_id': episode['episode_id'],
                        'path': raw_path.relative_to(folder).as_posix(), 'sha256': sha(raw_path)}])
        if result.get('interrupted') or result.get('status') != 'completed':
            raise RuntimeError('049 technical pause: ' + str(result.get('error', result.get('status'))))
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
    return verify_episode(folder, source, plan, scoped)


def verify_episode(folder, source, plan, scoped):
    """All original trace/action/video checks, with the explicit50 source helper."""
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.headless.schema import validate_protocol_result
    from benchmark.remaining_goals.headless.evidence import validate_evidence
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    folder = Path(folder)
    metadata = read(folder / 'task_run.json')
    episode = source['episodes'][0]
    if (metadata.get('status') != 'completed' or metadata.get('cleanup_errors')
            or metadata['source_plan'] != source or metadata['batch_identity_sha256'] != plan['plan_sha256']
            or metadata['runtime_config'] != plan['runtime'] or metadata['missing']
            or metadata['attempts'] != [episode['episode_id']] or len(metadata['results']) != 1):
        raise ValueError('Incomplete/mismatched049 episode cannot be scored')
    _verify_model(plan, metadata['model_runtime'])
    scoped['validate_snapshot'](folder, source)
    if read(folder / 'environment.json')['actual_environment'] != source['environment_config']['environment']:
        raise ValueError('049 actual bridge environment differs')
    ref = metadata['results'][0]
    path = workflow._contained(folder, ref['path'])
    if sha(path) != ref['sha256']:
        raise ValueError('049 raw bytes changed')
    raw = read(path)
    identity = workflow.evidence_identity(metadata, episode)
    validate_protocol_result(raw, episode, identity)
    if raw.get('model_identity') != workflow._model_identity(metadata):
        raise ValueError('049 raw loaded model identity differs')
    checked = validate_evidence(folder, raw, episode, identity)
    if checked.get('verified') is False or raw['status'] != 'completed':
        raise ValueError('049 incomplete evidence cannot become a policy failure')
    video = raw['video']
    if video['status'] != 'saved' or sha(workflow._contained(folder, video['path'])) != video['sha256']:
        raise ValueError('049 requires full video for each completed episode')
    return score_verified_result(episode, raw, condition='10', source={
        'model_identity': workflow._model_identity(metadata), 'original_protocol': metadata['protocol_version'],
        'input_evidence_level': 'verified_raw_execution_video_and_source_archive', 'run_path': str(folder),
        'verified_files': [{'path': str(folder / 'task_run.json'), 'sha256': sha(folder / 'task_run.json')},
                           {'path': str(path), 'sha256': ref['sha256']}], 'new_execution': True})


class Live:
    """Map each completed record through the exact034 binary criterion once."""
    def __init__(self, output, model, population):
        self.output, self.model = Path(output), model
        self.population = population
        self.records, self.outcomes = {}, {}
        self.started = time.monotonic()

    def add(self, episode, record):
        from libero_remain_reporting import map_verified_results
        name = episode['episode_id']
        if name in self.records:
            raise ValueError('Duplicate049 completed episode')
        single = map_verified_results([episode], {name: record})
        if single['integrity_errors'] or single['counts']['completed'] != 1:
            raise ValueError('049 live scoring failed original binary mapper')
        self.records[name] = record
        self.outcomes[name] = single['episodes'][0]['success']
        n, successes = len(self.outcomes), sum(self.outcomes.values())
        task = episode['task_id']
        task_names = [e['episode_id'] for e in self.population if e['task_id'] == task and e['episode_id'] in self.outcomes]
        task_successes = sum(self.outcomes[k] for k in task_names)
        value = {'schema_version': SCHEMA, 'phase': 'evaluation', 'model': self.model, 'completed': n,
                 'expected': 450, 'percent': 100*n/450, 'successes': successes,
                 'live_compliant_SR_percent': 100*successes/n, 'task_id': task,
                 'task_completed': len(task_names), 'task_successes': task_successes,
                 'task_SR_percent': 100*task_successes/len(task_names),
                 'episode_id': name, 'episode_success': self.outcomes[name],
                 'elapsed_seconds': time.monotonic()-self.started}
        write(self.output / 'progress.json', value)
        print(f"[049][{self.model}] completed={n}/450 ({value['percent']:.2f}%) "
              f"task={task} ep={episode['initial_state_index']+1}/50 "
              f"result={'SUCCESS' if self.outcomes[name] else 'FAILURE'} "
              f"task_SR={value['task_SR_percent']:.2f}% ({task_successes}/{len(task_names)}) "
              f"overall_SR={value['live_compliant_SR_percent']:.2f}% ({successes}/{n})", flush=True)


def run(cfg, output, model):
    protect_output(cfg, output)
    output = Path(output).resolve()
    bank = Path(cfg['source_bank']).resolve()
    if output == bank or bank in output.parents or output in bank.parents:
        raise ValueError('049 eval cannot overwrite source bank')
    frozen = plan(cfg, model)
    output.mkdir(parents=True)
    write(output / 'plan.json', frozen)
    scoped = helpers()
    live = Live(output, model, frozen['expected'])
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    from libero_remain_reporting import map_verified_results, render_report
    policy = None
    errors = []
    try:
        policy = SubprocessPolicy(_worker(frozen))
        _verify_model(frozen, policy.provenance)
        for source in frozen['sources']:
            episode = source['episodes'][0]
            folder = output / 'episodes' / episode['episode_id']
            record = execute_episode(folder, source, frozen, policy, scoped)
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
        report.update(schema_version=SCHEMA, model=model, source_bank_sha256=frozen['source_bank_sha256'],
                      software_exit='success' if report['counts']['formal_SR'] else 'incomplete',
                      execution_errors=errors, plan_sha256=frozen['plan_sha256'])
        if report['counts']['successes'] != sum(live.outcomes.values()):
            raise ValueError('049 live/final scoring discrepancy; preserve run for inspection')
        write(output / 'summary.json', report)
        (output / 'report.md').write_text(render_report(report), encoding='utf-8')
    if not report['counts']['formal_SR']:
        raise RuntimeError('049 not formally complete; next model is not started')
    print(f"[049][{model}] COMPLETE compliant_SR={report['counts']['formal_SR']['percent']:.2f}%", flush=True)
    return report


def compare(base, h1, output):
    base, h1 = read(Path(base)/'summary.json'), read(Path(h1)/'summary.json')
    if (any(r.get('schema_version') != SCHEMA or r['counts']['completed'] != 450
            or not r['counts']['formal_SR'] for r in (base, h1))
            or base['source_bank_sha256'] != h1['source_bank_sha256']
            or base['model'] != 'base' or h1['model'] != 'h1'):
        raise ValueError('049 requires complete paired450 base/H1 reports')
    left, right = base['episodes'], h1['episodes']
    if [r['episode_id'] for r in left] != [r['episode_id'] for r in right]:
        raise ValueError('049 paired population differs')
    value = {'schema_version': SCHEMA, 'base': base['counts']['formal_SR'], 'h1': h1['counts']['formal_SR'],
             'delta_pp': h1['counts']['formal_SR']['percent']-base['counts']['formal_SR']['percent'],
             'gains': sum(not a['success'] and b['success'] for a,b in zip(left,right)),
             'losses': sum(a['success'] and not b['success'] for a,b in zip(left,right)),
             'tasks': [{'task_id': a['task_id'], 'base': a['formal_SR'], 'h1': b['formal_SR']}
                       for a,b in zip(base['tasks'],h1['tasks'])]}
    if Path(output).exists():
        raise FileExistsError('Never overwrite049 comparison')
    write(output, value)
    return value
