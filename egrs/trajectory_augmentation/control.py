"""Small OSC_POSE tracker and executable-label projection, without simulator imports."""
from copy import deepcopy
import hashlib
import numpy as np


def _vector(value, size, label):
    a=np.asarray(value,dtype=np.float64)
    if a.shape!=(size,) or not np.isfinite(a).all(): raise ValueError('invalid '+label)
    return a.copy()


class ActionProjector:
    """Project before step; stored env actions survive the original loader exactly."""
    def __init__(self, mapping, action_spec):
        self.mapping=deepcopy(mapping)
        self.sign=_vector(mapping['axis_sign'],7,'axis signs')
        g=mapping['gripper']
        if (not np.array_equal(self.sign,np.ones(7)) or g['input_open']!=-1 or g['input_closed']!=1
            or g['output_open']!=1 or g['output_closed']!=0 or g['kind'] not in ('affine','binarize')):
            raise ValueError('task035 requires canonical deployed OFT/LIBERO signs and gripper endpoints')
        self.low=_vector(action_spec[0],7,'environment lower action bound')
        self.high=_vector(action_spec[1],7,'environment upper action bound')
        norm=mapping['action_normalization']
        self.mask=np.asarray(norm.get('mask',[False]*7),dtype=bool)
        self.lo=np.asarray(norm.get('q01',[-1]*7),dtype=float)
        self.hi=np.asarray(norm.get('q99',[1]*7),dtype=float)
        if norm['kind']=='identity_already_normalized':
            self.mask=np.array([True]*6+[False]);self.lo=np.full(7,-1.);self.hi=np.ones(7)
        if self.mask.shape!=(7,) or self.mask[6] or np.any(self.hi[self.mask]<=self.lo[self.mask]):
            raise ValueError('invalid original action normalization')
        self.low[~self.mask]=np.maximum(self.low[~self.mask],-1)
        self.high[~self.mask]=np.minimum(self.high[~self.mask],1)
        for i in np.flatnonzero(self.mask):
            lo,hi=sorted((self.lo[i]*self.sign[i],self.hi[i]*self.sign[i]))
            self.low[i]=max(self.low[i],lo);self.high[i]=min(self.high[i],hi)
        if np.any(self.low>self.high): raise ValueError('empty policy/environment action intersection')

    def encode(self, action):
        result=_vector(action,7,'action')*self.sign
        g=self.mapping['gripper']
        fraction=(result[6]-g['input_closed'])/(g['input_open']-g['input_closed'])
        if g['kind']=='binarize': fraction=float(fraction>=.5)
        result[6]=fraction
        result[self.mask]=np.clip(2*(result[self.mask]-self.lo[self.mask])/(self.hi[self.mask]-self.lo[self.mask])-1,-1,1)
        return result

    def decode(self, normalized):
        result=_vector(normalized,7,'normalized action')
        result[self.mask]=(result[self.mask]+1)*.5*(self.hi[self.mask]-self.lo[self.mask])+self.lo[self.mask]
        g=self.mapping['gripper']
        result[6]=g['input_closed']+result[6]*(g['input_open']-g['input_closed'])
        return result*self.sign

    def project(self, raw):
        raw=_vector(raw,7,'raw action')
        result=np.clip(raw,self.low,self.high)
        # The deployed OFT environment conversion binarizes open/closed. Select
        # that endpoint BEFORE execution even when a source used an affine map.
        g=self.mapping['gripper']
        fraction=(raw[6]-g['input_closed'])/(g['input_open']-g['input_closed'])
        result[6]=g['input_open'] if fraction>=.5 else g['input_closed']
        if not self.low[6]<=result[6]<=self.high[6]:
            raise ValueError('environment cannot execute the original gripper endpoint')
        encoded=self.encode(result)
        restored=self.decode(encoded)
        if not np.allclose(restored,result,rtol=0,atol=1e-7):
            raise ValueError('executed action fails original normalization roundtrip')
        return result,{'raw':raw.tolist(),'projected':result.tolist(),
            'normalized':encoded.tolist(),'changed':bool(np.any(raw!=result)),
            'max_roundtrip_error':float(np.max(np.abs(restored-result)))}


def rotvec_matrix(vector):
    v=_vector(vector,3,'rotation vector');angle=np.linalg.norm(v)
    if angle<1e-12: return np.eye(3)
    x,y,z=v/angle;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)+np.sin(angle)*k+(1-np.cos(angle))*(k@k)


