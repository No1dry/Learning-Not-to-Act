"""Native production algorithm exercised only against CPU fake sessions."""
import copy
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from egrs.augmentation import progress_native as native


def historical_root():
    """Explicit dependency override, with this workspace's existing checkout fallback."""
    candidate = os.environ.get('EGRS_PROGRESS_HISTORICAL_ROOT')
    root = native.Path(candidate) if candidate else native.Path(__file__).resolve().parents[2] / 'Learning-Not-to-Act-task016'
    if not root.is_dir():
        pytest.skip('accepted SourceEpisode integration requires EGRS_PROGRESS_HISTORICAL_ROOT')
    native.inspect_dependency(root)
    return root


def write_original_demo(tmp_path, observation_offset=0, action_offset=0):
    import h5py
    source, binding = fixture()
    source.update(instruction='synthetic instruction', file='libero_goal/synthetic.hdf5',
        mapping={**source['mapping'], 'images': ['obs/agentview_rgb', 'obs/eye_in_hand_rgb'],
                 'action': 'actions', 'observation_offset': observation_offset, 'action_offset': action_offset})
    binding['alignment'].update(observation_offset=observation_offset, action_offset=action_offset,
                                 state_offset=observation_offset + 1)
    path = tmp_path / source['file']; path.parent.mkdir(parents=True)
    physical = source['length'] + observation_offset
    with h5py.File(path, 'w') as hdf:
        data = hdf.create_group('data')
        data.attrs['env_args'] = native.json.dumps({'problem_name': 'synthetic', 'env_kwargs': {}})
        data.attrs['macros_image_convention'] = 'opengl'
        data.attrs['problem_info'] = native.json.dumps({'language_instruction': source['instruction']})
        ep = data.create_group('demo_0')
        ep.attrs['model_file'] = '<mujoco/>'
        ep.attrs['num_samples'] = physical
        ep.create_dataset('states', data=np.arange(physical * 3, dtype=float).reshape(physical, 3))
        ep.create_dataset('actions', data=np.zeros((source['length'] + action_offset, 7)))
        for field in ('agentview_rgb', 'eye_in_hand_rgb'):
            ep.create_dataset('obs/' + field, data=np.zeros((physical, 4, 4, 3), dtype=np.uint8))
    return source, binding


def fake_source_episode_worker(tmp_path):
    script = tmp_path / 'fake_native_boundary.py'
    script.write_text('''import importlib.util,sys
spec=importlib.util.spec_from_file_location('production_progress_native',sys.argv[1])
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
def factory(config,source,data_root,binding,goals):
    from egrs.offline import sim_native as old
    episode,legacy,layout=native.open_source_episode(old,data_root,source,binding)
    class FakeNativeSession:
        config={'rgb_threshold':.03,'replay_state_atol':1e-6}
        choose_alignment=staticmethod(old.choose_alignment)
        def measure(self,frame,rule):
            index=frame+(rule in ('next_state','replay_action'))
            state=episode.state(index)
            return {'state':state,'source_state_sha256':native._state_hash(episode.state(frame+(rule=='next_state'))),
                    'residuals':dict.fromkeys(('agentview','wrist'),.2 if rule=='same_state' else .01),
                    'flipped_residuals':dict.fromkeys(('agentview','wrist'),.2)}
        def facts(self,frame,rule):
            return dict(zip(goals,[True,False])),[],[g['predicate'] for g in binding['active_goals']]
        def close(self): episode.close()
    session=FakeNativeSession();session.episode=episode
    assert legacy['source_id']==source['source_id']
    session.inspection={'augmentation_bridge':layout,'reader_module_path':old.__file__,'source_id':legacy['source_id'],
                        'native_simulator_loaded':any(x=='mujoco' or x.startswith('libero.') for x in sys.modules)}
    print('synthetic native boundary log stays outside JSON protocol')
    return session
native._worker(sys.argv[2],runtime_factory=factory)
''', encoding='utf-8')
    return script


