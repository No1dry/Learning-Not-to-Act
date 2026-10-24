"""Synthetic immutable controller/export tests; no source HDF or native runtime."""
import copy
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from egrs.offline.common import digest, seal, read
from tests.test_data_training import example, FakeProcessor
from tests.test_sim_labels import registry, facts


def fixture(tmp_path):
    reg = registry()
    iid = digest(reg['instruction'])
    sources, windows = [], []
    for n, split in enumerate(('train', 'dev')):
        sid = f'synthetic{n}'
        source = dict(source_id=sid, sample_id=sid, file='never-open.hdf5', episode=f'demo_{n}',
                      T=2, instruction=reg['instruction'], instruction_id=iid, orientation='opengl',
                      group_ids=[f'alias{n}'], task_group='synthetic-task', ancestry_known=False, split=split)
        sources.append(source)
        samples, sensors = [], []
        for q in (1, 2):
            path = tmp_path / f'{sid}-{q}.png'
            Image.new('RGB', (5, 4), (n, q, 0)).save(path)
            sensors.append(dict(query_id=q, snapshot_id=f'q{q}', observation={
                'agentview_image': str(path), 'robot0_eye_in_hand_image': str(path)}))
            sample = example()
            sample.update(sample_id=f'{sid}/w0/q{q}', source_id=sid, window_id='w0', answer=None,
                          provenance={}, physical_truth=None, group_ids=source['group_ids'],
                          task_group=source['task_group'], ancestry_known=False, history_provenance={})
            sample['payload'] = dict(sensor=copy.deepcopy(sensors), context=dict(query_id=q,
                instruction=reg['instruction'], registry=reg, history=[], commands=[]))
            samples.append(sample)
        windows.append(dict(source_id=sid, window_id='w0', split=split, frames=[0, 1],
                            orientation='opengl', cameras=['agentview', 'wrist'], samples=samples))
    splits = {s['source_id']: s['split'] for s in sources}
    inv = seal(dict(format='egrs.inventory.v1', dataset='synthetic/task019', revision='synthetic-v1',
        root=str(tmp_path), sources=sources, planned_sources=copy.deepcopy(sources), source_splits=splits, gaps=[], seed=0))
    regs = seal(dict(format='egrs.registries.confirmed.v1', inventory_id=inv['identity'], registries={
        iid: dict(registry=reg, confirmed=True, reviewer='SYNTHETIC')}))
    wins = seal(dict(format='egrs.windows.v1', inventory_id=inv['identity'], source_splits=splits,
        planned_sources=copy.deepcopy(sources), gaps=[], windows=windows))
    config = dict(format='egrs.sim.backend.v1', identity_scope='synthetic', synthetic_basis='generated PNG fixtures only',
        expected=dict(dataset=inv['dataset'], revision=inv['revision'], inventory=inv['identity'],
                      windows=wins['identity'], registries=regs['identity']),
        worker=dict(python=sys.executable, module_paths=[], timeout_seconds=2),
        native=dict(core=dict(root=str(tmp_path), revision='synthetic'), bddl_root=str(tmp_path),
            versions={k:'synthetic' for k in ('numpy','h5py','robosuite','mujoco')},
            module_sha256={k:'a'*64 for k in ('libero.libero.envs.bddl_base_domain',
                'libero.libero.envs.predicates.base_predicates','robosuite.environments.robot_env')}))
    return inv, wins, regs, config


class Adapter:
    def __init__(self, request, *, emit):
        self.request = request
        self.inspection = {'synthetic': True, 'xml_sha256': 'a'*64,
            'bddl_provenance':{'mode':'metadata_resolved_installed_bddl','source_identifiers':'metadata-audit-secret'}}
        self.audit = [{'native_name': 'annotation-side-secret'}]
        emit('stage', {'stage': 'native_initialize', 'phase': 'begin'})
        emit('inspection', self.inspection)
    def align(self): return facts()['alignment']
    def frame(self, frame, alignment):
        value = facts(); value.update(source_id=self.request['source']['source_id'], frame=frame)
        if frame == 1:
            for goal in value['goals']: goal['evidence'] = []
        return value, {'native_truth': 'offline-secret', 'frame': frame}
    def close(self): pass


