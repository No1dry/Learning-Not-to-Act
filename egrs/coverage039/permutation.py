"""A single pre-restore physical instance swap for the two-pots teacher only.

Object identities and goal semantics stay fixed.  Coordinate ownership comes
from the live object registry and compiled freejoint addresses, never offsets
in a particular source file or guessed object/joint naming conventions.
"""
import hashlib

import numpy as np


KIND='two_pots_initial_freejoint_swap_v1'
OBJECTS=('moka_pot_1','moka_pot_2')


def _sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _integer(value,label):
    try:
        result=int(value)
        valid=not isinstance(value,(bool,np.bool_)) and result==value
    except (ValueError,TypeError,OverflowError):valid=False
    if not valid:raise ValueError('invalid '+label)
    return result


def _state(value):
    result=np.asarray(value)
    if result.ndim!=1 or result.dtype.kind not in 'fiu' or not np.isfinite(result).all():
        raise ValueError('invalid or nonfinite initial state')
    return result.copy()


def _registry(session):
    inner=getattr(getattr(session,'session',None),'inner',None)
    for owner in (inner,session.env):
        registry=getattr(owner,'objects_dict',None)
        if isinstance(registry,dict) and all(name in registry for name in OBJECTS):return registry
    raise ValueError('two_pots actual object registry missing specified objects')


def _joint_blocks(model):
    nq=_integer(model.nq,'model nq');nv=_integer(model.nv,'model nv')
    types=np.asarray(model.jnt_type);qpos=np.asarray(model.jnt_qposadr);qvel=np.asarray(model.jnt_dofadr)
    if nq<=0 or nv<=0 or types.ndim!=1 or qpos.shape!=types.shape or qvel.shape!=types.shape:
        raise ValueError('invalid compiled joint layout')
    if hasattr(model,'njnt') and _integer(model.njnt,'model njnt')!=len(types):
        raise ValueError('invalid compiled joint count')
    sizes={0:(7,6),1:(4,3),2:(1,1),3:(1,1)}
    blocks=[];used_q=set();used_v=set()
    for joint,(kind,q,v) in enumerate(zip(types,qpos,qvel)):
        kind=_integer(kind,'joint type');q=_integer(q,'qpos address');v=_integer(v,'qvel address')
        if kind not in sizes:raise ValueError('unsupported compiled joint type')
        qwidth,vwidth=sizes[kind];qi=list(range(q,q+qwidth));vi=list(range(v,v+vwidth))
        if q<0 or v<0 or q+qwidth>nq or v+vwidth>nv or used_q.intersection(qi) or used_v.intersection(vi):
            raise ValueError('illegal or overlapping compiled joint addresses')
        used_q.update(qi);used_v.update(vi)
        blocks.append({'joint_id':joint,'joint_type':kind,'qpos_indices':qi,'qvel_indices':vi})
    return nq,nv,blocks


def _object_block(model,obj,name,blocks):
    joints=getattr(obj,'joints',None)
    if isinstance(joints,str) or joints is None:
        raise ValueError('actual object joints required for '+name)
    joints=list(joints)
    if len(joints)!=1 or not isinstance(joints[0],str) or not joints[0]:
        raise ValueError('object must own one complete freejoint: '+name)
    try:joint=_integer(model.joint_name2id(joints[0]),'actual joint id')
    except (KeyError,IndexError,TypeError) as exc:raise ValueError('object joint missing: '+name) from exc
    if joint<0 or joint>=len(blocks) or blocks[joint]['joint_type']!=0:
        raise ValueError('object does not resolve to a compiled freejoint: '+name)
    result={**blocks[joint],'object_name':name,'joint_name':joints[0],
        'object_class':type(obj).__module__+'.'+type(obj).__qualname__}
    root=getattr(obj,'root_body',None)
    if root is not None:
        if not isinstance(root,str) or not root:raise ValueError('invalid actual object root body')
        try:body=_integer(model.body_name2id(root),'object root body id')
        except (KeyError,IndexError,TypeError) as exc:raise ValueError('object root body missing') from exc
        if body<0 or (hasattr(model,'jnt_bodyid') and int(model.jnt_bodyid[joint])!=body):
            raise ValueError('object freejoint does not belong to actual root body')
        result.update(root_body=root,root_body_id=body)
    return result


