"""The exact live failure is forbidden at token time; no output deduplication."""
import itertools
import json
import pytest
from egrs.selector.structured import unique_supports_parser,SUPPORTS,prediction_schema
from tests.test_structured import accepted
from tests.test_data_training import example


def support_accepts(value):
    parser=unique_supports_parser()
    for char in json.dumps(value,separators=(',',':')):
        if char not in parser.get_allowed_characters():return False
        parser=parser.add_character(char)
    return parser.can_end()


def test_all_325_valid_ordered_subsets_remain_available():
    count=0
    for length in range(1,6):
        for values in itertools.permutations(SUPPORTS,length):
            assert support_accepts(list(values));count+=1
    assert count==325


@pytest.mark.parametrize('bad',[[],['entity','entity'],['role','entity','role'],
    ['entity','role','relation','release','interaction','entity'],['made_up']])
def test_duplicates_empty_and_unknown_tags_rejected(bad):
    assert not support_accepts(bad)


def test_same_duplicate_in_full_prediction_rejected_by_generation_grammar():
    sample=example();ctx=sample['payload']['context']
    sample['answer']['goals'][0]['evidence'][0]['supports']=['entity','entity']
    assert not accepted(prediction_schema(ctx['registry'],1,sample['payload']['sensor']),sample['answer'])
