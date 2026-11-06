"""Fixed 037-v2 C0/C1 losses and single-base 1000-update training."""
from collections import Counter
from contextlib import contextmanager, nullcontext
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch.nn import functional as F

from egrs.augmentation import training as base
from egrs.augmentation.adapter_identity import RETENTION_STATS_SHA
from .reference import ReferenceBudget, StudentBudget, policy_modules, reference_prediction
from .sampling import TaskControlSampler, ThreePoolSampler, batch_weights, dev_indices, dev_pair_indices, POOLS, WEIGHTS, SAMPLES


PRESET = {'name': 'task_control_factorization', 'data_kind': 'task038-task-control-data-v1',
    'pool_weights': WEIGHTS, 'pool_samples': SAMPLES,
    'reference_prefix_samples': {'fresh': 2, 'raw': 2}, 'prefix': 'max(1,ceil(T_obs/3))',
    'photometric_probability': 0., 'seed': 7, 'updates': 1000, 'save_every': 250,
    'learning_rate': 2e-5, 'warmup_updates': 50, 'gradient_accumulation': 22, 'microbatch': 1,
    'precision': 'bf16', 'gradient_checkpointing': True, 'dev_ten_limit': 256,
    'dev_reference_per_pool': 128, 'dev_prefix_per_pool': 64, 'dev_pair_limit': 64,
    'reference_budget': 9024, 'student_budget': 24560, 'pairs_per_update': 1,
    'checkpoint_selection': 'fixed_terminal_update'}


def validate_config(config):
    if config != PRESET:
        raise ValueError('Configuration differs from the fixed task038 training preset')


def count_weights(labels):
    for label in labels:
        if label is not None and (type(label) is not int or not 0 <= label <= 2):
            raise ValueError('Count label must be 0/1/2 or missing')
    counts = Counter(label for label in labels if label is not None)
    return [1. / (len(counts) * counts[label]) if label is not None else 0. for label in labels]


def count_loss(logits, labels):
    scales = count_weights(labels)
    if logits.shape != (len(labels), 3):
        raise ValueError('Count logits must have one row and three classes per observation')
    targets = torch.tensor([0 if x is None else x for x in labels], device=logits.device)
    weights = torch.tensor(scales, device=logits.device)
    return (F.cross_entropy(logits.float(), targets, reduction='none') * weights).sum()


def _l1(prediction, item):
    target = torch.as_tensor(item['actions'], device=prediction.device).reshape(1, 8, 7)
    mask = torch.as_tensor(item['action_mask'], device=prediction.device, dtype=torch.bool).reshape(1, 8)
    return base.masked_l1(prediction, target, mask)


def pair_losses(policy, u, v, u_item, v_item, *, arm, decode):
    if arm not in ('c0', 'c1'):
        raise ValueError('Unknown task-control arm')
    own = .5 * (_l1(u.actions, u_item) + _l1(v.actions, v_item))
    zero = own.new_zeros(())
    swap = .5 * (_l1(decode(policy, u, z=v.z), u_item) + _l1(decode(policy, v, z=u.z), v_item)) if arm == 'c1' else zero
    align = (F.normalize(u.z.float(), dim=-1, eps=1e-6) - F.normalize(v.z.float(), dim=-1, eps=1e-6)).square().mean()
    return {'self': own, 'swap': swap, 'align': align}


def total_loss(main, count, losses, *, arm):
    if arm == 'c0':
        return main + .1 * count + .1 * losses['self']
    if arm == 'c1':
        return main + .1 * count + .05 * (losses['self'] + losses['swap']) + .01 * losses['align']
    raise ValueError('Unknown task-control arm')


def _sensors(item):
    return {key: item[key] for key in ('images', 'instruction', 'proprio')}


def _amp(policy):
    return torch.autocast('cuda', dtype=torch.bfloat16) if next(policy.model.parameters()).is_cuda else nullcontext()


@contextmanager
def _student_eval(policy):
    flags = [(m, m.training) for m in policy_modules(policy)]
    try:
        for module, _ in flags:
            module.training = False
        with torch.no_grad():
            yield
    finally:
        for module, training in flags:
            module.training = training


def _reference(policy, item, split, budget, predict):
    budget.consume(split)
    with _amp(policy):
        return reference_prediction(policy, _sensors(item), predict=predict)


