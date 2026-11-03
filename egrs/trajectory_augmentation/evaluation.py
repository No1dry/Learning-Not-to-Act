"""One final035 adapter, fixed original 90 mask10 and 90 normal00 episodes.

Planning and reporting are file-only. Only ``run`` creates the isolated policy
and native environments through the pinned benchmark workflow. Original six
normal00 endpoints and new-three official endpoints retain their own protocols.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from egrs.augmentation.dependencies import activate_core, activate_reporting
from egrs.augmentation.evaluation import _hash, _read, check_method_identity

SCHEMA = "task035-dual-condition-eval-v1"
FACTORY = "egrs.augmentation.evaluation:make_policy"
GROUP = "robot_rewind_mix"
IDENTITY_FIELDS = ("episode_id", "task_id", "suite", "initial_state_index", "initial_mask", "policy_seed", "evaluation_track")


def validate_adapter(identity):
    required = {"schema_version": "task035-oft-adapter-v1", "group": GROUP, "recipe": GROUP,
                "data_kind": "task035-generated-trajectories-v1", "update": 1000, "final_update": 1000}
    if any(identity.get(key) != value for key, value in required.items()):
        raise ValueError("evaluation requires the exact035 final1000 robot_rewind_mix adapter")


def _validate_population(plan):
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from benchmark.remaining_goals.headless.planning import canonical_hash
    validate_adapter(plan["adapter_identity"])
    if plan["config"]["group"] != GROUP:
        raise ValueError("035 evaluation group identity differs")
    for bits, protocol in (("10", "nine-mask10"), ("00", "nine-normal00")):
        expected = expected_episodes(protocol)
        if plan["expected"].get(bits) != expected:
            raise ValueError("fixed original evaluation population identity differs")
        lookup = {e["episode_id"]: e for e in expected}
        seen = set()
        for item in [t for t in plan["tasks"] if t["condition"] == bits]:
            source = item["source"]
            if source.get("source_plan_sha256") != canonical_hash({k: v for k, v in source.items() if k != "source_plan_sha256"}):
                raise ValueError("source plan identity differs")
            for ep in source["episodes"]:
                name = ep["episode_id"]
                if name not in lookup or name in seen or any(ep.get(k) != lookup[name][k] for k in IDENTITY_FIELDS):
                    raise ValueError("source population identity differs from fixed original condition")
                seen.add(name)
                legacy = ep["task_id"] in REUSE_TASKS
                if bits == "10" and legacy:
                    if item["scoped"] or len(source["episodes"]) != 10:
                        raise ValueError("legacy10 requires original full ten-source reader")
                else:
                    wanted = "normal00-control" if bits == "00" and legacy else protocol
                    if not item["scoped"] or source.get("protocol") != wanted or len(source["episodes"]) != 1:
                        raise ValueError("source protocol identity differs")
        if seen != set(lookup):
            raise ValueError("source population does not cover fixed90")
    if (set(plan["expected"]) != {"10", "00"} or any(t["condition"] not in {"10", "00"} for t in plan["tasks"])
            or len({t["key"] for t in plan["tasks"]}) != len(plan["tasks"])):
        raise ValueError("duplicate or foreign evaluation population")


def build_plan(config_path):
    """Resolve existing accepted sources; never construct states or load models."""
    from egrs.augmentation.adapter_identity import read_adapter_identity
    path = Path(config_path).resolve()
    cfg = _read(path)
    allowed = {"schema_version", "group", "benchmark_root", "reporting_root", "base_runtime", "adapter",
               "legacy_sources_10", "legacy_sources_00", "new_sources_10", "new_sources_00"}
    if set(cfg) != allowed or cfg["schema_version"] != SCHEMA or cfg["group"] != GROUP:
        raise ValueError("explicit035 same-adapter dual-condition configuration required")
    def resolve(value):
        p = Path(value).expanduser()
        return str((path.parent / p).resolve() if not p.is_absolute() else p.resolve())
    for key in allowed - {"schema_version", "group", "legacy_sources_10"}:
        cfg[key] = resolve(cfg[key])
    core_ref = activate_core(cfg["benchmark_root"])
    report_ref = activate_reporting(cfg["reporting_root"])
    from benchmark.remaining_goals.headless import planning, nine_planning, scoped_planning, scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    runtime = nine_planning.load_runtime(cfg["base_runtime"])
    identity = read_adapter_identity(cfg["adapter"])
    validate_adapter(identity)
    expected = {"10": nine_planning.expected_episodes("nine-mask10"), "00": nine_planning.expected_episodes("nine-normal00")}
    if set(cfg["legacy_sources_10"]) != set(REUSE_TASKS):
        raise ValueError("all six original legacy10 sources are required")
    tasks = []
    for task in REUSE_TASKS:
        origin = deepcopy(cfg["legacy_sources_10"][task])
        for key in ("manifest", "candidate_replay"):
            origin[key] = resolve(origin[key])
        cfg["legacy_sources_10"][task] = origin
        source = planning.source_plan(task, origin, acceptance=planning.MASK10_ACCEPTANCE)
        tasks.append({"key": "10_" + task, "condition": "10", "scoped": False, "source": source})
    _, old00 = scoped_planning.read_composite(cfg["legacy_sources_00"], "normal00-control")
    for bits, protocol in (("10", "nine-mask10"), ("00", "nine-normal00")):
        _, new = nine_planning.read_sources(cfg["new_sources_" + bits], protocol)
        for ep in expected[bits]:
            task, index = ep["task_id"], ep["initial_state_index"]
            if bits == "10" and task in REUSE_TASKS:
                continue
            original_protocol = "normal00-control" if task in REUSE_TASKS else protocol
            origins = old00 if task in REUSE_TASKS else new
            source = scoped_sources.resolve_source(original_protocol, task, index, origins.get((task, index)))
            tasks.append({"key": ep["episode_id"], "condition": bits, "scoped": True, "source": source})
    plan = {"schema_version": SCHEMA, "config": cfg, "base_runtime": runtime, "adapter_identity": identity,
            "core_revision": core_ref, "reporting_revision": report_ref, "expected": expected, "tasks": tasks,
            "simulation_created": False, "weights_loaded": False,
            "budget": {"10": 90, "00": 90, "total": 180, "policy_seed": 7, "max_chunk_steps": 8, "horizon": 520,
                       "video": "all", "raw_queries_actions": "all"}}
    _validate_population(plan)
    plan["plan_sha256"] = _hash(plan)
    return plan


def _read_task(directory, item, plan, model_identity=None):
    """Exact original readers verify archives, source, observations, actions/video."""
    from benchmark.remaining_goals.headless import workflow
    metadata, results = workflow._read_task(directory, scoped=item["scoped"], batch_identity=plan["plan_sha256"],
        runtime=plan["base_runtime"], sources=[item["source"]], model_identity=model_identity)
    check_method_identity(metadata, plan["adapter_identity"])
    return metadata, results


def make_report(records, identity, issues=None):
    """Use034 binary10 and the original core's official00 report independently."""
    from libero_remain_reporting import map_verified_results
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.nine_workflow import make_report as original_report
    issues = issues or {"10": [], "00": []}
    ten = map_verified_results(expected_episodes("nine-mask10"), records["10"], artifact_issues=issues["10"])
    normal = original_report(records["00"], protocols=["nine-normal00"])
    normal["artifact_issues"] = issues["00"]
    counts = normal["conditions"]["00"]
    rates = {"10": ten["counts"]["formal_SR"], "00": counts["official_task_SR"]
             if counts["official_signal_coverage"]["numerator"] == 90 and not issues["00"]
             and not normal["model_compatibility_issues"] else None}
    conditions = {}
    for bits, numerator, metric, report in (("10", 22, "binary_compliant_SR", ten), ("00", 78, "official_task_SR", normal)):
        baseline = {"numerator": numerator, "denominator": 90, "percent": 100 * numerator / 90}
        conditions[bits] = {"metric": metric, "baseline": baseline, "formal_SR": rates[bits],
            "delta_percentage_points": rates[bits]["percent"] - baseline["percent"] if rates[bits] else None,
            "report": report}
    return {"schema_version": SCHEMA, "group": GROUP, "method_adapter": identity, "conditions": conditions,
            "expected_all_conditions": 180, "note": "10 compliant and00 official SR use separate fixed90 denominators and separate baselines. "
            "Original six00 and new-three00 endpoint protocols remain distinct. Missing/integrity errors cannot become model failures."}


