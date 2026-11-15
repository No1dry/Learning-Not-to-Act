"""User-started once-only JSON sidecar. Never reads HDF/image/model payloads."""
from collections import Counter
from pathlib import Path
import json

from .contracts import (INDEX_IDENTITY, MAX_KEYS, SIDECAR_FORMAT, TEMPLATE_VERSION,
    require, read_json, write_json, identity, sha, lines, status_text, forbid_overlap)


def metadata(index_dir):
    root = Path(index_dir).resolve()
    control, report, seal = (read_json(root/n) for n in ('sources.json','report.json','identity.json'))
    require(control.get('format') == 'task040-task-control-sources-v1'
        and identity(control) == control.get('identity') == INDEX_IDENTITY
        and report.get('sources_identity') == INDEX_IDENTITY
        and identity(report) == report.get('identity') == seal.get('report_identity')
        and seal.get('sources_identity') == INDEX_IDENTITY, 'Pinned040 metadata identity differs')
    ret_dir = Path(control['retention_index']).resolve()
    ret, rr = (read_json(ret_dir/n) for n in ('sources.json','report.json'))
    require(identity(ret) == ret.get('identity') == control['retention_identity'] == rr.get('sources_identity')
        and identity(rr) == rr.get('identity'), 'Retention metadata seal differs')
    row_file = ret_dir/'rows.jsonl'
    require(sha(row_file) == rr['rows_sha256'], 'Original main rows hash differs')
    rows = lines(row_file)
    require(len(rows) == rr['rows'] == MAX_KEYS, 'Original main population differs')
    require(len({(r['source_id'],r['observation_index']) for r in rows}) == len(rows), 'Duplicate original main key')
    groups = {}
    for r in rows:
        s = ret['sources'][r['source_id']]
        require(r['split'] in ('train','dev') and r['pool'] in ('ten','fresh','raw'), 'Foreign row split/pool')
        require(all(r[k] == s[k] for k in ('split','pool','task_key','source_group','instruction')), 'Row/source binding differs')
        require(type(r['observation_index']) is int and 0 <= r['observation_index'] < s['observation_count'], 'Invalid observation time')
        previous = groups.setdefault(r['source_group'],r['split'])
        require(previous == r['split'], 'Parent group crosses train/dev')
    inputs = {str(p):sha(p) for p in (root/'sources.json',root/'report.json',root/'identity.json',
                                    ret_dir/'sources.json',ret_dir/'report.json',row_file)}
    return control, ret, rows, inputs


def source_facts(source, ret, control, inputs):
    # Raw has no recorded labels; do not touch its HDF or invent facts.
    if source['pool'] == 'raw':
        return None
    from egrs.task_control.index import _semantics, _active_values
    from egrs.augmentation.data import load_scope
    original = source['original_source']
    parent = ret['parents'][source['parent_demo_id']]
    scope = {t['key']:t for t in load_scope()['tasks']}
    require(all(parent[k] == source[k] for k in ('split','source_group','task_key','instruction')), 'Recorded parent binding differs')
    root = Path(ret['data_roots'][source['root_key']])
    declared = {**ret.get('inputs',{}), **control.get('inputs',{})}
    payloads, digests = {}, {}
    for kind in ('audit','lineage'):
        name = original[kind+'_path']
        p = (root/name).resolve()
        require(p.suffix == '.json', 'Only recorded JSON facts may be opened')
        expected = declared.get(str(p), original.get(kind+'_sha256'))
        require(isinstance(expected,str) and len(expected) == 64, 'Recorded JSON lacks admitted hash: '+kind)
        actual = sha(p)
        require(actual == expected, 'Recorded JSON bytes changed: '+kind)
        inputs[str(p)] = actual
        payloads[kind] = read_json(p)
        digests[kind] = actual
    audit, lineage = payloads['audit'], payloads['lineage']
    full_parent = lineage.get('source',{})
    require(all(full_parent.get(k) == parent.get(k) for k in
        ('source_id','file_sha256','source_group','split','task_key','instruction')), 'Recorded lineage parent differs')
    require(full_parent.get('active_goals') == scope[source['task_key']]['active_goals']
        and full_parent.get('invariant_predicates') == scope[source['task_key']]['invariant_predicates'], 'Task predicate binding differs')
    frames = audit.get('frames',[])
    require(len(frames) == source['observation_count'] == original['length']+1, 'T+1 recorded frame binding differs')
    semantics = _semantics(full_parent,lineage)
    # Retain only tiny current fact vectors, not all recorded physical states.
    return {'values':[_active_values(frame.get('facts',{}),semantics) for frame in frames],
            'audit_sha256':digests['audit'], 'lineage_sha256':digests['lineage'],
            'semantics_sha256':identity(semantics)}


