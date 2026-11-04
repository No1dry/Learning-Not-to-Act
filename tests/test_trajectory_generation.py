from copy import deepcopy
from types import SimpleNamespace
import json
import numpy as np
import h5py
import pytest
from test_trajectory_control import mapping


class FakeSession:
    """Environment boundary: exact Cartesian integrator, no real simulator."""
    def __init__(self, *, candidate=True, failure=False):
        self.candidate=candidate;self.failure=failure;self.steps=[];self.restores=[]
        self.action_spec=(np.full(7,-1.),np.ones(7))
        self.layout={'nq':3,'nv':3,'arm_qpos':[0],'arm_qvel':[0],
            'gripper_qpos':[],'gripper_qvel':[],'arm_limits':[[-2,2]],'gripper_open':[]}
        self.initial_state=np.zeros(7)
        self.source_actions=[np.array([.2,0,0,0,0,0,-1]) for _ in range(3)]
        self.controller=SimpleNamespace(use_delta=True,use_ori=True,impedance_mode='fixed',
            input_min=np.full(6,-1.),input_max=np.ones(6),output_min=np.full(6,-1.),output_max=np.ones(6),
            goal_pos=np.zeros(3),goal_ori=np.eye(3))
        self.inspection={'fake':True};self.sem=0
    def restore(self,state):
        self.state=np.asarray(state).copy();self.restores.append((len(self.steps),self.state.copy()))
    def pose(self):return np.array([self.state[1],0,0]),np.eye(3)
    def capture(self):
        p,r=self.pose()
        return {'state':self.state.copy(),'position':p,'rotation':r,
            'observation':{'obs/agentview_rgb':np.full((2,2,3),len(self.steps),np.uint8),
                'obs/eye_in_hand_rgb':np.zeros((2,2,3),np.uint8),'proprio':np.r_[p,np.zeros(5)]},
            'facts':{'goals':[bool(self.state[2]),bool(self.state[3])], 'invariant_values':[],
                'official_success':bool(self.state[2] and self.state[3]),'released':True},
            'hand_open':self.candidate,'held_free':False,'a_released':True,'a_regrasp':False,'penetration':False}
    def step(self,action):
        self.steps.append(action.copy());self.controller.goal_pos=self.pose()[0]+action[:3]
        self.state[0]+=.05
        if not self.failure:self.state[1]+=action[0]
        self.state[2]=float(self.state[2] or self.state[1]>=.19)
        self.state[3]=float(self.state[1]>=.59)
    def qualify(self,frames,domain):
        ok=frames[-1]['facts']['official_success'] and all(f['facts']['goals'][0] for f in frames) if domain=='10' else frames[-1]['facts']['official_success']
        ok=ok and frames[-1]['facts']['released'] is True
        return {'qualified':ok,'failure_reason':None if ok else 'unfinished','core_analysis':{'fake':True}}
    def close(self):pass


def source():
    m=mapping();m.update(images=['obs/agentview_rgb','obs/eye_in_hand_rgb'],proprio=['proprio'],
        observation_offset=0,action_offset=0,action='actions',instruction_binding={'group':'data','attribute':'language','json_key':None})
    return {'source_id':'parent','parent_demo_id':'parent','task_key':'basket','split':'train',
        'file_sha256':'a'*64,'instruction':'put both objects in basket','mapping':m}


def config():
    return {'recipe':{'name':'robot_rewind_v1','seed':7,'variants':3,'bridge_attempts':2,'horizon':30,
        'joint_perturbation_rad':.05,'position_tolerance_m':.005,'rotation_tolerance_deg':3.,
        'bridge_stage_steps':2,'lift_m':.1},'save_video':False}


