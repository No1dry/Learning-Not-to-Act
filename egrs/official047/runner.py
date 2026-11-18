"""Delegate all valid rollouts to the byte-pinned official OFT functions."""
from contextlib import contextmanager
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import sys

from . import contracts as c


@contextmanager
def patches(module, replacements):
    originals = {name: getattr(module, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(module, name, value)
        yield originals
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def import_official(repo):
    sys.path.insert(0, str(Path(repo).resolve()))
    api = importlib.import_module("experiments.robot.libero.run_libero_eval")
    for name in c.SOURCE_HASHES:
        module = importlib.import_module(name[:-3].replace("/", "."))
        c.require(Path(module.__file__).resolve() == (Path(repo)/name).resolve(),
                  "047 imported a different official source module")
    return api


def make_native_config(api, config, checkpoint, output):
    return api.GenerateConfig(
        model_family="openvla", pretrained_checkpoint=checkpoint, use_l1_regression=True,
        use_diffusion=False, use_film=False, num_images_in_input=2, use_proprio=True,
        center_crop=True, num_open_loop_steps=8, lora_rank=32,
        load_in_8bit=False, load_in_4bit=False, task_suite_name=config["suite"],
        num_steps_wait=10, num_trials_per_task=50, initial_states_path="DEFAULT",
        env_img_res=256, seed=7, use_wandb=False, run_id_note="047-" + config["arm"],
        local_log_dir=str(output/"official_logs"))


class Observer:
    """Bookkeeping only; the original task/episode/action/video functions run."""
    def __init__(self, api, config, output, completed_before, identity):
        self.api, self.config, self.output = api, config, output
        self.completed_before, self.identity = completed_before, identity
        self.original = {name: getattr(api, name) for name in
                         ("initialize_model", "run_task", "run_episode", "get_action",
                          "save_rollout_video", "log_message")}
        self.task = None
        self.task_count = 0
        self.task_episodes = 0
        self.pending = None
        self.rows = []
        self.requests = 0
        self.episode_requests = 0
        self.loaded = False
        self.limit_per_episode = (c.HORIZONS[config["suite"]] + 7)//8
        self.row_stream = (output/"episodes.jsonl").open("x", encoding="utf-8")

    def progress(self, phase="evaluation"):
        n = len(self.rows)
        successes = sum(row["success"] for row in self.rows)
        value = {"phase": phase, "cell": c.cell_name(self.config["arm"], self.config["suite"]),
                 "cell_completed": n, "cell_expected": 500, "cell_percent": 100*n/500,
                 "total_completed": self.completed_before+n, "total_expected": 3000,
                 "total_percent": 100*(self.completed_before+n)/3000,
                 "live_successes": successes, "live_SR_percent": None if n == 0 else 100*successes/n,
                 "predict_calls": self.requests, "formal_complete": False}
        c.write(self.output/"progress.json", value)
        print("[047] " + json.dumps(value, ensure_ascii=False), flush=True)

    def initialize_model(self, cfg):
        c.require(not self.loaded, "047 native model initialized more than once")
        self.progress("loading_model")
        original_cwd = Path.cwd()
        try:
            # The official local loader searches ./prismatic when syncing its
            # isolated checkpoint view. Keep that search pointed at pinned OFT.
            os.chdir(self.config["repo_path"])
            result = self.original["initialize_model"](cfg)
        finally:
            os.chdir(original_cwd)
        model, action_head, proprio, _, _ = result
        key = c.expected_key(self.config["suite"], model.norm_stats)
        c.require(cfg.unnorm_key == key == self.identity["unnorm_key"]
                  and c.statistic_sha(model.norm_stats[key]) == self.identity["normalization_statistics_sha256"],
                  "047 actual native suite statistics differ")
        c.require(all(c.sha(Path(cfg.pretrained_checkpoint)/name) == digest
                      for name, digest in c.CODE_HASHES.items()), "047 isolated loaded model code differs")
        if self.config["arm"] == "h1":
            from .adapter import attach_h1
            attach_h1(model, action_head, proprio, self.identity["method_adapter"],
                      self.config["method_adapter"], cfg)
        self.loaded = True
        c.write(self.output/"model_identity.json", dict(
            self.identity, arm=self.config["arm"], checkpoint_original=self.config["checkpoint"],
            deployment_hint=False, official_cfg_lora_rank=cfg.lora_rank,
            training_lineage_preserved=True, native_pipeline=True))
        self.progress("model_loaded")
        return result

    def run_task(self, *args, **kwargs):
        bound = inspect.signature(self.original["run_task"]).bind(*args, **kwargs)
        values = bound.arguments
        suite, task_id = values["task_suite"], values["task_id"]
        c.require(self.loaded and suite.n_tasks == 10 and task_id == self.task_count,
                  "047 official task population/order differs")
        task = suite.get_task(task_id)
        self.task = {"task_id": task_id, "task_name": task.name, "instruction": task.language}
        self.task_episodes = 0
        value = self.original["run_task"](*args, **kwargs)
        c.require(self.task_episodes == 50 and self.pending is None,
                  "047 official task did not complete its50 videos")
        c.require(value == (len(self.rows), sum(row["success"] for row in self.rows)),
                  "047 official counters and observed outcomes differ")
        self.task_count += 1
        self.task = None
        return value

    def run_episode(self, *args, **kwargs):
        import numpy as np
        bound = inspect.signature(self.original["run_episode"]).bind(*args, **kwargs)
        bound.apply_defaults()
        values = bound.arguments
        c.require(self.task is not None and self.pending is None and self.task_episodes < 50,
                  "047 unexpected episode invocation")
        c.require(values["task_description"] == self.task["instruction"],
                  "047 official original language changed")
        initial = np.asarray(values["initial_state"])
        c.require(initial.ndim == 1 and initial.size > 0, "047 missing official initial state")
        self.pending = dict(self.task, suite=self.config["suite"], arm=self.config["arm"],
                            initial_state_index=self.task_episodes,
                            initial_state_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
                            initial_state_dtype=str(initial.dtype), initial_state_shape=list(initial.shape),
                            ordinal=len(self.rows)+1, success=None, video_path=None)
        self.task_episodes += 1
        self.episode_requests = 0
        try:
            value = self.original["run_episode"](*args, **kwargs)
            c.require(isinstance(value, tuple) and len(value) == 2 and type(value[0]) is bool,
                      "047 official episode return contract differs")
            self.pending.update(success=value[0], status="completed",
                                predict_calls=self.episode_requests, video_frames=len(value[1]))
            return value
        except BaseException as error:
            self.pending.update(status="execution_error", success=None,
                                error=f"{type(error).__name__}: {error}",
                                predict_calls=self.episode_requests)
            raise

    def get_action(self, *args, **kwargs):
        c.require(self.pending is not None and self.loaded, "047 action outside an episode")
        c.require(self.episode_requests < self.limit_per_episode
                  and self.requests < self.limit_per_episode*500, "047 native request ceiling exhausted")
        self.episode_requests += 1
        self.requests += 1
        # No manipulation of inputs, instructions, returned actions or queues.
        return self.original["get_action"](*args, **kwargs)

    def log_message(self, message, log_file=None):
        result = self.original["log_message"](message, log_file)
        if str(message).startswith("Episode error:"):
            # Native catches rollout errors. Surface them instead of publishing
            # a nominal500 SR that silently treats a software fault as policy.
            raise RuntimeError("047 official pipeline reported " + str(message))
        return result

    def save_rollout_video(self, *args, **kwargs):
        c.require(self.pending is not None and self.pending["status"] == "completed",
                  "047 video without completed native episode")
        bound = inspect.signature(self.original["save_rollout_video"]).bind(*args, **kwargs)
        bound.apply_defaults()
        c.require(bound.arguments["success"] is self.pending["success"]
                  and bound.arguments["task_description"] == self.pending["instruction"]
                  and bound.arguments["idx"] == len(self.rows)+1, "047 official video binding differs")
        value = self.original["save_rollout_video"](*args, **kwargs)
        path = Path(value).resolve()
        c.require(self.output in path.parents and path.is_file() and path.stat().st_size > 0,
                  "047 native video missing or outside isolated output")
        self.pending.update(video_path=str(path.relative_to(self.output)))
        self.rows.append(self.pending)
        self.row_stream.write(json.dumps(self.pending, ensure_ascii=False, allow_nan=False)+"\n")
        self.row_stream.flush()
        os.fsync(self.row_stream.fileno())
        self.pending = None
        self.progress()
        return value

    def replacements(self):
        return {name: getattr(self, name) for name in self.original}

    def close(self):
        if self.pending is not None:
            c.write(self.output/"unfinished_episode.json", self.pending)
        self.row_stream.close()


def summarize(config, identity, observer, native_rate, error):
    rows = observer.rows if observer else []
    n = len(rows)
    complete = (error is None and n == 500 and observer.task_count == 10
                and observer.pending is None and all(x["status"] == "completed" for x in rows))
    count = sum(row["success"] for row in rows)
    if complete:
        c.require(native_rate == count/500, "047 official return SR differs from observed native successes")
    tasks = []
    for task in range(10):
        values = [row for row in rows if row["task_id"] == task]
        tasks.append({"task_id": task, "task_name": values[0]["task_name"] if values else None,
                      "instruction": values[0]["instruction"] if values else None,
                      "completed": len(values), "expected": 50,
                      "successes": sum(x["success"] for x in values)})
    return {"schema_version": c.SCHEMA, "arm": config["arm"], "suite": config["suite"],
            "formal_complete": complete, "software_exit": "success" if complete else "failed",
            "execution_error": error, "completed": n, "expected": 500, "tasks": tasks,
            "formal_SR": {"numerator": count, "denominator": 500, "percent": count/5} if complete else None,
            "live_completed_SR": None if not rows else 100*count/n,
            "predict_calls": observer.requests if observer else 0,
            "predict_call_limit": ((c.HORIZONS[config["suite"]]+7)//8)*500,
            "model_identity": identity, "native_pipeline": True,
            "scorer": "official_env_done", "all_videos_required": True,
            "deployment_hint": False, "new_training_or_labels": False}


def run_cell(config_path, output, *, completed_before=0):
    config = c.load_config(config_path)
    output = c.validate_output(config, output, inputs=[config_path])
    c.require(type(completed_before) is int and completed_before in range(0, 2501, 500),
              "047 invalid completed-before count")
    identity = c.verify_inputs(config)
    output.mkdir(parents=True, exist_ok=False)
    c.write(output/"config.json", config)
    c.write(output/"started.json", {"config_sha256": c.sha(config_path), "completed_before": completed_before,
                                   "new_execution": True, "implicit_retry": False})
    observer = None
    original_cwd = Path.cwd()
    try:
        print("[047] START " + c.cell_name(config["arm"], config["suite"]) + " official500; loading", flush=True)
        api = import_official(config["repo_path"])
        with c.checkpoint_view(config["checkpoint"]) as view:
            os.chdir(output)
            native_config = make_native_config(api, config, view, output)
            c.require(api.TASK_MAX_STEPS[config["suite"]] == c.HORIZONS[config["suite"]],
                      "047 official horizon changed")
            observer = Observer(api, config, output, completed_before, identity)
            body = inspect.unwrap(api.eval_libero)
            c.require(body is not api.eval_libero, "047 native draccus wrapper cannot be unwrapped")
            with patches(api, observer.replacements()):
                rate = body(native_config)
            summary = summarize(config, identity, observer, rate, None)
            c.require(summary["formal_complete"], "047 native evaluation incomplete")
            summary["episodes_sha256"] = c.sha(output/"episodes.jsonl")
            c.write(output/"summary.json", summary)
            observer.progress("complete")
            c.write(output/"progress.json", {"phase": "complete", "formal_complete": True,
                     "cell_completed": 500, "cell_percent": 100.0,
                     "total_completed": completed_before+500, "total_expected": 3000,
                     "total_percent": 100*(completed_before+500)/3000,
                     "formal_SR": summary["formal_SR"]})
            print("[047] COMPLETE " + c.cell_name(config["arm"], config["suite"])
                  + f" SR={summary['formal_SR']['percent']:.2f}% (500/500)", flush=True)
            return summary
    except BaseException as error:
        c.write(output/"summary.json", summarize(config, identity, observer, None,
                                                f"{type(error).__name__}: {error}"))
        raise
    finally:
        if observer:
            observer.close()
        os.chdir(original_cwd)
