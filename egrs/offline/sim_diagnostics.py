"""Explicit task023 controller consuming sealed historical annotation evidence.

Only the selected PNGs are opened. Historical code identity is evidence, while
the current source identity locks the independently launched diagnostic worker.
"""
from copy import deepcopy
import json
from pathlib import Path

from egrs.data import write_json
from .common import digest, new_output, read, seal, verify
from .sim import _backend, _jsonl, sha256_file
from .sim_contract import load_goal_map, mapping_for
from .sim_identity import code_identity
from .sim_worker import WorkerFailure, run_isolated, validate_request
from .sim_diagnostic_worker import (BUDGET, CAMERAS, CASES, REQUEST_FORMAT, DiagnosticTrace,
                                    validate_diagnostic_request)

HISTORICAL_MANIFEST = '318c572532ac3f489d6da59e51039466579664501c69bed1fa113be3345549b4'
HISTORICAL_CODE = 'b63e47c9c690937b528f5c03616db51b1f44b78971dd284f5d013241634d5a06'
REFERENCE_REVISION = 'c6dc98de0c54517c976057598b60f4cedf7fa3e5'
PLANNED_IDENTITY = ('sample_id','source_id','file','episode','group_ids','task_group','ancestry_known')
CONSUMED = ('inventory.json','registries.json','backend-config.json','requests.jsonl',
            'image-bindings.json','audit.jsonl')


