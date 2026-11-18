"""One user-started, sequential six-cell official evaluation; never retry."""
import json
from pathlib import Path
import subprocess
import sys

from . import contracts as c


def read_episodes(output, summary):
    path = Path(output)/"episodes.jsonl"
    c.require(c.sha(path) == summary.get("episodes_sha256"), "047 completed episode bytes differ")
    rows = [json.loads(line, object_pairs_hook=c.object_pairs) for line in path.read_text().splitlines()]
    c.require(len(rows) == 500 and all(
        row["task_id"] == i//50 and row["initial_state_index"] == i % 50
        and row["ordinal"] == i+1 and type(row["success"]) is bool and row["status"] == "completed"
        and row["arm"] == summary["arm"] and row["suite"] == summary["suite"]
        for i, row in enumerate(rows)), "047 completed episode population differs")
    for row in rows:
        video = (Path(output)/row["video_path"]).resolve()
        c.require(Path(output).resolve() in video.parents and video.is_file() and video.stat().st_size > 0,
                  "047 completed original video missing")
    return rows


def verify_cell(output, config):
    summary = c.read(Path(output)/"summary.json")
    c.require(summary.get("schema_version") == c.SCHEMA and summary.get("formal_complete") is True
              and summary.get("software_exit") == "success" and summary.get("execution_error") is None
              and summary.get("arm") == config["arm"] and summary.get("suite") == config["suite"]
              and summary.get("completed") == summary.get("expected") == 500
              and summary.get("scorer") == "official_env_done" and summary.get("deployment_hint") is False,
              "047 cell has no complete official500 result")
    identity = summary["model_identity"]
    adapter = identity.get("method_adapter")
    c.require(identity["checkpoint_source"] == c.BASE_SOURCE and identity["repo_commit"] == c.REVISION
              and identity["dataset_statistics_sha256"] == c.STATS_SHA
              and identity["component_checkpoint_sha256"] == c.COMPONENT_HASHES
              and identity["source_sha256"] == c.SOURCE_HASHES
              and identity["evaluation_suite"] == config["suite"], "047 completed model provenance differs")
    if config["arm"] == "base":
        c.require(adapter is None and identity["research_adapter_loaded"] is False,
                  "047 baseline unexpectedly loaded an adapter")
    else:
        c.require(isinstance(adapter, dict) and adapter.get("adapter_sha256") == c.ADAPTER_SHA
                  and adapter.get("arm") == "h1" and adapter.get("update") == adapter.get("final_update") == 3000
                  and identity["research_adapter_loaded"] is True, "047 wrong completed H1 artifact")
    stats = c.read(Path(config["checkpoint"])/"dataset_statistics.json")
    key = c.expected_key(config["suite"], stats)
    c.require(identity["unnorm_key"] == key and identity["normalization_statistics_sha256"]
              == c.statistic_sha(stats[key]), "047 completed inference normalization differs")
    rows = read_episodes(output, summary)
    successes = sum(row["success"] for row in rows)
    c.require(summary["formal_SR"] == {"numerator": successes, "denominator": 500, "percent": successes/5},
              "047 completed SR differs from official outcomes")
    c.require(len(summary["tasks"]) == 10 and all(
        task["task_id"] == i and task["completed"] == task["expected"] == 50
        and task["successes"] == sum(row["success"] for row in rows if row["task_id"] == i)
        for i, task in enumerate(summary["tasks"])), "047 task aggregates differ")
    return summary, rows


