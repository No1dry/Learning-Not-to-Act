# Task020 Source Metadata Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the real task019 missing-BDDL-body entrance failure while preserving task identity, source provenance, partial diagnostics and the existing physical/visual supervision boundaries.

**Architecture:** Inspect source metadata incrementally before requiring individual fields. Resolve all available BDDL identifiers to one exact basename in the inventory suite, retain embedded-byte equality when available, and otherwise record an explicit installed-BDDL provenance with a fixed LIBERO revision and an expected per-file digest. Native construction, XML/goal validation, per-frame RGB alignment and label masking remain in the existing worker pipeline.

**Tech Stack:** Existing Python, h5py/NumPy synthetic fixtures, pytest, JSONL worker; no new dependency.

**Spec:** `collaboration/tasks/020_sim_source_metadata_compatibility.md`

## Global Constraints

- 只做受影响CPU/fake回归；没有真实元信息证据的字段必须写明假设，不把fake当真实数据读取成功。
- 源instruction、目标原子映射、原XML与已有RGB对应规则继续核对。
- 禁止模糊搜索、按模型成败挑任务、任意默认任务或扫描候选后择优。
- 不得默默默认控制器、机器人、相机约定或state/RGB时序。
- 原始已确认inventory/RGB/窗口/文本规格/160:40划分不重建，对应阈值与可观察性约束不放宽。
- 完整元信息诊断只留离线audit；不得进入student输入、历史或训练prompt。
- 旧019失败manifest/日志/数据保持不变。用户启动真实标注，X仅实现与CPU/fake验证；不启动真实HDF读取、恢复、渲染、模型、训练或eval。
- Keep existing request/frame/answer contracts and export input isolation. No whole-repository/multiplatform/GPU gate or environment modification.

## Review Focus

1. Windows/POSIX historical paths, redundant separators and explicit suite disagreements must resolve deterministically or fail; equal basenames in different stated suites are not agreement.
2. Absent optional metadata differs from malformed/present-empty/conflicting metadata; never silently discard contradictory evidence.
3. A missing or malformed earlier field must not erase already enumerated keys or later-independent metadata summaries; failure diagnostics survive the actual worker event/result route.
4. Installed-file provenance must identify LIBERO source bytes and BDDL bytes without treating eval-core revision as LIBERO revision or inventing historical source hashes.
5. Missing redundant production attributes may be resolved only from explicit existing source evidence; controller/camera/timing conventions are never guessed, and offline metadata cannot enter selector samples.

---

### Task 1: Repair the complete source-metadata entrance and deliver its regression evidence

**Files:**
- Modify: `egrs/offline/sim_native.py` (SourceEpisode inspection, BDDL resolution and NativeAdapter initialization).
- Create if useful: `egrs/offline/sim_metadata.py` for pure metadata/path reconciliation, keeping the existing large native module focused.
- Modify only if required: `egrs/offline/sim_worker.py` for preservation of precise source failure diagnostics.
- Modify: `tests/test_sim_native.py`; add `tests/test_sim_metadata.py` if the pure helper is separated; amend `tests/test_sim_pipeline.py` only for new offline-audit isolation coverage.
- Modify: `configs/sim_backend.example.json`, `docs/offline_sim_supervision.md`; create `collaboration/responses/020_round1.md`.
- README gets only a short task020 entry; do not author Codex's STATUS/review/task acceptance records.

