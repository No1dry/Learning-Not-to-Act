"""Lazy pinned Qwen2.5-VL loading in a dedicated selector environment."""
import re
import hashlib
import json
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
REVISION = "66285546d2b821cf421d4f5eb2576359d3770cd3"
DEFAULTS = {"model_id": MODEL_ID, "revision": REVISION, "processor_id": MODEL_ID, "processor_revision": REVISION, "dtype": "bfloat16", "device": "cuda", "lora_r": 16, "lora_alpha": 32, "learning_rate": 1e-4, "epochs": 3, "global_batch_size": 16, "max_length": 4096, "max_visual_tokens": 256, "max_images": 6, "max_new_tokens": 1024, "use_history": True, "role_supervision": True, "seed": 0, "packing": False}


def resolve_config(config=None):
    value = dict(DEFAULTS)
    value.update(config or {})
    if "history" in value:
        if "use_history" in (config or {}) and value["history"] != value["use_history"]:
            raise ValueError("history and use_history conflict")
        value["use_history"] = value.pop("history")
    if "lora_path" in value:
        if "adapter" in value and value["adapter"] != value["lora_path"]:
            raise ValueError("adapter and lora_path conflict")
        value["adapter"] = value.pop("lora_path")
    if value["model_id"] != MODEL_ID or value["revision"] != REVISION:
        raise ValueError("selector requires the explicitly pinned Qwen2.5-VL-3B base")
    if value["processor_id"] != MODEL_ID or value["processor_revision"] != REVISION:
        raise ValueError("processor must match the pinned base revision")
    if value["packing"] or not 1 <= value["epochs"] <= 3:
        raise ValueError("packing disabled; epochs must be 1..3")
    if type(value["use_history"]) is not bool or type(value["role_supervision"]) is not bool:
        raise ValueError("history and role_supervision must be booleans")
    for key, limit in (("max_length", 4096), ("max_visual_tokens", 256), ("max_images", 6)):
        if not 0 < value[key] <= limit:
            raise ValueError(f"{key} must be 1..{limit}")
    if value["global_batch_size"] < 1 or value["learning_rate"] <= 0:
        raise ValueError("positive batch size and learning rate required")
    if not 0 < value["max_new_tokens"] < value["max_length"]:
        raise ValueError("answer generation budget must fit within total length")
    return value


def load_processor(config):
    from transformers import AutoProcessor
    return AutoProcessor.from_pretrained(config["processor_id"], revision=config["processor_revision"], min_pixels=28 * 28 * 4, max_pixels=28 * 28 * config["max_visual_tokens"], use_fast=True, trust_remote_code=False)


def checkpoint_identity(config):
    adapter = config.get("adapter")
    if not adapter:
        return None
    path = Path(adapter)
    checkpoint = path.parent
    if not path.is_dir() or not (checkpoint / "COMPLETE").is_file() or not (checkpoint / "state.json").is_file():
        raise ValueError("adapter requires a complete saved EGRS checkpoint with sibling state.json and COMPLETE")
    raw = (checkpoint / "state.json").read_bytes()
    state = json.loads(raw)
    saved = state.get("config", {})
    keys = ("model_id", "revision", "processor_id", "processor_revision", "role_supervision", "use_history")
    for key in keys:
        if key not in saved or saved[key] != config[key]:
            raise ValueError("checkpoint identity mismatch: " + key)
    for filename, expected in state.get("adapter_files_sha256", {}).items():
        target = (path / filename).resolve()
        if not target.is_relative_to(path.resolve()) or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError("checkpoint adapter hash mismatch: " + filename)
    return {**{key: saved[key] for key in keys}, "epoch": state.get("epoch"), "global_step": state.get("global_step"), "state_sha256": hashlib.sha256(raw).hexdigest(), "data_fingerprints": state.get("data_fingerprints", {}), "adapter_files_sha256": state.get("adapter_files_sha256", {})}


def language_lora_targets(model):
    targets = [name for name, _ in model.named_modules() if re.search(r"(?:^|\.)language_model\.layers\.\d+\.self_attn\.(?:q_proj|k_proj|v_proj|o_proj)$", name)]
    # Transformers 4.51 Qwen2.5-VL uses model.layers for its language decoder.
    if not targets:
        targets = [name for name, _ in model.named_modules() if re.fullmatch(r"model\.layers\.\d+\.self_attn\.(?:q_proj|k_proj|v_proj|o_proj)", name)]
    if not targets or any("visual" in name for name in targets):
        raise ValueError("could not identify language-only q/k/v/o projection modules")
    layers = {}
    for name in targets:
        layer, projection = name.rsplit(".", 1)
        layers.setdefault(layer, set()).add(projection)
    if any(projections != {"q_proj", "k_proj", "v_proj", "o_proj"} for projections in layers.values()):
        raise ValueError("language attention requires all four q/k/v/o projections")
    return targets


def assert_language_lora_only(model):
    names = []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            if "lora_" not in name or "visual" in name or not any(f".{p}." in name for p in ("q_proj", "k_proj", "v_proj", "o_proj")):
                raise ValueError("non-language-LoRA parameter is trainable: " + name)
            names.append({"name": name, "parameters": parameter.numel()})
    if not names:
        raise ValueError("no trainable language LoRA parameters")
    return names


def load_model(config, *, training=False, adapter=None):
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration
    dtype = {"bfloat16": torch.bfloat16, "float32": torch.float32, "float16": torch.float16}[config["dtype"]]
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(config["model_id"], revision=config["revision"], torch_dtype=dtype, trust_remote_code=False)
    model.requires_grad_(False)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter), is_trainable=training)
    elif training:
        from peft import LoraConfig, get_peft_model
        targets = language_lora_targets(model)
        model = get_peft_model(model, LoraConfig(r=config["lora_r"], lora_alpha=config["lora_alpha"], target_modules=targets, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
    if training:
        assert_language_lora_only(model)
        model.config.use_cache = False
        model.train()
    else:
        model.eval()
    return model.to(config["device"])
