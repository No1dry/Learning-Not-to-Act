"""Real pinned reference core, synthetic native-shaped arrays; no simulator/model."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pytest

from egrs.core import activate, run_episode
from egrs.policy import EGRSPolicy
from egrs.sidecar import inspect_sidecar
from tests.test_rpc_config import core_config
from tests.test_policy import Selector, Actor, config
from tests.test_runtime import INSTRUCTION, observation


def core_fixture(name):
    path=Path(os.environ["EGRS_CORE_ROOT"])/"tests"/name
    spec=importlib.util.spec_from_file_location("egrs_fixture_"+path.stem,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeometryEnv:
    def reset(self, source):
        from benchmark.remaining_goals.headless.environment import HeadlessMeasurements
        self.native=core_fixture("test_headless_environment.py").FakeNative("basket")
        self.measurements=HeadlessMeasurements(self.native,"basket",
            source_reset_model_xml_sha256=source["model_xml_sha256"])
        self.steps=0
        self.actions=[]
        return observation()
    def measurement_static(self):
        return self.measurements.measurement_static()
    def evaluator_state(self):
        return self.measurements.evaluator_state([True,self.steps>=2])
    def step(self,action):
        self.actions.append(action.copy())
        self.steps+=1
        self.native.steps+=1
        self.native.sim.data.site_xpos[0]=[self.steps/100,0,0]
        return observation()


@pytest.mark.parametrize("invalid", [False, True])
def test_egrs_original_core_evidence_metrics_and_partial(tmp_path,monkeypatch,invalid):
    info=activate(core_config())
    from benchmark.remaining_goals.headless import environment
    from benchmark.remaining_goals.headless.evidence import HeadlessEvidence,validate_evidence
    from benchmark.remaining_goals.headless.metrics import score_episode
    from benchmark.remaining_goals.task_catalog import TASKS
    monkeypatch.setattr(environment,"_callback_status",lambda:"absent")
    fixture=core_fixture("test_headless_runner.py")
    source=fixture.episode(task_name=TASKS["basket"]["name"],instruction=INSTRUCTION,
        model_xml_sha256=hashlib.sha256(b"<mujoco model='headless_cpu_synthetic'/>").hexdigest())
    identity={"episode_id":source["episode_id"],"state_sha256":source["state_sha256"],
              "model_identity":{"method":"CPU fixture","eval_core":info["revision"]}}
    evidence=HeadlessEvidence(tmp_path/"evidence"/source["episode_id"],identity)
    policy=EGRSPolicy(config(tmp_path),Selector(invalid),Actor(),{"core":info})
    video=fixture.Video()
    env=GeometryEnv()
    result=run_episode(env,policy,source,horizon=16,max_chunk_steps=8,
                       evidence=evidence,recorder=video,identity=identity)
    policy.close()
    assert validate_evidence(tmp_path,result,source,identity)["verified"]
    report=inspect_sidecar(tmp_path/"method"/"episode-000001.jsonl",result)
    assert report["aligned"]
    score=score_episode(source,result)
    if invalid:
        assert result["status"]=="runtime_error"
        assert result["error_phase"]=="policy_predict"
        assert report["status"]=="partial"
        assert score["classification"]=="technical_error"
        assert env.actions==[]
    else:
        assert result["status"]=="completed",result["error"]
        assert score["success"] is True
        assert result["n_steps"]==result["goal_confirmed_step"]==6
        assert result["path_length_m"]==pytest.approx(.06)
        assert result["queries"][0]["returned_chunk_length"]==10
        assert result["queries"][0]["accepted_chunk_length"]==8
        assert report["executed_steps"]==6 and report["returned_actions"]==10
        assert len(video.frames)==7
        assert env.native.resets==0 and env.native.steps==6
