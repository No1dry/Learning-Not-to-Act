from types import SimpleNamespace
import numpy as np
import pytest


def mapping():
    return {'axis_sign': [1]*7,
        'gripper': {'kind':'binarize','index':6,'input_open':-1.,'input_closed':1.,'output_open':1.,'output_closed':0.},
        'action_normalization': {'kind':'bounds_q99','q01':[-.8,-.4,-.3,-.2,-.2,-.2,0],
            'q99':[.6,.9,.7,.4,.4,.4,1], 'mask':[True]*6+[False]}}


def test_projection_precedes_execution_and_matches_deployed_asymmetric_bounds():
    from egrs.trajectory_augmentation.control import ActionProjector
    p=ActionProjector(mapping(), (np.full(7,-.5),np.array([.4,.5,.5,.5,.5,.5,1.])))
    executed, audit=p.project([2.,-2.,0.,0.,0.,0.,.2])
    np.testing.assert_allclose(executed,[.4,-.4,0,0,0,0,1])
    normalized=p.encode(executed)
    # Actual OFT unnormalization then LIBERO binary gripper conversion, with
    # no invented inverse signs or arbitrary gripper endpoints.
    norm=mapping()['action_normalization'];lo=np.array(norm['q01']);hi=np.array(norm['q99'])
    deployed=normalized.copy();deployed[:6]=.5*(normalized[:6]+1)*(hi[:6]-lo[:6])+lo[:6]
    deployed[6]=-1 if normalized[6]>.5 else 1
    np.testing.assert_allclose(deployed,executed,atol=1e-7)
    assert audit['changed'] and audit['raw'][-1]==.2


def test_projection_rejects_noncanonical_mapping_deployed_adapter_cannot_invert():
    from egrs.trajectory_augmentation.control import ActionProjector
    m=mapping();m['axis_sign'][1]=-1
    with pytest.raises(ValueError,match='canonical'):ActionProjector(m,(np.full(7,-1.),np.ones(7)))
    m=mapping();m['gripper']['input_open']=1;m['gripper']['input_closed']=-1
    with pytest.raises(ValueError,match='canonical'):ActionProjector(m,(np.full(7,-1.),np.ones(7)))


def test_projection_rejects_unrepresentable_gripper_endpoint():
    from egrs.trajectory_augmentation.control import ActionProjector
    p=ActionProjector(mapping(),(np.full(7,-.5),np.full(7,.5)))
    with pytest.raises(ValueError,match='gripper'): p.project([0]*6+[-1])


def test_world_rotation_action_uses_controller_site_and_actual_target_not_reached_pose():
    from egrs.trajectory_augmentation.control import target_action, controller_target, rotvec_matrix
    current=rotvec_matrix([.5,0,0]); target=rotvec_matrix([0,0,.2])@current
    c=SimpleNamespace(use_delta=True,use_ori=True,impedance_mode='fixed',
        input_min=np.full(6,-2.),input_max=np.full(6,2.),output_min=np.full(6,-.5),output_max=np.full(6,.5),
        goal_pos=np.array([1,2,3]),goal_ori=target,ee_pos=np.zeros(3),ee_ori_mat=current)
    action=target_action(c,np.zeros(3),current,np.array([.1,0,0]),target,-1)
    np.testing.assert_allclose(action,[.4,0,0,0,0,.8,-1],atol=1e-7)
    pos,ori=controller_target(c)
    np.testing.assert_equal(pos,[1,2,3]);np.testing.assert_allclose(ori,target)


def test_robot_rewind_preserves_every_nonrobot_velocity_and_uses_explicit_layout():
    from egrs.trajectory_augmentation.control import rewind_state
    checkpoint=np.arange(17,dtype=float);nominal=checkpoint+100
    layout={'nq':8,'nv':8,'arm_qpos':[1,4],'arm_qvel':[0,5],
        'gripper_qpos':[2,6],'gripper_qvel':[2,7],
        'arm_limits':[[-200,200],[-200,200]],'gripper_open':[.04,-.04]}
    changed,audit=rewind_state(checkpoint,nominal,layout,[.01,-.01])
    np.testing.assert_equal(changed[[0,1,4,6,8,10,12,13,15]],checkpoint[[0,1,4,6,8,10,12,13,15]])
    np.testing.assert_allclose(changed[[2,5]],[102.01,104.99])
    np.testing.assert_equal(changed[[9,14]],[109,114])
    assert audit['nonrobot_before_sha256']==audit['nonrobot_after_sha256']
    with pytest.raises(ValueError,match='limit'): rewind_state(checkpoint,nominal,{**layout,'arm_limits':[[0,1],[0,1]]},[0,0])
