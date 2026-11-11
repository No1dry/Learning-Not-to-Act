"""Sealed three-pool indices with lazy, observation-only ordinary examples."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from egrs.augmentation.data import (AugmentationDataset,_normalize,_require,
    file_sha256,identity,read_json,load_scope,_instruction)
from egrs.trajectory_augmentation.data import validate_seeds,DATA_KIND as GENERATED_KIND

CONFIG='task036-retention-index-config-v1'
DATA_KIND='task036-retention-data-v1'
POOLS=('ten','fresh','raw')
STATS_KEY='libero_10_no_noops'
STATS_SHA='6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3'
EXPECTED_COUNTS={'ten':{'train':161,'dev':60},'fresh':{'train':55,'dev':20},'raw':{'train':136,'dev':44}}
EXPECTED_PARENT_GROUPS={'ten':{'train':54,'dev':20},'fresh':{'train':55,'dev':20},'raw':{'train':136,'dev':44}}
EXPECTED_TASKS={'ten':6,'fresh':6,'raw':9}
RAW_CLAIM='same-row recorded observations only; no action timing or physical qualification claim'


def prefix_length(observation_count):
    _require(type(observation_count) is int and observation_count>0,'positive observation count required')
    return max(1,(observation_count+2)//3)


def _resolve(base,value):
    path=Path(value).expanduser()
    return (base/path).resolve() if not path.is_absolute() else path.resolve()


def _contained(root,relative):
    _require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'source path must be relative and contained')
    path=(root/relative).resolve()
    _require(path.is_relative_to(root),'source path escapes bound root')
    return path


def _obs_mapping(source,*,raw=False):
    mapping=source['mapping']
    result={key:deepcopy(mapping[key]) for key in ('images','image_transforms','proprio','proprio_normalization','processor_id','crop')}
    if raw:
        _require(result['images']==['obs/agentview_rgb','obs/eye_in_hand_rgb']
            and result['proprio']==['obs/ee_states','obs/gripper_states'],'raw same-row original camera/proprio fields required')
        result['image_transforms']=['rotate_180','rotate_180']
    norm=result['proprio_normalization']
    _require(norm['kind']=='bounds_q99' and norm['stats_id']==STATS_KEY and norm['stats_sha256']==STATS_SHA,
             'original036 proprio normalization binding required')
    return result


def _observation_count(path,source,mapping,*,fresh):
    """Inspect only observation shapes/dtypes and language metadata."""
    import h5py
    with h5py.File(path,'r') as hdf:
        group=hdf[source['episode']];lengths=[]
        for field in mapping['images']:
            values=group[field]
            _require(values.ndim==4 and values.shape[-1]==3 and values.dtype==np.uint8,
                     'observation images require uint8 TxHxWx3')
            lengths.append(len(values))
        width=0
        for field in mapping['proprio']:
            values=group[field]
            _require(values.ndim==2 and np.issubdtype(values.dtype,np.number),'observation proprio must be numeric TxD')
            width+=values.shape[1];lengths.append(len(values))
        _require(width==8 and min(lengths)>0 and len(set(lengths))==1,
                 'same-row observation image/proprio lengths or width differ')
        if fresh:_require(lengths[0]==source['length']+1,'fresh observations must retain existing T+1 length')
        _require(_instruction(hdf,source['mapping']['instruction_binding'])==source['instruction'],
                 'original full instruction differs from bound observations')
        return lengths[0]


def _write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def build_index(config_path,output_dir):
    """Bind existing data only; never execute an environment or a policy."""
    output=Path(output_dir)
    if output.exists():raise FileExistsError('new036 data index directory required')
    config_path=Path(config_path).resolve();cfg=read_json(config_path)
    _require(set(cfg)=={'format','generated_export','seed_manifest'} and cfg['format']==CONFIG,
             'explicit036 retention index configuration required')
    generated=_resolve(config_path.parent,cfg['generated_export']);seed_path=_resolve(config_path.parent,cfg['seed_manifest'])
    seeds=read_json(seed_path);parents=validate_seeds(seeds);by_parent={p['source_id']:p for p in parents}
    raw_root=_resolve(seed_path.parent,seeds['data_root'])
    original=read_json(generated/'sources.json');old_report=read_json(generated/'report.json')
    _require(original.get('format')==GENERATED_KIND and old_report.get('data_kind')==GENERATED_KIND
        and identity(original)==original.get('identity')==old_report.get('sources_identity')
        and identity(old_report)==old_report.get('identity')
        and file_sha256(generated/'windows.jsonl')==old_report.get('windows_sha256'),
        'existing035 generated export identity differs')
    generated_parents={p['source_id']:p for p in original['parents']}
    _require(set(generated_parents)==set(by_parent),'raw and fresh must share the original complete parent set')
    parent_fields=('source_id','parent_demo_id','source_group','split','task_key','instruction','file_sha256','episode','mapping','physical_ancestry')
    for sid,p in by_parent.items():
        _require(all(generated_parents[sid].get(k)==p.get(k) for k in parent_fields),
                 'raw/fresh parent identity, mapping or split differs')
    roots={'raw':str(raw_root),'generated':str(Path(original['data_root']).resolve())}
    sources={};rows=[];checked={}
    def bind(source,pool,root_key):
        p=by_parent.get(source.get('parent_demo_id',source['source_id']))
        _require(p is not None and source['split']==p['split'] and source['task_key']==p['task_key']
            and source['instruction']==p['instruction'],'source parent/split/full language differs')
        if pool!='raw':
            _require(source.get('source_group')==p['source_group'] and source.get('qualified') is True
                and source.get('status')=='completed' and source.get('qualification',{}).get('accepted') is True
                and source.get('parent_file_sha256')==p['file_sha256'],'fresh source must retain original qualified parent evidence')
            for field in ('images','image_transforms','proprio','action','axis_order','axis_sign','gripper',
                          'action_normalization','proprio_normalization','processor_id','crop','instruction_binding'):
                _require(source['mapping'][field]==p['mapping'][field],'fresh source original mapping differs: '+field)
        mapping=_obs_mapping(source,raw=pool=='raw')
        root=Path(roots[root_key]);path=_contained(root,source['file'])
        if path not in checked:checked[path]=file_sha256(path)
        _require(checked[path]==source['file_sha256'],'bound source HDF bytes differ')
        n=_observation_count(path,source,mapping,fresh=pool!='raw')
        sid=pool+'|'+source['source_id']
        _require(sid not in sources,'duplicate retention source')
        record={'source_id':sid,'pool':pool,'root_key':root_key,'file':source['file'],'file_sha256':source['file_sha256'],
            'episode':source['episode'],'parent_demo_id':p['source_id'],'source_group':p['source_group'],'split':p['split'],
            'task_key':p['task_key'],'instruction':p['instruction'],'physical_ancestry':p['physical_ancestry'],
            'variant':source.get('variant','recorded'),'observation_count':n,'observation_mapping':mapping,
            'provenance':'official_recorded_observation' if pool=='raw' else source['provenance'],
            'observation_basis':RAW_CLAIM if pool=='raw' else 'current observation from existing qualified fresh T+1/T execution'}
        if pool=='ten':
            norm=source['mapping']['action_normalization']
            _require(norm['stats_id']==STATS_KEY and norm['stats_sha256']==STATS_SHA,'original036 expert action statistics binding required')
            record['original_source']=deepcopy(source)
        sources[sid]=record
        return sid,n
    generated_ids={}
    for source in original['sources'].values():
        _require(source.get('domain') in {'10','normal'},'foreign generated training source')
        pool='ten' if source['domain']=='10' else 'fresh'
        sid,n=bind(source,pool,'generated');generated_ids[source['source_id']]=sid
        if pool=='fresh':
            for i in range(n):rows.append(_row(sources[sid],i))
    ten_seen={sid:set() for sid,s in sources.items() if s['pool']=='ten'}
    for line in (generated/'windows.jsonl').read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        old=json.loads(line);sid=generated_ids.get(old['source_id'])
        _require(sid is not None,'generated window has foreign source')
        if sources[sid]['pool']!='ten':continue
        source=sources[sid];p=by_parent[source['parent_demo_id']];expert=source['original_source']
        start,stop=old['start'],old['stop'];T=expert['length']
        _require(type(start) is int and 0<=start<T and stop==min(start+8,T)
            and old['action_mask']==[i<stop-start for i in range(8)]
            and old['split']==p['split'] and old['task_key']==p['task_key']
            and old['parent_demo_id']==p['source_id'] and old['instruction']==p['instruction'],
            'existing expert chunk/tail/parent binding differs')
        _require(start not in ten_seen[sid],'duplicate expert observation window')
        ten_seen[sid].add(start)
        rows.append({**deepcopy(old),**_row(source,start),'original_row':deepcopy(old)})
    _require(all(seen==set(range(sources[sid]['original_source']['length'])) for sid,seen in ten_seen.items()),
             'expert pool must retain every existing supervised window')
    for parent in parents:
        sid,n=bind(parent,'raw','raw')
        for i in range(n):rows.append(_row(sources[sid],i))
    counts={pool:{split:sum(s['pool']==pool and s['split']==split for s in sources.values())
        for split in ('train','dev')} for pool in POOLS}
    groups={pool:{split:len({s['source_group'] for s in sources.values() if s['pool']==pool and s['split']==split})
        for split in ('train','dev')} for pool in POOLS}
    tasks={pool:len({s['task_key'] for s in sources.values() if s['pool']==pool}) for pool in POOLS}
    _require(counts==EXPECTED_COUNTS and groups==EXPECTED_PARENT_GROUPS and tasks==EXPECTED_TASKS,
             'retention pools differ from approved original sources/counts/groups/tasks')
    parent_keys=('source_id','parent_demo_id','source_group','split','task_key','file','file_sha256','episode','instruction','physical_ancestry')
    manifest={'format':DATA_KIND,'data_roots':roots,'parents':{p['source_id']:{k:deepcopy(p[k]) for k in parent_keys} for p in parents},
        'sources':sources,'inputs':{str(path):file_sha256(path) for path in
            (seed_path,generated/'sources.json',generated/'windows.jsonl',generated/'report.json')},
        'statistics':{'key':STATS_KEY,'sha256':STATS_SHA}}
    manifest['identity']=identity(manifest)
    windows=''.join(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n' for row in rows)
    report={'data_kind':DATA_KIND,'pool_counts':counts,'parent_groups':groups,'task_counts':tasks,
        'pools':{pool:{split:{'sources':counts[pool][split],'parent_groups':groups[pool][split],
            'windows':sum(r['pool']==pool and r['split']==split for r in rows)} for split in ('train','dev')} for pool in POOLS},
        'all_unique_parent_groups':len({p['source_group'] for p in parents}),'rows':len(rows),
        'sources_identity':manifest['identity'],'rows_sha256':hashlib.sha256(windows.encode()).hexdigest(),
        'raw_qualification_claim':RAW_CLAIM,'prefix_rule':'first max(1,ceil(T_obs/3)) current observations; full bin includes prefix',
        'simulation_created':False,'model_loaded':False,'teacher_called':False}
    report['identity']=identity(report);output.mkdir(parents=True)
    _write(output/'sources.json',manifest);_write(output/'report.json',report)
    (output/'rows.jsonl').write_bytes(windows.encode('utf-8'))
    return report


def _row(source,index):
    return {key:deepcopy(source[key]) for key in ('source_id','pool','task_key','parent_demo_id','source_group','variant','split','instruction')}|{
        'observation_index':index,'observation_count':source['observation_count'],
        'prefix':index<prefix_length(source['observation_count'])}


class RetentionDataset:
    """Pool metadata stays offline; items expose only original policy inputs."""
    def __init__(self,export_dir,split=None,pools=None):
        directory=Path(export_dir);self.manifest=read_json(directory/'sources.json');self.report=read_json(directory/'report.json')
        _require(self.manifest.get('format')==DATA_KIND and self.report.get('data_kind')==DATA_KIND
            and identity(self.manifest)==self.manifest.get('identity')==self.report.get('sources_identity')
            and identity(self.report)==self.report.get('identity')
            and file_sha256(directory/'rows.jsonl')==self.report.get('rows_sha256'),'retention index identity differs')
        _require(split in (None,'train','dev'),'unknown retention split')
        pools=set(POOLS if pools is None else pools);_require(pools<=set(POOLS),'unknown retention pool')
        self.sources=self.manifest['sources']
        self.rows=[row for line in (directory/'rows.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()
            for row in [json.loads(line)] if row['pool'] in pools and (split is None or row['split']==split)]
        for path,digest in self.manifest['inputs'].items():
            _require(file_sha256(path)==digest,'original retention input metadata bytes changed')
        checked={}
        for sid in {r['source_id'] for r in self.rows}:
            source=self.sources[sid];path=self._path(source)
            if path not in checked:checked[path]=file_sha256(path)
            _require(checked[path]==source['file_sha256'],'retention source HDF bytes changed')

    def _path(self,source):return _contained(Path(self.manifest['data_roots'][source['root_key']]),source['file'])
    def __len__(self):return len(self.rows)

    def validate_normalization(self,stats,unnorm_key,stats_sha256):
        _require(unnorm_key==STATS_KEY and stats_sha256==STATS_SHA and unnorm_key in stats,
                 '036 requires its fixed original SOG10 normalization identity')
        original=stats[unnorm_key]
        for source in self.sources.values():
            norms={'proprio':source['observation_mapping']['proprio_normalization']}
            if source['pool']=='ten':norms['action']=source['original_source']['mapping']['action_normalization']
            for field,norm in norms.items():
                _require(norm['stats_id']==unnorm_key and norm['stats_sha256']==stats_sha256,'source original statistics identity differs')
                for key in ('q01','q99','mask'):
                    expected=original.get(field,{}).get(key,[True]*len(norm['mask']) if key=='mask' else None)
                    _require(np.array_equal(norm[key],expected),'source original normalization values differ: '+field+'.'+key)

    def __getitem__(self,index):
        row=self.rows[index];source=self.sources[row['source_id']]
        if source['pool']=='ten':
            original=source['original_source'];oldrow=row['original_row']
            view=SimpleNamespace(manifest={'data_root':self.manifest['data_roots'][source['root_key']]},
                sources={original['source_id']:original},rows=[oldrow])
            return AugmentationDataset.__getitem__(view,0)
        import h5py
        mapping=source['observation_mapping'];i=row['observation_index']
        with h5py.File(self._path(source),'r') as hdf:
            group=hdf[source['episode']]
            images=[np.asarray(group[key][i]) for key in mapping['images']]
            proprio=np.concatenate([np.asarray(group[key][i],dtype=np.float32) for key in mapping['proprio']])
        images=[im[::-1,::-1].copy() if transform=='rotate_180' else im for im,transform in zip(images,mapping['image_transforms'])]
        _require(proprio.shape==(8,) and np.isfinite(proprio).all(),'same-row finite original proprio8 required')
        proprio=_normalize(proprio,mapping['proprio_normalization'])
        if mapping['proprio_normalization']['kind']=='bounds_q99':proprio=np.clip(proprio,-1,1)
        return {'images':images,'proprio':proprio,'instruction':row['instruction']}
