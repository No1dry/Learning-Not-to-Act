# Task042 audited TCIF implementation plan

> **For agentic workers:** Use subagent-driven-development or executing-plans. User requests direct implementation from the approved work order; no additional design gate or real MVP. Publication is recorded by delivery receipts.

**Goal:** Matched F0/F1 C1 stages from full041R0, with F1's only research difference being task queries blocked from all control keys at every final SDPA.

**Architecture:** New `egrs/tcif042/` owns pure execution contract, per-instance audited SDPA adaptation, observed fused-token layout, strict source/stage adapters and training/eval wiring. Both arms use explicit dense masks; original references enter the same compatible native bidirectional path without the student layout hook. Immutable per-observation mask tensors reach each existing decoder checkpoint input, never a latest-sample field.

**Tech Stack:** Existing PyTorch/NumPy; original Transformers4.40.1/OFT source audit as read-only compatibility evidence. Only tiny CPU/fake tests, no upgrades/model downloads/real jobs.

**Spec:** `collaboration/tasks/042_task_control_information_firewall.md`, `collaboration/evidence/042_audited_sdpa_source_excerpt.md`, mainff707d3; acceptedPR16@e8dcf87979d14d081666629a2de3483629a4f59c. Local docsmergee4c0b4a, not a GitHub merge.

## Global constraints

- Base algorithm c1 in both arms; full041R0 source SHA d4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397, source phase-final1000 with2000 ancestralupdates. Each newstage1000, new optimizer/scheduler/sampler/RNG/budgets; cumulative3000, not oldrunresume or oldC0/C1.
- F0 native padding-only bidirectional graph; F1 same explicit backend/shape/math plus T-query×C-key=-inf only. No global causal mask, new parameters/heads/losses/labels/entities/teacher or changes to data, C1 losses/sampling/dev/score.
- Preserve actual q/k/v/o and LoRA Parameter objects/paths, RoPE/GQA/dropout/scaling/head layout. No site-packages/OFT/core edits or global primitive monkeypatch. Reject unsupported class/source/backend/cache/eager fallback explicitly at normal job init, no extra real forward.
- P verified in the original single fused embedding pass; A=inserted+nonzero(original _process_action_masks(labels[:,1:])), exactly56shifted positions, firstA∈C. T=valid positions before minA excludingP, C=other valid. AllH_v/H_l∈T, allA/P∈C, T/nonempty legal keys. Padding columns remain blocked.
- Each sample's full final mask is freshly built once and passed explicitly through LM→decoder→checkpoint→attention. No current/latest mask on policy/module or global/thread state. Differentlength pair graphs and subsequentreference calls cannot alter masks for recomputation.
- OriginalSOG10 reference bypasses TCIF layout prohibition and all LoRA/z/residual branches; all8references before22studentgraphs, no_grad/eval with modes/hooks/RNG/checkpoint/cache/requiresgrad restored. No039model or old10 objective.
- Existing040index8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe;370ten/pair,105fresh,180raw,143960rows, oldsplit/dev/order unchanged; no index production.
- Each arm1000updates/reference≤9024/student≤24560; total2000/18048/49120, formal360. Forward ledgers pre-spend/failure no refund; strictsame-run/source/index/contract/backend/arm/config resume, final1000only. Preserve actual float photometric_probability0.0 in generated JSON.
- No SSH/deploy/real models/features/data/labels/index/simulation/training/eval/extra seeds/search/baselines/MVP/automerge/deletion. Preserve all039040041 artifacts/history.

## Review focus

- Audit last-row expansion and upstream mask conversion cannot erase F1; primitive actually gets dense F0/F1 additive masks withis_causal=False.
- Multi-layer indirect P→C→T leakage defeated by full T←C prohibition, while firstshifted A and allC retainnative proprio/control access; no token movement.
- Fused insertion and padding are checked against actual inputs_embeds/proprio projection/outputprojector length, not assumed last56 or extra VLA forwards.
- u/v masks are explicit immutable checkpoint inputs; no temporary route state consulted at attention replay. Reference native path does not inherit studentprehook.
- Strict042metadata/runtime contract/source initialization, complete reload, ancestry2000+new1000, oldreaderreject, actualconfigs0.0/arms/backend unchanged and two budgets/no039teacher.

## Task1 — SDPA contract and per-instance final attention

Owner `tcif042/contract.py`, `attention.py`, `tests/test_tcif042_attention.py`.

Interfaces: `contract_for(experiment_arm)` returns deterministic JSON-only042contract; `validate_contract(value, experiment_arm=None)` exacttype/field/value check. `install_attention(policy, experiment_arm)` returns controller with `.contract`, `.runtime`(observed actual class/version/source/dtype, noforward) and callable `.forward(model, *, instruction_mask, **model_kwargs)` for student path. Instance-level LlamaModel `_update_causal_mask` passes verified dense4D unchanged or maps native2D padding to explicit native mask; no global torchpatch. Audited SDPA forward only removes last-row override and preserves math/params. Imports layout Task2 at use, not a circular top-level dependency.

Controller studentforward calls Task2 `prepare_layout(...)`, captures actualproprio projector output and registers one scoped LM prehook closing onlyoverthispreparedobject. Hook calls `build_layout(...)` on actualfusedembedding/padding/proprio, then `final_attention_mask(layout, arm, dtype)` into LM attention_mask. Hooks removed finally; mask itself enters existing layercheckpoint. Originalrefs have nohook and stay native. Fake runtime inspector seams only in tests, never public disable-check flags.

