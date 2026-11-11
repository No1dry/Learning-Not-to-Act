"""Task038 index contracts use synthetic HDF and recorded JSON only."""
from copy import deepcopy
import json

import h5py
import numpy as np
import pytest

from egrs.augmentation.data import file_sha256, identity, read_json
from test_retention_data import prepared


def write(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')


def seal_generated(export):
    sources = read_json(export/'sources.json')
    sources['identity'] = identity(sources)
    write(export/'sources.json', sources)
    report = read_json(export/'report.json')
    report['sources_identity'] = sources['identity']
    report['identity'] = identity(report)
    write(export/'report.json', report)


@pytest.fixture
def control_sources(prepared, tmp_path):
    from egrs.retention.data import build_index
    config, _, _ = prepared
    export = tmp_path/'generated/export'
    manifest = read_json(export/'sources.json')
    parents = {p['source_id']: p for p in manifest['parents']}
    layout = dict(nq=13, nv=13, arm_qpos=[0,2,3,4,5,6,7], arm_qvel=[0,2,3,4,5,6,7],
                  gripper_qpos=[8,9], gripper_qvel=[8,9], arm_joints=['j'+str(i) for i in range(7)],
                  gripper_joints=['left','right'], gripper_open=[.04,-.04], arm_limits=[[-3,3]]*7)
    modified = [1+i for i in layout['arm_qpos']] + [14+i for i in layout['arm_qvel']] + [9,10,22,23]
    for source in manifest['sources'].values():
        parent = parents[source['parent_demo_id']]
        normal = source['domain'] == 'normal'
        source['mapping']['alignment_id'] = 'task035-live-transitions-v1'
        states = np.zeros((3,27));states[:,0]=np.arange(3)
        states[:,2] = 42  # Actual nonrobot coordinate, even though it is among the first nine.
        if normal:states[1,3]=.7
        else:states[:,3]=.2
        hdf = tmp_path/'generated'/source['file']
        with h5py.File(hdf,'a') as h:
            del h['data/demo_0/states'];h['data/demo_0/states']=states
            h['data/demo_0/actions'][:,0]=.5 if normal else 2.5
        source['file_sha256']=file_sha256(hdf)
        facts=[]
        for i in range(3):
            goals = ([False,False] if normal and i==0 else [True,True] if i==2 else [True,False])
            facts.append(dict(goals=goals,official_goal_values=list(reversed(goals)),invariant_values=[],
                              required_open_values=[],released=True,official_success=all(goals)))
        frames=[dict(state=state.tolist(),facts=fact,hand_open=True,held_free=False,a_released=True,
                     penetration=False,a_regrasp=False) for state,fact in zip(states,facts)]
        audit = dict(frames=frames,confirmation_frames=[deepcopy(frames[-1])]*4,
                     steps=[{'phase':'source_replay'},{'phase':'source_replay'}]+[{'phase':'confirmation_hold'}]*4,
                     error=None,handoff=None if normal else {'normal_state_index':1},
                     rewind=None if normal else {'layout':layout,'modified_indices':modified,
                         'nonrobot_before_sha256':'f'*64,'nonrobot_after_sha256':'f'*64})
        semantics=dict(official_goal_predicates=[parent['active_goals'][1]['predicate'],parent['active_goals'][0]['predicate']],
                       active_goal_indices=[[1],[0]],invariant_indices=[],required_open_predicates=[])
        lineage=dict(source=parent,actual_initial_state=states[0].tolist(),actual_initial_facts=facts[0],
                     native={'runtime_xml_sha256':'d'*64,'joint_layout':layout,'environment_fingerprint':'e'*64},
                     task_semantics=semantics)
        source['audit_path']=source['source_id']+'.audit.json'
        source['lineage_path']=source['source_id']+'.lineage.json'
        write(tmp_path/'generated'/source['audit_path'],audit)
        write(tmp_path/'generated'/source['lineage_path'],lineage)
    write(export/'sources.json',manifest)
    seal_generated(export)
    retention=tmp_path/'retention'
    build_index(config,retention)
    return export,retention


def test_index_labels_active_goals_and_reads_each_own_outgoing_action(control_sources,tmp_path,monkeypatch):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export, retention = control_sources
    original=h5py.Dataset.__getitem__
    def metadata_only(dataset,key):
        if dataset.name.endswith(('rgb','states','actions')):
            pytest.fail('index read HDF payload instead of existing recorded JSON')
        return original(dataset,key)
    with monkeypatch.context() as patch:
        patch.setattr(h5py.Dataset,'__getitem__',metadata_only)
        report=build_index(export,retention,tmp_path/'control')
    assert report['available'] is True
    assert report['pairs']['valid']==2
    data=TaskControlDataset(tmp_path/'control',split='train')
    assert len(data.pairs)==1
    assert data.rows==__import__('egrs.retention.data',fromlist=['RetentionDataset']).RetentionDataset(retention,'train').rows
    u,v=data.get_pair(0)
    assert u['count_label']==v['count_label']==1
    assert u['actions'].shape==v['actions'].shape==(8,7)
    assert u['action_mask'].tolist()==[True]+[False]*7
    assert v['action_mask'].tolist()==[True,True]+[False]*6
    np.testing.assert_allclose(u['actions'][0,0],-1/6,atol=1e-7)
    np.testing.assert_allclose(v['actions'][0,0],.5,atol=1e-7)
    for i,row in enumerate(data.rows):
        item=data[i]
        if row['pool']=='raw':assert item['count_label'] is None
        elif row['pool']=='fresh' and row['observation_index']==0:assert item['count_label']==0
        if row['pool']=='fresh':assert 'actions' not in item
    assert max(r['observation_index'] for r in data.rows if r['pool']=='fresh')==2
    with pytest.raises(FileExistsError):build_index(export,retention,tmp_path/'control')


@pytest.mark.parametrize('mutation,reason',[
    ('nonrobot','recorded_nonrobot_state_changed'),('same_robot','robot_state_unchanged'),
    ('layout','robot_layout_mismatch'),('held','unsafe_handoff'),('tail','missing_outgoing_action'),
    ('facts','goal_facts_mismatch'),('environment','environment_mismatch')])
def test_invalid_recorded_pairs_are_reported_without_dropping_bc(control_sources,tmp_path,mutation,reason):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export,retention=control_sources
    manifest=read_json(export/'sources.json')
    for source in manifest['sources'].values():
        if source['domain']!='10':continue
        path=export.parent/source['audit_path'];audit=read_json(path)
        if mutation=='nonrobot':audit['frames'][0]['state'][2]+=.001
        elif mutation=='same_robot':audit['frames'][0]['state'][3]=.7
        elif mutation=='layout':audit['rewind']['modified_indices'].append(2)
        elif mutation=='held':audit['frames'][0]['held_free']=True
        elif mutation=='tail':audit['handoff']['normal_state_index']=2
        elif mutation=='facts':audit['frames'][0]['facts']['required_open_values']=[False]
        elif mutation=='environment':
            lp=export.parent/source['lineage_path'];lineage=read_json(lp)
            lineage['native']['environment_fingerprint']='b'*64;write(lp,lineage)
        write(path,audit)
    report=build_index(export,retention,tmp_path/'control')
    assert report['available'] is False
    assert report['pairs']['valid']==0
    assert report['pairs']['reasons'][reason]==2
    assert 'unavailable' in report['status']
    data=TaskControlDataset(tmp_path/'control','train')
    assert len(data.rows)==8 and not data.pairs  # ten2 + fresh3 + raw3


def test_source_sha_chain_detects_post_index_audit_change(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export,retention=control_sources
    build_index(export,retention,tmp_path/'control')
    source=next(iter(read_json(export/'sources.json')['sources'].values()))
    with (export.parent/source['audit_path']).open('a') as stream:stream.write(' ')
    with pytest.raises(ValueError,match='SHA|bytes|identity'):TaskControlDataset(tmp_path/'control')


def test_missing_bool_is_masked_but_false_is_counted(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export,retention=control_sources
    for source in read_json(export/'sources.json')['sources'].values():
        if source['domain']!='normal':continue
        path=export.parent/source['audit_path'];audit=read_json(path)
        audit['frames'][0]['facts']['goals']=[None,False]
        audit['frames'][0]['facts']['official_goal_values']=[False,None]
        write(path,audit)
    build_index(export,retention,tmp_path/'control')
    data=TaskControlDataset(tmp_path/'control')
    assert next(data[i]['count_label'] for i,r in enumerate(data.rows) if r['pool']=='fresh' and r['observation_index']==0) is None


def test_legacy_lineage_uses_existing_active_facts_and_never_official_prefix(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export,retention=control_sources
    for source in read_json(export/'sources.json')['sources'].values():
        path=export.parent/source['lineage_path'];lineage=read_json(path)
        del lineage['task_semantics'];write(path,lineage)
        path=export.parent/source['audit_path'];audit=read_json(path)
        for frame in audit['frames']:
            # Third official condition is an invariant, never the count label.
            frame['facts']['official_goal_values']=[False,False,True]
        write(path,audit)
    report=build_index(export,retention,tmp_path/'control')
    assert report['pairs']['valid']==2
    dataset=TaskControlDataset(tmp_path/'control')
    assert dataset.get_pair(0)[0]['count_label']==1


def test_source_variant_cannot_cross_its_original_parent_split(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    export,retention=control_sources
    manifest=read_json(export/'sources.json')
    source=next(s for s in manifest['sources'].values() if s['domain']=='10')
    source['split']='dev' if source['split']=='train' else 'train'
    write(export/'sources.json',manifest);seal_generated(export)
    # Updating the retention metadata input seals cannot authorize a split change.
    path=retention/'sources.json';ret=read_json(path)
    for name in ('sources.json','report.json'):
        ret['inputs'][str((export/name).resolve())]=file_sha256(export/name)
    ret['identity']=identity(ret);write(path,ret)
    path=retention/'report.json';rep=read_json(path)
    rep['sources_identity']=ret['identity'];rep['identity']=identity(rep);write(path,rep)
    with pytest.raises(ValueError,match='parent/split'):build_index(export,retention,tmp_path/'control')


def test_recorded_time_is_ignored_but_nonrobot_tolerance_is_strict(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    export,retention=control_sources
    for source in read_json(export/'sources.json')['sources'].values():
        if source['domain']!='10':continue
        path=export.parent/source['audit_path'];audit=read_json(path)
        audit['frames'][0]['state'][0]=12345
        audit['frames'][0]['state'][2]+=1e-9
        write(path,audit)
    report=build_index(export,retention,tmp_path/'control')
    assert report['pairs']['valid']==2


def test_report_includes_tasks_without_ten_coverage(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    export,retention=control_sources
    report=build_index(export,retention,tmp_path/'control')
    assert report['pairs']['by_task_split']['two_pots|train']=={'candidates':0,'valid':0,'reasons':{}}


def test_label_bytes_are_part_of_index_identity_not_only_report(control_sources,tmp_path):
    from egrs.task_control.index import build_index
    from egrs.task_control.data import TaskControlDataset
    export,retention=control_sources
    directory=tmp_path/'control';build_index(export,retention,directory)
    path=directory/'labels.jsonl';lines=path.read_text(encoding='utf-8').splitlines()
    row=json.loads(lines[0]);row['count_label']=2;lines[0]=json.dumps(row)
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report=read_json(directory/'report.json')
    report['labels_sha256']=file_sha256(path);report['identity']=identity(report)
    write(directory/'report.json',report)
    seal=read_json(directory/'identity.json');seal['report_identity']=report['identity'];write(directory/'identity.json',seal)
    with pytest.raises(ValueError,match='identity|bytes'):TaskControlDataset(directory)


def required_open_recorded_pair(task_key, semantics_mode, required_values):
    """Small recorded-state pair with task-catalog active predicates."""
    from egrs.augmentation.data import load_scope
    from egrs.task_control.index import _semantics
    task=next(t for t in load_scope()['tasks'] if t['key']==task_key)
    parent={'task_key':task_key,'active_goals':deepcopy(task['active_goals']),
            'invariant_predicates':deepcopy(task['invariant_predicates'])}
    layout=dict(nq=10,nv=10,arm_qpos=list(range(7)),arm_qvel=list(range(7)),
                gripper_qpos=[7,8],gripper_qvel=[7,8],arm_joints=['j'+str(i) for i in range(7)],
                gripper_joints=['left','right'])
    native={'runtime_xml_sha256':'a'*64,'joint_layout':layout}
    lineage={'native':native}
    if semantics_mode!='legacy':
        lineage['task_semantics']={'official_goal_predicates':[g['predicate'] for g in task['active_goals']],
                                  'active_goal_indices':[[0],[1]],'invariant_indices':[]}
        if semantics_mode=='explicit_empty':lineage['task_semantics']['required_open_predicates']=[]
        elif semantics_mode=='explicit':
            lineage['task_semantics']['required_open_predicates']=[['open',task['active_goals'][1]['predicate'][1]]]
    semantics=_semantics(parent,lineage)
    facts={'goals':[True,False],'official_goal_values':[True,False],
           'invariant_values':[],'released':True}
    if required_values!='missing':facts['required_open_values']=required_values
    frame={'facts':facts,'hand_open':True,'held_free':False,'a_released':True,'penetration':False,
           'state':[0.0]*21}
    u=deepcopy(frame);u['state'][3]=.7
    v=deepcopy(frame);v['state'][3]=.2
    source={'parent_demo_id':'parent','split':'train','instruction':'complete instruction',
            'task_key':task_key,'length':1}
    normal={**source,'source_id':'normal'};ten={**source,'source_id':'ten'}
    records={'normal':{'audit':{'frames':[u,deepcopy(u)]},'lineage':lineage,'parent':parent,
                       'semantics':semantics,'shape_valid':True},
             'ten':{'audit':{'frames':[v,deepcopy(v)],'handoff':{'normal_state_index':0},
                              'rewind':{'layout':layout,'modified_indices':list(range(1,10))+list(range(11,20))}},
                    'lineage':lineage,'parent':parent,'semantics':semantics,'shape_valid':True}}
    return normal,ten,records


@pytest.mark.parametrize('task_key',['bowl_drawer_close','mug_microwave_close'])
@pytest.mark.parametrize('semantics_mode',['legacy','explicit_empty','explicit_missing'])
@pytest.mark.parametrize('required_values',['missing',[],[1],[False]])
def test_required_open_cannot_be_omitted_or_forged(task_key,semantics_mode,required_values):
    from egrs.task_control.index import _pair_check
    normal,ten,records=required_open_recorded_pair(task_key,semantics_mode,required_values)
    reason,evidence=_pair_check(normal,ten,records)
    assert reason=='goal_facts_mismatch' and evidence is None


@pytest.mark.parametrize('task_key,target',[
    ('bowl_drawer_close','white_cabinet_1_bottom_region'),('mug_microwave_close','microwave_1')])
@pytest.mark.parametrize('semantics_mode',['legacy','explicit'])
def test_required_open_is_bound_to_fixed_source_close_goal(task_key,target,semantics_mode):
    from egrs.task_control.index import _pair_check
    normal,ten,records=required_open_recorded_pair(task_key,semantics_mode,[True])
    assert records['normal']['semantics']['required_open_predicates']==[['open',target]]
    assert _pair_check(normal,ten,records)[0] is None


@pytest.mark.parametrize('task_key',['bowl_drawer_close','mug_microwave_close'])
def test_required_open_refuses_a_different_source_close_predicate(task_key):
    from egrs.augmentation.data import load_scope
    from egrs.task_control.index import _semantics
    task=deepcopy(next(t for t in load_scope()['tasks'] if t['key']==task_key))
    parent={'task_key':task_key,'active_goals':task['active_goals'],'invariant_predicates':[]}
    parent['active_goals'][1]['predicate'][1]='other_mechanism'
    with pytest.raises(ValueError,match='required.open|close predicate'):_semantics(parent,{})


@pytest.mark.parametrize('task_key',['bowl_drawer_close','mug_microwave_close'])
def test_required_open_checks_boolean_type_on_both_pair_ends(task_key):
    from egrs.task_control.index import _pair_check
    normal,ten,records=required_open_recorded_pair(task_key,'explicit',[True])
    records['ten']['audit']['frames'][0]['facts']['required_open_values']=[1]
    assert _pair_check(normal,ten,records)[0]=='goal_facts_mismatch'