def test_generator_executes_bridge_and_retargets_then_persists_tplusone(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    session=FakeSession();result=generate_session(session,source(),config(),tmp_path)
    assert len(result['attempts'])==4
    assert all(a['qualified'] for a in result['attempts'])
    assert len(session.restores)==4  # only initial replay and three episode starts
    for attempt in result['attempts']:
        with h5py.File(tmp_path/attempt['file']) as h:
            g=h['data/demo_0'];assert len(g['states'])==len(g['actions'])+1
            assert len(g['obs/agentview_rgb'])==len(g['actions'])+1
            np.testing.assert_allclose(g['actions'][:,6],-1)
        audit=json.loads((tmp_path/attempt['audit_path']).read_text())
        assert audit['steps'] and all('projection' in s for s in audit['steps'])
        if attempt['domain']=='10':
            assert audit['steps'][0]['phase']=='bridge'
            assert any(s['phase']=='continuation' for s in audit['steps'])
            assert audit['rewind']['nonrobot_before_sha256']==audit['rewind']['nonrobot_after_sha256']


def test_no_safe_handoff_reports_gap_without_fabricating_attempts(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    result=generate_session(FakeSession(candidate=False),source(),config(),tmp_path)
    assert len(result['attempts'])==1 and result['attempts'][0]['qualified']
    assert result['gaps']==['no_safe_handoff']


def test_failed_replay_is_retained_in_denominator_and_has_no_supervised_file(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    result=generate_session(FakeSession(failure=True),source(),config(),tmp_path)
    assert len(result['attempts'])==1
    a=result['attempts'][0];assert not a['qualified'] and a['file'] is None
    assert (tmp_path/a['audit_path']).is_file()
    assert result['gaps']==['normal_replay_unqualified']


def test_safe_handoff_rejects_holding_unknown_release_and_invariant_failure():
    from egrs.trajectory_augmentation.generation import safe_handoff
    s=FakeSession();s.restore(np.array([0,0,1,0,0,0,0]));f=s.capture()
    assert safe_handoff(f)
    for key,value in [('held_free',True),('a_released',None),('hand_open',False)]:
        assert not safe_handoff({**f,key:value})
    assert not safe_handoff({**f,'facts':{**f['facts'],'invariant_values':[False]}})


def test_two_bridge_failures_per_variant_are_bounded_and_retained(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    s=FakeSession();base=s.restore
    def restore(state):
        base(state)
        if len(s.restores)>1:s.failure=True
    s.restore=restore
    result=generate_session(s,source(),config(),tmp_path)
    assert len(result['attempts'])==7
    assert sum(a['qualified'] for a in result['attempts'])==1
    assert all(a['length']<=30 for a in result['attempts'])
    assert all((tmp_path/a['audit_path']).is_file() for a in result['attempts'])


def test_native_qualification_uses_core_without_forcing_normal_initial_mask():
    from pathlib import Path
    from egrs.augmentation.dependencies import activate_core
    from egrs.trajectory_augmentation.native import qualify_frames
    activate_core(Path(__file__).resolve().parents[2]/'LIBERO-Remain-task033-r2')
    from benchmark.remaining_goals.nine_catalog import make_task_semantics
    semantics=make_task_semantics('bowl_drawer_close')
    def frame(goals,release=True):
        return {'facts':{'goals':goals,'invariant_values':[],'official_goal_values':goals,
            'official_success':all(goals),'required_open_values':[not goals[1]],'released':release,
            'tcp':{'site_id':0,'site_name':'grip','frame':'world','position':[0.,0.,0.]},'objects':{},
            'event_candidates':{k:{} for k in ('wrong_grasp','wrong_placement','table_drop')},
            'event_evidence':{k:{} for k in ('wrong_grasp','wrong_placement','table_drop')}},'a_regrasp':False}
    frames=[frame([False,True]),frame([False,False])]+[frame([True,True]) for _ in range(5)]
    assert qualify_frames(frames,'normal',semantics)['qualified']
    assert not qualify_frames(frames,'10',semantics)['qualified']
    frames=[frame([True,False])]+[frame([True,True]) for _ in range(5)]
    assert qualify_frames(frames,'10',semantics)['qualified']
    frames[-1]['a_regrasp']=True
    assert not qualify_frames(frames,'10',semantics)['qualified']
    frames[-1]['a_regrasp']=False;frames[-1]['facts']['released']=None
    assert not qualify_frames(frames,'10',semantics)['qualified']


def test_actual_joint_addresses_drive_native_layout_instead_of_first_seven():
    from egrs.trajectory_augmentation.native import robot_layout
    model=SimpleNamespace(nq=12,nv=11,jnt_type=np.array([0,3,3,2,2]),
        jnt_qposadr=np.array([0,7,8,10,11]),jnt_dofadr=np.array([0,6,7,9,10]),
        jnt_range=np.array([[0,0],[-2,2],[-2,2],[0,.04],[-.04,0]]),
        jnt_limited=np.ones(5),joint_name2id=lambda n:{'a':1,'b':2,'l':3,'r':4}[n])
    robot=SimpleNamespace(robot_model=SimpleNamespace(joints=['a','b']),
        gripper=SimpleNamespace(joints=['l','r'],init_qpos=np.array([.02,-.02])))
    layout=robot_layout(SimpleNamespace(sim=SimpleNamespace(model=model),robots=[robot]))
    assert layout['arm_qpos']==[7,8] and layout['arm_qvel']==[6,7]
    assert layout['gripper_open']==[.04,-.04]


def test_interrupted_native_step_keeps_attempt_and_requested_action(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    s=FakeSession()
    def interrupted(action):raise KeyboardInterrupt('synthetic termination')
    s.step=interrupted
    with pytest.raises(KeyboardInterrupt):generate_session(s,source(),config(),tmp_path)
    metadata=list(tmp_path.glob('*/metadata.json'))
    assert len(metadata)==1
    a=json.loads(metadata[0].read_text());assert not a['qualified']
    journal=[json.loads(x) for x in (tmp_path/a['journal_path']).read_text().splitlines()]
    assert journal[0]['event']=='initial_state_requested'
    assert journal[-1]['event']=='action_requested'
    assert journal[-1]['step']['projection']['projected']==[.2,0.,0.,0.,0.,0.,-1.]


def test_fake_generation_exports_through_real_dataset_contract(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    from egrs.trajectory_augmentation.data import export_generated,GeneratedTrajectoryDataset
    from test_trajectory_data import mapping as full_mapping
    p=source();p.update(source_group='parent',physical_ancestry='unknown');p['mapping']=full_mapping()
    s=FakeSession();capture=s.capture
    def observed():
        f=capture();f['observation']['obs/ee_states']=np.r_[f['position'],np.zeros(3)]
        f['observation']['obs/gripper_states']=np.array([.04,-.04]);return f
    s.capture=observed
    result=generate_session(s,p,config(),tmp_path)
    report=export_generated([p],result['attempts'],tmp_path,tmp_path/'export')
    ds=GeneratedTrajectoryDataset(tmp_path/'export')
    assert report['qualified_trajectories']==4
    assert set(ds[0])=={'images','proprio','actions','action_mask','instruction'}
    assert ds[0]['proprio'].shape==(8,)
    assert all(s['mapping']['observation_offset']==0 for s in ds.sources.values())


def test_audit_confirmation_cannot_perform_missing_supervised_release(tmp_path):
    from egrs.trajectory_augmentation.generation import generate_session
    s=FakeSession();capture=s.capture
    def observed():
        f=capture();f['facts']['released']=len(s.steps)>3
        f['hand_open']=len(s.steps)>3;return f
    s.capture=observed
    result=generate_session(s,source(),config(),tmp_path)
    assert len(s.steps)==3  # Do not open a held object using audit-only HOLD.
    assert len(result['attempts'])==1 and not result['attempts'][0]['qualified']
    assert result['attempts'][0]['file'] is None


def test_worker_launch_timeout_counts_failed_normal_attempt(tmp_path,monkeypatch):
    import subprocess
    from egrs.trajectory_augmentation.generation import generate_source
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('fake-worker',1)
    monkeypatch.setattr(subprocess,'run',timeout)
    result=generate_source(source(),{'native_backend':{}},tmp_path,tmp_path/'output')
    assert len(result['attempts'])==1
    a=result['attempts'][0];assert a['domain']=='normal' and not a['qualified']
    assert 'TimeoutExpired' in a['failure_reason']
    assert (tmp_path/'output'/a['audit_path']).is_file()


def test_native_initializer_real_pins_with_fake_environment_boundary(tmp_path,monkeypatch):
    """Check the actual NativeSession entry using only a fake legacy env factory."""
    from pathlib import Path
    import sys
    import egrs
    from egrs.augmentation import progress_native
    from egrs.augmentation.data import identity,file_sha256
    from egrs.augmentation.dependencies import activate_core
    from egrs.trajectory_augmentation.native import NativeSession
    from test_trajectory_data import mapping as full_mapping
    sibling=Path(__file__).resolve().parents[2]
    activate_core(sibling/'LIBERO-Remain-task033-r2')
    from benchmark.remaining_goals.nine_catalog import get_task
    task=get_task('basket');m=full_mapping()
    stats=tmp_path/'stats.json'
    stats.write_text(json.dumps({'libero_10':{f:{k:m[f+'_normalization'][k] for k in ('q01','q99','mask')}
        for f in ('action','proprio')}}))
    for f in ('action','proprio'):m[f+'_normalization']['stats_sha256']=file_sha256(stats)
    parent=tmp_path/'parent.hdf5';parent.write_bytes(b'fake environment boundary source')
    args={'env_kwargs':{'controller_configs':{'type':'OSC_POSE'},'control_freq':20}}
    p=source();p.update(file=parent.name,file_sha256=file_sha256(parent),mapping=m,
        controller_binding={'type':'OSC_POSE','control_freq':20,'env_args_sha256':identity(args)})
    c=FakeSession().controller;c.eef_name='actual_controlled_site'
    model=SimpleNamespace(nq=4,nv=4,jnt_type=np.array([3,3,2,2]),jnt_qposadr=np.arange(4),
        jnt_dofadr=np.arange(4),jnt_range=np.array([[-2,2],[-2,2],[0,.04],[-.04,0]]),
        jnt_limited=np.ones(4),joint_name2id=lambda n:{'a':0,'b':1,'l':2,'r':3}[n],
        site_name2id=lambda n:0 if n=='actual_controlled_site' else -1)
    robot=SimpleNamespace(controller=c,robot_model=SimpleNamespace(joints=['a','b']),
        gripper=SimpleNamespace(joints=['l','r'],init_qpos=np.array([.02,-.02])))
    env=SimpleNamespace(robots=[robot],sim=SimpleNamespace(model=model,data=SimpleNamespace(
        site_xpos=np.array([[.1,.2,.3]]),site_xmat=np.eye(3).reshape(1,9))),control_freq=20,
        action_dim=7,action_spec=(np.full(7,-1.),np.ones(7)))
    closed=[]
    legacy=SimpleNamespace(env=env,episode=SimpleNamespace(env_args=args,T=3,state=lambda i:np.zeros(9),
        action=lambda i:np.array([.2,0,0,0,0,0,-1])),full_atoms=task['official_goal_predicates'],
        inspection={'runtime_xml_sha256':'b'*64},close=lambda:closed.append(True))
    monkeypatch.setattr(progress_native,'_runtime',lambda *a,**k:legacy)
    monkeypatch.setattr(egrs,'__path__',list(egrs.__path__))
    monkeypatch.setitem(sys.modules,'egrs.core',None)
    cfg={'benchmark_root':str(sibling/'LIBERO-Remain-task033-r2'),
        'native_backend':{'historical_root':str(sibling/'Learning-Not-to-Act-task016')},
        'stats_path':str(stats),'stats_sha256':file_sha256(stats),'unnorm_key':'libero_10',
        'bindings':{'basket':{'orientation':'opengl','active_goals':[{'id':str(i),'predicate':g['predicates'][0]} for i,g in enumerate(task['goals'])],
            'invariant_predicates':task['invariant_predicates']}}}
    session=NativeSession(p,cfg,tmp_path)
    assert session.inspection['core_revision']=='d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9'
    assert len(session.source_actions)==3
    np.testing.assert_equal(session.pose()[0],[.1,.2,.3])
    session.close();assert closed==[True]
    p['controller_binding']['env_args_sha256']='0'*64
    with pytest.raises(ValueError,match='controller binding'):NativeSession(p,cfg,tmp_path)
    assert closed==[True,True]
