"""Revocable predicted beliefs; never evaluator truth or an action controller."""
from copy import deepcopy
from .contracts import validate_registry, SchemaError


class EvidenceMemory:
    def __init__(self, registry, *, sat_queries=2, expiry_queries=3, max_records=12):
        if (type(sat_queries) is not int or sat_queries < 2 or type(expiry_queries) is not int
            or expiry_queries < 1 or type(max_records) is not int or not 1 <= max_records <= 12):
            raise ValueError("invalid evidence-memory thresholds")
        self.registry = validate_registry(registry)
        self.sat_queries, self.expiry_queries, self.max_records = sat_queries, expiry_queries, max_records
        self.records, self.query_id = [], 0
        self.beliefs = {g["goal_ref"]: {"entity_ref": None, "complete": False, "carrying": False,
                         "sat_streak": 0, "unseen": 0, "carry_unseen": 0, "current_unsat": False}
                        for g in self.registry["goals"]}

    def update(self, prediction):
        query = prediction["query_id"]
        if query != self.query_id + 1:
            raise SchemaError("memory needs exactly one update per consecutive query")
        self.query_id = query
        kinds = {g["goal_ref"]: g["kind"] for g in self.registry["goals"]}
        summaries = []
        for row in prediction["goals"]:
            b = self.beliefs[row["goal_ref"]]
            fresh = set()
            for item in row["evidence"]:
                if item["query_id"] == query and item["bbox"] is not None and row["association"] == "MATCHED":
                    fresh.update(item["supports"])
            identity = "entity" in fresh
            changed = identity and b["entity_ref"] is not None and b["entity_ref"] != row["entity_ref"]
            if changed:
                b.update(complete=False, carrying=False, sat_streak=0)
            if identity:
                b["entity_ref"] = row["entity_ref"]
            bound = row["entity_ref"] is not None and row["entity_ref"] == b["entity_ref"]
            if not bound:
                # Evidence for B cannot update a cached belief about A. A fresh
                # entity association above can establish B; stale association cannot.
                fresh.clear()
            b["current_unsat"] = ("relation" in fresh and row["relation"] == "UNSAT")
            known = "relation" in fresh and row["relation"] != "UNKNOWN"
            released = "release" in fresh and row["release"] == "RELEASED"
            not_held = "interaction" in fresh and row["interaction"] == "NOT_HELD"
            held = "interaction" in fresh and row["interaction"] == "HELD" and identity
            if released or not_held or changed:
                b["carrying"] = False
                b["carry_unseen"] = 0
            if held and not released:
                b["carrying"] = True
                b["carry_unseen"] = 0
            elif not released and not not_held:
                b["carry_unseen"] += 1
            if b["carry_unseen"] >= self.expiry_queries:
                b["carrying"] = False
            completion_support = (known and row["relation"] == "SAT"
                and (kinds[row["goal_ref"]] == "mechanism" or released) and not held)
            b["unseen"] = 0 if completion_support else b["unseen"] + 1
            b["sat_streak"] = b["sat_streak"] + 1 if completion_support else 0
            contradiction = b["current_unsat"] or held or ("release" in fresh and row["release"] == "NOT_RELEASED")
            if contradiction or b["unseen"] >= self.expiry_queries:
                b["complete"] = False
            elif b["sat_streak"] >= self.sat_queries:
                b["complete"] = True
            summaries.append({"goal_ref": row["goal_ref"], "entity_ref": b["entity_ref"],
                "relation": row["relation"] if bound else "UNKNOWN",
                "release": row["release"] if bound or kinds[row["goal_ref"]] == "mechanism" else "UNKNOWN",
                "interaction": row["interaction"] if bound else "UNKNOWN",
                "complete": b["complete"], "carrying": b["carrying"],
                "evidence_queries": sorted({e["query_id"] for e in row["evidence"]}) if bound else []})
        self.records.append({"query_id": query, "goals": summaries})
        self.records = self.records[-self.max_records:]
        return deepcopy(summaries)

    def choose(self, current):
        goals = {g["goal_ref"]: g for g in self.registry["goals"]}
        if current in self.beliefs and self.beliefs[current]["carrying"]:
            selected, reason = current, "carry"
        else:
            remaining = [g for g, b in self.beliefs.items() if b["current_unsat"]]
            selected = current if current in remaining else (remaining[0] if remaining else None)
            reason = "current_unsat" if selected is not None else "original_fallback"
        return {"goal_ref": selected, "reason": reason,
                "instruction": goals[selected]["actor_text"] if selected is not None else self.registry["instruction"]}