def inspect_run(directory):
    directory = Path(directory).resolve()
    plan, batch = _read(directory / "plan.json"), _read(directory / "batch.json")
    if (plan.get("schema_version") != SCHEMA or plan.get("plan_sha256") != _hash({k: v for k, v in plan.items() if k != "plan_sha256"})
            or batch.get("schema_version") != SCHEMA or batch.get("plan_sha256") != plan["plan_sha256"]):
        raise ValueError("frozen035 plan/batch identity differs")
    activate_core(plan["config"]["benchmark_root"])
    activate_reporting(plan["config"]["reporting_root"])
    _validate_population(plan)
    from benchmark.remaining_goals.headless import workflow, planning
    from benchmark.remaining_goals.headless.offline_scoring import score_verified_result
    records, issues = {"10": {}, "00": {}}, {"10": [], "00": []}
    for item in plan["tasks"]:
        target = directory / "tasks" / item["key"]
        if not target.exists():
            state = batch.get("tasks", {}).get(item["key"])
            if state:
                issues[item["condition"]].append({"task_id": item["key"], "error": state})
            continue
        try:
            if "loaded_base_identity" not in batch:
                raise ValueError("executed task lacks the shared loaded base-model batch identity")
            metadata, results = _read_task(target, item, plan, batch.get("loaded_base_identity"))
            episodes = {e["episode_id"]: e for e in item["source"]["episodes"]}
            for raw in results:
                name = raw["episode_id"]
                records[item["condition"]][name] = score_verified_result(episodes[name], raw, condition=item["condition"], source={
                    "model_identity": workflow._model_identity(metadata), "original_protocol": metadata["protocol_version"],
                    "input_evidence_level": "verified_raw_execution_video_and_source_archive", "run_path": str(directory),
                    "verified_files": [{"path": str(target / "task_run.json"), "sha256": planning.file_sha(target / "task_run.json")}],
                    "new_execution": True})
        except (OSError, ValueError, KeyError, TypeError) as error:
            issues[item["condition"]].extend({"episode_id": e["episode_id"], "error": f"{type(error).__name__}: {error}"}
                                            for e in item["source"]["episodes"])
    return make_report(records, plan["adapter_identity"], issues)


