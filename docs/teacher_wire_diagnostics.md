# Task018 teacher wire format and existing-output diagnosis

Use the reviewed task018 implementation commit from the PR handoff, installed into the separate selector environment. Accepted task017 commit `c6840ae6` does not contain this repair. This update changes the offline teacher and adds a CPU diagnostic command; it does not rebuild sources, images, windows, registries or splits, and does not change the student model/prompt, contracts, VLA, metrics or training.

## Parsing and prompt identity

`egrs.teacher-wire.v2` accepts a bare JSON value or exactly one whole-output fenced block opened by a line containing ```json or ``` and closed by its own ``` line. Outer whitespace and LF/CRLF are allowed. Other languages, commentary around a fence, multiple/nested fences and incomplete fences are rejected. A balanced wrapper with truncated/malformed JSON fails the JSON stage. No substring/brace extraction, field normalization, missing-goal insertion or schema repair occurs.

Every generated attempt retains its original `raw` unchanged. `parsing` records `protocol`, `strategy`, separate `stages`/`errors` for wrapper, JSON and schema, `failure_stage`, and the first `schema_category`. Unreached stages remain `not_run`; model/load/budget failures remain distinct from output parsing. After decoding, the original `validate_registry` or `validate_prediction` is still authoritative. Schema failure leaves `answer=null` and never fabricates UNKNOWN. No parsing failure triggers a retry. Existing candidate window failure/skip/history behavior is unchanged.

`egrs.offline-teacher-guidance.v2` adds concise teacher-only contract guidance and complete legal UNKNOWN/evidence examples. It specifies sensor-assigned identifier syntax, exact fixed goal membership, no extra destination goal or DESTINATION role, transport/mechanism release distinctions, and field-specific bound evidence. Examples are expressly not observations or labels for the current input. Unsupported claims remain UNKNOWN; entities, regions and completion cannot be invented to pass validation.

Teacher metadata records prompt version, parser protocol, complete prompt hash and the existing pinned model/processor configuration. The actual messages are kept per attempt. The unchanged shared student prompt still governs both student training and inference, and all parties use the same unchanged semantic/evidence validators. Only the teacher gets the supplement. It goes through the existing encoder together with all images/context: max6 images, max256 visual tokens/image, max4096 total and max1024 answer tokens. No extra budget or silent trimming is added. Full real-tokenizer fit/output quality has not been measured in this CPU/fake repair; over-budget inputs remain explicit failures.

## CPU-only diagnosis of existing raw records

Run this separately with an already available artifact; the command does not contact the server, access pixels/HDF5, load a teacher, call a model or stop an active process:

```sh
python -m egrs.offline diagnose --help
python -m egrs.offline diagnose --input runs/017/06-candidates/candidates.partial.jsonl --output runs/018/diagnosis-001
```

Alternatives are the final `candidates.json` or `registries.json`. A final JSON manifest must retain its content identity. A partial candidate journal uses the existing `{"sample":...,"attempt":...}` JSONL records. No naked list of guessed answers is accepted. The command reads input bytes once; it can report a snapshot of a journal still being appended, but cannot claim that run is complete. A malformed/truncated outer journal record is listed as an input error, separately from generated-raw JSON failures. JSONL is framed by newline bytes and decoded strictly per row; a cut UTF-8 character in the last row does not discard earlier rows. A BOM is allowed only at the file start. Registry, query and ordered snapshot-reference metadata are checked without reading pixels; corrupt context is an input error and excluded from model-failure/attempted denominators. Missing original context or conflicting sample/actual-attempt payload is not silently substituted.

`--output` must be a new directory. `report.json` and `records.jsonl` are independent derived artifacts, never replacements for the source. The source byte size and SHA256 identify the exact snapshot. Available original teacher metadata/counts/calls are copied from final manifests; journal-only metadata remains unknown rather than inferred. Each derived row retains original raw/error/answer/parsing alongside the new diagnostic result. No later query, image or history is generated, and unattempted queries stay unattempted even if arbitrary raw text is attached to such a row.

Report fields:

- `counts`: structurally usable records, attempted, unattempted, attempted-without-raw, wrapper/JSON/schema passes, and input errors. Input errors are not included in usable-record totals.
- `first_errors`: one first failure per parsed raw. Wrapper/JSON errors are separate; schema buckets cover `release_kind`, `entity_identifier`, `fixed_goal_set`, `bound_evidence`, `role_enum`, `entity_association`, `evidence_supports`, and `other_schema`. Exact validator messages remain in per-record audits.
- `coverage`: strict-valid prediction queries/goals, all-UNKNOWN queries, queries with evidence-supported non-UNKNOWN fields, and per-field counts. Mechanism NOT_APPLICABLE is excluded from positive coverage; registry outputs are not visual state coverage. Counts are descriptive, not physical truth, completion rates or annotation accuracy.
- `original_generation`: yes/no/unknown counts of existing `generation_attempted` flags among attempted records. A missing legacy flag stays unknown; do not equate attempted wrapper calls with GPU forwards. `new_model_calls` is always0 for diagnosis.
- `supervision_ready=false`: diagnostic schema success remains a weak machine result. It does not promote a historical null/weak record, authenticate a human or establish useful supervision. Human visual evidence requirements remain unchanged.

The018 task reports a prior real snapshot:1057 processed/3200,397 actual calls,660 skipped,0 originally parsed candidates. A prior CPU wrapper-only analysis found397 JSON parses but0 strict-schema passes. X did not reread those397 raw files or reproduce that numerical diagnosis in this repair. These baseline facts remain attributed to the task; neither a new parser nor this document rewrites them. Running diagnosis produces a separate versioned result for the exact input bytes supplied.

## New inference is a separate user action after acceptance

Codex reviews this increment and prepares an isolated deployment. The user decides whether to stop/continue the old GPU job and, only after acceptance, starts a new output directory using the already prepared windows:

```sh
python -m egrs.offline candidates --windows runs/017/05-windows/windows.json --config configs/teacher_offline.json --core-config local/core.json --output runs/018/visual-candidates-001
```

Do not overwrite, delete, resume-as-called or recalculate old results. Keep old generation budgets and new-run calls separately; no retries, registry reruns, re-extraction or training is automatically chained to this command. Schema pass or an all-UNKNOWN answer alone is not a research success criterion.

Affected CPU/fake verification for this repair: `python -m pytest tests/test_teacher_wire.py tests/test_offline_pipeline.py -q` with the existing pinned core reference supplied for synthetic payload checks. Real raw diagnosis, model loads/forwards, GPU work, visual annotation, training and model evaluation by X in this repair:0.
