"""Toy CPU tensors plus the unchanged real official runner with fake devices."""
from copy import deepcopy
from dataclasses import dataclass
import functools
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

from egrs.official047 import contracts as c


class Tiny(nn.Module):
    def __init__(self, stats):
        super().__init__()
        attention = nn.Module()
        for name in ("q_proj", "k_proj", "v_proj", "o_proj"):
            setattr(attention, name, nn.Linear(3, 3))
        layer = nn.Module()
        layer.self_attn = attention
        self.language_model = nn.Module()
        self.language_model.model = nn.Module()
        self.language_model.model.layers = nn.ModuleList([layer])
        self.norm_stats = deepcopy(stats)
        self.llm_dim = 3

    def forward(self, value):
        for module in self.language_model.model.layers[0].self_attn.children():
            value = module(value)
        return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    from egrs.hint043 import adapter
    repo, checkpoint = tmp_path/"upstream", tmp_path/"checkpoint"
    repo.mkdir()
    checkpoint.mkdir()
    # Deployment includes this unchanged source; tests exercise its real loops.
    original = Path(__file__).parent/"fixtures/official047/run_libero_eval.py"
    source_hashes = {}
    for name, digest in c.SOURCE_HASHES.items():
        path = repo/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original.read_bytes() if name.endswith("run_libero_eval.py") else b"# stub dependency\n")
        source_hashes[name] = c.sha(path)
    assert source_hashes["experiments/robot/libero/run_libero_eval.py"] == c.SOURCE_HASHES["experiments/robot/libero/run_libero_eval.py"]
    monkeypatch.setattr(c, "SOURCE_HASHES", source_hashes)
    monkeypatch.setattr(c.subprocess, "check_output", lambda *a, **k: c.REVISION+"\n")
    stats = {suite+"_no_noops": {"action": {"q01": [float(i)], "q99": [float(i+1)]}}
             for i, suite in enumerate([*c.HORIZONS, "libero_10"])}
    write(checkpoint/"dataset_statistics.json", stats)
    stats_sha = c.sha(checkpoint/"dataset_statistics.json")
    monkeypatch.setattr(c, "STATS_SHA", stats_sha)
    monkeypatch.setattr(adapter, "RETENTION_STATS_SHA", stats_sha)
    components, code = {}, {}
    for name in c.COMPONENT_HASHES:
        (checkpoint/name).write_bytes(name.encode())
        components[name] = c.sha(checkpoint/name)
    monkeypatch.setattr(c, "COMPONENT_HASHES", components)
    for name in c.CODE_HASHES:
        (checkpoint/name).write_text("{}" if name.endswith(".json") else "# fixture\n")
        code[name] = c.sha(checkpoint/name)
    monkeypatch.setattr(c, "CODE_HASHES", code)
    def policy():
        return SimpleNamespace(model=Tiny(stats), action_head=nn.Linear(3, 1),
            proprio_projector=nn.Linear(8, 3), metadata={
                "repo_commit": c.REVISION, "checkpoint_source": deepcopy(c.BASE_SOURCE),
                "dataset_statistics_sha256": stats_sha, "component_checkpoint_sha256": components,
                "unnorm_key": "libero_10_no_noops",
                "normalization_statistics_sha256": c.statistic_sha(stats["libero_10_no_noops"])})
    toy = policy()
    adapter.install(toy)
    for name, parameter in toy.model.named_parameters():
        if name.endswith(".lora_B"):
            parameter.data.fill_(0.1)
    directory = tmp_path/"h1"
    parent = {"update": 1000, "arm": "h1", **{k: "a"*64 for k in
              ("adapter_sha256", "training_state_sha256", "identity_sha256", "run_config_sha256")}}
    identity = adapter.save_adapter(toy, directory, arm="h1", update=3000, sidecar_identity="f"*64,
        reference_calls={"train": 24000, "dev": 0, "total": 24000, "budget": 27072},
        model_calls={"main_train": 60000, "aux_train": 0, "main_dev": 0, "aux_dev": 0,
                     "total": 60000, "budget": 81216}, target_updates=3000, continuation_parent=parent)
    monkeypatch.setattr(c, "ADAPTER_SHA", identity["adapter_sha256"])
    configs = {}
    config_dir = tmp_path/"configs"
    for arm, suite in c.CELLS:
        cfg = {"schema_version": c.SCHEMA, "arm": arm, "suite": suite, "repo_path": str(repo),
               "checkpoint": str(checkpoint), "method_adapter": str(directory) if arm == "h1" else None}
        path = config_dir/c.config_name(arm, suite)
        write(path, cfg)
        configs[(arm, suite)] = path
    return SimpleNamespace(repo=repo, checkpoint=checkpoint, adapter=directory, identity=identity,
                           policy=policy, stats=stats, configs=configs, config_dir=config_dir,
                           toy=toy, tmp=tmp_path)


