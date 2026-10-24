from copy import deepcopy
import pytest
from tests.test_data_training import example
from tests.test_sim_labels import registry,facts
from egrs.offline.sim_consensus import FORMAT,RULES,build_consensus_answer,validate_consensus_fact


def case():
    sample=example();reg=registry();sample['payload']['context'].update(registry=reg,instruction=reg['instruction'])
    value=dict(format=FORMAT,source_id=sample['source_id'],frame=7,T=100,threshold=.03,
               min_visible_pixels=16,boundary_gap=False,candidates=[])
    for rule in RULES:
        cameras={}
        for camera in ('agentview','wrist'):
            cameras[camera]=dict(error=None,orientations={})
            for orientation,score in [('identity',.01),('flip_vertical',.5)]:
                cameras[camera]['orientations'][orientation]=dict(whole_mae=score,foreground_mae=score,
                    background_mae=score,original_max_metric=score,whole_pixels=100,foreground_pixels=20,background_pixels=80)
        goals=deepcopy(facts(reg)['goals'])
        for goal in goals:
            one=goal['evidence'][0];two=deepcopy(one);two['camera']='wrist';goal['evidence'].append(two)
        value['candidates'].append(dict(rule=rule,state_index=7+(rule=='next_state'),
            action_index=7 if rule=='replay_action' else None,cameras=cameras,goals=goals,error=None))
    return sample,value


def fail_camera(candidate,camera):
    x=candidate['cameras'][camera]['orientations']['identity']
    for key in ('whole_mae','foreground_mae','background_mae','original_max_metric'):x[key]=.05


def test_valid_wrist_survives_bad_agentview_without_fake_unique_alignment():
    sample,f=case();before=deepcopy(sample)
    for c in f['candidates']:fail_camera(c,'agentview')
    r=build_consensus_answer(sample,f,frame=7)
    assert [g['relation'] for g in r['answer']['goals']]==['SAT','UNSAT']
    assert r['supervised_state_query']
    assert {e['camera'] for g in r['answer']['goals'] for e in g['evidence']}=={'wrist'}
    assert sample==before and 'alignment' not in f
    assert all(g['interaction']=='UNKNOWN' for g in r['answer']['goals'])


def test_field_conflict_does_not_destroy_other_goal():
    sample,f=case();f['candidates'][1]['goals'][1]['native_truth']=True
    r=build_consensus_answer(sample,f,frame=7)
    assert [g['relation'] for g in r['answer']['goals']]==['SAT','UNKNOWN']
    assert any(g['reason']=='candidate_value_conflict' for g in r['gaps'])


def test_cannot_delete_uncertain_candidate_or_splice_different_cameras():
    sample,f=case();f['candidates'][0]['error']='restore failed'
    assert not build_consensus_answer(sample,f,frame=7)['supervised_state_query']
    sample,f=case();fail_camera(f['candidates'][0],'wrist')
    for c in f['candidates'][1:]:fail_camera(c,'agentview')
    assert not build_consensus_answer(sample,f,frame=7)['supervised_state_query']


def test_measured_two_camera_failure_is_an_exclusion_not_an_exception():
    sample,f=case()
    for camera in ('agentview','wrist'):fail_camera(f['candidates'][0],camera)
    f['candidates'][0]['goals'][1]['native_truth']=True
    r=build_consensus_answer(sample,f,frame=7)
    assert r['answer']['goals'][1]['relation']=='UNSAT'
    assert r['certificate']['candidates'][0]['membership']=='excluded'


def test_boundary_and_missing_visible_support_are_unknown():
    sample,f=case();f.update(T=8,boundary_gap=True,candidates=[])
    assert not build_consensus_answer(sample,f,frame=7)['supervised_state_query']
    sample,f=case()
    for c in f['candidates']:c['goals'][0]['evidence']=[]
    r=build_consensus_answer(sample,f,frame=7)
    assert r['answer']['goals'][0]['entity_ref'] is None
    assert r['answer']['goals'][0]['relation']=='UNKNOWN'


@pytest.mark.parametrize('issue',['missing_rule','higher_threshold','fake_max','wrong_frame','wrong_rule_index'])
def test_corrupt_proof_is_rejected(issue):
    sample,f=case()
    if issue=='missing_rule':f['candidates'].pop()
    if issue=='higher_threshold':f['threshold']=.04
    if issue=='fake_max':f['candidates'][0]['cameras']['agentview']['orientations']['identity']['original_max_metric']=0
    if issue=='wrong_frame':f['frame']=8
    if issue=='wrong_rule_index':f['candidates'][0]['state_index']=8
    with pytest.raises(ValueError):build_consensus_answer(sample,f,frame=7)


def test_parent_reuse_exports_without_rerunning_native_worker(tmp_path):
    from egrs.offline.sim import label_sim,export_sim
    from egrs.offline.sim_consensus import load_parent,PROTOCOL
    from tests.test_sim_pipeline import fixture,worker,ATTEST
    inv,wins,regs,config=fixture(tmp_path)
    label_sim(inv,wins,regs,config,tmp_path/'parent',worker_runner=worker)
    parent=load_parent(tmp_path/'parent/manifest.json',wins)
    assert len(parent['cached'])==2 and parent['supervised']==2
    config=deepcopy(config);config['annotation_protocol']=PROTOCOL
    def forbidden(*args,**kwargs):raise AssertionError('cached source must not launch native worker')
    result=label_sim(inv,wins,regs,config,tmp_path/'child',parent=parent,worker_runner=forbidden)
    assert result['format']=='egrs.sim.annotations.v2'
    assert result['reuse_summary']==dict(sources=2,supervised_queries=2,native_sources=0)
    exported=export_sim(tmp_path/'child/manifest.json',wins,ATTEST,tmp_path/'export')
    assert exported['usable'] and exported['splits']=={'train':1,'dev':1}
