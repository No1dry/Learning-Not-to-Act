"""User-started task030 v2 training; never imported to start an experiment."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import subprocess
import time

import numpy as np
from PIL import Image, ImageEnhance
import torch

from .oft import (BASE_SOURCE, OFT_REVISION, inject_language_lora, save_adapter,
                  restore_adapter_weights, read_adapter_identity, training_prediction, sha256)


def masked_l1(prediction, target, mask):
    if prediction.shape != target.shape:
        raise ValueError('Prediction/target shape mismatch')
    mask = torch.as_tensor(mask, device=prediction.device, dtype=torch.bool)
    if mask.ndim == prediction.ndim - 1:
        mask = mask.unsqueeze(-1).expand_as(prediction)
    if mask.shape != prediction.shape or not mask.any():
        raise ValueError('Loss requires valid action scalars')
    return (prediction.float() - target.float()).abs().masked_select(mask).mean()


class BalancedSampler:
    """View -> task -> source -> progress-stage -> row, with RAW fallback.

    Missing view weight transfers to RAW, rather than fabricating augmented
    examples. Only PROGRESS draws balance actual pending-goal stages.
    """
    def __init__(self, rows, weights, seed=7):
        self.rows, self.weights = rows, weights
        self.rng = random.Random(seed)
        self.pools = {}
        self.counts = Counter()
        for index, row in enumerate(rows):
            view = row['view']
            self.pools.setdefault(view, {}).setdefault(row['task_key'], {}).setdefault(row['source_id'], {}).setdefault(
                str(row.get('progress_stage', 'all')) if view == 'PROGRESS' else 'all', []).append(index)
        if not self.pools.get('RAW'):
            raise ValueError('A nonempty RAW training pool is required')
        if any(v < 0 for v in weights.values()) or abs(sum(weights.values()) - 1) > 1e-8:
            raise ValueError('View weights must sum to one')
        self.effective = {v: w for v, w in weights.items() if self.pools.get(v) and w > 0}
        missing = sum(w for v, w in weights.items() if not self.pools.get(v))
        self.effective['RAW'] = self.effective.get('RAW', 0) + missing
        self.expected_actual = Counter()
        raw = self.pools['RAW']
        for task, sources in raw.items():
            for source in sources:
                probability = 1 / len(raw) / len(sources)
                for view, weight in self.effective.items():
                    actual = view if self.pools.get(view, {}).get(task, {}).get(source) else 'RAW'
                    self.expected_actual[actual] += probability * weight

    def _choose(self, mapping):
        return mapping[self.rng.choice(sorted(mapping))]

    def draw(self):
        views = sorted(self.effective)
        view = self.rng.choices(views, [self.effective[v] for v in views])[0]
        # Draw task/source from the common RAW universe in both conditions.
        # A source without trustworthy evidence keeps its complete instruction.
        task = self.rng.choice(sorted(self.pools['RAW']))
        source = self.rng.choice(sorted(self.pools['RAW'][task]))
        stages = self.pools.get(view, {}).get(task, {}).get(source)
        if not stages:
            view = 'RAW'
            stages = self.pools['RAW'][task][source]
        rows = self._choose(stages)
        index = self.rng.choice(rows)
        self.counts[view] += 1
        return index

    def report(self):
        total = sum(self.counts.values())
        return {'requested_views': self.weights, 'effective_view_probabilities': dict(self.expected_actual),
            'actual_views': {v: n / total for v, n in sorted(self.counts.items())} if total else {},
            'draw_counts': dict(self.counts),
            'unavailable_views': sorted(v for v, w in self.weights.items() if w and not self.pools.get(v)),
            'augmentation_available': bool(self.pools.get('PROGRESS') or self.pools.get('ATOMIC'))}

    def state_dict(self):
        return {'rng': self.rng.getstate(), 'counts': dict(self.counts)}

    def load_state_dict(self, state):
        self.rng.setstate(state['rng'])
        self.counts = Counter(state['counts'])


def photometric(images, rng, probability=.5):
    if rng.random() >= probability:
        return images
    brightness, contrast = rng.uniform(.9, 1.1), rng.uniform(.9, 1.1)
    return [np.asarray(ImageEnhance.Contrast(ImageEnhance.Brightness(Image.fromarray(image)).enhance(
        brightness)).enhance(contrast)).copy() for image in images]


def save_training_state(directory, policy, optimizer, scheduler, sampler, update, best_dev, config,
                        adapter_metadata=None):
    directory = Path(directory)
    identity = save_adapter(policy, directory, group=config['name'], metadata=adapter_metadata)
    state = {'update': update, 'best_dev': best_dev, 'config': config,
        'optimizer': optimizer.state_dict(), 'scheduler': scheduler.state_dict(),
        'sampler': sampler.state_dict(), 'python_rng': random.getstate(),
        'numpy_rng': np.random.get_state(), 'torch_rng': torch.get_rng_state(),
        'cuda_rng': torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None}
    torch.save(state, directory / 'training_state.pt')
    (directory / 'training_state.sha256').write_text(sha256(directory / 'training_state.pt') + '\n', encoding='ascii')
    return identity


def load_training_state(directory, policy, optimizer, scheduler, sampler, config):
    directory = Path(directory)
    identity = read_adapter_identity(directory)
    if identity['base_lineage'] != {key: policy.metadata.get(key) for key in identity['base_lineage']}:
        raise ValueError('Resume base lineage mismatch')
    if sha256(directory / 'training_state.pt') != (directory / 'training_state.sha256').read_text().strip():
        raise ValueError('Resume state byte hash mismatch')
    # Local user-created state includes Python/NumPy RNG tuples; never load untrusted state files.
    state = torch.load(directory / 'training_state.pt', map_location='cpu', weights_only=False)
    if state['config'] != config:
        raise ValueError('Resume configuration or exported dataset identity changed')
    if identity['group'] != config['name']:
        raise ValueError('Resume adapter recipe differs from training configuration')
    if identity['group'] == 'robot_rewind_mix' and (
        identity['update'] != state['update'] or identity['export_identity'] != config.get('export_identity')
        or identity['recipe'] != config.get('name') or identity['data_kind'] != config.get('data_kind')):
        raise ValueError('Resume task035 adapter recipe/update/export identity changed')
    restore_adapter_weights(policy.model, directory, identity)
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    sampler.load_state_dict(state['sampler'])
    random.setstate(state['python_rng'])
    np.random.set_state(state['numpy_rng'])
    torch.set_rng_state(state['torch_rng'])
    if state['cuda_rng'] is not None:
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['update'], state['best_dev']


def load_policy(benchmark_root, oft_root, checkpoint):
    from .dependencies import activate_core
    activate_core(benchmark_root)
    revision = subprocess.check_output(['git', '-C', str(oft_root), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != OFT_REVISION:
        raise ValueError('Official OFT checkout must use the exact pinned revision')
    if subprocess.run(['git', '-C', str(oft_root), 'diff', '--quiet', 'HEAD', '--', '*.py']).returncode:
        raise ValueError('Official OFT Python source has local modifications')
    from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
    return OpenVLAOFTPolicy({'model_id': 'openvla_oft', 'suite': 'libero_10',
        'checkpoint_source': BASE_SOURCE,
        'policy_factory': 'benchmark.remaining_goals.adapters.openvla_oft:make_policy',
        'adapter_options': {'repo_path': str(oft_root), 'repo_revision': OFT_REVISION,
            'checkpoint': str(checkpoint), 'suite': 'libero_10', 'seed': 7,
            'center_crop': True, 'load_in_8bit': False, 'load_in_4bit': False}})


def evaluate_dev(policy, dataset):
    policy.model.eval()
    absolute_sum, valid_scalars = 0., 0
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        for item in dataset:
            prediction = training_prediction(policy, item)
            target = torch.as_tensor(item['actions'], device=prediction.device).unsqueeze(0)
            mask = torch.as_tensor(item['action_mask'], device=prediction.device).reshape(1, 8, 1).expand_as(prediction)
            absolute_sum += (prediction.float() - target.float()).abs().masked_select(mask).sum().item()
            valid_scalars += int(mask.sum())
    if not valid_scalars:
        raise ValueError('RAW dev has no valid action scalars')
    return absolute_sum / valid_scalars


def validate_config(config):
    required = {'name', 'view_weights', 'photometric_probability', 'seed', 'updates', 'save_every',
        'learning_rate', 'warmup_updates', 'gradient_accumulation', 'microbatch', 'precision', 'gradient_checkpointing'}
    if set(config) != required:
        raise ValueError('Unknown or missing configuration fields')
    expected = {'raw_control': ({'RAW':1., 'PROGRESS':0., 'ATOMIC':0.}, 0.),
                'progress_aug': ({'RAW':.5, 'PROGRESS':.25, 'ATOMIC':.25}, .5)}
    if config['name'] not in expected:
        raise ValueError('Unknown official training preset')
    weights, photometric_probability = expected[config['name']]
    fixed = {'view_weights': weights, 'photometric_probability': photometric_probability,
        'seed':7, 'updates':1000, 'save_every':250, 'learning_rate':2e-5, 'warmup_updates':50,
        'gradient_accumulation':16, 'microbatch':1, 'precision':'bf16', 'gradient_checkpointing':True}
    if any(config[name] != value for name,value in fixed.items()):
        raise ValueError('Configuration differs from the fixed task030 v2 training preset')


def run(args):
    from .data import AugmentationDataset
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate_config(config)
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise ValueError('Fresh run requires an empty output directory')
    train = AugmentationDataset(args.export_dir, split='train', views=[v for v,w in config['view_weights'].items() if w])
    dev = AugmentationDataset(args.export_dir, split='dev', views=['RAW'])
    if not len(dev):
        raise ValueError('The shared full-instruction RAW dev pool is empty')
    sampler = BalancedSampler(train.rows, config['view_weights'], config['seed'])
    if config['name'] == 'progress_aug' and not sampler.report()['augmentation_available']:
        raise ValueError('PROGRESS and ATOMIC pools are empty: progress augmentation is unavailable; supply trustworthy evidence before this run')
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    policy = load_policy(args.benchmark_root, args.oft_root, args.checkpoint)
    try:
        _run_loaded(args, config, train, dev, sampler, output, policy)
    finally:
        policy.close()


def _run_loaded(args, config, train, dev, sampler, output, policy, recipe=None):
    # Binding compares the export's declared original normalization to actual loaded stats.
    train.validate_normalization(policy.model.norm_stats, policy.cfg.unnorm_key,
                                 policy.metadata['dataset_statistics_sha256'])
    dev.validate_normalization(policy.model.norm_stats, policy.cfg.unnorm_key,
                               policy.metadata['dataset_statistics_sha256'])
    inject_language_lora(policy)
    policy.model.language_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    policy.model.language_model.config.use_cache = False
    parameters = [value for value in policy.model.parameters() if value.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=config['learning_rate'])
    warmup = config['warmup_updates']
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: min(1., (step + 1) / max(1, warmup)))
    run_config = dict(config, export_identity={name: sha256(Path(args.export_dir) / name)
        for name in ('sources.json', 'windows.jsonl', 'report.json')})
    update, best_dev = 0, float('inf')
    if args.resume:
        update, best_dev = load_training_state(args.resume, policy, optimizer, scheduler, sampler, run_config)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'run_config.json').write_text(json.dumps(run_config, indent=2), encoding='utf-8')
    started = time.monotonic()
    with (output / 'metrics.jsonl').open('a', encoding='utf-8') as log:
        while update < config['updates']:
            policy.model.train()
            # Frozen perception/head modules stay deterministic while language checkpointing trains.
            policy.model.vision_backbone.eval()
            policy.action_head.eval()
            policy.proprio_projector.eval()
            optimizer.zero_grad(set_to_none=True)
            loss_total = 0.
            if recipe is None:
                items = [train[sampler.draw()] for _ in range(config['gradient_accumulation'])]
            else:
                items, batch_scales, batch_metrics = recipe.batch(train, sampler)
            # Normalize over the complete effective batch's real action scalars;
            # shorter boundary chunks cannot gain extra weight via microbatch means.
            counts = [int(np.asarray(item['action_mask']).sum()) * 7 for item in items]
            denominator = sum(counts)
            if not denominator:
                raise ValueError('Effective training batch has no valid action scalars')
            if recipe is None:
                batch_scales = [count / denominator for count in counts]
            for item, scale in zip(items, batch_scales):
                images = photometric(item['images'], random, config['photometric_probability'])
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    prediction = training_prediction(policy, item, images)
                    target = torch.as_tensor(item['actions'], device=prediction.device).unsqueeze(0)
                    mask = torch.as_tensor(item['action_mask'], device=prediction.device).unsqueeze(0)
                    loss = masked_l1(prediction, target, mask)
                (loss * scale).backward()
                loss_total += loss.detach().item() * scale
            optimizer.step()
            scheduler.step()
            update += 1
            metrics = {'update': update, 'completion_percent': 100 * update / config['updates'],
                'loss': loss_total, 'learning_rate': scheduler.get_last_lr()[0], 'elapsed_seconds': time.monotonic() - started}
            if update % config['save_every'] == 0 or update == config['updates']:
                dev_metrics = recipe.evaluate_dev(policy, dev) if recipe else None
                dev_l1 = dev_metrics['weighted_l1'] if recipe else evaluate_dev(policy, dev)
                selected = update == config['updates'] if recipe else dev_l1 < best_dev
                best_dev = min(best_dev, dev_l1)
                directory = output / f'update-{update:06d}'
                save_training_state(directory, policy, optimizer, scheduler, sampler, update, best_dev, run_config,
                                    adapter_metadata=recipe.adapter_metadata(update, run_config) if recipe else None)
                if recipe:
                    metrics.update(dev=dev_metrics, selected=selected)
                    if selected:
                        (output / 'selected_checkpoint.json').write_text(json.dumps({'checkpoint': directory.name,
                            'update': update, 'selection': 'fixed terminal update',
                            'recipe': config['name']}, indent=2), encoding='utf-8')
                else:
                    metrics.update(dev_raw_l1=dev_l1, best_dev_raw_l1=best_dev, selected=selected)
                if selected and recipe is None:
                    (output / 'best_checkpoint.json').write_text(json.dumps({'checkpoint': directory.name,
                        'update': update, 'dev_raw_l1': dev_l1, 'selection': 'minimum valid-scalar L1 on shared RAW dev'}, indent=2), encoding='utf-8')
            metrics['sampling'] = sampler.report()
            if recipe:
                metrics['batch'] = batch_metrics
            print(json.dumps(metrics), flush=True)
            log.write(json.dumps(metrics) + '\n')
            log.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('config', 'export-dir', 'output-dir', 'benchmark-root', 'oft-root', 'checkpoint'):
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--resume', help='Local task030 update directory containing adapter and complete training state')
    args = parser.parse_args(argv)
    run(args)


if __name__ == '__main__':
    main()
