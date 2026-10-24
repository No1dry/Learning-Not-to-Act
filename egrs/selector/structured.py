"""Token-time JSON shape constraints, never semantic post-hoc repair or truth."""
from copy import deepcopy
import hashlib
import json

VERSION = 'egrs.visual-evidence-first.v3'
DEPENDENCY = 'lm-format-enforcer==0.11.3'
MAX_REGIONS = 3


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
            evidence=dict(type='array',items=dict(anyOf=regions),minItems=0,maxItems=MAX_REGIONS))))
    return obj(dict(query_id=enum(query_id),goals=dict(type='array',
        items=dict(anyOf=choices),minItems=len(choices),maxItems=len(choices))))


def schema_hash(schema):
    return hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def visual_parser(schema):
    """Canonical wire grammar with causal self-bindings, never scene truth.

    Cross-references echo the model's own earlier generated entity/query IDs.
    Normalized coordinates retain up to eight decimals (no rounding or repair).
    Compact field order and three regions bound repetition within the budget.
    """
    from lmformatenforcer import JsonSchemaParser, CharacterLevelParser
    from lmformatenforcer.characterlevelparser import (
        CharacterLevelParserConfig, StringParser, SequenceParser, UnionParser)
    from lmformatenforcer import RegexParser

    def js(value):
        return json.dumps(value,separators=(',',':'))

    def typed(value):
        return JsonSchemaParser(value,config=CharacterLevelParserConfig(
            max_consecutive_whitespaces=0,force_json_field_order=True))

    def literal(value):
        return (lambda ctx:StringParser(value),None)

    def field(factory,key=None):
        return (factory,key)

    class Fields(CharacterLevelParser):
        def __init__(self,steps,index=0,context=None,child=None,buffer=''):
            super().__init__()
            self.steps,self.index=steps,index
            self.context={} if context is None else context
            self.child=child if child is not None else (steps[index][0](self.context) if index<len(steps) else None)
            self.buffer=buffer

        def advance(self):
            context=dict(self.context)
            key=self.steps[self.index][1]
            if key is not None:context[key]=json.loads(self.buffer)
            return Fields(self.steps,self.index+1,context)

        def get_allowed_characters(self):
            if self.child is None:return ''
            chars=self.child.get_allowed_characters()
            if self.child.can_end():chars+=self.advance().get_allowed_characters()
            return ''.join(set(chars))

        def add_character(self,char):
            if self.child is not None and char in self.child.get_allowed_characters():
                return Fields(self.steps,self.index,self.context,self.child.add_character(char),self.buffer+char)
            if self.child is not None and self.child.can_end():return self.advance().add_character(char)
            raise ValueError('character outside canonical visual output grammar')

        def can_end(self):
            return self.child is None or (self.child.can_end() and self.advance().can_end())

    def box():
        parts=[StringParser('[')]
        for index in range(4):
            if index:parts.append(StringParser(','))
            parts.append(RegexParser(r'(0(\.[0-9]{1,8})?|1(\.0{1,8})?)'))
        return SequenceParser(parts+[StringParser(']')])

    def evidence(goal,entity,available):
        if entity is None:return StringParser('[]')
        def item():
            return Fields([
                literal('{"goal_ref":'+js(goal)+',"entity_ref":'+js(entity)+',"query_id":'),
                field(lambda ctx:typed(enum(*available)),'query'),
                field(lambda ctx:StringParser(',"snapshot_id":'+js('q'+str(ctx['query']))+',"camera":')),
                field(lambda ctx:typed(enum('agentview','wrist'))),
                literal(',"bbox":'),field(lambda ctx:box()),
                literal(',"coordinate_system":"normalized_xyxy","supports":'),
                field(lambda ctx:typed(dict(type='array',items=enum('entity','role','relation','release','interaction'),minItems=1,maxItems=5))),
                literal('}')])
        alternatives=[]
        for count in range(1,MAX_REGIONS+1):
            parts=[StringParser('[')]
            for index in range(count):
                if index:parts.append(StringParser(','))
                parts.append(item())
            alternatives.append(SequenceParser(parts+[StringParser(']')]))
        return UnionParser(alternatives)

    def goal_parser(goal):
        props=goal['properties'];ref=props['goal_ref']['enum'][0]
        regions=props['evidence']['items']['anyOf']
        available=[r['properties']['query_id']['enum'][0] for r in regions]
        mechanism=props['release']['enum']==['NOT_APPLICABLE']
        def supported(ctx,field_name):
            return any(field_name in item['supports'] and item['bbox'] is not None
                for item in ctx['evidence'])
        return Fields([
            literal('{"goal_ref":'+js(ref)+',"entity_ref":'),
            field(lambda ctx:typed(props['entity_ref']),'entity'),
            literal(',"association":'),field(lambda ctx:typed(enum('MATCHED' if ctx['entity'] is not None else 'UNKNOWN'))),
            literal(',"evidence":'),field(lambda ctx:evidence(ref,ctx['entity'],available),'evidence'),
            literal(',"role":'),field(lambda ctx:typed(props['role'] if supported(ctx,'role') else enum('UNKNOWN'))),
            literal(',"relation":'),field(lambda ctx:typed(props['relation'] if supported(ctx,'relation') else enum('UNKNOWN'))),
            literal(',"release":'),field(lambda ctx:typed(props['release'] if mechanism or supported(ctx,'release') else enum('UNKNOWN'))),
            literal(',"interaction":'),field(lambda ctx:typed(props['interaction'] if supported(ctx,'interaction') else enum('UNKNOWN'))),literal('}')])

    parts=[StringParser('{"query_id":'+js(schema['properties']['query_id']['enum'][0])+',"goals":[')]
    for index,goal in enumerate(schema['properties']['goals']['items']['anyOf']):
        if index:parts.append(StringParser(','))
        parts.append(goal_parser(goal))
    return SequenceParser(parts+[StringParser(']}')])


def build_visual_prefix(tokenizer, schema, cached_tokenizer_data=None):
    from lmformatenforcer.integrations.transformers import (
        build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn)
    class CachedSpecialTokens:
        all_special_ids=frozenset(tokenizer.all_special_ids)
        def __len__(self):return len(tokenizer)
        def __getattr__(self,name):return getattr(tokenizer,name)
    data = cached_tokenizer_data or build_token_enforcer_tokenizer_data(CachedSpecialTokens())
    return build_transformers_prefix_allowed_tokens_fn(data,visual_parser(schema)),data
