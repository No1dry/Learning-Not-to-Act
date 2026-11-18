"""User-started P1 then P2, with exclusive persistent markers and no retries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def _preflight(path,output):
    from .evaluation import load_config,validate_output_paths
    config=load_config(path)
    validate_output_paths(config,output)
    return config


def _execute(command):
    return subprocess.run(command,check=False)


def _overlap(a,b):
    return a==b or a in b.parents or b in a.parents


def _write(path,value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def _verify_report(output,variant):
    from .policy import check_adapter
    with (output/'summary.json').open(encoding='utf-8') as stream:report=json.load(stream)
    sr=report.get('formal_SR')
    if (report.get('schema_version')!='task046-prompt-eval-v1' or report.get('variant')!=variant
            or report.get('formal_complete') is not True or report.get('software_exit')!='success'
            or report.get('budget',{}).get('total')!=90 or not isinstance(sr,dict)
            or type(sr.get('denominator')) is not int or sr['denominator']!=90
            or type(sr.get('numerator')) is not int or not 0<=sr['numerator']<=90
            or sr.get('percent')!=100*sr['numerator']/90):
        raise ValueError('046 sequential arm lacks a complete successful formal90 report')
    check_adapter(report.get('method_adapter',{}))
    if (report.get('checkpoint_step')!=3000 or report.get('arm')!='h1'
            or report.get('research_adapter_loaded') is not True
            or report.get('p0',{}).get('new_execution') is not False
            or report.get('p0',{}).get('rate')!={'numerator':62,'denominator':90,'percent':100*62/90}):
        raise ValueError('046 sequential report is not the frozen H1@3000/P0 experiment')
    return report


def run_both(*,p1_config,p2_config,p1_output,p2_output,marker):
    configs=[Path(p1_config).resolve(),Path(p2_config).resolve()]
    outputs=[Path(p1_output).resolve(),Path(p2_output).resolve()]
    marker=Path(marker).resolve()
    destinations=[*outputs,marker]
    for i,path in enumerate(destinations):
        if path.exists():raise FileExistsError('046 refuses existing output or persistent launch marker: '+str(path))
        if any(_overlap(path,other) for other in destinations[:i]+configs):
            raise ValueError('046 output/marker/input paths overlap')
    prepared=[]
    for variant,config,output in zip(('p1','p2'),configs,outputs):
        value=_preflight(config,output)
        _preflight(config,marker)
        if value.get('variant')!=variant:raise ValueError('046 sequential config variant differs')
        prepared.append(value)
    if {k:v for k,v in prepared[0].items() if k!='variant'}!={k:v for k,v in prepared[1].items() if k!='variant'}:
        raise ValueError('046 matched variants require identical immutable inputs')
    # Atomic exclusive directory claim; both failures and completion remain.
    marker.mkdir(parents=True,exist_ok=False)
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in configs]
    state={'format':'task046-sequential-launch-v1','status':'running','variants':{},
        'budget':{'p1':90,'p2':90,'total':180,'predict_call_ceiling':11700},
        'configs':[str(p) for p in configs],'config_sha256':hashes,'outputs':[str(p) for p in outputs]}
    _write(marker/'status.json',state)
    try:
        for variant,config,output,digest in zip(('p1','p2'),configs,outputs,hashes):
            if hashlib.sha256(config.read_bytes()).hexdigest()!=digest:
                raise ValueError('046 configuration changed after sequential launch')
            if output.exists():raise FileExistsError('046 output appeared after launch preflight')
            state['variants'][variant]={'status':'running'};_write(marker/'status.json',state)
            command=[sys.executable,'-u','-m','egrs.prompt046','evaluate','--config',str(config),'--output',str(output)]
            result=_execute(command)
            if result.returncode!=0:raise RuntimeError(f'046 {variant} process exited {result.returncode}; next arm not started')
            report=_verify_report(output,variant)
            state['variants'][variant]={'status':'complete','formal_SR':report['formal_SR'],
                'summary_sha256':hashlib.sha256((output/'summary.json').read_bytes()).hexdigest()}
            _write(marker/'status.json',state)
        compare_reports(outputs[0],outputs[1],marker)
        state['status']='complete';_write(marker/'status.json',state)
        return state
    except BaseException as error:
        state.update(status='failed',error=f'{type(error).__name__}: {error}')
        _write(marker/'status.json',state)
        raise


def compare_reports(p1_output,p2_output,directory):
    from .evaluation import paired_results
    p1=_verify_report(Path(p1_output),'p1');p2=_verify_report(Path(p2_output),'p2')
    if p1['p0']!=p2['p0'] or p1['method_adapter']!=p2['method_adapter']:
        raise ValueError('046 compared models or reused P0 differ')
    table={t['task_id']:{'p0':0,'p1':0,'p2':0} for t in p1['binary_report']['tasks']}
    for variant,rows in [('p0',p1['p0']['episodes']),('p1',p1['binary_report']['episodes']),('p2',p2['binary_report']['episodes'])]:
        for row in rows:table[row['task_id']][variant]+=int(row['success'])
    result={'format':'task046-comparison-v1','p0':p1['p0']['rate'],'p1':p1['formal_SR'],'p2':p2['formal_SR'],
        'new_execution':{'p0':False,'p1':True,'p2':True},'tasks':table,
        'p1_vs_p0':p1['paired_vs_p0'],'p2_vs_p0':p2['paired_vs_p0'],
        'p2_vs_p1':paired_results(p1['binary_report']['episodes'],p2['binary_report']['episodes']),
        'method_adapter_sha256':p1['method_adapter']['adapter_sha256']}
    _write(Path(directory)/'comparison.json',result)
    lines=['# 046 H1@3000: P0/P1/P2','', '| Variant | Formal10 SR | Execution |','|---|---:|---|']
    for variant in ('p0','p1','p2'):
        r=result[variant];label='reused045' if variant=='p0' else 'new90'
        lines.append(f"| {variant.upper()} | {r['percent']:.2f}% ({r['numerator']}/90) | {label} |")
    lines+=['','| Task | P0 | P1 | P2 |','|---|---:|---:|---:|']
    for task,counts in table.items():lines.append('| '+task+' | '+' | '.join(f"{counts[v]*10}% ({counts[v]}/10)" for v in ('p0','p1','p2'))+' |')
    (Path(directory)/'comparison.md').write_text('\n'.join(lines)+'\n')
    print('046 COMPLETE '+ ' '.join(f"{v.upper()}={result[v]['percent']:.2f}%" for v in ('p0','p1','p2')),flush=True)
    return result
