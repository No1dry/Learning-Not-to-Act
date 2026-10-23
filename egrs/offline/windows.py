"""Fixed chronological windows of stored unmodified RGBs."""
import copy
from pathlib import Path

from egrs.data import extract_existing_images
from .common import new_output, seal, save, verify


def window_frames(length):
    if type(length) is not int or length < 1:
        raise ValueError('positive common camera length required')
    windows = []
    for i in range(6):
        anchor = i * (length - 1) // 5
        frames = sorted({max(0, anchor - offset) for offset in (16, 8, 0)})
        if frames not in windows:
            windows.append(frames)
    return windows


def prepare(inventory, registries, output):
    from egrs.contracts import validate_registry
    from .inventory import inspect_episode
    import h5py
    verify(inventory, 'egrs.inventory.v1')
    if registries.get('format') != 'egrs.registries.confirmed.v1' or registries.get('inventory_id') != inventory['identity']:
        raise ValueError('confirmed registries must match inventory')
    verify(registries, 'egrs.registries.confirmed.v1')
    output = new_output(output)
    result = {'format': 'egrs.windows.v1', 'inventory_id': inventory['identity'],
              'source_splits': inventory['source_splits'], 'planned_sources': inventory['planned_sources'],
              'gaps': copy.deepcopy(inventory['gaps']), 'windows': []}
    for source in inventory['sources']:
        sid = source['source_id']
        try:
            confirmed = registries['registries'].get(source['instruction_id'], {})
            if confirmed.get('confirmed') is not True or not confirmed.get('reviewer'):
                raise ValueError('registry not explicitly human confirmed')
            registry = validate_registry(confirmed['registry'], source['instruction'])
            with h5py.File(Path(inventory['root']) / source['file'], 'r') as file:
                if inspect_episode(file['data'], source['episode']) != source['T']:
                    raise ValueError('camera length changed since inventory')
            framesets = window_frames(source['T'])
            from .common import digest
            images = extract_existing_images(Path(inventory['root']) / source['file'], output / 'images' / digest(sid)[:20],
                                             episode=source['episode'], frames=sorted({f for w in framesets for f in w}))
            images = {x['frame']: x['observation'] for x in images}
            for w, frames in enumerate(framesets):
                wid = f'w{w}'
                samples, sensors = [], []
                for q, frame in enumerate(frames, 1):
                    sensors.append({'query_id': q, 'snapshot_id': f'q{q}', 'observation': images[frame]})
                    samples.append({'sample_id': f'{sid}/{wid}/q{q}', 'source_id': sid, 'window_id': wid,
                        'payload': {'sensor': copy.deepcopy(sensors), 'context': {'query_id': q, 'instruction': source['instruction'],
                            'registry': registry, 'history': [], 'commands': []}}, 'answer': None, 'provenance': {},
                        'physical_truth': None, 'group_ids': source['group_ids'], 'task_group': source['task_group'],
                        'ancestry_known': source['ancestry_known'], 'history_provenance': {}})
                result['windows'].append({'source_id': sid, 'window_id': wid, 'split': source['split'],
                    'frames': frames, 'orientation': source['orientation'], 'cameras': ['agentview', 'wrist'], 'samples': samples})
        except (ValueError, KeyError, OSError) as exc:
            result['gaps'].append({'source_id': sid, 'reason': f'{type(exc).__name__}: {exc}'})
        save(output / 'windows.partial.json', result)
    save(output / 'windows.json', result)
    return seal(result)
