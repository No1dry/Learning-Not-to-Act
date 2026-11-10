# Task035 implementation plan and execution ledger

Spec: `collaboration/tasks/035_mask10_robot_rewind_augmentation.md` and its linked approved plan.
Base: accepted030 `5bb32713`, plus main documents `cb026b3` merged as `58a05f0`.
Goal: deliver an executable bounded native trajectory generator, 7:3 mixed training and same-adapter 10/00 evaluation. Real jobs are never executed in this implementation turn.

Architecture: new `egrs.trajectory_augmentation` owns the generated-data schema and orchestration. Reuse030 model/LoRA/normalization/native components and fixed benchmark scoring. Only narrow extension hooks may change030 shared files; old configurations keep their meaning.
Tech: existing Python/NumPy/h5py/PyTorch and fixed native dependency, without a new planning framework.

## Global constraints

- Nine fixed tasks, natural first N<=20 original demos, at most180 parent sources. Parent groups split before variants.
- Each parent one normal replay; three predeclared robot starts, up to two bridge attempts each, H520 per attempt. No real generation, model or native test.
- Actual executed actions are projected before stepping using original SOG10 stats/gripper/env limits. Original controller target poses are recorded; B is retargeted, never pasted.
- Initial robot-only mutation, no mid-trajectory state or controller-goal jump. Nonrobot positions and velocities preserved.
- T+1 fresh observations/states and T actions. Only successful qualified trajectories supervise; all attempt failures remain in denominator/audit.
- No test-source/model data, no policy truth input, no change to benchmark physics or source population, no auto merge.

## Task1: native generator and control (native implementer)

Files: new `egrs/trajectory_augmentation/control.py`, `native.py`, `generation.py`; `tests/test_trajectory_generation.py`, `test_trajectory_control.py`.
Interfaces: `generation.generate_source(source, config, data_root, output_dir) -> dict` runs one source via actual isolated native worker. Return `{attempts:[metadata], source_id, error, gaps, ...}`; persist each attempt directory before returning. Metadata uses `source_id`(unique attempt), `parent_demo_id`, `task_key`, `split`, `domain` (`10` or `normal`), `provenance`, `variant`, `attempt`, `status`, `qualified`, `failure_reason`, `file` (success HDF relative to output_dir), `episode` (`data/demo_0`), `length`(T), `mapping`(030 mapping, offsets0), qualification/lineage/audit paths. All attempts including rejects persist audit; one fixed representative video per task handled by caller request `save_video`.
HDF success contract: original mapped two image datasets and ordered proprio datasets lengthT+1, `actions` lengthT, `states` lengthT+1. Save projected actual env actions; optional normalized actions and perstep original controller targets/audit. Use existing original mapping normalization exactly once at dataset read.
`source` is a validated035 seed record based on030 compound source fields plus preassigned parent/split. `config` includes explicit `native_backend` (030 backend config), `benchmark_root`, `stats_path`, `stats_sha256`, `unnorm_key`, `recipe`, per-source/task binding and `save_video`. Never infer goal binding from filename. New code may depend on030 public/pinned helpers, never modify frozen dependencies.
- [x] Write failing fake-native tests for projection/roundtrip, controller/world poses, robot-only components, real-step bridge, qualification and budget/failure accounting.
- [x] Implement native path, fake-inject only at environment boundary, verify synthetic tests.
- [x] Report API details and actual results; independent narrow review follows.

## Task2: source plan, data indexing and orchestration (root)

Files: new package init, `data.py`, `cli.py`, seed/generation config examples, data/generation docs, tests.
Interfaces: `validate_seeds(manifest) -> list[source]`, `build_plan(config_path) -> dict` is metadata-only. `generate(config_path, output, source_generator=None)` invokes concrete generate_source by default, persists plan/attempts/report, calls generated export. `GeneratedTrajectoryDataset(export_dir, split=None, domains=None)` exposes rows, sources, report, `validate_normalization(...)`, __len__/__getitem__ exact030 whitelist. Rows include domain/task_key/parent_demo_id/source_id/variant/start/stop/action_mask/split; source_id identifies an attempt, source file identity sealed. Files sources.json/windows.jsonl/report.json maintain familiar030 export identity hooks.
- [x] Test natural source selection, duplicate-group split, testdata exclusions, attempted/qualified counts, T+1 chunks/masks, hidden input separation, normalization and no fake RAW fallback.
- [x] Implement CLI plan/generate/export using fixed native source function, actual bounded attempt denominator and immutable source bindings.
- [x] Run fake end-to-end integration and document full ordinary commands.

