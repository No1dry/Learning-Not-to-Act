"""User-started042 F0/F1; fixed original C1 and explicit per-observation SDPA."""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import re
import time

import numpy as np
import torch

from egrs.augmentation import training as base
from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
from egrs.coverage039.io import HashContext, Progress
from egrs.task_control import training as original
from egrs.task_control.reference import ReferenceBudget, StudentBudget
from egrs.task_control.sampling import TaskControlSampler, dev_indices, dev_pair_indices, batch_weights, POOLS, WEIGHTS
from . import adapter, checkpoint
from .config import load_config
from egrs.retention041.data import StageDataset
from egrs.retention041.reference import original_reference_prediction, preserve_rng
from .contract import contract_for, validate_contract


def _stage(config, index_identity):
    initial = adapter.read_source_identity(config['initial_adapter'], index_identity)
    result = {'format': 'task042-stage-inputs-v1', 'arm': 'c1',
              'experiment_arm': config['experiment_arm'], 'initialization_identity': initial,
              'index_identity': index_identity, 'ancestor_updates': 2000, 'additional_updates': 1000,
              'attention_contract': contract_for(config['experiment_arm'])}
    adapter.validate_stage_identity(result, config['experiment_arm'], index_identity)
    return result


def _run_loaded(args, config, train, dev, policy, *, stage_identity=None, predict=None,
                decode=None, reference_predict=None, attention_factory=None):
    """Private short CPU seam; the public config retains the exact1000 preset."""
    from egrs.task_control.oft import install, decode as decode_actions
    from .oft import prediction
    from .attention import install_attention
    predict = prediction if predict is None else predict
    decode = decode_actions if decode is None else decode
    arm = config['experiment_arm']
    if arm not in ('f0', 'f1'):
        raise ValueError('042 experiment_arm must be f0 or f1; both use base C1')
    recipe = config['training_recipe']; output = _argument_path(args.output_dir)
    resume = _argument_path(args.resume) if args.resume else None
    if resume and resume.parent != output:
        raise ValueError('042 resume must stay in the original stage output and ledgers')
    if output.exists() and not args.resume:
        raise FileExistsError('New042 stage needs a new output; use explicit same-run resume')
    if train.identity != dev.identity:
        raise ValueError('042 train/dev input identity differs')
    for dataset in (train, dev):
        dataset.validate_normalization(policy.model.norm_stats, policy.cfg.unnorm_key,
                                       policy.metadata['dataset_statistics_sha256'])
    if policy.cfg.unnorm_key != 'libero_10_no_noops' or policy.metadata['dataset_statistics_sha256'] != RETENTION_STATS_SHA:
        raise ValueError('042 requires the original fixed SOG10 statistics')
    stage = _stage(config, train.identity) if stage_identity is None else deepcopy(stage_identity)
    adapter.validate_stage_identity(stage, arm, train.identity)
    sampler = TaskControlSampler(train.rows, train.pairs, seed=recipe['seed'])
    selection = dev_indices(dev.rows, seed=recipe['seed'])
    pair_selection = dev_pair_indices(dev.pairs, seed=recipe['seed'])
    # Same fresh stage initialization in both arms, never the041 optimizer/RNG.
    random.seed(recipe['seed']); np.random.seed(recipe['seed']); torch.manual_seed(recipe['seed'])
    install(policy)
    loaded = adapter.initialize_from041(policy, config['initial_adapter'], train.identity)
    if loaded != stage['initialization_identity']:
        raise ValueError('041 R0 initialization changed after stage validation')
    controller = (install_attention if attention_factory is None else attention_factory)(policy, arm)
    policy._tcif042 = controller
    validate_contract(controller.contract, arm)
    if controller.contract != stage['attention_contract']:
        raise ValueError('042 installed attention contract differs from stage identity')
    runtime = deepcopy(controller.runtime)
    # Observed class/source/version/dtype is recorded and bound to exact resume.
    json.dumps(runtime, allow_nan=False)
    policy.model.language_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    policy.model.language_model.config.use_cache = False
    parameters = [p for p in policy.model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=recipe['learning_rate'])
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer,
        lambda step: min(1., (step+1)/max(1, recipe['warmup_updates'])))
    output.mkdir(parents=True, exist_ok=True)
    reference_budget = ReferenceBudget(output/'reference_budget.json')
    student_budget = StudentBudget(output/'student_budget.json')
    # Persist both zeros before any real call, including failures on reference one.
    for budget in (reference_budget, student_budget):
        budget._persist()
    run_config = dict(recipe, arm='c1', experiment_arm=arm, index_identity=train.identity, output_dir=str(output),
                      stage_config=deepcopy(config), stage_identity=stage,
                      attention_contract=deepcopy(controller.contract), attention_runtime=runtime)
    update = 0
    if args.resume:
        update = checkpoint.load_training_state(resume, policy, optimizer, scheduler, sampler,
            config=run_config, experiment_arm=arm, index_identity=train.identity, stage_identity=stage,
            reference_budget=reference_budget, student_budget=student_budget)
    elif any(b.report()['total'] for b in (reference_budget, student_budget)):
        raise ValueError('New042 stage cannot reset spent forward budgets')
    if update >= recipe['updates']:
        raise ValueError('This042 stage is already complete; no new updates required')
    (output/'run_config.json').write_text(json.dumps(run_config, indent=2), encoding='utf-8')
    started = time.monotonic(); start_update = update; last_dev = None
    with (output/'metrics.jsonl').open('a', encoding='utf-8') as log:
        while update < recipe['updates']:
            original._student_train_mode(policy)
            optimizer.zero_grad(set_to_none=True)
            indices, pair_index = sampler.draw_batch()
            items = [train[i] for i in indices]; pools = [train.rows[i]['pool'] for i in indices]
            scales, batch = batch_weights(items, pools)
            u_item, v_item = train.get_pair(pair_index)
            labels = [item.get('count_label') if pool != 'raw' else None for item, pool in zip(items, pools)]
            labels += [u_item.get('count_label'), v_item.get('count_label')]
            count_scales = original.count_weights(labels)
            # All eight original SOG10 references finish before any student graph.
            targets = []
            for item, pool in zip(items, pools):
                if pool == 'ten':
                    targets.append(torch.as_tensor(item['actions']).reshape(1, 8, 7))
                else:
                    reference_budget.consume('train')
                    with original._amp(policy):
                        targets.append(original_reference_prediction(policy, original._sensors(item), reference_predict))
            pool_l1 = {pool: 0. for pool in POOLS}; count_value = 0.
            for offset, (item, pool, target, scale) in enumerate(zip(items, pools, targets, scales)):
                encoded = original._student(policy, item, 'train', student_budget, predict)
                with original._amp(policy):
                    target = target.to(encoded.actions.device)
                    loss = base.masked_l1(encoded.actions, target, torch.as_tensor(
                        item['action_mask'] if pool == 'ten' else [True]*8,
                        device=encoded.actions.device).reshape(1, 8))
                    count = original._count_term(encoded.count_logits, labels[offset], count_scales[offset])
                    objective = loss*scale + .1*count
                objective.backward()
                pool_l1[pool] += loss.detach().item()*scale/WEIGHTS[pool]
                count_value += count.detach().item()
            u = original._student(policy, u_item, 'train', student_budget, predict)
            v = original._student(policy, v_item, 'train', student_budget, predict)
            with original._amp(policy):
                losses = original.pair_losses(policy, u, v, u_item, v_item, arm='c1', decode=decode)
                pair_count = (original._count_term(u.count_logits, labels[-2], count_scales[-2])
                              + original._count_term(v.count_logits, labels[-1], count_scales[-1]))
                objective = original.total_loss(u.actions.new_zeros(()), pair_count, losses, arm='c1')
            objective.backward(); count_value += pair_count.detach().item()
            optimizer.step(); scheduler.step(); update += 1
            elapsed = time.monotonic()-started
            metrics = {'arm': 'c1', 'experiment_arm': arm, 'update': update,
                'ancestor_updates': 2000, 'additional_updates': update, 'total_ancestral_updates': 2000+update,
                'completion_percent': 100*update/recipe['updates'], 'pool_l1': pool_l1,
                'weighted_l1': sum(WEIGHTS[p]*pool_l1[p] for p in POOLS), 'count': count_value,
                **{key: value.detach().item() for key, value in losses.items()},
                'elapsed_seconds': elapsed, 'eta_seconds': elapsed/max(1, update-start_update)*(recipe['updates']-update),
                'learning_rate': scheduler.get_last_lr()[0], 'batch': batch,
                'sampling': original.sampling_log(sampler, compact=True)}
            if update % recipe['save_every'] == 0 or update == recipe['updates']:
                # Original fixed dev selection and native references, with isolated RNG.
                def dev_reference(current_policy, item):
                    return original_reference_prediction(current_policy, item, reference_predict)
                with preserve_rng():
                    last_dev = original.evaluate_dev(policy, dev, selection, pair_selection, reference_budget,
                        student_budget, arm='c1', predict=predict, decode=decode, reference_predict=dev_reference)
                checkpoint.save_training_state(output/f'update-{update:06d}', policy, optimizer, scheduler, sampler,
                    update=update, config=run_config, experiment_arm=arm, index_identity=train.identity, stage_identity=stage,
                    reference_budget=reference_budget, student_budget=student_budget)
                if update == recipe['updates']:
                    (output/'selected_checkpoint.json').write_text(json.dumps({'checkpoint': f'update-{update:06d}',
                        'update': update, 'selection': 'fixed terminal additional update', 'arm': 'c1',
                        'experiment_arm': arm, 'ancestor_updates': 2000}, indent=2), encoding='utf-8')
            metrics.update(dev=last_dev, reference_calls=reference_budget.report(),
                           student_calls=student_budget.report())
            print(json.dumps(metrics), flush=True); log.write(json.dumps(metrics)+'\n'); log.flush()
    return {'update': update, 'reference_calls': reference_budget.report(), 'student_calls': student_budget.report(),
            'selected_checkpoint': str(output/f'update-{update:06d}')}


