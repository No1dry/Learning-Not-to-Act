"""User-launched local native progress evidence, isolated from training imports.

The parent process imports no HDF/native/selector packages. A bounded worker
loads the byte-pinned accepted historical adapter, overrides its constructor
only, and reuses its XML/name/controller/restore/render validation unchanged.
No historical annotation pipeline or global alignment scan is invoked.
"""
from copy import deepcopy
import contextlib
import hashlib
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading

ESTIMATED_RESTORES_PER_ANCHOR = 4
_RULES = ('same_state', 'next_state', 'replay_action')


def episode_name(episode):
    """Translate the augmentation HDF path to the accepted data-relative name."""
    if not isinstance(episode, str) or not re.fullmatch(r'(?:data/)?demo_(?:0|[1-9][0-9]*)', episode):
        raise ValueError('native episode must be exactly data/demo_N or demo_N')
    return episode.removeprefix('data/')


def open_source_episode(old, data_root, source, binding):
    """Reconcile physical HDF lengths before invoking accepted SourceEpisode.

    Source length counts logical training samples. The historical reader's T
    counts physical rows, including any explicitly declared leading offset.
    Its equal-state/action/camera length contract is retained without adapting
    arrays, changing the HDF, or guessing a missing row.
    """
    import h5py
    root = Path(data_root).resolve(strict=True)
    path = (root / source['file']).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError('source escapes inventory root')
    name = episode_name(source['episode'])
    rows = {}
    with h5py.File(path, 'r') as hdf:
        group = hdf['data'][name]
        for field in ('states', 'actions', 'obs/agentview_rgb', 'obs/eye_in_hand_rgb'):
            array = group[field]
            if not array.shape:
                raise ValueError('original physical source field has no row axis: ' + field)
            rows[field] = int(array.shape[0])
    length = source['length']; alignment = binding['alignment']
    expected_obs = length + alignment['observation_offset']
    expected_action = length + alignment['action_offset']
    if (rows['obs/agentview_rgb'] != expected_obs or rows['obs/eye_in_hand_rgb'] != expected_obs
            or rows['actions'] != expected_action):
        raise ValueError('physical HDF lengths disagree with explicit logical observation/action offsets')
    if len(set(rows.values())) != 1:
        raise ValueError('accepted native restoration requires equal physical state/action/camera lengths; '
                         'unequal arrays are unsupported, not implicitly shifted or padded')
    physical_length = rows['states']
    legacy_source = {**source, 'episode': name, 'T': physical_length,
                     'orientation': binding['orientation'], 'task_group': source['file']}
    layout = {'augmentation_episode': source['episode'], 'native_episode': name,
        'hdf_episode_path': 'data/' + name, 'logical_length': length, 'physical_length': physical_length,
        'physical_rows': rows, 'observation_offset': alignment['observation_offset'],
        'action_offset': alignment['action_offset'], 'state_offset': alignment['state_offset']}
    return old.SourceEpisode(root, legacy_source), legacy_source, layout


def inspect_dependency(root):
    """Check source bytes only; safe for a plan, never import the dependency."""
    root = Path(root).expanduser().resolve(strict=True)
    lock = json.loads(Path(__file__).with_name('progress_native_files.json').read_text(encoding='utf-8-sig'))
    for name, expected in lock['files'].items():
        path = root / name
        # Git's Windows checkout conversion is representation-only. Pin the
        # accepted Git blob bytes with explicit LF normalization, on both hosts.
        if not path.is_file() or hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('accepted native dependency differs: ' + name)
    return {'root': str(root), 'accepted_revision': lock['accepted_revision'],
            'hash_basis': 'sha256 accepted Git blob bytes; checkout CRLF normalized to LF',
            'files': deepcopy(lock['files'])}