def _student(policy, item, split, budget, predict):
    budget.consume(split)
    with _amp(policy):
        return predict(policy, _sensors(item))


def _count_term(logits, label, weight):
    if not weight:
        return logits.sum() * 0.
    return weight * F.cross_entropy(logits.float(), torch.tensor([label], device=logits.device))


def _student_train_mode(policy):
    policy.model.train()
    for module in (policy.model.vision_backbone, policy.action_head, policy.proprio_projector):
        module.eval()
    if isinstance(getattr(policy.model, 'projector', None), torch.nn.Module):
        policy.model.projector.eval()


def evaluate_dev(policy, dataset, selection, pair_selection, reference_budget, student_budget,
                 *, arm, predict, decode, reference_predict=None):
    selected = {'ten': selection['ten'], **{p: selection[p]['prefix'] + selection[p]['all']
                                           for p in ('fresh', 'raw')}}
    pool_sums = {pool: 0. for pool in POOLS}
    pool_counts = {pool: 0 for pool in POOLS}
    class_correct = Counter()
    class_counts = Counter()
    def record_count(encoded, item, pool=None):
        label = None if pool == 'raw' else item.get('count_label')
        if label is not None:
            class_counts[label] += 1
            class_correct[label] += int(encoded.count_logits.argmax(-1).item() == label)
    diagnostic = Counter()
    with _student_eval(policy):
        for pool in POOLS:
            for index in selected[pool]:
                item = dataset[index]
                target = torch.as_tensor(item['actions']).reshape(1, 8, 7) if pool == 'ten' else _reference(
                    policy, item, 'dev', reference_budget, reference_predict)
                encoded = _student(policy, item, 'dev', student_budget, predict)
                target = target.to(encoded.actions.device)
                mask = torch.as_tensor(item['action_mask'] if pool == 'ten' else [True] * 8,
                    device=encoded.actions.device, dtype=torch.bool).reshape(1, 8, 1).expand_as(encoded.actions)
                pool_sums[pool] += (encoded.actions.float() - target.float()).abs().masked_select(mask).sum().item()
                pool_counts[pool] += int(mask.sum())
                record_count(encoded, item, pool)
        for index in pair_selection:
            u_item, v_item = dataset.get_pair(index)
            u = _student(policy, u_item, 'dev', student_budget, predict)
            v = _student(policy, v_item, 'dev', student_budget, predict)
            # Both arms receive the same diagnostics from cached encodings only.
            with _amp(policy):
                losses = pair_losses(policy, u, v, u_item, v_item, arm='c1', decode=decode)
                zero_delta = .5 * ((decode(policy, u, z=torch.zeros_like(u.z)) - u.actions).float().abs().mean()
                    + (decode(policy, v, z=torch.zeros_like(v.z)) - v.actions).float().abs().mean())
            for key, value in losses.items():
                diagnostic[key] += value.item()
            diagnostic['z_zero_action_delta_l1'] += zero_delta.item()
            diagnostic['z_distance_l2'] += (u.z.float() - v.z.float()).norm().item()
            record_count(u, u_item)
            record_count(v, v_item)
    pools = {p: pool_sums[p] / pool_counts[p] for p in POOLS}
    size = len(pair_selection)
    return {'pool_l1': pools, 'weighted_l1': sum(WEIGHTS[p] * pools[p] for p in POOLS),
        'ordinary_observations': sum(map(len, selected.values())), 'pair_count': size,
        'paired_diagnostics': {key: diagnostic[key] / size if size else None for key in
            ('self', 'swap', 'align', 'z_zero_action_delta_l1', 'z_distance_l2')},
        'count_class_coverage': {str(k): class_counts[k] for k in (0, 1, 2)},
        'count_accuracy_by_class': {str(k): class_correct[k] / class_counts[k] if class_counts[k] else None
                                    for k in (0, 1, 2)},
        'count_accuracy': sum(class_correct.values()) / sum(class_counts.values()) if class_counts else None,
        'reference_time_bins': {p: {b: len(selection[p][b]) for b in ('prefix', 'all')}
                                for p in ('fresh', 'raw')}}


