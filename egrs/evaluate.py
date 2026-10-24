"""OFT + trained selector, fixed 100-source evaluation using the unchanged core.

plan/help/inspect are file-only. Only the explicit run command creates models
or an environment. No native measurement, endpoint or scoring is implemented here.
"""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

FORMAT = 'egrs.evaluation.config.v1'
PLAN = 'egrs.evaluation.plan.v1'
BATCH = 'egrs.evaluation.batch.v1'
TASK = 'egrs.evaluation.task.v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    temporary.replace(path)


def contained(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('artifact reference must be relative')
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()): raise ValueError('artifact escapes run')
    return path


def load_config(path):
    path = Path(path).resolve(strict=True)
    config = read(path)
    required = {'format', 'core', 'baseline_batch', 'baseline_run', 'selector_config', 'selector_python',
                'checkpoint', 'checkpoint_state_sha256'}
    if set(config) != required or config['format'] != FORMAT:
        raise ValueError('evaluation requires the explicit core, baseline and trained selector')
    config = deepcopy(config)
    def absolute(value):
        p = Path(value).expanduser()
        return os.path.abspath(p if p.is_absolute() else path.parent / p)
    for key in ('baseline_batch', 'baseline_run', 'selector_config', 'selector_python', 'checkpoint'):
        config[key] = absolute(config[key])
    config['core']['root'] = absolute(config['core']['root'])
    from .core import EVAL_REVISION
    if config['core'].get('revision') != EVAL_REVISION or config['core'].get('allow_reference'):
        raise ValueError('formal evaluation requires the frozen eval core, not annotation reference')
    if not Path(config['selector_python']).is_file(): raise ValueError('selector interpreter missing')
    return config


def plan(config_path):
    config = load_config(config_path)
    from .core import activate
    core = activate(config['core'])
    from benchmark.remaining_goals.headless.planning import dry_plan, validate_plan
    baseline = validate_plan(dry_plan(config['baseline_batch']))
    prior = read(Path(config['baseline_run'])/'batch.json')
    if (not isinstance(prior.get('loaded_model_identity'),dict) or
            prior['identity']['runtime_configs'] != baseline['identity']['runtime_configs']):
        raise ValueError('original baseline actor runtime/asset identity is missing or differs')
    from .selector.model import resolve_config, checkpoint_identity
    selector = resolve_config(read(config['selector_config']))
    if not selector['use_history'] or not selector['role_supervision'] or selector.get('factory'):
        raise ValueError('this evaluation is the full trained selector, not an ablation/backend substitution')
    selector.pop('lora_path', None)
    selector['adapter'] = str(Path(config['checkpoint']) / 'adapter')
    checkpoint = checkpoint_identity(selector)
    if checkpoint['state_sha256'] != config['checkpoint_state_sha256']:
        raise ValueError('checkpoint is not the selected dev-loss checkpoint')
    selector['runtime'] = {'python_executable': config['selector_python'],
                           'startup_timeout_seconds': 1200, 'predict_timeout_seconds': 180}
    from .policy import method_source_hash
    identity = dict(config=config, core=core, baseline_identity=baseline['identity'],
                    baseline_actor_identity=prior['loaded_model_identity'],
                    selector=selector, selector_checkpoint=checkpoint,
                    method_source_sha256=method_source_hash(),
                    selector_config_sha256=file_sha(config['selector_config']))
    result = dict(format=PLAN, identity=identity, identity_sha256=digest(identity),
                  expected=baseline['expected'], tasks=baseline['tasks'],
                  ready_episodes=baseline['ready_episodes'],
                  simulation_created=False, models_loaded=False)
    result['plan_sha256'] = digest(result)
    return result


def validate_plan(value):
    from benchmark.remaining_goals.headless.planning import planned_episodes, COMMON_TEN_TASKS
    if (value.get('format') != PLAN or value.get('expected') != planned_episodes()
            or value.get('identity_sha256') != digest(value.get('identity'))
            or value.get('plan_sha256') != digest({k:v for k,v in value.items() if k != 'plan_sha256'})
            or [r['task_id'] for r in value['tasks']] != list(COMMON_TEN_TASKS)):
        raise ValueError('fixed method evaluation plan changed')
    for row in value['tasks']:
        if row['status'] == 'ready' and row.get('source_plan_sha256') != digest(
                {k:v for k,v in row.items() if k != 'source_plan_sha256'}):
            raise ValueError('source plan changed')
    return value


