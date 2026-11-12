# 030 v2 R2: sparse ordinary-demo progress production

The delivered producer is `egrs.augmentation.progress` with the concrete isolated
`NativeProgressBackend`. A user-started export can produce PROGRESS indexes in
the same operation. No external recovery script is required. The metadata plan
does not open HDF arrays, create a simulator, render images, or load a model.
Real local restoration/export remains a separately authorized, user-started job;
the CPU/fake checks do not establish real data readiness.

## Fixed dependencies and configuration

Copy [progress_native.example.json](../configs/augmentation/progress_native.example.json)
to a new local file. `/absolute/path/to/...` and the alignment evidence reference
are deployment placeholders. The empty runtime locks are deliberately incomplete;
the native worker rejects them. Bind actual paths and collected locks before
production. The example has a complete basket goal inventory from
[data_scope.json](../egrs/augmentation/data_scope.json), not a claim that basket
demonstrations have already been acquired or checked.

The existing accepted sources establish these separate identities:

| Dependency | Fixed identity and use |
| --- | --- |
| Historical restoration adapter | `Learning-Not-to-Act@fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391`; accepted Task023 implementation |
| Annotation reference core | `LIBERO-Remain@c6dc98de0c54517c976057598b60f4cedf7fa3e5`, `allow_reference: true` |
| Native LIBERO source | `8f1084e3132a39270c3a13ebe37270a43ece2a01`, with selected BDDL byte hashes |
| Ordinary dataset | `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3` |
| Nine-task scope | `191eabf1dad8bebc1cf2a39d26a98308ed4d6338` |

The adapter pin is enforced by
[progress_native_files.json](../egrs/augmentation/progress_native_files.json):
all listed accepted source files must match their SHA256, with checkout CRLF
normalized to LF. This reuses the isolated historical checkout without merging
old PRs or importing its selector pipeline into training. The reference core
is the annotation dependency from the accepted historical configuration; the
evaluation core remains the separate dependency documented in
[augmentation_commands.md](augmentation_commands.md).

Use an existing compatible annotation environment with modern `mujoco`,
LIBERO, robosuite, NumPy, h5py, Pillow, and functioning offscreen rendering.
Keep its previously reviewed rendering/environment settings. The selected
interpreter and ordered `backend.module_paths` must resolve the pinned LIBERO
and robosuite sources. If installation is needed,
use the reviewed environment lock and explicit source checkout, for example:

```bash
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/this-method
conda run -p /absolute/path/to/annotation-env python -m pip install -r /absolute/path/to/reviewed-native-requirements.txt
conda run -p /absolute/path/to/annotation-env python -m pip install --no-deps -e /absolute/path/to/LIBERO
```

The requirements lock and source paths above are inputs supplied by deployment,
not new package versions to guess or download as part of a plan. Existing
compatible environments can be reused without installation. The export
environment needs this method package, NumPy, h5py and Pillow; it does not need
the model or native simulator. Set `backend.python` to the annotation
interpreter's absolute executable path. Set `backend.historical_root` to the
isolated accepted method checkout. The loader resolves relative interpreter,
historical-root, recorded-report, module-path, native core-root, BDDL-root and
named asset-root paths against the new config's directory. Prefer the sealed
configuration's actual absolute paths. Preserve `native.core.root` as `root`
and preserve `asset_roots` as a dictionary with `libero`/`robosuite` keys.

The primary deployment workflow reuses the existing sealed Task022/023 native
backend configuration, including its real runtime version/module/BDDL locks.
Codex supplies and checks its actual file and interpreter/source paths, then
copies these objects into a new progress config. This requires no re-entry of
the 200 source records or recollection of unchanged accepted module locks.
The following preparation uses only JSON metadata and creates a new file;
replace the explicit paths with the deployed locations before executing it:

```python
from copy import deepcopy
import json
from pathlib import Path

old = json.loads(Path('/absolute/path/to/sealed-task023-sim-backend.json').read_text(encoding='utf-8-sig'))
new = json.loads(Path('/absolute/path/to/this-method/configs/augmentation/progress_native.example.json').read_text(encoding='utf-8-sig'))
new['backend'] = {
    'kind': 'native',
    'historical_root': '/absolute/path/to/accepted-method-at-fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391',
    'python': old['worker']['python'],
    'module_paths': deepcopy(old['worker']['module_paths']),
    'timeout_seconds': old['worker']['timeout_seconds'],
    'native': deepcopy(old['native']),
}
# Deployment supplies source-bound task/source bindings and the actual
# state_alignment_basis; the example binding is not alignment evidence.
with Path('/absolute/path/to/progress.local.json').open('x', encoding='utf-8') as stream:
    json.dump(new, stream, ensure_ascii=False, indent=2, allow_nan=False)
```

