"""Method policy: sensor-only selector, revocable memory, unchanged actor actions."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import hashlib
import json

from .contracts import validate_registry, validate_payload, validate_prediction, sensor_copy, text
from .memory import EvidenceMemory
from .sidecar import EpisodeLog


class EGRSPolicy:
    def __init__(self, config, selector, actor, provenance):
        self.config=deepcopy(config)
        self.variant=config.get("variant","full")
        if self.variant not in {"full","baseline","no_lora","no_history","no_role"}:
            raise ValueError("unknown method variant")
        self.use_history=config.get("history",True) and self.variant!="no_history"
        if type(self.use_history) is not bool:
            raise ValueError("history must be boolean")
        if self.variant!="baseline" and selector is None:
            raise ValueError("selector required outside baseline mode")
        self.selector,self.actor=selector,actor
        self.output=Path(config["output_dir"]).expanduser()
        self.output.mkdir(parents=True,exist_ok=False)
        self.metadata={"method":"egrs/v1","variant":self.variant,"history":self.use_history,
                       "provenance":deepcopy(provenance),"selector":deepcopy(getattr(selector,"metadata",None)),
                       "actor":deepcopy(getattr(actor,"metadata",getattr(actor,"provenance",{}))),
                       "memory":config.get("memory",{}),"actions":"commands; core alone measures execution"}
        (self.output/"metadata.json").write_text(json.dumps(self.metadata,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        self.episode=0
        self.log=None
        self.closed=False
        self.failed=False
        self.active=False

    def reset(self):
        if self.closed:
            raise RuntimeError("method policy is closed")
        if self.log is not None and not self.log.finished:
            self.log.close_partial()
        self.episode+=1
        self.failed=False
        self.active=True
        self.registry=None
        self.memory=None
        self.current=None
        self.original=None
        self.query_id=0
        self.snapshots=[]
        self.commands=[]
        self.log=EpisodeLog(self.output/f"episode-{self.episode:06d}.jsonl",self.metadata)
        try:
            if self.selector is not None:
                self.selector.reset()
            self.actor.reset()
        except BaseException as error:
            self._error(error,"reset")
            raise

    def _error(self, error, phase):
        self.failed=True
        self.log.write({"event":"error","query_id":self.query_id,"phase":phase,
                        "error":f"{type(error).__name__}: {error}"})

    def _invoke(self, kind, callback, *args, images=0):
        # Attempt records survive even if no action or successful query returns.
        self.log.write({"event":"call_start", "query_id":self.query_id,
                        "kind":kind,"image_count":images})
        start=perf_counter()
        try:
            result=callback(*args)
        except BaseException as error:
            self.log.write({"event":"call_end","query_id":self.query_id,"kind":kind,
                            "ok":False,"seconds":perf_counter()-start,
                            "input_audit":getattr(self.selector,"last_input_audit",None) if kind in {"selector","registry"} else None,
                            "error":f"{type(error).__name__}: {error}"})
            raise
        self.log.write({"event":"call_end","query_id":self.query_id,"kind":kind,
                        "ok":True,"seconds":perf_counter()-start,
                        "input_audit":getattr(self.selector,"last_input_audit",None) if kind in {"selector","registry"} else None})
        return result

    def predict(self, observation, instruction):
        if self.closed or not self.active or self.failed:
            raise RuntimeError("method policy is closed, not reset, or has a technical failure")
        phase="sensor_validation"
        try:
            obs=sensor_copy(observation)
            text(instruction,"instruction",4096)
            if self.original is not None and instruction != self.original:
                raise ValueError("original instruction cannot change within an episode")
            self.original=instruction
            self.query_id+=1
            query=self.query_id
            self.log.write({"event":"query_start","query_id":query})
            selector_seconds=0.
            if self.variant!="baseline" and self.registry is None:
                phase="registry"
                t=perf_counter()
                self.registry=validate_registry(self._invoke("registry",self.selector.registry,instruction),instruction)
                self.memory=EvidenceMemory(self.registry,**self.config.get("memory",{}))
                self.log.write({"event":"registry","registry":self.registry,"selector_calls":1,
                                "selector_seconds":perf_counter()-t,"image_count":0})
            shot={"query_id":query,"snapshot_id":f"q{query}","observation":obs}
            self.snapshots=(self.snapshots+[shot])[-3:] if self.use_history else [shot]
            if self.variant=="baseline":
                choice={"goal_ref":None,"instruction":instruction,"reason":"baseline_original"}
                prediction=None
                history=[]
            else:
                phase="selector"
                payload=validate_payload({"sensor":self.snapshots,"context":{"query_id":query,
                    "instruction":instruction,"registry":self.registry,
                    "history":self.memory.records if self.use_history else [],
                    "commands":self.commands if self.use_history else []}})
                t=perf_counter()
                prediction=validate_prediction(self._invoke("selector",self.selector.predict,payload,
                    images=len(self.snapshots)*2),self.registry,query,self.snapshots)
                selector_seconds=perf_counter()-t
                if not self.use_history:
                    # Remove learned/rule memory as well as visual/text history.
                    self.memory=EvidenceMemory(self.registry,**self.config.get("memory",{}))
                    self.memory.query_id=query-1
                self.memory.update(prediction)
                choice=self.memory.choose(self.current)
                history=deepcopy(self.memory.records)
            phase="actor"
            t=perf_counter()
            actions=self._invoke("actor",self.actor.predict,obs,choice["instruction"])
            actor_seconds=perf_counter()-t
            from benchmark.remaining_goals.runner import _actions
            validated=_actions(actions)
            command={"query_id":query,"goal_ref":choice["goal_ref"],"instruction":choice["instruction"],
                     "returned_chunk_length":len(validated),"semantics":"command_not_execution"}
            phase="sidecar"
            from benchmark.remaining_goals.pilot_evidence import observation_sha256
            self.log.write({"event":"query","query_id":query,
                "observation_sha256":observation_sha256(obs),
                "supplied_snapshot_ids":[s["snapshot_id"] for s in self.snapshots] if prediction else [],
                "selector_input_audit":getattr(self.selector,"last_input_audit",None),
                "choice":choice,"prediction":prediction,"history":history,"command":command,
                "selector_calls":int(self.variant!="baseline"),"actor_calls":1,
                "supplied_image_count":len(self.snapshots)*2 if prediction else 0,
                "selector_seconds":selector_seconds,"actor_seconds":actor_seconds})
            self.current=choice["goal_ref"]
            self.commands=(self.commands+[command])[-12:]
            return actions
        except BaseException as error:
            self._error(error,phase)
            raise

    def finish_episode(self, result):
        if self.log is None or self.log.finished:
            raise RuntimeError("no active method episode to finalize")
        self.log.finish("complete" if result["status"]=="completed" and not self.failed else "partial",
                        core_status=result["status"],
                        query_sequences=[q["sequence"] for q in result["queries"]])
        self.active=False

    def close(self):
        if self.closed:
            return
        self.closed=True
        errors=[]
        for obj in (self.selector,self.actor):
            if obj is not None:
                try:
                    obj.close()
                except BaseException as error:
                    errors.append(error)
        if self.log is not None:
            try:
                if errors and not self.log.finished:
                    self.log.write({"event":"error","phase":"close","error":str(errors[0]),"query_id":self.query_id})
                self.log.close_partial()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise errors[0]


def make_policy(config):
    from .configuration import validate_config
    from .core import activate
    from .actor import facade_config
    from .rpc import SelectorProcess
    config=validate_config(config)
    output=Path(config["output_dir"]).expanduser()
    if output.exists():
        raise FileExistsError(output)
    core_info=activate(config["core"])
    selector=actor=None
    try:
        if config["variant"]!="baseline":
            selector_config=deepcopy(config["selector"])
            selector_config["use_history"]=config["history"] and config["variant"]!="no_history"
            if config["variant"]=="no_lora":
                selector_config["lora_path"]=None
            selector=SelectorProcess(selector_config,config["core"])
        from benchmark.remaining_goals.isolated_policy import SubprocessPolicy
        actor=SubprocessPolicy(facade_config(config["actor"],config["goal_change_capability"],config["core"]))
        identity={"core":core_info,"method_source_sha256":method_source_hash(),
                  "configuration_sha256":hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()}
        return EGRSPolicy(config,selector,actor,identity)
    except BaseException as error:
        for obj in (selector,actor):
            if obj is not None:
                try:
                    obj.close()
                except BaseException:
                    pass
        if not output.exists():
            output.mkdir(parents=True,exist_ok=False)
        with (output/"startup_failure.json").open("x",encoding="utf-8") as stream:
            json.dump({"status":"partial","error":f"{type(error).__name__}: {error}"},stream)
        raise


def method_source_hash():
    digest=hashlib.sha256()
    root=Path(__file__).resolve().parent
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode()+b"\0"+path.read_bytes())
    return digest.hexdigest()
