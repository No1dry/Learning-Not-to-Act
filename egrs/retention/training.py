"""Explicit task036 three-pool training on one shared frozen SOG10 base."""
import argparse
from collections import Counter
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import json
from pathlib import Path
import random
import time

import numpy as np
import torch

from egrs.augmentation import training as base
from egrs.augmentation.adapter_identity import BASE_SOURCE, RETENTION_RECIPE, RETENTION_STATS_SHA
from egrs.augmentation.oft import (inject_language_lora, read_adapter_identity, sha256,
                                   training_prediction)
from .reference import ReferenceBudget, reference_prediction

NAME='policy_retention_distillation'
DATA_KIND='task036-retention-data-v1'
POOLS=('ten','fresh','raw')
WEIGHTS={'ten':.5,'fresh':.25,'raw':.25}
SAMPLES={'ten':12,'fresh':4,'raw':4}


def _hierarchies(rows,split):
    result={pool:{} for pool in POOLS}
    for index,row in enumerate(rows):
        pool=row.get('pool')
        if pool not in result:raise ValueError('Unknown retention pool')
        if pool=='ten':
            mask=np.asarray(row['action_mask'],dtype=bool)
            if mask.shape!=(8,) or not mask.any():raise ValueError('ten window has no valid action scalars')
            bins=('expert',)
        else:
            if type(row.get('prefix')) is not bool:raise ValueError('Explicit observation time-bin metadata required')
            bins=('all','prefix') if row['prefix'] else ('all',)
        for bin_ in bins:
            result[pool].setdefault(bin_,{}).setdefault(row['task_key'],{}).setdefault(
                row['source_group'],{}).setdefault(str(row.get('variant','observation')),[]).append(index)
    for pool in POOLS:
        needed=('expert',) if pool=='ten' else ('prefix','all')
        if any(not result[pool].get(bin_) for bin_ in needed):
            raise ValueError(f'{split} {pool} pool/time bin is empty; no fallback is permitted')
    return result


class ThreePoolSampler:
    """Pool/time-bin -> task -> parent group -> variant -> current window."""
    def __init__(self,rows,seed=7,budget=None):
        self.rows=rows;self.pools=_hierarchies(rows,'train');self.rng=random.Random(seed)
        self.counts=Counter();self.bin_counts=Counter();self.hierarchy_counts=Counter();self.budget=budget
        self.last_bins=[];self.resume_reference_calls=None

    def draw_batch(self):
        result=[];self.last_bins=[]
        for pool in POOLS:
            bins=['expert']*12 if pool=='ten' else ['prefix']*2+['all']*2
            for bin_ in bins:
                tasks=self.pools[pool][bin_];task=self.rng.choice(sorted(tasks))
                parent=self.rng.choice(sorted(tasks[task]));variants=tasks[task][parent]
                variant=self.rng.choice(sorted(variants));index=self.rng.choice(variants[variant])
                result.append(index);self.last_bins.append(bin_);self.counts[pool]+=1
                self.bin_counts[pool+'|'+bin_]+=1
                self.hierarchy_counts[json.dumps([pool,task,parent,variant])]+=1
        return result

    def report(self):
        return {'pool_samples':SAMPLES,'loss_weights':WEIGHTS,'pool_draw_counts':dict(self.counts),
                'time_bin_draw_counts':dict(self.bin_counts),'hierarchy_draw_counts':dict(self.hierarchy_counts)}

    def state_dict(self):
        return {'rng':self.rng.getstate(),'counts':dict(self.counts),'bin_counts':dict(self.bin_counts),
            'hierarchy_counts':dict(self.hierarchy_counts),
            'reference_budget':self.budget.state_dict() if self.budget is not None else None}

    def load_state_dict(self,state):
        if self.resume_reference_calls is not None and state.get('reference_budget')!=self.resume_reference_calls:
            raise ValueError('Resume reference budget differs from adapter identity')
        if self.budget is not None:self.budget.load_state_dict(state['reference_budget'])
        self.rng.setstate(state['rng']);self.counts=Counter(state['counts'])
        self.bin_counts=Counter(state['bin_counts']);self.hierarchy_counts=Counter(state['hierarchy_counts'])


