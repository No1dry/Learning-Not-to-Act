"""Real pinned pure resolver, synthetic text/files only; no simulator imports."""
import hashlib
from pathlib import Path
import pytest

MAC='/Users/yifengz/workspace/libero-dev/chiliocosm/assets/'
HOME='/home/yifengz/workspace/libero-dev/chiliocosm/assets/'
FLOOR=MAC+'scenes/../textures/light-gray-floor-tile.png'
BOWL=MAC+'stable_scanned_objects/akita_black_bowl/texture.png'

def resolve(text,root):
    from egrs.offline.sim_xml_assets import resolve_source_xml
    return resolve_source_xml(text,roots={'libero':str(root),'robosuite':str(root)})

def sha(text): return hashlib.sha256(text.encode()).hexdigest()

def asset(root,suffix):
    path=root/suffix; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'synthetic asset')
    return path.resolve().as_posix()


def test_observed_mac_paths_preserve_only_file_spans_and_full_source_audit(tmp_path):
    floor=asset(tmp_path,'textures/light-gray-floor-tile.png')
    bowl=asset(tmp_path,'stable_scanned_objects/akita_black_bowl/texture.png')
    text=f"<mujoco model='\u5408\u6210'><asset><texture name='floor' file='{FLOOR}'/><texture file=\"{BOWL}\"/>"+f"<texture file='{FLOOR}'/></asset><!-- {FLOOR} --><worldbody><body name='kept'/></worldbody></mujoco>"
    out,report=resolve(text,tmp_path)
    expected=text.replace("file='"+FLOOR+"'","file='"+floor+"'").replace('file=\"'+BOWL+'\"','file=\"'+bowl+'\"')
    assert out==expected
    assert report['status']=='resolved' and report['errors']==[]
    assert report['resolver_version']=='egrs.sim.historical-xml-assets.v1'
    assert report['source_xml_sha256']==sha(text)
    intermediate=text.replace("file='"+FLOOR+"'","file='"+HOME+FLOOR[len(MAC):]+"'").replace('file=\"'+BOWL+'\"','file=\"'+HOME+BOWL[len(MAC):]+'\"')
    assert report['intermediate_xml_sha256']==sha(intermediate)
    assert report['processed_xml_sha256']==sha(expected)
    core=report['intermediate_core_report']
    assert core['original_xml']==intermediate and core['original_xml_sha256']==sha(intermediate)
    assert report['source_xml']==text
    assert [x['occurrence'] for x in report['mappings']]==[0,1,2]
    assert [x['original'] for x in report['mappings']]==[FLOOR,BOWL,FLOOR]
    for row in report['mappings']:
        assert row['intermediate']==HOME+row['original'][len(MAC):]
        assert row['rule']=='mac_chiliocosm_exact_root_to_core_home'
        assert row['target_sha256']==hashlib.sha256(b'synthetic asset').hexdigest()
    assert report['mappings'][0]['relative_suffix']=='textures/light-gray-floor-tile.png'


@pytest.mark.parametrize('prefix',[HOME,'/x/libero/assets/','/x/robosuite/models/assets/'])
def test_existing_home_and_official_roots_still_resolve(tmp_path,prefix):
    target=asset(tmp_path,'textures/t.png'); original=prefix+'textures/t.png'
    text=f'<mujoco><asset><texture file="{original}"/></asset></mujoco>'
    out,report=resolve(text,tmp_path)
    assert out==text.replace(original,target)
    assert report['source_xml_sha256']==report['intermediate_xml_sha256']==sha(text)
    assert report['mappings'][0]['original']==report['mappings'][0]['intermediate']==original


@pytest.mark.parametrize('path,reason',[(MAC+'../outside.png','escapes'),
    (MAC+'a/../../outside.png','escapes'),(MAC+'missing.png','missing'),
    (MAC[:-1]+'-lookalike/textures/t.png','unknown'),
    (MAC+'libero/assets/textures/t.png','ambiguous'),
    ('/unknown/textures/t.png','unknown')])
def test_unresolved_paths_remain_gaps_with_actual_original(tmp_path,path,reason):
    asset(tmp_path,'textures/t.png')
    text=f'<mujoco><asset><texture file="{path}"/></asset></mujoco>'
    out,report=resolve(text,tmp_path)
    assert out is None and report['status']=='unresolved'
    assert report['processed_xml_sha256'] is None
    assert report['source_xml_sha256']==sha(text)
    assert report['errors'][0]['original']==path
    assert reason in report['errors'][0]['error']


def test_symlink_escape_is_rejected(tmp_path):
    root=tmp_path/'root'; root.mkdir(); outside=tmp_path/'outside'; outside.mkdir()
    asset(outside,'t.png')
    try: (root/'link').symlink_to(outside,target_is_directory=True)
    except OSError as error:
        if getattr(error,'winerror',None)==1314 or isinstance(error,PermissionError): pytest.skip('OS symlink privilege unavailable: '+str(error))
        raise
    out,report=resolve(f'<mujoco><asset><texture file="{MAC}link/t.png"/></asset></mujoco>',root)
    assert out is None and 'escapes' in report['errors'][0]['error']


@pytest.mark.parametrize('body',[f'<include file="{FLOOR}"/>',f'<worldbody><geom file="{FLOOR}"/></worldbody>',
    f'<asset><texture file="{FLOOR}" fileleft="{FLOOR}"/></asset>','<extension/>',
    '<compiler strippath="true"/>'])
def test_external_dependencies_cannot_be_translated_away(tmp_path,body):
    asset(tmp_path,'textures/light-gray-floor-tile.png')
    out,report=resolve('<mujoco>'+body+'</mujoco>',tmp_path)
    assert out is None and report['errors']


def test_duplicate_path_outside_asset_keeps_occurrence_specific_failure(tmp_path):
    asset(tmp_path,'textures/light-gray-floor-tile.png')
    text=f'<mujoco><texture file="{FLOOR}"/><asset><texture file="{FLOOR}"/></asset></mujoco>'
    out,report=resolve(text,tmp_path)
    assert out is None
    assert report['errors'][0]['occurrence']==0 and report['errors'][0]['original']==FLOOR
    assert report['mappings'][0]['occurrence']==1 and report['mappings'][0]['original']==FLOOR


def test_entities_and_ambiguous_markers_are_checked_before_normalization(tmp_path):
    asset(tmp_path,'textures/t.png')
    path=MAC+'libero/assets/../../textures/t.png'
    out,report=resolve(f'<mujoco><asset><texture file="{path}"/></asset></mujoco>',tmp_path)
    assert out is None and 'ambiguous' in report['errors'][0]['error']
    out,report=resolve('<!DOCTYPE mujoco [<!ENTITY a SYSTEM "file:///outside">]><mujoco/>',tmp_path)
    assert out is None and 'DTD' in report['errors'][0]['error']
