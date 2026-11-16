"""Original official SOG10, changing only the string passed to native predict."""
from copy import deepcopy
import json
import os
from pathlib import Path

from .prompts import (BASE_SOURCE,MANIFEST_SHA256,NATIVE_FACTORY,WRAPPER_SOURCE,
                      load_manifest,prompt_record,validate_native_runtime)

FACTORY='egrs.prompt044.policy:make_policy'
MAX_EPISODES=90
MAX_QUERIES_PER_EPISODE=65
MAX_PREDICT_CALLS=5850


def check_metadata(config,metadata):
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata
    validate_native_runtime(config)
    validate_policy_metadata(config,metadata)
    if metadata.get('unnorm_key')!='libero_10_no_noops':
        raise ValueError('044 requires original libero_10_no_noops normalization')
    if any(key in metadata for key in ('method_adapter','hint043_arm','task_control_arm','attention_contract','experiment_arm')):
        raise ValueError('044 cannot identify a research student as the original native model')
    return deepcopy(metadata)


class Prompt044Policy:
    def __init__(self,config):
        if not isinstance(config,dict) or config.get('policy_factory')!=FACTORY:
            raise ValueError('044 requires its explicit prompt policy factory')
        base_config=deepcopy(config)
        try:
            self.variant=base_config.pop('prompt_variant')
            manifest_path=base_config.pop('prompt_manifest')
            audit_path=base_config.pop('prompt_audit_path')
        except KeyError as error:raise ValueError('044 requires variant, frozen manifest and fresh audit path') from error
        self.manifest=load_manifest(manifest_path)
        # Check the arm independently of a future instruction before model load.
        prompt_record(self.manifest,self.variant,self.manifest['tasks'][0]['original_instruction'])
        base_config['policy_factory']=NATIVE_FACTORY
        validate_native_runtime(base_config)
        if not isinstance(audit_path,str) or not audit_path.strip():raise ValueError('044 requires a fresh audit path')
        audit=Path(audit_path).expanduser().resolve()
        protected=[Path(manifest_path).expanduser().resolve(),
                   *[Path(base_config['adapter_options'][k]).expanduser().resolve() for k in ('checkpoint','repo_path')]]
        if any(audit==p or p in audit.parents or audit in p.parents for p in protected):
            raise ValueError('044 audit path overlaps immutable model/manifest inputs')
        self.base=None;self._closed=False;self._failed=False
        self._episode=0;self._episode_query=0;self._sequence=0;self._instruction=None
        # Exclusive creation is the worker-level duplicate guard. Preserve it on
        # initialization/call failures; no implicit retry or ledger refund.
        self._audit=audit.open('x',encoding='utf-8',newline='\n')
        try:
            from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
            self.base=OpenVLAOFTPolicy(base_config)
            self.metadata=check_metadata(base_config,self.base.metadata)
            self.metadata.update(prompt_variant=self.variant,prompt_manifest_sha256=MANIFEST_SHA256,
                deployment_initial_semantic_information=True,prompt_fact_time='episode_initial_only',
                prompt_fixed_during_episode=True,prompt_wrapper_source=WRAPPER_SOURCE,
                prompt_audit_schema='task044-prompt-audit-v1',research_adapter_loaded=False)
            self._write({'event':'initialized','metadata':self.metadata,
                'budget':{'episodes':MAX_EPISODES,'predict_calls':MAX_PREDICT_CALLS,
                          'predict_calls_per_episode':MAX_QUERIES_PER_EPISODE}})
        except BaseException:
            try:
                if self.base is not None:self.base.close()
            finally:self._audit.close();self._closed=True
            raise

    def _write(self,record):
        value=dict(record,schema_version='task044-prompt-audit-v1')
        self._audit.write(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
        self._audit.flush();os.fsync(self._audit.fileno())

    def _ready(self):
        if self._closed:raise RuntimeError('044 policy is closed')
        if self._failed:raise RuntimeError('044 previous native call failed; preserve output and return control to user')

    def reset(self):
        self._ready()
        if self._episode>=MAX_EPISODES:raise ValueError('044 episode budget90 exhausted')
        self._episode+=1;self._episode_query=0;self._instruction=None
        try:
            self._write({'event':'episode_reset','episode_ordinal':self._episode})
            self.base.reset()
        except BaseException:
            self._failed=True
            raise

    def predict(self,observation,original_instruction):
        from benchmark.remaining_goals.adapters.openvla import _raw_observation
        self._ready()
        if not self._episode:raise ValueError('044 requires episode reset before predict')
        record=prompt_record(self.manifest,self.variant,original_instruction)
        if self._instruction is not None and self._instruction!=original_instruction:
            raise ValueError('044 source instruction/language changed within the episode')
        clean=_raw_observation(observation,wrist=True,proprio=True)
        if self._sequence>=MAX_PREDICT_CALLS or self._episode_query>=MAX_QUERIES_PER_EPISODE:
            raise ValueError('044 predict budget5850 or per-episode65 exhausted')
        self._instruction=original_instruction;self._sequence+=1;self._episode_query+=1
        try:
            self._write(dict(record,event='predict',sequence=self._sequence,
                episode_ordinal=self._episode,episode_query=self._episode_query))
        except BaseException:
            self._failed=True
            raise
        try:
            # This is the exact audited boundary, not a hand-written tokenizer
            # claim. Native predict owns original formatting, processing and API.
            result=self.base.predict(clean,record['model_instruction'])
        except BaseException as error:
            self._failed=True
            self._write({'event':'predict_result','sequence':self._sequence,'episode_ordinal':self._episode,
                'episode_query':self._episode_query,'status':'error','error':f'{type(error).__name__}: {error}'})
            raise
        try:
            self._write({'event':'predict_result','sequence':self._sequence,'episode_ordinal':self._episode,
                'episode_query':self._episode_query,'status':'returned'})
        except BaseException:
            self._failed=True
            raise
        return result

    def close(self):
        if self._closed:return
        try:
            if self.base is not None:self.base.close()
        finally:
            self._closed=True;self._audit.close()


def make_policy(config):
    return Prompt044Policy(config)
