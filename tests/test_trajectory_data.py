"""Generated-data contracts, using only tiny synthetic files."""
import copy
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from egrs.augmentation import data as original


def mapping():
    return {'alignment_id':'explicit','alignment_basis':'synthetic execution transitions',
        'observation_offset':0,'action_offset':0,
        'images':['obs/agentview_rgb','obs/eye_in_hand_rgb'],'image_transforms':['identity','rotate_180'],
        'proprio':['obs/ee_states','obs/gripper_states'],'action':'actions','action_dim':7,'proprio_dim':8,
        'axis_order':['x','y','z','rx','ry','rz','gripper'],'axis_sign':[1]*7,
        'gripper':{'index':6,'kind':'affine','input_open':-1,'input_closed':1,'output_open':1,'output_closed':0},
        'action_normalization':{'kind':'bounds_q99','stats_id':'libero_10','stats_sha256':'a'*64,
            'q01':[-2]*6+[0],'q99':[4]*6+[1],'mask':[True]*6+[False]},
        'proprio_normalization':{'kind':'bounds_q99','stats_id':'libero_10','stats_sha256':'a'*64,
            'q01':[-2]*8,'q99':[4]*8,'mask':[True]*8},
        'processor_id':'fixed-original','crop':'fixed-original',
        'instruction_binding':{'group':'data','attribute':'language','json_key':None}}


def seed_manifest(tmp_path,count=12):
    task=original.load_scope()['tasks'][0]
    sources=[]
    for i in range(count):
        sources.append({'source_id':f'parent{i}','task_key':task['key'],'domain':'compound',
            'file':'libero_10/seed.hdf5','file_sha256':'b'*64,'episode':f'data/demo_{i}',
            'instruction':'exact full instruction','length':10,'demo_index':i,
            'official_task_name':task['official_task_name'],'active_goals':task['active_goals'],
            'invariant_predicates':task['invariant_predicates'],'provenance':'ordinary_expert_demo',
            'physical_ancestry':'unknown','group_ids':[],'mapping':mapping(),
            'controller_binding':{'type':'OSC_POSE','control_freq':20,'env_args_sha256':'c'*64}})
    return {'format':'task035-seeds-v1','dataset':original.DATASET,'revision':original.REVISION,
        'data_root':str(tmp_path),'split_seed':7,'max_demos_per_task':20,'sources':sources,
        'exclusion_attestation':{**dict.fromkeys(original.ATTESTATIONS,True),'known_eval_overlap_excluded':True}}


def attempts_for(tmp_path,sources,*,T=10):
    attempts=[]
    for parent in sources:
        for domain in ('normal','10'):
            sid=parent['source_id']+'_'+domain
            path=tmp_path/(sid+'.hdf5')
            m=copy.deepcopy(parent['mapping'])
            with h5py.File(path,'w') as h:
                g=h.create_group('data/demo_0');h['data'].attrs['language']=parent['instruction']
                for camera in m['images']:
                    g[camera]=np.tile(np.arange(T+1,dtype=np.uint8)[:,None,None,None],(1,2,2,3))
                g['obs/ee_states']=np.ones((T+1,6),dtype=np.float32)
                g['obs/gripper_states']=np.ones((T+1,2),dtype=np.float32)
                actions=np.ones((T,7),dtype=np.float32);actions[:,6]=-1
                g['actions']=actions;g['states']=np.ones((T+1,4))
            attempts.append({'source_id':sid,'parent_demo_id':parent['source_id'],'task_key':parent['task_key'],
                'split':parent['split'],'domain':domain,'variant':0 if domain=='10' else 'normal',
                'attempt':0,'status':'completed','qualified':True,'failure_reason':None,
                'provenance':'counterfactual_generated_from_demo' if domain=='10' else 'ordinary_reexecuted',
                'file':path.name,'file_sha256':original.file_sha256(path),'episode':'data/demo_0','length':T,
                'mapping':m,'instruction':parent['instruction'],'parent_file_sha256':parent['file_sha256'],
                'qualification':{'accepted':True,'synthetic':True},'audit':'synthetic.json'})
    return attempts


def test_seed_groups_split_before_variants_without_old_200(tmp_path):
    from egrs.trajectory_augmentation.data import validate_seeds
    manifest=seed_manifest(tmp_path)
    manifest['sources'][0]['group_ids']=['known duplicate']
    manifest['sources'][4]['group_ids']=['known duplicate']
    sources=validate_seeds(manifest)
    assert len(sources)==12 and {s['split'] for s in sources}=={'train','dev'}
    assert sources[0]['split']==sources[4]['split']
    assert sources[0]['source_group']==sources[4]['source_group']
    assert all(s['parent_demo_id']==s['source_id'] for s in sources)
    assert 'split' not in manifest['sources'][0]


