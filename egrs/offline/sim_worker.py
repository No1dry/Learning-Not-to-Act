"""One-source JSONL worker and fake-compatible isolated transport.

Run explicitly: python -m egrs.offline.sim_worker. stdin is exactly one request;
stdout is versioned JSONL events only. Native diagnostics go to stderr. No retry,
sampling, model launch or automatic job scheduling is performed here.
"""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from .sim_contract import mapping_for, validate_frame_facts
from .sim_identity import code_identity
from .sim_metadata import validate_dataset_identity

REQUEST_FORMAT='egrs.sim.request.v1'
RESPONSE_FORMAT='egrs.sim.response.v1'
EVENT_FORMAT='egrs.sim.event.v1'
MAX_LINE_BYTES=16*1024*1024


def validate_request(request):
    json.dumps(request,allow_nan=False)
    expected={'format','request_id','source_root','source','registry','frames','config'}
    if not isinstance(request,dict) or set(request)-{'dataset_identity'}!=expected or request['format']!=REQUEST_FORMAT:
        raise ValueError('invalid simulator source request')
    if 'dataset_identity' in request: validate_dataset_identity(request['dataset_identity'])
    for key in ('request_id','source_root'):
        if not isinstance(request[key],str) or not request[key]: raise ValueError('missing '+key)
    source=request['source']
    if not isinstance(source,dict) or not {'source_id','file','episode','T','instruction','orientation'}<=set(source):
        raise ValueError('source must contain unchanged inventory descriptor')
    if type(source['T']) is not int or source['T']<1 or not isinstance(source['source_id'],str) or not source['source_id']:
        raise ValueError('invalid source binding')
    if request['registry']['instruction']!=source['instruction']:
        raise ValueError('source/registry instruction mismatch')
    mapping_for(request['registry'])
    if not isinstance(request['config'],dict): raise ValueError('native config object required')
    frames=request['frames']
    if not isinstance(frames,list) or not 1<=len(frames)<=18:
        raise ValueError('request needs 1..18 unique existing physical frames')
    seen=set()
    for item in frames:
        if not isinstance(item,dict) or set(item)!={'frame','images'}:
            raise ValueError('invalid frame request')
        frame=item['frame']
        if type(frame) is not int or not 0<=frame<source['T'] or frame in seen:
            raise ValueError('duplicate/out-of-bounds physical frame')
        seen.add(frame)
        if set(item['images'])!={'agentview','wrist'}:
            raise ValueError('exact original two-camera images required')
        for image in item['images'].values():
            if not isinstance(image,dict) or set(image)!={'path','width','height'}:
                raise ValueError('invalid original image descriptor')
            if not isinstance(image['path'],str) or not image['path'] or any(type(image[k]) is not int or not 1<=image[k]<=8192 for k in ('width','height')):
                raise ValueError('invalid original image path/dimensions')
    return deepcopy(request)


