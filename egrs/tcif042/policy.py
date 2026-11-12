"""One042 student using the accepted current-frame sensors and action decoding."""
from copy import deepcopy

from egrs.task_control.policy import TaskControlPolicy


class TCIF042Policy(TaskControlPolicy):
    def __init__(self, config):
        from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
        from benchmark.remaining_goals.adapters.oft_transfer import FACTORY as BASE_FACTORY
        from .adapter import read_adapter_identity,attach_trained_adapter
        base_config = deepcopy(config)
        directory = base_config.pop('method_adapter')
        arm = base_config.pop('task_control_arm')
        experiment_arm = base_config.pop('experiment_arm')
        identity = read_adapter_identity(directory)
        if (arm != 'c1' or experiment_arm not in ('f0','f1')
                or identity['experiment_arm'] != experiment_arm or identity['update'] != 1000):
            raise ValueError('042 evaluation requires base c1 and the requested experiment arm final1000')
        base_config['policy_factory'] = BASE_FACTORY
        self.base = OpenVLAOFTPolicy(base_config)
        try:
            identity = attach_trained_adapter(self.base,directory,experiment_arm=experiment_arm)
            self.metadata = deepcopy(self.base.metadata)
            self.metadata.update(method_adapter=identity,task_control_arm='c1',experiment_arm=experiment_arm,
                attention_contract=deepcopy(identity['attention_contract']),
                attention_runtime=deepcopy(self.base._tcif042.runtime),ancestor_updates=2000,
                additional_updates=identity['update'],total_ancestral_updates=2000+identity['update'])
        except BaseException:
            self.base.close()
            raise

    def predict(self, observation, instruction):
        import numpy as np
        from benchmark.remaining_goals.adapters.openvla import (
            _instruction,_raw_observation,_action_array,_decode_action)
        from experiments.robot.openvla_utils import normalize_proprio
        from . import oft
        self.base.reset()
        instruction = _instruction(instruction)
        raw = _raw_observation(observation,wrist=True,proprio=True)
        api = self.base.api
        images = [api.get_libero_image(raw),api.get_libero_wrist_image(raw)]
        proprio = np.concatenate((raw['robot0_eef_pos'],api.quat2axisangle(raw['robot0_eef_quat']),
                                  raw['robot0_gripper_qpos']))
        stats = self.base.model.norm_stats[self.base.cfg.unnorm_key]['proprio']
        item = {'images':images,'instruction':instruction,'proprio':normalize_proprio(proprio,stats)}
        with self.base.torch.inference_mode():
            encoded = oft.prediction(self.base,item)
        normalized = encoded.actions[0].float().cpu().numpy()
        action = self.base.model._unnormalize_actions(normalized,self.base.cfg.unnorm_key)
        action = _action_array(action,chunk=True)
        if action.shape != (8,7):
            raise ValueError('Expected an OFT (8, 7) action chunk')
        return _decode_action(api,action,chunk=True)


def make_policy(config):
    return TCIF042Policy(config)
