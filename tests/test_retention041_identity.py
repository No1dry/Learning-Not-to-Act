"""CPU contracts for strict041 stage sources, student adapters and continuation."""
from copy import deepcopy
import json
import random
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import torch

from test_task_control_training import tiny_policy, rows, pairs


@pytest.fixture
def stage_sources(tmp_path, monkeypatch):
    from egrs.retention041 import adapter
    from egrs.task_control import adapter as old
    from egrs.task_control.oft import install
    policy = tiny_policy(); install(policy)
    with torch.no_grad():
        for name, parameter in policy.model.named_parameters():
            if name.startswith('task_control.') or name.endswith(('.lora_A', '.lora_B')):
                parameter.fill_(.03)
    source = tmp_path / 'initial'
    initial = old.save_adapter(policy, source, arm='c1', update=1000,
        index_identity=adapter.INDEX_IDENTITY,
        reference_calls={'train':8000,'dev':1024,'total':9024,'budget':9024})
    monkeypatch.setattr(adapter, 'INITIALIZATION_SHA256', initial['adapter_sha256'])
    teacher_path = tmp_path / 'teacher'
    teacher = old.save_adapter(policy, teacher_path, arm='c1', update=1000,
        index_identity=adapter.TEACHER_INDEX_IDENTITY,
        reference_calls={'train':8000,'dev':1024,'total':9024,'budget':9024})
    monkeypatch.setattr(adapter, 'TEACHER_SHA256', teacher['adapter_sha256'])
    def stage(arm):
        return {'format':'task041-stage-inputs-v1','experiment_arm':arm,
            'initialization_identity':deepcopy(initial),
            'teacher_identity':deepcopy(teacher) if arm == 'r1' else None,
            'index_identity':adapter.INDEX_IDENTITY,
            'ancestor_updates':1000,'additional_updates':1000}
    return policy, source, teacher_path, stage


def calls(train=8, dev=0, budget=9024):
    return {'train':train,'dev':dev,'total':train+dev,'budget':budget}


def test_full040_initialization_and039_source_validation_do_not_mix_students(stage_sources):
    from egrs.retention041 import adapter
    from egrs.task_control.oft import install
    source, directory, teacher, stage = stage_sources
    student = tiny_policy(); install(student)
    identity = adapter.initialize_from040(student, directory, adapter.INDEX_IDENTITY)
    assert identity == stage('r0')['initialization_identity']
    expected = adapter.load_source_state(source, directory, identity)
    assert all(torch.equal(dict(student.model.named_parameters())[n], t) for n, t in expected.items())
    before = {n:p.detach().clone() for n,p in student.model.named_parameters()}
    tid = adapter.read_source_identity(teacher, 'teacher')
    teacher_state = adapter.load_source_state(student, teacher, tid)
    assert set(teacher_state) == set(expected)
    assert all(torch.equal(before[n], p) for n,p in student.model.named_parameters())
    with pytest.raises(ValueError, match='SHA|hash|index'):
        adapter.read_source_identity(directory, 'teacher')
    with pytest.raises(ValueError, match='index'):
        adapter.read_source_identity(directory, 'initialization', index_identity='f'*64)


@pytest.mark.parametrize('mutation', ['missing','shape','dtype','hash','base'])
def test_source_tensor_or_lineage_rejection_precedes_any_live_copy(stage_sources, mutation):
    from egrs.retention041 import adapter
    from egrs.task_control import adapter as old
    policy, directory, _, stage = stage_sources
    identity = stage('r0')['initialization_identity']
    before = {n:p.detach().clone() for n,p in policy.model.named_parameters()}
    state = torch.load(directory/'adapter.pt', weights_only=True)
    key = 'task_control.W_out.weight'
    if mutation == 'missing': state.pop(key)
    elif mutation == 'shape': state[key] = state[key][:1]
    elif mutation == 'dtype': state[key] = state[key].double()
    elif mutation == 'hash': state[key].fill_(99)
    else:
        identity['base_lineage']['normalization_statistics_sha256'] = 'd'*64
    if mutation != 'base':
        torch.save(state, directory/'adapter.pt')
        identity['adapter_sha256'] = old.sha256(directory/'adapter.pt')
    with pytest.raises(ValueError, match='tensor|inventory|lineage'):
        adapter.load_source_state(policy, directory, identity)
    assert all(torch.equal(before[n], p) for n,p in policy.model.named_parameters())


@pytest.mark.parametrize('arm', ['r0','r1'])
def test041_outer_schema_reloads_complete_student_and_old_reader_refuses(stage_sources,tmp_path,arm):
    from egrs.retention041 import adapter
    from egrs.task_control import adapter as old
    policy, _, _, stage = stage_sources
    destination = tmp_path/arm
    identity = adapter.save_adapter(policy,destination,experiment_arm=arm,update=1,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage(arm),
        reference_calls=calls(),student_calls=calls(22,budget=24560),
        old10_calls=calls(3 if arm=='r1' else 0,budget=4000 if arm=='r1' else 0))
    assert identity['arm']=='c1' and identity['experiment_arm']==arm
    assert identity['stage_identity']['ancestor_updates']==1000
    with pytest.raises(ValueError,match='recipe|identity'):
        old.read_adapter_identity(destination)
    assert adapter.read_adapter_identity(destination)==identity
    fresh = tiny_policy()
    adapter.attach_trained_adapter(fresh,destination,experiment_arm=arm)
    expected=old._state(policy.model);actual=old._state(fresh.model)
    assert set(expected)==set(actual) and all(torch.equal(expected[n],actual[n]) for n in expected)
    assert not any(p.requires_grad for p in fresh.model.parameters())