def process_source(request, *, adapter_factory=None, emit=None):
    """Return bounded source result; emit each completed fact/audit immediately.

    A failing native operation stops this source without retries. Previously
    emitted frames survive. The consumer must journal events synchronously.
    Adapter factory(request, *, emit) receives a synchronous initialization
    callback emit(kind,data) for inspection/stage before native work. Adapter
    protocol: inspection/audit attributes; align(), frame(index,align),
    close(). Constructor errors must clean their own partially owned resources.
    """
    request=validate_request(request)
    if adapter_factory is None:
        from .sim_native import NativeAdapter
        adapter_factory=NativeAdapter
    result={'format':RESPONSE_FORMAT,'request_id':request['request_id'],
            'source_id':request['source']['source_id'],'inspection':None,'alignment':None,
            'frames':[],'audit':[],'errors':[],'status':'failed'}
    sequence=0
    def event(kind,data):
        nonlocal sequence
        record={'format':EVENT_FORMAT,'request_id':request['request_id'],
                'source_id':request['source']['source_id'],'sequence':sequence,'type':kind,'data':deepcopy(data)}
        sequence+=1
        json.dumps(record,allow_nan=False)
        if emit is not None: emit(record)
    adapter=None; frame=None; audit_count=0
    def initialization_event(kind,data):
        if kind=='inspection':
            result['inspection']=deepcopy(data)
        elif kind=='stage':
            if not isinstance(data,dict) or set(data)!={'stage','phase'} or data['phase'] not in {'begin','complete'}:
                raise ValueError('invalid initialization stage event')
            result['audit'].append({'type':'initialization_stage',**deepcopy(data)})
        else:
            raise ValueError('unsupported initialization event')
        event(kind,data)
    try:
        adapter=adapter_factory(request,emit=initialization_event)
        result['inspection']=deepcopy(adapter.inspection)
        event('inspection',result['inspection'])
        result['alignment']=adapter.align()
        event('alignment',result['alignment'])
        for item in adapter.audit:
            result['audit'].append(deepcopy(item)); event('audit',item)
        audit_count=len(adapter.audit)
        for item in request['frames']:
            frame=item['frame']
            facts,audit=adapter.frame(frame,result['alignment'])
            facts=validate_frame_facts(facts)
            if facts['source_id']!=result['source_id'] or facts['frame']!=frame:
                raise ValueError('adapter frame/source response binding differs')
            result['frames'].append(facts)
            result['audit'].append(audit)
            event('frame',facts); event('audit',audit)
            # This is processed-frame progress; controller computes supervised-query counts.
            event('progress',{'processed_frames':len(result['frames']),'planned_frames':len(request['frames']),
                              'processed_percent':100*len(result['frames'])/len(request['frames'])})
        result['status']='complete'
    except Exception as error:
        if getattr(error,'inspection',None) is not None:
            result['inspection']=deepcopy(error.inspection); event('inspection',result['inspection'])
        for item in getattr(error,'audit',[]):
            result['audit'].append(deepcopy(item)); event('audit',item)
        failure={'stage':'frame' if frame is not None else getattr(error,'failure_stage','source'),'frame':frame,
                 'error_type':type(error).__name__,'reason':str(error)[:2000]}
        result['errors'].append(failure); event('error',failure)
        result['status']='partial' if result['frames'] else 'failed'
    finally:
        if adapter is not None:
            for item in adapter.audit[audit_count:]:
                result['audit'].append(deepcopy(item)); event('audit',item)
            try: adapter.close()
            except Exception as error:
                failure={'stage':'close','frame':None,'error_type':type(error).__name__,'reason':str(error)[:2000]}
                result['errors'].append(failure); event('error',failure)
                result['status']='partial' if result['frames'] else 'failed'
    event('result',result)
    return result


def serve(stdin=None, stdout=None, stderr=None, *, adapter_factory=None):
    stdin=stdin or sys.stdin; stdout=stdout or sys.stdout; stderr=stderr or sys.stderr
    line=stdin.readline(MAX_LINE_BYTES+1)
    def emit(event):
        stdout.write(json.dumps(event,allow_nan=False,separators=(',',':'))+'\n'); stdout.flush()
    try:
        if len(line.encode('utf-8'))>MAX_LINE_BYTES: raise ValueError('request exceeds protocol bound')
        request=json.loads(line)
        # Python prints from native imports and runtime never contaminate protocol stdout.
        with redirect_stdout(stderr), redirect_stderr(stderr):
            process_source(request,adapter_factory=adapter_factory,emit=emit)
        return 0
    except Exception as error:
        emit({'format':EVENT_FORMAT,'request_id':None,'source_id':None,'sequence':0,'type':'error',
              'data':{'stage':'protocol','frame':None,'error_type':type(error).__name__,'reason':str(error)[:2000]}})
        return 2


class WorkerFailure(RuntimeError):
    """Timeout/crash/protocol gap; preceding validated JSONL events are retained."""
    def __init__(self,message,events,stderr):
        super().__init__(message)
        self.events=events
        self.stderr=stderr