@pytest.mark.parametrize('mutation',['gap','eval','future','wrong_goal','model_action','controller','split','axis_sign','gripper_endpoints'])
def test_bad_seed_metadata_rejected_before_any_native(tmp_path,mutation):
    from egrs.trajectory_augmentation.data import validate_seeds
    m=seed_manifest(tmp_path)
    if mutation=='gap':m['sources'].pop(3)
    if mutation=='eval':m['exclusion_attestation']['known_eval_overlap_excluded']=False
    if mutation=='future':m['sources'][0]['mapping']['proprio']=['states']
    if mutation=='wrong_goal':m['sources'][0]['active_goals']=[]
    if mutation=='model_action':m['sources'][0]['provenance']='model_eval'
    if mutation=='controller':m['sources'][0]['controller_binding']['type']='JOINT_POSITION'
    if mutation=='split':m['sources'][0]['split']='invalid'
    if mutation=='axis_sign':m['sources'][0]['mapping']['axis_sign'][0]=-1
    if mutation=='gripper_endpoints':m['sources'][0]['mapping']['gripper'].update(input_open=0,input_closed=1)
    with pytest.raises(ValueError):validate_seeds(m)


def test_generated_Tplus1_chunks_keep_true_actions_and_model_whitelist(tmp_path):
    from egrs.trajectory_augmentation.data import validate_seeds,export_generated,GeneratedTrajectoryDataset
    parents=validate_seeds(seed_manifest(tmp_path,count=2))
    attempts=attempts_for(tmp_path,parents)
    out=tmp_path/'export'
    report=export_generated(parents,attempts,tmp_path,out)
    ds=GeneratedTrajectoryDataset(out)
    item=ds[0]
    assert set(item)=={'images','proprio','actions','action_mask','instruction'}
    assert item['actions'].shape==(8,7) and np.all(item['actions'][:,:6]==0)
    assert np.all(item['actions'][:,6]==1) and int(item['images'][0][0,0,0])==0
    row_index=next(i for i,r in enumerate(ds.rows) if r['start']==8)
    tail=ds[row_index]
    assert tail['action_mask'].tolist()==[True,True,False,False,False,False,False,False]
    assert tail['actions'][2:].sum()==0
    assert report['data_kind']=='task035-generated-trajectories-v1'
    assert report['attempts']==4 and report['qualified_trajectories']==4
    assert report['parent_sources']==2
    assert len(GeneratedTrajectoryDataset(out,domains=['10']))==20


def test_failure_denominator_preserved_and_variant_cannot_cross_split(tmp_path):
    from egrs.trajectory_augmentation.data import validate_seeds,export_generated
    parents=validate_seeds(seed_manifest(tmp_path,count=1));attempts=attempts_for(tmp_path,parents)
    failed={**copy.deepcopy(attempts[-1]),'source_id':'failure','qualified':False,'status':'rejected',
            'failure_reason':'bridge_goal_regression','variant':1,'file':None,'length':0}
    report=export_generated(parents,attempts+[failed],tmp_path,tmp_path/'export')
    assert report['attempts']==3 and report['qualified_trajectories']==2
    assert report['failed_attempts']==1 and report['failure_reasons']=={'bridge_goal_regression':1}
    assert report['counts_by_domain']['10']['windows']==10
    attempts[0]['split']='dev' if parents[0]['split']=='train' else 'train'
    with pytest.raises(ValueError,match='split'):
        export_generated(parents,attempts,tmp_path,tmp_path/'bad')


@pytest.mark.parametrize('mutation',['length','clip','gripper','hash','provenance'])
def test_generated_data_rejects_inconsistent_recorded_actions_or_identity(tmp_path,mutation):
    from egrs.trajectory_augmentation.data import validate_seeds,export_generated
    parents=validate_seeds(seed_manifest(tmp_path,count=1));attempts=attempts_for(tmp_path,parents)
    row=attempts[0];path=tmp_path/row['file']
    if mutation=='length':row['length']=9
    if mutation in ('clip','gripper'):
        with h5py.File(path,'r+') as h:h['data/demo_0/actions'][0,0 if mutation=='clip' else 6]=20 if mutation=='clip' else 0
        row['file_sha256']=original.file_sha256(path)
    if mutation=='hash':row['file_sha256']='d'*64
    if mutation=='provenance':row['provenance']='ordinary_expert_demo'
    with pytest.raises(ValueError):export_generated(parents,attempts,tmp_path,tmp_path/'bad')
