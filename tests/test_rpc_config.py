import copy
import os
import sys
from pathlib import Path
import random
import numpy as np
import pytest

from egrs.configuration import validate_config
from egrs.rpc import SelectorProcess
from egrs.core import REFERENCE_REVISION, inspect_core
from tests.test_runtime import registry, snapshots, INSTRUCTION


def core_config():
    return {"root":os.environ["EGRS_CORE_ROOT"],"revision":REFERENCE_REVISION,"allow_reference":True,
            "git_executable":os.environ.get("EGRS_GIT","git")}


def test_core_pin_checked_and_does_not_import_native():
    assert inspect_core(core_config())["reference_only"] is True
    bad=core_config()
    bad["revision"]="f"*40
    with pytest.raises(ValueError):
        inspect_core(bad)
    assert "mujoco" not in sys.modules


def test_selector_subprocess_uses_context_boundary_and_isolated_rng(tmp_path):
    # Test backend is an installed-style module in an explicit working directory;
    # production factory leaves cwd unspecified and requires installed egrs.
    config={"runtime":{"python_executable":sys.executable,"startup_timeout_seconds":30,
                       "predict_timeout_seconds":15},
            "factory":"testsupport.selector_backend:make","marker":"passed-through"}
    state=random.getstate()
    process=SelectorProcess(config,core_config())
    try:
        process.reset()
        assert process.metadata["config_marker"]=="passed-through"
        assert process.registry(INSTRUCTION)==registry()
        payload={"sensor":snapshots(),"context":{"query_id":1,"instruction":INSTRUCTION,
                 "registry":registry(),"history":[],"commands":[]}}
        assert process.predict(payload)["query_id"]==1
        bad=copy.deepcopy(payload)
        bad["context"]["physical_truth"]=True
        with pytest.raises((ValueError,RuntimeError)):
            process.predict(bad)
    finally:
        process.close()
    assert random.getstate()==state


def test_variant_config_never_silently_calls_base_instead_of_lora(tmp_path):
    base={"core":core_config(),"output_dir":str(tmp_path/"run"),"variant":"full","history":True,
          "actor":{"policy_factory":"benchmark.remaining_goals.adapters.openvla_oft:make_policy",
                   "runtime":{"python_executable":sys.executable},"adapter_options":{}},
          "goal_change_capability":"openvla_oft",
          "selector":{"runtime":{"python_executable":sys.executable}}}
    with pytest.raises(ValueError,match="LoRA"):
        validate_config(base)
    base["variant"]="no_lora"
    assert validate_config(base)["variant"]=="no_lora"
    base["variant"]="baseline"
    del base["selector"]
    assert validate_config(base)["variant"]=="baseline"


def test_selector_close_failure_is_not_silent():
    config={"runtime":{"python_executable":sys.executable,"startup_timeout_seconds":30},
            "factory":"testsupport.selector_backend:make","marker":"close-fail"}
    process=SelectorProcess(config,core_config())
    with pytest.raises(RuntimeError,match="exited"):
        process.close()
    assert process.process.poll() is not None