Retain the fixed core revision and strict thresholds above. Do not copy the
outer legacy `format` or `expected` objects, or nest its `worker` object in the
new backend. `native.versions` must include exact installed
`numpy`, `h5py`, `robosuite`, and `mujoco` versions. `native.module_sha256`
must hash the actual installed source bytes for:

- `libero.libero.envs.bddl_base_domain`
- `libero.libero.envs.predicates.base_predicates`
- `robosuite.environments.robot_env`

Codex checks that the sealed `libero_source.bddl_sha256` map also covers every
new planned nine-task BDDL, and adds only missing verified entries. The old
20-file map does not establish availability of these additional files.
If a lock is missing or the actual installation differs, the fallback
standard-library-only lock collection
recipe is in its `docs/offline_sim_supervision.md`, section “配置独立运行环境”.
Run that recipe using the selected annotation interpreter and explicit source
paths; it reads package metadata/source bytes and does not import a simulator
or read trajectories. Copy its `versions`, `module_sha256`, and `libero_source`
into `backend.native`. Extend only the selected BDDL list to the exact planned
task files: `<source file's suite>/<official_task_name>.bddl`, verified against
the fixed LIBERO revision's Git bytes. Preserve the collected paths and revision
verification basis as deployment evidence. Do not substitute arbitrary hashes
or treat a directory name as a revision check. If embedded source BDDL is
missing, exact installed-BDDL identity is required and historical embedded-byte
equality remains unverified.

## Original files and explicit bindings

Use the existing bound source manifest and sealed 200-source base inventory;
do not hand-enter another 200 records. The manifest retains the original
160 train / 40 dev base split, complete-trajectory duplicate grouping, source
file SHA256, exact language, and original action/proprio normalization.
Additional ordinary compound sources must satisfy the fixed scope and natural
demo selection rules. Files must already exist beneath `manifest.data_root`;
the producer does not acquire missing data.

The native path needs the original `states`, `actions`,
`obs/agentview_rgb`, `obs/eye_in_hand_rgb`, saved episode `model_file`, and
`data.attrs.env_args` with original robot/controller/camera settings.
It also checks the saved `macros_image_convention`, exact language binding,
task identifiers and BDDL, compiled XML/name/layout, permitted asset roots,
and complete native final goal atoms. Missing or conflicting information
remains an exclusion with diagnostics. Original HDFs are not rewritten.
Proprio uses ordered `obs/ee_pos` + `obs/ee_ori` + `obs/gripper_states`
or `obs/ee_states` + `obs/gripper_states`, totaling eight dimensions.

`task_bindings` applies one verified binding to every manifest source with
that exact `task_key`. `source_bindings` overrides it by exact source ID.
Unbound sources remain RAW. An old `domain=base` source can receive PROGRESS
when explicitly bound to its complete multi-goal native task; single-goal
sources remain RAW. New `domain=compound` bindings must equal all three scope
fields: `official_task_name`, `active_goals`, and `invariant_predicates`.
Copy complete goal inventories, including holding constraints, from the fixed
scope. Nine-task coverage is not a prerequisite for using reliable available
anchors.

The example's `opengl`, `same_state`, `identity`, and zero offsets illustrate
one declaration; they are not inferred facts about an uninspected file.
Replace them and `state_alignment_basis` with the source-bound correspondence
evidence. Observation/action offsets must equal the training mapping.
`next_state` requires `state_offset = observation_offset + 1`;
`same_state` and `replay_action` require `state_offset = observation_offset`;
`replay_action` also requires equal action and observation offsets.
The reused native episode reader requires states, actions and original RGB to
have the same physical length; the bridge accepts equal observation/action
offsets, including a shared positive offset such as one, with physical length
`source.length + observation_offset`. Unequal native offsets/physical arrays
remain a diagnostic RAW fallback, without truncating or rewriting the source.
The source convention is `opengl` or `opencv`; the correspondence orientation
is separately `identity` or `flip_vertical`. Export camera transforms remain
the explicit original preprocessing mapping. Array lengths do not establish
alignment.

