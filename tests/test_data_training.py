import copy
import json
import subprocess
import sys

import pytest


def example():
    registry = {"instruction": "put bowl in drawer", "goals": [{"goal_ref": "g0", "source_text": "put bowl in drawer", "actor_text": "put bowl in drawer", "target": "bowl", "destination": "drawer", "kind": "transport"}]}
    payload = {"sensor": [{"query_id": 1, "snapshot_id": "q1", "observation": {"agentview_image": "frame.png", "robot0_eye_in_hand_image": "wrist.png"}}], "context": {"query_id": 1, "instruction": registry["instruction"], "registry": registry, "history": [], "commands": []}}
    evidence = {"goal_ref": "g0", "entity_ref": "bowl1", "query_id": 1, "snapshot_id": "q1", "camera": "agentview", "bbox": [.1, .1, .7, .7], "coordinate_system": "normalized_xyxy", "supports": ["entity", "role", "relation", "release", "interaction"]}
    answer = {"query_id": 1, "goals": [{"goal_ref": "g0", "entity_ref": "bowl1", "association": "MATCHED", "role": "TARGET", "relation": "SAT", "release": "RELEASED", "interaction": "NOT_HELD", "evidence": [evidence]}]}
    return {"sample_id": "s0", "source_id": "source0", "window_id": "w0", "payload": payload, "answer": answer, "provenance": {"/goals/0/relation": "human"}}


def test_missing_annotations_report_gaps_and_physical_truth_stays_offline(tmp_path):
    from egrs.data import export_annotations, import_annotations, build_dataset
    sample = example()
    sample.pop("answer")
    sample.pop("provenance")
    sample["physical_truth"] = {"relation": "secret"}
    package = export_annotations([sample])
    assert package["samples"][0]["answer"] is None
    report = build_dataset([sample], tmp_path / "missing", attestation={"six_composites_excluded": True, "semantic_equivalents_excluded": True, "eval_sources_excluded": True})
    assert report["ready"] is False
    assert report["counts"] == {"sources": 1, "windows": 1, "queries": 1}
    assert report["gaps"]
    package["samples"][0].update(answer=example()["answer"], provenance=example()["provenance"])
    imported = import_annotations([sample], package)
    report = build_dataset(imported, tmp_path / "labeled", attestation={"six_composites_excluded": True, "semantic_equivalents_excluded": True, "eval_sources_excluded": True})
    content = (tmp_path / "labeled" / "train.jsonl").read_text() + (tmp_path / "labeled" / "dev.jsonl").read_text()
    assert "secret" not in content and "physical_truth" not in content


def test_transitive_source_aliases_never_cross_splits_and_attestation_required(tmp_path):
    from egrs.data import grouped_split, build_dataset
    records = [dict(example(), sample_id=f"s{i}", source_id=f"src{i}", group_ids=g) for i, g in enumerate([["a"], ["a", "b"], ["b"], ["c"], ["d"]])]
    split = grouped_split(records, seed=4)
    assert len({split[f"s{i}"] for i in range(3)}) == 1
    assert split == grouped_split(list(reversed(records)), seed=4)
    with pytest.raises(ValueError, match="exclusion"):
        build_dataset(records, tmp_path, attestation={})


def test_unconfirmed_values_neutralized_human_unknown_preserved_and_role_ablation():
    from egrs.selector.supervision import prepare_answer
    sample = example()
    sample["answer"]["goals"][0]["relation"] = "UNKNOWN"
    sample["provenance"]["/goals/0/release"] = "weak"
    answer, supervised = prepare_answer(sample["answer"], sample["provenance"])
    assert answer["goals"][0]["relation"] == "UNKNOWN"
    assert "/goals/0/relation" in supervised
    assert answer["goals"][0]["release"] == "UNKNOWN"
    assert "/goals/0/release" not in supervised
    sample["provenance"]["/goals/0"] = "human"
    answer, supervised = prepare_answer(sample["answer"], sample["provenance"], role_supervision=False)
    assert answer["goals"][0]["entity_ref"] is None
    assert answer["goals"][0]["role"] == "UNKNOWN"
    assert not any(p.endswith(("/entity_ref", "/role", "/association")) for p in supervised)


