# Task017 offline candidate and human review pipeline

Task018 adds bounded teacher-output decoding and a CPU-only `diagnose` command on the implementation branch. See [teacher wire protocol and diagnostics](teacher_wire_diagnostics.md) for the versioned behavior, exact commands and unchanged research boundaries. The task017 verification below remains its historical evidence.

This is software for separately invoked stages, not an experiment run. The task017 implementation extends the accepted task016 code (`5a77f158`) on the implementation branch; it is not available in the old fixed task016 commit or a main branch without the implementation. Use the reviewed task017 PR commit supplied by Codex. Do not install into the frozen VLA actor environment.

No real sources, teacher calls, human confirmations, training or model evaluations were performed for this delivery. Tests use small synthetic HDF5 files, fake model outputs and synthetic review events. Software completion does not establish dataset quality, task coverage, VRAM requirements or research readiness.

## Prerequisites and immutable identities

- Source catalog: all 20 files in `data/catalog.json`, dataset `yifengzhu-hf/LIBERO-datasets`, revision `147fa5eb607bb696dd922c3518084a90954cd2f3`. Keep suite subdirectories under your local dataset root. Only `demo_0` through `demo_9` are selected; never substitute `demo_10` for a gap.
- Offline teacher: `Qwen/Qwen2.5-VL-7B-Instruct`, model and processor revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`. `configs/teacher_offline.json` fixes explicit Qwen2.5 class, bf16, batch1, deterministic generation and budgets. Model/processor must already be present in the local Hugging Face cache. The loader uses `local_files_only=true`, has no paid API, LoRA, quantization, fallback or retry. The 3B student pin and its loader remain separate.
- Use the existing isolated selector environment described by `requirements-selector.txt`. Environment provisioning, model/data acquisition and real processing stages are separate actions, not launched by these commands automatically. The narrow raw-file transfer exception below does not authorize processing. Install this reviewed checkout into that environment with `python -m pip install --no-deps -e .`. Inventory/preparation additionally require h5py/Pillow/NumPy. Static help and plan need no HDF5/model/native imports.
- For visual candidates, provide a core dependency JSON using `configs/core.example.json`: an absolute clean checkout root and exact `515e87d9b93ab838428791273a0f3020d6f56e9c` revision. Existing `egrs.core.activate` verifies it before sensor validation. The accepted `c6dc98de0c54517c976057598b60f4cedf7fa3e5` reference checkout is usable only with `allow_reference: true`; that is reference validation, not an evaluation result. Optional `git_executable` names a local Git executable. No core simulation, rendering, VLA or scoring is run by the offline pipeline.

All `--output` arguments name **new directories**. Existing paths are refused, including after failures. Do not remove or overwrite partial runs. Each command returns a small receipt; complete manifests and raw audits are written to disk. Identity hashes detect accidental changes; they are not authenticated signatures or proof of a person's identity.

User-only cache acquisition, **not executed for this delivery**: in the isolated environment with the pinned `huggingface-hub==0.30.2`, this separate command downloads the fixed teacher snapshot into the default Hugging Face cache used by the loader. Keep the same cache environment (`HF_HOME`, if configured) for later teacher commands. It does not start inference:

```sh
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct --revision cc594898137f460bfe9f0759e9844b3ce807cfb5
```

For the approved source budget, see [selector data v1](experiment_plans/2026-10-23_selector_data_v1.md). Under the explicit 2026-10-23 network exception recorded in [AGENTS.md](../AGENTS.md), collaborating Codex separately downloads the fixed20 raw files locally and transfers them by SSH after the server download failed. This authorizes only byte transfer and integrity checks, not HDF5 trajectory reading, inventory/extraction, candidate inference, training or evaluation. Transfer progress belongs to its own logs; it does not establish200 valid sources or a ready training set. The offline pipeline performs neither dataset nor model downloads; X performed no real acquisition or processing during this implementation.

## Run each stage explicitly

The following commands use the Python interpreter of the isolated environment. Paths such as `local/libero` and `runs/017/...` are user-chosen local paths. None of these commands starts the next stage, training or evaluation.

```sh
python -m egrs.offline --help
python -m egrs.offline plan

