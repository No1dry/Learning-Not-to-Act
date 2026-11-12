"""Strict method-owned dispatch between two unchanged LIBERO bridge versions.

Describing/loading implementations reads source bytes only. Native scenes are
created only by the original environment's later reset, never by this module.
"""
from copy import deepcopy
import collections
from functools import wraps
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import types

from egrs.augmentation.data import identity
from egrs.augmentation.dependencies import activate_core

SCHEMA='task035-environment-dispatch-v1'
LEGACY_REVISION='ac1301779cf6ae4c34ebc80c20936a4f7a4953be'
CORE_REVISION='d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9'
LEGACY_BRIDGE='fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603'
CURRENT_BRIDGE='3a515dddc29311012180d4479dacd77511b510de44021ab6bc09516ca9a51efa'
COMPAT='d7519cd0817b99b6178370d3e1d64915bf2a14bd6c465a8e76b6c73983517555'
LEGACY_FILES={'benchmark/remaining_goals/libero_env.py':LEGACY_BRIDGE,
    'benchmark/remaining_goals/libero_compat.py':COMPAT,
    'benchmark/remaining_goals/schema.py':'3b554f4e913b587d59238287c8b2830d2c99598e0688519c0a2db8ae7236ec20'}


def coordination_identity():
    """Method-only transition lineage; never added retroactively to old runs."""
    result={'protocol':'task035-exact-owned-proxy-reset-v1',
        'implementation_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'compat_source_sha256':COMPAT,
        'strategy':'restore only exact owned proxy types to original collections before original reset'}
    result['identity']=identity(result)
    return result


def _coordinate_proxy_types(owned_types):
    """Release only these two stateless shims; foreign bindings stay rejected."""
    module=sys.modules.get('libero.libero.envs.utils')
    if module is None:return
    current=getattr(module,'collections',None)
    if current is collections:return
    if type(current) not in owned_types:
        raise RuntimeError('unexpected LIBERO utils.collections binding; refusing to hide a foreign patch')
    # Change the LIBERO-local binding, never the stdlib module itself. The
    # unchanged selected shim will install its own proxy during native reset.
    module.collections=collections


def _owned_proxy_types(dispatch):
    legacy_class=_legacy_environment(dispatch)
    namespace=legacy_class.__module__.rsplit('.headless.environment',1)[0]
    legacy=sys.modules[namespace+'.libero_compat']
    current=importlib.import_module('benchmark.remaining_goals.libero_compat')
    return (legacy._CollectionsProxy,current._CollectionsProxy)


