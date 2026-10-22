import copy
import json
from pathlib import Path

import numpy as np
import pytest

from egrs.policy import EGRSPolicy
from egrs.sidecar import inspect_sidecar
from tests.test_runtime import INSTRUCTION, observation, registry, prediction


class Selector:
    metadata = {"kind": "test-selector"}
    def __init__(self, invalid=False):
        self.payloads = []
        self.registry_calls = 0
        self.invalid = invalid
    def registry(self, instruction):
        self.registry_calls += 1
        return registry()
    def predict(self, payload):
        self.payloads.append(copy.deepcopy(payload))
        if self.invalid:
            return {"query_id": 1, "goals": []}
        return prediction(payload["context"]["query_id"])
    def reset(self):
        pass
    def close(self):
        pass


class Actor:
    metadata = {"kind": "test-actor"}
    def __init__(self):
        self.instructions = []
    def reset(self):
        pass
    def predict(self, obs, instruction):
        assert set(obs) == set(observation())
        self.instructions.append(instruction)
        return np.ones((10, 7))
    def close(self):
        pass


def config(tmp_path, history=True, variant="full"):
    return {"output_dir": str(tmp_path/"method"), "history": history,
            "variant": variant, "memory": {"sat_queries":2,"expiry_queries":3,"max_records":12}}


def test_policy_registry_once_history_bounded_and_command_not_execution(tmp_path):
    selector, actor = Selector(), Actor()
    policy = EGRSPolicy(config(tmp_path), selector, actor, {"core": "fixture"})
    policy.reset()
    for _ in range(4):
        assert policy.predict(observation(), INSTRUCTION).shape == (10,7)
    assert selector.registry_calls == 1
    assert actor.instructions == ["put the cup on the plate"]*4
    last = selector.payloads[-1]
    assert [s["query_id"] for s in last["sensor"]] == [2,3,4]
    assert len(last["context"]["history"]) == 3
    assert last["context"]["commands"][0]["returned_chunk_length"] == 10
    assert "executed" not in last["context"]["commands"][0]
    result = {"status":"completed","queries":[{"sequence":i,"returned_chunk_length":10,
              "accepted_chunk_length":8,"executed_steps":list(range(8))} for i in range(1,5)]}
    policy.finish_episode(result)
    policy.close()
    report = inspect_sidecar(tmp_path/"method"/"episode-000001.jsonl", result)
    assert report["aligned"] is True
    assert report["selector_calls"] == 5  # one language-only registry + four visual predictions
    assert report["actor_calls"] == 4
    assert report["returned_actions"] == 40
    assert report["executed_steps"] == 32


def test_no_history_removes_all_past_inputs_and_baseline_skips_selector(tmp_path):
    s, a = Selector(), Actor()
    p = EGRSPolicy(config(tmp_path,False),s,a,{})
    p.reset()
    for _ in range(3):
        p.predict(observation(),INSTRUCTION)
    assert len(s.payloads[-1]["sensor"]) == 1
    assert s.payloads[-1]["context"]["history"] == []
    assert s.payloads[-1]["context"]["commands"] == []
    p.close()
    base = EGRSPolicy(config(tmp_path/"base",variant="baseline"),None,Actor(),{})
    base.reset()
    base.predict(observation(), INSTRUCTION)
    assert base.actor.instructions == [INSTRUCTION]
    base.close()


def test_schema_failure_preserves_partial_and_never_calls_actor(tmp_path):
    s, a = Selector(True), Actor()
    p = EGRSPolicy(config(tmp_path),s,a,{})
    p.reset()
    with pytest.raises(ValueError):
        p.predict(observation(),INSTRUCTION)
    assert a.instructions == []
    p.close()
    records = [json.loads(x) for x in (tmp_path/"method"/"episode-000001.jsonl").read_text().splitlines()]
    assert any(r["event"] == "error" for r in records)
    assert records[-1]["status"] == "partial"
    with pytest.raises(FileExistsError):
        EGRSPolicy(config(tmp_path),Selector(),Actor(),{})


def test_log_failure_is_hard_and_no_unlogged_action_is_returned(tmp_path):
    p = EGRSPolicy(config(tmp_path),Selector(),Actor(),{})
    p.reset()
    p.log.stream.close()
    with pytest.raises((OSError,ValueError)):
        p.predict(observation(), INSTRUCTION)
    assert p.failed
    with pytest.raises(RuntimeError):
        p.predict(observation(), INSTRUCTION)
    with pytest.raises((OSError,ValueError)):
        p.close()


def test_failed_actor_still_counts_selector_and_actor_attempts(tmp_path):
    class BrokenActor(Actor):
        def predict(self,obs,instruction):
            raise RuntimeError("synthetic actor failure")
    p=EGRSPolicy(config(tmp_path),Selector(),BrokenActor(),{})
    p.reset()
    with pytest.raises(RuntimeError,match="synthetic actor failure"):
        p.predict(observation(),INSTRUCTION)
    p.close()
    result=inspect_sidecar(tmp_path/"method"/"episode-000001.jsonl")
    assert result["status"]=="partial" and result["queries"]==0
    assert result["selector_calls"]==2 and result["actor_calls"]==1
    assert result["supplied_images"]==2 and result["images"] is None and result["calls_failed"]==1
    assert result["calls_unfinished"]==0