@pytest.mark.parametrize("arm,suite", c.CELLS)
def test_file_binding_chooses_native_suite_not_training_stats(inputs, arm, suite):
    cfg = c.load_config(inputs.configs[(arm, suite)])
    identity = c.verify_inputs(cfg)
    assert identity["unnorm_key"] == suite+"_no_noops"
    assert identity["research_adapter_loaded"] is (arm == "h1")
    if arm == "h1":
        assert identity["method_adapter"]["base_lineage"]["unnorm_key"] == "libero_10_no_noops"


@pytest.mark.parametrize("field,value", [
    ("suite", "libero_90"), ("arm", "h0"), ("schema_version", "old"), ("extra", True),
    ("method_adapter", "/some/research/adapter"), ("repo_path", "relative/path")])
def test_config_rejects_unapproved_protocol(inputs, field, value):
    path = inputs.configs[("base", "libero_spatial")]
    cfg = c.read(path)
    cfg[field] = value
    write(path, cfg)
    with pytest.raises(ValueError):
        c.load_config(path)


@pytest.mark.parametrize("what", ["source", "stats", "component", "code", "adapter"])
def test_changed_files_rejected(inputs, what):
    cfg = c.load_config(inputs.configs[("h1", "libero_goal")])
    path = {"source": inputs.repo/next(iter(c.SOURCE_HASHES)),
            "stats": inputs.checkpoint/"dataset_statistics.json",
            "component": inputs.checkpoint/next(iter(c.COMPONENT_HASHES)),
            "code": inputs.checkpoint/"config.json", "adapter": inputs.adapter/"adapter.pt"}[what]
    path.write_bytes(path.read_bytes()+b"\n")
    with pytest.raises(ValueError):
        c.verify_inputs(cfg)


@pytest.mark.parametrize("suite", c.HORIZONS)
def test_cross_suite_attach_exact_tensors_rng_and_old_identity_unchanged(inputs, suite):
    from egrs.official047.adapter import attach_h1
    from egrs.augmentation.oft import LoRALinear
    p = inputs.policy()
    cfg = SimpleNamespace(unnorm_key=suite+"_no_noops", task_suite_name=suite)
    before = c.sha(inputs.adapter/"identity.json")
    torch.manual_seed(41)
    expected = torch.rand(3)
    torch.manual_seed(41)
    attach_h1(p.model, p.action_head, p.proprio_projector, inputs.identity, inputs.adapter, cfg)
    assert torch.equal(torch.rand(3), expected)
    assert c.sha(inputs.adapter/"identity.json") == before
    assert cfg.unnorm_key == suite+"_no_noops"
    assert all(not v.requires_grad for v in p.model.parameters()) and not p.model.training
    actual = {n: v for n, v in p.model.named_parameters() if n.endswith((".lora_A", ".lora_B"))}
    for name, tensor in actual.items():
        assert torch.equal(tensor, dict(inputs.toy.model.named_parameters())[name])
    assert sum(isinstance(x, LoRALinear) for x in p.model.modules()) == 4
    with pytest.raises(ValueError):
        attach_h1(p.model, p.action_head, p.proprio_projector, inputs.identity, inputs.adapter, cfg)


def test_cross_suite_does_not_relax_old_restore(inputs):
    from egrs.hint043.adapter import install, restore
    p = inputs.policy()
    p.metadata["unnorm_key"] = "libero_object_no_noops"
    p.metadata["normalization_statistics_sha256"] = c.statistic_sha(inputs.stats["libero_object_no_noops"])
    install(p)
    with pytest.raises(ValueError, match="Original base"):
        restore(p, inputs.adapter)