def _run_loaded(args, config, train, dev, policy, *, predict=None, decode=None, reference_predict=None):
    """Private loaded-policy seam permits synthetic CPU tests with short loops."""
    from . import checkpoint
    from .oft import install, prediction, decode as decode_actions
    predict = prediction if predict is None else predict
    decode = decode_actions if decode is None else decode
    arm = args.arm
    if arm not in ('c0', 'c1'):
        raise ValueError('Unknown task-control arm')
    output = Path(args.output_dir).resolve()
    if args.resume and Path(args.resume).resolve().parent != output:
        raise ValueError('Task038 resume must keep the original output directory and budget ledgers')
    if train.identity != dev.identity:
        raise ValueError('Train/dev task038 index identity differs')
    for dataset in (train, dev):
        dataset.validate_normalization(policy.model.norm_stats, policy.cfg.unnorm_key,
                                       policy.metadata['dataset_statistics_sha256'])
    if policy.metadata['dataset_statistics_sha256'] != RETENTION_STATS_SHA or policy.cfg.unnorm_key != 'libero_10_no_noops':
        raise ValueError('Task038 requires the original fixed SOG10 statistics')
    sampler = TaskControlSampler(train.rows, train.pairs, seed=config['seed'])
    selection = dev_indices(dev.rows, seed=config['seed'])
    pair_selection = dev_pair_indices(dev.pairs, seed=config['seed'])
    output.mkdir(parents=True, exist_ok=True)
    reference_budget = ReferenceBudget(output / 'reference_budget.json')
    student_budget = StudentBudget(output / 'student_budget.json')
    # Reset initialization consistently for C0/C1; neither consumes the sampler RNG.
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    install(policy)
    policy.model.language_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    policy.model.language_model.config.use_cache = False
    parameters = [p for p in policy.model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=config['learning_rate'])
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer,
        lambda step: min(1., (step + 1) / max(1, config['warmup_updates'])))
    run_config = dict(config, arm=arm, index_identity=train.identity)
    update = 0
    if args.resume:
        update = checkpoint.load_training_state(args.resume, policy, optimizer, scheduler, sampler,
            config=run_config, arm=arm, index_identity=train.identity,
            reference_budget=reference_budget, student_budget=student_budget)
    elif reference_budget.report()['total'] or student_budget.report()['total']:
        raise ValueError('Fresh task038 run cannot reset existing spent observation budgets')
    if update >= config['updates']:
        raise ValueError('This training run is already complete; no new updates required')
    (output / 'run_config.json').write_text(json.dumps(run_config, indent=2), encoding='utf-8')
    started = time.monotonic()
    start_update = update
    last_dev = None
    with (output / 'metrics.jsonl').open('a', encoding='utf-8') as log:
        while update < config['updates']:
            _student_train_mode(policy)
            optimizer.zero_grad(set_to_none=True)
            indices, pair_index = sampler.draw_batch()
            items = [train[i] for i in indices]
            pools = [train.rows[i]['pool'] for i in indices]
            scales, batch = batch_weights(items, pools)
            u_item, v_item = train.get_pair(pair_index)
            labels = [item.get('count_label') if pool != 'raw' else None for item, pool in zip(items, pools)]
            labels += [u_item.get('count_label'), v_item.get('count_label')]
            count_scales = count_weights(labels)
            # All eight original-base references precede all 22 student graphs.
            targets = [torch.as_tensor(item['actions']).reshape(1, 8, 7) if pool == 'ten' else
                       _reference(policy, item, 'train', reference_budget, reference_predict)
                       for item, pool in zip(items, pools)]
            pool_l1 = {pool: 0. for pool in POOLS}
            count_value = 0.
            # Main graphs can be released individually: class-normalization
            # weights were computed from the complete 22-observation label list.
            for offset, (item, pool, target, scale) in enumerate(zip(items, pools, targets, scales)):
                encoded = _student(policy, item, 'train', student_budget, predict)
                with _amp(policy):
                    loss = base.masked_l1(encoded.actions, target.to(encoded.actions.device),
                        torch.as_tensor(item['action_mask'] if pool == 'ten' else [True] * 8,
                            device=encoded.actions.device).reshape(1, 8))
                    count = _count_term(encoded.count_logits, labels[offset], count_scales[offset])
                    objective = loss * scale + .1 * count
                objective.backward()
                pool_l1[pool] += loss.detach().item() * scale / WEIGHTS[pool]
                count_value += count.detach().item()
            # Keep these two graphs alive together. Cross-z gradients reach both
            # sides; receiver H/proprio/action/mask are never exchanged.
            u = _student(policy, u_item, 'train', student_budget, predict)
            v = _student(policy, v_item, 'train', student_budget, predict)
            with _amp(policy):
                losses = pair_losses(policy, u, v, u_item, v_item, arm=arm, decode=decode)
                pair_count = (_count_term(u.count_logits, labels[-2], count_scales[-2])
                              + _count_term(v.count_logits, labels[-1], count_scales[-1]))
                objective = total_loss(u.actions.new_zeros(()), pair_count, losses, arm=arm)
            objective.backward()
            count_value += pair_count.detach().item()
            optimizer.step()
            scheduler.step()
            update += 1
            elapsed = time.monotonic() - started
            metrics = {'update': update, 'arm': arm, 'completion_percent': 100 * update / config['updates'],
                'pool_l1': pool_l1, 'weighted_l1': sum(WEIGHTS[p] * pool_l1[p] for p in POOLS),
                'count': count_value, **{key: value.detach().item() for key, value in losses.items()},
                'count_class_coverage': {str(k): labels.count(k) for k in (0, 1, 2)},
                'count_missing': labels.count(None), 'elapsed_seconds': elapsed,
                'eta_seconds': elapsed / max(1, update - start_update) * (config['updates'] - update),
                'learning_rate': scheduler.get_last_lr()[0], 'batch': batch, 'sampling': sampler.report(),
                'cuda_memory_allocated': torch.cuda.memory_allocated() if torch.cuda.is_initialized() else 0,
                'cuda_peak_memory_allocated': torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0}
            if update % config['save_every'] == 0 or update == config['updates']:
                last_dev = evaluate_dev(policy, dev, selection, pair_selection, reference_budget, student_budget,
                    arm=arm, predict=predict, decode=decode, reference_predict=reference_predict)
                directory = output / f'update-{update:06d}'
                checkpoint.save_training_state(directory, policy, optimizer, scheduler, sampler, update=update,
                    config=run_config, arm=arm, index_identity=train.identity,
                    reference_budget=reference_budget, student_budget=student_budget)
                if update == config['updates']:
                    (output / 'selected_checkpoint.json').write_text(json.dumps({'checkpoint': directory.name,
                        'update': update, 'selection': 'fixed terminal update', 'arm': arm,
                        'recipe': PRESET['name']}, indent=2), encoding='utf-8')
            metrics['dev'] = last_dev
            metrics['reference_calls'] = reference_budget.report()
            metrics['student_calls'] = student_budget.report()
            print(json.dumps(metrics), flush=True)
            log.write(json.dumps(metrics) + '\n')
            log.flush()
    return {'update': update, 'reference_calls': reference_budget.report(), 'student_calls': student_budget.report(),
            'selected_checkpoint': str(output / f'update-{update:06d}')}


