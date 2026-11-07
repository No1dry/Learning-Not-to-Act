"""CPU-only executable release closure around the original Attempt recorder."""
from copy import deepcopy
from types import SimpleNamespace
import json

import h5py
import numpy as np
import pytest

from egrs.trajectory_augmentation.generation import Attempt
from egrs.trajectory_augmentation.native import TEACHER_V2
from test_trajectory_generation import source


class ClosureSession:
    def __init__(self, *, release_after=2, release_unknown=False, fault=None):
        self.action_spec=(np.full(7,-1.),np.ones(7))
        self.controller=SimpleNamespace(use_delta=True,use_ori=True,impedance_mode='fixed',
            input_min=np.full(6,-1.),input_max=np.ones(6),output_min=np.full(6,-1.),
            output_max=np.ones(6),goal_pos=np.zeros(3),goal_ori=np.eye(3))
        self.state=np.zeros(9);self.state[3]=.2
        self.calls=[];self.inspection={'fake':True};self.release_after=release_after
        self.release_unknown=release_unknown;self.fault=fault

    def restore(self,state):self.state=np.asarray(state).copy()
    def pose(self):return self.state[1:4].copy(),np.eye(3)

    def step(self,action):
        if self.fault=='controller_exception' and len(self.calls)==1:raise ValueError('fake_control_failure')
        self.calls.append(np.asarray(action).copy());self.state[0]+=.05
        self.state[1:4]+=action[:3]
        self.controller.goal_pos=self.state[1:4].copy()

    def capture(self):
        n=len(self.calls);p,r=self.pose()
        released=None if self.release_unknown else bool(n>=self.release_after)
        goals=[True,True];invariants=[True];regrasp=False
        if n>=2 and self.fault=='A_regressed':goals[0]=False
        if n>=2 and self.fault=='K_regressed':invariants=[False]
        if n>=2 and self.fault=='regrasp_unknown':regrasp=None
        return {'state':self.state.copy(),'position':p,'rotation':r,
            'observation':{'obs/agentview_rgb':np.full((2,2,3),n,np.uint8),
                'obs/eye_in_hand_rgb':np.full((2,2,3),n,np.uint8),'proprio':np.r_[p,np.zeros(5)]},
            'facts':{'goals':goals,'official_success':all(goals),'invariant_values':invariants,
                'released':released},'hand_open':bool(n>=2),'held_free':False,
            'a_released':True,'a_regrasp':regrasp,
            'penetration':bool(n>=2 and self.fault=='penetration')}

    def qualify(self,frames,domain):
        streak=0
        for f in frames:
            streak=streak+1 if f['facts']['official_success'] and f['facts']['released'] is True else 0
        violation=any(i>=2 and self.fault=='event' for i in range(len(self.calls)+1))
        ok=streak>=5 and not violation
        return {'qualified':ok,'failure_reason':None if ok else 'original_release_unproven',
            'teacher_policy':TEACHER_V2,'core_release_confirmation_streak':streak,
            'core_analysis':{'confirmed_events':[{'event':'wrong_grasp'}] if violation else []}}


def attempt(tmp_path, **kwargs):
    session=ClosureSession(**kwargs)
    a=Attempt(session,source(),{'teacher_policy':TEACHER_V2,'recipe':{'horizon':520}},
        tmp_path,'normal','normal',0)
    a.begin(session.state.copy());a.step(np.zeros(7),'source_replay')
    return a


def test_release_is_executed_and_all_closure_transitions_are_supervised(tmp_path):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path)
    result=finish_attempt(a)
    assert result['qualified'] and len(a.actions)==6  # step 2..6 are the five true observations
    assert len(a.frames)==7 and not a.confirmation
    assert all(s['audit_only'] is False for s in a.steps)
    assert all(x[6]==-1 for x in a.actions[1:])
    assert result['teacher_policy']==TEACHER_V2
    assert result['closure_summary']['algorithm']=='physical_release_clearance_v3'
    with h5py.File(tmp_path/result['file']) as h:
        g=h['data/demo_0']
        assert len(g['states'])==7 and len(g['actions'])==6
        assert g['obs/agentview_rgb'][-1,0,0,0]==6
        np.testing.assert_array_equal(g['actions'],a.actions)
        np.testing.assert_allclose(g['controller_goal_pos'][-1],a.frames[-1]['position'])
    assert json.loads((tmp_path/result['audit_path']).read_text())['confirmation_frames']==[]


def test_already_confirmed_frames_stop_without_four_hidden_actions(tmp_path):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=0)
    for _ in range(3):a.step(np.zeros(7),'source_replay')
    assert len(a.frames)==5
    result=finish_attempt(a)
    assert result['qualified'] and len(a.actions)==4
    assert result['closure_summary']['added_steps']==0


