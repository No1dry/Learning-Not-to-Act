"""Synthetic native/source boundaries only; never imports a simulator."""
import copy
import importlib
import io
import json
from types import SimpleNamespace

import h5py
import numpy as np
import pytest


def native():
    return importlib.import_module('egrs.offline.sim_native')


def registry():
    from pathlib import Path
    package=json.loads(Path('docs/annotations/2026-10-23_registry_annotations_v2.json').read_text())
    return next(x['registry'] for x in package['registries'].values()
                if x['registry']['instruction']=='open the top drawer and put the bowl inside')


def make_source(tmp_path, *, missing=None):
    path = tmp_path/'synthetic.hdf5'
    with h5py.File(path, 'w') as f:
        d=f.create_group('data')
        d.attrs['env_args']=json.dumps({'problem_name':'synthetic', 'env_name':'synthetic',
            'bddl_file':'old/task.bddl','type':1,'env_kwargs':{'bddl_file_name':'old/task.bddl',
            'robots':['Panda'],'controller_configs':{'type':'OSC_POSE'},'control_freq':20,
            'camera_names':['agentview','robot0_eye_in_hand'],'camera_heights':4,'camera_widths':5,
            'camera_depths':False,'camera_segmentations':None}})
        d.attrs['bddl_file_content']='(synthetic bddl)'
        d.attrs['bddl_file_name']='old/task.bddl'
        d.attrs['macros_image_convention']='opengl'
        d.attrs['problem_info']=json.dumps({'language_instruction': registry()['instruction']})
        ep=d.create_group('demo_0'); ep.attrs['model_file']='<mujoco><worldbody/></mujoco>'
        ep.attrs['num_samples']=3
        ep.create_dataset('states',data=np.zeros((3,12)))
        ep.create_dataset('actions',data=np.zeros((3,7)))
        for camera in ('agentview_rgb','eye_in_hand_rgb'):
            ep.create_dataset('obs/'+camera,data=np.zeros((3,4,5,3),dtype=np.uint8))
        # An unrelated invalid demo must never be inspected.
        d.create_group('demo_10')
        if missing == 'xml': del ep.attrs['model_file']
        if missing == 'env_args': del d.attrs['env_args']
        if missing in ('states','actions'): del ep[missing]
        if missing == 'bddl': del d.attrs['bddl_file_content']
    return path


def descriptor():
    return {'source_id':'synthetic-source','file':'synthetic.hdf5','episode':'demo_0',
            'T':3,'instruction':registry()['instruction'],'orientation':'opengl'}


def test_source_inspects_only_designated_episode_and_records_hashes(tmp_path):
    make_source(tmp_path)
    with native().SourceEpisode(tmp_path, descriptor()) as episode:
        assert episode.inspection['states']['shape'] == [3,12]
        assert episode.inspection['actions']['shape'] == [3,7]
        assert len(episode.inspection['xml_sha256']) == 64
        assert episode.env_args['env_kwargs']['controller_configs'] == {'type':'OSC_POSE'}
        assert episode.state(1).shape == (12,)


@pytest.mark.parametrize('missing',['xml','env_args','states','actions','bddl'])
def test_missing_required_source_data_is_gap_not_demo_guess(tmp_path, missing):
    make_source(tmp_path,missing=missing)
    with pytest.raises(ValueError):
        with native().SourceEpisode(tmp_path,descriptor()): pass


def test_segmentation_filters_type_before_id_and_bbox_orientation():
    raw=np.zeros((4,5,2),dtype=int)
    raw[0,1]=[5,7]; raw[3,4]=[6,7]
    mask=native().geom_mask(raw,[7],geom_type=5)
    from egrs.offline.sim_alignment import visible_bbox
    assert visible_bbox(mask,orientation='flip_vertical') == [.2,.75,.4,1.]


def test_active_geoms_exclude_stationary_cabinet_and_other_drawer():
    model=SimpleNamespace(body_parentid=np.array([0,0,1,1,2]), geom_bodyid=np.array([1,2,3,4]))
    assert native().descendant_geoms(model,[2],[0,1,2,3]) == [1,3]