@pytest.mark.parametrize("change", ["train_stats", "eval_stats", "tensor_hash"])
def test_bad_training_or_inference_or_tensor_identity_rejected(inputs, change):
    from egrs.official047.adapter import attach_h1
    p = inputs.policy()
    identity = deepcopy(inputs.identity)
    cfg = SimpleNamespace(unnorm_key="libero_spatial_no_noops", task_suite_name="libero_spatial")
    if change == "train_stats":
        p.model.norm_stats["libero_10_no_noops"] = {}
    elif change == "eval_stats":
        cfg.unnorm_key = "libero_10_no_noops"
    else:
        identity["tensor_sha256"][next(iter(identity["tensor_sha256"]))] = "0"*64
    with pytest.raises(ValueError):
        attach_h1(p.model, p.action_head, p.proprio_projector, identity, inputs.adapter, cfg)


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    return result


@pytest.fixture
def native(inputs, monkeypatch):
    """Execute the original runner unchanged; dependency calls are fake."""
    events = []
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    observation = {"agentview_image": image, "robot0_eye_in_hand_image": image,
                   "robot0_eef_pos": np.zeros(3), "robot0_eef_quat": np.zeros(4),
                   "robot0_gripper_qpos": np.zeros(2)}
    class Env:
        def reset(self):
            self.steps = 0
            return observation
        def set_init_state(self, state):
            events.append(("init", np.asarray(state).tolist()))
            return observation
        def step(self, action):
            self.steps += 1
            return observation, 0, True, {}
    class Suite:
        n_tasks = 10
        def get_task(self, i):
            return SimpleNamespace(name=f"native_task_{i}", language=f"original instruction {i}")
        def get_task_init_states(self, i):
            return np.asarray([[i, j, 1.] for j in range(50)], dtype=np.float64)
    def get_env(task, family, resolution):
        events.append(("env", task.name, family, resolution))
        return Env(), task.language
    def get_model(cfg):
        events.append(("load", cfg.task_suite_name, cfg.lora_rank))
        return inputs.policy().model
    def action(cfg, model, obs, instruction, **kwargs):
        events.append(("action", cfg.task_suite_name, cfg.unnorm_key, instruction))
        return np.zeros((8, 7))
    def video(rollout_images, idx, success, task_description, log_file=None):
        p = Path("rollouts/fake")/f"{idx}.mp4"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"fake video; no renderer or codec")
        return str(p)
    def wrap():
        def decorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapped
        return decorator
    for name in ("experiments", "experiments.robot", "experiments.robot.libero",
                 "libero", "libero.libero", "prismatic", "prismatic.vla"):
        p = module(name)
        p.__path__ = []
        monkeypatch.setitem(sys.modules, name, p)
    robot = module("experiments.robot.robot_utils", DATE_TIME="fixed",
        get_action=action, get_image_resize_size=lambda cfg: 224, get_model=get_model,
        invert_gripper_action=lambda a: a, normalize_gripper_action=lambda a, **k: a,
        set_seed_everywhere=lambda seed: events.append(("seed", seed)))
    utils = module("experiments.robot.libero.libero_utils", get_libero_dummy_action=lambda _: [0]*7,
        get_libero_env=get_env, get_libero_image=lambda _: image, get_libero_wrist_image=lambda _: image,
        quat2axisangle=lambda _: np.zeros(3), save_rollout_video=video)
    vla = module("experiments.robot.openvla_utils",
        get_action_head=lambda *a, **k: nn.Linear(3, 1),
        get_noisy_action_projector=lambda *a, **k: None,
        get_processor=lambda cfg: object(), get_proprio_projector=lambda *a, **k: nn.Linear(8, 3),
        resize_image_for_policy=lambda a, b: a)
    for m, rel in ((robot, "experiments/robot/robot_utils.py"),
                   (utils, "experiments/robot/libero/libero_utils.py"),
                   (vla, "experiments/robot/openvla_utils.py")):
        m.__file__ = str(inputs.repo/rel)
        monkeypatch.setitem(sys.modules, m.__name__, m)
    for name, m in {
        "draccus": module("draccus", wrap=wrap),
        "tqdm": module("tqdm", tqdm=lambda x: x),
        "wandb": module("wandb"),
        "libero.libero.benchmark": module("libero.libero.benchmark",
            get_benchmark_dict=lambda: {suite: Suite for suite in c.HORIZONS}),
        "prismatic.vla.constants": module("prismatic.vla.constants", NUM_ACTIONS_CHUNK=8),
    }.items():
        monkeypatch.setitem(sys.modules, name, m)
    name = "experiments.robot.libero.run_libero_eval"
    spec = importlib.util.spec_from_file_location(name, inputs.repo/"experiments/robot/libero/run_libero_eval.py")
    api = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, api)
    spec.loader.exec_module(api)
    assert c.sha(api.__file__) == "701a20b6ca2942aa36e0e7d567b25647268b936a23af79c5893534f10bec7802"
    return SimpleNamespace(api=api, events=events, original_action=action)


