"""Ordinary OFT+adapter execution using the unchanged accepted benchmark core.

The stored base runtime describes its loader, not the resulting adapted model.
Adapter bytes and lineage are independently bound in batch and per-query raw
evidence. No task labels/mask or evaluator facts enter the policy interface.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from .dependencies import activate_core, activate_reporting

SCHEMA = "task030-adapter-eval-v1"
FACTORY = "egrs.augmentation.evaluation:make_policy"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def select_population(expected, group):
    if group not in {"progress_aug", "raw_control"}:
        raise ValueError("group must be progress_aug or raw_control")
    tasks = {r["task_id"] for r in expected}
    if (len(tasks) != 9 or len(expected) != 90 or len({r["episode_id"] for r in expected}) != 90
            or any(sorted(r["initial_state_index"] for r in expected if r["task_id"] == task) != list(range(10)) for task in tasks)):
        raise ValueError("the unchanged nine-task, ten-source population is required")
    indices = range(10) if group == "progress_aug" else (0, 3, 6, 9)
    return deepcopy([r for r in expected if r["initial_state_index"] in indices])


def check_method_identity(metadata, expected):
    if metadata.get("model_runtime", {}).get("policy_metadata", {}).get("method_adapter") != expected:
        raise ValueError("loaded adapter identity differs from the frozen method batch")


class AdapterPolicy:
    def __init__(self, config):
        from .oft import attach_trained_adapter
        from benchmark.remaining_goals.adapters.openvla_oft import OpenVLAOFTPolicy
        from benchmark.remaining_goals.adapters.oft_transfer import FACTORY as BASE_FACTORY
        base_config = deepcopy(config)
        adapter = base_config.pop("method_adapter")
        base_config["policy_factory"] = BASE_FACTORY
        self.base = OpenVLAOFTPolicy(base_config)
        try:
            identity = attach_trained_adapter(self.base, adapter)
            self.metadata = deepcopy(self.base.metadata)
            self.metadata["method_adapter"] = identity
        except BaseException:
            self.base.close()
            raise

    def predict(self, observation, instruction):
        # Same keys as the accepted core; ignores additional evaluator fields.
        keys = ("images", "proprio", "agentview_image", "robot0_eye_in_hand_image",
                "robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")
        obs = {key: deepcopy(observation[key]) for key in keys if key in observation}
        return self.base.predict(obs, instruction)

    def reset(self):
        return self.base.reset()

    def close(self):
        return self.base.close()


def make_policy(config):
    return AdapterPolicy(config)


def build_plan(config_path):
    """File-only source resolution; no model loading, native creation or replay."""
    from .adapter_identity import read_adapter_identity
    path = Path(config_path).resolve()
    cfg = _read(path)
    allowed = {"schema_version", "group", "benchmark_root", "reporting_root", "base_runtime", "adapter", "legacy_sources", "new_sources"}
    if set(cfg) != allowed or cfg["schema_version"] != SCHEMA:
        raise ValueError("explicit Task030 adapter evaluation configuration required")
    def resolve(value):
        p = Path(value).expanduser()
        return str((path.parent / p).resolve() if not p.is_absolute() else p.resolve())
    for key in ("benchmark_root", "reporting_root", "base_runtime", "adapter", "new_sources"):
        cfg[key] = resolve(cfg[key])
    core_ref = activate_core(cfg["benchmark_root"])
    report_ref = activate_reporting(cfg["reporting_root"])
    from benchmark.remaining_goals.headless import nine_planning, planning, scoped_sources
    from benchmark.remaining_goals.headless.planning import MASK10_ACCEPTANCE
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS, NEW_TASKS
    runtime = nine_planning.load_runtime(cfg["base_runtime"])
    identity = read_adapter_identity(cfg["adapter"])
    if identity.get("group") != cfg["group"]:
        raise ValueError("adapter training group differs from fixed evaluation population")
    expected = select_population(nine_planning.expected_episodes("nine-mask10"), cfg["group"])
    _, origins = nine_planning.read_sources(cfg["new_sources"], "nine-mask10")
    if set(cfg["legacy_sources"]) != set(REUSE_TASKS):
        raise ValueError("all six unchanged historical task sources are required")
    tasks = []
    for task in REUSE_TASKS:
        origin = deepcopy(cfg["legacy_sources"][task])
        for key in ("manifest", "candidate_replay"):
            origin[key] = resolve(origin[key])
        source = planning.source_plan(task, origin, acceptance=MASK10_ACCEPTANCE)
        selected = {e["episode_id"] for e in expected if e["task_id"] == task}
        source["method_parent_source_plan_sha256"] = source.pop("source_plan_sha256")
        source["episodes"] = [e for e in source["episodes"] if e["episode_id"] in selected]
        source["source_plan_sha256"] = planning.canonical_hash(source)
        tasks.append({"key": task, "scoped": False, "source": source})
    for episode in expected:
        if episode["task_id"] in NEW_TASKS:
            source = scoped_sources.resolve_source("nine-mask10", episode["task_id"], episode["initial_state_index"],
                                                   origins[(episode["task_id"], episode["initial_state_index"])])
            tasks.append({"key": episode["episode_id"], "scoped": True, "source": source})
    if sorted(e["episode_id"] for item in tasks for e in item["source"]["episodes"]) != sorted(e["episode_id"] for e in expected):
        raise ValueError("accepted sources do not cover the exact fixed method population")
    plan = {"schema_version": SCHEMA, "config": cfg, "base_runtime": runtime, "adapter_identity": identity,
            "core_revision": core_ref, "reporting_revision": report_ref, "expected": expected, "tasks": tasks,
            "simulation_created": False, "weights_loaded": False}
    plan["plan_sha256"] = _hash(plan)
    return plan


def _read_task(directory, item, plan, model_identity=None):
    """Reuse core evidence checks with an explicit 10/4 legacy task selection.