def worker(request, *, on_event, **kwargs):
    from egrs.offline.sim_worker import process_source
    return process_source(request, adapter_factory=Adapter, emit=on_event)


ATTEST = dict(six_composites_excluded=True, semantic_equivalents_excluded=True,
              eval_sources_excluded=True, basis='SYNTHETIC fixture exclusion')


def rows(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]


def test_mixed_run_preserves_originals_fixed_split_and_exports_real_tokens(tmp_path):
    from egrs.offline.sim import label_sim, export_sim
    inv, wins, regs, config = fixture(tmp_path)
    original = copy.deepcopy(wins)
    output = tmp_path/'labels'
    manifest = label_sim(inv, wins, regs, config, output, worker_runner=worker)
    assert wins == original
    annotated = rows(output/'annotations.jsonl')
    expected = [s for w in wins['windows'] for s in w['samples']]
    assert [r['sample_id'] for r in annotated] == [r['sample_id'] for r in expected]
    for actual, before in zip(annotated, expected):
        assert {k:v for k,v in actual.items() if k not in {'answer','provenance'}} == {
            k:v for k,v in before.items() if k not in {'answer','provenance'}}
    assert manifest['coverage']['total']['planned'] == 4
    assert manifest['coverage']['total']['processed'] == 4
    assert manifest['coverage']['total']['supervised'] == 2
    assert manifest['coverage']['total']['gap'] == 4  # release/interaction gaps retained even with relation
    assert manifest['ready'] is False
    assert manifest['source_splits'] == inv['source_splits']
    report = export_sim(output/'manifest.json', wins, ATTEST, tmp_path/'export')
    assert report['ready'] is False and report['usable'] is True
    assert report['splits'] == {'train':1, 'dev':1}
    train, dev = rows(tmp_path/'export/train.jsonl'), rows(tmp_path/'export/dev.jsonl')
    assert train[0]['source_id'] == 'synthetic0' and dev[0]['source_id'] == 'synthetic1'
    assert 'metadata-audit-secret' in (output/'audit.jsonl').read_text()
    assert 'metadata-audit-secret' not in json.dumps(annotated)
    text = json.dumps(train + dev)
    assert all(x not in text for x in ('native_truth', 'offline-secret', 'annotation-side-secret', 'alignment', 'physical_truth', 'metadata-audit-secret', 'bddl_provenance'))
    from egrs.selector.encoding import encode_sample
    encoded = encode_sample(train[0], FakeProcessor(), max_length=30000)
    learned = ''.join(chr(x-1) for x in encoded['labels'][0].tolist() if x != -100)
    assert 'SAT' in learned and 'UNSAT' in learned and 'UNKNOWN' not in learned
    prompt = ''.join(chr(x-1) for x in encoded['input_ids'][0].tolist()).split('assistant:')[0]
    assert 'sim_supervised' not in prompt and 'native_truth' not in prompt
    with pytest.raises(FileExistsError): export_sim(output/'manifest.json',wins,ATTEST,tmp_path/'export')


@pytest.mark.parametrize('change', ['identity','registry','split','group','source','frame','snapshot','image'])
def test_validation_precedes_worker_launch(tmp_path, change):
    from egrs.offline.sim import label_sim
    inv, wins, regs, config = fixture(tmp_path)
    if change == 'identity': config['expected']['windows'] = '0'*64
    if change == 'registry': regs['registries'][inv['sources'][0]['instruction_id']]['registry']['goals'][0]['target'] = 'bowl'
    if change == 'split': wins['windows'][0]['split'] = 'dev'
    if change == 'group': wins['windows'][0]['samples'][0]['group_ids'] = ['other']
    if change == 'source': wins['windows'][0]['samples'][0]['source_id'] = 'other'
    if change == 'frame': wins['windows'][0]['frames'] = [0, 2]
    if change == 'snapshot': wins['windows'][0]['samples'][1]['payload']['sensor'][0]['query_id'] = 2
    if change == 'image': wins['windows'][0]['samples'][1]['payload']['sensor'][0]['observation']['agentview_image'] = 'wrong.png'
    inv, wins, regs = seal(inv), seal(wins), seal(regs)
    config['expected'].update(inventory=inv['identity'], registries=regs['identity'])
    if change != 'identity': config['expected']['windows'] = wins['identity']
    def forbidden(*a, **kw): pytest.fail('worker launched before validation')
    with pytest.raises(ValueError): label_sim(inv,wins,regs,config,tmp_path/'bad',worker_runner=forbidden)
    assert not (tmp_path/'bad').exists()


