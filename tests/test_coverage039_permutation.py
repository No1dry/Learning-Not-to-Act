"""Full freejoint swaps use compiled addresses and leave every other byte alone."""
from copy import deepcopy
import hashlib
from types import SimpleNamespace

import numpy as np
import pytest


class Pot:
    def __init__(self,joint,root,size=(.05,.07)):
        self.joints=[joint];self.root_body=root;self.size=np.asarray(size)


def session(*, reverse=False, registry='inner'):
    names=['robot_scalar','totally_actual_free_joint_2','unrelated','unusual_actual_free_joint_1','hinge']
    model=SimpleNamespace(nq=24,nv=20,njnt=5,jnt_type=np.array([3,0,3,0,3]),
        jnt_qposadr=np.array([0,2,11,14,23]),jnt_dofadr=np.array([0,1,9,11,19]),
        jnt_bodyid=np.array([0,2,0,4,0]),joint_name2id=lambda n:names.index(n),
        body_name2id=lambda n:{'physical_first':4,'physical_second':2}[n])
    if reverse:
        order=[3,4,1,0,2]
        for key in ('jnt_type','jnt_qposadr','jnt_dofadr','jnt_bodyid'):
            setattr(model,key,getattr(model,key)[order])
        reordered=[names[i] for i in order]
        model.joint_name2id=lambda n:reordered.index(n)
    objects={'moka_pot_1':Pot('unusual_actual_free_joint_1','physical_first'),
        'moka_pot_2':Pot('totally_actual_free_joint_2','physical_second')}
    state=np.arange(48,dtype=float)
    state[3:10]=[1,2,3,1,0,0,0]
    state[15:22]=[4,5,6,0,0,1,0]
    env=SimpleNamespace(sim=SimpleNamespace(model=model))
    native=SimpleNamespace(initial_state=state,env=env)
    if registry=='inner':native.session=SimpleNamespace(inner=SimpleNamespace(objects_dict=objects))
    else:env.objects_dict=objects
    return native,objects


def sha(value):return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


@pytest.mark.parametrize('reverse,registry',[(False,'inner'),(True,'inner'),(True,'env')])
def test_swap_resolves_actual_unsorted_noncontiguous_object_freejoints(reverse,registry):
    from egrs.coverage039.permutation import prepare_initial
    native,objects=session(reverse=reverse,registry=registry)
    original=native.initial_state.copy();source={'task_key':'two_pots','goal_ids':['A','B'],'split':'train'}
    before=deepcopy(source)
    changed,evidence=prepare_initial(native,source)
    np.testing.assert_array_equal(changed[3:10],original[15:22])
    np.testing.assert_array_equal(changed[15:22],original[3:10])
    np.testing.assert_array_equal(changed[26:32],original[36:42])
    np.testing.assert_array_equal(changed[36:42],original[26:32])
    modified=list(range(3,10))+list(range(15,22))+list(range(26,32))+list(range(36,42))
    outside=np.ones(48,bool);outside[modified]=False
    np.testing.assert_array_equal(changed[outside],original[outside])
    np.testing.assert_array_equal(native.initial_state,original)
    assert source==before and not np.shares_memory(changed,native.initial_state)
    assert set(evidence['modified_indices'])==set(modified)
    assert evidence['non_target_before_sha256']==evidence['non_target_after_sha256']==sha(original[outside])
    assert evidence['original_initial_state_sha256']==sha(original)
    assert evidence['transformed_initial_state_sha256']==sha(changed)
    assert evidence['applied_at']=='before_initial_restore'
    assert evidence['objects'][0]['joint_name']=='unusual_actual_free_joint_1'


@pytest.mark.parametrize('key', ['basket','white_mug','stove_on','TWO_POTS'])
def test_other_tasks_return_identical_copy_without_touching_native_registry(key):
    from egrs.coverage039.permutation import prepare_initial,validate_initial
    original=np.array([0,1,2.])
    changed,evidence=prepare_initial(SimpleNamespace(initial_state=original),{'task_key':key})
    np.testing.assert_array_equal(changed,original)
    assert not np.shares_memory(changed,original) and evidence['kind']=='identity'
    validate_initial({}, {'task_key':key}, evidence)


@pytest.mark.parametrize('fault', ['missing_object','wrong_class','wrong_size','nonfinite_size',
    'extra_joint','scalar_joint','duplicate_joint','overlap','negative_address','overflow',
    'fractional_address','short_state','bad_quaternion','nonfinite','root_mismatch'])
