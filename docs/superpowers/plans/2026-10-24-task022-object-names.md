# Task022 Object historical names implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Extend the exact historical BDDL compatibility table to the ten already approved Object tasks, distinguishing four observed rows from six anticipated rows.

**Architecture:** Replace the Goal-only suite assumption with explicit suite/evidence metadata per exact row. Retain the same source/catalog/registry binding and installed/native gates; request and XML contracts remain unchanged.

**Tech Stack:** Python, pytest, fixed JSON registry and synthetic/fake fixtures.

**Spec:** `collaboration/tasks/022_object_historical_name_coverage.md`; evidence `collaboration/tasks/022_object_name_evidence.json`.

## Global Constraints

- X仅实现、受影响CPU/fake测试与GitHub交付；Codex审查部署；用户启动真实阶段。No real HDF/images, native simulator loading/restore/render, models, training/eval or autonomous stop/restart.
- 同一个固定dataset/revision和十任务catalog，不增加训练任务或数据；10个独立精确条目，其中4个有旧事件直接证据、6个是预期兼容，不是已观测或已物理验证。
- 运行时按精确表查找，不能做全局pick→pick_up替换、模糊语言匹配或允许任意未知冲突。
- canonical仍须由data.attrs明确提供且与该固定source/catalog/registry一致；原始字段、规范化字段、映射版本/证据状态与当前BDDL hash锁保留。
- 原021的5个Goal条目保持；未知别名、换物体/目的地、跨suite/任务、错dataset/revision、缺canonical、错误目标原子仍拒绝。
- 原XML、native目标/物体、state/RGB对应、可观察性及输入白名单照旧；历史原字节仍unverified，不据名称生成SAT。
- 只做名称解析、受影响fake构造/传输/导出CPU回归，不重复完整XML套件或全库。不热改运行目录、不重建原数据、不自动合并PR。保留旧输出、失败与所有分母。

## Review Focus

1. Six anticipated rows must never claim old-event evidence; test exact per-row evidence source/status.
2. Generalized suite lookup must reject crossed Goal/Object identifiers and multiple known old rows.
3. Correct object but wrong destination/instruction/registry must fail; use fixed registry instructions rather than deriving words from filenames.
4. Evidence-state fields must survive operational provenance yet remain outside samples/history/processor prompt.
5. Table expansion must not bypass explicit canonical data.attrs, hash locks or native atom checks; cover Object construction and wrong atom/digest rejection.

### Task 1: Add the ten precise Object rows and focused regressions

**Files:** modify `egrs/offline/sim_metadata.py`, `tests/test_sim_metadata.py`, focused fixtures/tests in `tests/test_sim_native.py` and `tests/test_sim_pipeline.py`, and `docs/offline_sim_supervision.md`. No XML helper/core/goal-map changes. Parent owns response/status/publication.

**Binding requirements:** Read the task022 spec/evidence in full and AGENTS.md. All Global Constraints above apply. Do not read real source data; evidence is existing tracked text.

**Interfaces and exact decisions:**
- Keep public metadata/worker/request/native interfaces unchanged. Use explicit suite on each row, exact old/canonical/source filename/instruction, per-row evidence path and observed boolean; small tuple/dataclass/dict organization is your judgment. No generic name transformations at runtime.
- Advance `NAME_RULE_VERSION` to `egrs.sim.historical-bddl-names.v2` for the expanded table. Existing new Goal resolutions use v2 with their original 021 evidence source and `observed_in_prior_events=true`; prior artifacts remain untouched. New Object rows use `collaboration/tasks/022_object_name_evidence.json`; four booleans true, six false, exactly per JSON. Add `observed_in_prior_events` and `evidence_status` (`observed_in_prior_events` or `anticipated_unobserved`) to `name_compatibility`; keep existing version/evidence_source and all binding/provenance keys.
- Ten Object instructions must be copied exactly from `egrs/offline/assets/sim_goal_map.json` and checked against `docs/annotations/2026-10-23_registry_annotations_v2.json`, not inferred from filenames. They are `pick up the <object> and place it in the basket` with frozen objects alphabet soup, bbq sauce, butter, chocolate pudding, cream cheese, ketchup, milk, orange juice, salad dressing and tomato sauce; store each complete literal row independently.
- All five original Goal entries remain accepted with their original exact instruction and source/evidence. Alias detection still occurs before uniqueness so all-old fields cannot bypass canonical attributes.
- Keep dataset/revision, exact source file/task_group, episode/source_id, catalog, original instruction and strict registry checks. Reject wrong object/destination, cross-suite/task, unknown alias, mixed known aliases, missing canonical, wrong identity, wrong native atom and canonical digest mismatch.
- `resolve_installed_bddl` and native/RGB code should not require production changes. Adapt synthetic constructor fixtures to select the explicit suite/source path without duplicating the whole existing fixture. No expansion of XML validation; use existing fake boundaries for affected Object cases.
- Add new audit markers to the existing pipeline no-leak assertions and ensure actual compatibility metadata can be carried through worker inspection without altering frozen samples/history. Do not inject physical truth into model data.

- [ ] **Step 1: RED.** Add parameterized tests for all ten rows using tracked022 evidence, checking canonical/raw values, complete binding, v2 and observed/anticipated status. At least the four observed cases must fail under old v1. Add Object negatives and actual fake-native success/wrong-atom/digest cases. Run only new/changed focused selections and capture expected old-code failure before implementation.
- [ ] **Step 2: Implement.** Change exact row structure/lookup and audit evidence fields; update existing v1 assertions to v2 while preserving original Goal behavior. Keep immutable original artifacts and avoid unrelated refactor.
- [ ] **Step 3: GREEN.** Run `tests/test_sim_metadata.py`, the metadata/native constructor and dataset_identity/transport selections from `tests/test_sim_native.py`, and the affected no-leak/export/request selections from `tests/test_sim_pipeline.py`. Native-before-pipeline order; no full XML module or full suite. Use existing Python `C:/ProgramData/anaconda3/python.exe`, EGRS_CORE_ROOT sibling `LIBERO-core-c6-reference`, fresh basetemp under pre-created `.work/task022`. Explain exact selection and cover unchanged strict native goal checks. No dependency mutation/KMP bypass; actual Windows symlink limitations may remain explicit skips.
- [ ] **Step 4: Guide/self-review/commit.** Add concise022 section distinguishing four observed/six anticipated and v2 version; retain021 text as historical version documentation. `git diff --check`, record commands/output/skips and empirical limits in ignored report. Git executable `C:/Users/robot/.conda/envs/direct/Library/cmd/git.exe`. Commit code/tests/guide only; no response/status/publish/job work. Return short status, commit, test summary and concerns.
