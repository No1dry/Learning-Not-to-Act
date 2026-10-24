"""Token-time JSON shape constraints, never semantic post-hoc repair or truth."""
from copy import deepcopy
import hashlib
import json

VERSION = 'egrs.visual-json-schema.v1'
DEPENDENCY = 'lm-format-enforcer==0.11.3'


def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def enum(*values):
    return dict(enum=list(values))


def prediction_schema(registry, query_id, snapshots):
    """Use only already-public goal IDs/kinds and supplied snapshot identities.

    All observed values, entity IDs, cameras, boxes and supports remain generated
    by the model. The unchanged semantic validator still rejects unsupported or
    mismatched claims. A grammar-valid answer is not necessarily a valid claim.
    """
    identifier = dict(type='string', pattern='[A-Za-z][A-Za-z0-9_-]{0,63}')
    choices = []
    for goal in registry['goals']:
        ref = goal['goal_ref']
        regions = []
        for shot in snapshots:
            regions.append(obj(dict(
                goal_ref=enum(ref), entity_ref=deepcopy(identifier),
                query_id=enum(shot['query_id']), snapshot_id=enum(shot['snapshot_id']),
                camera=enum('agentview','wrist'),
                bbox=dict(type='array', items=dict(type='number',minimum=0,maximum=1),minItems=4,maxItems=4),
                coordinate_system=enum('normalized_xyxy'),
                supports=dict(type='array', items=enum('entity','role','relation','release','interaction'),minItems=1,maxItems=5))))
        release = enum('NOT_APPLICABLE') if goal['kind']=='mechanism' else enum('RELEASED','NOT_RELEASED','UNKNOWN')
        choices.append(obj(dict(goal_ref=enum(ref),
            entity_ref=dict(anyOf=[deepcopy(identifier),dict(type='null')]),
            association=enum('MATCHED','UNKNOWN'),
            role=enum('TARGET','COMPLETED','DISTRACTOR','UNKNOWN'),
            relation=enum('SAT','UNSAT','UNKNOWN'), release=release,
            interaction=enum('HELD','NOT_HELD','UNKNOWN'),
            evidence=dict(type='array',items=dict(anyOf=regions),minItems=0,maxItems=12))))
    return obj(dict(query_id=enum(query_id),goals=dict(type='array',
        items=dict(anyOf=choices),minItems=len(choices),maxItems=len(choices))))


def schema_hash(schema):
    return hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build_visual_prefix(tokenizer, schema, cached_tokenizer_data=None):
    from lmformatenforcer import JsonSchemaParser
    from lmformatenforcer.integrations.transformers import (
        build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn)
    data = cached_tokenizer_data or build_token_enforcer_tokenizer_data(tokenizer)
    return build_transformers_prefix_allowed_tokens_fn(data,JsonSchemaParser(schema)),data
