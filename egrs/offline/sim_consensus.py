"""Versioned observable field consensus. No native runtime or model imports.

Unique physical correspondence is deliberately NOT asserted by this protocol.
All numerical gates and candidate memberships are rebuilt at export time.
"""
from copy import deepcopy
import json
import math

PROTOCOL = 'egrs.sim.frame-view-field-consensus.v1'
FORMAT = 'egrs.sim.frame-consensus.v1'
RULES = ('same_state', 'next_state', 'replay_action')
CAMERAS = ('agentview', 'wrist')
ORIENTATIONS = ('identity', 'flip_vertical')
FIELDS = ('entity_ref', 'association', 'role', 'relation', 'interaction', 'release')
SUPPORT = dict(entity_ref='entity', association='entity', role='role',
               relation='relation', interaction='interaction', release='release')


def unresolved_alignment():
    return dict(format='egrs.sim.alignment.v1', accepted=False, rule=None,
                basis=[], orientation='identity', boundary_policy='gap', threshold=.03,
                comparisons=[], reason='not_a_unique_physical_alignment_certificate')


def legacy_candidate_fact(value, goals):
    return dict(format='egrs.sim.frame.v1', source_id=value['source_id'],
                frame=value['frame'], alignment=unresolved_alignment(), goals=deepcopy(goals))


def camera_decision(report, threshold=.03, minimum=16):
    if report.get('error'):
        return dict(status='unknown', orientation=None, score=None)
    passed=[]; unavailable=False
    for orientation in ORIENTATIONS:
        metric=report['orientations'][orientation]
        score=metric['original_max_metric']
        if score is None or metric['foreground_pixels']<minimum:
            unavailable=True
        elif score<=threshold:
            passed.append((orientation,score))
    if len(passed)==1:
        return dict(status='pass',orientation=passed[0][0],score=passed[0][1])
    return dict(status='unknown' if unavailable or len(passed)>1 else 'fail',
                orientation=None,score=None)


def candidate_decision(candidate):
    if candidate['error']:
        return 'indeterminate',{}
    views={c:camera_decision(candidate['cameras'][c]) for c in CAMERAS}
    if any(v['status']=='pass' for v in views.values()):return 'admitted',views
    if all(v['status']=='fail' for v in views.values()):return 'excluded',views
    return 'indeterminate',views


def validate_consensus_fact(value):
    json.dumps(value,allow_nan=False)
    required={'format','source_id','frame','T','threshold','min_visible_pixels','boundary_gap','candidates'}
    if set(value)!=required or value['format']!=FORMAT:
        raise ValueError('invalid consensus frame schema')
    if not isinstance(value['source_id'],str) or not value['source_id']:
        raise ValueError('consensus source identity required')
    if (type(value['T']) is not int or type(value['frame']) is not int
            or not 0<=value['frame']<value['T'] or value['threshold']!=.03
            or value['min_visible_pixels']!=16 or type(value['boundary_gap']) is not bool):
        raise ValueError('consensus frame/budget/gate mismatch')
    if value['boundary_gap']:
        if value['frame']+1<value['T'] or value['candidates']!=[]:
            raise ValueError('consensus cannot invent a boundary gap')
        return deepcopy(value)
    if value['frame']+1>=value['T'] or len(value['candidates'])!=3:
        raise ValueError('all three nonboundary candidates required')
    from .sim_contract import validate_frame_facts
    for candidate,rule in zip(value['candidates'],RULES):
        if set(candidate)!={'rule','state_index','action_index','cameras','goals','error'}:
            raise ValueError('invalid consensus candidate schema')
        if (candidate['rule']!=rule or candidate['state_index']!=value['frame']+(rule=='next_state')
                or candidate['action_index']!=(value['frame'] if rule=='replay_action' else None)):
            raise ValueError('consensus operation binding mismatch')
        if candidate['error'] is not None:
            if not isinstance(candidate['error'],str) or not candidate['error']:
                raise ValueError('candidate exception must be explicit')
            continue
        if set(candidate['cameras'])!=set(CAMERAS):raise ValueError('both original cameras required')
        for report in candidate['cameras'].values():
            if set(report)!={'error','orientations'}:raise ValueError('invalid camera certificate')
            if report['error']:
                if not isinstance(report['error'],str) or report['orientations']!={}:
                    raise ValueError('camera failure cannot contain scores')
                continue
            if set(report['orientations'])!=set(ORIENTATIONS):raise ValueError('both orientation tests required')
            for metric in report['orientations'].values():
                for key in ('whole_mae','foreground_mae','background_mae','original_max_metric'):
                    x=metric[key]
                    if x is not None and (type(x) not in (float,int) or not math.isfinite(x) or not 0<=x<=1):
                        raise ValueError('invalid RGB residual')
                n,fg,bg=(metric[k] for k in ('whole_pixels','foreground_pixels','background_pixels'))
                if any(type(x) is not int for x in (n,fg,bg)) or n<1 or fg<0 or bg<0 or fg+bg!=n:
                    raise ValueError('invalid RGB support counts')
                expected=None if fg<16 else max(metric['whole_mae'],metric['foreground_mae'])
                if metric['original_max_metric']!=expected:
                    raise ValueError('original RGB gate was changed')
        validate_frame_facts(legacy_candidate_fact(value,candidate['goals']))
    return deepcopy(value)


