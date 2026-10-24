"""Append-only method evidence, separate from core physics and metrics."""
from __future__ import annotations
import json
import os
from pathlib import Path


class EpisodeLog:
    def __init__(self, path, metadata):
        self.path = Path(path)
        self.stream = self.path.open("x",encoding="utf-8",newline="\n")
        self.finished = False
        self.write({"event":"episode_start","schema":"egrs.sidecar/v1","metadata":metadata})

    def write(self, record):
        if self.finished:
            raise RuntimeError("cannot append to finalized method evidence")
        data = json.dumps(record,ensure_ascii=False,sort_keys=True,allow_nan=False)
        self.stream.write(data+"\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def finish(self, status, **details):
        self.write({"event":"episode_end","status":status,**details})
        self.finished = True
        self.stream.close()

    def close_partial(self):
        if not self.finished:
            self.finish("partial",reason="closed_without_core_finalization")


def inspect_sidecar(path, core_result=None):
    records=[]
    try:
        with Path(path).open(encoding="utf-8") as stream:
            for number,line in enumerate(stream,1):
                records.append(json.loads(line))
    except (json.JSONDecodeError,UnicodeError) as error:
        raise ValueError("truncated/corrupt sidecar; preserve as partial") from error
    if not records or records[0].get("event") != "episode_start":
        raise ValueError("missing method episode header")
    end = records[-1] if records[-1].get("event") == "episode_end" else {"status":"partial"}
    queries=[r for r in records if r.get("event")=="query"]
    ids=[q["query_id"] for q in queries]
    if ids != list(range(1,len(ids)+1)):
        raise ValueError("method query sequence is not contiguous")
    report={"status":end["status"],"queries":len(queries),"aligned":None,
            "selector_calls":sum(q.get("selector_calls",0) for q in queries)+sum(r.get("selector_calls",0) for r in records if r.get("event")=="registry"),
            "actor_calls":sum(q["actor_calls"] for q in queries),
            "images":None,
            "returned_actions":sum(q["command"]["returned_chunk_length"] for q in queries),
            "executed_steps":None,"has_error":any(r.get("event")=="error" for r in records)}
    calls=[r for r in records if r.get("event")=="call_start"]
    ends=[r for r in records if r.get("event")=="call_end"]
    report.update(selector_calls=sum(r["kind"] in {"selector","registry"} for r in calls),
                  actor_calls=sum(r["kind"]=="actor" for r in calls),
                  supplied_images=sum(r["image_count"] for r in calls),
                  calls_completed=sum(r["ok"] for r in ends),
                  calls_failed=sum(not r["ok"] for r in ends),
                  calls_unfinished=len(calls)-len(ends),
                  measured_call_seconds=sum(r["seconds"] for r in ends))
    selector_ends=[r for r in ends if r["kind"]=="selector"]
    if (len(selector_ends)==sum(r["kind"]=="selector" for r in calls)
        and all(isinstance(r.get("input_audit"),dict) and type(r["input_audit"].get("image_count")) is int for r in selector_ends)):
        report["images"]=sum(r["input_audit"]["image_count"] for r in selector_ends)
    if core_result is not None:
        core_queries=core_result["queries"]
        by_id={q["sequence"]:q for q in core_queries}
        if len(by_id)!=len(core_queries):
            raise ValueError("duplicate core query IDs")
        for q in queries:
            core=by_id.get(q["query_id"])
            if core is None or core["returned_chunk_length"] != q["command"]["returned_chunk_length"]:
                raise ValueError("method/core command identity mismatch")
            if ("observation_sha256" in core and core["observation_sha256"] != q["observation_sha256"]):
                raise ValueError("method/core sensor hash mismatch")
        if end["status"]=="complete" and (len(core_queries)!=len(queries) or core_result["status"]!="completed"):
            raise ValueError("complete method sidecar contradicts partial core result")
        if end.get("query_sequences") is not None and end["query_sequences"] != [q["sequence"] for q in core_queries]:
            raise ValueError("final core query identities changed")
        report.update(aligned=True,executed_steps=sum(len(q["executed_steps"]) for q in core_queries))
    return report
