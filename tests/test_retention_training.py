"""Three-pool training with tiny CPU policies and synthetic dataset boundaries."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from test_augmentation_training import policy
from test_retention_data import prepared


def rows():
    return [dict(pool=pool,task_key=task,parent_demo_id=task+parent,
        source_group=task+parent,variant=variant,source_id=task+parent+variant,
        observation_index=i,observation_count=3,prefix=i==0,split='train',
        action_mask=[True]*(i+1)+[False]*(7-i))
        for pool in ('ten','fresh','raw') for task in ('a','b')
        for parent in ('1','2') for variant in ('0','1') for i in range(3)]


def test_three_pools_exact_samples_time_bins_and_rng_restore():
    from egrs.retention.training import ThreePoolSampler
    population=rows();sampler=ThreePoolSampler(population,seed=7)
    picked=sampler.draw_batch()
    assert [population[i]['pool'] for i in picked]==['ten']*12+['fresh']*4+['raw']*4
    assert sampler.last_bins==['expert']*12+['prefix','prefix','all','all']*2
    assert all(population[i]['prefix'] for i,bin_ in zip(picked,sampler.last_bins) if bin_=='prefix')
    state=sampler.state_dict();want=sampler.draw_batch();sampler.load_state_dict(state)
    assert sampler.draw_batch()==want
    assert sampler.report()['pool_draw_counts']=={'ten':24,'fresh':8,'raw':8}
    with pytest.raises(ValueError,match='raw'):
        ThreePoolSampler([r for r in population if r['pool']!='raw'])


def test_pool_normalized_gradient_matches_concat_with_unequal_ten_tail():
    from egrs.retention.training import batch_weights
    from egrs.augmentation.training import masked_l1
    items=[{'action_mask':[True]+[False]*7},{'action_mask':[True]*8},{},{}]
    pools=['ten','ten','fresh','raw']
    weights,metrics=batch_weights(items,pools)
    pred=torch.ones(4,8,7,requires_grad=True)
    losses=[masked_l1(pred[i:i+1],torch.zeros(1,8,7),
        torch.as_tensor(item.get('action_mask',[True]*8)).unsqueeze(0)) for i,item in enumerate(items)]
    sum(v*w for v,w in zip(losses,weights)).backward()
    assert pred.grad[0,0].tolist()==pytest.approx([.5/63]*7)
    assert pred.grad[1,0].tolist()==pytest.approx([.5/63]*7)
    assert pred.grad[2,0].tolist()==pytest.approx([.25/56]*7)
    assert pred.grad[3,0].tolist()==pytest.approx([.25/56]*7)
    assert torch.equal(pred.grad[0,1:],torch.zeros(7,7))
    assert metrics['valid_scalars']=={'ten':63,'fresh':56,'raw':56}


def test_dev_is_fixed_bounded_unique_within_each_time_box():
    from egrs.retention.training import dev_indices
    population=rows()
    for pool in ('ten','fresh','raw'):
        population.extend(dict(population[0],pool=pool,observation_index=i,observation_count=3000,prefix=i<1000)
                          for i in range(2000))
    chosen=dev_indices(population)
    assert chosen==dev_indices(population)
    assert len(chosen['ten'])==256
    for pool in ('fresh','raw'):
        assert len(chosen[pool]['prefix'])==len(chosen[pool]['all'])==64
        assert len(set(chosen[pool]['prefix']))==64 and len(set(chosen[pool]['all']))==64
        assert all(population[i]['prefix'] for i in chosen[pool]['prefix'])


def test_public_recipe_rejects_budget_weights_or_old_adapter_changes():
    from egrs.retention.training import validate_config
    config=json.loads((Path(__file__).parents[1]/'configs/retention/policy_retention_distillation.json').read_text())
    validate_config(config)
    for key,value in [('updates',2),('gradient_accumulation',16),('pool_weights',{'ten':1.,'fresh':0.,'raw':0.}),
        ('reference_budget',10000),('checkpoint_selection','best_dev'),('photometric_probability',.5)]:
        with pytest.raises(ValueError,match='preset'):validate_config(dict(config,**{key:value}))


class Dataset:
    def __init__(self):
        self.rows=rows();self.report={'data_kind':'task036-retention-data-v1'};self.validation=[]
    def __getitem__(self,index):
        row=self.rows[index]
        value={'images':[np.zeros((2,2,3),dtype=np.uint8)]*2,'proprio':np.arange(8,dtype=np.float32)/8,
            'instruction':'original complete instruction'}
        if row['pool']=='ten':value.update(actions=np.zeros((8,7),dtype=np.float32),action_mask=np.array(row['action_mask']))
        return value
    def validate_normalization(self,*args):self.validation.append(args)


def tiny_policy():
    from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
    p=policy();p.metadata['dataset_statistics_sha256']=RETENTION_STATS_SHA
    p.cfg=SimpleNamespace(unnorm_key='libero_10_no_noops');p.model.norm_stats={'fake':'already validated dataset boundary'}
    p.model.language_model.config=SimpleNamespace(use_cache=True)
    p.model.language_model.gradient_checkpointing_enable=lambda **kw:None
    return p


def prediction(p,item):
    assert set(item)=={'images','proprio','instruction'}
    value=torch.as_tensor(item['proprio'][:3]).reshape(1,3)
    return p.action_head(p.model(value)).reshape(1,1,1).expand(1,8,7)


def test_tiny_loop_reference_first_budget_save_resume_and_new_identity(tmp_path):
    from egrs.retention import training
    from egrs.augmentation.oft import read_adapter_identity
    config=json.loads((Path(__file__).parents[1]/'configs/retention/policy_retention_distillation.json').read_text())
    # Only this private tiny loop seam shortens runtime; CLI validation rejects it.
    config.update(updates=2,save_every=1)
    exported=tmp_path/'export';exported.mkdir()
    for name in ('sources.json','rows.jsonl','report.json'):(exported/name).write_text('{}')
    args=SimpleNamespace(export_dir=exported,output_dir=tmp_path/'run',resume=None)
    train,dev=Dataset(),Dataset();p=tiny_policy()
    training._run_loaded(args,config,train,dev,p,predict=prediction)
    identity=read_adapter_identity(tmp_path/'run/update-000002')
    assert identity['schema_version']=='task036-oft-adapter-v1' and identity['update']==2
    assert identity['reference_calls']['train']==16
    assert identity['reference_calls']['total']<=9024
    assert train.validation and dev.validation
    assert all(value.grad is None for value in p.action_head.parameters())
    assert any(value.grad is not None for name,value in p.model.named_parameters() if name.endswith('lora_B'))
    metrics=[json.loads(line) for line in (tmp_path/'run/metrics.jsonl').read_text().splitlines()]
    assert all(set(m['pool_l1'])=={'ten','fresh','raw'} for m in metrics)
    assert metrics[-1]['completion_percent']==100 and 'eta_seconds' in metrics[-1]
    assert json.loads((tmp_path/'run/selected_checkpoint.json').read_text())['update']==2


def test_interrupted_checkpoint_resumes_same_directory_with_full_budget(tmp_path,monkeypatch):
    from egrs.retention import training
    from egrs.augmentation.oft import read_adapter_identity
    config=deepcopy(training.PRESET);config.update(updates=2,save_every=1)
    exported=tmp_path/'export';exported.mkdir()
    for name in ('sources.json','rows.jsonl','report.json'):(exported/name).write_text('{}')
    args=SimpleNamespace(export_dir=exported,output_dir=tmp_path/'run',resume=None)
    original_save=training.base.save_training_state
    def interrupted(*a,**kwargs):
        original_save(*a,**kwargs)
        raise RuntimeError('fake interruption after complete checkpoint')
    monkeypatch.setattr(training.base,'save_training_state',interrupted)
    with pytest.raises(RuntimeError,match='fake interruption'):
        training._run_loaded(args,config,Dataset(),Dataset(),tiny_policy(),predict=prediction)
    monkeypatch.setattr(training.base,'save_training_state',original_save)
    args.resume=tmp_path/'run/update-000001';resumed=tiny_policy()
    training._run_loaded(args,config,Dataset(),Dataset(),resumed,predict=prediction)
    assert read_adapter_identity(tmp_path/'run/update-000002')['reference_calls']['train']==16
    assert all(module.enabled for module in resumed.model.modules() if hasattr(module,'enabled'))


def test_resume_cannot_escape_advanced_original_reference_ledger(tmp_path,monkeypatch):
    from egrs.retention import training
    old=tmp_path/'old';old.mkdir();checkpoint=old/'update-000250';checkpoint.mkdir()
    (old/'reference_budget.json').write_text(json.dumps({'train':2200,'dev':256,'total':2456,'budget':9024}))
    config=tmp_path/'config.json';config.write_text(json.dumps(training.PRESET))
    args=SimpleNamespace(config=config,export_dir=tmp_path/'data',output_dir=tmp_path/'new',resume=checkpoint,
        benchmark_root=tmp_path/'core',oft_root=tmp_path/'oft',checkpoint=tmp_path/'SOG10')
    monkeypatch.setattr(training.base,'load_policy',lambda *a:pytest.fail('model loaded before cross-directory resume rejection'))
    with pytest.raises(ValueError,match='original output directory'):training.run(args)
    with pytest.raises(ValueError,match='original output directory'):
        training._run_loaded(args,training.PRESET,Dataset(),Dataset(),tiny_policy(),predict=prediction)
    assert not (tmp_path/'new').exists()


def test_all_references_precede_student_graph_and_freeze_base(tmp_path):
    from egrs.retention import training
    from egrs.augmentation.oft import LoRALinear
    config=deepcopy(training.PRESET);config.update(updates=1,save_every=1)
    exported=tmp_path/'export';exported.mkdir()
    for name in ('sources.json','rows.jsonl','report.json'):(exported/name).write_text('{}')
    args=SimpleNamespace(export_dir=exported,output_dir=tmp_path/'run',resume=None)
    p=tiny_policy();before={name:value.detach().clone() for name,value in p.model.named_parameters()}
    events=[]
    def tracked(policy,item):
        enabled=[module.enabled for module in policy.model.modules() if isinstance(module,LoRALinear)]
        events.append(('student' if torch.is_grad_enabled() else 'nograd',all(enabled)))
        return prediction(policy,item)
    training._run_loaded(args,config,Dataset(),Dataset(),p,predict=tracked)
    # Eight train teacher calls occur before all20 student graphs. Later events are dev only.
    assert events[:8]==[('nograd',False)]*8
    assert events[8:28]==[('student',True)]*20
    for name,value in p.model.named_parameters():
        if '.base_layer.' in name:
            original_name=name.replace('.base_layer.','.')
            assert torch.equal(value,before[original_name]) and value.grad is None


@pytest.mark.parametrize('missing_split,missing_pool',[('train','ten'),('train','fresh'),('train','raw'),
    ('dev','ten'),('dev','fresh'),('dev','raw')])
def test_all_six_pools_validated_before_model_load(tmp_path,monkeypatch,missing_split,missing_pool):
    from egrs.retention import training,data
    config=tmp_path/'config.json';config.write_text(json.dumps(training.PRESET))
    class Sparse(Dataset):
        def __init__(self,root,split=None,pools=None):
            super().__init__()
            self.rows=[row for row in self.rows if split!=missing_split or row['pool']!=missing_pool]
    monkeypatch.setattr(data,'RetentionDataset',Sparse)
    monkeypatch.setattr(training.base,'load_policy',lambda *a:pytest.fail('model loaded before missing pool error'))
    args=SimpleNamespace(config=config,output_dir=tmp_path/'run',export_dir=tmp_path/'data',resume=None,
        benchmark_root=tmp_path/'core',oft_root=tmp_path/'oft',checkpoint=tmp_path/'checkpoint')
    with pytest.raises(ValueError,match=missing_split+'.*'+missing_pool):training.run(args)


def test_actual_retention_index_to_tiny_training_and_strict_adapter(prepared,tmp_path):
    from egrs.retention import data,training
    from egrs.augmentation.oft import read_adapter_identity
    config_path,_,manifest=prepared
    index=tmp_path/'retention-index';data.build_index(config_path,index)
    train=data.RetentionDataset(index,split='train');dev=data.RetentionDataset(index,split='dev')
    p=tiny_policy();mapping=manifest['sources'][0]['mapping']
    p.model.norm_stats={data.STATS_KEY:{kind:{k:mapping[kind+'_normalization'][k]
        for k in ('q01','q99','mask')} for kind in ('action','proprio')}}
    config=deepcopy(training.PRESET);config.update(updates=1,save_every=1)
    args=SimpleNamespace(export_dir=index,output_dir=tmp_path/'run-real-index',resume=None)
    result=training._run_loaded(args,config,train,dev,p,predict=prediction)
    identity=read_adapter_identity(Path(result['selected_checkpoint']))
    assert identity['schema_version']=='task036-oft-adapter-v1'
    assert identity['reference_calls']['train']==8 and identity['reference_calls']['dev']<=256
    assert set(identity['export_identity'])=={'sources.json','rows.jsonl','report.json'}


def test_exhausted_reference_ledger_stops_before_teacher_or_student(tmp_path):
    from egrs.retention import training
    exported=tmp_path/'export';exported.mkdir()
    for name in ('sources.json','rows.jsonl','report.json'):(exported/name).write_text('{}')
    output=tmp_path/'run';output.mkdir()
    (output/'reference_budget.json').write_text(json.dumps({'train':8000,'dev':0,'total':8000,'budget':9024}))
    config=deepcopy(training.PRESET);config.update(updates=1,save_every=1)
    args=SimpleNamespace(export_dir=exported,output_dir=output,resume=None)
    with pytest.raises(ValueError,match='budget exhausted'):
        training._run_loaded(args,config,Dataset(),Dataset(),tiny_policy(),
            predict=lambda *a:pytest.fail('reference limit must stop before any forward'))
    assert not (output/'selected_checkpoint.json').exists()
    assert json.loads((output/'reference_budget.json').read_text())['train']==8000