@pytest.mark.parametrize("arm", ["base", "h1"])
def test_original_full500_pipeline_model_identity_videos_and_hooks_restore(inputs, native, arm):
    from egrs.official047.runner import run_cell
    from egrs.official047.launch import verify_cell
    originals = {k: getattr(native.api, k) for k in
                 ("run_task", "run_episode", "initialize_model", "get_action", "save_rollout_video", "log_message")}
    out = inputs.tmp/("output-"+arm)
    result = run_cell(inputs.configs[(arm, "libero_spatial")], out)
    assert result["formal_SR"] == {"numerator": 500, "denominator": 500, "percent": 100.}
    summary, rows = verify_cell(out, c.load_config(inputs.configs[(arm, "libero_spatial")]))
    assert len(rows) == len(list(out.glob("rollouts/fake/*.mp4"))) == 500
    assert result["predict_calls"] == 500
    assert len([x for x in native.events if x[0] == "load"]) == 1
    assert len([x for x in native.events if x[0] == "init"]) == 500
    assert all(x[2] == "libero_spatial_no_noops" for x in native.events if x[0] == "action")
    assert summary["model_identity"]["research_adapter_loaded"] is (arm == "h1")
    assert all(getattr(native.api, k) is f for k, f in originals.items())
    assert c.read(out/"progress.json")["formal_complete"] is True
    with pytest.raises(ValueError, match="existing"):
        run_cell(inputs.configs[(arm, "libero_spatial")], out)


def test_native_caught_model_error_is_technical_failure_not_zero_SR(inputs, native, monkeypatch):
    from egrs.official047.runner import run_cell
    def broken(*args, **kwargs):
        raise RuntimeError("fake inference problem")
    monkeypatch.setattr(native.api, "get_action", broken)
    out = inputs.tmp/"failed"
    with pytest.raises(RuntimeError, match="official pipeline reported"):
        run_cell(inputs.configs[("base", "libero_spatial")], out)
    summary = c.read(out/"summary.json")
    assert not summary["formal_complete"] and summary["formal_SR"] is None
    assert summary["completed"] == 0 and summary["software_exit"] == "failed"
    assert c.read(out/"unfinished_episode.json")["status"] == "execution_error"
    assert native.api.get_action is broken


def test_real_installed_draccus_is_unwrappable():
    import draccus
    @dataclass
    class Config:
        value: int = 1
    @draccus.wrap()
    def target(cfg: Config):
        return cfg.value
    assert inspect.unwrap(target)(Config()) == 1


