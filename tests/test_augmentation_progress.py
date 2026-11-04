"""Sparse progress evidence, synthetic HDF/backend only; no native experiment."""
import copy
import json
from pathlib import Path

import pytest

from test_augmentation_data import fixture


def config_for(manifest, *, base=False):
    source = manifest['sources'][0 if base else 200]
    goals = copy.deepcopy(manifest['sources'][200]['active_goals'])
    return {'format':'egrs.augmentation.progress-config.v1',
            'backend':{'kind':'native','historical_root':'not-constructed-in-fake-tests'},
            'selection':{'start':0,'stride':4,'max_anchors_per_source':3},
            'task_bindings':{}, 'source_bindings':{source['source_id']:{
                'active_goals':goals,'invariant_predicates':[],
                'official_task_name':manifest['sources'][200]['official_task_name'],
                'state_field':'states','state_alignment_basis':'synthetic paired source-state/RGB audit',
                'orientation':'opengl','alignment':{'rule':'same_state','orientation':'identity',
                    'state_offset':0,'action_offset':1,'observation_offset':0}}}}


class FakeBackend:
    constructions = []
    calls = []
    def __init__(self, config, source, data_root, binding, goals=None):
        self.source,self.binding = source,binding
        self.inspection = {'dependency':{'accepted_revision':'synthetic-only'},
                           'native':{'xml_validation':'synthetic'},'simulation_created':False}
        type(self).constructions.append(source['source_id'])
    def inspect_anchor(self,t):
        type(self).calls.append(t)
        values = {'A':t>=4,'B':t>=8}
        return {'reliable':True,'pending_goals':[k for k,v in values.items() if not v],
                'native_facts':{'goal_values':values,'invariant_values':[],
                    'final_goal_atoms':[g['predicate'] for g in self.binding['active_goals']]},
                'correspondence':{'accepted':True,'camera_residuals':{'agentview':0.,'wrist':0.}},
                'state_binding':{'state_field':'states','observation_index':t,'action_index':t+1,
                    'restored_state_index':t,'state_sha256':'a'*64},'diagnostics':{'synthetic':True}}
    def close(self): pass


def test_plan_is_metadata_only_and_bounds_restores(tmp_path,monkeypatch):
    from egrs.augmentation.progress import plan_progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    sources=data.validate_manifest(manifest,inventory)
    monkeypatch.setattr('h5py.File',lambda *a,**k:pytest.fail('plan opened HDF'))
    plan=plan_progress(config_for(manifest),sources,manifest['data_root'])
    assert plan['source_plans'][0]['anchors']==[0,4,8]
    assert plan['planned_anchors']==3 and plan['maximum_restores']==12
    assert plan['simulation_created'] is False
    assert plan['source_plans'][0]['source']['split']==sources[200]['split']


