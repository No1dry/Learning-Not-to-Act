import copy
import json
from pathlib import Path

import numpy as np
import pytest

from tests.test_data_training import example, FakeProcessor


def registry(instruction='open the top drawer and put the bowl inside'):
    package = json.loads(Path('docs/annotations/2026-10-23_registry_annotations_v2.json').read_text())
    return next(x['registry'] for x in package['registries'].values() if x['registry']['instruction'] == instruction)


def test_equivalent_alignment_recomputed_and_frame_authorization_is_bound():
    from egrs.offline.sim_alignment import choose_alignment,frame_operation
    from egrs.offline.sim_contract import validate_frame_facts
    samples=[{'frame':0,'camera':c} for c in ('agentview','wrist')]
    comparisons=[{'rule':r,'samples':samples,'residuals':[0.,0.]} for r in ('next_state','replay_action')]
    equivalence={'format':'egrs.sim.equivalence.v1','rules':['next_state','replay_action'],
        'representative':'next_state','state_atol':1e-6,'checks':[{'frame':0,'next_state_index':1,
        'replay_state_index':0,'action_index':0,'state_max_abs_residual':0.,
        'next_state_sha256':'a'*64,'replay_state_sha256':'a'*64,
        'rgb_residuals':{'next_state':{'agentview':0.,'wrist':0.},'replay_action':{'agentview':0.,'wrist':0.}}}]}
    alignment=choose_alignment(comparisons,basis=['synthetic physical equality'],orientation='identity',
        threshold=.03,equivalence=equivalence)
    assert alignment['accepted'] and alignment['rule']=='next_state'
    three=copy.deepcopy(comparisons)+[{'rule':'same_state','samples':samples,'residuals':[0.,0.]}]
    assert not choose_alignment(three,basis=['synthetic physical equality'],orientation='identity',
        threshold=.03,equivalence=equivalence)['accepted']
    bad=copy.deepcopy(equivalence); bad['checks'][0]['rgb_residuals']['replay_action'].pop('wrist')
    with pytest.raises(ValueError,match='cameras'):
        choose_alignment(comparisons,basis=['synthetic'],orientation='identity',threshold=.03,equivalence=bad)
    loose=copy.deepcopy(equivalence); loose['state_atol']=.01; loose['checks'][0]['state_max_abs_residual']=.001
    with pytest.raises(ValueError,match='equivalence state tolerance'):
        choose_alignment(comparisons,basis=['synthetic'],orientation='identity',threshold=.03,equivalence=loose)
    value=facts(); value['frame']=0; value['alignment']=alignment
    validate_frame_facts(value)
    assert frame_operation(alignment,1,3) is None
    value['frame']=1
    with pytest.raises(ValueError,match='equivalence'): validate_frame_facts(value)
    value['frame']=0; value['alignment']['equivalence']['checks'][0]['state_max_abs_residual']=.2
    with pytest.raises(ValueError,match='comparison|equivalence'): validate_frame_facts(value)


def test_similar_rgb_without_state_equivalence_stays_ambiguous():
    from egrs.offline.sim_alignment import choose_alignment
    samples=[{'frame':0,'camera':c} for c in ('agentview','wrist')]
    comparisons=[{'rule':r,'samples':samples,'residuals':[0.,0.]} for r in ('next_state','replay_action')]
    assert not choose_alignment(comparisons,basis=['same RGB only'],orientation='identity',threshold=.03)['accepted']


def facts(reg=None):
    reg = reg or registry()
    return {'format': 'egrs.sim.frame.v1', 'source_id': 'source0', 'frame': 7,
            'alignment': {'format':'egrs.sim.alignment.v1', 'accepted': True, 'rule': 'same_state', 'basis': ['synthetic producer'],
                          'orientation': 'identity', 'boundary_policy': 'gap', 'threshold':.03,
                          'comparisons': [{'rule':'same_state','residuals':[.01], 'samples':[{'frame':0,'camera':'agentview'}]}]},
            'goals': [{'goal_ref': g['goal_ref'], 'kind': g['kind'], 'entity_ref': ('entity1' if i==0 else 'entity0') if len(reg['goals'])==2 else 'entity0',
                       'native_truth': i == 0, 'grasp': 'unknown',
                       'evidence': [{'camera': 'agentview', 'bbox': [.1,.2,.8,.9],
                                     'components': ['target','destination','active_part','reference','hand'],
                                     'supports': ['entity','role','relation','interaction','release']}]} for i,g in enumerate(reg['goals'])]}


