# Task039 Implementation Plan

> **For agentic workers:** Use subagent-driven-development and CPU/fake TDD. Direct implementation of the supplied039 specification and a new PR are authorized; real jobs are not.

**Goal:** Recover three-task training coverage by physical teacher closure and initial symmetric-pot permutation, then bind actual new data for the unchanged038 algorithm.

**Architecture:** New `egrs/coverage039` package over accepted038. Teacher policy remainsV2, while the action algorithm and initial transformation have separate versioned provenance. Reuse old296 qualified trajectories by bound references, with explicit two-root artifact restrictions and one-process hash/stat context. New train CLI selects the new dataset contract; model, losses, sampling and eval remain038.

**Tech Stack:** Python, NumPy/HDF/JSON contracts, PyTorch tiny CPU tests; no real environment/model calls.

**Spec:** [039 task](../../../collaboration/tasks/039_teacher_release_and_coverage_recovery.md), [approved plan](../../research/2026-11-07_task039_coverage_recovery_plan.md).

## Constraints

- Base038 `5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`; merge main `d919233` docs, keep all old results/failures/raw/checkpoints and PR dependencies. STATUS conflict uses authoritative current main history.
- No native generation, real labels/index production, model/teacher, image features, real training/eval, server operations, MVP, merge or deletion.
- <=60 ordinary and <=360 ten attempts, initialization/interruption counted before actions, no refund/hidden retries; <=40 closure steps and520 total.
- Two pots only: actual freejoint qpos7/qvel6 once before first fresh observation; unchanged A/B/official goals/K/language/other coordinates. Admission remains originalV2.
- All closure transitions in T/T+1, no audit-only release supervision; retain invalid-prefix evidence.
- Same038 network/optimizer/losses/22 observations/pools/pair sampler; two new1000 runs,9024 reference/24560 student each,360 total eval. User alone starts approved real jobs.

## Tasks and checks

1. **Teacher and permutation** (`teacher.py`, `permutation.py`): test unknown/held release,5 true frames, anchor/open/retreat bounds, A/K/events, recording and unusual actual freejoint addresses. Implement real-action closure helper and immutable initial transform; no source-file or old-policy edits.
2. **Generation and budget** (`plan.py`, `recipe.py`, `generation.py`, `native.py`): test original first20/source split, counted failed init/3x2 slots, no retry, new workers/venv symlink, actual canonical10 and recorded transitions. Reuse strict original NativeSession/Attempt with new scoped subclass and per-source provenance.
3. **Bound merge/index and I/O** (`io.py`, `merge.py`, `index.py`, `data.py`): test single SHA per canonical stable file, changed stat rejection, progress; old221/75 byte/reference reuse, root escapes, actual new counts and unchanged180 raw/split; build dynamic039 retention plus038-compatible labels/pairs. Only explicit internal contracts parameterize038 index; old defaults retain strict checks.
4. **Pipeline, train adapter, CLI and docs** (root): test one generate→merge→indices sequence with no auto training, actual new-index consumption, zero new train10 guard before loading a model, compact training logs and same tiny checkpoint/eval contracts. Add complete commands and one-page039 reply.
5. **Final gate:** one independent concentrated code review; resolve material findings, run affected CPU/fake suite, commit code and evidence, publish new PR and verify exact remote HEAD/blobs; no merge/cleanup.

## Shared interfaces

- `teacher.finish_attempt(attempt)`; `permutation.prepare_initial(session,source)` and `validate_initial(frame,source,evidence)`.
- `plan.build_plan(config_path,context=None)`; `generation.generate(config_path,out,source_generator=None,context=None)` returns new-only export path/report.
- `HashContext.sha256/verify`, `Progress.update/tick/finish` with <=30sec intervals. One preparation context spans generation metadata/export, merge and both indices.
- `merge.merge_exports(old003,new039,out,context=None)`; `index.build_indices(merged,old_retention,out,context=None)` returns retention/task_control paths and reports.
- `CoverageTaskControlDataset(index_dir,split,context=None)` mirrors038 and reports actual `coverage039.new_qualified_train10`.
- New training wrapper passes an explicit dataset factory and compact logging into038; original defaults and model/adapter schema remain unchanged.
