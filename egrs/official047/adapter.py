"""A versioned cross-suite restore; old043/045 identity/restore stay unchanged."""
from types import SimpleNamespace

from .contracts import require, statistic_sha, expected_key


def attach_h1(model, action_head, proprio_projector, identity, directory, cfg):
    import torch
    from egrs.hint043.adapter import install, state, tensor_sha, validate

    validate(identity)
    lineage = identity["base_lineage"]
    require(statistic_sha(model.norm_stats[lineage["unnorm_key"]])
            == lineage["normalization_statistics_sha256"], "047 loaded training statistics differ")
    require(cfg.unnorm_key == expected_key(cfg.task_suite_name, model.norm_stats),
            "047 native inference normalization does not match the evaluated suite")
    policy = SimpleNamespace(model=model, action_head=action_head, proprio_projector=proprio_projector)
    # Original weights already include the published LoRA. Only our rank16 is new.
    # Restore RNG around temporary A initialization, not around a model forward.
    devices = sorted({p.device.index for p in model.parameters() if p.device.type == "cuda"})
    with torch.random.fork_rng(devices=devices):
        targets = install(policy)
    require(targets == identity["target_modules"], "047 LoRA target inventory differs")
    from pathlib import Path
    from .contracts import sha
    require(sha(Path(directory)/"adapter.pt") == identity["adapter_sha256"], "047 H1 bytes changed")
    tensors = torch.load(Path(directory)/"adapter.pt", map_location="cpu", weights_only=True)
    parameters = dict(model.named_parameters())
    require(set(tensors) == set(identity["trainable_parameters"]) == set(state(policy)),
            "047 LoRA tensor inventory differs")
    for name, tensor in tensors.items():
        require(list(tensor.shape) == identity["trainable_parameters"][name] == list(parameters[name].shape)
                and str(tensor.dtype) == identity["tensor_dtypes"][name]
                and tensor_sha(tensor) == identity["tensor_sha256"][name]
                and torch.isfinite(tensor).all().item(), "047 invalid tensor: " + name)
    with torch.no_grad():
        for name, tensor in tensors.items():
            parameters[name].copy_(tensor)
    for module in (model, action_head, proprio_projector):
        module.requires_grad_(False)
        module.eval()
    return identity
