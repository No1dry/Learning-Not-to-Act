"""Task058 quota sampler: 9 main ten draws + 3 auxiliary ten draws per update."""
from __future__ import annotations

import json
import random
from collections import Counter

from egrs.retention.training import POOLS, SAMPLES, ThreePoolSampler


class AuxThreePoolSampler(ThreePoolSampler):
    def __init__(self, main_rows, aux_rows, seed=7, aux_quota=3, budget=None):
        if not 0 < aux_quota < SAMPLES["ten"]:
            raise ValueError("aux quota must be between one and eleven")
        super().__init__(main_rows, seed=seed, budget=budget)
        self.aux_rows = list(aux_rows)
        self.aux_quota = int(aux_quota)
        self.aux_offset = len(main_rows)
        self.aux_pools = {}
        for index, row in enumerate(self.aux_rows):
            if row.get("pool") != "ten":
                raise ValueError("aux rows must join the ten pool")
            self.aux_pools.setdefault(row["task_key"], {}).setdefault(
                row["source_group"], {}).setdefault(str(row.get("variant", "scripted")), []).append(index)
        self.aux_counts = Counter()

    def _draw(self, pools):
        task = self.rng.choice(sorted(pools))
        parent = self.rng.choice(sorted(pools[task]))
        variants = pools[task][parent]
        variant = self.rng.choice(sorted(variants))
        return self.rng.choice(variants[variant])

    def draw_batch(self):
        result, self.last_bins = [], []
        for _ in range(SAMPLES["ten"] - self.aux_quota):
            result.append(self._draw(self.pools["ten"]["expert"]))
            self.last_bins.append("expert")
            self.counts["ten"] += 1
            self.bin_counts["ten|expert"] += 1
        for _ in range(self.aux_quota):
            local = self._draw(self.aux_pools)
            result.append(self.aux_offset + local)
            self.last_bins.append("expert")
            self.aux_counts["aux"] += 1
        for pool in ("fresh", "raw"):
            for bin_ in ["prefix"] * 2 + ["all"] * 2:
                result.append(self._draw(self.pools[pool][bin_]))
                self.last_bins.append(bin_)
                self.counts[pool] += 1
                self.bin_counts[pool + "|" + bin_] += 1
        return result

    def report(self):
        value = super().report()
        value["pool_draw_counts"]["aux"] = self.aux_counts.get("aux", 0)
        value["aux_quota"] = self.aux_quota
        value["aux_task_draw_counts"] = self.aux_counts.get("by_task", {})
        return value