def test_background_match_cannot_prove_alignment():
    rgb=np.zeros((10,10,3),dtype=np.uint8)
    support=np.zeros((10,10),dtype=bool)
    with pytest.raises(ValueError, match='foreground'):
        native().image_residual(rgb,rgb,support,min_pixels=2)
    support[0,:2]=True
    changed=rgb.copy(); changed[0,:2]=255
    assert native().image_residual(rgb,changed,support,min_pixels=2) == 1.0


def test_native_atoms_evaluated_independently_and_annotation_only_recorded():
    from egrs.offline.sim_contract import mapping_for
    goals=mapping_for(registry())
    inner=SimpleNamespace(_eval_predicate=lambda atom: atom[0]=='open')
    truths,audit=native().evaluate_atoms(inner,goals)
    assert truths == {'g0':True,'g1':False}
    assert audit[0]['annotation_only'] is True


def test_mechanism_evidence_requires_active_part_and_reference():
    from egrs.offline.sim_contract import mapping_for
    goal=mapping_for(registry())[0]
    ref=np.ones((4,5),dtype=bool); part=np.zeros((4,5),dtype=bool); part[1:3,1:3]=True
    assert native().make_evidence(goal,{'reference':ref},'agentview','identity','unknown',min_pixels=2)==[]
    evidence=native().make_evidence(goal,{'reference':ref,'active_part':part},'agentview','identity','unknown',min_pixels=2)
    assert any('relation' in e['supports'] for e in evidence)
    assert not any('interaction' in e['supports'] for e in evidence)


def request():
    return {'format':'egrs.sim.request.v1','request_id':'r1','source_root':'.','source':descriptor(),
        'registry':registry(),'frames':[{'frame':i,'images':{c:{'path':f'{c}-{i}.png','width':5,'height':4}
          for c in ('agentview','wrist')}} for i in (0,1,2)],'config':{}}


class FakeAdapter:
    def __init__(self, req, *, emit=None):
        self.req=req; self.inspection={'synthetic':True}; self.audit=[]; self.closed=False
    def align(self):
        from egrs.offline.sim_alignment import choose_alignment
        return choose_alignment([{'rule':'same_state','residuals':[0.,0.],
            'samples':[{'frame':0,'camera':c} for c in ('agentview','wrist')]}],
            basis=['synthetic correspondence'],orientation='identity',threshold=.01)
    def frame(self,frame,alignment):
        if frame==1: raise RuntimeError('synthetic render failure')
        from egrs.offline.sim_contract import mapping_for,entity_aliases
        goals=mapping_for(self.req['registry']); aliases=entity_aliases(goals)
        return {'format':'egrs.sim.frame.v1','source_id':'synthetic-source','frame':frame,
          'alignment':alignment,'goals':[{'goal_ref':g['goal_ref'],'kind':g['kind'],
          'entity_ref':aliases[g['atom'][1]],'native_truth':True,'grasp':'unknown','evidence':[]} for g in goals]}, {'frame':frame}
    def close(self): self.closed=True


def test_worker_retains_incremental_frame_on_failure_and_stdout_is_json():
    worker=importlib.import_module('egrs.offline.sim_worker')
    events=[]; adapters=[]
    def factory(req, *, emit=None):
        print('native diagnostic')
        adapters.append(FakeAdapter(req)); return adapters[-1]
    out=io.StringIO(); err=io.StringIO()
    worker.serve(io.StringIO(json.dumps(request())+'\n'),out,err,adapter_factory=factory)
    events=[json.loads(line) for line in out.getvalue().splitlines()]
    assert 'native diagnostic' in err.getvalue()
    assert [e['data']['frame'] for e in events if e['type']=='frame'] == [0]
    result=events[-1]['data']
    assert result['status']=='partial' and len(result['frames'])==1
    assert result['errors'][0]['frame']==1
    assert adapters[0].closed


