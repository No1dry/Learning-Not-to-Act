# Task023 bounded alignment diagnostics implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the user-launched two-source diagnostic requested by task023, without changing annotation decisions or starting real work.

**Architecture:** A separate manifest-consuming controller launches one bounded diagnostic worker per fixed source. It reuses NativeAdapter construction, restore/render/original-image/foreground/native-atom helpers, but never calls align(), frame(), label_sim(), export_sim(), or model code. Reuse the existing locked subprocess transport through one closed diagnostic mode, with separate request/result formats and no label-frame events.

**Tech Stack:** Existing Python, NumPy, Pillow, immutable JSON/JSONL sidecars and isolated worker; fixed installed c6 native stack remains unchanged.

**Spec:** `collaboration/tasks/023_bounded_alignment_diagnostics.md`; evidence: `collaboration/tasks/023_alignment_evidence.json`.

## Global Constraints

- Exactly `libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5#demo_0` frames `[0,66,129]` and `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5#demo_0` frames `[0,72,139]`, both original train sources.
- Rules exactly `same_state`, `next_state`, `replay_action`; cameras exactly `agentview`, `wrist`. No source/frame/rule/orientation search or automatic replacements.
- At most 18 candidate restores, 6 existing actions, 36 image comparisons and 72 direct RGB/segmentation renders. Initialization/restore/refresh internal renders are separately identified, bounded by the unchanged per-source timeout and reset/substep limits.
- Use original request indices and measured orientation. No next-state clamp, settle/hold, new action/episode/view, VLA/teacher, real-data test run, threshold change, label/answer, export, split change or follow-on job.
- Preserve metadata/BDDL/assets/module/version/core locks, source and frozen image equality, original inputs/results/165 annotations, all denominators and original 160/40 split.
- Real restoration/rendering is user-owned. X only implements and runs affected CPU/synthetic/fake tests. No full-suite/XML/multiplatform or new GPU prerequisite.
- Old manifest/code identity remains historical, separate from the current diagnostic source identity. Input ready=false is valid; no export prerequisite. New output only; no original artifact replacement.

## Review Focus

1. Old manifest differs from current diagnostic code: retain the old identity and prove current worker bytes separately, never rewrite history or call export validation.
2. One selected PNG/request has conflicting frame/camera/split/config: reject before native work; unrelated PNGs are never opened or rehashed.
3. Runtime state codec omits act or cannot round-trip: record explicit absent/unsupported evidence, never guessed slices or false zero agreement.
4. Render/native/timeout failure midway: retain completed PNG/measurement/events and honest partial status; no retries or success receipt for missing work.
5. Native predicate exception or inadequate foreground: retain unknown/error with null unavailable metrics; no false/zero substitute, candidate choice or labels.

### Task 1: Implement the complete bounded diagnostic seam

**Files:**
- Create `egrs/offline/sim_diagnostics.py`: fixed cases/budget, sealed historical-input binding, orchestration and diagnostic manifest.
- Create `egrs/offline/sim_diagnostic_worker.py`: bounded candidate loop, state/RGB measurements, labeled PNG sidecars, worker protocol.
- Modify `egrs/offline/cli.py`: explicit `diagnose-alignment --manifest ... --output ...` command only.
- Modify `egrs/offline/sim_worker.py` and `egrs/offline/sim_bootstrap.py` narrowly: closed diagnostic mode using the same byte lock, bounded JSONL/timeout and process cleanup; default annotation behavior unchanged.
- Create `tests/test_sim_diagnostics.py`; extend only affected transport/bootstrap/CLI tests if needed.
- Create `docs/alignment_diagnostics.md`; link from `docs/offline_sim_supervision.md`.
- Do not modify core/native alignment decisions, goals, label builders, training/eval or old research results. Parent writes public response/status after code review.

**Interfaces:**
- `diagnose_alignment(manifest_path, output, *, worker_runner=None) -> dict` in sim_diagnostics; accepts the completed old annotation manifest without comparing its code to current code.
- `validate_diagnostic_request(request) -> dict` and `process_diagnostic_source(request, *, adapter_factory=None, emit=None) -> dict` in sim_diagnostic_worker. Request wraps the unchanged selected source request plus fixed case/probes, old orientation/bindings, output and old/current identities. Distinct versioned diagnostic formats; records only operational sidecars.
- `run_isolated(..., mode='annotation')` adds only a closed `alignment_diagnostic` option, no configurable import/factory. Bootstrap whitelists this mode after checking current source identity. Diagnostic transport rejects label-frame events and validates diagnostic result binding. Annotation callers/tests retain defaults.

