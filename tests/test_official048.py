"""048 is only a versioned two-cell scope of the existing native pipeline."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from test_official047 import inputs, native, write
from egrs.official047 import contracts as c


@pytest.fixture
def scope048(inputs, native, monkeypatch):
    configs = inputs.tmp/"configs048"
    for arm in ("base", "h1"):
        cfg = c.read(inputs.configs[(arm, "libero_spatial")])
        cfg.update(schema_version=c.LIBERO10_SCHEMA, suite="libero_10")
        write(configs/c.config_name(arm, "libero_10"), cfg)
    mapping = native.api.benchmark.get_benchmark_dict()
    mapping["libero_10"] = mapping["libero_spatial"]
    monkeypatch.setattr(native.api.benchmark, "get_benchmark_dict", lambda: mapping)
    return configs


def test048_profile_keeps_original047_default_unchanged():
    before = dict(c.HORIZONS), c.CELLS, c.SCHEMA, c.TOTAL
    spec = c.protocol("libero10")
    assert spec["total"] == 1000 and spec["horizons"] == {"libero_10": 520}
    assert spec["cells"] == (("base", "libero_10"), ("h1", "libero_10"))
    assert spec["module"] == "egrs.official048"
    assert before == (c.HORIZONS, c.CELLS, c.SCHEMA, c.TOTAL)
    assert c.protocol()["total"] == 3000 and len(c.protocol()["cells"]) == 6


@pytest.mark.parametrize("arm", ["base", "h1"])
def test048_actual_config_uses_original10_stats(inputs, scope048, arm):
    config = c.load_config(scope048/c.config_name(arm, "libero_10"))
    identity = c.verify_inputs(config)
    assert c.horizon(config) == 520 and identity["unnorm_key"] == "libero_10_no_noops"
    assert identity["research_adapter_loaded"] is (arm == "h1")


@pytest.mark.parametrize("schema,suite", [(c.SCHEMA, "libero_10"), (c.LIBERO10_SCHEMA, "libero_goal")])
def test048_schema_and_suite_cannot_silently_change_scope(inputs, schema, suite):
    path = inputs.configs[("base", "libero_goal")]
    cfg = c.read(path)
    cfg.update(schema_version=schema, suite=suite)
    write(path, cfg)
    with pytest.raises(ValueError, match="mismatch"):
        c.load_config(path)


def test048_two_full500_native_loops_all10_tasks_and_progress1000(inputs, native, scope048, monkeypatch):
    from egrs.official047 import launch
    from egrs.official047.runner import run_cell
    calls = []
    def execute(command, check):
        assert command[command.index("-m")+1] == "egrs.official048"
        args = command[command.index("run-cell")+1:]
        values = dict(zip(args[::2], args[1::2]))
        calls.append(values)
        run_cell(values["--config"], values["--output"], completed_before=int(values["--completed-before"]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch.subprocess, "run", execute)
    output = inputs.tmp/"official048"
    result = launch.run_all(scope048, output, scope="libero10")
    assert len(calls) == 2 and [int(x["--completed-before"]) for x in calls] == [0, 500]
    assert result["format"] == "task048-official-comparison-v1" and result["total_completed_episodes"] == 1000
    assert result["overall"]["base"]["denominator"] == result["overall"]["h1"]["denominator"] == 500
    assert len(result["tasks"]) == 10 and result["tasks"][5]["denominator"] == 50
    for arm in ("base", "h1"):
        p = output/c.cell_name(arm, "libero_10")
        summary = c.read(p/"summary.json")
        assert summary["schema_version"] == c.LIBERO10_SCHEMA
        assert summary["predict_call_limit"] == 32500
        assert len(list(p.glob("rollouts/fake/*.mp4"))) == 500
        assert c.read(p/"progress.json")["total_expected"] == 1000
        assert summary["model_identity"]["unnorm_key"] == "libero_10_no_noops"
    assert launch.progress(output, scope="libero10")["percent"] == 100
    assert c.read(output/"status.json")["expected_episodes"] == 1000
    assert sum(x[0] == "load" for x in native.events) == 2
    assert all(x[1] == "libero_10" and x[2] == "libero_10_no_noops"
               for x in native.events if x[0] == "action")
    with pytest.raises(ValueError):
        launch.run_all(scope048, output, scope="libero10")
    with pytest.raises(ValueError, match="scope"):
        launch.progress(output)


def test048_official520_timeout_is_normal_false_not_software_fault(inputs, native, scope048, monkeypatch):
    from egrs.official047.runner import Observer, patches, make_native_config
    cfg = c.load_config(scope048/"base-10.json")
    output = inputs.tmp/"horizon048"
    output.mkdir()
    monkeypatch.chdir(output)
    observer = Observer(native.api, cfg, output, 0, c.verify_inputs(cfg))
    observer.loaded = True
    observer.task = {"task_id": 5, "task_name": "native_task_5", "instruction": "original instruction 5"}
    observation = {"robot0_eef_pos": np.zeros(3), "robot0_eef_quat": np.zeros(4),
                   "robot0_gripper_qpos": np.zeros(2)}
    steps = []
    env = SimpleNamespace(reset=lambda: None, set_init_state=lambda _: observation,
        step=lambda a: (steps.append(a) or (observation, 0, False, {})))
    policy = inputs.policy()
    config = make_native_config(native.api, cfg, str(inputs.checkpoint), output)
    native.api.check_unnorm_key(config, policy.model)
    try:
        with patches(native.api, observer.replacements()):
            success, images = native.api.run_episode(config, env, observer.task["instruction"],
                policy.model, 224, initial_state=np.asarray([5., 0., 1.]))
            native.api.save_rollout_video(images, 1, success, observer.task["instruction"])
        assert success is False and len(steps) == 530 and observer.requests == 65
        assert observer.rows[0]["status"] == "completed"
        progress = c.read(output/"progress.json")
        assert progress["total_expected"] == 1000 and progress["total_percent"] == .1
    finally:
        observer.close()


def test048_scope_mismatch_before_any_execution(inputs, scope048, monkeypatch):
    from egrs.official047 import launch
    calls = []
    monkeypatch.setattr(launch.subprocess, "run", lambda *a, **k: calls.append(a))
    with pytest.raises(FileNotFoundError):
        launch.run_all(scope048, inputs.tmp/"wrong-scope")
    assert calls == []


def test048_progress_before_start_is1000_not3000(tmp_path):
    from egrs.official047.launch import progress
    assert progress(tmp_path/"not-started", scope="libero10") == {
        "status": "not_started", "completed": 0, "expected": 1000, "percent": 0.0}


@pytest.mark.parametrize("arm", ["base", "h1"])
def test048_templates(arm):
    path = Path(__file__).parent.parent/"configs/official048"/(arm+"-10.example.json")
    cfg = c.load_config(path)
    assert cfg["schema_version"] == c.LIBERO10_SCHEMA and cfg["suite"] == "libero_10"
