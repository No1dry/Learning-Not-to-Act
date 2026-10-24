"""Synthetic metadata and text files only; no real dataset or native imports."""
import hashlib
import pytest


def metadata(args=None, attrs=None, suite='libero_goal'):
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    return resolve_bddl_metadata(args or {},attrs or {},suite=suite)


@pytest.mark.parametrize('field', ['attribute','argument','kwargs'])
@pytest.mark.parametrize('path', ['/old/libero_goal/task.bddl', r'C:\old\libero_goal\task.bddl', 'task.bddl'])
def test_metadata_each_identifier_can_resolve_alone(field,path,tmp_path):
    args={}; attrs={}
    if field=='attribute': attrs['bddl_file_name']=path
    elif field=='argument': args['bddl_file']=path
    else: args['env_kwargs']={'bddl_file_name':path}
    result=metadata(args,attrs)
    assert result['basename']=='task.bddl'
    from egrs.offline.sim_metadata import resolve_installed_bddl
    suite=tmp_path/'libero_goal'; suite.mkdir(); target=suite/'task.bddl'; target.write_bytes(b'(task)')
    lock={'revision':'a'*40,'bddl_sha256':{'libero_goal/task.bddl':hashlib.sha256(b'(task)').hexdigest()}}
    resolved,report=resolve_installed_bddl(tmp_path,result,embedded=None,runtime_identity=lock)
    assert resolved==target.resolve()
    assert report['mode']=='metadata_resolved_installed_bddl'
    assert report['source_embedded_bddl_present'] is False
    assert report['historical_source_byte_equality']=='unverified'
    assert report.get('source_bddl_sha256') is None
    assert report['libero_source']['revision_verified_at_runtime'] is False


@pytest.mark.parametrize('path', ['', 'task.xml','../task.bddl','https://host/task.bddl','x/./task.bddl','libero_object/task.bddl','TASK.BDDL','task.bddl/','task?.bddl', b'\xff'])
def test_metadata_malformed_present_path_is_gap(path):
    with pytest.raises(ValueError): metadata({'bddl_file':path})


def test_metadata_missing_and_conflicting_identifiers_are_gaps():
    with pytest.raises(ValueError,match='identifier'): metadata()
    with pytest.raises(ValueError,match='conflict'):
        metadata({'bddl_file':'task.bddl'}, {'bddl_file_name':'other.bddl'})
    with pytest.raises(ValueError,match='suite'):
        metadata({'bddl_file':'libero_object/task.bddl'}, {'bddl_file_name':'libero_goal/task.bddl'})


@pytest.mark.parametrize('issue', ['missing_lock','missing_digest','wrong_digest','wrong_body','wrong_case'])
def test_metadata_installed_identity_rejects_unbound_or_conflicting_file(tmp_path,issue):
    from egrs.offline.sim_metadata import resolve_installed_bddl
    suite=tmp_path/'libero_goal'; suite.mkdir(); (suite/'task.bddl').write_bytes(b'(task)')
    lock={'revision':'a'*40,'bddl_sha256':{'libero_goal/task.bddl':hashlib.sha256(b'(task)').hexdigest()}}
    embedded=None
    if issue=='missing_lock': lock=None
    if issue=='missing_digest': lock['bddl_sha256']={}
    if issue=='wrong_digest': lock['bddl_sha256']['libero_goal/task.bddl']='0'*64
    if issue=='wrong_body': embedded='(other)'
    name='Task.bddl' if issue=='wrong_case' else 'task.bddl'
    with pytest.raises((ValueError,FileNotFoundError)):
        resolve_installed_bddl(tmp_path,metadata({'bddl_file':name}),embedded=embedded,runtime_identity=lock)


def test_metadata_embedded_mode_retains_legacy_byte_equality(tmp_path):
    from egrs.offline.sim_metadata import resolve_installed_bddl
    suite=tmp_path/'libero_goal'; suite.mkdir(); (suite/'task.bddl').write_bytes(b'(task)')
    _,report=resolve_installed_bddl(tmp_path,metadata({'bddl_file':'task.bddl'}),embedded='(task)',runtime_identity=None)
    assert report['historical_source_byte_equality']=='verified'
    assert report['source_bddl_sha256']==hashlib.sha256(b'(task)').hexdigest()