class FakeTokenizer:
    pad_token_id = 0
    def __call__(self, text, **kwargs):
        return {"input_ids": [ord(c) + 1 for c in text], "offset_mapping": [(i, i + 1) for i in range(len(text))]}


class FakeProcessor:
    tokenizer = FakeTokenizer()
    image_token = "<image>"
    class ImageProcessor:
        merge_size = 2
    image_processor = ImageProcessor()
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        text = ""
        for message in messages:
            text += message["role"] + ":"
            content = message["content"]
            text += content if isinstance(content, str) else "".join("<image>" if c["type"] == "image" else c["text"] for c in content)
            text += "\n"
        return text + ("assistant:" if add_generation_prompt else "")
    def __call__(self, text, images=None, return_tensors=None, **kwargs):
        import torch
        expanded = text[0].replace("<image>", "<image>" * 2)
        result = {"input_ids": torch.tensor([[ord(c) + 1 for c in expanded]]), "attention_mask": torch.ones(1, len(expanded), dtype=torch.long)}
        if images:
            result["image_grid_thw"] = torch.tensor([[1, 2, 4]] * len(images))
        return result


def test_masks_align_after_chat_template_and_image_expansion(tmp_path):
    from egrs.selector.encoding import encode_sample
    from PIL import Image
    sample = example()
    for key in sample["payload"]["sensor"][0]["observation"]:
        filename = tmp_path / (key + ".png")
        Image.new("RGB", (8, 8)).save(filename)
        sample["payload"]["sensor"][0]["observation"][key] = str(filename)
    encoded = encode_sample(sample, FakeProcessor(), max_length=20000)
    labels = encoded["labels"][0].tolist()
    text = "".join(chr(i - 1) for i in encoded["input_ids"][0].tolist())
    learned = "".join(chr(i - 1) for i in labels if i != -100)
    assert learned == '"SAT"'
    assert '"release":"UNKNOWN"' in text
    assistant = text.split("assistant:")[-1]
    assert "RELEASED" not in assistant and "bowl1" not in assistant
    assert len(labels) == encoded["input_ids"].shape[1]
    with pytest.raises(ValueError, match="length"):
        encode_sample(sample, FakeProcessor(), max_length=20)


def test_no_history_removes_images_and_text_and_oldest_budget_drop():
    from egrs.selector.prompt import bounded_payload, build_messages
    sample = example()
    payload = sample["payload"]
    current = payload["sensor"][0]
    payload["sensor"] = [dict(copy.deepcopy(current), query_id=i, snapshot_id=f"q{i}") for i in range(4)]
    payload["context"]["query_id"] = 3
    payload["context"]["history"] = [{"query_id": 0, "note": "old-evidence"}]
    bounded, dropped = bounded_payload(payload)
    assert [s["query_id"] for s in bounded["sensor"]] == [1, 2, 3]
    assert dropped == [0]
    bounded, _ = bounded_payload(payload, use_history=False)
    assert len(bounded["sensor"]) == 1 and not bounded["context"]["history"]
    assert "old-evidence" not in json.dumps(build_messages(bounded))