`selection.start`, `stride`, and `max_anchors_per_source` define the finite
success-independent population. A binding may instead supply `anchors: [t,...]`
or local half-open `windows: [[start,stop],...]`. Windows inspect each included
time, so keep them small and predeclare them. Duplicate anchors, full-trajectory
coverage, invalid offsets, or exceeding the cap are rejected. The native
backend compares the three accepted correspondence candidates only at each
planned anchor and checks the selected current state's final goal facts.
Unresolved/ambiguous correspondence or false/unknown holding constraints do
not produce an enhanced example. A final frame without the required stored
next-state proof is excluded rather than clamped.

## Plan and user-started export

After deployment supplies actual manifest/config paths, these are the complete
entry commands. Run from the current method checkout, or install its package
in the export interpreter. Use a new plan filename and output directory.

```bash
conda run -p /absolute/path/to/export-env python -m egrs.augmentation.progress plan --manifest /absolute/path/to/sources.local.json --base-inventory /absolute/path/to/base-inventory.json --config /absolute/path/to/progress.local.json --output /absolute/path/to/progress-plan.json
```

Review `planned_sources`, `planned_anchors`, `source_plans`,
`excluded_sources`, and `maximum_restores`. The native maximum is four local
restorations per anchor: up to three correspondence candidates plus one
repeat of the selected candidate for native facts. The count excludes
per-source initialization, scene reset/XML compilation, and other setup
overhead. Planning performs no restoration and is not a compatibility test.

Only when the user starts the authorized real export:

```bash
conda run -p /absolute/path/to/export-env python -m egrs.augmentation.export --manifest /absolute/path/to/sources.local.json --base-inventory /absolute/path/to/base-inventory.json --progress-config /absolute/path/to/progress.local.json --output /absolute/path/to/new-progress-export
```

This writes `sources.json`, `windows.jsonl`, `evidence.json`, `report.json`,
and `progress_report.json`. Inspect accepted/terminal/excluded anchor counts,
source errors, retained native dependency/XML/asset/name/runtime inspection,
native audit records, correspondence measurements, source/state hashes and
explicit state/observation/action bindings. Setup/correspondence gaps remain reported
and retain RAW rather than generating fabricated pending goals. All-final
anchors add no FINISH or parking supervision.

Each accepted anchor contributes exactly one PROGRESS index at its current
`t`. No frames between anchors are labeled by interpolation. The item keeps
the complete source instruction and the original expert action chunk of up
to eight steps from `t`, with only the episode tail masked. The chunk may
cross a later goal transition. Offline pending-goal labels, states, native
facts, correspondence, hashes and exclusion reasons do not enter the model
item, policy prompt/history or evaluation stop decision.

The builtin producer emits no ATOMIC segments. Without separately reviewed
whole-segment action ownership, that pool stays empty and its sampling mass
falls back to RAW. Existing trusted segment evidence can still be supplied
via `--evidence`; a goal transition does not establish exclusive action
ownership. Use the exported pool counts and training's actual view ratios
instead of claiming the requested mixture was achieved.

## Reuse the exact produced evidence

Save the original `progress_report.json` and its byte SHA256. To re-export
without native restoration, keep the exact source manifest, binding objects,
and requested anchors, and replace only `backend` in a copied local config:

```json
{
  "kind": "recorded",
  "report": "/absolute/path/to/previous-export/progress_report.json",
  "sha256": "<ACTUAL_64_LOWERCASE_HEX_SHA256_OF_REPORT_BYTES>"
}
```

Use that copied file with the same `--progress-config` export command and a
new output directory. The recorded backend checks report bytes, report
identity, exact source identity and binding identity, and only reuses recorded
requested anchors. It opens no simulator and does not invent unrecorded
times. Original HDF file hashes and source bindings are still checked during
export/dataset construction. Alternatively the produced `evidence.json`
can be supplied with `--evidence` and no `--progress-config` for evidence-only
re-export; retain its production report beside it for audit. Neither reuse
route relaxes anchor validation or converts diagnostics into observations.
