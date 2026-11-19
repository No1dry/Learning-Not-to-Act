"""Three sources opt into052; original447 keep the complete unchanged051 path."""
import importlib
from pathlib import Path
import sys

from egrs.remain049 import sources as old
from egrs.remain051 import scope as previous
from . import policy

FAILED = {'stove_s021_10', 'two_pots_s011_10', 'two_pots_s045_10'}
REPAIR = 'task052-sparse-two-level-recovery-v1'


def extension_identity():
    return {'schema_version': old.SCHEMA, 'repair': REPAIR, 'index_domain': [0, 49],
            'scope_source_sha256': old.sha(__file__), 'admission': policy.identity(),
            'revised_episode_ids': sorted(FAILED), 'unchanged_sources': 447,
            'score_modified': False, 'dependency_files_or_canonical_modules_modified': False}


def package():
    import benchmark.remaining_goals as canonical
    directory = Path(canonical.__file__).parent.resolve()
    prefix = 'egrs._remain052_' + old.digest({'root': str(directory), 'extension': extension_identity()})[:16]
    if prefix in sys.modules:
        return sys.modules[prefix]
    root = previous._package(prefix, directory)
    previous._package(prefix+'.headless', directory/'headless')
    for name in ('schema', 'nine_catalog', 'task_catalog', 'libero_env', 'libero_compat',
                 'construction', 'observation_artifact', 'microwave_candidates'):
        previous._alias(prefix+'.'+name, 'benchmark.remaining_goals.'+name)
    for name in ('planning', 'protocols'):
        previous._alias(prefix+'.headless.'+name, 'benchmark.remaining_goals.headless.'+name)
    reader = previous._load(prefix+'.package_audit', directory/'package_audit.py')
    policy.configure_package_reader(reader)
    stability = previous._load(prefix+'.stability', directory/'stability.py')
    previous._extend_r7(stability)
    validation = previous._load(prefix+'.validation', directory/'validation.py')
    policy.configure_validation(validation)
    for name in ('build', 'replay_candidates', 'headless.source_acceptance', 'headless.rgb_revalidation',
                 'headless.scoped_sources', 'selected_build', 'selected_replay'):
        previous._load(prefix+'.'+name, directory/(name.replace('.', '/')+'.py'))
    acceptance = root.headless.source_acceptance
    original_audit = acceptance._audit
    def audit(value, *args, **kwargs):
        revised = value.get('observation_audit_rule',{}).get('rule_id') == policy.PROFILE
        if revised and value.get('task052_admission') != policy.identity():
            raise ValueError('052 audit lacks exact versioned admission binding')
        result = original_audit(value, *args, **kwargs)
        if revised:
            result['task052_admission'] = policy.identity()
        return result
    acceptance._audit = audit
    original_load = acceptance._load_mask10_source
    def load(task, manifest_path, replay_path, **kwargs):
        report = old.read(replay_path)
        if (report.get('observation_audit_rule') != validation.RGB_QUANTIZATION_RULE
                or report.get('observation_audit_limits') != policy.LIMITS):
            raise ValueError('052 replay must declare the actual sparse2 rule and limits')
        return original_load(task, manifest_path, replay_path, **kwargs)
    acceptance._load_mask10_source = load
    from benchmark.remaining_goals.task_catalog import COMMON_TEN_TASKS
    scoped = root.headless.scoped_sources
    scoped.SELECTED_TASKS = tuple(COMMON_TEN_TASKS)
    scoped._identity = old.extend_index_guard(scoped._identity, vars(scoped))
    root.selected_build.build = old.extend_index_guard(root.selected_build.build, vars(root.selected_build))
    root.selected_replay.SELECTED_TASKS = tuple(COMMON_TEN_TASKS)
    root.selected_replay.replay = old.extend_index_guard(root.selected_replay.replay, vars(root.selected_replay))
    return root


def legacy_package(dispatch):
    """Original legacy producer/control path; only private validation RGB bound."""
    from egrs.trajectory_augmentation import environment_dispatch as ed
    original_build, _ = old._legacy_backend(dispatch)  # checks all pinned producer bytes
    native_prefix = ed._legacy_environment(dispatch).__module__.rsplit('.headless.environment', 1)[0]
    directory = Path(dispatch['legacy_root'])/'benchmark/remaining_goals'
    prefix = 'egrs._remain052_legacy_' + old.digest({'root': str(directory), 'extension': extension_identity()})[:16]
    if prefix in sys.modules:
        return sys.modules[prefix]
    root = previous._package(prefix, directory)
    for name in ('schema', 'libero_env', 'libero_compat'):
        previous._alias(prefix+'.'+name, native_prefix+'.'+name)
    for name in ('construction', 'task_catalog', 'observation_artifact'):
        previous._load(prefix+'.'+name, directory/(name+'.py'))
    validation = previous._load(prefix+'.validation', directory/'validation.py')
    policy.configure_validation(validation)
    for name in ('build', 'replay_candidates'):
        previous._load(prefix+'.'+name, directory/(name+'.py'))
    # The producer itself is the pinned source; no placement, hold or physics seam.
    assert root.build.build.__code__.co_code == original_build.build.__code__.co_code
    return root


def helpers():
    strict = previous.helpers()
    revised = vars(package().headless.scoped_sources)
    result = dict(strict)
    def resolve(protocol, task, index, origin):
        target = revised if f'{task}_s{index:03d}_10' in FAILED else strict
        return target['resolve_source'](protocol, task, index, origin)
    def select(plan):
        return revised if plan['episodes'][0]['episode_id'] in FAILED else strict
    result['resolve_source'] = resolve
    result['archive_source'] = lambda directory, plan: select(plan)['archive_source'](directory, plan)
    result['validate_snapshot'] = lambda directory, plan: select(plan)['validate_snapshot'](directory, plan)
    return result


def producers(task, dispatch, scoped):
    from egrs.trajectory_augmentation import environment_dispatch as ed
    private = package()
    native = legacy_package(dispatch) if task == 'stove' else private
    replay = old._namespace(private.selected_replay)
    replay['_backend'] = lambda: native.replay_candidates
    replay['_candidate'] = lambda t, i, p, **kw: private.headless.scoped_sources.inspect_candidate(t, i, p, **kw)
    def coordinate():
        ed._coordinate_proxy_types(ed._owned_proxy_types(dispatch))
    return native.build, private.selected_build.build, replay['replay'], native.replay_candidates, coordinate
