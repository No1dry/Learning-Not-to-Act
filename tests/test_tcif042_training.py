"""Matched C1 continuation/ledgers on CPU tiny autograd graphs, no pretrained VLA."""
from copy import deepcopy
import json
import shutil
from types import SimpleNamespace

import pytest
import torch

from test_tcif042_identity import source042, stage_sources
from test_retention041_training import Dataset, predict
from test_task_control_training import tiny_reference


def config(source, arm, updates=1):
    from egrs.task_control.training import PRESET
    return {'experiment_arm':arm, 'initial_adapter':str(source),
            'training_recipe':dict(PRESET, updates=updates, save_every=1)}


def fake_attention(policy, arm):
    from egrs.tcif042.contract import contract_for
    result = SimpleNamespace(contract=contract_for(arm), runtime={'test':'tiny-training-seam'})
    policy._tcif042 = result
    return result


def run(training, cfg, policy, out, *, resume=None, **kwargs):
    # source042 returns an installed source student; public training starts with
    # the original frozen SOG10. Restore only that synthetic base view here.
    from egrs.augmentation.oft import LoRALinear
    base=deepcopy(policy)
    del base.model.task_control
    if hasattr(base, '_tcif042'): del base._tcif042
    for layer in base.model.language_model.model.layers:
        for name, module in list(layer.self_attn.named_children()):
            if isinstance(module, LoRALinear): setattr(layer.self_attn, name, module.base_layer)
    return training._run_loaded(SimpleNamespace(output_dir=out, resume=resume), cfg,
        Dataset(), Dataset('dev'), base, attention_factory=fake_attention,
        predict=kwargs.pop('predict', predict), reference_predict=kwargs.pop('reference_predict', tiny_reference),
        **kwargs)


def test_matched_arms_preserve_all_c1_losses_batches_and_reference_order(source042,tmp_path):
    from egrs.tcif042 import training, adapter
    policy, source, _ = source042
    traces=[]; metrics=[]
    for arm in ('f0','f1'):
        events=[]
        def student(p,item):
            events.append(('student',tuple(item['proprio'])))
            return predict(p,item)
        def reference(p,item):
            events.append(('reference',tuple(item['proprio'])))
            return tiny_reference(p,item)
        result=run(training,config(source,arm),policy,tmp_path/arm,predict=student,reference_predict=reference)
        assert result['reference_calls']['train']==8 and result['student_calls']['train']==22
        assert [e[0] for e in events[:30]]==['reference']*8+['student']*22
        traces.append(events)
        saved=adapter.read_adapter_identity(tmp_path/arm/'update-000001')
        assert saved['arm']=='c1' and saved['experiment_arm']==arm
        assert saved['ancestor_updates']==2000
        assert not (tmp_path/arm/'old10_budget.json').exists()
        data=json.loads((tmp_path/arm/'metrics.jsonl').read_text().splitlines()[0]); metrics.append(data)
        assert data['total_ancestral_updates']==2001 and data['completion_percent']==100
        assert data['reference_calls']['total']>=8 and data['student_calls']['total']>=22
        assert data['eta_seconds']==0 and 'attention_runtime' in json.loads((tmp_path/arm/'run_config.json').read_text())
    assert traces[0]==traces[1]
    for key in ('pool_l1','weighted_l1','count','self','swap','align'):
        assert metrics[0][key]==metrics[1][key]


def test_same_run_resume_restores_all_state_and_two_budgets(source042,tmp_path,monkeypatch):
    from egrs.tcif042 import training, checkpoint, adapter
    policy,source,_=source042; cfg=config(source,'f1',2)
    save=checkpoint.save_training_state
    def stop(*a,**kw):
        result=save(*a,**kw)
        if kw['update']==1: raise RuntimeError('synthetic interruption')
        return result
    monkeypatch.setattr(checkpoint,'save_training_state',stop)
    with pytest.raises(RuntimeError,match='synthetic interruption'):
        run(training,cfg,policy,tmp_path/'resumed')
    monkeypatch.setattr(checkpoint,'save_training_state',save)
    result=run(training,cfg,policy,tmp_path/'resumed',resume=tmp_path/'resumed/update-000001')
    assert result['reference_calls']['train']==16 and result['student_calls']['train']==44
    run(training,cfg,policy,tmp_path/'whole')
    a=adapter.read_adapter_identity(tmp_path/'resumed/update-000002')
    b=adapter.read_adapter_identity(tmp_path/'whole/update-000002')
    assert a['student_identity']['tensor_sha256']==b['student_identity']['tensor_sha256']
    assert a['reference_calls']==b['reference_calls'] and a['student_calls']==b['student_calls']
    with pytest.raises(ValueError,match='complete'):
        run(training,cfg,policy,tmp_path/'whole',resume=tmp_path/'whole/update-000002')
    shutil.copytree(tmp_path/'resumed',tmp_path/'copied')
    with pytest.raises(ValueError,match='configuration|config|run'):
        run(training,cfg,policy,tmp_path/'copied',resume=tmp_path/'copied/update-000001')