def _argument_path(value):
    value = os.path.expandvars(os.path.expanduser(str(value)))
    if re.search(r'\$[A-Za-z_{]|%[^%]+%|<[^>]+>', value):
        raise ValueError('Unresolved042 path variable or placeholder')
    return Path(value).resolve()


def run(args):
    config = load_config(args.config); output = _argument_path(args.output_dir)
    if output.exists() and not args.resume:
        raise FileExistsError('New042 stage requires a new output, never an old041 run')
    if args.resume and _argument_path(args.resume).parent != output:
        raise ValueError('042 resume must keep original output directory and ledgers')
    inputs = [config[k] for k in ('index_dir', 'initial_adapter', 'benchmark_root', 'runtime')]
    inputs.append(args.config)
    for value in inputs:
        path = _argument_path(value)
        if output == path or output.is_relative_to(path) or path.is_relative_to(output):
            raise ValueError('042 training output overlaps immutable input/dependency')
    context = HashContext(progress=Progress('task042_existing_inputs'))
    train = StageDataset(config['index_dir'], 'train', context=context)
    dev = StageDataset(config['index_dir'], 'dev', context=context)
    stage = _stage(config, train.identity)  # all source roles/SHA before model construction
    from egrs.augmentation.dependencies import activate_core
    activate_core(config['benchmark_root'])
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
    runtime = load_runtime(config['runtime'])
    policy = OpenVLAOFTPolicy(runtime)
    try:
        return _run_loaded(args, config, train, dev, policy, stage_identity=stage)
    finally:
        policy.close()
