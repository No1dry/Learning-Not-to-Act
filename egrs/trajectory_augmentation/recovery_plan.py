"""Approved exact73 recovery planning using JSON and byte identities only.

Path roots relocate evidence/legacy files only. The bound original generation
configuration must still name usable execution paths on the deployment machine.
No HDF content, simulator, renderer or model is opened by this module.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from egrs.augmentation.data import identity,file_sha256,read_json,_require,_hex
from .cli import build_plan

CONFIG='task035-teacher-v2-recovery-config-v1'
TEACHER_POLICY='table-drop-unknown-diagnostic-v2'
APPROVED_REFS=Path(__file__).resolve().parents[2]/'collaboration/tasks/035_teacher_v2_recovery_refs.json'
REUSED_FILES={'file','audit_path','qualification_path','lineage_path','journal_path'}
BUDGET={'max_normal_replays':73,'max_robot_starts':219,'max_10_attempts':438,
        'horizon_per_attempt':520,'max_control_steps':265720,'initialization_wall_time_included':False}


def _inside(root,relative):
    p=Path(relative)
    _require(not p.is_absolute() and '..' not in p.parts,'legacy file must be relative and contained')
    p=(root/p).resolve()
    _require(p.is_relative_to(root),'legacy file escapes its archive root')
    return p


def _bound_file(path,digest,expected_bytes=None):
    _require(_hex(digest),'explicit original byte SHA required')
    _require(file_sha256(path)==digest,'recovery evidence bytes changed: '+str(path))
    if expected_bytes is not None:
        _require(type(expected_bytes) is int and expected_bytes>=0 and path.stat().st_size==expected_bytes,
                 'recovery evidence size changed: '+str(path))
    return path


def build_recovery_plan(config_path):
    """Validate the original180, then select the approved73 and eight v1 rows."""
    config_path=Path(config_path).resolve();config=read_json(config_path)
    _require(set(config)=={'format','evidence','path_roots'} and config['format']==CONFIG,
             'explicit teacher v2 recovery configuration required')
    roots=config['path_roots']
    _require(isinstance(roots,dict) and all(isinstance(k,str) and k and isinstance(v,str) and v for k,v in roots.items()),
             'explicit evidence-only path prefix mapping required')
    def relocate(value):
        value=str(value).replace('\\','/')
        for old,new in sorted(roots.items(),key=lambda pair:-len(pair[0])):
            old=old.replace('\\','/').rstrip('/')
            if value==old or value.startswith(old+'/'):
                value=new.rstrip('/\\')+value[len(old):];break
        path=Path(value).expanduser()
        return (config_path.parent/path).resolve() if not path.is_absolute() else path.resolve()
    evidence=read_json(relocate(config['evidence']));approved=read_json(APPROVED_REFS)
    _require(identity(approved)==approved.get('identity') and identity(evidence)==evidence.get('identity')
             and evidence==approved,'recovery evidence differs from the approved exact73/eight binding')
    _require(evidence.get('format')=='task035-recovery-evidence-v1'
             and evidence.get('teacher_policy')==TEACHER_POLICY and evidence.get('new_budget')==BUDGET,
             'approved teacher policy and bounded recovery recipe required')
    def bound(ref):
        return _bound_file(relocate(ref['path']),ref['sha256'])
    manifest_path=bound(evidence['original_seed_manifest'])
    generation_path=bound(evidence['original_generation_config'])
    # Original config-relative path semantics and grouped split remain the
    # existing CLI's responsibility. Never give its natural-firstN validator a
    # gapped recovery subset or rewrite/replace the original bound config.
    original=build_plan(generation_path)
    _require(Path(original['config']['manifest']).resolve()==manifest_path,
             'original generation config is not bound to the approved seed manifest')
    original_sources=original['sources'];by_parent={s['source_id']:s for s in original_sources}
    _require(len(original_sources)==180 and evidence['original_seed_manifest']['parent_count']==180
             and len(by_parent)==180,'the complete original180 must be validated before selecting recovery sources')
    bound(evidence['candidate_analysis']);bound(evidence['reused_file_references'])
    legacy=relocate(evidence['legacy_run_root'])
    _bound_file(legacy/'generation_report.json',evidence['legacy_reports']['generation_report_sha256'])
    _bound_file(legacy/'export/report.json',evidence['legacy_reports']['export_report_sha256'])
    candidates=evidence['candidates'];candidate_ids=[c['parent_demo_id'] for c in candidates]
    _require(len(candidates)==73 and len(set(candidate_ids))==73,'exact73 distinct recovery parents required')
    _require(Counter(c['split'] for c in candidates)=={'train':53,'dev':20}
             and evidence['candidate_split']=={'train':53,'dev':20},'approved53/20 split required')
    selected=[]
    for c in candidates:
        p=by_parent.get(c['parent_demo_id'])
        _require(p is not None and p['task_key']==c['task_key'] and p['split']==c['split'],
                 'candidate does not match its original grouped parent')
        _require(c.get('legacy_qualified') is False and c.get('candidate_only_pending_v2_and_new_recording') is True
                 and c.get('rgb_training_hdf_exists') is False,'legacy candidates cannot be relabeled successes')
        qpath=_bound_file(relocate(c['qualification_file']),c['qualification_sha256'])
        mpath=_bound_file(relocate(c['metadata_file']),c['metadata_sha256'])
        _require(qpath.is_relative_to(legacy) and mpath.is_relative_to(legacy),'candidate evidence escapes legacy run')
        q=read_json(qpath);m=read_json(mpath);analysis=q.get('core_analysis',{})
        unknown=analysis.get('event_unknown')
        _require(q.get('qualified') is False and q.get('failure_reason')=='core_violation_evidence_unknown'
                 and type(q.get('core_release_confirmation_streak')) is int and q['core_release_confirmation_streak']>=5
                 and isinstance(unknown,list) and bool(unknown)
                 and all(isinstance(e,dict) and e.get('event')=='table_drop' for e in unknown)
                 and analysis.get('confirmed_events')==[],
                 'candidate is not rejected solely for table_drop unknown with release confirmation')
        _require(m.get('source_id')==p['source_id']+'__normal__vnormal__a0'
                 and m.get('parent_demo_id')==p['source_id'] and m.get('task_key')==p['task_key']
                 and m.get('split')==p['split'] and m.get('parent_file_sha256')==p['file_sha256']
                 and m.get('domain')=='normal' and m.get('variant')=='normal' and m.get('attempt')==0
                 and m.get('qualified') is False and m.get('status')=='rejected' and m.get('file') is None
                 and m.get('failure_reason')==q['failure_reason'] and m.get('qualification',{}).get('accepted') is False
                 and {k:v for k,v in m['qualification'].items() if k!='accepted'}==q,
                 'candidate metadata disagrees with its rejected qualification/original parent')
        selected.append(deepcopy(p))
    export=read_json(bound(evidence['reused_export_sources']))
    _require(export.get('format')=='task035-generated-trajectories-v1'
             and identity(export)==export.get('identity'),'legacy source export identity differs')
    export_parents={p['source_id']:p for p in export['parents']}
    _require(len(export['parents'])==180 and export_parents==by_parent,'legacy export parent grouping differs')
    _require(relocate(export['data_root'])==legacy,'legacy export data root differs')
    reused_refs=evidence['reused_sources'];reused_ids=[r['source_id'] for r in reused_refs]
    _require(len(reused_refs)==8 and len(set(reused_ids))==8 and set(export['sources'])==set(reused_ids),
             'exact eight approved legacy qualified sources required')
    reused=[]
    for r in reused_refs:
        s=deepcopy(export['sources'][r['source_id']]);p=by_parent.get(r['parent_demo_id'])
        _require(p is not None and p['source_id'] not in candidate_ids and p['split']=='train',
                 'reused source overlaps recovery or has an altered parent split')
        for key in ('source_id','parent_demo_id','task_key','split','domain','length','file_sha256'):
            _require(s.get(key)==r.get(key),'reused source identity differs: '+key)
        _require(s.get('parent_file_sha256')==p['file_sha256'] and s.get('instruction')==p['instruction']
                 and s.get('source_group')==p['source_group'] and s.get('task_key')==p['task_key']
                 and s.get('split')==p['split'] and s.get('qualified') is True and s.get('status')=='completed'
                 and s.get('qualification',{}).get('accepted') is True,
                 'reused source is not unchanged v1-qualified data from the original parent')
        _require(set(r['files'])==REUSED_FILES,'complete original HDF/qualification/audit/lineage/journal references required')
        for key,f in r['files'].items():
            _require(s.get(key)==f['relative_path'],'reused artifact path differs')
            _bound_file(_inside(legacy,f['relative_path']),f['sha256'],f['bytes'])
        _require(r['files']['file']['sha256']==s['file_sha256'],'reused HDF identity differs')
        q=read_json(_inside(legacy,s['qualification_path']))
        _require(q.get('qualified') is True and q.get('failure_reason') is None,
                 'reused original v1 qualification is not accepted')
        reused.append(s)
    _require(Counter(s['domain'] for s in reused)=={'normal':2,'10':6}
             and len({s['parent_demo_id'] for s in reused})==2,'exact two normal/six10 from two old train parents required')
    population={'original_parent_sources':180,'recovery_parent_sources':73,'recovery_split':{'train':53,'dev':20},
        'reused_trajectories':8,'reused_parent_sources':2,**BUDGET}
    plan={'format':'task035-teacher-v2-recovery-plan-v1','teacher_policy':TEACHER_POLICY,
        'original_plan':original,'sources':selected,'reused_sources':reused,'evidence':evidence,
        'evidence_identity':evidence['identity'],'legacy_root':str(legacy),'population':population,
        'simulation_created':False,'model_loaded':False,
        'selection':'validate original180 and grouped split, then select only approved73; reuse eight without replay'}
    plan['identity']=identity(plan)
    return plan
