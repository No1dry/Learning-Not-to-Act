"""Rebind frozen Task055 A-precompleted states to the Task058 milk BDDL.

The physical state does not depend on which B object the goal names: milk is already
on the table in the 055 canonical scene. This rebind only swaps the derived BDDL,
instruction and goal specs, and copies state.npy byte-for-byte. Provenance records
the 055 source it came from.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from egrs.composition057 import catalog as c057


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(bank055, canonical_bddl, output, pairs=(("probe_soup_milk", "composition_soup_butter"),
                                                  ("probe_tomato_milk", "composition_tomato_butter")),
          start=0, count=50):
    bank055 = Path(bank055).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("rebind requires a fresh output")
    rows = json.loads((bank055 / "sources.json").read_text(encoding="utf-8"))["rows"]
    canonical = Path(canonical_bddl).read_text(encoding="utf-8")
    manifest_rows = []
    for task_id, source_task in pairs:
        profile = c057.get_task(task_id)
        bddl_text = c057.render_bddl(canonical, task_id)
        selected = [row for row in rows if row["task_id"] == source_task][start:start + count]
        for index, row in enumerate(selected):
            source_dir = Path(row["source_manifest"]).resolve().parent
            state = source_dir / "state.npy"
            episode_id = f"cf_{task_id}_s{index:03d}_10"
            target = output / "sources" / episode_id
            target.mkdir(parents=True)
            (target / "task.bddl").write_text(bddl_text, encoding="utf-8")
            (target / "state.npy").write_bytes(state.read_bytes())
            episode = {
                "episode_id": episode_id,
                "task_id": task_id,
                "suite": c057.TASK_SUITE,
                "task_name": profile["name"],
                "instruction": profile["instruction"],
                "initial_state_index": index,
                "initial_mask": [True, False],
                "source_id": f"rebind058|{row['episode_id']}",
                "seed": index,
                "horizon": 520,
                "retention_steps": 150,
                "goal_specs": profile["goals"],
                "bddl_sha256": hashlib.sha256(bddl_text.encode()).hexdigest(),
                "model_xml_sha256": json.loads((source_dir / "source.json").read_text(encoding="utf-8"))["episode"]["model_xml_sha256"],
                "state_path": "state.npy",
                "state_sha256": _sha(target / "state.npy"),
                "initial_observation": {"path": "state.npy", "sha256": _sha(target / "state.npy")},
            }
            manifest = {
                "schema_version": "remaining-composition058-rebind-v1",
                "episode": episode,
                "environment": json.loads((source_dir / "source.json").read_text(encoding="utf-8"))["environment"],
                "ancestry": {"rebound_from": row["episode_id"], "source_bank": str(bank055)},
                "provenance": {"kind": "rebind_frozen_composition055_state",
                               "note": "state bytes copied; only BDDL/goal/instruction changed"},
                "artifacts": {"task.bddl": _sha(target / "task.bddl"),
                              "state.npy": _sha(target / "state.npy")},
            }
            path = target / "source.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_rows.append({"episode_id": episode_id, "task_id": task_id,
                                  "initial_state_index": index,
                                  "source_manifest": str(path),
                                  "source_manifest_sha256": _sha(path)})
    report = {"schema_version": "task058-rebind-bank-v1", "ready": len(manifest_rows),
              "failed": 0, "complete": True, "rows": manifest_rows, "output": str(output)}
    (output / "sources.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
