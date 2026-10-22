"""Activate an explicit pinned dependency; no simulator imports at module import."""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

EVAL_REVISION = "515e87d9b93ab838428791273a0f3020d6f56e9c"
REFERENCE_REVISION = "c6dc98de0c54517c976057598b60f4cedf7fa3e5"


def inspect_core(config):
    if not isinstance(config, dict) or set(config) - {"root","revision","allow_reference","git_executable"}:
        raise ValueError("invalid core dependency configuration")
    root = Path(config["root"]).expanduser().resolve(strict=True)
    revision = config.get("revision", EVAL_REVISION)
    if revision != EVAL_REVISION and not (revision == REFERENCE_REVISION and config.get("allow_reference") is True):
        raise ValueError("unapproved eval core revision")
    git = str(config.get("git_executable", "git"))
    def run(*args):
        return subprocess.check_output([git,"-c","safe.directory="+root.as_posix(),"-C",str(root),*args],
                                       stderr=subprocess.PIPE,timeout=15).decode().strip()
    if run("rev-parse","HEAD") != revision:
        raise ValueError("eval core checkout is not at the configured exact revision")
    if run("diff","--name-only","HEAD","--","benchmark"):
        raise ValueError("eval core has modified tracked benchmark files")
    if run("ls-files","--others","--exclude-standard","--","benchmark"):
        raise ValueError("eval core has untracked benchmark files that could shadow pinned modules")
    added = run("ls-files","--others","--","benchmark").splitlines()
    if any(Path(name).suffix.lower() in {".py", ".pyw", ".pyd", ".so", ".dll"}
           or (Path(name).suffix.lower() in {".pyc", ".pyo"} and "__pycache__" not in Path(name).parts)
           for name in added):
        raise ValueError("eval core has ignored importable source additions")
    required = ["runner.py","policy_transport.py","isolated_policy.py","policy_worker.py",
                "headless/runner.py","headless/schema.py","headless/evidence.py","headless/metrics.py"]
    hashes = {}
    for name in required:
        path = root/"benchmark"/"remaining_goals"/name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"root":str(root), "revision":revision, "reference_only":revision == REFERENCE_REVISION,
            "required_eval_revision":EVAL_REVISION, "file_sha256":hashes}


def activate(config):
    info = inspect_core(config)
    root = Path(info["root"])
    for name, module in tuple(sys.modules.items()):
        if name == "benchmark" or name.startswith("benchmark."):
            file = getattr(module,"__file__",None)
            if file and not Path(file).resolve().is_relative_to(root):
                raise RuntimeError("another benchmark package is already imported; use an isolated interpreter")
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    module = importlib.import_module("benchmark.remaining_goals.runner")
    if not Path(module.__file__).resolve().is_relative_to(root):
        raise RuntimeError("benchmark import resolved outside the pinned dependency")
    return info


class SidecarFinalizationError(RuntimeError):
    def __init__(self, message, result):
        super().__init__(message)
        self.partial_result = result


def run_episode(env, policy, episode, **kwargs):
    """Thin single-episode bridge to the ORIGINAL headless runner.

    env/recorder/evidence are created by the caller/core. This is not a batch driver.
    """
    from benchmark.remaining_goals.headless.runner import run_episode as core_run
    result = core_run(env, policy, episode, **kwargs)
    try:
        policy.finish_episode(result)
    except BaseException as error:
        raise SidecarFinalizationError("method sidecar finalization failed; retain core evidence as partial", result) from error
    return result
