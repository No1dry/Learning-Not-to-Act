# Task038 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. The user has authorized direct implementation of the supplied specification; no further design approval round is required.

**Goal:** Implement 037-v2 C0/C1 indexing, training/resume and shared-path adapter evaluation.

**Architecture:** New `egrs/task_control` package over accepted036. Preserve legacy035/036 contracts; reuse their data, reference conventions, strict environment dispatch and verified scoring. All new policy behavior uses one shared feature/decode path.

**Tech Stack:** Python, PyTorch; JSON/HDF source contracts; pytest CPU synthetic policies/files only.

**Spec:** [Task038](../../../collaboration/tasks/038_task_control_factorization.md), [037-v2](../../research/2026-11-06_task037_v2_task_control_factorization.md).

## Global Constraints

- Base accepted036 `205d6530e1ba389f74166a2e9520a3db7ae0edbf`; merge latest main documentation without merging GitHub PRs. STATUS conflict uses current main authoritative history.
- No real model/teacher, real image processing, labeling/index production, simulation, training/evaluation, server operations or deployment. No deletion or automatic merge.
- Inputs only two images, original instruction and proprio8. Output normalized8x7 through original head; no GT/pair/count/time routing.
- Same C0/C1 network/data/order, seed7, fixed1000, original three pools plus one pair per update. Each arm reference<=9024 and student<=24560. Real budgets remain unapproved.
- Preserve035/036 data, artifacts, scoring, identities and adapters. New schema and separate output paths.

## Review Focus

- Actual inserted multimodal token positions and instruction span; reject action/pad/GT in z.
- Existing truth must map active predicates, not official order; compare recorded states using actual rewind layout.
- Evaluation must execute the same learned modules; reference must bypass all additions and restore mode flags.
- Swap retains receiving H/proprio/targets/masks, gradients reach both z encodings, and no extra backbone call.
- All module tensors, sampler/RNG/budget states survive strict checkpoint and resume; reject changed arm/index or old result inheritance.

## Task 1: shared model, prediction and adapter

Files: `task_control/{model,oft,adapter,policy}.py`, CPU model/adapter tests.

- [ ] Write failing synthetic layout/gradient/train-eval equivalence and strict checkpoint tests; run red.
- [ ] Implement `TaskControlModules(hidden_dim)`; `oft.install(policy)`, `prediction(policy,item)` returning actions/h/z/proprio/count_logits; `decode(policy,encoded,z=None)` without a backbone call.
- [ ] Implement strict new adapter identity and whole-module save/load; policy uses shared prediction and unchanged original action conversion.
- [ ] Run scoped CPU tests and independently review the final path.

## Task 2: source-bound index and reader

Files: `task_control/{index,data}.py`, synthetic JSON/HDF tests.

- [ ] Write red tests for active-goal mapping, T+1/T, masks, actual robot layout/state equality, cross-parent/split rejection and confirmation exclusion.
- [ ] Implement `build_index(generated_export,retention_index,output_dir)` with labels/pairs/report/sources identities, no observation pixels or environment imports.
- [ ] Implement `TaskControlDataset(index_dir,split)` with rows/pairs/identity/report, main items and `get_pair(i)` returning each endpoint's actual action chunk.
- [ ] Report unavailable pairs without changing BC sources; run scoped tests.

## Task 3: training/reference/resume

Files: `task_control/{training,reference,checkpoint,sampling}.py`, fixed config and CPU fake tests.

- [ ] Write red tests for formulas, both gradients, same C0/C1 order, full module reference bypass and durable resume budgets.
- [ ] Implement public fixed `run(args)` and private `_run_loaded` tiny-loop seam; reuse036 pool normalization, count class means, self/swap/align objectives.
- [ ] Preserve optimizer/scheduler/RNG/main+pair sampler/reference+student budget and arm/data binding; log bounded dev diagnostics and ETA/memory without SR claims.
- [ ] Run scoped tests for bounded dev and uninterrupted-versus-resumed sequence.

## Task 4: evaluation, CLI and handoff

Files: `task_control/{evaluation,__init__,__main__}.py`, config templates, README, `responses/038_round1.md`, scoped tests.

- [ ] Write red fake tests for two180 plans, wrong-arm/final checkpoint rejection, method factory, scoring and old-run protection.
- [ ] Reuse036 runner/readers through explicit internal contract parameters, retaining036 defaults and strict public validation. No global monkeypatch dispatch in production.
- [ ] Add index/train/eval CLI and placeholder conda/python commands marked pending authorization.
- [ ] Run only affected CPU/fake suite; review full change, fix material findings, document actual results and unresolved limitations once.
- [ ] Commit/push new branch and PR, verify exact remote document/tensors contracts; no merge.