@pytest.mark.parametrize('offset', [0, 1])
def test_real_accepted_source_episode_synthetic_hdf_through_fake_worker_rpc(tmp_path, monkeypatch, offset):
    root = historical_root()
    source, binding = write_original_demo(tmp_path, offset, offset)
    original = copy.deepcopy(source)
    script = fake_source_episode_worker(tmp_path)
    real_popen = native.subprocess.Popen
    monkeypatch.setattr(native.subprocess, 'Popen', lambda args, **kwargs: real_popen(
        [sys.executable, '-u', str(script), native.__file__, str(root)], **kwargs))
    with native.NativeProgressBackend({'historical_root': str(root)}, source, tmp_path, binding, ['A', 'B']) as backend:
        assert backend.inspection['historical_dependency']['accepted_revision'] == 'fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391'
        assert backend.inspection['historical_dependency']['files']['egrs/offline/sim_native.py']
        assert backend.inspection['augmentation_bridge']['native_episode'] == 'demo_0'
        assert backend.inspection['source_id'] == source['source_id']
        assert backend.inspection['augmentation_bridge']['physical_length'] == source['length'] + offset
        assert not backend.inspection['native_simulator_loaded']
        assert native.Path(backend.inspection['reader_module_path']).resolve() == (root / 'egrs/offline/sim_native.py').resolve()
        row = backend.inspect_anchor(2)
        assert row['reliable'] and row['pending_goals'] == ['B']
        assert row['state_binding']['observation_index'] == 2 + offset
        assert row['state_binding']['action_index'] == 2 + offset
        assert row['state_binding']['restored_state_index'] == 3 + offset
        assert len(row['state_binding']['state_sha256']) == 64
    assert 'mujoco' not in sys.modules and 'libero' not in sys.modules
    assert source == original


def test_physical_lengths_are_reconciled_not_assumed_from_logical_T(tmp_path, monkeypatch):
    root = historical_root()
    source, binding = write_original_demo(tmp_path, observation_offset=1, action_offset=0)
    script = fake_source_episode_worker(tmp_path)
    real_popen = native.subprocess.Popen
    monkeypatch.setattr(native.subprocess, 'Popen', lambda args, **kwargs: real_popen(
        [sys.executable, '-u', str(script), native.__file__, str(root)], **kwargs))
    with pytest.raises(RuntimeError, match='requires equal physical state/action/camera lengths'):
        native.NativeProgressBackend({'historical_root': str(root)}, source, tmp_path, binding, ['A', 'B'])


def fixture():
    source = {'source_id': 'synthetic#demo_0', 'length': 6,
              'episode': 'data/demo_0',
              'mapping': {'observation_offset': 0, 'action_offset': 0}}
    binding = {'orientation': 'opengl', 'state_field': 'states',
               'state_alignment_basis': 'synthetic explicit source producer contract',
               'active_goals': [{'id': 'A', 'predicate': ['in', 'x', 'box']},
                                {'id': 'B', 'predicate': ['in', 'y', 'box']}],
               'invariant_predicates': [],
               'alignment': {'rule': 'next_state', 'orientation': 'identity',
                             'state_offset': 1, 'observation_offset': 0, 'action_offset': 0}}
    return source, binding


@pytest.mark.parametrize('episode,expected', [('data/demo_0', 'demo_0'), ('demo_12', 'demo_12')])
def test_augmentation_episode_normalizes_only_explicit_demo_group(episode, expected):
    assert native.episode_name(episode) == expected


@pytest.mark.parametrize('episode', ['other/demo_0', 'data/demo_0/obs', 'data/../demo_0', '/data/demo_0', 'data/demo_x'])
def test_augmentation_episode_rejects_ambiguous_paths(episode):
    with pytest.raises(ValueError, match='episode'):
        native.episode_name(episode)