python -m egrs.offline inventory --root local/libero --output runs/017/01-inventory
```

`inventory.json` retains all 200 planned source identities and source splits, available sources, exact original language, common camera length, orientation and explicit gaps. Split assignment is frozen **before opening files**, using existing `grouped_split`, seed0 and approximately 80/20 within task strata. All later stages carry these assignments, including missing/unreviewed sources. Known aliases cannot cross splits. Unknown physical ancestry remains disclosed.

Optional `--aliases aliases.json` maps exact `suite/file.hdf5#demo_N` source IDs to `{"group_ids":["explicit-known-alias"],"ancestry_known":false}`. Supply known aliases before inventory; adding them later requires a new inventory/version, never relabeling an existing split. Optional `--instruction-map instruction-map.json` maps `suite/file.hdf5` to `{"instruction":"exact human-supplied instruction","reviewer":"actual reviewer identity","basis":"where the instruction came from"}`. It is used only for an absent instruction. Nonempty original language is preserved verbatim; invalid language metadata is a gap, not silently replaced.

```sh
python -m egrs.offline registry-candidates --inventory runs/017/01-inventory/inventory.json --config configs/teacher_offline.json --output runs/017/02-registry-candidates
python -m egrs.offline registry-review-export --manifest runs/017/02-registry-candidates/registries.json --output runs/017/03-registry-review
```

Open `runs/017/03-registry-review/index.html` directly in a local browser. No server is required. Exact instruction identities, not task IDs, key registries. The human reviewer enters their identity, edits goal wording using the form, confirms the complete registry against the instruction, and exports `registry-review.json`. Failed/null registries can be explicitly drafted in the UI. Editing a confirmed registry clears its confirmation. Resume accepts a saved session only for the same immutable manifest. AI outputs must never be signed as human review.

```sh
python -m egrs.offline registry-review-import --manifest runs/017/02-registry-candidates/registries.json --session local/registry-review.json --output runs/017/04-registries-confirmed
python -m egrs.offline prepare --inventory runs/017/01-inventory/inventory.json --registries runs/017/04-registries-confirmed/registries-confirmed.json --output runs/017/05-windows
```

Unconfirmed/missing registries produce source gaps, so partial registry review is allowed. Extraction reads only the stored `agentview_rgb` and `eye_in_hand_rgb` datasets. Both must be nonempty uint8 THWC RGB with equal lengths. No shortest-stream fallback, image flip, crop, state restore or renderer. Original `macros_image_convention` (or `unknown`) and frame indices stay in operational sidecars.

Each source has anchors `floor(i*(T-1)/5)` for `i=0..5`; each window uses `[anchor-16,anchor-8,anchor]`, clamped, unique and ascending. Duplicate windows are removed. Within each window, query IDs start at1 and increase densely. Each query sees only that window's past/current snapshots, at most three dual-camera snapshots. These IDs do not claim to be original HDF5 frame indices. The budget is at most 200 sources / 1,200 windows / 3,600 queries; shorter episodes, deduplication and gaps reduce it.

```sh
python -m egrs.offline candidates --windows runs/017/05-windows/windows.json --config configs/teacher_offline.json --core-config local/core.json --output runs/017/06-candidates
```

One teacher backend is loaded lazily for this invocation. Registry and visual candidates are separate commands because human registry confirmation must precede extraction. Visual prompts use the existing sensor/context, schema and encoding: at most six images, 256 visual tokens per image, total4096 including at most1024 answer tokens. If the prompt exceeds3072 tokens, the stage records a failure; it does not trim, retry or substitute a model. The frozen review/training payload is therefore precisely the attempted input. File paths are image-loading references and never become prompt text; source IDs, task filenames, original frame indices, orientation and audit are not model context.

At every new window, memory is empty and `commands=[]`. Only prior legal machine predictions update existing `EvidenceMemory`, marked `history_provenance=model_prediction`. No human labels are backfilled into already generated history. JSON/schema/model errors retain `answer=null`, raw text when available, and the error. They are not converted to UNKNOWN. After a failed query, remaining queries in that window are retained as null/unattempted, because continuing would require inventing a consecutive memory update. Independent later windows proceed.

The candidate manifest reports attempted, succeeded, failed and unattempted query counts separately; actual model generation attempts are also audited (`generation_attempted`), distinct from preflight/load errors. Configuration/prompt identity, actual messages/payload, token counts where available and elapsed call time are retained. `candidates.partial.json` is an initial header; `candidates.partial.jsonl` is an append-only journal of completed query records and attempts. Interruptions preserve these files. They are evidence, not an automatic resume or retry command. The final `candidates.json` is written only after normal completion.

```sh
python -m egrs.offline review-export --manifest runs/017/06-candidates/candidates.json --output runs/017/07-review
```

Open `runs/017/07-review/index.html`. Copy the **whole review directory**, including its `images/` folder, to move it. Embedded JSON and relative image assets make `file://` work without fetch/CORS/server/remote assets. The original canonical training image paths remain untouched; the display mapping is separate. Only images legally present in each frozen sample are displayed. Boxes are canvas overlays and never alter training/VLA pixels.

