# Task023 bounded alignment diagnostics

This is a separate, user-launched evidence collection command. It consumes the
completed task022 annotation manifest, including `ready=false`, and writes a new
directory. It never generates answers, selector samples, labels or an export,
and never launches a teacher, training, evaluation or another job.

Run from the reviewed diagnostic implementation using the existing controller
Python environment. The old backend configuration supplies the existing worker
interpreter, module paths and per-source timeout; there is no new runtime config
or model prerequisite:

```sh
python -m egrs.offline diagnose-alignment --manifest /absolute/path/to/completed-task022/manifest.json --output /absolute/path/to/new-task023-diagnostics
```

The output must not exist and must be outside both the historical artifact tree
and the original source tree. Do not edit the historical manifest, backend config,
requests, images, results or annotations to make validation pass. Actual native
restoration/rendering is performed only when the user runs this command.

The fixed original train cases are:

| Source (`#demo_0`) | Existing requested probes |
|---|---|
| `libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5` | 0, 66, 129 |
| `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5` | 0, 72, 139 |

For each probe, the worker restores `same_state` at index `f`, `next_state` at
`f+1`, and `replay_action` at `f` followed by exactly existing action `f`.
There is no next-state clamp, settle/hold, alternate source, frame, action,
episode, orientation search or new camera. The existing measured identity
orientation and the two original cameras (`agentview`, `wrist`) are bound to the
old audit. The reusable worker supports applying an explicitly bound vertical
orientation to RGB and foreground together; this command does not select one.

The total conservative ceilings are 18 candidate restore attempts, 6 existing
action attempts, 36 completed image comparisons, and 72 direct render attempts
(one RGB and one segmentation call per camera/comparison). The counters count a
restore or paired render before the call, so a failed call can consume budget
without completing evidence. Initialization, restore and refresh may perform
internal renders; these are identified separately in `config.json` and the
unchanged initialization/stage audit, and remain bounded by the old per-source
timeout and reset/substep limits. There are no retries or expanded plans.

The historical production manifest identity is
`318c572532ac3f489d6da59e51039466579664501c69bed1fa113be3345549b4`,
with historical code identity
`b63e47c9c690937b528f5c03616db51b1f44b78971dd284f5d013241634d5a06`.
These remain historical evidence. A separate current source-byte identity locks
the absolute bootstrap and diagnostic worker before native construction, even
when the old method package appears in module paths or the working directory.
Production retains the fixed `LIBERO-core-c6-reference` checkout at
`c6dc98de0c54517c976057598b60f4cedf7fa3e5`, together with all existing
metadata/BDDL, asset, module and version locks. Synthetic fixtures require the
existing explicit, distinct synthetic backend scope and are marked in output.

Only consumed text artifacts and the twelve selected original PNG descriptors
and hashes are checked. The command does not rescan the other frozen images,
reconstruct windows, require export readiness or process the 200-source label
loop. The unchanged NativeAdapter checks original PNG pixels against each
designated HDF RGB frame during the user-run worker.

The output is entirely operational sidecar evidence:

| File | Contents |
|---|---|
| `config.json`, `requests.jsonl` | Fixed plan, budgets, old backend and selected bindings; old/current identities |
| `events.jsonl` | Flushed, ordered worker steps and inspection, including partial native initialization |
| `measurements.jsonl` | Source/frame/rule/camera RGB residual decomposition, orientation and hashes |
| `states.jsonl` | Independently labeled source-next versus replay and actual restored-next versus replay comparisons |
| `png-index.jsonl` | Every completed PNG, its binding, dimensions, path and SHA-256 |
| `errors.jsonl`, `progress.json` | Failure evidence and conservative counts/progress |
| `manifest.json` | Sealed final status, identities, source splits and hashes of completed output files |

Each completed comparison has original RGB, oriented candidate RGB, an unscaled
absolute difference (`x1`), a binary foreground mask and a labeled PNG comparison
panel. Whole, foreground and background MAE are normalized by 255. Counts are
pixels, not RGB channel values. Signed channel bias is candidate minus original,
also divided by 255. The old maximum of whole and foreground MAE is retained
only when the original foreground visibility minimum is met. Empty background
or insufficient foreground metrics are `null` with explicit reasons. Nothing
corrects source RGB, changes the old threshold or selects an alignment rule.

State hashes preserve the complete flattened bytes, dtype and length. Named
groups use the runtime state's `from_flattened(flat, sim)` API only after an
exact flatten round-trip. `time`, `qpos`, `qvel` and `act` errors are reported
separately in native units: qpos/qvel may themselves combine translational,
rotational or joint coordinates, so the full maximum mixes units. It is retained
as historical evidence, not a new acceptance threshold. A missing codec, failed
round-trip, absent field or unsupported layout produces explicit unavailable
group evidence; it never infers flattened slices. The reference robosuite codec
exposes time/qpos/qvel and omits act (with an `na==0` assertion); absent act is
reported as absent, not perfect zero agreement.

Native goal atoms are recorded independently for each candidate. Predicate
exceptions remain unknown (`null`) with error evidence. Native truths never
choose a rule or become labels. All arrays, masks, native audits and PNGs stay
outside selector samples, history, prompts and actor inputs.

A render/restore/native-operation failure stops that source's planned work;
timeout/crash kills and reaps the isolated worker. Completed PNGs, measurements
and events remain indexed, and other fixed source work can still complete.
Missing work, malformed events, close errors or mismatched result bindings cannot
produce a complete receipt. `complete` means the fixed diagnostic operations
finished; it does not certify alignment, semantic agreement or a correction.
The CLI prints the diagnostic status and returns exit code 1 for `partial` or
`failed`; the new manifest and completed sidecars remain available for review.

Implementation verification uses affected synthetic RGB, fake native boundaries
and subprocess tests only. No real source, native runtime, model or diagnostic
job was run to establish this implementation. The two cases cannot establish a
fix for all 200 sources, justify threshold changes or authorize relabeling or
training. Codex reviews/deploys; the user runs the diagnostic; Codex reviews the
resulting evidence before any later research decision.