@pytest.mark.parametrize('unknown', [False,True])
def test_missing_release_has_forty_real_steps_and_never_becomes_success(tmp_path,unknown):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1000,release_unknown=unknown)
    result=finish_attempt(a)
    assert not result['qualified'] and result['failure_reason']=='original_release_unproven'
    assert len(a.actions)==41 and len(a.frames)==42
    phases=[s['phase'] for s in a.steps[1:]]
    assert phases==['teacher_release_open']*10+['teacher_release_retreat']*20+['teacher_release_hold']*10
    positions=np.array([s['reference_target']['position'] for s in a.steps[1:]])
    np.testing.assert_allclose(positions[:10],np.tile([0,0,.2],(10,1)))
    np.testing.assert_allclose(positions[10:30,2],np.arange(1,21)*.005+.2)
    np.testing.assert_allclose(positions[30:],np.tile([0,0,.3],(10,1)))
    assert max(positions[:,2])<=.3+1e-12


@pytest.mark.parametrize('start,horizon,added',[(519,520,1),(520,520,0),(2,3,1),(519,900,1)])
def test_episode_horizon_caps_all_real_closure_steps(tmp_path,start,horizon,added):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1000)
    for _ in range(start-1):a.step(np.zeros(7),'source_replay')
    a.recipe['horizon']=horizon
    result=finish_attempt(a)
    assert not result['qualified'] and len(a.steps)==start+added
    assert result['closure_summary']['added_steps']==added


@pytest.mark.parametrize('fault,reason',[
    ('A_regressed','completed_A_regressed'),('K_regressed','holding_constraint_regressed'),
    ('regrasp_unknown','A_transport_regrasp_or_unknown'),('penetration','penetration'),
    ('event','confirmed_core_violation'),('controller_exception','fake_control_failure')])
def test_each_closure_step_stops_on_original_guard_or_violation(tmp_path,fault,reason):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1000,fault=fault);a.domain='10'
    result=finish_attempt(a)
    assert not result['qualified'] and reason in result['failure_reason']
    assert len(a.steps)==2
    assert len(a.frames)==len(a.actions)+1  # interrupted outgoing step stays audit-only


@pytest.mark.parametrize('blocker', ['unfinished','error','prior_violation','prior_penetration'])
def test_existing_failure_prefix_is_never_repaired_by_closure(tmp_path,blocker):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1000)
    if blocker=='unfinished':a.frames[-1]['facts']['official_success']=False
    elif blocker=='error':a.error='prior_control_exception'
    elif blocker=='prior_violation':a.session.fault='event';a.session.calls.append(np.zeros(7))
    else:a.frames[0]['penetration']=True
    result=finish_attempt(a)
    assert not result['qualified'] and len(a.steps)==1


def test_continuation_streak_is_used_without_restart(tmp_path):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1)
    for _ in range(2):a.step(np.zeros(7),'continuation')
    result=finish_attempt(a)
    assert result['qualified'] and len(a.actions)==5
    assert result['closure_summary']['added_steps']==2


@pytest.mark.parametrize('goal', [False,None])
def test_official_success_does_not_override_explicit_nontrue_native_goal(tmp_path,goal):
    from egrs.coverage039.teacher import finish_attempt
    a=attempt(tmp_path,release_after=1000)
    a.frames[-1]['facts']['goals']=[True,goal]
    result=finish_attempt(a)
    assert not result['qualified'] and len(a.actions)==1


@pytest.mark.parametrize('unknown_release,event,expected',[(True,'table_drop',False),
    (False,'table_drop',True),(False,'wrong_grasp',False)])
def test_original_core_qualifier_keeps_unknown_evidence_and_v2_policy(tmp_path,unknown_release,event,expected):
    from egrs.coverage039.teacher import finish_attempt
    from egrs.trajectory_augmentation.native import qualify_frames
    from test_trajectory_teacher_v2 import frames
    template,semantics=frames(event=event)
    session=ClosureSession(release_unknown=unknown_release)
    capture=session.capture
    def observed():
        f=capture();physical=f['facts'];facts=deepcopy(template[-1]['facts'])
        facts.update(physical,official_goal_values=physical['goals'],invariant_values=[],
            required_open_values=[not physical['goals'][1]])
        f['facts']=facts
        return f
    session.capture=observed
    session.qualify=lambda fs,domain:qualify_frames(fs,domain,semantics,teacher_policy=TEACHER_V2)
    a=Attempt(session,source(),{'teacher_policy':TEACHER_V2},tmp_path,'normal','normal',0)
    a.begin(session.state.copy());a.step(np.zeros(7),'source_replay')
    result=finish_attempt(a)
    assert result['qualified'] is expected
    assert result['qualification']['teacher_policy']==TEACHER_V2
    if unknown_release:
        assert a.frames[-1]['facts']['released'] is None
        assert result['qualification']['core_release_confirmation_streak']==0
    if event=='wrong_grasp':assert 'core_violation_evidence_unknown' in result['failure_reason']
