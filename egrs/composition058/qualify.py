"""Task058 G0b gate: scripted pick-and-place qualification for novel targets.

Executes a privileged-pose OSC pick-and-place for milk_1 / orange_juice_1 from the
frozen Task057 probe sources. This produces no training data and no formal score; it
only measures whether a scripted/retargeted trajectory can satisfy the goal predicate
and keep the precompleted A object.

Provenance of anything produced here would be `scripted_placement`, never human demo.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

TARGETS = ("milk_1", "orange_juice_1")


def _paths(env):
    sim = env.env.sim
    ctrl = env.env.robots[0].controller
    sid = int(sim.model.site_name2id(ctrl.eef_name))
    if sid < 0:
        raise ValueError("controlled end-effector site missing")
    pos = np.array(sim.data.site_xpos[sid], dtype=float)
    rot = np.array(sim.data.site_xmat[sid], dtype=float).reshape(3, 3)
    return sim, ctrl, pos, rot


def eef_pose(env):
    _, _, pos, rot = _paths(env)
    return pos, rot


def object_pose(env, name):
    sim = env.env.sim
    bid = env.inner.obj_body_id[name]
    return (np.array(sim.data.body_xpos[bid], dtype=float),
            np.array(sim.data.body_xquat[bid], dtype=float))


def site_pos(env, name):
    sim = env.env.sim
    sid = int(sim.model.site_name2id(name))
    if sid < 0:
        raise ValueError(f"missing site {name}")
    return np.array(sim.data.site_xpos[sid], dtype=float)


def topdown_rotation(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    x = np.array([c, s, 0.0])
    z = np.array([0.0, 0.0, -1.0])
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def yaw_of(quat):
    w, x, y, z = quat
    return float(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def servo(env, target_pos, target_rot, gripper, *, steps=45, tol=0.004):
    from egrs.trajectory_augmentation.control import pose_error, target_action

    _, ctrl, _, _ = _paths(env)
    for _ in range(steps):
        pos, rot = eef_pose(env)
        distance, angle = pose_error((pos, rot), (target_pos, target_rot))
        if distance <= tol and angle <= math.radians(3):
            return True
        env.step(target_action(ctrl, pos, rot, target_pos, target_rot, gripper))
    return False


def hold(env, gripper, steps):
    """Zero pose delta (null OSC action) with the requested gripper command."""
    action = np.zeros(7, dtype=float)
    action[6] = float(gripper)
    for _ in range(steps):
        env.step(action.copy())


def attempt(env, target):
    """Return (success, detail).

    Success requires A retained, B inside the basket region, and the basket itself
    not displaced (the scripted arm must release above the rim, never shove it).
    """
    obj_pos, obj_quat = object_pose(env, target)
    rest_rot = topdown_rotation(yaw_of(obj_quat))
    pre = obj_pos + np.array([0.0, 0.0, 0.14])
    grasp = obj_pos + np.array([0.0, 0.0, 0.045])
    lift = obj_pos + np.array([0.0, 0.0, 0.25])
    basket = site_pos(env, "basket_1_contain_region")
    above_basket = basket + np.array([0.0, 0.0, 0.30])

    detail = {"target": target, "obj_start": obj_pos.tolist(),
              "basket_site": basket.tolist()}
    servo(env, pre, rest_rot, -1.0)
    servo(env, grasp, rest_rot, -1.0, steps=50, tol=0.003)
    hold(env, 1.0, 30)
    servo(env, lift, rest_rot, 1.0, steps=60)
    held_pos, _ = object_pose(env, target)
    detail["obj_after_lift"] = held_pos.tolist()
    detail["lifted"] = bool(held_pos[2] > obj_pos[2] + 0.05)
    servo(env, above_basket, rest_rot, 1.0, steps=90, tol=0.004)
    # Stop residual motion, then center the OBJECT (not the eef) above the basket.
    hold(env, 1.0, 20)
    for _ in range(2):
        basket_now = site_pos(env, "basket_1_contain_region")
        obj_now, _ = object_pose(env, target)
        delta = np.array([basket_now[0] - obj_now[0], basket_now[1] - obj_now[1], 0.0])
        if float(np.linalg.norm(delta[:2])) <= 0.004:
            break
        eef_now, rot_now = eef_pose(env)
        servo(env, eef_now + delta, rest_rot, 1.0, steps=30, tol=0.002)
        hold(env, 1.0, 15)
    detail["obj_centered"] = object_pose(env, target)[0].tolist()
    hold(env, -1.0, 30)
    for _ in range(100):
        env.step(np.zeros(7))
    basket_end = site_pos(env, "basket_1_contain_region")
    goals = [bool(v) for v in env.goal_values()]
    moved = float(np.linalg.norm(basket_end - basket))
    detail.update(goals=goals, basket_move=moved, obj_end=object_pose(env, target)[0].tolist(),
                  success=bool(goals and all(goals) and moved < 0.01))
    return detail["success"], detail


def qualify(bank, archived_run, per_target=20, output=None):
    from egrs.composition057.source import adapt, make_environment

    bank_path = Path(bank).resolve()
    bank_doc = json.loads((bank_path / "sources.json").read_text(encoding="utf-8"))
    rows = bank_doc["rows"]
    from egrs.augmentation.dependencies import activate_core
    activate_core(Path(bank_doc["snapshot"]["config"]["benchmark_root"]))
    episodes = {row["episode_id"]: row for row in rows}
    run = Path(archived_run).resolve()
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    picks = []
    for target in TARGETS:
        selected = [s for s in plan["sources"]
                    if s["episodes"][0]["goal_specs"][1]["predicates"][0][1] == target]
        picks.append((target, selected[:per_target]))
    report = {"schema_version": "task058-g0b-qualification-v1",
              "diagnostic_only": True, "training_data_written": 0,
              "provenance": "scripted_placement", "targets": {}, "attempts": []}
    for target, sources in picks:
        stats = Counter()
        for source in sources:
            episode = source["episodes"][0]
            archived = run / "episodes" / episode["episode_id"] / "source"
            row = episodes[episode["episode_id"]]
            adapted = adapt(archived / "source.json", row)
            env = None
            try:
                env, _ = make_environment(adapted, archived)
                env.reset(adapted["episodes"][0])
                success, detail = attempt(env, target)
            except BaseException as error:
                success, detail = False, {"target": target, "error": f"{type(error).__name__}: {error}"}
            finally:
                if env is not None:
                    try:
                        env.close()
                    except BaseException:
                        pass
            stats["attempts"] += 1
            stats["successes"] += int(success)
            detail.update(episode_id=episode["episode_id"], task_id=episode["task_id"],
                          success=success)
            report["attempts"].append(detail)
            print(f"[058][{target}] {episode['episode_id']} -> {'SUCCESS' if success else 'FAIL'} "
                  f"({stats['successes']}/{stats['attempts']})", flush=True)
        report["targets"][target] = {
            "attempts": stats["attempts"], "successes": stats["successes"],
            "rate": stats["successes"] / stats["attempts"] if stats["attempts"] else 0.0}
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
