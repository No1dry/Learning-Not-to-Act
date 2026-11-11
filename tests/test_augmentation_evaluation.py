import copy
import importlib
from pathlib import Path

import pytest


def test_fixed_populations_cannot_expand_control_or_omit_a_task():
    from egrs.augmentation.evaluation import select_population
    rows = [{"task_id": str(t), "initial_state_index": i, "episode_id": f"{t}_{i}"}
            for t in range(9) for i in range(10)]
    assert len(select_population(rows, "progress_aug")) == 90
    selected = select_population(rows, "raw_control")
    assert len(selected) == 36
    assert {r["initial_state_index"] for r in selected} == {0, 3, 6, 9}
    with pytest.raises(ValueError):
        select_population(rows, "choose-best")
    with pytest.raises(ValueError):
        select_population(rows[:-1], "progress_aug")


def test_policy_exposes_only_rgb_proprio_and_full_instruction(monkeypatch):
    import numpy as np
    from egrs.augmentation.evaluation import AdapterPolicy
    seen = []
    class Base:
        def predict(self, obs, instruction):
            seen.append((obs, instruction))
            return np.ones((8, 7))
        def reset(self): pass
        def close(self): pass
    policy = AdapterPolicy.__new__(AdapterPolicy)
    policy.base = Base()
    obs = {"images": {"agentview": np.zeros((2, 2, 3), dtype=np.uint8)},
           "proprio": [1, 2], "initial_mask": [True, False], "goals": [True, False],
           "future_frame": "forbidden", "contact": {"oracle": True}}
    result = policy.predict(obs, "full instruction")
    assert result.shape == (8, 7)
    assert set(seen[0][0]) == {"images", "proprio"}
    assert seen[0][1] == "full instruction"
    assert "initial_mask" in obs


def test_adapter_identity_mismatch_rejected_before_scoring():
    from egrs.augmentation.evaluation import check_method_identity
    identity = {"adapter_sha256": "a" * 64, "schema_version": "task030-oft-adapter-v1"}
    metadata = {"model_runtime": {"policy_metadata": {"method_adapter": copy.deepcopy(identity)}}}
    check_method_identity(metadata, identity)
    metadata["model_runtime"]["policy_metadata"]["method_adapter"]["adapter_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="adapter"):
        check_method_identity(metadata, identity)


def test_core_mismatch_is_rejected_before_import(tmp_path):
    from egrs.augmentation.dependencies import activate_core
    (tmp_path / "benchmark").mkdir()
    with pytest.raises(ValueError, match="core"):
        activate_core(tmp_path)


@pytest.fixture
def accepted_core(monkeypatch):
    import os
    from egrs.augmentation.dependencies import activate_core
    core = Path(os.environ.get("TASK030_TEST_CORE", Path(__file__).resolve().parents[2] / "LIBERO-Remain-task033-r2")).resolve()
    activate_core(core)
    monkeypatch.syspath_prepend(str(core))  # test fixtures only; production uses exact package binding
    return core


def test_original_core_runs_selected_control_sources_and_verifies_adapter_and_video(tmp_path, monkeypatch, accepted_core):
    # Synthetic physical/model boundaries from the accepted core's CPU fixtures;
    # real archive, raw, observation, action/query and video-byte validators.
    from tests.test_headless_source_acceptance import make_source, tree_hash
    from tests.test_headless_workflow import configuration, execution
    from tests.test_headless_runner import synthetic_measurement_validator
    from benchmark.remaining_goals.headless import planning, source_acceptance, workflow
    from egrs.augmentation.evaluation import _read_task
    synthetic_measurement_validator.__wrapped__(monkeypatch)
    config = planning.read_json(configuration(tmp_path, monkeypatch))
    runtime = planning.read_json(config["runtime_config"])
    mp, rp, _, _ = make_source(tmp_path / "original")
    source = planning.source_plan("basket", {"manifest": str(mp), "candidate_replay": str(rp)}, acceptance=source_acceptance.SCHEMA)
    source["episodes"] = [e for e in source["episodes"] if e["initial_state_index"] in (0, 3, 6, 9)]
    source.pop("source_plan_sha256")
    source["source_plan_sha256"] = planning.canonical_hash(source)
    original = tree_hash(tmp_path / "original")
    made, environments = execution(monkeypatch)
    policy = workflow.make_policy(runtime)
    adapter = {"schema_version": "task030-oft-adapter-v1", "adapter_sha256": "d" * 64}
    policy.provenance["policy_metadata"]["method_adapter"] = adapter
    plan = {"plan_sha256": "b" * 64, "base_runtime": runtime, "adapter_identity": adapter}
    target = tmp_path / "output"
    workflow._run_task(target, source, runtime, plan["plan_sha256"], lambda identity: None, shared_policy=policy)
    metadata, results = _read_task(target, {"scoped": False, "source": source}, plan)
    assert metadata["status"] == "completed"
    assert [r["initial_state_index"] for r in results] == [0, 3, 6, 9]
    assert all(r["queries"] and r["executed_actions"] and r["video"]["status"] == "saved" for r in results)
    assert policy.calls == 4 and len(environments[0].actions) == 24
    assert tree_hash(tmp_path / "original") == original
    changed = copy.deepcopy(plan)
    changed["adapter_identity"] = {"adapter_sha256": "e" * 64}
    with pytest.raises(ValueError, match="adapter"):
        _read_task(target, {"scoped": False, "source": source}, changed)
    video = target / results[0]["video"]["path"]
    video.write_bytes(video.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="video"):
        _read_task(target, {"scoped": False, "source": source}, plan)


def test_incomplete_method_summary_uses_034_mapping(tmp_path, monkeypatch, accepted_core):
    from egrs.augmentation import evaluation as ev
    reporting = Path(__file__).resolve().parents[2] / "LIBERO-Remain-task034"
    import sys
    monkeypatch.syspath_prepend(str(reporting))
    monkeypatch.setattr(ev, "activate_reporting", lambda root: "test-034")
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    expected = ev.select_population(expected_episodes("nine-mask10"), "raw_control")
    plan = {"schema_version": ev.SCHEMA, "config": {"group": "raw_control", "benchmark_root": str(accepted_core), "reporting_root": str(reporting)},
            "adapter_identity": {"adapter_sha256": "c" * 64}, "expected": expected, "tasks": []}
    plan["plan_sha256"] = ev._hash(plan)
    import json
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "batch.json").write_text(json.dumps({"schema_version": ev.SCHEMA, "plan_sha256": plan["plan_sha256"]}))
    report = ev.inspect_run(tmp_path)
    assert report["counts"]["expected"] == 36
    assert report["counts"]["completed"] == 0
    assert report["counts"]["formal_SR"] is None
    assert all(row["outcome"] is None for row in report["episodes"])