- [ ] **Step 1: Add meaningful failing tests.** Synthetic sealed completed manifest includes the exact two source identifiers/probes plus an unrelated nonexistent PNG; ready=false and old code differs from current. Assert only selected bindings are consumed, exact candidate operations/budgets and original byte hashes stay unchanged. Assert CLI dispatches the diagnostic once and forbidden label/export/train entrypoints are not called. Parametrize changed source/frame/camera/split/config/file hashes, missing next state, non-original probe/orientation, reused output and output inside input tree.
- [ ] **Step 2: Verify RED.** Run `python -m pytest tests/test_sim_diagnostics.py -q --basetemp .work/task023/red` before implementation and record the specific missing-behavior failures (not fixture typos). Store concise failure evidence, not repeated full tracebacks in the report.
- [ ] **Step 3: Implement historical-input loading and controller.** Verify manifest seal and consumed artifact hashes (inventory, registries, backend config, requests, image bindings and relevant audit text), fixed input relationships, selected sources train membership, exact old probes/orientation and original image descriptors. Reuse `_backend`, `validate_request`, mapping checks and selected PNG hashes; do not call `_inputs` or export_sim, or scan all images/HDF. Production input is pinned to task023 evidence manifest/code identity and fixed c6 reference; explicitly synthetic fixtures remain distinct and marked. Keep old evidence separate from current code identity. Create a fresh outside-input output tree with journals/progress before worker launch. Validate streamed binding/order/counts and final status, journal failures, seal output indexes/hashes, never emit annotation samples.
- [ ] **Step 4: Implement the diagnostic worker and pure measurements.** Use NativeAdapter construction unchanged. Validate request scope before construction; loop frame then three fixed rules, one `_restore` each, keeping each next/replay state snapshot for comparison. Call `_original` for original PNG↔HDF equality, `_render` once per camera (RGB+segmentation), `_foreground`, and existing `evaluate_atoms`. Capture each step before further work; emit partial/error and release owned resources on failure. Never call align(), _prove_equivalence(), frame(), depth, or successor stages. Count attempts conservatively and stop on a failed restore/unsafe source operation, without expanding/retrying the plan.
- [ ] **Step 5: Implement measurement details and PNG artifacts.** Original and oriented candidate RGB, unscaled absolute RGB difference (x1 explicitly), binary foreground mask, and a simple labeled comparison panel per source/frame/rule/camera. Record normalized whole/foreground/background MAE, pixel counts, per-channel signed bias and original max metric with its existing visibility minimum. Empty/insufficient regions have explicit null/unavailable reason, not zero or a replacement acceptance metric. Preserve original and rendered hashes, identity/orientation, native goal atom bool/exception independently; never choose a rule from truths.
- [ ] **Step 6: Implement API-backed state grouping.** Use `type(sim.get_state()).from_flattened(source_next, sim)` where provided and validate exact flatten round-trip/length before reading named time/qpos/qvel/act. Snapshot actual next/replay named fields via the same API. Preserve original full source-next↔replay max and state hashes, plus structured per-group errors and actual-next↔replay comparison with origins clearly labeled. Local reference robosuite codec exposes time/qpos/qvel and asserts model.na==0; absent act must be explicit, not fabricated. Unsupported layouts/fields are honest unavailable diagnostics, not guessed partitions. Record runtime state class/module identity plus existing XML/asset/camera/version/module inspection.
- [ ] **Step 7: Cover the failure surfaces with focused fakes.** Numerically verify RGB decomposition against hand-computed arrays, orientation of RGB and mask, zero-support behavior, named state codec with nontrivial dimensions/act presence/absence and failed round-trip, native exception remains unknown, exact restore/action/render counts, final-next rejection, interrupted worker and close failure retaining artifacts. Verify locked bootstrap uses current code despite old source-code identity and stale module paths; malformed diagnostic events cannot become success. Exercise existing annotation transport where changed, without a full-suite gate.
- [ ] **Step 8: GREEN and guide.** Run `python -m pytest tests/test_sim_diagnostics.py -q -rs --basetemp .work/task023/final` plus precisely selected existing transport/bootstrap/CLI tests affected by changes; run git diff --check. Document one explicit command, fixed cases, timeout/budgets, output indexes/state units/errors, identity separation and no empirical claims. No real HDF/image/native/model calls. Commit code/tests/docs and provide exact commands/results/limitations in report.

## Delivery

Parent independently reviews the scoped implementation, publishes to existing PR #2 and verifies the full remote tree. Then `collaboration/responses/023_round1.md` records actual remote implementation SHA, invocation, budget, actual test evidence and remaining empirical uncertainty; STATUS is append-only and main changes are retained. Final handoff belongs to Codex review/deployment/command preparation, then user launches the two-source diagnostic.
