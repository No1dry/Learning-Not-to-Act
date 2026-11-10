"""Versioned035 seed groups and fresh executed trajectories; no native imports."""
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from egrs.augmentation.data import (DATASET,REVISION,ATTESTATIONS,SOURCE_FIELDS,
    AugmentationDataset,identity,file_sha256,read_json,load_scope,validate_mapping,
    _require,_hex,_text,_rows,_instruction)

SEEDS='task035-seeds-v1'
DATA_KIND='task035-generated-trajectories-v1'
DOMAINS=('10','normal')
PROVENANCE={'10':'counterfactual_generated_from_demo','normal':'ordinary_reexecuted'}


def validate_seeds(manifest):
    """Choose natural source prefixes and split entire known duplicate groups."""
    _require(manifest.get('format')==SEEDS,'explicit035 seed manifest required')
    _require(manifest.get('dataset')==DATASET and manifest.get('revision')==REVISION,'fixed ordinary dataset required')
    _require(manifest.get('split_seed')==7,'fixed parent split seed7 required')
    _require(all(manifest.get('exclusion_attestation',{}).get(k) is True
        for k in (*ATTESTATIONS,'known_eval_overlap_excluded')),'evaluation/model-action exclusion required')
    limit=manifest.get('max_demos_per_task')
    _require(type(limit) is int and 0<=limit<=20,'natural source limit must be in0..20')
    sources=deepcopy(manifest.get('sources'))
    _require(isinstance(sources,list),'explicit seed sources required')
    _require(len({s.get('source_id') for s in sources})==len(sources),'duplicate parent source ID')
    scope={t['key']:t for t in load_scope()['tasks']};by_task=defaultdict(list);parent={}
    def find(key):
        parent.setdefault(key,key)
        if parent[key]!=key:parent[key]=find(parent[key])
        return parent[key]
    def union(a,b):
        a,b=find(a),find(b);parent[max(a,b)]=min(a,b)
    for s in sources:
        _require(not set(s)-SOURCE_FIELDS-{'controller_binding','native_binding'},'unknown seed fields')
        _require(all(_text(s.get(k)) for k in ('source_id','task_key','instruction','file','episode')),'explicit source identity required')
        _require(s.get('provenance')=='ordinary_expert_demo' and s.get('domain')=='compound','035 seeds must be ordinary compound demos')
        _require(s.get('physical_ancestry') in {'unknown','known_separate_from_eval'},'known evaluation overlap cannot be a seed')
        _require(_hex(s.get('file_sha256')),'parent file SHA required')
        _require(not Path(s['file']).is_absolute() and '..' not in Path(s['file']).parts,'seed path must stay beneath data_root')
        _require(type(s.get('length')) is int and s['length']>0,'positive source length required')
        i=s.get('demo_index')
        _require(type(i) is int and i>=0 and s['episode']==f'data/demo_{i}','exact natural data/demo_N source required')
        task=scope.get(s['task_key']);_require(task is not None,'seed outside fixed nine tasks')
        for key in ('official_task_name','active_goals','invariant_predicates'):
            _require(s.get(key)==task[key],'fixed task goal binding differs: '+key)
        validate_mapping(s.get('mapping'))
        _require(s['mapping']['images']==['obs/agentview_rgb','obs/eye_in_hand_rgb']
            and s['mapping']['action']=='actions','original native camera/action field bindings required')
        _canonical_mapping(s['mapping'])
        ctrl=s.get('controller_binding',{})
        _require(set(ctrl)=={'type','control_freq','env_args_sha256'} and ctrl['type']=='OSC_POSE'
            and type(ctrl['control_freq']) in (int,float) and np.isfinite(ctrl['control_freq'])
            and ctrl['control_freq']>0 and _hex(ctrl['env_args_sha256']),'explicit original OSC_POSE controller binding required')
        _require(isinstance(s.get('group_ids'),list) and all(_text(x) for x in s['group_ids']),'known duplicate groups required')
        sid=s['source_id'];find(sid)
        aliases=s['group_ids']+['file-episode:'+s['file_sha256']+'#'+s['episode']]
        if s.get('trajectory_sha256'):
            _require(_hex(s['trajectory_sha256']),'invalid trajectory identity')
            aliases+=['trajectory:'+s['trajectory_sha256']]
        for alias in aliases:union(sid,'alias:'+alias)
        by_task[s['task_key']].append(i)
    for key,indices in by_task.items():
        _require(len(indices)<=limit and sorted(indices)==list(range(len(indices))),key+': natural firstN demos without gaps required')
    components=defaultdict(list)
    for s in sources:components[find(s['source_id'])].append(s)
    for members in components.values():
        key='|'.join(sorted(s['source_id'] for s in members))
        digest=hashlib.sha256(('7|'+key).encode()).hexdigest()
        split='dev' if int(digest,16)%5==0 else 'train'
        for s in members:
            _require(s.get('split') in (None,split),'parent split differs from fixed grouped assignment')
            s.update(split=split,parent_demo_id=s['source_id'],source_group=digest)
    return sources