def compare(output, configs):
    output = Path(output)
    suites = {}
    totals = {"base": 0, "h1": 0}
    rows_out = []
    for suite in c.HORIZONS:
        reports, episodes = {}, {}
        for arm in ("base", "h1"):
            summary, rows = verify_cell(output/c.cell_name(arm, suite), configs[(arm, suite)])
            reports[arm], episodes[arm] = summary, rows
            totals[arm] += summary["formal_SR"]["numerator"]
        gained, lost, both, neither = [], [], 0, 0
        for a, b in zip(episodes["base"], episodes["h1"]):
            binding = ("task_id", "task_name", "instruction", "initial_state_index",
                       "initial_state_sha256", "initial_state_dtype", "initial_state_shape")
            c.require(all(a[k] == b[k] for k in binding), "047 models did not use identical official initial states")
            name = f"{suite}/task{a['task_id']:02d}/init{a['initial_state_index']:02d}"
            if a["success"] and b["success"]:
                both += 1
            elif b["success"]:
                gained.append(name)
            elif a["success"]:
                lost.append(name)
            else:
                neither += 1
        tasks = []
        for a, b in zip(reports["base"]["tasks"], reports["h1"]["tasks"]):
            c.require(a["task_name"] == b["task_name"] and a["instruction"] == b["instruction"],
                      "047 task-language pairing differs")
            row = {"suite": suite, "task_id": a["task_id"], "task_name": a["task_name"],
                   "instruction": a["instruction"], "denominator": 50,
                   "base_successes": a["successes"], "h1_successes": b["successes"],
                   "base_SR_percent": 2*a["successes"], "h1_SR_percent": 2*b["successes"],
                   "delta_percentage_points": 2*(b["successes"]-a["successes"])}
            tasks.append(row)
            rows_out.append(row)
        rates = {arm: reports[arm]["formal_SR"] for arm in reports}
        suites[suite] = {"rates": rates, "delta_percentage_points": rates["h1"]["percent"]-rates["base"]["percent"],
                         "paired": {"gained": gained, "lost": lost, "both": both, "neither": neither},
                         "tasks": tasks}
    result = {"format": "task047-official-comparison-v1", "formal_complete": True,
              "total_completed_episodes": 3000, "suites": suites, "tasks": rows_out,
              "overall": {arm: {"numerator": n, "denominator": 1500, "percent": 100*n/1500}
                          for arm, n in totals.items()},
              "official_pipeline": True, "score": "official_env_done", "single_policy_seed": 7,
              "not_strict_zero_shot": True, "old_LIBERO10_results_not_pooled": True}
    result["overall_delta_percentage_points"] = result["overall"]["h1"]["percent"]-result["overall"]["base"]["percent"]
    c.write(output/"comparison.json", result)
    lines = ["# 047 Official three-suite retention", "",
             "| Suite | Base SR | H1@3000 SR | H1 - Base |", "|---|---:|---:|---:|"]
    for suite, value in suites.items():
        rates = value["rates"]
        lines.append(f"| {suite} | {rates['base']['percent']:.2f}% | {rates['h1']['percent']:.2f}% | {value['delta_percentage_points']:+.2f}pp |")
    a, b = result["overall"]["base"], result["overall"]["h1"]
    lines += [f"| Three-suite total | {a['percent']:.2f}% ({a['numerator']}/1500) | {b['percent']:.2f}% ({b['numerator']}/1500) | {result['overall_delta_percentage_points']:+.2f}pp |",
              "", "| Suite | Task | Instruction | Base | H1 | Delta |",
              "|---|---:|---|---:|---:|---:|"]
    for row in rows_out:
        lines.append(f"| {row['suite']} | {row['task_id']} | {row['instruction']} | {row['base_SR_percent']:.2f}% | {row['h1_SR_percent']:.2f}% | {row['delta_percentage_points']:+.2f}pp |")
    (output/"comparison.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return result


def run_all(config_dir, output):
    config_dir, output = Path(config_dir).resolve(), Path(output).resolve()
    paths = {(arm, suite): config_dir/c.config_name(arm, suite) for arm, suite in c.CELLS}
    configs = {key: c.load_config(path) for key, path in paths.items()}
    h1_directories = set()
    for key, config in configs.items():
        c.require((config["arm"], config["suite"]) == key, "047 six-cell config ordering differs")
        c.validate_output(config, output, inputs=paths.values())
        c.require(all(config[k] == next(iter(configs.values()))[k] for k in ("repo_path", "checkpoint")),
                  "047 cells do not share original model/source")
        if config["arm"] == "h1":
            h1_directories.add(config["method_adapter"])
    c.require(len(h1_directories) == 1, "047 H1 cells have different checkpoints")
    # Fixed file-only admission, not a GPU/model/physics diagnostic.
    for arm in ("base", "h1"):
        c.verify_inputs(configs[(arm, "libero_spatial")])
    stats = c.read(Path(next(iter(configs.values()))["checkpoint"])/"dataset_statistics.json")
    for suite in c.HORIZONS:
        c.expected_key(suite, stats)
    output.mkdir(parents=True, exist_ok=False)
    digests = {c.cell_name(*key): c.sha(path) for key, path in paths.items()}
    state = {"format": "task047-official-launch-v1", "status": "running",
             "expected_episodes": 3000, "completed_episodes": 0, "cells": {},
             "config_sha256": digests, "implicit_retry": False}
    c.write(output/"status.json", state)
    try:
        for index, key in enumerate(c.CELLS):
            name = c.cell_name(*key)
            c.require(c.sha(paths[key]) == digests[name], "047 config changed after launch")
            state["cells"][name] = {"status": "running"}
            c.write(output/"status.json", state)
            command = [sys.executable, "-u", "-m", "egrs.official047", "run-cell",
                       "--config", str(paths[key]), "--output", str(output/name),
                       "--completed-before", str(index*500)]
            process = subprocess.run(command, check=False)
            c.require(process.returncode == 0, f"047 {name} exited{process.returncode}; next cell not started")
            summary, _ = verify_cell(output/name, configs[key])
            state["cells"][name] = {"status": "complete", "formal_SR": summary["formal_SR"],
                                    "summary_sha256": c.sha(output/name/"summary.json")}
            state["completed_episodes"] += 500
            c.write(output/"status.json", state)
        result = compare(output, configs)
        state["status"] = "complete"
        c.write(output/"status.json", state)
        print(f"[047] ALL COMPLETE 3000/3000 (100%); Base={result['overall']['base']['percent']:.2f}% H1={result['overall']['h1']['percent']:.2f}%", flush=True)
        return result
    except BaseException as error:
        state.update(status="failed", error=f"{type(error).__name__}: {error}")
        c.write(output/"status.json", state)
        raise


def progress(output):
    output = Path(output)
    if not (output/"status.json").is_file():
        return {"status": "not_started", "completed": 0, "expected": 3000, "percent": 0.0}
    state = c.read(output/"status.json")
    completed = state["completed_episodes"]
    result = {"status": state["status"], "completed": completed,
              "expected": 3000, "percent": 100*completed/3000}
    for name, value in state["cells"].items():
        if value["status"] == "running":
            path = output/name/"progress.json"
            if path.is_file():
                cell = c.read(path)
                result.update(cell=name, phase=cell["phase"],
                              completed=completed+cell["cell_completed"],
                              percent=100*(completed+cell["cell_completed"])/3000,
                              cell_completed=cell["cell_completed"],
                              live_SR_percent=cell.get("live_SR_percent"))
    if state.get("error"):
        result["error"] = state["error"]
    return result
