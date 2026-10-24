"""Auditable whole-output JSON decoding; never repair semantic fields."""
import json
import re

PARSE_PROTOCOL = 'egrs.teacher-wire.v2'
_FENCE = re.compile(r'```(json)?[ \t]*\r?\n(.*?)\r?\n```[ \t]*', re.DOTALL)
_FENCE_LINE = re.compile(r'^[ \t]*```', re.MULTILINE)


def empty_parse_audit():
    return {'protocol': PARSE_PROTOCOL, 'strategy': None,
            'stages': dict.fromkeys(('wrapper', 'json', 'schema'), 'not_run'),
            'errors': dict.fromkeys(('wrapper', 'json', 'schema')),
            'failure_stage': None, 'schema_category': None, 'error': None}


def schema_category(message):
    """Stable first-error buckets; the existing validator remains authoritative."""
    if message.startswith('release: invalid state'):
        return 'release_kind'
    if message.startswith('entity_ref: invalid identifier'):
        return 'entity_identifier'
    if 'complete fixed goal set' in message or 'missing/extra/duplicate goal reference' in message:
        return 'fixed_goal_set'
    if 'needs bound regional evidence' in message or 'entity association needs evidence' in message:
        return 'bound_evidence'
    if message.startswith('role: invalid state'):
        return 'role_enum'
    if message.startswith('MATCHED needs'):
        return 'entity_association'
    if message == 'invalid evidence supports':
        return 'evidence_supports'
    return 'other_schema'


def decode_json_output(raw, *, protocol=PARSE_PROTOCOL):
    """Syntax only: one bare JSON value or one exact complete outer JSON fence.

    No substring extraction, prose stripping, field repair, coercion or retries.
    Online and offline consumers apply the same authoritative schemas afterward.
    """
    result = dict(empty_parse_audit(), value=None)
    result['protocol'] = protocol
    stage = 'wrapper'
    try:
        if not isinstance(raw, str):
            raise ValueError('generated raw must be text')
        text = raw.strip()
        fenced = _FENCE.fullmatch(text)
        if fenced:
            text = fenced[2]
            if _FENCE_LINE.search(text):
                raise ValueError('multiple or nested code blocks are not a single outer wrapper')
            result['strategy'] = 'fenced_json' if fenced[1] else 'fenced_untyped'
        elif _FENCE_LINE.search(text):
            raise ValueError('expected exactly one complete outer json/untyped code block, without prose')
        else:
            result['strategy'] = 'bare_json'
        result['stages'][stage] = 'passed'
        stage = 'json'
        result['value'] = json.loads(text)
        result['stages'][stage] = 'passed'
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        result['stages'][stage] = 'failed'
        result['errors'][stage] = error
        result['failure_stage'] = stage
        result['error'] = error
    return result


def parse_teacher_output(raw, *, instruction=None, payload=None):
    """Return separate wrapper/JSON/schema results, keeping the input untouched."""
    result = decode_json_output(raw)
    parsed = result.pop('value')
    result['answer'] = None
    if result['failure_stage'] is not None:
        return result
    try:
        stage = 'schema'
        from egrs.contracts import validate_registry, validate_prediction
        if instruction is not None and payload is None:
            answer = validate_registry(parsed, instruction)
        elif payload is not None and instruction is None:
            context = payload['context']
            answer = validate_prediction(parsed, context['registry'], context['query_id'], payload['sensor'])
        else:
            raise ValueError('exactly one original instruction or prediction payload is required')
        result['answer'] = answer
        result['stages'][stage] = 'passed'
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        result['stages'][stage] = 'failed'
        result['errors'][stage] = error
        result['failure_stage'] = stage
        result['error'] = error
        if stage == 'schema':
            result['schema_category'] = schema_category(str(exc))
    return result
