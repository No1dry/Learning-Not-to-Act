"""035 orchestration with pinned readers and CPU-only execution boundaries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest


@pytest.fixture
def core(monkeypatch):
    from egrs.augmentation.dependencies import activate_core, activate_reporting
    root = Path(__file__).resolve().parents[2]
    activate_core(root / "LIBERO-Remain-task033-r2")
    activate_reporting(root / "LIBERO-Remain-task034")
    monkeypatch.syspath_prepend(str(root / "LIBERO-Remain-task033-r2"))
    return root


def adapter():
    return {"schema_version": "task035-oft-adapter-v1", "group": "robot_rewind_mix",
            "recipe": "robot_rewind_mix", "data_kind": "task035-generated-trajectories-v1",
            "update": 1000, "final_update": 1000, "adapter_sha256": "a" * 64}


@pytest.fixture
def ready_config(tmp_path, monkeypatch, core):
    from egrs.trajectory_augmentation import evaluation as ev
    from egrs.augmentation import adapter_identity
    from benchmark.remaining_goals.headless import planning, scoped_planning, nine_planning, scoped_sources
    from benchmark.remaining_goals.nine_catalog import REUSE_TASKS
    from tests.test_headless_workflow import configuration
    cfg = planning.read_json(configuration(tmp_path, monkeypatch))
    monkeypatch.setattr(adapter_identity, "read_adapter_identity", lambda path: adapter())
    def legacy(task, origin, **kwargs):
        value = {"episodes": [deepcopy(e) for e in nine_planning.expected_episodes("nine-mask10") if e["task_id"] == task],
                 "source": origin, "protocol": "mask10"}
        value["source_plan_sha256"] = planning.canonical_hash(value)
        return value
    monkeypatch.setattr(planning, "source_plan", legacy)
    def inventory(path, protocol):
        expected = (scoped_planning.expected_episodes(protocol) if protocol == "normal00-control"
                    else nine_planning.expected_episodes(protocol))
        return {}, {(e["task_id"], e["initial_state_index"]): {"manifest": str(tmp_path / "sources/manifest.json")}
                    for e in expected}
    monkeypatch.setattr(nine_planning, "read_sources", inventory)
    monkeypatch.setattr(scoped_planning, "read_composite", inventory)
    def scoped(protocol, task, index, origin):
        expected = (scoped_planning.expected_episodes(protocol) if protocol == "normal00-control"
                    else nine_planning.expected_episodes(protocol))
        source = {"protocol": protocol, "source": origin,
                  "episodes": [deepcopy(next(e for e in expected if e["task_id"] == task and e["initial_state_index"] == index))]}
        source["source_plan_sha256"] = planning.canonical_hash(source)
        return source
    monkeypatch.setattr(scoped_sources, "resolve_source", scoped)
    value = {"schema_version": ev.SCHEMA, "group": "robot_rewind_mix", "benchmark_root": str(core / "LIBERO-Remain-task033-r2"),
             "reporting_root": str(core / "LIBERO-Remain-task034"), "base_runtime": cfg["runtime_config"],
             "adapter": "adapter/update-001000", "legacy_sources_10": {t: cfg["sources"][t] for t in REUSE_TASKS},
             "legacy_sources_00": "legacy00.json", "new_sources_10": "nine10.json", "new_sources_00": "nine00.json"}
    path = tmp_path / "eval.json"
    path.write_text(json.dumps(value))
    return path


def test_plan_retains_exact_original_dual_population_and_protocols(ready_config):
    from egrs.trajectory_augmentation import evaluation as ev
    plan = ev.build_plan(ready_config)
    assert {k: len(v) for k, v in plan["expected"].items()} == {"10": 90, "00": 90}
    assert len({e["episode_id"] for t in plan["tasks"] for e in t["source"]["episodes"]}) == 180
    assert len(plan["tasks"]) == 126
    assert sum(len(t["source"]["episodes"]) for t in plan["tasks"] if not t["scoped"]) == 60
    assert {t["source"]["protocol"] for t in plan["tasks"] if t["condition"] == "00"} == {"normal00-control", "nine-normal00"}
    assert not plan["simulation_created"] and not plan["weights_loaded"]
    assert plan["adapter_identity"] == adapter()


@pytest.mark.parametrize("changed", [{"update": 750}, {"final_update": 2000}, {"schema_version": "task030-oft-adapter-v1"},
                                     {"recipe": "raw_control"}, {"data_kind": "ordinary"}])
def test_earlier_or_foreign_adapter_is_rejected_before_execution(ready_config, monkeypatch, changed):
    from egrs.trajectory_augmentation import evaluation as ev
    from egrs.augmentation import adapter_identity
    monkeypatch.setattr(adapter_identity, "read_adapter_identity", lambda p: {**adapter(), **changed})
    with pytest.raises(ValueError, match="adapter"):
        ev.build_plan(ready_config)


def test_plan_rejects_source_with_wrong_condition(ready_config, monkeypatch):
    from egrs.trajectory_augmentation import evaluation as ev
    from benchmark.remaining_goals.headless import scoped_sources
    original = scoped_sources.resolve_source
    def wrong(*args):
        source = original(*args)
        source["episodes"][0]["initial_mask"] = [True, False]
        return source
    monkeypatch.setattr(scoped_sources, "resolve_source", wrong)
    with pytest.raises(ValueError, match="population|identity"):
        ev.build_plan(ready_config)


@pytest.mark.parametrize("pause", [True, False])
def test_run_uses_one_condition_neutral_worker_and_stops_after_technical_pause(ready_config, tmp_path, monkeypatch, pause):
    from egrs.trajectory_augmentation import evaluation as ev
    from benchmark.remaining_goals.headless import workflow
    from benchmark.remaining_goals import isolated_policy
    workers, calls = [], []
    class Policy:
        def __init__(self, config):
            self.config, self.closed = config, False
            self.provenance = {"policy_metadata": {"method_adapter": adapter()}}
            workers.append(self)
        def close(self): self.closed = True
    monkeypatch.setattr(isolated_policy, "SubprocessPolicy", Policy)
    def execute(directory, source, runtime, identity, bind, **kwargs):
        calls.append((source, kwargs["shared_policy"]))
        return {"status": "technical_pause" if pause and len(calls) == 2 else "completed", "error": None}
    monkeypatch.setattr(workflow, "_run_task", execute)
    output = tmp_path / "run"
    if pause:
        with pytest.raises(RuntimeError, match="technical"):
            ev.run(ready_config, output)
    else:
        ev.run(ready_config, output)
        assert sum(len(s["episodes"]) for s, _ in calls) == 180
        assert {s.get("protocol") for s, _ in calls} == {"mask10", "normal00-control", "nine-mask10", "nine-normal00"}
    assert len(workers) == 1 and workers[0].closed and len(calls) == (2 if pause else 126)
    assert all(p is workers[0] for _, p in calls)
    assert not {"condition", "domain", "initial_mask", "task_semantics"} & workers[0].config.keys()
    assert workers[0].config["method_adapter"].endswith("update-001000")
    report = json.loads((output / "summary.json").read_text())
    assert report["conditions"]["10"]["report"]["counts"]["formal_SR"] is None
    assert report["conditions"]["00"]["delta_percentage_points"] is None
    with pytest.raises(FileExistsError): ev.run(ready_config, output)


def test_reports_keep_034_binary10_and_official00_distinct(tmp_path, core):
    from egrs.trajectory_augmentation import evaluation as ev
    from benchmark.remaining_goals.headless.nine_planning import expected_episodes
    from benchmark.remaining_goals.headless.planning import file_sha
    proof = tmp_path / "proof.json"; proof.write_text("verified fixture")
    records = {}
    for bits in ("10", "00"):
        records[bits] = {}
        for index, ep in enumerate(expected_episodes("nine-mask10" if bits == "10" else "nine-normal00")):
            # 00 legacy failure (e.g. unreleased), official true: still native success.
            row = {**ep, "execution_status": "completed", "classification": "unknown" if bits == "10" else "success",
                   "official_goals_achieved": True, "failure_reasons": [], "unknown_reasons": [], "path_complete": False}
            records[bits][ep["episode_id"]] = {"condition": bits, "primary": row, "legacy": {**row, "classification": "failure"},
                "source": {"model_identity": {"policy_metadata": {"method_adapter": adapter(), "unnorm_key": "libero_10_no_noops"}}, "verified_files": [{"path": str(proof), "sha256": file_sha(proof)}],
                           "input_evidence_level": "verified fixture", "original_protocol": "remaining-headless-normal00-control-v1"}}
    report = ev.make_report(records, adapter())
    ten, normal = report["conditions"]["10"], report["conditions"]["00"]
    assert ten["report"]["counts"]["formal_SR"]["numerator"] == 0
    assert normal["report"]["conditions"]["00"]["official_task_SR"]["numerator"] == 90
    assert normal["report"]["conditions"]["00"]["compliant_task_SR"] is None
    assert ten["baseline"]["numerator"] == 22 and normal["baseline"]["numerator"] == 78
    assert ten["delta_percentage_points"] == pytest.approx(-100 * 22 / 90)
    assert normal["delta_percentage_points"] == pytest.approx(100 * 12 / 90)


@pytest.mark.parametrize("protocol", ["mask10", "normal00-control", "nine-mask10", "nine-normal00"])
@pytest.mark.parametrize('reader_version',['v1','v2','v3'])
def test_original_readers_verify_archive_actions_observations_and_video(tmp_path, monkeypatch, core, protocol,reader_version):
    from egrs.trajectory_augmentation import evaluation as ev
    from benchmark.remaining_goals.headless import workflow, planning
    from tests.test_headless_workflow import configuration, execution
    from tests.test_headless_source_acceptance import make_source, tree_hash
    from tests.test_headless_runner import synthetic_measurement_validator
    runtime = planning.read_json(planning.read_json(configuration(tmp_path, monkeypatch))["runtime_config"])
    if protocol == "mask10":
        synthetic_measurement_validator.__wrapped__(monkeypatch)
        mp, rp, _, _ = make_source(tmp_path / "original")
        source = planning.source_plan("basket", {"manifest": str(mp), "candidate_replay": str(rp)}, acceptance=planning.MASK10_ACCEPTANCE)
        made, envs = execution(monkeypatch)
        scoped = False
    elif protocol == "normal00-control":
        from tests.test_headless_scoped_sources import selected, normal_source
        from tests.test_headless_normal00_runtime import NormalEnv, synthetic_measurements
        from benchmark.remaining_goals.headless import scoped_sources
        synthetic_measurements.__wrapped__(monkeypatch)
        selection = selected.__wrapped__(tmp_path / "original")
        _, _, origin = normal_source(selection)
        source = scoped_sources.resolve_source(protocol, "frypan_stove9", 0, origin)
        made, envs = execution(monkeypatch)
        def normal_env(config):
            value = NormalEnv(); value.close = lambda: None
            return value
        monkeypatch.setattr(workflow, "make_environment", normal_env)
        scoped = True
    else:
        from tests.test_headless_nine_integration import make_nine_source, NineGeometryEnv
        from tests import test_headless_environment as native_fixtures
        from benchmark.remaining_goals.nine_catalog import get_task
        from benchmark.remaining_goals.headless import environment, scoped_sources
        monkeypatch.setattr(environment, "_callback_status", lambda: "absent")
        task = "bowl_drawer_close"
        origin = make_nine_source(tmp_path / "original", monkeypatch, task, protocol)
        source = scoped_sources.resolve_source(protocol, task, 0, origin)
        profile = get_task(task)
        monkeypatch.setitem(native_fixtures.TASKS, task, {**profile, "goals": profile["goals"] + [{"predicates": profile["invariant_predicates"]}]})
        made, envs = execution(monkeypatch)
        monkeypatch.setattr(workflow, "make_environment", lambda config: NineGeometryEnv(config))
        scoped = True
    before = tree_hash(tmp_path / "original")
    policy = workflow.make_policy(runtime)
    policy.provenance["policy_metadata"]["method_adapter"] = adapter()
    plan = {"plan_sha256": "c" * 64, "base_runtime": runtime, "adapter_identity": adapter()}
    target = tmp_path / "executed"
    metadata = workflow._run_task(target, source, runtime, plan["plan_sha256"], lambda identity: None, scoped=scoped, shared_policy=policy)
    assert metadata["status"] == "completed", metadata["error"]
    item = {"source": source, "scoped": scoped}
    kwargs={}
    if reader_version in ('v2','v3'):
        from egrs.trajectory_augmentation import environment_dispatch as dispatch
        binding={'implementation':'fake-reader-boundary','expected_environment':source['environment_config']['environment']}
        plan.update(schema_version=ev.SCHEMA_V3 if reader_version=='v3' else ev.SCHEMA_V2,
                    environment_dispatch={'identity':'d'*64})
        item['environment_binding']=binding
        monkeypatch.setattr(dispatch,'binding_for',lambda *a:deepcopy(binding))
        record={'schema_version':'task035-environment-dispatch-record-v1','plan_sha256':plan['plan_sha256'],
            'source_plan_sha256':source['source_plan_sha256'],'binding':binding,
            'status':'constructed','actual_environment':binding['expected_environment']}
        if reader_version=='v3':
            plan['proxy_coordination']=dispatch.coordination_identity()
            record['proxy_coordination']=plan['proxy_coordination']
        (target/'environment_dispatch.json').write_text(json.dumps(record))
        kwargs['environment_record_sha256']=ev._file_sha(target/'environment_dispatch.json')
    _, results = ev._read_task(target, item, plan,**kwargs)
    assert len(results) == (10 if protocol == "mask10" else 1)
    assert all(r["queries"] and r["executed_actions"] and r["video"]["status"] == "saved" for r in results)
    assert tree_hash(tmp_path / "original") == before
    if protocol in ("normal00-control", "nine-normal00"):
        assert results[0]["goal_regression"] is None and results[0]["preservation_applicable"] is False
    if protocol == "nine-normal00":
        assert results[0]["n_steps"] == 2 and results[0]["exit_reason"] == "official_success"
        assert results[0]["trace"][-1]["released"] is False
        assert results[0]["goal_regression"] is None
    with pytest.raises(ValueError, match="adapter"):
        ev._read_task(target, item, {**plan, "adapter_identity": {**adapter(), "adapter_sha256": "b" * 64}},**kwargs)
    video = target / results[0]["video"]["path"]
    video.write_bytes(video.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="video"):
        ev._read_task(target, item, plan,**kwargs)


def test_adapter_preserves_native_oft_camera_and_robot_sensor_inputs(core):
    import numpy as np
    from egrs.augmentation.evaluation import AdapterPolicy
    from benchmark.remaining_goals.adapters.openvla import _raw_observation
    from tests.test_headless_runner import observation
    obs = observation(0)
    obs.update(robot0_eef_pos=np.array([.1, .2, .3]), robot0_eef_quat=np.array([0., 0., 0., 1.]),
               robot0_gripper_qpos=np.array([.04, -.04]), domain="10", initial_mask=[True, False], contact={"oracle": True})
    class Base:
        def predict(self, sensors, instruction):
            assert not {"domain", "condition", "initial_mask", "contact"} & sensors.keys()
            raw = _raw_observation(sensors, wrist=True, proprio=True)
            assert raw["agentview_image"].shape == (2, 3, 3)
            assert instruction == "original full instruction"
            return np.zeros((8, 7))
    policy = AdapterPolicy.__new__(AdapterPolicy); policy.base = Base()
    assert policy.predict(obs, "original full instruction").shape == (8, 7)
