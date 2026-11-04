"""Fixed compatibility source and one shared synthetic utils; no native reset."""
import collections
import importlib
from pathlib import Path
import sys
import types

import pytest

from test_trajectory_environment_dispatch import bridge_roots,installed_libero,expected_environment


@pytest.fixture
def compatibility_pair(bridge_roots,monkeypatch):
    old,core=bridge_roots
    modules=[]
    for name,root in (('old',old),('new',core)):
        path=root/'benchmark/remaining_goals/libero_compat.py'
        module=types.ModuleType('_task035_test_'+name);module.__file__=str(path)
        exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
        modules.append(module)
    utils=types.SimpleNamespace(collections=collections)
    monkeypatch.setitem(sys.modules,'libero.libero.envs.utils',utils)
    return modules,utils


@pytest.mark.parametrize('sequence',[(0,0,1,1,0),(1,1,0,0,1)])
def test_same_utils_bidirectional_and_repeat_calls(compatibility_pair,sequence):
    from egrs.trajectory_augmentation.environment_dispatch import _coordinate_proxy_types
    modules,utils=compatibility_pair
    classes=tuple(m._CollectionsProxy for m in modules)
    before=dict(vars(collections))
    # Existing first-version proxy before method coordination is also owned.
    modules[sequence[0]].apply_libero_compat()
    for index in sequence:
        _coordinate_proxy_types(classes)
        assert utils.collections is collections
        modules[index].apply_libero_compat()
        assert type(utils.collections) is classes[index]
        assert utils.collections.Iterable is collections.abc.Iterable
    assert vars(collections)==before


@pytest.mark.parametrize('foreign',['object','namespace','old_subclass','new_subclass'])
def test_foreign_or_subclass_proxy_is_rejected_untouched(compatibility_pair,foreign):
    from egrs.trajectory_augmentation.environment_dispatch import _coordinate_proxy_types
    modules,utils=compatibility_pair
    classes=tuple(m._CollectionsProxy for m in modules)
    if foreign=='object':value=object()
    elif foreign=='namespace':value=types.SimpleNamespace(Iterable=collections.abc.Iterable)
    else:value=type('ForeignProxy',(classes[0 if foreign=='old_subclass' else 1],),{})()
    utils.collections=value
    with pytest.raises(RuntimeError,match='foreign patch'):_coordinate_proxy_types(classes)
    assert utils.collections is value


def test_actual_factory_guards_each_original_reset_and_keeps_identity(bridge_roots,installed_libero,monkeypatch):
    from egrs.trajectory_augmentation import environment_dispatch as module
    old,core=bridge_roots;installed,_=installed_libero
    dispatch=module.describe_dispatch(old,core)
    old_class=module._legacy_environment(dispatch)
    current=importlib.import_module('benchmark.remaining_goals.headless.environment').HeadlessLiberoEnv
    old_namespace=old_class.__module__.rsplit('.headless.environment',1)[0]
    old_compat=sys.modules[old_namespace+'.libero_compat']
    new_compat=importlib.import_module('benchmark.remaining_goals.libero_compat')
    utils=types.SimpleNamespace(collections=collections)
    monkeypatch.setitem(sys.modules,'libero.libero.envs.utils',utils)
    calls=[]
    def original_reset(compat):
        def reset(self,episode):
            # This fake replaces only physical reset; the wrapper must clean
            # the shared owned proxy before delegating to this exact callable.
            assert utils.collections is collections
            compat.apply_libero_compat();calls.append(episode)
            return {'episode':episode}
        return reset
    monkeypatch.setattr(old_class,'reset',original_reset(old_compat))
    monkeypatch.setattr(current,'reset',original_reset(new_compat))
    for index,(kind,sha) in enumerate([(old_class,module.LEGACY_BRIDGE),(current,module.CURRENT_BRIDGE),
                                     (old_class,module.LEGACY_BRIDGE),(current,module.CURRENT_BRIDGE)]):
        expected=expected_environment(installed,sha)
        env=module.make_environment({'manifest_dir':'unopened','environment':expected,
                                    'control_freq':20,'protocol':'normal00-control'},dispatch)
        assert env.identity==expected and env.env is None
        assert env.reset(index)=={'episode':index}
        assert env.reset(index)=={'episode':index}
        assert type(utils.collections) is (old_compat if kind is old_class else new_compat)._CollectionsProxy
        env.close()
    assert calls==[0,0,1,1,2,2,3,3]


def test_coordination_identity_is_method_source_not_old_parent_identity():
    from egrs.trajectory_augmentation import environment_dispatch as module
    from egrs.augmentation.data import file_sha256,identity
    record=module.coordination_identity()
    assert record['protocol']=='task035-exact-owned-proxy-reset-v1'
    assert record['implementation_source_sha256']==file_sha256(Path(module.__file__))
    assert record['compat_source_sha256']==module.COMPAT
    assert identity(record)==record['identity']