def _geometry(model,block):
    if 'root_body_id' not in block:raise ValueError('actual object root required for compiled geometry dimensions')
    try:
        parents=np.asarray(model.body_parentid);bodies=np.asarray(model.geom_bodyid)
        kinds=np.asarray(model.geom_type);sizes=np.asarray(model.geom_size)
    except AttributeError as exc:raise ValueError('object dimensions unavailable from size or compiled geometry') from exc
    root=block['root_body_id']
    if root>=len(parents) or bodies.shape!=kinds.shape or sizes.shape!=(len(bodies),3):
        raise ValueError('invalid compiled object geometry layout')
    def belongs(body):
        seen=set()
        while body>0:
            if body==root:return True
            if body in seen or body>=len(parents):raise ValueError('invalid object geometry body tree')
            seen.add(body);body=int(parents[body])
        return False
    def local_pose(prefix,index,*,required=False):
        position=getattr(model,prefix+'_pos',None);quaternion=getattr(model,prefix+'_quat',None)
        if position is None and quaternion is None and not required:return None
        try:
            position=np.asarray(position[index],dtype=float)
            quaternion=np.asarray(quaternion[index],dtype=float)
        except (IndexError,TypeError) as exc:raise ValueError('compiled geometry local pose unavailable') from exc
        if (position.shape!=(3,) or quaternion.shape!=(4,) or not np.isfinite(position).all()
                or not np.isfinite(quaternion).all() or not np.isclose(np.linalg.norm(quaternion),1.,rtol=0,atol=1e-6)):
            raise ValueError('invalid compiled geometry local pose')
        return {'position':position.tolist(),'quaternion':quaternion.tolist()}
    geometry=[]
    for gid,body in enumerate(bodies):
        if not belongs(int(body)):continue
        size=np.asarray(sizes[gid],dtype=float);kind=_integer(kinds[gid],'geom type')
        if not np.isfinite(size).all() or np.any(size<0) or not np.any(size>0):
            raise ValueError('invalid compiled object geometry size')
        signature={'type':kind,'size':size.tolist()}
        # Include the relative shape layout, excluding the root's world pose
        # (the two instances are deliberately located at different places).
        geom_pose=local_pose('geom',gid)
        if geom_pose is not None:signature['local_pose']=geom_pose
        path=[];current=int(body)
        while current!=root:
            path.append(local_pose('body',current,required=True));current=int(parents[current])
        signature['relative_body_poses']=path
        if kind==7:  # mjGEOM_MESH: include real compiled vertices, not just its bounding box.
            try:
                mid=_integer(model.geom_dataid[gid],'mesh id')
                if mid<0:raise ValueError('invalid compiled mesh id')
                start=_integer(model.mesh_vertadr[mid],'mesh vertex address')
                count=_integer(model.mesh_vertnum[mid],'mesh vertex count')
                vertices=np.asarray(model.mesh_vert)[start:start+count]
            except (AttributeError,IndexError,TypeError) as exc:raise ValueError('compiled object mesh dimensions unavailable') from exc
            if start<0 or count<=0 or vertices.shape!=(count,3) or not np.isfinite(vertices).all():
                raise ValueError('invalid compiled object mesh dimensions')
            signature['mesh_vertices_sha256']=_sha(vertices)
            mesh_pose=local_pose('mesh',mid)
            if mesh_pose is not None:signature['mesh_pose']=mesh_pose
        geometry.append(signature)
    if not geometry:raise ValueError('actual object compiled geometry empty')
    return sorted(geometry,key=repr)


def _dimensions(model,objects,blocks):
    if type(objects[0]) is not type(objects[1]):raise ValueError('two_pots object classes differ')
    sizes=[getattr(obj,'size',None) for obj in objects]
    if all(size is not None for size in sizes):
        try:sizes=[np.asarray(size,dtype=float) for size in sizes]
        except (ValueError,TypeError) as exc:raise ValueError('invalid object size') from exc
        if any(s.ndim!=1 or not s.size or not np.isfinite(s).all() or np.any(s<0) or not np.any(s>0) for s in sizes):
            raise ValueError('invalid object size')
        if not np.array_equal(*sizes):raise ValueError('two_pots object sizes differ')
        return {'basis':'actual_object_size','value':sizes[0].tolist()}
    if any(size is not None for size in sizes):raise ValueError('two_pots object size availability differs')
    geometry=[_geometry(model,block) for block in blocks]
    if geometry[0]!=geometry[1]:raise ValueError('two_pots compiled geometry dimensions differ')
    return {'basis':'compiled_geometry','value':geometry[0]}


