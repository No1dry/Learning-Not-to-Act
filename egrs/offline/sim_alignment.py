"""Pure alignment decisions and original-RGB-coordinate visible-pixel boxes.

Residuals are measured by the isolated worker against a fixed set of existing
frames. Neither task success nor frame clamping is an alignment criterion.
"""
from copy import deepcopy
import math
import json

import numpy as np

RULES = {'same_state', 'next_state', 'replay_action'}
ORIENTATIONS = {'identity', 'flip_vertical'}
EQUIVALENCE_MAX_ATOL = 1e-6


def choose_alignment(comparisons, *, basis, orientation, threshold, equivalence=None):
    """Accept one physical correspondence with explicit equivalent operations.

    Each comparison is {rule, residuals: [...], samples: [{frame, camera}, ...]}.
    The worker stores detailed measurement/runtime metadata in separate audit.
    Orientation describes the render/mask -> stored RGB transform, NOT a name
    such as opengl. The worker must establish it using actual RGB comparisons.
    Optional v2 equivalence coalesces next_state/replay_action only when their
    state and two-camera evidence is checked for each explicitly authorized frame.
    All original comparisons remain present; names alone never prove equivalence.
    """
    json.dumps(comparisons, allow_nan=False)
    if orientation not in ORIENTATIONS or not math.isfinite(threshold) or threshold < 0:
        raise ValueError('invalid alignment orientation or threshold')
    if not isinstance(basis, list) or any(not isinstance(x,str) or not x for x in basis):
        raise ValueError('alignment basis must be a list of nonempty strings')
    passing, seen, fixed_samples = [], set(), None
    for item in comparisons:
        if not isinstance(item,dict) or set(item) != {'rule','residuals','samples'}:
            raise ValueError('alignment comparisons require rule/residuals/samples only')
        rule = item['rule']
        if rule not in RULES or rule in seen:
            raise ValueError('unknown or duplicate alignment rule')
        seen.add(rule)
        residuals = item['residuals']
        samples = item.get('samples')
        if (not isinstance(samples,list) or len(samples)!=len(residuals) or not samples
                or any(not isinstance(x,dict) or set(x)!={'frame','camera'}
                       or type(x['frame']) is not int or x['frame']<0
                       or x['camera'] not in {'agentview','wrist'} for x in samples)):
            raise ValueError('fixed alignment probe frame/camera records required')
        identities=[(x['frame'],x['camera']) for x in samples]
        if len(set(identities)) != len(identities) or (fixed_samples is not None and identities != fixed_samples):
            raise ValueError('all alignment candidates must compare the same fixed probes')
        fixed_samples=identities
        if not isinstance(residuals, list) or any(type(x) not in (int,float) or not math.isfinite(x) or x < 0 for x in residuals):
            raise ValueError('invalid alignment residuals')
        if residuals and max(residuals) <= threshold:
            passing.append(rule)
    accepted = len(passing) == 1 and bool(basis)
    representative = passing[0] if accepted else None
    if equivalence is not None:
        valid = _validate_equivalence(equivalence, comparisons, threshold)
        accepted = valid and set(passing)=={'next_state','replay_action'} and bool(basis)
        representative = equivalence['representative'] if accepted else None
    result = {'format':'egrs.sim.alignment.v2' if equivalence is not None else 'egrs.sim.alignment.v1',
            'accepted': accepted, 'rule': representative,
            'basis': list(basis), 'orientation': orientation, 'boundary_policy': 'gap',
            'comparisons': deepcopy(comparisons), 'threshold': threshold,
            'reason': None if accepted else 'missing_basis_or_ambiguous_or_failed_comparison'}
    if equivalence is not None: result['equivalence']=deepcopy(equivalence)
    return result


