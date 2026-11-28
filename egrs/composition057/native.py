"""Construct and verify one fixed Scene2 precompleted source using the pinned core."""

from contextlib import contextmanager
from pathlib import Path

import numpy as np

from .catalog import (CANONICAL_BDDL_SHA256, CANONICAL_INITIAL_STATES_SHA256,
                      CANONICAL_SUITE, CANONICAL_TASK_ID, CANONICAL_TASK_NAME,
                      expected, get_task, render_bddl)
from .evidence import (array_digest, canonical_rows, digest, read_json, vector,
                       verified_artifacts, write_json)


SCHEMA = 'remaining-composition057-source-v1'
SETTLE_STEPS = 80
AUDIT_STEPS = 150
REPLAYS = 2
MAX_CANDIDATES = 24
REGION = 'basket_1_contain_region'
BASKET = 'basket_1'
OBJECTS = ('alphabet_soup_1', 'cream_cheese_1', 'tomato_sauce_1', 'ketchup_1',
           'orange_juice_1', 'milk_1', 'butter_1', BASKET)
OFFICIAL_GOALS = [['in', OBJECTS[0], REGION], ['in', OBJECTS[2], REGION]]
OFFICIAL_INSTRUCTION = 'put both the alphabet soup and the tomato sauce in the basket'


class _CheckpointAbort(BaseException):
    """Pass a storage failure through the core's recoverable audit boundary."""


class Controls:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        self.attempted = self.completed = self.failed = 0
        self.phase = 'input_verification'
        self.candidate = self.replay = None

    def record(self):
        return dict(phase=self.phase, candidate=self.candidate, replay=self.replay,
                    attempted_control_steps=self.attempted, completed_control_steps=self.completed,
                    failed_control_steps=self.failed)

    def _emit(self):
        try:
            self.checkpoint(self.record())
        except Exception as error:
            raise _CheckpointAbort from error

    def transition(self, phase, *, candidate=None, replay=None):
        self.phase, self.candidate, self.replay = phase, candidate, replay
        self._emit()

    def step(self, function, *args):
        self.attempted += 1
        self._emit()
        try:
            result = function(*args)
        except BaseException:
            self.failed += 1
            self._emit()
            raise
        self.completed += 1
        return result


def _source_row(row):
    matches = [item for item in expected() if item['episode_id'] == row.get('episode_id')]
    if not matches or any(type(row.get(key)) is not type(value) or row[key] != value
                          for key, value in matches[0].items()):
        raise ValueError('source row differs from the fixed Task057 population')
    if any(type(value) is not bool for value in row['initial_mask']):
        raise ValueError('source requires the boolean precompleted mask')
    return matches[0]


def _inputs(cfg, row):
    canonical = Path(cfg['canonical_bddl']).read_bytes()
    initial = Path(cfg['canonical_initial_states']).read_bytes()
    if digest(canonical) != CANONICAL_BDDL_SHA256 or digest(initial) != CANONICAL_INITIAL_STATES_SHA256:
        raise ValueError('canonical Scene2 source asset SHA-256 differs')
    index = row['initial_state_index']
    original = canonical_rows(initial)[index]
    environment_raw = Path(cfg['environment_config']).read_bytes()
    environment = read_json(environment_raw)['environment']
    ancestry = dict(suite=CANONICAL_SUITE, task_id=CANONICAL_TASK_ID, task_name=CANONICAL_TASK_NAME,
                    initial_state_index=index, bddl_sha256=digest(canonical),
                    init_asset_sha256=digest(initial), raw_initial_state_sha256=array_digest(original),
                    environment_config_sha256=digest(environment_raw))
    return render_bddl(canonical, row['task_id']), original, environment, ancestry


def _verify_official_task():
    from libero.libero import benchmark

    suite = benchmark.get_benchmark_dict()[CANONICAL_SUITE]()
    task = suite.get_task(CANONICAL_TASK_ID)
    if (task.name, task.bddl_file, task.init_states_file) != (
        CANONICAL_TASK_NAME, CANONICAL_TASK_NAME + '.bddl', CANONICAL_TASK_NAME + '.pruned_init'
    ):
        raise ValueError('native LIBERO-10 task zero identity differs from canonical Scene2')