def test_training_help_and_dry_run_do_not_import_optional_models(tmp_path):
    result = subprocess.run([sys.executable, "-m", "egrs.selector.train", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([sys.executable, "-m", "egrs.selector.train", "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["model_loaded"] is False


def test_optimizer_adapter_gradient_checkpoint_resume(tmp_path):
    import torch
    from egrs.selector.training import optimize_batches, save_checkpoint, load_checkpoint
    class Toy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.base = torch.nn.Linear(2, 2)
            self.base.requires_grad_(False)
            self.lora_A = torch.nn.Parameter(torch.ones(1, 2) * .1)
            self.lora_B = torch.nn.Parameter(torch.zeros(2, 1))
        def forward(self, input_ids, labels):
            value = self.base(input_ids.float()) + input_ids.float() @ self.lora_A.T @ self.lora_B.T
            return type("Output", (), {"loss": (value - labels.float()).square().mean()})()
    model = Toy()
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=.1)
    before = model.base.weight.detach().clone()
    batches = [{"input_ids": torch.ones(1, 2), "labels": torch.zeros(1, 2)}] * 2
    result = optimize_batches(model, batches, optimizer, accumulation=2)
    assert result["optimizer_steps"] == 1
    assert torch.equal(before, model.base.weight)
    assert model.lora_B.abs().sum() > 0
    save_checkpoint(tmp_path / "cp", model, optimizer, {"epoch": 1, "global_step": 1})
    restored = Toy()
    restored_optimizer = torch.optim.AdamW([p for p in restored.parameters() if p.requires_grad], lr=.1)
    state = load_checkpoint(tmp_path / "cp", restored, restored_optimizer)
    assert state["epoch"] == 1
    assert torch.equal(model.lora_B, restored.lora_B)


def test_final_id_mismatch_is_rejected_and_image_aliases_are_images(tmp_path):
    import numpy as np
    from egrs.selector.encoding import encode_sample
    sample = example()
    sample["payload"]["sensor"][0]["observation"] = {"images": {"agentview": np.zeros((2, 2, 3), dtype=np.uint8), "wrist": np.zeros((2, 2, 3), dtype=np.uint8)}}
    encoded = encode_sample(sample, FakeProcessor(), max_length=20000)
    text = "".join(chr(i - 1) for i in encoded["input_ids"][0].tolist())
    assert text.count("<image>") == 4
    class Broken(FakeProcessor):
        def __call__(self, **kwargs):
            value = super().__call__(**kwargs)
            value["input_ids"][0, 0] += 1
            return value
    with pytest.raises(ValueError, match="alignment"):
        encode_sample(sample, Broken(), max_length=20000)


def test_partial_evidence_weak_values_do_not_leak_and_unknown_provenance_rejected():
    from egrs.selector.supervision import prepare_answer
    sample = example()
    sample["provenance"] = {"/goals/0": "human", "/goals/0/evidence/0/entity_ref": "weak"}
    answer, fields = prepare_answer(sample["answer"], sample["provenance"])
    assert answer["goals"][0]["evidence"] == []
    with pytest.raises(ValueError, match="provenance"):
        prepare_answer(sample["answer"], {"/goals/0/relation": "teacher"})


def test_language_lora_selection_excludes_vision_and_requires_all_four_projections():
    import torch
    from egrs.selector.model import language_lora_targets
    class Named:
        def named_modules(self):
            return [("visual.blocks.0.attn.q_proj", None), ("model.layers.0.self_attn.q_proj", None)]
    with pytest.raises(ValueError, match="projection"):
        language_lora_targets(Named())


def test_extract_reads_stored_pixels_and_rejects_missing_views(tmp_path):
    import h5py
    import numpy as np
    from PIL import Image
    from egrs.data import extract_existing_images
    filename = tmp_path / "synthetic.hdf5"
    with h5py.File(filename, "w") as f:
        obs = f.create_group("data/demo_0/obs")
        obs["agentview_rgb"] = np.full((2, 3, 4, 3), 71, dtype=np.uint8)
        obs["eye_in_hand_rgb"] = np.full((2, 3, 4, 3), 42, dtype=np.uint8)
    result = extract_existing_images(filename, tmp_path / "images", episode="demo_0", frames=[1])
    assert np.asarray(Image.open(result[0]["observation"]["agentview_image"]))[0, 0, 0] == 71
    with h5py.File(filename, "a") as f:
        del f["data/demo_0/obs/eye_in_hand_rgb"]
    with pytest.raises(ValueError, match="no rendering"):
        extract_existing_images(filename, tmp_path / "bad", episode="demo_0", frames=[0])


def test_split_is_task_stratified_and_build_preserves_aliases(tmp_path):
    from egrs.data import grouped_split, build_dataset
    records = [dict(example(), sample_id=f"s{i}", source_id=f"src{i}", group_ids=[f"alias{i}"], task_group="goal", ancestry_known=True) for i in range(10)]
    split = grouped_split(records, seed=0)
    assert list(split.values()).count("dev") == 2
    report = build_dataset(records, tmp_path / "dataset", attestation={"six_composites_excluded": True, "semantic_equivalents_excluded": True, "eval_sources_excluded": True})
    assert report["ready"] is True
    row = json.loads((tmp_path / "dataset/train.jsonl").read_text().splitlines()[0])
    assert row["group_ids"] and row["task_group"] == "goal"
    assert report["unsupervised_fields"] > 0


def test_oracle_training_history_requires_visible_prediction_provenance():
    from egrs.data import validate_sample
    sample = example()
    sample["payload"]["context"]["history"] = [{"query_id": 1, "goals": []}]
    with pytest.raises(ValueError, match="history provenance"):
        validate_sample(sample)


def test_actual_training_entry_runs_dev_save_and_resume_with_cpu_toy(tmp_path, monkeypatch):
    import torch
    from PIL import Image
    from egrs.data import build_dataset
    from egrs.selector.train import main
    import egrs.selector.model as loading
    class Toy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.base = torch.nn.Parameter(torch.tensor(.5), requires_grad=False)
            self.model = torch.nn.Module()
            self.model.q_proj = torch.nn.Module()
            self.model.q_proj.lora_A = torch.nn.Parameter(torch.tensor(.1))
            self.model.q_proj.lora_B = torch.nn.Parameter(torch.tensor(0.0))
        def forward(self, input_ids, labels, **kwargs):
            value = self.base + self.model.q_proj.lora_A * self.model.q_proj.lora_B * input_ids.float().mean()
            return type("Output", (), {"loss": (value - labels[labels != -100].float().mean()).square()})()
        def save_pretrained(self, path, **kwargs):
            path.mkdir()
            (path / "adapter_config.json").write_text('{}')
    class Processor(FakeProcessor):
        def save_pretrained(self, path):
            path.mkdir()
            (path / "processor_config.json").write_text('{}')
    monkeypatch.setattr(loading, "load_processor", lambda config: Processor())
    monkeypatch.setattr(loading, "load_model", lambda config, **kwargs: Toy())
    image = tmp_path / "frame.png"
    Image.new("RGB", (2, 2)).save(image)
    records = []
    for i in range(5):
        sample = example()
        sample.update(sample_id=f"s{i}", source_id=f"src{i}", task_group="goal")
        sample["payload"]["sensor"][0]["observation"] = {"agentview_image": str(image), "robot0_eye_in_hand_image": str(image)}
        records.append(sample)
    dataset = tmp_path / "data"
    build_dataset(records, dataset, attestation={"six_composites_excluded": True, "semantic_equivalents_excluded": True, "eval_sources_excluded": True})
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"device": "cpu", "dtype": "float32", "role_supervision": False}))
    args = ["--config", str(config), "--train", str(dataset / "train.jsonl"), "--dev", str(dataset / "dev.jsonl")]
    assert main(args + ["--output", str(tmp_path / "run")]) == 0
    state = json.loads((tmp_path / "run/checkpoint-1/state.json").read_text())
    assert state["config"]["role_supervision"] is False
    assert main(args + ["--resume", str(tmp_path / "run/checkpoint-1"), "--output", str(tmp_path / "resumed")]) == 0
    result = json.loads((tmp_path / "resumed/status.json").read_text())
    assert result["status"] == "complete" and result["epoch"] == 3
    assert result["global_step"] == 3
    assert len((tmp_path / "resumed/epochs.jsonl").read_text().splitlines()) == 2


