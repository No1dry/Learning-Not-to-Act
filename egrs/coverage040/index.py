"""Append-only040 supervision; accepted039 recordings are immutable inputs."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from egrs.augmentation.data import _require, identity, read_json, load_scope
from egrs.retention import data as retention
from egrs.retention.training import dev_indices
from egrs.task_control.index import DATA_KIND, _semantics, _active_values, _shape, _pair_check
from egrs.task_control.sampling import dev_pair_indices
from egrs.coverage039.data import CoverageRetentionDataset
from egrs.coverage039.index import read_index as read_old_index
from egrs.coverage039.io import HashContext, Progress
from egrs.coverage039.merge import _load_export, _validate_new_transform, _lines, _write
from egrs.coverage039.recipe import TASKS, ALGORITHM, RECIPE_VERSION, generation_context, recipe_for
from egrs.trajectory_augmentation.native import TEACHER_V2

SOURCES_KIND = 'task040-task-control-sources-v1'
RETENTION_KIND = 'task040-retention-data-v1'
IDENTITY_KIND = 'task040-index-identity-v1'
ALGORITHM_CONTRACT = 'task038-recorded-active-state-count-and-pair-v1'
# Only synthetic tests override these private anchors; production has no opt-out.
_OLD_INDEX_IDENTITY = 'b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c'
_OLD_REPORT_IDENTITY = '64a2d4923dda271ffeb2a67f080c81c40bbdb277bae6351328a779791e1abdaf'
_OLD_COUNTS = {'ten':{'train':224,'dev':81},'fresh':{'train':78,'dev':27},'raw':{'train':136,'dev':44}}
_OLD_PAIR_COUNTS = {'train':224,'dev':81}


def _bytes(rows):
    return ''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows).encode('utf-8')


def _append(path, rows):
    prefix=Path(path).read_bytes()
    return prefix+(b'\n' if prefix and not prefix.endswith(b'\n') and rows else b'')+_bytes(rows)


def _counts(sources):
    return {pool:{split:sum(s['pool']==pool and s['split']==split for s in sources.values())
                  for split in ('train','dev')} for pool in retention.POOLS}


def _selection(rows,pairs):
    """Store source/observation keys, never only the incidental row numbers."""
    rows=[r for r in rows if r['split']=='dev']
    pairs=[p for p in pairs if p['split']=='dev']
    selected=dev_indices(rows,seed=7)
    def keys(indices):return [[rows[i]['source_id'],rows[i]['observation_index']] for i in indices]
    return {'ten':keys(selected['ten']),
            **{p:{b:keys(selected[p][b]) for b in ('prefix','all')} for p in ('fresh','raw')},
            'pairs':[pairs[i]['pair_id'] for i in dev_pair_indices(pairs,seed=7)]}


def _task_coverage(old_sources,new_sources,old_rows,new_rows,old_pairs,new_pairs,buckets):
    table={}
    for task in (t['key'] for t in load_scope()['tasks']):
        previous=[s for s in old_sources.values() if s['pool']=='ten' and s['task_key']==task]
        added=[s for s in new_sources.values() if s['task_key']==task]
        entry={}
        for name,before,after in (('ten',previous,added),
                ('ten_windows',[r for r in old_rows if r['pool']=='ten' and r['task_key']==task],
                               [r for r in new_rows if r['task_key']==task]),
                ('pairs',[p for p in old_pairs if p['task_key']==task],
                         [p for p in new_pairs if p['task_key']==task])):
            counts=[{split:sum(s['split']==split for s in items) for split in ('train','dev')}
                    for items in (before,after)]
            entry[name]={'old':counts[0],'new':counts[1],
                         'total':{s:counts[0][s]+counts[1][s] for s in ('train','dev')}}
        groups=[{s['source_group'] for s in items if s['split']=='train'} for items in (previous,added)]
        entry['train_parent_groups']={'old':len(groups[0]),'new':len(groups[1]),'total':len(groups[0]|groups[1])}
        entry['pair_gaps']=deepcopy(buckets.get(task,{}).get('reasons',{}));table[task]=entry
    return table


def _binding(delta,old_parents,context,inputs):
    binding=delta.get('generation_context',{}).get('coverage040',{})
    _require(binding.get('format')=='task040-generation-binding-v1'
             and binding.get('tasks')==list(TASKS)
             and binding.get('source_range')=={'start':20,'stop':40}
             and binding.get('train_only') is True and binding.get('newnormal_role')=='pair_only',
             'explicit040 fixed-range/train-only/pair-only generation binding required')
    for name in ('plan','ledger'):
        path=Path(binding.get(name+'_path',''))
        _require(path.is_absolute(),'040 '+name+' path must be explicit and absolute')
        context.verify(path,binding.get(name+'_sha256'));inputs[str(path.resolve())]=binding[name+'_sha256']
    plan=read_json(binding['plan_path']);ledger=read_json(binding['ledger_path'])
    _require(identity(plan)==plan.get('identity')==binding.get('plan_identity'), '040 plan identity differs')
    parents={p['source_id']:p for p in delta['parents']}
    candidates=binding.get('candidates');selected=binding.get('selected_train_parent_ids')
    _require(isinstance(candidates,list) and len(candidates)==60
             and candidates==plan.get('candidates') and delta['parents']==plan.get('parents'),
             '040 complete fixed candidate/parent metadata differs')
    expected={(task,number) for task in TASKS for number in range(20,40)};seen=set()
    for p in candidates:
        episode=p.get('episode','');number=episode.removeprefix('data/demo_')
        _require(number.isdigit() and episode=='data/demo_'+str(int(number))
                 and p['source_id']==p['file']+'#demo_'+str(int(number))
                 and p['source_id'] not in old_parents and parents.get(p['source_id'])==p,
                 '040 canonical new candidate source/range identity differs')
        seen.add((p['task_key'],int(number)))
    _require(seen==expected and len(parents)==len(old_parents)+60
             and all(parents.get(sid)==p for sid,p in old_parents.items()),
             '040 original parents changed or candidate task/range differs')
    planned=plan.get('sources',[])
    _require(isinstance(selected,list) and selected==[p['source_id'] for p in planned]
             and len(set(selected))==len(selected)
             and all(parents.get(p['source_id'])==p and p.get('split')=='train' for p in planned)
             and len({p['source_group'] for p in planned})==len(planned),
             '040 selected train representative plan differs')
    old_groups={p['source_group'] for p in old_parents.values()}
    _require(all(p['source_group'] not in old_groups for p in planned), '040 known old parent group must not regenerate')
    slots=ledger.get('slots',[])
    _require(ledger.get('format')=='task039-attempt-ledger-v1' and isinstance(slots,list)
             and type(ledger.get('normal_attempts')) is int and type(ledger.get('ten_attempts')) is int
             and 0<=ledger['normal_attempts']<=60 and 0<=ledger['ten_attempts']<=360
             and ledger['normal_attempts']==sum(s.get('domain')=='normal' for s in slots)
             and ledger['ten_attempts']==sum(s.get('domain')=='10' for s in slots),
             '040 durable attempt ledger/counts differ')
    seen_slots=set()
    for s in slots:
        key=(s.get('source_id'),s.get('domain'),s.get('variant'),s.get('attempt'))
        _require(s.get('source_id') in selected and s.get('status')=='spent_before_initialization'
                 and ((s.get('domain')=='normal' and s.get('variant')=='normal' and s.get('attempt')==0)
                      or (s.get('domain')=='10' and type(s.get('variant')) is int and s['variant'] in range(3)
                          and type(s.get('attempt')) is int and s['attempt'] in range(2)))
                 and key not in seen_slots,'040 ledger spent slot/selected parent differs')
        if s['domain']=='10':
            _require((s['source_id'],'normal','normal',0) in seen_slots,'040 normal must be spent before ten')
        seen_slots.add(key)
    expected_context=generation_context(plan['identity'],normal_attempts=ledger['normal_attempts'],ten_attempts=ledger['ten_attempts'])
    expected_context['coverage040']=binding
    _require(delta.get('generation_context')==expected_context,'040 generation algorithm/ledger context differs')
    return binding,parents,set(selected),seen_slots


def _new_records(delta,parents,selected,slots,binding,context,inputs):
    root=Path(delta['data_root']).resolve();records={};normals={};progress=Progress('040_recorded_metadata')
    scope={t['key']:t for t in load_scope()['tasks']}
    for sid,source in delta['sources'].items():
        p=parents[source['parent_demo_id']]
        _require(p['source_id'] in selected and p['split']==source['split']=='train'
                 and p['active_goals']==scope[p['task_key']]['active_goals']
                 and p['invariant_predicates']==scope[p['task_key']]['invariant_predicates'],
                 '040 qualified source must belong to a selected new train parent')
        _require(source.get('teacher_policy')==TEACHER_V2
                 and source.get('qualification',{}).get('teacher_policy')==TEACHER_V2
                 and source.get('generator_algorithm')==ALGORITHM,'040 original039 teacher/algorithm provenance differs')
        for field in ('images','image_transforms','proprio','action','axis_order','axis_sign','gripper',
                      'action_normalization','proprio_normalization','processor_id','crop','instruction_binding'):
            _require(source['mapping'][field]==p['mapping'][field],'040 original mapping/normalization differs: '+field)
        retention._obs_mapping(source)
        norm=source['mapping']['action_normalization']
        _require(norm.get('stats_id')==retention.STATS_KEY and norm.get('stats_sha256')==retention.STATS_SHA,
                 '040 original SOG10 action normalization differs')
        domain=source['domain'];variant=source['variant']
        _require(any(s[0]==p['source_id'] and s[1]==domain and s[2]==variant for s in slots),
                 '040 qualified source has no spent ledger slot')
        paths={}
        for field in ('file','audit_path','lineage_path','qualification_path','journal_path','metadata_path','video'):
            if source.get(field):
                path=retention._contained(root,source[field]);digest=context.sha256(path)
                if field=='file':_require(digest==source['file_sha256'],'040 qualified HDF bytes changed')
                inputs[str(path)]=digest;paths[field]=path
        audit=read_json(paths['audit_path']);lineage=read_json(paths['lineage_path'])
        transform=source.get('initialization_transform');recipe=source.get('recipe',{})
        episode_context=generation_context(binding['plan_identity']);episode_context['initialization_transform']=transform
        episode_context['coverage040']=binding
        _require(source.get('generation_context')==lineage.get('generation_context')==episode_context
                 and recipe.get('coverage040')==binding and lineage.get('recipe')==recipe
                 and source.get('recipe_identity')==identity(recipe)
                 and recipe.get('version')==RECIPE_VERSION and recipe.get('generator_algorithm')==ALGORITHM
                 and recipe.get('initialization_transform')==lineage.get('initialization_transform')==transform
                 and lineage.get('teacher_policy')==TEACHER_V2 and lineage.get('generator_algorithm')==ALGORITHM,
                 '040 source/lineage recipe/context provenance differs')
        recipe_for({'recipe':{k:v for k,v in recipe.items() if k not in ('initialization_transform','coverage040')}})
        frames=audit.get('frames',[])
        _require(lineage.get('source')==p and frames
                 and lineage.get('actual_initial_state')==frames[0].get('state'), '040 recorded initial state/parent differs')
        _require(_shape(paths['file'],source,audit),'040 valid T+1/T observation/action alignment required')
        if domain=='normal':
            _require(p['source_id'] not in normals,'040 multiple normal sources for one parent')
            _validate_new_transform(p,transform,frames[0]);normals[p['source_id']]=source
        records[sid]={'audit':audit,'lineage':lineage,'parent':p,'semantics':_semantics(p,lineage),
                      'shape_valid':True,'digests':{'audit':inputs[str(paths['audit_path'])],
                                                   'lineage':inputs[str(paths['lineage_path'])]}}
        progress.update(source=sid,completed=len(records),total=len(delta['sources']))
    for source in delta['sources'].values():
        normal=normals.get(source['parent_demo_id'])
        if normal is not None:
            _require(normal['initialization_transform']==source['initialization_transform'],
                     '040 ten must preserve its new normal initialization')
    progress.finish(completed=len(records),total=len(records))
    return records,normals


def _compose(old_index,delta_export,context):
    old_index=Path(old_index).resolve();delta_export=Path(delta_export).resolve()
    old,old_report,old_labels,old_pairs=read_old_index(old_index,context=context)
    _require(old['identity']==_OLD_INDEX_IDENTITY and old_report['identity']==_OLD_REPORT_IDENTITY,
             '040 requires the exact accepted039 index/report identity')
    base=CoverageRetentionDataset(old['retention_index'],context=context)
    _require(base.manifest['identity']==old['retention_identity'] and _counts(base.sources)==_OLD_COUNTS
             and {s:sum(p['split']==s for p in old_pairs) for s in ('train','dev')}==_OLD_PAIR_COUNTS,
             '040 accepted039 fixed pool/pair counts differ')
    old_generated=read_json(Path(old['generated_export'])/'sources.json')
    old_parents={p['source_id']:p for p in old_generated['parents']}
    delta,_,windows,inputs=_load_export(delta_export,context)
    inputs={**old['inputs'],**inputs}
    for directory,names in ((old_index,('sources.json','report.json','identity.json','labels.jsonl','pairs.jsonl')),
                            (Path(old['retention_index']),('sources.json','report.json','rows.jsonl'))):
        for name in names:inputs[str((directory/name).resolve())]=context.sha256(directory/name)
    binding,parents,selected,slots=_binding(delta,old_parents,context,inputs)
    records,normals=_new_records(delta,parents,selected,slots,binding,context,inputs)
    sources=deepcopy(base.sources);rows=deepcopy(base.rows);new_rows=[];new_labels=[];new_pairs=[]
    pair_sources={};new_sources={};rowmap={};windowmap={(w['source_id'],w['start']):w for w in windows}
    for sid,s in delta['sources'].items():
        p=parents[s['parent_demo_id']];rid=('pair|' if s['domain']=='normal' else 'ten|')+'new040|'+sid
        if s['domain']=='normal':
            pair_sources[rid]={'source_id':rid,'generated_source_id':sid,'data_root':delta['data_root'],
                               'source':deepcopy(s),'role':'pair_only'}
            continue
        record={'source_id':rid,'pool':'ten','root_key':'new040','file':s['file'],'file_sha256':s['file_sha256'],
                'episode':s['episode'],'parent_demo_id':p['source_id'],'source_group':p['source_group'],
                'split':'train','task_key':p['task_key'],'instruction':p['instruction'],
                'physical_ancestry':p['physical_ancestry'],'variant':s['variant'],'observation_count':s['length']+1,
                'observation_mapping':retention._obs_mapping(s),'provenance':s['provenance'],
                'observation_basis':'current observation from qualified executed T+1/T trajectory',
                'original_source':deepcopy(s)}
        _require(rid not in sources,'040 source ID collides with accepted039')
        sources[rid]=record;new_sources[rid]=deepcopy(s)
        for i in range(s['length']):
            row={**deepcopy(windowmap[sid,i]),**retention._row(record,i),'original_row':deepcopy(windowmap[sid,i])}
            new_rows.append(row);rowmap[rid,i]=row
            values=_active_values(records[sid]['audit']['frames'][i].get('facts',{}),records[sid]['semantics'])
            new_labels.append({'source_id':rid,'observation_index':i,'split':'train','pool':'ten',
                'count_label':sum(values) if values is not None else None,'label_basis':records[sid]['semantics']['basis']})
    gaps=Counter();buckets={}
    for ten in delta['sources'].values():
        if ten['domain']!='10':continue
        normal=normals.get(ten['parent_demo_id'])
        reason,evidence=('missing_qualified_normal_source',None) if normal is None else _pair_check(normal,ten,records)
        bucket=buckets.setdefault(ten['task_key'],{'candidates':0,'valid':0,'reasons':{}});bucket['candidates']+=1
        if reason:
            gaps[reason]+=1;bucket['reasons'][reason]=bucket['reasons'].get(reason,0)+1;continue
        endpoints={}
        for name,source,i in (('u',normal,evidence['handoff_index']),('v',ten,0)):
            sid=source['source_id'];rid=('pair|' if name=='u' else 'ten|')+'new040|'+sid
            original=windowmap[sid,i]
            if name=='u':
                values=_active_values(records[sid]['audit']['frames'][i].get('facts',{}),records[sid]['semantics'])
                new_labels.append({'source_id':rid,'observation_index':i,'split':'train','role':'pair_only',
                    'count_label':sum(values) if values is not None else None,'label_basis':records[sid]['semantics']['basis']})
            endpoints[name]={'source_id':rid,'generated_source_id':sid,'observation_index':i,
                'row':deepcopy(rowmap[rid,i]) if name=='v' else {'source_id':rid,'observation_index':i,'role':'pair_only'},
                'original_row':deepcopy(original),'action_mask':deepcopy(original['action_mask']),
                'file_sha256':source['file_sha256'],'audit_sha256':records[sid]['digests']['audit'],
                'lineage_sha256':records[sid]['digests']['lineage']}
        pair={k:deepcopy(ten[k]) for k in ('task_key','parent_demo_id','source_group','variant','split','instruction')}
        pair.update(endpoints);pair['evidence']=evidence;pair['pair_id']=identity(pair);new_pairs.append(pair);bucket['valid']+=1
    # Several variants may share one normal endpoint; supervision keys are unique.
    new_labels=list({(r['source_id'],r['observation_index']):r for r in new_labels}.values())
    rows+=new_rows;labels=deepcopy(old_labels)+new_labels;pairs=deepcopy(old_pairs)+new_pairs
    before=_selection(base.rows,old_pairs);after=_selection(rows,pairs)
    _require(before==after,'040 old dev source/observation/pair selection changed')
    coverage={'new_qualified_train10':len(new_sources),'new_train_pairs':len(new_pairs),'pair_gaps':dict(gaps),
        'by_task':_task_coverage(base.sources,new_sources,base.rows,new_rows,old_pairs,new_pairs,buckets),
        'new_pair_by_task':buckets,'candidate_dev_sealed':sum(p['split']=='dev' for p in binding['candidates']),
        'selected_train_parents':len(selected),'new_ten_windows':len(new_rows),'old_pool_counts':deepcopy(_OLD_COUNTS),
        'total_pool_counts':_counts(sources),'old_pair_counts':deepcopy(_OLD_PAIR_COUNTS),
        'old_dev_selection':before,'dev_selection_unchanged':True,'fresh_raw_unchanged':True,
        'old_index_identity':old['identity'],'old_report_identity':old_report['identity'],
        'delta_identity':delta['identity'],'generation_binding':deepcopy(binding)}
    main_parents=deepcopy(base.manifest['parents'])
    main_parents.update({p['source_id']:deepcopy(p) for p in binding['candidates']})
    roots={**deepcopy(base.manifest['data_roots']),'new040':str(Path(delta['data_root']).resolve())}
    ret={'format':RETENTION_KIND,'data_roots':roots,'parents':main_parents,'sources':sources,'inputs':inputs,
         'statistics':deepcopy(base.manifest['statistics']),'old_task_control_index':str(old_index),
         'delta_export':str(delta_export),'coverage040':deepcopy(coverage)}
    ret['identity']=identity(ret)
    row_bytes=_append(Path(old['retention_index'])/'rows.jsonl',new_rows)
    label_bytes=_append(old_index/'labels.jsonl',new_labels);pair_bytes=_append(old_index/'pairs.jsonl',new_pairs)
    ret_report={'data_kind':RETENTION_KIND,'sources_identity':ret['identity'],
        'rows_sha256':hashlib.sha256(row_bytes).hexdigest(),'rows':len(rows),'pool_counts':_counts(sources),
        'coverage040':deepcopy(coverage),'simulation_created':False,'model_loaded':False}
    ret_report['identity']=identity(ret_report)
    control={'format':SOURCES_KIND,'retention_identity':ret['identity'],'old_task_control_index':str(old_index),
        'delta_export':str(delta_export),'generated_data_root':old['generated_data_root'],
        'qualified_sources':deepcopy(old['qualified_sources']),'pair_sources':pair_sources,'new_sources':new_sources,
        'delta_data_root':str(Path(delta['data_root']).resolve()),'inputs':inputs,
        'labels_sha256':hashlib.sha256(label_bytes).hexdigest(),'pairs_sha256':hashlib.sha256(pair_bytes).hexdigest(),
        'algorithm_contract':ALGORITHM_CONTRACT,'coverage040':deepcopy(coverage)}
    report={'data_kind':DATA_KIND,'rows':len(rows),'available':bool(pairs),'status':'available' if pairs else 'zero valid pairs',
        'pairs':{'candidates':old_report['pairs']['candidates']+sum(v['candidates'] for v in buckets.values()),
                 'valid':len(pairs),'new_valid':len(new_pairs),'new_reasons':dict(gaps)},
        'labels':{'available':sum(r['count_label'] is not None for r in labels),
                  'missing':sum(r['count_label'] is None for r in labels)},
        'labels_sha256':control['labels_sha256'],'pairs_sha256':control['pairs_sha256'],
        'algorithm_contract':ALGORITHM_CONTRACT,'coverage040':deepcopy(coverage),
        'image_pixels_read':False,'model_loaded':False,'simulation_created':False}
    return ret,ret_report,control,report,row_bytes,label_bytes,pair_bytes


def build_indices(old_task_control_index,delta_export,out,context=None):
    context=context or HashContext();output=Path(out).resolve()
    if output.exists():raise FileExistsError('new040 indices directory required')
    for value in (old_task_control_index,delta_export):
        root=Path(value).resolve()
        _require(output!=root and root not in output.parents and output not in root.parents,
                 '040 index output overlaps immutable input')
    ret,ret_report,control,report,row_bytes,label_bytes,pair_bytes=_compose(old_task_control_index,delta_export,context)
    retention_dir=output/'retention';control_dir=output/'task_control'
    control['retention_index']=str(retention_dir);control['identity']=identity(control)
    report['sources_identity']=control['identity'];report['identity']=identity(report)
    retention_dir.mkdir(parents=True);control_dir.mkdir()
    for directory,manifest,summary in ((retention_dir,ret,ret_report),(control_dir,control,report)):
        _write(directory/'sources.json',manifest);_write(directory/'report.json',summary)
    (retention_dir/'rows.jsonl').write_bytes(row_bytes)
    (control_dir/'labels.jsonl').write_bytes(label_bytes);(control_dir/'pairs.jsonl').write_bytes(pair_bytes)
    _write(control_dir/'identity.json',{'format':IDENTITY_KIND,'sources_identity':control['identity'],
                                      'report_identity':report['identity']})
    return {'retention':str(retention_dir),'task_control':str(control_dir),
            'retention_report':ret_report,'task_control_report':report}


def read_index(directory,context=None):
    context=context or HashContext();directory=Path(directory).resolve()
    manifest,report,seal=(read_json(directory/name) for name in ('sources.json','report.json','identity.json'))
    _require(manifest.get('format')==SOURCES_KIND and report.get('data_kind')==DATA_KIND
             and seal.get('format')==IDENTITY_KIND and identity(manifest)==manifest.get('identity')
             ==report.get('sources_identity')==seal.get('sources_identity')
             and identity(report)==report.get('identity')==seal.get('report_identity'), '040 index identity differs')
    for name in ('labels','pairs'):
        context.verify(directory/(name+'.jsonl'),manifest[name+'_sha256'])
        _require(report.get(name+'_sha256')==manifest[name+'_sha256'],'040 supervision bytes/report differ')
    for path,digest in manifest['inputs'].items():context.verify(path,digest)
    ret,ret_report,expected,expected_report,rows,labels,pairs=_compose(
        manifest['old_task_control_index'],manifest['delta_export'],context)
    retention_dir=(directory.parent/'retention').resolve()
    expected['retention_index']=str(retention_dir);expected['identity']=identity(expected)
    expected_report['sources_identity']=expected['identity'];expected_report['identity']=identity(expected_report)
    _require(manifest==expected and report==expected_report,'040 appended source/label/pair/reuse contract differs')
    _require(read_json(retention_dir/'sources.json')==ret and read_json(retention_dir/'report.json')==ret_report,
             '040 retention source/report identity differs')
    context.verify(retention_dir/'rows.jsonl',ret_report['rows_sha256'])
    return manifest,report,_lines(directory/'labels.jsonl'),_lines(directory/'pairs.jsonl')
