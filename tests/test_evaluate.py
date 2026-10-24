"""025 orchestration: fake models/sources, real fixed core runner/evidence/metrics."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest

from egrs import evaluate as ev
from egrs.core import EVAL_REVISION,activate
from egrs.policy import EGRSPolicy
from egrs.selector.model import resolve_config,checkpoint_identity
from tests.test_runtime import INSTRUCTION,observation
from tests.test_policy import Selector,Actor


CORE=Path(os.environ['EGRS_CORE_ROOT'])


def core_fixture(name):
    spec=importlib.util.spec_from_file_location('core_025_'+name,CORE/'tests'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def actor_metadata(actor):
    from benchmark.remaining_goals.adapters.oft_transfer import SOG10_SOURCE,TRAINING_SUITES,REPO_REVISION,INFERENCE_SOURCES
    transfer=actor['adapter_options'].get('suite_transfer');suite=actor['suite']
    return dict(model='openvla_oft',suite=suite,evaluation_suite=suite,
        checkpoint_source=SOG10_SOURCE,checkpoint_training_suites=TRAINING_SUITES,
        normalization_suite='libero_10',evaluation_track='libero_90_zero_shot' if transfer else 'libero_10_primary',
        explicit_stop=False,action_chunk=8,repo_commit=REPO_REVISION,suite_transfer=transfer,
        unnorm_key='libero_10_no_noops',dataset_statistics_sha256='a'*64,
        normalization_statistics_sha256='b'*64,inference_source_sha256={x:'c'*64 for x in INFERENCE_SOURCES},
        component_checkpoint_sha256={'action_head--checkpoint.pt':'d'*64,'proprio_projector--checkpoint.pt':'e'*64},
        inference_configuration=dict(center_crop=True,load_in_8bit=False,load_in_4bit=False,
            use_l1_regression=True,use_diffusion=False,use_film=False,num_images_in_input=2,
            use_proprio=True,num_open_loop_steps=8,lora_rank=32),
        checkpoint=str(Path(actor['adapter_options']['checkpoint']).resolve()))


@pytest.fixture
def setup(tmp_path,monkeypatch):
    core=dict(root=str(CORE),revision=EVAL_REVISION);activate(core)
    from benchmark.remaining_goals.headless import planning,workflow,environment
    from benchmark.remaining_goals.adapters.oft_transfer import SOG10_SOURCE,TRANSFER
    monkeypatch.setattr(environment,'_callback_status',lambda:'absent')
    runtimes={}
    for suite in ('libero_10','libero_90'):
        runtimes[suite]=dict(model_id='openvla_oft',policy_id='synthetic-'+suite,
            policy_factory='benchmark.remaining_goals.adapters.openvla_oft:make_policy',suite=suite,
            runtime=dict(python_executable=sys.executable),execution=dict(max_chunk_steps=8,random_seed=7),
            checkpoint_source=SOG10_SOURCE,adapter_options=dict(checkpoint=str(tmp_path/'oft'),
                repo_path=str(tmp_path/'repo'),suite=suite))
        if suite=='libero_90':runtimes[suite]['adapter_options']['suite_transfer']=deepcopy(TRANSFER)
    sources=[]
    xml=hashlib.sha256(b"<mujoco model='headless_cpu_synthetic'/>").hexdigest()
    for task in planning.COMMON_TEN_TASKS:
        directory=tmp_path/'sources'/task;directory.mkdir(parents=True)
        episodes=[dict(e,instruction=INSTRUCTION,seed=0,state_sha256='a'*64,
            model_xml_sha256=xml,bddl_sha256='b'*64,goal_specs=planning.TASKS[task]['goals'])
            for e in planning.planned_episodes() if e['task_id']==task]
        ev.write(directory/'manifest.json',dict(environment='synthetic',episodes=episodes))
        ev.write(directory/'replay.json',dict(synthetic=True))
        row=dict(task_id=task,suite=planning.TASKS[task]['suite'],status='ready',episodes=episodes,
            source=dict(manifest=str(directory/'manifest.json'),candidate_replay=str(directory/'replay.json')),
            source_files={'manifest.json':ev.file_sha(directory/'manifest.json'),
                          'replay_report.json':ev.file_sha(directory/'replay.json')},
            environment_config=dict(task=task),source_acceptance=dict(schema_version=planning.MASK10_ACCEPTANCE,
                acceptance_scope='mask10',status='mask10_ready',selection_sha256=ev.digest(episodes),
                selected_episode_ids=[e['episode_id'] for e in episodes],selected_files=[]))
        row['source_plan_sha256']=ev.digest(row);sources.append(row)
    baseline=dict(schema_version=planning.PLAN_SCHEMA,protocol_version=planning.PROTOCOL,
        identity=dict(runtime_configs=runtimes,budget=planning.budget_plan(),
            config={'source_acceptance':planning.MASK10_ACCEPTANCE},harness_source_sha256='d'*64),
        expected=planning.planned_episodes(),tasks=sources,ready_episodes=100,runtime_checks={},
        simulation_created=False,weights_loaded=False)
    baseline['batch_identity_sha256']=ev.digest(baseline['identity']);baseline['plan_sha256']=ev.digest(baseline)
    monkeypatch.setattr(planning,'dry_plan',lambda _:deepcopy(baseline))
    # Only synthetic source acceptance is replaced; production validators are
    # unmodified and are exercised against existing real evidence at deployment.
    monkeypatch.setattr(workflow,'_archive_mask10_source',lambda directory,source:None)
    monkeypatch.setattr(workflow,'_validate_source_snapshot',lambda directory,source:None)
    checkpoint=tmp_path/'checkpoint-3';(checkpoint/'adapter').mkdir(parents=True)
    (checkpoint/'adapter/adapter_model.safetensors').write_bytes(b'synthetic weights, never loaded')
    ev.write(checkpoint/'state.json',dict(config=resolve_config(),epoch=3,global_step=369,
        data_fingerprints=dict(train='e'*64,dev='f'*64),adapter_files_sha256={
            'adapter_model.safetensors':ev.file_sha(checkpoint/'adapter/adapter_model.safetensors')}))
    (checkpoint/'COMPLETE').write_text('complete\n')
    ev.write(tmp_path/'selector.json',resolve_config())
    ev.write(tmp_path/'baseline.json',dict(synthetic=True))
    from benchmark.remaining_goals.headless.workflow import shared_model_identity
    ev.write(tmp_path/'prior-run/batch.json',dict(identity={'runtime_configs':runtimes},
        loaded_model_identity=shared_model_identity({'policy_metadata':actor_metadata(runtimes['libero_10'])})))
    config=dict(format=ev.FORMAT,core=core,baseline_batch='baseline.json',baseline_run='prior-run',selector_config='selector.json',
        selector_python=sys.executable,checkpoint='checkpoint-3',checkpoint_state_sha256=ev.file_sha(checkpoint/'state.json'))
    path=tmp_path/'evaluation.json';ev.write(path,config)
    return path


def components(monkeypatch,*,technical=False,interrupt=False,violation=False,close_failure=False):
    made=[];envs=[]
    class TestSelector(Selector):
        def __init__(self,config):
            super().__init__();self.metadata={**config,'checkpoint_identity':checkpoint_identity(config)}
    class TestActor(Actor):
        def __init__(self,config):
            super().__init__();self.metadata={'policy_metadata':{'method_facade':'egrs.actor/v1',
                'goal_change_capability':'openvla_oft','actor':{'policy_metadata':actor_metadata(config)}}}
        def predict(self,obs,instruction):
            if technical:raise RuntimeError('synthetic actor failure')
            return super().predict(obs,instruction)
        def close(self):
            if close_failure:raise RuntimeError('synthetic close failure')
    def policy(config):
        from egrs.policy import method_source_hash
        from egrs.core import inspect_core
        value=EGRSPolicy(config,TestSelector(config['selector']),TestActor(config['actor']),
            dict(core=inspect_core(config['core']),method_source_sha256=method_source_hash(),
                configuration_sha256=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()))
        made.append(value);return value
    class Env:
        def __init__(self,config):self.task=config['task'];envs.append(self);self.steps=0;self.closed=False
        def reset(self,source):
            from benchmark.remaining_goals.headless.environment import HeadlessMeasurements
            self.native=core_fixture('test_headless_environment').FakeNative(self.task)
            self.observer=HeadlessMeasurements(self.native,self.task,source_reset_model_xml_sha256=source['model_xml_sha256'])
            self.steps=0;return observation()
        def measurement_static(self):return self.observer.measurement_static()
        def evaluator_state(self):return self.observer.evaluator_state([True,self.steps>=2])
        def step(self,action):
            if interrupt:raise KeyboardInterrupt('synthetic interruption')
            self.steps+=1;self.native.steps+=1;self.native.sim.data.site_xpos[0]=[self.steps/100,0,0]
            if violation:
                self.native.move('distractor_1',[.1,0,.06]);self.native.grasped.add('distractor_1_geom')
            return observation()
        def close(self):self.closed=True
    class Video:
        def __init__(self,path,ep):self.path=path;self.frames=[]
        def capture(self,obs,*,step):self.frames.append(step)
        def close(self):
            self.path.parent.mkdir(exist_ok=True);self.path.write_bytes(b'synthetic video')
            return dict(status='saved',frame_steps=self.frames,synthetic=True)
    from egrs.core import run_episode
    from benchmark.remaining_goals.headless.evidence import HeadlessEvidence
    return dict(policy=policy,environment=Env,recorder=Video,evidence=HeadlessEvidence,episode=run_episode),made,envs


def test_plan_is_file_only_and_selected_checkpoint_bound(setup,tmp_path):
    value=ev.plan(setup)
    assert value['ready_episodes']==100 and len(value['expected'])==100
    assert value['models_loaded'] is False and value['simulation_created'] is False
    assert ev.method_config(value,value['tasks'][-1],tmp_path/'method')['actor']['suite']=='libero_90'
    cfg=ev.read(setup);cfg['checkpoint_state_sha256']='0'*64;ev.write(setup,cfg)
    with pytest.raises(ValueError,match='selected'):ev.plan(setup)


def test_exact100_core_metrics_sidecars_videos_progress(setup,tmp_path,monkeypatch):
    parts,made,envs=components(monkeypatch)
    out=tmp_path/'run';assert ev.run(setup,out,components=parts)['status']=='completed'
    summary=ev.inspect(out)
    assert summary['counts']['success_percent']==100 and summary['counts']['expected']==100
    assert not summary['unverified_task_artifacts']
    assert [x['expected'] for x in summary['tracks']]==[60,40]
    assert all(x['path_length_m']==pytest.approx(.06) for x in summary['episodes'])
    assert len(list(out.glob('tasks/*/videos/*.mp4')))==100
    assert len(list(out.glob('tasks/*/method/episode-*.jsonl')))==100
    assert all(e.closed for e in envs) and len(made)==10
    progress=ev.read(out/'progress.json');assert progress['completed']==100 and progress['completed_percent']==100
    assert progress['query']==1
    with pytest.raises(FileExistsError):ev.run(setup,out,components=parts)
    raw=next(out.glob('tasks/*/raw/*.json'));raw.write_bytes(raw.read_bytes()+b' ')
    assert ev.inspect(out)['counts']['successes']==99


def test_wrong_grasp_is_original_core_failure_not_success(setup,tmp_path,monkeypatch):
    parts,_,_=components(monkeypatch,violation=True)
    ev.run(setup,tmp_path/'run',components=parts)
    summary=ev.inspect(tmp_path/'run')
    assert summary['counts']['classification_counts']['failure']==100
    assert summary['counts']['failure_reasons']['wrong_grasp']==100


@pytest.mark.parametrize('interrupt',[False,True])
def test_technical_failure_or_interrupt_retains_fixed_denominator_and_stops(setup,tmp_path,monkeypatch,interrupt):
    parts,made,envs=components(monkeypatch,technical=not interrupt,interrupt=interrupt)
    with pytest.raises(KeyboardInterrupt if interrupt else RuntimeError):ev.run(setup,tmp_path/'run',components=parts)
    summary=ev.inspect(tmp_path/'run')
    assert summary['counts']['classification_counts']['technical_error']==1
    assert summary['counts']['classification_counts']['missing']==99
    assert len(made)==1 and all(e.closed for e in envs)
    assert ev.read(tmp_path/'run/progress.json')['completed']==0
    assert ev.read(tmp_path/'run/batch.json')['status']=='technical_pause'


def test_close_failure_is_retained_and_not_silently_retried(setup,tmp_path,monkeypatch):
    parts,made,_=components(monkeypatch,close_failure=True)
    with pytest.raises(RuntimeError):ev.run(setup,tmp_path/'run',components=parts)
    summary=ev.inspect(tmp_path/'run')
    assert len(made)==1 and summary['counts']['successes']==10
    assert summary['task_execution']['basket']['cleanup_errors']


def test_changed_actor_statistics_rejected_before_any_environment(setup,tmp_path,monkeypatch):
    parts,made,envs=components(monkeypatch)
    factory=parts['policy']
    def changed(config):
        value=factory(config)
        value.metadata['actor']['policy_metadata']['actor']['policy_metadata']['normalization_statistics_sha256']='f'*64
        return value
    parts['policy']=changed
    with pytest.raises(RuntimeError,match='baseline'):ev.run(setup,tmp_path/'run',components=parts)
    assert len(made)==1 and not envs
    assert ev.inspect(tmp_path/'run')['counts']['classification_counts']['missing']==100


def test_explicit_partial_source_scope_keeps_denominator_without_replaying(setup,tmp_path,monkeypatch):
    from benchmark.remaining_goals.headless import planning
    baseline=planning.dry_plan(None)
    missing=baseline['tasks'][1]
    baseline['tasks'][1]=dict(task_id=missing['task_id'],suite=missing['suite'],status='preparation_error',
        error='synthetic missing old replay',episodes=[])
    baseline['ready_episodes']=90
    baseline['plan_sha256']=ev.digest({k:v for k,v in baseline.items() if k!='plan_sha256'})
    monkeypatch.setattr(planning,'dry_plan',lambda _:deepcopy(baseline))
    parts,made,_=components(monkeypatch)
    with pytest.raises(ValueError,match='allow-missing'):ev.run(setup,tmp_path/'strict',components=parts)
    assert not made
    result=ev.run(setup,tmp_path/'partial',components=parts,allow_missing_sources=True)
    assert result['status']=='completed_with_missing_sources' and len(made)==9
    summary=ev.inspect(tmp_path/'partial')
    assert summary['counts']['expected']==100 and summary['counts']['successes']==90
    assert summary['counts']['classification_counts']['missing']==10
    assert ev.read(tmp_path/'partial/progress.json')['completed_percent']==90


def test_missing_video_keeps_original_raw_and_stops(setup,tmp_path,monkeypatch):
    parts,_,_=components(monkeypatch)
    original=parts['recorder']
    def recorder(path,episode):
        value=original(path,episode);close=value.close
        def lost():
            result=close();path.unlink();return result
        value.close=lost;return value
    parts['recorder']=recorder
    with pytest.raises(RuntimeError):ev.run(setup,tmp_path/'run',components=parts)
    raw=list((tmp_path/'run').glob('tasks/*/raw/*.json'))
    assert len(raw)==1 and ev.read(raw[0])['n_steps']==6
    assert ev.inspect(tmp_path/'run')['unverified_task_artifacts']


@pytest.mark.parametrize('issue',['selector','actor','sidecar','source','video'])
def test_tampering_cannot_be_scored_as_original_method(setup,tmp_path,monkeypatch,issue):
    parts,_,_=components(monkeypatch)
    # One clean task followed by a deliberately technical second initialization.
    original=parts['policy'];calls=[]
    def factory(config):
        if calls:raise RuntimeError('stop fixture after one task')
        calls.append(True);return original(config)
    parts['policy']=factory
    out=tmp_path/'run'
    with pytest.raises(RuntimeError):ev.run(setup,out,components=parts)
    directory=out/'tasks/basket'
    if issue in ('selector','actor'):
        meta=ev.read(directory/'task_run.json')
        if issue=='selector':meta['method_config']['selector']['adapter']='wrong'
        else:meta['method_config']['actor']['suite']='libero_90'
        ev.write(directory/'task_run.json',meta)
    else:
        patterns=dict(sidecar='method/episode-*.jsonl',source='source/manifest.json',video='videos/*.mp4')
        path=next(directory.glob(patterns[issue]));path.write_bytes(path.read_bytes()+b' ')
    summary=ev.inspect(out)
    assert summary['unverified_task_artifacts'] and summary['counts']['successes']<10
