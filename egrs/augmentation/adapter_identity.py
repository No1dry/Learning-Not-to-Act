"""Standard-library-only adapter identity validation for planning before model load."""
import hashlib
import json
from pathlib import Path
import re

OFT_REVISION = 'e4287e94541f459edc4feabc4e181f537cd569a8'
BASE_SOURCE = {'repository': 'moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10',
               'revision': '638918f3d1c2e43a39a8a20772bdb8b91835e4b7'}
LINEAGE_KEYS = ('repo_commit', 'checkpoint_source', 'dataset_statistics_sha256',
                'normalization_statistics_sha256', 'component_checkpoint_sha256', 'unnorm_key')
TARGET = re.compile(r'language_model\.model\.layers\.\d+\.self_attn\.(q_proj|k_proj|v_proj|o_proj)$')
GENERATED_DATA_KIND = 'task035-generated-trajectories-v1'
RETENTION_STATS_SHA='6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3'
RETENTION_RECIPE={'pool_weights':{'ten':.5,'fresh':.25,'raw':.25},
    'pool_samples':{'ten':12,'fresh':4,'raw':4},'prefix':'max(1,ceil(T_obs/3))',
    'reference_prefix_samples':{'fresh':2,'raw':2},'gradient_accumulation':20,'seed':7,'updates':1000}


def validate_retention_recipe_identity(identity):
    """Independent036 identity; planning must stay free of model imports."""
    digest=lambda value:isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value)
    exports=identity.get('export_identity',{});calls=identity.get('reference_calls',{})
    update=identity.get('update')
    if (identity.get('schema_version')!='task036-oft-adapter-v1'
            or identity.get('group')!='policy_retention_distillation'
            or identity.get('recipe')!='policy_retention_distillation'
            or identity.get('data_kind')!='task036-retention-data-v1'
            or type(update) is not int or not 1<=update<=1000 or identity.get('final_update')!=1000
            or not isinstance(exports,dict) or set(exports)!={'sources.json','rows.jsonl','report.json'}
            or not all(digest(v) for v in exports.values())
            or identity.get('reference_view')!='shared_frozen_base_without_added_lora'
            or identity.get('reference_base')!=BASE_SOURCE
            or identity.get('training_recipe')!=RETENTION_RECIPE
            or not isinstance(calls,dict) or set(calls)!={'train','dev','total','budget'}
            or type(calls.get('train')) is not int or not 8*update<=calls['train']<=8000
            or type(calls.get('dev')) is not int or not 0<=calls['dev']<=1024
            or type(calls.get('total')) is not int or calls['total']!=calls['train']+calls['dev']
            or type(calls.get('budget')) is not int or calls['budget']!=9024
            or calls['total']>9024):
        raise ValueError('Invalid task036 recipe, reference, budget or export identity')


def validate_retention_lineage(lineage):
    if (lineage.get('unnorm_key')!='libero_10_no_noops'
            or lineage.get('dataset_statistics_sha256')!=RETENTION_STATS_SHA):
        raise ValueError('task036 requires original SOG10 statistics and normalization key')


def validate_recipe_identity(identity):
    """035 identities bind the generated export and concrete update; 030 stays v1."""
    digest = lambda value: isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
    exports = identity.get('export_identity', {})
    if (identity.get('schema_version') != 'task035-oft-adapter-v1'
        or identity.get('group') != 'robot_rewind_mix'
        or identity.get('recipe') != 'robot_rewind_mix'
        or identity.get('data_kind') != GENERATED_DATA_KIND
        or identity.get('final_update') != 1000
        or type(identity.get('update')) is not int
        or not 1 <= identity['update'] <= 1000
        or not isinstance(exports, dict)
        or set(exports) != {'sources.json', 'windows.jsonl', 'report.json'}
        or not all(digest(value) for value in exports.values())):
        raise ValueError('Invalid task035 recipe, update or generated export identity')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _lineage(policy):
    lineage = {key: policy.metadata.get(key) for key in LINEAGE_KEYS}
    if lineage['repo_commit'] != OFT_REVISION or lineage['checkpoint_source'] != BASE_SOURCE:
        raise ValueError('Original OFT/SOG10 lineage does not match pinned sources')
    if any(lineage[key] is None for key in LINEAGE_KEYS):
        raise ValueError('Original OFT component/statistics lineage is incomplete')
    return lineage


def read_adapter_identity(directory):
    directory = Path(directory)
    identity = json.loads((directory / 'identity.json').read_text(encoding='utf-8'))
    if identity.get('schema_version') == 'task035-oft-adapter-v1':
        validate_recipe_identity(identity)
        valid_recipe = True
    elif identity.get('schema_version') == 'task036-oft-adapter-v1':
        validate_retention_recipe_identity(identity)
        validate_retention_lineage(identity.get('base_lineage',{}))
        valid_recipe = True
    else:
        valid_recipe = (identity.get('schema_version') == 'task030-oft-adapter-v1'
                        and identity.get('group') in {'raw_control', 'progress_aug'})
    if (not valid_recipe
        or identity.get('implementation') != 'native-linear-lora'
        or (identity.get('rank'), identity.get('alpha'), identity.get('dropout')) != (16, 32, 0)
        or identity.get('base_lineage', {}).get('repo_commit') != OFT_REVISION
        or identity.get('base_lineage', {}).get('checkpoint_source') != BASE_SOURCE
        or sha256(directory / 'adapter.pt') != identity.get('adapter_sha256')):
        raise ValueError('Invalid adapter identity, lineage or adapter byte hash')
    lineage = identity['base_lineage']
    digest = lambda value: isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
    components = lineage.get('component_checkpoint_sha256')
    if (set(lineage) != set(LINEAGE_KEYS)
        or not digest(lineage.get('dataset_statistics_sha256'))
        or not digest(lineage.get('normalization_statistics_sha256'))
        or lineage.get('unnorm_key') not in {'libero_10', 'libero_10_no_noops'}
        or not isinstance(components, dict) or len(components) != 2
        or not all(digest(value) for value in components.values())
        or not all(sum(component in name for name in components) == 1
                   for component in ('action_head', 'proprio_projector'))):
        raise ValueError('Incomplete or malformed original OFT lineage')
    targets = identity.get('target_modules', [])
    if not targets or targets != sorted(set(targets)) or any(not TARGET.fullmatch(n) for n in targets):
        raise ValueError('Invalid adapter language target inventory')
    shapes = identity.get('trainable_parameters', {})
    if set(shapes) != {n + suffix for n in targets for suffix in ('.lora_A', '.lora_B')}:
        raise ValueError('Invalid adapter parameter inventory')
    for target in targets:
        a, b = shapes[target + '.lora_A'], shapes[target + '.lora_B']
        if (not isinstance(a, list) or not isinstance(b, list) or len(a) != 2 or len(b) != 2
            or any(type(size) is not int or size < 1 for size in a + b)
            or a[0] != 16 or b[1] != 16):
            raise ValueError('Invalid adapter parameter shapes or rank')
    return identity
