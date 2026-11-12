"""Actual frozen bridge code with fake package metadata, never native scenes."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

import pytest


@pytest.fixture
def bridge_roots(tmp_path):
    core=Path(__file__).resolve().parents[2]/'LIBERO-Remain-task033-r2'
    old=tmp_path/'legacy'
    git=shutil.which('git')
    if git is None and os.name=='nt':
        git=str(Path(os.environ['LOCALAPPDATA'])/'Programs/Git/cmd/git.exe')
    for name in ('libero_env.py','libero_compat.py','schema.py'):
        relative='benchmark/remaining_goals/'+name
        target=old/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(subprocess.check_output([git,'show','ac1301779cf6ae4c34ebc80c20936a4f7a4953be:'+relative],cwd=core))
    return old,core


@pytest.fixture
def installed_libero(tmp_path,monkeypatch):
    root=tmp_path/'installed/libero';(root/'assets').mkdir(parents=True)
    (root/'__init__.py').write_bytes(b'# fixed synthetic LIBERO source\n')
    (root/'scene.bddl').write_bytes(b'(synthetic scene)\n')
    (root/'assets/mesh.obj').write_bytes(b'synthetic asset bytes\n')
    package=types.ModuleType('libero');package.__path__=[]
    inner=types.ModuleType('libero.libero');inner.__file__=str(root/'__init__.py');inner.__path__=[str(root)]
    package.libero=inner
    monkeypatch.setitem(sys.modules,'libero',package);monkeypatch.setitem(sys.modules,'libero.libero',inner)
    import importlib.metadata
    versions={'robosuite':'1.4.0','mujoco':'2.3.7'}
    def version(name):
        if name not in versions:raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]
    monkeypatch.setattr(importlib.metadata,'version',version)
    monkeypatch.setattr('platform.system',lambda:'Linux')
    return root,versions


def expected_environment(root,bridge_sha):
    """Independent complete lock from fixture bytes and pinned compatibility."""
    source=hashlib.sha256()
    for name,raw in [('__init__.py',b'# fixed synthetic LIBERO source\n'),('scene.bddl',b'(synthetic scene)\n')]:
        source.update(name.encode());source.update(hashlib.sha256(raw).digest())
    assets=hashlib.sha256(b'mesh.obj\0'+hashlib.sha256(b'synthetic asset bytes\n').digest()).hexdigest()
    compatibility={'protocol':'remaining-libero-runtime-compat-v1','rules':[
        'libero-utils-local-collections-iterable-proxy-v1','native-reset-randomization-only-bounded-retries-v1',
        'windows-private-macro-and-version-matched-dll-record-v1','post-step-synchronized-observations-forward-force-v1',
        'forward-free-ball-unit-quaternion-roundoff-16eps-restore-bits-v1',
        'panda-gripper-qpos-inverse-position-servo-clipped-command-and-ctrl-v1',
        'hard-reset-rebuild-bddl-property-samplers-without-history-accumulation-v1'],
        'source_sha256':'d7519cd0817b99b6178370d3e1d64915bf2a14bd6c465a8e76b6c73983517555',
        'bridge_source_sha256':bridge_sha,'platform':'Linux'}
    lock={'source_sha256':source.hexdigest(),'assets_sha256':assets,
        'versions':{'robosuite':'1.4.0','mujoco-py':None,'mujoco':'2.3.7'},'control_freq':20,
        'compatibility':compatibility}
    return {'name':'libero','fingerprint':hashlib.sha256(json.dumps(lock,sort_keys=True).encode()).hexdigest(),'lock':lock}


@pytest.mark.parametrize('implementation,sha',[
    ('legacy-ac130177','fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603'),
    ('current-d8541ef4','3a515dddc29311012180d4479dacd77511b510de44021ab6bc09516ca9a51efa')])
def test_actual_bridge_identity_and_original_headless_constructor(bridge_roots,installed_libero,implementation,sha):
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,binding_for,make_environment
    old,core=bridge_roots;root,_=installed_libero
    dispatch=describe_dispatch(old,core);expected=expected_environment(root,sha)
    binding=binding_for(expected,dispatch)
    assert binding['implementation']==implementation and binding['expected_environment']==expected
    import benchmark.remaining_goals.libero_env as standard
    standard_class=standard.LiberoGoalEnv
    env=make_environment({'manifest_dir':'unopened-fixture','environment':expected,'control_freq':20,
                          'protocol':'normal00-control'},dispatch)
    assert env.identity==expected and env.env is None and env.protocol.key=='normal00-control'
    assert standard.LiberoGoalEnv is standard_class
    if implementation.startswith('legacy'):
        base=sys.modules[type(env).__module__.rsplit('.',2)[0]+'.libero_env']
        assert Path(base.__file__).resolve()==old.resolve()/'benchmark/remaining_goals/libero_env.py'
        compat=sys.modules[base.__package__+'.libero_compat']
        assert compat.compatibility_identity()['bridge_source_sha256']==sha
    else:
        assert type(env).__module__=='benchmark.remaining_goals.headless.environment'
    env.close()


@pytest.mark.parametrize('changed',['source','asset','version','compat','unknown_bridge','lock_fingerprint'])
def test_full_runtime_lock_changes_are_rejected(bridge_roots,installed_libero,changed):
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,make_environment
    old,core=bridge_roots;root,versions=installed_libero
    dispatch=describe_dispatch(old,core)
    expected=expected_environment(root,'fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603')
    if changed=='source':(root/'scene.bddl').write_bytes(b'changed scene')
    elif changed=='asset':(root/'assets/mesh.obj').write_bytes(b'changed asset')
    elif changed=='version':versions['mujoco']='3.4.0'
    elif changed=='compat':expected['lock']['compatibility']['rules'].append('foreign-rule')
    elif changed=='unknown_bridge':expected['lock']['compatibility']['bridge_source_sha256']='f'*64
    else:expected['lock']['assets_sha256']='e'*64
    if changed in ('compat','unknown_bridge'):
        expected['fingerprint']=hashlib.sha256(json.dumps(expected['lock'],sort_keys=True).encode()).hexdigest()
    with pytest.raises(ValueError,match='fingerprint|environment|bridge|compatibility'):
        make_environment({'manifest_dir':'unopened','environment':expected,'control_freq':20},dispatch)


@pytest.mark.parametrize('name',['libero_env.py','libero_compat.py','schema.py'])
def test_changed_legacy_dependency_bytes_rejected(bridge_roots,name):
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,validate_dispatch
    old,core=bridge_roots;dispatch=describe_dispatch(old,core)
    with (old/'benchmark/remaining_goals'/name).open('ab') as stream:stream.write(b'\n# changed\n')
    with pytest.raises(ValueError,match='legacy|dependency'):validate_dispatch(dispatch)


def test_forged_dispatch_description_rejected(bridge_roots):
    from egrs.trajectory_augmentation.environment_dispatch import describe_dispatch,validate_dispatch
    old,core=bridge_roots;dispatch=describe_dispatch(old,core)
    dispatch['legacy_files']['benchmark/remaining_goals/schema.py']='f'*64
    with pytest.raises(ValueError,match='dispatch|legacy'):validate_dispatch(dispatch)
