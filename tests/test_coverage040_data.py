"""Incremental040 contracts over tiny recorded HDF/JSON, never a simulator."""
from copy import deepcopy
import json
import shutil

import numpy as np
import pytest

from egrs.augmentation.data import identity, read_json, file_sha256, load_scope
from test_retention_data import prepared
from test_task_control_index import control_sources
from test_coverage039_data import coverage_inputs, seal_export, write


@pytest.fixture
def delta_inputs(coverage_inputs, tmp_path):
    from egrs.coverage039.merge import merge_exports
    from egrs.coverage039.index import build_indices
    old, new, retention = coverage_inputs
    merge_exports(old, new, tmp_path/'merged039')
    built = build_indices(tmp_path/'merged039', retention, tmp_path/'indices039')
    old_index = tmp_path/'indices039/task_control'
    old_manifest = read_json(old_index/'sources.json')
    old_report = read_json(old_index/'report.json')
    original = read_json(new/'sources.json')
    parents = deepcopy(original['parents'])
    prototype = deepcopy(next(p for p in parents if p['split']=='train'))
    candidates = []
    tasks = {t['key']:t for t in load_scope()['tasks']}
    for task in ('stove','mug_pudding','two_pots'):
        for number in range(20,40):
            p = deepcopy(prototype)
            p.update(task_key=task, file=f'{task}.hdf5', source_id=f'{task}.hdf5#demo_{number}',
                     parent_demo_id=f'{task}.hdf5#demo_{number}', episode=f'data/demo_{number}',
                     source_group=f'new-{task}-{number}', split='train' if task=='stove' and number==20 else 'dev',
                     active_goals=deepcopy(tasks[task]['active_goals']),
                     invariant_predicates=deepcopy(tasks[task]['invariant_predicates']))
            candidates.append(p)
    parents += candidates
    selected = candidates[0]
    plan = {'parents':parents,'candidates':candidates,'sources':[selected]}
    plan['identity'] = identity(plan)
    plan_path = tmp_path/'plan040.json'; write(plan_path,plan)
    ledger = {'format':'task039-attempt-ledger-v1','normal_attempts':1,'ten_attempts':1,
              'slots':[{'source_id':selected['source_id'],'domain':d,'variant':v,'attempt':0,
                        'status':'spent_before_initialization','reserved_unix_seconds':1}
                       for d,v in (('normal','normal'),('10',0))]}
    ledger_path = tmp_path/'ledger040.json';write(ledger_path,ledger)
    binding = {'format':'task040-generation-binding-v1','plan_identity':plan['identity'],
        'plan_path':str(plan_path),'plan_sha256':file_sha256(plan_path),
        'ledger_path':str(ledger_path),'ledger_sha256':file_sha256(ledger_path),
        'candidates':candidates,'selected_train_parent_ids':[selected['source_id']],
        'tasks':['stove','mug_pudding','two_pots'],'source_range':{'start':20,'stop':40},
        'train_only':True,'newnormal_role':'pair_only'}
    root=tmp_path/'new040';root.mkdir();export=root/'export';export.mkdir()
    manifest=deepcopy(original);manifest.update(parents=parents,data_root=str(root))
    context=manifest['generation_context'];context['plan_identity']=plan['identity'];context['coverage040']=binding
    sources={}; ids={}
    for sid,source in manifest['sources'].items():
        source=deepcopy(source);newid='new040-'+sid;ids[sid]=newid
        for field in ('file','audit_path','lineage_path'):
            shutil.copyfile(new.parent/source[field],root/source[field])
        source.update(source_id=newid,parent_demo_id=selected['source_id'],source_group=selected['source_group'],task_key='stove')
        source['generation_context']['plan_identity']=plan['identity']
        source['generation_context']['coverage040']=deepcopy(binding)
        source['recipe']['coverage040']=deepcopy(binding);source['recipe_identity']=identity(source['recipe'])
        lineage=read_json(root/source['lineage_path']);lineage['source']=deepcopy(selected)
        lineage['generation_context']=deepcopy(source['generation_context'])
        lineage['recipe']=deepcopy(source['recipe'])
        lineage['task_semantics']['official_goal_predicates']=[g['predicate'] for g in reversed(selected['active_goals'])]
        write(root/source['lineage_path'],lineage)
        sources[newid]=source
    manifest['sources']=sources
    rows=[json.loads(line) for line in (new/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows:
        row.update(source_id=ids[row['source_id']],parent_demo_id=selected['source_id'],source_group=selected['source_group'],task_key='stove')
    shutil.copyfile(new/'report.json',export/'report.json');seal_export(export,manifest,rows)
    return old_index,export,old_manifest,old_report


def module():
    try:
        from egrs.coverage040 import index
        return index
    except ImportError:
        pytest.fail('040 incremental index and pair-only dataset are not implemented')


def build(delta_inputs,tmp_path,monkeypatch):
    index=module();old,delta,manifest,report=delta_inputs
    monkeypatch.setattr(index,'_OLD_INDEX_IDENTITY',manifest['identity'])
    monkeypatch.setattr(index,'_OLD_REPORT_IDENTITY',report['identity'])
    monkeypatch.setattr(index,'_OLD_COUNTS',{p:{'train':1,'dev':1} for p in ('ten','fresh','raw')})
    monkeypatch.setattr(index,'_OLD_PAIR_COUNTS',{'train':1,'dev':1})
    return index.build_indices(old,delta,tmp_path/'indices040')


def selected_keys(dataset):
    from egrs.retention.training import dev_indices
    from egrs.task_control.sampling import dev_pair_indices
    selection=dev_indices(dataset.rows)
    def keys(indices):return [(dataset.rows[i]['source_id'],dataset.rows[i]['observation_index']) for i in indices]
    return {'ten':keys(selection['ten']),
            **{p:{b:keys(selection[p][b]) for b in ('prefix','all')} for p in ('fresh','raw')},
            'pairs':[dataset.pairs[i]['pair_id'] for i in dev_pair_indices(dataset.pairs)]}


def test_append_only_rows_and_pair_only_normal_keep_old_dev_selection(delta_inputs,tmp_path,monkeypatch):
    result=build(delta_inputs,tmp_path,monkeypatch)
    from egrs.coverage040.data import CoverageTaskControlDataset
    from egrs.coverage039.data import CoverageTaskControlDataset as OldDataset
    old=OldDataset(delta_inputs[0],'dev');dev=CoverageTaskControlDataset(result['task_control'],'dev')
    train=CoverageTaskControlDataset(result['task_control'],'train')
    assert selected_keys(dev)==selected_keys(old)
    assert dev.rows==old.rows and dev.pairs==old.pairs
    assert train.identity==dev.identity!=old.identity
    assert train.report['coverage040']['new_qualified_train10']==1
    assert len(train.rows)==10 and len(train.pairs)==2
    assert len(train.manifest['pair_sources'])==1
    assert all('pool' not in s for s in train.manifest['pair_sources'].values())
    assert not set(train.manifest['pair_sources']) & {r['source_id'] for r in train.rows}
    u,v=train.get_pair(1)
    np.testing.assert_allclose(u['actions'][0,0],-1/6,atol=1e-7)
    np.testing.assert_allclose(v['actions'][0,0],.5,atol=1e-7)
    assert u['count_label']==v['count_label']==1
    assert u['action_mask'].tolist()==[True]+[False]*7
    assert v['action_mask'].tolist()==[True,True]+[False]*6
    assert set(u)=={'images','proprio','instruction','actions','action_mask','count_label'}
    old_retention=read_json(delta_inputs[0]/'sources.json')['retention_index']
    from pathlib import Path
    assert (Path(result['retention'])/'rows.jsonl').read_bytes().startswith((Path(old_retention)/'rows.jsonl').read_bytes())
    assert (Path(result['task_control'])/'labels.jsonl').read_bytes().startswith((delta_inputs[0]/'labels.jsonl').read_bytes())
    assert (Path(result['task_control'])/'pairs.jsonl').read_bytes().startswith((delta_inputs[0]/'pairs.jsonl').read_bytes())
    old_sources=read_json(Path(old_retention)/'sources.json')['sources']
    assert all(train.sources[sid]==source for sid,source in old_sources.items())


def test_report_contains_per_task_old_new_actual_coverage(delta_inputs,tmp_path,monkeypatch):
    result=build(delta_inputs,tmp_path,monkeypatch)
    by_task=result['task_control_report']['coverage040']['by_task']
    assert by_task['stove']['train_parent_groups']=={'old':0,'new':1,'total':1}
    assert by_task['stove']['ten']['new']=={'train':1,'dev':0}
    assert by_task['stove']['ten_windows']['new']=={'train':2,'dev':0}
    assert by_task['basket']['pairs']['old']=={'train':1,'dev':1}


def test_missing_normal_is_only_a_pair_gap(delta_inputs,tmp_path,monkeypatch):
    _,delta,_,_=delta_inputs
    manifest=read_json(delta/'sources.json')
    manifest['sources']={sid:s for sid,s in manifest['sources'].items() if s['domain']=='10'}
    rows=[json.loads(line) for line in (delta/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
    seal_export(delta,manifest,[r for r in rows if r['domain']=='10'])
    result=build(delta_inputs,tmp_path,monkeypatch)
    assert result['task_control_report']['coverage040']['new_qualified_train10']==1
    assert result['task_control_report']['coverage040']['pair_gaps']=={'missing_qualified_normal_source':1}


def test_zero_qualified_delta_reports_zero_without_discarding_old_pairs(delta_inputs,tmp_path,monkeypatch):
    _,delta,_,_=delta_inputs
    manifest=read_json(delta/'sources.json');manifest['sources']={}
    seal_export(delta,manifest,[])
    result=build(delta_inputs,tmp_path,monkeypatch)
    assert result['task_control_report']['coverage040']['new_qualified_train10']==0
    assert result['task_control_report']['pairs']['valid']==2


@pytest.mark.parametrize('change,reason',[('nonrobot','recorded_nonrobot_state_changed'),('handoff','missing_outgoing_action')])
def test_new_pair_gap_preserves_qualified_bc(delta_inputs,tmp_path,monkeypatch,change,reason):
    _,delta,_,_=delta_inputs
    for source in read_json(delta/'sources.json')['sources'].values():
        if source['domain']!='10':continue
        path=delta.parent/source['audit_path'];audit=read_json(path)
        if change=='nonrobot':
            audit['frames'][0]['state'][2]+=.001
            lineage_path=delta.parent/source['lineage_path'];lineage=read_json(lineage_path)
            lineage['actual_initial_state']=deepcopy(audit['frames'][0]['state']);write(lineage_path,lineage)
        else:audit['handoff']['normal_state_index']=2
        write(path,audit)
    result=build(delta_inputs,tmp_path,monkeypatch)
    from egrs.coverage040.data import CoverageTaskControlDataset
    train=CoverageTaskControlDataset(result['task_control'],'train')
    assert len(train.rows)==10 and len(train.pairs)==1
    assert train.report['coverage040']['new_qualified_train10']==1
    assert train.report['coverage040']['pair_gaps'][reason]==1


@pytest.mark.parametrize('change',['mask','split','root','normalization','provenance'])
def test_delta_binding_rejects_invalid_source(delta_inputs,tmp_path,monkeypatch,change):
    _,delta,_,_=delta_inputs
    manifest=read_json(delta/'sources.json')
    rows=[json.loads(line) for line in (delta/'windows.jsonl').read_text(encoding='utf-8').splitlines()]
    source=next(s for s in manifest['sources'].values() if s['domain']=='10')
    if change=='mask':rows[-1]['action_mask']=[True]*8
    elif change=='split':source['split']='dev'
    elif change=='root':source['file']='../outside.hdf5'
    elif change=='normalization':source['mapping']['action_normalization']['stats_sha256']='0'*64
    else:source['generator_algorithm']='different'
    seal_export(delta,manifest,rows)
    with pytest.raises((ValueError,FileNotFoundError)):
        build(delta_inputs,tmp_path,monkeypatch)


def test_fixed_old039_identity_is_required(delta_inputs,tmp_path):
    with pytest.raises(ValueError,match='039|identity'):
        module().build_indices(delta_inputs[0],delta_inputs[1],tmp_path/'rejected')


def test_readers_share_live_hash_context_and_reject_stat_change(delta_inputs,tmp_path,monkeypatch):
    result=build(delta_inputs,tmp_path,monkeypatch)
    from egrs.coverage039.io import HashContext
    from egrs.coverage040.data import CoverageTaskControlDataset
    context=HashContext()
    CoverageTaskControlDataset(result['task_control'],'train',context=context)
    count=context.files_read
    CoverageTaskControlDataset(result['task_control'],'dev',context=context)
    assert context.files_read==count
    source=next(iter(read_json(delta_inputs[1]/'sources.json')['sources'].values()))
    with (delta_inputs[1].parent/source['file']).open('ab') as stream:stream.write(b' ')
    with pytest.raises(ValueError,match='stat|SHA|bytes'):
        CoverageTaskControlDataset(result['task_control'],'dev',context=context)