def _predicate_values(env, inner, goals):
    raw = [inner._eval_predicate(predicate) for predicate in goals]
    success = env.check_success()
    if any(not isinstance(value, (bool, np.bool_)) for value in (*raw, success)):
        raise ValueError('native predicate facts must be boolean')
    values = [bool(value) for value in raw]
    if bool(success) != all(values):
        raise ValueError('native success disagrees with the two actual predicates')
    return values


@contextmanager
def _scene(path, index, goals, instruction):
    from benchmark.remaining_goals import libero_env as bridge

    env = bridge._new_scene(path, image_size=256, control_freq=20)
    try:
        env.seed(index)
        bridge.reset_scene(env)
        inner = bridge._task_environment(env)
        if ([list(value) for value in inner.parsed_problem['goal_state']] != goals
                or env.language_instruction != instruction
                or list(env.obj_of_interest) != [goal[1] for goal in goals] + [BASKET]
                or inner.workspace_name != 'living_room_table'
                or set(inner.objects_dict) != set(OBJECTS)
                or inner.fixtures_dict
                or inner.parsed_problem['fixtures'] != {'living_room_table': ['living_room_table']}
                or inner.object_sites_dict[REGION].parent_name != BASKET
                or inner.parsed_problem['regions'][REGION]['target'] != BASKET):
            raise ValueError('native BDDL goal, language or Scene2 object/region identity differs')
        yield env, inner
    finally:
        env.close()


def _binding(env, inner, state):
    from benchmark.remaining_goals.construction import _descendants
    from benchmark.remaining_goals.finish.environment import _layout
    from benchmark.remaining_goals.libero_env import model_xml_hash
    from benchmark.states import mujoco_state as ms

    model = env.sim.model
    layout = ms.StateLayout.from_state(state, model)
    topology = _layout(model)
    topology['na'] = layout.na
    topology['jnt_bodyid'] = np.asarray(model.jnt_bodyid).tolist()
    for name, obj in inner.objects_dict.items():
        joints = list(obj.joints)
        if len(joints) != 1 or joints[0] != name + '_joint0':
            raise ValueError(f'unexpected Scene2 object joint: {name}')
        ji = model.joint_name2id(joints[0])
        bid = model.body_name2id(obj.root_body)
        if (not 0 <= ji < model.njnt or not 0 < bid < model.nbody or model.jnt_type[ji] != 0
                or model.jnt_bodyid[ji] != bid or inner.obj_body_id[name] != bid):
            raise ValueError(f'model joint does not bind exact native object body: {name}')
    sid = model.site_name2id(REGION)
    if not 0 <= sid < model.nsite or model.site_bodyid[sid] not in _descendants(model, inner.obj_body_id[BASKET]):
        raise ValueError('compiled basket site owner differs')
    return {'model_xml_sha256': model_xml_hash(env), 'topology': topology}


def _indices(topology, completed):
    if (topology['nq'], topology['nv'], topology['na']) != (65, 57, 0):
        raise ValueError('Scene2 state topology differs from the canonical vector shape')
    joint_names = topology['joint_names']
    if (len(joint_names) != topology['njnt'] or len(set(joint_names)) != len(joint_names)
            or sum(kind == 0 for kind in topology['jnt_type']) != len(OBJECTS)):
        raise ValueError('incomplete Scene2 joint layout')
    qnext = vnext = 0
    addresses = {}
    for name, kind, qpos, qvel in zip(joint_names, topology['jnt_type'],
                                      topology['jnt_qposadr'], topology['jnt_dofadr'], strict=True):
        qwidth, vwidth = {0: (7, 6), 1: (4, 3), 2: (1, 1), 3: (1, 1)}[kind]
        if (qpos, qvel) != (qnext, vnext):
            raise ValueError('joint topology is not a full qpos/qvel partition')
        if kind == 0:
            addresses[name] = (qpos, qvel)
        qnext += qwidth
        vnext += vwidth
    if (qnext, vnext) != (65, 57) or set(addresses) != {name + '_joint0' for name in OBJECTS}:
        raise ValueError('unexpected Scene2 free-joint inventory')
    qpos, qvel = addresses[completed + '_joint0']
    return list(range(1 + qpos, 8 + qpos)) + list(range(66 + qvel, 72 + qvel))


