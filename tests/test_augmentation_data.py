"""Tiny synthetic HDF only; catch temporal, leakage and language/action mistakes."""
import copy
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pytest


def fixture(tmp_path, monkeypatch):
    from egrs.augmentation import data
    path = tmp_path / 'tiny.hdf5'
    with h5py.File(path, 'w') as h:
        h.attrs['language'] = 'full instruction'
        for i in range(202):
            group=f'data/demo_{i}' if i<200 else f'data/compound{i-200}/demo_{i-200}'
            g = h.create_group(group)
            g['front'] = np.arange(12*2*2*3, dtype=np.uint8).reshape(12,2,2,3)
            g['wrist'] = np.ones((12,2,2,3), dtype=np.uint8)
            g['proprio'] = np.tile(np.arange(8, dtype=np.float32), (12,1))
            a = np.zeros((13,7), dtype=np.float32)
            a[:,0] = np.arange(13)
            a[:,6] = -1
            g['actions'] = a
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    norm = {'kind':'identity_already_normalized', 'stats_id':'synthetic-stats', 'stats_sha256':'a'*64}
    mapping = {'alignment_id':'synthetic-alignment', 'alignment_basis':'fixture explicit o[t] -> a[t+1]',
               'observation_offset':0, 'action_offset':1, 'images':['front','wrist'],
               'image_transforms':['identity','identity'], 'proprio':['proprio'],
               'action':'actions', 'action_dim':7, 'proprio_dim':8,
               'axis_order':['x','y','z','rx','ry','rz','gripper'], 'axis_sign':[1]*7,
               'gripper':{'index':6,'kind':'affine','input_open':-1,'input_closed':1,'output_open':1,'output_closed':0},
               'action_normalization':norm, 'proprio_normalization':norm,
               'processor_id':'original-synthetic-processor', 'crop':'original-processor',
               'instruction_binding':{'group':'/','attribute':'language','json_key':None}}
    sources = []
    for i in range(200):
        sources.append({'source_id':f'base{i}', 'task_key':f'base_task{i//10}', 'domain':'base',
                        'file':'tiny.hdf5','file_sha256':sha,'episode':f'data/demo_{i}',
                        'instruction':'full instruction','length':12, 'split':'dev' if i%10>=8 else 'train',
                        'group_ids':[], 'physical_ancestry':'unknown', 'provenance':'ordinary_expert_demo',
                        'mapping':copy.deepcopy(mapping)})
    inventory={'dataset':data.DATASET,'revision':data.REVISION,'sources':[
        {'source_id':s['source_id'],'file':s['file'],'episode':s['episode'],
         'instruction':s['instruction'],'split':s['split'],'task_group':s['task_key'],'group_ids':[]}
        for s in sources]}
    inventory['identity']=data.identity(inventory)
    monkeypatch.setattr(data,'BASE_INVENTORY_IDENTITY', inventory['identity'])
    scope=data.load_scope()
    task=scope['tasks'][0]
    for i in range(2):
        s=copy.deepcopy(sources[0])
        s.update(source_id=f'compound{i}',domain='compound',task_key='basket',episode=f'data/compound{i}/demo_{i}',
                 split=None,demo_index=i,official_task_name=task['official_task_name'],
                 active_goals=task['active_goals'],invariant_predicates=[])
        sources.append(s)
    manifest={'format':'egrs.augmentation.sources.v1','dataset':data.DATASET,'revision':data.REVISION,
              'data_root':str(tmp_path),'sources':sources, 'compound_limit_per_task':2,
              'exclusion_attestation':{'eval_initial_states_excluded':True,'eval_trajectories_excluded':True,
                                       'edited_states_excluded':True,'model_actions_excluded':True}}
    return data,manifest,inventory