def run(args):
    from .data import TaskControlDataset
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate_config(config)
    if args.arm not in ('c0', 'c1'):
        raise ValueError('Unknown task-control arm')
    output = Path(args.output_dir).resolve()
    if args.resume and Path(args.resume).resolve().parent != output:
        raise ValueError('Task038 resume must keep the original output directory and budget ledgers')
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise ValueError('Fresh run requires an empty output directory')
    for value in (args.index_dir, args.benchmark_root, args.runtime):
        root = Path(value).resolve()
        if output == root or root in output.parents or output in root.parents:
            raise ValueError('Training output overlaps immutable input/dependency')
    train = TaskControlDataset(args.index_dir, split='train')
    dev = TaskControlDataset(args.index_dir, split='dev')
    if any(dataset.report.get('data_kind') != PRESET['data_kind'] for dataset in (train, dev)):
        raise ValueError('Task038 training requires the versioned task-control data kind')
    TaskControlSampler(train.rows, train.pairs, seed=config['seed'])
    dev_indices(dev.rows, seed=config['seed'])
    if args.resume:
        from .adapter import read_adapter_identity
        identity = read_adapter_identity(args.resume)
        if identity['arm'] != args.arm or identity['index_identity'] != train.identity:
            raise ValueError('Resume arm or task038 index identity differs')
    from egrs.augmentation.dependencies import activate_core
    activate_core(args.benchmark_root)
    from benchmark.remaining_goals.headless.nine_planning import load_runtime
    from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
    runtime = load_runtime(args.runtime)
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    policy = OpenVLAOFTPolicy(runtime)
    try:
        return _run_loaded(args, config, train, dev, policy)
    finally:
        policy.close()
