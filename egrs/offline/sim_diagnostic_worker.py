"""Fixed task023 operational evidence; never returns labels or chooses alignment."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from .common import digest
from .sim_identity import code_identity
from .sim_worker import validate_request

REQUEST_FORMAT = 'egrs.sim.alignment-diagnostic.request.v1'
RESPONSE_FORMAT = 'egrs.sim.alignment-diagnostic.response.v1'
EVENT_FORMAT = 'egrs.sim.alignment-diagnostic.event.v1'
CASES = {
    'libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5#demo_0': [0, 66, 129],
    'libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5#demo_0': [0, 72, 139],
}
RULES = ('same_state', 'next_state', 'replay_action')
CAMERAS = ('agentview', 'wrist')
BUDGET = dict(candidate_restores=18, actions=6, comparisons=36, direct_renders=72)


def validate_diagnostic_request(request):
    json.dumps(request, allow_nan=False)
    keys = {'format', 'request_id', 'source_request', 'probes', 'orientation', 'image_bindings',
            'historical', 'code', 'output'}
    if not isinstance(request, dict) or set(request) != keys or request['format'] != REQUEST_FORMAT:
        raise ValueError('invalid alignment diagnostic request')
    source_request = validate_request(request['source_request'])
    from .sim_native import validate_config
    validate_config(source_request['config'])
    if request['code'] != code_identity():
        raise ValueError('diagnostic implementation identity differs from current worker bytes')
    source = source_request['source']; sid = source['source_id']
    if (sid not in CASES or request['probes'] != CASES[sid] or source.get('split') != 'train'
            or source['file'] + '#' + source['episode'] != sid
            or any(f + 1 >= source['T'] for f in request['probes'])):
        raise ValueError('diagnostic requires fixed original train source/probes with next state')
    if (request['orientation'] not in {'identity', 'flip_vertical'}
            or request['historical'].get('orientation') != request['orientation']
            or request['historical'].get('source_orientation') != source['orientation']
            or request['request_id'] != 'diagnostic-' + digest(source_request)):
        raise ValueError('diagnostic original orientation/request binding differs')
    frames = {x['frame']: x['images'] for x in source_request['frames']}
    selected = []
    for frame in request['probes']:
        if frame not in frames: raise ValueError('diagnostic probe was not originally requested')
        for camera in CAMERAS:
            matches = [b for b in request['image_bindings'] if b.get('frame') == frame and b.get('camera') == camera]
            if len(matches) != 1: raise ValueError('missing/duplicate diagnostic image binding')
            b = matches[0]
            if (b.get('source_id') != sid or {k:b.get(k) for k in ('path','width','height')} != frames[frame][camera]
                    or not isinstance(b.get('sha256'), str) or len(b['sha256']) != 64):
                raise ValueError('diagnostic image descriptor binding differs')
            selected.append(b)
            if hashlib.sha256(Path(b['path']).read_bytes()).hexdigest()!=b['sha256']:
                raise ValueError('selected original PNG hash differs before native construction')
    if len(selected) != len(request['image_bindings']): raise ValueError('extra diagnostic image binding')
    if not Path(request['output']).is_absolute(): raise ValueError('absolute diagnostic output required')
    for identity in (request['code'], request['historical'].get('code', {})):
        if (identity.get('format') != 'egrs.sim.code.v1' or identity.get('identity') != digest(identity.get('files'))):
            raise ValueError('invalid diagnostic/historical code identity')
    return deepcopy(request)


def measure_rgb(original, candidate, foreground, *, min_pixels):
    original = np.asarray(original); candidate = np.asarray(candidate); foreground = np.asarray(foreground)
    if (original.dtype != np.uint8 or candidate.dtype != np.uint8 or original.shape != candidate.shape
            or original.ndim != 3 or original.shape[2] != 3 or foreground.dtype != bool
            or foreground.shape != original.shape[:2]):
        raise ValueError('diagnostic RGB/mask dimensions or types differ')
    signed = (candidate.astype(float) - original.astype(float))/255.
    absolute = np.abs(signed); count = int(foreground.sum()); total = foreground.size
    whole = float(absolute.mean())
    fg = float(absolute[foreground].mean()) if count >= min_pixels and count else None
    bg = float(absolute[~foreground].mean()) if count < total else None
    return dict(whole_mae=whole, foreground_mae=fg, background_mae=bg,
                whole_pixels=total, foreground_pixels=count, background_pixels=total-count,
                signed_bias=signed.mean(axis=(0,1)).tolist(), bias_direction='candidate-minus-original; /255',
                original_max_metric=max(whole,fg) if fg is not None else None,
                foreground_unavailable=None if fg is not None else 'insufficient_visible_foreground',
                background_unavailable=None if bg is not None else 'empty_background',
                min_foreground_pixels=min_pixels, units='absolute RGB /255', difference_multiplier=1)


def state_snapshot(sim, flattened=None, *, origin):
    """Decode using the runtime API, never inferred slices of a mixed-unit vector."""
    state = sim.get_state()
    flat = np.asarray(state.flatten() if flattened is None else flattened).copy()
    result = dict(origin=origin, runtime_class=type(state).__qualname__, runtime_module=type(state).__module__,
                  sha256=hashlib.sha256(flat.tobytes()).hexdigest(), dtype=str(flat.dtype), length=int(flat.size),
                  flattened=flat.tolist(), groups={}, unavailable=None)
    try:
        if flat.ndim != 1 or not flat.size or not np.isfinite(flat).all(): raise ValueError('invalid flattened state')
        codec = getattr(type(state), 'from_flattened', None)
        if codec is None: raise ValueError('runtime state codec from_flattened unavailable')
        decoded = codec(flat.copy(), sim)
        roundtrip = np.asarray(decoded.flatten())
        if roundtrip.shape != flat.shape or not np.array_equal(roundtrip, flat):
            raise ValueError('runtime state codec exact round-trip failed')
        for name in ('time','qpos','qvel','act'):
            if not hasattr(decoded, name):
                result['groups'][name] = dict(values=None, unavailable='field absent in runtime state API')
                continue
            value = np.asarray(getattr(decoded, name))
            if not np.issubdtype(value.dtype, np.number) or not np.isfinite(value).all():
                result['groups'][name] = dict(values=None, unavailable='nonfinite/nonnumeric runtime field')
            else:
                result['groups'][name] = dict(values=value.reshape(-1).tolist(), unavailable=None)
    except Exception as error:
        result['unavailable'] = type(error).__name__ + ': ' + str(error)[:1000]
    return result


def compare_states(left, right):
    a = np.asarray(left['flattened']); b = np.asarray(right['flattened'])
    full = float(np.max(np.abs(a-b))) if a.shape == b.shape and a.size and np.isfinite(a).all() and np.isfinite(b).all() else None
    result = dict(left_origin=left['origin'], right_origin=right['origin'], left_sha256=left['sha256'],
                  right_sha256=right['sha256'], full_max_abs_residual=full,
                  full_unavailable=None if full is not None else 'full state shape/nonfinite mismatch', groups={})
    for name in ('time','qpos','qvel','act'):
        x = left['groups'].get(name, {}); y = right['groups'].get(name, {})
        reason = left['unavailable'] or right['unavailable'] or x.get('unavailable') or y.get('unavailable')
        av = x.get('values'); bv = y.get('values')
        if reason or av is None or bv is None or len(av) != len(bv) or not av:
            result['groups'][name] = dict(max_abs_residual=None, size=None, unavailable=reason or 'empty/different named field layout')
        else:
            result['groups'][name] = dict(max_abs_residual=float(np.max(np.abs(np.asarray(av)-bv))), size=len(av),
                                           unavailable=None)
    return result


def _png_artifacts(output, original, candidate, support, *, label, emit):
    from PIL import Image, ImageDraw
    images = dict(original=Image.fromarray(original), candidate=Image.fromarray(candidate),
                  difference=Image.fromarray(np.abs(candidate.astype(np.int16)-original.astype(np.int16)).astype(np.uint8)),
                  foreground=Image.fromarray(support.astype(np.uint8)*255))
    width, height = images['original'].size
    text_width = ImageDraw.Draw(images['original']).textbbox((0,0),label)[2]
    panel = Image.new('RGB', (max(width*4, text_width+6, 900), height+65), 'white')
    draw = ImageDraw.Draw(panel); draw.text((3,3), label, fill='black')
    draw.text((3,20), 'original | candidate (existing orientation) | absolute difference x1 | foreground', fill='black')
    for i, image in enumerate(images.values()): panel.paste(image, (i*width,60))
    images['panel'] = panel
    artifacts = {}
    for name, image in images.items():
        path = output/(name+'.png'); image.save(path)
        record = dict(kind=name, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      width=image.width, height=image.height)
        artifacts[name] = record; emit(record)
    return artifacts


def process_diagnostic_source(request, *, adapter_factory=None, emit=None):
    request = validate_diagnostic_request(request)
    if adapter_factory is None:
        from .sim_native import NativeAdapter
        adapter_factory = NativeAdapter
    from .sim_native import evaluate_atoms
    source = request['source_request']; sid = source['source']['source_id']
    output = Path(request['output']); output.mkdir(parents=True, exist_ok=False)
    result = dict(format=RESPONSE_FORMAT, request_id=request['request_id'], source_id=sid,
                  historical=request['historical'], code=request['code'], inspection=None, candidates=[],
                  measurements=[], states=[], artifacts=[], errors=[], counts={k:0 for k in BUDGET}, status='failed')
    sequence = 0
    def event(kind, data):
        nonlocal sequence
        record = dict(format=EVENT_FORMAT, request_id=request['request_id'], source_id=sid,
                      sequence=sequence, type=kind, data=deepcopy(data))
        json.dumps(record, allow_nan=False); sequence += 1
        if emit is not None: emit(record)
    def initialization(kind,data):
        if kind not in {'stage','inspection'}: raise ValueError('unsupported diagnostic initialization event')
        if kind == 'inspection': result['inspection'] = deepcopy(data)
        event(kind,data)
    adapter = None; current = None
    try:
        adapter = adapter_factory(source, emit=initialization)
        result['inspection'] = deepcopy(adapter.inspection); event('inspection',result['inspection'])
        # Every original binding is checked against HDF by the unchanged helper.
        originals = {}
        for frame in request['probes']:
            for camera in CAMERAS:
                originals[(frame,camera)] = adapter._original(frame,camera)
                event('original_binding', dict(frame=frame,camera=camera,
                      binding=deepcopy(adapter.image_bindings[f'{frame}:{camera}'])))
        for frame in request['probes']:
            snapshots = {}
            for rule in RULES:
                current = dict(frame=frame, rule=rule, state_index=frame+(rule=='next_state'),
                               action_index=frame if rule=='replay_action' else None)
                result['counts']['candidate_restores'] += 1
                result['counts']['actions'] += int(rule=='replay_action')
                event('operation', current)
                adapter._restore(current['state_index'], current['action_index'])
                snapshot = state_snapshot(adapter.env.sim, origin=rule+'_actual')
                snapshots[rule] = snapshot
                truths, atoms = {}, []
                for goal in adapter.goals:
                    try:
                        values, records = evaluate_atoms(adapter.inner, [goal])
                        truths.update(values); atoms.extend(records)
                    except Exception as error:
                        # An unrecognized native predicate failure is still unknown.
                        truths[goal['goal_ref']] = None
                        atoms.append(dict(goal_ref=goal['goal_ref'],atom=deepcopy(goal['atom']),truth=None,
                                          gap=type(error).__name__+': '+str(error)[:1000]))
                candidate = dict(**current, state=snapshot, native_truths=truths, native_atoms=atoms)
                result['candidates'].append(candidate); event('candidate',candidate)
                if rule == 'replay_action':
                    source_next = state_snapshot(adapter.env.sim, adapter.episode.state(frame+1), origin='source_next')
                    comparison = dict(frame=frame, source_next_vs_replay=compare_states(source_next,snapshot),
                                      actual_next_vs_replay=compare_states(snapshots['next_state'],snapshot),
                                      source_next=source_next)
                    result['states'].append(comparison); event('state_comparison',comparison)
                for camera in CAMERAS:
                    # Conservative attempts: _render owns exactly RGB + segmentation calls.
                    result['counts']['direct_renders'] += 2
                    event('render_attempt',dict(frame=frame,rule=rule,camera=camera,direct_renders=2))
                    rgb, raw = adapter._render(camera)
                    support = adapter._foreground(raw)
                    if request['orientation'] == 'flip_vertical': rgb=rgb[::-1]; support=support[::-1]
                    original = originals[(frame,camera)]
                    metrics = measure_rgb(original,rgb,support,min_pixels=adapter.config['min_visible_pixels'])
                    directory = output/f'{frame:06d}'/rule/camera; directory.mkdir(parents=True)
                    binding = dict(frame=frame,rule=rule,camera=camera)
                    def artifact(record):
                        value = dict(**binding,**record)
                        result['artifacts'].append(value); event('artifact',value)
                    artifacts = _png_artifacts(directory,original,rgb,support,
                        label=f'{sid} frame={frame} rule={rule} camera={camera} orientation={request["orientation"]}', emit=artifact)
                    measurement = dict(**binding,orientation=request['orientation'], metrics=metrics,artifacts=artifacts,
                        original_pixel_sha256=hashlib.sha256(original.tobytes()).hexdigest(),
                        candidate_pixel_sha256=hashlib.sha256(np.ascontiguousarray(rgb).tobytes()).hexdigest())
                    result['counts']['comparisons'] += 1
                    result['measurements'].append(measurement); event('measurement',measurement)
        result['status'] = 'complete'
    except Exception as error:
        if getattr(error,'inspection',None) is not None:
            result['inspection']=deepcopy(error.inspection); event('inspection',result['inspection'])
        for item in getattr(error,'audit',[]): event('audit',item)
        failure=dict(operation=current,error_type=type(error).__name__,reason=str(error)[:2000])
        result['errors'].append(failure); event('error',failure)
        result['status']='partial' if result['candidates'] or result['artifacts'] else 'failed'
    finally:
        if adapter is not None:
            try:
                for item in adapter.audit: event('audit',item)
            finally:
                try: adapter.close()
                except Exception as error:
                    failure=dict(operation='close',error_type=type(error).__name__,reason=str(error)[:2000])
                    result['errors'].append(failure); event('error',failure)
                    result['status']='partial' if result['candidates'] or result['artifacts'] else 'failed'
    event('result',result)
    return result


class DiagnosticTrace:
    """Closed streamed protocol shared by controller and subprocess transport."""
    def __init__(self, request):
        self.request=validate_diagnostic_request(request); self.events=[]; self.result=None
        self.candidates=[]; self.measurements=[]; self.states=[]; self.artifacts=[]; self.errors=[]
        self.counts={k:0 for k in BUDGET}; self.operations=[]; self.renders=[]
        self.plan=[(f,r) for f in request['probes'] for r in RULES]
        self.image_plan=[(f,r,c) for f,r in self.plan for c in CAMERAS]

    def accept(self,event):
        req=self.request; sid=req['source_request']['source']['source_id']
        kinds={'stage','inspection','original_binding','operation','candidate','state_comparison',
               'render_attempt','artifact','measurement','audit','error','result'}
        if (not isinstance(event,dict) or set(event)!={'format','request_id','source_id','sequence','type','data'}
                or event['format']!=EVENT_FORMAT or event['request_id']!=req['request_id']
                or event['source_id']!=sid or type(event['sequence']) is not int
                or event['sequence']!=len(self.events) or event['type'] not in kinds or self.result is not None):
            raise ValueError('diagnostic event identity/order/schema mismatch')
        kind=event['type']; data=event['data']
        if kind=='operation':
            index=len(self.operations)
            if index>=len(self.plan) or (data.get('frame'),data.get('rule'))!=self.plan[index]:
                raise ValueError('diagnostic candidate plan/order mismatch')
            frame,rule=self.plan[index]
            if data.get('state_index')!=frame+(rule=='next_state') or data.get('action_index')!=(frame if rule=='replay_action' else None):
                raise ValueError('diagnostic operation indices differ')
            self.operations.append(deepcopy(data)); self.counts['candidate_restores']+=1
            self.counts['actions']+=int(rule=='replay_action')
        elif kind=='candidate':
            if (len(self.candidates)>=len(self.operations) or not self.operations
                    or any(data.get(k)!=v for k,v in self.operations[-1].items())):
                raise ValueError('diagnostic candidate binding mismatch')
            self.candidates.append(deepcopy(data))
        elif kind=='render_attempt':
            index=len(self.renders)
            if (index>=len(self.image_plan) or (data.get('frame'),data.get('rule'),data.get('camera'))!=self.image_plan[index]
                    or data.get('direct_renders')!=2 or not self.candidates
                    or (data['frame'],data['rule'])!=(self.candidates[-1]['frame'],self.candidates[-1]['rule'])):
                raise ValueError('diagnostic render budget/order differs')
            self.renders.append(deepcopy(data)); self.counts['direct_renders']+=2
        elif kind in {'artifact','measurement'}:
            if not self.renders or any(data.get(k)!=self.renders[-1][k] for k in ('frame','rule','camera')):
                raise ValueError('diagnostic image binding differs')
            if kind=='artifact':
                if data.get('kind') not in {'original','candidate','difference','foreground','panel'}:
                    raise ValueError('invalid diagnostic PNG kind')
                path=Path(data['path']).resolve()
                if not path.is_relative_to(Path(req['output']).resolve()): raise ValueError('diagnostic artifact escapes output')
                if any(x['path']==data['path'] for x in self.artifacts): raise ValueError('duplicate diagnostic artifact')
                self.artifacts.append(deepcopy(data))
            else:
                index=len(self.measurements)
                if index>=len(self.image_plan) or (data['frame'],data['rule'],data['camera'])!=self.image_plan[index]:
                    raise ValueError('diagnostic measurement count/order differs')
                if data.get('orientation')!=req['orientation']: raise ValueError('diagnostic measurement orientation differs')
                artifacts=[a for a in self.artifacts if all(a[k]==data[k] for k in ('frame','rule','camera'))]
                if len(artifacts)!=5 or data.get('artifacts')!={a['kind']:{k:v for k,v in a.items() if k not in {'frame','rule','camera'}} for a in artifacts}:
                    raise ValueError('diagnostic measurement PNG index differs')
                self.measurements.append(deepcopy(data)); self.counts['comparisons']+=1
        elif kind=='state_comparison':
            if (len(self.states)>=3 or data.get('frame')!=req['probes'][len(self.states)]
                    or not self.candidates or self.candidates[-1]['rule']!='replay_action'):
                raise ValueError('diagnostic state comparison binding differs')
            self.states.append(deepcopy(data))
        elif kind=='error': self.errors.append(deepcopy(data))
        elif kind=='stage':
            if not isinstance(data,dict) or set(data)!={'stage','phase'} or data['phase'] not in {'begin','complete'}:
                raise ValueError('invalid diagnostic initialization stage')
        elif kind=='result':
            keys={'format','request_id','source_id','historical','code','inspection','candidates',
                  'measurements','states','artifacts','errors','counts','status'}
            if (set(data)!=keys or data.get('format')!=RESPONSE_FORMAT or data.get('request_id')!=req['request_id'] or data.get('source_id')!=sid
                    or data.get('historical')!=req['historical'] or data.get('code')!=req['code']
                    or data.get('status') not in {'complete','partial','failed'} or data.get('counts')!=self.counts
                    or any(data.get(k)!=getattr(self,k) for k in ('candidates','measurements','states','artifacts','errors'))
                    or (data['status']=='complete' and (self.errors or len(self.measurements)!=18 or len(self.states)!=3))
                    or (data['status']!='complete' and not self.errors)):
                raise ValueError('diagnostic result disagrees with streamed evidence')
            self.result=deepcopy(data)
        json.dumps(event,allow_nan=False); self.events.append(deepcopy(event))


def serve(stdin=None,stdout=None,stderr=None):
    import sys
    from contextlib import redirect_stdout,redirect_stderr
    from .sim_worker import MAX_LINE_BYTES
    stdin=stdin or sys.stdin; stdout=stdout or sys.stdout; stderr=stderr or sys.stderr
    line=stdin.readline(MAX_LINE_BYTES+1)
    def emit(event):
        stdout.write(json.dumps(event,allow_nan=False,separators=(',',':'))+'\n'); stdout.flush()
    if len(line.encode('utf-8'))>MAX_LINE_BYTES: raise ValueError('diagnostic request exceeds protocol bound')
    with redirect_stdout(stderr),redirect_stderr(stderr): process_diagnostic_source(json.loads(line),emit=emit)
    return 0


def main():
    import os
    import sys
    protocol=os.fdopen(os.dup(sys.stdout.fileno()),'w',encoding='utf-8',buffering=1)
    os.dup2(sys.stderr.fileno(),sys.stdout.fileno())
    return serve(stdout=protocol)
