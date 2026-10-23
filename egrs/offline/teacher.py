"""Independent pinned offline 7B teacher. No student config, LoRA or fallback."""
import copy
import json
import time

from .common import digest

MODEL = 'Qwen/Qwen2.5-VL-7B-Instruct'
REVISION = 'cc594898137f460bfe9f0759e9844b3ce807cfb5'
DEFAULTS = {'model_id': MODEL, 'revision': REVISION, 'processor_id': MODEL,
    'processor_revision': REVISION, 'dtype': 'bfloat16', 'device': 'cuda', 'batch_size': 1,
    'do_sample': False, 'max_images': 6, 'max_visual_tokens': 256, 'max_length': 4096,
    'max_new_tokens': 1024, 'local_files_only': True}


def resolve_config(config=None):
    value = dict(DEFAULTS)
    value.update(config or {})
    if set(value) != set(DEFAULTS) or any(value[k] != v for k, v in DEFAULTS.items() if k != 'device'):
        raise ValueError('offline teacher requires fixed pinned 7B identity and budgets; no adapters/fallback')
    if not isinstance(value['device'], str) or not value['device']:
        raise ValueError('device must be a nonempty string')
    return value


class _Backend:
    def __init__(self, config):
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        self.config = config
        self.processor = AutoProcessor.from_pretrained(config['processor_id'], revision=config['processor_revision'],
            min_pixels=28 * 28 * 4, max_pixels=28 * 28 * config['max_visual_tokens'], use_fast=True,
            trust_remote_code=False, local_files_only=True)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(config['model_id'], revision=config['revision'],
            torch_dtype=torch.bfloat16, trust_remote_code=False, local_files_only=True)
        self.model.requires_grad_(False)
        self.model.eval()
        self.model.to(config['device'])

    def generate(self, messages, images, audit):
        import torch
        from egrs.selector.encoding import encode_messages
        encoded, _, _ = encode_messages(messages, images, self.processor,
            max_length=self.config['max_length'] - self.config['max_new_tokens'],
            max_visual_tokens=self.config['max_visual_tokens'], generation=True)
        audit['input_tokens'] = int(encoded['input_ids'].shape[1])
        encoded = {k: v.to(self.config['device']) if hasattr(v, 'to') else v for k, v in encoded.items()}
        audit['generation_attempted'] = True
        with torch.inference_mode():
            output = self.model.generate(**encoded, max_new_tokens=self.config['max_new_tokens'], do_sample=False)
        tokens = output[0, audit['input_tokens']:]
        audit['generated_tokens'] = len(tokens)
        return self.processor.tokenizer.decode(tokens, skip_special_tokens=True)

    def close(self):
        self.model = None
        self.processor = None


class OfflineTeacher:
    """One lazy backend per invocation, raw failures retained; injection is for tests."""
    def __init__(self, config=None, *, loader=None):
        from egrs.selector.prompt import PREDICTION_SCHEMA, REGISTRY_SCHEMA
        self.config = resolve_config(config)
        self.metadata = {'config': self.config, 'prompt_sha256': digest([REGISTRY_SCHEMA, PREDICTION_SCHEMA]),
                         'synthetic_backend': loader is not None}
        self._loader, self._backend = loader or _Backend, None
        self._load_error = None
        self.calls = 0

    def _run(self, *, instruction=None, payload=None):
        from egrs.contracts import validate_registry, validate_prediction, validate_payload
        from egrs.selector.prompt import build_messages, IMAGE_KEYS
        from egrs.selector.encoding import load_images
        start = time.monotonic()
        self.calls += 1
        audit = {'call': self.calls, 'attempted': True, 'raw': None, 'answer': None, 'error': None,
                 'generation_attempted': False, 'input_tokens': None, 'generated_tokens': None,
                 'payload': copy.deepcopy(payload), 'instruction': instruction, 'image_count': 0}
        try:
            images = []
            if payload is not None:
                images = load_images(payload)
                if len(images) > self.config['max_images']:
                    raise ValueError('image budget exceeded')
                materialized = copy.deepcopy(payload)
                import numpy as np
                image_iter = iter(images)
                for snap in materialized['sensor']:
                    for key in IMAGE_KEYS:
                        if key in snap['observation']:
                            snap['observation'][key] = np.asarray(next(image_iter))
                validate_payload(materialized)
            messages = build_messages(payload, instruction=instruction)
            audit.update(messages=messages, image_count=len(images))
            if self._load_error is not None:
                raise RuntimeError('previous backend load failed; no retry: ' + self._load_error)
            if self._backend is None:
                try:
                    self._backend = self._loader(self.config)
                except Exception as exc:
                    self._load_error = f'{type(exc).__name__}: {exc}'
                    raise
            audit['raw'] = self._backend.generate(messages, images, audit)
            parsed = json.loads(audit['raw'])
            if instruction is not None:
                audit['answer'] = validate_registry(parsed, instruction)
            else:
                c = payload['context']
                audit['answer'] = validate_prediction(parsed, c['registry'], c['query_id'], payload['sensor'])
        except Exception as exc:
            audit['error'] = f'{type(exc).__name__}: {exc}'
        audit['elapsed_seconds'] = time.monotonic() - start
        return audit

    def registry(self, instruction):
        return self._run(instruction=instruction)

    def predict(self, payload):
        return self._run(payload=payload)

    def close(self):
        if self._backend is not None:
            self._backend.close()
            self._backend = None