def _confirmation_observations():
    from benchmark.remaining_goals.headless.protocols import get_protocol

    return get_protocol().confirmation_steps + 1


def _release_confirmed(rows):
    count = _confirmation_observations()
    return len(rows) >= count and all(row['released'] is True for row in rows[:count])


def _audit(env, inner, state, episode, profile, controls, steps):
    from benchmark.remaining_goals import build, validation
    from benchmark.remaining_goals.finish.environment import _release
    from benchmark.remaining_goals.headless.environment import _callback_status
    from benchmark.remaining_goals.headless.geometry import GeometryObserver, release_measurement

    targets = {name: inner.objects_dict[name] for name in
               (profile['completed_object'], profile['remaining_object'])}
    gripper = env.robots[0].gripper
    completed = profile['completed_object']
    observed = []

    class Audit(build.CandidateAuditEnv):
        def restore_candidate(self, item):
            observation = super().restore_candidate(item)
            self.geometry = GeometryObserver(env, targets, gripper, contact_filter_getter=_callback_status)
            return observation

        def step(self, action):
            return controls.step(super().step, action)

        def validation_snapshot(self):
            snapshot = super().validation_snapshot()
            values = _predicate_values(env, inner, profile['raw_goals'])
            if values != snapshot['goals']:
                raise ValueError('native goal truth changed during a read-only snapshot')
            poses = self.geometry.pose()
            old, legacy = _release(env, inner, gripper, targets[completed])
            released, release = release_measurement(completed, old, legacy, self.geometry.static, poses)
            if array_digest(snapshot['state']) != array_digest(build._state(env)):
                raise ValueError('release measurement changed physical state')
            observed.append(dict(step=len(observed), state_sha256=array_digest(snapshot['state']),
                                 goals=values, released=released, release=release, poses=poses))
            return snapshot

    audit = Audit(env, state, profile['goals'])
    physics = validation.validate_candidate(audit, episode, steps=steps, hold_action=build.HOLD,
                                            **validation.RGB_QUANTIZATION_AUDIT)
    measurement = getattr(audit, 'geometry', None)
    evidence = {'physics': physics, 'release': {'object_name': completed,
                'confirmation_observations': _confirmation_observations(),
                'geometry': measurement.static if measurement is not None else None, 'trace': observed}}
    return evidence, audit.initial_observation


def _accepted(evidence, steps):
    return (evidence['physics']['technical_acceptance'] is True
            and (evidence['release']['trace'][0]['released'] is True if steps == 0
                 else _release_confirmed(evidence['release']['trace'])))


def _policy_observation(observation):
    from benchmark.remaining_goals.libero_env import OBSERVATION_KEYS

    cameras = ('agentview_image', 'robot0_eye_in_hand_image')
    required = {*cameras, 'robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos'}
    if (not required <= observation.keys() or not observation.keys() <= set(OBSERVATION_KEYS)
            or any(observation[key].dtype != np.uint8 or observation[key].ndim != 3
                   or observation[key].shape[-1] != 3 for key in cameras)):
        raise ValueError('initial observation requires both native uint8 RGB cameras and policy-only proprioception')


def _match_reset_observation(replayed, original):
    from benchmark.remaining_goals.validation import RGB_QUANTIZATION_AUDIT, compare_observations

    check = compare_observations(replayed, original, atol=0, require_non_rgb_exact=True,
                                 refresh_state_unchanged=True, **RGB_QUANTIZATION_AUDIT)
    if not check['matches'] or not check['non_rgb_bit_exact']:
        raise ValueError('typed initial observation differs across independent reset')


def _window(directory, name, env, inner, state, episode, profile, controls):
    from benchmark.remaining_goals.observation_artifact import save_observation_artifact

    evidence, observation = _audit(env, inner, state, episode, profile, controls, AUDIT_STEPS)
    path = directory / (name + '.json')
    write_json(path, evidence)
    if not _accepted(evidence, AUDIT_STEPS):
        raise ValueError(f'{name} failed original physical or five-observation source-release admission')
    _policy_observation(observation)
    reference = save_observation_artifact(directory, name + '.npz', observation)
    return {'audit_path': path.name, 'observation': reference}, observation