def _legacy_files(root):
    for name,digest in LEGACY_FILES.items():
        path=(root/name).resolve()
        if (not path.is_relative_to(root) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
            raise ValueError('pinned legacy bridge dependency differs: '+name)


def describe_dispatch(legacy_root,core_root):
    """Validate exact old dependencies and the existing complete fixed core."""
    old=Path(legacy_root).resolve();core=Path(core_root).resolve()
    _legacy_files(old)
    revision=activate_core(core)
    if revision!=CORE_REVISION:raise ValueError('fixed dispatch core revision differs')
    core_manifest=json.loads(Path(__file__).resolve().parents[1].joinpath('augmentation/core_files.json').read_text(encoding='utf-8'))
    if core_manifest['files']['benchmark/remaining_goals/libero_env.py']!=CURRENT_BRIDGE:
        raise ValueError('fixed current bridge dependency differs')
    result={'schema_version':SCHEMA,'legacy_root':str(old),'core_root':str(core),
        'legacy_revision':LEGACY_REVISION,'core_revision':CORE_REVISION,
        'legacy_files':deepcopy(LEGACY_FILES),'core_files_identity':identity(core_manifest),
        'current_bridge_sha256':CURRENT_BRIDGE}
    result['identity']=identity(result)
    return result


def validate_dispatch(dispatch):
    """Recheck byte locks; a forged descriptor cannot authorize other code."""
    if (not isinstance(dispatch,dict) or dispatch.get('schema_version')!=SCHEMA
            or identity(dispatch)!=dispatch.get('identity')):
        raise ValueError('environment dispatch identity differs')
    actual=describe_dispatch(dispatch['legacy_root'],dispatch['core_root'])
    if actual!=dispatch:raise ValueError('environment dispatch dependency binding differs')
    return actual


def binding_for(environment,dispatch):
    """Select by a coherent complete source lock; runtime still rechecks it."""
    if (not isinstance(dispatch,dict) or dispatch.get('schema_version')!=SCHEMA
            or identity(dispatch)!=dispatch.get('identity') or dispatch.get('legacy_files')!=LEGACY_FILES
            or dispatch.get('current_bridge_sha256')!=CURRENT_BRIDGE):
        raise ValueError('environment dispatch identity differs')
    if not isinstance(environment,dict) or environment.get('name')!='libero' or not isinstance(environment.get('lock'),dict):
        raise ValueError('complete frozen LIBERO environment lock required')
    lock=environment['lock']
    fingerprint=hashlib.sha256(json.dumps(lock,sort_keys=True,allow_nan=False).encode()).hexdigest()
    if environment.get('fingerprint')!=fingerprint:
        raise ValueError('frozen environment fingerprint does not match its complete lock')
    compat=lock.get('compatibility',{})
    if compat.get('source_sha256')!=COMPAT:
        raise ValueError('unsupported frozen compatibility implementation')
    bridge=compat.get('bridge_source_sha256')
    if bridge==LEGACY_BRIDGE:
        implementation,revision,files='legacy-ac130177',LEGACY_REVISION,LEGACY_FILES
    elif bridge==CURRENT_BRIDGE:
        implementation,revision,files='current-d8541ef4',CORE_REVISION,{'core_files_identity':dispatch['core_files_identity']}
    else:raise ValueError('unsupported frozen bridge implementation')
    result={'implementation':implementation,'revision':revision,
        'expected_environment':deepcopy(environment),'source_files':deepcopy(files),
        'dispatch_identity':dispatch['identity']}
    result['identity']=identity(result)
    return result


def _package(name):
    module=types.ModuleType(name);module.__path__=[];module.__package__=name
    sys.modules[name]=module
    return module


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    # Execute the checked source bytes, not an unbound adjacent .pyc cache.
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def _legacy_environment(dispatch):
    """Execute unchanged source under a private package with explicit imports."""
    suffix=identity({'legacy_root':dispatch['legacy_root'],'core_root':dispatch['core_root']})[:20]
    namespace='egrs._task035_bridge_'+suffix
    target=namespace+'.headless.environment'
    if target in sys.modules:return sys.modules[target].HeadlessLiberoEnv
    old=Path(dispatch['legacy_root'])/'benchmark/remaining_goals'
    try:
        _package(namespace);_package(namespace+'.headless')
        for name in ('schema','libero_compat','libero_env'):
            _load(namespace+'.'+name,old/(name+'.py'))
        # Helpers and all their transitive code come from the already verified
        # 97-file execution core, never arbitrary legacy package imports.
        for name in ('headless.roles','headless.geometry','headless.protocols','finish','finish.environment','nine_catalog'):
            sys.modules[namespace+'.'+name]=importlib.import_module('benchmark.remaining_goals.'+name)
        module=_load(target,Path(dispatch['core_root'])/'benchmark/remaining_goals/headless/environment.py')
        return module.HeadlessLiberoEnv
    except BaseException:
        for name in list(sys.modules):
            if name==namespace or name.startswith(namespace+'.'):sys.modules.pop(name,None)
        raise


def make_environment(config,dispatch):
    """Construct original headless logic using the actual selected bridge.

The original bridge computes versions/source/assets/compatibility independently
and rejects a different fingerprint. No expected value is substituted for it.
"""
    validate_dispatch(dispatch)
    binding=binding_for(config.get('environment'),dispatch)
    if config.get('control_freq',20)!=binding['expected_environment']['lock'].get('control_freq'):
        raise ValueError('environment control frequency differs from frozen lock')
    if binding['implementation']=='legacy-ac130177':
        cls=_legacy_environment(dispatch)
    else:
        cls=importlib.import_module('benchmark.remaining_goals.headless.environment').HeadlessLiberoEnv
    env=cls(deepcopy(config))
    if env.identity!=binding['expected_environment']:
        env.close();raise ValueError('actual complete environment identity differs from frozen lock')
    try:
        owned_types=_owned_proxy_types(dispatch)
        _coordinate_proxy_types(owned_types)
        original_reset=env.reset
        @wraps(original_reset)
        def reset(*args,**kwargs):
            _coordinate_proxy_types(owned_types)
            return original_reset(*args,**kwargs)
        env.reset=reset
    except BaseException:
        env.close();raise
    return env
