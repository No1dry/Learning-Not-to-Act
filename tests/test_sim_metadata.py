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
