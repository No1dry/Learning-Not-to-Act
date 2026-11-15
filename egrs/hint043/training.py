"""User-invoked original-base LoRA training, hinted aux and unhinted actor."""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import random
import time

import numpy as np
import torch

from egrs.augmentation import training as base
from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
from egrs.retention.training import ThreePoolSampler, batch_weights, dev_indices
from egrs.retention.reference import ReferenceBudget, reference_prediction
from egrs.retention041.reference import preserve_rng
from .contracts import (INDEX_IDENTITY, RECIPE, require, sensors, transfer_weight,
                        write_json, read_json, identity, forbid_overlap, load_config)
from .budget import ModelBudget
from .prepare import Sidecar
from . import adapter, checkpoint
from .oft import prediction


def amp(policy):
    return torch.autocast('cuda',dtype=torch.bfloat16) if next(policy.model.parameters()).is_cuda else nullcontext()


def _student_train_mode(policy):
    policy.model.train()
    for module in (policy.model.vision_backbone,policy.action_head,policy.proprio_projector):
        module.eval()
    if isinstance(getattr(policy.model,'projector',None),torch.nn.Module):
        policy.model.projector.eval()


def aux_slots(rows, indices, sidecar):
    return [i for i,index in enumerate(indices) if rows[index]['pool']=='ten'
            and sidecar.for_row(rows[index])['hint_eligible']][:4]


def main_forward(policy,item,budget,kind,predict):
    budget.consume(kind)
    with amp(policy): return predict(policy,sensors(item))


def auxiliary_forward(policy,item,text,arm,budget,kind,predict):
    budget.consume(kind)
    with amp(policy): return predict(policy,sensors(item),hint=text if arm=='h1' else None)


def reference(policy,item,budget,split,predict):
    budget.consume(split)
    # A frozen-base call must not change later training randomness or modes.
    with preserve_rng(), amp(policy):
        return reference_prediction(policy,sensors(item),predict=lambda p,x:predict(p,x))


def target(item, device):
    return torch.as_tensor(item['actions'],device=device).reshape(1,8,7)


def mask(item, device):
    return torch.as_tensor(item['action_mask'],dtype=torch.bool,device=device).reshape(1,8)


def train_update(policy,items,pools,texts,slots,*,update,arm,reference_budget,model_budget,predict=prediction):
    """One software-testable update, no optimizer step inside this function."""
    scales,batch = batch_weights(items,pools)
    targets = [torch.as_tensor(item['actions']).reshape(1,8,7) if pool=='ten'
               else reference(policy,item,reference_budget,'train',predict) for item,pool in zip(items,pools)]
    denominator = sum(sum(items[i]['action_mask'])*7 for i in slots)
    detached = {}; auxiliary_loss=0.; transfer_loss=0.; main_loss=0.
    # All references are complete before any adapter graph is constructed.
    for i in slots:
        item = items[i]
        out = auxiliary_forward(policy,item,texts[i],arm,model_budget,'aux_train',predict)
        detached[i] = out.detach().clone()
        count = sum(item['action_mask'])*7
        loss = base.masked_l1(out,target(item,out.device),mask(item,out.device))*(count/denominator)
        (.25*loss).backward()
        auxiliary_loss += loss.detach().item()
        del out,loss
    for i,(item,pool,truth,scale) in enumerate(zip(items,pools,targets,scales)):
        out = main_forward(policy,item,model_budget,'main_train',predict)
        m = mask(item,out.device) if pool=='ten' else torch.ones((1,8),device=out.device,dtype=torch.bool)
        with amp(policy):
            loss = base.masked_l1(out,truth.to(out.device),m)*scale
            if i in detached:
                portion = sum(item['action_mask'])*7/denominator
                transfer = base.masked_l1(out,detached.pop(i),m)*portion
                loss = loss+transfer_weight(update)*transfer
                transfer_loss += transfer.detach().item()
        main_loss += (loss.detach().item())
        loss.backward()
        del out,loss
    return {'main_and_transfer_loss':main_loss,'auxiliary_bc':auxiliary_loss,
            'transfer_l1':transfer_loss,'transfer_weight':transfer_weight(update),
            'auxiliary_draws':len(slots),'batch':batch}


