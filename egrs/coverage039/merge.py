"""Reference-only release merge: keep old teacher bytes and qualification."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from egrs.augmentation.data import _require, identity, read_json, load_scope, _hex
from egrs.retention.data import _contained
from egrs.trajectory_augmentation.data import DATA_KIND as PHYSICAL_KIND
from .io import HashContext, Progress
from .recipe import TASKS, ALGORITHM, RECIPE_VERSION, generation_context, recipe_for
from .permutation import KIND as SWAP_KIND, OBJECTS, _sha
from egrs.trajectory_augmentation.native import TEACHER_V2

MERGED_KIND = 'task039-merged-qualified-export-v1'
_EXPECTED_OLD = {'10':221, 'normal':75}
_EXPECTED_PARENTS = 180
_TASKS = TASKS
_ARTIFACT_FIELDS = ('file','audit_path','lineage_path','qualification_path','journal_path','metadata_path','video')


def _write(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def _load_export(directory, context):
    directory = Path(directory).resolve()
    manifest, report = (read_json(directory/name) for name in ('sources.json','report.json'))
    _require(manifest.get('format') == PHYSICAL_KIND and report.get('data_kind') == PHYSICAL_KIND
             and identity(manifest) == manifest.get('identity') == report.get('sources_identity')
             and identity(report) == report.get('identity'), 'qualified export identity differs')
    context.verify(directory/'windows.jsonl',report.get('windows_sha256'))
    inputs={str((directory/name).resolve()):context.sha256(directory/name)
            for name in ('sources.json','report.json','windows.jsonl')}
    if (directory/'attempts.json').exists():
        inputs[str((directory/'attempts.json').resolve())]=context.sha256(directory/'attempts.json')
    sources=manifest.get('sources',{})
    _require(isinstance(sources,dict), 'qualified export source map required')
    parents={p['source_id']:p for p in manifest['parents']}
    _require(len(parents)==len(manifest['parents']), 'duplicate parent identity')
    seen=set()
    rows=_lines(directory/'windows.jsonl')
    for sid,source in sources.items():
        parent=parents.get(source.get('parent_demo_id'))
        _require(parent is not None and source.get('source_id')==sid
                 and source.get('domain') in ('normal','10') and source.get('qualified') is True
                 and source.get('status')=='completed' and source.get('qualification',{}).get('accepted') is True
                 and source.get('parent_file_sha256')==parent['file_sha256']
                 and all(source.get(k)==parent[k] for k in ('task_key','split','source_group','instruction')),
                 'qualified export source parent/split/evidence differs')
        _require(type(source.get('length')) is int and 0<source['length']<=520,
                 'qualified outgoing transition length differs')
    for row in rows:
        source=sources.get(row.get('source_id'));start=row.get('start')
        _require(source is not None and type(start) is int and 0<=start<source['length']
                 and row.get('stop')==min(start+8,source['length'])
                 and row.get('action_mask')==[i<row['stop']-start for i in range(8)]
                 and all(row.get(k)==source[k] for k in ('split','task_key','parent_demo_id','source_group','instruction','domain','variant')),
                 'qualified export source window binding differs')
        _require((row['source_id'],start) not in seen,'duplicate qualified export window')
        seen.add((row['source_id'],start))
    _require(seen=={(sid,i) for sid,source in sources.items() for i in range(source['length'])},
             'qualified export windows missing outgoing transitions')
    actual=Counter(s['domain'] for s in sources.values())
    _require(all(report.get('counts_by_domain',{}).get(d,{}).get('trajectories')==actual[d]
                 for d in ('normal','10')), 'qualified export reported counts differ')
    return manifest,report,rows,inputs


def _artifact(root, relative):
    return _contained(root,relative)


def _validate_new_transform(parent, evidence, frame):
    """Bind the initialization recipe to recorded state, without a replay."""
    state=np.asarray(frame.get('state'),dtype=float)
    _require(state.ndim==1 and state.size>0 and np.isfinite(state).all()
             and isinstance(evidence,dict) and evidence.get('applied_at')=='before_initial_restore'
             and evidence.get('transformed_initial_state_sha256')==_sha(state),
             'new039 recorded initial transform/state provenance differs')
    if parent['task_key']!='two_pots':
        _require(evidence.get('kind')=='identity' and evidence.get('modified_indices')==[]
                 and evidence.get('objects')==[]
                 and evidence.get('original_initial_state_sha256')==_sha(state)
                 and evidence.get('non_target_before_sha256')==evidence.get('non_target_after_sha256')==_sha(state),
                 'new039 non-two_pots initialization must preserve original state')
        return
    _require(evidence.get('kind')==SWAP_KIND, 'new039 two_pots initial swap evidence required')
    nq,nv=evidence.get('nq'),evidence.get('nv');blocks=evidence.get('objects')
    _require(type(nq) is int and type(nv) is int and nq>0 and nv>0 and len(state)>=1+nq+nv
             and isinstance(blocks,list) and len(blocks)==2
             and [b.get('object_name') for b in blocks]==list(OBJECTS), 'new039 two_pots swap layout differs')
    changed=[]
    for block in blocks:
        _require(block.get('joint_type')==0 and type(block.get('joint_id')) is int
                 and isinstance(block.get('joint_name'),str) and block['joint_name']
                 and isinstance(block.get('object_class'),str) and block['object_class'],
                 'new039 two_pots actual freejoint identity missing')
        for field,count,limit,offset in (('qpos',7,nq,1),('qvel',6,nv,1+nq)):
            indices=block.get(field+'_indices')
            _require(isinstance(indices,list) and len(indices)==count
                     and all(type(i) is int and 0<=i<limit for i in indices)
                     and indices==list(range(indices[0],indices[0]+count))
                     and block.get('state_'+field+'_indices')==[offset+i for i in indices],
                     'new039 two_pots complete freejoint coordinate evidence differs')
            changed.extend(block['state_'+field+'_indices'])
    _require(blocks[0]['joint_id']!=blocks[1]['joint_id'] and blocks[0]['joint_name']!=blocks[1]['joint_name']
             and blocks[0]['object_class']==blocks[1]['object_class']
             and len(set(changed))==26 and sorted(changed)==evidence.get('modified_indices')
             and isinstance(evidence.get('dimensions'),dict)
             and evidence['dimensions'].get('basis') in ('actual_object_size','compiled_geometry')
             and bool(evidence['dimensions'].get('value')), 'new039 two_pots instance swap evidence differs')
    original=state.copy()
    for field in ('state_qpos_indices','state_qvel_indices'):
        first,second=blocks[0][field],blocks[1][field]
        original[first]=state[second];original[second]=state[first]
    mask=np.ones(len(state),dtype=bool);mask[changed]=False
    _require(_sha(original)==evidence.get('original_initial_state_sha256')
             and evidence['original_initial_state_sha256']!=evidence['transformed_initial_state_sha256']
             and evidence.get('non_target_before_sha256')==evidence.get('non_target_after_sha256')==_sha(state[mask]),
             'new039 two_pots recorded swap/non-target state hashes differ')


def _validate_new039(manifest,context):
    """Only the new release must prove this039 generator and initialization."""
    declared=manifest.get('generation_context',{})
    _require(isinstance(declared,dict) and _hex(declared.get('plan_identity'))
             and type(declared.get('normal_attempts')) is int and 0<=declared['normal_attempts']<=60
             and type(declared.get('ten_attempts')) is int and 0<=declared['ten_attempts']<=360
             and declared==generation_context(declared['plan_identity'],normal_attempts=declared['normal_attempts'],
                                               ten_attempts=declared['ten_attempts']),
             'new039 explicit algorithm/recipe/teacher generation context required')
    root=Path(manifest['data_root']).resolve();parents={p['source_id']:p for p in manifest['parents']}
    normals={};transforms={};progress=Progress('new039_provenance')
    for source in manifest['sources'].values():
        progress.update(source=source['source_id'],completed=len(transforms),total=len(manifest['sources']))
        _require(source['task_key'] in _TASKS and source.get('teacher_policy')==TEACHER_V2
                 and source.get('qualification',{}).get('teacher_policy')==TEACHER_V2
                 and source.get('generator_algorithm')==ALGORITHM,
                 'new039 task/teacher/generator provenance differs')
        lineage_path=_artifact(root,source['lineage_path']);audit_path=_artifact(root,source['audit_path'])
        context.sha256(lineage_path);context.sha256(audit_path)
        lineage=read_json(lineage_path);audit=read_json(audit_path)
        transform=source.get('initialization_transform');recipe=source.get('recipe',{})
        expected_context=generation_context(declared['plan_identity'])
        expected_context['initialization_transform']=deepcopy(transform)
        _require(isinstance(transform,dict) and source.get('generation_context')==expected_context
                 and lineage.get('generation_context')==expected_context
                 and lineage.get('teacher_policy')==TEACHER_V2 and lineage.get('generator_algorithm')==ALGORITHM
                 and lineage.get('initialization_transform')==transform
                 and lineage.get('recipe')==recipe and recipe.get('version')==RECIPE_VERSION
                 and recipe.get('generator_algorithm')==ALGORITHM
                 and recipe.get('initialization_transform')==transform
                 and source.get('recipe_identity')==identity(recipe),
                 'new039 source/lineage recipe/context/transform provenance differs')
        # Persisted recipes replace the policy declaration with this episode's
        # actual evidence, which is checked separately against its first frame.
        recipe_for({'recipe':{k:v for k,v in recipe.items() if k!='initialization_transform'}})
        frames=audit.get('frames',[]);parent=parents[source['parent_demo_id']]
        _require(frames and lineage.get('source')==parent
                 and lineage.get('actual_initial_state')==frames[0].get('state'),
                 'new039 recorded initial state/original parent provenance differs')
        transforms[source['source_id']]=transform
        if source['domain']=='normal':
            _require(source['parent_demo_id'] not in normals,'new039 duplicate normal parent')
            normals[source['parent_demo_id']]=source
            _validate_new_transform(parent,transform,frames[0])
    for source in manifest['sources'].values():
        normal=normals.get(source['parent_demo_id'])
        _require(normal is not None and transforms[source['source_id']]==transforms[normal['source_id']],
                 'new039 ten must retain its new normal initialization transform')
    progress.finish(completed=len(transforms),total=len(manifest['sources']))


def _coverage_table(releases):
    table={task['key']+'|'+split+'|'+domain:{'success':0,'windows':0,'valid_actions':0,
           'new':0,'reused':0,'by_release':{}}
           for task in load_scope()['tasks'] for split in ('train','dev') for domain in ('normal','10')}
    for release,directory,manifest,rows in releases:
        path=Path(directory)/'attempts.json'
        attempts=read_json(path) if path.exists() else None
        _require(attempts is None or isinstance(attempts,list),'release attempts ledger must be a list')
        parents={p['source_id']:p for p in manifest['parents']}
        for bucket in table.values():
            bucket['by_release'][release]={'attempts':0 if attempts is not None else None,
                'success':0,'windows':0,'valid_actions':0,'failure_reasons':{}}
        for attempt in attempts or []:
            parent=parents.get(attempt.get('parent_demo_id'))
            key='|'.join(str(attempt.get(k)) for k in ('task_key','split','domain'))
            _require(parent is not None and key in table
                     and all(attempt.get(k)==parent[k] for k in ('task_key','split')),
                     'attempt task/split/original parent ledger differs')
            bucket=table[key]['by_release'][release];bucket['attempts']+=1
            if attempt.get('qualified') is False:
                reason=attempt.get('failure_reason')
                _require(isinstance(reason,str) and reason,'failed release attempt reason required')
                bucket['failure_reasons'][reason]=bucket['failure_reasons'].get(reason,0)+1
        for source in manifest['sources'].values():
            key='|'.join(source[k] for k in ('task_key','split','domain'))
            bucket=table[key];bucket['success']+=1
            bucket['new' if release=='new039' else 'reused']+=1
            bucket['by_release'][release]['success']+=1
        for row in rows:
            key='|'.join(row[k] for k in ('task_key','split','domain'))
            bucket=table[key];bucket['windows']+=1;bucket['valid_actions']+=sum(row['action_mask'])
            bucket['by_release'][release]['windows']+=1
            bucket['by_release'][release]['valid_actions']+=sum(row['action_mask'])
    for bucket in table.values():
        known=all(v['attempts'] is not None for v in bucket['by_release'].values())
        bucket['attempts']=sum(v['attempts'] for v in bucket['by_release'].values()) if known else None
        failures=Counter()
        for value in bucket['by_release'].values():failures.update(value['failure_reasons'])
        bucket['failure_reasons']=dict(failures)
    return table


def merge_exports(old003_export,new039_export,out,context=None):
    context=context or HashContext()
    output=Path(out).resolve()
    if output.exists():
        raise FileExistsError('new039 merged export directory required')
    old,old_report,old_rows,old_inputs=_load_export(old003_export,context)
    new,new_report,new_rows,new_inputs=_load_export(new039_export,context)
    _require(dict(Counter(s['domain'] for s in old['sources'].values()))==_EXPECTED_OLD,
             'old003 must retain approved 221 ten/75 normal counts')
    _require(len(old['parents'])==_EXPECTED_PARENTS and old['parents']==new['parents'],
             'complete original parent identities/paths/splits must remain unchanged')
    _validate_new039(new,context)
    roots={'old003':str(Path(old['data_root']).resolve()),'new039':str(Path(new['data_root']).resolve())}
    common=Path(os.path.commonpath(list(roots.values()))).resolve()
    _require(all(Path(root).is_relative_to(common) for root in roots.values()),'common generated root differs')
    sources={}; rows=[]; artifacts={}; progress=Progress('merge_metadata')
    total=len(old['sources'])+len(new['sources'])
    for release,manifest,release_rows in (('old003',old,old_rows),('new039',new,new_rows)):
        root=Path(roots[release]); ids={}
        for original_id,original in manifest['sources'].items():
            sid=release+'|'+original_id;ids[original_id]=sid
            source=deepcopy(original);source['source_id']=sid
            source['coverage039_origin']={'release':release,'source_id':original_id,
                                          'original_source':deepcopy(original)}
            bound={}
            _require(all(source.get(k) for k in ('file','audit_path','lineage_path')),
                     'recorded HDF/audit/lineage required')
            for field in _ARTIFACT_FIELDS:
                if not source.get(field):continue
                path=_artifact(root,source[field]);digest=context.sha256(path)
                if field=='file':_require(digest==source['file_sha256'],'qualified source HDF bytes changed')
                relative=path.relative_to(common).as_posix();source[field]=relative
                bound[field]={'path':relative,'sha256':digest,'release':release,
                              'original_relative':original[field]}
            sources[sid]=source;artifacts[sid]=bound
            progress.update(source=sid,completed=len(sources),total=total)
        for original in release_rows:
            row=deepcopy(original);row['source_id']=ids[row['source_id']];rows.append(row)
    coverage={'new_qualified_train10':sum(s['domain']=='10' and s['split']=='train' for s in new['sources'].values()),
              'qualified_counts':{release:{d:sum(s['domain']==d for s in manifest['sources'].values())
                                           for d in ('normal','10')}
                                  for release,manifest in (('old003',old),('new039',new))},
              'release_identities':{'old003':old['identity'],'new039':new['identity']},
              'task_split_domain':_coverage_table((('old003',old003_export,old,old_rows),
                                                    ('new039',new039_export,new,new_rows))),
              'new_generation_context':deepcopy(new['generation_context'])}
    manifest={'format':PHYSICAL_KIND,'merge_format':MERGED_KIND,'data_root':str(common),
              'allowed_data_roots':roots,'sources':sources,'parents':deepcopy(old['parents']),
              'release_exports':{'old003':str(Path(old003_export).resolve()),'new039':str(Path(new039_export).resolve())},
              'source_artifacts':artifacts,'inputs':{**old_inputs,**new_inputs},
              'coverage039':coverage,'generation_context':{'format':MERGED_KIND,
                  'old003':deepcopy(old.get('generation_context')),'new039':deepcopy(new['generation_context'])}}
    manifest['identity']=identity(manifest)
    content=''.join(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n' for row in rows).encode('utf-8')
    counts={d:{'trajectories':sum(s['domain']==d for s in sources.values()),
               'windows':sum(r['domain']==d for r in rows),
               'valid_actions':sum(sum(r['action_mask']) for r in rows if r['domain']==d)} for d in ('10','normal')}
    report={'data_kind':PHYSICAL_KIND,'merge_format':MERGED_KIND,'sources_identity':manifest['identity'],
            'windows_sha256':hashlib.sha256(content).hexdigest(),'parent_sources':len(old['parents']),
            'counts_by_domain':counts,'qualified_trajectories':len(sources),'coverage039':deepcopy(coverage),
            'releases':{'old003':deepcopy(old_report),'new039':deepcopy(new_report)},
            'old_teacher_replayed':False,'old_qualification_rejudged':False,
            'hdf_copied':False,'simulation_created':False,'model_loaded':False}
    report['identity']=identity(report)
    output.mkdir(parents=True)
    _write(output/'sources.json',manifest);_write(output/'report.json',report)
    (output/'windows.jsonl').write_bytes(content)
    progress.finish(completed=total,total=total)
    return report


def read_merged(directory,context=None):
    context=context or HashContext()
    manifest,report,rows,_=_load_export(directory,context)
    _require(manifest.get('merge_format')==report.get('merge_format')==MERGED_KIND,
             'explicit039 merged export required')
    roots=manifest.get('allowed_data_roots',{})
    _require(set(roots)=={'old003','new039'} and all(Path(p).is_absolute() for p in roots.values()),
             'two explicit allowlisted generated roots required')
    common=Path(manifest['data_root']).resolve()
    _require(common==Path(os.path.commonpath(list(roots.values()))).resolve(), 'bound common generated root differs')
    for path,digest in manifest['inputs'].items():context.verify(path,digest)
    exports=manifest.get('release_exports',{})
    _require(set(exports)==set(roots), 'original release export bindings missing')
    originals={}
    for release,path in exports.items():
        directory=Path(path).resolve()
        parent=read_json(directory/'sources.json');release_report=read_json(directory/'report.json')
        _require(identity(parent)==parent.get('identity')==release_report.get('sources_identity')
                 ==manifest['coverage039']['release_identities'][release]
                 and identity(release_report)==release_report.get('identity')
                 and parent.get('data_root')==roots[release]
                 and parent.get('parents')==manifest['parents']
                 and release_report==report['releases'][release], 'original release/parent evidence differs')
        names=('sources.json','report.json','windows.jsonl')
        if (directory/'attempts.json').exists():names+=('attempts.json',)
        for name in names:
            bound=str((directory/name).resolve())
            _require(bound in manifest['inputs'], 'original release metadata binding missing')
            context.verify(bound,manifest['inputs'][bound])
        originals[release]=parent
    _validate_new039(originals['new039'],context)
    _require(set(manifest['sources'])=={release+'|'+sid for release,parent in originals.items()
             for sid in parent['sources']}, 'original release qualified source set differs')
    _require(set(manifest['source_artifacts'])==set(manifest['sources']),'source artifact allowlist differs')
    for sid,source in manifest['sources'].items():
        origin=source.get('coverage039_origin',{});release=origin.get('release')
        _require(release in roots and sid==release+'|'+origin.get('source_id',''), '039 release/source origin differs')
        original=origin.get('original_source',{})
        _require(original==originals[release]['sources'].get(origin['source_id']),
                 'original release qualification/teacher evidence differs')
        bound=manifest['source_artifacts'][sid]
        _require(set(bound)=={k for k in _ARTIFACT_FIELDS if source.get(k)},'source artifact fields differ')
        rewritten=deepcopy(original);rewritten['source_id']=sid;rewritten['coverage039_origin']=deepcopy(origin)
        for field,artifact in bound.items():
            _require(source.get(field)==artifact.get('path') and artifact.get('release')==release
                     and artifact.get('original_relative')==original.get(field), 'source artifact binding differs')
            path=_artifact(common,artifact['path'])
            _require(path.is_relative_to(Path(roots[release]).resolve())
                     and path==_artifact(Path(roots[release]).resolve(),original[field]),
                     'artifact escapes two-root allowlist')
            context.verify(path,artifact['sha256'])
            if field=='file':_require(artifact['sha256']==source['file_sha256'],'source artifact file SHA differs')
            rewritten[field]=artifact['path']
        _require(source==rewritten,'source qualification/teacher lineage changed during merge')
    _require(dict(Counter(s['domain'] for s in manifest['sources'].values()
                         if s['coverage039_origin']['release']=='old003'))==_EXPECTED_OLD,
             'old003 approved counts changed')
    _require(len(manifest['parents'])==_EXPECTED_PARENTS,'original complete parents changed')
    actual_counts={release:{domain:sum(s['domain']==domain for s in parent['sources'].values())
                            for domain in ('normal','10')} for release,parent in originals.items()}
    actual_train10=sum(s['domain']=='10' and s['split']=='train' for s in originals['new039']['sources'].values())
    actual_table=_coverage_table(tuple((release,exports[release],parent,
        [r for r in rows if r['source_id'].startswith(release+'|')]) for release,parent in originals.items()))
    _require(manifest['coverage039']==report['coverage039']
             and manifest['coverage039']['qualified_counts']==actual_counts
             and manifest['coverage039']['task_split_domain']==actual_table
             and type(manifest['coverage039']['new_qualified_train10']) is int
             and manifest['coverage039']['new_qualified_train10']==actual_train10
             and manifest['coverage039']['new_generation_context']==originals['new039'].get('generation_context'),
             '039 actual qualified coverage counts/context differ')
    return manifest,report,rows
