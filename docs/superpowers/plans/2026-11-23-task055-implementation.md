# Task055 implementation plan

> **For agentic workers:** Use subagent-driven implementation for the independent catalogue/native-builder boundaries and targeted CPU/fake verification. The user has explicitly requested direct implementation; this is an execution record, not another design-approval gate.

**Goal:** Deliver an isolated three-task, 50 fixed canonical indices per task, precompleted-only construction package, with honest evidence and no real execution in this turn.

**Architecture:** `egrs.composition055` registers only its three new combinations. Its BDDL derivatives preserve the canonical Scene2 scene/assets, changing only language, objects of interest and two goal predicates. The native builder calls pinned core geometry, restoration, observation, physical validation and release primitives; the orchestration freezes provenance, spends each source once, preserves failures and exports only precompleted states. Existing training/banks/scoring modules remain byte-identical.

**Tech stack:** Python, existing pinned eval core, NumPy and existing native LIBERO runtime only at explicit build time. Tests use CPU doubles at the native boundary.

**Spec:** `collaboration/tasks/055_compositional_generalization_benchmark.md` at `6e650887ba43b7fff81c24e8491442a8337de252`.

## Global constraints

- Exactly soup+butter, tomato+cream-cheese, tomato+butter, in that order; each source index0..49. Only first object precompleted, exact initial mask `[true,false]`.
- No normal-state bank, pairing requirement, new training/dev/sidecar rows, model evaluation, old450 modification, SSH, deployment or real simulation this turn.
- Fixed canonical official Scene2 basket task0 assets: BDDL SHA `2e661058917f683a25bce480015197f0a2c1911bcbc2b9dd9d947199069c9618`, initial-state asset SHA `1899fe54c51e24a41d5f9e32254730d6777f4894ab68e0e873f1fa7ae2062030`; source array50×123, float64. No replacement/reordering by outcome.
- Original physical thresholds,80 settling/150 verification steps, release evidence and confirmation window are delegated to fixed core; no zeroing measured velocities or fabricated readiness. Bounded original candidate generation is construction within one fixed source, not replacement of a failed source.
- Fresh output, durable attempts, all failures retained. Source is ready only with full restored state/observation/physical/release/provenance evidence.

## Review focus

- Cold CLI must activate pinned dependencies before importing core-dependent code; help/config parsing must not import native ML/simulation.
- Canonical ancestry must bind full asset SHA and selected index, not just rename a prior task or accept a new file with a convenient vector length.
- Native predicate and release measurement must target the exact two designated objects, never a third scene object.
- A-only transplant must retain every non-A state component and the legitimate robot start; stale observations, unknown release or partial audit are failure.
- Incomplete/duplicate/out-of-order population, corrupted artifacts, interrupted attempts and output/input overlap cannot become a complete150 bank.

## 1. Catalogue and task BDDL derivatives

Files: `egrs/composition055/catalog.py`, `tests/test_composition055_catalog.py`.

Interfaces: `get_task(task_id)` returns a detached profile with `task_id`, `name`, `instruction`, `completed_object`, `remaining_object`, `goals`; `expected()` returns the fixed150 ordered identities; `render_bddl(canonical_text,task_id)` edits only three declared BDDL forms and rejects any wrong canonical file/scene/object inventory. Constants expose canonical hashes and task order.

- [x] Write/run failing tests for exact task/goal/role identity, Scene2 preservation, unknown/third-object rejection and deterministic150 population.
- [x] Implement pure catalogue and BDDL generation, no official registration/global mutation.
- [x] Run only the catalogue CPU tests; report actual failures and final command.

## 2. Native precompleted-only builder and validation

Files: `egrs/composition055/native.py`, `tests/test_composition055_native.py`.

Interface: `build_source(config, row, output_dir, checkpoint)` produces one manifest with state, original typed observation, physical/release evidence and canonical ancestry; `checkpoint(event)` persists source-phase accounting before native work. It accepts no model object or ordinary-state mode. Root orchestration validates the exported contract and hashes.

- [x] Identify exact existing geometry/restore/validation/release APIs and pin dependency identity; record topology/ancestry seam.
- [x] Write failing CPU tests against actual core primitives with small native doubles for accepted and rejected masks, whitelist, stability, penetration, release, stale observation and closing failure.
- [x] Implement A-only candidate settlement/transplant using existing primitives, preserve non-A/robot components, save failed attempts, never export ordinary states.
- [x] Verify restoration/render evidence and original confirmation window; run affected native tests only.

## 3. Strict configuration, build orchestration, bank reader and CLI

Files: `egrs/composition055/{__init__,__main__,contracts,preparation}.py`, `configs/composition055/build.example.json`, `tests/test_composition055_preparation.py`.

Interfaces: `load_config(path)` performs pure strict parsing; `prepare(config_path,output)` activates fixed core then binds canonical assets before any build, processes exactly150 new ordered rows once, returns durable per-task ready/failed/pending counts; `read_bank(path)` verifies stored provenance, population and artifact hashes before reporting readiness.

- [x] Write/run failing fake150 tests, including interrupted/failed source, duplicate/out-of-range/missing IDs, tampering, source/output overlap and fresh-process import.
- [x] Implement no-overwrite/no-retry orchestration with no training/evaluation/normal CLI; bind code/core/config and each selected canonical index.
- [x] Integrate actual native backend and generated BDDL, without changing old registries/modules or450 bank.
- [x] Run targeted integrated fake path and byte-identity assertions for existing production code.

## 4. Delivery

- [x] Focused implementation review against the work order; resolve concrete integration defects only.
- [x] Final affected CPU/fake commands and honest JUnit/summary evidence; no complete-suite or real-MVP gate.
- [x] `docs/task055_usage.md`, `collaboration/responses/055_round1.md`, stage/STATUS entry, configuration and limitations.
- [ ] New PR against latest accepted code dependency, no merge; verify exact remote head/files, retain local source/evidence backup.

The user has approved the scope and direct implementation. Skill suggestions to reconfirm design, broaden testing or remove old workspaces do not apply to this explicit task. Original evidence and all old worktrees stay untouched.
