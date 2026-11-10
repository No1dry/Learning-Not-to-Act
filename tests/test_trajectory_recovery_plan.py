"""Byte-only recovery planning; all evidence is synthetic and no native is started."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from egrs.augmentation.data import identity,file_sha256,read_json,load_scope
from test_trajectory_data import seed_manifest,mapping


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return str(path)


def seal_fixture_refs(config_path,refs):
    """Reseal deliberately synthetic evidence and its independent fake approval."""
    refs['identity']=identity(refs)
    write(Path(config_path).parent/'evidence.json',refs)
    write(Path(config_path).parent/'approved.json',refs)


def recovery_fixture(tmp_path,monkeypatch):
    import egrs.trajectory_augmentation.recovery_plan as module
    approved=read_json(Path(__file__).resolve().parents[1]/'collaboration/tasks/035_teacher_v2_recovery_refs.json')
    refs=deepcopy(approved);manifest=seed_manifest(tmp_path,count=0);sources=[];bindings={}
    stats=tmp_path/'stats.json';write(stats,{})
    for task in load_scope()['tasks']:
        for i in range(20):
            s=seed_manifest(tmp_path,count=1)['sources'][0]
            s.update({k:deepcopy(task[k]) for k in ('task_key',) if k in task})
            s['task_key']=task['key']
            s.update({k:deepcopy(task[k]) for k in ('official_task_name','active_goals','invariant_predicates')})
            s['file']=f"libero_10/{task['official_task_name']}_demo.hdf5"
            s['file_sha256']=hashlib.sha256(task['key'].encode()).hexdigest()
            s['source_id']=s['file']+f'#demo_{i}';s['episode']=f'data/demo_{i}';s['demo_index']=i
            for kind in ('action_normalization','proprio_normalization'):
                s['mapping'][kind]['stats_sha256']=file_sha256(stats)
            sources.append(s)
        bindings[task['key']]={k:deepcopy(task[k]) for k in ('official_task_name','active_goals','invariant_predicates')}
        bindings[task['key']].update(orientation='opengl',state_field='states',state_alignment_basis='synthetic',
            alignment={'rule':'same_state','orientation':'identity','state_offset':0,'observation_offset':0,'action_offset':0})
    manifest['sources']=sources
    manifest_path=tmp_path/'seeds.json';write(manifest_path,manifest)
    from egrs.trajectory_augmentation.cli import RECIPE,build_plan
    cfg={'format':'task035-generation-config-v1','manifest':str(manifest_path),'benchmark_root':str(tmp_path/'unopened-core'),
        'stats_path':str(stats),'stats_sha256':file_sha256(stats),'unnorm_key':'libero_10','recipe':RECIPE,
        'native_backend':{'kind':'native','historical_root':str(tmp_path/'unopened-native'),'python':'venv/bin/python'},
        'bindings':bindings}
    cfg_path=tmp_path/'original.json';write(cfg_path,cfg);original_plan=build_plan(cfg_path)
    parents={s['source_id']:s for s in original_plan['sources']}
    legacy=tmp_path/'generated-002';legacy.mkdir()
    for c in refs['candidates']:
        p=parents[c['parent_demo_id']];assert p['split']==c['split']
        folder=legacy/'artifacts'/c['artifact_source']/'normal_vnormal_a0'
        q={'qualified':False,'failure_reason':'core_violation_evidence_unknown',
            'core_analysis':{'event_unknown':[{'step':0,'event':'table_drop','object':'fake'}],'confirmed_events':[]},
            'core_release_confirmation_streak':5,'domain':'normal'}
        metadata={'source_id':p['source_id']+'__normal__vnormal__a0','parent_demo_id':p['source_id'],
            'task_key':p['task_key'],'split':p['split'],'domain':'normal','variant':'normal','attempt':0,
            'qualified':False,'status':'rejected','failure_reason':q['failure_reason'],'file':None,
            'qualification':{'accepted':False,**q},'parent_file_sha256':p['file_sha256']}
        c['qualification_file']=write(folder/'qualification.json',q)
        c['qualification_sha256']=file_sha256(c['qualification_file'])
        c['metadata_file']=write(folder/'metadata.json',metadata)
        c['metadata_sha256']=file_sha256(c['metadata_file'])
    reused={}
    for r in refs['reused_sources']:
        p=parents[r['parent_demo_id']];assert p['split']=='train'
        row={'source_id':r['source_id'],'parent_demo_id':p['source_id'],'task_key':p['task_key'],
            'split':p['split'],'source_group':p['source_group'],'domain':r['domain'],'length':r['length'],
            'variant':'normal' if r['domain']=='normal' else int(r['source_id'].rsplit('__v',1)[1].split('__')[0]),
            'attempt':0,'qualified':True,'status':'completed','failure_reason':None,
            'instruction':p['instruction'],'parent_file_sha256':p['file_sha256'],'mapping':deepcopy(p['mapping']),
            'provenance':'ordinary_reexecuted' if r['domain']=='normal' else 'counterfactual_generated_from_demo',
            'qualification':{'accepted':True,'qualified':True,'failure_reason':None},'episode':'data/demo_0'}
        for key,f in r['files'].items():
            target=legacy/f['relative_path'];target.parent.mkdir(parents=True,exist_ok=True)
            if key=='file':target.write_bytes(b'synthetic byte-only HDF; never opened by plan')
            elif key=='qualification_path':write(target,{'qualified':True,'failure_reason':None})
            else:write(target,{'synthetic':True,'source_id':r['source_id']})
            f.update(bytes=target.stat().st_size,sha256=file_sha256(target));row[key]=f['relative_path']
        r['file_sha256']=r['files']['file']['sha256'];row['file_sha256']=r['file_sha256']
        reused[r['source_id']]=row
    export={'format':'task035-generated-trajectories-v1','data_root':str(legacy),
        'parents':deepcopy(original_plan['sources']),'sources':reused}
    export['identity']=identity(export)
    export_path=legacy/'export/sources.json';write(export_path,export)
    refs.update(legacy_run_root=str(legacy))
    for key,path in [('original_seed_manifest',manifest_path),('original_generation_config',cfg_path),('reused_export_sources',export_path)]:
        refs[key].update(path=str(path),sha256=file_sha256(path))
    for key in ('candidate_analysis','reused_file_references'):
        target=tmp_path/(key+'.json');write(target,{'synthetic':True})
        refs[key].update(path=str(target),sha256=file_sha256(target))
    for key in ('generation_report','export_report'):
        target=legacy/('generation_report.json' if key=='generation_report' else 'export/report.json')
        write(target,{'synthetic':True});refs['legacy_reports'][key+'_sha256']=file_sha256(target)
    config_path=tmp_path/'recovery.json'
    write(config_path,{'format':'task035-teacher-v2-recovery-config-v1','evidence':'evidence.json','path_roots':{}})
    seal_fixture_refs(config_path,refs)
    monkeypatch.setattr(module,'APPROVED_REFS',tmp_path/'approved.json')
    return config_path,manifest,refs


def test_plan_validates_original180_before_exact73_and_preserves_split(tmp_path,monkeypatch):
    import egrs.trajectory_augmentation.recovery_plan as module
    config,manifest,refs=recovery_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr('h5py.File',lambda *a,**k:pytest.fail('plan opened HDF content'))
    plan=module.build_recovery_plan(config)
    assert len(plan['original_plan']['sources'])==180 and len(plan['sources'])==73
    assert Counter(s['split'] for s in plan['sources'])=={'train':53,'dev':20}
    original={s['source_id']:s for s in plan['original_plan']['sources']}
    assert all(s==original[s['source_id']] for s in plan['sources'])
    assert len(plan['reused_sources'])==8 and len({s['parent_demo_id'] for s in plan['reused_sources']})==2
    assert not {s['parent_demo_id'] for s in plan['reused_sources']}&{s['source_id'] for s in plan['sources']}
    assert plan['population']['max_normal_replays']==73 and plan['population']['max_10_attempts']==438
    assert plan['simulation_created'] is False and plan['model_loaded'] is False


@pytest.mark.parametrize('mutation',['candidate_set','qualification_bytes','other_unknown','confirmed','streak','split','reuse_bytes','reuse_split','seed_gap'])
def test_bad_bound_evidence_has_no_fallback(tmp_path,monkeypatch,mutation):
    import egrs.trajectory_augmentation.recovery_plan as module
    config,manifest,refs=recovery_fixture(tmp_path,monkeypatch)
    candidate=refs['candidates'][0]
    if mutation=='candidate_set':
        refs['candidates'].pop();refs['identity']=identity(refs);write(tmp_path/'evidence.json',refs)
    elif mutation=='qualification_bytes':
        write(candidate['qualification_file'],{})
    elif mutation in ('other_unknown','confirmed','streak'):
        q=read_json(candidate['qualification_file'])
        if mutation=='other_unknown':q['core_analysis']['event_unknown'][0]['event']='wrong_grasp'
        if mutation=='confirmed':q['core_analysis']['confirmed_events']=[{'event':'table_drop'}]
        if mutation=='streak':q['core_release_confirmation_streak']=4
        write(candidate['qualification_file'],q);candidate['qualification_sha256']=file_sha256(candidate['qualification_file'])
        seal_fixture_refs(config,refs)
    elif mutation=='split':
        candidate['split']='train' if candidate['split']=='dev' else 'dev';seal_fixture_refs(config,refs)
    elif mutation=='reuse_bytes':
        f=refs['reused_sources'][0]['files']['file'];(Path(refs['legacy_run_root'])/f['relative_path']).write_bytes(b'changed')
    elif mutation=='reuse_split':
        export_path=refs['reused_export_sources']['path'];export=read_json(export_path)
        export['sources'][refs['reused_sources'][0]['source_id']]['split']='dev';export['identity']=identity(export)
        write(export_path,export);refs['reused_export_sources']['sha256']=file_sha256(export_path);seal_fixture_refs(config,refs)
    elif mutation=='seed_gap':
        manifest['sources'].pop(3);write(refs['original_seed_manifest']['path'],manifest)
        refs['original_seed_manifest']['sha256']=file_sha256(refs['original_seed_manifest']['path']);seal_fixture_refs(config,refs)
    with pytest.raises((ValueError,FileNotFoundError)):
        module.build_recovery_plan(config)