@pytest.mark.parametrize("group,count", [("progress_aug", 90), ("raw_control", 36)])
def test_plan_joins_legacy_and_new_sources_without_evaluating(tmp_path, monkeypatch, accepted_core, group, count):
    import json
    from egrs.augmentation import evaluation as ev, adapter_identity
    from benchmark.remaining_goals.headless import planning, nine_planning, scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from tests.test_headless_workflow import configuration
    cfg = planning.read_json(configuration(tmp_path, monkeypatch))
    expected = nine_planning.expected_episodes("nine-mask10")
    monkeypatch.setattr(ev, "activate_reporting", lambda root: "test034")
    monkeypatch.setattr(adapter_identity, "read_adapter_identity", lambda path: {"group": group})
    def source(task, origin, **kwargs):
        rows = copy.deepcopy([e for e in expected if e["task_id"] == task])
        return {"episodes": rows, "source_plan_sha256": "a" * 64}
    monkeypatch.setattr(planning, "source_plan", source)
    origins = {(e["task_id"], e["initial_state_index"]): {} for e in expected}
    monkeypatch.setattr(nine_planning, "read_sources", lambda path, protocol: ({}, origins))
    monkeypatch.setattr(scoped_sources, "resolve_source", lambda protocol, task, index, origin:
        {"episodes": [copy.deepcopy(next(e for e in expected if e["task_id"] == task and e["initial_state_index"] == index))]})
    config = {"schema_version": ev.SCHEMA, "group": group, "benchmark_root": str(accepted_core),
        "reporting_root": "reporting", "base_runtime": cfg["runtime_config"], "adapter": "adapter", "new_sources": "sources.json",
        "legacy_sources": {task: cfg["sources"][task] for task in REUSE_TASKS}}
    path = tmp_path / "method.json"
    path.write_text(json.dumps(config))
    plan = ev.build_plan(path)
    assert len(plan["expected"]) == count
    assert sum(len(t["source"]["episodes"]) for t in plan["tasks"]) == count
    assert not plan["simulation_created"] and not plan["weights_loaded"]
    assert len({e["episode_id"] for t in plan["tasks"] for e in t["source"]["episodes"]}) == count


def test_clean_process_keeps_report_checkout_from_shadowing_frozen_core(accepted_core):
    import os
    import subprocess
    import sys
    reporting = Path(os.environ.get("TASK030_TEST_REPORTING", Path(__file__).resolve().parents[2] / "LIBERO-Remain-task034"))
    result = subprocess.run([sys.executable, "-c", """
import sys
from pathlib import Path
from egrs.augmentation.dependencies import activate_core, activate_reporting
activate_core(sys.argv[1])
activate_reporting(sys.argv[2])
import benchmark
import benchmark.remaining_goals.headless.nine_planning
import libero_remain_reporting
assert Path(benchmark.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
assert Path(libero_remain_reporting.__file__).resolve().is_relative_to(Path(sys.argv[2]).resolve())
print('isolated identities verified')
""", str(accepted_core), str(reporting)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "isolated identities verified" in result.stdout