def dev_indices(rows,seed=7):
    pools=_hierarchies(rows,'dev');rng=random.Random(seed)
    def interleave(pool):
        if isinstance(pool,list):
            result=list(pool);rng.shuffle(result);return result
        queues=[interleave(pool[key]) for key in sorted(pool)]
        return [queue[offset] for offset in range(max(map(len,queues))) for queue in queues if offset<len(queue)]
    return {'ten':interleave(pools['ten']['expert'])[:256],
        **{pool:{bin_:interleave(pools[pool][bin_])[:64] for bin_ in ('prefix','all')} for pool in ('fresh','raw')}}


def batch_weights(items,pools):
    if len(items)!=len(pools) or any(pool not in POOLS for pool in pools):raise ValueError('Invalid retention batch')
    counts=[]
    for item,pool in zip(items,pools):
        mask=np.asarray(item['action_mask'] if pool=='ten' else [True]*8,dtype=bool)
        if mask.shape!=(8,) or not mask.any():raise ValueError('Every sample requires valid action scalars')
        counts.append(int(mask.sum())*7)
    totals={pool:sum(n for n,p in zip(counts,pools) if p==pool) for pool in POOLS}
    if any(not n for n in totals.values()):raise ValueError('Three valid pools required; no fallback is permitted')
    return [WEIGHTS[p]*n/totals[p] for p,n in zip(pools,counts)],{
        'valid_scalars':totals,'sample_counts':dict(Counter(pools)),'loss_weights':WEIGHTS}


def validate_config(config):
    if config!=PRESET:raise ValueError('Configuration differs from the fixed task036 training preset')


PRESET={'name':NAME,'data_kind':DATA_KIND,'pool_weights':WEIGHTS,'pool_samples':SAMPLES,
    'reference_prefix_samples':{'fresh':2,'raw':2},'prefix':'max(1,ceil(T_obs/3))',
    'photometric_probability':0.,'seed':7,'updates':1000,'save_every':250,
    'learning_rate':2e-5,'warmup_updates':50,'gradient_accumulation':20,'microbatch':1,
    'precision':'bf16','gradient_checkpointing':True,'dev_ten_limit':256,
    'dev_reference_per_pool':128,'dev_prefix_per_pool':64,'reference_budget':9024,
    'checkpoint_selection':'fixed_terminal_update'}


def _sensors(item):
    return {key:item[key] for key in ('images','proprio','instruction')}


def _amp(policy):
    return torch.autocast('cuda',dtype=torch.bfloat16) if next(policy.model.parameters()).is_cuda else nullcontext()


def _modules(policy):
    return list({id(module):module for root in (policy.model,policy.action_head,policy.proprio_projector)
                 for module in root.modules()}.values())


@contextmanager
def _student_eval(policy):
    modules=_modules(policy);flags=[m.training for m in modules]
    try:
        for module in modules:module.training=False
        with torch.no_grad():yield
    finally:
        for module,flag in zip(modules,flags):module.training=flag


def _reference(policy,item,split,budget,predict):
    budget.consume(split)
    with _amp(policy):return reference_prediction(policy,_sensors(item),predict=predict)


def evaluate_dev(policy,dataset,selection,budget,*,predict=training_prediction):
    sums={pool:0. for pool in POOLS};counts={pool:0 for pool in POOLS}
    selected={'ten':selection['ten'],**{p:selection[p]['prefix']+selection[p]['all'] for p in ('fresh','raw')}}
    with _student_eval(policy):
        for pool in POOLS:
            for index in selected[pool]:
                item=dataset[index]
                target=(torch.as_tensor(item['actions']).unsqueeze(0) if pool=='ten'
                    else _reference(policy,item,'dev',budget,predict))
                with _amp(policy):prediction=predict(policy,_sensors(item))
                target=target.to(device=prediction.device)
                mask=torch.as_tensor(item['action_mask'] if pool=='ten' else [True]*8,
                    device=prediction.device,dtype=torch.bool).reshape(1,8,1).expand_as(prediction)
                sums[pool]+=(prediction.float()-target.float()).abs().masked_select(mask).sum().item()
                counts[pool]+=int(mask.sum())
    losses={pool:sums[pool]/counts[pool] for pool in POOLS}
    return {'pool_l1':losses,'weighted_l1':sum(WEIGHTS[p]*losses[p] for p in POOLS),
            'observations':{p:len(selected[p]) for p in POOLS},'reference_time_bins':{
                p:{b:len(selection[p][b]) for b in ('prefix','all')} for p in ('fresh','raw')}}