def _canonical_mapping(mapping):
    grip=mapping['gripper']
    _require(mapping['axis_sign']==[1]*7 and grip['input_open']==-1 and grip['input_closed']==1
        and grip['kind'] in {'affine','binarize'},'035 actual environment actions require canonical deployed OFT signs/gripper endpoints')


def validate_executed_actions(actions,mapping):
    """Reject labels whose old030 preprocessing would clip executed behavior."""
    _canonical_mapping(mapping)
    x=np.asarray(actions,dtype=np.float64)*np.asarray(mapping['axis_sign'])
    _require(x.ndim==2 and x.shape[1]==7 and np.isfinite(x).all(),'finite actual action7 required')
    grip=mapping['gripper']
    _require(np.all(np.isclose(x[:,6],grip['input_open'],atol=1e-7,rtol=0)
                   |np.isclose(x[:,6],grip['input_closed'],atol=1e-7,rtol=0)),
             'actual gripper must roundtrip through original binary policy endpoints')
    x[:,6]=(x[:,6]-grip['input_closed'])/(grip['input_open']-grip['input_closed'])
    norm=mapping['action_normalization']
    if norm['kind']=='bounds_q99':
        mask=np.asarray(norm['mask'],dtype=bool);lo=np.asarray(norm['q01']);hi=np.asarray(norm['q99'])
        _require(np.all(x[:,mask]>=lo[mask]-1e-7) and np.all(x[:,mask]<=hi[mask]+1e-7),
                 'actual executed action exceeds original policy bounds; loader must not clip teacher labels')
        x[:,mask]=2*(x[:,mask]-lo[mask])/(hi[mask]-lo[mask])-1
    _require(np.all(x>=-1-1e-7) and np.all(x<=1+1e-7),'actual action is not representable by original normalized policy')
    return x


def inspect_generated(path,source):
    import h5py
    m=source['mapping'];T=source['length']
    validate_mapping(m)
    _require(m['observation_offset']==0 and m['action_offset']==0,'fresh transitions require o_t to a_t offsets0')
    _require(type(T) is int and 0<T<=520,'generated supervision length must be in1..520')
    with h5py.File(path,'r') as h:
        g=h[source['episode']]
        _require(_instruction(h,m['instruction_binding'])==source['instruction'],'generated full instruction differs')
        for field in m['images']:
            v=g[field]
            _require(v.ndim==4 and v.shape[-1]==3 and v.dtype==np.uint8 and len(v)==T+1,'fresh RGB requires T+1 observations')
        width=0
        for field in m['proprio']:
            v=g[field]
            _require(v.ndim==2 and len(v)==T+1 and np.isfinite(v[:]).all(),'fresh proprio requires T+1 finite observations')
            width+=v.shape[1]
        _require(width==8,'fresh proprio must have8 original dimensions')
        states=g['states']
        _require(states.ndim==2 and len(states)==T+1 and np.isfinite(states[:]).all(),'fresh states require T+1 finite records')
        actions=np.asarray(g[m['action']])
        _require(len(actions)==T,'fresh actions require exactlyT executed transitions')
        validate_executed_actions(actions,m)