def test_same_export_produces_exact_anchor_rows_no_interpolation_and_no_atomic(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    FakeBackend.calls=[];FakeBackend.constructions=[]
    out=tmp_path/'export'
    report=data.export_dataset(manifest,inventory,out,progress_config=config_for(manifest))
    ds=data.AugmentationDataset(out)
    rows=[r for r in ds.rows if r['view']=='PROGRESS']
    assert [r['start'] for r in rows]==[0,4]
    assert rows[0]['stop']==8 and rows[0]['action_mask']==[True]*8
    assert rows[1]['stop']==12 and rows[1]['action_mask']==[True]*8
    assert all(r['instruction']=='full instruction' for r in rows)
    assert not any(r['view']=='ATOMIC' for r in ds.rows)
    assert FakeBackend.calls==[0,4,8]
    assert report['counts_by_view']['PROGRESS']['windows']==2
    assert report['base_sources']=={'train':160,'dev':40}
    assert report['progress_production']['terminal_anchors']==1
    item=ds[next(i for i,r in enumerate(ds.rows) if r['view']=='PROGRESS')]
    assert set(item)=={'images','proprio','actions','action_mask','instruction'}
    assert item['actions'][:,0].tolist()==list(range(1,9))


def test_base_compound_native_goals_can_produce_progress_without_relabeling_split(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    out=tmp_path/'base_export'
    data.export_dataset(manifest,inventory,out,progress_config=config_for(manifest,base=True))
    rows=data.AugmentationDataset(out,views=['PROGRESS']).rows
    assert len(rows)==2 and {r['source_id'] for r in rows}=={'base0'}
    assert {r['split'] for r in rows}=={'train'}


def test_unreliable_or_inconsistent_anchor_stays_raw_with_diagnostics(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    class Bad(FakeBackend):
        def inspect_anchor(self,t):
            result=super().inspect_anchor(t)
            if t==0:result['correspondence']['accepted']=False
            if t==4:result['pending_goals']=['A']
            return result
    monkeypatch.setattr(progress,'NativeProgressBackend',Bad)
    report=data.export_dataset(manifest,inventory,tmp_path/'bad',progress_config=config_for(manifest))
    assert report['counts_by_view']['PROGRESS']['windows']==0
    assert report['progress_production']['excluded_anchors']==2
    assert report['progress_production']['terminal_anchors']==1
    audit=json.loads((tmp_path/'bad/progress_report.json').read_text())
    assert audit['source_reports'][0]['anchors'][0]['result']['correspondence']['accepted'] is False


def test_sparse_tail_mask_uses_episode_end_not_next_stage_and_no_full_scan(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    cfg=config_for(manifest)
    cfg['source_bindings']['compound0']['anchors']=[10]
    class Tail(FakeBackend):
        def inspect_anchor(self,t):
            row=super().inspect_anchor(t)
            row['native_facts']['goal_values']={'A':True,'B':False};row['pending_goals']=['B']
            return row
    monkeypatch.setattr(progress,'NativeProgressBackend',Tail)
    data.export_dataset(manifest,inventory,tmp_path/'tail',progress_config=cfg)
    row=data.AugmentationDataset(tmp_path/'tail',views=['PROGRESS']).rows[0]
    assert row['start']==10 and row['stop']==12
    assert row['action_mask']==[True,True,False,False,False,False,False,False]
    cfg['source_bindings']['compound0']['anchors']=list(range(12))
    with pytest.raises(ValueError,match='sparse|full'):
        progress.plan_progress(cfg,data.validate_manifest(manifest,inventory),manifest['data_root'])


def test_existing_output_rejected_before_backend_can_restore(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    output=tmp_path/'exists';output.mkdir()
    monkeypatch.setattr(progress,'NativeProgressBackend',lambda *a,**k:pytest.fail('native called'))
    with pytest.raises(FileExistsError):
        data.export_dataset(manifest,inventory,output,progress_config=config_for(manifest))


def test_export_cli_retains_initialization_audit_and_can_reuse_exact_recorded_report(tmp_path,monkeypatch):
    from egrs.augmentation import progress, export
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    cfg=config_for(manifest)
    for name,value in [('manifest',manifest),('inventory',inventory),('config',cfg)]:
        (tmp_path/(name+'.json')).write_text(json.dumps(value),encoding='utf-8')
    out=tmp_path/'cli'
    export.main(['--manifest',str(tmp_path/'manifest.json'),'--base-inventory',str(tmp_path/'inventory.json'),
                 '--progress-config',str(tmp_path/'config.json'),'--output',str(out)])
    original=data.read_json(out/'progress_report.json')
    assert original['source_reports'][0]['backend_inspection']['native']['xml_validation']=='synthetic'
    cfg['backend']={'kind':'recorded','report':str(out/'progress_report.json'),
                    'sha256':data.file_sha256(out/'progress_report.json')}
    monkeypatch.setattr(progress,'NativeProgressBackend',lambda *a,**k:pytest.fail('recorded path created native'))
    replay=tmp_path/'reuse'
    report=data.export_dataset(manifest,inventory,replay,progress_config=cfg)
    assert report['counts_by_view']['PROGRESS']['windows']==2
    reused=data.read_json(replay/'progress_report.json')
    assert reused['simulation_requested'] is False
    assert reused['plan']['maximum_restores']==0
    assert reused['source_reports'][0]['backend_inspection']['reused_report_identity']==original['identity']
    assert reused['source_reports'][0]['backend_inspection']['original_backend_inspection']==original['source_reports'][0]['backend_inspection']


@pytest.mark.parametrize('mutation',['hash','binding','missing_anchor'])
def test_recorded_evidence_mismatch_remains_raw_without_new_native(tmp_path,monkeypatch,mutation):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    cfg=config_for(manifest);out=tmp_path/'first'
    data.export_dataset(manifest,inventory,out,progress_config=cfg)
    report_path=out/'progress_report.json'
    if mutation=='missing_anchor':
        original=data.read_json(report_path);original['source_reports'][0]['anchors']=[]
        original['identity']=data.identity(original)
        report_path.write_text(json.dumps(original),encoding='utf-8')
    cfg['backend']={'kind':'recorded','report':str(report_path),'sha256':data.file_sha256(report_path)}
    if mutation=='hash':cfg['backend']['sha256']='b'*64
    if mutation=='binding':cfg['source_bindings']['compound0']['state_alignment_basis']='changed declaration'
    monkeypatch.setattr(progress,'NativeProgressBackend',lambda *a,**k:pytest.fail('new native call'))
    report=data.export_dataset(manifest,inventory,tmp_path/'mismatch',progress_config=cfg)
    assert report['counts_by_view']['PROGRESS']['windows']==0
    assert report['progress_production']['excluded_anchors']==3


def test_verified_atomic_input_survives_native_progress_without_requiring_full_coverage(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    from test_augmentation_data import evidence_for
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    out=tmp_path/'with_atomic'
    report=data.export_dataset(manifest,inventory,out,evidence=[evidence_for(manifest)],progress_config=config_for(manifest))
    assert report['counts_by_view']['PROGRESS']['windows']==2
    assert report['counts_by_view']['ATOMIC']['windows']==4
    assert len(report['raw_fallback_sources'])==201
    rows=data.AugmentationDataset(out,views=['ATOMIC']).rows
    assert all(r['stop']==8 and r['instruction']=='perform goal A' for r in rows)


def test_single_goal_base_stays_raw_and_compound_scope_cannot_change(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    sources=data.validate_manifest(manifest,inventory)
    cfg=config_for(manifest,base=True)
    cfg['source_bindings']['base0']['active_goals']=cfg['source_bindings']['base0']['active_goals'][:1]
    plan=progress.plan_progress(cfg,sources,manifest['data_root'])
    assert plan['planned_anchors']==0
    assert plan['excluded_sources'][0]['reason']=='single_goal_is_RAW_not_compound_progress'
    cfg=config_for(manifest)
    cfg['source_bindings']['compound0']['invariant_predicates']=[['turnon','stove_1']]
    with pytest.raises(ValueError,match='fixed nine-task'):
        progress.plan_progress(cfg,sources,manifest['data_root'])


def test_config_loader_preserves_accepted_native_path_mapping(tmp_path):
    from egrs.augmentation.progress import load_progress_config
    path=tmp_path/'config.json'
    cfg={'backend':{'python':'~/native/python','historical_root':'old',
        'module_paths':['libero-source'], 'native':{'core':{'root':'core'},'bddl_root':'bddl',
        'asset_roots':{'libero':'assets/libero','robosuite':'assets/robosuite'}}}}
    path.write_text(json.dumps(cfg),encoding='utf-8')
    backend=load_progress_config(path)['backend']
    assert backend['python']==str(Path('~/native/python').expanduser())
    assert backend['native']['core']['root']==str((tmp_path/'core').resolve())
    assert backend['native']['asset_roots']=={k:str((tmp_path/'assets'/k).resolve()) for k in ('libero','robosuite')}
    assert backend['module_paths']==[str((tmp_path/'libero-source').resolve())]


def test_roundtrip_exported_evidence_does_not_duplicate_progress_or_lose_atomic(tmp_path,monkeypatch):
    from egrs.augmentation import progress
    from test_augmentation_data import evidence_for
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    out=tmp_path/'before'
    data.export_dataset(manifest,inventory,out,evidence=[evidence_for(manifest)],progress_config=config_for(manifest))
    saved=data.read_json(out/'evidence.json')
    report=data.export_dataset(manifest,inventory,tmp_path/'after',evidence=saved,progress_config=config_for(manifest))
    assert report['counts_by_view']['PROGRESS']['windows']==2
    assert report['counts_by_view']['ATOMIC']['windows']==4


@pytest.mark.parametrize('mutation',['binding','anchors','invariants','facts'])
def test_malformed_produced_evidence_retains_raw_with_diagnostics(tmp_path,monkeypatch,mutation):
    from egrs.augmentation import progress
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(progress,'NativeProgressBackend',FakeBackend)
    out=tmp_path/'original'
    data.export_dataset(manifest,inventory,out,progress_config=config_for(manifest))
    evidence=data.read_json(out/'evidence.json')
    if mutation=='binding':del evidence[0]['binding']
    if mutation=='anchors':evidence[0]['progress_anchors']=None
    if mutation=='invariants':evidence[0]['binding']['invariant_predicates']=[['turnon','stove_1']]
    if mutation=='facts':
        for anchor in evidence[0]['progress_anchors']:anchor['result']['native_facts']['final_goal_atoms']=[[]]
    report=data.export_dataset(manifest,inventory,tmp_path/'malformed',evidence=evidence)
    assert report['counts_by_view']['PROGRESS']['windows']==0
    assert report['excluded_evidence']
