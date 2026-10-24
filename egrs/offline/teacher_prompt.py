"""Versioned teacher guidance; shared student messages and contracts are unchanged."""
import json

from egrs.selector.prompt import build_messages, PREDICTION_SCHEMA, REGISTRY_SCHEMA, REGISTRY_PROMPT_SHA256
from .common import digest

PROMPT_VERSION = 'egrs.offline-teacher-guidance.v2'
PREDICTION_EXAMPLES = [
    {'query_id': 1, 'goals': [{'goal_ref': 'g0', 'entity_ref': None, 'association': 'UNKNOWN',
        'role': 'UNKNOWN', 'relation': 'UNKNOWN', 'release': 'UNKNOWN', 'interaction': 'UNKNOWN', 'evidence': []}]},
    {'query_id': 1, 'goals': [{'goal_ref': 'g0', 'entity_ref': 'entity0', 'association': 'MATCHED',
        'role': 'TARGET', 'relation': 'UNSAT', 'release': 'RELEASED', 'interaction': 'NOT_HELD',
        'evidence': [{'goal_ref': 'g0', 'entity_ref': 'entity0', 'query_id': 1, 'snapshot_id': 'q1',
            'camera': 'agentview', 'bbox': [0.1, 0.1, 0.7, 0.7], 'coordinate_system': 'normalized_xyxy',
            'supports': ['entity', 'role', 'relation', 'release', 'interaction']}]}]}
]

PREDICTION_GUIDANCE = '''Teacher contract guidance v2:
One JSON object, no prose. Every registry goal_ref exactly once; no extra destination goal. Use current query_id.
entity_ref: sensor-assigned ID matching [A-Za-z][A-Za-z0-9_-]{0,63}, not a spaced object name or simulator/GT ID. Reuse IDs only with visible identity support. UNKNOWN association requires null; MATCHED needs an ID and regional evidence supporting entity.
role: TARGET/COMPLETED/DISTRACTOR/UNKNOWN only, never DESTINATION. transport release: RELEASED/NOT_RELEASED/UNKNOWN only. mechanism release: NOT_APPLICABLE only; this is not completion evidence.
Unknown entity/association requires UNKNOWN role/relation/interaction and transport release. Keep unsupported fields UNKNOWN. Never invent entities, bbox or completion. Each known field needs a visible bbox bound to its own goal/entity, legal query/snapshot/camera and corresponding supports: entity/role/relation/release/interaction. Use supplied views; history/commands alone are not current truth.
Examples assume one transport goal g0 and query1. They are NOT current observations: use the actual fixed goals, and never copy example IDs/boxes/states without visible support. All-UNKNOWN is uncertainty, not useful supervision ready.
Unknown example: ''' + json.dumps(PREDICTION_EXAMPLES[0], separators=(',', ':')) + '''
Evidence example, ONLY if the region visibly supports all listed claims: ''' + json.dumps(PREDICTION_EXAMPLES[1], separators=(',', ':'))

PROMPT_SHA256 = digest([REGISTRY_SCHEMA, REGISTRY_PROMPT_SHA256, PREDICTION_SCHEMA, PROMPT_VERSION, PREDICTION_GUIDANCE])


def build_teacher_messages(payload=None, *, instruction=None):
    messages = build_messages(payload, instruction=instruction)
    if instruction is None:
        messages[0]['content'] += '\n\n' + PREDICTION_GUIDANCE
    return messages
