"""Durable, pre-forward accounting including auxiliary training/dev views."""
import os
from pathlib import Path

from .contracts import read_json, write_json, require, training_recipe


class ModelBudget:
    LIMITS = {'main_train':20000, 'aux_train':4000, 'main_dev':2048, 'aux_dev':1024}

    def __init__(self, path=None, *, target_updates=1000):
        training_recipe(target_updates)
        self.target_updates = target_updates
        self.limits = {k:v*(target_updates//1000) for k,v in self.LIMITS.items()}
        self.path = Path(path) if path else None
        self.counts = {k:0 for k in self.LIMITS}
        if self.path and self.path.exists():
            self.counts = self.validated(read_json(self.path), target_updates=target_updates)

    @classmethod
    def validated(cls, value, *, target_updates=1000):
        training_recipe(target_updates)
        factor = target_updates//1000
        require(isinstance(value,dict) and set(value) == set(cls.LIMITS)|{'total','budget'}, 'Invalid model ledger fields')
        require(all(type(value[k]) is int and 0 <= value[k] <= cap*factor for k,cap in cls.LIMITS.items())
                and type(value['total']) is int and value['total'] == sum(value[k] for k in cls.LIMITS)
                and type(value['budget']) is int and value['budget'] == sum(cls.LIMITS.values())*factor
                and value['total'] <= sum(cls.LIMITS.values())*factor, 'Invalid forward budget')
        return {k:value[k] for k in cls.LIMITS}

    def report(self):
        return dict(self.counts, total=sum(self.counts.values()), budget=sum(self.limits.values()))

    state_dict = report

    def persist(self):
        if self.path:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            write_json(temporary, self.report())
            os.replace(temporary, self.path)

    def consume(self, kind):
        require(kind in self.limits and self.counts[kind] < self.limits[kind], 'Forward budget exhausted')
        self.counts[kind] += 1
        self.persist()

    def load_state_dict(self, value):
        counts = self.validated(value, target_updates=self.target_updates)
        self.counts = {k:max(self.counts[k],counts[k]) for k in self.LIMITS}
        self.validated(self.report(), target_updates=self.target_updates)
        self.persist()

    def inherit(self, value, *, parent_target_updates=1000):
        require(self.report()['total'] == 0, 'Cannot replace already-spent child ledger')
        counts = self.validated(value, target_updates=parent_target_updates)
        converted = dict(counts, total=sum(counts.values()), budget=sum(self.limits.values()))
        self.load_state_dict(converted)


class ReferenceBudget(ModelBudget):
    """Same reference allocations as043, scaled without resetting ancestor spend."""
    LIMITS = {'train':8000, 'dev':1024}

    def consume(self, split, count=1):
        require(type(count) is int and count > 0, 'Positive reference allocation required')
        require(split in self.limits and self.counts[split]+count <= self.limits[split], 'Reference budget exhausted')
        self.counts[split] += count
        self.persist()

    _persist = ModelBudget.persist
