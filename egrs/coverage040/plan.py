"""Fixed040 candidate metadata; no simulator, policy, RGB, states or action reads."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re

from egrs.augmentation.data import _instruction, _require, identity, inspect_source, read_json
from egrs.augmentation.progress_native import validate_binding
from egrs.coverage039.io import HashContext, Progress
from egrs.coverage039.recipe import ALGORITHM, BUDGET, RECIPE, TASKS
from egrs.trajectory_augmentation.cli import CONFIG as ORIGINAL_CONFIG, RECIPE as ORIGINAL_RECIPE
from egrs.trajectory_augmentation.data import validate_seeds
from egrs.trajectory_augmentation.native import TEACHER_V2

CONFIG = 'task040-parent-coverage-config-v1'
_BASE_INDEX_IDENTITY = 'b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c'
_BASE_REPORT_IDENTITY = '64a2d4923dda271ffeb2a67f080c81c40bbdb277bae6351328a779791e1abdaf'
_BASE_POOL_COUNTS = {'ten': {'train':224,'dev':81}, 'fresh':{'train':78,'dev':27},
                     'raw':{'train':136,'dev':44}}
_UNRESOLVED = re.compile(r'\$[A-Za-z_{]|%[A-Za-z_][A-Za-z0-9_]*%|<[^>]+>')


def _expand(value):
    if isinstance(value, dict): return {k:_expand(v) for k,v in value.items()}
    if isinstance(value, list): return [_expand(v) for v in value]
    if not isinstance(value, str): return value
    expanded = os.path.expandvars(value)
    _require(not _UNRESOLVED.search(expanded), 'unresolved040 configuration variable or placeholder: '+value)
    return expanded


def _path(base, value, *, preserve_entry=False):
    value = Path(_expand(value)).expanduser()
    joined = value if value.is_absolute() else base/value
    # A native venv interpreter may be a symlink to a different environment.
    return os.path.abspath(joined) if preserve_entry else str(joined.resolve())


def _original(config_path):
    """Same strict035 contract, with040-only environment path expansion."""
    path=Path(config_path); cfg=_expand(read_json(path))
    fields={'format','manifest','benchmark_root','stats_path','stats_sha256','unnorm_key','recipe','native_backend','bindings'}
    _require(set(cfg)==fields and cfg['format']==ORIGINAL_CONFIG and cfg['recipe']==ORIGINAL_RECIPE,
             'unchanged original035 generation configuration required')
    for key in ('manifest','benchmark_root','stats_path'): cfg[key]=_path(path.parent,cfg[key])
    native=cfg['native_backend']; _require(native.get('kind')=='native','original native backend required')
    if 'historical_root' in native: native['historical_root']=_path(path.parent,native['historical_root'])
    if 'python' in native: native['python']=_path(path.parent,native['python'],preserve_entry=True)
    if 'module_paths' in native: native['module_paths']=[_path(path.parent,v) for v in native['module_paths']]
    legacy=native.get('native',{})
    for obj,key in ((legacy,'bddl_root'),(legacy.get('core',{}),'root')):
        if key in obj: obj[key]=_path(path.parent,obj[key])
    if 'asset_roots' in legacy: legacy['asset_roots']={k:_path(path.parent,v) for k,v in legacy['asset_roots'].items()}
    manifest=read_json(cfg['manifest']); parents=validate_seeds(manifest)
    root=_path(Path(cfg['manifest']).parent,manifest['data_root'])
    _require(len(parents)==180 and len({p['source_id'] for p in parents})==180
             and sorted(Counter(p['task_key'] for p in parents).values())==[20]*9,
             'complete original180 nine-task first20 metadata required')
    _require(Counter(p['split'] for p in parents)==_BASE_POOL_COUNTS['raw'],
             'original180 train/dev split differs')
    bindings=cfg['bindings']; _require(isinstance(bindings,dict),'explicit original native bindings required')
    _require(not set(bindings)-{p['source_id'] for p in parents}-{p['task_key'] for p in parents},'foreign native binding')
    for parent in parents:
        binding=deepcopy(parent.get('native_binding',bindings.get(parent['source_id'],bindings.get(parent['task_key']))))
        _require(binding is not None,'original native source binding missing')
        validate_binding(parent,binding)
        for key in ('official_task_name','active_goals','invariant_predicates'):
            _require(binding.get(key)==parent[key],'original native task binding differs')
        parent['native_binding']=binding
        for field in ('action_normalization','proprio_normalization'):
            norm=parent['mapping'][field]
            _require(norm['stats_sha256']==cfg['stats_sha256'] and norm['stats_id']==cfg['unnorm_key'],
                     'original statistics identity differs')
    return cfg, manifest, parents, root


def _sealed(directory, context, names=('sources.json','report.json')):
    source,report=(read_json(directory/name) for name in names)
    _require(identity(source)==source.get('identity')==report.get('sources_identity')
             and identity(report)==report.get('identity'),'old039 metadata identity differs')
    return source,report


def _baseline(cfg, parents, root, context):
    directory=Path(cfg['old_task_control_index'])
    control,report=_sealed(directory,context)
    seal=read_json(directory/'identity.json')
    _require(control.get('format')=='task039-task-control-sources-v1'
             and report.get('data_kind')=='task038-task-control-data-v1'
             and control['identity']==_BASE_INDEX_IDENTITY and report['identity']==_BASE_REPORT_IDENTITY
             and seal=={'format':'task039-index-identity-v1','sources_identity':control['identity'],
                       'report_identity':report['identity']}, 'fixed accepted039 index/report anchor differs')
    for name in ('labels','pairs'):
        _require(control.get(name+'_sha256')==report.get(name+'_sha256'),'old039 label/pair binding differs')
        context.verify(directory/(name+'.jsonl'),control[name+'_sha256'])
    for path,digest in control.get('inputs',{}).items(): context.verify(path,digest)
    ret_dir=Path(_path(directory,control['retention_index']))
    merged_dir=Path(_path(directory,control['generated_export']))
    retention,ret_report=_sealed(ret_dir,context); merged,merged_report=_sealed(merged_dir,context)
    _require(retention.get('format')=='task039-retention-data-v1'
             and retention['identity']==control['retention_identity']
             and merged['identity']==control['merged_export_identity'], 'old039 retention/merged binding differs')
    context.verify(ret_dir/'rows.jsonl',ret_report['rows_sha256'])
    for path,digest in retention.get('inputs',{}).items(): context.verify(path,digest)
    for path,digest in merged.get('inputs',{}).items(): context.verify(path,digest)
    counts={pool:{split:sum(s['pool']==pool and s['split']==split for s in retention['sources'].values())
                       for split in ('train','dev')} for pool in ('ten','fresh','raw')}
    _require(counts==_BASE_POOL_COUNTS==ret_report.get('pool_counts')==retention.get('expected_pool_counts'),
             'old039305ten/105fresh/180raw metadata counts differ')
    _require(Path(retention['data_roots']['raw']).resolve()==Path(root).resolve(), 'old039 original raw root differs')
    fields=('source_id','parent_demo_id','source_group','split','task_key','file','file_sha256','episode','instruction','physical_ancestry')
    by_id={p['source_id']:p for p in parents}; old=retention['parents']
    _require(set(old)==set(by_id) and all(all(old[sid].get(k)==p.get(k) for k in fields)
             for sid,p in by_id.items()),'old039 complete180 parent identity/group/split differs')
    merged_parents={p['source_id']:p for p in merged['parents']}
    full_fields=fields+('mapping','controller_binding','official_task_name','active_goals','invariant_predicates')
    _require(len(merged['parents'])==180 and set(merged_parents)==set(by_id)
             and all(all(merged_parents[sid].get(k)==p.get(k) for k in full_fields)
                     for sid,p in by_id.items()),'old039 merged180 parent binding differs')
    roots=retention['allowed_generated_roots']
    _require(set(roots)=={'old003','new039'} and all(Path(p).is_absolute() for p in roots.values()),
             'old039 concrete artifact roots required')
    cfg.update(old_retention_index=str(ret_dir),old_merged_export=str(merged_dir))
    metadata={}
    for folder,names in ((directory,('sources.json','report.json','identity.json','labels.jsonl','pairs.jsonl')),
                         (ret_dir,('sources.json','report.json','rows.jsonl')),
                         (merged_dir,('sources.json','report.json'))):
        for name in names: metadata[str((folder/name).resolve())]=context.sha256(folder/name)
    protected=[root,str(directory),str(ret_dir),str(merged_dir),*roots.values()]
    return {'task_control_identity':control['identity'],'report_identity':report['identity'],
            'retention_identity':retention['identity'],'merged_identity':merged['identity'],
            'metadata_inputs':metadata,'allowed_generated_roots':deepcopy(roots),
            'old_qualification_rejudged':False}, protected


def assign_candidates(old, candidates):
    """Group complete known aliases while leaving every old record untouched."""
    candidates=deepcopy(candidates); parent={}
    def find(key):
        parent.setdefault(key,key)
        if parent[key]!=key: parent[key]=find(parent[key])
        return parent[key]
    def union(a,b):
        a,b=find(a),find(b);parent[max(a,b)]=min(a,b)
    for source in [*old,*candidates]:
        sid=source['source_id'];find(sid)
        aliases=source['group_ids']+['file-episode:'+source['file_sha256']+'#'+source['episode']]
        if source.get('trajectory_sha256'): aliases+=['trajectory:'+source['trajectory_sha256']]
        for alias in aliases: union(sid,'alias:'+alias)
    components=defaultdict(lambda:{'old':[],'new':[]})
    for kind,rows in (('old',old),('new',candidates)):
        for row in rows: components[find(row['source_id'])][kind].append(row)
    for component in components.values():
        new=component['new']; anchors=component['old']
        if not new: continue
        representative=min(new,key=lambda p:(p.get('demo_index',0),p['source_id']))['source_id']
        splits={p['split'] for p in anchors}
        digest=hashlib.sha256(('7|'+'|'.join(sorted(p['source_id'] for p in new))).encode()).hexdigest()
        split=next(iter(splits)) if len(splits)==1 else ('dev' if int(digest,16)%5==0 else 'train')
        group=min(anchors,key=lambda p:p['source_id'])['source_group'] if anchors else digest
        for source in new:
            reason=('old_split_conflict' if len(splits)>1 else 'known_old_duplicate' if anchors else
                    'sealed_new_dev' if split=='dev' else
                    'selected_new_train' if source['source_id']==representative else 'new_component_alias')
            source.update(parent_demo_id=source['source_id'],source_group=group,split=split,
                          representative_id=representative,selection_reason=reason,
                          anchored_parent_ids=sorted(p['source_id'] for p in anchors))
            if len(splits)>1: source['split']=None
    selected=[p for p in candidates if p['selection_reason']=='selected_new_train']
    return candidates,selected


def build_plan(config_path, context=None):
    """Read exact candidate shapes/attributes, never trajectory payloads or eval."""
    import h5py
    context=context if context is not None else HashContext()
    path=Path(_expand(str(config_path))).expanduser().resolve(strict=True)
    cfg=_expand(read_json(path))
    _require(set(cfg)=={'format','generation_config','old_task_control_index'} and cfg.get('format')==CONFIG,
             'explicit040 parent coverage configuration required')
    for key in ('generation_config','old_task_control_index'): cfg[key]=_path(path.parent,cfg[key])
    execution,manifest,parents,root=_original(cfg['generation_config'])
    dependencies,protected=_baseline(cfg,parents,root,context)
    dependencies['metadata_inputs'][str(path)]=context.sha256(path)
    for original_path in (cfg['generation_config'],execution['manifest']):
        dependencies['metadata_inputs'][str(original_path)]=context.sha256(original_path)
    candidates=[];progress=Progress('candidate_metadata')
    for task in TASKS:
        originals=[p for p in parents if p['task_key']==task]
        template=min(originals,key=lambda p:p['demo_index'])
        _require(len({p['file'] for p in originals})==1,'one original official HDF per040 task required')
        file=Path(root)/template['file'];context.verify(file,template['file_sha256'])
        with h5py.File(file,'r') as hdf:
            for index in range(20,40):
                source=deepcopy(template)
                for key in ('split','source_group','trajectory_sha256'): source.pop(key,None)
                source.update(source_id=Path(template['file']).as_posix()+f'#demo_{index}',
                    parent_demo_id=Path(template['file']).as_posix()+f'#demo_{index}',
                    episode=f'data/demo_{index}',demo_index=index,group_ids=[],physical_ancestry='unknown')
                group=hdf[source['episode']]
                source['length']=int(group[source['mapping']['action']].shape[0])
                _require(source['length']>0,'candidate has no recorded transitions')
                _require(_instruction(hdf,source['mapping']['instruction_binding'])==template['instruction'],
                         'candidate full original instruction differs')
                inspect_source(hdf,source)
                # Only explicit recorded duplicate evidence is used; no trajectory hash is fabricated.
                if 'group_ids' in group.attrs:
                    value=group.attrs['group_ids']
                    if isinstance(value,bytes): value=value.decode('utf-8')
                    source['group_ids']=json.loads(value) if isinstance(value,str) else list(value)
                    _require(isinstance(source['group_ids'],list) and all(isinstance(v,str) and v for v in source['group_ids']),
                             'candidate known alias metadata differs')
                if 'trajectory_sha256' in group.attrs:
                    value=group.attrs['trajectory_sha256']
                    if isinstance(value,bytes): value=value.decode('ascii')
                    _require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'invalid recorded candidate trajectory SHA')
                    source['trajectory_sha256']=value
                candidates.append(source);progress.update(completed=len(candidates),total=60,source=source['source_id'])
        context.verify(file,template['file_sha256'])
    candidates,selected=assign_candidates(parents,candidates)
    execution.update(teacher_policy=TEACHER_V2,recipe=deepcopy(RECIPE))
    result={'format':'task040-parent-coverage-plan-v1','config':cfg,'parents':deepcopy(parents)+deepcopy(candidates),
        'candidates':candidates,'sources':selected,'data_root':root,'execution_config':execution,
        'old_dependencies':dependencies,'protected_paths':list(dict.fromkeys(map(str,protected))),
        'source_range':{'start':20,'stop':40},'tasks':list(TASKS),'train_only':True,'newnormal_role':'pair_only',
        'population':{'original_parent_sources':180,'candidate_parent_sources':60,'selected_train_parents':len(selected),
            'candidate_split':dict(Counter(p['split'] or 'conflict' for p in candidates)),
            'selection_reasons':dict(Counter(p['selection_reason'] for p in candidates)),**BUDGET},
        'generator_algorithm':ALGORITHM,'teacher_policy':TEACHER_V2,
        'simulation_created':False,'model_loaded':False,'trajectory_payloads_read':False}
    result['identity']=identity(result);progress.finish(completed=60,total=60)
    return result