def matrix_rotvec(matrix):
    r=np.asarray(matrix,dtype=float)
    if r.shape!=(3,3) or not np.isfinite(r).all() or not np.allclose(r.T@r,np.eye(3),atol=1e-6) or np.linalg.det(r)<0:
        raise ValueError('invalid world rotation')
    angle=np.arccos(np.clip((np.trace(r)-1)/2,-1,1))
    if angle<1e-8: return np.array([r[2,1]-r[1,2],r[0,2]-r[2,0],r[1,0]-r[0,1]])*.5
    if np.pi-angle<1e-6:
        values,vectors=np.linalg.eigh((r+r.T)/2);axis=vectors[:,np.argmax(values)]
        skew=np.array([r[2,1]-r[1,2],r[0,2]-r[2,0],r[1,0]-r[0,1]])
        if axis@skew<0:axis=-axis
        return axis*angle
    return angle/(2*np.sin(angle))*np.array([r[2,1]-r[1,2],r[0,2]-r[2,0],r[1,0]-r[0,1]])


def controller_target(controller):
    """Read true command goals after step, never substitute measured ee pose."""
    pos=_vector(controller.goal_pos,3,'controller goal position')
    ori=np.asarray(controller.goal_ori,dtype=float).copy();matrix_rotvec(ori)
    return pos,ori


def target_action(controller, position, rotation, target_position, target_rotation, gripper):
    if not controller.use_delta or not controller.use_ori or controller.impedance_mode!='fixed':
        raise ValueError('requires original fixed delta OSC_POSE controller')
    delta=np.r_[_vector(target_position,3,'target position')-_vector(position,3,'controlled site position'),
                matrix_rotvec(np.asarray(target_rotation)@np.asarray(rotation).T)]
    imin=np.broadcast_to(controller.input_min,(6,));imax=np.broadcast_to(controller.input_max,(6,))
    omin=np.broadcast_to(controller.output_min,(6,));omax=np.broadcast_to(controller.output_max,(6,))
    if np.any(omax<=omin) or np.any(imax<=imin): raise ValueError('invalid controller action scale')
    action=(delta-(omax+omin)/2)*(imax-imin)/(omax-omin)+(imax+imin)/2
    return np.r_[np.clip(action,imin,imax),float(gripper)]


def interpolate_pose(start, finish, fraction):
    p,r=start;q,s=finish
    return np.asarray(p)+(np.asarray(q)-p)*fraction,rotvec_matrix(matrix_rotvec(np.asarray(s)@np.asarray(r).T)*fraction)@r


def pose_error(actual, target):
    return float(np.linalg.norm(actual[0]-target[0])),float(np.linalg.norm(matrix_rotvec(target[1]@actual[1].T)))


def rewind_state(checkpoint, nominal, layout, perturbation):
    """MjSimState: time, qpos[nq], qvel[nv], act. Only named robot DOFs change."""
    before=np.asarray(checkpoint,dtype=float);nominal=np.asarray(nominal,dtype=float)
    if before.ndim!=1 or before.shape!=nominal.shape or len(before)<1+layout['nq']+layout['nv']:
        raise ValueError('state layout differs')
    if not np.isfinite(before).all() or not np.isfinite(nominal).all():raise ValueError('nonfinite state')
    result=before.copy();aq=np.asarray(layout['arm_qpos'],dtype=int)+1
    av=np.asarray(layout['arm_qvel'],dtype=int)+1+layout['nq']
    gq=np.asarray(layout['gripper_qpos'],dtype=int)+1;gv=np.asarray(layout['gripper_qvel'],dtype=int)+1+layout['nq']
    delta=_vector(perturbation,len(aq),'robot perturbation')
    if np.any(np.abs(delta)>.05+1e-12):raise ValueError('robot perturbation exceeds bound')
    result[aq]=nominal[aq]+delta;result[av]=nominal[av]
    result[gq]=layout['gripper_open'];result[gv]=0
    limits=np.asarray(layout['arm_limits'])
    if np.any(result[aq]<limits[:,0]) or np.any(result[aq]>limits[:,1]): raise ValueError('robot joint limit')
    modified=np.r_[aq,av,gq,gv]
    if len(set(modified))!=len(modified):raise ValueError('overlapping robot joint layout')
    mask=np.ones(len(before),bool);mask[modified]=False
    digest=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    if not np.array_equal(before[mask],result[mask]):raise ValueError('nonrobot state changed')
    return result,{'modified_indices':modified.tolist(),'layout':deepcopy(layout),
        'nonrobot_before_sha256':digest(before[mask]),'nonrobot_after_sha256':digest(result[mask]),
        'initial_state_sha256':digest(result),'perturbation_rad':delta.tolist()}
