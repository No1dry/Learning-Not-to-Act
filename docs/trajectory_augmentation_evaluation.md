# Task035 same-adapter evaluation

The implementation prepares and runs one fixed final1000 `robot_rewind_mix`
adapter on the original nine tasks, ten sources each, in both10 and00 (180
new model episodes). This document does not authorize generation, training or
evaluation. The user confirms the new035 budget and starts real operations.

Copy `configs/trajectory_augmentation/eval_robot_rewind_mix.json` to an isolated
configuration location and fill its existing-source paths. Relative paths are
relative to that configuration. `base_runtime` is the original frozen SOG10
runtime (including original camera/crop/proprio/action normalization). There is
exactly one adapter path; it must contain schema `task035-oft-adapter-v1`, group
and recipe `robot_rewind_mix`, data kind `task035-generated-trajectories-v1`,
`update=final_update=1000`. A dev-selected or earlier checkpoint is rejected.

The six legacy10 entries use their original full-ten manifest/replay reader.
`legacy_sources_00` uses the existing `normal00-control` composite inventory;
its six task entries retain their original initial-only acceptance and recorded
release/five-observation endpoint. `new_sources_10` and `new_sources_00` use the
existing `nine-mask10` and `nine-normal00` inventories for the new three tasks.
New-three00 retains the official-success endpoint. Inventories retain their
original schema/populations; no regenerated states, acceptance migration or
benchmark edits are required. All nine tasks still use seed7/chunk8/H520, full
original instructions, original cameras/proprio/crop and every video.

File-only plan (no model/native environment creation):

```powershell
python -m egrs.trajectory_augmentation.evaluation plan --config <eval.json> --out <new-plan.json>
```

Only after the user authorizes and starts the real180-episode operation:

```powershell
python -m egrs.trajectory_augmentation.evaluation run --config <eval.json> --out <new-eval-directory>
```

One isolated worker loads the adapter once and is shared across all126 task
invocations: six ten-source legacy10 tasks and120 one-source scoped tasks.
Only current camera/robot sensors and the unchanged full instruction reach the
policy; condition/domain/task truth never selects an adapter or changes a prompt.
The benchmark owns reset, action decoding, stepping and endpoints. Every raw
result, query input, returned/executed action and full video remains in the new
output, with source archives and adapter/base lineage. A technical pause stops
the queue and preserves missing denominators. Existing output directories are
rejected; this entry point never retries or overwrites an episode.

File-only exact-evidence report, to a separate new directory:

```powershell
python -m egrs.trajectory_augmentation.evaluation report --run <eval-directory> --out <new-report-directory>
```

Reporting invokes the pinned core's original archive/raw/observation/query/
action/video readers and `score_verified_result`; it does not copy physical
scoring.10 then uses034's binary compliant mapper (unknown completed facts are
unsuccessful; errors/missing stay unresolved).00 uses the fixed core's official
goal metric, with preservation inapplicable; release diagnostics cannot reject
an official00 success. The original six00 and new-three00 endpoints remain
separate in path diagnostics. JSON includes both independent source reports,
coverage and integrity errors. Formal deltas appear only for complete,
compatible, verified90 populations, separately against10=22/90 and00=78/90.
No combined10/00 SR or cross-metric subtraction is emitted.