def validate_binding(source, binding, goals=None):
    """Pure declaration check; actual BDDL goal/name agreement is runtime-only."""
    if not isinstance(binding, dict) or binding.get('orientation') not in {'opengl', 'opencv'}:
        raise ValueError('explicit saved HDF image convention required')
    if (binding.get('state_field') != 'states' or not isinstance(binding.get('state_alignment_basis'), str)
            or not binding['state_alignment_basis'].strip()):
        raise ValueError('accepted original states field and explicit state alignment basis required')
    active = binding.get('active_goals')
    if not isinstance(active, list) or not active:
        raise ValueError('explicit active native goals required')
    ids = []
    atoms = []
    for goal in active:
        if (not isinstance(goal, dict) or set(goal) != {'id', 'predicate'}
                or not isinstance(goal['id'], str) or not goal['id']):
            raise ValueError('active goals require exact id/predicate')
        ids.append(goal['id']); atoms.append(goal['predicate'])
    invariants = binding.get('invariant_predicates')
    if not isinstance(invariants, list):
        raise ValueError('explicit invariant predicate list required')
    if set(ids) & {'invariant' + str(i) for i in range(len(invariants))}:
        raise ValueError('active goal ID collides with invariant audit reference')
    atoms += invariants
    for atom in atoms:
        if (not isinstance(atom, list) or len(atom) < 2
                or any(not isinstance(x, str) or not x for x in atom)
                or atom[0].lower() not in {'in', 'on', 'open', 'close', 'turnon', 'turnoff'}):
            raise ValueError('unsupported or malformed exact native goal atom')
    canonical = [(a[0].lower(), *a[1:]) for a in atoms]
    if len(ids) != len(set(ids)) or len(canonical) != len(set(canonical)):
        raise ValueError('duplicate native goals or invariants')
    if goals is not None and list(goals) != ids:
        raise ValueError('requested goal IDs differ from native binding')
    a = binding.get('alignment', {})
    if set(a) != {'rule', 'orientation', 'state_offset', 'observation_offset', 'action_offset'}:
        raise ValueError('explicit state/observation/action alignment required')
    if a['rule'] not in _RULES or a['orientation'] not in {'identity', 'flip_vertical'}:
        raise ValueError('invalid declared native correspondence')
    for name in ('state_offset', 'observation_offset', 'action_offset'):
        if type(a[name]) is not int or a[name] < 0:
            raise ValueError('alignment offsets must be nonnegative integers')
    mapping = source['mapping']
    if (a['observation_offset'] != mapping['observation_offset']
            or a['action_offset'] != mapping['action_offset']
            or a['state_offset'] != a['observation_offset'] + (a['rule'] == 'next_state')
            or (a['rule'] == 'replay_action' and a['action_offset'] != a['observation_offset'])):
        raise ValueError('declared state/observation/action correspondence disagrees with training mapping')
    return deepcopy(binding)


def _state_hash(state):
    return hashlib.sha256(state.tobytes()).hexdigest()