def build_consensus_answer(sample,value,*,frame):
    from .sim_labels import _build_answer_core
    from .sim_contract import mapping_for
    from egrs.contracts import validate_prediction
    value=validate_consensus_fact(value)
    if value['source_id']!=sample['source_id'] or value['frame']!=frame:
        raise ValueError('consensus source/frame binding mismatch')
    mapped=mapping_for(sample['payload']['context']['registry'])
    empty=[dict(goal_ref=g['goal_ref'],kind=g['kind'],entity_ref=None,
                native_truth=None,grasp='unknown',evidence=[]) for g in mapped]
    result=_build_answer_core(sample,legacy_candidate_fact(value,empty),frame=frame,evidence_authorized=False)
    decisions=[]; admitted=[];indeterminate=False
    for candidate in value['candidates']:
        status,views=candidate_decision(candidate)
        decisions.append(dict(rule=candidate['rule'],membership=status,views=views))
        if status=='indeterminate':indeterminate=True
        if status=='admitted':
            goals=deepcopy(candidate['goals'])
            for goal in goals:
                goal['evidence']=[e for e in goal['evidence'] if views[e['camera']]['status']=='pass']
            answer=_build_answer_core(sample,legacy_candidate_fact(value,goals),frame=frame,evidence_authorized=True)['answer']
            admitted.append((candidate,views,answer))
    result['certificate']=dict(protocol=PROTOCOL,candidates=decisions,fields=[])
    if value['boundary_gap'] or indeterminate or not admitted:
        reason='boundary_gap' if value['boundary_gap'] else 'candidate_indeterminate' if indeterminate else 'no_matched_candidate'
        for gap in result['gaps']:gap['reason']=reason
        return result
    provenance={};gaps=[]
    for i,row in enumerate(result['answer']['goals']):
        selected=[];why={}
        for field in FIELDS:
            vals=[answer['goals'][i][field] for _,_,answer in admitted]
            if any(v in (None,'UNKNOWN','NOT_APPLICABLE') for v in vals):
                why[field]='candidate_field_unknown';continue
            if any(v!=vals[0] for v in vals[1:]):
                why[field]='candidate_value_conflict';continue
            if field not in ('entity_ref','association') and row['entity_ref'] is None:
                why[field]='entity_not_observable';continue
            common=set(CAMERAS)
            for _,views,answer in admitted:
                common&={e['camera'] for e in answer['goals'][i]['evidence']
                         if SUPPORT[field] in e['supports'] and views[e['camera']]['status']=='pass'}
            common={c for c in common if len({views[c]['orientation'] for _,views,_ in admitted})==1}
            if not common:
                why[field]='no_common_supported_camera';continue
            camera=min(common,key=lambda c:(max(v[c]['score'] for _,v,_ in admitted),c))
            candidate,views,answer=min(admitted,key=lambda x:(x[1][camera]['score'],RULES.index(x[0]['rule'])))
            row[field]=vals[0]
            provenance[f'/goals/{i}/{field}']='sim_supervised'
            for e in answer['goals'][i]['evidence']:
                if e['camera']==camera and SUPPORT[field] in e['supports']:
                    copied=deepcopy(e);copied['supports']=[SUPPORT[field]];selected.append(copied)
            result['certificate']['fields'].append(dict(goal_ref=row['goal_ref'],field=field,
                camera=camera,representative=candidate['rule'],candidates=[x[0]['rule'] for x in admitted]))
        merged={}
        for e in selected:
            k=(e['camera'],tuple(e['bbox']),e['snapshot_id'])
            if k not in merged:merged[k]=e
            else:merged[k]['supports']=sorted(set(merged[k]['supports'])|set(e['supports']))
        row['evidence']=list(merged.values())
        for j in range(len(row['evidence'])):provenance[f'/goals/{i}/evidence/{j}']='sim_supervised'
        for field in ('relation','interaction','release'):
            if row[field]=='UNKNOWN':gaps.append(dict(goal_ref=row['goal_ref'],field=field,reason=why.get(field,'no_consensus')))
    validate_prediction(result['answer'],sample['payload']['context']['registry'],
                        sample['payload']['context']['query_id'],sample['payload']['sensor'])
    result['provenance']=provenance;result['gaps']=gaps
    result['supervised_state_query']=any(g[f] not in ('UNKNOWN','NOT_APPLICABLE')
        for g in result['answer']['goals'] for f in ('relation','interaction','release'))
    return result


