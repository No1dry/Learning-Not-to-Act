"""Private pinned helper package: extend all four source-index guards only.

R7's inner validation imports must see the same extended admission in build,
replay and file readers. A private package keeps relative imports coherent,
without modifying canonical modules, dependency files, physics or RGB limits.
Native bridge/compatibility modules are aliases of the unchanged canonical core.
"""
import ast
import importlib
import importlib.util
import inspect
from pathlib import Path
import sys
from types import ModuleType

from egrs.remain049 import sources as old

REPAIR = 'task051-four-guard-strict-recovery-v1'


def extension_identity():
    return {'schema_version':old.SCHEMA, 'index_domain':[0,49], 'repair':REPAIR,
            'index_extension_source_sha256':old.sha(__file__),
            'change':'four private index guards 10->50, including nested R7 stability admission',
            'score_modified':False, 'physical_or_RGB_limits_modified':False,
            'dependency_files_or_canonical_modules_modified':False}


def _package(name, directory):
    module=ModuleType(name);module.__package__=name;module.__path__=[str(directory)]
    sys.modules[name]=module
    if '.' in name:
        parent,child=name.rsplit('.',1);setattr(sys.modules[parent],child,module)
    return module


def _alias(name, canonical):
    module=importlib.import_module(canonical);sys.modules[name]=module
    parent,child=name.rsplit('.',1);setattr(sys.modules[parent],child,module)


def _load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(Path(path).read_bytes(),str(path),'exec'),module.__dict__)
    parent,child=name.rsplit('.',1);setattr(sys.modules[parent],child,module)
    return module


def _extend_r7(module):
    tree=ast.parse(inspect.getsource(module.validate_scope));matches=[]
    for node in ast.walk(tree):
        if (isinstance(node,ast.Compare) and len(node.ops)==1 and isinstance(node.ops[0],ast.NotIn)
                and isinstance(node.left,ast.Subscript) and isinstance(node.left.value,ast.Name)
                and node.left.value.id=='episode' and isinstance(node.left.slice,ast.Constant)
                and node.left.slice.value=='initial_state_index' and len(node.comparators)==1):
            call=node.comparators[0]
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='range'
                    and len(call.args)==1 and isinstance(call.args[0],ast.Constant) and call.args[0].value==10):
                matches.append(call.args[0])
    if len(matches)!=1:raise ValueError('Pinned051 R7 index seam differs')
    matches[0].value=50;local={}
    exec(compile(ast.fix_missing_locations(tree),module.__file__,'exec'),vars(module),local)
    module.validate_scope=local['validate_scope']


def package():
    """Called only after the complete fixed core has been activated/verified."""
    import benchmark.remaining_goals as canonical
    directory=Path(canonical.__file__).parent.resolve()
    prefix='egrs._remain051_'+old.digest({'root':str(directory),'repair':extension_identity()})[:16]
    if prefix in sys.modules:return sys.modules[prefix]
    try:
        root=_package(prefix,directory);_package(prefix+'.headless',directory/'headless')
        for name in ('schema','nine_catalog','task_catalog','libero_env','libero_compat','construction',
                     'observation_artifact','microwave_candidates','package_audit'):
            _alias(prefix+'.'+name,'benchmark.remaining_goals.'+name)
        for name in ('planning','protocols'):
            _alias(prefix+'.headless.'+name,'benchmark.remaining_goals.headless.'+name)
        stability=_load(prefix+'.stability',directory/'stability.py');_extend_r7(stability)
        for name in ('validation','build','replay_candidates','headless.source_acceptance',
                     'headless.rgb_revalidation','headless.scoped_sources','selected_build','selected_replay'):
            _load(prefix+'.'+name,directory/(name.replace('.','/')+'.py'))
        from benchmark.remaining_goals.task_catalog import COMMON_TEN_TASKS
        scoped=root.headless.scoped_sources
        scoped.SELECTED_TASKS=tuple(COMMON_TEN_TASKS)
        scoped._identity=old.extend_index_guard(scoped._identity,vars(scoped))
        root.selected_build.build=old.extend_index_guard(root.selected_build.build,vars(root.selected_build))
        root.selected_replay.SELECTED_TASKS=tuple(COMMON_TEN_TASKS)
        root.selected_replay.replay=old.extend_index_guard(root.selected_replay.replay,vars(root.selected_replay))
        return root
    except BaseException:
        for name in list(sys.modules):
            if name==prefix or name.startswith(prefix+'.'):sys.modules.pop(name,None)
        parent,child=prefix.rsplit('.',1)
        if hasattr(sys.modules[parent],child):delattr(sys.modules[parent],child)
        raise


def helpers():return vars(package().headless.scoped_sources)


def producers(task, dispatch, scoped):
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from egrs.trajectory_augmentation import environment_dispatch as ed
    private=package();legacy=task in REUSE_TASKS
    old_build,old_replay=old._legacy_backend(dispatch)
    build=old_build if legacy else private.build
    replay_backend=old_replay if legacy else private.replay_candidates
    replay=old._namespace(private.selected_replay)
    replay['_backend']=lambda:replay_backend
    def coordinate():ed._coordinate_proxy_types(ed._owned_proxy_types(dispatch))
    return build,private.selected_build.build,replay['replay'],replay_backend,coordinate
