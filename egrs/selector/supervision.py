"""Field provenance is applied before teacher forcing, never only to loss."""
import copy
import json

CONFIRMED = {"human", "reviewed_candidate"}
PROVENANCE = CONFIRMED | {"weak"}
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
        raise ValueError("provenance must map JSON pointers to human, reviewed_candidate or weak")
    supervised = set()
    identity = {"goal_ref", "query_id"}

    def walk(value, pointer="", key=""):
        confirmed = source_for(pointer, provenance) in CONFIRMED
        if key == "physical_truth":
            raise ValueError("physical_truth cannot appear in an answer")
        if not role_supervision and key in ROLE_FIELDS:
            return None if key == "entity_ref" else "UNKNOWN"
        if key == "evidence" and (not confirmed or not role_supervision or any(p.startswith(pointer + "/") and s not in CONFIRMED for p, s in provenance.items())):
            # An evidence item itself asserts a physical/entity conclusion. Partial
            # evidence cannot be retained as teacher-forcing context.
            return []
        if isinstance(value, dict):
            return {k: walk(v, pointer + "/" + pointer_escape(k), k) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, pointer + "/" + str(i), key) for i, v in enumerate(value)]
        if confirmed:
            supervised.add(pointer)
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
