"""Three retention pools from synthetic HDF; no policy or environment."""
from copy import deepcopy
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from egrs.augmentation.data import file_sha256,identity,read_json
from egrs.trajectory_augmentation.data import validate_seeds,export_generated
from test_trajectory_data import seed_manifest,attempts_for


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    from egrs.retention import data
    monkeypatch.setattr(data,'EXPECTED_COUNTS',{p:{'train':1,'dev':1} for p in data.POOLS})
    monkeypatch.setattr(data,'EXPECTED_PARENT_GROUPS',{p:{'train':1,'dev':1} for p in data.POOLS})
    monkeypatch.setattr(data,'EXPECTED_TASKS',dict.fromkeys(data.POOLS,1))
    rawroot=tmp_path/'raw';raw=(rawroot/'libero_10/seed.hdf5');raw.parent.mkdir(parents=True)
    with h5py.File(raw,'w') as h:
        h.require_group('data').attrs['language']='exact full instruction'
        for i,n in ((0,3),(1,1)):
            g=h.require_group(f'data/demo_{i}')
            pixels=np.tile(np.arange(4,dtype=np.uint8).reshape(1,2,2,1),(n,1,1,3))
            pixels+=np.arange(n,dtype=np.uint8)[:,None,None,None]*10
            g['obs/agentview_rgb']=pixels;g['obs/eye_in_hand_rgb']=pixels+100
            g['obs/ee_states']=np.tile(np.arange(n,dtype=np.float32)[:,None],(1,6))
            g['obs/gripper_states']=np.tile(np.arange(n,dtype=np.float32)[:,None],(1,2))
    manifest=seed_manifest(rawroot,count=2)
    for p in manifest['sources']:
        p['file_sha256']=file_sha256(raw)
        for field in ('action_normalization','proprio_normalization'):
            p['mapping'][field].update(stats_id=data.STATS_KEY,stats_sha256=data.STATS_SHA)
    seed=tmp_path/'seeds.json';seed.write_text(json.dumps(manifest),encoding='utf-8')
    parents=validate_seeds(manifest)
    gen=tmp_path/'generated';gen.mkdir()
    attempts=attempts_for(gen,parents,T=2)
    export_generated(parents,attempts,gen,gen/'export')
    cfg={'format':data.CONFIG,'generated_export':'generated/export','seed_manifest':'seeds.json'}
    config=tmp_path/'index.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    return config,raw,manifest


def test_three_pools_preserve_parent_split_and_observation_only_raw(prepared,tmp_path):
    from egrs.retention.data import build_index,RetentionDataset,POOLS
    config,raw,_=prepared
    report=build_index(config,tmp_path/'index')
    assert report['pool_counts']=={p:{'train':1,'dev':1} for p in POOLS}
    dataset=RetentionDataset(tmp_path/'index')
    assert len(dataset)==14  # ten4 + fresh6 + raw4
    assert all(s['split']==dataset.manifest['parents'][s['parent_demo_id']]['split'] for s in dataset.sources.values())
    raw_sources=[s for s in dataset.sources.values() if s['pool']=='raw']
    assert all(s['provenance']=='official_recorded_observation' for s in raw_sources)
    assert all('action' not in s['observation_mapping'] and 'alignment_basis' not in s['observation_mapping'] for s in raw_sources)
    assert report['raw_qualification_claim']=='same-row recorded observations only; no action timing or physical qualification claim'


def test_raw_current_row_rotation_and_normalization_exactly_once(prepared,tmp_path,monkeypatch):
    from egrs.retention.data import build_index,RetentionDataset
    config,raw,_=prepared;build_index(config,tmp_path/'index')
    dataset=RetentionDataset(tmp_path/'index',pools=['raw'])
    row=next(i for i,r in enumerate(dataset.rows) if r['observation_index']==1)
    original=h5py.Group.__getitem__
    def observations_only(group,key):
        if str(key).split('/')[-1] in {'actions','states'}:pytest.fail('ordinary pool accessed actions/state')
        return original(group,key)
    monkeypatch.setattr(h5py.Group,'__getitem__',observations_only)
    item=dataset[row]
    assert set(item)=={'images','proprio','instruction'}
    assert item['images'][0][:,:,0].tolist()==[[13,12],[11,10]]
    assert item['images'][1][:,:,0].tolist()==[[113,112],[111,110]]
    np.testing.assert_allclose(item['proprio'],np.zeros(8),atol=1e-7)
    assert item['instruction']=='exact full instruction'
    short=[r for r in dataset.rows if r['observation_count']==1]
    assert len(short)==1 and short[0]['prefix'] is True
    three=[r for r in dataset.rows if r['observation_count']==3]
    assert [r['prefix'] for r in three]==[True,False,False]


def test_index_and_fresh_items_never_read_expert_actions_or_states(prepared,tmp_path,monkeypatch):
    from egrs.retention.data import build_index,RetentionDataset
    config,_,_=prepared
    original=h5py.Group.__getitem__
    def observations_only(group,key):
        if str(key).split('/')[-1] in {'actions','states'}:pytest.fail('index/ref accessed action/state dataset')
        return original(group,key)
    monkeypatch.setattr(h5py.Group,'__getitem__',observations_only)
    build_index(config,tmp_path/'index')
    fresh=RetentionDataset(tmp_path/'index',pools=['fresh'])
    assert len(fresh)==6 and set(fresh[-1])=={'images','proprio','instruction'}
    assert sorted({r['observation_index'] for r in fresh.rows})==[0,1,2]