def _metadata(update,run_config,budget):
    return {'recipe':NAME,'data_kind':DATA_KIND,'update':update,'final_update':1000,
        'export_identity':run_config['export_identity'],'reference_view':'shared_frozen_base_without_added_lora',
        'reference_base':deepcopy(BASE_SOURCE),'training_recipe':deepcopy(RETENTION_RECIPE),
        'reference_calls':budget.report()}


def _run_loaded(args,config,train,dev,policy,*,predict=training_prediction):
    if args.resume and Path(args.resume).resolve().parent!=Path(args.output_dir).resolve():
        raise ValueError('Task036 resume must keep the original output directory and reference budget ledger')
    for dataset in (train,dev):dataset.validate_normalization(policy.model.norm_stats,policy.cfg.unnorm_key,
        policy.metadata['dataset_statistics_sha256'])
    if policy.metadata['dataset_statistics_sha256']!=RETENTION_STATS_SHA or policy.cfg.unnorm_key!='libero_10_no_noops':
        raise ValueError('Task036 requires the original fixed SOG10 statistics')
    output=Path(args.output_dir);output.mkdir(parents=True,exist_ok=True)
    budget=ReferenceBudget(ledger_path=output/'reference_budget.json')
    sampler=ThreePoolSampler(train.rows,seed=config['seed'],budget=budget);selection=dev_indices(dev.rows,seed=config['seed'])
    inject_language_lora(policy)
    policy.model.language_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    policy.model.language_model.config.use_cache=False
    parameters=[value for value in policy.model.parameters() if value.requires_grad]
    optimizer=torch.optim.AdamW(parameters,lr=config['learning_rate'])
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda step:min(1.,(step+1)/max(1,config['warmup_updates'])))
    run_config=dict(config,export_identity={name:sha256(Path(args.export_dir)/name)
        for name in ('sources.json','rows.jsonl','report.json')},reference_view='shared_frozen_base_without_added_lora')
    update=0
    if args.resume:
        identity=read_adapter_identity(args.resume)
        if identity.get('schema_version')!='task036-oft-adapter-v1' or identity['export_identity']!=run_config['export_identity']:
            raise ValueError('Resume requires matching task036 adapter and exported data')
        sampler.resume_reference_calls=identity['reference_calls']
        update,_=base.load_training_state(args.resume,policy,optimizer,scheduler,sampler,run_config)
        if identity['update']!=update:raise ValueError('Resume adapter update differs from optimizer state')
        sampler.resume_reference_calls=None
    if update>=config['updates']:raise ValueError('This training run is already complete; no new updates required')
    (output/'run_config.json').write_text(json.dumps(run_config,indent=2),encoding='utf-8')
    started=time.monotonic();start_update=update
    with (output/'metrics.jsonl').open('a',encoding='utf-8') as log:
        while update<config['updates']:
            policy.model.train()
            for module in (policy.model.vision_backbone,policy.action_head,policy.proprio_projector):module.eval()
            if isinstance(getattr(policy.model,'projector',None),torch.nn.Module):policy.model.projector.eval()
            optimizer.zero_grad(set_to_none=True)
            indices=sampler.draw_batch();items=[train[i] for i in indices]
            pools=[train.rows[i]['pool'] for i in indices];scales,batch=batch_weights(items,pools)
            # All references precede every student graph, including checkpoint recomputation.
            targets=[torch.as_tensor(item['actions']).unsqueeze(0) if pool=='ten'
                else _reference(policy,item,'train',budget,predict) for item,pool in zip(items,pools)]
            pool_l1={pool:0. for pool in POOLS}
            for item,pool,target,scale in zip(items,pools,targets,scales):
                with _amp(policy):
                    prediction=predict(policy,_sensors(item));target=target.to(device=prediction.device)
                    mask=torch.as_tensor(item['action_mask'] if pool=='ten' else [True]*8,
                        device=prediction.device).unsqueeze(0)
                    loss=base.masked_l1(prediction,target,mask)
                (loss*scale).backward();pool_l1[pool]+=loss.detach().item()*scale/WEIGHTS[pool]
            optimizer.step();scheduler.step();update+=1
            elapsed=time.monotonic()-started
            metrics={'update':update,'completion_percent':100*update/config['updates'],'pool_l1':pool_l1,
                'weighted_l1':sum(WEIGHTS[p]*pool_l1[p] for p in POOLS),'elapsed_seconds':elapsed,
                'eta_seconds':elapsed/max(1,update-start_update)*(config['updates']-update),
                'learning_rate':scheduler.get_last_lr()[0],'batch':batch,'sampling':sampler.report()}
            if update%config['save_every']==0 or update==config['updates']:
                metrics['dev']=evaluate_dev(policy,dev,selection,budget,predict=predict)
                directory=output/f'update-{update:06d}'
                if directory.exists():raise FileExistsError('New task036 checkpoint directory required')
                base.save_training_state(directory,policy,optimizer,scheduler,sampler,update,
                    metrics['dev']['weighted_l1'],run_config,adapter_metadata=_metadata(update,run_config,budget))
                if update==config['updates']:
                    (output/'selected_checkpoint.json').write_text(json.dumps({'checkpoint':directory.name,'update':update,
                        'selection':'fixed terminal update','recipe':NAME},indent=2),encoding='utf-8')
            metrics['reference_calls']=budget.report()
            print(json.dumps(metrics),flush=True);log.write(json.dumps(metrics)+'\n');log.flush()
    return {'update':update,'reference_calls':budget.report(),'selected_checkpoint':str(output/f'update-{update:06d}')}


