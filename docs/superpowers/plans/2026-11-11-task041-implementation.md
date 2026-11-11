# Task041 old10 retention implementation plan

> **For agentic workers:** Use subagent-driven-development or executing-plans. User explicitly requests direct implementation; no additional design approval or experiment gate. Checkbox state tracks software tasks before publication receipts.

**Goal:** Matched R0/R1 additional1000-update C1 stages from complete040 weights, with only R1 adding0.10 masked039 old003train10 action retention.

**Architecture:** New `egrs/retention041/` composes the unchanged040 dataset, base C1 losses/sampling/dev and strict original adapters. Separate039 branch shares only the frozen original backbone; all references finish before any student graph. New041 schema/checkpoint/eval records040 ancestry, experiment arm and three durable observation budgets without relaxing old readers.

**Tech Stack:** Existing Python/NumPy/PyTorch; tiny CPU/fake only, no dependency upgrades/downloads.

**Spec:** `collaboration/tasks/041_old10_behavior_retention.md` at mainbe43704, acceptedPR15@428c13585cebac1d6c90fd86a205e914caa2bb8f; local docs merge6fe4bb9, no GitHub merge.

## Global constraints

- Both experiment_arm r0/r1 have base arm c1, full040 init SHA a51f9062fc5a54982233ffdb93f7fa164eaf78b6dbdc097721db9d7f87f57b12; ancestor1000 plus additional1000, fresh optimizer/scheduler/sampler/three ledgers. R0 is not C0 and is not old040resume.
- Frozen039 C1 teacher SHA6d340e99186090bab6739f173ecb118d03eb1bf574ae96d5f1c34241b02d644e, its original indexb85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c retained. Student040 index8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe,370ten/370pair,105fresh/180raw,143960rows. Do not rebuild anything.
- Original C1 loss/sampler/dev/input/score unchanged. Perupdate12ten+4fresh+4raw+1pair(twoends)=22student/8original references. R1 selects first≤4 eligible original batch positions, preserves duplicates/order; old003 six train ten only, no fallback, zero selection zero teacher forwards/loss. Exact per-sample masked mean over7D then mean across actual selected count, coefficient.10, same student graph/BC retained.
- One frozen backbone, independent complete039 LoRA/context/residual/count teacher, no teacher parameters in optimizer. All original/039 reference forwards before student graphs. no_grad/eval and exact mixed mode/hook/requiresgrad/checkpoint/cache/Python-NumPy-Torch-CUDA RNG restoration. Teacher installation isolated from RNG. R0 never loads039model.
- Each arm original references≤9024/student≤24560; R1old10≤4000train/0dev, R0zero; totals22048references/49120student/360formal. Forward budget spent durably before execution, no refund, advanced-ledger resume refuses. Oldrun/files/defaults/score preserved.
- No SSH/deploy/real data/labels/index/model/simulation/training/eval, extra seed/coefficient/baseline/MVP or automaticmerge/deletion. Only user starts approved real workloads after Codex acceptance/deployment.

## Review focus

- Wrong source adapter SHA/index/base lineage or incomplete040/039 parameter payload rejects before any live copy or teacher use.
- Independent teacher branch must produce distinct behavior and preserve student tensor/storage, hooks, mixed modes, cache and RNG even on exceptions/checkpointed backward.
- Eligibility comes from sealed040→039→old003 provenance, never task name/path substrings; dev/new sources rejected without changing sampler or student22 count.
- New-stage init and same-run resume are distinct; restore validates arm/init/teacher/index/config, all three durable budgets and actual sampler/update before restoring RNG.
- New041 adapters must be rejected by old root readers and load one student through new180eval contract, never teacher inference; metadata keeps c1 and r0/r1 distinct.

## Task1 — independent039 reference branch

Owner files: new `retention041/reference.py`, `tests/test_retention041_reference.py`; minimally extend `task_control/oft.py` prediction/decode with optional explicit modules argument, default old behavior unchanged.