def run_isolated(request, *, python, module_paths=(), timeout_seconds=600, on_event=None,
                 expected_code_identity=None):
    """One interpreter/source; callback receives validated events as they arrive.

    Timeout applies to the entire source (including native initialization). Kill
    and reap the isolated worker on timeout/crash/protocol error; never retry.
    WorkerFailure.events preserves completed frame/audit events for the journal.
    Only the last 64 KiB diagnostics are retained in memory.
    Private expected_code_identity binds the controller's manifest snapshot;
    standalone callers default to this package's current source identity.
    """
    request=validate_request(request)
    if type(timeout_seconds) not in (int,float) or not 0<timeout_seconds<=86400:
        raise ValueError('bounded positive source timeout required')
    env=os.environ.copy()
    paths=[str(Path(__file__).resolve().parents[2]),*(str(Path(x).resolve(strict=True)) for x in module_paths)]
    env['PYTHONPATH']=os.pathsep.join(paths)
    env['PYTHONUNBUFFERED']='1'
    if expected_code_identity is None: expected_code_identity=code_identity()['identity']
    bootstrap=Path(__file__).resolve().with_name('sim_bootstrap.py')
    process=subprocess.Popen([str(python),'-B',str(bootstrap),expected_code_identity],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env)
    events=[]; diagnostics=[]; inbox=queue.Queue(maxsize=256)
    def read_stdout():
        try:
            while True:
                line=process.stdout.readline(MAX_LINE_BYTES+1)
                if not line: break
                inbox.put(line)
        finally: inbox.put(None)
    def read_stderr():
        while True:
            chunk=process.stderr.read(4096)
            if not chunk: break
            diagnostics.append(chunk)
            while sum(map(len,diagnostics))>65536: diagnostics.pop(0)
    readers=[threading.Thread(target=read_stdout,daemon=True),threading.Thread(target=read_stderr,daemon=True)]
    for reader in readers: reader.start()
    deadline=time.monotonic()+timeout_seconds
    result=None
    try:
        process.stdin.write(json.dumps(request,allow_nan=False)+'\n'); process.stdin.close()
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise TimeoutError('native source timeout')
            try: line=inbox.get(timeout=remaining)
            except queue.Empty: raise TimeoutError('native source timeout') from None
            if line is None: break
            if len(line.encode('utf-8'))>MAX_LINE_BYTES: raise ValueError('worker response exceeds bound')
            event=json.loads(line)
            if (not isinstance(event,dict) or set(event)!={'format','request_id','source_id','sequence','type','data'}
                or event['format']!=EVENT_FORMAT or event['request_id']!=request['request_id']
                or event['source_id']!=request['source']['source_id'] or event['sequence']!=len(events)
                or event['type'] not in {'inspection','stage','alignment','frame','audit','error','progress','result'} or result is not None):
                raise ValueError('worker event identity/order/schema mismatch')
            if event['type']=='frame':
                facts=validate_frame_facts(event['data'])
                if facts['source_id']!=request['source']['source_id'] or facts['frame'] not in {x['frame'] for x in request['frames']}:
                    raise ValueError('worker fact source/frame mismatch')
            events.append(event)
            if on_event is not None: on_event(deepcopy(event))
            if event['type']=='result': result=event['data']
        process.wait(timeout=max(.01,deadline-time.monotonic()))
        readers[1].join(timeout=1)  # Retain startup diagnostics before building WorkerFailure.
        if process.returncode!=0 or result is None:
            raise RuntimeError('worker exited without a complete protocol result')
        if result.get('format')!=RESPONSE_FORMAT or result.get('request_id')!=request['request_id'] or result.get('source_id')!=request['source']['source_id']:
            raise ValueError('worker result binding mismatch')
        return result
    except Exception as error:
        raise WorkerFailure(str(error),deepcopy(events),''.join(diagnostics)) from error
    finally:
        if process.poll() is None: process.kill()
        process.wait()
        for stream in (process.stdout,process.stderr): stream.close()
        for reader in readers: reader.join(timeout=1)


def main():
    # Also redirect OS-level stdout (native C/C++ diagnostics); retain a separate
    # original descriptor exclusively for the JSONL protocol.
    protocol=os.fdopen(os.dup(sys.stdout.fileno()),'w',encoding='utf-8',buffering=1)
    os.dup2(sys.stderr.fileno(),sys.stdout.fileno())
    return serve(stdout=protocol)


if __name__=='__main__':
    raise SystemExit(main())
