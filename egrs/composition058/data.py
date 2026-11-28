"""Task058 auxiliary pool: scripted counterfactual ten windows and a combined view.

The aux index is the file produced by `record.run` (provenance scripted_placement).
Main/datasets keep their own identities; the combined dataset exposes the frozen main
identity so the original trainer's identity check still refers to the main index.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from egrs.augmentation.data import AugmentationDataset


class AuxScriptedDataset:
    """Lazy HDF windows for scripted episodes; same item contract as the main ten pool."""

    def __init__(self, index_path, split="train"):
        path = Path(index_path).resolve()
        raw = path.read_bytes()
        self.index_path = path
        self.identity = hashlib.sha256(raw).hexdigest()
        doc = json.loads(raw)
        sources = doc.get("sources") or []
        if not sources:
            raise ValueError("aux index has no scripted sources")
        self.sources = {}
        self.rows = []
        for source in sources:
            file = Path(source["file"]).resolve()
            if not file.is_file():
                raise ValueError(f"aux HDF missing: {file}")
            if hashlib.sha256(file.read_bytes()).hexdigest() != source["file_sha256"]:
                raise ValueError(f"aux HDF hash differs: {file}")
            sid = source["source_id"]
            if source["split"] != split:
                continue
            self.sources[sid] = {
                "file": str(file), "file_sha256": source["file_sha256"],
                "mapping": source["mapping"], "instruction": source["instruction"],
                "task_key": source["task_key"], "pool": "ten",
            }
            length = int(source["length"])
            for start in range(length):
                stop = min(start + 8, length)
                self.rows.append({
                    "source_id": sid, "task_key": source["task_key"],
                    "source_group": f"{source['task_key']}|{sid}", "variant": "scripted",
                    "pool": "ten", "view": "PROGRESS", "split": split,
                    "instruction": source["instruction"], "start": start, "stop": stop,
                    "observation_index": start,
                    "action_mask": [True] * (stop - start) + [False] * (8 - (stop - start)),
                })
        if not self.rows:
            raise ValueError("aux index produced no training windows")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        source = self.sources[row["source_id"]]
        view = SimpleNamespace(manifest={"data_root": str(Path(source["file"]).parent)},
                               sources={row["source_id"]: source}, rows=[row])
        return AugmentationDataset.__getitem__(view, 0)

    def validate_normalization(self, stats, unnorm_key, stats_sha256):
        for source in self.sources.values():
            for field in ("action", "proprio"):
                norm = source["mapping"][field + "_normalization"]
                if norm["stats_id"] != unnorm_key or norm["stats_sha256"] != stats_sha256:
                    raise ValueError("aux normalization stats identity differs from checkpoint")


class CombinedDataset:
    """Main frozen dataset + aux scripted pool behind the trainer's dataset interface."""

    def __init__(self, main, aux):
        self.main, self.aux = main, aux
        self.rows = list(main.rows) + list(aux.rows)
        self.identity = main.identity
        self._main_len = len(main.rows)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        if index < self._main_len:
            return self.main[index]
        return self.aux[index - self._main_len]

    def validate_normalization(self, stats, unnorm_key, stats_sha256):
        self.main.validate_normalization(stats, unnorm_key, stats_sha256)
        self.aux.validate_normalization(stats, unnorm_key, stats_sha256)