def evaluate_dev(policy,dataset,selection,sidecar,*,arm,reference_budget,model_budget,predict=prediction):
    selected = {'ten':selection['ten'],**{p:selection[p]['prefix']+selection[p]['all'] for p in ('fresh','raw')}}
    modules = list({id(m):m for root in (policy.model,policy.action_head,policy.proprio_projector) for m in root.modules()}.values())
    flags = [(m,m.training) for m in modules]
    sums={p:0. for p in selected};counts={p:0 for p in selected}
    aux_sum=0.;transfer_sum=0.;aux_count=0
    try:
        for m,_ in flags:m.training=False
        with torch.no_grad():
            for pool,indices in selected.items():
                for index in indices:
                    item=dataset[index]
                    truth=target(item,'cpu') if pool=='ten' else reference(policy,item,reference_budget,'dev',predict)
                    out=main_forward(policy,item,model_budget,'main_dev',predict)
                    m=mask(item,out.device) if pool=='ten' else torch.ones((1,8),device=out.device,dtype=torch.bool)
                    n=int(m.sum())*7
                    sums[pool]+=base.masked_l1(out,truth.to(out.device),m).item()*n;counts[pool]+=n
                    row=sidecar.for_row(dataset.rows[index])
                    if pool=='ten' and row['hint_eligible']:
                        aux=auxiliary_forward(policy,item,row['text'],arm,model_budget,'aux_dev',predict)
                        aux_sum+=base.masked_l1(aux,truth.to(aux.device),m).item()*n
                        transfer_sum+=base.masked_l1(out,aux,m).item()*n;aux_count+=n
    finally:
        for m,flag in flags:m.training=flag
    losses={p:sums[p]/counts[p] for p in selected}
    return {'pool_l1':losses,'weighted_l1':sum(RECIPE['pool_weights'][p]*losses[p] for p in selected),
            'auxiliary_bc':aux_sum/aux_count if aux_count else None,
            'transfer_l1':transfer_sum/aux_count if aux_count else None,
            'auxiliary_valid_scalars':aux_count,'not_closed_loop_SR':True}


