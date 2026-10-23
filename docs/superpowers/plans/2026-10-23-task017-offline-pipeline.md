# Task017 Offline Candidate and Review Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Deliver the complete offline source-to-reviewed-training-data workflow requested in task017, without executing real research work.

**Architecture:** Add an `egrs.offline` package with independent inventory, window preparation, fixed offline teacher, candidate orchestration and static HTML review modules. Keep model inputs in existing sensor/context schemas, keep operational metadata/audits alongside them, and call the existing annotation/build/encoding contracts. Preserve the inventory's source-level split through partial annotation.

**Tech Stack:** Python, existing h5py/Pillow/NumPy/Torch interfaces; vanilla offline HTML/CSS/JavaScript, no service, database, remote assets or telemetry.

**Spec:** `collaboration/tasks/017_selector_data_pipeline.md` (main `e062970`), plus accepted implementation `5a77f158229442d9a9ee95ba828b371dfc4c995a`.

## Global Constraints

- Only implementation and targeted synthetic CPU/fake tests. No actual HDF5 data, model weights, real processor, teacher/model forward, rendering, training or eval. Synthetic tests must be identified as fixtures, never human research annotations.
- Fixed catalog: `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`; all 20 approved files and `demo_0..demo_9`, no replacement.
- Preserve `data.attrs.problem_info.language_instruction` exactly; explicit human mapping only when absent. Metadata never enters the model context.
- Source/known-alias grouping with existing `grouped_split`, seed 0, approximately 80/20. Freeze before labeling and never recalculate from the reviewed subset.
- Anchors `floor(i*(T-1)/5)` for `i=0..5`; window frames `[anchor-16, anchor-8, anchor]`, clamp, unique, ascending; deduplicate windows. Equal, nonempty uint8 HWC RGB camera lengths required.
- Query IDs start at 1 within each window; model sees only current/past window snapshots, maximum 6 images, 256 visual tokens/image, total 4096, answer 1024. `commands=[]`; initial memory empty; history is only past legal predictions through existing `EvidenceMemory`.
- Independent offline teacher `Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5`, same processor revision, explicit Qwen2.5 class, bf16, batch1, deterministic generation; one load per invocation, no LoRA, no retries/model fallback. Student 3B config/pin remains unchanged.
- Machine provenance remains weak; failures remain null plus errors. Human confirmation is explicit and field/item-level; no AI-generated signatures. Audit time is observed UI elapsed time, not claimed labor estimates.
- Existing policy/contracts/scoring/actor/trainer are not redesigned. An additive optional fixed split argument to the existing dataset builder is permitted to preserve task017 source grouping, with original behavior as default.
- New output directories only; preserve partial outputs and raw failures. No automatic transitions to the next real stage, downloads, deployment, merge or cleanup of history.

## Review Focus

1. Missing/corrupt episodes, UTF-8/bytes problem_info and camera mismatch: gaps are explicit, no source replacement or shortened streams.
2. Partial review removes whole sources: train/dev memberships and known alias grouping must not move.
3. A malformed candidate inside a window: no fabricated UNKNOWN/history, raw output/error retained, independent later windows proceed.
4. Human edits entity/evidence or imports a previous session: provenance must not confirm unrelated/changed fields or mutate frozen payload/source/split.
5. Installed package/static HTML opened outside repository: template assets and portable images work, canonical training image paths remain unchanged.

## Implementation choices

The detailed task is already authorized. Use a small staged CLI (`python -m egrs.offline`) with `plan`, `inventory`, `registry-candidates`, `registry-review-export`, `registry-review-import`, `prepare`, `candidates`, `review-export`, `review-import`, and `build`. Equivalent descriptive names are acceptable if docs/tests/CLI agree.

Use JSON envelopes with version tags for inventory/source splits/registries/windows/candidate manifests; training samples keep the existing `SAMPLE_KEYS`. Sidecars hold frame indices, orientation, frozen hashes, model/prompt configuration, raw output, calls, errors and human audit. A static plan must not open HDF5 or import models.

If a query fails, keep its null/error and mark later queries in that same window unattempted with the preceding-failure reason. This preserves consecutive original EvidenceMemory semantics without inventing an UNKNOWN update. Continue independent subsequent windows. Explain this in docs and report skipped versus attempted counts separately.

Review export embeds only requested legal images (copied portable image assets) and JSON in HTML so file:// works without fetch/CORS or a server. Form controls edit fields, evidence items and normalized boxes with visible overlays. Registry review has its own mode before extraction. Loading an earlier review validates its immutable manifest identity. Changing an already confirmed value clears affected confirmation; changing entity/evidence invalidates dependent confirmations before re-review.

## Task 1: Complete integrated offline pipeline

This is a single end-to-end deliverable: source split, teacher history, review payload identity and build semantics must agree. Implement the phases below in order, with small commits and one independent whole-deliverable review.