def test_duplicate_or_out_of_bounds_frames_rejected_before_factory():
    worker=importlib.import_module('egrs.offline.sim_worker')
    req=request(); req['frames'].append(copy.deepcopy(req['frames'][0]))
    with pytest.raises(ValueError): worker.validate_request(req)
    req=request(); req['frames'][0]['frame']=3
    with pytest.raises(ValueError): worker.validate_request(req)


def test_visible_surface_excludes_occluders_walls_and_region_exterior():
    y,x=np.mgrid[-3:4,-3:4]
    world=np.stack((x*.01,y*.01,np.zeros_like(x)),axis=-1)
    visible=np.ones((7,7),dtype=bool)
    visible[3,3]=False  # foreground target occludes destination here
    mask=native().surface_support(world,visible,camera_position=np.array([0,0,1.]),
        center=np.zeros(3),rotation=np.eye(3),half_size=np.array([.02,.02,.01]),
        vertical_margin=.005)
    assert mask[2,2] and not mask[3,3] and not mask[1,1]
    wall=np.stack((np.zeros_like(x),y*.01,x*.01),axis=-1)
    assert not native().surface_support(wall,np.ones((7,7),dtype=bool),camera_position=np.array([1.,0,0]),
        center=np.zeros(3),rotation=np.eye(3),half_size=np.ones(3),vertical_margin=.005).any()


def test_png_must_equal_designated_hdf_frame_and_hash_is_audited(tmp_path):
    from PIL import Image
    make_source(tmp_path)
    adapter=native().NativeAdapter.__new__(native().NativeAdapter)
    adapter.episode=native().SourceEpisode(tmp_path,descriptor())
    path=tmp_path/'rgb.png'; Image.new('RGB',(5,4)).save(path)
    adapter.images={0:{'agentview':{'path':str(path),'width':5,'height':4}}}
    adapter.image_bindings={}
    try:
        adapter._original(0,'agentview')
        assert len(adapter.image_bindings['0:agentview']['pixel_sha256'])==64
        Image.new('RGB',(5,4),'white').save(path)
        with pytest.raises(ValueError,match='differs'): adapter._original(0,'agentview')
    finally: adapter.episode.close()


def alignment_adapter(values, *, failure=None):
    adapter=native().NativeAdapter.__new__(native().NativeAdapter)
    adapter.images={0:{},1:{},2:{}}
    adapter.episode=SimpleNamespace(T=3,orientation='opengl',state=lambda index:np.array([index]))
    adapter.config={'probe_count':2,'rgb_threshold':.03,'min_visible_pixels':2,'replay_state_atol':1e-6}
    adapter.inspection={'env_args_sha256':'synthetic'}; adapter.audit=[]; adapter.image_bindings={}
    adapter.env=SimpleNamespace(sim=SimpleNamespace(get_state=lambda:np.array([adapter.current+1])))
    def restore(index,action=None):
        adapter.current=index
        adapter.rule='replay_action' if action is not None else 'same_state' if index in (0,1) else 'next_state'
        # Distinguish direct state via RGB scoring frame/index comparison below.
        adapter.action=action
        if failure and action is not None: raise ValueError('replay failed')
    adapter._restore=restore
    adapter._render=lambda camera:(None,None)
    def compare(frame,renders,orientation):
        rule='replay_action' if adapter.action is not None else 'same_state' if adapter.current==frame else 'next_state'
        return [values.get((rule,orientation),1.)]*2
    adapter._compare=compare
    return adapter


def test_alignment_ambiguous_orientation_or_failed_candidate_stays_gap():
    a=alignment_adapter({('next_state','identity'):0.})
    assert a.align()['rule']=='next_state'
    a=alignment_adapter({('next_state','identity'):0.,('next_state','flip_vertical'):0.})
    assert not a.align()['accepted']
    a=alignment_adapter({('next_state','identity'):0.},failure=True)
    assert not a.align()['accepted']


