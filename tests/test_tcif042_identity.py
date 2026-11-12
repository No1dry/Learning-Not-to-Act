"""CPU-only complete041R0 initialization and independent042 continuation."""
from copy import deepcopy
import json
import random
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from test_retention041_identity import stage_sources, calls
from test_task_control_training import tiny_policy, rows, pairs


@pytest.fixture
def source042(stage_sources, tmp_path, monkeypatch):
    from egrs.retention041 import adapter as previous
    from egrs.tcif042 import adapter
    from egrs.tcif042.contract import contract_for
    policy, _, _, stage041 = stage_sources
    source = tmp_path/'complete041r0'
    initial = previous.save_adapter(policy, source, experiment_arm='r0', update=1000,
        index_identity=previous.INDEX_IDENTITY, stage_identity=stage041('r0'),
        reference_calls=calls(8000,1024),student_calls=calls(22000,2560,24560),
        old10_calls=calls(0,budget=0))
    monkeypatch.setattr(adapter,'INITIALIZATION_SHA256',initial['adapter_sha256'])
    def stage(arm):
        # Only the attention runtime inspection is external to these identity
        # tests. Actual primitive/layout behavior has its own tiny CPU suite.
        policy._tcif042=SimpleNamespace(contract=contract_for(arm),runtime={
            'actual_attention_class':'CPU fake only','torch_version':'fixture'})
        return {'format':'task042-stage-inputs-v1','arm':'c1','experiment_arm':arm,
            'initialization_identity':deepcopy(initial),'index_identity':adapter.INDEX_IDENTITY,
            'ancestor_updates':2000,'additional_updates':1000,'attention_contract':contract_for(arm)}
    return policy, source, stage


def test_complete041r0_source_loads_all_student_tensors_without_old_training_state(source042):
    from egrs.tcif042 import adapter
    from egrs.task_control import adapter as common
    from egrs.task_control.oft import install
    source, directory, stage = source042
    student=tiny_policy();install(student)
    identity=adapter.initialize_from041(student,directory,adapter.INDEX_IDENTITY)
    assert identity==stage('f0')['initialization_identity']
    expected,actual=common._state(source.model),common._state(student.model)
    assert set(expected)==set(actual)
    assert all(torch.equal(expected[n],actual[n]) for n in expected)
    assert {'task_control.W_out.weight','task_control.context.0.weight','task_control.count_head.weight'}<=set(actual)
    assert not list(directory.glob('training_state*'))


@pytest.mark.parametrize('mutation',['r1','not_final','sha','index','ancestor','teacher'])
def test_fixed041r0_source_rejects_other_source_roles(source042,mutation):
    from egrs.tcif042 import adapter
    _,directory,stage=source042
    identity=stage('f0')['initialization_identity']
    if mutation=='r1':identity['experiment_arm']='r1'
    elif mutation=='not_final':identity['update']=750
    elif mutation=='sha':identity['adapter_sha256']='f'*64
    elif mutation=='index':identity['index_identity']='f'*64
    elif mutation=='ancestor':identity['stage_identity']['ancestor_updates']=0
    else:identity['stage_identity']['teacher_identity']=identity['student_identity']
    (directory/'identity.json').write_text(json.dumps(identity))
    with pytest.raises(ValueError):adapter.read_source_identity(directory)


@pytest.mark.parametrize('mutation',['missing','shape','dtype','hash','base'])
def test_full_source_validation_finishes_before_any_live_tensor_copy(source042,mutation):
    from egrs.tcif042 import adapter
    from egrs.task_control import adapter as common
    policy,directory,_=source042
    before={n:p.detach().clone() for n,p in policy.model.named_parameters()}
    identity=adapter.read_source_identity(directory)
    state=torch.load(directory/'adapter.pt',weights_only=True)
    key='task_control.W_out.weight'
    if mutation=='missing':state.pop(key)
    elif mutation=='shape':state[key]=state[key][:1]
    elif mutation=='dtype':state[key]=state[key].double()
    elif mutation=='hash':state[key].fill_(88)
    else:policy.metadata['normalization_statistics_sha256']='d'*64
    if mutation!='base':
        torch.save(state,directory/'adapter.pt')
        digest=common.sha256(directory/'adapter.pt')
        identity['adapter_sha256']=identity['student_identity']['adapter_sha256']=digest
        (directory/'identity.json').write_text(json.dumps(identity))
        adapter.INITIALIZATION_SHA256=digest
    with pytest.raises(ValueError,match='tensor|inventory|lineage'):
        adapter.initialize_from041(policy,directory,adapter.INDEX_IDENTITY)
    assert all(torch.equal(before[n],p) for n,p in policy.model.named_parameters())