def test_selector_api_validates_generated_wire_and_has_lazy_lifecycle():
    import numpy as np
    from egrs.selector import QwenSelector
    selector = QwenSelector({"device": "cpu"})
    assert selector.metadata["model_loaded"] is False
    sample = example()
    generated = iter([sample["payload"]["context"]["registry"], sample["answer"], {"query_id": 1, "goals": []}])
    selector._generate = lambda messages, images: next(generated)
    assert selector.registry("put bowl in drawer")["goals"][0]["goal_ref"] == "g0"
    sample["payload"]["sensor"][0]["observation"] = {"image": np.zeros((2, 2, 3), dtype=np.uint8), "wrist_image": np.zeros((2, 2, 3), dtype=np.uint8)}
    assert selector.predict(sample["payload"])["goals"][0]["relation"] == "SAT"
    with pytest.raises(ValueError, match="goal"):
        selector.predict(sample["payload"])
    selector.close()
    with pytest.raises(RuntimeError, match="closed"):
        selector.reset()


def test_inference_cli_help_and_dry_run_are_model_free(tmp_path):
    path = tmp_path / "instruction.json"
    path.write_text(json.dumps({"instruction": "put bowl in drawer"}))
    result = subprocess.run([sys.executable, "-m", "egrs.selector.infer", "--mode", "registry", "--input", str(path), "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["model_loaded"] is False


def test_encoding_audit_counts_final_tokens_and_dropped_images(tmp_path):
    from PIL import Image
    from egrs.selector.encoding import encode_sample
    sample = example()
    path = tmp_path / "frame.png"
    Image.new("RGB", (2, 2)).save(path)
    current = sample["payload"]["sensor"][0]
    current["observation"] = {"agentview_image": str(path), "robot0_eye_in_hand_image": str(path)}
    sample["payload"]["sensor"] = [dict(copy.deepcopy(current), query_id=i, snapshot_id=f"q{i}") for i in range(1, 5)]
    sample["payload"]["context"]["query_id"] = 4
    sample["answer"]["query_id"] = 4
    audit = {}
    encoded = encode_sample(sample, FakeProcessor(), max_length=20000, audit=audit)
    assert audit["dropped_snapshot_queries"] == [1]
    assert audit["image_count"] == 6 and audit["visual_tokens"] == 12
    assert audit["supervised_tokens"] == 5
    assert audit["final_tokens"] == encoded["input_ids"].shape[1]


def test_training_rejects_cross_split_known_aliases_before_model_loading(tmp_path):
    from egrs.selector.train import main
    paths = []
    for name in ("train", "dev"):
        sample = example()
        sample.update(source_id=name, sample_id=name, group_ids=["same-initial-state"])
        path = tmp_path / (name + ".jsonl")
        path.write_text(json.dumps(sample) + "\n")
        paths.append(str(path))
    with pytest.raises(ValueError, match="group"):
        main(["--train", paths[0], "--dev", paths[1], "--output", str(tmp_path / "run")])


def test_answer_evidence_cannot_reference_history_removed_for_budget(tmp_path):
    from PIL import Image
    from egrs.selector.encoding import encode_sample
    sample = example()
    sample["provenance"] = {"": "human"}
    path = tmp_path / "frame.png"
    Image.new("RGB", (2, 2)).save(path)
    sample["payload"]["sensor"][0]["observation"] = {"agentview_image": str(path), "robot0_eye_in_hand_image": str(path)}
    old = sample["payload"]["sensor"][0]
    sample["payload"]["sensor"] = [dict(copy.deepcopy(old), query_id=i, snapshot_id=f"q{i}") for i in range(1, 5)]
    sample["payload"]["context"]["query_id"] = 4
    sample["answer"]["query_id"] = 4
    with pytest.raises(ValueError, match="answer evidence"):
        encode_sample(sample, FakeProcessor(), max_length=20000)


def test_runtime_history_config_alias_removes_selector_history_setting():
    from egrs.selector import QwenSelector
    selector = QwenSelector({"history": False, "lora_path": None})
    assert selector.config["use_history"] is False
    assert selector.config["adapter"] is None


def test_checkpoint_identity_guard_rejects_mismatch_before_loading(tmp_path):
    from egrs.selector import QwenSelector
    from egrs.selector.model import resolve_config
    checkpoint = tmp_path / "checkpoint-1"
    adapter = checkpoint / "adapter"
    adapter.mkdir(parents=True)
    config = resolve_config({"role_supervision": False, "use_history": False})
    state = {"config": config, "epoch": 1, "global_step": 3}
    (checkpoint / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError, match="complete"):
        QwenSelector({"adapter": str(adapter)})
    (checkpoint / "COMPLETE").write_text("complete")
    with pytest.raises(ValueError, match="role_supervision"):
        QwenSelector({"adapter": str(adapter)})
    with pytest.raises(ValueError, match="use_history"):
        QwenSelector({"adapter": str(adapter), "role_supervision": False})
    selector = QwenSelector({"adapter": str(adapter), "role_supervision": False, "use_history": False})
    assert selector.metadata["checkpoint_identity"]["epoch"] == 1
    assert selector.metadata["checkpoint_identity"]["role_supervision"] is False
    assert selector.metadata["model_loaded"] is False
    state["config"]["processor_revision"] = "different"
    (checkpoint / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError, match="processor_revision"):
        QwenSelector({"adapter": str(adapter), "role_supervision": False, "use_history": False})


def three_snapshot_request():
    import numpy as np
    sample = example()
    current = sample["payload"]["sensor"][0]
    current["observation"] = {"image": np.zeros((2, 2, 3), dtype=np.uint8), "wrist_image": np.zeros((2, 2, 3), dtype=np.uint8)}
    sample["payload"]["sensor"] = [dict(copy.deepcopy(current), query_id=i, snapshot_id=f"q{i}") for i in range(1, 4)]
    sample["payload"]["context"]["query_id"] = 3
    sample["answer"]["query_id"] = 3
    sample["answer"]["goals"][0]["evidence"][0].update(query_id=3, snapshot_id="q3")
    return sample


def test_selector_input_audit_reports_actual_image_limit_trimming_and_no_stale_registry():
    from egrs.selector import QwenSelector
    sample = three_snapshot_request()
    selector = QwenSelector({"device": "cpu", "max_images": 2})
    selector._generate = lambda messages, images: sample["answer"]
    selector.predict(sample["payload"])
    assert selector.last_input_audit == {"supplied_snapshot_ids": ["q1", "q2", "q3"], "snapshot_ids": ["q3"], "dropped_snapshot_ids": ["q1", "q2"], "image_count": 2, "final_prompt_tokens": None, "generated_tokens": None}
    audit = selector.last_input_audit
    audit["snapshot_ids"].clear()
    assert selector.last_input_audit["snapshot_ids"] == ["q3"]
    selector._generate = lambda messages, images: sample["payload"]["context"]["registry"]
    selector.registry("put bowl in drawer")
    assert selector.last_input_audit == {"supplied_snapshot_ids": [], "snapshot_ids": [], "dropped_snapshot_ids": [], "image_count": 0, "final_prompt_tokens": None, "generated_tokens": None}


def test_selector_input_audit_captures_length_trimming_and_failed_attempt():
    from egrs.selector import QwenSelector
    sample = three_snapshot_request()
    selector = QwenSelector({"device": "cpu"})
    def generated(messages, images):
        if len(images) > 4:
            raise ValueError("total length exceeds budget")
        return sample["answer"]
    selector._generate = generated
    selector.predict(sample["payload"])
    assert selector.last_input_audit["snapshot_ids"] == ["q2", "q3"]
    assert selector.last_input_audit["dropped_snapshot_ids"] == ["q1"]
    assert selector.last_input_audit["image_count"] == 4
    def failed(messages, images):
        raise ValueError("total length exceeds budget")
    selector._generate = failed
    with pytest.raises(ValueError, match="length"):
        selector.predict(sample["payload"])
    assert selector.last_input_audit["snapshot_ids"] == ["q3"]
    assert selector.last_input_audit["image_count"] is None
    assert selector.last_input_audit["final_prompt_tokens"] is None


def test_actual_generation_audit_retains_known_tokens_on_invalid_json(monkeypatch):
    import torch
    from egrs.selector import QwenSelector
    import egrs.selector.encoding as encoding
    selector = QwenSelector({"device": "cpu"})
    class Tokenizer:
        def decode(self, tokens, **kwargs):
            return "invalid JSON"
    selector._processor = type("Processor", (), {"tokenizer": Tokenizer()})()
    class Model:
        def generate(self, **kwargs):
            return torch.tensor([[1, 2, 3, 4, 5, 6, 7]])
    selector._model = Model()
    monkeypatch.setattr(encoding, "encode_messages", lambda *a, **kw: ({"input_ids": torch.tensor([[1, 2, 3, 4]])}, "", []))
    with pytest.raises(ValueError, match="invalid JSON"):
        selector.registry("put bowl in drawer")
    assert selector.last_input_audit["final_prompt_tokens"] == 4
    assert selector.last_input_audit["generated_tokens"] == 3
    assert selector.last_input_audit["image_count"] == 0