def test_failure_retains_initialization_and_completed_frame_before_gap(tmp_path):
    from egrs.offline.sim import label_sim
    from egrs.offline.sim_worker import WorkerFailure
    inv,wins,regs,config = fixture(tmp_path)
    def crash(request, *, on_event, **kw):
        events=[]
        from egrs.offline.sim_worker import process_source
        process_source(request,adapter_factory=Adapter,emit=events.append)
        delivered=[]
        for event in events:
            if event['type'] == 'progress':
                assert (tmp_path/'failed/annotations.partial.jsonl').stat().st_size > 0
                assert read(tmp_path/'failed/progress.json')['coverage']['total']['supervised'] > 0
                raise WorkerFailure('synthetic timeout',delivered,'retained diagnostic')
            delivered.append(event); on_event(event)
    manifest = label_sim(inv,wins,regs,config,tmp_path/'failed',worker_runner=crash)
    assert manifest['coverage']['total']['processed'] == 2
    assert manifest['coverage']['total']['supervised'] == 2
    journal = rows(tmp_path/'failed/events.jsonl')
    assert any(e.get('type')=='stage' for e in journal)
    assert any(e.get('type')=='inspection' for e in journal)
    assert 'retained diagnostic' in (tmp_path/'failed/audit.jsonl').read_text()
    assert len(rows(tmp_path/'failed/annotations.jsonl')) == 4


@pytest.mark.parametrize('bad', ['duplicate','unsolicited','misbound'])
def test_invalid_facts_are_rejected_and_journaled(tmp_path,bad):
    from egrs.offline.sim import label_sim
    inv,wins,regs,config = fixture(tmp_path)
    def invalid(request, *, on_event, **kw):
        value=facts(); value.update(source_id=request['source']['source_id'],frame=0)
        if bad=='unsolicited': value['frame']=19
        if bad=='misbound': value['source_id']='wrong'
        for i in range(2 if bad=='duplicate' else 1):
            on_event(dict(format='egrs.sim.event.v1',request_id=request['request_id'],source_id=request['source']['source_id'],
                          sequence=i,type='frame',data=value))
    with pytest.raises(ValueError): label_sim(inv,wins,regs,config,tmp_path/'invalid',worker_runner=invalid)
    assert (tmp_path/'invalid/events.jsonl').stat().st_size > 0
    assert (tmp_path/'invalid/audit.jsonl').stat().st_size > 0


def test_all_unknown_refuses_export_and_existing_outputs_refused(tmp_path):
    from egrs.offline.sim import label_sim,export_sim
    inv,wins,regs,config = fixture(tmp_path)
    def empty(request, **kwargs):
        from egrs.offline.sim_worker import WorkerFailure
        raise WorkerFailure('no evidence', [], '')
    manifest=label_sim(inv,wins,regs,config,tmp_path/'empty',worker_runner=empty)
    assert manifest['coverage']['total']['supervised']==0 and not manifest['ready']
    with pytest.raises(ValueError,match='supervis'): export_sim(tmp_path/'empty/manifest.json',wins,ATTEST,tmp_path/'no-export')
    assert not (tmp_path/'no-export').exists()
    with pytest.raises(FileExistsError): label_sim(inv,wins,regs,config,tmp_path/'empty',worker_runner=empty)