The legacy batch reader only permits ten episodes. This method-owned batching
bridge additionally admits exactly the preregistered four; no physical test or
score is reimplemented here.
"""
    from benchmark.remaining_goals.headless import workflow, planning
    from benchmark.remaining_goals.headless.schema import validate_result
    from benchmark.remaining_goals.headless.evidence import validate_evidence
    from benchmark.remaining_goals.adapters.oft_transfer import validate_policy_metadata
    if item["scoped"]:
        metadata, results = workflow._read_task(directory, scoped=True, batch_identity=plan["plan_sha256"],
            runtime=plan["base_runtime"], sources=[item["source"]], model_identity=model_identity)
    else:
        directory = Path(directory)
        metadata = _read(directory / "task_run.json")
        source = item["source"]
        if (metadata.get("schema_version") != "remaining-headless-task-run-v1"
                or metadata.get("protocol_version") != planning.PROTOCOL
                or metadata.get("status") not in {"completed", "technical_pause"}
                or metadata.get("batch_identity_sha256") != plan["plan_sha256"]
                or metadata.get("source_plan") != source or metadata.get("runtime_config") != plan["base_runtime"]):
            raise ValueError("method task/source/runtime identity differs")
        for name, digest in source["source_files"].items():
            if planning.file_sha(workflow._contained(directory / "source", name)) != digest:
                raise ValueError("archived source changed")
        workflow._validate_source_snapshot(directory, source)
        validate_policy_metadata(plan["base_runtime"], metadata["model_runtime"]["policy_metadata"])
        if model_identity is not None and workflow.shared_model_identity(metadata["model_runtime"]) != model_identity:
            raise ValueError("base model components/statistics differ between tasks")
        episodes = {e["episode_id"]: e for e in source["episodes"]}
        seen, results = set(), []
        for ref in metadata["results"]:
            name = ref["episode_id"]
            if name not in episodes or name in seen:
                raise ValueError("foreign or duplicate method result")
            seen.add(name)
            rawpath = workflow._contained(directory, ref["path"])
            if planning.file_sha(rawpath) != ref["sha256"]:
                raise ValueError("raw episode bytes changed")
            raw = _read(rawpath)
            identity = workflow.evidence_identity(metadata, episodes[name])
            validate_result(raw, episodes[name], identity)
            if raw.get("model_identity") != workflow._model_identity(metadata):
                raise ValueError("raw adapter/base identity differs")
            validation = validate_evidence(directory, raw, episodes[name], identity)
            if ref["validation"] != ("partial_evidence" if validation.get("verified") is False else "verified"):
                raise ValueError("raw evidence verification differs")
            video = raw.get("video", {})
            if raw["status"] == "completed" and video.get("status") != "saved":
                raise ValueError("completed method episode lacks full video")
            if video.get("status") == "saved" and planning.file_sha(workflow._contained(directory, video["path"])) != video["sha256"]:
                raise ValueError("video bytes changed")
            results.append(raw)
        if (len(metadata["missing"]) != len(set(metadata["missing"])) or set(metadata["missing"]) != set(episodes) - seen
                or metadata["status"] == "completed" and (metadata["missing"] or any(r["status"] != "completed" for r in results))):
            raise ValueError("method execution/missing ledger differs")
    check_method_identity(metadata, plan["adapter_identity"])
    return metadata, results


def inspect_run(directory):
    directory = Path(directory).resolve()
    batch = _read(directory / "batch.json")
    plan = _read(directory / "plan.json")
    if (plan.get("schema_version") != SCHEMA or plan.get("plan_sha256") != _hash({k: v for k, v in plan.items() if k != "plan_sha256"})
            or batch.get("plan_sha256") != plan["plan_sha256"] or batch.get("schema_version") != SCHEMA):
        raise ValueError("frozen method plan/batch identity differs")
    activate_core(plan["config"]["benchmark_root"])
    activate_reporting(plan["config"]["reporting_root"])
    from benchmark.remaining_goals.headless import workflow, planning
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    from libero_remain_reporting import map_verified_results
    records, issues = {}, []
    for item in plan["tasks"]:
        path = directory / "tasks" / item["key"]
        if not path.exists():
            if item["key"] in batch.get("tasks", {}):
                issues.append({"task_id": item["key"], "error": batch["tasks"][item["key"]]})
            continue
        try:
            metadata, results = _read_task(path, item, plan, batch.get("loaded_base_identity"))
            episodes = {e["episode_id"]: e for e in item["source"]["episodes"]}
            for result in results:
                name = result["episode_id"]
                if name in records:
                    raise ValueError("duplicate result across method tasks")
                records[name] = score_verified_result(episodes[name], result, condition="10", source={
                    "model_identity": workflow._model_identity(metadata), "original_protocol": metadata["protocol_version"],
                    "input_evidence_level": "verified_raw_execution_video_and_source_archive",
                    "verified_files": [{"path": str(path / "task_run.json"), "sha256": planning.file_sha(path / "task_run.json")}],
                    "run_path": str(directory), "new_execution": True})
        except (OSError, ValueError, KeyError, TypeError) as error:
            for episode in item["source"]["episodes"]:
                issues.append({"episode_id": episode["episode_id"], "error": f"{type(error).__name__}: {error}"})
    report = map_verified_results(plan["expected"], records, artifact_issues=issues)
    report["method_adapter"] = plan["adapter_identity"]
    report["group"] = plan["config"]["group"]
    return report


def _save_report(directory, report):
    from benchmark.remaining_goals.headless.workflow import write_json
    from libero_remain_reporting import render_report
    directory = Path(directory)
    write_json(directory / "summary.json", report, update=(directory / "summary.json").exists())
    (directory / "report.md").write_text(render_report(report), encoding="utf-8")


def run(config, output):
    plan = build_plan(config)
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("new method output required; existing results are never rerun or overwritten")
    protected = [Path(plan["config"][key]) for key in ("benchmark_root", "reporting_root", "adapter")]
    protected.extend(Path(item["source"]["source"][key]).parent for item in plan["tasks"] for key in ("manifest", "candidate_replay"))
    if any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError("new run overlaps a read-only dependency or source")
    output.mkdir(parents=True)
    workflow.write_json(output / "plan.json", plan)
    batch = {"schema_version": SCHEMA, "plan_sha256": plan["plan_sha256"], "tasks": {}}
    workflow.write_json(output / "batch.json", batch)
    worker = deepcopy(plan["base_runtime"])
    worker.update(policy_factory=FACTORY, method_adapter=plan["config"]["adapter"])
    def bind_model(actual):
        if batch.get("loaded_base_identity", actual) != actual:
            raise ValueError("base model identity changed between tasks")
        batch["loaded_base_identity"] = actual
        workflow.write_json(output / "batch.json", batch, update=True)
    policy, start = None, time.monotonic()
    try:
        policy = SubprocessPolicy(worker)
        check_method_identity({"model_runtime": policy.provenance}, plan["adapter_identity"])
        for item in plan["tasks"]:
            batch["tasks"][item["key"]] = {"status": "running"}
            workflow.write_json(output / "batch.json", batch, update=True)
            result = workflow._run_task(output / "tasks" / item["key"], item["source"], plan["base_runtime"],
                plan["plan_sha256"], bind_model, scoped=item["scoped"], shared_policy=policy)
            batch["tasks"][item["key"]] = {"status": result["status"], "error": result["error"]}
            workflow.write_json(output / "batch.json", batch, update=True)
            report = inspect_run(output)
            _save_report(output, report)
            from libero_remain_reporting import render_report
            print(f"task={item['key']} elapsed_s={time.monotonic()-start:.1f}\n{render_report(report)}", flush=True)
            if result["status"] != "completed":
                raise RuntimeError("technical interruption retained; remaining tasks not started")
    finally:
        try:
            if policy is not None:
                policy.close()
        finally:
            _save_report(output, inspect_run(output))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run"):
        p = sub.add_parser(command)
        p.add_argument("--config", required=True)
        p.add_argument("--out", required=True)
    p = sub.add_parser("report")
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.config, args.out)
    elif args.command == "plan":
        plan = build_plan(args.config)
        with Path(args.out).open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
    else:
        out, original = Path(args.out).resolve(), Path(args.run).resolve()
        if out == original or out in original.parents or original in out.parents:
            raise ValueError("derived report requires a separate output directory")
        report = inspect_run(original)
        out.mkdir(parents=True, exist_ok=False)
        _save_report(out, report)


if __name__ == "__main__":
    main()
