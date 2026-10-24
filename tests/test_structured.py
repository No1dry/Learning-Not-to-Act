"""Required keys constrained before sampling; unchanged semantics remain strict."""
import copy
import json
import pytest
from egrs.selector.structured import prediction_schema,schema_hash
from egrs.contracts import validate_prediction
from tests.test_data_training import example


def accepted(schema,value):
    from lmformatenforcer import JsonSchemaParser
    parser=JsonSchemaParser(schema)
    for char in json.dumps(value,separators=(',',':')):
        if char not in parser.get_allowed_characters():return False
        parser=parser.add_character(char)
    return parser.can_end()


def test_complete_answer_accepted_missing_evidence_forbidden():
    sample=example();ctx=sample['payload']['context']
    schema=prediction_schema(ctx['registry'],ctx['query_id'],sample['payload']['sensor'])
    assert accepted(schema,sample['answer'])
    missing=copy.deepcopy(sample['answer']);del missing['goals'][0]['evidence']
    assert not accepted(schema,missing)
    assert len(schema_hash(schema))==64


def test_evidence_not_invented_or_semantic_validator_weakened():
    sample=example();ctx=sample['payload']['context']
    schema=prediction_schema(ctx['registry'],ctx['query_id'],sample['payload']['sensor'])
    empty=copy.deepcopy(sample['answer']);empty['goals'][0]['evidence']=[]
    assert accepted(schema,empty)
    with pytest.raises(ValueError,match='evidence'):
        validate_prediction(empty,ctx['registry'],ctx['query_id'],sample['payload']['sensor'])


def test_constraint_uses_only_input_ids_not_image_values_or_truth():
    sample=example();ctx=sample['payload']['context']
    before=copy.deepcopy(sample['payload'])
    schema=prediction_schema(ctx['registry'],ctx['query_id'],sample['payload']['sensor'])
    assert sample['payload']==before
    assert 'physical_truth' not in json.dumps(schema)
    wrong=copy.deepcopy(sample['answer']);wrong['query_id']=2
    assert not accepted(schema,wrong)
    wrong=copy.deepcopy(sample['answer']);wrong['goals'][0]['evidence'][0]['snapshot_id']='q999'
    assert not accepted(schema,wrong)
