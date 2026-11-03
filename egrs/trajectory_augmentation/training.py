"""User-started task035 generated-trajectory mixed training, reusing030 OFT."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random

import numpy as np
import torch

from egrs.augmentation import training as base
from egrs.augmentation.adapter_identity import GENERATED_DATA_KIND


DOMAINS = ('10', 'normal')
DOMAIN_WEIGHTS = {'10': .7, 'normal': .3}
DOMAIN_SAMPLES = {'10': 12, 'normal': 4}


def _pools(rows, split):
    pools = {domain: {} for domain in DOMAINS}
    for index, row in enumerate(rows):
        mask = np.asarray(row['action_mask'], dtype=bool)
        if mask.shape != (8,) or not mask.any():
            raise ValueError(f'{split} window has no valid action chunk')
        domain = row['domain']
        if domain not in pools:
            raise ValueError(f'Unknown generated training domain: {domain}')
        pools[domain].setdefault(row['task_key'], {}).setdefault(row['parent_demo_id'], {}).setdefault(
            str(row['variant']), []).append(index)
    for domain in DOMAINS:
        if not pools[domain]:
            raise ValueError(f'{split} domain {domain} pool is empty; no fallback is permitted')
    return pools


class DomainBalancedSampler:
    """Independent domain -> task -> parent -> variant -> window draws."""
    def __init__(self, rows, seed=7):
        self.rows = rows
        self.pools = _pools(rows, 'train')
        self.rng = random.Random(seed)
        self.counts = Counter()
        self.hierarchy_counts = Counter()

    def draw_batch(self):
        indices = []
        for domain, count in DOMAIN_SAMPLES.items():
            for _ in range(count):
                tasks = self.pools[domain]
                task = self.rng.choice(sorted(tasks))
                parent = self.rng.choice(sorted(tasks[task]))
                variant = self.rng.choice(sorted(tasks[task][parent]))
                indices.append(self.rng.choice(tasks[task][parent][variant]))
                self.counts[domain] += 1
                self.hierarchy_counts[json.dumps([domain, task, parent, variant])] += 1
        return indices

    def report(self):
        total = sum(self.counts.values())
        return {'requested_domain_samples': DOMAIN_SAMPLES, 'loss_weights': DOMAIN_WEIGHTS,
                'draw_counts': dict(self.counts),
                'actual_domain_fraction': {d: self.counts[d]/total for d in DOMAINS} if total else {},
                'task_parent_variant_draw_counts': dict(self.hierarchy_counts)}

    def state_dict(self):
        return {'rng': self.rng.getstate(), 'counts': dict(self.counts),
                'hierarchy_counts': dict(self.hierarchy_counts)}

    def load_state_dict(self, state):
        self.rng.setstate(state['rng'])
        self.counts = Counter(state['counts'])
        self.hierarchy_counts = Counter(state['hierarchy_counts'])


def dev_indices(rows, limit=256, seed=7):
    """Fixed unique windows interleaved across task, parent and variant."""
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('Dev limit must be between1 and256 per domain')
    pools = _pools(rows, 'dev')
    rng = random.Random(seed)

    def interleave(pool):
        if isinstance(pool, list):
            values = list(pool)
            rng.shuffle(values)
            return values
        queues = [interleave(pool[key]) for key in sorted(pool)]
        # Interleave without replacement; exhaustion never duplicates a window.
        return [queue[offset] for offset in range(max(map(len, queues)))
                for queue in queues if offset < len(queue)]

    return {domain: interleave(pools[domain])[:limit] for domain in DOMAINS}


def batch_weights(items, domains):
    """Weight microbatch means by their domain's complete valid scalar count."""
    if len(items) != len(domains) or any(d not in DOMAINS for d in domains):
        raise ValueError('Invalid domain batch')
    counts = [int(np.asarray(item['action_mask'], dtype=bool).sum()) * 7 for item in items]
    totals = {d: sum(n for n, domain in zip(counts, domains) if domain == d) for d in DOMAINS}
    if any(count <= 0 for count in counts) or any(total <= 0 for total in totals.values()):
        raise ValueError('Each domain requires valid action scalars; no fallback is permitted')
    weights = [DOMAIN_WEIGHTS[d] * count/totals[d] for d, count in zip(domains, counts)]
    return weights, {'sample_counts': dict(Counter(domains)), 'valid_scalars': totals,
                     'valid_scalar_fraction': {d: totals[d]/sum(totals.values()) for d in DOMAINS},
                     'loss_weights': DOMAIN_WEIGHTS}


class MixedRecipe:
    def __init__(self, dev_rows):
        self.dev_selection = dev_indices(dev_rows)

    def batch(self, train, sampler):
        indices = sampler.draw_batch()
        items = [train[index] for index in indices]
        scales, metrics = batch_weights(items, [train.rows[index]['domain'] for index in indices])
        return items, scales, metrics

    def evaluate_dev(self, policy, dataset):
        losses = {domain: base.evaluate_dev(policy, (dataset[index] for index in indices))
                  for domain, indices in self.dev_selection.items()}
        return {'domain_l1': losses,
                'weighted_l1': sum(DOMAIN_WEIGHTS[d]*losses[d] for d in DOMAINS),
                'windows': {d: len(indices) for d, indices in self.dev_selection.items()}}

    def adapter_metadata(self, update, run_config):
        return {'recipe': 'robot_rewind_mix', 'data_kind': GENERATED_DATA_KIND,
                'update': update, 'final_update': 1000, 'export_identity': run_config['export_identity']}


def validate_config(config):
    expected = {'name': 'robot_rewind_mix', 'data_kind': GENERATED_DATA_KIND,
        'domain_weights': DOMAIN_WEIGHTS, 'domain_samples': DOMAIN_SAMPLES,
        'photometric_probability': 0., 'seed': 7, 'updates': 1000, 'save_every': 250,
        'learning_rate': 2e-5, 'warmup_updates': 50, 'gradient_accumulation': 16,
        'microbatch': 1, 'precision': 'bf16', 'gradient_checkpointing': True,
        'dev_limit_per_domain': 256, 'checkpoint_selection': 'fixed_terminal_update'}
    if config != expected:
        raise ValueError('Configuration differs from the fixed task035 mixed training preset')


def run(args):
    from .data import GeneratedTrajectoryDataset
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate_config(config)
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise ValueError('Fresh run requires an empty output directory')
    train = GeneratedTrajectoryDataset(args.export_dir, split='train', domains=list(DOMAINS))
    dev = GeneratedTrajectoryDataset(args.export_dir, split='dev', domains=list(DOMAINS))
    if any(dataset.report.get('data_kind') != GENERATED_DATA_KIND for dataset in (train, dev)):
        raise ValueError('Training requires the task035 generated trajectories data kind')
    sampler = DomainBalancedSampler(train.rows, seed=config['seed'])
    recipe = MixedRecipe(dev.rows)  # All four pools validated before model loading.
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    policy = base.load_policy(args.benchmark_root, args.oft_root, args.checkpoint)
    try:
        base._run_loaded(args, config, train, dev, sampler, output, policy, recipe=recipe)
    finally:
        policy.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('config', 'export-dir', 'output-dir', 'benchmark-root', 'oft-root', 'checkpoint'):
        parser.add_argument('--'+flag, required=True)
    parser.add_argument('--resume', help='Local task035 update directory with complete adapter/training state')
    run(parser.parse_args(argv))


if __name__ == '__main__':
    main()
