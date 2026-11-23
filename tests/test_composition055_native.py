"""CPU doubles exercise the actual geometry and evidence rules without LIBERO."""
from hashlib import sha256
import json
import os
from pathlib import Path
import pickle
from types import SimpleNamespace
from zipfile import ZipFile

import numpy as np
import pytest

from egrs.augmentation.dependencies import activate_core


OBJECTS = ('alphabet_soup_1', 'cream_cheese_1', 'tomato_sauce_1', 'ketchup_1',
           'orange_juice_1', 'milk_1', 'butter_1', 'basket_1')
REGION = 'basket_1_contain_region'
ROW = {'task_id': 'composition_soup_butter', 'initial_state_index': 49,
       'episode_id': 'composition_soup_butter_s049_10',
       'source_id': 'composition055_canonical_basket_049',
       'instruction': 'put both the alphabet soup and the butter in the basket',
       'initial_mask': [True, False], 'split': 'test', 'horizon': 520,
       'retention_steps': 150}


class Model:
    def __init__(self):
        self.joint_names = [f'robot0_{i}' for i in range(9)] + [name + '_joint0' for name in OBJECTS]
        self.body_names = ['world', 'hand', 'left', 'right', 'living_room_table'] + list(OBJECTS)
        self.geom_names = ['left_pad', 'right_pad', 'palm', 'table'] + [name + '_geom' for name in OBJECTS]
        self.site_names = [REGION]
        self.actuator_names = []
        for kind in ('joint', 'body', 'geom', 'site', 'actuator'):
            names = getattr(self, kind + '_names')
            setattr(self, kind + '_id2name', names.__getitem__)
            setattr(self, kind + '_name2id', names.index)
        self.nq, self.nv, self.na, self.nu = 65, 57, 0, 0
        self.njnt, self.ngeom, self.nbody, self.nsite = 17, len(self.geom_names), len(self.body_names), 1
        self.nmesh = self.npair = self.nexclude = 0
        self.jnt_type = np.r_[np.full(9, 3), np.zeros(8, int)]
        self.jnt_qposadr = np.r_[np.arange(9), np.arange(9, 65, 7)]
        self.jnt_dofadr = np.r_[np.arange(9), np.arange(9, 57, 6)]
        self.jnt_bodyid = np.r_[np.full(9, 1), np.arange(5, 13)]
        self.body_parentid = np.r_[0, 0, 1, 1, np.zeros(9, int)]
        self.body_weldid = np.r_[0, 1, 2, 3, 0, np.arange(5, 13)]
        self.geom_bodyid = np.r_[2, 3, 1, 4, np.arange(5, 13)]
        self.site_bodyid = np.array([12])
        self.site_type = np.array([6])
        self.site_size = np.array([[.07, .07, .075]])
        self.geom_type = np.full(self.ngeom, 6)
        self.geom_dataid = np.full(self.ngeom, -1)
        self.geom_contype = self.geom_conaffinity = np.ones(self.ngeom, dtype=int)
        self.geom_margin = self.geom_gap = np.zeros(self.ngeom)
        self.geom_size = np.array([[.01, .01, .01]] * self.ngeom)
        self.geom_size[-1] = [.075, .075, .005]
        self.geom_rbound = np.linalg.norm(self.geom_size, axis=1)
        self.geom_pos = np.zeros((self.ngeom, 3))
        self.geom_quat = np.tile([1., 0, 0, 0], (self.ngeom, 1))
        self.pair_geom1 = self.pair_geom2 = self.exclude_signature = np.array([], dtype=int)
        self.actuator_trnid, self.actuator_trntype = np.empty((0, 2), int), np.array([], int)
        self.opt = SimpleNamespace(collision=0, disableflags=0, enableflags=0)

    def get_xml(self):
        return '<mujoco model="composition055_fake"/>'


