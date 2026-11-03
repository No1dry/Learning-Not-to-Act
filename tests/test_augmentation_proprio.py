"""Official sensor names on tiny synthetic HDFs; no real trajectories or simulator."""
import copy

import h5py
import numpy as np
import pytest

from test_augmentation_data import fixture


@pytest.mark.parametrize('fields', [
    ['obs/ee_pos', 'obs/ee_ori', 'obs/gripper_states'],
    ['obs/ee_states', 'obs/gripper_states'],
])
def test_official_proprio_layout_exports_and_reads_current_ordered_sensors(tmp_path, monkeypatch, fields):
    data, manifest, inventory = fixture(tmp_path, monkeypatch)
    # Distinct coordinates and timesteps catch reordered fields and future reads.
    sensors = np.arange(1, 9, dtype=np.float32)[None, :] + 10 * np.arange(12)[:, None]
    with h5py.File(tmp_path / 'tiny.hdf5', 'r+') as hdf:
        for source in manifest['sources']:
            group = hdf[source['episode']]
            group.move('front', 'obs/agentview_rgb')
            group.move('wrist', 'obs/eye_in_hand_rgb')
            group['obs/ee_pos'] = sensors[:, :3]
            group['obs/ee_ori'] = sensors[:, 3:6]
            group['obs/ee_states'] = sensors[:, :6]
            group['obs/gripper_states'] = sensors[:, 6:]
            group['states'] = np.full((12, 8), 999., dtype=np.float32)
            group['obs/object_pos'] = np.full((12, 8), 999., dtype=np.float32)
    digest = data.file_sha256(tmp_path / 'tiny.hdf5')
    for source in manifest['sources']:
        source['file_sha256'] = digest
        source['mapping']['images'] = ['obs/agentview_rgb', 'obs/eye_in_hand_rgb']
        source['mapping']['proprio'] = copy.deepcopy(fields)
    output = tmp_path / 'export'
    report = data.export_dataset(manifest, inventory, output)
    dataset = data.AugmentationDataset(output, split='train', views=['RAW'])
    item = dataset[1]
    assert set(item) == {'images', 'proprio', 'instruction', 'actions', 'action_mask'}
    assert item['proprio'].tolist() == [11, 12, 13, 14, 15, 16, 17, 18]
    assert item['proprio'].shape == (8,)
    assert item['actions'][:, 0].tolist() == [2, 3, 4, 5, 6, 7, 8, 9]
    assert item['actions'][:, 6].tolist() == [1] * 8
    assert item['instruction'] == 'full instruction'
    assert item['action_mask'].tolist() == [True] * 8
    assert len(item['images']) == 2
    assert report['base_sources'] == {'train': 160, 'dev': 40}
    assert dataset[11]['action_mask'].tolist() == [True] + [False] * 7


@pytest.mark.parametrize('field', [
    'states', 'robot_states', 'obs/robot_states', 'obs/object_pos',
    'obs/object_states', 'obs/predicate', 'obs/contact', 'obs/reward',
    'obs/success', 'obs/future', 'obs/future/ee_states',
    'obs/other/ee_states', 'obs/gripper_states_extra',
])
def test_hidden_fields_cannot_be_declared_as_proprio(tmp_path, monkeypatch, field):
    data, manifest, _ = fixture(tmp_path, monkeypatch)
    mapping = manifest['sources'][0]['mapping']
    mapping['proprio'] = [field]
    with pytest.raises(ValueError, match='whitelist|forbidden'):
        data.validate_mapping(mapping)


@pytest.mark.parametrize('role', ['images', 'action'])
def test_sensor_state_exception_is_limited_to_proprio_role(tmp_path, monkeypatch, role):
    data, manifest, _ = fixture(tmp_path, monkeypatch)
    mapping = manifest['sources'][0]['mapping']
    if role == 'images':
        mapping[role][0] = 'obs/gripper_states'
    else:
        mapping[role] = 'obs/ee_states'
    with pytest.raises(ValueError, match='whitelist|forbidden'):
        data.validate_mapping(mapping)
