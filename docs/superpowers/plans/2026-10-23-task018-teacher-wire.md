# Task018 Teacher Wire Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Accept exactly supported JSON wrappers, retain strict semantics, and diagnose existing raw outputs without another model call.

**Architecture:** One offline parsing function supplies staged audit to both the teacher and a CPU-only diagnostic CLI. A versioned teacher-only supplement extends the unchanged shared prompt with contract rules and validated examples. Student prompts/contracts, budgets, images, source splits and history machinery remain unchanged.

**Tech Stack:** Existing Python/json/re contracts and pytest CPU/fake fixtures; no new dependencies.

**Spec:** `collaboration/tasks/018_teacher_wire_format_and_schema_alignment.md`, accepted implementation `c6840ae6c27429c8a6eb27a4e937927f4f934202`.

## Global Constraints

- Accept naked JSON or exactly one complete outer ```json / untyped code block. No brace extraction, field repairs, goal insertion, ID normalization or enum substitution.
- Preserve raw and original counts/results. Keep existing validate_registry/validate_prediction semantic/evidence validation unchanged; report wrapper, JSON and schema stages separately.
- Teacher-only prompt supplement is versioned and shares the existing student contract. Existing six-image/256-visual-per-image/4096-total/1024-answer limits still apply to the complete prompt; no silent trimming or budget enlargement.
- No real data/model calls, GPU, registry reruns, frame extraction, training/eval, stopping jobs, or source rebuilding. Tests use synthetic artifacts/fake generation only.
- Diagnostic outputs are separate new directories; never promote old null answers, regenerate missing history or mark unattempted queries as called. Actual old and new budgets remain separate.
- Deliver incrementally on original PR2 with response018; no automatic PR merge/deploy.

## Review Focus

1. A single fence with trailing prose, multiple blocks or a truncated closing fence must not become an accepted answer.
2. Schema-invalid JSON must remain null with the original raw and first semantic error retained.
3. Legal all-UNKNOWN predictions must be distinguished from outputs with supported non-UNKNOWN claims.
4. Snapshot diagnosis of a partial JSONL journal must not invent later queries or treat malformed outer records as model JSON failures.
5. Teacher examples/instructions must actually reach the encoding budget and audit, while student training/inference retain their existing shared prompt and unchanged schema.

## Task 1: Complete bounded parsing, prompt and diagnostic repair

**Files:** Create `egrs/offline/parsing.py`, `teacher_prompt.py`, `diagnostics.py`, `tests/test_teacher_wire.py`; modify `teacher.py`, `cli.py`, `docs/offline_pipeline.md`; create `collaboration/responses/018_round1.md`. Synchronize latest main coordination unchanged.

**Interfaces:** `parse_teacher_output(raw, *, instruction=None, payload=None)` returns answer/null, error/failure_stage, version, strategy, and independent wrapper/json/schema stage statuses. Teacher stores this audit while retaining its original raw. `build_teacher_messages` calls existing `build_messages`, appending versioned guidance only for visual predictions. `diagnose(input_path, output)` reads a final candidate/registry manifest or candidate partial JSONL byte snapshot; emits sealed report and per-record derived diagnostics, with source SHA256 and original protocol/counts when present.

- [x] Write failing parser/teacher tests: bare/fenced success, disallowed wrapper variants, malformed JSON, all seven reported schema categories, legal mechanism/transport and exact multi-goal set, current/past bindings, raw preserved and no retries/history fabrication.
- [x] Run `python -m pytest tests/test_teacher_wire.py -q` and inspect expected missing parsing/prompt APIs or fenced-answer failures.
- [x] Implement staged parsing using anchored whole-output wrapper matching and existing strict validators; wire into teacher with version/hash metadata. Implement compact UNKNOWN and visibly grounded examples that pass existing validators, with explicit example-only warning.
- [x] Run the targeted tests; confirm success and shared encoder rejects over-budget augmented input before any fake forward.
- [x] Add failing diagnostic tests using synthetic final manifests and journals: wrapper/JSON/schema counts, stable first-error classes, all-UNKNOWN vs supported non-UNKNOWN coverage, unattempted/no-raw counts, malformed outer journal records, immutable input hash/bytes, no optional model/image/HDF loading, and existing output refusal.
- [x] Implement `python -m egrs.offline diagnose --input PATH --output NEW_DIR`; only parse existing raw with original context, never load images or call teacher. Keep raw and old errors in derived rows; report finite snapshot extent and input errors explicitly.
- [x] Run affected `tests/test_teacher_wire.py` and `tests/test_offline_pipeline.py`; no whole-repository or unrelated runtime tests. Shared contracts/student code are unchanged.
- [x] Document exact CPU diagnostic and new-run commands, separate protocol/prompt versions, original397-record baseline from task evidence (not rerun), no empirical quality claim, and all real work count0 for X.
- [x] Commit, generate full incremental review package, obtain one fresh independent review, and address concrete blocking findings using RED/GREEN (two diagnostic P2 findings, 55/55 affected tests pass).
- [ ] Deliver original PR2 and verify final tree equality; fixed remote SHA and handoff recorded in the PR.

## Decisions

Use teacher-only guidance to avoid changing the accepted student training/inference prompt; both still use the exact same contracts. A diagnostic uses the bytes read once from an existing artifact and reports that snapshot, never implying the active run finished. No existing raw outputs are available/required for this implementation; reported397-record facts remain attributed to the task's prior CPU diagnosis.