def run_loaded(config,output,train,dev,sidecar,policy,*,resume=None,predict=prediction):
    out=Path(output).resolve();arm=config['arm']
    require(train.identity==dev.identity==INDEX_IDENTITY, 'Original train/dev index differs')
    require(policy.cfg.unnorm_key=='libero_10_no_noops' and policy.metadata['dataset_statistics_sha256']==RETENTION_STATS_SHA,
            'Original SOG10 statistics required')
    for ds in (train,dev):
        ds.validate_normalization(policy.model.norm_stats,policy.cfg.unnorm_key,RETENTION_STATS_SHA)
        for row in ds.rows: sidecar.for_row(row)
    require(not out.exists() if not resume else Path(resume).resolve().parent==out, 'Fresh run/resume output differs')
    random.seed(7);np.random.seed(7);torch.manual_seed(7)
    adapter.install(policy)
    policy.model.language_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    policy.model.language_model.config.use_cache=False
    optimizer=torch.optim.AdamW([p for p in policy.model.parameters() if p.requires_grad],lr=2e-5)
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda step:min(1.,(step+1)/50))
    sampler=ThreePoolSampler(train.rows,seed=7);selection=dev_indices(dev.rows,seed=7)
    # Bind exact selected keys, rather than incidental row indices only.
    selected_keys={'ten':[(dev.rows[i]['source_id'],dev.rows[i]['observation_index']) for i in selection['ten']],
        **{p:{b:[(dev.rows[i]['source_id'],dev.rows[i]['observation_index']) for i in selection[p][b]]
              for b in ('prefix','all')} for p in ('fresh','raw')}}
    run_config=dict(deepcopy(config),output_dir=str(out),sidecar_identity=sidecar.manifest['identity'],
                    dev_selection=selected_keys,initialization='original_sog10_research_update_zero')
    # JSON roundtrip keeps resume equality independent of tuple/list serialization.
    run_config=json.loads(json.dumps(run_config))
    out.mkdir(parents=True,exist_ok=True)
    reference_budget=ReferenceBudget(out/'reference_budget.json');model_budget=ModelBudget(out/'model_budget.json')
    reference_budget._persist();model_budget.persist()
    update=0
    if resume:
        update=checkpoint.load(resume,policy,optimizer,scheduler,sampler,config=run_config,
            sidecar_identity=sidecar.manifest['identity'],reference_budget=reference_budget,model_budget=model_budget)
    else:
        require(reference_budget.report()['total']==model_budget.report()['total']==0,'Spent budget cannot be reset')
    require(update<1000,'Training already complete')
    write_json(out/'run_config.json',run_config)
    started=time.monotonic();start_update=update
    with (out/'metrics.jsonl').open('a',encoding='utf-8') as log:
        while update<1000:
            _student_train_mode(policy);optimizer.zero_grad(set_to_none=True)
            indices=sampler.draw_batch();items=[train[i] for i in indices];pools=[train.rows[i]['pool'] for i in indices]
            slots=aux_slots(train.rows,indices,sidecar)
            texts={i:sidecar.for_row(train.rows[indices[i]])['text'] for i in slots}
            values=train_update(policy,items,pools,texts,slots,update=update+1,arm=arm,
                reference_budget=reference_budget,model_budget=model_budget,predict=predict)
            optimizer.step();scheduler.step();update+=1
            metrics=dict(values,arm=arm,update=update,expected_updates=1000,completion_percent=100*update/1000,
                elapsed_seconds=time.monotonic()-started,
                seconds_per_update=(time.monotonic()-started)/(update-start_update),
                sampling=sampler.report(),batch_keys_sha256=identity({'draws':[(train.rows[i]['source_id'],train.rows[i]['observation_index']) for i in indices]}))
            if update%250==0:
                metrics['dev']=evaluate_dev(policy,dev,selection,sidecar,arm=arm,
                    reference_budget=reference_budget,model_budget=model_budget,predict=predict)
                directory=out/f'update-{update:06d}'
                checkpoint.save(directory,policy,optimizer,scheduler,sampler,update=update,config=run_config,
                    sidecar_identity=sidecar.manifest['identity'],reference_budget=reference_budget,model_budget=model_budget)
                if update==1000:write_json(out/'selected_checkpoint.json',{'checkpoint':directory.name,'update':update,'selection':'fixed_terminal_1000'})
            metrics.update(reference_calls=reference_budget.report(),model_calls=model_budget.report())
            log.write(json.dumps(metrics,allow_nan=False)+'\n');log.flush();write_json(out/'progress.json',metrics)
            print(f"043 {arm} train {update}/1000 ({update/10:.1f}%) aux={len(slots)} loss={values['main_and_transfer_loss']:.5f}",flush=True)
    return {'complete':True,'arm':arm,'update':update,'selected_checkpoint':str(out/'update-001000'),
            'reference_calls':reference_budget.report(),'model_calls':model_budget.report()}


def run(config_path,output,*,resume=None):
    from egrs.coverage040.data import CoverageTaskControlDataset
    from egrs.coverage039.io import HashContext
    from egrs.augmentation.dependencies import activate_core
    cfg=load_config(config_path)
    forbid_overlap(output,[cfg[k] for k in ('index_dir','sidecar_dir','benchmark_root','runtime')])
    if not resume:require(not Path(output).exists(),'New run output required')
    sidecar=Sidecar(cfg['sidecar_dir'],cfg['index_dir'])
    context=HashContext()
    train=CoverageTaskControlDataset(cfg['index_dir'],'train',context=context)
    dev=CoverageTaskControlDataset(cfg['index_dir'],'dev',context=context)
    activate_core(cfg['benchmark_root'])
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
    runtime=load_runtime(cfg['runtime'])
    require(not {'method_adapter','task_control_arm','experiment_arm','hint','sidecar_dir'} & runtime.keys(), 'Original runtime must not load a historical adapter or hint')
    forbid_overlap(output,[runtime['adapter_options'][k] for k in ('repo_path','checkpoint')])
    policy=OpenVLAOFTPolicy(runtime)
    try:
        return run_loaded(cfg,output,train,dev,sidecar,policy,resume=resume)
    finally:policy.close()
