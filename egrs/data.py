"""Offline local-image manifests and external annotation workflow; no simulation."""
import copy
import hashlib
import json
from pathlib import Path

ATTESTATION_KEYS = ("six_composites_excluded", "semantic_equivalents_excluded", "eval_sources_excluded")
SAMPLE_KEYS = {"sample_id", "source_id", "window_id", "payload", "answer", "provenance", "physical_truth", "group_ids", "task_group", "ancestry_known", "history_provenance"}


def load_records(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    value = json.loads(text) if path.suffix == ".json" else [json.loads(line) for line in text.splitlines() if line.strip()]
    records = value["samples"] if isinstance(value, dict) else value
    if not isinstance(records, list):
        raise ValueError("manifest must be an array or JSONL records")
    return records


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def validate_sample(sample):
    from egrs.selector.supervision import PROVENANCE, source_for
    if set(sample) - SAMPLE_KEYS:
        raise ValueError("unknown manifest fields: " + str(sorted(set(sample) - SAMPLE_KEYS)))
    for name in ("sample_id", "source_id", "window_id"):
        if not isinstance(sample.get(name), str) or not sample[name]:
            raise ValueError(f"{name} must be a nonempty string")
    if not isinstance(sample.get("payload"), dict):
        raise ValueError("payload is required")
    if "physical_truth" in json.dumps(sample["payload"]):
        raise ValueError("physical_truth forbidden in payload")
    history = sample["payload"].get("context", {}).get("history", [])
    hp = sample.get("history_provenance", {})
    if any(hp.get(str(h.get("query_id"))) not in {"human_visual", "reviewed_candidate", "model_prediction"} for h in history):
        raise ValueError("history provenance must attest visible evidence or past model predictions; no oracle history")
    if any(not isinstance(x, str) or not x for x in sample.get("group_ids", [])):
        raise ValueError("group_ids must contain nonempty string aliases")
    provenance = sample.get("provenance", {})
    for pointer, source in provenance.items():
        if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")) or source not in PROVENANCE:
            raise ValueError("invalid JSON pointer provenance")
        node = sample.get("answer")
        try:
            for part in pointer.split("/")[1:] if pointer else []:
                part = part.replace("~1", "/").replace("~0", "~")
                node = node[int(part)] if isinstance(node, list) else node[part]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("provenance pointer does not exist: " + pointer) from exc
    if sample.get("answer") is not None:
        from egrs.contracts import validate_prediction, validate_registry
        context = sample["payload"]["context"]
        registry = validate_registry(context["registry"], context["instruction"])
        validate_prediction(sample["answer"], registry, context["query_id"], sample["payload"]["sensor"])
    return sample


def export_annotations(records):
    seen = set()
    samples = []
    for record in records:
        validate_sample(record)
        if record["sample_id"] in seen:
            raise ValueError("duplicate sample_id")
        seen.add(record["sample_id"])
        item = copy.deepcopy(record)
        item.setdefault("answer", None)
        item.setdefault("provenance", {})
        samples.append(item)
    return {"format": "egrs.annotations.v1", "provenance_values": ["human", "reviewed_candidate", "weak"], "samples": samples}


def import_annotations(records, package):
    if package.get("format") != "egrs.annotations.v1":
        raise ValueError("unsupported annotation format")
    originals = {r["sample_id"]: r for r in records}
    if len(originals) != len(records):
        raise ValueError("duplicate sample_id")
    seen, merged = set(), []
    for annotation in package["samples"]:
        sid = annotation["sample_id"]
        if sid not in originals or sid in seen:
            raise ValueError("unknown or duplicate annotation sample_id")
        seen.add(sid)
        original = originals[sid]
        for field in ("source_id", "window_id", "payload", "group_ids", "task_group", "history_provenance"):
            if annotation.get(field) != original.get(field):
                raise ValueError("annotation changed immutable manifest field: " + field)
        item = copy.deepcopy(original)
        for field in ("answer", "provenance", "physical_truth"):
            if field in annotation:
                item[field] = copy.deepcopy(annotation[field])
        merged.append(validate_sample(item))
    if seen != set(originals):
        raise ValueError("annotation package missing samples; retain explicit null answers")
    return merged


def grouped_split(records, seed=0, dev_fraction=.2):
    if not 0 < dev_fraction < 1:
        raise ValueError("dev_fraction must be between zero and one")
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        ra, rb = find(a), find(b)
        parent[max(ra, rb)] = min(ra, rb)
    for r in records:
        source = "source:" + r["source_id"]
        find(source)
        for group in r.get("group_ids", []):
            union(source, "group:" + group)
    # Hashing the complete component membership prevents order-sensitive roots.
    components = {}
    for node in sorted(parent):
        components.setdefault(find(node), []).append(node)
    strata = {}
    for root, members in components.items():
        tasks = sorted({r.get("task_group", "unclassified") for r in records if find("source:" + r["source_id"]) == root})
        fingerprint = hashlib.sha256((str(seed) + "|" + "|".join(members)).encode()).hexdigest()
        strata.setdefault(tuple(tasks), []).append((fingerprint, root))
    assignment = {}
    for members in strata.values():
        members.sort()
        n = len(members)
        ndev = max(1, min(n - 1, round(n * dev_fraction))) if n > 1 else 0
        for i, (_, root) in enumerate(members):
            assignment[root] = "dev" if i < ndev else "train"
    return {r["sample_id"]: assignment[find("source:" + r["source_id"])] for r in records}


def build_dataset(records, output, *, attestation, seed=0, fixed_source_splits=None):
    from egrs.selector.supervision import prepare_answer
    if not all(attestation.get(key) is True for key in ATTESTATION_KEYS):
        raise ValueError("explicit six-composite, equivalent and eval-source exclusion attestation required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    records = [validate_sample(r) for r in records]
    if len({r["sample_id"] for r in records}) != len(records):
        raise ValueError("duplicate sample_id")
    if fixed_source_splits is None:
        split = grouped_split(records, seed)
    else:
        if not isinstance(fixed_source_splits, dict) or any(v not in {'train', 'dev'} for v in fixed_source_splits.values()):
            raise ValueError('fixed source splits must map source IDs to train/dev')
        split, aliases = {}, {}
        for record in records:
            source = record['source_id']
            if source not in fixed_source_splits:
                raise ValueError('source missing from fixed split: ' + source)
            part = fixed_source_splits[source]
            split[record['sample_id']] = part
            for group in record.get('group_ids', []):
                if group in aliases and aliases[group] != part:
                    raise ValueError('known alias crosses fixed source splits: ' + group)
                aliases[group] = part
    report = {"ready": False, "counts": {"sources": len({r['source_id'] for r in records}), "windows": len({(r['source_id'], r['window_id']) for r in records}), "queries": len(records)}, "splits": {"train": 0, "dev": 0}, "field_supervision": {}, "unsupervised_fields": 0, "gaps": [], "unknown_ancestry_sources": sorted({r["source_id"] for r in records if not r.get("ancestry_known", False)}), "exclusion_attestation": attestation, "seed": seed}
    outputs = {"train": [], "dev": []}
    for record in records:
        if record.get("answer") is None:
            report["gaps"].append({"sample_id": record["sample_id"], "reason": "missing annotation"})
            continue
        _, fields = prepare_answer(record["answer"], record.get("provenance", {}))
        from egrs.selector.supervision import serialize_with_spans
        _, all_fields = serialize_with_spans(record["answer"])
        report["unsupervised_fields"] += len(set(all_fields) - fields)
        if not fields:
            report["gaps"].append({"sample_id": record["sample_id"], "reason": "no confirmed supervised fields"})
            continue
        item = {key: copy.deepcopy(record[key]) for key in ("sample_id", "source_id", "window_id", "payload", "answer", "provenance")}
        for key in ("group_ids", "task_group", "ancestry_known", "history_provenance"):
            if key in record:
                item[key] = copy.deepcopy(record[key])
        outputs[split[record["sample_id"]]].append(item)
        report["splits"][split[record["sample_id"]]] += 1
        for field in fields:
            name = field.rsplit("/", 1)[-1]
            report["field_supervision"][name] = report["field_supervision"].get(name, 0) + 1
    for name, items in outputs.items():
        (output / (name + ".jsonl")).write_text("".join(json.dumps(x, ensure_ascii=False, allow_nan=False) + "\n" for x in items), encoding="utf-8")
        if not items:
            report["gaps"].append({"split": name, "reason": "no usable labeled queries"})
    report["ready"] = not report["gaps"] and bool(outputs["train"] and outputs["dev"])
    report["split_counts"] = {name: {"sources": len({r["source_id"] for r in items}), "windows": len({(r["source_id"], r["window_id"]) for r in items}), "queries": len(items)} for name, items in outputs.items()}
    write_json(output / "report.json", report)
    return report


def extract_existing_images(hdf5_path, output, *, episode, frames):
    """Read already stored official RGBs. Never restore states or render."""
    import h5py
    from PIL import Image
    import numpy as np
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = []
    with h5py.File(hdf5_path, "r") as file:
        obs = file[f"data/{episode}/obs"]
        for frame in frames:
            paths = {}
            for key in ("agentview_rgb", "eye_in_hand_rgb"):
                if key not in obs:
                    raise ValueError(f"stored image dataset missing: {key}; no rendering fallback")
                image = np.asarray(obs[key][frame])
                if image.ndim != 3 or image.shape[-1] != 3 or image.dtype != np.uint8:
                    raise ValueError("stored image must be uint8 HWC RGB")
                path = output / f"{episode}_{frame}_{key}.png"
                Image.fromarray(image).save(path)
                paths["agentview_image" if key == "agentview_rgb" else "robot0_eye_in_hand_image"] = str(path.resolve())
            result.append({"frame": frame, "observation": paths})
    write_json(output / "images.json", result)
    return result
