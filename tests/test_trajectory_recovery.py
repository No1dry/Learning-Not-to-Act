"""Recovery orchestration with synthetic HDF and fake source workers only."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from egrs.augmentation.data import file_sha256, identity, read_json
from egrs.trajectory_augmentation.data import validate_seeds, GeneratedTrajectoryDataset
from test_trajectory_data import seed_manifest, attempts_for

V2='table-drop-unknown-diagnostic-v2'


def run_fixture(tmp_path,monkeypatch):
    from egrs.trajectory_augmentation import recovery
    parents=validate_seeds(seed_manifest(tmp_path,count=12))
    old=[p for p in parents if p['split']=='train'][:2]
    remaining=[p for p in parents if p not in old]
    new=[next(p for p in remaining if p['split']=='dev'),
         next(p for p in remaining if p['split']=='train')]
    legacy=tmp_path/'legacy';legacy.mkdir()
    stats=tmp_path/'stats.json';stats.write_text('{}',encoding='utf-8')
    reused=attempts_for(legacy,old,T=2);refs=[]
    for row in reused:
        row.pop('audit')
        files={'file':{'relative_path':row['file'],'sha256':row['file_sha256']}}
        for key in ('audit_path','qualification_path','lineage_path','journal_path'):
            artifact=legacy/(row['source_id']+'-'+key+'.json')
            artifact.write_text(json.dumps({'qualified':True,'original_v1':True}),encoding='utf-8')
            row[key]=artifact.name
            files[key]={'relative_path':artifact.name,'sha256':file_sha256(artifact)}
        for ref in files.values():ref['bytes']=(legacy/ref['relative_path']).stat().st_size
        refs.append({'source_id':row['source_id'],'files':files})
    plan={'original_plan':{'sources':parents,'config':{'recipe':{},'native_backend':{},
        'stats_path':str(stats),'stats_sha256':file_sha256(stats)},'data_root':str(tmp_path)},
        'sources':new,'reused_sources':reused,'legacy_root':str(legacy),
        'evidence':{'reused_sources':refs,'teacher_policy':V2,'identity':'a'*64,
            'reused_export_sources':{'sha256':'b'*64}},
        'population':{'max_normal_replays':2,'max_robot_starts':6,'max_10_attempts':12},'identity':'c'*64}
    monkeypatch.setattr(recovery,'build_recovery_plan',lambda _:deepcopy(plan))
    return recovery,plan


def fake_source(source,config,data_root,output_dir):
    assert config['teacher_policy']==V2
    rows=attempts_for(output_dir,[source],T=3)
    for row in rows:
        row['teacher_policy']=V2
        row['qualification'].update(teacher_policy=V2)
        row.pop('audit')
    return {'source_id':source['source_id'],'attempts':rows,'error':None,'gaps':[]}


def test_recovery_reuses_bytes_executes_only_selected_and_seals_mixed_identity(tmp_path,monkeypatch,capsys):
    recovery,plan=run_fixture(tmp_path,monkeypatch);calls=[]
    def worker(source,*args):
        calls.append(source['source_id']);return fake_source(source,*args)
    out=tmp_path/'new-run'
    result=recovery.recover('fake-config',out,source_generator=worker)
    assert calls==[p['source_id'] for p in plan['sources']]
    assert result['new_execution']['attempts']==4
    assert result['reused']['trajectories']==4 and result['reused']['parent_sources']==2
    assert result['training_ready'] is True
    manifest=read_json(out/'export/sources.json')
    assert manifest['generation_context']['teacher_policy']==V2
    assert manifest['generation_context']['recovery_plan_identity']==plan['identity']
    assert identity(manifest)==manifest['identity']
    assert len(manifest['sources'])==8
    for old in plan['reused_sources']:
        row=manifest['sources'][old['source_id']]
        assert row['qualification']==old['qualification']
        assert row['mapping']==old['mapping'] and row['split']==old['split']
        assert row['reused_from_generated002']['new_execution'] is False
        for key in ('file','audit_path','qualification_path','lineage_path','journal_path'):
            assert file_sha256(out/row[key])==file_sha256(Path(plan['legacy_root'])/old[key])
            assert not (out/row[key]).is_symlink()
    dataset=GeneratedTrajectoryDataset(out/'export')
    assert set(dataset[0])=={'images','proprio','instruction','actions','action_mask'}
    lines=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[-1]['training_ready'] is True and lines[-1]['reused_trajectories']==4
    assert lines[0]['processed_sources']==1 and lines[0]['planned_sources']==2


def test_rejected_new_prefix_retained_but_not_indexed_and_no_empty_pool_fallback(tmp_path,monkeypatch):
    recovery,plan=run_fixture(tmp_path,monkeypatch)
    def rejected(source,*args):
        result=fake_source(source,*args)
        for row in result['attempts']:
            row.update(qualified=False,status='rejected',failure_reason='unfinished')
            row['qualification']['accepted']=False
        return result
    out=tmp_path/'rejected'
    result=recovery.recover('fake-config',out,source_generator=rejected)
    assert result['new_execution']['attempts']==4 and result['new_execution']['qualified_trajectories']==0
    assert result['training_ready'] is False
    manifest=read_json(out/'export/sources.json')
    assert set(manifest['sources'])=={r['source_id'] for r in plan['reused_sources']}
    rejected_rows=[r for r in read_json(out/'export/attempts.json') if not r['qualified']]
    assert len(rejected_rows)==4 and all((out/r['file']).is_file() for r in rejected_rows)


def test_recovery_rejects_old_output_and_changed_reuse_before_new_worker(tmp_path,monkeypatch):
    recovery,plan=run_fixture(tmp_path,monkeypatch)
    fail=lambda *a:pytest.fail('worker called before immutable reuse validation')
    with pytest.raises(ValueError,match='legacy'):
        recovery.recover('fake-config',Path(plan['legacy_root'])/'nested',source_generator=fail)
    existing=tmp_path/'exists';existing.mkdir()
    with pytest.raises(FileExistsError):recovery.recover('fake-config',existing,source_generator=fail)
    old=plan['reused_sources'][0]
    (Path(plan['legacy_root'])/old['file']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='reused'):
        recovery.recover('fake-config',tmp_path/'changed',source_generator=fail)


def test_exact73_full_plan_to_reuse8_and_new_fake_export(tmp_path,monkeypatch):
    from egrs.trajectory_augmentation.recovery import recover
    from test_trajectory_recovery_plan import recovery_fixture,seal_fixture_refs,write
    config,_,refs=recovery_fixture(tmp_path,monkeypatch)
    legacy=Path(refs['legacy_run_root'])
    exported=read_json(refs['reused_export_sources']['path'])
    parents={p['source_id']:p for p in exported['parents']}
    stage=tmp_path/'synthetic-hdf';stage.mkdir()
    for ref in refs['reused_sources']:
        parent=deepcopy(parents[ref['parent_demo_id']]);parent['source_id']='template'
        rows=attempts_for(stage,[parent],T=ref['length'])
        row=next(r for r in rows if r['domain']==ref['domain'])
        target=legacy/ref['files']['file']['relative_path']
        shutil.copy2(stage/row['file'],target)
        binding=ref['files']['file'];binding.update(bytes=target.stat().st_size,sha256=file_sha256(target))
        ref['file_sha256']=binding['sha256']
        exported['sources'][ref['source_id']]['file_sha256']=binding['sha256']
    exported['identity']=identity(exported);write(refs['reused_export_sources']['path'],exported)
    refs['reused_export_sources']['sha256']=file_sha256(refs['reused_export_sources']['path'])
    seal_fixture_refs(config,refs)
    called=[]
    def worker(parent,cfg,data_root,folder):
        called.append(parent['source_id'])
        template=deepcopy(parent);template['source_id']='synthetic'
        result=fake_source(template,cfg,data_root,folder)
        result['source_id']=parent['source_id']
        for row in result['attempts']:
            row['source_id']=parent['source_id']+'__'+row['domain']+'__fake'
            row['parent_demo_id']=parent['source_id']
        return result
    out=tmp_path/'generated-003-fake'
    result=recover(config,out,source_generator=worker)
    assert len(called)==73 and set(called)=={c['parent_demo_id'] for c in refs['candidates']}
    assert not set(called)&{r['parent_demo_id'] for r in refs['reused_sources']}
    assert result['population']['original_parent_sources']==180
    assert result['population']['recovery_split']=={'train':53,'dev':20}
    assert result['population']['max_10_attempts']==438
    assert result['new_execution']['attempts']==146
    assert result['reused']['trajectories']==8 and result['reused']['parent_sources']==2
    assert result['merged_data']['qualified_trajectories']==154
    assert result['training_ready'] is True and result['source_errors']==0
    assert len(GeneratedTrajectoryDataset(out/'export',split='dev',domains=['10']))==60
