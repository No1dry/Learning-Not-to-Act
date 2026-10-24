import copy
import random

import numpy as np
import pytest

from egrs.contracts import SchemaError, validate_registry, validate_prediction, validate_payload
from egrs.memory import EvidenceMemory
from egrs.actor import ActorFacade, facade_config


INSTRUCTION = "put the cup on the plate and turn on the stove"


def registry():
    return {"instruction": INSTRUCTION, "goals": [
        {"goal_ref": "g0", "source_text": "put the cup on the plate",
         "actor_text": "put the cup on the plate", "target": "cup",
         "destination": "plate", "kind": "transport"},
        {"goal_ref": "g1", "source_text": "turn on the stove",
         "actor_text": "turn on the stove", "target": "stove",
         "destination": None, "kind": "mechanism"}]}


def observation():
    return {"agentview_image": np.zeros((8, 8, 3), dtype=np.uint8),
            "robot0_eye_in_hand_image": np.zeros((8, 8, 3), dtype=np.uint8),
            "robot0_eef_pos": np.zeros(3)}


def snapshots(q=1):
    return [{"query_id": q, "snapshot_id": f"q{q}", "observation": observation()}]


def prediction(q=1, relation="UNSAT", interaction="NOT_HELD", entity="cup1", release="RELEASED"):
    rows = []
    for i in range(2):
        ref = f"g{i}"
        ent = entity if i == 0 else "stove1"
        rows.append({"goal_ref": ref, "entity_ref": ent, "association": "MATCHED",
                     "role": "TARGET", "relation": relation if i == 0 else "UNKNOWN",
                     "release": release if i == 0 else "NOT_APPLICABLE",
                     "interaction": interaction if i == 0 else "UNKNOWN",
                     "evidence": [{"goal_ref": ref, "entity_ref": ent, "query_id": q,
                                   "snapshot_id": f"q{q}", "camera": "agentview",
                                   "bbox": [.1, .2, .4, .5],
                                   "coordinate_system": "normalized_xyxy",
                                   "supports": ["entity", "relation", "release", "interaction", "role"]}]})
    return {"query_id": q, "goals": rows}


def test_registry_and_prediction_identity_and_unsupported_evidence():
    reg = validate_registry(registry(), INSTRUCTION)
    valid = prediction()
    assert validate_prediction(valid, reg, 1, snapshots()) == valid
    for mutation in (
        lambda p: p["goals"].pop(),
        lambda p: p["goals"][0].update(goal_ref="g9"),
        lambda p: p["goals"][0]["evidence"][0].update(query_id=2),
        lambda p: p["goals"][0]["evidence"][0].update(entity_ref="other"),
        lambda p: p["goals"][0]["evidence"][0].update(bbox=[0,0,2,1]),
        lambda p: p["goals"][1].update(release="UNKNOWN"),
        lambda p: p["goals"][0].update(physical_truth=True),
    ):
        bad = copy.deepcopy(valid)
        mutation(bad)
        with pytest.raises(SchemaError):
            validate_prediction(bad, reg, 1, snapshots())
    bad = registry()
    bad["goals"][0]["actor_text"] = "open the gripper"
    with pytest.raises(SchemaError):
        validate_registry(bad)


def test_payload_rejects_future_truth_and_untrusted_history():
    payload = {"sensor": snapshots(), "context": {"query_id": 1, "instruction": INSTRUCTION,
        "registry": registry(), "history": [], "commands": []}}
    assert validate_payload(payload)["context"]["query_id"] == 1
    for field in ("mask", "physical_truth", "task_id", "goals"):
        bad = copy.deepcopy(payload)
        bad["sensor"][0]["observation"][field] = [1, 0]
        with pytest.raises((SchemaError, ValueError)):
            validate_payload(bad)
    bad = copy.deepcopy(payload)
    bad["context"]["history"] = [{"physical_truth": True}]
    with pytest.raises(SchemaError):
        validate_payload(bad)
    bad = copy.deepcopy(payload)
    bad["sensor"][0]["query_id"] = 2
    with pytest.raises(SchemaError):
        validate_payload(bad)


def update(memory, p, past=None):
    snaps = (past or []) + snapshots(p["query_id"])
    return memory.update(validate_prediction(p, registry(), p["query_id"], snaps))


def test_fresh_sat_twice_stale_repeats_and_immediate_revocation():
    m = EvidenceMemory(registry())
    assert m.records == []
    update(m, prediction(1, "SAT"))
    assert not m.beliefs["g0"]["complete"]
    p = prediction(2, "SAT")
    p["goals"][0]["evidence"][0].update(query_id=1, snapshot_id="q1")
    update(m, p, snapshots(1))
    assert not m.beliefs["g0"]["complete"]
    update(m, prediction(3, "SAT"))
    assert not m.beliefs["g0"]["complete"]
    update(m, prediction(4, "SAT"))
    assert m.beliefs["g0"]["complete"]
    update(m, prediction(5, "UNSAT"))
    assert not m.beliefs["g0"]["complete"]