@pytest.mark.parametrize('tamper', ['bytes','payload','ancestry','splits','attestation','windows'])
def test_export_verifies_artifacts_bindings_and_attestation(tmp_path,tamper):
    from egrs.offline.sim import label_sim,export_sim,sha256_file
    inv,wins,regs,config=fixture(tmp_path)
    output=tmp_path/'labels'; label_sim(inv,wins,regs,config,output,worker_runner=worker)
    if tamper=='bytes': (output/'audit.jsonl').write_text('changed')
    if tamper in {'payload','ancestry'}:
        items=rows(output/'annotations.jsonl')
        if tamper=='payload': items[0]['payload']['context']['history']=[{'oracle':'secret'}]
        else: items[0]['ancestry_known']=True
        (output/'annotations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in items),encoding='utf-8')
        m=read(output/'manifest.json'); m['files']['annotations.jsonl']=sha256_file(output/'annotations.jsonl')
        (output/'manifest.json').write_text(json.dumps(seal(m)),encoding='utf-8')
    if tamper=='splits':
        m=read(output/'manifest.json'); m['source_splits']['synthetic0']='dev'
        (output/'manifest.json').write_text(json.dumps(seal(m)),encoding='utf-8')
    if tamper=='attestation': ATTEST_LOCAL=dict(ATTEST,eval_sources_excluded=False)
    else: ATTEST_LOCAL=ATTEST
    if tamper=='windows': wins=seal(dict(wins,gaps=[{'reason':'changed'}]))
    with pytest.raises(ValueError): export_sim(output/'manifest.json',wins,ATTEST_LOCAL,tmp_path/'export')
    assert not (tmp_path/'export').exists()


def test_cli_exposes_independent_stages_without_native_imports():
    import subprocess
    code="from egrs.offline.cli import main; main(['label-sim','--help'])"
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert result.returncode==0 and '--backend-config' in result.stdout
    result=subprocess.run([sys.executable,'-m','egrs.offline','export-sim','--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--attestation' in result.stdout


def test_export_rejects_changed_original_png_bytes(tmp_path):
    from egrs.offline.sim import label_sim,export_sim
    inv,wins,regs,config=fixture(tmp_path)
    label_sim(inv,wins,regs,config,tmp_path/'labels',worker_runner=worker)
    Image.new('RGB',(5,4),'red').save(tmp_path/'synthetic0-1.png')
    with pytest.raises(ValueError,match='image'):
        export_sim(tmp_path/'labels/manifest.json',wins,ATTEST,tmp_path/'export')
    assert not (tmp_path/'export').exists()


def test_stage_only_crash_is_sealed_as_failed_with_audit(tmp_path):
    from egrs.offline.sim import label_sim
    from egrs.offline.sim_worker import WorkerFailure
    inv,wins,regs,config=fixture(tmp_path)
    def startup_crash(request, *, on_event, **kw):
        event=dict(format='egrs.sim.event.v1',request_id=request['request_id'],source_id=request['source']['source_id'],
                   sequence=0,type='stage',data=dict(stage='native_construction',phase='begin'))
        on_event(event)
        assert 'native_construction' in (tmp_path/'startup/events.jsonl').read_text()
        raise WorkerFailure('hard exit 23',[event],'native startup')
    m=label_sim(inv,wins,regs,config,tmp_path/'startup',worker_runner=startup_crash)
    assert all(s['status']=='failed' for s in m['source_results'])
    assert m['coverage']['total']['processed']==0 and not m['usable']


def test_all_processed_identity_and_boxes_only_are_not_usable(tmp_path):
    from egrs.offline.sim import label_sim,export_sim
    from egrs.offline.sim_worker import process_source
    inv,wins,regs,config=fixture(tmp_path)
    class IdentityOnly(Adapter):
        def frame(self,frame,alignment):
            f,a=super().frame(frame,alignment)
            for g in f['goals']:
                for e in g['evidence']: e['supports']=['entity','role']
            return f,a
    def identity_worker(request, *, on_event, **kw):
        return process_source(request,adapter_factory=IdentityOnly,emit=on_event)
    m=label_sim(inv,wins,regs,config,tmp_path/'identity',worker_runner=identity_worker)
    assert m['coverage']['total']['processed_percent']==100
    assert m['coverage']['total']['supervised']==0 and not m['usable']
    with pytest.raises(ValueError,match='supervision'):
        export_sim(tmp_path/'identity/manifest.json',wins,ATTEST,tmp_path/'export')


def test_actual_cli_dispatch_uses_explicit_worker_and_separate_export(tmp_path,monkeypatch,capsys):
    from egrs.offline.cli import main
    import egrs.offline.sim as sim
    inv,wins,regs,config=fixture(tmp_path)
    called=[]
    def boundary(request, **kw):
        assert kw['python']==sys.executable and kw['module_paths']==[] and kw['timeout_seconds']==2
        assert kw['expected_code_identity']==sim.code_identity()['identity']
        assert [x['frame'] for x in request['frames']]==[0,1]
        assert all(set(f['images'])=={'agentview','wrist'} for f in request['frames'])
        assert all((im['width'],im['height'])==(5,4) for f in request['frames'] for im in f['images'].values())
        called.append(request['source']['source_id'])
        return worker(request,**kw)
    monkeypatch.setattr(sim,'run_isolated',boundary)
    for name,value in [('inv',inv),('wins',wins),('regs',regs),('config',config),('attest',ATTEST)]:
        (tmp_path/f'{name}.json').write_text(json.dumps(value),encoding='utf-8')
    assert main(['label-sim','--inventory',str(tmp_path/'inv.json'),'--windows',str(tmp_path/'wins.json'),
        '--registries',str(tmp_path/'regs.json'),'--backend-config',str(tmp_path/'config.json'),
        '--output',str(tmp_path/'labels')])==0
    assert called==['synthetic0','synthetic1']
    assert not (tmp_path/'labels/train.jsonl').exists()
    assert main(['export-sim','--annotations',str(tmp_path/'labels/manifest.json'),
        '--windows',str(tmp_path/'wins.json'),'--attestation',str(tmp_path/'attest.json'),
        '--output',str(tmp_path/'export')])==0
    assert rows(tmp_path/'export/train.jsonl')[0]['source_id']=='synthetic0'
    assert called==['synthetic0','synthetic1']


def test_code_change_during_label_cannot_seal_different_implementation(tmp_path,monkeypatch):
    import egrs.offline.sim as sim
    inv,wins,regs,config=fixture(tmp_path)
    original=sim.code_identity()
    identities=iter([original,{**original,'identity':'0'*64}])
    monkeypatch.setattr(sim,'code_identity',lambda:next(identities))
    with pytest.raises(ValueError,match='implementation identity changed'):
        sim.label_sim(inv,wins,regs,config,tmp_path/'changed-code',worker_runner=worker)
    assert not (tmp_path/'changed-code/manifest.json').exists()


def test_existing_model_history_is_preserved_and_oracle_history_rejected(tmp_path):
    from egrs.offline.sim import label_sim
    inv,wins,regs,config=fixture(tmp_path)
    sample=wins['windows'][0]['samples'][1]
    sample['payload']['context']['history']=[dict(query_id=1,goals=[dict(goal_ref=g['goal_ref'],entity_ref=None,
        relation='UNKNOWN',interaction='UNKNOWN',release='NOT_APPLICABLE' if g['kind']=='mechanism' else 'UNKNOWN',
        complete=False,carrying=False,evidence_queries=[]) for g in registry()['goals']])]
    sample['history_provenance']={'1':'model_prediction'}
    wins=seal(wins); config['expected']['windows']=wins['identity']
    m=label_sim(inv,wins,regs,config,tmp_path/'history',worker_runner=worker)
    assert m['coverage']['total']['history_available']==1
    assert rows(tmp_path/'history/annotations.jsonl')[1]['payload']==sample['payload']
    sample['history_provenance']={'1':'sim_supervised'}
    wins=seal(wins); config['expected']['windows']=wins['identity']
    with pytest.raises(ValueError,match='history provenance'):
        label_sim(inv,wins,regs,config,tmp_path/'oracle',worker_runner=worker)


def test_source_split_table_cannot_contain_unplanned_source(tmp_path):
    from egrs.offline.sim import label_sim
    inv,wins,regs,config=fixture(tmp_path)
    inv['source_splits']['unplanned']='train'
    inv=seal(inv)
    wins.update(inventory_id=inv['identity'],source_splits=copy.deepcopy(inv['source_splits']))
    wins=seal(wins); regs=seal(dict(regs,inventory_id=inv['identity']))
    config['expected'].update(inventory=inv['identity'],windows=wins['identity'],registries=regs['identity'])
    with pytest.raises(ValueError,match='planned'):
        label_sim(inv,wins,regs,config,tmp_path/'unplanned',worker_runner=worker)


def test_result_stream_disagreement_is_not_sealed(tmp_path):
    from egrs.offline.sim import label_sim
    inv,wins,regs,config=fixture(tmp_path)
    def bad_result(request, **kw):
        result=worker(request,**kw)
        result['frames']=[]
        return result
    with pytest.raises(ValueError,match='streamed'):
        label_sim(inv,wins,regs,config,tmp_path/'disagreement',worker_runner=bad_result)
    assert not (tmp_path/'disagreement/manifest.json').exists()
    assert 'controller_failure' in (tmp_path/'disagreement/audit.jsonl').read_text()


@pytest.mark.parametrize('unavailable', ['python','module_paths','both'])
def test_export_works_after_worker_only_runtime_paths_are_unavailable(tmp_path,unavailable):
    from egrs.offline.sim import label_sim,export_sim
    inv,wins,regs,config=fixture(tmp_path)
    runtime=tmp_path/'synthetic-worker-runtime'
    runtime.mkdir()
    interpreter=runtime/'fake-worker-python.exe'
    interpreter.write_text('synthetic fake-runner path, never executed',encoding='utf-8')
    modules=runtime/'imports'
    modules.mkdir()
    config['worker'].update(python=str(interpreter) if unavailable!='module_paths' else sys.executable,
                            module_paths=[str(modules)] if unavailable!='python' else [])
    label_sim(inv,wins,regs,config,tmp_path/'labels',worker_runner=worker)
    # Retire only this fixture-owned directory; no system interpreter/library is touched.
    runtime.rename(tmp_path/'retired-synthetic-worker-runtime')
    assert not interpreter.exists() and not modules.exists()
    report=export_sim(tmp_path/'labels/manifest.json',wins,ATTEST,tmp_path/'export')
    assert report['usable'] and report['splits']=={'train':1,'dev':1}
    assert rows(tmp_path/'export/train.jsonl')[0]['payload']==wins['windows'][0]['samples'][0]['payload']
    with pytest.raises(ValueError,match='module' if unavailable=='module_paths' else 'interpreter'):
        label_sim(inv,wins,regs,config,tmp_path/'unavailable-label',worker_runner=worker)
    assert not (tmp_path/'unavailable-label').exists()


@pytest.mark.parametrize('extra', [{}, {'basis':''}, {'basis':'original basis','evidence':{'files':['original-note']}}])
def test_export_accepts_original_boolean_attestation_and_retains_optional_evidence(tmp_path,extra):
    from egrs.offline.sim import label_sim,export_sim
    inv,wins,regs,config=fixture(tmp_path)
    label_sim(inv,wins,regs,config,tmp_path/'labels',worker_runner=worker)
    attestation=dict(six_composites_excluded=True,semantic_equivalents_excluded=True,eval_sources_excluded=True,**extra)
    before=copy.deepcopy(attestation)
    report=export_sim(tmp_path/'labels/manifest.json',wins,attestation,tmp_path/'export')
    assert report['usable'] and report['exclusion_attestation']==before
    assert read(tmp_path/'export/export-manifest.json')['attestation']==before
    assert attestation==before
