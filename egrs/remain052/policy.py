"""Explicit sparse-two-level rule inside private, pinned dependency namespaces.

Only the RGB bound changes: <=2 channel levels and <=floor(H*W/10000)
changed pixels (minimum one). Existing447 sources use their unchanged051 reader.
No input images, native bridge, physics checks or model scores are modified.
"""
import ast
from copy import deepcopy
import inspect
import textwrap

from egrs.remain049 import sources as old

PROFILE = 'named-uint8-rgb-sparse-two-level-task052-v1'
LIMITS = {'rgb_max_abs_error': 2, 'rgb_max_changed_fraction': .0001}
LIMITATION = (
    'Explicit user-approved Task052 sparse uint8 RGB admission: channel error <=2, '
    'changed pixels per named camera <=max(1,floor(H*W*0.0001)); 6 at256x256. '
    'Requires unchanged non-stepping simulator state; initial non-RGB is dtype/byte exact. '
    'All original physical, semantic and dynamic non-RGB checks remain. Original RGB '
    'arrays and hashes are retained, not filtered or quantized. This is a declared '
    'technical tolerance, not calibrated renderer error or policy-invariance evidence.'
)


def identity():
    return {'profile': PROFILE, 'limits': dict(LIMITS), 'implementation_sha256': old.sha(__file__),
            'pixel_cap': 'max(1,floor(H*W/10000))', 'policy_images_modified': False,
            'physical_limits_modified': False, 'action_score_modified': False,
            'limitation': LIMITATION}


def _replace(function, namespace, change):
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    change(tree)
    local = {}
    exec(compile(ast.fix_missing_locations(tree), function.__code__.co_filename, 'exec'), namespace, local)
    return local[function.__name__]


def _bounds(tree):
    matches = [n for n in ast.walk(tree) if isinstance(n, ast.Tuple) and len(n.elts) == 2
               and all(isinstance(v, ast.Constant) for v in n.elts)
               and [v.value for v in n.elts] == [1, .0001]]
    if len(matches) != 1:
        raise ValueError('Pinned052 RGB configuration seam differs')
    matches[0].elts[0].value = 2
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node.value = node.value.replace('one-level', 'sparse-two-level').replace('(1,0.0001)', '(2,0.0001)')


def configure_validation(module):
    """Original algorithms, explicit new rule/limits; canonical globals untouched."""
    rule = deepcopy(module.RGB_QUANTIZATION_RULE)
    rule.update(rule_id=PROFILE, max_abs_channel_error=2,
                basis='Task052 user-approved sparse numerical admission; not a calibrated error bound')
    module.RGB_QUANTIZATION_AUDIT = dict(LIMITS)
    module.RGB_QUANTIZATION_RULE = rule
    module.RGB_QUANTIZATION_LIMITATION = LIMITATION
    module._rgb_bounds = _replace(module._rgb_bounds, vars(module), _bounds)
    original = module.validate_candidate
    def validate(*args, **kwargs):
        result = original(*args, **kwargs)
        result['task052_admission'] = identity()
        return result
    module.validate_candidate = validate


def configure_package_reader(module):
    """Extend only the recorded max channel-error guard, never physical checks."""
    def change(tree):
        matches = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant)
                    and node.left.value == 0 and len(node.comparators) == 2
                    and isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == 'error'
                    and isinstance(node.comparators[1], ast.Constant) and node.comparators[1].value == 1
                    and all(isinstance(op, ast.LtE) for op in node.ops)):
                matches.append(node.comparators[1])
        if len(matches) != 1:
            raise ValueError('Pinned052 recorded RGB seam differs')
        matches[0].value = 2
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                node.value = node.value.replace('one-level', 'sparse-two-level')
    module._passing_observation_comparison = _replace(module._passing_observation_comparison, vars(module), change)
