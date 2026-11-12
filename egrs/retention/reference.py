"""Shared frozen-base reference view; never loads a second model or runs itself."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

import torch

from egrs.augmentation.oft import LoRALinear,training_prediction


@contextmanager
def shared_base_reference(policy):
    """Temporarily bypass added native LoRA and restore every module flag."""
    modules=[];seen=set()
    for root in (policy.model,policy.action_head,policy.proprio_projector):
        for module in root.modules():
            if id(module) not in seen:modules.append(module);seen.add(id(module))
    flags=[(module,module.training) for module in modules]
    adapters=[(module,module.enabled) for module in modules if isinstance(module,LoRALinear)]
    if not adapters:raise ValueError('shared-base reference requires injected native LoRA')
    try:
        for module,_ in flags:module.training=False
        for module,_ in adapters:module.enabled=False
        with torch.no_grad():yield
    finally:
        # Direct flags preserve mixed frozen/eval subtrees; train(True) would
        # recursively overwrite the original vision/head/module modes.
        for module,enabled in adapters:module.enabled=enabled
        for module,training in flags:module.training=training


def reference_prediction(policy,item,predict=None):
    """Reference first, then restore student modes before returning its target."""
    with shared_base_reference(policy):
        output=(training_prediction if predict is None else predict)(policy,item)
        if (not isinstance(output,torch.Tensor) or tuple(output.shape)!=(1,8,7)
                or not torch.is_floating_point(output) or not torch.isfinite(output).all()):
            raise ValueError('reference must produce finite normalized action shape1x8x7')
        # Clone prevents a test/custom predictor returning a view of mutable
        # policy storage from coupling the frozen target to later updates.
        result=output.detach().clone()
    return result


class ReferenceBudget:
    """Count single-observation requests before calling the reference policy."""
    LIMITS={'train':8000,'dev':1024}
    def __init__(self,ledger_path=None):
        self.ledger_path=Path(ledger_path) if ledger_path is not None else None
        self.counts={'train':0,'dev':0}
        if self.ledger_path is not None and self.ledger_path.exists():
            self.counts=self._validated(json.loads(self.ledger_path.read_text(encoding='utf-8')))

    @classmethod
    def _validated(cls,value):
        if (not isinstance(value,dict) or set(value)!={'train','dev','total','budget'}
                or type(value.get('budget')) is not int or value['budget']!=9024
                or any(type(value.get(key)) is not int or not 0<=value[key]<=limit for key,limit in cls.LIMITS.items())
                or type(value.get('total')) is not int or value['total']!=value['train']+value['dev'] or value['total']>9024):
            raise ValueError('reference budget state is invalid')
        return {key:value[key] for key in cls.LIMITS}

    def report(self):
        return {**self.counts,'total':sum(self.counts.values()),'budget':9024}

    def state_dict(self):return self.report()

    def _persist(self):
        if self.ledger_path is not None:
            self.ledger_path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.ledger_path.with_suffix(self.ledger_path.suffix+'.tmp')
            temporary.write_text(json.dumps(self.report(),sort_keys=True)+'\n',encoding='utf-8')
            os.replace(temporary,self.ledger_path)

    def consume(self,split,count=1):
        if split not in self.LIMITS or type(count) is not int or count<=0:
            raise ValueError('reference budget requires train/dev and positive observation count')
        if self.counts[split]+count>self.LIMITS[split] or sum(self.counts.values())+count>9024:
            raise ValueError('reference budget exhausted; no extra reference calls authorized')
        self.counts[split]+=count
        # The durable allocation precedes the forward, so exceptions/restarts
        # cannot silently reuse already spent calls from an older checkpoint.
        self._persist()

    def load_state_dict(self,state):
        counts=self._validated(state)
        if self.ledger_path is not None and self.ledger_path.exists():
            disk=self._validated(json.loads(self.ledger_path.read_text(encoding='utf-8')))
            counts={key:max(counts[key],disk[key]) for key in self.LIMITS}
        self.counts={key:max(counts[key],self.counts[key]) for key in self.LIMITS}
        self._validated(self.report());self._persist()