def _validate_equivalence(value, comparisons, threshold):
    """Validate bounded physical/correspondence certificates; no full state data."""
    json.dumps(value,allow_nan=False)
    if (not isinstance(value,dict) or set(value)!={'format','rules','representative','state_atol','checks'}
        or value['format']!='egrs.sim.equivalence.v1'
        or value['rules']!=['next_state','replay_action'] or value['representative']!='next_state'):
        raise ValueError('invalid physical equivalence contract')
    atol=value['state_atol']
    if type(atol) not in (int,float) or not math.isfinite(atol) or not 0<=atol<=EQUIVALENCE_MAX_ATOL:
        raise ValueError('invalid equivalence state tolerance')
    checks=value['checks']
    if not isinstance(checks,list) or not 1<=len(checks)<=18:
        raise ValueError('equivalence requires 1..18 frame-bound checks')
    by_frame={}; passed=True
    for check in checks:
        fields={'frame','next_state_index','replay_state_index','action_index','state_max_abs_residual',
                'next_state_sha256','replay_state_sha256','rgb_residuals'}
        if not isinstance(check,dict) or set(check)!=fields:
            raise ValueError('invalid equivalence frame check')
        frame=check['frame']
        if type(frame) is not int or frame<0 or frame in by_frame:
            raise ValueError('invalid/duplicate equivalence frame')
        for key,expected in [('next_state_index',frame+1),('replay_state_index',frame),('action_index',frame)]:
            if type(check[key]) is not int or check[key]!=expected:
                raise ValueError('equivalence physical operation binding mismatch')
        for key in ('next_state_sha256','replay_state_sha256'):
            digest=check[key]
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('equivalence requires state hashes')
        residual=check['state_max_abs_residual']
        if type(residual) not in (int,float) or not math.isfinite(residual) or residual<0:
            raise ValueError('invalid equivalence state residual')
        passed &= residual<=atol
        rgb=check['rgb_residuals']
        if not isinstance(rgb,dict) or set(rgb)!={'next_state','replay_action'}:
            raise ValueError('equivalence needs both operation RGB checks')
        for cameras in rgb.values():
            if not isinstance(cameras,dict) or set(cameras)!={'agentview','wrist'}:
                raise ValueError('equivalence needs both original cameras')
            for residual in cameras.values():
                if type(residual) not in (int,float) or not math.isfinite(residual) or residual<0:
                    raise ValueError('invalid equivalence RGB residual')
                passed &= residual<=threshold
        by_frame[frame]=check
    # The equivalence certificate must cover, and agree with, retained probes.
    required={'next_state','replay_action'}
    if not required<={item['rule'] for item in comparisons}: return False
    for item in comparisons:
        if item['rule'] not in required: continue
        for sample,residual in zip(item['samples'],item['residuals']):
            check=by_frame.get(sample['frame'])
            if check is None or check['rgb_residuals'][item['rule']][sample['camera']]!=residual:
                return False
    return bool(passed)


def frame_operation(alignment, frame, state_count, *, replay_corroborated=False):
    """Return explicit state/action indices or None for an unresolved boundary.

    Final replay is allowed only after worker corroboration against known next
    states. This flag is evidence-backed worker output, never a success signal.
    """
    if type(frame) is not int or type(state_count) is not int or not 0 <= frame < state_count:
        raise ValueError('invalid physical frame/state count')
    if not alignment.get('accepted'):
        return None
    if alignment.get('equivalence') is not None:
        measured=choose_alignment(alignment['comparisons'],basis=alignment['basis'],
            orientation=alignment['orientation'],threshold=alignment['threshold'],equivalence=alignment['equivalence'])
        if (not measured['accepted'] or measured['rule']!=alignment['rule']
                or frame not in {x['frame'] for x in alignment['equivalence']['checks']}):
            return None
    rule = alignment['rule']
    if rule == 'same_state':
        return {'state_index': frame, 'action_index': None}
    if rule == 'next_state':
        return {'state_index': frame+1, 'action_index': None} if frame+1 < state_count else None
    if rule == 'replay_action':
        if frame+1 == state_count and replay_corroborated is not True:
            return None
        return {'state_index': frame, 'action_index': frame}
    raise ValueError('unknown alignment rule')


def clip_bbox(box, *, width, height):
    """Clip pixel edge coordinates to the stored frame; discard empty boxes."""
    if type(width) is not int or type(height) is not int or min(width,height) <= 0:
        raise ValueError('positive image dimensions required')
    if len(box) != 4 or any(not math.isfinite(x) for x in box):
        raise ValueError('finite pixel bbox required')
    x1,y1,x2,y2 = box
    x1,x2 = max(0,min(width,x1)),max(0,min(width,x2))
    y1,y2 = max(0,min(height,y1)),max(0,min(height,y2))
    if x1 >= x2 or y1 >= y2:
        return None
    return [x1/width,y1/height,x2/width,y2/height]


def visible_bbox(mask, *, orientation):
    """Bound only visible mask pixels; never bound full projected geometry."""
    mask = np.asarray(mask)
    if mask.ndim != 2 or mask.dtype != np.bool_ or not mask.size:
        raise ValueError('visible mask must be a nonempty 2D bool array')
    if orientation not in ORIENTATIONS:
        raise ValueError('explicit verified mask orientation required')
    if orientation == 'flip_vertical':
        mask = mask[::-1]
    ys,xs = np.nonzero(mask)
    if not len(xs):
        return None
    return clip_bbox([int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1],
                     width=mask.shape[1],height=mask.shape[0])