@pytest.mark.parametrize('advanced_budget',[0,1,2])
def test_resume_restores_three_budgets_rng_optimizer_sampler_and_refuses_cross_stage(stage_sources,tmp_path,advanced_budget):
    from egrs.retention041 import adapter, checkpoint
    from egrs.task_control.reference import ReferenceBudget,StudentBudget,ObservationBudget
    from egrs.task_control.sampling import TaskControlSampler
    class OldBudget(ObservationBudget):
        LIMITS={'train':4000,'dev':0}
    policy,_,_,stage=stage_sources
    opt=torch.optim.AdamW([p for p in policy.model.parameters() if p.requires_grad],lr=.001)
    sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda n:1.)
    sampler=TaskControlSampler(rows(),pairs());sampler.draw_batch()
    sum(p.square().sum() for g in opt.param_groups for p in g['params']).backward();opt.step();sched.step()
    budgets=(ReferenceBudget(tmp_path/'ref.json'),StudentBudget(tmp_path/'student.json'),OldBudget(tmp_path/'old.json'))
    for budget,n in zip(budgets,(8,22,3)):budget.consume('train',n)
    options=dict(config={'updates':1000},experiment_arm='r1',index_identity=adapter.INDEX_IDENTITY,
        stage_identity=stage('r1'),reference_budget=budgets[0],student_budget=budgets[1],old10_budget=budgets[2])
    saved={n:p.detach().clone() for n,p in policy.model.named_parameters()}
    checkpoint.save_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,update=1,**options)
    expected_rng=(random.random(),float(np.random.rand()),torch.rand(2))
    next_batch=sampler.draw_batch()
    with torch.no_grad():
        for p in policy.model.parameters():
            if p.requires_grad:p.add_(2)
    assert checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,**options)==1
    assert random.random()==expected_rng[0] and float(np.random.rand())==expected_rng[1]
    assert torch.equal(torch.rand(2),expected_rng[2]) and sampler.draw_batch()==next_batch
    assert all(torch.equal(saved[n],p) for n,p in policy.model.named_parameters())
    assert opt.state and sched.last_epoch==1
    with pytest.raises(ValueError,match='arm|stage'):
        checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,
            **dict(options,experiment_arm='r0',stage_identity=stage('r0')))
    for changed in (
        dict(options,config={'updates':1000,'changed':True}),
        dict(options,index_identity='f'*64),
        dict(options,stage_identity={**stage('r1'),'teacher_identity':stage('r0')['initialization_identity']}),
        dict(options,stage_identity={**stage('r1'),'initialization_identity':{
            **stage('r1')['initialization_identity'],'tensor_sha256':{
                **stage('r1')['initialization_identity']['tensor_sha256'],'task_control.W_out.weight':'e'*64}}}),
    ):
        with pytest.raises(ValueError,match='configuration|stage|index|source'):
            checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,**changed)
    state_path=tmp_path/'checkpoint/training_state.pt';original_bytes=state_path.read_bytes()
    state_path.write_bytes(original_bytes+b'bad')
    with pytest.raises(ValueError,match='hash'):
        checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,**options)
    state_path.write_bytes(original_bytes)
    budgets[advanced_budget].consume('train')
    with pytest.raises(ValueError,match='older than spent'):
        checkpoint.load_training_state(tmp_path/'checkpoint',policy,opt,sched,sampler,**options)


def test_invalid041_calls_cannot_leave_an_old038_root_adapter(stage_sources,tmp_path):
    from egrs.retention041 import adapter
    policy,_,_,stage=stage_sources
    destination=tmp_path/'bad-new-stage'
    with pytest.raises(ValueError,match='budget'):
        adapter.save_adapter(policy,destination,experiment_arm='r1',update=1,
            index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('r1'),
            reference_calls=calls(),student_calls=calls(23,budget=24560),old10_calls=calls(1,budget=4000))
    assert not (destination/'identity.json').exists()


@pytest.mark.parametrize('change',[{'arm':'c0'},{'update':750},{'index_identity':'e'*64},
    {'adapter_sha256':'f'*64}])
def test_fixed_source_roles_reject_changed_metadata(stage_sources,change):
    from egrs.retention041 import adapter
    _,directory,_,_=stage_sources
    path=directory/'identity.json';identity=json.loads(path.read_text())
    identity.update(change);path.write_text(json.dumps(identity))
    with pytest.raises(ValueError):adapter.read_source_identity(directory,'initialization')


def test_new041_and_source_metadata_readers_need_only_stdlib(stage_sources,tmp_path):
    from egrs.retention041 import adapter
    policy,directory,_,stage=stage_sources
    destination=tmp_path/'stdlib'
    adapter.save_adapter(policy,destination,experiment_arm='r1',update=1,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage('r1'),
        reference_calls=calls(),student_calls=calls(22,budget=24560),old10_calls=calls(0,budget=4000))
    script='''
import importlib.abc,json,sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','transformers'}:raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
from egrs.retention041 import adapter
from pathlib import Path
outer=json.loads((Path(sys.argv[1])/'identity.json').read_text())
adapter.INITIALIZATION_SHA256=outer['stage_identity']['initialization_identity']['adapter_sha256']
adapter.TEACHER_SHA256=outer['stage_identity']['teacher_identity']['adapter_sha256']
assert adapter.read_source_identity(sys.argv[2],'initialization')['arm']=='c1'
assert adapter.read_adapter_identity(sys.argv[1])['experiment_arm']=='r1'
'''
    result=subprocess.run([sys.executable,'-c',script,str(destination),str(directory)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
