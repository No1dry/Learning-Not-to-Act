"""Task055 durable150 orchestration, with native construction replaced by a CPU fixture."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def configured(tmp_path, monkeypatch):
    from egrs.composition055 import catalog
    inputs=tmp_path/'inputs';inputs.mkdir()
    bddl=inputs/'canonical.bddl';bddl.write_bytes(b'CPU fake canonical BDDL')
    states=inputs/'canonical.pruned_init';states.write_bytes(b'CPU fake init serialization; never unpickled')
    monkeypatch.setattr(catalog,'CANONICAL_BDDL_SHA256',hashlib.sha256(bddl.read_bytes()).hexdigest())
    monkeypatch.setattr(catalog,'CANONICAL_INITIAL_STATES_SHA256',hashlib.sha256(states.read_bytes()).hexdigest())
    env=inputs/'environment.json';write(env,{'environment':{'name':'libero','fingerprint':'a'*64,'lock':{'control_freq':20}}})
    core=inputs/'core';core.mkdir()
    protected=tmp_path/'old450';protected.mkdir();(protected/'unchanged.json').write_bytes(b'old bank, training and results')
    config={'schema_version':'task055-composition-build-v1','benchmark_root':str(core),
        'canonical_bddl':str(bddl),'canonical_initial_states':str(states),'environment_config':str(env),
        'protected_roots':[str(protected)]}
    path=tmp_path/'configs'/'build.json';write(path,config)
    return path, config, protected


def fake_native(monkeypatch, *, failure=None, interrupt=None, invalidate=None):
    from egrs.composition055 import preparation as p
    called=[]
    monkeypatch.setattr(p,'activate',lambda cfg:'d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9')
    def build(cfg,row,destination,checkpoint):
        index=len(called);called.append(deepcopy(row))
        # The real orchestration must persist budget before native work.
        report=json.loads((destination.parent.parent/'sources.json').read_text(encoding='utf-8'))
        assert report['attempted']==index+1
        assert report['rows'][index]['status']=='running'
        destination.mkdir(parents=True, exist_ok=False)
        checkpoint({'phase':'fake_native','attempted_control_steps':3,'completed_control_steps':3,'failed_control_steps':0})
        if index==interrupt:raise KeyboardInterrupt('synthetic interrupt')
        if index==failure:
            write(destination/'failure.json',{'error':'synthetic unreleased object'})
            return {'status':'failed','error':'synthetic unreleased object'}
        manifest=destination/'source.json';write(manifest,{'fake':True,'episode':row})
        return {'status':'ready','source_manifest':str(manifest)}
    def inspect(path,row,cfg):
        if row['initial_state_index']==invalidate:raise ValueError('synthetic missing release evidence')
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        assert data=={'fake':True,'episode':row}
        return {**row,'source_manifest':str(path),'source_manifest_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    monkeypatch.setattr(p,'build_source',build);monkeypatch.setattr(p,'inspect_source',inspect)
    return called


def test_fake150_is_fixed_precompleted_only_fresh_and_keeps_all_old_bytes(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,cfg,protected=configured;before=(protected/'unchanged.json').read_bytes()
    called=fake_native(monkeypatch);output=tmp_path/'new150'
    report=p.prepare(path,output)
    assert len(called)==150 and report['ready']==150 and report['complete'] is True
    assert report['ordinary_state_count']==0 and report['model_rollouts']==0 and report['eligible_for_training'] is False
    assert [(r['task_id'],r['initial_state_index']) for r in called]==[
        (task,index) for task in ('composition_soup_butter','composition_tomato_cheese','composition_tomato_butter') for index in range(50)]
    assert all(r['initial_mask']==[True,False] and r['split']=='test' for r in called)
    assert [t['ready'] for t in report['per_task'].values()]==[50,50,50]
    assert p.read_bank(output)['complete'] is True
    assert (protected/'unchanged.json').read_bytes()==before
    with pytest.raises(FileExistsError):p.prepare(path,output)
    assert len(called)==150


def test_failed_source_retained_no_retry_no_replacement_and_no_false150(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,_,_=configured;called=fake_native(monkeypatch,failure=51);output=tmp_path/'partial'
    report=p.prepare(path,output)
    assert len(called)==150 and report['ready']==149 and report['failed']==1 and report['pending']==0
    assert report['complete'] is False and report['per_task']['composition_tomato_cheese']['failed']==1
    assert report['rows'][51]['status']=='failed' and 'unreleased' in report['rows'][51]['error']
    assert (output/'sources'/report['rows'][51]['episode_id']/'failure.json').is_file()
    assert p.read_bank(output)['complete'] is False
    with pytest.raises(FileExistsError):p.prepare(path,output)
    assert len(called)==150


def test_interrupt_keeps_spent_source_and_pending_denominator(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,_,_=configured;called=fake_native(monkeypatch,interrupt=2);output=tmp_path/'interrupted'
    with pytest.raises(KeyboardInterrupt):p.prepare(path,output)
    report=json.loads((output/'sources.json').read_text(encoding='utf-8'))
    assert len(called)==report['attempted']==3
    assert report['ready']==2 and report['failed']==1 and report['pending']==147
    assert report['complete'] is False and report['status']=='interrupted'
    with pytest.raises(FileExistsError):p.prepare(path,output)


@pytest.mark.parametrize('which',['canonical_bddl','canonical_initial_states'])
def test_canonical_changed_bytes_refused_before_any_native_work(configured,tmp_path,monkeypatch,which):
    from egrs.composition055 import preparation as p
    path,cfg,_=configured;called=fake_native(monkeypatch)
    Path(cfg[which]).write_bytes(b'foreign bytes')
    with pytest.raises(ValueError,match='SHA|canonical'):p.prepare(path,tmp_path/'out')
    assert called==[] and not (tmp_path/'out').exists()


@pytest.mark.parametrize('change',[{'normal_states':True},{'count':49},{'model':'base'},{'schema_version':'old'}])
def test_extra_modes_or_population_knobs_refused(configured,tmp_path,monkeypatch,change):
    from egrs.composition055 import preparation as p
    path,cfg,_=configured;called=fake_native(monkeypatch);write(path,{**cfg,**change})
    with pytest.raises(ValueError):p.prepare(path,tmp_path/'out')
    assert called==[]


def test_output_cannot_overlap_old_bank_input_or_method_code(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,cfg,protected=configured;called=fake_native(monkeypatch)
    for output in (protected/'new',Path(cfg['benchmark_root'])/'new',Path(cfg['canonical_bddl']).parent/'new',
                   Path(p.__file__).parent/'should-not-create'):
        with pytest.raises(ValueError,match='overlap|protected'):p.prepare(path,output)
        assert not output.exists()
    assert called==[]


def test_source_readback_failure_is_failed_not_ready(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,_,_=configured;called=fake_native(monkeypatch,invalidate=17)
    report=p.prepare(path,tmp_path/'out')
    assert len(called)==150 and report['ready']==147 and report['failed']==3 and not report['complete']


@pytest.mark.parametrize('mutation',['duplicate','missing','out_of_order','out_of_range','source_bytes'])
def test_frozen_bank_rejects_population_or_artifact_corruption(configured,tmp_path,monkeypatch,mutation):
    from egrs.composition055 import preparation as p
    path,_,_=configured;fake_native(monkeypatch);output=tmp_path/'out';p.prepare(path,output)
    report=json.loads((output/'sources.json').read_text(encoding='utf-8'))
    if mutation=='duplicate':report['rows'][1]=deepcopy(report['rows'][0])
    elif mutation=='missing':report['rows'].pop()
    elif mutation=='out_of_order':report['rows'][0],report['rows'][1]=report['rows'][1],report['rows'][0]
    elif mutation=='out_of_range':report['rows'][0]['initial_state_index']=50
    else:Path(report['rows'][0]['source_manifest']).write_bytes(b'changed')
    write(output/'sources.json',report)
    with pytest.raises(ValueError):p.read_bank(output)


def test_actual_template_expands_paths_and_rejects_unresolved(configured,monkeypatch):
    from egrs.composition055.contracts import load_config
    path,cfg,protected=configured
    template=Path(__file__).resolve().parents[1]/'configs/composition055/build.example.json'
    for key,value in {'LNA_CORE':cfg['benchmark_root'],'LNA_CANONICAL_BDDL':cfg['canonical_bddl'],
        'LNA_CANONICAL_STATES':cfg['canonical_initial_states'],'LNA_ENVIRONMENT_CONFIG':cfg['environment_config'],
        'LNA_EXISTING_DATA_ROOT':str(protected),'LNA_EXISTING_RUNS_ROOT':str(protected)}.items():monkeypatch.setenv(key,value)
    loaded=load_config(template)
    assert loaded['canonical_initial_states']==cfg['canonical_initial_states']
    monkeypatch.delenv('LNA_CANONICAL_STATES')
    with pytest.raises(ValueError,match='Unresolved'):load_config(template)


def test_fresh_cli_help_has_no_native_or_training_routes():
    code="""
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','mujoco','libero','robosuite','benchmark'}:raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
sys.argv=['composition055','--help']
from egrs.composition055.__main__ import main
main()
"""
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert '{build,inspect}' in result.stdout


def test_fresh_cli_activates_before_native_boundary(configured,tmp_path):
    path,_,_=configured
    code="""
