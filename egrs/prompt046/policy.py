"""Small model-loader adaptation; all prompt/audit/control code is reused."""
from copy import deepcopy
from pathlib import Path

from egrs.prompt044.policy import Prompt044Policy
from egrs.prompt044.prompts import (MANIFEST_SHA256, NATIVE_FACTORY, WRAPPER_SOURCE,
                                  load_manifest, prompt_record, validate_native_runtime)

FACTORY = 'egrs.prompt046.policy:make_policy'
EXPECTED_ADAPTER_SHA256 = '78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d'


def read_bound_adapter(directory):
    from egrs.hint043.adapter import read_adapter_identity
    value = read_adapter_identity(directory)
    check_adapter(value)
    return value


def check_adapter(value):
    from egrs.hint043.adapter import validate
    validate(value)
    if (value['arm'] != 'h1' or value['update'] != 3000 or value['final_update'] != 3000
            or value['adapter_sha256'] != EXPECTED_ADAPTER_SHA256):
        raise ValueError('046 requires the frozen045 H1@3000 adapter bytes')
    return value


def native_config(config):
    cfg = deepcopy(config)
    for key in ('method_adapter', 'hint043_arm', 'hint043_checkpoint_step',
                'prompt_variant', 'prompt_manifest', 'prompt_audit_path'):
        cfg.pop(key, None)
    cfg['policy_factory'] = NATIVE_FACTORY
    validate_native_runtime(cfg)
    return cfg


def check_metadata(config, metadata):
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata
    validate_policy_metadata(native_config(config), metadata)
    check_adapter(metadata.get('method_adapter', {}))
    if (metadata.get('unnorm_key') != 'libero_10_no_noops'
            or metadata.get('hint043_arm') != 'h1'
            or metadata.get('hint043_checkpoint_step') != 3000
            or metadata.get('research_adapter_loaded') is not True
            or metadata.get('deployment_hint') is not True
            or metadata.get('deployment_initial_semantic_information') is not True):
        raise ValueError('046 loaded model or diagnostic semantic-input metadata differs')
    return deepcopy(metadata)


def construct_hint_policy(config):
    from egrs.hint043.policy import HintPolicy
    return HintPolicy(config)


class Prompt046Policy(Prompt044Policy):
    # predict/reset/close, exact language lookup, observation allowlist and
    # durable call accounting are the unchanged accepted044 implementation.
    def __init__(self, config):
        if not isinstance(config, dict) or config.get('policy_factory') != FACTORY:
            raise ValueError('046 explicit policy factory required')
        cfg = deepcopy(config)
        try:
            self.variant = cfg.pop('prompt_variant')
            manifest_path = cfg.pop('prompt_manifest')
            audit_path = cfg.pop('prompt_audit_path')
            directory = cfg['method_adapter']
        except KeyError as error:
            raise ValueError('046 requires fixed adapter, prompts and new audit path') from error
        if cfg.get('hint043_arm') != 'h1' or cfg.get('hint043_checkpoint_step') != 3000:
            raise ValueError('046 requires explicit H1 and checkpoint step3000')
        self.manifest = load_manifest(manifest_path)
        prompt_record(self.manifest, self.variant, self.manifest['tasks'][0]['original_instruction'])
        native = native_config(cfg)
        expected = read_bound_adapter(directory)
        if not isinstance(audit_path, str) or not audit_path.strip():
            raise ValueError('046 requires a nonempty fresh audit path')
        audit = Path(audit_path).expanduser().resolve()
        protected = [Path(manifest_path).expanduser().resolve(), Path(directory).expanduser().resolve(),
                     *[Path(native['adapter_options'][key]).expanduser().resolve() for key in ('checkpoint', 'repo_path')]]
        if any(audit == p or p in audit.parents or audit in p.parents for p in protected):
            raise ValueError('046 audit overlaps immutable inputs')
        self.base = None
        self._closed = self._failed = False
        self._episode = self._episode_query = self._sequence = 0
        self._instruction = None
        self._audit = audit.open('x', encoding='utf-8', newline='\n')
        try:
            # HintPolicy owns the original loader and exactly one LoRA attach.
            self.base = construct_hint_policy(cfg)
            if self.base.metadata.get('method_adapter') != expected:
                raise ValueError('046 actual HintPolicy adapter differs from frozen artifact')
            self.metadata = deepcopy(self.base.metadata)
            self.metadata.update(prompt_variant=self.variant, prompt_manifest_sha256=MANIFEST_SHA256,
                deployment_hint=True, deployment_initial_semantic_information=True,
                prompt_fact_time='episode_initial_only', prompt_fixed_during_episode=True,
                prompt_wrapper_source=WRAPPER_SOURCE, prompt_audit_schema='task044-prompt-audit-v1',
                research_adapter_loaded=True, experiment='task046')
            # The immutable method_adapter.deployment_hint remains False; it
            # describes training/deployment artifact provenance, not this prompt.
            check_metadata(native, self.metadata)
            self._write({'event': 'initialized', 'metadata': self.metadata,
                         'budget': {'episodes': 90, 'predict_calls': 5850, 'predict_calls_per_episode': 65}})
        except BaseException:
            try:
                if self.base is not None:
                    self.base.close()
            finally:
                self._audit.close()
                self._closed = True
            raise


def make_policy(config):
    return Prompt046Policy(config)