def test_final_replay_needs_known_next_state_corroboration():
    a=alignment_adapter({('replay_action','identity'):0.})
    assert a.align()['rule']=='replay_action' and a.replay_corroborated
    a=alignment_adapter({('replay_action','identity'):0.})
    a.env.sim.get_state=lambda:np.array([99.])
    assert a.align()['rule']=='replay_action' and not a.replay_corroborated


def test_compiled_drawer_handle_alone_cannot_be_active_part_evidence():
    a=native().NativeAdapter.__new__(native().NativeAdapter)
    a.model=SimpleNamespace(geom_type=np.array([7,7]),geom_dataid=np.array([0,1]),
        mesh_id2name=lambda index:['wooden_cabinet_top_vis','wooden_cabinet_top_handle_vis'][index])
    assert a._mechanism_visual_ids([0,1])==[0]


def test_native_frame_mismatch_masks_all_truth_and_no_destination_depth_work():
    from egrs.offline.sim_contract import mapping_for,entity_aliases
    a=alignment_adapter({('same_state','identity'):0.})
    alignment=a.align()
    a.request=request(); a.goals=mapping_for(registry()); a.aliases=entity_aliases(a.goals)
    a.inner=SimpleNamespace(_eval_predicate=lambda atom:atom[0]=='open')
    a.refresh=lambda env:None
    a._compare=lambda *args:[.5,.5]
    a.image_bindings={f'0:{c}':{'pixel_sha256':'synthetic'} for c in ('agentview','wrist')}
    facts,audit=a.frame(0,alignment)
    assert not facts['alignment']['accepted']
    assert [g['native_truth'] for g in facts['goals']]==[True,False]
    assert all(not g['evidence'] and g['grasp']=='unknown' for g in facts['goals'])
    assert audit['gaps']==['per_frame_RGB_foreground_mismatch']


def test_isolated_transport_journals_prior_event_on_timeout(tmp_path,monkeypatch):
    import subprocess
    import sys
    worker=importlib.import_module('egrs.offline.sim_worker')
    script=tmp_path/'fake_worker.py'
    script.write_text("import sys,json,time\nr=json.loads(sys.stdin.readline())\n"
        "print(json.dumps({'format':'egrs.sim.event.v1','request_id':r['request_id'],'source_id':r['source']['source_id'],"
        "'sequence':0,'type':'audit','data':{'completed':'synthetic'}}),flush=True)\ntime.sleep(20)\n")
    real_popen=subprocess.Popen
    monkeypatch.setattr(worker.subprocess,'Popen',lambda args,**kwargs:real_popen([sys.executable,str(script)],**kwargs))
    events=[]
    with pytest.raises(worker.WorkerFailure,match='timeout') as error:
        worker.run_isolated(request(),python=sys.executable,timeout_seconds=.5,on_event=events.append)
    assert events[0]['data']=={'completed':'synthetic'}
    assert error.value.events==events


def test_isolated_transport_rejects_foreign_source_event(tmp_path,monkeypatch):
    import subprocess
    import sys
    worker=importlib.import_module('egrs.offline.sim_worker')
    script=tmp_path/'foreign_worker.py'
    script.write_text("import sys,json\nr=json.loads(sys.stdin.readline())\n"
        "print(json.dumps({'format':'egrs.sim.event.v1','request_id':r['request_id'],'source_id':'foreign',"
        "'sequence':0,'type':'audit','data':{}}),flush=True)\n")
    real_popen=subprocess.Popen
    monkeypatch.setattr(worker.subprocess,'Popen',lambda args,**kwargs:real_popen([sys.executable,str(script)],**kwargs))
    with pytest.raises(worker.WorkerFailure,match='identity'):
        worker.run_isolated(request(),python=sys.executable,timeout_seconds=5)