def run(args):
    from .data import RetentionDataset
    config=json.loads(Path(args.config).read_text(encoding='utf-8'));validate_config(config)
    output=Path(args.output_dir).resolve()
    if args.resume and Path(args.resume).resolve().parent!=output:
        raise ValueError('Task036 resume must keep the original output directory and reference budget ledger')
    if output.exists() and any(output.iterdir()) and not args.resume:raise ValueError('Fresh run requires an empty output directory')
    for name in ('export_dir','benchmark_root','oft_root','checkpoint'):
        root=Path(getattr(args,name)).resolve()
        if output==root or root in output.parents or output in root.parents:
            raise ValueError('Training output overlaps immutable input/dependency')
    train=RetentionDataset(args.export_dir,split='train',pools=list(POOLS))
    dev=RetentionDataset(args.export_dir,split='dev',pools=list(POOLS))
    if any(dataset.report.get('data_kind')!=DATA_KIND for dataset in (train,dev)):
        raise ValueError('Task036 requires the versioned three-pool data kind')
    ThreePoolSampler(train.rows,seed=config['seed']);dev_indices(dev.rows,seed=config['seed'])
    if args.resume and read_adapter_identity(args.resume).get('schema_version')!='task036-oft-adapter-v1':
        raise ValueError('Only task036 checkpoints may be resumed; do not continue035')
    random.seed(config['seed']);np.random.seed(config['seed']);torch.manual_seed(config['seed'])
    policy=base.load_policy(args.benchmark_root,args.oft_root,args.checkpoint)
    try:return _run_loaded(args,config,train,dev,policy)
    finally:policy.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('config','export-dir','output-dir','benchmark-root','oft-root','checkpoint'):parser.add_argument('--'+flag,required=True)
    parser.add_argument('--resume',help='Matching local task036 checkpoint, never a035 adapter')
    run(parser.parse_args(argv))


if __name__=='__main__':main()