def inspect_session(session, source, binding, goals, t):
    """Three candidates at this anchor only; never extrapolate a stage label."""
    import numpy as np
    validate_binding(source, binding, goals)
    result = {'reliable': False, 'pending_goals': None, 'native_facts': {},
              'correspondence': {}, 'diagnostics': []}
    if type(t) is not int or t < 0 or t >= source['length']:
        raise ValueError('anchor outside original episode')
    frame = t + binding['alignment']['observation_offset']
    # Never clamp or infer a terminal replay without a stored next-state proof.
    if frame + 1 >= session.episode.T:
        result['diagnostics'].append('alignment_boundary_without_stored_next_state')
        return result
    threshold = session.config['rgb_threshold']
    if threshold > .03 or session.config['replay_state_atol'] > 1e-6:
        raise ValueError('accepted RGB/state thresholds may not be relaxed')
    measurements = {}; states = {}; failures = []
    for rule in _RULES:
        try:
            measured = session.measure(frame, rule)
            state = np.asarray(measured.pop('state'))
            if state.ndim != 1 or not state.size or not np.isfinite(state).all():
                raise ValueError('full flattened finite simulator state required')
            states[rule] = state
            measured['state_sha256'] = _state_hash(state)
            measurements[rule] = measured
        except Exception as error:
            failures.append({'rule': rule, 'reason': str(error)[:1000]})
    passing = []
    for rule, measured in measurements.items():
        for orientation, field in [('identity', 'residuals'), ('flip_vertical', 'flipped_residuals')]:
            residuals = measured.get(field, {'agentview': 1., 'wrist': 1.})
            if (set(residuals) == {'agentview', 'wrist'}
                    and all(type(x) in (int, float) and np.isfinite(x) and x >= 0 for x in residuals.values())
                    and max(residuals.values()) <= threshold):
                passing.append((orientation, rule))
    declared = binding['alignment']; accepted = False; equivalence = None
    if not failures and passing == [(declared['orientation'], declared['rule'])]:
        accepted = True
    elif (not failures and set(passing) == {(declared['orientation'], 'next_state'),
                                         (declared['orientation'], 'replay_action')}
            and declared['rule'] in {'next_state', 'replay_action'}):
        left, right = states['next_state'], states['replay_action']
        if left.shape == right.shape:
            residual = float(np.max(np.abs(left - right)))
            equivalence = {'max_state_abs_residual': residual, 'state_atol': session.config['replay_state_atol'],
                           'next_state_sha256': _state_hash(left), 'replay_state_sha256': _state_hash(right)}
            accepted = residual <= session.config['replay_state_atol']
    # Reuse the accepted pure correspondence validator, including its bounded
    # physical-equivalence certificate, before certifying any native truth.
    comparisons = []
    for rule, measured in measurements.items():
        field = 'residuals' if declared['orientation'] == 'identity' else 'flipped_residuals'
        residuals = measured.get(field, {'agentview': 1., 'wrist': 1.})
        comparisons.append({'rule': rule, 'residuals': [residuals[c] for c in ('agentview', 'wrist')],
                            'samples': [{'frame': frame, 'camera': c} for c in ('agentview', 'wrist')]})
    certificate = None
    if equivalence is not None:
        field = 'residuals' if declared['orientation'] == 'identity' else 'flipped_residuals'
        certificate = {'format': 'egrs.sim.equivalence.v1', 'rules': ['next_state', 'replay_action'],
            'representative': 'next_state', 'state_atol': session.config['replay_state_atol'],
            'checks': [{'frame': frame, 'next_state_index': frame + 1, 'replay_state_index': frame,
                'action_index': frame, 'state_max_abs_residual': equivalence['max_state_abs_residual'],
                'next_state_sha256': equivalence['next_state_sha256'],
                'replay_state_sha256': equivalence['replay_state_sha256'],
                'rgb_residuals': {r: measurements[r][field] for r in ('next_state', 'replay_action')}}]}
    decision = session.choose_alignment(comparisons, basis=[binding['state_alignment_basis']],
        orientation=declared['orientation'], threshold=threshold, equivalence=certificate)
    accepted = accepted and decision['accepted']
    result['correspondence'] = {'accepted': accepted, 'frame': frame, 'logical_t': t,
        'declared': deepcopy(declared), 'measurements': measurements, 'passing': passing,
        'equivalence': equivalence, 'threshold': threshold, 'failures': failures,
        'accepted_alignment_evidence': decision}
    if not accepted:
        result['diagnostics'].append('unresolved_or_ambiguous_current_anchor_correspondence')
        return result
    try:
        values, invariant_values, full_atoms = session.facts(frame, declared['rule'])
    except Exception as error:
        result['diagnostics'].append('native_fact_restore_gap:' + str(error)[:1000])
        return result
    result['native_facts'] = {'goal_values': values, 'invariant_values': invariant_values,
                              'final_goal_atoms': full_atoms}
    result['state_binding'] = {'state_field': 'states', 'observation_index': frame,
        'action_index': t + declared['action_offset'], 'restored_state_index': t + declared['state_offset'],
        'state_sha256': measurements[declared['rule']].get('source_state_sha256',
                                                          measurements[declared['rule']]['state_sha256']),
        'simulator_state_sha256': measurements[declared['rule']]['state_sha256'],
        'alignment_basis': binding['state_alignment_basis']}
    if set(values) != set(goals) or any(type(v) is not bool for v in values.values()):
        result['diagnostics'].append('native_goal_truth_gap')
        return result
    if any(type(v) is not bool or not v for v in invariant_values):
        result['diagnostics'].append('native_invariant_false_or_unknown')
        return result
    result.update(reliable=True, pending_goals=[g for g in goals if not values[g]])
    return result