def test_one_launch_delegates_all_six_original500_and_pairs_same_initial_states(inputs, native, monkeypatch):
    from egrs.official047.runner import run_cell
    from egrs.official047 import launch
    calls = []
    def execute(command, check):
        assert not check
        args = command[command.index("run-cell")+1:]
        values = dict(zip(args[::2], args[1::2]))
        calls.append(c.load_config(values["--config"]))
        run_cell(values["--config"], values["--output"], completed_before=int(values["--completed-before"]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch.subprocess, "run", execute)
    out = inputs.tmp/"six"
    result = launch.run_all(inputs.config_dir, out)
    assert [(x["arm"], x["suite"]) for x in calls] == list(c.CELLS)
    assert result["total_completed_episodes"] == 3000 and len(result["tasks"]) == 30
    assert result["overall"]["base"]["denominator"] == result["overall"]["h1"]["denominator"] == 1500
    assert all(x["paired"]["both"] == 500 for x in result["suites"].values())
    assert c.read(out/"status.json")["status"] == "complete"
    assert launch.progress(out)["percent"] == 100
    assert len(list(out.glob("*/rollouts/fake/*.mp4"))) == 3000
    with pytest.raises(ValueError):
        launch.run_all(inputs.config_dir, out)


def test_launch_stops_on_first_error_and_preserves_marker(inputs, native, monkeypatch):
    from egrs.official047 import launch
    calls = []
    monkeypatch.setattr(launch.subprocess, "run",
                        lambda command, check: (calls.append(command) or SimpleNamespace(returncode=9)))
    out = inputs.tmp/"stopped"
    with pytest.raises(ValueError, match="next cell not started"):
        launch.run_all(inputs.config_dir, out)
    assert len(calls) == 1
    assert c.read(out/"status.json")["status"] == "failed"
    assert launch.progress(out)["status"] == "failed"


def test_existing_input_directories_protected_and_checkpoint_view_keeps_original(inputs):
    cfg = c.load_config(inputs.configs[("base", "libero_goal")])
    for output in (inputs.checkpoint, inputs.repo/"inside", inputs.tmp):
        with pytest.raises(ValueError):
            c.validate_output(cfg, output)
    original = (inputs.checkpoint/"config.json").read_bytes()
    with c.checkpoint_view(inputs.checkpoint) as view:
        (Path(view)/"config.json").write_text('{"isolated":true}')
    assert (inputs.checkpoint/"config.json").read_bytes() == original


@pytest.mark.parametrize("suite,horizon", list(c.HORIZONS.items()))
def test_official_horizon_false_is_valid_policy_outcome_and_chunk_ceiling(inputs, native, suite, horizon, monkeypatch):
    from egrs.official047.runner import Observer, make_native_config, patches
    cfg = c.load_config(inputs.configs[("base", suite)])
    output = inputs.tmp/"false-outcome"
    output.mkdir()
    monkeypatch.chdir(output)
    observer = Observer(native.api, cfg, output, 0, c.verify_inputs(cfg))
    observer.loaded = True
    observer.task = {"task_id": 0, "task_name": "native_task_0", "instruction": "original instruction 0"}
    observation = {"robot0_eef_pos": np.zeros(3), "robot0_eef_quat": np.zeros(4),
                   "robot0_gripper_qpos": np.zeros(2)}
    steps = []
    env = SimpleNamespace(reset=lambda: None, set_init_state=lambda _: observation,
        step=lambda action: (steps.append(action) or (observation, 0, False, {})))
    policy = inputs.policy()
    config = make_native_config(native.api, cfg, str(inputs.checkpoint), output)
    native.api.check_unnorm_key(config, policy.model)
    try:
        with patches(native.api, observer.replacements()):
            success, images = native.api.run_episode(config, env, "original instruction 0",
                policy.model, 224, initial_state=np.array([0., 0., 1.]))
            assert success is False and observer.pending["status"] == "completed"
            native.api.save_rollout_video(images, 1, success, "original instruction 0")
        assert observer.rows[0]["success"] is False
        assert len(steps) == horizon+10
        assert observer.requests == (horizon+7)//8
        assert c.read(output/"progress.json")["live_SR_percent"] == 0
    finally:
        observer.close()


def test_missing_video_is_software_incomplete_not_success(inputs, native, monkeypatch):
    from egrs.official047.runner import run_cell
    monkeypatch.setattr(native.api, "save_rollout_video", lambda rollout_images, idx, success,
                        task_description, log_file=None: "missing.mp4")
    output = inputs.tmp/"missing-video"
    with pytest.raises(ValueError, match="video missing"):
        run_cell(inputs.configs[("base", "libero_spatial")], output)
    summary = c.read(output/"summary.json")
    assert summary["formal_SR"] is None and not summary["formal_complete"]
    assert (output/"unfinished_episode.json").is_file()


@pytest.mark.parametrize("name", ["base-spatial", "h1-spatial", "base-object", "h1-object", "base-goal", "h1-goal"])
def test_six_deployment_templates_use_only_approved_fields(name):
    path = Path(__file__).parent.parent/"configs/official047"/(name+".example.json")
    cfg = c.load_config(path)
    assert c.cell_name(cfg["arm"], cfg["suite"]) == name


def test_progress_when_not_started_and_without_native_imports(tmp_path):
    from egrs.official047.launch import progress
    assert progress(tmp_path/"not-created") == {
        "status": "not_started", "completed": 0, "expected": 3000, "percent": 0.0}
