"""Actual optimizer/dev/checkpoint mechanics; no optional imports at module load."""
import json
import hashlib
import random
from pathlib import Path


def move_batch(batch, device):
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in batch.items()}


def optimize_batches(model, batches, optimizer, *, accumulation=16, device="cpu"):
    import torch
    if accumulation < 1:
        raise ValueError("accumulation must be positive")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    steps = count = pending = 0
    total = 0.0
    for batch in batches:
        loss = model(**move_batch(batch, device)).loss
        if not bool(torch.isfinite(loss)):
            raise ValueError("nonfinite training loss")
        (loss / accumulation).backward()
        total += float(loss.detach())
        count += 1
        pending += 1
        if pending == accumulation:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            pending = 0
            steps += 1
    if pending:
        for group in optimizer.param_groups:
            for parameter in group["params"]:
                if parameter.grad is not None:
                    parameter.grad.mul_(accumulation / pending)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        steps += 1
    if not count:
        raise ValueError("empty training split")
    return {"optimizer_steps": steps, "queries": count, "mean_loss": total / count}


def evaluate_batches(model, batches, *, device="cpu"):
    import torch
    model.eval()
    count, total, tokens = 0, 0.0, 0
    with torch.no_grad():
        for batch in batches:
            batch = move_batch(batch, device)
            loss = model(**batch).loss
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite dev loss")
            n = int((batch["labels"] != -100).sum())
            total += float(loss) * n
            tokens += n
            count += 1
    if not count or not tokens:
        raise ValueError("empty dev supervision")
    return {"queries": count, "supervised_tokens": tokens, "token_mean_loss": total / tokens}


def save_checkpoint(path, model, optimizer, state, *, processor=None):
    import torch
    import numpy as np
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    if hasattr(model, "save_pretrained"):
        model.save_pretrained(path / "adapter", safe_serialization=True)
    if processor is not None:
        processor.save_pretrained(path / "processor")
    parameters = {name: p.detach().cpu() for name, p in model.named_parameters() if p.requires_grad}
    torch.save({"parameters": parameters, "optimizer": optimizer.state_dict(), "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [], "python_rng": random.getstate(), "numpy_rng": np.random.get_state()}, path / "training.pt")
    state = dict(state)
    if (path / "adapter").is_dir():
        state["adapter_files_sha256"] = {file.relative_to(path / "adapter").as_posix(): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted((path / "adapter").rglob("*")) if file.is_file()}
    (path / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (path / "COMPLETE").write_text("checkpoint complete\n", encoding="utf-8")


def load_checkpoint(path, model, optimizer):
    import torch
    import numpy as np
    path = Path(path)
    if not (path / "COMPLETE").is_file():
        raise ValueError("incomplete checkpoint")
    # This is a local trusted checkpoint, never an untrusted annotation input.
    saved = torch.load(path / "training.pt", map_location="cpu", weights_only=False)
    parameters = dict(model.named_parameters())
    expected = {name for name, p in parameters.items() if p.requires_grad}
    if expected != set(saved["parameters"]):
        raise ValueError("checkpoint trainable parameters differ")
    with torch.no_grad():
        for name, value in saved["parameters"].items():
            parameters[name].copy_(value)
    optimizer.load_state_dict(saved["optimizer"])
    torch.set_rng_state(saved["torch_rng"])
    if saved["cuda_rng"]:
        torch.cuda.set_rng_state_all(saved["cuda_rng"])
    random.setstate(saved["python_rng"])
    np.random.set_state(saved["numpy_rng"])
    return json.loads((path / "state.json").read_text(encoding="utf-8"))
