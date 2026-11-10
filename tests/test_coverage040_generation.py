"""040 orchestration spends durable slots before its only native fake boundary."""
from copy import deepcopy
from pathlib import Path

import pytest

from egrs.augmentation.data import file_sha256, read_json
from test_coverage040_plan import prepared040


def test_initialization_failures_spend_only_selected_train_parents_and_bind_export(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    from egrs.coverage039.generation import AttemptLedger
    path,old=prepared040(tmp_path,monkeypatch);plan=build_plan(path)
    seen=[]
    def failed(source,config,root,directory):
        ledger=AttemptLedger(config['_budget_ledger'])
        assert ledger.contains(source['source_id'],'normal','normal',0)
        assert source['split']=='train' and source['demo_index'] in range(20,40)
        seen.append(source['source_id']);raise RuntimeError('fake initialization unavailable')
    out=tmp_path/'production';report=generate(path,out,source_generator=failed,plan=plan)
    assert seen==[p['source_id'] for p in plan['sources']]
    assert report['spent']['normal_attempts']==len(seen) and report['spent']['ten_attempts']==0
    assert report['source_errors']==len(seen) and report['completion_percent']==100
    manifest=read_json(Path(report['export'])/'sources.json')
    assert manifest['parents'][:180]==old and len(manifest['parents'])==240
    binding=manifest['generation_context']['coverage040']
    assert binding['selected_train_parent_ids']==seen
    assert binding['plan_sha256']==file_sha256(binding['plan_path'])
    assert binding['ledger_sha256']==file_sha256(binding['ledger_path'])
    assert binding['train_only'] and binding['newnormal_role']=='pair_only'
    attempts=read_json(Path(report['export'])/'attempts.json')
    assert len(attempts)==len(seen)
    for a in attempts:
        assert a['generation_context']['coverage040']==binding
        lineage=read_json(out/a['lineage_path'])
        assert lineage['generation_context']['coverage040']==binding
        assert lineage['generator_algorithm']=='physical_release_clearance_v3'
        audit=read_json(out/a['audit_path'])
        assert audit['generation_context']['coverage040']==binding
    with pytest.raises(FileExistsError): generate(path,out,source_generator=failed,plan=plan)


def test_overlap_refused_before_any_attempt(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path)
    for directory in (tmp_path/'raw/new-output',tmp_path/'old-artifacts/new-output'):
        with pytest.raises(ValueError,match='overlap'):
            generate(path,directory,plan=plan,source_generator=lambda *a:pytest.fail('native called'))
        assert not directory.exists()


def test_fake_recordings_keep039_physical_control_and_add040_context(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    from egrs.coverage039.generation import generate_session
    from test_coverage039_generation import ClosureSession
    from test_trajectory_generation import config as fake_config
    from egrs.trajectory_augmentation.native import TEACHER_V2
    from egrs.augmentation.data import identity
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path)
    recorded_parent=next(p['source_id'] for p in plan['sources'] if p['task_key']=='stove')
    class FullObservationSession(ClosureSession):
        def capture(self):
            frame=super().capture();proprio=frame['observation']['proprio']
            frame['observation'].update({'obs/ee_states':proprio[:6], 'obs/gripper_states':proprio[6:]})
            return frame
    def recorded(source,cfg,root,directory):
        if source['source_id']!=recorded_parent: raise RuntimeError('fake unavailable parent')
        execution=fake_config();execution['teacher_policy']=TEACHER_V2
        execution.update({k:v for k,v in cfg.items() if k.startswith('_')})
        return generate_session(FullObservationSession(),source,execution,directory)
    report=generate(path,tmp_path/'recordings',source_generator=recorded,plan=plan)
    export=read_json(Path(report['export'])/'sources.json')
    assert report['actual_new_train_10']>0
    assert {s['domain'] for s in export['sources'].values()}=={'normal','10'}
    for source in export['sources'].values():
        assert source['split']=='train'
        assert source['recipe']['coverage040']==source['generation_context']['coverage040']
        assert source['recipe_identity']==identity(source['recipe'])
        assert source['teacher_policy']==TEACHER_V2


def test_interrupted_source_is_spent_and_never_runs_later_parents(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path);out=tmp_path/'interrupted'
    def interrupted(source,cfg,root,directory): raise KeyboardInterrupt('fake user termination')
    with pytest.raises(KeyboardInterrupt): generate(path,out,plan=plan,source_generator=interrupted)
    ledger=read_json(out/'attempt_ledger.json')
    assert ledger['normal_attempts']==1 and ledger['ten_attempts']==0 and len(ledger['slots'])==1
    assert ledger['slots'][0]['source_id']==plan['sources'][0]['source_id']
    report=read_json(out/'generation_report.json')
    assert report['status']=='interrupted' and report['processed_sources']==1
    assert len(read_json(out/'export/attempts.json'))==1
    with pytest.raises(FileExistsError): generate(path,out,plan=plan,source_generator=interrupted)


def test_raw_change_after_plan_rejected_before_source_creation(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path)
    target=Path(plan['data_root'])/plan['sources'][0]['file']
    with target.open('ab') as stream: stream.write(b'changed after planning')
    with pytest.raises(ValueError,match='SHA|stat'):
        generate(path,tmp_path/'changed',plan=plan,source_generator=lambda *a:pytest.fail('native called'))
    assert not (tmp_path/'changed').exists()


def test_resealed_plan_cannot_omit_selected_representatives(tmp_path,monkeypatch):
    from egrs.coverage040.plan import build_plan
    from egrs.coverage040.generation import generate
    from egrs.augmentation.data import identity
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path)
    plan['sources']=plan['sources'][:1];plan['identity']=identity(plan)
    with pytest.raises(ValueError,match='fixed|representative'):
        generate(path,tmp_path/'partial',plan=plan,source_generator=lambda *a:pytest.fail('native called'))


