"""035 file-only plan and explicit user-started bounded native generation."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from egrs.augmentation.data import identity,file_sha256,read_json,load_scope,_require,_hex
from egrs.augmentation.progress_native import validate_binding
from .data import validate_seeds,export_generated,DATA_KIND

CONFIG='task035-generation-config-v1'
RECIPE={'name':'robot_rewind_v1','seed':7,'variants':3,'bridge_attempts':2,'horizon':520,
        'joint_perturbation_rad':0.05,'position_tolerance_m':0.005,'rotation_tolerance_deg':3.,
        'bridge_stage_steps':40,'lift_m':0.1}


def _resolve(base,value):
    p=Path(value).expanduser()
    return str((base/p).resolve() if not p.is_absolute() else p.resolve())


def build_plan(config_path):
    """Read JSON metadata only; do not read HDF contents or instantiate native."""
    path=Path(config_path).resolve();cfg=read_json(path)
    fields={'format','manifest','benchmark_root','stats_path','stats_sha256','unnorm_key','recipe','native_backend','bindings'}
    _require(set(cfg)==fields and cfg['format']==CONFIG,'explicit035 generation configuration required')
    _require(cfg['recipe']==RECIPE,'fixed bounded035 recipe required')
    _require(_hex(cfg['stats_sha256']) and cfg['unnorm_key'] in {'libero_10','libero_10_no_noops'},'original SOG10 statistics binding required')
    for key in ('manifest','benchmark_root','stats_path'):cfg[key]=_resolve(path.parent,cfg[key])
    # Use the already delivered030 path resolution schema, without constructing its backend.
    native=cfg['native_backend'];_require(native.get('kind')=='native','035 requires the concrete native generator')
    for key in ('historical_root','python'):
        if key in native:native[key]=_resolve(path.parent,native[key])
    if 'module_paths' in native:native['module_paths']=[_resolve(path.parent,p) for p in native['module_paths']]
    legacy=native.get('native',{})
    for obj,key in ((legacy,'bddl_root'),(legacy.get('core',{}),'root')):
        if key in obj:obj[key]=_resolve(path.parent,obj[key])
    if 'asset_roots' in legacy:
        _require(isinstance(legacy['asset_roots'],dict),'native asset roots must be named mapping')
        legacy['asset_roots']={k:_resolve(path.parent,p) for k,p in legacy['asset_roots'].items()}
    manifest=read_json(cfg['manifest']);sources=validate_seeds(manifest)
    data_root=_resolve(Path(cfg['manifest']).parent,manifest['data_root'])
    bindings=cfg['bindings'];_require(isinstance(bindings,dict),'explicit source/task native bindings required')
    _require(not set(bindings)-{s['source_id'] for s in sources}-{s['task_key'] for s in sources},'foreign native binding')
    for s in sources:
        binding=deepcopy(s.get('native_binding',bindings.get(s['source_id'],bindings.get(s['task_key']))))
        _require(binding is not None,'native source binding missing: '+s['source_id'])
        validate_binding(s,binding)
        for key in ('official_task_name','active_goals','invariant_predicates'):
            _require(binding.get(key)==s[key],'native goal/scope binding differs: '+key)
        s['native_binding']=binding
        for field in ('action_normalization','proprio_normalization'):
            norm=s['mapping'][field]
            _require(norm['stats_sha256']==cfg['stats_sha256'] and norm['stats_id']==cfg['unnorm_key'],
                     'source original statistics identity differs')
    n=len(sources)
    plan={'format':'task035-generation-plan-v1','config':cfg,'source_manifest_identity':identity(manifest),
        'data_root':data_root,'sources':sources,'population':{'parent_sources':n,
            'parent_groups':len({s['source_group'] for s in sources}),'max_normal_replays':n,
            'max_robot_starts':3*n,'max_10_attempts':6*n,'max_control_steps':7*n*520,
            'audit_hold_steps_included_in_horizon':True,'native_initialization_time_included':False},
        'task_coverage':{t['key']:{'requested_max':manifest['max_demos_per_task'],
            'available':sum(s['task_key']==t['key'] for s in sources)} for t in load_scope()['tasks']},
        'simulation_created':False,'model_loaded':False,'selection':'natural firstN parents before outcomes; grouped seed7 split',
        'representative_video':'first natural parent per task; fixed before execution, failures retained'}
    plan['identity']=identity(plan)
    return plan


def _write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def generate(config_path,output,*,source_generator=None):
    """Run the concrete source generator, only when the user invokes generate."""
    output=Path(output)
    if output.exists():raise FileExistsError('new035 generation output required')
    plan=build_plan(config_path);cfg=plan['config']
    _require(file_sha256(cfg['stats_path'])==cfg['stats_sha256'],'original SOG10 stats bytes changed')
    if source_generator is None:
        from .generation import generate_source
        source_generator=generate_source
    output.mkdir(parents=True);_write(output/'generation_plan.json',plan)
    reports=[];attempts=[];errors=0
    for index,source in enumerate(plan['sources']):
        name=f'source-{index:03d}'
        directory=output/'artifacts'/name;directory.mkdir(parents=True)
        source_cfg=deepcopy(cfg);source_cfg['save_video']=source['demo_index']==0
        try:
            result=source_generator(deepcopy(source),source_cfg,Path(plan['data_root']),directory)
            _require(result.get('source_id')==source['source_id'] and isinstance(result.get('attempts'),list),'generator source/attempt contract differs')
            if result.get('error'):errors+=1
            for attempt in result['attempts']:
                row=deepcopy(attempt)
                for key in ('file','audit','video','qualification_file','audit_path','lineage_path','qualification_path','journal_path'):
                    if isinstance(row.get(key),str):
                        child=(directory/row[key]).resolve()
                        _require(child.is_relative_to(directory.resolve()),'attempt artifact escapes source directory')
                        row[key]=child.relative_to(output.resolve()).as_posix()
                attempts.append(row)
        except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
            errors+=1
            result={'source_id':source['source_id'],'attempts':[],
                    'error':f'{type(error).__name__}: {error}','gaps':['source_technical_error_no_success_claim']}
        reports.append(result)
        _write(directory/'source_report.json',result)
        # Durable parent-level checkpoint even if a later user-started source stops.
        _write(output/'generation_progress.json',{'plan_identity':plan['identity'],'source_reports':reports,
            'processed_sources':len(reports),'completion_percent':100*len(reports)/max(1,len(plan['sources']))})
        print(json.dumps({'processed_sources':len(reports),'planned_sources':len(plan['sources']),
                          'completion_percent':100*len(reports)/max(1,len(plan['sources']))}),flush=True)
    data=export_generated(plan['sources'],attempts,output,output/'export')
    result={'format':'task035-generation-report-v1','data_kind':DATA_KIND,'plan_identity':plan['identity'],
        'population':plan['population'],'source_reports':reports,'source_errors':errors,'data':data,
        'status':'completed_with_source_gaps' if errors else 'completed',
        'processed_sources':len(reports),'completion_percent':100.,'model_loaded':False,
        'actual_qualified_10':data['counts_by_domain']['10']['trajectories'],
        'actual_qualified_normal':data['counts_by_domain']['normal']['trajectories']}
    result['identity']=identity(result);_write(output/'generation_report.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['plan','generate'])
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if args.command=='plan':
        output=Path(args.output)
        if output.exists():raise FileExistsError('new plan file required')
        plan=build_plan(args.config)
        with output.open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2,allow_nan=False)
        print(json.dumps(plan['population']),flush=True)
    else:generate(args.config,args.output)


if __name__=='__main__':main()
