"""Shared-base reference and versioned036 adapter checks with tiny CPU modules."""
from copy import deepcopy
from contextlib import nullcontext
import json
import subprocess
import sys

import pytest
import torch
from torch import nn
from torch.utils.checkpoint import checkpoint

from test_augmentation_training import policy
from egrs.augmentation.oft import inject_language_lora,save_adapter,attach_trained_adapter,read_adapter_identity


def tiny_policy():
    p=policy()
    p.metadata['dataset_statistics_sha256']='6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3'
    return p


def metadata(update=2):
    from egrs.augmentation.adapter_identity import RETENTION_RECIPE,BASE_SOURCE
    return {'recipe':'policy_retention_distillation','data_kind':'task036-retention-data-v1',
        'update':update,'final_update':1000,'export_identity':{name:'e'*64 for name in ('sources.json','rows.jsonl','report.json')},
        'reference_view':'shared_frozen_base_without_added_lora','reference_base':deepcopy(BASE_SOURCE),
        'training_recipe':deepcopy(RETENTION_RECIPE),
        'reference_calls':{'train':update*8,'dev':0,'total':update*8,'budget':9024}}


def prediction(p,item):
    return p.model(item['x']).sum().expand(1,8,7)


def test_reference_is_original_base_and_lora_changes_only_student():
    from egrs.retention.reference import reference_prediction
    torch.manual_seed(4);p=tiny_policy();x=torch.ones(1,3)
    original=prediction(p,{'x':x}).detach().clone()
    inject_language_lora(p)
    for name,value in p.model.named_parameters():
        if name.endswith('lora_B'):value.data.fill_(.2)
    student=prediction(p,{'x':x})
    teacher=reference_prediction(p,{'x':x},predict=prediction)
    assert torch.equal(teacher,original) and not torch.equal(student,teacher)
    assert not teacher.requires_grad and teacher.grad_fn is None
    (student-teacher).abs().mean().backward()
    assert any(v.grad is not None and v.grad.abs().sum()>0 for n,v in p.model.named_parameters() if n.endswith('lora_B'))
    assert all(v.grad is None for n,v in p.model.named_parameters() if 'lora_' not in n)
    assert all(v.grad is None for v in p.action_head.parameters())


def test_reference_context_restores_each_flag_enable_and_grad_on_exception():
    from egrs.retention.reference import shared_base_reference
    from egrs.augmentation.oft import LoRALinear
    p=tiny_policy();inject_language_lora(p)
    p.model.train();p.model.vision_backbone.eval();p.action_head.eval()
    modules=list(p.model.modules())+list(p.action_head.modules())+list(p.proprio_projector.modules())
    loras=[m for m in modules if isinstance(m,LoRALinear)]
    loras[0].enabled=False
    before=[m.training for m in modules];enabled=[m.enabled for m in loras]
    requires=[v.requires_grad for m in (p.model,p.action_head,p.proprio_projector) for v in m.parameters()]
    with pytest.raises(RuntimeError,match='predict failed'):
        with shared_base_reference(p):
            assert not torch.is_grad_enabled()
            assert not any(m.training for m in modules) and not any(m.enabled for m in loras)
            raise RuntimeError('predict failed')
    assert [m.training for m in modules]==before and [m.enabled for m in loras]==enabled
    assert [v.requires_grad for m in (p.model,p.action_head,p.proprio_projector) for v in m.parameters()]==requires
    assert torch.is_grad_enabled()


def test_reference_restoration_keeps_nonreentrant_student_checkpoint_gradient():
    from egrs.retention.reference import reference_prediction
    from egrs.augmentation.oft import LoRALinear
    p=tiny_policy();inject_language_lora(p);p.model.train();p.model.vision_backbone.eval()
    item={'x':torch.ones(1,3)}
    target=reference_prediction(p,item,predict=prediction)
    y=checkpoint(lambda x:p.model(x),item['x'],use_reentrant=False)
    (y.sum().expand(1,8,7)-target+1).abs().mean().backward()
    assert all(m.enabled for m in p.model.modules() if isinstance(m,LoRALinear))
    assert any(v.grad is not None and v.grad.abs().sum()>0 for n,v in p.model.named_parameters() if n.endswith('lora_B'))
    assert not p.model.vision_backbone.training


