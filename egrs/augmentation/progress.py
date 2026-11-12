"""Sparse ordinary-demo progress production; real recovery is explicitly run.

Planning reads only supplied metadata. Production visits only planned anchors;
neither goal success nor model output chooses the population. One reliable anchor
proves only its current pending goals, not an interpolated interval or a skill.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from .data import identity, file_sha256, load_scope, read_json, validate_manifest, _hex
from .progress_native import NativeProgressBackend, validate_binding, ESTIMATED_RESTORES_PER_ANCHOR

CONFIG = 'egrs.augmentation.progress-config.v1'
PLAN = 'egrs.augmentation.progress-plan.v1'
REPORT = 'egrs.augmentation.progress-report.v1'
EVIDENCE = 'egrs.augmentation.progress-evidence.v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _atoms(atoms):
    _require(isinstance(atoms,list) and all(isinstance(a,list) and len(a)>=2
        and all(isinstance(x,str) and x for x in a) for a in atoms), 'malformed native final goal inventory')
    return sorted((str(atom[0]).lower(), *atom[1:]) for atom in atoms)


def plan_progress(config, sources, data_root):
    """Metadata-only finite plan; no native construction or HDF content reads."""
    _require(isinstance(config, dict) and config.get('format') == CONFIG, 'explicit progress configuration required')
    _require(set(config) <= {'format','backend','selection','task_bindings','source_bindings'}, 'unknown progress configuration field')
    backend = deepcopy(config.get('backend', {}))
    _require(backend.get('kind') in {'native','recorded'}, 'built-in native or recorded progress backend required')
    if backend['kind'] == 'recorded':
        _require(isinstance(backend.get('report'),str) and _hex(backend.get('sha256')), 'recorded production report path/hash required')
    selection = config.get('selection', {})
    _require(set(selection) == {'start','stride','max_anchors_per_source'}, 'explicit deterministic sparse selection required')
    _require(all(type(selection[k]) is int for k in selection) and selection['start'] >= 0
        and selection['stride'] >= 1 and selection['max_anchors_per_source'] >= 1, 'invalid sparse selection')
    source_bindings, task_bindings = config.get('source_bindings', {}), config.get('task_bindings', {})
    _require(isinstance(source_bindings,dict) and isinstance(task_bindings,dict), 'explicit source/task bindings required')
    _require(not set(source_bindings) - {s['source_id'] for s in sources}, 'unplanned source binding')
    _require(not set(task_bindings) - {s['task_key'] for s in sources}, 'unplanned task binding')
    scope = {t['key']:t for t in load_scope()['tasks']}
    selected, excluded = [], []
    for source in sources:
        binding = deepcopy(source_bindings.get(source['source_id'],task_bindings.get(source['task_key'])))
        if binding is None:
            excluded.append({'source_id':source['source_id'],'reason':'no_explicit_state_and_goal_binding'});continue
        validate_binding(source,binding)
        if source['domain'] == 'compound':
            expected = scope[source['task_key']]
            for field in ('official_task_name','active_goals','invariant_predicates'):
                _require(binding.get(field) == expected[field], 'progress binding differs from fixed nine-task '+field)
        if len(binding['active_goals']) < 2:
            excluded.append({'source_id':source['source_id'],'reason':'single_goal_is_RAW_not_compound_progress'});continue
        if 'anchors' in binding:
            anchors = binding['anchors']
        elif 'windows' in binding:
            _require(isinstance(binding['windows'],list) and binding['windows'], 'explicit local windows required')
            anchors = []
            for window in binding['windows']:
                _require(isinstance(window,list) and len(window)==2 and all(type(x) is int for x in window)
                    and 0 <= window[0] < window[1] <= source['length'], 'invalid local anchor window')
                anchors.extend(range(*window))
        else:
            anchors = list(range(selection['start'],source['length'],selection['stride']))[:selection['max_anchors_per_source']]
        _require(isinstance(anchors,list) and all(type(t) is int and 0<=t<source['length'] for t in anchors), 'anchor outside source')
        _require(len(anchors)==len(set(anchors)), 'duplicate planned anchor')
        _require(len(anchors)<source['length'] and len(anchors)<=selection['max_anchors_per_source'], 'sparse anchors may not scan a full trajectory or exceed the declared cap')
        if not anchors:
            excluded.append({'source_id':source['source_id'],'reason':'no_anchors_in_declared_window'});continue
        selected.append({'source':deepcopy(source),'binding':binding,'anchors':sorted(anchors),
                         'source_identity':identity(source),'binding_identity':identity(binding)})
    n = sum(len(s['anchors']) for s in selected)
    plan = {'format':PLAN,'backend':backend,'selection':deepcopy(selection),'data_root':str(Path(data_root).resolve()),
            'source_plans':selected,'excluded_sources':excluded,'planned_sources':len(selected),'planned_anchors':n,
            'maximum_restores':n*ESTIMATED_RESTORES_PER_ANCHOR if backend['kind']=='native' else 0,
            'simulation_created':False,'weights_loaded':False,'model_rollouts':0,
            'selection_basis':'predeclared stride or local windows; independent of goal values and model outcomes'}
    plan['identity'] = identity(plan)
    return plan


def validate_anchor(source,binding,t,result):
    """Validate returned current-anchor facts; never infer another frame's label."""
    validate_binding(source,binding)
    _require(type(t) is int and 0<=t<source['length'], 'anchor outside source')
    _require(isinstance(result,dict) and result.get('reliable') is True, 'unreliable anchor')
    _require(result.get('correspondence',{}).get('accepted') is True, 'current RGB/state correspondence not accepted')
    facts = result.get('native_facts',{})
    values = facts.get('goal_values',{})
    goals = [g['id'] for g in binding['active_goals']]
    _require(set(values)==set(goals) and all(type(v) is bool for v in values.values()), 'native current goal facts incomplete')
    _require(_atoms(facts.get('final_goal_atoms',[])) == _atoms([g['predicate'] for g in binding['active_goals']] + binding['invariant_predicates']), 'native final goal inventory differs')
    invariants = facts.get('invariant_values')
    _require(isinstance(invariants,list) and len(invariants)==len(binding['invariant_predicates'])
             and all(type(v) is bool and v for v in invariants), 'native holding constraint unconfirmed')
    pending = [g for g in goals if not values[g]]
    _require(result.get('pending_goals') == pending, 'pending goals disagree with native current facts')
    state = result.get('state_binding',{})
    a = binding['alignment']
    _require(state.get('state_field') == binding['state_field']
        and state.get('observation_index') == t+source['mapping']['observation_offset']
        and state.get('action_index') == t+source['mapping']['action_offset']
        and state.get('restored_state_index') == t+a['state_offset'] and _hex(state.get('state_sha256')),
        'native state/observation/action binding differs from exported expert chunk')
    return pending