**Files:**
- Create `egrs/offline/__init__.py`, `__main__.py`, `cli.py`, `inventory.py`, `windows.py`, `teacher.py`, `candidates.py`, `review.py`, and `assets/review.html` (split JS/CSS permitted).
- Modify `egrs/data.py` only for additive fixed split support and validation; `pyproject.toml` for CLI/package assets; README for correct branch/software entry points.
- Create `configs/teacher_offline.json`, `docs/offline_pipeline.md`, `tests/test_offline_pipeline.py`, `tests/test_offline_review.py`, `collaboration/responses/017_round1.md`.

**Interfaces:**
- Existing `validate_registry`, `validate_prediction`, `validate_payload`, `build_messages`, `encode_messages`, `load_images`, `EvidenceMemory`, `export_annotations`, `import_annotations`, `grouped_split`, `build_dataset`, `prepare_answer` are the shared authority.
- Inventory produces source rows with stable `source_id`, raw instruction, approved relative file and episode, T, orientation, known aliases, frozen split and gap lists; aliases/instruction maps are explicit optional JSON inputs.
- Registry candidates and confirmed registry maps are keyed by exact instruction identity, not task ID. Unconfirmed registries cannot prepare source samples.
- Prepared windows produce dense chronological query samples plus separate metadata, all unsupervised until candidates/review.
- Teacher exposes reusable registry/predict operations with raw generation and attempted-call audit, and closes once. Fake injection is a test seam; production default is the independent pinned 7B loader.
- Candidate artifacts contain full sample manifests with immutable payloads plus errors/raw output/identity; exported review results retain all originals and a separate audit file.
- Review import validates both the existing annotation contract and frozen operational identity, returns complete records plus audit; build uses frozen splits and writes confirmed train/dev alongside full candidate/unreviewed/gap reports. Exclusion attestations default to unset, require explicit true external assertions, and report basis/unknown ancestry.

- [x] Write and run failing inventory/sampling/split tests using synthetic HDF5 only: numeric selection never uses demo_10, missing/invalid instruction gaps, exact source instruction, mismatched lengths, deterministic clamped/deduped windows, preserved alias splits after partial review. Expected: new module/API missing.
- [x] Implement inventory/prepare/static plan and additive frozen-split builder. Run those targeted tests, expected PASS; commit.
- [x] Write and run failing teacher/candidate tests with a fake model: one load per command, no retries or student config relaxation, attempted-call/raw error audit, all-weak outputs, frozen chronological history, null/error and skipped remainder of failed window. Expected: candidate functions absent/failing.
- [x] Implement pinned independent loader, two-stage registry confirmation and candidate orchestration. Run targeted tests, expected PASS; commit.
- [x] Write and run failing review/import/build tests: no future views, no payload mutation, explicit UNKNOWN versus weak/null, per-field/item confirmation, evidence-index edits consumed by existing final token masks, resume preserves immutable source/split, round-robin queue and optional stratified re-review suggestion. Expected: review functions absent/failing.
- [x] Implement offline HTML form/overlay/export/resume and backend validation; package assets. Run targeted review tests and complete synthetic pipeline tests; commit.
- [x] Provide exact stage-by-stage commands, required files, data/model pins, gap behavior, no false ready/coverage claims and no real runs. Static help/plan must work without optional model/native imports; commit docs.
- [x] Run all affected task017 tests plus `tests/test_data_training.py` in a separate process; record command/output and red/green evidence. No full-repo/multi-platform or real-model tests.
- [x] Generate a small synthetic review package for controller browser verification of fields, bbox edits, export and resume; never label this as real human research review.
- [x] Self-review against every task017 section, commit, report. Independent reviewer then checks the complete incremental diff from `5a77f158`; fix concrete blocking findings with targeted regressions.

## Verification status (2026-10-23)

Implementation and the listed synthetic CPU/fake checks are complete: 59/59 affected tests passed. The internal independent reviewer inspected `5a77f158..ad69afd38a41b6195e92b918b9dfbdb14fef26c0` and returned spec PASS / code-quality PASS with no blocking findings, using code inspection and supplied test evidence; tests were not rerun by that reviewer. External collaborating Codex acceptance remains pending.

- [x] Synthetic prediction and registry review packages generated under `.work/task017-ui/`; no real human annotation identity.
- [x] Installed-wheel static plan/catalog/portable resource checks completed. This wheel predates the final report-only fix and is not the final release artifact.
- [ ] Interactive browser QA: NOT RUN. The browser tool rejected local `file://` URLs; no workaround was attempted. Static inspection and backend tests do not establish visual interaction acceptance.

## Delivery

X/controller delivers incrementally to original PR #2, checks remote/local complete tree identity and preserves an archive. Browser interactive QA remains not run as recorded above. External collaborating Codex reviews the delivery and prepares isolated deployment. No automatic merge or server deployment. The user separately starts each real data/candidate/human-review/training/evaluation stage; all real-stage counts in this implementation remain zero.
