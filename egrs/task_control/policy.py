"""Task038 evaluation uses the exact same current-frame encode/decode as training."""
from copy import deepcopy


class TaskControlPolicy:
    def __init__(self, config):
        from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
        from benchmark.remaining_goals.adapters.oft_transfer import FACTORY as BASE_FACTORY
        from .adapter import attach_trained_adapter, read_adapter_identity
        base_config = deepcopy(config)
        adapter = base_config.pop('method_adapter')
        arm = base_config.pop('task_control_arm')
        if arm not in {'c0','c1'}:
            raise ValueError('task_control_arm must be c0 or c1')
        identity = read_adapter_identity(adapter)
        if identity['arm'] != arm or identity['update'] != 1000:
            raise ValueError('Evaluation requires the requested arm fixed final1000 adapter')
        base_config['policy_factory'] = BASE_FACTORY
        self.base = OpenVLAOFTPolicy(base_config)
        try:
            identity = attach_trained_adapter(self.base, adapter, arm=arm)
            self.metadata = deepcopy(self.base.metadata)
            self.metadata.update(method_adapter=identity, task_control_arm=arm)
        except BaseException:
            self.base.close()
            raise

    def predict(self, observation, instruction):
        import numpy as np
        from benchmark.remaining_goals.adapters.openvla import (
            _instruction, _raw_observation, _action_array, _decode_action)
        from experiments.robot.openvla_utils import normalize_proprio
        from . import oft
        self.base.reset()
        instruction = _instruction(instruction)
        raw = _raw_observation(observation, wrist=True, proprio=True)
        api = self.base.api
        # The accepted prepare_observation uses these original camera/axis-angle
        # functions. Resize is performed once inside shared prediction, before
        # the same official center crop, rather than recompressing a resized RGB.
        images = [api.get_libero_image(raw), api.get_libero_wrist_image(raw)]
        proprio = np.concatenate((raw['robot0_eef_pos'], api.quat2axisangle(raw['robot0_eef_quat']),
                                  raw['robot0_gripper_qpos']))
        stats = self.base.model.norm_stats[self.base.cfg.unnorm_key]['proprio']
        item = {'images':images, 'instruction':instruction,
                'proprio':normalize_proprio(proprio, stats)}
        with self.base.torch.inference_mode():
            encoded = oft.prediction(self.base, item)
        normalized = encoded.actions[0].float().cpu().numpy()
        action = self.base.model._unnormalize_actions(normalized, self.base.cfg.unnorm_key)
        action = _action_array(action, chunk=True)
        if action.shape != (8,7):
            raise ValueError('Expected an OFT (8, 7) action chunk')
        return _decode_action(api, action, chunk=True)

    def reset(self):
        return self.base.reset()

    def close(self):
        return self.base.close()


def make_policy(config):
    return TaskControlPolicy(config)