**Interfaces:**
- Keep `SourceEpisode(root, source)` usable by existing callers; optional keyword `emit=None` may deliver JSON-safe inspection snapshots during construction. On failure attach the latest inspection to the raised exception.
- Keep `NativeAdapter(request, *, emit=None)` and worker protocol formats. Forward partial inspection before/after fallible phases without overwriting it with None.
- If separated, `resolve_bddl_metadata(env_args: dict, data_attrs: Mapping, *, suite: str) -> dict` returns reconciled exact basename and source-field evidence; `resolve_installed_bddl(root, metadata, *, embedded: str | None, runtime_identity: dict) -> tuple[Path, dict]` resolves one contained path and provenance. Equivalent private names may be chosen, but document the final interface in the report.
- New provenance is versioned, uses `metadata_resolved_installed_bddl` when body absent, explicitly sets `source_embedded_bddl_present=false` and historical-byte equality unverified, omits/nulls the source-body digest, and records all source identifier fields, fixed LIBERO source identity, installed path and SHA256. Embedded mode continues strict byte equality.
- Add optional native `libero_source = {revision: <40 lowercase hex>, bddl_sha256: {<suite>/<exact basename.bddl>: <64 lowercase hex>}}`. Require it for missing-body mode; if supplied, verify the selected file digest in either mode. The declared fixed LIBERO revision plus pre-collected expected BDDL hashes and existing verified module locks bind the selected installation; do not label the revision runtime git-verified if it was supplied as deployment provenance. Keep eval-core revision separate. Capture file bytes and check unchanged before native construct. Existing embedded-body configs remain usable without the new lock. Extend the existing standard-library lock collection recipe to collect only the fixed catalog filenames from an explicitly selected pinned installation, recording how its revision was established; no HDF/simulator read or arbitrary filesystem search.
- Reconcile actual supported BDDL identifiers including `data.attrs.bddl_file_name`, `env_args.bddl_file`, and `env_args.env_kwargs.bddl_file_name`; any present malformed or contradictory identifier gaps. Historical machine prefixes may differ; explicit known suite segments must match the inventory suite. If no unambiguous task identifier exists, gap.
- For other fields, enumerate keys/status/provenance first. A redundant optional field may be absent if explicit source evidence suffices; otherwise emit a precise missing-field gap. Do not infer controller/robot/camera settings. `num_samples`, when present, must match actual shape; instruction and image convention must retain explicit validated provenance and reject contradictions. Existing source/inventory instruction equality remains; do not add literal BDDL :language equality because official benchmark instructions can differ in wording (top drawer vs top layer of drawer). Native atom mapping remains the task-semantic check.

- [ ] **Step 1: Add focused failing tests for missing optional BDDL metadata and partial inspection.** Synthetic fixture omits the known missing body while keeping a unique env_args path. Assert successful exact resolution, honest missing-body provenance and no fabricated source hash. Cover optional filename absence, each available identifier as sole evidence, missing identifiers, conflicts including same basename/different suite, historical Windows/POSIX paths, malformed-present fields and embedded-byte mismatch.
- [ ] **Step 2: Run focused tests before implementation.** Use `C:/ProgramData/anaconda3/python.exe -m pytest tests/test_sim_native.py tests/test_sim_metadata.py -q -k metadata` (omit absent helper file); retain expected RED output under `.work/task020/` and explain the concrete failure. Source fixtures are generated under pytest temp paths only.
- [ ] **Step 3: Implement incremental inspection and deterministic resolution.** Preserve key/type/hash summaries without copying XML/state/truth into diagnostic inputs. Retain every completed snapshot on subsequent parse/source/native failure. Verify exact installed file, source instruction, actual runtime goal atoms and original XML/RGB before useful labels. Do not change alignment/visibility thresholds or supervision rules.
- [ ] **Step 4: Extend the actual worker/fake-native route tests.** Assert missing-body constructor can reach the unchanged native boundaries using fake modules, body mismatch/identifier conflict stops before native construction, failures retain partial inspection and precise stage, and offline inspection never appears in annotations/student input or history. Exercise contradictory/missing controller and camera metadata without defaulting. Test installed-file mutation rejection and source-identity honesty.
- [ ] **Step 5: Run affected GREEN once after changes.** `python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py tests/test_sim_pipeline.py -q --basetemp .work/task020/final` (omit nonexistent file; native first). Set EGRS_CORE_ROOT to the existing pinned reference checkout. The prior Windows OpenMP import-order issue is known; no KMP bypass, dependency modifications or unrelated diagnosis. Run changed-file compile and `git diff --check`. Do not rerun unchanged full suites.
- [ ] **Step 6: Update guide and response.** Explain provenance modes, real known evidence (only missing body is confirmed), fixture assumptions, test commands/results, remaining real validation, new output directories and next actors. If original metadata is truly necessary, supply a user-run metadata-only command without executing it; otherwise do not add a new gate. Preserve historical019 findings, counts and failures. Preparation/implementation percentages must be separate from real annotation/training/eval progress.
- [ ] **Step 7: Self-review and commit explicit deliverable paths.** No force-add of `.superpowers`, `.work`, private paths or data. Write a detailed ignored report with RED/GREEN, changed files, final interfaces and concerns; return short commit/test summary for independent review. Controller publishes reviewed content to existing PR2 without merging.
