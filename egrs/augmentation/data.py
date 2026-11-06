"""Explicit HDF action indexes. No simulator, selector, or model is imported.

Metadata/evidence stays outside __getitem__; only current RGB/proprio, instruction,
expert targets and their loss mask reach training. All offsets are declarations,
never inferred from similarly sized arrays.
"""
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re

import numpy as np

DATASET = 'yifengzhu-hf/LIBERO-datasets'
REVISION = '147fa5eb607bb696dd922c3518084a90954cd2f3'
BASE_INVENTORY_IDENTITY = '3f550e7736ba5428dad789a307e2c18b32f25ec51dcc763e1fb8e65db563bb33'
SCOPE_REF = '191eabf1dad8bebc1cf2a39d26a98308ed4d6338'
ATTESTATIONS = ('eval_initial_states_excluded', 'eval_trajectories_excluded',
                'edited_states_excluded', 'model_actions_excluded')
VIEWS = ('RAW', 'PROGRESS', 'ATOMIC')
SOURCE_FIELDS = {'source_id','task_key','domain','file','file_sha256','episode','instruction','length',
                 'split','group_ids','physical_ancestry','provenance','mapping','demo_index',
                 'official_task_name','active_goals','invariant_predicates','trajectory_sha256'}
MAPPING_FIELDS = {'alignment_id','alignment_basis','observation_offset','action_offset','images',
                  'image_transforms','proprio','action','action_dim','proprio_dim','axis_order',
                  'axis_sign','gripper','action_normalization','proprio_normalization','processor_id',
                  'crop','instruction_binding'}


