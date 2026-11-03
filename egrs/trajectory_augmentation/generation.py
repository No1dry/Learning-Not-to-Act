"""Bounded ordinary replay and robot-rewind generation, with durable attempt ledgers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

from .control import (ActionProjector, controller_target, target_action, interpolate_pose,
                      pose_error, rewind_state)

DEFAULT_RECIPE={'name':'robot_rewind_v1','seed':7,'variants':3,'bridge_attempts':2,'horizon':520,
    'joint_perturbation_rad':.05,'position_tolerance_m':.005,'rotation_tolerance_deg':3.,
    'bridge_stage_steps':40,'lift_m':.1}


def _json(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,default=_json,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def initialization_failure(source,directory,reason):
    """Durable denominator entry even when native construction never returns."""
    folder=Path(directory)/'normal_vnormal_a0';folder.mkdir(parents=True,exist_ok=True)
    meta={'source_id':source['source_id']+'__normal__vnormal__a0','parent_demo_id':source['parent_demo_id'],
        'task_key':source['task_key'],'split':source['split'],'domain':'normal','provenance':'ordinary_reexecuted',
        'variant':'normal','attempt':0,'status':'rejected','qualified':False,'failure_reason':reason,'file':None,
        'qualification':{'accepted':False,'qualified':False,'failure_reason':reason},
        'parent_file_sha256':source['file_sha256'],'instruction':source['instruction'],
        'episode':'data/demo_0','length':0,'mapping':source['mapping'],'audit_path':'normal_vnormal_a0/audit.json',
        'qualification_path':'normal_vnormal_a0/qualification.json','lineage_path':'normal_vnormal_a0/lineage.json'}
    write_json(folder/'audit.json',{'steps':[],'frames':[],'error':reason})
    write_json(folder/'qualification.json',meta['qualification'])
    write_json(folder/'lineage.json',{'source':source})
    write_json(folder/'metadata.json',meta)
    return meta


def safe_handoff(frame):
    f=frame['facts']
    return (f['goals']==[True,False] and all(v is True for v in f['invariant_values'])
        and all(v is True for v in f.get('required_open_values',[]))
        and frame['hand_open'] is True and frame['held_free'] is False
        and frame['a_released'] is True and frame.get('penetration') is False)


def _guard(frame,phase):
    if frame['facts']['goals'][0] is not True:raise ValueError('completed_A_regressed')
    if not all(v is True for v in frame['facts']['invariant_values']):raise ValueError('holding_constraint_regressed')
    if frame['a_regrasp'] is not False:raise ValueError('A_transport_regrasp_or_unknown')
    if phase=='bridge' and (frame['held_free'] is not False or frame['hand_open'] is not True):
        raise ValueError('bridge_grasp_or_open_hand_unconfirmed')


class Attempt:
    def __init__(self, session, source, config, directory, domain, variant, number):
        self.session=session;self.source=source;self.config=config;self.directory=Path(directory)
        self.domain=domain;self.variant=variant;self.number=number
        self.recipe={**DEFAULT_RECIPE,**config.get('recipe',{})}
        self.frames=[];self.actions=[];self.targets=[];self.steps=[];self.confirmation=[]
        self.rewind=None;self.handoff=None;self.error=None
        self.projector=ActionProjector(source['mapping'],session.action_spec)
        self.folder=self.directory/(self.domain+f'_v{self.variant}_a{self.number}')

    def journal(self,event,**values):
        self.folder.mkdir(parents=True,exist_ok=True)
        with (self.folder/'journal.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'event':event,**values},default=_json,allow_nan=False)+'\n')
            stream.flush()

    def begin(self,state):
        # Predeclare the counted attempt and requested full initial state before
        # entering native code. Hard worker termination therefore loses no slot.
        self.persist({'qualified':False,'failure_reason':'attempt_interrupted_before_finalization'})
        self.journal('initial_state_requested',state=state,rewind=self.rewind)
        self.session.restore(state);self.frames.append(self.session.capture())
        self.journal('initial_observation',frame={k:v for k,v in self.frames[0].items() if k!='observation'})
        if self.domain=='10':
            if not safe_handoff(self.frames[0]):raise ValueError('invalid_rewound_initial_state')
            _guard(self.frames[0],'bridge')

    def step(self,raw,phase,reference=None,*,audit_only=False):
        if len(self.steps)>=self.recipe['horizon']:raise ValueError('attempt_horizon_exhausted')
        action,projection=self.projector.project(raw)
        # Persist the actual input before the environment can throw/mutate it.
        event={'phase':phase,'projection':projection,'reference_target':reference,'audit_only':audit_only}
        self.steps.append(event)
        self.journal('action_requested',step=event)
        self.session.step(action.copy())
        position,rotation=controller_target(self.session.controller)
        target={'position':position.tolist(),'rotation':rotation.tolist(),'gripper':float(action[6])}
        event['controller_target']=target
        frame=self.session.capture()
        self.journal('action_completed',step=event,frame={k:v for k,v in frame.items() if k!='observation'})
        if audit_only:self.confirmation.append(frame)
        else:
            self.actions.append(action.copy());self.targets.append(target);self.frames.append(frame)
        if self.domain=='10':_guard(frame,phase)
        return frame

    def track(self,pose,gripper,phase):
        pos,rot=self.session.pose()
        return self.step(target_action(self.session.controller,pos,rot,*pose,gripper),phase,
                         {'position':np.asarray(pose[0]).tolist(),'rotation':np.asarray(pose[1]).tolist(),'gripper':float(gripper)})

    def bridge(self,target,lift):
        start=self.session.pose();points=[]
        if lift:
            z=max(start[0][2],target[0][2])+self.recipe['lift_m']
            p=start[0].copy();p[2]=z;q=target[0].copy();q[2]=z
            points=[(p,start[1]),(q,target[1])]
        points.append(target)
        opened=self.source['mapping']['gripper']['input_open'];n=self.recipe['bridge_stage_steps']
        for end in points:
            begin=self.session.pose()
            for i in range(1,n+1):self.track(interpolate_pose(begin,end,i/n),opened,'bridge')
        # A bounded final settle uses ordinary OSC actions, never set_goal/state.
        for _ in range(n+1):
            distance,angle=pose_error(self.session.pose(),target)
            if distance<=self.recipe['position_tolerance_m'] and angle<=np.deg2rad(self.recipe['rotation_tolerance_deg']):return
            if _==n:break
            self.track(target,opened,'bridge')
        raise ValueError('bridge_pose_tolerance_not_reached')

    def finish(self):
        if (not self.error and self.frames and self.frames[-1]['facts']['official_success']
                and self.frames[-1]['facts']['released'] is True and self.frames[-1]['hand_open'] is True):
            # Existing core confirms over five observations. Added actions are
            # evidence only, never extra parking supervision in the HDF.
            target=self.session.pose();opened=self.source['mapping']['gripper']['input_open']
            try:
                for _ in range(min(4,self.recipe['horizon']-len(self.steps))):
                    p,r=self.session.pose()
                    self.step(target_action(self.session.controller,p,r,*target,opened),'confirmation_hold',audit_only=True)
            except Exception as e:self.error=str(e)
        qualification=self.session.qualify(self.frames+self.confirmation,self.domain) if self.frames else {'qualified':False,'failure_reason':'initialization_failed'}
        if self.error:qualification.update(qualified=False,failure_reason=self.error)
        if not self.actions:qualification.update(qualified=False,failure_reason=self.error or 'empty_trajectory')
        return self.persist(qualification)

    def persist(self,qualification):
        from egrs.augmentation.data import file_sha256,identity
        sid=f"{self.source['source_id']}__{self.domain}__v{self.variant}__a{self.number}"
        folder=self.directory/(self.domain+f'_v{self.variant}_a{self.number}')
        folder.mkdir(parents=True,exist_ok=True)
        relative=lambda p:p.relative_to(self.directory).as_posix()
        mapping=deepcopy(self.source['mapping']);mapping.update(observation_offset=0,action_offset=0,
            alignment_id='task035-live-transitions-v1',alignment_basis='fresh observation before executed action; T+1/T')
        meta={'source_id':sid,'parent_demo_id':self.source['parent_demo_id'],'task_key':self.source['task_key'],
            'split':self.source['split'],'domain':self.domain,'provenance':'ordinary_reexecuted' if self.domain=='normal' else 'counterfactual_generated_from_demo',
            'variant':self.variant,'attempt':self.number,'status':'completed' if qualification['qualified'] else 'rejected',
            'qualified':bool(qualification['qualified']),'failure_reason':qualification.get('failure_reason'),
            'qualification':{'accepted':bool(qualification['qualified']),**qualification},
            'file':None,'episode':'data/demo_0','length':len(self.actions),'mapping':mapping,
            'instruction':self.source['instruction'],'parent_file_sha256':self.source['file_sha256'],
            'recipe':deepcopy(self.recipe),'recipe_identity':identity(self.recipe),
            'audit_path':relative(folder/'audit.json'),'qualification_path':relative(folder/'qualification.json'),
            'lineage_path':relative(folder/'lineage.json'),'journal_path':relative(folder/'journal.jsonl'),
            'attempt_steps':len(self.steps)}
        # All failures retain full initial state, outgoing actions, facts, true
        # controller goals and the separately marked confirmation evidence.
        audit={'steps':self.steps,'frames':[{k:v for k,v in f.items() if k!='observation'} for f in self.frames],
            'confirmation_frames':[{k:v for k,v in f.items() if k!='observation'} for f in self.confirmation],
            'rewind':self.rewind,'handoff':self.handoff,'error':self.error}
        write_json(folder/'audit.json',audit);write_json(folder/'qualification.json',qualification)
        write_json(folder/'lineage.json',{'source':self.source,'native':self.session.inspection,
            'stats_sha256':self.config.get('stats_sha256'),'unnorm_key':self.config.get('unnorm_key'),
            'actual_initial_state':self.frames[0]['state'] if self.frames else None,
            'actual_initial_facts':self.frames[0]['facts'] if self.frames else None})
        if qualification['qualified']:
            import h5py
            file=folder/'trajectory.hdf5'
            with h5py.File(file,'w') as h:
                g=h.require_group('data/demo_0');g.create_dataset('actions',data=np.asarray(self.actions))
                g.create_dataset('states',data=np.stack([f['state'] for f in self.frames]))
                for key in mapping['images']+mapping['proprio']:
                    g.create_dataset(key,data=np.stack([f['observation'][key] for f in self.frames]),compression='gzip')
                bind=mapping['instruction_binding'];text=self.source['instruction']
                h.require_group(bind['group']).attrs[bind['attribute']]=text if bind['json_key'] is None else json.dumps({bind['json_key']:text})
                g.attrs['provenance']=meta['provenance'];g.attrs['parent_demo_id']=meta['parent_demo_id']
                g.create_dataset('controller_goal_pos',data=[t['position'] for t in self.targets])
                g.create_dataset('controller_goal_ori',data=[t['rotation'] for t in self.targets])
            meta.update(file=relative(file),file_sha256=file_sha256(file))
        if self.config.get('save_video') and self.domain=='normal' and self.frames:
            try:
                import imageio.v2 as imageio
                with imageio.get_writer(str(folder/'representative.mp4'),fps=20,macro_block_size=1) as writer:
                    for frame in self.frames:
                        image=frame['observation'][mapping['images'][0]]
                        if mapping['image_transforms'][0]=='rotate_180':image=image[::-1,::-1]
                        writer.append_data(image)
                meta['video']=relative(folder/'representative.mp4')
            except Exception as e:meta['video_error']=str(e)
        write_json(folder/'metadata.json',meta)
        return meta


def generate_session(session,source,config,output_dir):
    """Concrete orchestration; the sole fake injection boundary is the native session."""
    result={'source_id':source['source_id'],'attempts':[],'gaps':[],'error':None}
    recipe={**DEFAULT_RECIPE,**config.get('recipe',{})}
    if (recipe['variants']!=3 or recipe['bridge_attempts']!=2 or recipe['seed']!=7
        or not 1<=recipe['horizon']<=520 or not 1<=recipe['bridge_stage_steps']<=40
        or not 0<=recipe['joint_perturbation_rad']<=.05):raise ValueError('invalid bounded generation recipe')
    normal=Attempt(session,source,config,output_dir,'normal','normal',0)
    try:
        normal.begin(session.initial_state)
        for action in session.source_actions:normal.step(action,'source_replay')
    except Exception as e:normal.error=type(e).__name__+': '+str(e)
    try:normal_meta=normal.finish()
    except Exception as e:
        normal.error=type(e).__name__+': '+str(e)
        normal_meta=normal.persist({'qualified':False,'failure_reason':normal.error})
    result['attempts'].append(normal_meta)
    if not normal_meta['qualified']:
        result['gaps'].append('normal_replay_unqualified');return result
    eligible=[i for i,f in enumerate(normal.frames[:-1]) if safe_handoff(f)]
    if not eligible:result['gaps'].append('no_safe_handoff');return result
    # Geometry-only preregistered choice, deterministic earliest-index tie break.
    index=min(eligible,key=lambda i:(float(np.linalg.norm(normal.frames[i]['position']-normal.frames[0]['position'])),i))
    handoff=normal.frames[index];target=(handoff['position'],handoff['rotation'])
    rng=np.random.default_rng(7);joints=len(session.layout['arm_qpos'])
    perturbations=[np.zeros(joints)]+[rng.uniform(-recipe['joint_perturbation_rad'],recipe['joint_perturbation_rad'],joints) for _ in range(2)]
    for variant,delta in enumerate(perturbations):
        for attempt in (0,1):
            current=Attempt(session,source,config,output_dir,'10',variant,attempt)
            current.handoff={'normal_state_index':index,'selection':'nearest nominal initial controlled site; earliest tie'}
            try:
                state,current.rewind=rewind_state(handoff['state'],session.initial_state,session.layout,delta)
                current.begin(state);current.bridge(target,lift=attempt==1)
                for reference in normal.targets[index:]:
                    current.track((np.asarray(reference['position']),np.asarray(reference['rotation'])),reference['gripper'],'continuation')
            except Exception as e:current.error=type(e).__name__+': '+str(e)
            try:meta=current.finish()
            except Exception as e:
                current.error=type(e).__name__+': '+str(e)
                meta=current.persist({'qualified':False,'failure_reason':current.error})
            result['attempts'].append(meta)
            if meta['qualified']:break
    if not any(a['qualified'] and a['domain']=='10' for a in result['attempts']):result['gaps'].append('no_qualified_10')
    return result


def generate_source(source,config,data_root,output_dir):
    """Run the actual pinned native session in a fresh bounded worker process."""
    directory=Path(output_dir).resolve();directory.mkdir(parents=True,exist_ok=True)
    request=directory/'request.json';response=directory/'result.json'
    write_json(request,{'source':source,'config':config,'data_root':str(Path(data_root).resolve()),'output_dir':str(directory)})
    backend=config['native_backend'];python=backend.get('python',sys.executable)
    command=[python,'-m','egrs.trajectory_augmentation.native','--request',str(request)]
    timeout=backend.get('source_timeout_seconds',7200)
    if type(timeout) not in (int,float) or not 1<=timeout<=86400:raise ValueError('source timeout must be 1..86400 seconds')
    with (directory/'worker.stdout.log').open('wb') as out,(directory/'worker.stderr.log').open('wb') as err:
        try:
            completed=subprocess.run(command,cwd=str(Path(__file__).resolve().parents[2]),stdout=out,stderr=err,timeout=timeout)
            if completed.returncode!=0:raise RuntimeError('native worker exited '+str(completed.returncode))
            return json.loads(response.read_text(encoding='utf-8'))
        except Exception as e:
            # Recover every attempt already persisted before a worker crash.
            attempts=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('*/metadata.json'))]
            if not attempts:attempts=[initialization_failure(source,directory,type(e).__name__+': '+str(e))]
            result={'source_id':source['source_id'],'attempts':attempts,'error':type(e).__name__+': '+str(e),'gaps':['native_worker_failure']}
            write_json(response,result);return result