class Session:
    @staticmethod
    def choose_alignment(comparisons, **kwargs):
        # Boundary fake checks that the real producer supplies a frame-bound
        # accepted-validator certificate, rather than an ungrounded bool.
        assert all(x['samples'][0]['frame'] == 2 for x in comparisons)
        certificate = kwargs['equivalence']
        if certificate:
            assert certificate['checks'][0]['next_state_index'] == 3
            assert len(certificate['checks'][0]['next_state_sha256']) == 64
        return {'accepted': True, 'synthetic_validator': True}

    def __init__(self, scores=None, state_error=0):
        self.calls = []
        self.scores = scores or {'same_state': .2, 'next_state': .01, 'replay_action': .01}
        self.state_error = state_error
        self.config = {'rgb_threshold': .03, 'replay_state_atol': 1e-6}
        self.episode = SimpleNamespace(T=6)
        self.inspection = {'synthetic': True}

    def measure(self, frame, rule):
        self.calls.append((frame, rule))
        return {'residuals': {'agentview': self.scores[rule], 'wrist': self.scores[rule]},
                'state': np.array([1., self.state_error if rule == 'replay_action' else 0.])}

    def facts(self, frame, rule):
        self.calls.append(('facts', frame, rule))
        return {'A': True, 'B': False}, [], ['actual final atoms']


def test_local_equivalence_uses_full_state_and_current_anchor_only():
    source, binding = fixture()
    session = Session()
    row = native.inspect_session(session, source, binding, ['A', 'B'], 2)
    assert row['reliable'] and row['pending_goals'] == ['B']
    assert row['native_facts']['goal_values'] == {'A': True, 'B': False}
    assert {x[0] for x in session.calls if isinstance(x[0], int)} == {2}
    assert row['correspondence']['equivalence']['max_state_abs_residual'] == 0
    assert len(session.calls) <= native.ESTIMATED_RESTORES_PER_ANCHOR


@pytest.mark.parametrize('case', ['state', 'orientation', 'ambiguous', 'exception'])
def test_unresolved_correspondence_never_certifies_progress(case):
    source, binding = fixture()
    session = Session(state_error=.001 if case == 'state' else 0)
    if case == 'orientation': binding['alignment']['orientation'] = 'flip_vertical'
    if case == 'ambiguous': session.scores['same_state'] = .01
    if case == 'exception':
        old = session.measure
        def measure(frame, rule):
            if rule == 'same_state': raise ValueError('unresolved candidate')
            return old(frame, rule)
        session.measure = measure
    row = native.inspect_session(session, source, binding, ['A', 'B'], 2)
    assert not row['reliable'] and row['pending_goals'] is None
    assert row['diagnostics']


def test_binding_rejects_undeclared_state_action_or_goal_mapping():
    source, binding = fixture()
    native.validate_binding(source, binding, ['A', 'B'])
    for field in ['state_offset', 'action_offset', 'observation_offset']:
        bad = copy.deepcopy(binding)
        bad['alignment'][field] += 2
        with pytest.raises(ValueError): native.validate_binding(source, bad, ['A', 'B'])
    with pytest.raises(ValueError): native.validate_binding(source, binding, ['A'])


def test_terminal_boundary_is_a_diagnostic_without_clamping():
    source, binding = fixture()
    session = Session()
    row = native.inspect_session(session, source, binding, ['A', 'B'], 5)
    assert not row['reliable'] and not session.calls


@pytest.mark.parametrize('values,invariants', [({'A': True, 'B': None}, []),
                                             ({'A': True, 'B': False}, [False])])
def test_native_goal_or_invariant_gap_stays_diagnostic(values, invariants):
    source, binding = fixture()
    session = Session()
    session.facts = lambda frame, rule: (values, invariants, [])
    row = native.inspect_session(session, source, binding, ['A', 'B'], 2)
    assert not row['reliable'] and row['pending_goals'] is None
    assert row['diagnostics'] and row['native_facts']['goal_values'] == values


def test_import_and_dependency_inspection_load_no_native_packages(tmp_path):
    assert 'mujoco' not in sys.modules and 'libero' not in sys.modules
    with pytest.raises(ValueError, match='accepted native dependency differs'):
        native.inspect_dependency(tmp_path)
    lock = native.json.loads(native.Path(native.__file__).with_name('progress_native_files.json').read_text(encoding='utf-8-sig'))
    assert lock['accepted_revision'] == 'fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391'
    assert 'mujoco' not in sys.modules and 'libero' not in sys.modules


