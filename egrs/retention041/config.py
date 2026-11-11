"""Strict, explicit inputs for the fixed Task041 continuation experiment."""
import json
import os
from pathlib import Path
import re

from egrs.task_control.training import PRESET

FORMAT = 'task041-old10-retention-training-v1'
_FIELDS = {'format', 'experiment_arm', 'training_recipe', 'index_dir',
           'initial_adapter', 'teacher_adapter', 'benchmark_root', 'runtime'}
_VARIABLE = re.compile(r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)|%([^%]+)%')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate configuration field: ' + key + ' (duplicate key)')
        result[key] = value
    return result


def _same_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same_value(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same_value(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _input_path(value, name, directory):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('041 ' + name + ' requires an explicit nonempty path')
    def replace(match):
        variable = next(part for part in match.groups() if part is not None)
        if variable not in os.environ:
            raise ValueError('041 ' + name + ' has unresolved environment variable: ' + variable)
        return os.environ[variable]
    # Nested references are explicit too; cycles or malformed placeholders fail below.
    for _ in range(16):
        expanded = _VARIABLE.sub(replace, value)
        if expanded == value:
            break
        value = expanded
    if not value.strip() or any(character in value for character in '<>$') or _VARIABLE.search(value):
        raise ValueError('041 ' + name + ' contains an unresolved variable or placeholder')
    path = Path(os.path.expanduser(value))
    if str(path).startswith('~'):
        raise ValueError('041 ' + name + ' contains an unresolved home directory')
    return str((directory / path).resolve() if not path.is_absolute() else path.resolve())


def load_config(path):
    """Read exactly the041 schema and resolve paths relative to its JSON file.

    This only validates configuration, without opening data, models or runtime.
    R0 has no teacher path; R1 requires one. Output/resume are CLI concerns.
    """
    directory = Path(path).resolve().parent
    with Path(path).open(encoding='utf-8') as stream:
        config = json.load(stream, object_pairs_hook=_unique_object)
    if not isinstance(config, dict) or set(config) != _FIELDS or config.get('format') != FORMAT:
        raise ValueError('041 requires the exact ' + FORMAT + ' fields')
    arm = config['experiment_arm']
    if arm not in ('r0', 'r1'):
        raise ValueError('041 experiment_arm must be r0 or r1; both use base C1')
    if not _same_value(config['training_recipe'], PRESET):
        raise ValueError('041 training_recipe must equal the complete fixed task038 1000-update preset')
    if arm == 'r0' and config['teacher_adapter'] is not None:
        raise ValueError('041 r0 teacher_adapter must be null')
    names = ['index_dir', 'initial_adapter', 'benchmark_root', 'runtime']
    if arm == 'r1':
        names.append('teacher_adapter')
    for name in names:
        config[name] = _input_path(config[name], name, directory)
    return config
