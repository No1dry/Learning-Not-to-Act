"""Task023 synthetic evidence only: never constructs native runtime or reads HDF."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest
from PIL import Image

from egrs.offline.common import digest, read, seal
from egrs.offline.sim import sha256_file
from tests.test_sim_pipeline import fixture, rows

CASES = [
    ('libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5#demo_0', [0, 66, 129]),
    ('libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5#demo_0', [0, 72, 139]),
]


def sealed_input(tmp_path):
    inv, _, regs, config = fixture(tmp_path)
    root = tmp_path/'old'; root.mkdir()
    sources, requests, bindings, audits = [], [], [], []
    for n, (sid, frames) in enumerate(CASES):
        source = deepcopy(inv['sources'][0])
        source.update(source_id=sid, file=sid.split('#')[0], episode='demo_0', T=150, split='train')
        sources.append(source)
        requested = []
        for frame in frames:
            images = {}
            for camera in ('agentview', 'wrist'):
                path = tmp_path/f'{n}-{frame}-{camera}.png'
                Image.new('RGB', (2, 2), (10, 20, 30)).save(path)
                images[camera] = dict(path=str(path), width=2, height=2)
                bindings.append(dict(source_id=sid, frame=frame, camera=camera,
                                     **images[camera], sha256=sha256_file(path)))
            requested.append(dict(frame=frame, images=images))
        reg = regs['registries'][source['instruction_id']]['registry']
        request = dict(format='egrs.sim.request.v1', request_id='source-'+digest(sid), source_root=str(tmp_path),
                       source=source, registry=reg, frames=requested, config={})
        requests.append(request)
        audits.append(dict(type='worker_audit', source_id=sid, sequence=3, data=dict(
            type='alignment_measurement', probes=frames,
            producer_evidence={'image_convention':'opengl'},
            orientation_candidates={'identity':{'orientation':'identity'}, 'flip_vertical':{'orientation':'flip_vertical'}},
            image_bindings=[dict(frame=b['frame'], camera=b['camera'], path=b['path'], width=2, height=2,
                                 file_sha256=b['sha256'], pixel_sha256='b'*64, hdf_pixel_equality=True)
                            for b in bindings if b['source_id']==sid])))
    # This unrelated frozen descriptor must never be opened or rehashed.
    bindings.append(dict(source_id='unrelated', frame=0, camera='agentview', path=str(tmp_path/'absent.png'),
                         width=2, height=2, sha256='f'*64))
    inv.update(root=str(tmp_path/'source-data'),sources=sources, planned_sources=deepcopy(sources), source_splits={sid:'train' for sid,_ in CASES})
    for request in requests: request['source_root']=inv['root']
    inv = seal(inv)
    regs['inventory_id']=inv['identity']; regs=seal(regs)
    config['expected'].update(inventory=inv['identity'], registries=regs['identity'])
    from egrs.offline.sim import _backend
    native=_backend(config)[1]
    for request in requests: request['config']=deepcopy(native)
    values={'inventory.json':inv, 'registries.json':regs, 'backend-config.json':config,
            'image-bindings.json':{'format':'egrs.sim.images.v1','images':bindings}}
    for name,value in values.items(): (root/name).write_text(json.dumps(value),encoding='utf-8')
    for name,value in [('requests.jsonl',requests),('audit.jsonl',audits)]:
        (root/name).write_text(''.join(json.dumps(x)+'\n' for x in value),encoding='utf-8')
    manifest=seal(dict(format='egrs.sim.annotations.v1', inputs=config['expected'], config_identity=digest(config),
        mapping_identity=digest(__import__('egrs.offline.sim_contract',fromlist=['load_goal_map']).load_goal_map()),
        code={'format':'egrs.sim.code.v1','files':{'historical.py':'a'*64},'identity':digest({'historical.py':'a'*64})},
        source_splits=inv['source_splits'], source_results=[{'source_id':sid,'status':'complete'} for sid,_ in CASES],
        ready=False, files={name:sha256_file(root/name) for name in [*values,'requests.jsonl','audit.jsonl']}))
    (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    return root/'manifest.json'


class State:
    def __init__(self, value):
        self.time=float(value[0]); self.qpos=np.array(value[1:3]); self.qvel=np.array(value[3:6]); self.act=np.array(value[6:8])
    def flatten(self): return np.r_[self.time,self.qpos,self.qvel,self.act]
    @classmethod
    def from_flattened(cls, value, sim): return cls(value)


class FakeAdapter:
    instances=[]
    fail_render=None
    fail_restore=None
    close_error=False
    def __init__(self, request, *, emit):
        self.request=request; self.config=request['config']; self.inspection={'synthetic':True,'xml':'unchanged'}
        self.audit=[]; self.image_bindings={}; self.calls=[]; self.closed=False
        self.goals=[dict(goal_ref='g1',atom=['open','drawer'],annotation_only=True,basis=['fake'])]
        self.inner=SimpleNamespace(_eval_predicate=lambda atom: True)
        self.state=State(np.arange(8,dtype=float))
        self.env=SimpleNamespace(sim=SimpleNamespace(get_state=lambda:self.state))
        self.episode=SimpleNamespace(T=150,state=lambda f:np.arange(8,dtype=float)+f)
        type(self).instances.append(self)
        emit('stage',{'stage':'fake_initialize','phase':'begin'})
    def _restore(self,index,action=None):
        self.calls.append(('restore',index,action))
        if self.fail_restore==len([x for x in self.calls if x[0]=='restore']): raise RuntimeError('restore interrupted')
        self.state=State(np.arange(8,dtype=float)+index+(0.25 if action is not None else 0))
    def _original(self,frame,camera):
        self.calls.append(('original',frame,camera))
        self.image_bindings[f'{frame}:{camera}']={'hdf_pixel_equality':True}
        return np.full((2,2,3),10,dtype=np.uint8)
    def _render(self,camera):
        self.calls.append(('render',camera))
        if self.fail_render==len([x for x in self.calls if x[0]=='render']): raise RuntimeError('render interrupted')
        return np.full((2,2,3),20,dtype=np.uint8),np.array([[1,0],[0,0]])
    def _foreground(self,raw): return raw.astype(bool)
    def close(self):
        self.closed=True
        if self.close_error: raise RuntimeError('close interrupted')
    def align(self): pytest.fail('diagnostic called annotation align')
    def frame(self,*a): pytest.fail('diagnostic called annotation frame')
    def _prove_equivalence(self,*a): pytest.fail('diagnostic called equivalence search')


@pytest.fixture(autouse=True)
def reset_fake():
    FakeAdapter.instances=[]; FakeAdapter.fail_render=None; FakeAdapter.fail_restore=None; FakeAdapter.close_error=False


def fake_runner(request, *, on_event, **kwargs):
    assert kwargs['mode']=='alignment_diagnostic'
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    return process_diagnostic_source(request,adapter_factory=FakeAdapter,emit=on_event)


def first_request(tmp_path):
    from egrs.offline.sim_diagnostics import diagnose_alignment
    requests=[]
    def runner(request,**kwargs):
        requests.append(deepcopy(request)); return fake_runner(request,**kwargs)
    diagnose_alignment(sealed_input(tmp_path),tmp_path/'diagnostic',worker_runner=runner)
    request=requests[0]; request['output']=str(tmp_path/'separate-worker'); return request


def test_controller_consumes_only_fixed_bindings_and_preserves_historical_bytes(tmp_path, monkeypatch):
    from egrs.offline.sim_diagnostics import diagnose_alignment
    import egrs.offline.sim as sim
    manifest=sealed_input(tmp_path)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    for name in ('_inputs','label_sim','export_sim'):
        monkeypatch.setattr(sim,name,lambda *a,**kw:pytest.fail('forbidden annotation/export stage'))
    result=diagnose_alignment(manifest,tmp_path/'diagnostic',worker_runner=fake_runner)
    assert result['status']=='complete' and result['counts']['comparisons']==36
    assert result['counts']['candidate_restores']==18 and result['counts']['actions']==6
    assert result['counts']['direct_renders']==72
    assert result['historical']['manifest_identity']==read(manifest)['identity']
    assert result['historical']['code']!=result['code']
    assert result['source_splits']=={sid:'train' for sid,_ in CASES}
    assert all(Path(p).read_bytes()==value for p,value in before.items())
    assert len(rows(tmp_path/'diagnostic/png-index.jsonl'))==180
    assert not list((tmp_path/'diagnostic').rglob('*annotations*'))
    for adapter,(_,frames) in zip(FakeAdapter.instances,CASES):
        assert [x for x in adapter.calls if x[0]=='restore']==[
            x for f in frames for x in [('restore',f,None),('restore',f+1,None),('restore',f,f)]]
        assert len([x for x in adapter.calls if x[0]=='render'])==18
        assert adapter.closed


@pytest.mark.parametrize('change',['source','frame','camera','split','config','file_hash','probe','orientation','missing_next'])
def test_conflicting_consumed_binding_rejected_before_native(tmp_path,change):
    from egrs.offline.sim_diagnostics import diagnose_alignment
    path=sealed_input(tmp_path); root=path.parent
    if change in {'source','frame','camera','config','missing_next'}:
        value=rows(root/'requests.jsonl')
        if change=='source': value[0]['source']['file']='different.hdf5'
        if change=='frame': value[0]['frames'][0]['frame']=1
        if change=='camera': value[0]['frames'][0]['images']['side']=value[0]['frames'][0]['images'].pop('wrist')
        if change=='config': value[0]['config']['max_physics_substeps']+=1
        if change=='missing_next': value[0]['source']['T']=130
        name='requests.jsonl'; text=''.join(json.dumps(x)+'\n' for x in value)
    elif change in {'probe','orientation'}:
        value=rows(root/'audit.jsonl'); name='audit.jsonl'
        if change=='probe': value[0]['data']['probes']=[0,65,129]
        else: value[0]['data']['producer_evidence']['image_convention']='opencv'
        text=''.join(json.dumps(x)+'\n' for x in value)
    elif change=='split':
        value=read(path); value['source_splits'][CASES[0][0]]='dev'
        path.write_text(json.dumps(seal(value)),encoding='utf-8'); name=None
    else:
        value=read(root/'image-bindings.json'); value['images'][0]['sha256']='0'*64
        name='image-bindings.json'; text=json.dumps(value)
    if name:
        (root/name).write_text(text,encoding='utf-8')
        value=read(path); value['files'][name]=sha256_file(root/name)
        path.write_text(json.dumps(seal(value)),encoding='utf-8')
    with pytest.raises(ValueError):
        diagnose_alignment(path,tmp_path/'rejected',worker_runner=lambda *a,**kw:pytest.fail('native launched'))
    assert not (tmp_path/'rejected').exists()


def test_output_must_be_new_and_outside_historical_tree(tmp_path):
    from egrs.offline.sim_diagnostics import diagnose_alignment
    path=sealed_input(tmp_path)
    with pytest.raises(ValueError): diagnose_alignment(path,path.parent/'nested',worker_runner=fake_runner)
    with pytest.raises(ValueError): diagnose_alignment(path,tmp_path/'source-data'/'nested',worker_runner=fake_runner)
    with pytest.raises(FileExistsError): diagnose_alignment(path,tmp_path,worker_runner=fake_runner)


def test_rgb_decomposition_and_unavailable_regions_are_numeric_not_acceptance():
    from egrs.offline.sim_diagnostic_worker import measure_rgb
    original=np.zeros((2,1,3),dtype=np.uint8)
    candidate=np.array([[[3,6,9]],[[12,15,18]]],dtype=np.uint8)
    support=np.array([[True],[False]])
    got=measure_rgb(original,candidate,support,min_pixels=1)
    assert got['whole_mae']==pytest.approx(10.5/255)
    assert got['foreground_mae']==pytest.approx(6/255)
    assert got['background_mae']==pytest.approx(15/255)
    assert got['signed_bias']==pytest.approx([7.5/255,10.5/255,13.5/255])
    assert got['original_max_metric']==pytest.approx(10.5/255)
    got=measure_rgb(original,candidate,np.zeros((2,1),dtype=bool),min_pixels=1)
    assert got['foreground_mae'] is None and got['original_max_metric'] is None
    assert got['foreground_unavailable']=='insufficient_visible_foreground'
    got=measure_rgb(original,candidate,np.ones((2,1),dtype=bool),min_pixels=3)
    assert got['background_mae'] is None and got['original_max_metric'] is None


@pytest.mark.parametrize('act',['present','absent','bad_roundtrip'])
def test_state_grouping_uses_codec_and_reports_missing_fields(act):
    from egrs.offline.sim_diagnostic_worker import state_snapshot, compare_states
    class Codec(State):
        def __init__(self,value):
            super().__init__(value)
            if act=='absent': del self.act
        def flatten(self):
            value=np.r_[self.time,self.qpos,self.qvel]
            if act!='absent': value=np.r_[value,self.act]
            return value
        @classmethod
        def from_flattened(cls,value,sim):
            result=cls(value)
            if act=='bad_roundtrip': result.time+=1
            return result
    left=np.arange(8 if act!='absent' else 6,dtype=float)
    sim=SimpleNamespace(get_state=lambda:Codec(left))
    a=state_snapshot(sim,left,origin='source_next')
    b=state_snapshot(sim,left+2,origin='replay_actual')
    got=compare_states(a,b)
    assert got['full_max_abs_residual']==2
    if act=='bad_roundtrip':
        assert got['groups']['qpos']['max_abs_residual'] is None
        assert 'round-trip' in a['unavailable']
    else:
        assert got['groups']['time']['max_abs_residual']==2
        assert got['groups']['qpos']['size']==2 and got['groups']['qvel']['size']==3
        if act=='absent': assert got['groups']['act']['max_abs_residual'] is None
        else: assert got['groups']['act']['size']==2


@pytest.mark.parametrize('failure',['render','restore','close','native'])
def test_worker_failure_retains_completed_artifacts_and_unknown_native(tmp_path,failure):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path)
    if failure=='render': FakeAdapter.fail_render=2
    if failure=='restore': FakeAdapter.fail_restore=2
    if failure=='close': FakeAdapter.close_error=True
    class Adapter(FakeAdapter):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            if failure=='native': self.inner._eval_predicate=lambda atom:(_ for _ in ()).throw(RuntimeError('predicate missing'))
    events=[]; result=process_diagnostic_source(request,adapter_factory=Adapter,emit=events.append)
    assert result['measurements'] and list(Path(request['output']).rglob('*.png'))
    assert FakeAdapter.instances[-1].closed
    if failure=='native':
        assert result['status']=='complete'
        assert result['candidates'][0]['native_truths']=={'g1':None}
        assert result['candidates'][0]['native_atoms'][0]['gap']=='predicate missing'
    else: assert result['status']=='partial' and result['errors']
    assert events[-1]['type']=='result'


def test_orientation_applies_to_both_rgb_and_mask_without_search(tmp_path):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path); request['orientation']='flip_vertical'
    request['historical']['orientation']='flip_vertical'
    class Adapter(FakeAdapter):
        def _render(self,camera):
            return np.array([[[1,2,3],[4,5,6]],[[7,8,9],[10,11,12]]],dtype=np.uint8),np.array([[1,0],[0,0]])
    result=process_diagnostic_source(request,adapter_factory=Adapter)
    artifacts=result['measurements'][0]['artifacts']
    assert np.array(Image.open(artifacts['candidate']['path']))[0,0].tolist()==[7,8,9]
    assert np.array(Image.open(artifacts['foreground']['path'])).tolist()==[[0,0],[255,0]]


def test_interrupted_transport_retains_progress_and_rejects_label_events(tmp_path):
    from egrs.offline.sim_diagnostics import diagnose_alignment
    from egrs.offline.sim_worker import WorkerFailure
    path=sealed_input(tmp_path)
    def interrupted(request,*,on_event,**kw):
        def forward(event):
            on_event(event)
            if event['type']=='measurement': raise WorkerFailure('timeout',[],'fake timeout')
        return fake_runner(request,on_event=forward,**kw)
    result=diagnose_alignment(path,tmp_path/'partial',worker_runner=interrupted)
    assert result['status']=='partial' and result['counts']['comparisons']>0
    assert rows(tmp_path/'partial/png-index.jsonl')
    def bad(request,*,on_event,**kw):
        from egrs.offline.sim_diagnostic_worker import EVENT_FORMAT
        on_event(dict(format=EVENT_FORMAT,request_id=request['request_id'],source_id=request['source_request']['source']['source_id'],
                      sequence=0,type='frame',data={}))
    result=diagnose_alignment(path,tmp_path/'bad-protocol',worker_runner=bad)
    assert result['status']=='failed' and result['errors']


def test_cli_dispatches_only_explicit_alignment_diagnostic(tmp_path,monkeypatch,capsys):
    import egrs.offline.sim_diagnostics as diagnostics
    from egrs.offline.cli import main
    seen=[]
    monkeypatch.setattr(diagnostics,'diagnose_alignment',lambda manifest,output:seen.append((manifest,output)) or {'format':'diagnostic'})
    assert main(['diagnose-alignment','--manifest','old.json','--output','new'])==0
    assert seen==[('old.json','new')]
    assert json.loads(capsys.readouterr().out)=={'format':'diagnostic'}


def test_cli_partial_diagnostic_has_honest_receipt_and_exit_status(monkeypatch,capsys):
    import egrs.offline.sim_diagnostics as diagnostics
    from egrs.offline.cli import main
    monkeypatch.setattr(diagnostics,'diagnose_alignment',lambda *a:{'format':'diagnostic','status':'partial','counts':{'comparisons':1}})
    assert main(['diagnose-alignment','--manifest','old.json','--output','new'])==1
    assert json.loads(capsys.readouterr().out)['status']=='partial'


@pytest.mark.parametrize('change',['final_next','probe','orientation','config','code','png'])
def test_worker_rejects_unsafe_request_before_adapter(tmp_path,change):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path)
    if change=='final_next': request['source_request']['source']['T']=130
    if change=='probe': request['probes']=[0,65,129]
    if change=='orientation': request['orientation']='flip_vertical'
    if change=='config': request['source_request']['config']['max_physics_substeps']=1001
    if change=='code': request['code']=deepcopy(request['historical']['code'])
    if change=='png': Path(request['image_bindings'][0]['path']).write_bytes(b'changed after controller preflight')
    if change in {'final_next','config'}: request['request_id']='diagnostic-'+digest(request['source_request'])
    with pytest.raises(ValueError):
        process_diagnostic_source(request,adapter_factory=lambda *a,**kw:pytest.fail('unsafe native construction'))
    assert not Path(request['output']).exists()


def test_state_comparisons_keep_source_and_restored_origins_independent(tmp_path):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path)
    class Adapter(FakeAdapter):
        def _restore(self,index,action=None):
            super()._restore(index,action)
            if action is None: self.state=State(self.state.flatten()+5)
    result=process_diagnostic_source(request,adapter_factory=Adapter)
    comparison=result['states'][0]
    assert comparison['source_next_vs_replay']['left_origin']=='source_next'
    assert comparison['source_next_vs_replay']['full_max_abs_residual']==.75
    assert comparison['actual_next_vs_replay']['left_origin']=='next_state_actual'
    assert comparison['actual_next_vs_replay']['full_max_abs_residual']==5.75
    assert comparison['source_next_vs_replay']['left_sha256']!=comparison['actual_next_vs_replay']['left_sha256']


def test_unsupported_codec_and_native_exception_never_become_zero_or_false(tmp_path):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path)
    class NoCodec:
        def flatten(self): return np.arange(8,dtype=float)
    class Adapter(FakeAdapter):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            self.env.sim.get_state=lambda:NoCodec()
            self.inner._eval_predicate=lambda atom:(_ for _ in ()).throw(OSError('native predicate IO'))
    result=process_diagnostic_source(request,adapter_factory=Adapter)
    assert result['status']=='complete'
    assert result['candidates'][0]['native_truths']=={'g1':None}
    assert 'native predicate IO' in result['candidates'][0]['native_atoms'][0]['gap']
    assert 'unavailable' in result['candidates'][0]['state']['unavailable']
    assert result['states'][0]['source_next_vs_replay']['groups']['qpos']['max_abs_residual'] is None


def test_constructor_failure_keeps_inspection_and_partial_native_audit(tmp_path):
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path); events=[]
    def initialize(request,*,emit):
        emit('inspection',{'stage':'source_xml_assets','xml_sha256':'a'*64})
        error=RuntimeError('initialization stopped')
        error.audit=[{'type':'partial_assets','resolved':'completed before failure'}]
        raise error
    result=process_diagnostic_source(request,adapter_factory=initialize,emit=events.append)
    assert result['status']=='failed'
    assert result['inspection']['stage']=='source_xml_assets'
    assert any(e['type']=='audit' and e['data']['type']=='partial_assets' for e in events)


@pytest.mark.parametrize('mismatch',['none','hash','diagnostic_root','timeout','hard_exit'])
def test_real_diagnostic_bootstrap_locks_current_bytes_despite_old_code_and_stale_cwd(tmp_path,monkeypatch,mismatch):
    from egrs.offline.sim_worker import run_isolated,WorkerFailure
    request=first_request(tmp_path)
    hook=tmp_path/'hook'; hook.mkdir()
    marker=tmp_path/'constructed'
    # Fake only native construction; real bootstrap, worker, codec, files and protocol execute.
    (hook/'sitecustomize.py').write_text(
        'import sys,importlib.abc,importlib.util\n'
        'class NativeBoundary(importlib.abc.MetaPathFinder):\n'
        '    def find_spec(self,fullname,path=None,target=None):\n'
        '        if fullname=="egrs.offline.sim_native":\n'
        '            sys.meta_path.remove(self)\n'
        '            spec=importlib.util.find_spec(fullname)\n'
        '            original=spec.loader\n'
        '            class Loader:\n'
        '                def create_module(self,spec): return None\n'
        '                def exec_module(self,module):\n'
        '                    original.exec_module(module)\n'
        '                    from tests.test_sim_diagnostics import FakeAdapter\n'
        '                    from pathlib import Path\n'
        '                    class NativeAdapter(FakeAdapter):\n'
        '                        def __init__(self,*a,**kw):\n'
        f'                            Path({str(marker)!r}).write_text("constructed")\n'
        '                            super().__init__(*a,**kw)\n'
        '                        def _render(self,camera):\n'
        '                            value=super()._render(camera)\n'
        '                            count=len([x for x in self.calls if x[0]=="render"])\n'
        + ('                            if count==2:\n                                import time\n                                time.sleep(20)\n' if mismatch=='timeout' else
           '                            if count==2:\n                                import os\n                                os._exit(23)\n' if mismatch=='hard_exit' else '') +
        '                            return value\n'
        '                    module.NativeAdapter=NativeAdapter\n'
        '            spec.loader=Loader()\n'
        '            return spec\n'
        'sys.meta_path.insert(0,NativeBoundary())\n',encoding='utf-8')
    if mismatch=='diagnostic_root':
        with (hook/'sitecustomize.py').open('a',encoding='utf-8') as stream:
            stream.write('import types\nm=types.ModuleType("egrs.offline.sim_diagnostic_worker")\n'
                         f'm.__file__={str(hook/"foreign.py")!r}\n'
                         'sys.modules[m.__name__]=m\n')
    stale=tmp_path/'stale'; (stale/'egrs').mkdir(parents=True)
    (stale/'egrs/__init__.py').write_text('raise RuntimeError("stale package selected")',encoding='utf-8')
    monkeypatch.chdir(stale)
    events=[]
    if mismatch in {'timeout','hard_exit'}:
        with pytest.raises(WorkerFailure) as caught:
            run_isolated(request,python=sys.executable,module_paths=[hook],timeout_seconds=3,
                         mode='alignment_diagnostic',on_event=events.append)
        assert caught.value.events==events
        assert len([e for e in events if e['type']=='measurement'])==1
        assert len([e for e in events if e['type']=='artifact'])==5
        assert not any(e['type']=='result' for e in events)
        assert len(list(Path(request['output']).rglob('*.png')))==5
    elif mismatch!='none':
        expected='0'*64 if mismatch=='hash' else request['code']['identity']
        with pytest.raises(WorkerFailure) as caught:
            run_isolated(request,python=sys.executable,module_paths=[hook],timeout_seconds=10,
                         expected_code_identity=expected,mode='alignment_diagnostic',on_event=events.append)
        assert 'implementation identity mismatch' in caught.value.stderr
        assert not marker.exists()
    else:
        result=run_isolated(request,python=sys.executable,module_paths=[hook],timeout_seconds=10,
                            mode='alignment_diagnostic',on_event=events.append)
        assert result['status']=='complete' and len(result['measurements'])==18
        assert result['historical']['code']!=result['code']
        assert result['code']==request['code'] and marker.exists()
        assert events[-1]['type']=='result'


@pytest.mark.parametrize('bad',['label','foreign','duplicate','missing','extra_result','bad_count'])
def test_isolated_diagnostic_transport_cannot_accept_malformed_evidence(tmp_path,monkeypatch,bad):
    import subprocess
    from egrs.offline.sim_worker import run_isolated,WorkerFailure
    from egrs.offline.sim_diagnostic_worker import process_diagnostic_source
    request=first_request(tmp_path); events=[]
    process_diagnostic_source(request,adapter_factory=FakeAdapter,emit=events.append)
    if bad=='label': events[0]['type']='frame'
    if bad=='foreign': events[0]['source_id']='foreign'
    if bad=='duplicate': events[1]['sequence']=0
    if bad=='missing': events=[events[-1]]; events[0]['sequence']=0
    if bad=='extra_result': events[-1]['data']['answer']={'label':'forbidden'}
    if bad=='bad_count': events[-1]['data']['counts']['comparisons']=0
    event_file=tmp_path/'malformed.jsonl'; event_file.write_text(''.join(json.dumps(e)+'\n' for e in events),encoding='utf-8')
    script=tmp_path/'malformed.py'
    script.write_text('import sys\nfrom pathlib import Path\nsys.stdin.readline()\n'
                      f'sys.stdout.write(Path({str(event_file)!r}).read_text(encoding="utf-8"))\n',encoding='utf-8')
    real_popen=subprocess.Popen
    monkeypatch.setattr(subprocess,'Popen',lambda args,**kw:real_popen([sys.executable,str(script)],**kw))
    with pytest.raises(WorkerFailure):
        run_isolated(request,python=sys.executable,timeout_seconds=10,mode='alignment_diagnostic')