@pytest.mark.parametrize('wrong_final_goal', [False, True])
def test_concrete_runtime_uses_inherited_initialization_and_exact_original_rows(monkeypatch, wrong_final_goal):
    """Fake the native dependency boundary, execute the real new constructor."""
    import types
    source, binding = fixture()
    source.update(instruction='synthetic instruction', file='libero_10/synthetic.hdf5',
                  mapping={**source['mapping'], 'images': ['obs/agentview_rgb', 'obs/eye_in_hand_rgb'],
                           'action': 'actions'})
    events = []
    stored = np.zeros((4, 4, 3), dtype=np.uint8); stored[2:] = 255

    class Adapter:
        def _initialize(self):
            events.append('inherited_initialize')
            assert self.request['source']['T'] == 6
            assert self.request['source']['orientation'] == 'opengl'
            assert [g['atom'] for g in self.goals] == [g['predicate'] for g in binding['active_goals']]
            if wrong_final_goal: raise ValueError('native BDDL goals disagree with annotation map')
            self.index = 0
            self.env = SimpleNamespace(sim=SimpleNamespace(get_state=lambda: np.array([float(self.index)])))
            self.inner = SimpleNamespace(parsed_problem={'goal_state': [g['predicate'] for g in binding['active_goals']]})

        def _restore(self, index, action=None):
            events.append(('restore', index, action)); self.index = index + (action is not None)

        def _render(self, camera):
            return (stored.copy() if self.index == 3 else np.zeros_like(stored)), None

        def _foreground(self, raw): return np.ones((4, 4), dtype=bool)
        def close(self): events.append('closed')

    class Episode:
        def __init__(self, root, legacy_source): self.T = 6; self.inspection = {}
        def state(self, index): return np.array([float(index)])
        def rgb(self, frame, camera):
            assert frame == 2
            return stored.copy()

    def open_episode(old, root, source, binding):
        return Episode(root, source), {**source, 'episode': 'demo_0', 'T': source['length'],
                                      'orientation': binding['orientation']}, {'synthetic': True}
    monkeypatch.setattr(native, 'open_source_episode', open_episode)

    old = types.ModuleType('egrs.offline.sim_native')
    old.NativeAdapter = Adapter; old.SourceEpisode = Episode; old.np = np
    old.validate_config = lambda x: {'rgb_threshold': .03, 'replay_state_atol': 1e-6,
                                    'min_visible_pixels': 16, **x}
    old.choose_alignment = Session.choose_alignment
    old.CAMERAS = ('agentview', 'wrist')
    old.image_residual = lambda a, b, m, **kw: float(np.abs(a.astype(float) - b).mean() / 255)
    old.evaluate_atoms = lambda inner, goals: ({'A': True, 'B': False}, [])
    package = types.ModuleType('egrs.offline'); package.sim_native = old
    contract = types.ModuleType('egrs.offline.sim_contract')
    contract.load_goal_map = lambda: {'instructions': []}
    for name, module in [('egrs.offline', package), ('egrs.offline.sim_native', old),
                         ('egrs.offline.sim_contract', contract)]:
        monkeypatch.setitem(sys.modules, name, module)
    if wrong_final_goal:
        with pytest.raises(ValueError, match='native BDDL goals disagree'):
            native._runtime({'native': {}}, source, 'synthetic-root', binding, ['A', 'B'])
        assert events == ['inherited_initialize', 'closed']
    else:
        session = native._runtime({'native': {}}, source, 'synthetic-root', binding, ['A', 'B'])
        row = native.inspect_session(session, source, binding, ['A', 'B'], 2)
        assert row['reliable'] and row['pending_goals'] == ['B']
        assert row['state_binding']['restored_state_index'] == 3
        assert row['state_binding']['observation_index'] == 2
        assert row['state_binding']['action_index'] == 2
        assert len([x for x in events if isinstance(x, tuple)]) == 4
