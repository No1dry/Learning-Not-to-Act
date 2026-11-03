"""File plan and bounded production orchestration; fake generator only."""
import copy
import json
from pathlib import Path

import pytest

from test_trajectory_data import seed_manifest,attempts_for
from egrs.augmentation.data import identity,file_sha256,read_json


def prepared(tmp_path):
    from egrs.trajectory_augmentation.cli import RECIPE
    manifest=seed_manifest(tmp_path,count=2)
    stats={'libero_10':{'action':{k:manifest['sources'][0]['mapping']['action_normalization'][k] for k in ('q01','q99','mask')},
                       'proprio':{k:manifest['sources'][0]['mapping']['proprio_normalization'][k] for k in ('q01','q99','mask')}}}
    stats_path=tmp_path/'stats.json';stats_path.write_text(json.dumps(stats),encoding='utf-8')
    for s in manifest['sources']:
        for key in ('action_normalization','proprio_normalization'):s['mapping'][key]['stats_sha256']=file_sha256(stats_path)
    (tmp_path/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    task=manifest['sources'][0]
    binding={k:copy.deepcopy(task[k]) for k in ('official_task_name','active_goals','invariant_predicates')}
    binding.update(orientation='opengl',state_field='states',state_alignment_basis='synthetic source contract',
        alignment={'rule':'same_state','orientation':'identity','state_offset':0,'observation_offset':0,'action_offset':0})
    cfg={'format':'task035-generation-config-v1','manifest':'manifest.json','benchmark_root':'unopened-core',
         'stats_path':'stats.json','stats_sha256':file_sha256(stats_path),'unnorm_key':'libero_10',
         'recipe':RECIPE,'native_backend':{'kind':'native','historical_root':'unopened-native','python':'unopened-python'},
         'bindings':{task['task_key']:binding}}
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg),encoding='utf-8')
    return path,manifest


def test_plan_only_metadata_full_budget_and_no_hdf_or_native(tmp_path,monkeypatch):
    from egrs.trajectory_augmentation.cli import build_plan,main
    path,manifest=prepared(tmp_path)
    monkeypatch.setattr('h5py.File',lambda *a,**k:pytest.fail('plan openedHDF'))
    plan=build_plan(path)
    assert plan['population']['parent_sources']==2 and plan['population']['max_normal_replays']==2
    assert plan['population']['max_robot_starts']==6 and plan['population']['max_10_attempts']==12
    assert plan['simulation_created'] is False and plan['model_loaded'] is False
    assert plan['population']['max_control_steps']==14*520
    out=tmp_path/'plan.json'
    main(['plan','--config',str(path),'--output',str(out)])
    assert read_json(out)['identity']==plan['identity']


def test_generate_fake_source_path_indexes_actual_outputs_and_keeps_gaps(tmp_path):
    from egrs.trajectory_augmentation.cli import generate
    path,manifest=prepared(tmp_path);calls=[]
    def fake(source,config,data_root,output_dir):
        calls.append((source['source_id'],config['save_video']))
        output_dir.mkdir(parents=True,exist_ok=True)
        attempts=attempts_for(output_dir,[source])
        for attempt in attempts:
            attempt['audit_path']='audit.json'
            attempt['lineage_path']='lineage.json'
            attempt['qualification_path']='qualification.json'
            attempt['journal_path']='steps.jsonl'
        if source['demo_index']==1:
            attempts[-1].update(qualified=False,status='rejected',failure_reason='no_safe_handoff',file=None,length=0)
        return {'source_id':source['source_id'],'attempts':attempts,'gaps':['missing_other_variants'],'error':None}
    result=generate(path,tmp_path/'run',source_generator=fake)
    assert calls==[('parent0',True),('parent1',False)]
    assert result['data']['attempts']==4 and result['data']['qualified_trajectories']==3
    assert result['data']['failed_attempts']==1
    assert result['source_reports'][1]['gaps']==['missing_other_variants']
    assert result['population']['max_10_attempts']==12
    assert (tmp_path/'run/export/windows.jsonl').exists()
    saved=read_json(tmp_path/'run/export/attempts.json')
    assert saved[0]['audit_path']=='artifacts/source-000/audit.json'
    assert saved[0]['lineage_path']=='artifacts/source-000/lineage.json'
    assert saved[0]['qualification_path']=='artifacts/source-000/qualification.json'
    assert saved[0]['journal_path']=='artifacts/source-000/steps.jsonl'
    assert result['model_loaded'] is False


def test_generation_never_overwrites_or_uses_changed_stats(tmp_path):
    from egrs.trajectory_augmentation.cli import generate
    path,manifest=prepared(tmp_path);out=tmp_path/'existing';out.mkdir()
    with pytest.raises(FileExistsError):generate(path,out,source_generator=lambda *a:pytest.fail('generator'))
    (tmp_path/'stats.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='stats'):
        generate(path,tmp_path/'new',source_generator=lambda *a:pytest.fail('generator'))


def test_source_initialization_error_recorded_without_inventing_attempts(tmp_path):
    from egrs.trajectory_augmentation.cli import generate
    path,manifest=prepared(tmp_path)
    def fake(*args):raise ValueError('source XML unavailable')
    result=generate(path,tmp_path/'run',source_generator=fake)
    assert result['data']['attempts']==0 and result['data']['qualified_trajectories']==0
    assert result['source_errors']==2 and result['completion_percent']==100
    assert result['data']['counts_by_domain']['10']['windows']==0
    assert result['status']=='completed_with_source_gaps'
