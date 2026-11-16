"""Pure contracts: no torch, HDF payloads, renderer, or model construction."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re

INDEX_IDENTITY = '8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe'
MAX_KEYS = 143960
GROUP = 'language_status_transfer'
SIDECAR_FORMAT = 'task043-status-language-v1'
ADAPTER_FORMAT = 'task043-hint-adapter-v1'
EXTENDED_ADAPTER_FORMAT = 'task043-hint-adapter-v2'
CONFIG_FORMAT = 'task043-hint-training-v1'
EXTENDED_CONFIG_FORMAT = 'task043-hint-training-v2'
TEMPLATE_VERSION = 'current-native-goal-relations-v1'
SENSOR_FIELDS = frozenset(('images', 'instruction', 'proprio'))
RELATIONS = {
    'basket': ('alphabet soup in basket', 'tomato sauce in basket'),
    'basket_cheese_butter': ('cream cheese box in basket', 'butter in basket'),
    'stove': ('stove switched on', 'moka pot on stove'),
    'bowl_drawer_close': ('black bowl in bottom drawer', 'bottom drawer closed'),
    'dual_mugs': ('white mug on left plate', 'yellow-and-white mug on right plate'),
    'mug_pudding': ('white mug on plate', 'chocolate pudding to right of plate'),
    'basket_soup_cheese': ('alphabet soup in basket', 'cream cheese box in basket'),
    'mug_microwave_close': ('yellow-and-white mug in microwave', 'microwave door closed'),
}
RECIPE = {
    'name': GROUP, 'updates': 1000, 'seed': 7, 'save_every': 250,
    'learning_rate': 2e-5, 'warmup_updates': 50, 'precision': 'bf16',
    'gradient_checkpointing': True, 'microbatch': 1, 'photometric_probability': 0.0,
    'pool_samples': {'ten': 12, 'fresh': 4, 'raw': 4},
    'pool_weights': {'ten': .5, 'fresh': .25, 'raw': .25},
    'auxiliary_max': 4, 'auxiliary_weight': .25,
    'transfer_weight_max': .1, 'transfer_zero_through': 100, 'transfer_full_at': 200,
    'dev_ten_limit': 256, 'dev_reference_per_pool': 128,
    'reference_budget': 9024, 'model_forward_budget': 27072,
    'checkpoint_selection': 'fixed_terminal_1000',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k != 'identity'},
        sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for k,v in pairs:
        require(k not in result, 'Duplicate JSON field: '+k)
        result[k] = v
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def lines(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(row, object_pairs_hook=unique_object) for row in stream if row.strip()]


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same(actual[k],v) for k,v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a,b) for a,b in zip(actual,expected))
    return actual == expected


def status_text(task, values):
    require(task in RELATIONS or task == 'two_pots', 'Unknown task semantic template')
    if not isinstance(values, list) or len(values) != 2 or not all(type(v) is bool for v in values):
        return None
    if task == 'two_pots':
        return f'{sum(values)} of 2 moka pots are currently on the stove.'
    return ' '.join(f'The goal relation "{relation}" is currently '+
        ('satisfied.' if v else 'not satisfied.') for relation,v in zip(RELATIONS[task],values))


def prompt(instruction, hint=None):
    require(isinstance(instruction, str) and bool(instruction.strip()), 'Full original instruction required')
    prefix = f'In: What action should the robot take to {instruction.lower()}?\n'
    if hint is not None:
        require(isinstance(hint,str) and bool(hint.strip()), 'Nonempty status text required')
        prefix += 'Current task-goal facts: '+hint.lower()+'\n'
    return prefix+'Out:'


def sensors(item):
    # Training metadata is never forwarded even when it lives next to sensors.
    require(SENSOR_FIELDS <= item.keys(), 'Missing current policy sensor input')
    return {k:item[k] for k in SENSOR_FIELDS}


def training_recipe(target_updates=1000):
    require(type(target_updates) is int and target_updates >= 1000 and target_updates % 1000 == 0,
            'Target updates must be a positive multiple of1000')
    result = json.loads(json.dumps(RECIPE))
    result.update(updates=target_updates, reference_budget=9024*(target_updates//1000),
                  model_forward_budget=27072*(target_updates//1000),
                  checkpoint_selection='fixed_terminal_1000' if target_updates == 1000 else 'fixed_thousand_step_milestones')
    return result


def transfer_weight(update, *, target_updates=1000):
    training_recipe(target_updates)
    require(type(update) is int and 1 <= update <= target_updates, 'Update outside requested training horizon')
    return .1 * min(1., max(0., (update - 100) / 100))


def input_path(value, directory):
    require(isinstance(value,str) and bool(value.strip()), 'Explicit input path required')
    expanded = os.path.expandvars(value)
    require(not any(c in expanded for c in '<>$') and not re.search(r'%[^%]+%', expanded),
            'Unresolved path placeholder')
    p = Path(expanded).expanduser()
    return str((directory / p).resolve() if not p.is_absolute() else p.resolve())


def load_config(path):
    cfg = read_json(path)
    require(set(cfg) == {'format','arm','index_dir','sidecar_dir','benchmark_root','runtime','training_recipe'}
            and cfg['format'] in (CONFIG_FORMAT, EXTENDED_CONFIG_FORMAT) and cfg['arm'] in ('h0','h1'), 'Exact043 configuration required')
    target = cfg['training_recipe'].get('updates')
    expected_format = CONFIG_FORMAT if target == 1000 else EXTENDED_CONFIG_FORMAT
    require(cfg['format'] == expected_format and same(cfg['training_recipe'], training_recipe(target)),
            'Fixed043 recipe required; only the declared training horizon/budgets may change')
    for key in ('index_dir','sidecar_dir','benchmark_root','runtime'):
        cfg[key] = input_path(cfg[key], Path(path).resolve().parent)
    return cfg


def forbid_overlap(output, inputs):
    out = Path(output).resolve()
    for value in inputs:
        root = Path(value).resolve()
        require(out != root and root not in out.parents and out not in root.parents,
                'Output overlaps protected input: '+str(root))
    return out