@pytest.mark.parametrize('mismatch',['none','hash','worker_root'])
def test_real_launch_binds_method_before_native_with_stale_cwd(tmp_path,monkeypatch,mismatch):
    """Keep the real launch; fake only the native adapter through an import hook."""
    import sys
    from pathlib import Path
    worker=importlib.import_module('egrs.offline.sim_worker')
    req=request(); req['frames']=req['frames'][:1]
    facts=FakeAdapter(req).frame(0,FakeAdapter(req).align())[0]
    stale=tmp_path/'stale'; (stale/'egrs').mkdir(parents=True)
    shadow=tmp_path/'shadow-imported'
    (stale/'egrs/__init__.py').write_text(
        f"from pathlib import Path\nPath({str(shadow)!r}).write_text('stale')\nraise RuntimeError('stale egrs selected')\n")
    for name in ('core','bddl','libero-assets','robosuite-assets'):
        (stale/name).mkdir()
    req['config']={'core':{'root':'core'},'bddl_root':'bddl',
        'asset_roots':{'libero':'libero-assets','robosuite':'robosuite-assets'}}
    hook=tmp_path/'hook'; hook.mkdir()
    marker=tmp_path/'native-started'
    fake=hook/'fake_native.py'
    fake.write_text("import sys\nfrom pathlib import Path\nclass NativeAdapter:\n"
        "    def __init__(self,request,*,emit=None):\n"
        f"        Path({str(marker)!r}).write_text('started')\n"
        "        c=request['config']\n"
        "        self.inspection={'cwd':str(Path.cwd()),'worker':sys.modules['egrs.offline.sim_worker'].__file__,\n"
        "            'paths':[str(Path(p).resolve(strict=True)) for p in [c['core']['root'],c['bddl_root'],*c['asset_roots'].values()]]}\n"
        "        self.audit=[]\n"
        "    def align(self): return {}\n"
        f"    def frame(self,frame,alignment): return {facts!r},{{'frame':frame}}\n"
        "    def close(self): pass\n")
    (hook/'sitecustomize.py').write_text(
        "import sys,importlib.abc,importlib.util\nclass NativeOnly(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self,fullname,path=None,target=None):\n"
        f"        if fullname=='egrs.offline.sim_native': return importlib.util.spec_from_file_location(fullname,{str(fake)!r})\n"
        "sys.meta_path.insert(0,NativeOnly())\n")
    if mismatch=='worker_root':
        with (hook/'sitecustomize.py').open('a') as stream:
            stream.write("import types\nm=types.ModuleType('egrs.offline.sim_worker')\n"
                f"m.__file__={str(hook/'foreign_worker.py')!r}\n"
                f"m.main=lambda: open({str(marker)!r},'w').write('foreign worker executed')\n"
                "sys.modules[m.__name__]=m\n")
    # The request is built before changing cwd; native paths deliberately stay relative.
    monkeypatch.chdir(stale)
    if mismatch!='none':
        if mismatch=='hash':
            monkeypatch.setattr(worker,'code_identity',lambda:{'identity':'0'*64})
        with pytest.raises(worker.WorkerFailure) as error:
            worker.run_isolated(req,python=sys.executable,module_paths=[hook],timeout_seconds=5)
        assert 'implementation identity mismatch' in error.value.stderr
        assert error.value.events==[]
        assert not marker.exists()
    else:
        result=worker.run_isolated(req,python=sys.executable,module_paths=[hook],timeout_seconds=5)
        assert result['status']=='complete'
        assert result['frames']==[facts]
        assert Path(result['inspection']['worker']).resolve()==Path(worker.__file__).resolve()
        assert result['inspection']['cwd']==str(stale)
        assert result['inspection']['paths']==[str(stale/name) for name in ('core','bddl','libero-assets','robosuite-assets')]
        assert marker.read_text()=='started'
    assert not shadow.exists()


