"""Task058: record scripted pick-and-place episodes in the fixed ten HDF schema.

Provenance is `scripted_placement`: privileged object poses generate the trajectory,
the policy is never queried. Images are stored at 128x128 in raw LIBERO orientation;
the training mapping's rotate_180/center_crop transforms stay unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .qualify import (TARGETS, eef_pose, hold, object_pose, servo, site_pos,
                      topdown_rotation, yaw_of)

IMAGE_SIZE = 128


def _downscale(image):
    import cv2
    array = np.asarray(image)
    if array.shape[0] == IMAGE_SIZE and array.shape[1] == IMAGE_SIZE:
        return array.astype(np.uint8)
    return cv2.resize(array, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA).astype(np.uint8)


def _proprio(obs):
    pos = np.asarray(obs["robot0_eef_pos"], dtype=float)
    quat = np.asarray(obs["robot0_eef_quat"], dtype=float)  # xyzw (robosuite)
    grip = np.asarray(obs["robot0_gripper_qpos"], dtype=float)
    # convert xyzw quaternion to axis-angle for the 6D eef state convention
    x, y, z, w = quat
    angle = 2.0 * np.arctan2(np.linalg.norm([x, y, z]), w)
    norm = np.linalg.norm([x, y, z])
    axis = np.array([x, y, z]) / norm if norm > 1e-12 else np.zeros(3)
    return np.concatenate([pos, axis * angle]), grip


class Recorder:
    def __init__(self, env):
        self.env = env
        self.actions, self.images, self.wrists = [], [], []
        self.ee, self.grip, self.states = [], [], []
        self.goals_pos, self.goals_ori = [], []

    def reset(self):
        from benchmark.remaining_goals.libero_env import fresh_observation
        obs = fresh_observation(self.env.env)
        self._push(obs)
        return obs

    def _push(self, obs):
        self.images.append(_downscale(obs["agentview_image"]))
        self.wrists.append(_downscale(obs["robot0_eye_in_hand_image"]))
        ee, grip = _proprio(obs)
        self.ee.append(ee)
        self.grip.append(grip)
        self.states.append(np.asarray(self.env.env.sim.get_state().flatten(), dtype=float).copy())

    def step(self, action):
        from benchmark.remaining_goals.libero_env import fresh_observation
        action = np.asarray(action, dtype=float)
        self.env.step(action)
        ctrl = self.env.env.robots[0].controller
        self.actions.append(action.copy())
        self.goals_pos.append(np.asarray(ctrl.goal_pos, dtype=float).copy())
        self.goals_ori.append(np.asarray(ctrl.goal_ori, dtype=float).reshape(3, 3).copy())
        self._push(fresh_observation(self.env.env))
        return action


def run_recorded(env, target, instruction, recorder):
    """Mirror qualify.attempt with recording; returns (success, detail)."""
    rec = recorder
    obs = rec.reset()
    obj_pos, obj_quat = object_pose(env, target)
    rest_rot = topdown_rotation(yaw_of(obj_quat))
    pre = obj_pos + np.array([0.0, 0.0, 0.14])
    grasp = obj_pos + np.array([0.0, 0.0, 0.045])
    lift = obj_pos + np.array([0.0, 0.0, 0.25])
    basket = site_pos(env, "basket_1_contain_region")
    above = basket + np.array([0.0, 0.0, 0.30])

    def servo_rec(target_pos, target_rot, gripper, steps=45, tol=0.004):
        from egrs.trajectory_augmentation.control import pose_error, target_action
        ctrl = env.env.robots[0].controller
        for _ in range(steps):
            pos, rot = eef_pose(env)
            distance, angle = pose_error((pos, rot), (target_pos, target_rot))
            if distance <= tol and angle <= np.radians(3):
                return True
            rec.step(target_action(ctrl, pos, rot, target_pos, target_rot, gripper))
        return False

    def hold_rec(gripper, steps):
        action = np.zeros(7, dtype=float)
        action[6] = float(gripper)
        for _ in range(steps):
            rec.step(action.copy())

    servo_rec(pre, rest_rot, -1.0)
    servo_rec(grasp, rest_rot, -1.0, steps=50, tol=0.003)
    hold_rec(1.0, 30)
    servo_rec(lift, rest_rot, 1.0, steps=60)
    servo_rec(above, rest_rot, 1.0, steps=90)
    hold_rec(1.0, 20)
    for _ in range(2):
        b = site_pos(env, "basket_1_contain_region")
        obj, _ = object_pose(env, target)
        delta = np.array([b[0] - obj[0], b[1] - obj[1], 0.0])
        if float(np.linalg.norm(delta[:2])) <= 0.004:
            break
        eef, _ = eef_pose(env)
        servo_rec(eef + delta, rest_rot, 1.0, steps=30, tol=0.002)
        hold_rec(1.0, 15)
    hold_rec(-1.0, 30)
    for _ in range(100):
        rec.step(np.zeros(7))
    b0 = basket
    b1 = site_pos(env, "basket_1_contain_region")
    goals = [bool(v) for v in env.goal_values()]
    success = bool(goals and all(goals) and np.linalg.norm(b1 - b0) < 0.01)
    return success, {"target": target, "instruction": instruction, "goals": goals,
                     "basket_move": float(np.linalg.norm(b1 - b0)),
                     "steps": len(rec.actions)}


def write_ten_hdf(path, recorder, instruction):
    import h5py
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as hdf:
        group = hdf.create_group("data/demo_0")
        obs = group.create_group("obs")
        obs.create_dataset("agentview_rgb", data=np.stack(recorder.images), dtype=np.uint8)
        obs.create_dataset("eye_in_hand_rgb", data=np.stack(recorder.wrists), dtype=np.uint8)
        obs.create_dataset("ee_states", data=np.stack(recorder.ee), dtype=np.float64)
        obs.create_dataset("gripper_states", data=np.stack(recorder.grip), dtype=np.float64)
        group.create_dataset("actions", data=np.stack(recorder.actions), dtype=np.float64)
        group.create_dataset("states", data=np.stack(recorder.states), dtype=np.float64)
        group.create_dataset("controller_goal_pos", data=np.stack(recorder.goals_pos), dtype=np.float64)
        group.create_dataset("controller_goal_ori", data=np.stack(recorder.goals_ori), dtype=np.float64)
        hdf.require_group("data").attrs["problem_info"] = json.dumps(
            {"language_instruction": instruction})
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def aux_entry(task_key, instruction, hdf_path, sha256, length, mapping):
    return {
        "source_id": f"scripted058|{task_key}|{hdf_path.name}",
        "task_key": task_key,
        "split": "train",
        "domain": "10",
        "episode": "data/demo_0",
        "length": int(length),
        "instruction": instruction,
        "file": str(hdf_path),
        "file_sha256": sha256,
        "mapping": mapping,
        "provenance": "scripted_placement",
        "policy_rollouts": 0,
    }


def run(bank, output_dir, index_path, mapping_path, benchmark_root, limit=0):
    """Record successful scripted milk placements into ten HDFs plus an aux index."""
    import json
    from pathlib import Path

    from egrs.augmentation.dependencies import activate_core
    from egrs.composition057.source import adapt, make_environment

    activate_core(Path(benchmark_root))
    bank_path = Path(bank).resolve()
    doc = json.loads((bank_path / "sources.json").read_text(encoding="utf-8"))
    mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    hdf_dir = out / "hdf"
    hdf_dir.mkdir(exist_ok=True)
    entries, stats = [], {}
    for row in doc["rows"][:limit or None]:
        manifest = Path(row["source_manifest"]).resolve()
        archived = manifest.parent
        source = adapt(manifest, row)
        episode = source["episodes"][0]
        env = None
        rec = None
        try:
            env, _ = make_environment(source, archived)
            env.reset(episode)
            rec = Recorder(env)
            ok, detail = run_recorded(env, "milk_1", episode["instruction"], rec)
        except BaseException as error:
            ok, detail = False, {"error": f"{type(error).__name__}: {error}"}
        finally:
            if env is not None:
                try:
                    env.close()
                except BaseException:
                    pass
        print(f"[058][record] {row['episode_id']} -> {'OK' if ok else 'FAIL'} "
              f"steps={detail.get('steps')} goals={detail.get('goals')} "
              f"{detail.get('error','')}", flush=True)
        if ok and rec is not None:
            path = hdf_dir / (row["episode_id"] + ".hdf5")
            info = write_ten_hdf(path, rec, episode["instruction"])
            entries.append(aux_entry(episode["task_id"], episode["instruction"], path,
                                     info["sha256"], len(rec.actions), mapping))
            stats[episode["task_id"]] = stats.get(episode["task_id"], 0) + 1
    index = {"schema_version": "task058-scripted-aux-index-v1",
             "provenance": "scripted_placement", "policy_rollouts": 0,
             "sources": entries, "counts": stats}
    Path(index_path).write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index