def _historical_inputs(path, output):
    path=Path(path).resolve(strict=True); root=path.parent
    output=Path(output).resolve()
    if output.is_relative_to(root): raise ValueError('diagnostic output must be outside historical input tree')
    if output.exists(): raise FileExistsError(output)
    manifest=verify(read(path),'egrs.sim.annotations.v1')
    for name in CONSUMED:
        if manifest.get('files',{}).get(name)!=sha256_file(root/name):
            raise ValueError('consumed historical artifact hash differs: '+name)
    inventory=verify(read(root/'inventory.json'),'egrs.inventory.v1')
    if output.is_relative_to(Path(inventory['root']).resolve()):
        raise ValueError('diagnostic output must be outside original source tree')
    registries=verify(read(root/'registries.json'),'egrs.registries.confirmed.v1')
    config=read(root/'backend-config.json'); worker,native=_backend(config)
    actual=dict(dataset=inventory['dataset'],revision=inventory['revision'],inventory=inventory['identity'],
                windows=config['expected']['windows'],registries=registries['identity'])
    if (actual!=config['expected'] or manifest.get('inputs')!=actual or manifest.get('config_identity')!=digest(config)
            or registries['inventory_id']!=inventory['identity'] or manifest.get('source_splits')!=inventory['source_splits']
            or manifest.get('mapping_identity')!=digest(load_goal_map())):
        raise ValueError('historical inventory/registry/config/split/mapping binding differs')
    if config['identity_scope']=='production':
        if manifest['identity']!=HISTORICAL_MANIFEST or manifest.get('code',{}).get('identity')!=HISTORICAL_CODE:
            raise ValueError('production input differs from task023 historical evidence')
        if native['core']['revision']!=REFERENCE_REVISION or native['core'].get('allow_reference') is not True:
            raise ValueError('task023 requires unchanged fixed complete c6 reference core')
    images=read(root/'image-bindings.json')
    if images.get('format')!='egrs.sim.images.v1': raise ValueError('invalid historical image bindings')
    requests=_jsonl(root/'requests.jsonl'); audits=_jsonl(root/'audit.jsonl')
    selected=[]
    for sid,probes in CASES.items():
        sources=[s for s in inventory['sources'] if s.get('source_id')==sid]
        planned=[s for s in inventory['planned_sources'] if s.get('source_id')==sid]
        matches=[r for r in requests if r['source']['source_id']==sid]
        results=[r for r in manifest.get('source_results',[]) if r['source_id']==sid]
        if (len(sources)!=1 or len(planned)!=1
                or any(k not in sources[0] or k not in planned[0] or sources[0][k]!=planned[0][k] for k in PLANNED_IDENTITY)
                or len(matches)!=1 or len(results)!=1
                or results[0].get('status')!='complete' or inventory['source_splits'].get(sid)!='train'
                or sources[0].get('split')!='train'):
            raise ValueError('fixed completed original train source required')
        source=sources[0]; request=validate_request(matches[0])
        entry=registries['registries'].get(source['instruction_id'],{})
        if (entry.get('confirmed') is not True or not entry.get('reviewer') or digest(source['instruction'])!=source['instruction_id']
                or request['source']!=source or request['registry']!=entry.get('registry') or request['config']!=native
                or request['source_root']!=str(Path(inventory['root']).resolve())
                or request.get('dataset_identity',dict(dataset=inventory['dataset'],revision=inventory['revision']))
                    !=dict(dataset=inventory['dataset'],revision=inventory['revision'])):
            raise ValueError('original source/request/registry/config binding differs')
        mapping_for(request['registry'])
        measurements=[a['data'] for a in audits if a.get('type')=='worker_audit' and a.get('source_id')==sid
                      and a.get('data',{}).get('type')=='alignment_measurement']
        if len(measurements)!=1: raise ValueError('unique historical alignment measurement required')
        measurement=measurements[0]
        # Task023 evidence measured these fixed cases in identity orientation.
        orientation='identity'
        if (measurement.get('probes')!=probes
                or measurement.get('producer_evidence',{}).get('image_convention')!=source['orientation']
                or measurement.get('orientation_candidates',{}).get(orientation,{}).get('orientation')!=orientation):
            raise ValueError('fixed old probes/measured orientation binding differs')
        selected_images=[]
        frames={item['frame']:item['images'] for item in request['frames']}
        from PIL import Image
        for frame in probes:
            if frame not in frames or frame+1>=source['T']: raise ValueError('original requested next-state probe required')
            for camera in CAMERAS:
                bindings=[b for b in images['images'] if b.get('source_id')==sid and b.get('frame')==frame and b.get('camera')==camera]
                old=[b for b in measurement.get('image_bindings',[]) if b.get('frame')==frame and b.get('camera')==camera]
                if len(bindings)!=1 or len(old)!=1: raise ValueError('unique selected PNG/audit binding required')
                b=bindings[0]; historic=old[0]; descriptor=frames[frame][camera]
                if (any(b.get(k)!=descriptor[k] or historic.get(k)!=descriptor[k] for k in ('path','width','height'))
                        or historic.get('file_sha256')!=b.get('sha256') or historic.get('hdf_pixel_equality') is not True
                        or sha256_file(descriptor['path'])!=b['sha256']):
                    raise ValueError('selected PNG/source/frame/camera/hash binding differs')
                with Image.open(descriptor['path']) as image:
                    if image.format!='PNG' or image.mode!='RGB' or image.size!=(descriptor['width'],descriptor['height']):
                        raise ValueError('selected original RGB PNG descriptor differs')
                selected_images.append(deepcopy(b))
        selected.append(dict(source_request=request,probes=probes,orientation=orientation,image_bindings=selected_images,
            historical=dict(manifest_identity=manifest['identity'],code=manifest['code'],orientation=orientation,
                            source_orientation=source['orientation'],alignment_measurement=deepcopy(measurement))))
    return manifest,worker,config,selected


