"""Task039 merge and indices consume only tiny synthetic recordings."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from egrs.augmentation.data import file_sha256, identity, read_json
from test_retention_data import prepared
from test_task_control_index import control_sources


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def seal_export(path,manifest,rows):
    content=''.join(json.dumps(r)+'\n' for r in rows)
    (path/'windows.jsonl').write_text(content,encoding='utf-8')
    manifest['identity']=identity(manifest);write(path/'sources.json',manifest)
    report=read_json(path/'report.json');report['sources_identity']=manifest['identity']
    report['windows_sha256']=file_sha256(path/'windows.jsonl')
    report['counts_by_domain']={d:{'trajectories':sum(s['domain']==d for s in manifest['sources'].values())} for d in ('normal','10')}
    report['identity']=identity(report);write(path/'report.json',report)


@pytest.fixture
def coverage_inputs(control_sources,tmp_path,monkeypatch):
    from egrs.coverage039 import merge,data
    from egrs.coverage039.recipe import generation_context,recipe_for,ALGORITHM
    from egrs.coverage039.permutation import _sha
    from egrs.trajectory_augmentation.native import TEACHER_V2
    import numpy as np
    monkeypatch.setattr(merge,'_EXPECTED_OLD',{'10':1,'normal':1})
    monkeypatch.setattr(merge,'_EXPECTED_PARENTS',2)
    monkeypatch.setattr(merge,'_TASKS',('basket',),raising=False)
    monkeypatch.setattr(data,'_RAW_COUNTS',{'train':1,'dev':1})
    old,retention=control_sources
    all_manifest=read_json(old/'sources.json')
    all_rows=[json.loads(line) for line in (old/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
    newroot=tmp_path/'new039';newroot.mkdir();new=newroot/'export';new.mkdir()
    manifest=deepcopy(all_manifest);manifest['data_root']=str(newroot.resolve())
    manifest['sources']={sid:s for sid,s in manifest['sources'].items() if s['split']=='train'}
    manifest['generation_context']=generation_context('f'*64,normal_attempts=1,ten_attempts=1)
    rows=[r for r in all_rows if r['split']=='train']
    for source in manifest['sources'].values():
        for key in ('file','audit_path','lineage_path'):
            shutil.copyfile(old.parent/source[key],newroot/source[key])
    normal=next(s for s in manifest['sources'].values() if s['domain']=='normal')
    state=np.asarray(read_json(newroot/normal['lineage_path'])['actual_initial_state'],dtype=float)
    transform={'kind':'identity','applied_at':'before_initial_restore',
        'original_initial_state_sha256':_sha(state),'transformed_initial_state_sha256':_sha(state),
        'modified_indices':[],'non_target_before_sha256':_sha(state),'non_target_after_sha256':_sha(state),'objects':[]}
    for source in manifest['sources'].values():
        recipe=recipe_for({});recipe['initialization_transform']=deepcopy(transform)
        context=generation_context('f'*64);context['initialization_transform']=deepcopy(transform)
        extra={'teacher_policy':TEACHER_V2,'generator_algorithm':ALGORITHM,'recipe':recipe,
               'initialization_transform':deepcopy(transform),'generation_context':context}
        source.update(deepcopy(extra),recipe_identity=identity(recipe))
        source['qualification']['teacher_policy']=TEACHER_V2
        lineage=read_json(newroot/source['lineage_path']);lineage.update(deepcopy(extra))
        write(newroot/source['lineage_path'],lineage)
    shutil.copyfile(old/'report.json',new/'report.json')
    seal_export(new,manifest,rows)
    old_manifest=deepcopy(all_manifest)
    old_manifest['sources']={sid:s for sid,s in old_manifest['sources'].items() if s['split']=='dev'}
    seal_export(old,old_manifest,[r for r in all_rows if r['split']=='dev'])
    ret=read_json(retention/'sources.json')
    ret['sources']={sid:s for sid,s in ret['sources'].items() if s['pool']=='raw' or s['split']=='dev'}
    rows=[json.loads(line) for line in (retention/'rows.jsonl').read_text(encoding='utf-8').splitlines()]
    rows=[r for r in rows if r['source_id'] in ret['sources']]
    (retention/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    for name in ('sources.json','report.json','windows.jsonl'):
        ret['inputs'][str((old/name).resolve())]=file_sha256(old/name)
    ret['identity']=identity(ret);write(retention/'sources.json',ret)
    report=read_json(retention/'report.json');report['sources_identity']=ret['identity']
    report['rows_sha256']=file_sha256(retention/'rows.jsonl');report['identity']=identity(report)
    write(retention/'report.json',report)
    return old,new,retention


def test_merge_dynamic_indices_preserve_old_and_feed_038_pairs(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports
    from egrs.coverage039.index import build_indices
    from egrs.coverage039.data import CoverageTaskControlDataset
    from egrs.coverage039.io import HashContext
    from egrs.task_control.data import TaskControlDataset
    old,new,retention=coverage_inputs
    old_bytes={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    context=HashContext();merged=tmp_path/'merged'
    merge_exports(old,new,merged,context=context)
    manifest=read_json(merged/'sources.json')
    assert manifest['parents']==read_json(old/'sources.json')['parents']
    assert len(manifest['sources'])==4
    assert set(manifest['allowed_data_roots'])=={'old003','new039'}
    assert all(p.read_bytes()==content for p,content in old_bytes.items())
    result=build_indices(merged,retention,tmp_path/'indices',context=context)
    data=CoverageTaskControlDataset(result['task_control'],'train',context=context)
    assert len(data.rows)==8 and len(data.pairs)==1
    assert data.report['data_kind']=='task038-task-control-data-v1'
    assert data.report['coverage039']['new_qualified_train10']==1
    u,v=data.get_pair(0)
    assert u['count_label']==v['count_label']==1
    assert u['action_mask'].tolist()==[True]+[False]*7
    assert v['action_mask'].tolist()==[True,True]+[False]*6
    assert set(data[0]) <= {'images','proprio','instruction','actions','action_mask','count_label'}
    before=context.files_read
    CoverageTaskControlDataset(result['task_control'],'dev',context=context)
    assert context.files_read==before
    with pytest.raises(ValueError,match='identity|kind'):
        TaskControlDataset(result['task_control'])


def test_merge_rejects_old_count_contract_without_private_fixture_seam(coverage_inputs,tmp_path,monkeypatch):
    from egrs.coverage039 import merge
    old,new,_=coverage_inputs
    monkeypatch.setattr(merge,'_EXPECTED_OLD',{'10':221,'normal':75})
    with pytest.raises(ValueError,match='221|counts|old003'):
        merge.merge_exports(old,new,tmp_path/'bad')


def test_merged_artifact_cannot_escape_two_allowlisted_roots(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports,read_merged
    old,new,_=coverage_inputs
    output=tmp_path/'merged';merge_exports(old,new,output)
    manifest=read_json(output/'sources.json')
    source=next(iter(manifest['sources'].values()))
    source['file']='outside.hdf5'
    manifest['identity']=identity(manifest);write(output/'sources.json',manifest)
    report=read_json(output/'report.json');report['sources_identity']=manifest['identity']
    report['identity']=identity(report);write(output/'report.json',report)
    with pytest.raises(ValueError,match='allowlist|artifact|root'):
        read_merged(output)


def test_merge_rejects_resealed_old_qualification_rewrite(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports,read_merged
    old,new,_=coverage_inputs;output=tmp_path/'merged';merge_exports(old,new,output)
    manifest=read_json(output/'sources.json')
    source=next(s for s in manifest['sources'].values() if s['coverage039_origin']['release']=='old003')
    source['qualification']['rejudged']=True
    source['coverage039_origin']['original_source']['qualification']['rejudged']=True
    manifest['identity']=identity(manifest);write(output/'sources.json',manifest)
    report=read_json(output/'report.json');report['sources_identity']=manifest['identity']
    report['identity']=identity(report);write(output/'report.json',report)
    with pytest.raises(ValueError,match='original|qualification|release'):
        read_merged(output)


def test_new_train_count_cannot_be_resealed_to_make_old_data_trainable(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports,read_merged
    old,new,_=coverage_inputs;output=tmp_path/'merged';merge_exports(old,new,output)
    manifest=read_json(output/'sources.json');manifest['coverage039']['new_qualified_train10']=999
    manifest['identity']=identity(manifest);write(output/'sources.json',manifest)
    report=read_json(output/'report.json');report['sources_identity']=manifest['identity']
    report['coverage039']['new_qualified_train10']=999
    report['identity']=identity(report);write(output/'report.json',report)
    with pytest.raises(ValueError,match='count|coverage'):
        read_merged(output)


def test_retention_raw_root_stays_bound_to_original_not_identical_copy(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports
    from egrs.coverage039.index import build_indices
    from egrs.coverage039.data import CoverageRetentionDataset
    old,new,retention=coverage_inputs;merged=tmp_path/'merged';merge_exports(old,new,merged)
    result=build_indices(merged,retention,tmp_path/'indices')
    directory=Path(result['retention']);manifest=read_json(directory/'sources.json')
    replacement=tmp_path/'replacement';replacement.mkdir()
    shutil.copytree(Path(manifest['data_roots']['raw'])/'libero_10',replacement/'libero_10')
    manifest['data_roots']['raw']=str(replacement.resolve())
    manifest['identity']=identity(manifest);write(directory/'sources.json',manifest)
    report=read_json(directory/'report.json');report['sources_identity']=manifest['identity']
    report['identity']=identity(report);write(directory/'report.json',report)
    with pytest.raises(ValueError,match='raw|original'):
        CoverageRetentionDataset(directory)


def test_retention_cannot_rebind_ten_row_to_another_outgoing_action(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports
    from egrs.coverage039.index import build_indices
    from egrs.coverage039.data import CoverageRetentionDataset
    old,new,retention=coverage_inputs;merged=tmp_path/'merged';merge_exports(old,new,merged)
    result=build_indices(merged,retention,tmp_path/'indices')
    directory=Path(result['retention'])
    rows=[json.loads(line) for line in (directory/'rows.jsonl').read_text(encoding='utf-8').splitlines()]
    row=next(r for r in rows if r['pool']=='ten' and r['observation_index']==0)
    row['original_row']['start']=1
    (directory/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    report=read_json(directory/'report.json');report['rows_sha256']=file_sha256(directory/'rows.jsonl')
    report['identity']=identity(report);write(directory/'report.json',report)
    with pytest.raises(ValueError,match='outgoing|expert|row'):
        CoverageRetentionDataset(directory)


def test_merge_reports_actual_task_split_attempts_new_and_reused(coverage_inputs,tmp_path):
    from egrs.coverage039.merge import merge_exports
    old,new,_=coverage_inputs
    report=merge_exports(old,new,tmp_path/'merged')
    table=report['coverage039']['task_split_domain']
    assert table['basket|train|10']['success']==1
    assert table['basket|train|10']['new']==1
    assert table['basket|dev|10']['reused']==1
    assert table['two_pots|train|10']['success']==0
    assert table['basket|train|10']['windows']==2
    assert table['basket|dev|10']['by_release']['old003']['attempts']==1


@pytest.mark.parametrize('fault',['old_copy','task','teacher','algorithm','recipe','context','lineage_transform'])
def test_new039_requires_bound_generator_provenance_not_format_only(coverage_inputs,tmp_path,monkeypatch,fault):
    from egrs.coverage039 import merge
    old,new,_=coverage_inputs
    manifest=read_json(new/'sources.json')
    if fault=='task':monkeypatch.setattr(merge,'_TASKS',('stove','mug_pudding','two_pots'))
    for source in manifest['sources'].values():
        lineage=read_json(new.parent/source['lineage_path'])
        if fault=='old_copy':
            for key in ('teacher_policy','generator_algorithm','recipe','recipe_identity','generation_context','initialization_transform'):
                source.pop(key,None);lineage.pop(key,None)
            manifest['generation_context']={'format':'task039-generation-context-v1'}
        elif fault=='teacher':source['teacher_policy']='old_v1'
        elif fault=='algorithm':source['generator_algorithm']='old_generator'
        elif fault=='recipe':
            source['recipe']['version']='old_recipe';source['recipe_identity']=identity(source['recipe'])
        elif fault=='context':source['generation_context']['plan_identity']='e'*64
        elif fault=='lineage_transform':lineage['initialization_transform']['kind']='changed'
        write(new.parent/source['lineage_path'],lineage)
    rows=[json.loads(line) for line in (new/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
    seal_export(new,manifest,rows)
    with pytest.raises(ValueError,match='039|provenance|teacher|recipe|transform'):
        merge.merge_exports(old,new,tmp_path/'rejected')


def test_two_pots_cannot_claim_new039_with_identity_initialization(coverage_inputs,tmp_path,monkeypatch):
    from egrs.coverage039 import merge
    old,new,_=coverage_inputs;monkeypatch.setattr(merge,'_TASKS',('two_pots',))
    for directory in (old,new):
        manifest=read_json(directory/'sources.json')
        for parent in manifest['parents']:
            if parent['split']=='train':parent['task_key']='two_pots'
        for source in manifest['sources'].values():
            if source['split']=='train':
                source['task_key']='two_pots'
                path=directory.parent/source['lineage_path'];lineage=read_json(path)
                lineage['source']['task_key']='two_pots';write(path,lineage)
        rows=[json.loads(line) for line in (directory/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
        for row in rows:
            if row['split']=='train':row['task_key']='two_pots'
        seal_export(directory,manifest,rows)
        if (directory/'attempts.json').exists():
            attempts=read_json(directory/'attempts.json')
            for attempt in attempts:
                if attempt['split']=='train':attempt['task_key']='two_pots'
            write(directory/'attempts.json',attempts)
    with pytest.raises(ValueError,match='two_pots|transform|swap'):
        merge.merge_exports(old,new,tmp_path/'rejected')


def test_new039_accepts_recorded_complete_two_pots_swap_evidence():
    from egrs.coverage039.merge import _validate_new_transform
    from egrs.coverage039.permutation import prepare_initial
    from test_coverage039_permutation import session
    world,_=session();parent={'task_key':'two_pots'}
    state,evidence=prepare_initial(world,parent)
    _validate_new_transform(parent,evidence,{'state':state.tolist()})
    evidence['non_target_after_sha256']='0'*64
    with pytest.raises(ValueError,match='swap|non-target'):
        _validate_new_transform(parent,evidence,{'state':state.tolist()})