@pytest.mark.parametrize('failing', ['reference','student'])
def test_failure_prespends_persistent_budget_and_never_refunds(source042,tmp_path,failing):
    from egrs.tcif042 import training
    policy,source,_=source042;out=tmp_path/failing
    def fail(*a,**kw): raise RuntimeError('synthetic forward failure')
    kwargs={('reference_predict' if failing=='reference' else 'predict'):fail}
    with pytest.raises(RuntimeError,match='synthetic forward failure'):
        run(training,config(source,'f0'),policy,out,**kwargs)
    assert json.loads((out/'reference_budget.json').read_text())['train']==(1 if failing=='reference' else 8)
    assert json.loads((out/'student_budget.json').read_text())['train']==(0 if failing=='reference' else 1)
    with pytest.raises(FileExistsError): run(training,config(source,'f0'),policy,out)


def test_default_prediction_and_native_reference_share_real_tiny_sdpa_training_path(tmp_path,monkeypatch):
    """No prediction/attention callback replacement in this integration test."""
    from test_tcif042_attention import make_policy
    import test_tcif042_attention as tiny_sdpa
    from test_task_control_model import Processor, tiny_policy as prepared_policy
    from egrs.task_control import adapter as common
    from egrs.task_control.oft import install
    from egrs.retention041 import adapter as previous
    from egrs.tcif042 import adapter, training
    from torch.utils.checkpoint import checkpoint
    # The public entry requests nonreentrant checkpointing. The tiny fixture's
    # default reentrant mode is exercised separately by attention mask tests.
    def nonreentrant(function,*args,**kwargs):
        return checkpoint(function,*args,use_reentrant=False)
    monkeypatch.setattr(tiny_sdpa,'checkpoint',nonreentrant)
    original=make_policy(monkeypatch)
    # The inherited accepted7B adapter schema has equal-width q/k/v/o. Keep
    # that inventory here; grouped-query numerics have their own attention test.
    for layer in original.model.language_model.model.layers:
        layer.self_attn.num_key_value_heads=2
        layer.self_attn.num_key_value_groups=1
        layer.self_attn.k_proj=torch.nn.Linear(4,4)
        layer.self_attn.v_proj=torch.nn.Linear(4,4)
    prepared=prepared_policy(monkeypatch)  # supplies only CPU image-helper module
    original.processor=Processor();original.resize_size=224
    original.cfg=SimpleNamespace(unnorm_key='libero_10_no_noops')
    original.metadata=deepcopy(prepared.metadata)
    original.model.norm_stats={'synthetic':'validated boundary'}
    def enable(**kwargs): original.model.language_model.model.gradient_checkpointing=True
    original.model.language_model.gradient_checkpointing_enable=enable
    student=deepcopy(original);install(student)
    with torch.no_grad():
        for name,p in student.model.named_parameters():
            if p.requires_grad:p.fill_(.015)
    calls=lambda train,dev,budget:dict(train=train,dev=dev,total=train+dev,budget=budget)
    initial040=common.save_adapter(student,tmp_path/'040',arm='c1',update=1000,
        index_identity=adapter.INDEX_IDENTITY,reference_calls=calls(8000,1024,9024))
    monkeypatch.setattr(previous,'INITIALIZATION_SHA256',initial040['adapter_sha256'])
    stage041={'format':'task041-stage-inputs-v1','experiment_arm':'r0',
        'initialization_identity':initial040,'teacher_identity':None,'index_identity':adapter.INDEX_IDENTITY,
        'ancestor_updates':1000,'additional_updates':1000}
    source=tmp_path/'041r0'
    initial=previous.save_adapter(student,source,experiment_arm='r0',update=1000,
        index_identity=adapter.INDEX_IDENTITY,stage_identity=stage041,
        reference_calls=calls(8000,1024,9024),student_calls=calls(22000,2560,24560),old10_calls=calls(0,0,0))
    monkeypatch.setattr(adapter,'INITIALIZATION_SHA256',initial['adapter_sha256'])
    class Sensors(Dataset):
        def __getitem__(self,index):
            item=super().__getitem__(index)
            item.update(images=[10,20],instruction='Move cup')
            return item
    native=torch.nn.functional.scaled_dot_product_attention;trace=[]
    def primitive(q,k,v,**kwargs):
        mask=kwargs['attn_mask']
        same_rows=torch.equal(mask,mask[:,:,:1,:].expand_as(mask))
        trace.append((torch.isneginf(mask).any().item(),kwargs['is_causal'],same_rows))
        return native(q,k,v,**kwargs)
    monkeypatch.setattr(torch.nn.functional,'scaled_dot_product_attention',primitive)
    result=training._run_loaded(SimpleNamespace(output_dir=tmp_path/'run',resume=None),config(source,'f1'),
        Sensors(),Sensors('dev'),original)
    assert result['reference_calls']['train']==8 and result['student_calls']['train']==22
    assert trace[:24]==[(True,False,True)]*24  # native refs: all query rows identical
    assert trace[24:27]==[(True,False,False)]*3  # all student layers retain F1 bans
    assert original.model.calls==result['reference_calls']['total']+result['student_calls']['total']
    assert original.model.vision_backbone.calls==original.model.calls
    assert original.proprio_projector.calls==original.model.calls
    assert not original.model.language_model._forward_pre_hooks.keys()-{original._tcif042._guard_handle.id}
    saved=adapter.read_adapter_identity(tmp_path/'run/update-000001')
    assert saved['attention_runtime']==original._tcif042.runtime
    assert all(p.grad is None for p in original.model.parameters() if not p.requires_grad)
