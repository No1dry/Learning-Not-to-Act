"""Unchanged 036 three-pool draws plus an independent hierarchical pair stream."""
from collections import Counter
import random

from egrs.retention.training import (ThreePoolSampler, batch_weights, dev_indices,
                                     POOLS, SAMPLES, WEIGHTS)


def pair_hierarchy(pairs):
    result = {}
    for index, pair in enumerate(pairs):
        result.setdefault(pair['task_key'], {}).setdefault(pair['source_group'], {}).setdefault(
            str(pair['variant']), []).append(index)
    return result


class PairSampler:
    def __init__(self, pairs, seed=7):
        self.hierarchy = pair_hierarchy(pairs)
        if not self.hierarchy:
            raise ValueError('Training has zero valid pairs; no fallback is permitted')
        self.rng = random.Random(seed)
        self.counts = Counter()
        self.draws = 0

    def draw(self):
        task = self.rng.choice(sorted(self.hierarchy))
        parent = self.rng.choice(sorted(self.hierarchy[task]))
        variant = self.rng.choice(sorted(self.hierarchy[task][parent]))
        result = self.rng.choice(self.hierarchy[task][parent][variant])
        self.counts[str(result)] += 1
        self.draws += 1
        return result

    def state_dict(self):
        return {'rng': self.rng.getstate(), 'counts': dict(self.counts), 'draws': self.draws}

    def load_state_dict(self, state):
        self.rng.setstate(state['rng'])
        self.counts = Counter(state['counts'])
        self.draws = state['draws']


class TaskControlSampler:
    def __init__(self, rows, pairs, seed=7):
        self.main = ThreePoolSampler(rows, seed=seed)
        self.pair = PairSampler(pairs, seed=seed)

    def draw_batch(self):
        return self.main.draw_batch(), self.pair.draw()

    def report(self):
        return dict(self.main.report(), pair_draws=self.pair.draws,
                    pair_draw_counts=dict(self.pair.counts))

    def state_dict(self):
        return {'main': self.main.state_dict(), 'pair': self.pair.state_dict()}

    def load_state_dict(self, state):
        self.main.load_state_dict(state['main'])
        self.pair.load_state_dict(state['pair'])


def dev_pair_indices(pairs, seed=7):
    """Deterministic without replacement, interleaved task -> parent -> variant."""
    rng = random.Random(seed)
    def interleave(node):
        if isinstance(node, list):
            values = list(node)
            rng.shuffle(values)
            return values
        queues = [interleave(node[key]) for key in sorted(node)]
        return [queue[offset] for offset in range(max(map(len, queues), default=0))
                for queue in queues if offset < len(queue)]
    return interleave(pair_hierarchy(pairs))[:64]
