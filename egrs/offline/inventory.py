"""Inspect only the approved existing RGB datasets, never state/action/reward."""
import json
import sys
from pathlib import Path

from egrs.data import grouped_split
from .common import digest, seal, save, new_output

DATASET = 'yifengzhu-hf/LIBERO-datasets'
REVISION = '147fa5eb607bb696dd922c3518084a90954cd2f3'


def catalog():
    installed = Path(sys.prefix) / 'share/egrs/catalog.json'
    source = Path(__file__).resolve().parent / 'assets/catalog.json'
    # Package copy is shipped in wheels; repository catalog remains authoritative.
    if not source.exists():
        source = Path(__file__).resolve().parents[2] / 'data/catalog.json'
    value = json.loads((source if source.exists() else installed).read_text(encoding='utf-8'))
    if value['dataset'] != DATASET or value['revision'] != REVISION or len(value['files']) != 20:
        raise ValueError('approved catalog identity mismatch')
    return value


def instruction_id(instruction):
    return digest(instruction)


def plan():
    c = catalog()
    return {'format': 'egrs.offline.plan.v1', 'dataset': DATASET, 'revision': REVISION,
            'files': c['files'], 'episodes': [f'demo_{i}' for i in range(10)],
            'budget_only': c['budget_only'], 'actual_verified_sources': 0,
            'exclusion_attestation': dict.fromkeys(('six_composites_excluded', 'semantic_equivalents_excluded', 'eval_sources_excluded')),
            'stages': ['inventory', 'registry-candidates', 'registry-review-export', 'registry-review-import', 'prepare', 'candidates', 'review-export', 'review-import', 'build']}


def _decode(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value


def _instruction(data, relative, mapping):
    raw = data.attrs.get('problem_info')
    if raw is not None:
        try:
            instruction = json.loads(_decode(raw)).get('language_instruction')
        except (ValueError, TypeError, AttributeError, UnicodeError) as exc:
            raise ValueError('invalid problem_info instruction metadata') from exc
        if isinstance(instruction, str) and instruction.strip():
            return instruction, 'data.attrs.problem_info.language_instruction', None
        if instruction is not None:
            raise ValueError('invalid language_instruction')
    entry = mapping.get(relative)
    if (not isinstance(entry, dict) or not isinstance(entry.get('instruction'), str) or not entry['instruction'].strip()
            or not entry.get('reviewer') or not entry.get('basis')):
        raise ValueError('missing instruction: explicit human instruction mapping required')
    return entry['instruction'], 'explicit_human_mapping', entry


def inspect_episode(data, episode):
    import numpy as np
    obs = data[f'{episode}/obs']
    shapes = []
    for key in ('agentview_rgb', 'eye_in_hand_rgb'):
        images = obs[key]
        if len(images.shape) != 4 or images.shape[-1] != 3 or images.dtype != np.uint8 or not all(images.shape):
            raise ValueError('camera must be nonempty uint8 THWC RGB')
        shapes.append(images.shape)
    if shapes[0][0] != shapes[1][0]:
        raise ValueError('camera length mismatch; no shortened stream fallback')
    return shapes[0][0]


def inventory(root, *, instruction_map=None, aliases=None, output=None):
    import h5py
    root = Path(root).resolve()
    output = new_output(output) if output is not None else None
    aliases, instruction_map = aliases or {}, instruction_map or {}
    planned = []
    for entry in catalog()['files']:
        relative = entry['suite'] + '/' + entry['file']
        for i in range(10):
            sid = relative + f'#demo_{i}'
            alias = aliases.get(sid, {})
            groups = alias.get('group_ids', [])
            if not isinstance(groups, list) or any(not isinstance(x, str) or not x for x in groups):
                raise ValueError('aliases need nonempty string group_ids')
            planned.append({'sample_id': sid, 'source_id': sid, 'file': relative, 'episode': f'demo_{i}',
                            'group_ids': groups, 'task_group': relative, 'ancestry_known': alias.get('ancestry_known') is True})
    splits = grouped_split(planned, seed=0)
    result = {'format': 'egrs.inventory.v1', 'dataset': DATASET, 'revision': REVISION, 'root': str(root),
              'seed': 0, 'planned_sources': planned, 'source_splits': splits, 'sources': [], 'gaps': []}
    for entry in planned:
        try:
            with h5py.File(root / entry['file'], 'r') as file:
                data = file['data']
                instruction, origin, mapping = _instruction(data, entry['file'], instruction_map)
                length = inspect_episode(data, entry['episode'])
                orientation = str(_decode(data.attrs.get('macros_image_convention', 'unknown')))
                result['sources'].append({**entry, 'instruction': instruction, 'instruction_id': instruction_id(instruction),
                    'instruction_origin': origin, 'instruction_mapping': mapping, 'T': length,
                    'orientation': orientation, 'split': splits[entry['source_id']]})
        except (OSError, KeyError, ValueError, TypeError) as exc:
            result['gaps'].append({'source_id': entry['source_id'], 'reason': f'{type(exc).__name__}: {exc}'})
        if output:
            save(output / 'inventory.partial.json', result)
    result = seal(result)
    if output:
        save(output / 'inventory.json', result)
    return result
