"""User-started selector LoRA training. --help/--dry-run never load models."""
import argparse
import hashlib
import json
from pathlib import Path

from .model import resolve_config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="selector JSON config")
    parser.add_argument("--core-config", help="optional pinned eval core dependency JSON; activated only for actual training")
    parser.add_argument("--train", help="built train.jsonl")
    parser.add_argument("--dev", help="built dev.jsonl")
    parser.add_argument("--output", help="new output directory")
    parser.add_argument("--resume", help="complete trusted epoch checkpoint; output must be new")
    parser.add_argument("--dry-run", action="store_true", help="validate files/config, never import torch or load a model")
    args = parser.parse_args(argv)
    config = resolve_config(json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {})
    records = {}
    for name in ("train", "dev"):
        filename = getattr(args, name)
        if filename:
            from egrs.data import load_records, validate_sample
            records[name] = [validate_sample(r) for r in load_records(filename)]
    if records.get("train") and records.get("dev"):
        sources = [{r["source_id"] for r in records[name]} for name in ("train", "dev")]
        groups = [{g for r in records[name] for g in r.get("group_ids", [])} for name in ("train", "dev")]
        if sources[0] & sources[1]:
            raise ValueError("source leakage across train/dev")
        if groups[0] & groups[1]:
            raise ValueError("known group leakage across train/dev")
    if args.dry_run:
        print(json.dumps({"model_loaded": False, "config": config, "queries": {k: len(v) for k, v in records.items()}, "ready": bool(records.get("train") and records.get("dev")), "gaps": [name for name in ("train", "dev", "output") if not getattr(args, name)]}, indent=2))
        return 0
    if not all(getattr(args, name) for name in ("train", "dev", "output")):
        parser.error("actual training requires --train --dev --output")
    if not records["train"] or not records["dev"]:
        raise ValueError("train and dev require confirmed labels; empty split is not ready")
    if args.core_config:
        from egrs.core import activate
        activate(json.loads(Path(args.core_config).read_text(encoding="utf-8")))
    fingerprints = {name: hashlib.sha256(Path(getattr(args, name)).read_bytes()).hexdigest() for name in ("train", "dev")}
    import random
    import torch
    import numpy as np
    from .model import load_model, load_processor, assert_language_lora_only
    from .encoding import encode_sample
    from .training import optimize_batches, evaluate_batches, save_checkpoint, load_checkpoint
    random.seed(config["seed"])
    np.random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    if args.resume:
        prior = json.loads((Path(args.resume) / "state.json").read_text())
        if prior["config"] != config or prior["data_fingerprints"] != fingerprints:
            raise ValueError("resume config or data differs from checkpoint")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "status.json").write_text(json.dumps({"status": "partial", "config": config}), encoding="utf-8")
    try:
        processor = load_processor(config)
        model = load_model(config, training=True, adapter=Path(args.resume) / "adapter" if args.resume else None)
        trainable = assert_language_lora_only(model)
        (output / "trainable_parameters.json").write_text(json.dumps(trainable, indent=2), encoding="utf-8")
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=config["learning_rate"])
        state = {"epoch": 0, "global_step": 0}
        if args.resume:
            state = load_checkpoint(args.resume, model, optimizer)
        def batches(name, epoch):
            order = list(range(len(records[name])))
            if name == "train":
                random.Random(config["seed"] + epoch).shuffle(order)
            for index in order:
                sample = records[name][index]
                try:
                    audit = {"sample_id": sample["sample_id"], "split": name, "epoch": epoch + 1}
                    batch = encode_sample(sample, processor, max_length=config["max_length"], max_visual_tokens=config["max_visual_tokens"], max_images=config["max_images"], max_answer_tokens=config["max_new_tokens"], use_history=config["use_history"], role_supervision=config["role_supervision"], audit=audit)
                    with (output / "encoding.jsonl").open("a", encoding="utf-8") as encoded_log:
                        encoded_log.write(json.dumps(audit) + "\n")
                    yield batch
                except Exception as exc:
                    raise ValueError(f"{name} sample {sample['sample_id']} rejected; no replacement: {exc}") from exc
        with (output / "epochs.jsonl").open("x", encoding="utf-8") as log:
            for epoch in range(state["epoch"], config["epochs"]):
                train = optimize_batches(model, batches("train", epoch), optimizer, accumulation=config["global_batch_size"], device=config["device"])
                dev = evaluate_batches(model, batches("dev", epoch), device=config["device"])
                state = {"epoch": epoch + 1, "global_step": state["global_step"] + train["optimizer_steps"], "config": config, "data_fingerprints": fingerprints}
                log.write(json.dumps({"epoch": epoch + 1, "train": train, "dev": dev}) + "\n")
                log.flush()
                save_checkpoint(output / f"checkpoint-{epoch + 1}", model, optimizer, state, processor=processor)
        (output / "status.json").write_text(json.dumps({"status": "complete", **state}), encoding="utf-8")
    except BaseException as exc:
        (output / "status.json").write_text(json.dumps({"status": "partial", "error": str(exc), "config": config}), encoding="utf-8")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
