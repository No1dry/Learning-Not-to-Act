"""Actual core result/evidence gates with fake physics; immutable continuation."""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def core():
    from egrs.augmentation.dependencies import activate_core,activate_reporting
    activate_core(os.environ['EGRS049_CORE']);activate_reporting(os.environ['EGRS049_REPORTING'])


def raw_fixture(tmp_path,monkeypatch,index):
    path=Path(os.environ['EGRS049_CORE'])/'tests/test_headless_runner.py'
    spec=importlib.util.spec_from_file_location('_headless053_fixture',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.synthetic_measurement_validator.__wrapped__(monkeypatch)
    e=m.episode(episode_id=f'basket_s{index:03d}_10',initial_state_index=index,seed=index)
    identity={'episode_id':e['episode_id'],'state_sha256':'a'*64,'model_runtime_sha256':'f'*64,
        'track':'libero_10','model_identity':{'checkpoint':'synthetic-sog10','normalization_key':'libero_10'}}
    recorder=m.HeadlessEvidence(tmp_path/'evidence'/'ep',identity)
    result=m.run_episode(m.Env(),m.Policy(),e,horizon=16,evidence=recorder,identity=identity)
    return e,identity,result


@pytest.mark.parametrize('index',[0,9,10,49])
def test053_real_schema_and_nested_evidence_accept50_original_guard_unchanged(tmp_path,monkeypatch,index):
    from egrs.remain053 import validation as v
    from benchmark.remaining_goals.headless.schema import validate_protocol_result as original
    e,i,r=raw_fixture(tmp_path,monkeypatch,index)
    v.validate_protocol_result(r,e,i)
    assert v.validate_evidence(tmp_path,r,e,i)['verified']
    if index>9:
        with pytest.raises(ValueError,match='zero through nine'):original(r,e,i)
    else:original(r,e,i)


@pytest.mark.parametrize('index',[-1,50,True,'10'])
def test053_bad_index_still_rejected(tmp_path,monkeypatch,index):
    from egrs.remain053 import validation as v
    e,i,r=raw_fixture(tmp_path,monkeypatch,10)
    e['initial_state_index']=r['initial_state_index']=index
    with pytest.raises(ValueError):v.validate_protocol_result(r,e,i)


@pytest.mark.parametrize('fault',['actions','model','input_file'])
def test053_no_relaxation_of_actions_model_or_saved_observation(tmp_path,monkeypatch,fault):
    from egrs.remain053 import validation as v
    e,i,r=raw_fixture(tmp_path,monkeypatch,49)
    if fault=='actions':r['queries'][0]['accepted_actions'][0][0]+=1
    elif fault=='model':r['model_identity']['checkpoint']='wrong'
    else:(tmp_path/'evidence/ep/initial.npz').write_bytes(b'corrupted fixture')
    with pytest.raises(ValueError):v.validate_evidence(tmp_path,r,e,i)


def test053_verifier_redirects_both_imports_without_changing_scoring():
    import inspect
    from egrs.remain053 import evaluation
    from egrs.remain049 import evaluation as old
    n=evaluation.engine()
    assert n['run'].__code__ is old.run.__code__
    assert n['execute_episode'].__code__ is old.execute_episode.__code__
    assert n['Live'] is old.Live
    assert 'egrs.remain053.validation' in n['verify_episode'].__code__.co_names
    assert 'benchmark.remaining_goals.headless.offline_scoring' in n['verify_episode'].__code__.co_names
    assert n['verify_episode'].__globals__ is n


@pytest.mark.parametrize('model',['base','h1'])
def test053_fake450_preserves11_and_executes_only439_then_h1_450(tmp_path,monkeypatch,model,capsys):
    from egrs.remain053 import evaluation as new
    from egrs.remain049 import evaluation as old,sources
    from egrs.remain052 import scope
    from benchmark.remaining_goals import isolated_policy
    from test_remain049 import _record
    population=sources.expected();cfg={'source_bank':str(tmp_path/'bank'),'adapter':'fixed-fake-h1'}
    frozen={'model':model,'runtime':{},'expected':population,'sources':[{'episodes':[e]} for e in population],
        'source_bank_sha256':new.BANK_SHA,'plan_sha256':'b'*64,'config':cfg,'adapter_identity':None}
    records={}
    parent_path=tmp_path/'parent';parent_path.mkdir()
    for e in population[:11]:
        p=parent_path/(e['episode_id']+'.json');p.write_text('{}')
        record=_record(e,p,'success' if e['initial_state_index']%2==0 else 'failure')
        record['source']['new_execution']=False;records[e['episode_id']]=record
    monkeypatch.setattr(old,'protect_output',lambda *a,**k:None)
    monkeypatch.setattr(old,'_verify_model',lambda *a:None)
    monkeypatch.setattr(scope,'helpers',lambda:{})
    monkeypatch.setattr(new,'parent',lambda *a:(frozen,records,None,{'format':'fake053','inherited_executed':11}))
    # H1 plan through052 coordinator, no production data or model.
    monkeypatch.setattr(sources,'activate',lambda *a:{})
    from egrs.remain052 import recovery
    monkeypatch.setattr(recovery,'validate_recovery',lambda *a:None)
    sources.write(tmp_path/'bank/sources.json',{'fake':'bank'})
    monkeypatch.setattr(old,'plan',lambda *a:frozen)
    policies=[];executed=[]
    class Policy:
        def __init__(self,cfg):self.provenance={};policies.append(self)
        def close(self):pass
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    def execute(folder,source,*args):
        e=source['episodes'][0];executed.append(e['episode_id']);folder.mkdir(parents=True)
        p=folder/'raw.json';p.write_text('{}')
        return _record(e,p,'success' if e['initial_state_index']%2==0 else 'failure')
    monkeypatch.setattr(old,'execute_episode',execute)
    before={p.name:p.read_bytes() for p in parent_path.iterdir()}
    out=tmp_path/'child'
    report=new.run(cfg,out,model,continue_from=parent_path if model=='base' else None)
    assert len(policies)==1 and len(executed)==(439 if model=='base' else 450)
    assert report['counts']['formal_SR']=={'numerator':225,'denominator':450,'percent':50.0}
    assert report['inherited_completed']==(11 if model=='base' else 0)
    assert report['new_execution_attempts']==len(executed)
    assert before=={p.name:p.read_bytes() for p in parent_path.iterdir()}
    if model=='base':
        assert set(executed).isdisjoint(new.INHERITED)
        assert all(not (out/'episodes'/n).exists() for n in new.INHERITED)
    assert capsys.readouterr().out.count('overall_SR=')==450


def test053_no_base_full_rerun_or_h1_parent_silently_allowed(tmp_path,monkeypatch):
    from egrs.remain053 import evaluation as e
    monkeypatch.setattr(e.original,'protect_output',lambda *a:None)
    with pytest.raises(ValueError,match='explicit parent'):e.run({},tmp_path/'out','base')
    with pytest.raises(ValueError,match='explicit parent'):e.run({},tmp_path/'out','h1',continue_from=tmp_path/'parent')
