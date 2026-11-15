"""Durable, pre-forward accounting including auxiliary training/dev views."""
import os
from pathlib import Path

from .contracts import read_json, write_json, require


class ModelBudget:
    LIMITS = {'main_train':20000, 'aux_train':4000, 'main_dev':2048, 'aux_dev':1024}

    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.counts = {k:0 for k in self.LIMITS}
        if self.path and self.path.exists():
            self.counts = self.validated(read_json(self.path))

    @classmethod
    def validated(cls, value):
        require(isinstance(value,dict) and set(value) == set(cls.LIMITS)|{'total','budget'}, 'Invalid model ledger fields')
        require(all(type(value[k]) is int and 0 <= value[k] <= cap for k,cap in cls.LIMITS.items())
                and type(value['total']) is int and value['total'] == sum(value[k] for k in cls.LIMITS)
                and type(value['budget']) is int and value['budget'] == 27072
                and value['total'] <= 27072, 'Invalid model forward budget')
        return {k:value[k] for k in cls.LIMITS}

    def report(self):
        return dict(self.counts, total=sum(self.counts.values()), budget=27072)

    state_dict = report

    def persist(self):
        if self.path:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            write_json(temporary, self.report())
            os.replace(temporary, self.path)

    def consume(self, kind):
        require(kind in self.LIMITS and self.counts[kind] < self.LIMITS[kind], 'Model forward budget exhausted')
        self.counts[kind] += 1
        self.persist()

    def load_state_dict(self, value):
        counts = self.validated(value)
        self.counts = {k:max(self.counts[k],counts[k]) for k in self.LIMITS}
        self.validated(self.report())
        self.persist()