def test_ten_reuses_original_chunk_tail_and_policy_whitelist(prepared,tmp_path):
    from egrs.retention.data import build_index,RetentionDataset
    config,_,_=prepared;build_index(config,tmp_path/'index')
    ten=RetentionDataset(tmp_path/'index',pools=['ten'])
    item=ten[1]
    assert set(item)=={'images','proprio','instruction','actions','action_mask'}
    assert item['action_mask'].tolist()==[True]+[False]*7
    assert item['actions'].shape==(8,7)
    assert not {'pool','domain','prefix','split','states','parent_demo_id'}&item.keys()


def test_observation_proprio_clips_unscaled_dimension_like_original_helper(prepared,tmp_path):
    from egrs.retention.data import build_index,RetentionDataset
    config,_,_=prepared;build_index(config,tmp_path/'index')
    raw=RetentionDataset(tmp_path/'index',pools=['raw'])
    index=next(i for i,row in enumerate(raw.rows) if row['observation_index']==2)
    source=raw.sources[raw.rows[index]['source_id']]
    # Characterize the original helper's final full-vector clamp. Production
    # SOG10 defaults to an all-true mask; this catches a future masked dimension.
    source['observation_mapping']['proprio_normalization']['mask'][0]=False
    np.testing.assert_allclose(raw[index]['proprio'],[1]+[1/3]*7,atol=1e-7)


@pytest.mark.parametrize('changed',['raw_length','parent_split','fresh_mapping','index_bytes','source_bytes'])
def test_misaligned_or_changed_data_is_rejected(prepared,tmp_path,changed):
    from egrs.retention.data import build_index,RetentionDataset
    config,raw,manifest=prepared
    if changed=='raw_length':
        with h5py.File(raw,'a') as h:
            del h['data/demo_0/obs/gripper_states']
            h['data/demo_0/obs/gripper_states']=np.ones((2,2),dtype=np.float32)
        manifest['sources'][0]['file_sha256']=manifest['sources'][1]['file_sha256']=file_sha256(raw)
        (tmp_path/'seeds.json').write_text(json.dumps(manifest))
        # Deliberately update matching generated parents so the shape guard is reached.
        path=tmp_path/'generated/export/sources.json';export=read_json(path)
        for parent in export['parents']:parent['file_sha256']=file_sha256(raw)
        for source in export['sources'].values():source['parent_file_sha256']=file_sha256(raw)
        export['identity']=identity(export);path.write_text(json.dumps(export))
        path=tmp_path/'generated/export/report.json';report=read_json(path)
        report['sources_identity']=export['identity'];report['identity']=identity(report);path.write_text(json.dumps(report))
        with pytest.raises(ValueError,match='observation'):build_index(config,tmp_path/'index')
    elif changed in ('parent_split','fresh_mapping'):
        path=tmp_path/'generated/export/sources.json';export=read_json(path)
        source=next(iter(export['sources'].values()))
        if changed=='parent_split':source['split']='opposite'
        else:source['mapping']['image_transforms']=['rotate_180','identity']
        export['identity']=identity(export);path.write_text(json.dumps(export))
        path=tmp_path/'generated/export/report.json';report=read_json(path)
        report['sources_identity']=export['identity'];report['identity']=identity(report);path.write_text(json.dumps(report))
        with pytest.raises(ValueError,match='parent|mapping'):build_index(config,tmp_path/'index')
    else:
        build_index(config,tmp_path/'index')
        path=tmp_path/'index/rows.jsonl' if changed=='index_bytes' else raw
        with path.open('ab') as out:out.write(b' ')
        with pytest.raises(ValueError):RetentionDataset(tmp_path/'index')


def test_original_normalization_binding_and_new_output_are_strict(prepared,tmp_path):
    from egrs.retention.data import build_index,RetentionDataset,STATS_KEY,STATS_SHA
    config,_,_=prepared;build_index(config,tmp_path/'index')
    dataset=RetentionDataset(tmp_path/'index')
    norm=next(iter(dataset.sources.values()))['observation_mapping']['proprio_normalization']
    stats={STATS_KEY:{'proprio':{k:norm[k] for k in ('q01','q99','mask')},
        'action':{'q01':[-2]*6+[0],'q99':[4]*6+[1],'mask':[True]*6+[False]}}}
    dataset.validate_normalization(stats,STATS_KEY,STATS_SHA)
    with pytest.raises(ValueError):dataset.validate_normalization(stats,STATS_KEY,'f'*64)
    with pytest.raises(FileExistsError):build_index(config,tmp_path/'index')


@pytest.mark.parametrize('observations,expected',[(1,1),(2,1),(3,1),(4,2),(8,3)])
def test_prefix_boundary_is_time_only_ceil_third(observations,expected):
    from egrs.retention.data import prefix_length
    assert prefix_length(observations)==expected