def export_generated(parents,attempts,data_root,output,*,generation_context=None,context=None):
    """Index qualified real transitions, retaining every failed attempt in audit."""
    hash_file=file_sha256 if context is None else context.sha256
    output=Path(output)
    if output.exists():raise FileExistsError('new035 export directory required')
    root=Path(data_root).resolve();by_parent={s['source_id']:s for s in parents}
    _require(len(by_parent)==len(parents),'duplicate parent identity')
    _require(len({a['source_id'] for a in attempts})==len(attempts),'duplicate attempt identity')
    sources={};rows=[];slots=set();failed=Counter();counts={d:{'trajectories':0,'windows':0,'valid_actions':0} for d in DOMAINS}
    details={}
    for a in attempts:
        p=by_parent.get(a.get('parent_demo_id'));_require(p is not None,'attempt has unplanned parent')
        d=a.get('domain');_require(d in DOMAINS,'unknown generated domain')
        _require(a.get('split')==p['split'] and a.get('task_key')==p['task_key'],'variant task/split differs from parent')
        _require(a.get('parent_file_sha256')==p['file_sha256'],'attempt parent file identity differs')
        _require(a.get('provenance')==PROVENANCE[d],'generated provenance must not masquerade as ordinary official data')
        slot=(p['source_id'],d,str(a.get('variant')),a.get('attempt'))
        _require(slot not in slots,'duplicate attempted variant/bridge slot');slots.add(slot)
        if d=='normal':
            _require(a.get('variant')=='normal' and a.get('attempt')==0,'one normal replay per parent')
        else:
            _require(type(a.get('variant')) is int and a['variant'] in range(3)
                and type(a.get('attempt')) is int and a['attempt'] in range(2),'bounded three starts/two bridges required')
        _require(type(a.get('qualified')) is bool,'explicit actual qualification result required')
        bucket=details.setdefault('|'.join((p['task_key'],p['split'],d)),{'parent_sources':set(),'attempts':0,'qualified':0,'windows':0,'valid_actions':0})
        bucket['parent_sources'].add(p['source_group']);bucket['attempts']+=1
        if not a['qualified']:
            _require(_text(a.get('failure_reason')),'failed attempt must retain reason')
            failed[a['failure_reason']]+=1;continue
        _require(a.get('status')=='completed' and a.get('qualification',{}).get('accepted') is True,'qualified completed execution evidence required')
        _require(a.get('instruction')==p['instruction'],'generated language must be full original instruction')
        _require(_hex(a.get('file_sha256')),'generated file hash required')
        path=(root/a['file']).resolve();_require(path.is_relative_to(root),'generated file escapes data root')
        _require(hash_file(path)==a['file_sha256'],'generated file byte identity differs')
        source=deepcopy(a);source['source_group']=p['source_group'];source['physical_ancestry']=p['physical_ancestry']
        # Targets keep exactly the original normalization/sign/gripper/camera transforms.
        for key in ('images','image_transforms','proprio','action','axis_order','axis_sign','gripper',
                    'action_normalization','proprio_normalization','processor_id','crop'):
            _require(source['mapping'][key]==p['mapping'][key],'generated original mapping changed: '+key)
        inspect_generated(path,source);sources[a['source_id']]=source
        generated=list(_rows(source,0,a['length'],'GENERATED',a['instruction'],domain=d,
            parent_demo_id=p['source_id'],source_group=p['source_group'],variant=a['variant']))
        rows.extend(generated);valid=sum(sum(r['action_mask']) for r in generated)
        counts[d]['trajectories']+=1;counts[d]['windows']+=len(generated);counts[d]['valid_actions']+=valid
        bucket['qualified']+=1;bucket['windows']+=len(generated);bucket['valid_actions']+=valid
    for bucket in details.values():bucket['parent_sources']=len(bucket['parent_sources'])
    windows=''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows)
    source_manifest={'format':DATA_KIND,'data_root':str(root),'sources':sources,'parents':deepcopy(parents)}
    if generation_context is not None:source_manifest['generation_context']=deepcopy(generation_context)
    source_manifest['identity']=identity(source_manifest)
    report={'data_kind':DATA_KIND,'parent_sources':len(parents),'parent_groups':len({p['source_group'] for p in parents}),
        'attempts':len(attempts),'qualified_trajectories':len(sources),'failed_attempts':sum(failed.values()),
        'failure_reasons':dict(failed),'counts_by_domain':counts,'task_split_domain':details,
        'task_coverage':{t['key']:{'parents':sum(p['task_key']==t['key'] for p in parents),
            **{d:sum(s['task_key']==t['key'] and s['domain']==d for s in sources.values()) for d in DOMAINS}}
            for t in load_scope()['tasks']},
        'unknown_ancestry_parent_sources':sum(p['physical_ancestry']=='unknown' for p in parents),
        'sources_identity':source_manifest['identity'],'windows_sha256':hashlib.sha256(windows.encode()).hexdigest(),
        'coverage_claim':'same-task generated expert data; unknown demo/init ancestry remains unknown; no unseen-task claim'}
    if generation_context is not None:report['generation_context']=deepcopy(generation_context)
    report['identity']=identity(report)
    output.mkdir(parents=True)
    for name,value in [('sources.json',source_manifest),('report.json',report),('attempts.json',attempts)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (output/'windows.jsonl').write_bytes(windows.encode('utf-8'))
    return report


class GeneratedTrajectoryDataset(AugmentationDataset):
    """Reuse030 item transforms, with versioned T+1/T source validation."""
    def __init__(self,export_dir,split=None,domains=None):
        directory=Path(export_dir);self.manifest=read_json(directory/'sources.json');self.report=read_json(directory/'report.json')
        _require(self.manifest.get('format')==DATA_KIND and self.report.get('data_kind')==DATA_KIND,'035 generated dataset kind required')
        _require(identity(self.manifest)==self.manifest.get('identity')==self.report.get('sources_identity')
            and identity(self.report)==self.report.get('identity'),'generated dataset metadata identity differs')
        _require(file_sha256(directory/'windows.jsonl')==self.report['windows_sha256'],'generated window index bytes changed')
        domains=set(DOMAINS if domains is None else domains);_require(domains<=set(DOMAINS),'unknown generated domains')
        _require(split in (None,'train','dev'),'unknown generated split')
        self.sources=self.manifest['sources']
        self.rows=[r for line in (directory/'windows.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()
                   for r in [json.loads(line)] if (split is None or r['split']==split) and r['domain'] in domains]
        root=Path(self.manifest['data_root']).resolve();checked={}
        for sid in {r['source_id'] for r in self.rows}:
            s=self.sources[sid];path=(root/s['file']).resolve()
            _require(path.is_relative_to(root),'generated source escapes data root')
            if path not in checked:checked[path]=file_sha256(path)
            _require(checked[path]==s['file_sha256'],'generated source HDF changed since export')
        self._source_digests=checked