def _runtime(config, source, data_root, binding, goals):
    """Called only inside a fresh worker whose egrs package is historical."""
    from egrs.offline import sim_native as old
    from egrs.offline.sim_contract import load_goal_map
    validate_binding(source, binding, goals)
    if (source['mapping']['images'] != ['obs/agentview_rgb', 'obs/eye_in_hand_rgb']
            or source['mapping']['action'] != 'actions'):
        raise ValueError('native adapter requires the original accepted camera/action fields')

    class LocalSession(old.NativeAdapter):
        choose_alignment = staticmethod(old.choose_alignment)

        def __init__(self):
            self.env = self.episode = None
            self.audit = []; self._emit = None; self.image_bindings = {}
            self.config = old.validate_config(config['native'])
            if (self.config['rgb_threshold'] > .03 or self.config['replay_state_atol'] > 1e-6
                    or self.config['min_visible_pixels'] < 16):
                raise ValueError('accepted correspondence thresholds may not be relaxed')
            self.goals = []
            for ref, atom in [(g['id'], g['predicate']) for g in binding['active_goals']] + [
                    ('invariant' + str(i), atom) for i, atom in enumerate(binding['invariant_predicates'])]:
                mechanism = atom[0].lower() in {'open', 'close', 'turnon', 'turnoff'}
                self.goals.append({'goal_ref': ref, 'atom': atom, 'annotation_only': False,
                    'basis': 'explicit source-bound final BDDL atom',
                    'kind': 'mechanism' if mechanism else 'transport'})
            self.aliases = {}; self.images = {}; self.replay_corroborated = False
            self._measured_states = {}
            registry = binding.get('registry')
            if registry is None:
                item = next((r for r in load_goal_map()['instructions'] if r['instruction'] == source['instruction']), None)
                registry = {'instruction': source['instruction'], 'goals': []}
                if item:
                    registry['goals'] = [{**{k: g[k] for k in ('goal_ref', 'kind', 'target', 'destination')},
                        'source_text': source['instruction'], 'actor_text': g['target']} for g in item['goals']]
            try:
                self.episode, legacy_source, layout = open_source_episode(old, data_root, source, binding)
                self.request = {'source_root': str(data_root), 'source': legacy_source, 'registry': registry,
                    'dataset_identity': {'dataset': 'yifengzhu-hf/LIBERO-datasets',
                                         'revision': '147fa5eb607bb696dd922c3518084a90954cd2f3'}}
                self.inspection = deepcopy(self.episode.inspection)
                self.inspection['augmentation_bridge'] = layout
                self._initialize()
                actual = self.inner.parsed_problem['goal_state']
                self.full_atoms = [list(x) for x in actual]
                name = binding.get('official_task_name')
                if name and self.inspection['bddl_identifier_fields']:
                    installed = Path(self.inspection['installed_bddl']['path']).stem
                    if installed != name:
                        raise ValueError('official task name differs from resolved native BDDL')
            except BaseException:
                self.close()
                raise

        def measure(self, frame, rule):
            self._restore(frame + (rule == 'next_state'), frame if rule == 'replay_action' else None)
            state = old.np.asarray(self.env.sim.get_state().flatten()).copy()
            self._measured_states[(frame, rule)] = _state_hash(state)
            output = {'state': state, 'residuals': {}, 'flipped_residuals': {},
                'source_state_sha256': _state_hash(self.episode.state(frame + (rule == 'next_state'))),
                'state_index': frame + (rule == 'next_state'),
                'replayed_action_index': frame if rule == 'replay_action' else None}
            for camera in old.CAMERAS:
                rgb, raw = self._render(camera)
                foreground = self._foreground(raw)
                stored = self.episode.rgb(frame, camera)
                for field, image, mask in [('residuals', rgb, foreground),
                        ('flipped_residuals', rgb[::-1], foreground[::-1])]:
                    output[field][camera] = old.image_residual(stored, image, mask,
                        min_pixels=self.config['min_visible_pixels'])
            return output

        def facts(self, frame, rule):
            self._restore(frame + (rule == 'next_state'), frame if rule == 'replay_action' else None)
            if _state_hash(old.np.asarray(self.env.sim.get_state().flatten())) != self._measured_states[(frame, rule)]:
                raise ValueError('selected native state changed on repeated local restoration')
            values, audit = old.evaluate_atoms(self.inner, self.goals)
            self.audit.append({'frame': frame, 'atoms': audit})
            active = {g: values[g] for g in goals}
            invariants = [values['invariant' + str(i)] for i in range(len(binding['invariant_predicates']))]
            return active, invariants, self.full_atoms

    return LocalSession()


