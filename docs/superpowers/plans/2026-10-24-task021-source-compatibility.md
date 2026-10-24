# Task021 historical source compatibility implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Let the five observed historical BDDL name pairs and exact Mac asset prefix reach existing source/physics checks with honest provenance.

**Architecture:** Add a versioned, source-bound metadata normalization to the method offline layer. Pass frozen dataset identity through the operational worker request; reconcile exact catalog/task/instruction/registry bindings before accepting aliases. Wrap the pinned c6 XML resolver with byte-span changes limited to approved direct asset file attributes, retaining separate source/intermediate/final identities.

**Tech Stack:** Python, pytest, synthetic HDF/XML fixtures, unchanged fixed annotation core.

**Spec:** `collaboration/tasks/021_historical_source_names_and_xml_assets.md`; observed snippets: `collaboration/tasks/021_runtime_compatibility_examples.json`.

## Global Constraints

- X仅实现与CPU/fake测试；Codex审查部署；用户启动真实标注。No real HDF/images, simulator import/restore/render, models, training or eval. No automatic stop/restart/merge.
- Only the five exact mappings in the spec, bound to dataset `yifengzhu-hf/LIBERO-datasets`, revision `147fa5eb607bb696dd922c3518084a90954cd2f3`, suite `libero_goal`, canonical source file and original instruction. Unknown aliases and cross-task/suite conflicts remain gaps.
- canonical必须同时匹配冻结catalog/registry、来源data.attrs明确标识与原source instruction。
- 不改固定core、原始数据、native谓词、对象映射、控制器、state/时间规则或RGB阈值；安装hash不证明历史字节一致性。
- XML only direct asset mesh/texture/hfield file locations; exact historical root, bounded dot/dotdot normalization, no escape, symlink escape, ambiguous root, missing file or forbidden external dependencies.
- Audit source identifiers, mapping version/source, BDDL hash and original/intermediate/final XML hashes accurately. Operational diagnostics never enter student samples/history.
- Preserve old artifacts/denominators and partial coverage. Run affected tests only; no new GPU/full-suite/multi-platform gate.

## Review Focus

1. Alias with absent canonical data attribute or missing dataset context must fail; ordinary exact-match metadata remains backward compatible.
2. A valid alias from another canonical task must fail even if catalog and instruction independently exist.
3. Prefix lookalikes and a second official-root marker in a Mac suffix must remain rejected as unknown/ambiguous.
4. Byte-level replacement must preserve quoted/XML-escaped surrounding content and never treat intermediate text as the original audit.
5. Early resolution failures must retain actionable error stage and complete operational provenance without student leakage.

### Task 1: Implement and validate source-bound name and XML adaptation

**Files:**
- Modify `egrs/offline/sim_metadata.py`, `sim.py`, `sim_worker.py`, `sim_native.py`.
- Create `egrs/offline/sim_xml_assets.py` for the method-only wrapper.
- Modify `tests/test_sim_metadata.py`, `tests/test_sim_native.py`, `tests/test_sim_pipeline.py`; create `tests/test_sim_xml_assets.py`.
- Update `docs/sim_annotation_pipeline.md` or the existing relevant offline annotation guide (locate its actual name before editing). Add concise compatibility/version/audit/limitations documentation; do not rewrite previous results.
- Controller owns public `collaboration/responses/021_round1.md`, status append and publication metadata after review.

**Binding spec:** Read the task021 spec and evidence JSON above in full. All Global Constraints apply. Exact snippets from that JSON are the fixtures, not newly read source data.

**Interfaces and decisions:**
- Extend `resolve_bddl_metadata(env_args, data_attrs, *, suite, source=None, dataset_identity=None, registry=None) -> dict` with optional context. Existing exact matches work without new context; alias normalization requires all context.
- Add an optional operational request key `dataset_identity` with exactly `dataset` and `revision`, nonempty strings. The controller creates it from the already verified frozen inventory in `_inputs`; worker validation checks its shape. It is never attached to frozen samples. Keep old request shape accepted when alias support is not used.
- Use fixed source file/task key (including `source_id`/episode consistency), catalog membership, exact original instruction and `mapping_for(registry)` to bind each map row. Explicitly store canonical instruction in the five-row table; do not derive it with generic word substitutions. SourceEpisode already checks saved problem_info against inventory; preserve that check.
- Only actually present `env_args.bddl_file` and `env_args.env_kwargs.bddl_file_name` may normalize through the exact five-row table. `data.attrs.bddl_file_name` must explicitly be canonical for a mapped source. Retain raw values and distinguish missing, validated, normalized, conflicting, malformed states. Include rule version `egrs.sim.historical-bddl-names.v1` and evidence source path, plus dataset/revision/task binding in metadata.
- Keep `resolve_installed_bddl` byte locks and all native/RGB gates unchanged. Successful mapped metadata feeds the existing canonical file resolution; absence of embedded historical bytes stays `unverified`.
- Add `resolve_source_xml(text, *, roots=None) -> (processed_or_none, report)` in `sim_xml_assets.py`; import pinned core resolver lazily. Reuse its pure parser/span machinery if useful; never mutate core constants. Only `/Users/yifengz/workspace/libero-dev/chiliocosm/assets/` is new. A file-attribute-only translation to the already supported exact `/home/yifengz/workspace/libero-dev/chiliocosm/assets/` root allows the real core resolver to perform bounded normalization, ambiguity, existence, containment and hash checks. Do not normalize away evidence before those checks.
- Wrapper version `egrs.sim.historical-xml-assets.v1`. Source/intermediate/final hashes must identify the correct text; retain the actual original value, intermediate value, normalized suffix, rule and target hash. Core report may be nested and explicitly named intermediate; it must not masquerade as source original. Keep full audit, while the native error message summarizes unresolved count and first few reasons.
- Replace only the NativeAdapter callsite; keep `_verify_xml_topology(original, processed)` and all native gates. Integration fake fixtures may patch native boundaries; XML-specific cases must execute real core resolution against temporary synthetic files.

- [ ] **Step 1: Add regression fixtures and observe RED.** Use all five evidence name rows and at least the observed floor texture and bowl texture paths. Pin exact accepted canonical identities/audit and reject missing canonical field, missing/wrong dataset/revision, wrong task/instruction/registry, cross-suite and unknown names. Test file hash mismatch, native cream-cheese atom preservation and RGB mismatch still block. Add XML success and failure tests for home/official roots, root escape, symlink escape (skip only actual OS privilege limitation), prefix lookalike, ambiguous marker, missing file, external dependency, only-file mutation and all hashes.
- [ ] **Step 2: Implement minimal helpers and request/native integration.** Keep pure compatibility logic separate from native constructor; do not expand generic task semantics or scoring.
- [ ] **Step 3: Focused GREEN and affected regression.** Python is `C:/ProgramData/anaconda3/python.exe`; set EGRS_CORE_ROOT to sibling `LIBERO-core-c6-reference`. Run native tests before pipeline tests due installed NumPy/Torch OpenMP order; use fresh `--basetemp .work/task021/<run>`. Cover metadata, XML wrapper, native fake, worker transport and pipeline export/no-leak paths; add other existing directly affected test modules only when justified. Record commands, outputs, skips, not just percentages. No environment changes or KMP bypass.
- [ ] **Step 4: Document rules and limits, self-review, commit.** Git is `C:/Users/robot/.conda/envs/direct/Library/cmd/git.exe`. Include RED/GREEN evidence, file list and remaining empirical/platform limits in the ignored report. Do not force-add `.superpowers` or `.work`. Do not publish or launch real jobs. Return DONE/DONE_WITH_CONCERNS with commit(s), test summary and report path.