@pytest.mark.parametrize('kind',['suite_outside','suite_other','file_outside','file_other'])
def test_metadata_symlink_cannot_escape_fixed_suite(tmp_path,kind):
    from egrs.offline.sim_metadata import resolve_installed_bddl
    root=tmp_path/'root'; root.mkdir()
    elsewhere=tmp_path/'outside'; elsewhere.mkdir(); (elsewhere/'task.bddl').write_bytes(b'(task)')
    other=root/'libero_object'; other.mkdir(); (other/'task.bddl').write_bytes(b'(task)')
    suite=root/'libero_goal'
    destination=elsewhere if kind.endswith('outside') else other
    try:
        if kind.startswith('suite'): suite.symlink_to(destination,target_is_directory=True)
        else:
            suite.mkdir(); (suite/'task.bddl').symlink_to(destination/'task.bddl')
    except OSError as error: pytest.skip('platform disallows test symlink: '+str(error))
    with pytest.raises(ValueError,match='escape|alias'):
        resolve_installed_bddl(root,metadata({'bddl_file':'task.bddl'}),embedded='(task)',runtime_identity=None)


@pytest.mark.parametrize('lock',[{}, {'revision':'C'*40,'bddl_sha256':{}},
    {'revision':'a'*40,'bddl_sha256':{'libero_goal/task.bddl':'bad'}},
    {'revision':'a'*40,'bddl_sha256':{'../task.bddl':'b'*64}}])
def test_metadata_malformed_libero_identity_rejected(lock,tmp_path):
    from egrs.offline.sim_metadata import resolve_installed_bddl
    suite=tmp_path/'libero_goal'; suite.mkdir(); (suite/'task.bddl').write_bytes(b'(task)')
    with pytest.raises(ValueError):
        resolve_installed_bddl(tmp_path,metadata({'bddl_file':'task.bddl'}),embedded='(task)',runtime_identity=lock)



def test_metadata_digest_failure_retains_observed_file_identity(tmp_path):
    from egrs.offline.sim_metadata import resolve_installed_bddl
    suite=tmp_path/'libero_goal'; suite.mkdir(); target=suite/'task.bddl'; target.write_bytes(b'(task)')
    lock={'revision':'a'*40,'bddl_sha256':{'libero_goal/task.bddl':'0'*64}}
    with pytest.raises(ValueError) as caught:
        resolve_installed_bddl(tmp_path,metadata({'bddl_file':'task.bddl'}),embedded=None,runtime_identity=lock)
    report=caught.value.bddl_provenance
    assert report['installed']['sha256']==hashlib.sha256(b'(task)').hexdigest()
    assert report['libero_source']['expected_bddl_sha256']=='0'*64
    assert report['identity_check']=='failed'
    assert report['historical_source_byte_equality']=='unverified'


# Literal instructions are the frozen source identities, never inferred from aliases.
HISTORICAL_ROWS = [
    ('open_the_middle_drawer_of_the_cabinet_demo.hdf5', 'open the middle drawer of the cabinet'),
    ('open_the_top_drawer_and_put_the_bowl_inside_demo.hdf5', 'open the top drawer and put the bowl inside'),
    ('put_the_bowl_on_top_of_the_cabinet_demo.hdf5', 'put the bowl on top of the cabinet'),
    ('put_the_cream_cheese_in_the_bowl_demo.hdf5', 'put the cream cheese in the bowl'),
    ('put_the_wine_bottle_on_top_of_the_cabinet_demo.hdf5', 'put the wine bottle on top of the cabinet'),
]


def historical_fixture(index=0):
    import json
    from pathlib import Path
    evidence=json.loads(Path('collaboration/tasks/021_runtime_compatibility_examples.json').read_text())
    filename,instruction=HISTORICAL_ROWS[index]; key='libero_goal/'+filename
    fields=evidence['conflicts'][key]['fields']
    args={'bddl_file':fields['env_args.bddl_file']['value'],
          'env_kwargs':{'bddl_file_name':fields['env_args.env_kwargs.bddl_file_name']['value']}}
    attrs={'bddl_file_name':fields['data.attrs.bddl_file_name']['value']}
    source={'file':key,'task_group':key,'episode':'demo_0','source_id':key+'#demo_0','instruction':instruction}
    identity={'dataset':'yifengzhu-hf/LIBERO-datasets','revision':'147fa5eb607bb696dd922c3518084a90954cd2f3'}
    package=json.loads(Path('docs/annotations/2026-10-23_registry_annotations_v2.json').read_text())
    reg=next(v['registry'] for v in package['registries'].values() if v['registry']['instruction']==instruction)
    return args,attrs,dict(suite='libero_goal',source=source,dataset_identity=identity,registry=reg)