class Scene:
    def __init__(self, state, predicates, instruction, fault, generation):
        self.state, self.fault, self.generation = state.copy(), fault, generation
        self.model, self.last_step, self.closed = Model(), 0, False
        model = self.model
        self.sim = SimpleNamespace(model=model, get_state=lambda: SimpleNamespace(flatten=lambda: self.state.copy()))
        self.sim.data = SimpleNamespace(geom_xpos=np.zeros((model.ngeom, 3)),
            geom_xmat=np.tile(np.eye(3).reshape(9), (model.ngeom, 1)),
            site_xmat=np.eye(3).reshape(1, 9), site_xpos=np.zeros((1, 3)), contact=[], ncon=0)
        objects = {name: SimpleNamespace(root_body=name, contact_geoms=[name + '_geom'], joints=[name + '_joint0'])
                   for name in OBJECTS}
        problems = {'goal_state': predicates, 'objects': {name: [name] for name in objects},
                    'fixtures': {'living_room_table': ['living_room_table']},
                    'regions': {REGION: {'target': 'basket_1'}}}
        self.env = SimpleNamespace(objects_dict=objects, parsed_problem=problems,
            fixtures_dict={},
            workspace_name='living_room_table', obj_body_id={name: model.body_name2id(name) for name in objects},
            object_sites_dict={REGION: SimpleNamespace(parent_name='basket_1')}, _eval_predicate=self.predicate,
            _check_grasp=lambda *_: False, check_contact=lambda _, names: self.fault == 'release' and names[0] == 'alphabet_soup_1_geom')
        gripper = SimpleNamespace(root_body='hand', contact_geoms=['left_pad', 'right_pad', 'palm'],
                                  important_geoms={'left_fingerpad': ['left_pad'], 'right_fingerpad': ['right_pad']})
        self.robots = [SimpleNamespace(gripper=gripper)]
        self.language_instruction = instruction
        self.obj_of_interest = [p[1] for p in predicates] + ['basket_1']
        self.update_data()

    def seed(self, index):
        assert index == 49

    def close(self):
        self.closed = True
        if self.fault == 'close':
            raise RuntimeError('close failed')

    def update_data(self):
        data = self.sim.data
        data.qpos = self.state[1:66]
        data.geom_xpos[:4] = [[-1.04, 0, .3], [-.96, 0, .3], [-1, 0, .25], [0, 0, 0]]
        data.geom_xpos[4:] = self.state[10:66].reshape(8, 7)[:, :3]
        data.site_xpos[0] = data.geom_xpos[-1] + [0, 0, .075]
        bad_contact = self.fault == 'contact' and self.predicate(['in', 'alphabet_soup_1', REGION])
        data.contact = [SimpleNamespace(geom1=4, geom2=11, dist=-.003)] if bad_contact else []
        data.ncon = len(data.contact)

    def predicate(self, p):
        if self.fault == 'mask' and p[1] == 'butter_1' and self.predicate(['in', 'alphabet_soup_1', REGION]):
            return True
        location = self.sim.data.geom_xpos[self.model.geom_name2id(p[1] + '_geom')]
        return bool(np.all(np.abs(location - self.sim.data.site_xpos[0]) <= self.model.site_size[0]))

    def check_success(self):
        return all(self.predicate(p) for p in self.env.parsed_problem['goal_state'])

    def step(self, _):
        self.state[0] += .05
        self.last_step += 1
        if self.fault == 'velocity' and self.predicate(['in', 'alphabet_soup_1', REGION]):
            self.state[75] = .02
        self.update_data()

    def observe(self):
        value = self.generation if self.fault == 'stale' else 0
        observation = {'agentview_image': np.full((8, 8, 3), value, np.uint8),
                       'robot0_eye_in_hand_image': np.full((8, 8, 3), value, np.uint8),
                       'robot0_eef_pos': np.zeros(3), 'robot0_eef_quat': np.array([1., 0, 0, 0]),
                       'robot0_gripper_qpos': np.zeros(2)}
        if self.fault == 'missing_wrist':
            del observation['robot0_eye_in_hand_image']
        return observation