class RecordedProgressBackend:
    """Reuse exact produced anchor records, never infer unrecorded frames."""
    def __init__(self,config,source,data_root,binding,goals=None):
        path=Path(config['report']).resolve()
        _require(file_sha256(path)==config['sha256'], 'recorded progress report hash differs')
        report=read_json(path)
        _require(report.get('format')==REPORT and report.get('identity')==identity(report), 'recorded production report identity differs')
        matches=[r for r in report['source_reports'] if r['source_identity']==identity(source)
                 and r['binding_identity']==identity(binding)]
        _require(len(matches)==1,'recorded source/goal/time binding missing or ambiguous')
        self.rows={a['t']:a['result'] for a in matches[0]['anchors']}
        _require(len(self.rows)==len(matches[0]['anchors']), 'duplicate recorded anchor')
        self.inspection={'reused_report_identity':report['identity'],'reused_report_sha256':config['sha256'],
            'simulation_created':False,'original_backend_inspection':deepcopy(matches[0].get('backend_inspection'))}
    def inspect_anchor(self,t):
        _require(t in self.rows,'recorded source has no evidence for requested anchor')
        return deepcopy(self.rows[t])
    def close(self):pass


def produce_progress(config,sources,data_root):
    """Called only by a user-started export/run; never by the planning command."""
    plan=plan_progress(config,sources,data_root)
    evidence=[];reports=[];accepted=terminal=excluded=0
    for item in plan['source_plans']:
        source,binding=item['source'],item['binding'];sid=source['source_id']
        source_path=(Path(data_root)/source['file']).resolve()
        _require(source_path.is_relative_to(Path(data_root).resolve()) and file_sha256(source_path)==source['file_sha256'], 'progress source bytes changed')
        audit={**deepcopy(item),'anchors':[],'error':None};reports.append(audit)
        anchors=[];backend=None
        try:
            factory=NativeProgressBackend if config['backend']['kind']=='native' else RecordedProgressBackend
            backend=factory(config['backend'],source,str(data_root),binding,[g['id'] for g in binding['active_goals']])
            audit['backend_inspection']=deepcopy(backend.inspection)
            for t in item['anchors']:
                row={'t':t,'status':'excluded','result':None,'reason':None}
                audit['anchors'].append(row)
                try:
                    row['result']=backend.inspect_anchor(t)
                    pending=validate_anchor(source,binding,t,row['result'])
                    if not pending:
                        row.update(status='terminal',reason='all_final_goals_satisfied_no_parking_target');terminal+=1
                    else:
                        row['status']='accepted';accepted+=1
                        anchors.append({'t':t,'pending_goals':pending,'result':deepcopy(row['result'])})
                except (OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
                    row['reason']=f'{type(error).__name__}: {error}';excluded+=1
        except (OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
            audit['error']=f'{type(error).__name__}: {error}'
            for t in item['anchors']:
                if t not in {r['t'] for r in audit['anchors']}:
                    audit['anchors'].append({'t':t,'status':'excluded','result':None,'reason':audit['error']});excluded+=1
        finally:
            if backend is not None:
                try:backend.close()
                except Exception as error:audit['cleanup_error']=f'{type(error).__name__}: {error}'
        if anchors:
            evidence.append({'format':EVIDENCE,'source_id':sid,'file_sha256':source['file_sha256'],
                'alignment_id':source['mapping']['alignment_id'],'provenance':'verified_local_sim_evidence',
                'reviewer':'builtin_native_progress_producer_v1','basis':'current-anchor original RGB correspondence and complete native final goals',
                'active_goals':deepcopy(binding['active_goals']),'binding':deepcopy(binding),
                'source_identity':identity(source),'plan_identity':plan['identity'],
                'progress_anchors':anchors,'atomic_segments':[]})
        print(json.dumps({'progress_source':sid,'anchors':len(item['anchors']),
                          'accepted':sum(r['status']=='accepted' for r in audit['anchors'])}),flush=True)
    report={'format':REPORT,'plan':plan,'source_reports':reports,'accepted_anchors':accepted,
            'terminal_anchors':terminal,'excluded_anchors':excluded,'produced_atomic_segments':0,
            'backend':deepcopy(config['backend']),'model_rollouts':0,
            'simulation_requested':config['backend']['kind']=='native' and bool(reports),
            'coverage':'verified current anchors only; no stage interpolation or atomic ownership inference'}
    report['identity']=identity(report)
    return evidence,report


def load_progress_config(path):
    path=Path(path).resolve();config=read_json(path)
    # Only explicit path fields; never traverse or rewrite dependency goal data.
    backend=config.get('backend',{})
    for key in ('historical_root','python','report'):
        if key in backend:
            p=Path(backend[key]).expanduser()
            backend[key]=str(p if p.is_absolute() else (path.parent/p).resolve())
    native=backend.get('native',{})
    for container,key in ((native,'bddl_root'),(native.get('core',{}),'root')):
        if key in container:
            p=Path(container[key]).expanduser()
            container[key]=str(p if p.is_absolute() else (path.parent/p).resolve())
    if 'asset_roots' in native:
        _require(isinstance(native['asset_roots'],dict),'native asset_roots must retain named root mapping')
        native['asset_roots']={k:str(p if p.is_absolute() else (path.parent/p).resolve())
                              for k,x in native['asset_roots'].items() for p in [Path(x).expanduser()]}
    if 'module_paths' in backend:
        _require(isinstance(backend['module_paths'],list),'native module_paths must be a list')
        backend['module_paths']=[str(p if p.is_absolute() else (path.parent/p).resolve())
                                for x in backend['module_paths'] for p in [Path(x).expanduser()]]
    return config


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['plan'])
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--base-inventory',required=True)
    parser.add_argument('--config',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    manifest=read_json(args.manifest)
    root=Path(manifest['data_root'])
    if not root.is_absolute():root=Path(args.manifest).resolve().parent/root
    plan=plan_progress(load_progress_config(args.config),validate_manifest(manifest,read_json(args.base_inventory)),root)
    with Path(args.output).open('x',encoding='utf-8') as stream:
        json.dump(plan,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:plan[k] for k in ('planned_sources','planned_anchors','maximum_restores','simulation_created')}),flush=True)


if __name__=='__main__':main()