@pytest.mark.parametrize('index',range(5))
@pytest.mark.parametrize('present',['both','argument','kwargs'])
def test_historical_rows_resolve_only_source_bound_canonical_identity(index,present,tmp_path):
    from egrs.offline.sim_metadata import resolve_bddl_metadata,resolve_installed_bddl
    args,attrs,context=historical_fixture(index)
    if present=='argument': del args['env_kwargs']['bddl_file_name']
    if present=='kwargs': del args['bddl_file']
    result=resolve_bddl_metadata(args,attrs,**context)
    canonical=HISTORICAL_ROWS[index][0].removesuffix('_demo.hdf5')+'.bddl'
    assert result['basename']==canonical
    assert result['fields']['data.attrs.bddl_file_name']['status']=='validated'
    for field,key,container in [('env_args.bddl_file','bddl_file',args),
        ('env_args.env_kwargs.bddl_file_name','bddl_file_name',args['env_kwargs'])]:
        row=result['fields'][field]
        assert row['status']==('normalized' if key in container else 'missing')
        if key in container:
            assert row['value']==container[key] and row['normalized_basename']==canonical
    audit=result['name_compatibility']
    assert audit['version']=='egrs.sim.historical-bddl-names.v2'
    assert audit['observed_in_prior_events'] is True
    assert audit['evidence_status']=='observed_in_prior_events'
    assert audit['evidence_source']=='collaboration/tasks/021_runtime_compatibility_examples.json'
    assert audit['dataset_identity']==context['dataset_identity']
    assert audit['source_file']==context['source']['file']
    assert audit['source_id']==context['source']['source_id']
    assert audit['instruction']==HISTORICAL_ROWS[index][1]
    suite=tmp_path/'libero_goal'; suite.mkdir(); (suite/canonical).write_bytes(b'(synthetic canonical)')
    lock={'revision':'a'*40,'bddl_sha256':{'libero_goal/'+canonical:hashlib.sha256(b'(synthetic canonical)').hexdigest()}}
    _,provenance=resolve_installed_bddl(tmp_path,result,embedded=None,runtime_identity=lock)
    assert provenance['historical_source_byte_equality']=='unverified'
    assert provenance['installed']['sha256']==hashlib.sha256(b'(synthetic canonical)').hexdigest()
    lock['bddl_sha256']['libero_goal/'+canonical]='0'*64
    with pytest.raises(ValueError,match='digest'):
        resolve_installed_bddl(tmp_path,result,embedded=None,runtime_identity=lock)


@pytest.mark.parametrize('issue',['no_context','no_source','no_registry','no_identity','wrong_dataset','wrong_revision',
    'no_canonical','all_old','wrong_canonical','wrong_task','wrong_task_group','wrong_source_id','wrong_episode',
    'wrong_instruction','wrong_registry','wrong_registry_goals','cross_suite','unknown_alias','unlisted_source'])
def test_historical_aliases_reject_unbound_or_conflicting_sources(issue,monkeypatch):
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    args,attrs,ctx=historical_fixture()
    if issue=='no_context': ctx={'suite':'libero_goal'}
    if issue=='no_source': ctx.pop('source')
    if issue=='no_registry': ctx.pop('registry')
    if issue=='no_identity': ctx.pop('dataset_identity')
    if issue=='wrong_dataset': ctx['dataset_identity']['dataset']='synthetic'
    if issue=='wrong_revision': ctx['dataset_identity']['revision']='wrong'
    if issue=='no_canonical': attrs={}
    if issue=='all_old': attrs['bddl_file_name']=args['bddl_file']
    if issue=='wrong_canonical': attrs['bddl_file_name']='other.bddl'
    if issue=='wrong_task': ctx['source']['file']=historical_fixture(1)[2]['source']['file']
    if issue=='wrong_task_group': ctx['source']['task_group']='other'
    if issue=='wrong_source_id': ctx['source']['source_id']+='wrong'
    if issue=='wrong_episode': ctx['source']['episode']='demo_10'
    if issue=='wrong_instruction': ctx['source']['instruction']='other instruction'
    if issue=='wrong_registry': ctx['registry']=historical_fixture(1)[2]['registry']
    if issue=='wrong_registry_goals': ctx['registry']['goals'][0]['target']='bowl'
    if issue=='cross_suite': ctx['suite']='libero_object'
    if issue=='unknown_alias': args['bddl_file']='unknown_historical.bddl'
    if issue=='unlisted_source':
        import egrs.offline.inventory as inventory
        original=inventory.catalog
        monkeypatch.setattr(inventory,'catalog',lambda:dict(original(),files=[]))
    with pytest.raises(ValueError) as caught: resolve_bddl_metadata(args,attrs,**ctx)
    assert caught.value.metadata_fields