def _build(cfg, row, directory, controls):
    from benchmark.remaining_goals import build, libero_env as bridge
    from benchmark.remaining_goals.construction import placement_candidates, state_diff_whitelist
    from benchmark.states import mujoco_state as ms

    task = get_task(row['task_id'])
    derived, original, environment, ancestry = _inputs(cfg, row)
    if bridge.environment_identity(20) != environment:
        raise ValueError('actual LIBERO identity differs from frozen environment config')
    _verify_official_task()
    bddl = directory / 'task.bddl'
    bddl.write_bytes(derived)
    index = row['initial_state_index']
    controls.transition('canonical_scene')
    with _scene(Path(cfg['canonical_bddl']), index, OFFICIAL_GOALS, OFFICIAL_INSTRUCTION) as (env, inner):
        canonical = _binding(env, inner, original)
        bridge.restore_raw_state(env, original)
        canonical_values = _predicate_values(env, inner, OFFICIAL_GOALS)
        if canonical_values != [False, False]:
            raise ValueError('canonical selected index does not start from empty basket goals')

    active = task['completed_object']
    goals = task['raw_goals']
    instruction = task['instruction']
    controls.transition('derived_scene')
    with _scene(bddl, index, goals, instruction) as (env, inner):
        binding = _binding(env, inner, original)
        if binding['topology'] != canonical['topology']:
            raise ValueError('derived Scene2 compiled topology differs from canonical')
        bridge.restore_raw_state(env, original)
        original_values = _predicate_values(env, inner, goals)
        if original_values != [False, False]:
            raise ValueError('canonical Scene2 index already completes a new goal')
        controls.transition('base_settle')
        for _ in range(SETTLE_STEPS):
            controls.step(build._step, env, build.HOLD)
        base = build._state(env)
        if not np.isfinite(base).all() or _predicate_values(env, inner, goals) != [False, False]:
            raise ValueError('canonical settled base is nonfinite or already completes a goal')
        model = env.sim.model
        layout = ms.StateLayout.from_model(model)
        indices = _indices(binding['topology'], active)
        other = sorted(set(range(len(base))) - set(indices))
        episode = {**row, 'suite': task['suite'], 'task_name': task['name'], 'seed': index,
                   'goal_specs': task['goals'], 'bddl_sha256': digest(derived),
                   'model_xml_sha256': binding['model_xml_sha256'],
                   'reference_robot_qpos': ms.get_robot_qpos(base, layout, n=9).tolist()}
        seeds = placement_candidates(base, model, env.sim.data, active, REGION, relation='in',
                                     reservation_objects=[active, task['remaining_object']], max_candidates=MAX_CANDIDATES)
        if not 1 <= len(seeds) <= MAX_CANDIDATES:
            raise ValueError('no bounded Scene2 active-object candidates')
        state = construction = None
        for number, seed in enumerate(seeds):
            controls.transition('candidate_settle', candidate=number)
            candidate = seed['state'].copy()
            candidate[layout.qvel_slice] = base[layout.qvel_slice]
            if seed['allowed_indices'] != indices or array_digest(candidate[other]) != array_digest(base[other]):
                raise ValueError('native geometry candidate changed non-A state')
            bridge.restore_raw_state(env, candidate)
            for _ in range(SETTLE_STEPS):
                controls.step(build._step, env, build.HOLD)
            settled = build._state(env)
            selected = base.copy()
            selected[indices] = settled[indices]
            changes = state_diff_whitelist(base, selected, model, indices)
            if not changes['valid'] or array_digest(selected[other]) != array_digest(base[other]):
                raise ValueError('transplant changed non-A state coordinates')
            stem = f'candidate_{number:02d}'
            controls.transition('static_audit', candidate=number)
            static, _ = _audit(env, inner, selected, episode, task, controls, 0)
            write_json(directory / f'{stem}_static.json', {'seed': seed['diagnostics'], 'audit': static})
            if static['physics']['error'] is not None:
                raise ValueError(f'{stem} static audit encountered a native error: {static["physics"]["error"]}')
            if not _accepted(static, 0):
                continue
            controls.transition('construction_audit', candidate=number)
            dynamic, observation = _audit(env, inner, selected, episode, task, controls, AUDIT_STEPS)
            audit_path = f'{stem}_construction.json'
            write_json(directory / audit_path, dynamic)
            if dynamic['physics']['error'] is not None:
                raise ValueError(f'{stem} construction audit encountered a native error: {dynamic["physics"]["error"]}')
            if not _accepted(dynamic, AUDIT_STEPS):
                continue
            from benchmark.remaining_goals.observation_artifact import save_observation_artifact

            _policy_observation(observation)
            reference = save_observation_artifact(directory, 'construction.npz', observation)
            construction = {'audit_path': audit_path, 'observation': reference}
            state = selected
            break
        if state is None:
            raise ValueError('every bounded A candidate failed actual mask, physics, observation or release admission')

    replays = []
    for replay in range(REPLAYS):
        controls.transition('independent_replay', replay=replay)
        with _scene(bddl, index, goals, instruction) as (env, inner):
            replay_binding = _binding(env, inner, state)
            if replay_binding != binding:
                raise ValueError('independent reset binding differs from construction')
            window, replayed = _window(directory, f'replay_{replay}', env, inner, state, episode, task, controls)
            _match_reset_observation(replayed, observation)
            replays.append({**window, 'binding': replay_binding})

    # Publish only the selected precompleted state. A's original components and
    # complement hash are retained for audit without exporting a normal bank.
    state_path = directory / 'state.npy'
    with state_path.open('xb') as stream:
        np.save(stream, state, allow_pickle=False)
    episode.update(state_path=state_path.name, state_sha256=digest(state_path.read_bytes()),
                   initial_observation=construction['observation'])
    provenance = {'canonical_binding': canonical, 'derived_binding': binding, 'indices': indices,
                  'base_array_sha256': array_digest(base), 'base_other_sha256': array_digest(base[other]),
                  'base_completed_component': base[indices].tolist(), 'final_array_sha256': array_digest(state),
                  'selected_candidate': number, 'canonical_goals': canonical_values,
                  'derived_raw_goals': original_values, 'settled_base_goals': [False, False]}
    return {'schema_version': SCHEMA, 'episode': episode, 'environment': environment,
            'ancestry': ancestry, 'provenance': provenance, 'construction_window': construction,
            'replay_windows': replays, 'controls': controls.record(),
            'artifacts': {path.name: digest(path.read_bytes()) for path in sorted(directory.iterdir())}}