The queue rotates tasks and sources, independent of confidence or success. Inspect current/past camera views, fixed instruction/registry and past model history. Edit entity/association/role/relation/release/interaction fields and evidence goal/entity/query/camera/normalized box/supports with form controls. Add/remove evidence items as needed. A field checkbox confirms only that field; an evidence checkbox confirms that **complete item**, including all bindings and supports. There is no whole-sample promotion. Changing entity/association/evidence clears dependent goal confirmations; changing another label clears its confirmation. Import also checks saved confirmation values/dependencies and refuses stale confirmations.

Null candidates have a “Create editable answer draft” button. Draft UNKNOWN values remain unconfirmed; a supervised UNKNOWN requires an explicit human field confirmation. Skip leaves fields weak. Enter the real reviewer identity yourself; none is filled automatically. Export the review JSON regularly. “Resume JSON” validates the immutable manifest and original sample identities before replacing the session. Operational identity, source, split, original payload and physical truth cannot be edited by the review form. The importer rebuilds provenance from explicit confirmation records, not from arbitrary provenance pasted into the JSON.

```sh
python -m egrs.offline review-import --manifest runs/017/06-candidates/candidates.json --session local/annotations-review.json --output runs/017/08-reviewed
```

The output contains complete records, including null/weak/unreviewed records, plus a separate audit and the saved session. The audit reports actual confirmed field/item count, changed answer count and observed UI event intervals; it does not estimate labor hours, prove human identity, or promise annotation accuracy. A suggested deterministic approximately10% stratified window re-review list is produced at build time. It is an optional work-organization suggestion, not a new model experiment gate.

## Build the confirmed subset

Create an external attestation JSON with all flags initially unset:

```json
{
  "six_composites_excluded": null,
  "semantic_equivalents_excluded": null,
  "eval_sources_excluded": null,
  "basis": ""
}
```

The actual responsible person must assess the catalog against the six composite tasks, semantic equivalents and known same/derived evaluation sources, document the basis, and explicitly set each assertion to `true` before build accepts it. These flags are never inferred from teacher predictions or prefilled by a stage. The six composites and fixed evaluation exclusions are listed in `data/catalog.json`. Unknown physical ancestry is still reported; the tool does not claim proof about unseen scenes.

```sh
python -m egrs.offline build --manifest runs/017/06-candidates/candidates.json --session local/annotations-review.json --attestation local/exclusions.json --output runs/017/09-dataset
```

Build revalidates the original manifest/session, invokes the existing annotation importer and dataset builder, and preserves the inventory source split even when review omits whole sources. Only records with confirmed supervised fields enter `train.jsonl` / `dev.jsonl`; the existing `prepare_answer` and encoder still neutralize unconfirmed values and filter/compact evidence before final token masking. You do not need to confirm all fields in all3,600 possible queries to build a useful partial subset.

Outputs include `report.json`, `all-candidates.json`, `all-reviewed.json`, `unreviewed.json` and `audit.json`. Counts distinguish sources/windows/queries and train/dev candidate and supervised coverage; source gaps and unknown ancestry are retained. Missing sources, null/weak records, an empty split, or any unconfirmed label field/evidence item prevent a full `ready` claim, even when every query already has some usable supervision. The unreviewed report lists remaining field/item pointers separately from entirely unsupervised queries. Candidate and confirmed field-value distributions are reported separately; they do not guarantee clear/ambiguous, DISTRACTOR or dual-target quotas. No success-conditioned sampling, quota-filling SAT frames or automatic training is added.

## Verification and handoff

Affected verification only:

```sh
python -m pytest tests/test_offline_pipeline.py tests/test_offline_review.py tests/test_data_training.py -q
```

The caller supplies the pinned core via the existing test configuration (`EGRS_CORE_ROOT` for these CPU/fake tests). These tests prevent source substitution/split drift, wrong instruction/camera handling, future/history leakage, loader retries/pin relaxation, false human promotion, stale confirmation reuse, and incorrect evidence masks. They do not run actual datasets, processors, weights or VLA/model training/eval. Browser interaction QA was unavailable in the delivery environment: the browser tool refused local file URLs. Static packaging and backend integration were checked, but interactive visual behavior remains a manual review item.

Next: X/controller delivers the increment to original PR #2; external collaborating Codex reviews it, prepares isolated deployment and handles the separately authorized fixed20-file raw transfer. The user separately starts real inventory/extraction, teacher inference, human review, training and evaluation. X's real processing/model/human-annotation/training/evaluation counts in this software delivery remain0; raw transfer status is reported separately.
