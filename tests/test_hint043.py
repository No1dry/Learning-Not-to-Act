"""Synthetic CPU contracts only; no pretrained policy, real trajectory, or env."""
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from egrs.hint043 import contracts as c


@pytest.mark.parametrize('task', list(c.RELATIONS)+['two_pots'])
@pytest.mark.parametrize('values', [[True,False],[False,True],[False,False],[True,True]])
def test_nine_current_fact_templates_no_hidden_ids_or_action_commands(task,values):
    text=c.status_text(task,values)
    assert text and not any(x in text for x in ('_1','_2','mask','source_id','only pick','ignore'))
    if task=='two_pots':
        assert text==c.status_text(task,list(reversed(values)))
    else:
        assert text.count('currently')==2


@pytest.mark.parametrize('values',[None,[True,None],[True,1],[False],['true',False]])
def test_missing_facts_never_become_negative(values):
    assert c.status_text('basket',values) is None


def test_prompt_and_sensor_whitelist_and_fixed_transfer_schedule():
    assert c.prompt('Move Cup')=='In: What action should the robot take to move cup?\nOut:'
    assert 'Current task-goal facts:' in c.prompt('Move Cup','relation currently satisfied.')
    assert c.sensors(dict(images=[],proprio=[],instruction='full',hint='GT',future='GT'))==dict(images=[],proprio=[],instruction='full')
    assert [c.transfer_weight(i) for i in (1,100,150,200,1000)]==[0.,0.,.05,.1,.1]
    with pytest.raises(ValueError): c.transfer_weight(1001)


@pytest.mark.parametrize('change',[{'updates':1001},{'photometric_probability':0},{'auxiliary_max':5},{'seed':8}])
def test_strict_actual_config_does_not_accept_type_or_budget_drift(tmp_path,change):
    cfg=dict(format=c.CONFIG_FORMAT,arm='h1',index_dir='index',sidecar_dir='sidecar',benchmark_root='core',runtime='runtime.json',training_recipe=deepcopy(c.RECIPE))
    path=tmp_path/'training.json';c.write_json(path,cfg)
    assert c.load_config(path)['arm']=='h1'
    cfg['training_recipe'].update(change);c.write_json(path,cfg)
    with pytest.raises(ValueError): c.load_config(path)