class NativeProgressBackend:
    """Concrete persistent isolated native worker; instantiate only for produce."""
    estimated_restores_per_anchor = ESTIMATED_RESTORES_PER_ANCHOR

    def __init__(self, config, source, data_root, restoration_binding, goals):
        self.process = None; self._stderr = None
        self.config = deepcopy(config)
        episode_name(source['episode'])
        validate_binding(source, restoration_binding, goals)
        self.dependency = inspect_dependency(config['historical_root'])
        self.timeout = config.get('timeout_seconds', 120)
        if type(self.timeout) not in (int, float) or not 1 <= self.timeout <= 3600:
            raise ValueError('native RPC timeout must be in 1..3600 seconds')
        self._responses = queue.Queue()
        self._stderr = tempfile.TemporaryFile(mode='w+b')
        try:
            self.process = subprocess.Popen([config.get('python', sys.executable), '-u',
                str(Path(__file__).resolve()), '--native-worker', self.dependency['root']],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                text=True, encoding='utf-8', bufsize=1)
            process = self.process
            def read_responses():
                try:
                    for line in process.stdout:
                        self._responses.put(line)
                finally:
                    self._responses.put(None)
            threading.Thread(target=read_responses, daemon=True).start()
            self.inspection = self._rpc({'op': 'open', 'config': config, 'source': source,
                'data_root': str(data_root), 'binding': restoration_binding, 'goals': list(goals)})
            self.inspection['historical_dependency'] = deepcopy(self.dependency)
        except BaseException:
            self.close(); raise

    def _rpc(self, request):
        self.process.stdin.write(json.dumps(request, allow_nan=False) + '\n'); self.process.stdin.flush()
        try: line = self._responses.get(timeout=self.timeout)
        except queue.Empty:
            self.close(); raise TimeoutError('native progress worker exceeded bounded RPC timeout')
        if line is None:
            self._stderr.seek(0)
            raise RuntimeError('native progress worker exited: ' + self._stderr.read().decode('utf-8', errors='replace')[-4000:])
        response = json.loads(line)
        if not response['ok']:
            raise RuntimeError('native progress worker: ' + response['error'])
        return response['result']

    def inspect_anchor(self, t):
        return self._rpc({'op': 'inspect', 't': t})

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write('{"op":"close"}\n'); self.process.stdin.flush()
                    self.process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    self.process.terminate()
                try: self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill(); self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream: stream.close()
            self.process = None
        if self._stderr is not None:
            self._stderr.close(); self._stderr = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def make_backend(config, source, data_root, binding, goals):
    return NativeProgressBackend(config, source, data_root, binding, goals)


def _worker(root, *, runtime_factory=None):
    # The current augmentation package is deliberately not added to this worker.
    # Historical imports resolve to their accepted checkout in a fresh process.
    inspect_dependency(root)
    sys.path.insert(0, str(Path(root).resolve()))
    session = None
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                with contextlib.redirect_stdout(sys.stderr):
                    if request['op'] == 'open':
                        if session is not None: raise ValueError('worker already opened')
                        module_paths = request['config'].get('module_paths', [])
                        if not isinstance(module_paths, list) or any(not isinstance(p, str) for p in module_paths):
                            raise ValueError('native module_paths must be explicit import root paths')
                        for path in reversed(module_paths):
                            resolved = Path(path).expanduser().resolve(strict=True)
                            if not resolved.is_dir(): raise ValueError('native import root must be a directory')
                            # Keep the byte-pinned historical egrs ahead of all
                            # user-declared LIBERO/native import roots.
                            sys.path.insert(1, str(resolved))
                        source = request['source']; binding = request['binding']; goals = request['goals']
                        session = (runtime_factory or _runtime)(request['config'], source, request['data_root'], binding, goals)
                        result = session.inspection
                    elif request['op'] == 'inspect':
                        result = inspect_session(session, source, binding, goals, request['t'])
                    elif request['op'] == 'close':
                        break
                    else: raise ValueError('unknown native worker operation')
                response = {'ok': True, 'result': result}
            except Exception as error:
                response = {'ok': False, 'error': type(error).__name__ + ': ' + str(error)[:4000]}
            print(json.dumps(response, allow_nan=False), flush=True)
    finally:
        if session is not None:
            with contextlib.redirect_stdout(sys.stderr): session.close()


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--native-worker':
        raise SystemExit('Internal worker; use the augmentation progress producer command.')
    _worker(sys.argv[2])
