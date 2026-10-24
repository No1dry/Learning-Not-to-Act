"""Field provenance is applied before teacher forcing, never only to loss."""
import copy
import json

CONFIRMED = {"human", "reviewed_candidate"}
PROVENANCE = CONFIRMED | {"weak", "sim_supervised"}
ROLE_FIELDS = {"entity_ref", "association", "role"}


def source_for(pointer, provenance):
    while True:
        if pointer in provenance:
            return provenance[pointer]
        if not pointer:
            return None
        pointer = pointer.rsplit("/", 1)[0]


def pointer_escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def prepare_answer(answer, provenance, role_supervision=True):
    if not isinstance(provenance, dict) or any(v not in PROVENANCE for v in provenance.values()):
        raise ValueError("provenance must map JSON pointers to human, reviewed_candidate, sim_supervised or weak")
    supervised = set()
    identity = {"goal_ref", "query_id"}

    def fully_confirmed(value, pointer):
        # Resolve the effective source at each leaf, including more-specific
        # overrides. Empty containers need their own inherited confirmation.
        if isinstance(value, dict) and value:
            return all(fully_confirmed(v, pointer + "/" + pointer_escape(k)) for k, v in value.items())
        if isinstance(value, list) and value:
            return all(fully_confirmed(v, pointer + "/" + str(i)) for i, v in enumerate(value))
        source = source_for(pointer, provenance)
        return source in CONFIRMED or (source == "sim_supervised" and value is not None and value != "UNKNOWN")

    # Even broad sim provenance cannot promote hidden/unsupported or UNKNOWN
    # values. Human-confirmed UNKNOWN retains its existing semantics.
    sim_fields, sim_evidence = set(), set()
    for i, row in enumerate(answer.get("goals", [])):
        base = f"/goals/{i}"
        supported = set()
        for j, item in enumerate(row.get("evidence", [])):
            pointer = base + f"/evidence/{j}"
            supports = item.get("supports", [])
            if (item.get("bbox") is not None and row.get("entity_ref") is not None
                    and item.get("entity_ref") == row["entity_ref"]
                    and item.get("goal_ref") == row.get("goal_ref")
                    and supports and fully_confirmed(item, pointer)
                    and all(s == "entity" or row.get(s) not in (None, "UNKNOWN", "NOT_APPLICABLE") for s in supports)):
                supported.update(supports)
                sim_evidence.add(pointer)
        if "entity" in supported:
            sim_fields.update({base + "/entity_ref", base + "/association"})
            for field in ("role", "relation", "interaction", "release"):
                if field in supported and row.get(field) not in (None, "UNKNOWN", "NOT_APPLICABLE"):
                    sim_fields.add(base + "/" + field)
        # A malformed held/released pair must not become sim training truth.
        if row.get("interaction") == "HELD" and row.get("release") == "RELEASED":
            sim_fields.discard(base + "/interaction")
            sim_fields.discard(base + "/release")
            sim_evidence = {p for p in sim_evidence if not p.startswith(base + "/evidence/")}

    def walk(value, pointer="", key="", output_pointer=""):
        source = source_for(pointer, provenance)
        confirmed = source in CONFIRMED or (source == "sim_supervised" and
            (pointer in sim_fields or any(pointer.startswith(p + "/") for p in sim_evidence)))
        if key == "physical_truth":
            raise ValueError("physical_truth cannot appear in an answer")
        if not role_supervision and key in ROLE_FIELDS:
            return None if key == "entity_ref" else "UNKNOWN"
        if key == "evidence":
            retained = []
            if role_supervision:
                for i, item in enumerate(value):
                    source_pointer = pointer + "/" + str(i)
                    if (fully_confirmed(item, source_pointer) and
                            (source_for(source_pointer, provenance) != "sim_supervised" or source_pointer in sim_evidence)):
                        # Filter before teacher forcing; supervise the compacted
                        # answer index while reading provenance at the source index.
                        retained.append(walk(item, source_pointer, output_pointer=output_pointer + "/" + str(len(retained))))
            return retained
        if isinstance(value, dict):
            return {k: walk(v, pointer + "/" + pointer_escape(k), k, output_pointer + "/" + pointer_escape(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, pointer + "/" + str(i), key, output_pointer + "/" + str(i)) for i, v in enumerate(value)]
        if confirmed:
            supervised.add(output_pointer)
            return copy.deepcopy(value)
        if key in identity:
            return copy.deepcopy(value)
        if key in {"entity_ref", "bbox"} or value is None:
            return None
        if key == "release" and value == "NOT_APPLICABLE":
            return value  # task kind, independent of observed physical state
        return "UNKNOWN" if isinstance(value, str) else None

    return walk(answer), supervised


def serialize_with_spans(value):
    """Canonical JSON and exact scalar character intervals, including quotes."""
    chunks, spans, position = [], {}, 0

    def emit(text):
        nonlocal position
        chunks.append(text)
        position += len(text)

    def walk(item, pointer=""):
        if isinstance(item, dict):
            emit("{")
            for i, (key, child) in enumerate(item.items()):
                if i:
                    emit(",")
                emit(json.dumps(key, ensure_ascii=False) + ":")
                walk(child, pointer + "/" + pointer_escape(key))
            emit("}")
        elif isinstance(item, list):
            emit("[")
            for i, child in enumerate(item):
                if i:
                    emit(",")
                walk(child, pointer + "/" + str(i))
            emit("]")
        else:
            start = position
            emit(json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
            spans[pointer] = (start, position)

    walk(value)
    return "".join(chunks), spans
