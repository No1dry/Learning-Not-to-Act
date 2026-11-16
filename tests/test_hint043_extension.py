"""Targeted CPU-only continuation and explicit2000/3000 checkpoint tests."""
from copy import deepcopy
import json
from pathlib import Path
import random
import shutil
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from egrs.hint043 import contracts as c
from test_hint043 import fake_policy,fake_prediction,items20
from test_trajectory_evaluation import core,ready_config
from test_retention_evaluation import config036


class Dataset:
    identity=c.INDEX_IDENTITY
    def __init__(self,split):
        self.rows=[dict(source_id=f'{split}/{pool}/{i}',observation_index=i,split=split,pool=pool,
            task_key='basket',source_group=split+'/parent',variant=0,prefix=i==0,action_mask=[True]*8)
            for pool in ('ten','fresh','raw') for i in (0,1)]
    def __getitem__(self,index):return items20()[0][0]
    def validate_normalization(self,*args):pass


@pytest.fixture(scope='module')
def parent(tmp_path_factory):
    from egrs.hint043 import training
    root=tmp_path_factory.mktemp('hint-original1000')
    train,dev=Dataset('train'),Dataset('dev')
    side=SimpleNamespace(manifest={'identity':'f'*64},for_row=lambda r:{'hint_eligible':r['pool']=='ten','text':'two current relations'})
    cfg={'arm':'h1','training_recipe':deepcopy(c.RECIPE)}
    model=fake_policy();original=deepcopy(model)
    training.run_loaded(cfg,root/'parent',train,dev,side,model,predict=fake_prediction)
    return SimpleNamespace(root=root/'parent',checkpoint=root/'parent/update-001000',initial=original,
                           train=train,dev=dev,side=side,config=cfg)


