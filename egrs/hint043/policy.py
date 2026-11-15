"""Native unhinted deployment. No sidecar or reference teacher is constructed."""
from copy import deepcopy

from .contracts import require


class HintPolicy:
    def __init__(self,config):
        from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
        from benchmark.remaining_goals.adapters.oft_transfer import FACTORY
        from .adapter import attach
        cfg=deepcopy(config)
        require(not {'hint','status','sidecar','sidecar_dir','teacher_adapter','task_control_arm','experiment_arm'} & cfg.keys(),
                'Deployment cannot receive training hints or a historical research controller')
        directory=cfg.pop('method_adapter');arm=cfg.pop('hint043_arm')
        require(arm in ('h0','h1'),'043 evaluation arm required')
        cfg['policy_factory']=FACTORY
        self.base=OpenVLAOFTPolicy(cfg)
        try:
            value=attach(self.base,directory,arm)
            self.metadata=deepcopy(self.base.metadata)
            self.metadata.update(method_adapter=value,hint043_arm=arm,deployment_hint=False)
        except BaseException:
            self.base.close()
            raise

    def predict(self,observation,instruction):
        # Never forward evaluator facts or arbitrary training metadata to OFT.
        keys=('images','proprio','agentview_image','robot0_eye_in_hand_image',
              'robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos')
        require(isinstance(instruction,str) and bool(instruction.strip()),'Original instruction required')
        return self.base.predict({k:deepcopy(observation[k]) for k in keys if k in observation},instruction)

    def reset(self):return self.base.reset()
    def close(self):return self.base.close()


def make_policy(config):return HintPolicy(config)