def test_packaged_map_binds_exact_registry_and_native_atoms():
    from egrs.offline.sim_contract import load_goal_map, mapping_for, validate_native_mapping
    package = load_goal_map()
    assert len(package['instructions']) == 20
    assert sum(len(x['goals']) for x in package['instructions']) == 21
    for item in package['instructions']:
        mapped = mapping_for(registry(item['instruction']))
        atoms = [x['atom'] for x in mapped if not x['annotation_only']]
        validate_native_mapping(mapped, atoms, {name for x in mapped for name in x['atom'][1:]})
    mapped = mapping_for(registry())
    assert mapped[0]['atom'] == ['open', 'wooden_cabinet_1_top_region']
    assert mapped[0]['annotation_only'] is True
    assert mapped[1]['atom'] == ['in', 'akita_black_bowl_1', 'wooden_cabinet_1_top_region']
    assert mapping_for(registry('put the cream cheese in the bowl'))[0]['atom'][0] == 'on'
    assert mapping_for(registry('push the plate to the front of the stove'))[0]['atom'][-1] == 'main_table_stove_front_region'
    with pytest.raises(ValueError, match='BDDL'):
        validate_native_mapping(mapped, [['on','akita_black_bowl_1','plate_1']], {'wooden_cabinet_1_top_region','akita_black_bowl_1'})
    bad = registry(); bad['goals'][0]['kind'] = 'transport'
    with pytest.raises(ValueError, match='registry'):
        mapping_for(bad)


def test_alignment_requires_unique_comparisons_and_corroborates_final_replay():
    from egrs.offline.sim_alignment import choose_alignment, frame_operation
    comparisons = [{'rule': 'same_state','residuals': [.5,.6]}, {'rule':'next_state','residuals':[.01,.02]}]
    for c in comparisons: c['samples']=[{'frame':0,'camera':'agentview'},{'frame':0,'camera':'wrist'}]
    result = choose_alignment(comparisons, basis=['synthetic runtime metadata'], orientation='identity', threshold=.03)
    assert result['accepted'] and result['rule'] == 'next_state'
    assert frame_operation(result, 2, 5) == {'state_index': 3, 'action_index': None}
    assert frame_operation(result, 4, 5) is None
    comparisons[0]['residuals'] = [.01,.02]
    assert not choose_alignment(comparisons, basis=['metadata'], orientation='identity', threshold=.03)['accepted']
    assert not choose_alignment(comparisons[:1], basis=[], orientation='identity', threshold=.03)['accepted']
    replay = choose_alignment([{'rule':'replay_action','residuals':[.01,.01], 'samples':[{'frame':0,'camera':'agentview'},{'frame':0,'camera':'wrist'}]}], basis=['metadata'], orientation='identity', threshold=.03)
    assert frame_operation(replay, 4, 5) is None
    assert frame_operation(replay, 4, 5, replay_corroborated=True) == {'state_index':4, 'action_index':4}
    same = choose_alignment(comparisons[:1], basis=['metadata'], orientation='flip_vertical', threshold=.03)
    assert frame_operation(same, 4, 5) == {'state_index':4,'action_index':None}


def test_visible_pixels_use_declared_orientation_and_clipped_boxes():
    from egrs.offline.sim_alignment import visible_bbox, clip_bbox
    mask = np.zeros((4,8), dtype=bool); mask[0:2,6:8] = True
    assert visible_bbox(mask, orientation='identity') == [.75,0.,1.,.5]
    assert visible_bbox(mask, orientation='flip_vertical') == [.75,.5,1.,1.]
    assert visible_bbox(np.zeros_like(mask), orientation='identity') is None
    assert clip_bbox([-3,1,10,8], width=8,height=4) == [0.,.25,1.,1.]
    assert clip_bbox([9,0,10,2],width=8,height=4) is None
    with pytest.raises(ValueError): visible_bbox(mask, orientation='opengl')


def test_labels_keep_open_and_in_independent_and_truth_out_of_payload():
    from egrs.offline.sim_labels import build_answer
    sample = example(); sample['payload']['context'].update(registry=registry(), instruction=registry()['instruction'])
    original = copy.deepcopy(sample)
    result = build_answer(sample, facts(), frame=7)
    first,second = result['answer']['goals']
    assert [first['relation'],second['relation']] == ['SAT','UNSAT']
    assert first['release'] == 'NOT_APPLICABLE' and second['release'] == 'UNKNOWN'
    assert result['supervised_state_query'] is True
    assert result['provenance']['/goals/1/relation'] == 'sim_supervised'
    assert '/goals/1/release' not in result['provenance']
    assert sample == original
    assert 'native_truth' not in json.dumps(result['answer'])
    for changes in ({'source_id':'wrong'}, {'frame':8}):
        with pytest.raises(ValueError, match='binding'): build_answer(sample, dict(facts(), **changes), frame=7)