@pytest.mark.parametrize('camera_order', [['agentview','robot0_eye_in_hand'],['robot0_eye_in_hand','agentview']])
def test_native_constructor_keeps_saved_controller_and_restores_exact_source_xml(tmp_path,monkeypatch,camera_order):
    """Fake only native/core boundaries; exercise the concrete adapter constructor."""
    import sys
    import types
    from egrs import core
    (tmp_path/'libero_goal').mkdir()
    make_source(tmp_path/'libero_goal')
    with h5py.File(tmp_path/'libero_goal/synthetic.hdf5','r+') as source_file:
        data=source_file['data']; args=json.loads(data.attrs['env_args'])
        dimensions={'agentview':(6,8),'robot0_eye_in_hand':(4,5)}
        args['env_kwargs']['camera_names']=camera_order
        args['env_kwargs']['camera_heights']=[dimensions[n][0] for n in camera_order]
        args['env_kwargs']['camera_widths']=[dimensions[n][1] for n in camera_order]
        data.attrs['env_args']=json.dumps(args)
        del data['demo_0/obs/agentview_rgb']
        data['demo_0/obs'].create_dataset('agentview_rgb',data=np.zeros((3,6,8,3),dtype=np.uint8))
    bddl=tmp_path/'bddl/libero_goal'; bddl.mkdir(parents=True)
    (bddl/'task.bddl').write_text('(synthetic bddl)')
    module_file=tmp_path/'native_source.py'; module_file.write_text('# synthetic native source\n')
    events=[]
    model=SimpleNamespace(get_xml=lambda:'<mujoco><worldbody/></mujoco>')
    env=SimpleNamespace(sim=SimpleNamespace(model=model,get_state=lambda:np.zeros(12)),action_dim=7,
        control_timestep=.05,model_timestep=.002,
        seed=lambda value:events.append(('seed',value)),
        reset_from_xml_string=lambda xml:events.append(('xml',xml)),
        close=lambda:events.append(('close',)),
        parsed_problem={'goal_state':[['in','akita_black_bowl_1','wooden_cabinet_1_top_region']]},
        object_states_dict={'akita_black_bowl_1':None,'wooden_cabinet_1_top_region':None})
    def task(**kwargs): events.append(('constructor',kwargs)); return env
    class Base:
        def __init__(self,bddl_file_name,robots,controller_configs,control_freq,camera_names,
                     camera_heights,camera_widths,camera_depths,camera_segmentations): pass
    def module(name,**values):
        item=types.ModuleType(name); item.__dict__.update(values); item.__file__=str(module_file)
        monkeypatch.setitem(sys.modules,name,item); return item
    monkeypatch.setattr(core,'activate',lambda config:{'revision':'synthetic'})
    monkeypatch.setattr(native().importlib.metadata,'version',lambda name:'synthetic')
    module('benchmark.remaining_goals.libero_compat',apply_libero_compat=lambda:None,
           reset_scene=lambda e,**kw:events.append(('reset',kw)))
    module('benchmark.remaining_goals.libero_env',restore_raw_state=lambda *a:None,fresh_observation=lambda *a:None)
    module('benchmark.remaining_goals.finish.environment',_release=lambda *a:None,
           _verify_demo_native_references=lambda e:{'checked':True},_layout=lambda m:{'synthetic':True})
    module('benchmark.remaining_goals.finish.xml_assets',resolve_xml=lambda xml,**kw:(xml,{'synthetic':True}))
    module('libero.libero.envs',TASK_MAPPING={'synthetic':task})
    module('libero.libero.envs.bddl_base_domain',BDDLBaseDomain=Base)
    module('libero.libero.envs.predicates.base_predicates')
    module('robosuite.environments.robot_env')
    module('mujoco',mjtObj=SimpleNamespace(mjOBJ_GEOM=5))
    req=request(); req['source_root']=str(tmp_path); req['source']['file']='libero_goal/synthetic.hdf5'
    req['config']={'core':{},'bddl_root':str(tmp_path/'bddl'),
        'versions':{k:'synthetic' for k in ('numpy','h5py','robosuite','mujoco')},
        'module_sha256':{k:native().sha256(module_file.read_bytes()) for k in
            ('libero.libero.envs.bddl_base_domain','libero.libero.envs.predicates.base_predicates','robosuite.environments.robot_env')}}
    adapter=native().NativeAdapter(req)
    try:
        kwargs=events[0][1]
        assert kwargs['controller_configs']=={'type':'OSC_POSE'}
        assert kwargs['robots']==['Panda'] and kwargs['camera_segmentations'] is None
        assert kwargs['camera_names']==camera_order
        assert kwargs['camera_heights']==[dimensions[n][0] for n in camera_order]
        assert kwargs['camera_widths']==[dimensions[n][1] for n in camera_order]
        assert events[2]==('reset',{'max_attempts':3})
        assert events[3]==('xml','<mujoco><worldbody/></mujoco>')
        assert adapter.inspection['goal_mapping'][0]['annotation_only'] is True
    finally: adapter.close()