def render_report(report):
    from libero_remain_reporting import render_report as binary_report
    from benchmark.remaining_goals.headless.nine_workflow import render_report as normal_report
    lines = ["# Task035 same-adapter10/00 evaluation", "", report["note"], "",
             "| Condition | Metric | Baseline | Formal SR | Change (pp) |", "|---|---|---:|---:|---:|"]
    for bits, item in report["conditions"].items():
        value, delta = item["formal_SR"], item["delta_percentage_points"]
        score = f"{value['percent']:.2f}% ({value['numerator']}/{value['denominator']})" if value else "N/A"
        change = f"{delta:+.2f}" if delta is not None else "N/A"
        lines.append(f"| {bits} | {item['metric']} | {item['baseline']['numerator']}/90 | {score} | {change} |")
    return "\n".join(lines) + "\n\n" + binary_report(report["conditions"]["10"]["report"]) + "\n" + normal_report(report["conditions"]["00"]["report"])


def _save_report(directory, report):
    from benchmark.remaining_goals.headless.workflow import write_json
    directory = Path(directory)
    write_json(directory / "summary.json", report, update=(directory / "summary.json").exists())
    (directory / "report.md").write_text(render_report(report), encoding="utf-8")


def run(config, output):
    plan = build_plan(config)
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("new035 output required; existing episodes are never rerun or overwritten")
    protected = {Path(plan["config"][k]) for k in ("benchmark_root", "reporting_root", "adapter", "base_runtime", "legacy_sources_00", "new_sources_10", "new_sources_00")}
    for item in plan["tasks"]:
        protected.update(Path(value).parent for key, value in item["source"]["source"].items()
                         if key in {"manifest", "candidate_replay", "initialization", "rgb_certificate"})
    if any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError("new035 output overlaps read-only source/dependency/adapter")
    output.mkdir(parents=True)
    workflow.write_json(output / "plan.json", plan)
    batch = {"schema_version": SCHEMA, "plan_sha256": plan["plan_sha256"], "tasks": {}}
    workflow.write_json(output / "batch.json", batch)
    worker = deepcopy(plan["base_runtime"])
    worker.update(policy_factory=FACTORY, method_adapter=plan["config"]["adapter"])
    def bind_model(actual):
        if batch.get("loaded_base_identity", actual) != actual:
            raise ValueError("base model identity changed across conditions")
        batch["loaded_base_identity"] = actual
        workflow.write_json(output / "batch.json", batch, update=True)
    policy = None
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
            _save_report(output, inspect_run(output))
            print(f"condition={item['condition']} task={item['key']} status={result['status']}", flush=True)
            if result["status"] != "completed":
                raise RuntimeError("technical interruption retained; remaining episodes not started")
    finally:
        try:
            if policy is not None:
                policy.close()
        finally:
            _save_report(output, inspect_run(output))
    return inspect_run(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run"):
        p = sub.add_parser(command); p.add_argument("--config", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("report"); p.add_argument("--run", required=True); p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.config, args.out)
    elif args.command == "plan":
        plan = build_plan(args.config)
        with Path(args.out).open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2, allow_nan=False)
    else:
        output, original = Path(args.out).resolve(), Path(args.run).resolve()
        if output == original or output in original.parents or original in output.parents:
            raise ValueError("derived035 report requires separate output directory")
        report = inspect_run(original)
        output.mkdir(parents=True, exist_ok=False)
        _save_report(output, report)


if __name__ == "__main__":
    main()