import sys
from pathlib import Path
from egrs.composition055 import preparation as p,catalog
from egrs.composition055.contracts import sha,read
cfg=read(sys.argv[1]);catalog.CANONICAL_BDDL_SHA256=sha(cfg['canonical_bddl']);catalog.CANONICAL_INITIAL_STATES_SHA256=sha(cfg['canonical_initial_states'])
seen=[]
def activate(cfg):seen.append('activated');return 'd8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9'
def build(cfg,row,destination,checkpoint):
 assert seen==['activated']
 raise KeyboardInterrupt('CPU boundary sentinel')
p.activate=activate;p.build_source=build
from egrs.composition055.__main__ import main
try: main(['build','--config',sys.argv[1],'--output',sys.argv[2]])
except KeyboardInterrupt: print('ACTIVATED_BEFORE_NATIVE')
"""
    result=subprocess.run([sys.executable,'-c',code,str(path),str(tmp_path/'cold')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'ACTIVATED_BEFORE_NATIVE' in result.stdout


def test_atomic_checkpoint_windows_sharing_lock_retries_only_the_rename(tmp_path,monkeypatch):
    from egrs.composition055 import contracts as c
    calls=[];real=c.os.replace
    def replace(source,target):
        calls.append((source,target))
        if len(calls)==1:
            error=PermissionError('synthetic Windows sharing lock');error.winerror=5;raise error
        return real(source,target)
    monkeypatch.setattr(c.os,'replace',replace)
    c.write(tmp_path/'record.json',{'spent':1})
    assert c.read(tmp_path/'record.json')=={'spent':1} and len(calls)==2


def test_failed_durable_native_checkpoint_stops_before_next_source(configured,tmp_path,monkeypatch):
    from egrs.composition055 import preparation as p
    path,_,_=configured;called=fake_native(monkeypatch);real=p.write
    def write_fail(target,value):
        if target.parent.name=='controls':raise OSError('synthetic ledger storage failure')
        return real(target,value)
    monkeypatch.setattr(p,'write',write_fail)
    with pytest.raises(OSError,match='ledger|checkpoint'):p.prepare(path,tmp_path/'out')
    assert len(called)==1


@pytest.mark.parametrize('mutation',['delete_failure','edit_failure','delete_ledger'])
def test_failed_and_interrupted_evidence_is_retained_and_verified(configured,tmp_path,monkeypatch,mutation):
    from egrs.composition055 import preparation as p
    path,_,_=configured;called=fake_native(monkeypatch,failure=0,interrupt=1);output=tmp_path/'partial'
    with pytest.raises(KeyboardInterrupt):p.prepare(path,output)
    report=p.read_bank(output)
    assert report['failed']==2 and report['pending']==148 and len(called)==2
    # A pre-native interrupt need not invent native failure.json; a native failure
    # must retain the exact evidence it actually produced.
    row=report['rows'][0]
    failure=output/'sources'/row['episode_id']/'failure.json'
    if mutation=='delete_failure':failure.unlink()
    elif mutation=='edit_failure':failure.write_bytes(b'failure silently changed')
    else:Path(row['control_ledger']).unlink()
    with pytest.raises((ValueError,OSError)):p.read_bank(output)
    assert len(called)==2
