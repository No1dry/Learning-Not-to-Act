"""Extend only fixed-index admission, not construction physics or score rules.

The pinned core's selected-source helpers admit indices 0..9. Private function
namespaces extend three *index guard* constants to 50, with an exact AST check.
No dependency module/file or global import is patched. The executed extension
and original dependency bytes are recorded alongside every new source.
"""
from copy import deepcopy
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import FunctionType

SCHEMA = 'task049-remain50-v1'
COUNT = 50
LEGACY_FILES = {
    'build.py': '84bd122e742a4b3506953e004d2408620a1353f8a12023cf4dc7504fc058b008',
    'construction.py': '3f16e4f912c2570eb329401e88ddb7123e7cc10be0cfb11647ec4dfb6fc23e1e',
    'validation.py': '6864d1fcf4ff0c90c0acb56700685c73474c5447e5bc4f2fda7d1e799f2dd235',
    'task_catalog.py': '44cca1decd518ca2b158ee8af89ad846fcb9e480fa5354bb56f83a1cbf4613ba',
    'observation_artifact.py': '02d49afc556061e86062111ba1f007abc3fd1412d47dd9d3711de9e8fccae2e1',
    'replay_candidates.py': 'c48fa83019cd93e5b76d39fa17ec7fde39cea8b8ebaf54a77a8ea546ae1bb9a2',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate049 field: ' + key)
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    temporary.replace(path)


def expected():
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    templates = {e['task_id']: e for e in expected_episodes('nine-mask10')}
    rows = []
    for task, template in templates.items():
        for index in range(COUNT):
            row = deepcopy(template)
            row.update(episode_id=f'{task}_s{index:03d}_10', initial_state_index=index,
                       source_id=f'{task}_official_{index}', policy_seed=7,
                       development_source=task == 'basket' and index < 5)
            rows.append(row)
    return rows


def _namespace(module):
    """Clone defined functions together, retaining original defaults/closures."""
    namespace = dict(vars(module))
    for name, value in vars(module).items():
        if inspect.isfunction(value) and value.__module__ == module.__name__:
            clone = FunctionType(value.__code__, namespace, name, value.__defaults__, value.__closure__)
            clone.__kwdefaults__ = value.__kwdefaults__
            namespace[name] = clone
    return namespace


def extend_index_guard(function, namespace):
    """Exactly one `index not in range(10)` admission becomes range(50).

    Physics loops, thresholds, class logic and all other constants are identical.
    Fail closed if a future dependency no longer has this precise seam.
    """
    tree = ast.parse(inspect.getsource(function))
    matches = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name)
                and node.left.id == 'index' and len(node.ops) == 1
                and isinstance(node.ops[0], ast.NotIn) and len(node.comparators) == 1):
            call = node.comparators[0]
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == 'range' and len(call.args) == 1
                    and isinstance(call.args[0], ast.Constant) and call.args[0].value == 10):
                matches.append(call.args[0])
    if len(matches) != 1:
        raise ValueError('Pinned049 index seam differs: ' + function.__name__)
    matches[0].value = COUNT
    local = {}
    exec(compile(ast.fix_missing_locations(tree), function.__code__.co_filename, 'exec'), namespace, local)
    return local[function.__name__]


def helpers():
    from benchmark.remaining_goals.headless import scoped_sources
    from benchmark.remaining_goals.task_catalog import COMMON_TEN_TASKS
    scoped = _namespace(scoped_sources)
    # selected-mask10 uses the unchanged legacy task catalogue; nine-mask10
    # keeps its original goal/invariant semantics. Callers restrict to nine10.
    scoped['SELECTED_TASKS'] = tuple(COMMON_TEN_TASKS)
    scoped['_identity'] = extend_index_guard(scoped_sources._identity, scoped)
    return scoped


def extension_identity():
    return {'schema_version': SCHEMA, 'index_domain': [0, 49],
            'index_extension_source_sha256': sha(__file__),
            'change': 'only three private index-admission guards 10->50; legacy selected catalogue reused',
            'score_modified': False, 'dependency_files_modified': False}


def activate(cfg):
    from egrs.augmentation.dependencies import activate_core, activate_reporting
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch
    activate_core(cfg['benchmark_root'])
    activate_reporting(cfg['reporting_root'])
    return describe_dispatch(cfg['legacy_root'], cfg['benchmark_root'])


def _legacy_backend(dispatch):
    from egrs.trajectory_augmentation import environment_dispatch as ed
    cls = ed._legacy_environment(dispatch)
    namespace = cls.__module__.rsplit('.headless.environment', 1)[0]
    import sys
    root = Path(dispatch['legacy_root']) / 'benchmark/remaining_goals'
    for name, expected_hash in LEGACY_FILES.items():
        if sha(root / name) != expected_hash:
            raise ValueError('Pinned049 legacy producer differs: ' + name)
    for name in ('task_catalog', 'validation', 'observation_artifact', 'construction', 'build', 'replay_candidates'):
        qualified = namespace + '.' + name
        if qualified not in sys.modules:
            ed._load(qualified, root / (name + '.py'))
    return sys.modules[namespace + '.build'], sys.modules[namespace + '.replay_candidates']


def producers(task, dispatch, scoped):
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from benchmark.remaining_goals import selected_build, selected_replay
    from egrs.trajectory_augmentation import environment_dispatch as ed
    legacy = task in REUSE_TASKS
    old_build, old_replay = _legacy_backend(dispatch)
    backend = old_build if legacy else importlib.import_module('benchmark.remaining_goals.build')
    replay_backend = old_replay if legacy else importlib.import_module('benchmark.remaining_goals.replay_candidates')
    builder = _namespace(selected_build)
    builder['build'] = extend_index_guard(selected_build.build, builder)
    replay = _namespace(selected_replay)
    replay['SELECTED_TASKS'] = tuple(scoped['SELECTED_TASKS'])
    replay['replay'] = extend_index_guard(selected_replay.replay, replay)
    replay['_candidate'] = lambda t, i, p, **kw: scoped['inspect_candidate'](t, i, p, **kw)
    replay['_backend'] = lambda: replay_backend
    def coordinate():
        ed._coordinate_proxy_types(ed._owned_proxy_types(dispatch))
    return backend, builder['build'], replay['replay'], replay_backend, coordinate


def protocol(task):
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    return 'selected-mask10' if task in REUSE_TASKS else 'nine-mask10'


def resolve(scoped, task, index, origin):
    from benchmark.remaining_goals.nine_catalog import NINE_TASKS
    if task not in NINE_TASKS or type(index) is not int or index not in range(COUNT):
        raise ValueError('049 requires one of nine LIBERO10 tasks and index0..49')
    source = scoped['resolve_source'](protocol(task), task, index, origin)
    if source['episodes'][0]['initial_mask'] != [True, False]:
        raise ValueError('049 requires actual mask10')
    return source


def original_origins(cfg):
    old = read(cfg['reference_config'])
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    inventory_path = Path(old['new_sources_10'])
    from benchmark.remaining_goals.headless.nine_planning import read_sources
    _, new = read_sources(inventory_path, 'nine-mask10')
    result = {}
    for row in expected():
        task, index = row['task_id'], row['initial_state_index']
        if index >= 10:
            continue
        if task in REUSE_TASKS:
            paths = old['legacy_sources_10'][task]
            manifest = read(paths['manifest'])
            origin = {**paths, 'manifest_sha256': sha(paths['manifest']),
                      'content_hash': manifest['content_hash'], 'replay_sha256': sha(paths['candidate_replay'])}
        else:
            origin = deepcopy(new[task, index])
        result[task, index] = origin
    return result
