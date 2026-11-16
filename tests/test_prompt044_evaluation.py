"""Frozen native-only ten population and real reporting over synthetic execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from test_trajectory_evaluation import core, ready_config
from test_retention_evaluation import config036


@pytest.fixture
def config044(config036, tmp_path, monkeypatch):
    from egrs.retention import evaluation as old
    from egrs.prompt044 import evaluation as ev
    from egrs.prompt044.prompts import load_manifest
    from benchmark.remaining_goals.headless import planning, scoped_sources
    manifest=Path(__file__).resolve().parents[1]/'collaboration/evidence/044_prompt_manifest.json'
    rows={r['task_id']:r for r in load_manifest(manifest)['tasks']}
    original, scoped=planning.source_plan, scoped_sources.resolve_source
    def language(source):
        for ep in source['episodes']:
            ep['instruction']=rows[ep['task_id']]['original_instruction']
            ep['goal_specs']=[{'goal':'A retained'},{'goal':'B remaining'}]
        source['source_plan_sha256']=planning.canonical_hash({k:v for k,v in source.items() if k!='source_plan_sha256'})
        return source
    monkeypatch.setattr(planning,'source_plan',lambda *a,**kw:language(original(*a,**kw)))
    monkeypatch.setattr(scoped_sources,'resolve_source',lambda *a,**kw:language(scoped(*a,**kw)))
    reference=old.build_plan(config036)
    ref=tmp_path/'old043'/'plan.json';ref.parent.mkdir();ref.write_text(json.dumps(reference))
    monkeypatch.setattr(ev,'REFERENCE_PLAN_SHA256',ev.file_sha(ref))
    monkeypatch.setattr(ev,'EXPECTED10_SHA256',ev.projection_hash(reference['expected']['10']))
    cfg={k:deepcopy(reference['config'][k]) for k in ('benchmark_root','reporting_root','base_runtime','environment_dispatch')}
    cfg.update(schema_version=ev.SCHEMA,variant='p1',prompt_manifest=str(manifest),reference_plan=str(ref))
    path=tmp_path/'044.json';path.write_text(json.dumps(cfg))
    return path,reference


def test_plan_has_only_exact_native90_same_original_scoring_sources(config044):
    from egrs.prompt044 import evaluation as ev
    path,reference=config044
    plan=ev.build_plan(path)
    assert len(plan['tasks'])==36 and len(plan['expected']['10'])==90
    assert set(plan['expected'])=={'10'}
    assert plan['tasks']==[t for t in reference['tasks'] if t['condition']=='10']
    assert not {'adapter_identity','continuation','hint043_arm'} & plan.keys()
    assert plan['base_runtime']==reference['base_runtime']
    assert plan['budget']['total']==90 and plan['budget']['model_predict_calls']==5850
    cfg=json.loads(path.read_text());cfg['variant']='p2';path.write_text(json.dumps(cfg))
    second=ev.build_plan(path)
    assert second['tasks']==plan['tasks'] and second['expected']==plan['expected']


@pytest.mark.parametrize('mutation',['variant','extra','reference','runtime','source'])
def test_invalid_or_foreign_contract_fails_before_model(config044,monkeypatch,mutation):
    from egrs.prompt044 import evaluation as ev
    path,_=config044;cfg=json.loads(path.read_text())
    if mutation=='variant':cfg['variant']='h1'
    elif mutation=='extra':cfg['adapter']='research.pt'
    elif mutation=='reference':Path(cfg['reference_plan']).write_text('{}')
    elif mutation=='runtime':
        runtime=json.loads(Path(cfg['base_runtime']).read_text());runtime['method_adapter']='research'
        Path(cfg['base_runtime']).write_text(json.dumps(runtime))
    else:
        from benchmark.remaining_goals.headless import planning
        original=planning.source_plan
        def changed(*a,**kw):
            value=original(*a,**kw);value['episodes'][0]['instruction']='do only B';return value
        monkeypatch.setattr(planning,'source_plan',changed)
    path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError):ev.build_plan(path)


def test_outputs_reject_input_roots_and_existing_directories(config044,tmp_path):
    from egrs.prompt044 import evaluation as ev
    path,_=config044;cfg=ev.load_config(path)
    for target in (Path(cfg['reference_plan']).parent/'child',tmp_path/'sources'/'new',Path(cfg['benchmark_root'])/'new'):
        with pytest.raises(ValueError,match='overlap'):ev.validate_output_paths(cfg,target)
    out=tmp_path/'existing';out.mkdir()
    with pytest.raises(FileExistsError):ev.validate_output_paths(cfg,out)
    reference=json.loads(Path(cfg['reference_plan']).read_text())
    reference['tasks'][0]['source']['source']['manifest']=str(tmp_path/'data'/'old_bank'/'manifest.json')
    Path(cfg['reference_plan']).write_text(json.dumps(reference))
    with pytest.raises(ValueError,match='overlap'):ev.validate_output_paths(cfg,tmp_path/'data'/'new_output')


def fake_execution(config044,tmp_path,monkeypatch,*,pause=False):
    from egrs.prompt044 import evaluation as ev
    from egrs.prompt044.prompts import load_manifest,prompt_record
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring,workflow
    path,_=config044;cfg=ev.load_config(path);manifest=load_manifest(cfg['prompt_manifest'])
    created=[];executed=[];read=[]
    class Policy:
        def __init__(self,config):
            assert 'method_adapter' not in config and config['policy_factory']==ev.FACTORY
            self.config=config;self.ep=0;self.seq=0;self.query=0
            self.provenance={'policy_metadata':{'prompt_variant':config['prompt_variant'],
                'prompt_manifest_sha256':ev.PROMPT_MANIFEST_SHA256,'deployment_initial_semantic_information':True,
                'actual_native_fixture':True,'unnorm_key':'libero_10_no_noops'}}
            self.audit=Path(config['prompt_audit_path']);self.audit.write_text('')
            self.write({'event':'initialized','metadata':self.provenance['policy_metadata'],
                'budget':{'episodes':90,'predict_calls':5850,'predict_calls_per_episode':65}})
            created.append(self)
        def write(self,row):
            with self.audit.open('a') as f:f.write(json.dumps(dict(row,schema_version='task044-prompt-audit-v1'))+'\n')
        def reset(self):
            self.ep+=1;self.query=0;self.write({'event':'episode_reset','episode_ordinal':self.ep})
        def predict(self,obs,instruction):
            self.seq+=1;self.query+=1
            self.write({'event':'predict','sequence':self.seq,'episode_ordinal':self.ep,'episode_query':self.query,
                **prompt_record(manifest,self.config['prompt_variant'],instruction)})
            self.write({'event':'predict_result','sequence':self.seq,'episode_ordinal':self.ep,
                'episode_query':self.query,'status':'returned'})
            return [[0.]*7]*8
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        executed.append(item);folder=Path(folder);(folder/'raw').mkdir(parents=True)
        refs=[];attempts=[]
        for index,ep in enumerate(item['source']['episodes']):
            assert ep['goal_specs']==[{'goal':'A retained'},{'goal':'B remaining'}]
            policy.reset();policy.predict({},ep['instruction']);attempts.append(ep['episode_id'])
            raw={'episode_id':ep['episode_id'],'status':'runtime_error' if pause else 'completed',
                 'policy_queries':1,'queries':[{'sequence':1,'status':'ok'}]}
            target=folder/'raw'/f'{index}.json';target.write_text(json.dumps(raw))
            refs.append({'episode_id':ep['episode_id'],'path':f'raw/{index}.json','sha256':ev.file_sha(target)})
            if pause:break
        metadata={'status':'technical_pause' if pause else 'completed','error':'fake failure' if pause else None,
            'attempts':attempts,'results':refs,'missing':[ep['episode_id'] for ep in item['source']['episodes'] if ep['episode_id'] not in attempts],
            'model_runtime':policy.provenance,'runtime_config':plan['base_runtime'],'protocol_version':'mask10'}
        (folder/'task_run.json').write_text(json.dumps(metadata));(folder/'environment_dispatch.json').write_text('{}')
        bind({'actual':'official native fixture'})
        return metadata
    def reader(folder,item,plan,model_identity,batch):
        read.append(item['key']);folder=Path(folder);metadata=json.loads((folder/'task_run.json').read_text())
        return metadata,[json.loads((folder/ref['path']).read_text()) for ref in metadata['results']]
    def score(ep,raw,*,condition,source):
        assert condition=='10' and ep['goal_specs'][0]['goal']=='A retained'
        # Existing scorer decides the full A+B task: P2 does not change failures.
        row={**ep,'execution_status':raw['status'],'classification':'success' if ep['initial_state_index']%2==0 else 'failure',
             'failure_reasons':[] if ep['initial_state_index']%2==0 else ['goal_regression','wrong_grasp'],
             'unknown_reasons':[],'path_complete':False}
        return {'condition':'10','primary':row,'legacy':deepcopy(row),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(ev,'_execute_task',execute);monkeypatch.setattr(ev,'_read_task',reader)
    monkeypatch.setattr(ev,'check_policy',lambda *a:None)
    monkeypatch.setattr(workflow,'_model_identity',lambda m:{'policy_metadata':m['model_runtime']['policy_metadata']})
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    return path,created,executed,read


@pytest.mark.parametrize('variant',['p1','p2'])
def test_fake90_only_native_single_worker_scores_original_targets_and_audit(config044,tmp_path,monkeypatch,variant):
    from egrs.prompt044 import evaluation as ev
    path,created,executed,read=fake_execution(config044,tmp_path,monkeypatch)
    cfg=json.loads(path.read_text());cfg['variant']=variant;path.write_text(json.dumps(cfg))
    output=tmp_path/variant
    report=ev.run(path,output)
    assert len(created)==1 and len(executed)==len(read)==36
    assert report['formal_complete'] and report['formal_SR']=={'numerator':45,'denominator':90,'percent':50.}
    assert report['prompt_audit']['predict_calls']==90 and report['prompt_audit']['episode_resets']==90
    assert report['p0']['comparison']=='aggregate-only' and report['p0']['rate']['numerator']==22
    assert report['model_completed']==90 and report['budget']['00']==0
    assert len(report['binary_report']['tasks'])==9
    assert json.loads((output/'progress.json').read_text())['formal_complete'] is True
    with pytest.raises(FileExistsError):ev.run(path,output)


def test_failure_keeps_fixed_denominator_no_retry_and_retains_spent_query(config044,tmp_path,monkeypatch):
    from egrs.prompt044 import evaluation as ev
    path,created,executed,read=fake_execution(config044,tmp_path,monkeypatch,pause=True)
    output=tmp_path/'failed'
    with pytest.raises(RuntimeError,match='fake failure'):ev.run(path,output)
    report=json.loads((output/'summary.json').read_text())
    assert len(created)==len(executed)==1 and report['formal_SR'] is None
    assert report['binary_report']['counts']['expected']==90
    assert report['prompt_audit']['predict_calls']==1 and report['software_exit']=='execution_error'


def test_corrupt_prompt_query_invalidates_formal_score_without_changing_original_raw(config044,tmp_path,monkeypatch):
    from egrs.prompt044 import evaluation as ev
    path,_,_,_=fake_execution(config044,tmp_path,monkeypatch)
    output=tmp_path/'run';ev.run(path,output)
    audit=output/'prompt_audit.jsonl';rows=[json.loads(x) for x in audit.read_text().splitlines()]
    rows[2]['model_instruction']='different actual prompt';audit.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
    report=ev.inspect_run(output)
    assert report['formal_SR'] is None and not report['formal_complete']
    assert any('prompt' in str(x).lower() for x in report['binary_report']['integrity_errors'])


@pytest.mark.parametrize('mutation',['result_error','result_ordinal','bool_sequence','schema','reset_missing'])
def test_audit_rejects_inconsistent_actual_call_records(config044,tmp_path,monkeypatch,mutation):
    from egrs.prompt044 import evaluation as ev
    path,created,_,_=fake_execution(config044,tmp_path,monkeypatch)
    plan=ev.build_plan(path);ep=plan['tasks'][0]['source']['episodes'][0]
    from benchmark.remaining_goals import isolated_policy
    audit=tmp_path/'audit.jsonl'
    policy=isolated_policy.SubprocessPolicy(dict(plan['base_runtime'],policy_factory=ev.FACTORY,
        prompt_variant='p1',prompt_manifest=plan['config']['prompt_manifest'],prompt_audit_path=str(audit)))
    policy.reset();policy.predict({},ep['instruction'])
    rows=[json.loads(x) for x in audit.read_text().splitlines()]
    if mutation=='result_error':rows[-1]['status']='error'
    elif mutation=='result_ordinal':rows[-1]['episode_ordinal']=2
    elif mutation=='bool_sequence':rows[2]['sequence']=True
    elif mutation=='schema':rows[2]['schema_version']='other'
    else:rows.pop(1)
    audit.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    raw={'status':'completed','policy_queries':1,'queries':[{'sequence':1}]}
    with pytest.raises(ValueError,match='prompt'):
        ev.verify_audit(audit,plan,policy.provenance,[ep['episode_id']],{ep['episode_id']:raw})


def test_audit_binds_zero_query_initial_failure_without_spending_a_prediction(config044,tmp_path,monkeypatch):
    from egrs.prompt044 import evaluation as ev
    from benchmark.remaining_goals import isolated_policy
    path,_,_,_=fake_execution(config044,tmp_path,monkeypatch)
    plan=ev.build_plan(path);ep=plan['tasks'][0]['source']['episodes'][0]
    audit=tmp_path/'zero.jsonl'
    policy=isolated_policy.SubprocessPolicy(dict(plan['base_runtime'],policy_factory=ev.FACTORY,
        prompt_variant='p1',prompt_manifest=plan['config']['prompt_manifest'],prompt_audit_path=str(audit)))
    policy.reset()
    raw={'status':'invalid_initial_state','policy_queries':0,'queries':[]}
    value=ev.verify_audit(audit,plan,policy.provenance,[ep['episode_id']],{ep['episode_id']:raw})
    assert value['episode_resets']==1 and value['predict_calls']==0
    assert value['bindings'][0]['episode_id']==ep['episode_id']


@pytest.mark.parametrize('reason',['goal_regression','wrong_grasp','invariant_regression'])
def test_original_scoring_and_binary_mapping_keep_a_protection_even_after_full_goals_restored(config044,reason):
    from egrs.prompt044 import evaluation as ev
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    from tests.test_headless_offline_scoring import row
    path,_=config044;plan=ev.build_plan(path);records={}
    changed=plan['expected']['10'][0]['episode_id']
    for ep in plan['expected']['10']:
        legacy=row(**ep,classification='success',success=True,unknown_reasons=[],event_unknown=[])
        if ep['episode_id']==changed:
            legacy.update(classification='failure',success=False,failure_reasons=[reason])
        raw={'status':'completed','official_goals_achieved':True,'n_steps':1,
            'trace':[{'goals':[True,False]},{'goals':[True,True]}],
            'event_unknown':[],'confirmed_events':[],'goal_confirmed_step':1}
        records[ep['episode_id']]=score_verified_result(ep,raw,condition='10',legacy_row=legacy,source={
            'input_evidence_level':'synthetic_scoring_fixture',
            'verified_files':[{'path':str(path),'sha256':ev.file_sha(path)}]})
    report=ev.make_report(records,plan)
    assert records[changed]['primary']['failure_reasons']==[reason]
    assert report['formal_SR']['numerator']==89 and report['formal_SR']['denominator']==90
