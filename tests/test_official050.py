"""Targeted H0 scope/tensor/native500 checks; CPU/fake only."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from test_official047 import inputs, native, write
from egrs.official047 import contracts as c


@pytest.fixture
def h0(inputs, native, monkeypatch):
    from egrs.hint043.adapter import save_adapter
    for name,p in inputs.toy.model.named_parameters():
        if name.endswith('.lora_B'):
            p.data.fill_(.2)
    directory=inputs.tmp/'h0'
    parent={'update':1000,'arm':'h0',**{k:'a'*64 for k in (
        'adapter_sha256','training_state_sha256','identity_sha256','run_config_sha256')}}
    identity=save_adapter(inputs.toy,directory,arm='h0',update=3000,sidecar_identity='f'*64,
        reference_calls={'train':24000,'dev':0,'total':24000,'budget':27072},
        model_calls={'main_train':60000,'aux_train':0,'main_dev':0,'aux_dev':0,'total':60000,'budget':81216},
        target_updates=3000,continuation_parent=parent)
    monkeypatch.setattr(c,'H0_ADAPTER_SHA',identity['adapter_sha256'])
    cfg=c.read(inputs.configs[('h1','libero_spatial')])
    cfg.update(schema_version=c.H0_LIBERO10_SCHEMA,arm='h0',suite='libero_10',method_adapter=str(directory))
    path=inputs.tmp/'h0-10.json';write(path,cfg)
    mapping=native.api.benchmark.get_benchmark_dict();mapping['libero_10']=mapping['libero_spatial']
    monkeypatch.setattr(native.api.benchmark,'get_benchmark_dict',lambda:mapping)
    return SimpleNamespace(path=path,cfg=cfg,identity=identity,directory=directory)


def test050_keeps_047_048_scopes_and_pinned_h1_unchanged():
    assert c.protocol()['total']==3000
    assert c.protocol('libero10')['total']==1000
    spec=c.protocol('h0-libero10')
    assert spec['total']==500 and spec['cells']==(('h0','libero_10'),)
    assert spec['horizons']=={'libero_10':520}
    assert c.ADAPTER_SHA=='78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d'


@pytest.mark.parametrize('field,value',[
    ('arm','h1'),('arm','base'),('suite','libero_goal'),
    ('schema_version',c.LIBERO10_SCHEMA),('schema_version',c.SCHEMA)])
def test050_cannot_mislabel_h0_as_h1_or_change_scope(h0,field,value):
    cfg=deepcopy(h0.cfg);cfg[field]=value;write(h0.path,cfg)
    with pytest.raises(ValueError):c.load_config(h0.path)


def test050_h0_identity_and_original_norms(h0):
    cfg=c.load_config(h0.path);identity=c.verify_inputs(cfg)
    assert identity['method_adapter']==h0.identity and identity['research_adapter_loaded']
    assert identity['unnorm_key']=='libero_10_no_noops'
    assert c.horizon(cfg)==520
    with pytest.raises(ValueError,match='H1'):c.read_h1(h0.directory)


def test050_rejects_h1_checkpoint(h0,inputs):
    cfg=deepcopy(h0.cfg);cfg['method_adapter']=str(inputs.adapter)
    with pytest.raises(ValueError,match='H0'):c.verify_inputs(cfg)


def test050_restore_exact_h0_tensors_and_rng(h0,inputs):
    from egrs.official050.adapter import attach_h0
    from egrs.hint043.adapter import state
    policy=inputs.policy();cfg=SimpleNamespace(unnorm_key='libero_10_no_noops',task_suite_name='libero_10')
    before=c.sha(h0.directory/'identity.json')
    torch.manual_seed(9);expected=torch.rand(3);torch.manual_seed(9)
    attach_h0(policy.model,policy.action_head,policy.proprio_projector,h0.identity,h0.directory,cfg)
    assert torch.equal(expected,torch.rand(3))
    assert c.sha(h0.directory/'identity.json')==before
    assert all(torch.equal(t,state(inputs.toy)[n]) for n,t in state(policy).items())
    assert all(not p.requires_grad for p in policy.model.parameters())


def test050_full_original500_native_loop_all_tasks_and_live_sr(h0,inputs,native,capsys):
    from egrs.official050.__main__ import main
    from egrs.official047.launch import verify_cell
    output=inputs.tmp/'official050'
    assert main(['run','--config',str(h0.path),'--output',str(output)])==0
    summary,rows=verify_cell(output,c.load_config(h0.path))
    assert len(rows)==500 and summary['formal_SR']['denominator']==500
    assert {r['task_id'] for r in rows}==set(range(10))
    assert all(r['arm']=='h0' for r in rows)
    assert summary['model_identity']['method_adapter']['arm']=='h0'
    assert c.read(output/'progress.json')['total_expected']==500
    assert c.read(output/'progress.json')['total_percent']==100
    text=capsys.readouterr().out
    assert text.count('"live_SR_percent":')==503 and '[050] ALL COMPLETE 500/500' in text
    assert sum(x[0]=='load' for x in native.events)==1
    with pytest.raises(ValueError,match='existing'):main(['run','--config',str(h0.path),'--output',str(output)])


def test050_progress_before_start_is500(tmp_path,capsys):
    from egrs.official050.__main__ import main
    assert main(['progress','--output',str(tmp_path/'none')])==0
    assert '"total_expected": 500' in capsys.readouterr().out
    assert main(['progress','--output',str(tmp_path/'none'),'--brief'])==0
    assert '0/500 (0.00%)  SR=--' in capsys.readouterr().out