def build_sidecar(index_dir, output, *, progress=None):
    control, ret, rows, inputs = metadata(index_dir)
    out = forbid_overlap(output, [index_dir,control['retention_index'],*ret['data_roots'].values()])
    require(not out.exists(), 'Sidecar output already exists; preserve prior attempt')
    # Claim once before reading facts; partial failures remain visible, not overwritten.
    out.mkdir(parents=True)
    write_json(out/'production_started.json', {'format':SIDECAR_FORMAT,'max_keys':MAX_KEYS,'index_identity':INDEX_IDENTITY})
    cache, counts, missing = {}, Counter(), Counter()
    target = out/'status.jsonl'
    try:
        with target.open('w',encoding='utf-8') as stream:
            for n,row in enumerate(rows,1):
                sid = row['source_id']
                if sid not in cache:
                    cache[sid] = source_facts(ret['sources'][sid],ret,control,inputs)
                facts = cache[sid]
                values = None if facts is None else facts['values'][row['observation_index']]
                text = status_text(row['task_key'], values)
                eligible = row['pool'] == 'ten' and text is not None
                record = {k:row[k] for k in ('source_id','observation_index','split','pool','task_key','source_group','instruction')}
                record.update(format=SIDECAR_FORMAT, template_version=TEMPLATE_VERSION,
                    goals=values, text=text, hint_eligible=eligible,
                    evidence=None if facts is None else {k:v for k,v in facts.items() if k != 'values'},
                    missing_reason=None if text is not None else 'recorded_current_goal_facts_unavailable')
                stream.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
                counts['|'.join((row['split'],row['pool'],row['task_key'],'eligible' if eligible else 'not_eligible'))] += 1
                if text is None: missing[row['pool']] += 1
                if n == 1 or n % 1000 == 0 or n == len(rows):
                    info = {'phase':'status_text','completed':n,'expected':len(rows),'percent':100*n/len(rows)}
                    write_json(out/'progress.json',info)
                    (progress or (lambda x:print(json.dumps(x),flush=True)))(info)
        manifest = {'format':SIDECAR_FORMAT,'template_version':TEMPLATE_VERSION,'index_identity':INDEX_IDENTITY,
            'index_dir':str(Path(index_dir).resolve()),'rows':len(rows),'rows_sha256':sha(target),'inputs':inputs,
            'coverage':dict(counts),'missing':dict(missing),
            'training_ready':any(k.startswith('train|ten|') and k.endswith('|eligible') and v for k,v in counts.items()),
            'image_pixels_read':False,'model_loaded':False,'simulation_created':False}
        manifest['identity'] = identity(manifest)
        write_json(out/'manifest.json',manifest)
        write_json(out/'progress.json', {'phase':'complete','completed':len(rows),'expected':len(rows),'percent':100.,'training_ready':manifest['training_ready']})
        return manifest
    except BaseException as error:
        write_json(out/'preparation_error.json', {'error':type(error).__name__+': '+str(error),'partial_preserved':True})
        raise


class Sidecar:
    def __init__(self, directory, index_dir):
        root = Path(directory).resolve()
        self.manifest = read_json(root/'manifest.json')
        m = self.manifest
        require(m.get('format') == SIDECAR_FORMAT and m.get('template_version') == TEMPLATE_VERSION
            and identity(m) == m.get('identity') and m['index_identity'] == INDEX_IDENTITY
            and Path(m['index_dir']).resolve() == Path(index_dir).resolve()
            and m['rows'] == MAX_KEYS and sha(root/'status.jsonl') == m['rows_sha256'], 'Sidecar identity/binding differs')
        for path,digest in m['inputs'].items():
            require(Path(path).suffix in ('.json','.jsonl') and sha(path) == digest, 'Sidecar recorded JSON input changed')
        records = lines(root/'status.jsonl')
        self.records = {(r['source_id'],r['observation_index']):r for r in records}
        require(len(records) == len(self.records) == m['rows'], 'Sidecar key population differs')
        for r in records:
            text = status_text(r['task_key'],r['goals'])
            require(r['text'] == text and r['hint_eligible'] is (r['pool']=='ten' and text is not None)
                and r['template_version'] == TEMPLATE_VERSION, 'Status text/eligibility differs from current facts')
        actual_ready = any(r['split']=='train' and r['pool']=='ten' and r['hint_eligible'] for r in records)
        require(m['training_ready'] is actual_ready, 'Sidecar readiness differs from actual recorded keys')
        require(actual_ready, 'Zero eligible train hints; do not silently fall back to no-hint H1')

    def for_row(self, row):
        r = self.records[(row['source_id'],row['observation_index'])]
        require(all(r[k] == row[k] for k in ('split','pool','task_key','source_group','instruction')), 'Sidecar/main row mismatch')
        return r
