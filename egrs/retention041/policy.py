"""One041 student, with the accepted current-frame action encoding and decoding."""
from copy import deepcopy

from egrs.task_control.policy import TaskControlPolicy


class Retention041Policy(TaskControlPolicy):
    def __init__(self, config):
        from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
        from benchmark.remaining_goals.adapters.oft_transfer import FACTORY as BASE_FACTORY
        from .adapter import read_adapter_identity, attach_trained_adapter
        base_config = deepcopy(config)
        directory = base_config.pop('method_adapter')
        arm = base_config.pop('task_control_arm')
        experiment_arm = base_config.pop('experiment_arm')
        identity = read_adapter_identity(directory)
        if (arm != 'c1' or experiment_arm not in ('r0','r1')
                or identity['experiment_arm'] != experiment_arm or identity['update'] != 1000):
            raise ValueError('041 evaluation requires base c1 and the requested experiment arm final1000')
        base_config['policy_factory'] = BASE_FACTORY
        self.base = OpenVLAOFTPolicy(base_config)
        try:
            identity = attach_trained_adapter(self.base, directory, experiment_arm=experiment_arm)
            self.metadata = deepcopy(self.base.metadata)
            self.metadata.update(method_adapter=identity, task_control_arm='c1',experiment_arm=experiment_arm)
        except BaseException:
            self.base.close()
            raise


def make_policy(config):
    return Retention041Policy(config)
