"""Shared training/inference wire prompt, including explicit image identities."""
import copy
import json

IMAGE_KEYS = {"agentview_image": "agentview", "robot0_eye_in_hand_image": "wrist"}
IMAGE_ALIASES = {"agentview_image": ("agentview_image", "image"), "robot0_eye_in_hand_image": ("robot0_eye_in_hand_image", "wrist_image")}
PREDICTION_SCHEMA = '''Return only JSON with exactly these keys:
{"query_id":int,"goals":[{"goal_ref":str,"entity_ref":str|null,"association":"MATCHED|UNKNOWN","role":"TARGET|COMPLETED|DISTRACTOR|UNKNOWN","relation":"SAT|UNSAT|UNKNOWN","release":"RELEASED|NOT_RELEASED|UNKNOWN|NOT_APPLICABLE","interaction":"HELD|NOT_HELD|UNKNOWN","evidence":[{"goal_ref":str,"entity_ref":str|null,"query_id":int,"snapshot_id":"qN","camera":"agentview|wrist","bbox":[x1,y1,x2,y2]|null,"coordinate_system":"normalized_xyxy","supports":["entity|role|relation|release|interaction"]}]}]}.
Vertical bars describe enum alternatives, not literal strings. Return every fixed goal exactly once. Use only supplied snapshots, no future evidence. Boxes use normalized [0,1] xyxy coordinates. Evidence must name its matching goal/entity, query/snapshot and camera. Current meaningful evidence needs current query, nonnull entity and box. Mechanisms use NOT_APPLICABLE release. MATCHED requires an entity; unknown association uses null. Human-visible evidence only: commands are proposed commands, never proof of execution, grasp, release or completion. UNKNOWN expresses uncertainty. Never infer truth from unavailable physical state. SAT requires visible relation evidence; held identity must match the goal entity.'''
REGISTRY_SCHEMA = '''From the instruction alone return only JSON:
{"instruction":str,"goals":[{"goal_ref":"g0","source_text":str,"actor_text":str,"target":str,"destination":str|null,"kind":"transport|mechanism"}]}.
Use sequential fixed g0,g1,... goal IDs. source_text must occur verbatim in the instruction. All target/destination/actor words derive from the instruction. Preserve each goal's meaning; no invented objects, task IDs, state or completion claims. Keep the exact original instruction.'''


def bounded_payload(payload, use_history=True, max_images=6):
    result = copy.deepcopy(payload)
    q = result["context"]["query_id"]
    sensors = result["sensor"]
    for sensor in sensors:
        observation = sensor["observation"]
        canonical = {key: value for key, value in observation.items() if key not in {"images", "image", "wrist_image", *IMAGE_KEYS}}
        nested = observation.get("images", {})
        for key, names in IMAGE_ALIASES.items():
            values = [observation[n] for n in names if n in observation]
            values += [nested[n] for n in (("agentview",) if key == "agentview_image" else ("wrist", "robot0_eye_in_hand")) if n in nested]
            if values:
                canonical[key] = values[0]
        sensor["observation"] = canonical
    if not sensors or not any(s["query_id"] == q for s in sensors):
        raise ValueError("current sensor snapshot is required")
    if any(s["query_id"] > q for s in sensors):
        raise ValueError("future sensor snapshot")
    if len({s["query_id"] for s in sensors}) != len(sensors):
        raise ValueError("duplicate sensor query")
    sensors.sort(key=lambda s: s["query_id"])
    dropped = []
    if not use_history:
        dropped = [s["query_id"] for s in sensors if s["query_id"] != q]
        sensors[:] = [s for s in sensors if s["query_id"] == q]
        result["context"]["history"] = []
        result["context"]["commands"] = []
    def count():
        return sum(sum(k in s["observation"] for k in IMAGE_KEYS) for s in sensors)
    while count() > max_images or len(sensors) > 3:
        if sensors[0]["query_id"] == q:
            raise ValueError("current images exceed image budget")
        dropped.append(sensors.pop(0)["query_id"])
    if dropped:
        result["context"]["history"] = [h for h in result["context"]["history"] if h.get("query_id") not in dropped]
        result["context"]["commands"] = [h for h in result["context"]["commands"] if h.get("query_id") not in dropped]
    if len(result["context"]["history"]) > 12:
        result["context"]["history"] = result["context"]["history"][-12:]
    return result, dropped


def build_messages(payload=None, *, instruction=None, answer=None):
    if instruction is not None:
        messages = [{"role": "system", "content": REGISTRY_SCHEMA}, {"role": "user", "content": instruction}]
    else:
        content = [{"type": "text", "text": json.dumps(payload["context"], ensure_ascii=False, separators=(",", ":"))}]
        for sensor in payload["sensor"]:
            non_image = {k: v for k, v in sensor["observation"].items() if k not in IMAGE_KEYS}
            content.append({"type": "text", "text": json.dumps({"query_id": sensor["query_id"], "snapshot_id": sensor["snapshot_id"], "sensors": non_image}, default=lambda a: a.tolist(), separators=(",", ":"))})
            for key, camera in IMAGE_KEYS.items():
                if key in sensor["observation"]:
                    content.extend([{"type": "text", "text": f"snapshot={sensor['snapshot_id']} query={sensor['query_id']} camera={camera}"}, {"type": "image"}])
        messages = [{"role": "system", "content": PREDICTION_SCHEMA}, {"role": "user", "content": content}]
    if answer is not None:
        messages.append({"role": "assistant", "content": answer})
    return messages