def test_historical_malformed_field_retains_raw_evidence():
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    args,attrs,ctx=historical_fixture(); args['bddl_file']='../bad.bddl'
    with pytest.raises(ValueError) as caught: resolve_bddl_metadata(args,attrs,**ctx)
    field=caught.value.metadata_fields['env_args.bddl_file']
    assert field['status']=='malformed' and field['value']=='../bad.bddl'


@pytest.mark.parametrize('canonical_field',['argument','kwargs'])
def test_mixed_historical_and_canonical_env_fields_normalize_individually(canonical_field):
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    args,attrs,ctx=historical_fixture()
    if canonical_field=='argument': args['bddl_file']=attrs['bddl_file_name']
    else: args['env_kwargs']['bddl_file_name']=attrs['bddl_file_name']
    result=resolve_bddl_metadata(args,attrs,**ctx)
    assert result['basename']=='open_the_middle_drawer_of_the_cabinet.bddl'
    assert result['fields']['env_args.bddl_file']['status']==('validated' if canonical_field=='argument' else 'normalized')
    assert result['fields']['env_args.env_kwargs.bddl_file_name']['status']==('validated' if canonical_field=='kwargs' else 'normalized')


def test_historical_binding_accepts_last_frozen_episode_without_changing_context():
    from copy import deepcopy
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    args,attrs,ctx=historical_fixture(4)
    ctx['source']['episode']='demo_9'
    ctx['source']['source_id']=ctx['source']['file']+'#demo_9'
    original=deepcopy((args,attrs,ctx))
    result=resolve_bddl_metadata(args,attrs,**ctx)
    assert result['name_compatibility']['episode']=='demo_9'
    assert (args,attrs,ctx)==original


# These complete literals come from the frozen goal map, checked against registry below.
OBJECT_INSTRUCTIONS = [
    'pick up the alphabet soup and place it in the basket',
    'pick up the bbq sauce and place it in the basket',
    'pick up the butter and place it in the basket',
    'pick up the chocolate pudding and place it in the basket',
    'pick up the cream cheese and place it in the basket',
    'pick up the ketchup and place it in the basket',
    'pick up the milk and place it in the basket',
    'pick up the orange juice and place it in the basket',
    'pick up the salad dressing and place it in the basket',
    'pick up the tomato sauce and place it in the basket',
]


def object_historical_fixture(index=0):
    import json
    from pathlib import Path
    evidence=json.loads(Path('collaboration/tasks/022_object_name_evidence.json').read_text())
    row=evidence['rows'][index]; instruction=OBJECT_INSTRUCTIONS[index]
    goal_map=json.loads(Path('egrs/offline/assets/sim_goal_map.json').read_text())
    assert instruction in [v['instruction'] for v in goal_map['instructions']]
    package=json.loads(Path('docs/annotations/2026-10-23_registry_annotations_v2.json').read_text())
    reg=next(v['registry'] for v in package['registries'].values() if v['registry']['instruction']==instruction)
    key=row['suite']+'/'+row['file']
    args={'bddl_file':'/historical/'+row['suite']+'/'+row['legacy'],
          'env_kwargs':{'bddl_file_name':row['legacy']}}
    attrs={'bddl_file_name':row['canonical']}
    context=dict(suite=row['suite'],
        source={'file':key,'task_group':key,'episode':'demo_0','source_id':key+'#demo_0','instruction':instruction},
        dataset_identity={'dataset':'yifengzhu-hf/LIBERO-datasets','revision':'147fa5eb607bb696dd922c3518084a90954cd2f3'},
        registry=reg)
    return args,attrs,context