def identity(value):
    """Canonical metadata identity compatible with the existing sealed inventory."""
    value = {k:v for k,v in value.items() if k != 'identity'}
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                         separators=(',',':'),allow_nan=False).encode()).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def load_scope():
    return read_json(Path(__file__).with_name('data_scope.json'))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hex(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _text(value):
    return isinstance(value,str) and bool(value.strip())


def _field(path, role=None):
    _require(_text(path) and not path.startswith('/') and '..' not in path.split('/'),
             'HDF field must be an explicit relative path')
    if role=='proprio':
        # Exact current robot sensors, plus the existing synthetic packed alias.
        # In particular, ee_states is not permission to read world/robot states.
        allowed={'obs/ee_pos','obs/ee_ori','obs/ee_states','obs/gripper_states','proprio'}
        _require(path in allowed, 'forbidden HDF proprio input outside whitelist')
        return
    # This is an input whitelist, not a promise that unknown physical ancestry was resolved.
    forbidden = ('state','predicate','contact','reward','success','mask','segmentation','object_pose',
                 'goal_truth','future','eval','completion','progress')
    _require(not any(token in path.lower() for token in forbidden), 'forbidden HDF input outside whitelist')


def _normalization(norm, dim):
    _require(isinstance(norm,dict) and norm.get('kind') in {'identity_already_normalized','bounds_q99'},
             'explicit normalization kind required')
    _require(_text(norm.get('stats_id')) and _hex(norm.get('stats_sha256')), 'normalization stats identity required')
    if norm['kind']=='bounds_q99':
        lo,hi,mask=norm.get('q01'),norm.get('q99'),norm.get('mask')
        _require(all(isinstance(x,list) and len(x)==dim for x in (lo,hi,mask)), 'normalization dimension mismatch')
        _require(all(type(x) is bool for x in mask), 'normalization mask must contain booleans')
        _require(np.isfinite(lo).all() and np.isfinite(hi).all(), 'nonfinite normalization bounds')
        _require(all(not m or h>l for l,h,m in zip(lo,hi,mask)), 'invalid normalization range')


def validate_mapping(mapping):
    _require(isinstance(mapping,dict) and set(mapping)==MAPPING_FIELDS, 'explicit field/time/normalization mapping required')
    for key in ('alignment_id','alignment_basis','processor_id','crop'):
        _require(_text(mapping.get(key)),f'explicit {key} required')
    for key in ('observation_offset','action_offset'):
        _require(type(mapping[key]) is int and mapping[key]>=0,'explicit nonnegative time offsets required')
    _require(mapping['action_dim']==7 and mapping['proprio_dim']==8,'official OFT requires action7/proprio8')
    _require(isinstance(mapping['images'],list) and len(mapping['images'])==2,'two camera fields required')
    _require(isinstance(mapping['image_transforms'],list) and len(mapping['image_transforms'])==2
             and all(t in {'identity','rotate_180'} for t in mapping['image_transforms']), 'explicit camera orientation required')
    _require(isinstance(mapping['proprio'],list) and bool(mapping['proprio']),'proprio field order required')
    for field in mapping['images']+[mapping['action']]:
        _field(field)
    for field in mapping['proprio']:
        _field(field,role='proprio')
    _require(mapping['axis_order']==['x','y','z','rx','ry','rz','gripper'], 'explicit official action axis order required')
    _require(len(mapping['axis_sign'])==7 and all(v in (-1,1) for v in mapping['axis_sign']), 'explicit action signs required')
    grip=mapping['gripper']
    _require(isinstance(grip,dict) and grip.get('index')==6 and grip.get('kind') in {'affine','binarize','identity'},
             'explicit gripper mapping required')
    _require(all(isinstance(grip.get(k),(int,float)) and np.isfinite(grip[k])
                 for k in ('input_open','input_closed','output_open','output_closed')),
             'gripper endpoints required')
    _require(grip['input_open']!=grip['input_closed'] and grip['output_open']==1 and grip['output_closed']==0,
             'gripper must map to original OFT open1/closed0')
    if grip['kind']=='identity':
        _require(grip['input_open']==1 and grip['input_closed']==0,'identity gripper requires already converted endpoints')
    _require(mapping['axis_sign'][6]==1,'gripper sign belongs in explicit endpoint mapping')
    for key,dim in [('action_normalization',7),('proprio_normalization',8)]:
        _normalization(mapping[key],dim)
    if mapping['action_normalization']['kind']=='bounds_q99':
        _require(mapping['action_normalization']['mask'][6] is False,'do not bounds-normalize converted binary gripper')
    binding=mapping['instruction_binding']
    _require(isinstance(binding,dict) and set(binding)=={'group','attribute','json_key'}
             and _text(binding['group']) and _text(binding['attribute'])
             and (binding['json_key'] is None or _text(binding['json_key'])), 'exact HDF instruction binding required')


def validate_manifest(manifest, inventory):
    """Bind original 200/160:40, then split complete duplicate components."""
    _require(manifest.get('format')=='egrs.augmentation.sources.v1','unsupported source manifest')
    for value in (manifest,inventory):
        _require(value.get('dataset')==DATASET and value.get('revision')==REVISION,'fixed official dataset revision required')
    _require(inventory.get('identity')==BASE_INVENTORY_IDENTITY and identity(inventory)==BASE_INVENTORY_IDENTITY,
             'exact prior inventory identity required')
    _require(all(manifest.get('exclusion_attestation',{}).get(k) is True for k in ATTESTATIONS),
             'explicit evaluation/model-action exclusion attestation required')
    sources=copy.deepcopy(manifest.get('sources',[]))
    _require(len({s.get('source_id') for s in sources})==len(sources),'duplicate source_id')
    prior={s['source_id']:s for s in inventory['sources']}
    base=[s for s in sources if s.get('domain')=='base']
    _require(len(prior)==200 and len(base)==200 and {s['source_id'] for s in base}==set(prior),'exact prior 200 sources required')
    _require(len({s['task_group'] for s in prior.values()})==20,'exact prior 20 task groups required')
    _require(Counter(s['split'] for s in prior.values())=={'train':160,'dev':40},'prior 160:40 split required')
    limit=manifest.get('compound_limit_per_task',20)
    _require(type(limit) is int and 0<=limit<=20,'compound limit must be in 0..20')
    scope={t['key']:t for t in load_scope()['tasks']}
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x: parent[x]=find(parent[x])
        return parent[x]
    def union(a,b):
        a,b=find(a),find(b)
        parent[max(a,b)]=min(a,b)
    by_task=defaultdict(list)
    for s in sources:
        _require(not set(s)-SOURCE_FIELDS,'unknown source fields: whitelist required')
        _require(all(_text(s.get(k)) for k in ('source_id','task_key','instruction','episode','file')), 'source identity/instruction required')
        _require(s.get('domain') in {'base','compound'} and s.get('provenance')=='ordinary_expert_demo',
                 'only ordinary expert demonstrations are allowed')
        _require(s.get('physical_ancestry') in {'unknown','known_separate_from_eval'},'physical ancestry disclosure required')
        _require(_hex(s.get('file_sha256')),'exact source file SHA256 required')
        _require(type(s.get('length')) is int and s['length']>0,'positive trajectory length required')
        _require(not Path(s['file']).is_absolute() and '..' not in Path(s['file']).parts,'source file must stay under data_root')
        _require(isinstance(s.get('group_ids'),list) and all(_text(g) for g in s['group_ids']), 'explicit known duplicate groups required')
        _field(s['episode'])
        validate_mapping(s.get('mapping'))
        sid=s['source_id'];find(sid)
        for alias in s['group_ids']+['file-episode:'+s['file_sha256']+'#'+s['episode']]:
            union(sid,'alias:'+alias)
        if s.get('trajectory_sha256'):
            _require(_hex(s['trajectory_sha256']),'invalid trajectory hash')
            union(sid,'trajectory:'+s['trajectory_sha256'])
        if s['domain']=='base':
            p=prior[sid]
            for key in ('file','instruction','split'):
                _require(s[key]==p[key],f'prior {key} changed')
            _require(s['episode'].removeprefix('data/')==p['episode'].removeprefix('data/'),'prior episode changed')
            _require(s['task_key']==p['task_group'],'prior task changed')
            _require(set(p.get('group_ids',[]))<=set(s['group_ids']),'prior known duplicate aliases omitted')
        else:
            t=scope.get(s['task_key'])
            _require(t is not None,'compound task outside fixed nine-task scope')
            for key in ('official_task_name','active_goals','invariant_predicates'):
                _require(s.get(key)==t[key],f'exact official scope {key} binding required')
            _require(type(s.get('demo_index')) is int and s['demo_index']>=0,'explicit natural demo index required')
            _require(s['episode'].split('/')[-1]==f"demo_{s['demo_index']}",'natural demo index must bind actual HDF episode')
            by_task[s['task_key']].append(s['demo_index'])
    for task,indices in by_task.items():
        _require(len(indices)<=limit and sorted(indices)==list(range(len(indices))),
                 f'{task}: select first natural demos without gaps, at most {limit}')
    components=defaultdict(list)
    for s in sources: components[find(s['source_id'])].append(s)
    for members in components.values():
        pinned={s['split'] for s in members if s['domain']=='base'}
        _require(len(pinned)<=1,'known duplicate component crosses prior train/dev split')
        if pinned: split=next(iter(pinned))
        else:
            # Deterministic whole-component allocation; 80/20 is an expectation, not forced source counts.
            key='|'.join(sorted(s['source_id'] for s in members))
            split='dev' if int(hashlib.sha256(('7|'+key).encode()).hexdigest(),16)%5==0 else 'train'
        for s in members:
            _require(s.get('split') in (None,split),'known duplicate or compound split crosses grouped assignment')
            s['split']=split
    return sources


def _instruction(hdf,binding):
    value=hdf[binding['group']].attrs[binding['attribute']]
    if isinstance(value,bytes):value=value.decode('utf-8')
    if binding['json_key'] is not None:value=json.loads(value)[binding['json_key']]
    return value


def inspect_source(hdf,source):
    """Read shapes and exact language; never inspect simulator state or extra datasets."""
    m=source['mapping'];g=hdf[source['episode']];T=source['length'];o=m['observation_offset'];a=m['action_offset']
    _require(_instruction(hdf,m['instruction_binding'])==source['instruction'],'exact HDF instruction mismatch')
    for field in m['images']:
        x=g[field]
        _require(len(x.shape)==4 and x.shape[-1]==3 and x.dtype==np.uint8 and len(x)==T+o,'image mapping/length mismatch')
    widths=[]
    for field in m['proprio']:
        x=g[field]
        _require(len(x.shape)==2 and len(x)==T+o,'proprio mapping/length mismatch')
        widths.append(x.shape[-1])
    _require(sum(widths)==8,'proprio concatenation must have 8 original dimensions')
    actions=g[m['action']]
    _require(len(actions.shape)==2 and actions.shape[1]==7 and len(actions)==T+a,'action mapping/length mismatch')


def _rows(source,start,stop,view,instruction,**metadata):
    for t in range(start,stop):
        end=min(t+8,stop)
        yield {'source_id':source['source_id'],'task_key':source['task_key'],'split':source['split'],
               'view':view,'start':t,'stop':end,'instruction':instruction,
               'action_mask':[True]*(end-t)+[False]*(8-end+t),**metadata}


def _evidence_rows(source,evidence,excluded):
    """Reject candidates lacking reviewed action ownership. Never infer a boundary."""
    sid=source['source_id']; m=source['mapping']; T=source['length']
    try:
        produced = evidence.get('format') == 'egrs.augmentation.progress-evidence.v1'
        _require(source['domain']=='compound' or produced,'single/base sources need produced native multi-goal anchors')
        _require(evidence.get('file_sha256')==source['file_sha256'] and evidence.get('alignment_id')==m['alignment_id'],
                 'evidence source/time alignment mismatch')
        _require(evidence.get('provenance') in {'reviewed_local_evidence','verified_local_sim_evidence'}
                 and _text(evidence.get('reviewer')) and _text(evidence.get('basis')), 'untrusted evidence provenance')
        if source['domain']=='compound':
            _require(evidence.get('active_goals')==source['active_goals'],'evidence goal binding mismatch')
        if produced:
            _require(evidence.get('source_identity')==identity(source),'produced anchor source binding differs')
            _require(len(evidence.get('active_goals',[]))>=2,'single-goal evidence cannot claim compound progress')
            binding=evidence['binding']
            _require(binding['active_goals']==evidence['active_goals'],'produced anchor goal inventory differs')
            _require(isinstance(evidence.get('progress_anchors'),list),'produced anchors must be a list')
            if source['domain']=='compound':
                for field in ('official_task_name','active_goals','invariant_predicates'):
                    _require(binding.get(field)==source[field],'produced binding differs from fixed source '+field)
    except (ValueError,KeyError,TypeError) as exc:
        excluded.append({'source_id':sid,'reason':str(exc)});return []
    ref=identity(evidence);result=[];goals={g['id'] for g in evidence['active_goals']}
    if produced:
        from .progress import validate_anchor
        seen=set()
        for anchor in evidence.get('progress_anchors',[]):
            try:
                t=anchor['t']
                _require(t not in seen,'duplicate produced progress anchor')
                seen.add(t)
                pending=validate_anchor(source,binding,t,anchor['result'])
                _require(anchor['pending_goals']==pending,'produced pending goal facts differ')
                if not pending:continue
                # One current-anchor index only. Full instruction permits the
                # original chunk to cross the next stage; only episode end masks.
                result.append(next(_rows(source,t,T,'PROGRESS',source['instruction'],
                    evidence_ref=ref,progress_stage='pending:'+','.join(sorted(pending)))))
            except (ValueError,KeyError,TypeError) as exc:
                excluded.append({'source_id':sid,'view':'PROGRESS','reason':str(exc),'anchor':anchor})
        return result
    for kind,segments in [('PROGRESS',evidence.get('stages',[])),('ATOMIC',evidence.get('atomic_segments',[]))]:
        if not isinstance(segments,list) or any(not isinstance(s,dict) for s in segments):
            excluded.append({'source_id':sid,'view':kind,'reason':'malformed evidence segment list'})
            continue
        accepted=[]
        for segment in segments:
            try:
                start,stop=segment.get('start'),segment.get('stop')
                _require(type(start) is int and type(stop) is int and 0<=start<stop<=T,'invalid evidence interval')
                _require(not any(start<b and stop>a for a,b in accepted),'overlapping evidence intervals')
                instruction=source['instruction'];metadata={'evidence_ref':ref}
                if kind=='PROGRESS':
                    pending=segment.get('pending_goals')
                    _require(isinstance(pending,list) and len(pending)==len(set(pending)) and set(pending)<=goals,
                             'unknown pending goal stage')
                    if not pending:continue # All-final terminal poses add no parking supervision.
                    metadata['progress_stage']='pending:'+','.join(sorted(pending))
                else:
                    _require(segment.get('goal_id') in goals and segment.get('exclusive_goal_actions') is True
                             and _text(segment.get('review_basis')) and _text(segment.get('instruction')),
                             'atomic needs reviewed exclusive action ownership and exact instruction')
                    _require((start,stop)!=(0,T),'whole compound trajectory cannot be relabeled atomic')
                    instruction=segment['instruction'];metadata['goal_id']=segment['goal_id']
                accepted.append((start,stop))
                result.extend(_rows(source,start,stop,kind,instruction,**metadata))
            except ValueError as exc:
                excluded.append({'source_id':sid,'view':kind,'reason':str(exc),'segment':segment})
    return result


def resolve_local_evidence(config,sources,data_root):
    """Run a separately reviewed, hash-pinned producer on named local windows.

    This interface does not certify a producer's physics. Its module/dependencies and
    alignment/review procedures must be trusted by the operator before execution.
    This legacy hook is separate from the built-in sparse native producer.
    """
    import importlib.util
    required={'module','module_sha256','callable','producer','trust_basis','requests'}
    _require(isinstance(config,dict) and set(config)==required,'explicit local evidence provider config required')
    _require(all(_text(config[k]) for k in ('module','callable','producer','trust_basis')) and _hex(config['module_sha256']),
             'pinned local evidence producer identity required')
    source_map={s['source_id']:s for s in sources};requested={}
    _require(isinstance(config['requests'],list) and bool(config['requests']),'bounded local windows required')
    for request in config['requests']:
        sid=request.get('source_id');source=source_map.get(sid)
        _require(source is not None and source['domain']=='compound','local evidence source outside compound manifest')
        _require(sid not in requested,'duplicate local evidence request')
        windows=request.get('windows')
        _require(request.get('purpose')=='stage_anchor_and_skill_boundary' and isinstance(windows,list) and bool(windows),
                 'only stage/boundary local windows supported')
        coverage=set()
        for window in windows:
            _require(isinstance(window,list) and len(window)==2 and all(type(v) is int for v in window)
                     and 0<=window[0]<window[1]<=source['length'],'invalid local windows')
            coverage.update(range(*window))
        _require(len(coverage)<source['length'],'local windows cannot cover the full trajectory')
        requested[sid]=windows
    module_path=Path(config['module']).resolve()
    _require(file_sha256(module_path)==config['module_sha256'],'local evidence provider hash mismatch')
    spec=importlib.util.spec_from_file_location('_egrs_augmentation_local_evidence',module_path)
    _require(spec is not None and spec.loader is not None,'cannot load local evidence provider')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    callback=getattr(module,config['callable'],None)
    _require(callable(callback),'local evidence callable missing')
    result=callback(requests=copy.deepcopy(config['requests']),
                    sources={sid:copy.deepcopy(source_map[sid]) for sid in requested},data_root=str(data_root))
    _require(isinstance(result,list),'local evidence producer must return an evidence list')
    for evidence in result:
        _require(evidence.get('source_id') in requested,'producer returned unrequested source')
        windows=requested[evidence['source_id']]
        # Segment interiors can be inferred only by a trusted reviewed producer;
        # each claimed endpoint must have a requested local evidence window.
        for segment in evidence.get('stages',[])+evidence.get('atomic_segments',[]):
            for endpoint in (segment.get('start'),segment.get('stop')):
                _require(type(endpoint) is int and any(a<=endpoint<=b for a,b in windows),
                         'evidence boundary outside requested local windows')
        evidence['producer_lock']={k:config[k] for k in ('module_sha256','producer','trust_basis')}
    return result


def export_dataset(manifest,inventory,output,*,evidence=None,evidence_provider=None,progress_config=None):
    """One real-data entry, called only when the user starts the authorized export.

    Local reviewed evidence is optional. Explicit progress_config runs the built-in
    sparse producer; ordinary RAW export never constructs the native backend.
    """
    import h5py
    output=Path(output)
    if output.exists():raise FileExistsError('new export output required before any evidence production')
    sources=validate_manifest(manifest,inventory)
    root=Path(manifest['data_root']).resolve();rows=[];excluded=[];hashes={}
    # Check ordinary input identity/field shapes before invoking any backend.
    for source in sources:
        path=(root/source['file']).resolve()
        _require(path.is_relative_to(root),'HDF path escapes data_root')
        if path not in hashes:hashes[path]=file_sha256(path)
        _require(hashes[path]==source['file_sha256'],'source HDF hash mismatch')
        with h5py.File(path,'r') as hdf:inspect_source(hdf,source)
    evidence=copy.deepcopy(evidence or [])
    if evidence_provider is not None:
        evidence.extend(resolve_local_evidence(evidence_provider,sources,root))
    progress_report=None
    if progress_config is not None:
        from .progress import produce_progress
        produced,progress_report=produce_progress(progress_config,sources,root)
        # Existing trusted atomic ownership may coexist with new native anchors.
        # Preserve it as a separate evidence record; never infer ownership.
        for row in produced:
            old=next((e for e in evidence if e.get('source_id')==row['source_id']),None)
            if old is not None:
                reviewed=old
                while reviewed and reviewed.get('format')=='egrs.augmentation.progress-evidence.v1':
                    reviewed=reviewed.get('prior_reviewed_evidence')
                if reviewed is not None:
                    row['prior_reviewed_evidence']=copy.deepcopy(reviewed)
                row['prior_evidence_identity']=identity(old)
                evidence.remove(old)
            evidence.append(row)
    _require(isinstance(evidence,list),'evidence must be an array')
    by_id={e['source_id']:e for e in evidence}
    _require(len(by_id)==len(evidence),'duplicate source evidence')
    _require(set(by_id)<={s['source_id'] for s in sources},'unknown source evidence')
    fallback=[]
    for source in sources:
        path=(root/source['file']).resolve()
        _require(path.is_relative_to(root),'HDF path escapes data_root')
        if path not in hashes:hashes[path]=file_sha256(path)
        _require(hashes[path]==source['file_sha256'],'source HDF hash mismatch')
        rows.extend(_rows(source,0,source['length'],'RAW',source['instruction']))
        extra=_evidence_rows(source,by_id[source['source_id']],excluded) if source['source_id'] in by_id else []
        if source['source_id'] in by_id and by_id[source['source_id']].get('prior_reviewed_evidence'):
            prior=copy.deepcopy(by_id[source['source_id']]['prior_reviewed_evidence'])
            prior['stages']=[] # PROGRESS now uses verified anchors only.
            extra.extend(_evidence_rows(source,prior,excluded))
        rows.extend(extra)
        if not extra:fallback.append(source['source_id'])
    counts={view:{'windows':0,'valid_actions':0} for view in VIEWS}
    details={}
    for row in rows:
        for bucket in (counts[row['view']], details.setdefault('|'.join((row['task_key'],row['split'],row['view'])),
                                                             {'windows':0,'valid_actions':0})):
            bucket['windows']+=1;bucket['valid_actions']+=sum(row['action_mask'])
    report={'format':'egrs.augmentation.report.v1','base_inventory_identity':inventory['identity'],
            'source_manifest_identity':identity(manifest),'scope_ref':SCOPE_REF,
            'sources':len(sources),'base_sources':dict(Counter(s['split'] for s in sources if s['domain']=='base')),
            'compound_sources':dict(Counter(s['task_key'] for s in sources if s['domain']=='compound')),
            'candidate_source_availability':{t['key']:{'requested_max':manifest.get('compound_limit_per_task',20),
                 'actual':sum(s['domain']=='compound' and s['task_key']==t['key'] for s in sources),
                 'shortfall':manifest.get('compound_limit_per_task',20)-sum(s['domain']=='compound' and s['task_key']==t['key'] for s in sources)}
                 for t in load_scope()['tasks']},
            'counts_by_view':counts,'counts_by_task_split_view':details,
            'counts_by_progress_stage':dict(Counter('|'.join((r['split'],r['task_key'],r['progress_stage']))
                                               for r in rows if r['view']=='PROGRESS')),
            'index_view_ratios':{v:counts[v]['windows']/len(rows) for v in VIEWS},
            'requested_training_ratios':{'RAW':.5,'PROGRESS':.25,'ATOMIC':.25},
            'augmentation_available':bool(counts['PROGRESS']['windows'] or counts['ATOMIC']['windows']),
            'raw_fallback_sources':fallback,'excluded_evidence':excluded,
            'unknown_physical_ancestry_sources':[s['source_id'] for s in sources if s['physical_ancestry']=='unknown'],
            'coverage_claim':'ordinary_demonstrations_only_no_external_progress_states',
            'exclusion_attestation':manifest['exclusion_attestation'],
            'normalization_bindings':{s['source_id']:{k:s['mapping'][k] for k in
                                      ('action_normalization','proprio_normalization','alignment_id','processor_id','crop')}
                                      for s in sources},
            'evidence_identity':identity({'evidence':evidence}),
            'local_evidence_provider':evidence_provider,
            'recovery_backend':'external_hash_pinned_local_window_provider' if evidence_provider else 'trusted_local_evidence_or_RAW'}
    if progress_report is not None:
        report['progress_production']={k:progress_report[k] for k in
            ('accepted_anchors','terminal_anchors','excluded_anchors','produced_atomic_segments','identity')}
        report['recovery_backend']='builtin_sparse_progress_v1'
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    source_map={'format':'egrs.augmentation.index.v1','data_root':str(root),
                'sources':{s['source_id']:s for s in sources},'manifest_identity':identity(manifest)}
    write('sources.json',source_map);write('report.json',report);write('evidence.json',evidence)
    if progress_report is not None:write('progress_report.json',progress_report)
    (output/'windows.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows),encoding='utf-8')
    return report


def _normalize(values,norm):
    if norm['kind']=='identity_already_normalized':return values
    lo=np.asarray(norm['q01'],dtype=np.float32);hi=np.asarray(norm['q99'],dtype=np.float32)
    mask=np.asarray(norm['mask'],dtype=bool)
    result=values.copy()
    result[...,mask]=np.clip(2*(values[...,mask]-lo[mask])/(hi[mask]-lo[mask])-1,-1,1)
    return result


class AugmentationDataset:
    """Worker-safe HDF-on-demand dataset; .rows is metadata for offline sampling only."""
    def __init__(self,export_dir,split=None,views=None):
        directory=Path(export_dir);self.manifest=read_json(directory/'sources.json')
        self.report=read_json(directory/'report.json');self.sources=self.manifest['sources']
        views=set(VIEWS if views is None else views)
        _require(views<=set(VIEWS),'unknown dataset views')
        self.rows=[r for line in (directory/'windows.jsonl').read_text(encoding='utf-8').splitlines()
                   if line.strip() for r in [json.loads(line)] if (split is None or r['split']==split) and r['view'] in views]
        # Each new training/resume dataset rebinds selected original HDF bytes to
        # the exported identity. Hash shared files once, never on every item read.
        root=Path(self.manifest['data_root']).resolve()
        self._source_digests={}
        for sid in sorted({r['source_id'] for r in self.rows}):
            source=self.sources[sid]
            path=(root/source['file']).resolve()
            _require(path.is_relative_to(root),'HDF path escapes data_root')
            if path not in self._source_digests:
                self._source_digests[path]=file_sha256(path)
            _require(self._source_digests[path]==source['file_sha256'],
                     'source HDF hash mismatch since export: '+sid)

    def __len__(self):return len(self.rows)

    def validate_normalization(self,stats,unnorm_key,stats_sha256):
        """Bind each once-only transform to the original checkpoint, before training."""
        _require(unnorm_key in stats,'original normalization key missing')
        original=stats[unnorm_key]
        for source in self.sources.values():
            for field in ('action','proprio'):
                norm=source['mapping'][field+'_normalization']
                _require(norm['stats_id']==unnorm_key and norm['stats_sha256']==stats_sha256,
                         'normalization stats identity differs from original checkpoint')
                if norm['kind']=='bounds_q99':
                    expected=original.get(field,{})
                    for key in ('q01','q99','mask'):
                        # Official masks default to all dimensions if absent in released stats.
                        value=expected.get(key,[True]*len(norm['mask']) if key=='mask' else None)
                        _require(np.array_equal(norm[key],value),f'normalization {field}.{key} differs from original checkpoint')

    def __getitem__(self,index):
        import h5py
        row=self.rows[index];source=self.sources[row['source_id']];m=source['mapping']
        start,stop=row['start'],row['stop'];o=start+m['observation_offset'];a=start+m['action_offset']
        path=Path(self.manifest['data_root'])/source['file']
        with h5py.File(path,'r') as hdf:
            g=hdf[source['episode']]
            images=[np.asarray(g[key][o]) for key in m['images']]
            images=[image[::-1,::-1].copy() if transform=='rotate_180' else image
                    for image,transform in zip(images,m['image_transforms'])]
            proprio=np.concatenate([np.asarray(g[key][o],dtype=np.float32) for key in m['proprio']])
            actions=np.asarray(g[m['action']][a:a+stop-start],dtype=np.float32)*np.asarray(m['axis_sign'],dtype=np.float32)
        grip=m['gripper'];idx=grip['index']
        if grip['kind']!='identity':
            fraction=(actions[:,idx]-grip['input_closed'])/(grip['input_open']-grip['input_closed'])
            if grip['kind']=='binarize':fraction=(fraction>=.5).astype(np.float32)
            actions[:,idx]=grip['output_closed']+fraction*(grip['output_open']-grip['output_closed'])
        actions=_normalize(actions,m['action_normalization'])
        padded=np.zeros((8,7),dtype=np.float32);padded[:len(actions)]=actions
        _require(np.isfinite(actions).all() and np.isfinite(proprio).all(),'nonfinite model inputs/targets')
        proprio=_normalize(proprio,m['proprio_normalization'])
        if m['proprio_normalization']['kind']=='bounds_q99':proprio=np.clip(proprio,-1,1)
        return {'images':images,'proprio':proprio,
                'actions':padded,'action_mask':np.asarray(row['action_mask'],dtype=bool),
                'instruction':row['instruction']}


IndexedActionDataset = AugmentationDataset
