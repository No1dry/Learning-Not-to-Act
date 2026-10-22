import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from egrs.cli import main
from egrs.configuration import load_config
from egrs.actor import facade_config
from egrs.core import inspect_core
from tests.test_rpc_config import core_config


def test_compose_preserves_transfer_and_inspect_is_file_only(tmp_path,capsys):
    from benchmark.remaining_goals.adapters.oft_transfer import TRANSFER,SOG10_SOURCE,FACTORY,validate_suite_transfer
    actor={"model_id":"openvla_oft","suite":"libero_90","policy_factory":FACTORY,
           "checkpoint_source":SOG10_SOURCE,"runtime":{"python_executable":sys.executable},
           "execution":{"random_seed":7,"max_chunk_steps":8},
           "adapter_options":{"suite":"libero_90","suite_transfer":TRANSFER,
                              "repo_path":"repo","checkpoint":"weights"}}
    a=tmp_path/"actor.json"; a.write_text(json.dumps(actor))
    c=tmp_path/"core.json"; c.write_text(json.dumps(core_config()))
    output=tmp_path/"method.json"
    assert main(["compose","--actor",str(a),"--core",str(c),"--capability","openvla_oft",
                 "--variant","baseline","--run-dir",str(tmp_path/"run"),"--output",str(output)])==0
    config=load_config(output)
    original=config["actor"]
    assert original["adapter_options"]["checkpoint"]==str(tmp_path/"weights")
    assert validate_suite_transfer(original)==TRANSFER
    facade=facade_config(original,"openvla_oft",config["core"])
    assert validate_suite_transfer(facade) is None
    assert validate_suite_transfer(facade["adapter_options"]["actor_config"])==TRANSFER
    bad=copy.deepcopy(facade)
    bad["adapter_options"]["suite_transfer"]=TRANSFER
    with pytest.raises(ValueError):
        validate_suite_transfer(bad)
    assert main(["inspect","--config",str(output)])==2
    # A fresh process proves import/dry inspection has no model/native side effects.
    script="from egrs.cli import main; import sys; main(['inspect','--config',sys.argv[1]]); assert not any(x in sys.modules for x in ('torch','transformers','mujoco','robosuite'))"
    subprocess.run([sys.executable,"-c",script,str(output)],check=True,capture_output=True,text=True)


def test_pin_rejects_ignored_shadow_module(tmp_path,monkeypatch):
    import egrs.core as core
    root=tmp_path/"fakecore"; root.mkdir()
    git=os.environ.get("EGRS_GIT","git")
    def run(*args):
        return subprocess.check_output([git,"-c","safe.directory="+root.as_posix(),"-C",str(root),*args],stderr=subprocess.PIPE,text=True).strip()
    run("init")
    (root/".gitignore").write_text("benchmark/remaining_goals/runner/\n")
    run("add",".gitignore")
    run("-c","user.name=CPU fixture","-c","user.email=fixture@example.invalid","commit","-m","fixture")
    rev=run("rev-parse","HEAD")
    monkeypatch.setattr(core,"REFERENCE_REVISION",rev)
    shadow=root/"benchmark/remaining_goals/runner"; shadow.mkdir(parents=True)
    (shadow/"__init__.py").write_text("raise RuntimeError('must not import')")
    with pytest.raises(ValueError,match="ignored importable"):
        inspect_core({"root":str(root),"revision":rev,"allow_reference":True,"git_executable":git})
