"""Swap only the policy adapter; reuse053 rollout, evidence and binary score.

The source configuration remains the original bank's H1-bound configuration.
The executed H0 adapter is a separate, explicit plan field, never a relabelled
H1 source configuration. No source construction or training is available here.
"""
from copy import deepcopy
from pathlib import Path

from egrs.remain049 import evaluation as original, sources
from egrs.remain053 import evaluation as previous, validation

ADAPTER_SHA = 'e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20'
BANK_SHA = previous.BANK_SHA
load_source_config = previous.load_config


def adapter_identity(directory):
    from egrs.hint043.adapter import read_adapter_identity
    from egrs.hint043.evaluation import validate_final
    value = read_adapter_identity(directory)
    validate_final(value, 3000)
    if value['arm'] != 'h0' or value['adapter_sha256'] != ADAPTER_SHA:
        raise ValueError('054 requires the frozen045 H0@3000 adapter')
    return value


def worker(plan):
    cfg = deepcopy(plan['runtime'])
    cfg.update(policy_factory='egrs.hint043.policy:make_policy',
               method_adapter=plan['method_adapter'], hint043_arm='h0',
               hint043_checkpoint_step=3000)
    return cfg


def protect(cfg, output, adapter):
    original.protect_output(cfg, output)
    output, adapter = Path(output).resolve(), Path(adapter).resolve()
    if output == adapter or output in adapter.parents or adapter in output.parents:
        raise ValueError('054 output overlaps immutable H0 weights')


def run(cfg, output, adapter):
    adapter = str(Path(adapter).resolve())
    protect(cfg, output, adapter)
    # Must precede benchmark-dependent engine/identity calls in a fresh CLI.
    sources.activate(cfg)
    identity = adapter_identity(adapter)
    namespace = previous.engine()
    source_plan = namespace['plan']

    def plan(source_cfg, model):
        if model != 'h0':
            raise ValueError('054 executes only H0@3000')
        # Original source-bound plan, no base policy is instantiated or run.
        value = source_plan(source_cfg, 'base')
        if value['source_bank_sha256'] != BANK_SHA:
            raise ValueError('054 must reuse the exact completed053 source bank')
        value.pop('plan_sha256')
        value.update(model='h0', method_adapter=adapter, adapter_identity=identity,
                     evaluation_scope='task054-h0-remain450-v1',
                     source_binding='unchanged original source configuration',
                     validation_extension=validation.identity())
        value['plan_sha256'] = sources.digest(value)
        return value

    namespace.update(plan=plan, _worker=worker)
    return namespace['run'](cfg, output, 'h0')
