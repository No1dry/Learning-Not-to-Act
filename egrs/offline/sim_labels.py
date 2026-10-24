"""Deterministic observable labels from annotation-only operational facts."""
from egrs.contracts import validate_prediction
from .sim_contract import mapping_for, validate_frame_facts, entity_aliases


def build_answer(sample, frame_facts, *, frame):
    """Return answer/provenance/gaps/supervised_state_query; never mutate sample.

    The controller binds physical frame to the original window's current query.
    It must use the same worker alias table for every window of a source. Each
    evidence box must contain all named visible components (not projected or
    hidden geometry). Supports are independently gated for each emitted field.
    """
    if frame_facts.get('format') == 'egrs.sim.frame-consensus.v1':
        from .sim_consensus import build_consensus_answer
        return build_consensus_answer(sample, frame_facts, frame=frame)
    facts=validate_frame_facts(frame_facts)
    return _build_answer_core(sample, facts, frame=frame, evidence_authorized=facts['alignment']['accepted'])


def _build_answer_core(sample, facts, *, frame, evidence_authorized):
    """Shared field construction; callers first validate their distinct evidence proof.

    This does not assert unique physical alignment. The consensus caller may
    authorize an individual camera's evidence without changing alignment.accepted.
    """
    if facts['source_id'] != sample['source_id'] or facts['frame'] != frame:
        raise ValueError('source/frame binding mismatch')
    context=sample['payload']['context']; registry=context['registry']; query=context['query_id']
    mapping=mapping_for(registry)
    source_aliases=entity_aliases(mapping)
    by_ref={g['goal_ref']:g for g in facts['goals']}
    if set(by_ref) != {g['goal_ref'] for g in mapping}:
        raise ValueError('fact goal binding mismatch')
    current=[s for s in sample['payload']['sensor'] if s['query_id']==query and s['snapshot_id']==f'q{query}']
    if len(current)!=1:
        raise ValueError('current query snapshot binding mismatch')
    observation=current[0]['observation']
    cameras=set()
    for name,aliases in [('agentview',('agentview_image','image')),('wrist',('robot0_eye_in_hand_image','wrist_image'))]:
        nested=observation.get('images',{})
        if any(k in observation for k in aliases) or name in nested or (name=='wrist' and 'robot0_eye_in_hand' in nested):
            cameras.add(name)
    answer={'query_id':query,'goals':[]}; provenance={}; gaps=[]; supervised_state=False
    for i,m in enumerate(mapping):
        f=by_ref[m['goal_ref']]
        if f['entity_ref'] is not None and f['entity_ref'] != source_aliases[m['atom'][1]]:
            raise ValueError('source-stable entity alias binding mismatch')
        if f['kind'] != m['kind']:
            raise ValueError('fact kind binding mismatch')
        row={'goal_ref':m['goal_ref'],'entity_ref':None,'association':'UNKNOWN','role':'UNKNOWN',
             'relation':'UNKNOWN','interaction':'UNKNOWN',
             'release':'NOT_APPLICABLE' if m['kind']=='mechanism' else 'UNKNOWN','evidence':[]}
        eligible=[]
        if evidence_authorized and f['entity_ref'] is not None:
            for e in f['evidence']:
                if e['camera'] not in cameras:
                    raise ValueError('evidence camera binding mismatch')
                components=set(e['components']); support=set(e['supports']); allowed=set()
                if set(m['identity_components']) <= components:
                    allowed |= support & {'entity','role'}
                if set(m['relation_components']) <= components and f['native_truth'] is not None:
                    allowed |= support & {'relation'}
                if set(m['interaction_components']) <= components and f['grasp'] != 'unknown':
                    allowed |= support & {'interaction','release'}
                eligible.append((e,allowed))
        supported=set().union(*(s for _,s in eligible)) if eligible else set()
        if 'entity' in supported:
            row['entity_ref']=f['entity_ref']; row['association']='MATCHED'
            if 'role' in supported:
                row['role']='TARGET'
            if 'relation' in supported:
                row['relation']='SAT' if f['native_truth'] else 'UNSAT'
            if 'interaction' in supported:
                row['interaction']='HELD' if f['grasp']=='dual_pad' else 'NOT_HELD'
            if 'release' in supported and m['kind']=='transport':
                row['release']='NOT_RELEASED' if f['grasp']=='dual_pad' else 'RELEASED'
            for e,support in eligible:
                support={s for s in support if s=='entity' or row[s] not in {'UNKNOWN','NOT_APPLICABLE'}}
                if support:
                    row['evidence'].append({'goal_ref':m['goal_ref'],'entity_ref':f['entity_ref'],
                        'query_id':query,'snapshot_id':f'q{query}','camera':e['camera'],
                        'bbox':e['bbox'],'coordinate_system':'normalized_xyxy','supports':sorted(support)})
            for field in ('entity_ref','association','role','relation','interaction','release'):
                if row[field] is not None and row[field] not in {'UNKNOWN','NOT_APPLICABLE'}:
                    provenance[f'/goals/{i}/{field}']='sim_supervised'
            for j in range(len(row['evidence'])):
                provenance[f'/goals/{i}/evidence/{j}']='sim_supervised'
        for field in ('relation','interaction','release'):
            if row[field]=='UNKNOWN':
                gaps.append({'goal_ref':m['goal_ref'],'field':field,'reason':
                    'alignment_unresolved' if not facts['alignment']['accepted'] else 'missing_visible_support_or_native_certificate'})
            elif row[field]!='NOT_APPLICABLE':
                supervised_state=True
        answer['goals'].append(row)
    validate_prediction(answer,registry,query,sample['payload']['sensor'])
    return {'answer':answer,'provenance':provenance,'gaps':gaps,'supervised_state_query':supervised_state}