Interfaces: `Old10Teacher(policy, verified_state, identity)` installs039 buffers/independent complete context using shared frozen original base while preserving student parameter names/objects. `.predict(policy,item,predict=None)` returns detached normalized1×8×7 actions; optional predict seam accepts explicit teacher modules. `preserve_rng()` and `original_reference_prediction(policy,item,predict=None)` protect exact RNG/modes; `Old10Budget(ledger_path=None)` durable limits train4000/dev0 (R0 budget constructed0 by explicit arm contract or disabled class). Full039 state is prevalidated by Task2.

- [ ] Red tests then minimal branch/context implementation; no active-graph weight copying, no second backbone.
- [ ] Test distinct base/teacher/student outputs, exact exception restoration/RNG, independent frozen teacher storage, no_grad and real checkpointed autograd backward safety. Original oft default regressions only affected paths.
- [ ] Report API/test evidence externally, no commit/real jobs.

## Task2 — strict stage adapter/checkpoint and single-student eval

Owner files: new `retention041/adapter.py`, `checkpoint.py`, `policy.py`, `evaluation.py` and corresponding tests.

Interfaces: `read_source_identity(directory, role, index_identity=None)` pure strict old038 payload validation and fixed SHA/role/index; `initialize_from040(policy,directory,index_identity)` restores complete existing installed student; `load_source_state(policy,directory,identity)` validates all tensors first and returns039state without student mutation. New `save_adapter/read_adapter_identity/restore_adapter_weights/attach_trained_adapter` use explicit041 root schema/experiment_arm and stage lineage. No schema masquerading or global old-reader relaxation; a genuine nested common payload is acceptable only with a mandatory strict041 outer envelope.

Checkpoint API `save_training_state(..., update,config,experiment_arm,index_identity,initialization_identity,teacher_identity,reference_budget,student_budget,old10_budget)` and symmetric `load_training_state` saves/restores all student params, optimizer/scheduler/sampler/RNG/three ledgers, exact inputs. Inputs and same-run binding may be grouped into a clearly named stage_identity dict if agreed with root before implementation.

Evaluation uses original retention.engine contract, new041schema/group/factory, base arm c1 plus experiment_arm, validates fixed phase-final1000 and040/039 identities; single student only. `run(config,out,experiment_arm)`, `build_plan(config,experiment_arm=None)`, report helpers preserve original180 population/score/videos/dualbridge.

- [ ] Red tests for roleSHA/base/index/inventory rejection, complete040 initialization, newroot rejected by oldreader, full newstage save/reload/same-run resume and advanced ledgers.
- [ ] Implement and test strict r0/r1 metadata; R0 requires no039model load. fake180 bindings use original fixed core/reporting fixture.
- [ ] Report API/test evidence externally, no commit/real jobs.

## Task3 — root data selection, training loop and delivery

Owner files: new `retention041/data.py`, `config.py`, `training.py`, `__main__.py`, `__init__.py`; config examples, entry/data/training CPU tests, docs/response/status/stage and evidence.

Public config format `task041-old10-retention-training-v1`: experiment_arm, training_recipe(exact existing038PRESET), index_dir, initial_adapter, teacher_adapter(null forR0), benchmark_root, runtime. Environment-variable expansion explicit; output/resume CLI options separate. New041 config guards original1000preset and actual fixed inputs before model loading.

- [ ] Red queue/mask tests: known old003 six train ten positions only, first4/less/zero/duplicates, strict unavailable ancestry errors, exact masked mean no fixed4 dilution. Reuse040 reader and preserve data/dev/selection.
- [ ] Red loop tests then implement minimal C1 stage loop reusing original loss/dev/sampler/forward. References all precomputed under RNG isolation; R1 add old10 to same main student graph only. Save progress/old10 counters/coefficient and ancestry without huge sampling logs.
- [ ] Tiny actual autograd/checkpointing init/teacher/state, matched R0/R1 sampling/RNG/base loss,22/8/≤4 calls, gradient isolation, interruption/resume equivalence and strict new eval reload; only targeted original regressions.
- [ ] One whole041 review and scoped fixes; final root-run affected CPU/fake, keep actual JUnit/red failures and honest boundaries.
- [ ] Commit code/evidence then concise responses/041_round1.md with commit, conda/python train/resume/eval/optional serial templates. NewPRto main lists unmerged PR15dependency, exacthead/tree/blob remote verification and local source/docs/CPU backup; no automaticmerge/deletion/deploy.