def method_config(plan_value, source, output):
    from .configuration import validate_config
    identity = plan_value['identity']
    actor = deepcopy(identity['baseline_identity']['runtime_configs'][source['suite']])
    return validate_config(dict(policy_factory='egrs.policy:make_policy',
        core=deepcopy(identity['config']['core']), actor=actor,
        goal_change_capability='openvla_oft', selector=deepcopy(identity['selector']),
        variant='full', history=True, output_dir=str(Path(output).resolve())))


def verify_runtime(plan_value, config, metadata):
    """Verify the nested original actor; never present the facade as baseline."""
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata
    from benchmark.remaining_goals.headless.workflow import shared_model_identity
    if metadata.get('method') != 'egrs/v1' or metadata.get('variant') != 'full' or metadata.get('history') is not True:
        raise ValueError('not the full EGRS method')
    provenance = metadata['provenance']
    if (provenance['method_source_sha256'] != plan_value['identity']['method_source_sha256']
            or provenance['core'] != plan_value['identity']['core']
            or provenance['configuration_sha256'] != hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()):
        raise ValueError('loaded method code/core/config identity differs')
    selector = metadata['selector']
    if (selector.get('checkpoint_identity') != plan_value['identity']['selector_checkpoint']
            or any(selector.get(k) != v for k,v in config['selector'].items())):
        raise ValueError('initialized selector checkpoint/config differs')
    facade = metadata['actor']['policy_metadata']
    if facade.get('method_facade') != 'egrs.actor/v1' or facade.get('goal_change_capability') != 'openvla_oft':
        raise ValueError('missing original OFT actor facade')
    actor = facade['actor']
    validate_policy_metadata(config['actor'], actor['policy_metadata'])
    return shared_model_identity(actor)


def runtime_identity(plan_value, metadata):
    return dict(method='egrs/v1', variant='full',
        method_source_sha256=plan_value['identity']['method_source_sha256'],
        selector_checkpoint=plan_value['identity']['selector_checkpoint'],
        original_actor=metadata['actor']['policy_metadata']['actor'],
        method_runtime_sha256=digest(metadata))