def test_hidden_truth_identity_only_and_unaccepted_alignment_stay_gaps():
    from egrs.offline.sim_labels import build_answer
    sample = example(); sample['payload']['context'].update(registry=registry(), instruction=registry()['instruction'])
    f = facts()
    for g in f['goals']: g['evidence'] = []
    result = build_answer(sample,f,frame=7)
    assert all(g['relation'] == 'UNKNOWN' and g['entity_ref'] is None for g in result['answer']['goals'])
    assert not result['supervised_state_query'] and result['gaps']
    f = facts()
    for g in f['goals']: g['evidence'][0]['components'] = ['target']
    result = build_answer(sample,f,frame=7)
    assert not result['supervised_state_query']
    assert all(g['relation'] == 'UNKNOWN' for g in result['answer']['goals'])
    f['alignment']['accepted'] = False
    result = build_answer(sample,f,frame=7)
    assert not result['provenance']


@pytest.mark.parametrize('grasp,want_interaction,want_release', [('dual_pad','HELD','NOT_RELEASED'),('released','NOT_HELD','RELEASED'),('unknown','UNKNOWN','UNKNOWN')])
def test_grasp_and_release_require_visible_hand(grasp,want_interaction,want_release):
    from egrs.offline.sim_labels import build_answer
    reg = registry('put the bowl on the plate'); sample = example()
    sample['payload']['context'].update(registry=reg,instruction=reg['instruction'])
    f = facts(reg); f['goals'][0]['grasp'] = grasp
    row = build_answer(sample,f,frame=7)['answer']['goals'][0]
    assert (row['interaction'],row['release']) == (want_interaction,want_release)
    f['goals'][0]['evidence'][0]['components'].remove('hand')
    row = build_answer(sample,f,frame=7)['answer']['goals'][0]
    assert row['interaction'] == row['release'] == 'UNKNOWN'


@pytest.mark.parametrize('field,value', [('entity_ref','native body name'),('kind','wrong'),('native_truth',1),('grasp','single_contact')])
def test_bad_operational_facts_rejected(field,value):
    from egrs.offline.sim_contract import validate_frame_facts
    f = facts(); f['goals'][0][field] = value
    with pytest.raises(ValueError): validate_frame_facts(f)


def test_sim_provenance_masks_unknown_unsupported_and_still_trains_real_tokens(tmp_path):
    from egrs.selector.supervision import prepare_answer
    from egrs.selector.encoding import encode_sample
    from egrs.data import validate_sample, export_annotations
    from PIL import Image
    sample=example(); sample['provenance']={'':'sim_supervised'}
    row=sample['answer']['goals'][0]; row['interaction']='UNKNOWN'; row['release']='UNKNOWN'
    row['evidence'][0]['supports']=['entity','role','relation']
    answer,fields=prepare_answer(sample['answer'],sample['provenance'])
    assert '/goals/0/relation' in fields
    assert '/goals/0/interaction' not in fields and '/goals/0/release' not in fields
    assert '/query_id' not in fields
    path=tmp_path/'rgb.png'; Image.new('RGB',(2,2)).save(path)
    sample['payload']['sensor'][0]['observation']={k:str(path) for k in sample['payload']['sensor'][0]['observation']}
    encoded=encode_sample(sample,FakeProcessor(),max_length=20000)
    learned=''.join(chr(x-1) for x in encoded['labels'][0].tolist() if x!=-100)
    assert 'SAT' in learned and 'UNKNOWN' not in learned
    prompt=''.join(chr(x-1) for x in encoded['input_ids'][0].tolist()).split('assistant:')[0]
    assert all(x not in prompt for x in ['native_truth','sim_supervised','same_state'])
    assert 'sim_supervised' in export_annotations([sample])['provenance_values']
    row['evidence']=[]
    assert not prepare_answer(sample['answer'],sample['provenance'])[1]
    sample['payload']['context']['history']=[{'query_id':1,'goals':[]}]
    sample['history_provenance']={'1':'sim_supervised'}
    with pytest.raises(ValueError,match='history provenance'): validate_sample(sample)