def build_source(cfg, row, output_dir, checkpoint):
    """Attempt a single fixed-index 10 source in a new directory."""
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    controls = Controls(checkpoint)
    try:
        row = _source_row(row)
        controls.transition('input_verification')
        manifest = _build(cfg, row, directory, controls)
        controls.transition('offline_verification')
        _inspect(manifest, directory, row, cfg)
        source_path = directory / 'source.json'
        write_json(source_path, manifest)
        controls.transition('ready')
        return {'status': 'ready', 'source_manifest': str(source_path)}
    except _CheckpointAbort as error:
        raise error.__cause__
    except Exception as error:
        message = f'{type(error).__name__}: {error}'
        write_json(directory / 'failure.json', {'error': message, 'controls': controls.record()})
        return {'status': 'failed', 'error': message}


def _binding_checks(binding, topology):
    if set(binding) != {'model_xml_sha256', 'topology'} or binding['topology'] != topology:
        raise ValueError('compiled model topology differs between source stages')
    checksum = binding['model_xml_sha256']
    if not isinstance(checksum, str) or len(checksum) != 64 or any(c not in 'abcdef0123456789' for c in checksum):
        raise ValueError('missing reset model XML SHA-256')


def _verify_window(contents, directory, window, episode, state, task, topology):
    from benchmark.remaining_goals.headless.geometry import release_measurement, validate_measurement_static
    from benchmark.remaining_goals.headless.scoped_sources import _observation_binding
    from benchmark.remaining_goals.headless.source_acceptance import _audit as verify_physics
    from benchmark.remaining_goals.observation_artifact import load_observation_artifact

    evidence = read_json(contents[window['audit_path']])
    observation_ref = window['observation']
    if digest(contents[observation_ref['path']]) != observation_ref['sha256']:
        raise ValueError('initial observation artifact hash differs from its reference')
    observation = load_observation_artifact(directory, observation_ref)
    _policy_observation(observation)
    verify_physics(evidence['physics'], episode, state, steps=AUDIT_STEPS,
                   initial_hash=observation_ref['observation_sha256'], fixed=True)
    _observation_binding(observation, evidence['physics']['trace'][0]['observation_check'])
    release = evidence['release']
    completed, remaining = task['completed_object'], task['remaining_object']
    if (release['object_name'] != completed or release['confirmation_observations'] != _confirmation_observations()
            or len(release['trace']) != AUDIT_STEPS + 1):
        raise ValueError('release trace identity or original confirmation window differs')
    geometry = validate_measurement_static(release['geometry'])
    if (set(geometry['groups']) != {completed, remaining, 'hand', 'left_fingerpad', 'right_fingerpad'}
            or geometry['compiled_model_xml_sha256'] != episode['model_xml_sha256']
            or geometry['body_names'] != topology['body_names'] or geometry['geom_names'] != topology['geom_names']
            or geometry['arrays']['geom_bodyid'] != topology['geom_bodyid']
            or geometry['arrays']['body_parentid'] != topology['body_parentid']):
        raise ValueError('release geometry differs from the compiled topology or intended targets')
    for name in (completed, remaining):
        index = topology['joint_names'].index(name + '_joint0')
        if geometry['owner_roots'][name] != topology['jnt_bodyid'][index]:
            raise ValueError('release geometry owner differs from the named native target')
    for sample, physics in zip(release['trace'], evidence['physics']['trace'], strict=True):
        if (type(sample['step']) is not int or sample['step'] != physics['step']
                or sample['goals'] != [True, False] or any(type(goal) is not bool for goal in sample['goals'])
                or sample['state_sha256'] != physics['state_sha256']):
            raise ValueError('release trace is not bound to the actual same-step source mask and state')
        traced = np.asarray(physics['state'], dtype=np.float64)
        if (array_digest(physics['qvel']) != array_digest(traced[66:])
                or array_digest(physics['robot_qpos']) != array_digest(traced[1:10])
                or set(physics['object_positions']) != set(OBJECTS)):
            raise ValueError('raw physics vectors do not agree with the bound state and object inventory')
        for name in OBJECTS:
            ji = topology['joint_names'].index(name + '_joint0')
            start = 1 + topology['jnt_qposadr'][ji]
            if array_digest(physics['object_positions'][name]) != array_digest(traced[start:start + 3]):
                raise ValueError('monitored object pose differs from the bound state')
        legacy = sample['release']
        value, actual = release_measurement(completed, legacy['legacy_released'], legacy['legacy'],
                                            geometry, sample['poses'])
        if value is not sample['released'] or actual != legacy:
            raise ValueError('saved release measurement differs from native geometry recomputation')
    if not _release_confirmed(release['trace']):
        raise ValueError('restored precompleted object did not satisfy the five-observation release window')
    return observation