class Progress:
    def __init__(self, output):
        self.output = Path(output)
        self.value = dict(format='egrs.evaluation.progress.v1', expected=100, attempted=0,
                          completed=0, completed_percent=0., task=None, episode=None, query=0)

    def update(self, **changes):
        self.value.update(changes)
        self.value['completed_percent'] = self.value['completed']
        self.value['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
        write(self.output/'progress.json', self.value)
        print(json.dumps({'evaluation_progress': self.value}, ensure_ascii=False), flush=True)


class QueryProgress:
    """Only delegates sensor/actions; no evaluator facts enter this wrapper."""
    def __init__(self, policy, progress):
        self.policy, self.progress, self.query = policy, progress, 0
    def reset(self):
        self.query = 0
        return self.policy.reset()
    def predict(self, observation, instruction):
        self.query += 1
        self.progress.update(phase='policy_predict', query=self.query)
        result = self.policy.predict(observation, instruction)
        self.progress.update(phase='policy_returned', query=self.query)
        return result
    def finish_episode(self, result): return self.policy.finish_episode(result)


def _components():
    from .policy import make_policy
    from .core import run_episode
    from benchmark.remaining_goals.headless.workflow import make_environment, make_recorder
    from benchmark.remaining_goals.headless.evidence import HeadlessEvidence
    return dict(policy=make_policy, environment=make_environment, recorder=make_recorder,
                evidence=HeadlessEvidence, episode=run_episode)


def _task(plan_value, source, output, batch, progress, components, bind_actor):
    from benchmark.remaining_goals.headless.planning import HORIZON, CONFIRMATION, CHUNK
    from benchmark.remaining_goals.headless.workflow import _archive_mask10_source
    from benchmark.remaining_goals.headless.evidence import validate_evidence
    from .sidecar import inspect_sidecar
    from .core import SidecarFinalizationError
    directory = Path(output)/'tasks'/source['task_id']
    directory.mkdir(parents=True, exist_ok=False)
    config = method_config(plan_value, source, directory/'method')
    metadata = dict(format=TASK, run_id=uuid.uuid4().hex, status='running', source_plan=source,
        batch_identity_sha256=plan_value['identity_sha256'], method_config=config,
        model_runtime=None, identity=None, results=[], error=None, cleanup_errors=[])
    task_file = directory/'task_run.json'
    write(task_file, metadata)
    policy = env = None
    try:
        for key, name in (('manifest','manifest.json'),('candidate_replay','replay_report.json')):
            raw = Path(source['source'][key]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['source_files'][name]: raise ValueError('source changed')
            target = directory/'source'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream: stream.write(raw)
        if 'source_acceptance' in source: _archive_mask10_source(directory, source)
        else: raise ValueError('formal method evaluation requires accepted mask10 sources')
        progress.update(task=source['task_id'], episode=None, query=0, phase='policy_initialize')
        policy = components['policy'](config)
        metadata['model_runtime'] = deepcopy(policy.metadata)
        bind_actor(verify_runtime(plan_value, config, metadata['model_runtime']))
        metadata['identity'] = runtime_identity(plan_value, metadata['model_runtime'])
        write(task_file, metadata)
        environment = deepcopy(source['environment_config'])
        environment['manifest_dir'] = str(directory/'source/manifest_files')
        progress.update(phase='environment_initialize')
        env = components['environment'](environment)
        wrapped = QueryProgress(policy, progress)
        for index, episode in enumerate(source['episodes'], 1):
            name = episode['episode_id']
            progress.update(episode=name, query=0, phase='episode_start',
                            attempted=progress.value['attempted']+1)
            identity = dict(protocol_version='remaining-headless-goal-endpoint-v1',
                run_id=metadata['run_id'], batch_identity_sha256=plan_value['identity_sha256'],
                source_plan_sha256=source['source_plan_sha256'], model_identity=metadata['identity'],
                episode_id=name, state_sha256=episode['state_sha256'], suite=episode['suite'],
                policy_seed=7, horizon=HORIZON, confirmation_steps=CONFIRMATION, max_chunk_steps=CHUNK,
                source_acceptance={k:deepcopy(source['source_acceptance'][k]) for k in
                    ('schema_version','acceptance_scope','selection_sha256','selected_episode_ids')})
            recorder = components['recorder'](directory/'videos'/(name+'.mp4'), episode)
            try: evidence = components['evidence'](directory/'evidence'/name, identity)
            except BaseException:
                recorder.close()
                raise
            finalization_error = None
            try:
                result = components['episode'](env, wrapped, episode, horizon=HORIZON,
                    confirmation_steps=CONFIRMATION, max_chunk_steps=CHUNK,
                    recorder=recorder, evidence=evidence, identity=identity)
            except SidecarFinalizationError as error:
                result = error.partial_result
                finalization_error = error
            # Write the original result even when subsequent artifact checks fail.
            artifact_error = None
            if result.get('video',{}).get('status') == 'saved':
                result['video'].update(path=f'videos/{name}.mp4')
                try: result['video']['sha256'] = file_sha(directory/result['video']['path'])
                except Exception as error: artifact_error = error
            raw_path = f'raw/{name}.json'
            write(directory/raw_path, result)
            reference = dict(episode_id=name, path=raw_path, sha256=file_sha(directory/raw_path),
                identity=identity, sidecar=f'method/episode-{index:06d}.jsonl', verified=False,
                error=None)
            metadata['results'].append(reference)
            write(task_file, metadata)
            if artifact_error is not None: raise artifact_error
            if finalization_error is not None: raise finalization_error
            reference['sidecar_sha256'] = file_sha(directory/reference['sidecar'])
            validation = validate_evidence(directory, result, episode, identity)
            sidecar = inspect_sidecar(directory/reference['sidecar'], result)
            if validation.get('verified') is not True: raise ValueError('partial core evidence retained')
            if sidecar['status'] != ('complete' if result['status']=='completed' else 'partial'):
                raise ValueError('method/core completion mismatch')
            reference['verified'] = True
            write(task_file, metadata)
            if result.get('interrupted'): raise KeyboardInterrupt('interrupted episode retained')
            if result['status'] != 'completed': raise RuntimeError('technical episode failure: '+str(result.get('error')))
            progress.update(completed=progress.value['completed']+1, phase='episode_complete')
        metadata['status'] = 'completed'
    except BaseException as error:
        metadata.update(status='technical_pause', error=type(error).__name__+': '+str(error))
        if metadata['results'] and not metadata['results'][-1]['verified']:
            metadata['results'][-1]['error'] = metadata['error']
        if isinstance(error,(KeyboardInterrupt,SystemExit)): raise
    finally:
        for obj in (env, policy):
            if obj is not None:
                try: obj.close()
                except BaseException as error:
                    metadata['cleanup_errors'].append(type(error).__name__+': '+str(error))
                    metadata['status']='technical_pause'
        write(task_file, metadata)
    return metadata


def _validate_task(plan_value, source, directory):
    """Read archived evidence only, not the live state/model source tree."""
    from benchmark.remaining_goals.headless.workflow import _validate_source_snapshot
    from benchmark.remaining_goals.headless.evidence import validate_evidence
    from benchmark.remaining_goals.headless.schema import validate_result
    from .sidecar import inspect_sidecar
    metadata = read(directory/'task_run.json')
    if (metadata['format'] != TASK or metadata['batch_identity_sha256'] != plan_value['identity_sha256']
            or metadata['source_plan'] != source): raise ValueError('task identity changed')
    if metadata['method_config'] != method_config(plan_value, source, metadata['method_config']['output_dir']):
        raise ValueError('task method configuration differs from planned selector/actor')
    for filename, sha in source['source_files'].items():
        if file_sha(contained(directory/'source',filename)) != sha: raise ValueError('archived source changed')
    _validate_source_snapshot(directory, source)
    if metadata['model_runtime'] is not None:
        verify_runtime(plan_value, metadata['method_config'], metadata['model_runtime'])
        if metadata['identity'] != runtime_identity(plan_value, metadata['model_runtime']):
            raise ValueError('method runtime identity changed')
    episodes = {e['episode_id']:e for e in source['episodes']}
    results, issues, seen = [], [], set()
    for reference in metadata['results']:
        name = reference['episode_id']
        if name not in episodes or name in seen: raise ValueError('duplicate/unplanned method result')
        seen.add(name)
        try:
            result_path = contained(directory, reference['path'])
            if file_sha(result_path) != reference['sha256']: raise ValueError('raw bytes changed')
            result = read(result_path); identity = reference['identity']; episode = episodes[name]
            if (identity['model_identity'] != metadata['identity'] or identity['run_id'] != metadata['run_id']
                    or identity['batch_identity_sha256'] != plan_value['identity_sha256']
                    or identity['source_plan_sha256'] != source['source_plan_sha256']):
                raise ValueError('episode method identity differs')
            validate_result(result, episode, identity)
            valid = validate_evidence(directory,result,episode,identity)
            if not reference['verified'] or valid.get('verified') is not True: raise ValueError('unverified episode retained')
            sidecar_path = contained(directory,reference['sidecar'])
            if file_sha(sidecar_path) != reference['sidecar_sha256']: raise ValueError('sidecar bytes changed')
            header = read_lines(sidecar_path)[0]
            if header['metadata'] != metadata['model_runtime']: raise ValueError('sidecar runtime changed')
            inspect_sidecar(sidecar_path,result)
            video = result.get('video',{})
            if result['status']=='completed' and video.get('status')!='saved':raise ValueError('full video missing')
            if video.get('status')=='saved' and file_sha(contained(directory,video['path']))!=video['sha256']:
                raise ValueError('video bytes changed')
            results.append(result)
        except (OSError,ValueError,KeyError,TypeError) as error:
            issues.append(dict(episode_id=name,task_id=source['task_id'],error=str(error)))
    return metadata, results, issues


def read_lines(path):
    with Path(path).open(encoding='utf-8') as stream: return [json.loads(s) for s in stream if s.strip()]


def inspect(output):
    output = Path(output).resolve(strict=True)
    batch = read(output/'batch.json'); value = read(output/'plan.json')
    from .core import activate
    activate(value['identity']['config']['core'])
    validate_plan(value)
    if (batch['format'] != BATCH or batch['identity_sha256'] != value['identity_sha256']
            or batch['plan_sha256'] != value['plan_sha256']): raise ValueError('batch/plan changed')
    results, issues, task_execution = [], [], {}
    actor_id = value['identity']['baseline_actor_identity']
    for source in value['tasks']:
        directory = output/'tasks'/source['task_id']
        if not directory.exists(): continue
        try:
            metadata, rows, errors = _validate_task(value,source,directory)
            if metadata['model_runtime'] is not None:
                actual = verify_runtime(value, metadata['method_config'], metadata['model_runtime'])
                if actor_id is not None and actual != actor_id: raise ValueError('actor assets differ across suites')
                actor_id = actual
            results.extend(rows); issues.extend(errors)
            task_execution[source['task_id']] = {k:metadata[k] for k in ('status','error','cleanup_errors')}
        except (OSError,ValueError,KeyError,TypeError) as error:
            issues.append(dict(task_id=source['task_id'],error=str(error)))
    from benchmark.remaining_goals.headless.metrics import summarize
    summary = summarize(value['expected'], results)
    summary.update(method='egrs/v1',variant='full',task_execution=task_execution,
        unverified_task_artifacts=issues,identity_sha256=value['identity_sha256'],
        selector_checkpoint=value['identity']['selector_checkpoint'],
        notice=summary['notice']+' This is full EGRS + frozen OFT, not a baseline rerun.')
    return summary


def save_summary(output, summary):
    import csv
    from benchmark.remaining_goals.headless.metrics import render_report
    output = Path(output)
    write(output/'summary.json', summary)
    report=render_report(summary).replace('# Headless ten-task baseline',
        '# EGRS + frozen OFT: fixed mask10 evaluation',1)
    report+='\n## Execution and artifact diagnostics\n\n'+json.dumps(
        {k:summary[k] for k in ('task_execution','unverified_task_artifacts')},ensure_ascii=False,indent=2)+'\n'
    (output/'report.md').write_text(report,encoding='utf-8')
    rows = summary['episodes']
    with (output/'episodes.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def run(config_path, output, *, components=None):
    value = validate_plan(plan(config_path))
    from .policy import method_source_hash
    if method_source_hash()!=value['identity']['method_source_sha256']:raise ValueError('method code changed')
    if value['ready_episodes']!=100:raise ValueError('reuse the accepted 100 mask10 sources; see file-only plan')
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)  # No hidden retry/resume or overwrite.
    write(output/'plan.json',value)
    batch=dict(format=BATCH,identity_sha256=value['identity_sha256'],plan_sha256=value['plan_sha256'],
               status='running',tasks={},error=None)
    write(output/'batch.json',batch)
    progress=Progress(output);progress.update(phase='starting')
    components=components or _components()
    shared=[]
    def bind_actor(actual):
        if actual!=value['identity']['baseline_actor_identity']:
            raise ValueError('actual OFT assets/statistics differ from the existing baseline')
        if shared and shared[0]!=actual:raise ValueError('actual OFT assets differ across tasks/suites')
        if not shared:shared.append(actual)
    try:
        for source in value['tasks']:
            metadata=_task(value,source,output,batch,progress,components,bind_actor)
            batch['tasks'][source['task_id']]={k:metadata[k] for k in ('status','error','cleanup_errors')}
            write(output/'batch.json',batch)
            if metadata['status']!='completed':
                raise RuntimeError('technical pause; preserve evidence, do not automatically retry: '+str(metadata['error']))
        batch['status']='completed'
    except BaseException as error:
        batch.update(status='technical_pause',error=type(error).__name__+': '+str(error))
        raise
    finally:
        write(output/'batch.json',batch)
        progress.update(phase=batch['status'])
        save_summary(output,inspect(output))
    return batch


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('plan',help='file-only configuration/source/checkpoint plan; no model/native work')
    p.add_argument('--config',required=True);p.add_argument('--output')
    r=commands.add_parser('run',help='user-started real fixed 100-episode evaluation')
    r.add_argument('--config',required=True);r.add_argument('--output',required=True)
    i=commands.add_parser('inspect',help='offline verification/summary of archived artifacts')
    i.add_argument('--run',required=True);i.add_argument('--output')
    args=parser.parse_args(argv)
    if args.command=='plan':
        value=plan(args.config)
        if args.output:
            if Path(args.output).exists():raise FileExistsError(args.output)
            write(args.output,value)
        print(json.dumps(dict(format=PLAN,ready_episodes=value['ready_episodes'],expected=100,
            models_loaded=False,simulation_created=False,identity_sha256=value['identity_sha256']),indent=2))
        return 0 if value['ready_episodes']==100 else 2
    if args.command=='run':
        run(args.config,args.output)
        return 0
    summary=inspect(args.run)
    if args.output:
        Path(args.output).mkdir(parents=True,exist_ok=False)
        save_summary(args.output,summary)
    print(json.dumps(dict(counts=summary['counts'],unverified=summary['unverified_task_artifacts']),indent=2))
    return 2 if (summary['unverified_task_artifacts'] or
        any(t['status']!='completed' for t in summary['task_execution'].values()) or
        summary['counts']['classification_counts']['missing']) else 0


if __name__=='__main__':raise SystemExit(main())
