# Task040 train-parent coverage implementation plan

> **For agentic workers:** Use subagent-driven-development or executing-plans; the user explicitly requests direct implementation, so no additional design approval gate. Steps use checkbox tracking.

**Goal:** Add only new train-parent ten and pair supervision from three tasks' demo_20..39, retaining the exact accepted039 reference/dev view and the original C1 algorithm.

**Architecture:** A separate `egrs.coverage040` contract composes039 recording helpers and the unchanged038 model/trainer/evaluator. The delta owns normal recordings only for generation/pairs; main rows copy old039 rows then append new ten. A single production command plans, generates and builds indices with one live hash context, never training/evaluating implicitly.

**Tech Stack:** Existing Python, NumPy/h5py, PyTorch CPU fake tests. No dependency upgrades or real workloads.

**Spec:** `collaboration/tasks/040_parent_coverage_augmentation.md` at main3d92223; accepted code PR14@113ded21434a06e2cdc156e5d6283a11c3f15488. Local docs merge fef4a95, not a GitHub PR merge.

## Global constraints

- Exactly stove/mug_pudding/two_pots demo_20..39 candidates; canonical source IDs preserve official relative HDF and demo. Original180 parents136train/44dev never move. Seed7 known alias components inherit old anchors; cross-split conflicts reject new candidates. Only new train representatives generate.
- Original039305ten (224/81),105fresh (78/27),180raw (136/44),305pairs (224/81) remain unchanged. Newnormal is pair-only, newten is train-only; dev stable source/observation/pair keys and order must be exactly equal, not just counts.
- Reuse039 physical_release_clearance_v3/originalV2 qualification, five real release observations,40 added/520 total steps, two-pot initial freejoint transform only. Durable attempts at most60normal/360ten; failure/interruption consumed, no refund/retry. No change to original035/036/038/039 strict defaults.
- One new C1 from originalSOG10,1000updates/seed7,12ten+4fresh+4raw plus1pair/twoends. Original model/loss/weights,9024reference/24560student, fixed terminal1000, new180eval, score/state/video/dualbridge unchanged. No S/C0/seed/baseline runs.
- No new qualified train-parent ten => refuse before model load; no per-task minimum/pair minimum or extra budget. No deployment/SSH/real generation/model/simulation/labels/index/training/eval. Preserve all old files, no automaticmerge or deletion.

## Review focus

- Oldtrain/dev alias conflict must reject only new candidates without moving old sources; new duplicate representative must not spend twice.
- Newnormal must remain accessible to get_pair with its actual outgoing action while absent from every main sampler row.
- Olddev selected stable keys/order and fresh/raw sources/rows/count labels must match despite a new shared outeridentity.
- Validten with missing pair remains BC data; oldtrain pairs allow training, zero genuinely newtrain10 cannot load a model.
- Configuration env expansion rejects unresolved placeholders; metadata-only entry does not launch a native worker. Hash context spans export/index and both train/dev readers; stat changes reject.

## Task1 — independent040 source planning and generation

Files: create `egrs/coverage040/plan.py`, `generation.py`, source/generation CPU tests. Do not edit039 production modules.

Interfaces: `build_plan(config_path, context=None)` returns config, parents(old180+newcandidates), candidates, sources(newtrain representatives), execution_config, data_root, identity and source selection/binding coverage. Configuration format `task040-parent-coverage-config-v1` with `generation_config`, `old_task_control_index`; derive and bind old retention/merged roots from accepted039 manifest rather than hand-copying fields.

`generate(config_path, out, *, source_generator=None, context=None, plan=None)` returns `export` path, population/counts/sourceerrors and spent budget. Export retains original035 sample schema plus `generation_context.coverage040` binding complete fixed candidate plan/train-only/newnormal-role/ledger identity. Every attempt sidecar/recipe/lineage binds040 context while retaining039 algorithm/V2 provenance. No new control algorithm.

- [x] Write red tests for exactrange/seed7/anchors/alias/conflict/dev exclusion/unresolvedpaths and init-before-spent ledger/newoutput refusal.
- [x] Run red; implement minimal explicit planner and orchestration reusing039 helpers/native worker; run focused green and039 generation regressions only if affected.
- [x] Report code/test commands/results and boundary concerns to root; no real jobs or branch mutations.

## Task2 — explicit delta index and pair-only normal dataset

Files: create `egrs/coverage040/data.py`, `index.py`, related data CPU tests. New modules may reuse unchanged039readers/hash and038 label/pair helpers; do not relax old defaults.

Interfaces: `build_indices(old_task_control_index, delta_export, out, context=None)` returns retention/task_control paths and corresponding reports. `CoverageTaskControlDataset(index_dir, split='train', context=None)` matches038 dataset including get_pair/normalization/report/data_kind; report.coverage040.new_qualified_train10 is actual int. New outeridentity binds old frozen inputs, validated delta and exact reused/dev keys; old035schema delta context carries040plan/train-only/range. Any further interface change is coordinated with root.

- [x] Red tests: oldfresh/raw/dev exactrecords and deterministic selections unchanged; newnormal only pair_sources; qualifiednewten survives missingpair; source/mask/provenance/root/stat changes reject.
- [x] Implement reference-only appended rows/labels/pairs preserving old objects verbatim; strict039actualcounts/identity anchors (private synthetic fixture overrides only in tests); validate new recorded pair using original1e-8/layout/active semantics.
- [x] Run focused green; report API/commands/results. No real data/index production.

## Task3 — root production/C1/CLI integration and handoff

Files: create coverage040 `__init__.py`, `__main__.py`, `pipeline.py`, `training.py`;040 config examples; entry/integration tests; docs/task040_usage.md, responses/040_round1.md, stage summary and currentSTATUS/README pointer.

- [x] Red tests: one command plan/generate/buildindices shares context, refuses overlapping/existingoutput; C1only/no-newdata before model; eval delegates original038 C1.
- [x] Implement minimal wrappers, config env expansion delegated planner, separate user-started C1train/eval. Preserve original038 preset and compact logging.
- [x] Synthetic NumPy-only recording worker -> delta/index -> original038 tiny C1 (22student/8reference perupdate), save/resume/reload and fakeeval contracts; verify newpairs are actually consumed and normal never a main row.
- [x] Root-run only new/affected CPU/fake groups in separate file/model processes for known NumPyMKL/Torch OpenMP host issue; retain actual JUnit/results including skips/failures.
- [x] One independent whole040diff review, fix explicit defects with covering regressions, one scoped recheck. No platform/fullsuite/MVP gates.
- [ ] Commit implementation then concise response including implementationSHA and complete conda/python/nohup/progress templates. NewPR to main explicitly states unmerged PR14dependency. Verify remote exacthead/tree/keyblobs and preserve local source/docs/CPUevidence archive with SHAmanifest. No auto-merge, cleanup or server operations.
