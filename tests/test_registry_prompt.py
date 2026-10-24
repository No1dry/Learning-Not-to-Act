"""Registry-only prompt repair; no real generation or semantic validator changes."""
import copy
import hashlib
import json

import pytest

from egrs.contracts import validate_registry
from egrs.selector.prompt import (REGISTRY_EXAMPLES,REGISTRY_SCHEMA,REGISTRY_PROMPT_VERSION,
    REGISTRY_PROMPT_SHA256,PREDICTION_SCHEMA,build_messages)
from tests.test_data_training import example


@pytest.mark.parametrize('instruction,registry',REGISTRY_EXAMPLES)
def test_generic_registry_examples_obey_unchanged_contract(instruction,registry):
    assert validate_registry(registry,instruction)==registry
    for goal in registry['goals']:
        assert goal['source_text'] in instruction
        assert goal['actor_text'].split()[0] in {'put','open'}
        assert 'person' not in goal['actor_text']
        assert set(goal)=={'goal_ref','source_text','actor_text','target','destination','kind'}


def test_examples_do_not_replace_actual_user_instruction_or_mutate():
    instruction='place the orange cone beside the gray box'
    before=copy.deepcopy(REGISTRY_EXAMPLES)
    messages=build_messages(instruction=instruction)
    assert [m['role'] for m in messages]==['system','user','assistant','user','assistant','user']
    assert messages[-1]=={'role':'user','content':instruction}
    assert messages[0]['content']==REGISTRY_SCHEMA
    assert REGISTRY_EXAMPLES==before
    assert 'NOT a person' in REGISTRY_SCHEMA


def test_observed_error_categories_still_rejected_without_rewriting():
    instruction=REGISTRY_EXAMPLES[0][0]
    bad=copy.deepcopy(REGISTRY_EXAMPLES[0][1])
    bad['instruction']=instruction.capitalize()+'.'
    for goal in bad['goals']:
        goal['source_text']=bad['instruction'];goal['actor_text']='the person'
    with pytest.raises(ValueError,match='original instruction'):validate_registry(bad,instruction)
    bad['instruction']=instruction
    with pytest.raises(ValueError,match='literal span'):validate_registry(bad,instruction)
    for goal in bad['goals']:goal['source_text']=goal['target']
    with pytest.raises(ValueError,match='actor_text'):validate_registry(bad,instruction)


def test_visual_training_and_prediction_prompt_is_byte_identical_to026():
    assert hashlib.sha256(PREDICTION_SCHEMA.encode()).hexdigest()=='0084ebe606c9975a26c47e44b26390b2df34741c551289acc2960931be2cb6d6'
    messages=build_messages(example()['payload'])
    assert hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()=='173a79b97cba88d5cc43c7df21c2458ba5b3949ffc45e8a9b6e583b1660fa0c7'


def test_registry_prompt_identity_recorded_without_loading_weights():
    from egrs.selector import QwenSelector
    value=QwenSelector({'device':'cpu'})
    assert value.metadata['registry_prompt_version']==REGISTRY_PROMPT_VERSION
    assert value.metadata['registry_prompt_sha256']==REGISTRY_PROMPT_SHA256
    assert value.metadata['model_loaded'] is False