def prepare_initial(session,source):
    """Copy source state0, swapping only the two named objects' 7/6 blocks.

    This pure helper never restores or mutates the simulator, source record,
    native initial state, A/B bindings, or files.  The caller restores the
    returned state once, before its first fresh observation.
    """
    original=_state(session.initial_state)
    evidence={'kind':'identity','applied_at':'before_initial_restore',
        'original_initial_state_sha256':_sha(original),'transformed_initial_state_sha256':_sha(original),
        'modified_indices':[],'non_target_before_sha256':_sha(original),'non_target_after_sha256':_sha(original),
        'objects':[]}
    if source['task_key']!='two_pots':return original,evidence
    registry=_registry(session);model=session.env.sim.model
    nq,nv,all_blocks=_joint_blocks(model)
    if len(original)<1+nq+nv:raise ValueError('initial state shorter than time+qpos+qvel')
    objects=[registry[name] for name in OBJECTS]
    blocks=[_object_block(model,obj,name,all_blocks) for obj,name in zip(objects,OBJECTS)]
    if blocks[0]['joint_id']==blocks[1]['joint_id']:raise ValueError('two objects share a compiled joint')
    dimensions=_dimensions(model,objects,blocks)
    for block in blocks:
        block['state_qpos_indices']=[1+i for i in block['qpos_indices']]
        block['state_qvel_indices']=[1+nq+i for i in block['qvel_indices']]
        quaternion=original[block['state_qpos_indices'][3:]]
        if not np.isclose(float(np.linalg.norm(quaternion)),1.,rtol=0,atol=1e-6):
            raise ValueError('invalid object freejoint quaternion')
    changed=original.copy()
    for field in ('state_qpos_indices','state_qvel_indices'):
        first,second=blocks[0][field],blocks[1][field]
        changed[first]=original[second];changed[second]=original[first]
    modified=sorted(i for block in blocks for field in ('state_qpos_indices','state_qvel_indices') for i in block[field])
    if len(set(modified))!=26:raise ValueError('object state coordinate ownership overlaps')
    mask=np.ones(len(original),bool);mask[modified]=False
    if not np.array_equal(original[mask],changed[mask]):raise ValueError('non-target state changed')
    evidence.update(kind=KIND,objects=blocks,dimensions=dimensions,nq=nq,nv=nv,
        modified_indices=modified,transformed_initial_state_sha256=_sha(changed),
        non_target_before_sha256=_sha(original[mask]),non_target_after_sha256=_sha(changed[mask]))
    return changed,evidence


def _contains_true(value):
    if isinstance(value,dict):return any(_contains_true(v) for v in value.values())
    if isinstance(value,(list,tuple)):return any(_contains_true(v) for v in value)
    return value is True or isinstance(value,np.bool_) and bool(value)


def validate_initial(frame,source,evidence):
    """Check the fresh first observation after the caller's one initial restore."""
    if source['task_key']!='two_pots':return
    if evidence.get('kind')!=KIND or evidence.get('applied_at')!='before_initial_restore':
        raise ValueError('two_pots initial transformation evidence missing')
    actual=_state(frame['state'])
    if _sha(actual)!=evidence['transformed_initial_state_sha256']:
        raise ValueError('two_pots first observed state differs from requested restored state')
    facts=frame['facts'];goals=facts.get('goals',[]);invariants=facts.get('invariant_values',[])
    if len(goals)!=2 or any(value is not False for value in goals):
        raise ValueError('two_pots initial fixed A/B goals must both be false')
    if not invariants or any(value is not True for value in invariants):
        raise ValueError('two_pots initial stove invariant must be true')
    if frame.get('penetration') is True or frame.get('invalid') is True or facts.get('invalid') is True:
        raise ValueError('two_pots initial physical state invalid')
    if _contains_true(facts.get('event_candidates',{})):
        raise ValueError('two_pots initial confirmed physical event')