def load_parent(path,windows):
    """Verify legacy physical proofs; reuse is selected by proof, never label sign."""
    from pathlib import Path
    from .common import read,verify,digest
    from .sim import ARTIFACT_FILES,_inputs,sha256_file,_jsonl
    from .sim_contract import validate_frame_facts
    from .sim_labels import build_answer
    path=Path(path).resolve(strict=True);root=path.parent
    manifest=verify(read(path),'egrs.sim.annotations.v1')
    if set(manifest['files'])!=ARTIFACT_FILES:raise ValueError('parent artifact set changed')
    for name,h in manifest['files'].items():
        if sha256_file(root/name)!=h:raise ValueError('parent file hash changed: '+name)
    config=read(root/'backend-config.json');inventory=read(root/'inventory.json');registries=read(root/'registries.json')
    _,requests,originals,bindings=_inputs(inventory,windows,registries,config,require_worker_runtime=False)
    if (manifest['inputs']!=config['expected'] or manifest['config_identity']!=digest(config)
            or manifest['source_splits']!=inventory['source_splits']
            or manifest['code']['identity']!=digest(manifest['code']['files'])):
        raise ValueError('parent identities differ')
    if config['identity_scope']=='production' and (
            manifest['identity']!='318c572532ac3f489d6da59e51039466579664501c69bed1fa113be3345549b4'
            or manifest['code']['identity']!='b63e47c9c690937b528f5c03616db51b1f44b78971dd284f5d013241634d5a06'):
        raise ValueError('unapproved production parent')
    if _jsonl(root/'requests.jsonl')!=list(requests.values()):raise ValueError('parent requests changed')
    accepted=set();facts={}
    with (root/'events.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            # Keep this streaming: inspection and source results contain large
            # redundant XML; no need to retain them in memory to reuse facts.
            if '"type":"alignment"' not in line and '"type":"frame"' not in line and '"type": "alignment"' not in line and '"type": "frame"' not in line:continue
            e=json.loads(line)
            if e.get('type')=='alignment' and e['data'].get('accepted'):accepted.add(e['source_id'])
            if e.get('type')=='frame':
                f=validate_frame_facts(e['data']);key=(f['source_id'],f['frame'])
                if key in facts:raise ValueError('duplicate parent frame')
                facts[key]=f
    statuses={x['source_id']:x for x in manifest['source_results']}
    cached={}
    for sid in accepted:
        if sid not in requests or statuses[sid]['status']!='complete':continue
        selected={x['frame']:facts.get((sid,x['frame'])) for x in requests[sid]['frames']}
        if any(x is None for x in selected.values()):raise ValueError('parent accepted source missing facts')
        cached[sid]=selected
    records=_jsonl(root/'annotations.jsonl')
    if len(records)!=len(originals):raise ValueError('parent sample count changed')
    supervised=0
    for row,original in zip(records,originals):
        if {k:v for k,v in row.items() if k not in {'answer','provenance'}}!={k:v for k,v in original.items() if k not in {'answer','provenance'}}:
            raise ValueError('parent changed input/history/group/order')
        sid,frame=bindings[row['sample_id']]
        if sid in cached:
            result=build_answer(original,cached[sid][frame],frame=frame)
            if row['answer']!=result['answer'] or row['provenance']!=result['provenance']:
                raise ValueError('parent label does not reconstruct from physical proof')
            supervised+=int(result['supervised_state_query'])
    return dict(path=str(path),manifest=manifest,inventory=inventory,registries=registries,
                config=config,cached=cached,supervised=supervised)


def label_consensus(parent_path,windows,output):
    from .sim import label_sim
    parent=load_parent(parent_path,windows)
    config=deepcopy(parent['config']);config['annotation_protocol']=PROTOCOL
    return label_sim(parent['inventory'],windows,parent['registries'],config,output,parent=parent)