def test_carry_keeps_goal_then_expires_or_identity_reverses():
    m = EvidenceMemory(registry())
    update(m, prediction(1, "UNSAT", "HELD", release="NOT_RELEASED"))
    assert m.choose("g0")["goal_ref"] == "g0"
    for q in (2, 3, 4):
        p = prediction(q, "UNKNOWN", "UNKNOWN", release="UNKNOWN")
        p["goals"][0].update(entity_ref=None, association="UNKNOWN", role="UNKNOWN", evidence=[])
        update(m, p)
        assert m.choose("g0")["reason"] == ("carry" if q < 4 else "original_fallback")
    m = EvidenceMemory(registry())
    update(m, prediction(1, "UNSAT", "HELD", release="NOT_RELEASED"))
    p = prediction(2, "UNKNOWN", "UNKNOWN", entity="other", release="UNKNOWN")
    update(m, p)
    assert m.choose("g0")["reason"] == "original_fallback"


def test_unknown_and_sat_never_emit_stop_or_drop_goals():
    m = EvidenceMemory(registry())
    for q in range(1, 17):
        update(m, prediction(q, "SAT"))
    choice = m.choose(None)
    assert choice["instruction"] == INSTRUCTION
    assert choice["goal_ref"] is None
    assert len(m.records) == 12
    assert set(m.beliefs) == {"g0", "g1"}


def test_other_entity_fields_cannot_update_cached_identity():
    m = EvidenceMemory(registry())
    update(m, prediction(1, "UNSAT", "HELD", entity="cupA", release="NOT_RELEASED"))
    p = prediction(2, "UNKNOWN", "NOT_HELD", entity="cupB", release="RELEASED")
    current = p["goals"][0]["evidence"][0]
    old = copy.deepcopy(current)
    old.update(query_id=1, snapshot_id="q1", supports=["entity"])
    current["supports"] = ["interaction", "release", "role"]
    p["goals"][0]["evidence"].append(old)
    update(m, p, snapshots(1))
    assert m.beliefs["g0"]["entity_ref"] == "cupA"
    assert m.beliefs["g0"]["carrying"]
    assert m.records[-1]["goals"][0]["interaction"] == "UNKNOWN"


def test_complete_belief_expires_without_new_release_support():
    m = EvidenceMemory(registry())
    update(m, prediction(1, "SAT"))
    update(m, prediction(2, "SAT"))
    assert m.beliefs["g0"]["complete"]
    for q in (3,4,5):
        update(m, prediction(q, "SAT", release="UNKNOWN"))
    assert not m.beliefs["g0"]["complete"]


class Actor:
    def __init__(self):
        self._history = "old"
        self.weight = object()
        self.resets = 0
        self.decoder = Decoder()
        self.metadata = {"test": True}
    def reset(self):
        self.resets += 1
        random.seed(999)
    def predict(self, obs, text):
        self._history += text
        return np.ones(7)
    def close(self):
        pass


class Decoder:
    def __init__(self):
        self.buffer = [1]
        self.resets = 0
    def reset(self):
        self.buffer = []
        self.resets += 1


def test_goal_change_clears_only_univla_cache_without_rng_or_weights():
    actor = Actor()
    facade = ActorFacade(actor, "univla", {"inner": "retained"})
    facade.predict(observation(), "one")
    old = random.getstate()
    weight = actor.weight
    facade.predict(observation(), "two")
    assert random.getstate() == old
    assert actor.weight is weight and actor.resets == 0
    assert actor._history == "two" and actor.decoder.buffer == []
    facade.predict(observation(), "two")
    assert actor.decoder.resets == 1


def test_facade_nested_transfer_unchanged_and_unknown_requires_hook():
    original = {"model": "openvla_oft", "policy_factory": "benchmark.remaining_goals.adapters.openvla_oft:make_policy",
                "transfer": {"from": "sog10"}, "adapter_options": {"checkpoint": "weights"},
                "runtime": {"python_executable": "python"}, "execution": {"random_seed": 1}}
    before = copy.deepcopy(original)
    outer = facade_config(original, "openvla_oft", {"root": "core"})
    assert outer["policy_factory"] == "egrs.actor:make_policy"
    assert "transfer" not in outer
    assert outer["adapter_options"]["actor_config"] == before
    assert original == before
    with pytest.raises(ValueError):
        ActorFacade(Actor(), "not-audited", {})
