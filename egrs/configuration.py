"""File-only configuration checks. Import/help never creates models or native envs."""
from copy import deepcopy
import json
import math
from pathlib import Path
from .actor import AUDITED
from .core import EVAL_REVISION


def runtime_config(value):
    if not isinstance(value, dict) or not isinstance(value.get("python_executable"),str) or not value["python_executable"].strip():
        raise ValueError("runtime.python_executable must name an explicitly installed interpreter")
    for field,default in (("predict_timeout_seconds",180),("startup_timeout_seconds",1200)):
        timeout=value.get(field,default)
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise ValueError(f"runtime.{field} must be finite and positive")


def validate_config(config):
    if not isinstance(config,dict):
        raise ValueError("method configuration must be an object")
    c=deepcopy(config)
    if set(c)-{"core","output_dir","variant","history","memory","actor","selector","goal_change_capability","policy_factory"}:
        raise ValueError("unexpected method configuration key; nest the original actor configuration")
    if c.get("policy_factory","egrs.policy:make_policy")!="egrs.policy:make_policy":
        raise ValueError("method factory mismatch")
    c.setdefault("variant","full")
    c.setdefault("history",True)
    c.setdefault("memory",{"sat_queries":2,"expiry_queries":3,"max_records":12})
    if c["variant"] not in {"full","baseline","no_lora","no_history","no_role"} or type(c["history"]) is not bool:
        raise ValueError("invalid variant/history")
    if c["variant"] == "no_history":
        c["history"] = False
    elif c["variant"] != "baseline" and not c["history"]:
        raise ValueError("disabled history requires the no_history variant")
    if not isinstance(c.get("output_dir"),str) or not c["output_dir"]:
        raise ValueError("output_dir must name a new run directory")
    if not isinstance(c.get("core"),dict) or not isinstance(c["core"].get("root"),str):
        raise ValueError("core.root must name the explicit pinned checkout")
    c["core"].setdefault("revision",EVAL_REVISION)
    actor=c["actor"]
    if not isinstance(actor,dict) or not isinstance(actor.get("policy_factory"),str):
        raise ValueError("actor must preserve its complete original factory/config")
    runtime_config(actor.get("runtime"))
    capability=c["goal_change_capability"]
    if capability!="custom_hook" and AUDITED.get(capability)!=actor["policy_factory"]:
        raise ValueError("actor factory does not match audited capability")
    if c["variant"]!="baseline":
        selector=c["selector"]
        runtime_config(selector.get("runtime"))
        adapter=selector.get("lora_path",selector.get("adapter"))
        if c["variant"]!="no_lora" and not adapter:
            raise ValueError("this variant requires a trained selector LoRA; use no_lora explicitly")
        if c["variant"]=="no_lora" and adapter:
            raise ValueError("no_lora must not configure an adapter")
        if c["variant"]=="no_role" and selector.get("role_supervision",True) is not False:
            raise ValueError("no_role needs a checkpoint trained with role_supervision=false")
        if c["variant"]!="no_role" and selector.get("role_supervision",True) is False:
            raise ValueError("role-ablated checkpoint requires the no_role variant")
    memory=c["memory"]
    if not isinstance(memory,dict) or set(memory)!={"sat_queries","expiry_queries","max_records"}:
        raise ValueError("memory thresholds must be explicit")
    if (type(memory["sat_queries"]) is not int or memory["sat_queries"]<2 or
        type(memory["expiry_queries"]) is not int or memory["expiry_queries"]<1 or
        type(memory["max_records"]) is not int or not 1<=memory["max_records"]<=12):
        raise ValueError("invalid memory thresholds")
    return c


def load_config(path):
    p=Path(path).expanduser().resolve()
    c=validate_config(json.loads(p.read_text(encoding="utf-8")))
    # Paths are relative to the configuration file, never the shell's activation.
    def resolve(obj,key):
        if obj.get(key) and isinstance(obj[key],str):
            path=Path(obj[key]).expanduser()
            # abspath preserves venv interpreter symlinks (Path.resolve does not).
            import os
            obj[key]=os.path.abspath(path if path.is_absolute() else p.parent/path)
    for obj,key in ((c,"output_dir"),(c["core"],"root")):
        resolve(obj,key)
    for part in ("actor","selector"):
        if part not in c:
            continue
        resolve(c[part]["runtime"],"python_executable")
        for key in ("lora_path","adapter"):
            resolve(c[part],key)
    for key in ("repo_path","checkpoint","action_decoder_path"):
        resolve(c["actor"].get("adapter_options",{}),key)
    if "git_executable" in c["core"] and ("/" in c["core"]["git_executable"] or "\\" in c["core"]["git_executable"]):
        resolve(c["core"],"git_executable")
    return c
