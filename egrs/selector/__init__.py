"""Independent selector; model weights are loaded only on the first RPC."""
import json
from copy import deepcopy

from .model import resolve_config, checkpoint_identity


class QwenSelector:
    def __init__(self, config=None):
        self.config = resolve_config(config)
        self._checkpoint = checkpoint_identity(self.config)
        self._model = self._processor = None
        self._closed = False
        self._set_input_audit([], [])

    @property
    def last_input_audit(self):
        """Latest call/attempt, including failures; None counts mean unconfirmed."""
        return deepcopy(self._last_input_audit)

    def _set_input_audit(self, supplied, kept):
        self._last_input_audit = {
            "supplied_snapshot_ids": list(supplied),
            "snapshot_ids": list(kept or []),
            "dropped_snapshot_ids": [sid for sid in supplied if sid not in kept] if kept is not None else [],
            "image_count": None,
            "final_prompt_tokens": None,
            "generated_tokens": None,
            "raw_output": None,
            "parsing": None,
        }

    @property
    def metadata(self):
        from .prompt import REGISTRY_PROMPT_VERSION,REGISTRY_PROMPT_SHA256
        return {"selector": "qwen2.5-vl", **self.config, "output_protocol": "egrs.selector-wire.v1", "registry_prompt_version":REGISTRY_PROMPT_VERSION,"registry_prompt_sha256":REGISTRY_PROMPT_SHA256, "checkpoint_identity": self._checkpoint, "model_loaded": self._model is not None, "adapter_loaded": self._model is not None and bool(self.config.get("adapter")), "trained_claim": False}

    def _load(self):
        if self._closed:
            raise RuntimeError("selector is closed")
        if self._model is None:
            from .model import load_model, load_processor
            self._checkpoint = checkpoint_identity(self.config)
            self._processor = load_processor(self.config)
            self._model = load_model(self.config, adapter=self.config.get("adapter"))

    def _generate(self, messages, images):
        self._load()
        import torch
        from .encoding import encode_messages
        from .training import move_batch
        inputs, _, _ = encode_messages(messages, images, self._processor, max_length=self.config["max_length"] - self.config["max_new_tokens"], max_visual_tokens=self.config["max_visual_tokens"], generation=True)
        # An encoding failure leaves counts unknown. Once encoding succeeds,
        # retain what is known even if model generation or JSON validation fails.
        self._last_input_audit.update(image_count=len(images), final_prompt_tokens=int(inputs["input_ids"].shape[1]))
        inputs = move_batch(inputs, self.config["device"])
        with torch.inference_mode():
            generated = self._model.generate(**inputs, do_sample=False, max_new_tokens=self.config["max_new_tokens"])
        self._last_input_audit["generated_tokens"] = int(generated.shape[1] - inputs["input_ids"].shape[1])
        answer = self._processor.tokenizer.decode(generated[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        from egrs.offline.parsing import decode_json_output
        decoded = decode_json_output(answer, protocol="egrs.selector-wire.v1")
        self._last_input_audit.update(raw_output=answer,
            parsing={key:value for key,value in decoded.items() if key != 'value'})
        if decoded['failure_stage'] is not None:
            raise ValueError("selector generated invalid JSON at " + decoded['failure_stage'] +
                ": " + decoded['error'] + "; raw retained, no semantic repair/retry")
        return decoded['value']

    def _validate_generated(self, validator, *args):
        try:
            result = validator(*args)
        except Exception as error:
            audit = self._last_input_audit.get('parsing')
            if audit is not None:
                from egrs.offline.parsing import schema_category
                message = type(error).__name__ + ': ' + str(error)
                audit['stages']['schema'] = 'failed'
                audit['errors']['schema'] = message
                audit.update(failure_stage='schema',error=message,
                             schema_category=schema_category(str(error)))
            raise
        audit = self._last_input_audit.get('parsing')
        if audit is not None: audit['stages']['schema'] = 'passed'
        return result

    def registry(self, instruction):
        self._set_input_audit([], [])
        from egrs.contracts import validate_registry
        from .prompt import build_messages
        answer = self._generate(build_messages(instruction=instruction), [])
        if self._last_input_audit["image_count"] is None:
            self._last_input_audit["image_count"] = 0
        return self._validate_generated(validate_registry, answer, instruction)

    def predict(self, payload):
        supplied = [shot["snapshot_id"] for shot in payload.get("sensor", []) if isinstance(shot, dict) and "snapshot_id" in shot] if isinstance(payload, dict) and isinstance(payload.get("sensor"), list) else []
        self._set_input_audit(supplied, None)
        from egrs.contracts import validate_payload, validate_prediction
        from .prompt import bounded_payload, build_messages
        from .encoding import load_images
        payload = validate_payload(payload)
        bounded, _ = bounded_payload(payload, self.config["use_history"], self.config["max_images"])
        # Reserve the complete answer budget. Drop oldest historical snapshots,
        # never the current observation, registry or answer allocation.
        while True:
            self._set_input_audit(supplied, [shot["snapshot_id"] for shot in bounded["sensor"]])
            try:
                images = load_images(bounded)
                answer = self._generate(build_messages(bounded), images)
                # Injected generators may not expose tokenizer counts; a
                # successful call still establishes which images it received.
                if self._last_input_audit["image_count"] is None:
                    self._last_input_audit["image_count"] = len(images)
                break
            except ValueError as exc:
                if "total length" not in str(exc) or len(bounded["sensor"]) <= 1:
                    raise
                oldest = bounded["sensor"].pop(0)["query_id"]
                for field in ("history", "commands"):
                    bounded["context"][field] = [x for x in bounded["context"][field] if x.get("query_id") != oldest]
        context = bounded["context"]
        return self._validate_generated(validate_prediction, answer, context["registry"], context["query_id"], bounded["sensor"])

    def reset(self):
        if self._closed:
            raise RuntimeError("selector is closed")
        # Stateless prompts; no hidden per-episode model or image history.

    def close(self):
        self._model = self._processor = None
        self._closed = True


def make_selector(config=None):
    return QwenSelector(config)