- [x] Red then implement primitive masks/native equality/grad, GQA/RoPE/dropout/param inventory, unsupported/cache/eager rejection, actualsourceaudit guard and per-instance ownership.
- [x] Test multi-layer numeric noninterference/control access and explicitcheckpointu/v masks with actual SDPA; reference native afterstudent hooksremoved, noaddedforward or params.
- [x] External report/test evidence; no commit/real jobs.

## Task2 — prepared/fused layout and shared prediction

Owner `tcif042/layout.py`, `oft.py`, `tests/test_tcif042_layout.py`, minimal `task_control/oft.py` optional `forward=None` seam.

Interfaces: `prepare_layout(model,input_ids,labels,instruction_mask)` returns immutable prepared positions/clonedmetadata. `build_layout(prepared, inputs_embeds, attention_mask, projected_proprio)` checks actual inserted/visual/P/shifted56/z and returns T/C/P/A/valid layout. `final_attention_mask(layout, experiment_arm, dtype)` makes fresh B×1×S×S additive0/-inf, validrows legal, F0/F1samedims. Agent coordinates exact dataclassfields with Task1.

Old sharedprediction adds optional forward callback, default model(**kwargs) unchanged; callback receivesmodel plus originalkwargs and instruction_mask, noexpertvalues. `tcif042.oft.prediction(policy,item)` delegates originalpreparation/encode/decode and042controller.forward; no rerun ofimages/vision/projectors. Keep normaldecoder matrices/taskcontext unchanged. Controller layoutresult can be checked against returnedprojector_features in call without mutable latest fields.

- [x] Red tests for shifted firstA, H_v/H_l/T/P, variablelength/scaffold/stop/padding, no legalkeys/invalidlayout; exactoneprojector/visioncall and originalsharedhidden/action selection.
- [x] Prove pair graphs checkpoint eachownmask, unsupportedshape/cache errors, rawitem white list. Coordinate with Task1 controller implementation.
- [x] External report; no commit/real jobs.

## Task3 — R0 initialization, strict042 adapter/checkpoint/policy/eval

Owner `tcif042/adapter.py`, `checkpoint.py`, `policy.py`, `evaluation.py` plusidentity/evaltests.

Pure metadata accepts real041R0root throughstrict041reader, then fixedsourceSHA/fullstudentpayload/index/base lineage and stage ancestry. New042root independently strict; never relabeloldschema, masks/contract not lost. `read_source_identity`, `initialize_from041(policy,directory,index_identity)` copy everyvalidatedstudenttensor; `.student_identity` uses originalcommonpayload keys. Newstageidentity agreed: formattask042-stage-inputs-v1, armc1, experiment_arm, fullinitialization_identity(041outer),index_identity,ancestor_updates2000,additional_updates1000,attention_contract.

save/load adapters/checkpoints mirror041 APIs minus teacher/old10, add attention_contract via stageidentity or explicitmatching parameter. Restore configuration/arm/source/index/contract+allstudent/optimizer/scheduler/sampler/RNG/twoledgers, rejectadvancedbudgets and oldreaders. Policy only onebase+student then042attention install; prediction explicitly uses042shared path, no039teacher. Eval originalengine180/H520/chunk8/seed7/sources/score/videos with f0/f1 and basec1.

- [x] Red real041syntheticR0source/full restore/newschema/type/contract/source/budget/run identity rejection, safe failedsave.
- [x] fake180/arm singlepolicy and sharedpredict, reference absent at eval, originalbinary10/official00report; nooldreaderrelaxation.
- [x] External report/API; no commit/real jobs.

## Task4 — root fixeddata/config/training and delivery

Owner `tcif042/config.py`, `training.py`, `__main__.py`, `__init__.py`; configexamples, rootentry/trainingtests, docs/evidence/response/status.

Reuse immutable041StageDataset/040reader (no queue needed), exactexistingC1PRESET and actual0.0 JSONtype. Config fixed042 format/f0f1, training_recipe,index_dir,initial_adapter,benchmark_root,runtime; no teacher paths/old10 knobs. Rootloop composes originalC1 functions: full041R0init thenattentioninstall, fresh optimizer/RNG andreference/studentledgers,8protectednative references before22student, unchangedpair/dev/microbatch, allpredictions042path. Same-run outputbound in runconfig; strictresume/noautomaticphases.

- [x] Red parser/actual generatedconfigfloat types/rolepreflight/zeroold10, matchedF0F1sampling/C1loss formulas, actual tinycheckpoint training+references+fullresume andsingleforward budgets.
- [x] Only affectedCPU/fake root verification; onewhole042diff read-onlyreview, scopedfixes. Recordactualpass/fail/skip andCPU-only/GPUunrun boundaries, nofull166repeat gate.
- [x] Commit then042_round1 withimplementationSHA/nativeaudit/primitive masks/immutablecheckpoint/refbypass/ancestry/contracts andfullconda train/resume/eval/nohup/serial-failstop commands. NewPR lists unmergedPR16dependency; exacthead/tree/blobreadback andlocalSHA softwarebackup. Noautomerge/deploy/deletion.

Execution: implementation03e0efcd; affected109passed, independent review no blocker. Publication/readback/backup is the remaining delivery step tracked by root. No real jobs or deployment.
