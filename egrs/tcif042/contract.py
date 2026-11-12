"""JSON-only execution identity, separate from unchanged base lineage."""

AUDITED_SOURCE_SHA256 = '3aac24cec583a6ef5f60b6ec634a8bd3c8377784c5c63c8cc14cb6790554c52e'
TRANSFORMERS_VERSION = '4.40.1'
TORCH_VERSION = '2.4.1+cu121'


def contract_for(experiment_arm):
    if type(experiment_arm) is not str or experiment_arm not in {'f0', 'f1'}:
        raise ValueError('Task042 experiment_arm must be f0 or f1')
    return {
        'format': 'task042-attention-contract-v1',
        'implementation': 'instance-audited-llama-sdpa-v1',
        'experiment_arm': experiment_arm,
        'backend': 'torch.nn.functional.scaled_dot_product_attention',
        'mask': 'explicit-dense-additive-0-negative-infinity',
        'native_graph': 'padding-only-bidirectional',
        'routing': ('native-padding-only' if experiment_arm == 'f0'
                    else 'block-task-query-control-key-every-layer'),
        'control_reads_task_and_control': True,
        'is_causal': False,
        'use_cache': False,
        'checkpoint_mask': 'immutable-per-observation-explicit-layer-input',
        'reference': 'native-padding-only-without-student-layout-hook',
        'transformers_version': TRANSFORMERS_VERSION,
        'torch_version': TORCH_VERSION,
        'audited_source_sha256': AUDITED_SOURCE_SHA256,
    }


def validate_contract(value, experiment_arm=None):
    if type(value) is not dict:
        raise ValueError('Task042 attention contract must be an exact JSON object')
    arm = value.get('experiment_arm') if experiment_arm is None else experiment_arm
    expected = contract_for(arm)
    if (set(value) != set(expected)
            or any(type(value[key]) is not type(want) or value[key] != want
                   for key, want in expected.items())):
        raise ValueError('Task042 attention contract, arm, or execution backend differs')
    return value
