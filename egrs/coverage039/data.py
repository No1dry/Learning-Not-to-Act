"""Dynamic Task039 three-pool indices; original036 remains strict."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from egrs.augmentation.data import _require,identity,read_json
from egrs.retention import data as original
from egrs.task_control.data import TaskControlDataset
from .io import HashContext,Progress
from .merge import read_merged,_write,_lines

RETENTION_KIND='task039-retention-data-v1'
SOURCES_KIND='task039-task-control-sources-v1'
_RAW_COUNTS={'train':136,'dev':44}


def _counts(sources):
    return {pool:{split:sum(s['pool']==pool and s['split']==split for s in sources.values())
                  for split in ('train','dev')} for pool in original.POOLS}


def _old_retention(directory,context):
    directory=Path(directory).resolve()
    manifest,report=(read_json(directory/name) for name in ('sources.json','report.json'))
    _require(manifest.get('format')==original.DATA_KIND and report.get('data_kind')==original.DATA_KIND
             and identity(manifest)==manifest.get('identity')==report.get('sources_identity')
             and identity(report)==report.get('identity'),'original036 retention identity differs')
    context.verify(directory/'rows.jsonl',report['rows_sha256'])
    for path,digest in manifest['inputs'].items():context.verify(path,digest)
    _require(manifest.get('statistics')=={'key':original.STATS_KEY,'sha256':original.STATS_SHA},
             'original036 fixed statistics identity differs')
    for source in manifest['sources'].values():
        context.verify(original._contained(Path(manifest['data_roots'][source['root_key']]).resolve(),source['file']),source['file_sha256'])
    return manifest,report,_lines(directory/'rows.jsonl')


def build_retention_index(merged_export,old_retention_index,output_dir,context=None):
    context=context or HashContext();output=Path(output_dir).resolve()
    if output.exists():raise FileExistsError('new039 retention index directory required')
    merged,merged_report,generated_rows=read_merged(merged_export,context)
    old,_,old_rows=_old_retention(old_retention_index,context)
    parents={p['source_id']:p for p in merged['parents']}
    fields=('source_id','parent_demo_id','source_group','split','task_key','file','file_sha256','episode','instruction','physical_ancestry')
    _require(set(parents)==set(old['parents']) and all(all(old['parents'][sid][k]==p[k] for k in fields)
             for sid,p in parents.items()),'raw original180 parent path/group/split identity differs')
    _require(Path(old['data_roots']['generated']).resolve()==Path(merged['allowed_data_roots']['old003']).resolve(),
             'old003 retention generated root differs')
    old_sources={sid:s for sid,s in merged['sources'].items() if s['coverage039_origin']['release']=='old003'}
    _require({s['source_id'] for s in old['sources'].values() if s['pool']!='raw'}=={
        ('fresh|' if s['domain']=='normal' else 'ten|')+s['coverage039_origin']['source_id'] for s in old_sources.values()},
        'old003 qualified source retention differs')
    for source in old_sources.values():
        origin=source['coverage039_origin'];pool='fresh' if source['domain']=='normal' else 'ten'
        kept=old['sources'][pool+'|'+origin['source_id']];before=origin['original_source']
        _require(all(kept[k]==before[k] for k in ('file','file_sha256','episode','parent_demo_id','source_group','split','task_key','instruction')),
                 'reused old003 retained teacher source differs')
        if 'original_source' in kept:_require(kept['original_source']==before,'old003 teacher/qualification evidence differs')
    roots={'raw':str(Path(old['data_roots']['raw']).resolve()),'generated':merged['data_root']}
    sources={sid:deepcopy(s) for sid,s in old['sources'].items() if s['pool']=='raw'}
    _require(_counts(sources)['raw']==_RAW_COUNTS,'original raw136train/44dev parents must remain unchanged')
    rows=[deepcopy(r) for r in old_rows if r['pool']=='raw']
    _require({s['parent_demo_id'] for s in sources.values()}==set(parents),'original raw parent set differs')
    progress=Progress('retention_metadata');total=len(merged['sources'])
    for gid,source in merged['sources'].items():
        parent=parents[source['parent_demo_id']];pool='ten' if source['domain']=='10' else 'fresh'
        for key in ('images','image_transforms','proprio','action','axis_order','axis_sign','gripper',
                    'action_normalization','proprio_normalization','processor_id','crop','instruction_binding'):
            _require(source['mapping'][key]==parent['mapping'][key],'039 original source mapping differs: '+key)
        mapping=original._obs_mapping(source)
        path=original._contained(Path(roots['generated']),source['file']);context.verify(path,source['file_sha256'])
        n=original._observation_count(path,source,mapping,fresh=True)
        sid=pool+'|'+gid
        record={'source_id':sid,'pool':pool,'root_key':'generated','file':source['file'],
                'file_sha256':source['file_sha256'],'episode':source['episode'],
                'parent_demo_id':parent['source_id'],'source_group':parent['source_group'],
                'split':parent['split'],'task_key':parent['task_key'],'instruction':parent['instruction'],
                'physical_ancestry':parent['physical_ancestry'],'variant':source['variant'],
                'observation_count':n,'observation_mapping':mapping,'provenance':source['provenance'],
                'observation_basis':'current observation from qualified executed T+1/T trajectory',
                'original_source':deepcopy(source)}
        if pool=='ten':
            norm=source['mapping']['action_normalization']
            _require(norm['stats_id']==original.STATS_KEY and norm['stats_sha256']==original.STATS_SHA,
                     'original SOG10 expert action statistics binding required')
        sources[sid]=record
        if pool=='fresh':rows.extend(original._row(record,i) for i in range(n))
        progress.update(source=gid,completed=sum(s['pool']!='raw' for s in sources.values()),total=total)
    for row in generated_rows:
        if merged['sources'][row['source_id']]['domain']!='10':continue
        sid='ten|'+row['source_id'];record=sources[sid]
        rows.append({**deepcopy(row),**original._row(record,row['start']),'original_row':deepcopy(row)})
    inputs={**old['inputs'],**merged['inputs']}
    for directory,filenames in ((Path(merged_export),('sources.json','report.json','windows.jsonl')),
                                 (Path(old_retention_index),('sources.json','report.json','rows.jsonl'))):
        for name in filenames:inputs[str((directory/name).resolve())]=context.sha256(directory/name)
    counts=_counts(sources)
    groups={pool:{split:len({s['source_group'] for s in sources.values() if s['pool']==pool and s['split']==split})
                  for split in ('train','dev')} for pool in original.POOLS}
    coverage=deepcopy(merged['coverage039'])
    manifest={'format':RETENTION_KIND,'data_roots':roots,'allowed_generated_roots':deepcopy(merged['allowed_data_roots']),
              'parents':deepcopy(old['parents']),'sources':sources,'inputs':inputs,'statistics':deepcopy(old['statistics']),
              'merged_export':str(Path(merged_export).resolve()),'merged_identity':merged['identity'],
              'old_retention_index':str(Path(old_retention_index).resolve()),
              'old_retention_identity':old['identity'],'expected_pool_counts':counts,'coverage039':coverage}
    manifest['identity']=identity(manifest)
    content=''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows).encode('utf-8')
    report={'data_kind':RETENTION_KIND,'sources_identity':manifest['identity'],'rows_sha256':hashlib.sha256(content).hexdigest(),
            'pool_counts':counts,'parent_groups':groups,
            'task_counts':{pool:len({s['task_key'] for s in sources.values() if s['pool']==pool}) for pool in original.POOLS},
            'rows':len(rows),'coverage039':deepcopy(coverage),'raw_qualification_claim':original.RAW_CLAIM,
            'pools':{pool:{split:{'sources':counts[pool][split],'parent_groups':groups[pool][split],
                'windows':sum(r['pool']==pool and r['split']==split for r in rows)} for split in ('train','dev')} for pool in original.POOLS},
            'all_unique_parent_groups':len({p['source_group'] for p in parents.values()}),
            'simulation_created':False,'model_loaded':False,'teacher_called':False}
    report['identity']=identity(report);output.mkdir(parents=True)
    _write(output/'sources.json',manifest);_write(output/'report.json',report);(output/'rows.jsonl').write_bytes(content)
    progress.finish(completed=total,total=total)
    return report


class CoverageRetentionDataset(original.RetentionDataset):
    def __init__(self,export_dir,split=None,pools=None,context=None):
        context=context or HashContext();directory=Path(export_dir).resolve()
        self.manifest,self.report=(read_json(directory/name) for name in ('sources.json','report.json'))
        _require(self.manifest.get('format')==self.report.get('data_kind')==RETENTION_KIND
                 and identity(self.manifest)==self.manifest.get('identity')==self.report.get('sources_identity')
                 and identity(self.report)==self.report.get('identity'),'039 retention index identity differs')
        context.verify(directory/'rows.jsonl',self.report['rows_sha256'])
        _require(split in (None,'train','dev'),'unknown039 retention split')
        selected=set(original.POOLS if pools is None else pools)
        _require(selected<=set(original.POOLS),'unknown039 retention pool')
        for path,digest in self.manifest['inputs'].items():context.verify(path,digest)
        merged,_,generated_rows=read_merged(self.manifest['merged_export'],context)
        _require(merged['identity']==self.manifest['merged_identity']
                 and merged['allowed_data_roots']==self.manifest['allowed_generated_roots']
                 and merged['coverage039']==self.manifest['coverage039']==self.report['coverage039'],
                 '039 merged source contract differs')
        self.sources=self.manifest['sources'];all_rows=_lines(directory/'rows.jsonl')
        old_directory=Path(self.manifest['old_retention_index']).resolve()
        old=read_json(old_directory/'sources.json')
        _require(identity(old)==old.get('identity')==self.manifest['old_retention_identity']
                 and self.manifest['parents']==old['parents']
                 and self.manifest['data_roots']['raw']==old['data_roots']['raw'],
                 'original raw parent/root identity differs')
        for name in ('sources.json','report.json','rows.jsonl'):
            path=str((old_directory/name).resolve())
            _require(path in self.manifest['inputs'],'original retention metadata binding missing')
            context.verify(path,self.manifest['inputs'][path])
        _require({sid:s for sid,s in self.sources.items() if s['pool']=='raw'}
                 =={sid:s for sid,s in old['sources'].items() if s['pool']=='raw'}
                 and [r for r in all_rows if r['pool']=='raw']
                 ==[r for r in _lines(old_directory/'rows.jsonl') if r['pool']=='raw'],
                 'original raw source/observation rows differ')
        counts=_counts(self.sources)
        _require(counts==self.manifest['expected_pool_counts']==self.report['pool_counts']
                 and counts['raw']==_RAW_COUNTS,'039 actual qualified/raw pool counts differ')
        _require(self.manifest['statistics']=={'key':original.STATS_KEY,'sha256':original.STATS_SHA},
                 '039 original normalization identity differs')
        expected_ids={('ten|' if s['domain']=='10' else 'fresh|')+gid for gid,s in merged['sources'].items()}
        _require({sid for sid,s in self.sources.items() if s['pool']!='raw'}==expected_ids,
                 '039 qualified source set differs')
        seen=set()
        outgoing={(r['source_id'],r['start']):r for r in generated_rows}
        for row in all_rows:
            source=self.sources.get(row.get('source_id'));i=row.get('observation_index')
            _require(source is not None and type(i) is int and 0<=i<source['observation_count']
                     and all(row.get(k)==source[k] for k in ('pool','task_key','parent_demo_id','source_group','variant','split','instruction','observation_count'))
                     and row.get('prefix')==(i<original.prefix_length(source['observation_count'])),
                     '039 retention observation binding differs')
            _require((source['source_id'],i) not in seen,'duplicate039 retention row');seen.add((source['source_id'],i))
            if source['pool']=='ten':
                gid=source['source_id'].split('|',1)[1]
                _require(row.get('original_row')==outgoing.get((gid,i)),
                         '039 expert own outgoing action row differs')
        expected_rows={(sid,i) for sid,s in self.sources.items()
                       for i in range(s['observation_count']-(s['pool']=='ten'))}
        _require(seen==expected_rows,'039 retention complete observations differ')
        for source in self.sources.values():
            parent=self.manifest['parents'].get(source['parent_demo_id'])
            _require(parent is not None and all(source[k]==parent[k] for k in ('source_group','split','task_key','instruction','physical_ancestry')),
                     '039 retention original parent/split differs')
            if source['pool']!='raw':
                gid=source['source_id'].split('|',1)[1]
                _require(source.get('original_source')==merged['sources'][gid], '039 retained original qualified source differs')
                _require(source['observation_mapping']==original._obs_mapping(merged['sources'][gid]),
                         '039 original observation mapping differs')
            context.verify(self._path(source),source['file_sha256'])
        self.rows=[r for r in all_rows if r['pool'] in selected and (split is None or r['split']==split)]

    def _path(self,source):
        path=original._contained(Path(self.manifest['data_roots'][source['root_key']]).resolve(),source['file'])
        if source['pool']!='raw':
            origin=source['original_source']['coverage039_origin']['release']
            root=Path(self.manifest['allowed_generated_roots'][origin]).resolve()
            _require(source['root_key']=='generated' and path.is_relative_to(root)
                     and source['file']==source['original_source']['file'],'039 generated source escapes allowlisted root')
        else:
            parent=self.manifest['parents'][source['parent_demo_id']]
            _require(source['root_key']=='raw' and source['file']==parent['file']
                     and source['file_sha256']==parent['file_sha256'],'039 raw parent HDF path identity differs')
        return path


# The public039 name deliberately cannot be consumed through the036 reader.
RetentionDataset=CoverageRetentionDataset


class CoverageTaskControlDataset(TaskControlDataset):
    def __init__(self,index_dir,split='train',context=None):
        from .index import read_index
        _require(split in ('train','dev'),'unknown039 task-control split')
        context=context or HashContext()
        self.manifest,self.report,labels,pairs=read_index(index_dir,context=context)
        self.identity=self.manifest['identity']
        self.retention=CoverageRetentionDataset(self.manifest['retention_index'],split=split,context=context)
        _require(self.retention.manifest['identity']==self.manifest['retention_identity'],
                 '039 retention identity differs')
        _require(self.retention.manifest['coverage039']==self.report['coverage039'], '039 coverage count contract differs')
        self.rows=self.retention.rows;self.sources=self.retention.sources
        self.pairs=[p for p in pairs if p['split']==split]
        self._labels={(r['source_id'],r['observation_index']):r['count_label'] for r in labels}
        _require(all((r['source_id'],r['observation_index']) in self._labels for r in self.rows),
                 '039 count label row binding missing')