@pytest.fixture
def fake(tmp_path, monkeypatch, request):
    core = Path(os.environ.get('LNA_CORE', Path(__file__).resolve().parents[2] / 'LIBERO-Remain-task033-r2'))
    activate_core(core)
    from benchmark.remaining_goals import build, libero_env
    from egrs.composition055 import native

    fault = getattr(request, 'param', None)
    state = np.zeros(123)
    state[10:66].reshape(8, 7)[:, :4] = [[.3 + n / 10, 0, .1, 1.] for n in range(7)] + [[0, 0, 0, 1.]]
    states = np.tile(state, (50, 1))
    states[:, 1] = np.arange(50) / 100
    initial = tmp_path / 'official.pruned_init'
    with ZipFile(initial, 'w') as archive:
        archive.writestr('archive/data.pkl', pickle.dumps(states, protocol=2))
    bddl = tmp_path / 'official.bddl'
    bddl.write_bytes(b'cpu fixture official bddl')
    env_identity = {'name': 'libero', 'fingerprint': 'cpu-fake', 'lock': {}}
    config = tmp_path / 'environment.json'
    config.write_text(json.dumps({'environment': env_identity}), encoding='utf-8')
    cfg = {'canonical_bddl': str(bddl), 'canonical_initial_states': str(initial),
           'environment_config': str(config), 'benchmark_root': str(core), 'protected_roots': []}
    monkeypatch.setattr(native, 'CANONICAL_BDDL_SHA256', sha256(bddl.read_bytes()).hexdigest())
    monkeypatch.setattr(native, 'CANONICAL_INITIAL_STATES_SHA256', sha256(initial.read_bytes()).hexdigest())
    monkeypatch.setattr(native, 'render_bddl', lambda *_: b'cpu fixture derived bddl')
    monkeypatch.setattr(native, '_verify_official_task', lambda: None)
    created = []
    official = [['in', 'alphabet_soup_1', REGION], ['in', 'tomato_sauce_1', REGION]]
    composed = [['in', 'alphabet_soup_1', REGION], ['in', 'butter_1', REGION]]

    def scene(path, **_):
        canonical = Path(path) == bddl
        active = Scene(state, official if canonical else composed,
                       'put both the alphabet soup and the tomato sauce in the basket' if canonical else ROW['instruction'],
                       fault, len(created))
        created.append(active)
        return active

    def restore(active, value):
        active.state = value.copy()
        active.update_data()
        return active.observe()

    monkeypatch.setattr(libero_env, '_new_scene', scene)
    monkeypatch.setattr(libero_env, 'reset_scene', lambda _: None)
    monkeypatch.setattr(libero_env, 'environment_identity', lambda _: env_identity)
    for module in (build, libero_env):
        monkeypatch.setattr(module, 'restore_raw_state', restore)
        monkeypatch.setattr(module, 'fresh_observation', lambda active: active.observe())
    return native, cfg, created, tmp_path / 'new'


def test_source_build_round_trip_preserves_fixed_population_and_non_a_state(fake):
    native, cfg, created, output = fake
    ledger = []
    result = native.build_source(cfg, ROW, output, ledger.append)
    assert result['status'] == 'ready', result
    verified = native.inspect_source(result['source_manifest'], ROW, cfg)
    assert verified['episode']['initial_mask'] == [True, False]
    assert verified['initial_state_index'] == 49
    assert len(created) == 4 and all(scene.closed for scene in created)
    assert ledger[-1]['completed_control_steps'] == 80 + 80 + 3 * 150
    assert len(list(output.rglob('*.npy'))) == 1
    state_file = next(output.rglob('*.npy'))
    edited = np.load(state_file, allow_pickle=False)
    assert edited[1] == .49 and edited[10] < .1 and edited[24] == .5
    state_file.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash'):
        native.inspect_source(result['source_manifest'], ROW, cfg)


@pytest.mark.parametrize('fake', ['mask', 'velocity', 'contact', 'release', 'stale', 'missing_wrist', 'close'], indirect=True)
def test_failed_native_source_is_not_published(fake):
    native, cfg, created, output = fake
    result = native.build_source(cfg, ROW, output, lambda _: None)
    assert result['status'] == 'failed' and result['error']
    assert 'source_manifest' not in result
    assert created and all(scene.closed for scene in created)
    assert not list(output.rglob('source.json'))
    assert not list(output.rglob('*.npy'))


def test_checkpoint_failure_aborts_the_core_validation_without_trying_another_candidate(fake):
    native, cfg, created, output = fake

    def checkpoint(event):
        if event['phase'] == 'construction_audit' and event['attempted_control_steps'] == 167:
            raise OSError('fake durable storage failure')

    with pytest.raises(OSError, match='durable storage'):
        native.build_source(cfg, ROW, output, checkpoint)
    assert len(created) == 2 and all(scene.closed for scene in created)
    assert created[1].last_step == 166
    assert not list(output.rglob('source.json'))