def test_drawer_handle_is_not_a_fixed_reference():
    from egrs.offline.sim_contract import mapping_for
    a=native().NativeAdapter.__new__(native().NativeAdapter)
    obj=SimpleNamespace(visual_geoms=['base','panel','handle'],joints=['slide'])
    gripper=SimpleNamespace(visual_geoms=[])
    a.model=SimpleNamespace(geom_name2id=lambda name:['base','panel','handle'].index(name),
        joint_name2id=lambda name:0,jnt_type=np.array([2]),jnt_bodyid=np.array([2]),
        body_parentid=np.array([0,0,1]),geom_bodyid=np.array([1,2,2]),
        geom_type=np.array([7,7,7]),geom_dataid=np.array([0,1,2]),
        mesh_id2name=lambda index:['wooden_cabinet_base_vis','wooden_cabinet_top_vis','wooden_cabinet_top_handle_vis'][index])
    a.inner=SimpleNamespace(objects_dict={'cabinet':obj},fixtures_dict={},
        object_sites_dict={'wooden_cabinet_1_top_region':SimpleNamespace(parent_name='cabinet',joints=['slide'])})
    a.env=SimpleNamespace(robots=[SimpleNamespace(gripper=gripper)]); a.geom_type=5
    raw=np.array([[[5,0],[5,2]]])
    masks,_=a._parts(mapping_for(registry())[0],raw)
    assert masks['reference'].tolist()==[[True,False]]
    assert not masks['active_part'].any()


def test_source_runtime_substep_budget_is_enforced_before_replay():
    a=native().NativeAdapter.__new__(native().NativeAdapter)
    a.config={'max_physics_substeps':100}
    a.env=SimpleNamespace(control_timestep=.05,model_timestep=.00001)
    with pytest.raises(ValueError,match='substep'): a._check_substeps()


def test_native_initialization_failure_preserves_source_inspection_in_worker_result():
    worker=importlib.import_module('egrs.offline.sim_worker')
    def broken(req, *, emit=None):
        error=ValueError('synthetic native initialization failed')
        error.inspection={'xml_sha256':'synthetic-inspected'}
        error.audit=[{'native_initialization':'failed after source inspection'}]
        raise error
    events=[]
    result=worker.process_source(request(),adapter_factory=broken,emit=events.append)
    assert result['inspection']=={'xml_sha256':'synthetic-inspected'}
    assert result['audit']==[{'native_initialization':'failed after source inspection'}]
    assert result['status']=='failed'