@pytest.mark.parametrize('arm',['f0','f1'])
def test042_schema_keeps_full_payload_contract_and_2000_ancestry_old_reader_refuses(source042,tmp_path,arm):
    from egrs.tcif042 import adapter
    from egrs.retention041 import adapter as previous
    from egrs.task_control import adapter as common
    policy,_,stage=source042;directory=tmp_path/arm
    identity=adapter.save_adapter(policy,directory,experiment_arm=arm,update=1,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
        reference_calls=calls(),student_calls=calls(22,budget=24560))
    assert identity['arm']=='c1' and identity['experiment_arm']==arm
    assert identity['ancestor_updates']==2000 and identity['additional_updates']==1
    assert identity['total_ancestral_updates']==2001
    assert identity['attention_contract']==stage(arm)['attention_contract']
    assert not {'teacher_identity','old10_calls'}&set(identity)
    for reader in (previous.read_adapter_identity,common.read_adapter_identity):
        with pytest.raises(ValueError):reader(directory)
    assert adapter.read_adapter_identity(directory)==identity
    fresh=tiny_policy()
    from egrs.task_control.oft import install
    install(fresh);fresh._tcif042=deepcopy(policy._tcif042)
    adapter.restore_adapter_weights(fresh,directory)
    assert all(torch.equal(t,common._state(fresh.model)[n]) for n,t in common._state(policy.model).items())
    with pytest.raises(FileExistsError):
        adapter.save_adapter(policy,directory,experiment_arm=arm,update=1,
            index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
            reference_calls=calls(),student_calls=calls(22,budget=24560))


@pytest.mark.parametrize('mutation',['arm','source','index','ancestor','contract','type'])
def test_stage_rejects_cross_arm_source_index_ancestry_and_execution_changes(source042,mutation):
    from egrs.tcif042 import adapter
    _,_,stage=source042;value=stage('f1')
    if mutation=='arm':value['arm']='c0'
    elif mutation=='source':value['initialization_identity']['adapter_sha256']='f'*64
    elif mutation=='index':value['index_identity']='f'*64
    elif mutation=='ancestor':value['ancestor_updates']=1000
    elif mutation=='type':value['ancestor_updates']=2000.
    else:value['attention_contract']['backend']='changed'
    with pytest.raises(ValueError):adapter.validate_stage_identity(value,'f1',adapter.INDEX_IDENTITY)


def test_invalid_save_does_not_create_old_or_new_root(source042,tmp_path):
    from egrs.tcif042 import adapter
    policy,_,stage=source042;destination=tmp_path/'invalid'
    with pytest.raises(ValueError):adapter.save_adapter(policy,destination,experiment_arm='f1',update=1,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('f1'),
        reference_calls=calls(),student_calls=calls(23,budget=24560))
    assert not destination.exists()


@pytest.mark.parametrize('advanced',[0,1])
def test_resume_restores_all_state_and_two_ledgers_without_refund_or_cross_contract(source042,tmp_path,advanced):
    from egrs.tcif042 import adapter,checkpoint
    from egrs.task_control.reference import ReferenceBudget,StudentBudget
    from egrs.task_control.sampling import TaskControlSampler
    policy,_,stage=source042
    opt=torch.optim.AdamW([p for p in policy.model.parameters() if p.requires_grad],lr=.001)
    scheduler=torch.optim.lr_scheduler.LambdaLR(opt,lambda n:1.)
    sampler=TaskControlSampler(rows(),pairs());sampler.draw_batch()
    sum(p.square().sum() for g in opt.param_groups for p in g['params']).backward();opt.step();scheduler.step()
    budgets=(ReferenceBudget(tmp_path/'ref.json'),StudentBudget(tmp_path/'student.json'))
    for budget,n in zip(budgets,(8,22)):budget.consume('train',n)
    options=dict(config={'updates':1000,'output_dir':str(tmp_path),'photometric_probability':0.0},experiment_arm='f1',
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('f1'),
        reference_budget=budgets[0],student_budget=budgets[1])
    saved={n:p.detach().clone() for n,p in policy.model.named_parameters()}
    checkpoint.save_training_state(tmp_path/'checkpoint',policy,opt,scheduler,sampler,update=1,**options)
    expected=(random.random(),float(np.random.rand()),torch.rand(2));next_batch=sampler.draw_batch()
    with torch.no_grad():
        for p in policy.model.parameters():
            if p.requires_grad:p.add_(2)
    assert checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,scheduler,sampler,**options)==1
    assert random.random()==expected[0] and float(np.random.rand())==expected[1]
    assert torch.equal(torch.rand(2),expected[2]) and sampler.draw_batch()==next_batch
    assert all(torch.equal(saved[n],p) for n,p in policy.model.named_parameters())
    assert opt.state and scheduler.last_epoch==1
    for changed in (dict(options,experiment_arm='f0',stage_identity=stage('f0')),
        dict(options,config={'updates':1000,'changed':True}),dict(options,index_identity='f'*64),
        dict(options,config={**options['config'],'photometric_probability':0}),
        dict(options,stage_identity={**stage('f1'),'attention_contract':{**stage('f1')['attention_contract'],'backend':'wrong'}})):
        with pytest.raises(ValueError):checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,scheduler,sampler,**changed)
    path=tmp_path/'checkpoint/training_state.pt';original=path.read_bytes();path.write_bytes(original+b'bad')
    with pytest.raises(ValueError,match='hash'):checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,scheduler,sampler,**options)
    path.write_bytes(original);budgets[advanced].consume('train')
    with pytest.raises(ValueError,match='older than spent'):checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,scheduler,sampler,**options)


