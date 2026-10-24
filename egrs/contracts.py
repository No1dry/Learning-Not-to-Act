"""Strict sensor/context boundary and stable language-goal wire contracts."""
from __future__ import annotations

from copy import deepcopy
import math
import re
import numpy as np


class SchemaError(ValueError):
    pass


def keys(obj, required, name):
    if not isinstance(obj, dict) or set(obj) != set(required):
        raise SchemaError(f"{name}: expected keys {sorted(required)}")
    return obj


def text(value, name, limit=2048):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise SchemaError(f"{name}: expected nonempty text of at most {limit} characters")
    return value


def integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise SchemaError(f"{name}: expected integer >= {minimum}")
    return value


def enum(value, allowed, name):
    if not isinstance(value, str) or value not in allowed:
        raise SchemaError(f"{name}: invalid state {value!r}")
    return value


def identifier(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise SchemaError(f"{name}: invalid identifier")
    return value


def validate_registry(value, instruction=None):
    keys(value, {"instruction", "goals"}, "registry")
    original = text(value["instruction"], "instruction", 4096)
    if instruction is not None and original != instruction:
        raise SchemaError("registry must preserve the original instruction")
    goals = value["goals"]
    if not isinstance(goals, list) or not 1 <= len(goals) <= 12:
        raise SchemaError("registry needs 1..12 goals")
    seen = set()
    original_words = set(re.findall(r"\w+", original.lower()))
    for goal in goals:
        keys(goal, {"goal_ref", "source_text", "actor_text", "target", "destination", "kind"}, "goal")
        ref = identifier(goal["goal_ref"], "goal_ref")
        if ref in seen:
            raise SchemaError("duplicate goal_ref")
        seen.add(ref)
        if text(goal["source_text"], "source_text") not in original:
            raise SchemaError("source_text must be a literal span of the instruction")
        for key in ("actor_text", "target", "destination"):
            if key == "destination" and goal[key] is None:
                continue
            words = set(re.findall(r"\w+", text(goal[key], key).lower()))
            if not words or not words <= original_words:
                raise SchemaError(f"{key}: words must derive from the original instruction")
        enum(goal["kind"], {"transport", "mechanism"}, "kind")
    return deepcopy(value)


def camera_images(observation):
    """Resolve two unmodified RGB views; do not synthesize or render a view."""
    aliases = {"agentview": ("agentview_image", "image"),
               "wrist": ("robot0_eye_in_hand_image", "wrist_image")}
    output = {}
    nested = observation.get("images", {})
    if any(k not in {"agentview", "wrist", "robot0_eye_in_hand"} for k in nested):
        raise SchemaError("selector requires named agentview/wrist cameras only")
    for camera, names in aliases.items():
        candidates = [observation[n] for n in names if n in observation]
        candidates += [nested[n] for n in ((camera,) if camera == "agentview" else ("wrist", "robot0_eye_in_hand")) if n in nested]
        if not candidates:
            raise SchemaError(f"missing {camera} RGB image")
        first = np.asarray(candidates[0])
        if any(not np.array_equal(first, np.asarray(x)) for x in candidates[1:]):
            raise SchemaError(f"conflicting aliases for {camera}")
        if first.ndim != 3 or first.shape[-1] != 3 or first.dtype != np.uint8 or not first.size:
            raise SchemaError(f"{camera} must be nonempty uint8 HWC RGB")
        output[camera] = first
    return output


def sensor_copy(observation):
    # Use the fixed core's actual whitelist, never a second permissive copy.
    try:
        from benchmark.remaining_goals.runner import _observation
    except ImportError as error:
        raise RuntimeError("install/configure the pinned eval core before using sensors") from error
    result = _observation(observation)
    camera_images(result)
    return result


def validate_prediction(value, registry, query_id, snapshots):
    validate_registry(registry)
    integer(query_id, "query_id")
    keys(value, {"query_id", "goals"}, "prediction")
    if type(value["query_id"]) is not int or value["query_id"] != query_id:
        raise SchemaError("prediction query_id mismatch")
    available = {}
    for shot in snapshots:
        q = integer(shot["query_id"], "snapshot query")
        if q > query_id or shot["snapshot_id"] != f"q{q}" or q in available:
            raise SchemaError("future/duplicate/invalid snapshot")
        available[q] = shot
    registry_map = {g["goal_ref"]: g for g in registry["goals"]}
    rows = value["goals"]
    if not isinstance(rows, list) or len(rows) != len(registry_map):
        raise SchemaError("prediction must contain the complete fixed goal set")
    seen = set()
    for row in rows:
        keys(row, {"goal_ref", "entity_ref", "association", "role", "relation",
                   "release", "interaction", "evidence"}, "prediction goal")
        ref = row["goal_ref"]
        if not isinstance(ref, str) or ref not in registry_map or ref in seen:
            raise SchemaError("missing/extra/duplicate goal reference")
        seen.add(ref)
        ent = row["entity_ref"]
        if ent is not None:
            identifier(ent, "entity_ref")
        enum(row["association"], {"MATCHED", "UNKNOWN"}, "association")
        if (row["association"] == "MATCHED") != (ent is not None):
            raise SchemaError("MATCHED needs a sensor entity reference; UNKNOWN uses null")
        enum(row["role"], {"TARGET", "COMPLETED", "DISTRACTOR", "UNKNOWN"}, "role")
        enum(row["relation"], {"SAT", "UNSAT", "UNKNOWN"}, "relation")
        enum(row["interaction"], {"HELD", "NOT_HELD", "UNKNOWN"}, "interaction")
        release_states = ({"NOT_APPLICABLE"} if registry_map[ref]["kind"] == "mechanism"
                          else {"RELEASED", "NOT_RELEASED", "UNKNOWN"})
        enum(row["release"], release_states, "release")
        evidence = row["evidence"]
        if not isinstance(evidence, list) or len(evidence) > 12:
            raise SchemaError("evidence must contain at most 12 regions per goal")
        supported = set()
        for item in evidence:
            keys(item, {"goal_ref", "entity_ref", "query_id", "snapshot_id", "camera",
                        "bbox", "coordinate_system", "supports"}, "evidence")
            q = integer(item["query_id"], "evidence query")
            if q not in available or item["snapshot_id"] != f"q{q}":
                raise SchemaError("evidence references unavailable/future observation")
            if item["goal_ref"] != ref or item["entity_ref"] != ent:
                raise SchemaError("evidence must bind to its own goal/entity")
            enum(item["camera"], {"agentview", "wrist"}, "camera")
            enum(item["coordinate_system"], {"normalized_xyxy"}, "coordinate_system")
            bbox = item["bbox"]
            if bbox is not None:
                if (not isinstance(bbox, list) or len(bbox) != 4 or
                    any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in bbox)
                    or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
                    raise SchemaError("invalid normalized bbox")
            supports = item["supports"]
            if (not isinstance(supports, list) or not supports or
                any(not isinstance(x, str) or x not in {"entity", "role", "relation", "release", "interaction"} for x in supports)
                or len(set(supports)) != len(supports)):
                raise SchemaError("invalid evidence supports")
            if bbox is not None and ent is not None:
                supported.update(supports)
        for field, unknown in (("relation", "UNKNOWN"), ("interaction", "UNKNOWN"), ("role", "UNKNOWN")):
            if row[field] != unknown and field not in supported:
                raise SchemaError(f"{field}: non-UNKNOWN claim needs bound regional evidence")
        if row["release"] not in {"UNKNOWN", "NOT_APPLICABLE"} and "release" not in supported:
            raise SchemaError("release: claim needs bound regional evidence")
        if row["association"] == "MATCHED" and "entity" not in supported:
            raise SchemaError("entity association needs evidence")
    return deepcopy(value)


def validate_payload(payload):
    keys(payload, {"sensor", "context"}, "selector payload")
    context = payload["context"]
    keys(context, {"query_id", "instruction", "registry", "history", "commands"}, "context")
    query = integer(context["query_id"], "query_id")
    reg = validate_registry(context["registry"], context["instruction"])
    refs = {g["goal_ref"] for g in reg["goals"]}
    snapshots = payload["sensor"]
    if not isinstance(snapshots, list) or not 1 <= len(snapshots) <= 3:
        raise SchemaError("one current plus at most two historical dual-camera snapshots")
    clean, ids = [], []
    for snap in snapshots:
        keys(snap, {"query_id", "snapshot_id", "observation"}, "sensor snapshot")
        q = integer(snap["query_id"], "snapshot query")
        if q > query or snap["snapshot_id"] != f"q{q}":
            raise SchemaError("future or invalid snapshot")
        ids.append(q)
        clean.append({**snap, "observation": sensor_copy(snap["observation"])})
    if ids != sorted(set(ids)) or ids[-1] != query:
        raise SchemaError("ordered unique snapshots must end at the current query")
    history = context["history"]
    if not isinstance(history, list) or len(history) > 12:
        raise SchemaError("history limit exceeded")
    history_ids = []
    for record in history:
        keys(record, {"query_id", "goals"}, "history record")
        q = integer(record["query_id"], "history query")
        if q >= query:
            raise SchemaError("history cannot include current/future predictions")
        history_ids.append(q)
        if not isinstance(record["goals"], list) or len(record["goals"]) != len(refs):
            raise SchemaError("history goals incomplete")
        actual = []
        for row in record["goals"]:
            keys(row, {"goal_ref", "entity_ref", "relation", "release", "interaction",
                       "complete", "carrying", "evidence_queries"}, "history goal")
            actual.append(row["goal_ref"])
            if row["entity_ref"] is not None:
                identifier(row["entity_ref"], "history entity")
            enum(row["relation"], {"SAT","UNSAT","UNKNOWN"}, "history relation")
            enum(row["release"], {"RELEASED","NOT_RELEASED","UNKNOWN","NOT_APPLICABLE"}, "history release")
            enum(row["interaction"], {"HELD","NOT_HELD","UNKNOWN"}, "history interaction")
            if type(row["complete"]) is not bool or type(row["carrying"]) is not bool:
                raise SchemaError("history beliefs must be boolean predictions")
            eq = row["evidence_queries"]
            if not isinstance(eq, list) or len(eq) > 12 or any(type(x) is not int or not 1 <= x <= q for x in eq):
                raise SchemaError("history contains invalid/future evidence")
        if len(set(actual)) != len(refs) or set(actual) != refs:
            raise SchemaError("history goals differ from registry")
    if history_ids != sorted(set(history_ids)):
        raise SchemaError("history query IDs must be strictly increasing")
    commands = context["commands"]
    if not isinstance(commands, list) or len(commands) > 12:
        raise SchemaError("commands limit exceeded")
    command_ids = []
    texts = {g["goal_ref"]: g["actor_text"] for g in reg["goals"]}
    for command in commands:
        keys(command, {"query_id", "goal_ref", "instruction", "returned_chunk_length", "semantics"}, "command")
        q = integer(command["query_id"], "command query")
        command_ids.append(q)
        if q >= query or command["semantics"] != "command_not_execution":
            raise SchemaError("commands are past predictions, never execution evidence")
        ref = command["goal_ref"]
        if ref is not None and ref not in refs:
            raise SchemaError("command goal mismatch")
        if command["instruction"] != (texts[ref] if ref is not None else reg["instruction"]):
            raise SchemaError("command language must be the stable registry text")
        integer(command["returned_chunk_length"], "returned chunk length")
    if command_ids != sorted(set(command_ids)):
        raise SchemaError("command query IDs must be strictly increasing")
    return {"sensor": clean, "context": deepcopy(context)}
