"""Private runtime registration for the three frozen composition tasks."""
from egrs.composition055.catalog import TASK_ORDER

TASK_SUITE = 'libero_remain_composition055'
PROTOCOL = 'mask10'
PROTOCOL_VERSION = 'remaining-headless-goal-endpoint-v1'
BANK_SHA256 = '4a60ea3c25c379204353b0c5dfc167b16718f535426b918618f5a5221282ee0b'
PREPARATION_IDENTITY = 'dd36fda6e6bf355db0682652e1b82329d01df8cbb77d43b1ebaa20d1daecc348'
ADAPTER_SHA256 = {
    'h0': 'e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20',
    'h1': '78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d',
}
MODEL_ORDER = ('base', 'h0', 'h1')


def task_index(task_id):
    if task_id not in TASK_ORDER:
        raise ValueError(f'unknown056 task {task_id!r}')
    return TASK_ORDER.index(task_id)


def register(source, archived_directory):
    from libero.libero import benchmark as native_benchmark
    from benchmark.remaining_goals.headless import roles

    episode = source['episodes'][0]
    task_id = episode['task_id']
    task_index(task_id)
    if episode['suite'] != TASK_SUITE:
        raise ValueError('056 source suite differs from the isolated composition suite')
    task = native_benchmark.Task(
        name=episode['task_name'], language=episode['instruction'], problem='Libero',
        problem_folder=str(archived_directory), bddl_file='task.bddl', init_states_file='state.npy')
    native_benchmark.task_maps[TASK_SUITE] = {episode['task_name']: task}

    class CompositionBenchmark(native_benchmark.Benchmark):
        def __init__(self, task_order_index=0):
            super().__init__(task_order_index=task_order_index)
            self.name = TASK_SUITE
            self._make_benchmark()

    native_benchmark.BENCHMARK_MAPPING[TASK_SUITE] = CompositionBenchmark
    profile = {
        'suite': TASK_SUITE,
        'name': episode['task_name'],
        'goals': episode['goal_specs'],
    }
    roles.TASKS = {**roles.TASKS, task_id: profile}
    roles.COMMON_TEN_TASKS = tuple(dict.fromkeys((*roles.COMMON_TEN_TASKS, task_id)))
    roles.PROFILES = {**roles.PROFILES, task_id: {'basket_1_contain_region': 'basket_1'}}
    return {
        'suite': TASK_SUITE,
        'task_id': task_id,
        'libero_task_id': task_index(task_id),
        'task_name': episode['task_name'],
        'instruction': episode['instruction'],
        'problem_folder': str(archived_directory),
        'bddl_sha256': episode['bddl_sha256'],
        'goal_specs': episode['goal_specs'],
    }
