"""NumPy-only fake recorder worker; never a native/model entry point."""
from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
import json
import sys
import numpy as np

class RecordedWorld:
    """Cartesian fake only; all captures follow executed controls, never MuJoCo."""
    def __init__(self,parent,layout):
        self.parent=parent;self.layout=deepcopy(layout)
        self.initial_state=np.zeros(1+layout['nq']+layout['nv'],dtype=float)
        self.action_spec=(np.full(7,-1.),np.ones(7));self.steps=[];self.local_steps=0
        self.source_actions=[np.array([.2,0,0,0,0,0,-1.]) for _ in range(3)]
        self.controller=SimpleNamespace(use_delta=True,use_ori=True,impedance_mode='fixed',
            input_min=np.full(6,-1.),input_max=np.ones(6),output_min=np.full(6,-1.),output_max=np.ones(6),
            goal_pos=np.zeros(3),goal_ori=np.eye(3))
        self.inspection={'runtime_xml_sha256':'d'*64,'joint_layout':self.layout,'environment_fingerprint':'e'*64}
    def restore(self,state):
        self.state=np.asarray(state).copy();self.local_steps=0
    def pose(self):return np.array([self.state[3],0.,0.]),np.eye(3)
    def step(self,action):
        self.steps.append(action.copy());self.local_steps+=1
        self.controller.goal_pos=self.pose()[0]+action[:3]
        self.state[3]+=action[0];self.state[0]+=.05
        if self.state[3]>=.19:self.state[2]=1.
        if self.state[3]>=.59:self.state[11]=1.
    def capture(self):
        goals=[bool(self.state[2]),bool(self.state[11])];position,rotation=self.pose()
        return {'state':self.state.copy(),'position':position,'rotation':rotation,
            'observation':{'obs/agentview_rgb':np.full((2,2,3),self.local_steps,dtype=np.uint8),
                'obs/eye_in_hand_rgb':np.zeros((2,2,3),dtype=np.uint8),
                'obs/ee_states':np.r_[position,np.zeros(3)],'obs/gripper_states':np.array([.04,-.04])},
            'facts':{'goals':goals,'official_goal_values':goals,'invariant_values':[],
                'required_open_values':[],'official_success':all(goals),
                'released':not all(goals) or self.local_steps>=5},
            'hand_open':True,'held_free':False,'a_released':True,'a_regrasp':False,'penetration':False}
    def qualify(self,frames,domain):
        streak=0
        for frame in frames:
            streak=streak+1 if frame['facts']['official_success'] and frame['facts']['released'] is True else 0
        valid=streak>=5 and (domain=='normal' or frames[0]['facts']['goals']==[True,False])
        return {'qualified':valid,'failure_reason':None if valid else 'release_unconfirmed',
            'core_release_confirmation_streak':streak,'core_analysis':{'confirmed_events':[]}}


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from egrs.coverage039.generation import generate_session
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    result = generate_session(RecordedWorld(request['parent'], request['layout']), request['parent'],
                              request['config'], request['root'])
    Path(request['result']).write_text(json.dumps(result), encoding='utf-8')
