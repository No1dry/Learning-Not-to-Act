"""Synthetic review events only. No real human review is asserted."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from tests.test_data_training import example, FakeProcessor


def fixture(tmp_path):
    from egrs.offline.common import seal
    sample = example()
    sample['provenance'] = {'': 'weak'}
    sample['ancestry_known'] = False
    sample['physical_truth'] = None
    for k in sample['payload']['sensor'][0]['observation']:
        path = tmp_path / (k + '.png')
        Image.new('RGB', (16, 12), (80, 110, 130)).save(path)
        sample['payload']['sensor'][0]['observation'][k] = str(path)
    return seal({'format': 'egrs.candidates.v1', 'synthetic': True, 'samples': [sample],
        'source_splits': {'source0': 'dev'}, 'planned_sources': [{'source_id': 'source0', 'group_ids': []}],
        'windows': [{'source_id': 'source0', 'window_id': 'w0', 'frames': [0]}], 'gaps': [], 'attempts': [], 'teacher': {'synthetic_backend': True}})


def session_for(manifest):
    from egrs.offline.review import new_session
    return new_session(manifest)


def confirm(session, sample, pointer):
    from egrs.offline.review import confirmation
    session['confirmations'].setdefault(sample['sample_id'], {})[pointer] = confirmation(sample['answer'], pointer, 'SYNTHETIC TEST ONLY', 123)


def test_portable_export_uses_legal_views_without_mutating_training_paths(tmp_path):
    from egrs.offline.review import export_review
    manifest = fixture(tmp_path)
    original = copy.deepcopy(manifest)
    package = export_review(manifest, tmp_path / 'portable')
    assert manifest == original
    html = (tmp_path / 'portable/index.html').read_text(encoding='utf-8')
    assert 'SYNTHETIC' in html
    assert len(package['images']) == 2
    assert all((tmp_path / 'portable' / p).is_file() for p in package['images'].values())
    assert 'fetch(' not in html and 'https://' not in html
    assert package['manifest']['samples'][0]['payload'] == manifest['samples'][0]['payload']


def test_explicit_field_review_unknown_and_unconfirmed_evidence_are_separate(tmp_path):
    from egrs.offline.review import import_review
    from egrs.selector.supervision import prepare_answer
    manifest = fixture(tmp_path)
    session = session_for(manifest)
    sample = session['annotations']['samples'][0]
    sample['answer']['goals'][0]['relation'] = 'UNKNOWN'
    confirm(session, sample, '/goals/0/relation')
    result = import_review(manifest, session)
    row = result['samples'][0]
    answer, fields = prepare_answer(row['answer'], row['provenance'])
    assert answer['goals'][0]['relation'] == 'UNKNOWN' and '/goals/0/relation' in fields
    assert answer['goals'][0]['evidence'] == []
    assert row['provenance']['/goals/0/relation'] == 'reviewed_candidate'
    assert result['audit']['confirmed_fields_or_items'] == 1


@pytest.mark.parametrize('mutation', ['payload', 'ancestry', 'split', 'stale_value', 'stale_evidence', 'whole_goal'])
def test_import_rejects_immutable_or_stale_confirmation_changes(tmp_path, mutation):
    from egrs.offline.review import import_review
    manifest = fixture(tmp_path)
    session = session_for(manifest)
    sample = session['annotations']['samples'][0]
    confirm(session, sample, '/goals/0/relation')
    if mutation == 'payload':
        sample['payload']['context']['instruction'] = 'tampered'
    elif mutation == 'ancestry':
        sample['ancestry_known'] = True
    elif mutation == 'split':
        session['manifest_id'] = 'wrong identity'
    elif mutation == 'stale_value':
        sample['answer']['goals'][0]['relation'] = 'UNKNOWN'
    elif mutation == 'stale_evidence':
        sample['answer']['goals'][0]['evidence'][0]['bbox'] = [.2, .2, .8, .8]
    else:
        session['confirmations']['s0']['/goals/0'] = {'reviewer': 'SYNTHETIC'}
    with pytest.raises(ValueError):
        import_review(manifest, session)


def test_evidence_item_edit_and_index_compaction_reach_final_token_masks(tmp_path):
    from egrs.offline.review import import_review
    from egrs.selector.encoding import encode_sample
    manifest = fixture(tmp_path)
    session = session_for(manifest)
    sample = session['annotations']['samples'][0]
    evidence = sample['answer']['goals'][0]['evidence']
    evidence.append(copy.deepcopy(evidence[0]))
    evidence[1]['camera'] = 'wrist'
    evidence[1]['bbox'] = [.2, .3, .6, .9]
    confirm(session, sample, '/goals/0/evidence/1')
    result = import_review(manifest, session)
    encoded = encode_sample(result['samples'][0], FakeProcessor(), max_length=20000)
    learned = ''.join(chr(i - 1) for i in encoded['labels'][0].tolist() if i != -100)
    assert 'wrist' in learned and '0.9' in learned and 'agentview' not in learned
    assert result['audit']['corrections'] == 1


def test_null_stays_unsupervised_until_explicit_human_value_and_build_preserves_dev(tmp_path):
    from egrs.offline.review import import_review, build_reviewed
    from egrs.offline.common import seal
    manifest = fixture(tmp_path)
    manifest['samples'][0].update(answer=None, provenance={})
    manifest = seal(manifest)
    session = session_for(manifest)
    assert import_review(manifest, session)['samples'][0]['answer'] is None
    sample = session['annotations']['samples'][0]
    sample['answer'] = example()['answer']
    confirm(session, sample, '/goals/0/relation')
    attestation = dict.fromkeys(('six_composites_excluded', 'semantic_equivalents_excluded', 'eval_sources_excluded'), True)
    attestation['basis'] = 'SYNTHETIC FIXTURE ONLY'
    report = build_reviewed(manifest, session, tmp_path / 'built', attestation=attestation)
    assert report['splits'] == {'train': 0, 'dev': 1}
    assert report['ready'] is False
    assert (tmp_path / 'built/all-candidates.json').exists()
    assert (tmp_path / 'built/unreviewed.json').exists()
    assert json.loads((tmp_path / 'built/dev.jsonl').read_text())['provenance']['/goals/0/relation'] == 'human'


def test_round_robin_queue_and_stratified_window_suggestion(tmp_path):
    from egrs.offline.review import review_queue, rereview_suggestion
    rows = []
    for task in ['a', 'b']:
        for source in ['0', '1']:
            for q in [1, 2]:
                rows.append(dict(example(), task_group=task, source_id=task+source, sample_id=task+source+str(q)))
    assert review_queue(rows)[:4] == ['a01', 'b01', 'a11', 'b11']
    assert len(rereview_suggestion(rows, {r['source_id']: 'train' for r in rows})) == 2


def test_registry_review_confirmed_identity_and_explicit_edit(tmp_path):
    from egrs.offline.review import new_registry_session, import_registry_review, export_review
    from egrs.offline.common import seal
    from egrs.offline.inventory import instruction_id
    registry = example()['payload']['context']['registry']
    key = instruction_id(registry['instruction'])
    manifest = seal({'format': 'egrs.registry-candidates.v1', 'inventory_id': 'synthetic-inventory',
        'registries': {key: {'instruction': registry['instruction'], 'registry': registry, 'confirmed': False, 'provenance': 'weak'}}})
    session = new_registry_session(manifest)
    assert import_registry_review(manifest, session)['registries'] == {}
    session['confirmations'][key] = {'value': copy.deepcopy(registry), 'reviewer': 'SYNTHETIC TEST ONLY', 'elapsed_ms': 10}
    result = import_registry_review(manifest, session)
    assert result['registries'][key]['confirmed'] is True
    export_review(manifest, tmp_path / 'registry-ui')
    session['registries'][key]['instruction'] += ' changed'
    with pytest.raises(ValueError):
        import_registry_review(manifest, session)


def test_partial_field_coverage_never_claims_full_ready_and_reports_distribution(tmp_path):
    from egrs.offline.review import build_reviewed
    from egrs.offline.common import seal
    manifest = fixture(tmp_path)
    second = copy.deepcopy(manifest['samples'][0])
    second.update(sample_id='s1', source_id='source1')
    manifest['samples'].append(second)
    manifest['source_splits']['source1'] = 'train'
    manifest['planned_sources'].append({'source_id': 'source1', 'group_ids': []})
    manifest = seal(manifest)
    session = session_for(manifest)
    for row in session['annotations']['samples']:
        confirm(session, row, '/goals/0/relation')
    attest = dict.fromkeys(('six_composites_excluded', 'semantic_equivalents_excluded', 'eval_sources_excluded'), True)
    attest['basis'] = 'SYNTHETIC ONLY'
    report = build_reviewed(manifest, session, tmp_path / 'partial-fields', attestation=attest)
    assert report['ready'] is False
    assert len(report['unconfirmed_fields_or_items']) == 2
    assert report['label_distributions']['confirmed']['relation'] == {'SAT': 2}
    assert report['label_distributions']['confirmed']['role'] == {}
    assert report['label_distributions']['candidate']['role'] == {'TARGET': 2}
    assert report['candidate_split_counts']['dev']['sources'] == 1