@pytest.mark.parametrize('bad',['shape','nonfinite'])
def test_bad_reference_is_rejected_after_flags_restore(bad):
    from egrs.retention.reference import reference_prediction
    p=tiny_policy();inject_language_lora(p)
    before=[m.training for m in p.model.modules()]
    value=torch.zeros(8,7) if bad=='shape' else torch.full((1,8,7),float('nan'))
    with pytest.raises(ValueError):reference_prediction(p,{},predict=lambda *a:value)
    assert [m.training for m in p.model.modules()]==before


def test_reference_budget_hard_caps_and_resume_never_rewinds_ledger(tmp_path):
    from egrs.retention.reference import ReferenceBudget
    ledger=tmp_path/'reference_budget.json';budget=ReferenceBudget(ledger_path=ledger)
    budget.consume('train',7999);budget.consume('dev',1024)
    checkpoint_state=budget.state_dict()
    budget.consume('train')
    assert budget.report()=={'train':8000,'dev':1024,'total':9024,'budget':9024}
    with pytest.raises(ValueError,match='budget'):budget.consume('train')
    restored=ReferenceBudget(ledger_path=ledger);restored.load_state_dict(checkpoint_state)
    assert restored.report()==budget.report()
    with pytest.raises(ValueError,match='budget'):restored.consume('dev')
    assert json.loads(ledger.read_text())==budget.report()


def test_036_adapter_roundtrip_loads_enabled_and_rejects_recipe_or_stats(tmp_path):
    from egrs.augmentation.oft import LoRALinear
    p=tiny_policy();base=deepcopy(p);inject_language_lora(p)
    for name,value in p.model.named_parameters():
        if name.endswith('lora_B'):value.data.fill_(.1)
    want=prediction(p,{'x':torch.ones(1,3)}).detach()
    # Runtime bypass is deliberately absent from the serialized adapter.
    for m in p.model.modules():
        if isinstance(m,LoRALinear):m.enabled=False
    identity=save_adapter(p,tmp_path,group='policy_retention_distillation',metadata=metadata())
    assert identity['schema_version']=='task036-oft-adapter-v1'
    attach_trained_adapter(base,tmp_path)
    assert torch.equal(prediction(base,{'x':torch.ones(1,3)}),want)
    assert all(m.enabled for m in base.model.modules() if isinstance(m,LoRALinear))
    identity['training_recipe']['pool_weights']['ten']=.7
    (tmp_path/'identity.json').write_text(json.dumps(identity))
    with pytest.raises(ValueError,match='036'):read_adapter_identity(tmp_path)
    wrong=tiny_policy();wrong.metadata['dataset_statistics_sha256']='f'*64;inject_language_lora(wrong)
    with pytest.raises(ValueError,match='statistics|036'):
        save_adapter(wrong,tmp_path/'bad',group='policy_retention_distillation',metadata=metadata())


def test_036_identity_planning_imports_no_model_stack(tmp_path):
    p=tiny_policy();inject_language_lora(p)
    save_adapter(p,tmp_path,group='policy_retention_distillation',metadata=metadata())
    script='''
import importlib.abc
import sys
class BlockModels(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','transformers'}:
            raise AssertionError('036 planning imported model dependency: '+fullname)
sys.meta_path.insert(0,BlockModels())
from egrs.augmentation.adapter_identity import read_adapter_identity
print(read_adapter_identity(sys.argv[1])['schema_version'])
'''
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='task036-oft-adapter-v1'


@pytest.mark.parametrize('field,value',[('train',8001),('dev',1025),('total',True),('budget',10000)])
def test_036_identity_reference_budget_cannot_be_forged(tmp_path,field,value):
    p=tiny_policy();inject_language_lora(p)
    bound=metadata();bound['reference_calls'][field]=value
    with pytest.raises(ValueError,match='036'):
        save_adapter(p,tmp_path,group='policy_retention_distillation',metadata=bound)