def metadata_fixture(tmp_path,monkeypatch,values=None):
    from egrs.hint043 import prepare as p
    from egrs.augmentation.data import load_scope
    source_root=tmp_path/'recorded';source_root.mkdir()
    root=tmp_path/'index';root.mkdir();ret_dir=tmp_path/'retention';ret_dir.mkdir()
    scope=deepcopy(next(t for t in load_scope()['tasks'] if t['key']=='basket'))
    parent=dict(source_id='parent',source_group='group',split='train',task_key='basket',instruction='put both objects in the basket',file_sha256='a'*64)
    full=dict(parent,active_goals=scope['active_goals'],invariant_predicates=[],extra_historical_metadata=True)
    frames=[{'facts':{'goals':v}} for v in (values if values is not None else [[False,False],[True,False],[True,True]])]
    c.write_json(source_root/'audit.json',{'frames':frames})
    c.write_json(source_root/'lineage.json',{'source':full})
    original={'audit_path':'audit.json','lineage_path':'lineage.json','length':2}
    source=dict(parent,source_id='ten|s',pool='ten',parent_demo_id='parent',root_key='generated',observation_count=3,original_source=original)
    raw=dict(parent,source_id='raw|s',pool='raw',parent_demo_id='parent',root_key='raw',observation_count=1)
    rows=[dict(source_id=source['source_id'],observation_index=i,split='train',pool='ten',task_key='basket',source_group='group',instruction=source['instruction']) for i in (0,1)]
    rows+=[dict(rows[0],source_id='raw|s',pool='raw')]
    (ret_dir/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    inputs={str((source_root/n).resolve()):c.sha(source_root/n) for n in ('audit.json','lineage.json')}
    ret={'data_roots':{'generated':str(source_root),'raw':str(tmp_path/'does-not-exist')},'parents':{'parent':parent},
        'sources':{'ten|s':source,'raw|s':raw},'inputs':inputs}
    ret['identity']=c.identity(ret);c.write_json(ret_dir/'sources.json',ret)
    rr={'sources_identity':ret['identity'],'rows':len(rows),'rows_sha256':c.sha(ret_dir/'rows.jsonl')}
    rr['identity']=c.identity(rr);c.write_json(ret_dir/'report.json',rr)
    control={'format':'task040-task-control-sources-v1','retention_index':str(ret_dir),
        'retention_identity':ret['identity'],'inputs':inputs}
    control['identity']=c.identity(control)
    report={'sources_identity':control['identity']};report['identity']=c.identity(report)
    c.write_json(root/'sources.json',control);c.write_json(root/'report.json',report)
    c.write_json(root/'identity.json',{'sources_identity':control['identity'],'report_identity':report['identity']})
    monkeypatch.setattr(p,'INDEX_IDENTITY',control['identity']);monkeypatch.setattr(p,'MAX_KEYS',len(rows))
    return root,source_root


def test_prepare_current_frame_legacy_parent_subset_no_hdf_and_once_only(tmp_path,monkeypatch):
    from egrs.hint043.prepare import build_sidecar,Sidecar
    root,src=metadata_fixture(tmp_path,monkeypatch)
    out=tmp_path/'status'
    report=build_sidecar(root,out,progress=lambda _:None)
    data=c.lines(out/'status.jsonl')
    assert data[0]['goals']==[False,False] and data[1]['goals']==[True,False]
    assert not data[2]['hint_eligible'] and data[2]['goals'] is None
    assert report['training_ready'] and not report['image_pixels_read'] and not report['simulation_created']
    side=Sidecar(out,root);assert len(side.records)==3
    with pytest.raises(ValueError,match='already'): build_sidecar(root,out)
    # No HDF file or image exists in this synthetic fixture.
    assert not list(src.glob('*.hdf5'))


def test_no_eligible_hints_reported_not_silently_training_h1(tmp_path,monkeypatch):
    from egrs.hint043.prepare import build_sidecar,Sidecar
    root,_=metadata_fixture(tmp_path,monkeypatch,[[None,False]]*3)
    out=tmp_path/'status';report=build_sidecar(root,out,progress=lambda _:None)
    assert not report['training_ready']
    with pytest.raises(ValueError,match='Zero eligible'):Sidecar(out,root)


def test_json_change_is_rejected_and_partial_output_preserved(tmp_path,monkeypatch):
    from egrs.hint043.prepare import build_sidecar
    root,src=metadata_fixture(tmp_path,monkeypatch)
    (src/'audit.json').write_text('{}')
    out=tmp_path/'failed'
    with pytest.raises(ValueError,match='changed'):build_sidecar(root,out)
    assert (out/'production_started.json').exists() and (out/'preparation_error.json').exists()


def test_active_predicate_mapping_is_not_official_array_order():
    from egrs.task_control.index import _active_values
    semantics={'active_goal_indices':[[1],[0]],'official_goal_predicates':['closed','inside']}
    assert _active_values({'official_goal_values':[False,True],'goals':[True,False]},semantics)==[True,False]
    assert _active_values({'official_goal_values':[False,True],'goals':[False,True]},semantics) is None


def fake_policy():
    from test_augmentation_training import policy
    from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
    p=policy();p.metadata['dataset_statistics_sha256']=RETENTION_STATS_SHA
    p.cfg=SimpleNamespace(unnorm_key='libero_10_no_noops')
    p.model.norm_stats={'libero_10_no_noops':{}}
    p.model.language_model.config=SimpleNamespace(use_cache=True)
    p.model.language_model.gradient_checkpointing_enable=lambda **kwargs:None
    p.close=lambda:None
    return p


def fake_prediction(p,item,hint=None):
    assert set(item)==c.SENSOR_FIELDS
    value=torch.full((1,56,3),1. if hint is None else 1.5)
    return p.action_head(p.model(value)).reshape(1,8,7)


def items20():
    item={'images':[0,1],'proprio':[0.]*8,'instruction':'full original',
          'actions':np.zeros((8,7),dtype=np.float32),'action_mask':[True]*8}
    return [deepcopy(item) for _ in range(20)],['ten']*12+['fresh']*4+['raw']*4


@pytest.mark.parametrize('arm',['h0','h1'])
def test_two_views_real_cpu_backward_reference_order_and_forward_counts(arm):
    from egrs.hint043 import adapter,training
    from egrs.hint043.budget import ModelBudget
    from egrs.retention.reference import ReferenceBudget
    from egrs.augmentation.oft import LoRALinear
    p=fake_policy();adapter.install(p);items,pools=items20();events=[]
    def predict(policy,item,hint=None):
        is_reference=not next(m for m in p.model.modules() if isinstance(m,LoRALinear)).enabled
        events.append(('ref' if is_reference else 'model',hint,torch.is_grad_enabled()))
        return fake_prediction(policy,item,hint)
    ref=ReferenceBudget();model=ModelBudget()
    loss=training.train_update(p,items,pools,{i:'status current facts' for i in range(4)},list(range(4)),
        update=201,arm=arm,reference_budget=ref,model_budget=model,predict=predict)
    assert [e[0] for e in events[:8]]==['ref']*8 and all(not e[2] for e in events[:8])
    assert len(events)==32 and ref.report()['total']==8
    assert model.report()['main_train']==20 and model.report()['aux_train']==4
    assert sum(e[1] is not None for e in events)==(4 if arm=='h1' else 0)
    assert all(v.grad is None for v in p.action_head.parameters())
    assert any(v.grad is not None and v.grad.abs().sum()>0 for n,v in p.model.named_parameters() if n.endswith('.lora_B'))
    if arm=='h0': assert loss['transfer_l1']==0.


def test_no_auxiliary_is_not_resampled_and_reference_preserves_rng():
    from egrs.hint043 import adapter,training
    from egrs.hint043.budget import ModelBudget
    from egrs.retention.reference import ReferenceBudget
    p=fake_policy();adapter.install(p);items,pools=items20();ref=ReferenceBudget();budget=ModelBudget()
    random.seed(5);np.random.seed(5);torch.manual_seed(5)
    expected=(random.random(),np.random.rand(),torch.rand(1))
    random.seed(5);np.random.seed(5);torch.manual_seed(5)
    def predictor(p,item):
        random.random();np.random.rand();torch.rand(1)
        return fake_prediction(p,item)
    training.reference(p,items[0],ref,'train',predictor)
    got=(random.random(),np.random.rand(),torch.rand(1))
    assert got[:2]==expected[:2] and torch.equal(got[2],expected[2])
    result=training.train_update(p,items,pools,{},[],update=1,arm='h1',reference_budget=ref,model_budget=budget,predict=fake_prediction)
    assert result['auxiliary_draws']==0 and budget.report()['total']==20


def test_auxiliary_selection_is_original_draw_slots_not_unique_or_new_samples():
    from egrs.hint043.training import aux_slots
    rows=[{'pool':'ten','hint_eligible':True},{'pool':'raw','hint_eligible':False}]
    side=SimpleNamespace(for_row=lambda row:row)
    assert aux_slots(rows,[0,0,1,0,0,0],side)==[0,1,3,4]


def test_ledger_allocates_before_failure_and_never_refunds(tmp_path):
    from egrs.hint043.budget import ModelBudget
    p=tmp_path/'model.json';b=ModelBudget(p);old=b.report();b.consume('aux_train')
    restored=ModelBudget(p);restored.load_state_dict(old)
    assert restored.report()['aux_train']==1
    restored.counts['aux_train']=4000
    with pytest.raises(ValueError,match='exhausted'):restored.consume('aux_train')
    assert ModelBudget.validated(b.report())['aux_train']==1


def save_fake_adapter(tmp_path,arm='h1',update=1000):
    from egrs.hint043 import adapter
    p=fake_policy();adapter.install(p)
    model={'main_train':20*update,'aux_train':0,'main_dev':0,'aux_dev':0,'total':20*update,'budget':27072}
    ref={'train':8*update,'dev':0,'total':8*update,'budget':9024}
    v=adapter.save_adapter(p,tmp_path,arm=arm,update=update,sidecar_identity='f'*64,reference_calls=ref,model_calls=model)
    return p,v


def test_adapter_roundtrip_original_base_only_and_old_reader_refuses(tmp_path):
    from egrs.hint043 import adapter
    from egrs.augmentation.adapter_identity import read_adapter_identity as old
    p,v=save_fake_adapter(tmp_path/'adapter')
    q=fake_policy();adapter.attach(q,tmp_path/'adapter','h1')
    assert not hasattr(q.model,'task_control')
    assert all(not t.requires_grad for t in q.model.parameters())
    assert all(torch.equal(pv,qv) for pv,qv in zip(adapter.state(p).values(),adapter.state(q).values()))
    with pytest.raises(ValueError):old(tmp_path/'adapter')
    with pytest.raises(ValueError,match='historical'):adapter.install(q)


@pytest.mark.parametrize('field,value',[('deployment_hint',True),('index_identity','e'*64),('arm','c1'),('update',0)])
def test_adapter_identity_rejects_leakage_or_wrong_experiment(tmp_path,field,value):
    from egrs.hint043 import adapter
    _,v=save_fake_adapter(tmp_path/'adapter');v[field]=value
    with pytest.raises(ValueError):adapter.validate(v)


def test_planning_imports_no_model_libraries():
    code="import sys; import egrs.hint043.evaluation; assert 'torch' not in sys.modules; assert 'h5py' not in sys.modules"
    subprocess.run([sys.executable,'-c',code],check=True)


def test_prompt_override_keeps_native_shifted56_for_different_lengths(monkeypatch):
    from test_task_control_model import tiny_policy,sensors,Inputs
    from egrs.hint043 import adapter,oft
    p=tiny_policy(monkeypatch);adapter.install(p);seen=[]
    class VariableProcessor:
        def __call__(self,text,image):
            seen.append(text)
            n=5 if 'Current task-goal facts:' not in text else 13
            return Inputs(input_ids=torch.ones((1,n),dtype=torch.long),attention_mask=torch.ones((1,n),dtype=torch.long),
                          pixel_values=torch.tensor([image]).reshape(1,1,1,1))
    p.processor=VariableProcessor()
    for hint in (None,'two current goal relations'):
        result=oft.prediction(p,sensors(),hint)
        assert result.shape==(1,8,7);result.sum().backward()
    assert len(seen)==4 and seen[0]==seen[1]==c.prompt('Move cup')
    assert 'Current task-goal facts:' in seen[-1]
    with pytest.raises(ValueError,match='only current'):oft.prediction(p,dict(sensors(),hint='leak'))


def test_auxiliary_loss_is_valid_scalar_mean_not_per_view_mean(monkeypatch):
    from egrs.hint043 import training
    from egrs.hint043.budget import ModelBudget
    from egrs.retention.reference import ReferenceBudget
    p=fake_policy();p.model.test_scalar=torch.nn.Parameter(torch.tensor(1.))
    items,pools=items20()
    items[0]['action_mask']=[True]+[False]*7
    items[1]['actions'].fill(10.)
    monkeypatch.setattr(training,'reference',lambda *args:torch.zeros(1,8,7))
    result=training.train_update(p,items,pools,{0:'fact',1:'fact'},[0,1],update=200,arm='h1',
        reference_budget=ReferenceBudget(),model_budget=ModelBudget(),
        predict=lambda p,item,hint=None:p.model.test_scalar.expand(1,8,7))
    assert result['auxiliary_bc']==pytest.approx((1+8*9)/9)


def test_full1000_fake_training_checkpoints_and_exact_resume(tmp_path):
    from egrs.hint043 import training,adapter,checkpoint
    from egrs.hint043.budget import ModelBudget
    from egrs.retention.reference import ReferenceBudget
    from egrs.retention.training import ThreePoolSampler
    class Dataset:
        identity=c.INDEX_IDENTITY
        def __init__(self,split):
            self.rows=[dict(source_id=f'{split}/{pool}/{i}',observation_index=i,split=split,pool=pool,
                task_key='basket',source_group=split+'/parent',variant=0,prefix=i==0,action_mask=[True]*8)
                for pool in ('ten','fresh','raw') for i in (0,1)]
        def __getitem__(self,i):return items20()[0][0]
        def validate_normalization(self,*args):pass
    train,dev=Dataset('train'),Dataset('dev')
    side=SimpleNamespace(manifest={'identity':'f'*64},for_row=lambda r:{'hint_eligible':r['pool']=='ten','text':'two current relations'})
    cfg={'arm':'h1','training_recipe':deepcopy(c.RECIPE)}
    p=fake_policy();initial=deepcopy(p)
    result=training.run_loaded(cfg,tmp_path/'run',train,dev,side,p,predict=fake_prediction)
    assert result['update']==1000 and result['reference_calls']['train']==8000
    assert result['model_calls']['main_train']==20000 and result['model_calls']['aux_train']==4000
    assert (tmp_path/'run/selected_checkpoint.json').exists()
    assert len(list((tmp_path/'run').glob('update-*')))==4
    saved=c.read_json(tmp_path/'run/run_config.json')
    q=deepcopy(initial);adapter.install(q)
    optim=torch.optim.AdamW([p for p in q.model.parameters() if p.requires_grad],lr=2e-5)
    sched=torch.optim.lr_scheduler.LambdaLR(optim,lambda n:min(1.,(n+1)/50))
    sampler=ThreePoolSampler(train.rows,seed=7)
    assert checkpoint.load(tmp_path/'run/update-000250',q,optim,sched,sampler,config=saved,
        sidecar_identity='f'*64,reference_budget=ReferenceBudget(),model_budget=ModelBudget())==250
    with pytest.raises(ValueError,match='older than spent'):
        checkpoint.load(tmp_path/'run/update-000250',q,optim,sched,sampler,config=saved,sidecar_identity='f'*64,
            reference_budget=ReferenceBudget(tmp_path/'run/reference_budget.json'),model_budget=ModelBudget(tmp_path/'run/model_budget.json'))
    final=adapter.read_adapter_identity(tmp_path/'run/update-001000')
    assert final['deployment_hint'] is False and final['initialization']=='original_sog10_research_update_zero'


def test_cli_does_not_dump_large_manifests_or_full_episode_reports(monkeypatch,capsys):
    from egrs.hint043 import prepare,evaluation
    from egrs.hint043.__main__ import main
    monkeypatch.setattr(prepare,'build_sidecar',lambda *a:{'format':'fake','identity':'a'*64,
        'rows':3,'training_ready':True,'inputs':{'do not dump':'private metadata'}})
    main(['prepare','--index-dir','fake','--output','fake'])
    text=capsys.readouterr().out
    assert 'private metadata' not in text and len(text)<300
    monkeypatch.setattr(evaluation,'run',lambda *a,**k:{'schema_version':'fake','arm':'h1','formal_complete':True,
        'conditions':{b:{'formal_SR':{'percent':50},'episodes':'not printed'} for b in ('10','00')}})
    main(['evaluate','--config','fake','--output','fake','--arm','h1'])
    text=capsys.readouterr().out
    assert 'not printed' not in text and 'formal_SR' in text and len(text)<300


def test_deployed_templates_keep_sidecar_outside_legacy_broad_data_root(tmp_path):
    templates=Path(__file__).parents[1]/'configs/hint043'
    data=tmp_path/'data'
    protected=[data,data/'trajectory035/raw',data/'coverage040/production-001/generated']
    with pytest.raises(ValueError,match='overlaps protected input'):
        c.forbid_overlap(data/'hint043/status-001',protected)
    for arm in ('h0','h1'):
        config=json.loads((templates/f'training.{arm}.example.json').read_text().replace('${LNA043_ROOT}',str(tmp_path)))
        assert c.forbid_overlap(config['sidecar_dir'],protected)==tmp_path/'annotations/task043/status-001'
    script=(templates/'prepare_and_train_both.sh').read_text()
    assert '$LNA043_ROOT/annotations/task043/status-001' in script
    assert 'data/hint043/status-001' not in script


def test_pathfix_launcher_fake_calls_and_preserves_failed_launch_marker(tmp_path):
    import os
    templates=Path(__file__).parents[1]/'configs/hint043'
    config=tmp_path/'config';config.mkdir()
    (tmp_path/'runs/task043-train-launch-001').mkdir(parents=True)
    binary=tmp_path/'bin';binary.mkdir()
    fake=binary/'python'
    fake.write_text('#!'+sys.executable+'\n'+'''import json,sys,os
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['FAKE_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
out=Path(args[args.index('--output')+1]);out.mkdir(parents=True)
if args[3]=='train':
 (out/'update-001000').mkdir()
 (out/'update-001000/identity.json').write_text('{}')
 (out/'selected_checkpoint.json').write_text('{}')
''')
    fake.chmod(0o755)
    calls=tmp_path/'calls.jsonl'
    env=dict(os.environ,LNA043_ROOT=str(tmp_path),LNA043_CODE=str(tmp_path),LNA043_CONFIG=str(config),
             FAKE_CALLS=str(calls),PATH=str(binary)+os.pathsep+os.environ['PATH'])
    result=subprocess.run(['bash',str(templates/'prepare_and_train_both.sh')],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    records=[json.loads(x) for x in calls.read_text().splitlines()]
    assert [r[3] for r in records]==['prepare','train','train']
    assert records[0][-1]==str(tmp_path/'annotations/task043/status-001')
    assert (tmp_path/'runs/task043-train-launch-001').is_dir()
    assert (tmp_path/'runs/task043-train-launch-pathfix1').is_dir()
    assert 'COMPLETE both' in result.stdout
    again=subprocess.run(['bash',str(templates/'prepare_and_train_both.sh')],env=env,capture_output=True,text=True)
    assert again.returncode!=0 and len(calls.read_text().splitlines())==3