def test_execution_runtime_change_rejects_restore_before_copy(source042,tmp_path):
    from egrs.tcif042 import adapter
    p,_,stage=source042;target=tmp_path/'runtime'
    identity=adapter.save_adapter(p,target,experiment_arm='f1',update=1,index_identity=adapter.INDEX_IDENTITY,
        stage_identity=stage('f1'),reference_calls=calls(),student_calls=calls(22,budget=24560))
    with torch.no_grad():
        for value in p.model.parameters():
            if value.requires_grad:value.add_(3)
    before={n:v.detach().clone() for n,v in p.model.named_parameters()}
    p._tcif042.runtime={**identity['attention_runtime'],'backend':'changed'}
    with pytest.raises(ValueError,match='runtime|backend'):adapter.restore_adapter_weights(p,target)
    assert all(torch.equal(before[n],v) for n,v in p.model.named_parameters())


def test042_reload_cannot_silently_omit_attention_execution(source042,tmp_path):
    from egrs.tcif042 import adapter
    p,_,stage=source042;target=tmp_path/'required-execution'
    adapter.save_adapter(p,target,experiment_arm='f0',update=1,index_identity=adapter.INDEX_IDENTITY,
        stage_identity=stage('f0'),reference_calls=calls(),student_calls=calls(22,budget=24560))
    del p._tcif042
    with pytest.raises(ValueError,match='contract'):adapter.restore_adapter_weights(p,target)


def test_nonfinite_student_cannot_be_saved_as_valid042_adapter(source042,tmp_path):
    from egrs.tcif042 import adapter
    p,_,stage=source042;target=tmp_path/'nonfinite';identity=stage('f1')
    with torch.no_grad():p.model.task_control.W_out.weight.fill_(float('nan'))
    with pytest.raises(ValueError,match='finite|tensor'):adapter.save_adapter(p,target,experiment_arm='f1',update=1,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=identity,
        reference_calls=calls(),student_calls=calls(22,budget=24560))
    assert not target.exists()


def test_invalid_progress_cannot_leave_an_apparently_resumable_checkpoint(source042,tmp_path):
    from egrs.tcif042 import adapter,checkpoint
    from egrs.task_control.reference import ReferenceBudget,StudentBudget
    from egrs.task_control.sampling import TaskControlSampler
    p,_,stage=source042
    opt=torch.optim.AdamW([v for v in p.model.parameters() if v.requires_grad],lr=.001)
    scheduler=torch.optim.lr_scheduler.LambdaLR(opt,lambda step:1.)
    sampler=TaskControlSampler(rows(),pairs())  # deliberately no update drawn
    ref,student=ReferenceBudget(),StudentBudget();ref.consume('train',8);student.consume('train',22)
    target=tmp_path/'bad-progress'
    with pytest.raises(ValueError,match='sequence|update'):
        checkpoint.save_training_state(target,p,opt,scheduler,sampler,update=1,config={'updates':1000},
            experiment_arm='f1',index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('f1'),
            reference_budget=ref,student_budget=student)
    assert not target.exists()


def test_metadata_readers_need_only_standard_library(source042,tmp_path):
    from egrs.tcif042 import adapter
    policy,source,stage=source042;target=tmp_path/'stdlib'
    adapter.save_adapter(policy,target,experiment_arm='f0',update=1,index_identity=adapter.INDEX_IDENTITY,
        stage_identity=stage('f0'),reference_calls=calls(),student_calls=calls(22,budget=24560))
    script='''
import importlib.abc,json,sys
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','transformers'}:raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
from egrs.retention041 import adapter as previous
from egrs.tcif042 import adapter
outer=json.loads((Path(sys.argv[1])/'identity.json').read_text())
source=outer['stage_identity']['initialization_identity']
previous.INITIALIZATION_SHA256=source['stage_identity']['initialization_identity']['adapter_sha256']
adapter.INITIALIZATION_SHA256=source['adapter_sha256']
assert adapter.read_source_identity(sys.argv[2])['experiment_arm']=='r0'
assert adapter.read_adapter_identity(sys.argv[1])['experiment_arm']=='f0'
'''
    result=subprocess.run([sys.executable,'-c',script,str(target),str(source)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
