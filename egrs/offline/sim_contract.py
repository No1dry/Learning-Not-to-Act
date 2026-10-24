"""Annotation-only JSON contracts. No native runtime imports or model inputs."""
from copy import deepcopy
import json
import math
from pathlib import Path
import re
from typing import Literal, TypedDict

from egrs.contracts import keys, integer, identifier, validate_registry
from .sim_alignment import RULES, ORIENTATIONS, choose_alignment

FRAME_FORMAT = 'egrs.sim.frame.v1'
MAP_FORMAT = 'egrs.sim.goal-map.v1'
COMPONENTS = {'target','destination','active_part','reference','hand'}
SUPPORTS = {'entity','role','relation','interaction','release'}


class VisibleEvidence(TypedDict):
    camera: Literal['agentview','wrist']
    bbox: list[float]
    components: list[str]
    supports: list[str]


class GoalFact(TypedDict):
    goal_ref: str
    kind: Literal['transport','mechanism']
    entity_ref: str | None
    native_truth: bool | None
    grasp: Literal['dual_pad','released','unknown']
    evidence: list[VisibleEvidence]


class FrameFacts(TypedDict):
    format: str
    source_id: str
    frame: int
    alignment: dict
    goals: list[GoalFact]


def load_goal_map():
    value = json.loads((Path(__file__).parent/'assets/sim_goal_map.json').read_text(encoding='utf-8'))
    if value['format'] != MAP_FORMAT:
        raise ValueError('unsupported goal mapping format')
    return value


def mapping_for(registry):
    """Resolve exact instruction/ref/kind/target/destination; no fuzzy fallback."""
    validate_registry(registry)
    for item in load_goal_map()['instructions']:
        if item['instruction'] == registry['instruction']:
            expected = [{k:g[k] for k in ('goal_ref','kind','target','destination')} for g in item['goals']]
            actual = [{k:g[k] for k in ('goal_ref','kind','target','destination')} for g in registry['goals']]
            if actual != expected:
                raise ValueError('registry disagrees with annotation goal map')
            return deepcopy(item['goals'])
    raise ValueError('registry instruction absent from annotation goal map')


def entity_aliases(mapped_goals):
    """Stable annotation-side native-target -> legal entity alias table.

    Compute once per source using the complete mapping, never visible subsets.
    The mapping itself belongs only in audit; labels contain alias values only.
    """
    return {name:f'entity{i}' for i,name in enumerate(sorted({g['atom'][1] for g in mapped_goals}))}


def validate_native_mapping(mapped_goals, goal_atoms, available_names):
    """Check actual parsed BDDL atoms and resolved native object/region names.

    Only operator case is canonicalized. Open top drawer is the sole declared
    annotation-only atom; its name must still resolve in the installed scene.
    Caller separately verifies saved-vs-installed BDDL bytes/hash.
    """
    def canonical(atom):
        if not isinstance(atom,(list,tuple)) or not atom or any(not isinstance(x,str) for x in atom):
            raise ValueError('invalid native BDDL atom')
        return (atom[0].lower(),*atom[1:])
    expected = {canonical(g['atom']) for g in mapped_goals if not g['annotation_only']}
    if {canonical(a) for a in goal_atoms} != expected:
        raise ValueError('native BDDL goals disagree with annotation map')
    if any(not set(g['atom'][1:]) <= set(available_names) for g in mapped_goals):
        raise ValueError('native BDDL mapping names unavailable')


def validate_frame_facts(value):
    """Validate JSON-safe source/frame facts; native names/state arrays forbidden.

    Native truth and component/support availability remain in this operational
    sidecar, never in selector payloads. entityN is a source-stable sensor alias.
    Worker retains alias->native bindings and physical diagnostics in audit only.
    """
    json.dumps(value, allow_nan=False)
    keys(value, {'format','source_id','frame','alignment','goals'}, 'frame facts')
    if value['format'] != FRAME_FORMAT or not isinstance(value['source_id'],str) or not value['source_id']:
        raise ValueError('invalid frame facts identity')
    integer(value['frame'],'physical frame',minimum=0)
    a=value['alignment']
    if not isinstance(a,dict) or not {'format','accepted','rule','basis','orientation','boundary_policy','comparisons','threshold'} <= set(a):
        raise ValueError('alignment record incomplete')
    if set(a) - {'format','accepted','rule','basis','orientation','boundary_policy','comparisons','threshold','reason','equivalence'}:
        raise ValueError('unexpected alignment fields; native diagnostics belong in audit')
    if a['format'] not in {'egrs.sim.alignment.v1','egrs.sim.alignment.v2'}:
        raise ValueError('unsupported alignment format')
    if (a['format']=='egrs.sim.alignment.v2') != ('equivalence' in a and a['equivalence'] is not None):
        raise ValueError('alignment version/equivalence mismatch')
    if a['format']=='egrs.sim.alignment.v1' and 'equivalence' in a:
        raise ValueError('v1 alignment cannot carry equivalence')
    if type(a['accepted']) is not bool or a['orientation'] not in ORIENTATIONS or a['boundary_policy'] != 'gap':
        raise ValueError('invalid alignment record')
    if a['accepted'] and (a['rule'] not in RULES or not a['basis']):
        raise ValueError('accepted alignment needs rule and basis')
    measured=choose_alignment(a['comparisons'],basis=a['basis'],orientation=a['orientation'],threshold=a['threshold'],
                              equivalence=a.get('equivalence'))
    if a['accepted'] and (not measured['accepted'] or measured['rule'] != a['rule']):
        raise ValueError('accepted alignment lacks unique passing comparison evidence')
    if a['accepted'] and a.get('equivalence') is not None and value['frame'] not in {x['frame'] for x in a['equivalence']['checks']}:
        raise ValueError('frame is not authorized by checked physical equivalence')
    if not isinstance(value['goals'],list) or not value['goals']:
        raise ValueError('frame goals required')
    refs=set()
    for g in value['goals']:
        keys(g, {'goal_ref','kind','entity_ref','native_truth','grasp','evidence'}, 'goal fact')
        identifier(g['goal_ref'],'goal_ref')
        if g['goal_ref'] in refs:
            raise ValueError('duplicate fact goal_ref')
        refs.add(g['goal_ref'])
        if g['kind'] not in {'transport','mechanism'}:
            raise ValueError('invalid goal kind')
        if g['entity_ref'] is not None and (not isinstance(g['entity_ref'],str) or not re.fullmatch(r'entity[0-9]+',g['entity_ref'])):
            raise ValueError('source-stable entityN alias required; native names forbidden')
        if g['native_truth'] is not None and type(g['native_truth']) is not bool:
            raise ValueError('native_truth must be bool or null')
        if g['grasp'] not in {'dual_pad','released','unknown'}:
            raise ValueError('unsupported grasp/release certificate')
        if not isinstance(g['evidence'],list) or len(g['evidence']) > 12:
            raise ValueError('invalid fact evidence count')
        for e in g['evidence']:
            keys(e, {'camera','bbox','components','supports'}, 'visible evidence')
            if e['camera'] not in {'agentview','wrist'}:
                raise ValueError('unknown evidence camera')
            b=e['bbox']
            if not isinstance(b,list) or len(b)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in b) or b[0]>=b[2] or b[1]>=b[3]:
                raise ValueError('invalid normalized visible bbox')
            for field,allowed in [('components',COMPONENTS),('supports',SUPPORTS)]:
                v=e[field]
                if not isinstance(v,list) or not v or any(not isinstance(x,str) or x not in allowed for x in v) or len(set(v))!=len(v):
                    raise ValueError('invalid evidence '+field)
    return deepcopy(value)
