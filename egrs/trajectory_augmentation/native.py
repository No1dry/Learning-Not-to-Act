"""Isolated pinned historical initializer plus fixed d854 physical observers.

Importing this module is CPU-only. Native construction occurs solely when the
explicit user-launched worker creates NativeSession. No model is ever loaded.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import types
import numpy as np


def robot_layout(env):
    """Resolve scalar arm/finger coordinates from actual compiled named joints."""
    if len(env.robots)!=1:raise ValueError('one original Panda robot required')
    robot=env.robots[0];model=env.sim.model
    def coordinates(names,kind):
        ids=[int(model.joint_name2id(n)) for n in names]
        if len(set(ids))!=len(ids) or any(i<0 or int(model.jnt_type[i])!=kind or not model.jnt_limited[i] for i in ids):
            raise ValueError('unsupported original robot joint layout')
        return ([int(model.jnt_qposadr[i]) for i in ids],[int(model.jnt_dofadr[i]) for i in ids],
                [[float(x) for x in model.jnt_range[i]] for i in ids])
    aq,av,limits=coordinates(robot.robot_model.joints,3)
    gq,gv,glimits=coordinates(robot.gripper.joints,2)
    initial=np.asarray(robot.gripper.init_qpos)
    if len(gq)!=2 or initial.shape!=(2,) or not initial[0]>0>initial[1]:
        raise ValueError('requires original two-finger Panda open direction')
    return {'nq':int(model.nq),'nv':int(model.nv),'arm_qpos':aq,'arm_qvel':av,
        'gripper_qpos':gq,'gripper_qvel':gv,'arm_limits':limits,
        'gripper_open':[glimits[0][1],glimits[1][0]],
        'arm_joints':list(robot.robot_model.joints),'gripper_joints':list(robot.gripper.joints)}


def qualify_frames(frames,domain,semantics):
    """Use core endpoints/events; normal never has a fabricated mask00 initial."""
    from benchmark.remaining_goals.headless.schema import analyze_trace
    trace=[{'step':i,**deepcopy(f['facts'])} for i,f in enumerate(frames)]
    analysis=analyze_trace(trace,protocol='nine-mask10' if domain=='10' else 'nine-normal00',task_semantics=semantics)
    # Ordinary demonstrations still need teacher release confirmation. The
    # unchanged core mask10 analyzer provides that streak, but its preservation
    # fields are deliberately NOT used for ordinary complete-task replay.
    confirmation=analyze_trace(trace,protocol='nine-mask10',task_semantics=semantics)
    reasons=[]
    if not frames or not frames[-1]['facts']['official_success']:reasons.append('native_full_task_unfinished')
    if not confirmation['frames'] or confirmation['frames'][-1]['completion_streak']<5:
        reasons.append('release_or_continuous_confirmation_unproven')
    if analysis['confirmed_events']:reasons.append('confirmed_core_violation')
    if analysis['event_unknown']:reasons.append('core_violation_evidence_unknown')
    if domain=='10':
        from benchmark.remaining_goals.nine_catalog import initial_constraints_match
        if not frames or frames[0]['facts']['goals']!=[True,False] or not initial_constraints_match(frames[0]['facts']):
            reasons.append('initial_mask10_or_holding_constraints_invalid')
        if analysis['goal_regression'] or analysis['invariant_regression']:reasons.append('A_or_invariant_regression')
        if any(f['a_regrasp'] is not False for f in frames):reasons.append('A_transport_regrasp_or_unknown')
    return {'qualified':not reasons,'failure_reason':';'.join(reasons) or None,
        'core_analysis':{k:v for k,v in analysis.items() if k!='frames'},
        'core_release_confirmation_streak':confirmation['frames'][-1]['completion_streak'] if frames else 0,
        'domain':domain,'initial_facts':frames[0]['facts'] if frames else None,
        'normal_initial_preservation_applicable':False if domain=='normal' else None}


def _binding(source,config):
    bindings=config.get('bindings',{})
    binding=source.get('native_binding',bindings.get(source['source_id'],bindings.get(source['task_key'])))
    if not isinstance(binding,dict):raise ValueError('explicit source/task native goal binding required')
    return deepcopy(binding)


def validate_original_stats(source,config):
    from egrs.augmentation.data import file_sha256,read_json
    path=Path(config['stats_path'])
    if file_sha256(path)!=config['stats_sha256']:raise ValueError('original SOG10 stats hash changed')
    original=read_json(path)[config['unnorm_key']]
    for field in ('action','proprio'):
        norm=source['mapping'][field+'_normalization']
        if norm['stats_id']!=config['unnorm_key'] or norm['stats_sha256']!=config['stats_sha256']:
            raise ValueError('source mapping stats identity differs')
        if norm['kind']!='bounds_q99':raise ValueError('native raw generation requires original bounds_q99 mappings')
        for key in ('q01','q99','mask'):
            expected=original[field].get(key,[True]*len(norm['mask']) if key=='mask' else None)
            if not np.array_equal(norm[key],expected):raise ValueError('source mapping differs from original '+field+'.'+key)


class NativeSession:
    def __init__(self,source,config,data_root):
        from egrs.augmentation.data import file_sha256,identity
        from egrs.augmentation.dependencies import activate_core
        from egrs.augmentation.progress_native import inspect_dependency,_runtime
        self.session=None;self.source=deepcopy(source);self.config=deepcopy(config)
        validate_original_stats(source,config)
        root=Path(data_root).resolve(strict=True);file=(root/source['file']).resolve(strict=True)
        if not file.is_relative_to(root) or file_sha256(file)!=source['file_sha256']:
            raise ValueError('parent source HDF identity differs')
        backend=deepcopy(config['native_backend']);dep=inspect_dependency(backend['historical_root'])
        revision=activate_core(config['benchmark_root'])
        # Historical initialization imports egrs.core.activate internally. Bind
        # that one entry to the verified current fixed core inside this isolated
        # process, without changing historical files or broadening accepted API.
        import egrs
        historical=str(Path(dep['root'])/'egrs')
        if historical not in egrs.__path__:egrs.__path__.append(historical)
        bridge=types.ModuleType('egrs.core')
        def activate(_):
            actual=activate_core(config['benchmark_root'])
            if actual!=revision:raise ValueError('fixed core identity changed')
            return {'revision':actual,'root':str(Path(config['benchmark_root']).resolve()),
                    'bridge':'task035 historical initializer; fixed d854 core override'}
        bridge.activate=activate;sys.modules['egrs.core']=bridge
        for path in reversed(backend.get('module_paths',[])):
            resolved=Path(path).expanduser().resolve(strict=True)
            if not resolved.is_dir():raise ValueError('native module path must be a directory')
            sys.path.append(str(resolved))
        binding=_binding(source,config);self.binding=binding
        try:
            self.session=_runtime(backend,source,root,binding,[g['id'] for g in binding['active_goals']])
            self.env=self.session.env;self.controller=self.env.robots[0].controller
            args=self.session.episode.env_args;declared=source['controller_binding'];kwargs=args['env_kwargs']
            if (declared['type']!='OSC_POSE' or kwargs['controller_configs']['type']!='OSC_POSE'
                or kwargs['control_freq']!=declared['control_freq'] or self.env.control_freq!=declared['control_freq']
                or identity(args)!=declared['env_args_sha256']):raise ValueError('original controller binding differs')
            if not self.controller.use_delta or not self.controller.use_ori or self.controller.impedance_mode!='fixed':
                raise ValueError('requires original fixed delta OSC_POSE')
            if self.env.action_dim!=7:raise ValueError('requires original 7D environment action interface')
            from benchmark.remaining_goals.nine_catalog import get_task,make_task_semantics
            self.profile=get_task(source['task_key']);self.semantics=make_task_semantics(source['task_key'],self.session.full_atoms)
            if ([g['predicate'] for g in binding['active_goals']]!=[g['predicates'][0] for g in self.profile['goals']]
                or binding['invariant_predicates']!=self.profile['invariant_predicates']):
                raise ValueError('source A/B/invariant binding differs from fixed nine-task native semantics')
            self.layout=robot_layout(self.env);self.action_spec=self.env.action_spec
            self.initial_state=self.session.episode.state(0)
            self.source_actions=[self.session.episode.action(i) for i in range(self.session.episode.T)]
            self.inspection={**deepcopy(self.session.inspection),'historical_dependency':dep,'core_revision':revision,
                'controller_binding':declared,'joint_layout':self.layout,
                'source_replay':'complete physical source from state0/action0; no old RGB alignment certification',
                'fresh_image_convention':binding['orientation']}
            self.a_objects=[p[1] for p in self.profile['goals'][0]['predicates'] if p[0].lower() in ('in','on')]
            self.measurements=None
        except BaseException:self.close();raise

    def restore(self,state):
        from benchmark.remaining_goals.headless.environment import HeadlessMeasurements
        self.session.restore(self.env,np.asarray(state).copy())
        self.env.done=False;self.env.timestep=0
        self.measurements=HeadlessMeasurements(self.env,self.source['task_key'],
            source_reset_model_xml_sha256=self.inspection['runtime_xml_sha256'],task_semantics=self.semantics)

    def pose(self):
        sim=self.env.sim;sid=int(sim.model.site_name2id(self.controller.eef_name))
        if sid<0:raise ValueError('original controlled end effector site missing')
        return np.array(sim.data.site_xpos[sid],copy=True),np.array(sim.data.site_xmat[sid],copy=True).reshape(3,3)

    def _penetration(self):
        model,data=self.env.sim.model,self.env.sim.data
        root=int(model.body_name2id(self.env.robots[0].robot_model.root_body))
        def robot_geom(gid):
            bid=int(model.geom_bodyid[gid])
            while bid>0:
                if bid==root:return True
                bid=int(model.body_parentid[bid])
            return False
        return any(float(data.contact[i].dist)<-.005
            and robot_geom(int(data.contact[i].geom1))!=robot_geom(int(data.contact[i].geom2)) for i in range(data.ncon))

    def capture(self):
        from benchmark.remaining_goals.nine_catalog import read_goal_facts
        from benchmark.remaining_goals.headless.environment import validate_evaluator_evidence
        from robosuite.utils.transform_utils import quat2axisangle
        import robosuite.macros as macros
        raw=self.session.refresh(self.env)
        goals=read_goal_facts(self.session.inner._eval_predicate,self.session.inner._check_success(),self.semantics)
        facts=self.measurements.evaluator_state(goals['goals'],goal_facts=goals)
        validate_evaluator_evidence(facts,self.measurements.static)
        # Preserve original source pixel convention, then the existing mapping
        # applies the original SOG10 image transform exactly once on read.
        native_convention=macros.IMAGE_CONVENTION
        if native_convention not in ('opengl','opencv'):raise ValueError('unknown live image convention')
        images=[np.array(raw[k],copy=True) for k in ('agentview_image','robot0_eye_in_hand_image')]
        if native_convention!=self.binding['orientation']:images=[im[::-1].copy() for im in images]
        position=np.asarray(raw['robot0_eef_pos']);orientation=quat2axisangle(np.asarray(raw['robot0_eef_quat']))
        gripper=np.asarray(raw['robot0_gripper_qpos'])
        fields={'obs/ee_pos':position,'obs/ee_ori':orientation,'obs/ee_states':np.r_[position,orientation],
                'obs/gripper_states':gripper,'proprio':np.r_[position,orientation,gripper]}
        mapping=self.source['mapping'];obs=dict(zip(mapping['images'],images))
        obs.update({key:np.array(fields[key],copy=True) for key in mapping['proprio']})
        if sum(obs[k].size for k in mapping['proprio'])!=8:raise ValueError('fresh original proprio must contain eight scalars')
        movable=[n for n,r in self.measurements.roles['roles'].items() if r['movable']]
        grasps={n:facts['objects'][n]['raw_evidence']['legacy_release_evidence'].get('dual_pad_grasp') for n in movable}
        if self.measurements.geometry.static['filters']['contact_filter_callback']!='absent':
            grasps={n:True if v is True else None for n,v in grasps.items()}
        held=True if any(v is True for v in grasps.values()) else False if all(v is False for v in grasps.values()) else None
        a_grasps=[grasps[n] for n in self.a_objects]
        a_regrasp=True if any(v is True for v in a_grasps) else False if all(v is False for v in a_grasps) else None
        a_release=[facts['objects'][n]['released'] for n in self.a_objects]
        a_released=True if all(v is True for v in a_release) else False if any(v is False for v in a_release) else None
        pos,rot=self.pose()
        opened=np.asarray(self.layout['gripper_open'])
        hand_open=bool(np.all(np.abs(np.asarray(self.env.sim.data.qpos)[self.layout['gripper_qpos']]-opened)<=.003))
        return {'state':np.asarray(self.env.sim.get_state().flatten()).copy(),'observation':obs,'facts':facts,
            'position':pos,'rotation':rot,'hand_open':hand_open,'held_free':held,
            'a_released':a_released,'a_regrasp':a_regrasp,'penetration':self._penetration()}

    def step(self,action):
        self.session._check_substeps()
        # Continue physical teacher release after native task success; no state
        # or controller reset occurs within this episode.
        self.env.done=False
        self.env.step(action)

    def qualify(self,frames,domain):return qualify_frames(frames,domain,self.semantics)

    def close(self):
        if self.session is not None:self.session.close();self.session=None


def worker(request_path):
    from .generation import generate_session,write_json,initialization_failure
    request=json.loads(Path(request_path).read_text(encoding='utf-8'))
    source=request['source'];directory=Path(request['output_dir']);session=None
    initialization_failure(source,directory,'native_initialization_interrupted')
    try:
        session=NativeSession(source,request['config'],request['data_root'])
        result=generate_session(session,source,request['config'],directory)
    except Exception as e:
        reason=type(e).__name__+': '+str(e)
        # Initializer failure is a counted ordinary replay attempt, not a lost
        # source. Preserve the concrete failure even if no state was available.
        saved=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('*/metadata.json'))]
        if not saved or (len(saved)==1 and saved[0].get('failure_reason')=='native_initialization_interrupted'):
            saved=[initialization_failure(source,directory,reason)]
        result={'source_id':source['source_id'],'attempts':saved,'gaps':['native_initialization_or_execution_failure'],'error':reason}
    finally:
        if session is not None:session.close()
    write_json(directory/'result.json',result)


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='--request':raise SystemExit('Use the task035 generate command.')
    worker(sys.argv[2])