def diagnose_alignment(manifest_path, output, *, worker_runner=None):
    manifest,worker,config,selected=_historical_inputs(manifest_path,output)
    implementation=code_identity(); output=new_output(output)
    runner=worker_runner or run_isolated
    summary=dict(format='egrs.sim.alignment-diagnostics.v1',status='failed',
                 historical=dict(manifest_identity=manifest['identity'],code=deepcopy(manifest['code'])),
                 code=implementation,identity_scope=config['identity_scope'],
                 synthetic_basis=config.get('synthetic_basis'),source_splits=deepcopy(manifest['source_splits']),
                 budget=BUDGET,counts={k:0 for k in BUDGET},source_results=[],errors=[])
    write_json(output/'config.json',dict(backend=config,cases=CASES,rules=['same_state','next_state','replay_action'],
        cameras=list(CAMERAS),budget=BUDGET,internal_renders='unchanged initialization/restore/refresh; bounded by source timeout and reset/substeps',
        historical=summary['historical'],code=implementation,
        consumed_files={k:manifest['files'][k] for k in CONSUMED}))
    streams={name:(output/name).open('x',encoding='utf-8') for name in
             ('requests.jsonl','events.jsonl','measurements.jsonl','states.jsonl','png-index.jsonl','errors.jsonl')}
    def append(name,value):
        streams[name].write(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n'); streams[name].flush()
    def progress():
        write_json(output/'progress.json',dict(status='running',counts=summary['counts'],budget=BUDGET,
            comparison_percent=100*summary['counts']['comparisons']/36,completed_sources=len(summary['source_results'])))
    progress()
    try:
        for index,case in enumerate(selected):
            request=dict(format=REQUEST_FORMAT,request_id='diagnostic-'+digest(case['source_request']),
                         **deepcopy(case),code=implementation,output=str(output/f'source-{index}'))
            validate_diagnostic_request(request); append('requests.jsonl',request)
            trace=DiagnosticTrace(request); before=deepcopy(summary['counts']); sid=request['source_request']['source']['source_id']
            protocol_errors=[]
            def on_event(event):
                append('events.jsonl',event)
                try:
                    trace.accept(event)
                    kind=event['type']; data=event['data']
                    if kind=='artifact':
                        if sha256_file(data['path'])!=data['sha256']: raise ValueError('diagnostic PNG hash differs')
                        append('png-index.jsonl',dict(source_id=sid,**data))
                    if kind=='measurement': append('measurements.jsonl',dict(source_id=sid,**data))
                    if kind=='state_comparison': append('states.jsonl',dict(source_id=sid,**data))
                    if kind=='error': append('errors.jsonl',dict(source_id=sid,**data))
                    summary['counts']={k:before[k]+trace.counts[k] for k in BUDGET}; progress()
                except Exception as error:
                    protocol_errors.append(str(error)); raise
            try:
                result=runner(deepcopy(request),**worker,on_event=on_event,
                              expected_code_identity=implementation['identity'],mode='alignment_diagnostic')
                if trace.result is None or result!=trace.result or protocol_errors:
                    raise ValueError('diagnostic result differs from streamed result')
                status=result['status']; errors=result['errors']
            except Exception as error:
                failure=dict(source_id=sid,error_type=type(error).__name__,reason=str(error)[:2000],
                             stderr=error.stderr if isinstance(error,WorkerFailure) else None,protocol_errors=protocol_errors)
                append('errors.jsonl',failure); summary['errors'].append(failure)
                status='partial' if trace.candidates or trace.artifacts else 'failed'; errors=[failure]
            summary['source_results'].append(dict(source_id=sid,status=status,counts=deepcopy(trace.counts),errors=errors))
            summary['counts']={k:before[k]+trace.counts[k] for k in BUDGET}; progress()
    finally:
        for stream in streams.values(): stream.close()
    complete=all(r['status']=='complete' for r in summary['source_results']) and len(summary['source_results'])==2
    if code_identity()!=implementation:
        summary['errors'].append(dict(reason='diagnostic implementation changed during run')); complete=False
    summary['status']='complete' if complete else 'partial' if summary['counts']['comparisons'] else 'failed'
    write_json(output/'progress.json',dict(status=summary['status'],counts=summary['counts'],budget=BUDGET,
        comparison_percent=100*summary['counts']['comparisons']/36,completed_sources=len(summary['source_results'])))
    summary['files']={p.relative_to(output).as_posix():sha256_file(p) for p in sorted(output.rglob('*')) if p.is_file()}
    summary=seal(summary); write_json(output/'manifest.json',summary)
    return summary
