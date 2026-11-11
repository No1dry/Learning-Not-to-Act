"""Versioned teacher qualification and rejected-prefix CPU/fake regression."""
from copy import deepcopy
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from test_trajectory_generation import FakeSession,source,config

V2='table-drop-unknown-diagnostic-v2'


def frames(*,event='table_drop',value=None,domain='normal'):
    from egrs.augmentation.dependencies import activate_core
    activate_core(Path(__file__).resolve().parents[2]/'LIBERO-Remain-task033-r2')
    from benchmark.remaining_goals.nine_catalog import make_task_semantics
    semantics=make_task_semantics('bowl_drawer_close')
    def frame(goals):
        candidates={k:{} for k in ('wrong_grasp','wrong_placement','table_drop')}
        evidence=deepcopy(candidates)
        candidates[event]={'distractor':value};evidence[event]={'distractor':{'synthetic':True}}
        return {'facts':{'goals':goals,'invariant_values':[],'official_goal_values':goals,
            'official_success':all(goals),'required_open_values':[not goals[1]],'released':True,
            'tcp':{'site_id':0,'site_name':'grip','frame':'world','position':[0.,0.,0.]},
            'objects':{'distractor':{'role':'distractor','position':[0.,0.,0.],
                'released':True,'release_evidence':{}}},
            'event_candidates':candidates,'event_evidence':evidence},'a_regrasp':False}
    trace=[frame([True,False] if domain=='10' else [False,True])]+[frame([True,True]) for _ in range(5)]
    return trace,semantics


def test_teacher_v2_only_table_drop_unknown_is_diagnostic_and_none_unchanged():
    from egrs.trajectory_augmentation.native import qualify_frames
    trace,semantics=frames();before=deepcopy(trace)
    assert not qualify_frames(trace,'normal',semantics)['qualified']
    result=qualify_frames(trace,'normal',semantics,teacher_policy=V2)
    assert result['qualified'] and result['teacher_policy']==V2
    assert len(result['diagnostic_events'])==6
    assert result['diagnostic_events']==result['core_analysis']['event_unknown']
    assert trace==before
    assert trace[0]['facts']['event_candidates']['table_drop']['distractor'] is None


@pytest.mark.parametrize('event',['wrong_grasp','wrong_placement'])
def test_teacher_v2_other_unknown_still_rejected(event):
    from egrs.trajectory_augmentation.native import qualify_frames
    trace,semantics=frames(event=event)
    result=qualify_frames(trace,'normal',semantics,teacher_policy=V2)
    assert not result['qualified'] and result['failure_reason']=='core_violation_evidence_unknown'
    assert result['diagnostic_events']==[]


@pytest.mark.parametrize('event',['table_drop','wrong_grasp','wrong_placement'])
def test_teacher_v2_all_confirmed_events_still_rejected(event):
    from egrs.trajectory_augmentation.native import qualify_frames
    trace,semantics=frames(event=event,value=True)
    result=qualify_frames(trace,'normal',semantics,teacher_policy=V2)
    assert not result['qualified'] and result['failure_reason']=='confirmed_core_violation'
    assert result['core_analysis']['confirmed_events'][0]['event']==event


@pytest.mark.parametrize('broken',['unfinished','release','confirmation','initial','regression','regrasp','invariant'])
def test_teacher_v2_completion_release_and_a_protection_remain_required(broken):
    from egrs.trajectory_augmentation.native import qualify_frames
    trace,semantics=frames(domain='10')
    if broken=='unfinished':
        trace[-1]['facts'].update(goals=[True,False],official_goal_values=[True,False],official_success=False,
                                  required_open_values=[True])
    elif broken=='release':trace[-1]['facts']['released']=None
    elif broken=='confirmation':trace=trace[:-1]
    elif broken=='initial':trace[0]['facts'].update(goals=[False,False],official_goal_values=[False,False])
    elif broken=='regression':trace[1]['facts'].update(goals=[False,True],official_goal_values=[False,True],official_success=False)
    elif broken=='regrasp':trace[-1]['a_regrasp']=True
    else:
        # core semantics for this task have no invariants; use its independently
        # derived regression flag at the analysis boundary for this guard only.
        import benchmark.remaining_goals.headless.schema as schema
        original=schema.analyze_trace
        def invariant_analysis(*args,**kwargs):
            result=original(*args,**kwargs);result['invariant_regression']=True;return result
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(schema,'analyze_trace',invariant_analysis)
            assert not qualify_frames(trace,'10',semantics,teacher_policy=V2)['qualified']
        return
    assert not qualify_frames(trace,'10',semantics,teacher_policy=V2)['qualified']


def test_unknown_teacher_policy_is_rejected():
    from egrs.trajectory_augmentation.native import qualify_frames
    trace,semantics=frames()
    with pytest.raises(ValueError,match='teacher policy'):
        qualify_frames(trace,'normal',semantics,teacher_policy='unapproved')


def test_v2_failed_aligned_prefix_saved_but_v1_not_changed(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    for version in ('v1','v2'):
        cfg=config()
        if version=='v2':cfg['teacher_policy']=V2
        result=generate_session(FakeSession(failure=True),source(),cfg,tmp_path/version)
        attempt=result['attempts'][0]
        assert not attempt['qualified']
        if version=='v1':assert attempt['file'] is None
        else:
            assert attempt['teacher_policy']==V2
            assert attempt['qualification']['teacher_policy']==V2
            lineage=json.loads((tmp_path/version/attempt['lineage_path']).read_text())
            assert lineage['teacher_policy']==V2
            with h5py.File(tmp_path/version/attempt['file']) as h:
                g=h['data/demo_0']
                assert len(g['actions'])==3 and len(g['states'])==4
                assert len(g['obs/agentview_rgb'])==4


def test_v2_capture_failure_keeps_only_completed_transitions_and_zero_frame_has_no_hdf(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    for captured in (0,2):
        session=FakeSession();original=session.capture;calls=[]
        def capture():
            calls.append(True)
            if len(calls)>captured:raise RuntimeError('synthetic capture failure')
            return original()
        session.capture=capture;cfg={**config(),'teacher_policy':V2}
        result=generate_session(session,source(),cfg,tmp_path/str(captured))
        attempt=result['attempts'][0]
        assert not attempt['qualified']
        if captured==0:
            assert attempt['file'] is None and attempt['length']==0
        else:
            assert attempt['length']==1  # second outgoing action had no observed completion
            with h5py.File(tmp_path/str(captured)/attempt['file']) as h:
                g=h['data/demo_0'];assert len(g['actions'])==1 and len(g['states'])==2
            audit=json.loads((tmp_path/str(captured)/attempt['audit_path']).read_text())
            assert len(audit['steps'])==2 and len(audit['frames'])==2


def test_v2_rejected_prefix_is_not_indexed_for_training(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    from egrs.trajectory_augmentation.data import export_generated
    p=source();p.update(source_group='parent',physical_ancestry='unknown')
    result=generate_session(FakeSession(failure=True),p,{**config(),'teacher_policy':V2},tmp_path)
    assert result['attempts'][0]['file'] is not None
    report=export_generated([p],result['attempts'],tmp_path,tmp_path/'export')
    assert report['attempts']==1 and report['failed_attempts']==1 and report['qualified_trajectories']==0
    assert (tmp_path/'export/windows.jsonl').read_text()==''