@pytest.mark.parametrize('index',range(10))
@pytest.mark.parametrize('present',['both','argument','kwargs','mixed'])
def test_object_historical_rows_keep_exact_binding_raw_values_and_evidence(index,present):
    import json
    from copy import deepcopy
    from pathlib import Path
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    row=json.loads(Path('collaboration/tasks/022_object_name_evidence.json').read_text())['rows'][index]
    args,attrs,ctx=object_historical_fixture(index)
    if present=='argument': del args['env_kwargs']['bddl_file_name']
    if present=='kwargs': del args['bddl_file']
    if present=='mixed': args['env_kwargs']['bddl_file_name']=row['canonical']
    before=deepcopy((args,attrs,ctx))
    result=resolve_bddl_metadata(args,attrs,**ctx)
    assert (args,attrs,ctx)==before
    assert result['suite']=='libero_object' and result['basename']==row['canonical']
    assert result['fields']['data.attrs.bddl_file_name']==dict(status='validated',value=row['canonical'],basename=row['canonical'])
    for field,key,container in [('env_args.bddl_file','bddl_file',args),
        ('env_args.env_kwargs.bddl_file_name','bddl_file_name',args['env_kwargs'])]:
        actual=result['fields'][field]
        if key not in container:
            assert actual=={'status':'missing'}
        elif present=='mixed' and key=='bddl_file_name':
            assert actual==dict(status='validated',value=row['canonical'],basename=row['canonical'])
        else:
            assert actual==dict(status='normalized',value=container[key],basename=row['legacy'],
                normalized_basename=row['canonical'],normalization_rule='egrs.sim.historical-bddl-names.v2')
    observed=index<4
    assert row['observed_in_prior_events'] is observed
    assert result['name_compatibility']=={
        'version':'egrs.sim.historical-bddl-names.v2',
        'evidence_source':'collaboration/tasks/022_object_name_evidence.json',
        'observed_in_prior_events':observed,
        'evidence_status':'observed_in_prior_events' if observed else 'anticipated_unobserved',
        'dataset_identity':ctx['dataset_identity'],'suite':'libero_object',
        'source_file':ctx['source']['file'],'task_group':ctx['source']['task_group'],
        'source_id':ctx['source']['source_id'],'episode':'demo_0','instruction':OBJECT_INSTRUCTIONS[index],
        'historical_basename':row['legacy'],'canonical_basename':row['canonical']}


@pytest.mark.parametrize('issue',['wrong_object','wrong_destination','cross_suite','cross_task',
    'unknown_alias','mixed_aliases','mixed_goal_alias','no_canonical','all_old','wrong_canonical',
    'wrong_dataset','wrong_revision','wrong_source_id','wrong_episode','wrong_task_group',
    'wrong_registry','wrong_registry_target','wrong_registry_destination','no_registry','no_identity','unlisted_source'])
def test_object_historical_aliases_reject_unbound_or_conflicting_sources(issue,monkeypatch):
    from egrs.offline.sim_metadata import resolve_bddl_metadata
    args,attrs,ctx=object_historical_fixture()
    if issue=='wrong_object': ctx['source']['instruction']=OBJECT_INSTRUCTIONS[1]
    if issue=='wrong_destination': ctx['source']['instruction']='pick up the alphabet soup and place it in the bowl'
    if issue=='cross_suite': ctx['suite']='libero_goal'
    if issue=='cross_task': ctx['source']['file']=object_historical_fixture(1)[2]['source']['file']
    if issue=='unknown_alias':
        args['bddl_file']='pick_alphabet_soup_and_place_it_in_the_basket.bddl'
        args['env_kwargs']['bddl_file_name']=args['bddl_file']
    if issue=='mixed_aliases': args['env_kwargs']['bddl_file_name']=object_historical_fixture(1)[0]['bddl_file']
    if issue=='mixed_goal_alias': args['env_kwargs']['bddl_file_name']=historical_fixture()[0]['bddl_file']
    if issue=='no_canonical': attrs={}
    if issue=='all_old': attrs['bddl_file_name']=args['bddl_file']
    if issue=='wrong_canonical': attrs['bddl_file_name']=object_historical_fixture(1)[1]['bddl_file_name']
    if issue=='wrong_dataset': ctx['dataset_identity']['dataset']='synthetic'
    if issue=='wrong_revision': ctx['dataset_identity']['revision']='wrong'
    if issue=='wrong_source_id': ctx['source']['source_id']+='wrong'
    if issue=='wrong_episode': ctx['source']['episode']='demo_10'
    if issue=='wrong_task_group': ctx['source']['task_group']='other'
    if issue=='wrong_registry': ctx['registry']=object_historical_fixture(1)[2]['registry']
    if issue=='wrong_registry_target': ctx['registry']['goals'][0]['target']='butter'
    if issue=='wrong_registry_destination': ctx['registry']['goals'][0]['destination']='bowl'
    if issue=='no_registry': ctx.pop('registry')
    if issue=='no_identity': ctx.pop('dataset_identity')
    if issue=='unlisted_source':
        import egrs.offline.inventory as inventory
        original=inventory.catalog
        monkeypatch.setattr(inventory,'catalog',lambda:dict(original(),files=[]))
    with pytest.raises(ValueError) as caught: resolve_bddl_metadata(args,attrs,**ctx)
    assert caught.value.metadata_fields