def _inspect(manifest, directory, row, cfg):
    task = get_task(row['task_id'])
    derived, _, environment, ancestry = _inputs(cfg, row)
    if (manifest['schema_version'] != SCHEMA or manifest['ancestry'] != ancestry
            or manifest['environment'] != environment):
        raise ValueError('source manifest ancestry or environment identity differs')
    episode = manifest['episode']
    if _source_row(episode) != row or any(episode.get(key) != expected_value for key, expected_value in {
        'suite': task['suite'], 'task_name': task['name'], 'seed': row['initial_state_index'],
        'goal_specs': task['goals'], 'bddl_sha256': digest(derived), 'state_path': 'state.npy',
    }.items()):
        raise ValueError('source episode differs from the fixed composition identity')
    if set(manifest['artifacts']) != {path.name for path in directory.iterdir() if path.name != 'source.json'}:
        raise ValueError('source artifact inventory differs from its hash manifest')
    contents = verified_artifacts(directory, manifest['artifacts'])
    if contents['task.bddl'] != derived or digest(contents[episode['state_path']]) != episode['state_sha256']:
        raise ValueError('selected BDDL or state artifact hash differs from episode bindings')
    state = vector(contents[episode['state_path']])
    provenance = manifest['provenance']
    topology = provenance['canonical_binding']['topology']
    binding = provenance['derived_binding']
    _binding_checks(provenance['canonical_binding'], topology)
    _binding_checks(binding, topology)
    if episode['model_xml_sha256'] != binding['model_xml_sha256']:
        raise ValueError('source episode differs from derived reset XML SHA-256')
    indices = _indices(topology, task['completed_object'])
    other = sorted(set(range(len(state))) - set(indices))
    if provenance['indices'] != indices or any(type(index) is not int for index in provenance['indices']):
        raise ValueError('transplant whitelist does not bind only the exact A free joint')
    base = state.copy()
    base[indices] = provenance['base_completed_component']
    if (not np.isfinite(base).all() or array_digest(base) != provenance['base_array_sha256']
            or array_digest(state) != provenance['final_array_sha256']
            or array_digest(base[other]) != provenance['base_other_sha256']
            or array_digest(base[1:10]) != array_digest(episode['reference_robot_qpos'])
            or any(provenance.get(field) != [False, False] or any(type(bit) is not bool for bit in provenance[field])
                   for field in ('canonical_goals', 'derived_raw_goals', 'settled_base_goals'))):
        raise ValueError('settled-base and A-only transplant ancestry differs')
    construction = manifest['construction_window']
    selected = provenance['selected_candidate']
    if (type(selected) is not int or selected not in range(MAX_CANDIDATES)
            or construction['audit_path'] != f'candidate_{selected:02d}_construction.json'
            or construction['observation'] != episode['initial_observation']
            or construction['observation']['path'] != 'construction.npz'):
        raise ValueError('selected construction audit does not bind the published initial observation')
    original_obs = _verify_window(contents, directory, construction, episode, state, task, topology)
    replays = manifest['replay_windows']
    if len(replays) != REPLAYS:
        raise ValueError('source requires two independent replay windows')
    for number, replay in enumerate(replays):
        if (replay['audit_path'] != f'replay_{number}.json' or replay['observation']['path'] != f'replay_{number}.npz'
                or replay['binding'] != binding):
            raise ValueError('independent replay identity or reset binding differs')
        observation = _verify_window(contents, directory, replay, episode, state, task, topology)
        _match_reset_observation(observation, original_obs)
    controls = manifest['controls']
    attempted, completed, failed = (controls[key] for key in
        ('attempted_control_steps', 'completed_control_steps', 'failed_control_steps'))
    audits = sum(path.endswith('_construction.json') for path in contents)
    if (any(type(value) is not int for value in (attempted, completed, failed)) or failed != 0
            or controls['phase'] != 'independent_replay' or controls['replay'] != REPLAYS - 1
            or attempted != completed or completed != (2 + selected) * SETTLE_STEPS + (REPLAYS + audits) * AUDIT_STEPS):
        raise ValueError('source control ledger differs from recorded native windows')
    return episode


def inspect_source(source_manifest, row, cfg):
    """Read and recompute persisted source evidence without native simulation."""
    path = Path(source_manifest).resolve()
    raw = path.read_bytes()
    if path.name != 'source.json':
        raise ValueError('source manifest must be the admitted source.json')
    try:
        episode = _inspect(read_json(raw), path.parent, _source_row(row), cfg)
    except (KeyError, TypeError, IndexError, OSError) as error:
        raise ValueError(f'invalid Task057 source evidence: {error}') from error
    return {'task_id': episode['task_id'], 'initial_state_index': episode['initial_state_index'],
            'episode_id': episode['episode_id'], 'episode': episode,
            'source_manifest': str(path), 'source_manifest_sha256': digest(raw)}
