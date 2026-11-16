"""Pure file/JSON contracts for the approved044 initial semantic diagnostics."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

MANIFEST_SHA256='e648ef202c31e6e99e14478f6ec36952a1791d2187bf023a224b25974f669566'
_CONTENT_SHA256='99cc99e44b727170ab8316c34834e989d8b95e2596ee28e8d220239bb95ad3c1'
NATIVE_FACTORY='benchmark.remaining_goals.adapters.openvla_oft:make_policy'
OFT_REVISION='e4287e94541f459edc4feabc4e181f537cd569a8'
BASE_SOURCE={'repository':'moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10',
             'revision':'638918f3d1c2e43a39a8a20772bdb8b91835e4b7'}
WRAPPER_SOURCE='unchanged official OFT formatting, tokenization and native forward'


def text_sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate044 JSON field: '+key)
        result[key]=value
    return result


def validate_manifest(manifest):
    try:
        encoded=json.dumps(manifest,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError) as error:
        raise ValueError('Invalid frozen044 prompt manifest') from error
    if text_sha256(encoded)!=_CONTENT_SHA256:
        raise ValueError('Frozen044 prompt manifest content differs')
    return manifest


def load_manifest(path):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('Frozen044 prompt manifest byte SHA differs from approved table')
    return validate_manifest(json.loads(raw,object_pairs_hook=_unique))


def prompt_record(manifest,variant,original_instruction):
    validate_manifest(manifest)
    if type(variant) is not str or variant not in ('p1','p2'):
        raise ValueError('044 prompt variant must be p1 or p2')
    if type(original_instruction) is not str:
        raise ValueError('044 source instruction must exactly match a frozen task')
    matches=[row for row in manifest['tasks'] if row['original_instruction']==original_instruction]
    if len(matches)!=1:raise ValueError('044 source instruction does not exactly match one frozen task')
    row=matches[0]
    instruction=(original_instruction+'. '+row['p1_added_initial_fact'] if variant=='p1'
                 else row['p2_instruction'])
    if instruction!=row[variant+'_instruction']:
        raise ValueError('044 prompt construction conflicts with frozen table')
    return {'task_id':row['task_id'],'official_task_id':row['official_task_id'],
        'source_instruction':original_instruction,'model_instruction':instruction,
        'source_instruction_sha256':text_sha256(original_instruction),
        'model_instruction_sha256':text_sha256(instruction),'prompt_variant':variant,
        'prompt_manifest_sha256':MANIFEST_SHA256}


def validate_native_runtime(config):
    """Reject research routes before any official model construction."""
    if not isinstance(config,dict):raise ValueError('044 native runtime must be an object')
    forbidden={'method_adapter','adapter','teacher_adapter','initial_adapter','task_control_arm',
        'experiment_arm','hint043_arm','attention_contract','attention_runtime','finish','training_recipe',
        'prompt_override','status_sidecar','sidecar','checkpoint_override'}
    if forbidden.intersection(config):raise ValueError('044 forbids research adapter/head/routing fields')
    options=config.get('adapter_options');execution=config.get('execution')
    if not isinstance(options,dict) or not isinstance(execution,dict):
        raise ValueError('044 requires original native options and execution contract')
    allowed={'repo_path','repo_revision','checkpoint','suite','seed','center_crop','load_in_8bit','load_in_4bit'}
    if set(options)-allowed:raise ValueError('044 forbids non-native adapter options')
    if (config.get('model_id')!='openvla_oft' or config.get('policy_factory')!=NATIVE_FACTORY
            or config.get('checkpoint_source')!=BASE_SOURCE or config.get('suite')!='libero_10'
            or options.get('suite')!='libero_10' or options.get('repo_revision')!=OFT_REVISION
            or options.get('center_crop',True) is not True
            or options.get('load_in_8bit',False) is not False or options.get('load_in_4bit',False) is not False
            or type(execution.get('random_seed')) is not int or execution['random_seed']!=7
            or type(execution.get('max_chunk_steps')) is not int or execution['max_chunk_steps']!=8
            or type(options.get('seed',7)) is not int or options.get('seed',7)!=7):
        raise ValueError('044 requires original official SOG10/libero10/crop/seed7/chunk8/full precision')
    for key in ('repo_path','checkpoint'):
        if not isinstance(options.get(key),str) or not options[key].strip():
            raise ValueError('044 native runtime requires '+key)
    return deepcopy(config)
