"""Synthetic update998 -> two tiny CPU updates -> strict036 ->180 new fake episodes.

The998 checkpoint is an explicitly manufactured fixture, never real training
history. Only999/1000 use a tiny policy forward/backward; no native or7B runs.
Run this file in its own process, separate from NumPy native geometry fixtures.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import torch

from egrs.augmentation.adapter_identity import read_adapter_identity as strict_adapter_identity
from test_retention_training import Dataset,tiny_policy,prediction
from test_retention_evaluation import core,ready_config,config036


def synthetic_update998(output,export,config):
    """Write a complete, explicitly fake optimizer/RNG/sampler/budget resume state."""
    from egrs.retention import training
    from egrs.retention.reference import ReferenceBudget
    from egrs.augmentation.oft import inject_language_lora,sha256
    policy=tiny_policy();inject_language_lora(policy)
    parameters=[p for p in policy.model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(parameters,lr=config['learning_rate'])
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,
        lambda step:min(1.,(step+1)/config['warmup_updates']))
    for parameter in parameters:
        optimizer.state[parameter]={'step':torch.tensor(998.),
            'exp_avg':torch.zeros_like(parameter),'exp_avg_sq':torch.zeros_like(parameter)}
    for group in optimizer.param_groups:group['lr']=config['learning_rate']
    scheduler.last_epoch=998;scheduler._step_count=999;scheduler._last_lr=[config['learning_rate']]
    budget=ReferenceBudget(ledger_path=output/'reference_budget.json')
    budget.load_state_dict({'train':7984,'dev':768,'total':8752,'budget':9024})
    sampler=training.ThreePoolSampler(Dataset().rows,seed=7,budget=budget)
    # Simulate the sampler state cheaply using metadata draws, never model calls.
    for _ in range(998):sampler.draw_batch()
    run_config=dict(config,export_identity={name:sha256(export/name)
        for name in ('sources.json','rows.jsonl','report.json')},
        reference_view='shared_frozen_base_without_added_lora')
    checkpoint=output/'update-000998'
    training.base.save_training_state(checkpoint,policy,optimizer,scheduler,sampler,998,0.,run_config,
        adapter_metadata=training._metadata(998,run_config,budget))
    (output/'synthetic_fixture_origin.json').write_text(json.dumps({
        'synthetic_prior_checkpoint_update':998,'actual_tiny_updates_to_run':[999,1000],
        'synthetic_prior_reference_calls':budget.report(),'real_models_loaded':False}),encoding='utf-8')
    return checkpoint


def test_tiny_final1000_strict_adapter_to_all180_new_fake_episodes(config036,tmp_path,monkeypatch,capsys):
    from egrs.retention import training
    from egrs.augmentation import adapter_identity
    from egrs.augmentation.oft import load_trained_adapter,LoRALinear
    import test_retention_evaluation as evaluation_tests
    config=deepcopy(training.PRESET)
    exported=tmp_path/'training-index';exported.mkdir()
    for name in ('sources.json','rows.jsonl','report.json'):(exported/name).write_text('{}')
    output=tmp_path/'tiny-training';output.mkdir()
    checkpoint=synthetic_update998(output,exported,config)
    args=SimpleNamespace(export_dir=exported,output_dir=output,resume=checkpoint)
    trained=tiny_policy()
    result=training._run_loaded(args,config,Dataset(),Dataset(),trained,predict=prediction)
    final=Path(result['selected_checkpoint'])
    assert final.name=='update-001000'
    identity=strict_adapter_identity(final)
    assert identity['update']==identity['final_update']==1000
    assert identity['reference_calls']['train']==8000
    assert identity['reference_calls']['dev']<=1024 and identity['reference_calls']['total']<=9024
    metrics=[json.loads(line) for line in (output/'metrics.jsonl').read_text().splitlines()]
    assert [m['update'] for m in metrics]==[999,1000]
    loaded=tiny_policy();loaded_identity=load_trained_adapter(loaded,final)
    assert loaded_identity==identity
    assert all(module.enabled for module in loaded.model.modules() if isinstance(module,LoRALinear))
    observation=training._sensors(Dataset()[0])
    assert torch.equal(prediction(trained,observation),prediction(loaded,observation))
    # The existing eval fixture mocks identity reading. Replace that boundary
    # with the captured real standard-library byte/schema validator for this chain.
    monkeypatch.setattr(adapter_identity,'read_adapter_identity',strict_adapter_identity)
    monkeypatch.setattr(evaluation_tests,'adapter036',lambda:deepcopy(identity))
    cfg=json.loads(Path(config036).read_text());cfg['adapter']=str(final)
    Path(config036).write_text(json.dumps(cfg),encoding='utf-8')
    evaluation_tests.test_new180_final_reader_once_progress_and_errors(
        config036,tmp_path,monkeypatch,capsys,mode='complete')
    plan=json.loads((tmp_path/'eval036/plan.json').read_text())
    assert plan['adapter_identity']==identity and plan['config']['adapter']==str(final.resolve())
    assert plan['new_model_execution_only'] is True and 'continuation' not in plan