def test_sim_identity_only_is_not_exported_as_supervised_query(tmp_path):
    from egrs.data import build_dataset
    sample=example(); row=sample['answer']['goals'][0]
    row.update(relation='UNKNOWN',interaction='UNKNOWN',release='UNKNOWN',role='TARGET')
    row['evidence'][0]['supports']=['entity','role']
    sample['provenance']={'':'sim_supervised'}
    report=build_dataset([sample],tmp_path/'dataset',attestation=dict.fromkeys(['six_composites_excluded','semantic_equivalents_excluded','eval_sources_excluded'],True),fixed_source_splits={'source0':'train'})
    assert report['splits']['train']==0
    assert report['gaps']

def test_alignment_rejects_forged_acceptance():
    from egrs.offline.sim_alignment import choose_alignment
    from egrs.offline.sim_contract import validate_frame_facts
    f=facts(); f['alignment']['comparisons']=[]
    with pytest.raises(ValueError,match='alignment'): validate_frame_facts(f)


def test_alignment_rejects_mismatched_probe_frames():
    from egrs.offline.sim_alignment import choose_alignment
    probes=[{'rule':'same_state','residuals':[.01], 'samples':[{'frame':0,'camera':'agentview'}]},
            {'rule':'next_state','residuals':[.9], 'samples':[{'frame':2,'camera':'agentview'}]}]
    with pytest.raises(ValueError,match='fixed'): choose_alignment(probes,basis=['metadata'],orientation='identity',threshold=.03)


def test_source_aliases_are_stable_across_mapping_order_and_never_native_names():
    from egrs.offline.sim_contract import entity_aliases, mapping_for
    mapped=mapping_for(registry())
    aliases=entity_aliases(mapped)
    assert aliases==entity_aliases(list(reversed(mapped)))
    assert aliases=={'akita_black_bowl_1':'entity0','wooden_cabinet_1_top_region':'entity1'}


def test_invalid_box_and_camera_or_goal_binding_never_emit_labels():
    from egrs.offline.sim_labels import build_answer
    sample=example(); sample['payload']['context'].update(registry=registry(),instruction=registry()['instruction'])
    f=facts(); f['goals'][0]['evidence'][0]['bbox']=[-.1,0,.5,.5]
    with pytest.raises(ValueError,match='bbox'): build_answer(sample,f,frame=7)
    f=facts(); f['goals'][0]['goal_ref']='g9'
    with pytest.raises(ValueError,match='binding'): build_answer(sample,f,frame=7)
    f=facts(); del sample['payload']['sensor'][0]['observation']['agentview_image']
    with pytest.raises(ValueError,match='camera binding'): build_answer(sample,f,frame=7)


def test_sim_specific_weak_evidence_override_and_role_ablation_are_preserved():
    from egrs.selector.supervision import prepare_answer
    sample=example(); sample['provenance']={'':'sim_supervised'}
    _,fields=prepare_answer(sample['answer'],sample['provenance'],role_supervision=False)
    assert '/goals/0/relation' in fields
    assert not any('/evidence/' in p or p.endswith(('/entity_ref','/association','/role')) for p in fields)
    sample['provenance']['/goals/0/evidence/0/bbox/0']='weak'
    answer,fields=prepare_answer(sample['answer'],sample['provenance'])
    assert not fields and answer['goals'][0]['evidence']==[]


def test_plate_front_requires_visible_stove_landmark_as_well_as_local_surface():
    from egrs.offline.sim_labels import build_answer
    reg=registry('push the plate to the front of the stove')
    sample=example(); sample['payload']['context'].update(registry=reg,instruction=reg['instruction'])
    f=facts(reg); f['goals'][0]['evidence'][0]['components']=['target','destination']
    assert build_answer(sample,f,frame=7)['answer']['goals'][0]['relation']=='UNKNOWN'

def test_fact_alias_cannot_change_between_windows_or_swap_goal_instances():
    from egrs.offline.sim_labels import build_answer
    sample=example(); sample['payload']['context'].update(registry=registry(),instruction=registry()['instruction'])
    f=facts(); f['goals'][0]['entity_ref']='entity99'
    with pytest.raises(ValueError,match='alias'): build_answer(sample,f,frame=7)


def test_alignment_operational_record_rejects_state_payloads():
    from egrs.offline.sim_contract import validate_frame_facts
    f=facts(); f['alignment']['state']=[1.,2.,3.]
    with pytest.raises(ValueError,match='alignment'): validate_frame_facts(f)
