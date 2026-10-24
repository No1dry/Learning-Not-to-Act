"""Final multimodal token alignment. Ambiguity is a technical error."""
from pathlib import Path

from .prompt import IMAGE_KEYS, bounded_payload, build_messages
from .supervision import prepare_answer, serialize_with_spans


def load_images(payload):
    from PIL import Image
    import numpy as np
    images = []
    for sensor in payload["sensor"]:
        for key in IMAGE_KEYS:
            if key not in sensor["observation"]:
                continue
            value = sensor["observation"][key]
            if isinstance(value, (str, Path)):
                with Image.open(value) as im:
                    images.append(im.convert("RGB").copy())
            elif isinstance(value, Image.Image):
                images.append(value.convert("RGB"))
            else:
                array = np.asarray(value)
                if array.dtype != np.uint8 or array.ndim != 3 or array.shape[-1] != 3:
                    raise ValueError("images must be uint8 HWC RGB")
                images.append(Image.fromarray(array))
    return images


def expand_image_text(text, encoded, processor, max_visual_tokens):
    token = getattr(processor, "image_token", "<|image_pad|>")
    grids = encoded.get("image_grid_thw")
    if grids is None:
        if token in text:
            raise ValueError("image token without processor image grid")
        return text
    grids = grids.tolist() if hasattr(grids, "tolist") else grids
    if text.count(token) != len(grids):
        raise ValueError("image token/grid count mismatch")
    parts = text.split(token)
    result = parts[0]
    merge = processor.image_processor.merge_size ** 2
    for i, grid in enumerate(grids):
        count = int(grid[0] * grid[1] * grid[2]) // merge
        if not 0 < count <= max_visual_tokens:
            raise ValueError("per-image visual token budget exceeded")
        result += token * count + parts[i + 1]
    return result


def encode_messages(messages, images, processor, *, max_length=4096, max_visual_tokens=256, generation=False):
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=generation)
    kwargs = {"text": [text], "return_tensors": "pt", "padding": False, "truncation": False}
    if images:
        kwargs["images"] = images
    encoded = processor(**kwargs)
    expanded = expand_image_text(text, encoded, processor, max_visual_tokens)
    alignment = processor.tokenizer(expanded, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
    actual = encoded["input_ids"][0].tolist()
    if alignment["input_ids"] != actual:
        raise ValueError("final processor IDs and expanded-template tokenizer IDs disagree; mask alignment rejected")
    if len(actual) > max_length:
        raise ValueError(f"total length {len(actual)} exceeds budget {max_length}")
    return encoded, expanded, alignment["offset_mapping"]


def encode_sample(sample, processor, *, max_length=4096, max_visual_tokens=256, max_images=6, max_answer_tokens=1024, use_history=True, role_supervision=True, audit=None):
    import torch
    answer, supervised = prepare_answer(sample["answer"], sample.get("provenance", {}), role_supervision)
    answer_text, spans = serialize_with_spans(answer)
    payload, dropped = bounded_payload(sample["payload"], use_history, max_images)
    while True:
        available = {s["snapshot_id"] for s in payload["sensor"]}
        if any(e["snapshot_id"] not in available for goal in answer["goals"] for e in goal["evidence"]):
            raise ValueError("answer evidence refers to history removed by the image/context budget")
        # Validate the materialized sensor envelope through the shared contract.
        from egrs.contracts import validate_payload
        import copy
        materialized = copy.deepcopy(payload)
        import numpy as np
        images = load_images(payload)
        idx = 0
        for sensor in materialized["sensor"]:
            for key in IMAGE_KEYS:
                if key in sensor["observation"]:
                    sensor["observation"][key] = np.asarray(images[idx])
                    idx += 1
        validate_payload(materialized)
        messages = build_messages(payload, answer=answer_text)
        try:
            encoded, text, offsets = encode_messages(messages, images, processor, max_length=max_length, max_visual_tokens=max_visual_tokens)
            break
        except ValueError as exc:
            if "total length" not in str(exc) or len(payload["sensor"]) <= 1:
                raise
            oldest = payload["sensor"].pop(0)["query_id"]
            dropped.append(oldest)
            for field in ("history", "commands"):
                payload["context"][field] = [x for x in payload["context"][field] if x.get("query_id") != oldest]
    # The complete canonical answer must occur once, with no heuristic ID matching.
    start = text.rfind(answer_text)
    if start < 0 or text.find(answer_text) != start:
        raise ValueError("assistant answer alignment is ambiguous")
    answer_tokens = sum(right > start and left < start + len(answer_text) for left, right in offsets)
    if answer_tokens > max_answer_tokens:
        raise ValueError("complete answer exceeds answer token budget; never truncate an answer")
    intervals = [(start + spans[p][0], start + spans[p][1]) for p in supervised if p in spans]
    ids = encoded["input_ids"]
    labels = torch.full_like(ids, -100)
    covered = {p: False for p in supervised if p in spans}
    for i, (left, right) in enumerate(offsets):
        # BPE tokens crossing a field boundary are masked. Never label prompt/key
        # bytes simply because a token overlaps a confirmed value.
        if right > left and any(a <= left and right <= b for a, b in intervals):
            labels[0, i] = ids[0, i]
            for p in covered:
                a, b = spans[p]
                if start + a <= left and right <= start + b:
                    covered[p] = True
    if not covered or not all(covered.values()):
        raise ValueError("no unambiguous supervised tokens for one or more confirmed fields")
    encoded["labels"] = labels
    if audit is not None:
        grids = encoded.get("image_grid_thw")
        visual = sum(int(g[0] * g[1] * g[2]) // processor.image_processor.merge_size ** 2 for g in grids.tolist()) if grids is not None else 0
        audit.update({"dropped_snapshot_queries": dropped, "image_count": len(images), "visual_tokens": visual, "final_tokens": ids.shape[1], "answer_tokens": answer_tokens, "answer_budget": max_answer_tokens, "context_budget_after_images_and_answer": max_length - visual - answer_tokens, "prompt_and_history_tokens": ids.shape[1] - visual - answer_tokens, "supervised_tokens": int((labels != -100).sum()), "confirmed_fields": len(supervised), "masked_fields": len(spans) - len(supervised), "role_supervision": role_supervision, "use_history": use_history})
    return encoded