def test_parent_heartbeat_reports_overall_percent_current_controls_and_live_budget(tmp_path):
    from egrs.coverage040.generation import GenerationHeartbeat
    from egrs.coverage039.generation import AttemptLedger, durable_write
    ledger=AttemptLedger(tmp_path/'ledger.json');ledger.reserve('parent','normal','normal',0)
    heartbeat=GenerationHeartbeat(tmp_path,'parent',ledger,completed=2,total=5)
    durable_write(tmp_path/'heartbeat.json',{'phase':'bridge','controls':17,'attempt':'10/v0/a0'})
    ledger.reserve('parent','10',0,0);heartbeat._emit()
    record=read_json(tmp_path/'parent_heartbeat.json')
    assert record['completed']==2 and record['total']==5 and record['percent']==40
    assert record['normal_attempts']==1 and record['ten_attempts']==1
    assert record['max_normal_replays']==60 and record['max_10_attempts']==360
    assert record['phase']=='bridge' and record['controls']==17


def test_default_launcher_interrupt_reaps_child_before_recovery_and_export(tmp_path,monkeypatch):
    import subprocess
    from egrs.coverage040 import generation
    from egrs.coverage040.plan import build_plan
    path,_=prepared040(tmp_path,monkeypatch);plan=build_plan(path);events=[]
    class Worker:
        stopped=False
        def poll(self): return -9 if self.stopped else None
        def wait(self,timeout=None):
            if not self.stopped: raise KeyboardInterrupt('parent-only SIGINT')
            events.append('waited');return -9
        def kill(self): self.stopped=True;events.append('killed')
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:Worker())
    recover=generation._recover_source;export=generation.export_generated
    def recovered(*args,**kwargs):
        assert events[-2:]==['killed','waited']
        events.append('recovered');return recover(*args,**kwargs)
    def exported(*args,**kwargs):
        assert 'waited' in events and events.index('waited')<events.index('recovered')
        events.append('exported');return export(*args,**kwargs)
    monkeypatch.setattr(generation,'_recover_source',recovered)
    monkeypatch.setattr(generation,'export_generated',exported)
    output=tmp_path/'parent-interrupt'
    with pytest.raises(KeyboardInterrupt,match='parent-only SIGINT'):
        generation.generate(path,output,plan=plan)
    assert events==['killed','waited','recovered','exported']
    assert read_json(output/'attempt_ledger.json')['normal_attempts']==1
    assert read_json(output/'generation_report.json')['status']=='interrupted'


@pytest.mark.parametrize('outcome',['success','failure','keyboard','system_exit','cleanup_failure'])
def test040_launcher_preserves_literal_interpreter_and_original_worker_contract(tmp_path,monkeypatch,outcome):
    import subprocess
    from egrs.coverage040 import generation
    from egrs.coverage039.generation import durable_write
    from egrs.trajectory_augmentation.native import TEACHER_V2
    from test_trajectory_generation import source
    parent=source();literal=str(tmp_path/'venv-symlink'/'python');commands=[];events=[]
    resolve=Path.resolve
    def linked_resolution(self,*args,**kwargs):
        if str(self)==literal: return tmp_path/'base-interpreter'
        return resolve(self,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',linked_resolution)
    class Worker:
        stopped=False
        def poll(self): return -9 if self.stopped else None
        def wait(self,timeout=None):
            if self.stopped: events.append('waited');return -9
            if outcome in ('keyboard','cleanup_failure'): raise KeyboardInterrupt('launcher interrupt')
            if outcome=='system_exit': raise SystemExit('launcher shutdown')
            if outcome=='failure': raise RuntimeError('worker transport failure')
            return 0
        def kill(self):
            if outcome=='cleanup_failure': raise OSError('fake kill denied')
            self.stopped=True;events.append('killed')
    def launch(command,**kwargs):
        commands.append(command)
        request=read_json(command[-1])
        assert request['config']['teacher_policy']==TEACHER_V2
        assert request['config']['native_backend']['python']==literal
        assert request['source']==parent
        durable_write(tmp_path/'result.json',{'source_id':parent['source_id'],'attempts':[],'fake_result':True})
        return Worker()
    monkeypatch.setattr(subprocess,'Popen',launch)
    cfg={'native_backend':{'python':literal,'source_timeout_seconds':5},'recipe':{'untouched':'config'}}
    if outcome=='cleanup_failure':
        with pytest.raises(generation.WorkerCleanupFailure,match='kill denied'):
            generation.generate_source(parent,cfg,tmp_path/'raw',tmp_path)
        # Cleanup failure bypasses the ordinary Exception/KeyboardInterrupt
        # recovery handler, so no immutable export is claimed with a live child.
        assert not issubclass(generation.WorkerCleanupFailure,Exception)
    elif outcome in ('keyboard','system_exit'):
        exception=KeyboardInterrupt if outcome=='keyboard' else SystemExit
        with pytest.raises(exception): generation.generate_source(parent,cfg,tmp_path/'raw',tmp_path)
        assert events==['killed','waited']
    else:
        result=generation.generate_source(parent,cfg,tmp_path/'raw',tmp_path)
        if outcome=='success': assert result['fake_result'] and events==[]
        else:
            assert result['source_id']==parent['source_id'] and 'transport failure' in result['error']
            assert events==['killed','waited']
    assert commands[0][:4]==[literal,'-m','egrs.coverage039.native','--request']
    assert cfg=={'native_backend':{'python':literal,'source_timeout_seconds':5},'recipe':{'untouched':'config'}}