## Task3: mixed training and recipe identity (training implementer)

Files: new `egrs/trajectory_augmentation/training.py`, minimal hooks in030 training.py/oft.py/adapter_identity.py only if necessary, config and tests.
Recipe/group: `robot_rewind_mix`. Data kind `task035-generated-trajectories-v1`. Dataset interface above. 12 samples10 +4 normal, task->parent->variant->window balanced. Perdomain masked scalarL1 then0.7/0.3; no pool fallback. Train/dev eachdomain required before model load. Dev bounded deterministic<=256/domain, periodic250, final1000checkpoint is fixed selected checkpoint. Reuse030 load/inject/predict/save/resume, avoid duplicating model/adapter machinery. Identity schema extension must distinguish035 data/recipe and final update from030 identities; coordinate eval consumer.
- [x] Write gradient/padding/pools/sampler/devcap/resume identity CPU tests.
- [x] Implement complete CLI using unchanged030 base components; fake training loop as needed, no real model.
- [x] Report integration API and tests.

## Task4: same-adapter dual conditions (evaluation implementer)

Files: new `egrs/trajectory_augmentation/evaluation.py`, configs, tests; narrow optional hooks in030 evaluation.py if necessary. Do not edit training-owned files.
Use fixed core d8541ef4/readers/00 protocol/scoring and03410 reports. One explicit adapter path/identity shared by conditions; fixed10/00 each90. group robot_rewind_mix, finalupdate1000 from task3. Expose plan/run/report commands; truth never reaches adapter policy. Full video/query/action/raw preservation. Baselines10=22/90,00=78/90 separate endpoints/metrics; no legacy mask10 qualification on normal00.
- [x] Test exact source population/protocol identity, sameadapter bothconditions, distinct score summaries and absence of condition policy input.
- [x] Implement concrete endpoint/readers/report paths and configs, fake integration.
- [x] Report tests and interface coordination.

## Cross-task review focus / rulings

| Tasks | Interface/risk | Ruling |
|---|---|---|
|1/2|Generated provenance/actions/obs length|Use agreed HDF T+1/T and source metadata above; never ordinary_expert_demo for output.|
|2/3|Dataset metadata and split|Domains10/normal, parent split immutable, item unchanged030.|
|3/4|Adapter recipe/update identity|Training owns shared identity additions; eval requests exact matching035 finalupdate.|
|1/4|Core physics/protocol imports|Reuse fixed dependency under isolated native workers or controlled module activation; no scorer copy.|
|1 internally|normal initially true goals|Normal qualification ignores initial-goal preservation, retains actual initial facts.|
|2 internally|Partial task coverage|Report missing tasks and parents; require bothtrain/devdomains only for training.|
|3 internally|Padding changes7:3|Normalize eachdomain across its effectivebatch validscalars beforeweight.|
|4 internally|00 baseline differs10|Use existing00endpoint/native score, separate denominators/deltas.|

Progress: implementation complete; independent scoped review has no remaining blocking findings. Root final verification: generation/data 38 passed, training plus impacted030 25 passed, evaluation plus impacted030 24 passed, all in separate processes (87/87, zero failures/errors/skips). CLI help and git diff --check passed. Combined-process tests aborted from the independently reproduced local NumPy/PyTorch duplicate OpenMP runtime; that failed run is retained and not counted as passing. See collaboration/responses/035_round1.md for exact commands, dependencies, and delivery. Real generation, training, and evaluation remain 0%; no real operation authorized.