def test_worker_modules_import_without_native_or_model_packages():
    import subprocess
    import sys
    completed=subprocess.run([sys.executable,'-c',
        "import sys; import egrs.offline.sim_worker; import egrs.offline.sim_native; "
        "assert not any(n in sys.modules for n in ('torch','libero','robosuite','mujoco'))"],
        capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr


@pytest.mark.parametrize('names', [['agentview','robot0_eye_in_hand'],['robot0_eye_in_hand','agentview']])
def test_saved_camera_order_binds_unequal_dimensions_by_name(names):
    a=native().NativeAdapter.__new__(native().NativeAdapter)
    a.inspection={'cameras':{'agentview':{'shape':[3,6,8,3]},'wrist':{'shape':[3,4,5,3]}}}
    dimensions={'agentview':(6,8),'robot0_eye_in_hand':(4,5)}
    kwargs={'robots':['Panda'],'controller_configs':{'type':'OSC_POSE'},'control_freq':20,
        'camera_names':names,'camera_heights':[dimensions[n][0] for n in names],
        'camera_widths':[dimensions[n][1] for n in names],'camera_depths':False,'camera_segmentations':None}
    original=copy.deepcopy(kwargs)
    a._validate_kwargs(kwargs)
    assert kwargs==original
    kwargs['camera_heights'].reverse()
    with pytest.raises(ValueError,match='dimensions'): a._validate_kwargs(kwargs)


def test_equivalent_next_and_replay_are_accepted_with_next_state_representative():
    from egrs.offline.sim_alignment import frame_operation
    a=alignment_adapter({('next_state','identity'):0.,('replay_action','identity'):0.})
    decision=a.align()
    assert decision['accepted'] and decision['rule']=='next_state'
    assert decision['format']=='egrs.sim.alignment.v2'
    assert decision['equivalence']['representative']=='next_state'
    assert [x['frame'] for x in decision['equivalence']['checks']]==[0,1]
    assert frame_operation(decision,0,3)=={'state_index':1,'action_index':None}
    assert frame_operation(decision,2,3,replay_corroborated=True) is None


@pytest.mark.parametrize('divergence',['state','image'])
def test_probe_equivalence_cannot_authorize_later_divergent_frame(divergence):
    a=alignment_adapter({('next_state','identity'):0.,('replay_action','identity'):0.})
    a.images={i:{} for i in range(5)}; a.episode.T=5
    if divergence=='state':
        a.env.sim.get_state=lambda:np.array([99 if a.current==2 else a.current+1])
    else:
        previous=a._compare
        a._compare=lambda frame,renders,orientation: [.5,.5] if frame==2 and a.action is not None else previous(frame,renders,orientation)
    decision=a.align()
    assert not decision['accepted']
    checks=decision['equivalence']['checks']
    assert [x['frame'] for x in checks]==[0,1,2,3]


def test_physical_equivalence_does_not_remove_orientation_ambiguity():
    a=alignment_adapter({(rule,orientation):0. for rule in ('next_state','replay_action')
                         for orientation in ('identity','flip_vertical')})
    assert not a.align()['accepted']


@pytest.mark.parametrize('failure',['timeout','hard_exit'])
def test_initial_inspection_survives_native_startup_before_constructor_returns(tmp_path,monkeypatch,failure):
    import subprocess
    import sys
    worker=importlib.import_module('egrs.offline.sim_worker')
    make_source(tmp_path)
    req=request(); req['source_root']=str(tmp_path)
    req['config']={'core':{},'bddl_root':str(tmp_path),
        'versions':{n:'synthetic' for n in ('numpy','h5py','robosuite','mujoco')},
        'module_sha256':{n:'0'*64 for n in ('libero.libero.envs.bddl_base_domain',
            'libero.libero.envs.predicates.base_predicates','robosuite.environments.robot_env')}}
    script=tmp_path/'initializing_worker.py'
    script.write_text("import os,time\nfrom egrs.offline.sim_native import NativeAdapter\n"
        "from egrs.offline.sim_worker import serve\n"
        "def initialize(self):\n    "+("time.sleep(20)" if failure=='timeout' else "os._exit(23)")+"\n"
        "NativeAdapter._initialize=initialize\nserve()\n")
    real_popen=subprocess.Popen
    monkeypatch.setattr(worker.subprocess,'Popen',lambda args,**kwargs:real_popen([sys.executable,str(script)],**kwargs))
    events=[]
    with pytest.raises(worker.WorkerFailure) as error:
        worker.run_isolated(req,python=sys.executable,timeout_seconds=1.5,on_event=events.append)
    inspection=next(e['data'] for e in events if e['type']=='inspection')
    assert inspection['source_id']=='synthetic-source' and len(inspection['xml_sha256'])==64
    assert any(e['type']=='stage' and e['data']['stage']=='native_initialize' for e in events)
    assert error.value.events==events