def test_invalid_object_identity_layout_or_initial_state_rejects(fault):
    from egrs.coverage039.permutation import prepare_initial
    native,objects=session();model=native.env.sim.model
    if fault=='missing_object':objects.pop('moka_pot_2')
    elif fault=='wrong_class':objects['moka_pot_2']=SimpleNamespace(**vars(objects['moka_pot_2']))
    elif fault=='wrong_size':objects['moka_pot_2'].size=np.array([.06,.07])
    elif fault=='nonfinite_size':objects['moka_pot_2'].size=np.array([np.nan,.07])
    elif fault=='extra_joint':objects['moka_pot_1'].joints.append('hinge')
    elif fault=='scalar_joint':model.jnt_type[3]=3
    elif fault=='duplicate_joint':objects['moka_pot_2'].joints=objects['moka_pot_1'].joints
    elif fault=='overlap':model.jnt_qposadr[1]=13
    elif fault=='negative_address':model.jnt_dofadr[1]=-1
    elif fault=='overflow':model.jnt_qposadr[1]=20
    elif fault=='fractional_address':model.jnt_qposadr=model.jnt_qposadr.astype(float);model.jnt_qposadr[1]=2.5
    elif fault=='short_state':native.initial_state=native.initial_state[:30]
    elif fault=='bad_quaternion':native.initial_state[18:22]=[2,0,0,0]
    elif fault=='nonfinite':native.initial_state[8]=np.nan
    elif fault=='root_mismatch':objects['moka_pot_1'].root_body='physical_second'
    with pytest.raises(ValueError):prepare_initial(native,{'task_key':'two_pots'})


def frame(changed):
    return {'state':changed.copy(),'facts':{'goals':[False,False],'invariant_values':[True],
        'event_candidates':{'wrong_grasp':{'x':False},'table_drop':{'x':None}}},'penetration':False}


def test_first_frame_validation_checks_restored_state_and_fixed_goal_semantics():
    from egrs.coverage039.permutation import prepare_initial,validate_initial
    native,_=session();changed,evidence=prepare_initial(native,{'task_key':'two_pots'})
    assert validate_initial(frame(changed),{'task_key':'two_pots'},evidence) is None


@pytest.mark.parametrize('fault',['goalA','goalB','unknown_goal','K_false','K_unknown','K_missing',
    'penetration','nonfinite','wrong_restore','confirmed_event'])
def test_invalid_restored_first_frame_is_rejected(fault):
    from egrs.coverage039.permutation import prepare_initial,validate_initial
    native,_=session();changed,evidence=prepare_initial(native,{'task_key':'two_pots'});f=frame(changed)
    if fault=='goalA':f['facts']['goals'][0]=True
    elif fault=='goalB':f['facts']['goals'][1]=True
    elif fault=='unknown_goal':f['facts']['goals'][0]=None
    elif fault=='K_false':f['facts']['invariant_values']=[False]
    elif fault=='K_unknown':f['facts']['invariant_values']=[None]
    elif fault=='K_missing':f['facts']['invariant_values']=[]
    elif fault=='penetration':f['penetration']=True
    elif fault=='nonfinite':f['state'][0]=np.nan
    elif fault=='wrong_restore':f['state']=native.initial_state.copy()
    elif fault=='confirmed_event':f['facts']['event_candidates']['wrong_grasp']['x']=True
    with pytest.raises(ValueError):validate_initial(f,{'task_key':'two_pots'},evidence)


def test_dimensions_can_come_from_actual_compiled_object_geometry():
    from egrs.coverage039.permutation import prepare_initial
    native,objects=session();model=native.env.sim.model
    for obj in objects.values():del obj.size
    model.nbody=5;model.body_parentid=np.array([0,0,0,0,0])
    model.geom_bodyid=np.array([4,2]);model.geom_type=np.array([3,3])
    model.geom_size=np.array([[.05,.07,0],[.05,.07,0]])
    changed,evidence=prepare_initial(native,{'task_key':'two_pots'})
    assert evidence['dimensions']['basis']=='compiled_geometry'
    model.geom_size[1,0]=.09
    with pytest.raises(ValueError,match='dimension|size|geometry'):prepare_initial(native,{'task_key':'two_pots'})


@pytest.mark.parametrize('fault',['geom_offset','child_offset','invalid_geometry_pose','mesh_vertices'])
def test_compiled_dimensions_include_geometry_offsets_and_actual_mesh(fault):
    from egrs.coverage039.permutation import prepare_initial
    native,objects=session();model=native.env.sim.model
    for obj in objects.values():del obj.size
    model.nbody=7;model.body_parentid=np.array([0,0,0,0,0,4,2])
    model.body_pos=np.zeros((7,3));model.body_quat=np.tile([1.,0,0,0],(7,1))
    model.geom_bodyid=np.array([5,6]);model.geom_type=np.array([3,3])
    model.geom_size=np.array([[.05,.07,0],[.05,.07,0]])
    model.geom_pos=np.zeros((2,3));model.geom_quat=np.tile([1.,0,0,0],(2,1))
    if fault=='geom_offset':model.geom_pos[1,0]=.2
    elif fault=='child_offset':model.body_pos[6,0]=.2
    elif fault=='invalid_geometry_pose':model.geom_pos[0,0]=np.nan
    else:
        model.geom_type[:]=7;model.geom_dataid=np.array([0,1])
        model.mesh_vertadr=np.array([0,3]);model.mesh_vertnum=np.array([3,3])
        model.mesh_vert=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,0],[2,0,0],[0,1,0]])
    with pytest.raises(ValueError,match='dimension|size|geometry'):prepare_initial(native,{'task_key':'two_pots'})