def test_raw_chunk_time_gripper_padding_and_model_input_whitelist(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    out=tmp_path/'export'
    report=data.export_dataset(manifest,inventory,out)
    ds=data.AugmentationDataset(out,split='train',views=['RAW'])
    assert report['augmentation_available'] is False
    item=ds[0]
    assert set(item)=={'images','proprio','actions','action_mask','instruction'}
    assert item['actions'].shape==(8,7)
    assert item['actions'][:,0].tolist()==[1,2,3,4,5,6,7,8]
    assert item['actions'][:,6].tolist()==[1]*8
    last=next(i for i,r in enumerate(ds.rows) if r['source_id']=='base0' and r['start']==11)
    tail=ds[last]
    assert tail['action_mask'].tolist()==[True,False,False,False,False,False,False,False]
    assert tail['actions'][:,0].tolist()==[12,0,0,0,0,0,0,0]
    assert report['base_sources']=={'train':160,'dev':40}


def test_known_duplicate_components_preserve_prior_split_and_reject_leakage(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][200]['group_ids']=['same-scene']
    manifest['sources'][0]['group_ids']=['same-scene']
    assigned=data.validate_manifest(manifest,inventory)
    assert assigned[200]['split']=='train'
    manifest['sources'][8]['group_ids']=['same-scene']
    with pytest.raises(ValueError,match='crosses'):
        data.validate_manifest(manifest,inventory)
    manifest['sources'][8]['group_ids']=[]
    manifest['sources'][200]['provenance']='model_eval_trajectory'
    with pytest.raises(ValueError,match='expert'):
        data.validate_manifest(manifest,inventory)


def evidence_for(manifest):
    s=manifest['sources'][200]
    return {'source_id':s['source_id'],'file_sha256':s['file_sha256'],
            'alignment_id':'synthetic-alignment','provenance':'reviewed_local_evidence',
            'reviewer':'synthetic reviewer','basis':'synthetic disjoint action segment review',
            'active_goals':s['active_goals'],
            'stages':[{'start':0,'stop':4,'pending_goals':['A','B']},
                      {'start':4,'stop':8,'pending_goals':['A']},
                      {'start':8,'stop':12,'pending_goals':[]}],
            'atomic_segments':[{'start':4,'stop':8,'goal_id':'A','instruction':'perform goal A',
                                'exclusive_goal_actions':True,'review_basis':'reviewed every action in window'}]}


def test_atomic_never_crosses_boundary_progress_has_true_stages_and_fallback(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    out=tmp_path/'export'
    report=data.export_dataset(manifest,inventory,out,evidence=[evidence_for(manifest)])
    ds=data.AugmentationDataset(out)
    atomic=[r for r in ds.rows if r['view']=='ATOMIC']
    assert len(atomic)==4
    assert atomic[0]['action_mask']==[True]*4+[False]*4
    assert all(r['stop']==8 for r in atomic)
    assert all(r['instruction']=='perform goal A' for r in atomic)
    progress=[r for r in ds.rows if r['view']=='PROGRESS']
    assert len(progress)==8
    assert {r['progress_stage'] for r in progress}=={'pending:A,B','pending:A'}
    assert all(r['instruction']=='full instruction' for r in progress)
    assert report['augmentation_available'] is True
    assert len(report['raw_fallback_sources'])==201
    assert report['coverage_claim']=='ordinary_demonstrations_only_no_external_progress_states'


@pytest.mark.parametrize('mutation', ['goal_transition_only','whole_trajectory_atomic','wrong_alignment','wrong_hash'])
def test_untrusted_evidence_falls_back_raw_without_inventing_coverage(tmp_path,monkeypatch,mutation):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    evidence=evidence_for(manifest)
    if mutation=='goal_transition_only': evidence['provenance']='goal_transition_candidate'
    if mutation=='whole_trajectory_atomic': evidence['atomic_segments'][0].update(start=0,stop=12)
    if mutation=='wrong_alignment': evidence['alignment_id']='wrong'
    if mutation=='wrong_hash': evidence['file_sha256']='b'*64
    report=data.export_dataset(manifest,inventory,tmp_path/'export',evidence=[evidence])
    assert report['excluded_evidence']
    if mutation!='whole_trajectory_atomic': assert report['augmentation_available'] is False
    assert report['counts_by_view']['ATOMIC']['windows']==0


@pytest.mark.parametrize('mutation', ['instruction','goals','time','normalization','prior_split','missing_demo'])
def test_explicit_mapping_scope_and_exact_prior_binding_are_required(tmp_path,monkeypatch,mutation):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    if mutation=='instruction': manifest['sources'][0]['instruction']='wrong'
    if mutation=='goals': manifest['sources'][200]['active_goals']=[]
    if mutation=='time': del manifest['sources'][0]['mapping']['action_offset']
    if mutation=='normalization': del manifest['sources'][0]['mapping']['action_normalization']
    if mutation=='prior_split': manifest['sources'][0]['split']='dev'
    if mutation=='missing_demo': manifest['sources'][201]['demo_index']=3
    with pytest.raises(ValueError): data.export_dataset(manifest,inventory,tmp_path/'export')


def test_normalizes_once_with_explicit_q99_mask_and_orients_only_as_declared(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    mapping=manifest['sources'][0]['mapping']
    mapping['action_normalization']={'kind':'bounds_q99','q01':[0]*7,'q99':[10]*7,'mask':[True]*6+[False],
                                     'stats_id':'synthetic','stats_sha256':'a'*64}
    mapping['proprio_normalization']={'kind':'bounds_q99','q01':[0]*8,'q99':[10]*8,'mask':[True]*8,
                                      'stats_id':'synthetic','stats_sha256':'a'*64}
    mapping['image_transforms'][0]='rotate_180'
    data.export_dataset(manifest,inventory,tmp_path/'export')
    ds=data.AugmentationDataset(tmp_path/'export',split='train',views=['RAW'])
    item=ds[0]
    assert item['actions'][0].tolist()==pytest.approx([-.8,-1,-1,-1,-1,-1,1])
    assert item['proprio'].tolist()==pytest.approx([-1,-.8,-.6,-.4,-.2,0,.2,.4])
    assert item['images'][0][0,0].tolist()==[9,10,11]


def test_no_hidden_hdf_fields_are_read_as_inputs(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][0]['mapping']['proprio']=['states']
    with pytest.raises(ValueError,match='whitelist|forbidden'):
        data.validate_manifest(manifest,inventory)


def test_natural_demo_index_cannot_hide_later_success_selected_episode(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][200]['episode']='data/demo_19'
    with pytest.raises(ValueError,match='natural demo'):
        data.validate_manifest(manifest,inventory)


def test_declared_length_cannot_silently_truncate_raw_trajectory(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][0]['length']=5
    with pytest.raises(ValueError,match='length'):
        data.export_dataset(manifest,inventory,tmp_path/'export')


def test_gripper_identity_cannot_skip_needed_sign_conversion(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][0]['mapping']['gripper']['kind']='identity'
    with pytest.raises(ValueError,match='identity gripper'):
        data.validate_manifest(manifest,inventory)


def test_progress_report_exposes_stages_and_missing_candidate_tasks(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    report=data.export_dataset(manifest,inventory,tmp_path/'export',evidence=[evidence_for(manifest)])
    assert report['counts_by_progress_stage']=={'train|basket|pending:A,B':4,'train|basket|pending:A':4}
    assert report['candidate_source_availability']['basket']=={'requested_max':2,'actual':2,'shortfall':0}
    assert report['candidate_source_availability']['two_pots']=={'requested_max':2,'actual':0,'shortfall':2}


def test_dataset_rejects_stats_that_do_not_match_loaded_original_checkpoint(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][0]['mapping']['action_normalization']={
        'kind':'bounds_q99','q01':[0]*7,'q99':[10]*7,'mask':[True]*6+[False],
        'stats_id':'synthetic-stats','stats_sha256':'a'*64}
    data.export_dataset(manifest,inventory,tmp_path/'export')
    ds=data.AugmentationDataset(tmp_path/'export')
    stats={'synthetic-stats':{'action':{'q01':[0]*7,'q99':[10]*7,'mask':[True]*6+[False]},
                              'proprio':{'q01':[0]*8,'q99':[10]*8,'mask':[True]*8}}}
    ds.validate_normalization(stats,'synthetic-stats','a'*64)
    for key,bad in [('q99',[9]*7),('mask',[True]*7)]:
        altered=copy.deepcopy(stats);altered['synthetic-stats']['action'][key]=bad
        with pytest.raises(ValueError,match='normalization'):
            ds.validate_normalization(altered,'synthetic-stats','a'*64)
    with pytest.raises(ValueError,match='normalization'):
        ds.validate_normalization(stats,'synthetic-stats','b'*64)


def test_proprio_normalization_clips_unmasked_dimensions_like_original_helper(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    manifest['sources'][0]['mapping']['proprio_normalization']={
        'kind':'bounds_q99','q01':[0]*8,'q99':[10]*8,'mask':[False]*8,
        'stats_id':'synthetic-stats','stats_sha256':'a'*64}
    data.export_dataset(manifest,inventory,tmp_path/'export')
    ds=data.AugmentationDataset(tmp_path/'export',split='train',views=['RAW'])
    assert ds[0]['proprio'].tolist()==[0,1,1,1,1,1,1,1]


def test_one_export_can_resolve_pinned_local_evidence_and_audit_producer(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    evidence=evidence_for(manifest)
    producer=tmp_path/'synthetic_provider.py'
    producer.write_text('def recover(*,requests,sources,data_root):\n'
                        '    assert requests[0]["source_id"] == "compound0"\n'
                        '    return '+repr([evidence])+'\n',encoding='utf-8')
    config={'module':str(producer),'module_sha256':hashlib.sha256(producer.read_bytes()).hexdigest(),
            'callable':'recover','producer':'synthetic-local-window-fixture',
            'trust_basis':'tiny test fixture only',
            'requests':[{'source_id':'compound0','windows':[[0,1],[3,5],[7,9],[11,12]],
                         'purpose':'stage_anchor_and_skill_boundary'}]}
    report=data.export_dataset(manifest,inventory,tmp_path/'export',evidence_provider=config)
    assert report['augmentation_available'] is True
    assert report['local_evidence_provider']['module_sha256']==config['module_sha256']
    config['module_sha256']='f'*64
    with pytest.raises(ValueError,match='provider hash'):
        data.export_dataset(manifest,inventory,tmp_path/'bad',evidence_provider=config)


def test_local_recovery_must_request_only_bounded_windows(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    provider={'module':'unused','module_sha256':'a'*64,'callable':'recover','producer':'test',
              'trust_basis':'test','requests':[{'source_id':'compound0','windows':[[0,12]],
                                               'purpose':'stage_anchor_and_skill_boundary'}]}
    with pytest.raises(ValueError,match='local windows'):
        data.export_dataset(manifest,inventory,tmp_path/'bad',evidence_provider=provider)


def test_export_cli_writes_real_indexes_from_explicit_manifest(tmp_path,monkeypatch,capsys):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    from egrs.augmentation.export import main
    manifest['data_root']='.'
    (tmp_path/'sources.json').write_text(json.dumps(manifest),encoding='utf-8')
    (tmp_path/'inventory.json').write_text(json.dumps(inventory),encoding='utf-8')
    main(['--manifest',str(tmp_path/'sources.json'),'--base-inventory',str(tmp_path/'inventory.json'),
          '--output',str(tmp_path/'export')])
    assert json.loads(capsys.readouterr().out)['sources']==202
    ds=data.AugmentationDataset(tmp_path/'export',views=['RAW'])
    assert len(ds)==2424
    assert ds[0]['actions'][0,0]==1


def test_malformed_evidence_is_excluded_without_discarding_raw(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    evidence=evidence_for(manifest)
    evidence['stages']=None
    report=data.export_dataset(manifest,inventory,tmp_path/'export',evidence=[evidence])
    assert report['excluded_evidence']
    assert report['counts_by_view']['RAW']['windows']==2424


def test_dataset_rejects_hdf_replaced_after_export_before_training_or_resume(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    data.export_dataset(manifest,inventory,tmp_path/'export')
    with h5py.File(tmp_path/'tiny.hdf5','r+') as hdf:
        hdf['data/demo_0/actions'][1,0]=99
    with pytest.raises(ValueError,match='HDF hash mismatch'):
        data.AugmentationDataset(tmp_path/'export',split='train',views=['RAW'])


def test_dataset_hashes_shared_source_file_once_per_instance_not_per_item(tmp_path,monkeypatch):
    data,manifest,inventory=fixture(tmp_path,monkeypatch)
    data.export_dataset(manifest,inventory,tmp_path/'export')
    calls=[]
    digest=data.file_sha256
    def measured_digest(path):
        calls.append(Path(path))
        return digest(path)
    monkeypatch.setattr(data,'file_sha256',measured_digest)
    ds=data.AugmentationDataset(tmp_path/'export',split='train',views=['RAW'])
    assert ds[0]['actions'][0,0]==1
    assert ds[1]['actions'][0,0]==2
    assert calls==[tmp_path/'tiny.hdf5']
    data.AugmentationDataset(tmp_path/'export',split='dev',views=['RAW'])
    assert calls==[tmp_path/'tiny.hdf5',tmp_path/'tiny.hdf5']
