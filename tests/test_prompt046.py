"""CPU/fake coverage for046's model swap, historical P0 and unchanged controls."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from test_prompt044_evaluation import config044
from test_prompt044_policy import runtime as old_runtime
from test_trajectory_evaluation import core, ready_config
from test_retention_evaluation import config036


@pytest.fixture
def config046(config044,tmp_path,monkeypatch):
    from egrs.hint043 import adapter
    from egrs.prompt046 import evaluation as ev, policy
    from test_hint043 import fake_policy
    path,reference=config044
    p=fake_policy();adapter.install(p)
    parent={'update':1000,'arm':'h1',**{k:'a'*64 for k in ('adapter_sha256','training_state_sha256','identity_sha256','run_config_sha256')}}
    directory=tmp_path/'h1-3000'
    identity=adapter.save_adapter(p,directory,arm='h1',update=3000,sidecar_identity='f'*64,
        reference_calls={'train':24000,'dev':0,'total':24000,'budget':27072},
        model_calls={'main_train':60000,'aux_train':0,'main_dev':0,'aux_dev':0,'total':60000,'budget':81216},
        target_updates=3000,continuation_parent=parent)
    monkeypatch.setattr(policy,'EXPECTED_ADAPTER_SHA256',identity['adapter_sha256'])
    reference.update(adapter_identity=identity,arm='h1',checkpoint_step=3000,deployment_hint=False)
    cfg=json.loads(path.read_text());ref=Path(cfg['reference_plan']);ref.write_text(json.dumps(reference))
    rows=[dict(e,success=i<62,execution_status='completed') for i,e in enumerate(reference['expected']['10'])]
    p0={'arm':'h1','checkpoint_step':3000,'method_adapter':identity,'deployment_hint':False,
        'formal_complete':True,'model_completed':180,'software_exit':'success',
        'execution_error':None,'cleanup_warning':None,'ledger_warning':None,
        'conditions':{'10':{'formal_SR':{'numerator':62,'denominator':90,'percent':100*62/90},
            'report':{'episodes':rows,'integrity_errors':[],'model_aggregation_compatible':True}}}}
    summary=tmp_path/'p0'/'summary.json';summary.parent.mkdir();summary.write_text(json.dumps(p0))
    cfg.update(schema_version=ev.SCHEMA,method_adapter=str(directory),p0_summary=str(summary))
    path=tmp_path/'046.json';path.write_text(json.dumps(cfg))
    monkeypatch.setattr(ev,'REFERENCE_PLAN_SHA256',ev.file_sha(ref))
    monkeypatch.setattr(ev,'P0_SUMMARY_SHA256',ev.file_sha(summary))
    monkeypatch.setattr(ev,'EXPECTED10_SHA256',ev.projection_hash(reference['expected']['10']))
    return path,reference,identity


@pytest.mark.parametrize('variant',['p1','p2'])
def test_plan_same90_full_goals_and_reused_p0_without_model(config046,variant):
    from egrs.prompt046 import evaluation as ev
    path,reference,identity=config046;cfg=json.loads(path.read_text());cfg['variant']=variant;path.write_text(json.dumps(cfg))
    p=ev.build_plan(path)
    assert p['tasks']==[t for t in reference['tasks'] if t['condition']=='10']
    assert p['expected']=={'10':reference['expected']['10']} and len(p['tasks'])==36
    assert p['adapter_identity']==identity and p['checkpoint_step']==3000 and p['research_adapter_loaded']
    assert p['p0']['rate']['numerator']==62 and p['p0']['new_execution'] is False and len(p['p0']['episodes'])==90
    assert p['budget']['total']==90 and p['budget']['00']==0
    assert not p['weights_loaded'] and not p['simulation_created']


@pytest.mark.parametrize('kind',['p0_bytes','p0_model','p0_count','p0_population','adapter_arm','adapter_step','adapter_bytes','variant'])
def test_wrong_reference_or_model_rejected_before_execution(config046,kind,monkeypatch):
    from egrs.prompt046 import evaluation as ev
    path,_,_=config046;cfg=json.loads(path.read_text())
    if kind.startswith('p0'):
        f=Path(cfg['p0_summary']);d=json.loads(f.read_text())
        if kind=='p0_bytes':f.write_bytes(f.read_bytes()+b'\n')
        else:
            if kind=='p0_model':d['arm']='h0'
            if kind=='p0_count':d['conditions']['10']['formal_SR']['numerator']=22
            if kind=='p0_population':d['conditions']['10']['report']['episodes'][0]['episode_id']='foreign'
            f.write_text(json.dumps(d));monkeypatch.setattr(ev,'P0_SUMMARY_SHA256',ev.file_sha(f))
    elif kind=='variant':cfg['variant']='p0';path.write_text(json.dumps(cfg))
    else:
        f=Path(cfg['method_adapter'])/'identity.json';d=json.loads(f.read_text())
        if kind=='adapter_arm':d['arm']='h0'
        if kind=='adapter_step':d['update']=2000
        if kind=='adapter_bytes':(f.parent/'adapter.pt').write_bytes(b'changed')
        else:f.write_text(json.dumps(d))
    with pytest.raises(ValueError):ev.build_plan(path)


@pytest.fixture
def policy_runtime(config046,tmp_path,monkeypatch,core):
    from egrs.prompt046 import policy
    from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
    path,_,identity=config046;source=json.loads(path.read_text())
    native_root=tmp_path/'policy-runtime';native_root.mkdir()
    cfg,calls=old_runtime.__wrapped__(native_root,monkeypatch,core)
    cfg.update(policy_factory=policy.FACTORY,method_adapter=source['method_adapter'],hint043_arm='h1',hint043_checkpoint_step=3000)
    constructed=[]
    def make(config):
        assert config['method_adapter']==source['method_adapter'] and config['hint043_checkpoint_step']==3000
        constructed.append(deepcopy(config))
        p=OpenVLAOFTPolicy(policy.native_config(config))
        p.metadata.update(method_adapter=deepcopy(identity),hint043_arm='h1',hint043_checkpoint_step=3000,deployment_hint=False)
        return p
    monkeypatch.setattr(policy,'construct_hint_policy',make)
    return cfg,calls,constructed,identity


@pytest.mark.parametrize('variant',['p1','p2'])
def test_one_hint_loader_exact044_native_text_sensors_and_truthful_metadata(policy_runtime,variant):
    from egrs.prompt046.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,calls,constructed,identity=policy_runtime;cfg['prompt_variant']=variant;before=deepcopy(cfg)
    p=make_policy(cfg);row=load_manifest(cfg['prompt_manifest'])['tasks'][0]
    obs=observation();obs.update(goal_specs=['GT'],mask=[True,False],contact='oracle',future='not allowed')
    try:
        p.reset();p.predict(obs,row['original_instruction']);obs['mask']=[False,True];p.predict(obs,row['original_instruction'])
        actions=[c for c in calls if c[0]=='action'];assert len(actions)==2
        assert all(c[3]==row[variant+'_instruction'] for c in actions)
        assert len(constructed)==1 and cfg==before
        assert p.metadata['research_adapter_loaded'] and p.metadata['deployment_hint'] is True
        assert p.metadata['method_adapter']==identity and identity['deployment_hint'] is False
        assert p.metadata['hint043_checkpoint_step']==3000 and p.metadata['prompt_variant']==variant
        assert all(set(c[1])=={'agentview_image','robot0_eye_in_hand_image','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos'} for c in calls if c[0]=='prepare')
        events=[json.loads(x) for x in Path(cfg['prompt_audit_path']).read_text().splitlines()]
        assert events[0]['metadata']==p.metadata
        assert [x['model_instruction'] for x in events if x['event']=='predict']==[row[variant+'_instruction']]*2
    finally:p.close()


@pytest.mark.parametrize('mutation',[{'hint043_arm':'h0'},{'hint043_checkpoint_step':1000},{'prompt_variant':'p0'},{'finish':{}}])
def test_invalid_policy_never_constructs_model(policy_runtime,monkeypatch,mutation):
    from egrs.prompt046 import policy
    cfg,_,_,_=policy_runtime;cfg.update(mutation)
    monkeypatch.setattr(policy,'construct_hint_policy',lambda *a:pytest.fail('invalid model constructed'))
    with pytest.raises(ValueError):policy.make_policy(cfg)


def test_failed_call_no_refund_or_unlogged_retry(policy_runtime):
    from egrs.prompt046.policy import make_policy
    from egrs.prompt044.prompts import load_manifest
    from tests.test_remaining_adapter_openvla import observation
    cfg,_,_,_=policy_runtime;p=make_policy(cfg);p.reset()
    def fail(*args):raise RuntimeError('fake inference failure')
    p.base.predict=fail;language=load_manifest(cfg['prompt_manifest'])['tasks'][0]['original_instruction']
    try:
        with pytest.raises(RuntimeError):p.predict(observation(),language)
        with pytest.raises(RuntimeError,match='previous'):p.predict(observation(),language)
        rows=[json.loads(x)for x in Path(cfg['prompt_audit_path']).read_text().splitlines()]
        assert sum(x['event']=='predict' for x in rows)==1 and rows[-1]['status']=='error'
    finally:p.close()


def fake_run(config046,tmp_path,monkeypatch,pause=False):
    from egrs.prompt046 import evaluation as ev
    from egrs.prompt044.prompts import load_manifest,prompt_record
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import workflow,offline_scoring
    path,_,identity=config046;cfg=ev.load_config(path);manifest=load_manifest(cfg['prompt_manifest'])
    created=[];executed=[]
    class Policy:
        def __init__(self,config):
            assert config['method_adapter']==cfg['method_adapter'] and config['hint043_checkpoint_step']==3000
            self.config=config;self.ep=self.seq=self.query=0
            self.provenance={'policy_metadata':{'prompt_variant':config['prompt_variant'],'method_adapter':identity}}
            self.audit=Path(config['prompt_audit_path']);self.audit.write_text('')
            self.write({'event':'initialized','metadata':self.provenance['policy_metadata'],'budget':{'episodes':90,'predict_calls':5850,'predict_calls_per_episode':65}})
            created.append(self)
        def write(self,r):
            with self.audit.open('a')as f:f.write(json.dumps(dict(r,schema_version='task044-prompt-audit-v1'))+'\n')
        def reset(self):self.ep+=1;self.query=0;self.write({'event':'episode_reset','episode_ordinal':self.ep})
        def predict(self,obs,text):
            self.seq+=1;self.query+=1
            self.write(dict(prompt_record(manifest,self.config['prompt_variant'],text),event='predict',sequence=self.seq,episode_ordinal=self.ep,episode_query=self.query))
            self.write({'event':'predict_result','sequence':self.seq,'episode_ordinal':self.ep,'episode_query':self.query,'status':'returned'})
            return np.zeros((8,7))
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        folder=Path(folder);(folder/'raw').mkdir(parents=True);refs=[];attempts=[];executed.append(item)
        for i,ep in enumerate(item['source']['episodes']):
            assert ep['goal_specs']==[{'goal':'A retained'},{'goal':'B remaining'}]
            policy.reset();policy.predict({},ep['instruction']);attempts.append(ep['episode_id'])
            raw={'episode_id':ep['episode_id'],'status':'runtime_error' if pause else 'completed','policy_queries':1,'queries':[{'sequence':1,'status':'ok'}]}
            target=folder/'raw'/f'{i}.json';target.write_text(json.dumps(raw))
            refs.append({'episode_id':ep['episode_id'],'path':f'raw/{i}.json','sha256':ev.file_sha(target)})
            if pause:break
        meta={'status':'technical_pause'if pause else'completed','error':'fake failure'if pause else None,'attempts':attempts,'results':refs,'protocol_version':'mask10','model_runtime':policy.provenance}
        (folder/'task_run.json').write_text(json.dumps(meta));(folder/'environment_dispatch.json').write_text('{}');bind({'fake':'H1'})
        return meta
    def reader(folder,*args):
        folder=Path(folder);meta=json.loads((folder/'task_run.json').read_text());return meta,[json.loads((folder/r['path']).read_text())for r in meta['results']]
    def score(ep,raw,*,condition,source):
        p=dict(ep,execution_status=raw['status'],classification='success'if ep['initial_state_index']%2==0 else'failure',failure_reasons=[]if ep['initial_state_index']%2==0 else['goal_regression'],unknown_reasons=[],path_complete=False)
        return {'condition':'10','primary':p,'legacy':deepcopy(p),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(ev,'_execute_task',execute);monkeypatch.setattr(ev,'_read_task',reader);monkeypatch.setattr(ev,'check_policy',lambda *a:None)
    monkeypatch.setattr(workflow,'_model_identity',lambda m:{'policy_metadata':m['model_runtime']['policy_metadata']})
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    return path,created,executed


@pytest.mark.parametrize('variant',['p1','p2'])
def test_fake90_formal_report_audit_p0_pairing_and_no00(config046,tmp_path,monkeypatch,variant):
    from egrs.prompt046 import evaluation as ev
    path,created,executed=fake_run(config046,tmp_path,monkeypatch)
    cfg=json.loads(path.read_text());cfg['variant']=variant;path.write_text(json.dumps(cfg))
    report=ev.run(path,tmp_path/variant)
    assert report['formal_SR']['numerator']==45 and report['p0']['rate']['numerator']==62
    assert report['formal_complete'] and report['software_exit']=='success'
    assert len(created)==1 and len(executed)==36 and report['budget']['00']==0
    assert report['prompt_audit']['episode_resets']==report['prompt_audit']['predict_calls']==90
    pair=report['paired_vs_p0']['counts'];assert pair['gained']-pair['lost']==45-62 and sum(pair.values())==90
    assert report['research_adapter_loaded'] and report['checkpoint_step']==3000
    with pytest.raises(FileExistsError):ev.run(path,tmp_path/variant)


def test_partial_failure_keeps90_denominator_and_no_complete_pairs(config046,tmp_path,monkeypatch):
    from egrs.prompt046 import evaluation as ev
    path,created,executed=fake_run(config046,tmp_path,monkeypatch,pause=True)
    with pytest.raises(RuntimeError):ev.run(path,tmp_path/'failed')
    r=json.loads((tmp_path/'failed/summary.json').read_text())
    assert r['formal_SR'] is None and r['paired_vs_p0'] is None
    assert len(created)==len(executed)==1 and r['binary_report']['counts']['expected']==90


def test_launcher_stops_on_failure_and_creates_three_way_report(config046,tmp_path,monkeypatch):
    from egrs.prompt046 import evaluation as ev,launch
    path,_,_=fake_run(config046,tmp_path,monkeypatch)
    cfg=json.loads(path.read_text());cfg['variant']='p2';p2=tmp_path/'p2.json';p2.write_text(json.dumps(cfg))
    calls=[]
    def execute(command):
        from types import SimpleNamespace
        calls.append(command)
        ev.run(command[command.index('--config')+1],command[command.index('--output')+1])
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch,'_execute',execute)
    args=dict(p1_config=path,p2_config=p2,p1_output=tmp_path/'a1',p2_output=tmp_path/'a2',marker=tmp_path/'marker')
    result=launch.run_both(**args)
    assert len(calls)==2 and all(c[3]=='egrs.prompt046' for c in calls)
    comparison=json.loads((tmp_path/'marker/comparison.json').read_text())
    assert comparison['p0']['numerator']==62 and comparison['p1']['numerator']==comparison['p2']['numerator']==45
    assert comparison['new_execution']=={'p0':False,'p1':True,'p2':True}
    assert len(comparison['tasks'])==9 and comparison['p2_vs_p1']['counts']['both']==45
    with pytest.raises(FileExistsError):launch.run_both(**args)
    calls.clear();monkeypatch.setattr(launch,'_execute',lambda command:calls.append(command)or type('Result',(),{'returncode':2})())
    args.update(p1_output=tmp_path/'b1',p2_output=tmp_path/'b2',marker=tmp_path/'failed-marker')
    with pytest.raises(RuntimeError):launch.run_both(**args)
    assert len(calls)==1 and not Path(args['p2_output']).exists()


@pytest.mark.parametrize('variant',['p1','p2'])
def test_actual_templates_and_cli_use_only046(config046,tmp_path,monkeypatch,variant):
    from egrs.prompt046 import evaluation as ev
    from egrs.prompt046.__main__ import main
    for key in ('LNA046_CODE','LNA046_ROOT','LNA046_CORE','LNA046_REPORTING','LNA046_RUNTIME','LNA046_LEGACY_CORE'):
        monkeypatch.setenv(key,str(tmp_path/key))
    root=Path(__file__).resolve().parents[1]
    cfg=ev.load_config(root/f'configs/prompt046/evaluation.{variant}.example.json')
    assert cfg['variant']==variant and cfg['schema_version']==ev.SCHEMA
    assert cfg['method_adapter'].endswith('/runs/task045-h1-train-001/update-003000')
    calls=[]
    monkeypatch.setattr(ev,'run',lambda *args:calls.append(args)or {'variant':variant,'formal_SR':{'numerator':1,'denominator':90,'percent':100/90}})
    main(['evaluate','--config','config','--output','out'])
    assert calls==[('config','out')]
