"""Frozen044 language boundary on the original native loader with CPU doubles."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from test_trajectory_evaluation import core

MANIFEST=Path(__file__).resolve().parents[1]/'collaboration/evidence/044_prompt_manifest.json'


def test_all_eighteen_exact_frozen_prompts_and_no_instance_identifiers():
    from egrs.prompt044.prompts import load_manifest,prompt_record,MANIFEST_SHA256
    manifest=load_manifest(MANIFEST)
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest()==MANIFEST_SHA256
    assert len(manifest['tasks'])==9
    for row in manifest['tasks']:
        for variant in ('p1','p2'):
            value=prompt_record(manifest,variant,row['original_instruction'])
            assert value['source_instruction']==row['original_instruction']
            assert value['model_instruction']==row[variant+'_instruction']
            assert value['model_instruction_sha256']==hashlib.sha256(value['model_instruction'].encode()).hexdigest()
            if variant=='p1':assert value['model_instruction']==row['original_instruction']+'. '+row['p1_added_initial_fact']
    pots=next(row for row in manifest['tasks'] if row['task_id']=='two_pots')
    assert 'remaining moka pot' in pots['p2_instruction']
    assert not any(value in pots['p1_instruction']+pots['p2_instruction'] for value in ('moka_pot_1','first pot','second pot'))


def test_prompt_lookup_rejects_unknown_variant_or_changed_manifest(tmp_path):
    from egrs.prompt044.prompts import load_manifest,prompt_record
    manifest=load_manifest(MANIFEST);original=manifest['tasks'][0]['original_instruction']
    for language in (original.upper(),original+' ',original+'.',None):
        with pytest.raises(ValueError):prompt_record(manifest,'p1',language)
    for variant in ('p0','h0',None,1):
        with pytest.raises(ValueError):prompt_record(manifest,variant,original)
    changed=deepcopy(manifest);changed['tasks'].append(changed['tasks'][0])
    with pytest.raises(ValueError):prompt_record(changed,'p1',original)
    target=tmp_path/'changed.json';target.write_bytes(MANIFEST.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='SHA|frozen'):load_manifest(target)


@pytest.fixture
def runtime(tmp_path,monkeypatch,core):
    from tests.test_remaining_oft_transfer import configs,fake_upstream
    from benchmark.remaining_goals.adapters import openvla_oft,oft_transfer
    cfg,_=configs(tmp_path)
    api,torch,calls=fake_upstream(cfg['adapter_options'])
    monkeypatch.setattr(openvla_oft,'_load_upstream',lambda *a:(api,torch,oft_transfer.REPO_REVISION))
    cfg.update(policy_factory='egrs.prompt044.policy:make_policy',prompt_variant='p1',
        prompt_manifest=str(MANIFEST),prompt_audit_path=str(tmp_path/'audit.jsonl'))
    return cfg,calls


@pytest.mark.parametrize('variant',['p1','p2'])
def test_actual_native_predict_sees_exact_static_language_only_allowlisted_sensors(runtime,variant):
    from egrs.prompt044.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,calls=runtime;cfg['prompt_variant']=variant;original=deepcopy(cfg)
    policy=make_policy(cfg)
    row=load_manifest(MANIFEST)['tasks'][0]
    raw=observation();raw.update(goal_specs=['ORACLE'],task_id='wrong',predicates={'A':False},future='GT')
    try:
        policy.reset();policy.predict(raw,row['original_instruction'])
        raw['predicates']['A']=True;raw['mask']=[False,True]
        policy.predict(raw,row['original_instruction'])
        actions=[call for call in calls if call[0]=='action']
        assert len(actions)==2 and all(a[3]==row[variant+'_instruction'] for a in actions)
        prepared=[call[1] for call in calls if call[0]=='prepare']
        assert all(set(value)=={'agentview_image','robot0_eye_in_hand_image','robot0_eef_pos',
            'robot0_eef_quat','robot0_gripper_qpos'} for value in prepared)
        assert cfg==original and policy.base.metadata['unnorm_key']=='libero_10_no_noops'
        assert policy.metadata['prompt_variant']==variant
        assert policy.metadata['deployment_initial_semantic_information'] is True
        assert policy.metadata['checkpoint_source']==cfg['checkpoint_source']
        assert 'method_adapter' not in policy.metadata and 'hint043_arm' not in policy.metadata
        events=[json.loads(line) for line in Path(cfg['prompt_audit_path']).read_text().splitlines()]
        queries=[e for e in events if e['event']=='predict']
        assert [e['episode_ordinal'] for e in queries]==[1,1]
        assert [e['episode_query'] for e in queries]==[1,2]
        assert events[0]['metadata']==policy.metadata
        assert queries[0]['model_instruction']==queries[1]['model_instruction']==actions[0][3]
        assert len([e for e in events if e['event']=='episode_reset'])==1
    finally:policy.close()


@pytest.mark.parametrize('mutation',[{'method_adapter':'h0'},{'hint043_arm':'h1'},{'finish':{}},
                                  {'task_control_arm':'c1'},{'prompt_variant':'p0'}])
def test_research_or_wrong_variant_options_refused_before_load(runtime,monkeypatch,mutation):
    from egrs.prompt044.policy import make_policy
    from benchmark.remaining_goals.adapters import openvla_oft
    cfg,_=runtime;cfg.update(mutation)
    monkeypatch.setattr(openvla_oft,'OpenVLAOFTPolicy',lambda *a:pytest.fail('invalid config loaded model'))
    with pytest.raises(ValueError):make_policy(cfg)
    assert not Path(cfg['prompt_audit_path']).exists()


def test_native_metadata_and_original_loader_identity_remain_strict(runtime,monkeypatch):
    from egrs.prompt044.policy import make_policy
    from benchmark.remaining_goals.adapters import openvla_oft
    cfg,_=runtime;real=openvla_oft.OpenVLAOFTPolicy
    def wrong(config):
        policy=real(config);policy.metadata['unnorm_key']='libero_10';return policy
    monkeypatch.setattr(openvla_oft,'OpenVLAOFTPolicy',wrong)
    with pytest.raises(ValueError,match='normalization|no_noops'):make_policy(cfg)


def test_repeat_audit_cannot_reload_and_reset_is_required(runtime,monkeypatch):
    from egrs.prompt044.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,_=runtime;policy=make_policy(cfg)
    try:
        with pytest.raises(ValueError,match='reset|episode'):policy.predict(observation(),load_manifest(MANIFEST)['tasks'][0]['original_instruction'])
        with pytest.raises(FileExistsError):make_policy(cfg)
    finally:policy.close()


def test_failed_predict_is_durably_spent_before_call_and_fixed_within_episode(runtime):
    from egrs.prompt044.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,_=runtime;policy=make_policy(cfg);row=load_manifest(MANIFEST)['tasks'][0]
    def failure(raw,instruction):
        rows=[json.loads(line) for line in Path(cfg['prompt_audit_path']).read_text().splitlines()]
        assert rows[-1]['event']=='predict' and rows[-1]['sequence']==1
        raise RuntimeError('synthetic native failure')
    policy.base.predict=failure
    try:
        policy.reset()
        with pytest.raises(RuntimeError,match='synthetic native failure'):policy.predict(observation(),row['original_instruction'])
        rows=[json.loads(line) for line in Path(cfg['prompt_audit_path']).read_text().splitlines()]
        assert rows[-1]['event']=='predict_result' and rows[-1]['status']=='error'
        assert rows[-1]['sequence']==1
        with pytest.raises(RuntimeError):policy.predict(observation(),row['original_instruction'])
    finally:policy.close()


def test_episode_language_change_and_call_ceilings_reject_without_extra_forward(runtime):
    from egrs.prompt044.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,_=runtime;policy=make_policy(cfg);rows=load_manifest(MANIFEST)['tasks'];seen=[]
    policy.base.predict=lambda raw,instruction:seen.append(instruction) or np.zeros((8,7))
    try:
        policy.reset();policy.predict(observation(),rows[0]['original_instruction'])
        with pytest.raises(ValueError,match='instruction|language'):policy.predict(observation(),rows[1]['original_instruction'])
        for _ in range(64):policy.predict(observation(),rows[0]['original_instruction'])
        with pytest.raises(ValueError,match='budget|65'):policy.predict(observation(),rows[0]['original_instruction'])
        for _ in range(89):policy.reset()
        with pytest.raises(ValueError,match='90|budget'):policy.reset()
        assert len(seen)==65
    finally:policy.close()


def test_prompt_mapping_import_does_not_load_native_libraries(tmp_path):
    import subprocess
    code="""
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','numpy','transformers'}: raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
from egrs.prompt044.prompts import load_manifest,prompt_record
m=load_manifest(sys.argv[1]);print(prompt_record(m,'p2',m['tasks'][0]['original_instruction'])['model_instruction'])
"""
    run=subprocess.run([sys.executable,'-c',code,str(MANIFEST)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr


@pytest.mark.parametrize('mutation',[{'center_crop':1},{'seed':7.0},{'load_in_8bit':True},
    {'suite':'libero_90'},{'repo_revision':'other'},{'lora_path':'h1'}])
def test_native_option_type_and_frozen_contract_fail_before_construction(runtime,monkeypatch,mutation):
    from egrs.prompt044.policy import make_policy
    from benchmark.remaining_goals.adapters import openvla_oft
    cfg,_=runtime;cfg['adapter_options'].update(mutation)
    monkeypatch.setattr(openvla_oft,'OpenVLAOFTPolicy',lambda *a:pytest.fail('changed native contract reached loader'))
    with pytest.raises(ValueError):make_policy(cfg)
    assert not Path(cfg['prompt_audit_path']).exists()


def test_audit_write_failure_does_not_allow_unlogged_model_calls_or_retry(runtime,monkeypatch):
    from egrs.prompt044.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,_=runtime;policy=make_policy(cfg);policy.reset();calls=[]
    policy.base.predict=lambda *a:calls.append(a)
    real=policy._write
    def fail(record):raise OSError('synthetic durable storage failure')
    monkeypatch.setattr(policy,'_write',fail)
    language=load_manifest(MANIFEST)['tasks'][0]['original_instruction']
    try:
        with pytest.raises(OSError):policy.predict(observation(),language)
        monkeypatch.setattr(policy,'_write',real)
        with pytest.raises(RuntimeError):policy.predict(observation(),language)
        assert calls==[]
    finally:policy.close()
