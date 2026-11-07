"""Once-only Task038 supervision index over existing qualified recordings.

Index construction reads JSON facts/state records and HDF structure, never RGB
pixels, action payloads, a policy, or an environment.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from egrs.augmentation.data import (_instruction, _require, file_sha256, identity,
                                    load_scope, read_json)
from egrs.retention.data import RetentionDataset, _contained
from egrs.trajectory_augmentation.data import DATA_KIND as GENERATED_KIND

DATA_KIND = 'task038-task-control-data-v1'
SOURCES_KIND = 'task038-task-control-sources-v1'


@dataclass(frozen=True)
class IndexContract:
    """Explicit alternate data identity; the038 default stays bound to036."""
    sources_kind: str
    identity_kind: str
    dataset_factory: object
    metadata: dict
    progress: object = None


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def _semantics(parent, lineage):
    """Bind recorded active facts by their predicates, never official position."""
    active = parent['active_goals']
    required_open = {
        'bowl_drawer_close': [['open','white_cabinet_1_bottom_region']],
        'mug_microwave_close': [['open','microwave_1']],
    }.get(parent['task_key'], [])
    _require([g['predicate'] for g in active if g['predicate'][0] == 'close']
             == [['close',p[1]] for p in required_open], 'required-open source close predicate differs')
    declared = lineage.get('task_semantics', lineage.get('native', {}).get('task_semantics'))
    if declared is None:
        # Existing035 frames.goals was already produced by read_goal_facts with
        # source-bound active semantics; old lineage does not store a new field.
        return {'active_predicates': [g['predicate'] for g in active],
                'basis': 'existing035 source-bound active facts.goals',
                'invariant_predicates': parent['invariant_predicates'],
                'required_open_predicates': required_open}
    official = declared.get('official_goal_predicates', [])
    groups = declared.get('active_goal_indices', [])
    _require(len(groups) == 2 and all(isinstance(g, list) and g for g in groups), 'active semantics mapping missing')
    _require(all(type(i) is int and 0 <= i < len(official) for g in groups for i in g), 'active semantics index differs')
    _require([[official[i] for i in g] for g in groups] == [[g['predicate']] for g in active],
             'active semantics predicates differ from bound source')
    inv = declared.get('invariant_indices', [])
    _require(all(type(i) is int and 0 <= i < len(official) for i in inv)
             and [official[i] for i in inv] == parent['invariant_predicates'], 'invariant semantics differ')
    return {**deepcopy(declared), 'active_predicates': [g['predicate'] for g in active],
            'required_open_predicates': required_open,
            'basis': 'explicit active predicate-to-official semantics mapping'}


def _active_values(facts, semantics):
    values = facts.get('goals')
    if 'active_goal_indices' in semantics:
        full = facts.get('official_goal_values')
        groups = semantics['active_goal_indices']
        if isinstance(full, list) and len(full) == len(semantics['official_goal_predicates']):
            mapped = [all(full[i] for i in g) if all(type(full[i]) is bool for i in g) else None for g in groups]
            if values is not None and values != mapped:
                return None
            values = mapped
    return values if isinstance(values, list) and len(values) == 2 and all(type(v) is bool for v in values) else None


def _shape(path, source, audit):
    import h5py
    m = source['mapping']; T = source['length']
    if not (type(T) is int and T > 0 and m.get('action_offset') == m.get('observation_offset') == 0
            and m.get('alignment_id') == 'task035-live-transitions-v1'):
        return False
    with h5py.File(path, 'r') as hdf:
        g = hdf[source['episode']]
        if _instruction(hdf, m['instruction_binding']) != source['instruction']:
            return False
        for key in m['images']:
            a = g[key]
            if a.ndim != 4 or a.shape[0] != T+1 or a.shape[-1] != 3 or a.dtype != np.uint8:
                return False
        width = 0
        for key in m['proprio']:
            a = g[key]
            if a.ndim != 2 or a.shape[0] != T+1 or not np.issubdtype(a.dtype, np.number):
                return False
            width += a.shape[1]
        actions = g[m['action']]; states = g['states']
        return (width == 8 and actions.shape == (T, 7) and states.ndim == 2 and states.shape[0] == T+1
                and len(audit.get('frames', [])) == T+1
                and all(len(f.get('state', [])) == states.shape[1] for f in audit['frames']))


def _robot_indices(rewind, normal_lineage, ten_lineage, state_length):
    layout = rewind.get('layout')
    _require(isinstance(layout, dict) and layout == normal_lineage.get('native', {}).get('joint_layout')
             == ten_lineage.get('native', {}).get('joint_layout'), 'robot_layout_mismatch')
    nq, nv = layout.get('nq'), layout.get('nv')
    _require(type(nq) is int and type(nv) is int and nq > 0 and nv > 0 and state_length >= 1+nq+nv,
             'robot_layout_mismatch')
    indices = []
    for prefix, count in (('arm', 7), ('gripper', 2)):
        names = layout.get(prefix+'_joints', [])
        _require(isinstance(names, list) and len(names) == count and len(set(names)) == count
                 and all(isinstance(name, str) and name for name in names), 'robot_layout_mismatch')
        for suffix, limit, offset in (('qpos', nq, 1), ('qvel', nv, 1+nq)):
            coordinates = layout.get(prefix+'_'+suffix, [])
            _require(isinstance(coordinates, list) and len(coordinates) == count
                     and all(type(i) is int and 0 <= i < limit for i in coordinates), 'robot_layout_mismatch')
            indices.extend(offset+i for i in coordinates)
    declared = rewind.get('modified_indices')
    _require(isinstance(declared, list) and all(type(i) is int for i in declared)
             and len(set(indices)) == len(indices) == len(declared)
             and set(indices) == set(declared), 'robot_layout_mismatch')
    return indices


def _pair_check(normal, ten, records):
    n, t = records[normal['source_id']], records[ten['source_id']]
    na, ta = n['audit'], t['audit']; nl, tl = n['lineage'], t['lineage']
    handoff = ta.get('handoff') or {}; i = handoff.get('normal_state_index')
    if not (type(i) is int and 0 <= i < normal['length'] and ten['length'] > 0):
        return 'missing_outgoing_action', None
    if not n['shape_valid'] or not t['shape_valid']:
        return 'invalid_T_plus_one_T_alignment', None
    if not (normal['parent_demo_id'] == ten['parent_demo_id'] and normal['split'] == ten['split']
            and normal['instruction'] == ten['instruction'] and normal['task_key'] == ten['task_key']):
        return 'parent_split_language_mismatch', None
    nn, tn = nl.get('native', {}), tl.get('native', {})
    if not (nn.get('runtime_xml_sha256') and nn == tn):
        return 'environment_mismatch', None
    if n['semantics'] != t['semantics']:
        return 'goal_semantics_mismatch', None
    u, v = na['frames'][i], ta['frames'][0]
    uf, vf = u.get('facts', {}), v.get('facts', {})
    active_u, active_v = _active_values(uf, n['semantics']), _active_values(vf, t['semantics'])
    inv_len = len(n['semantics'].get('invariant_predicates', n['parent']['invariant_predicates']))
    for key in ('goals', 'official_goal_values', 'invariant_values', 'required_open_values'):
        if uf.get(key) != vf.get(key):
            return 'goal_facts_mismatch', None
    invariants = uf.get('invariant_values'); required = uf.get('required_open_values')
    required_len = len(n['semantics']['required_open_predicates'])
    if not (active_u == active_v == [True, False] and isinstance(invariants, list) and len(invariants) == inv_len
            and all(value is True for value in invariants)
            and all(isinstance(facts.get('required_open_values'), list)
                    and len(facts['required_open_values']) == required_len
                    and all(value is True for value in facts['required_open_values']) for facts in (uf,vf))):
        return 'goal_facts_mismatch', None
    for frame in (u, v):
        if not (frame.get('hand_open') is True and frame.get('held_free') is False
                and frame.get('a_released') is True and frame.get('penetration') is False
                and frame['facts'].get('released') is True):
            return 'unsafe_handoff', None
    a, b = np.asarray(u.get('state'), dtype=float), np.asarray(v.get('state'), dtype=float)
    if not (a.ndim == b.ndim == 1 and a.shape == b.shape and a.size > 1
            and np.isfinite(a).all() and np.isfinite(b).all()):
        return 'invalid_recorded_state', None
    try:
        robot = _robot_indices(ta.get('rewind') or {}, nl, tl, len(a))
    except ValueError:
        return 'robot_layout_mismatch', None
    mask = np.ones(len(a), dtype=bool); mask[0] = False; mask[robot] = False
    nonrobot = float(np.max(np.abs(a[mask]-b[mask]), initial=0))
    delta = float(np.max(np.abs(a[robot]-b[robot]), initial=0))
    if nonrobot > 1e-8:
        return 'recorded_nonrobot_state_changed', None
    if delta == 0:
        return 'robot_state_unchanged', None
    return None, {'handoff_index': i, 'ten_index': 0, 'excluded_time_index': 0,
                  'robot_modified_indices': robot, 'recorded_nonrobot_max_abs_difference': nonrobot,
                  'recorded_robot_max_abs_difference': delta,
                  'active_goal_values':active_u,'invariant_values':deepcopy(invariants),
                  'required_open_values':deepcopy(required),'hand_open':[True,True],
                  'held_free':[False,False],'released':[True,True],
                  'lineage_summary':{'parent_source_id':ten['parent_demo_id'],
                                     'runtime_xml_sha256':nn['runtime_xml_sha256'],
                                     'semantics':deepcopy(n['semantics'])}}


def build_index(generated_export, retention_index, output_dir, *, contract=None, context=None):
    """Seal new labels/pairs without modifying the original035/036 indices."""
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError('new038 index directory required')
    generated, retention = Path(generated_export).resolve(), Path(retention_index).resolve()
    hash_file = file_sha256 if context is None else context.sha256
    original = read_json(generated/'sources.json'); old_report = read_json(generated/'report.json')
    _require(original.get('format') == GENERATED_KIND and old_report.get('data_kind') == GENERATED_KIND
             and identity(original) == original.get('identity') == old_report.get('sources_identity')
             and identity(old_report) == old_report.get('identity')
             and hash_file(generated/'windows.jsonl') == old_report.get('windows_sha256'),
             'generated035 identity differs')
    _require(contract is None or isinstance(contract, IndexContract), 'explicit task-control index contract required')
    progress = None if contract is None else contract.progress
    base = RetentionDataset(retention) if contract is None else contract.dataset_factory(retention, context=context)
    inputs = {}
    def bind(path, expected=None):
        path = Path(path).resolve(); digest = hash_file(path)
        _require(expected is None or digest == expected, 'source SHA bytes changed: '+str(path))
        inputs[str(path)] = digest
        return digest
    for directory, filenames in ((generated, ('sources.json','report.json','windows.jsonl')),
                                 (retention, ('sources.json','report.json','rows.jsonl'))):
        for name in filenames:
            bind(directory/name)
    if (generated/'attempts.json').exists():
        bind(generated/'attempts.json')
    for path, digest in base.manifest['inputs'].items():
        bind(path, digest)
    for source in base.sources.values():
        bind(base._path(source), source['file_sha256'])
    parents = {p['source_id']: p for p in original['parents']}
    scope = {t['key']: t for t in load_scope()['tasks']}
    for p in parents.values():
        _require(p['split'] in ('train', 'dev') and p['active_goals'] == scope[p['task_key']]['active_goals']
                 and p['invariant_predicates'] == scope[p['task_key']]['invariant_predicates'], 'parent active semantics differs')
    group_splits = {}
    for row in base.rows:
        p = parents.get(row['parent_demo_id'])
        _require(p is not None and all(row[k] == p[k] for k in ('split','task_key','instruction','source_group')),
                 'retention row parent/split/full instruction differs')
        group_splits.setdefault(row['source_group'], row['split'])
        _require(group_splits[row['source_group']] == row['split'], 'parent group crosses split')
    source_map = original['sources']; root = Path(original['data_root']).resolve(); records = {}
    for sid, source in source_map.items():
        if progress is not None:
            progress.update(phase='recorded_metadata', source=sid, completed=len(records), total=len(source_map))
        p = parents.get(source['parent_demo_id']); domain = source.get('domain')
        _require(p is not None and domain in ('normal','10') and source.get('source_id') == sid
                 and source.get('qualified') is True and source.get('status') == 'completed'
                 and source.get('qualification', {}).get('accepted') is True
                 and all(source[k] == p[k] for k in ('split','task_key','instruction','source_group'))
                 and source['parent_file_sha256'] == p['file_sha256'], 'qualified source parent/split differs')
        rid = ('fresh|' if domain == 'normal' else 'ten|')+sid
        retained = base.sources.get(rid)
        _require(retained is not None and all(retained[k] == source[k] for k in
                 ('file','file_sha256','episode','parent_demo_id','source_group','split','task_key','instruction'))
                 and retained['observation_count'] == source['length']+1, 'retention/generated source binding differs')
        if 'original_source' in retained:
            _require(all(source.get(k) == value for k, value in retained['original_source'].items()), 'original036 source differs')
        path = _contained(root, source['file']); bind(path, source['file_sha256'])
        paths = {name: _contained(root, source[name+'_path']) for name in ('audit','lineage')}
        digests = {name: bind(path) for name, path in paths.items()}
        for name in ('qualification_path','journal_path'):
            if source.get(name):
                bind(_contained(root, source[name]))
        audit, lineage = read_json(paths['audit']), read_json(paths['lineage'])
        ancestor = lineage.get('source', {})
        _require(all(ancestor.get(k) == p[k] for k in ('source_id','file_sha256','split','task_key','instruction','active_goals','invariant_predicates')),
                 'lineage original parent/active semantics differs')
        semantics = _semantics(p, lineage)
        records[sid] = {'audit': audit, 'lineage': lineage, 'digests': digests, 'parent': p,
                        'semantics': semantics, 'shape_valid': _shape(path, source, audit)}
    _require({s['source_id'].split('|',1)[1] for s in base.sources.values() if s['pool'] != 'raw'} == set(source_map),
             'all original036 BC/reference sources must be retained')
    original_rows = {}
    for row in _lines(generated/'windows.jsonl'):
        sid = row['source_id']; s = source_map.get(sid); start = row['start']
        _require(s is not None and type(start) is int and 0 <= start < s['length']
                 and row['stop'] == min(start+8,s['length'])
                 and row['action_mask'] == [j < row['stop']-start for j in range(8)]
                 and all(row[k] == s[k] for k in ('split','task_key','parent_demo_id','source_group','instruction')),
                 'existing generated chunk/mask binding differs')
        _require((sid,start) not in original_rows, 'duplicate generated source window')
        original_rows[sid,start] = row
    _require(all((sid,i) in original_rows for sid,s in source_map.items() for i in range(s['length'])),
             'existing generated windows missing outgoing transitions')
    row_map = {(r['source_id'],r['observation_index']): r for r in base.rows}
    _require(len(row_map) == len(base.rows), 'duplicate retention observation')
    labels = []
    for row in base.rows:
        label = None; basis = 'raw labels unavailable'
        if row['pool'] != 'raw':
            rec = records[row['source_id'].split('|',1)[1]]; frames = rec['audit'].get('frames',[])
            i = row['observation_index']
            values = _active_values(frames[i].get('facts',{}),rec['semantics']) if i < len(frames) else None
            label = sum(values) if values is not None else None
            basis = rec['semantics']['basis']
        labels.append({'source_id':row['source_id'],'observation_index':row['observation_index'],
                       'split':row['split'],'pool':row['pool'],'count_label':label,'label_basis':basis})
        if progress is not None:
            progress.update(phase='count_labels', source=row['source_id'], completed=len(labels), total=len(base.rows))
    normals = {}
    for source in source_map.values():
        if source['domain'] == 'normal':
            _require(source['parent_demo_id'] not in normals, 'multiple normal sources for parent')
            normals[source['parent_demo_id']] = source
    pairs = []; reasons = Counter()
    buckets = {key+'|'+split:{'candidates':0,'valid':0,'reasons':{}}
               for key in scope for split in ('train','dev')}
    for ten in source_map.values():
        if ten['domain'] != '10':
            continue
        bucket = buckets.setdefault(ten['task_key']+'|'+ten['split'], {'candidates':0,'valid':0,'reasons':{}})
        bucket['candidates'] += 1
        normal = normals.get(ten['parent_demo_id'])
        reason, evidence = ('missing_qualified_normal_source',None) if normal is None else _pair_check(normal,ten,records)
        if reason:
            reasons[reason] += 1; bucket['reasons'][reason] = bucket['reasons'].get(reason,0)+1
            continue
        endpoints = {}
        for name, source, index in (('u',normal,evidence['handoff_index']),('v',ten,0)):
            rid = ('fresh|' if name == 'u' else 'ten|')+source['source_id']
            old = original_rows[source['source_id'],index]
            endpoints[name] = {'source_id':rid,'generated_source_id':source['source_id'],'observation_index':index,
                               'row':deepcopy(row_map[rid,index]),'original_row':deepcopy(old),
                               'action_mask':deepcopy(old['action_mask']),'file_sha256':source['file_sha256'],
                               'audit_sha256':records[source['source_id']]['digests']['audit'],
                               'lineage_sha256':records[source['source_id']]['digests']['lineage']}
        pair = {k:deepcopy(ten[k]) for k in ('task_key','parent_demo_id','source_group','variant','split','instruction')}
        pair.update(endpoints); pair['evidence'] = evidence
        pair['pair_id'] = identity(pair); pairs.append(pair); bucket['valid'] += 1
    label_bytes = ''.join(_json(row)+'\n' for row in labels).encode('utf-8')
    pair_bytes = ''.join(_json(row)+'\n' for row in pairs).encode('utf-8')
    label_sha, pair_sha = hashlib.sha256(label_bytes).hexdigest(), hashlib.sha256(pair_bytes).hexdigest()
    manifest = {'format':SOURCES_KIND if contract is None else contract.sources_kind,'retention_index':str(retention),'generated_export':str(generated),
                'generated_data_root':str(root),'retention_identity':base.manifest['identity'],
                'qualified_sources':deepcopy(source_map),'inputs':inputs,
                'labels_sha256':label_sha,'pairs_sha256':pair_sha}
    if contract is not None:
        _require(not set(contract.metadata) & set(manifest), 'task-control contract may not overwrite identity fields')
        manifest.update(deepcopy(contract.metadata))
    manifest['identity'] = identity(manifest)
    report = {'data_kind':DATA_KIND,'sources_identity':manifest['identity'],'available':bool(pairs),
              'status':'available' if pairs else 'data unavailable: zero valid recorded pairs; training not ready',
              'rows':len(base.rows),'pairs':{'candidates':sum(b['candidates'] for b in buckets.values()),
              'valid':len(pairs),'reasons':dict(reasons),'by_task_split':buckets},
              'labels':{'available':sum(r['count_label'] is not None for r in labels),
                        'missing':sum(r['count_label'] is None for r in labels)},
              'labels_sha256':label_sha,'pairs_sha256':pair_sha,
              'image_pixels_read':False,'model_loaded':False,'simulation_created':False,'confirmation_frames_exported':False}
    if contract is not None:
        _require(not set(contract.metadata) & set(report), 'task-control contract may not overwrite report fields')
        report.update(deepcopy(contract.metadata))
    report['identity'] = identity(report)
    output.mkdir(parents=True)
    _write(output/'sources.json',manifest); _write(output/'report.json',report)
    _write(output/'identity.json',{'format':'task038-index-identity-v1' if contract is None else contract.identity_kind,'sources_identity':manifest['identity'],
                                 'report_identity':report['identity']})
    (output/'labels.jsonl').write_bytes(label_bytes); (output/'pairs.jsonl').write_bytes(pair_bytes)
    if progress is not None:
        progress.finish(phase='sealed_index', completed=len(base.rows), total=len(base.rows), pairs=len(pairs))
    return report


def read_index(directory):
    directory = Path(directory)
    manifest, report, seal = (read_json(directory/name) for name in ('sources.json','report.json','identity.json'))
    _require(manifest.get('format') == SOURCES_KIND and report.get('data_kind') == DATA_KIND
             and identity(manifest) == manifest.get('identity') == report.get('sources_identity') == seal.get('sources_identity')
             and identity(report) == report.get('identity') == seal.get('report_identity'), 'task038 index identity differs')
    for name in ('labels','pairs'):
        _require(file_sha256(directory/(name+'.jsonl')) == report.get(name+'_sha256') == manifest.get(name+'_sha256'),
                 'task038 '+name+' bytes/identity changed')
    for path, digest in manifest['inputs'].items():
        _require(file_sha256(path) == digest, 'original source SHA bytes changed: '+path)
    return manifest, report, _lines(directory/'labels.jsonl'), _lines(directory/'pairs.jsonl')