@pytest.mark.parametrize('steps',[1000,2000,3000,5000])
def test_parameterized_horizon_budgets_keep_loss_and_warmup_unchanged(steps):
    r=c.training_recipe(steps)
    assert r['reference_budget']==9024*(steps//1000)
    assert r['model_forward_budget']==27072*(steps//1000)
    changed={'updates','reference_budget','model_forward_budget','checkpoint_selection'}
    assert {k:v for k,v in r.items() if k not in changed}=={k:v for k,v in c.RECIPE.items() if k not in changed}
    assert c.transfer_weight(steps,target_updates=steps)==.1
    assert c.transfer_weight(1001,target_updates=3000)==.1
    with pytest.raises(ValueError):c.transfer_weight(1001)


@pytest.mark.parametrize('steps',[True,999,1001,0,-1000])
def test_invalid_target_refused(steps):
    with pytest.raises(ValueError):c.training_recipe(steps)


def test_restore_keeps_optimizer_scheduler_sampler_rng_and_ancestor_spend(parent,tmp_path):
    from egrs.hint043 import adapter,checkpoint
    from egrs.hint043.budget import ModelBudget,ReferenceBudget
    from egrs.retention.training import ThreePoolSampler
    source=torch.load(parent.checkpoint/'training_state.pt',weights_only=False)
    cfg=deepcopy(source['config']);cfg.update(output_dir=str(tmp_path/'child'),training_recipe=c.training_recipe(3000),
                                            continuation_parent=checkpoint.parent_binding(parent.checkpoint))
    model=deepcopy(parent.initial);adapter.install(model)
    optim=torch.optim.AdamW([p for p in model.model.parameters() if p.requires_grad],lr=2e-5)
    sched=torch.optim.lr_scheduler.LambdaLR(optim,lambda n:min(1.,(n+1)/50))
    sampler=ThreePoolSampler(parent.train.rows,seed=7);ref=ReferenceBudget(target_updates=3000);budget=ModelBudget(target_updates=3000)
    assert checkpoint.extend_from(parent.checkpoint,model,optim,sched,sampler,config=cfg,
        sidecar_identity='f'*64,reference_budget=ref,model_budget=budget)==1000
    assert sched.state_dict()==source['scheduler'] and optim.param_groups[0]['lr']==2e-5
    assert all(int(state['step'])==1000 for state in optim.state.values())
    assert sampler.state_dict()==source['sampler']
    assert torch.equal(torch.get_rng_state(),source['torch_rng'])
    assert random.getstate()==source['python_rng']
    assert np.array_equal(np.random.get_state()[1],source['numpy_rng'][1])
    assert ref.report()['total']==source['reference_budget']['total'] and ref.report()['budget']==27072
    assert budget.report()['total']==source['model_budget']['total'] and budget.report()['budget']==81216
    for name,t in adapter.state(model).items():
        old=torch.load(parent.checkpoint/'adapter.pt',weights_only=True)
        assert torch.equal(t,old[name])
    cfg['continuation_parent']['arm']='h0'
    with pytest.raises(ValueError,match='parent/arm'):
        checkpoint.extend_from(parent.checkpoint,model,optim,sched,sampler,config=cfg,
            sidecar_identity='f'*64,reference_budget=ref,model_budget=budget)


def test_full_fake_extension_to3000_keeps_parent_and_explicit_milestones(parent,tmp_path):
    from egrs.hint043 import adapter,checkpoint,training
    from egrs.hint043.budget import ModelBudget,ReferenceBudget
    from egrs.retention.training import ThreePoolSampler
    before={str(p.relative_to(parent.root)):c.sha(p) for p in parent.root.rglob('*') if p.is_file()}
    cfg=dict(parent.config,training_recipe=c.training_recipe(3000))
    output=tmp_path/'child'
    report=training.run_loaded(cfg,output,parent.train,parent.dev,parent.side,deepcopy(parent.initial),
                              init_from=parent.checkpoint,predict=fake_prediction)
    assert report['update']==3000 and report['ancestor_updates']==1000
    rows=[json.loads(x) for x in (output/'metrics.jsonl').read_text().splitlines()]
    assert [x['update'] for x in rows]==list(range(1001,3001))
    assert rows[0]['sampling']['pool_draw_counts']=={'ten':12012,'fresh':4004,'raw':4004}
    assert rows[0]['transfer_weight']==rows[-1]['transfer_weight']==.1
    assert rows[-1]['additional_updates']==2000 and rows[-1]['additional_completion_percent']==100.
    milestones=c.read_json(output/'evaluation_checkpoints.json')['checkpoints']
    assert milestones=={'2000':'update-002000','3000':'update-003000'}
    for step in (2000,3000):
        v=adapter.read_adapter_identity(output/f'update-{step:06d}')
        assert v['update']==step and v['final_update']==3000 and v['schema_version']==c.EXTENDED_ADAPTER_FORMAT
        assert v['reference_calls']['train']==8*step and v['model_calls']['main_train']==20*step
        q=deepcopy(parent.initial);adapter.attach(q,output/f'update-{step:06d}','h1',checkpoint_step=step)
        with pytest.raises(ValueError):adapter.attach(deepcopy(parent.initial),output/f'update-{step:06d}','h1')
    assert before=={str(p.relative_to(parent.root)):c.sha(p) for p in parent.root.rglob('*') if p.is_file()}
    # Same-run full recovery is legal; already-spent later forwards cannot be refunded.
    saved=c.read_json(output/'run_config.json');q=deepcopy(parent.initial);adapter.install(q)
    opt=torch.optim.AdamW([p for p in q.model.parameters() if p.requires_grad],lr=2e-5)
    sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda n:min(1.,(n+1)/50))
    sampler=ThreePoolSampler(parent.train.rows,seed=7)
    assert checkpoint.load(output/'update-002000',q,opt,sched,sampler,config=saved,sidecar_identity='f'*64,
        reference_budget=ReferenceBudget(target_updates=3000),model_budget=ModelBudget(target_updates=3000))==2000
    assert sched.last_epoch==2000 and sampler.state_dict()['counts']=={'ten':24000,'fresh':8000,'raw':8000}
    with pytest.raises(ValueError,match='older than spent'):
        checkpoint.load(output/'update-002000',q,opt,sched,sampler,config=saved,sidecar_identity='f'*64,
            reference_budget=ReferenceBudget(output/'reference_budget.json',target_updates=3000),
            model_budget=ModelBudget(output/'model_budget.json',target_updates=3000))


def test_spend_after_parent_checkpoint_blocks_continuation_without_refund(parent,tmp_path):
    from egrs.hint043.checkpoint import parent_binding
    root=tmp_path/'changed-parent';shutil.copytree(parent.root,root)
    budget=c.read_json(root/'reference_budget.json');budget['dev']+=1;budget['total']+=1
    c.write_json(root/'reference_budget.json',budget)
    with pytest.raises(ValueError,match='spend beyond'):parent_binding(root/'update-001000')


@pytest.mark.parametrize('step',[2000,3000])
def test_explicit_checkpoint_evaluation_uses_same_original180_and_no_hint(config036,tmp_path,step):
    from egrs.hint043 import adapter,evaluation
    p=fake_policy();adapter.install(p)
    parent={'update':1000,'arm':'h1',**{k:'a'*64 for k in ('adapter_sha256','training_state_sha256','identity_sha256','run_config_sha256')}}
    folder=tmp_path/f'step-{step}'
    v=adapter.save_adapter(p,folder,arm='h1',update=step,sidecar_identity='f'*64,
        reference_calls={'train':8*step,'dev':0,'total':8*step,'budget':27072},
        model_calls={'main_train':20*step,'aux_train':0,'main_dev':0,'aux_dev':0,'total':20*step,'budget':81216},
        target_updates=3000,continuation_parent=parent)
    cfg=json.loads(config036.read_text());cfg.update(schema_version=evaluation.SCHEMA,group=evaluation.GROUP,arm='h1',adapter=str(folder))
    path=tmp_path/'eval.json';path.write_text(json.dumps(cfg))
    plan=evaluation.build_plan(path,'h1',checkpoint_step=step)
    assert plan['checkpoint_step']==step and plan['deployment_hint'] is False
    assert plan['budget']['total']==180 and sum(len(t['source']['episodes']) for t in plan['tasks'])==180
    assert evaluation.spec('h1',step).worker_extra(plan)=={'hint043_arm':'h1','hint043_checkpoint_step':step}
    with pytest.raises(ValueError):evaluation.build_plan(path,'h1')
    report=evaluation.make_report({'10':{},'00':{}},v,checkpoint_step=step)
    assert report['ancestor_updates']==1000 and report['additional_updates']==step-1000 and report['total_ancestral_updates']==step


def test_cli_forwards_explicit_continuation_and_eval_step(monkeypatch):
    from egrs.hint043.__main__ import main
    from egrs.hint043 import training,evaluation
    calls=[]
    monkeypatch.setattr(training,'run',lambda *a,**kw:calls.append((a,kw)) or {'complete':True})
    main(['train','--config','cfg','--output','child','--init-from','parent','--target-updates','3000'])
    assert calls[-1][1]=={'resume':None,'init_from':'parent','target_updates':3000}
    monkeypatch.setattr(evaluation,'run',lambda *a,**kw:calls.append((a,kw)) or {
        'schema_version':'fake','arm':'h1','formal_complete':True,'conditions':{'10':{'formal_SR':None},'00':{'formal_SR':None}}})
    main(['evaluate','--config','cfg','--output','new','--arm','h1','--checkpoint-step','2000'])
    assert calls[-1][1]=={'arm':'h1','checkpoint_step':2000}


@pytest.mark.parametrize('step',[2000,3000])
def test_deployed_policy_forwards_step_only_to_adapter_not_native_or_sensors(monkeypatch,step):
    import sys
    from types import ModuleType
    from egrs.hint043 import adapter,policy
    received=[]
    base=SimpleNamespace(metadata={},reset=lambda:None,close=lambda:None,
        predict=lambda obs,text:received.append((obs,text)) or 'actions')
    native=ModuleType('benchmark.remaining_goals.adapters.openvla_oft')
    def construct(config):
        assert config=={'policy_factory':'original:factory'}
        return base
    native.OpenVLAOFTPolicy=construct
    transfer=ModuleType('benchmark.remaining_goals.adapters.oft_transfer');transfer.FACTORY='original:factory'
    monkeypatch.setitem(sys.modules,native.__name__,native);monkeypatch.setitem(sys.modules,transfer.__name__,transfer)
    def attach(p,path,arm,*,checkpoint_step):
        assert checkpoint_step==step and arm=='h1' and path=='fixed-checkpoint'
        return {'update':step,'arm':arm}
    monkeypatch.setattr(adapter,'attach',attach)
    wrapped=policy.make_policy({'method_adapter':'fixed-checkpoint','hint043_arm':'h1','hint043_checkpoint_step':step})
    assert wrapped.predict({'images':['a','b'],'proprio':[0]*8,'goals':[True,False]},'original')=='actions'
    assert received==[({'images':['a','b'],'proprio':[0]*8},'original')]
    assert wrapped.metadata['hint043_checkpoint_step']==step and wrapped.metadata['deployment_hint'] is False


@pytest.mark.parametrize('kind',['train','eval'])
def test_real_shell_templates_only_launch_requested_two_train_or_four_eval(tmp_path,kind):
    import os,subprocess,sys
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'launches').mkdir();(tmp_path/'config').mkdir();binary=tmp_path/'bin';binary.mkdir()
    for arm in ('h0','h1'):
        parent=tmp_path/f'runs/task043-{arm}-train-001/update-001000';parent.mkdir(parents=True)
        (parent/'training_state.pt').write_bytes(b'fake')
        if kind=='eval':
            for step in (2000,3000):
                p=tmp_path/f'runs/task045-{arm}-train-001/update-{step:06d}';p.mkdir(parents=True)
                (p/'identity.json').write_text('{}')
    fake=binary/'python'
    fake.write_text('#!'+sys.executable+'\n'+'''import sys,os,json
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['CAPTURE'],'a') as f:f.write(json.dumps(args)+'\\n')
out=Path(args[args.index('--output')+1]);out.mkdir(parents=True)
if 'train' in args:
 for step in (2000,3000):
  p=out/f'update-{step:06d}';p.mkdir();(p/'identity.json').write_text('{}')
else:(out/'summary.json').write_text('{}')
''');fake.chmod(0o755)
    capture=tmp_path/'calls.jsonl'
    env=dict(os.environ,LNA045_ROOT=str(tmp_path),LNA045_CODE=str(root),LNA045_CONFIG=str(tmp_path/'config'),
             CAPTURE=str(capture),PATH=str(binary)+os.pathsep+os.environ['PATH'])
    script=root/'configs/hint043'/('extend_train_both.sh' if kind=='train' else 'eval_training_length.sh')
    result=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    calls=[json.loads(x) for x in capture.read_text().splitlines()]
    assert len(calls)==(2 if kind=='train' else 4)
    if kind=='train':
        assert all(x[x.index('--target-updates')+1]=='3000' and 'task043-' in x[x.index('--init-from')+1] for x in calls)
    else:assert [x[x.index('--checkpoint-step')+1] for x in calls]==['2000','2000','3000','3000']
    again=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True)
    assert again.returncode!=0 and len(capture.read_text().splitlines())==len(calls)
