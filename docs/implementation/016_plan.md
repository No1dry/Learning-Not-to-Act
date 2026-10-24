# EGRS task 016 implementation plan

> For agentic workers: use subagent-driven-development or executing-plans, with targeted CPU/fake verification. This plan operationalizes the approved task; it does not authorize research runs.

Goal: deliver a usable independent selector, evidence memory, frozen actor bridge, data preparation and LoRA training/inference software.

Architecture: the method policy owns immutable language goals, bounded sensor snapshots and revocable evidence. A selector process receives a strict sensor/context envelope; an actor process retains the original adapter and its transfer configuration. Only the effective language instruction changes.

Tech stack: Python >=3.10, NumPy; isolated optional PyTorch/Transformers/PEFT selector environment.

Spec: collaboration/tasks/016_egrs_full_implementation.md, collaboration/reviews/015_round1.md; fixed 015 response bdb6318.

## Constraints

- No real Qwen/VLA forward, training, teacher calls, simulator/render or data restoration during this implementation.
- Core pin: LIBERO-Remain-Eval@515e87d9b93ab838428791273a0f3020d6f56e9c; if inaccessible, label reference export c6dc98de0c54517c976057598b60f4cedf7fa3e5 explicitly.
- Preserve H520, 20Hz, K4/five observations, original metrics/evidence and action processing; no duplicate evaluator.
- New output directories only. Fail technical errors, preserve partial records, no implicit retries.
- Only language LoRA trainable. No VLA imports in training. No physical_truth in prompts or answers.
- Defaults: six images, two past timestamps, twelve records; SAT requires two fresh supporting queries; carry/completion expires after three unseen queries.

## Shared wire contract

All JSON objects use strict keys. Python arrays are allowed only in sensor envelopes handled through the core transport.

Registry: `{"instruction": str, "goals": [{"goal_ref": "g0", "source_text": str, "actor_text": str, "target": str, "destination": str|null, "kind": "transport"|"mechanism"}]}`.
Source text must occur in the original instruction; target/destination/actor words must derive from the instruction. Registry is proposed once from instruction alone, then validated and frozen for an episode.

Prediction: `{"query_id": int, "goals": [{"goal_ref": str, "entity_ref": str|null, "association": "MATCHED"|"UNKNOWN", "role": "TARGET"|"COMPLETED"|"DISTRACTOR"|"UNKNOWN", "relation": "SAT"|"UNSAT"|"UNKNOWN", "release": "RELEASED"|"NOT_RELEASED"|"UNKNOWN"|"NOT_APPLICABLE", "interaction": "HELD"|"NOT_HELD"|"UNKNOWN", "evidence": [Evidence]}]}`.
Evidence: `{"goal_ref": str, "entity_ref": str|null, "query_id": int, "snapshot_id": "qN", "camera": "agentview"|"wrist", "bbox": [x1,y1,x2,y2]|null, "coordinate_system": "normalized_xyxy", "supports": ["entity"|"role"|"relation"|"release"|"interaction"]}`.
One prediction per fixed goal, no missing/extra IDs. Meaningful current evidence requires current query ID and non-null region/entity. Mechanism release must be NOT_APPLICABLE.

Selector envelope:
`{"sensor": [{"query_id": int, "snapshot_id": "qN", "observation": whitelisted sensor dict}], "context": {"query_id": int, "instruction": str, "registry": Registry, "history": [short structured records], "commands": [command summaries]}}`.
Registry RPC uses only instruction. Prediction RPC receives no task ID/mask/GT. Commands include returned_chunk_length and command_not_execution semantics, never claim accepted/executed length.

Public interfaces: `egrs.policy.make_policy(config)` -> reset()/predict(observation,instruction)/close()/metadata; selector -> registry(instruction), predict(payload), reset(), close(), metadata; actor -> original reset/predict/close wrapped by actor facade inside core worker.

## Task 1: runtime contracts, memory, actor bridge

Files: egrs/contracts.py, memory.py, actor.py, core.py, policy.py, rpc.py, worker.py, sidecar.py; tests/test_runtime.py, test_policy.py.

Produces shared wire contract and factory. Consumes pinned core whitelist, frame transport, actor worker and headless APIs without copying scoring.

- [x] Write tests for missing goal, future evidence, held/entity mismatch, mechanism release, GT rejection, repeated old SAT, 3-query expiry, immediate reversal, stable actor text, nested OFT transfer.
- [x] Observe RED, implement strict contracts/memory/facade, observe GREEN.
- [x] Add policy/RPC/sidecar tests: no-history removes both image/text, no STOP, partial on selector/log failure, actor unchanged, commands not execution, process isolation and bounded waits.
- [x] Commit runtime.

## Task 2: data, token masks and actual selector train/inference

Files: egrs/data.py, egrs/selector/*, tests/test_data_training.py, data/catalog.json, configs/selector*.json, docs/data_training.md.

Consumes shared prediction/registry envelope. Produces QwenSelector with registry(instruction), predict(payload), reset(), close(), metadata; actual offline data preparation CLI and actual training entry.

- [x] Test external annotations, physical_truth isolation, source/group split and missing labels before implementation.
- [x] Test post-template token masking, weak-label neutralization, real UNKNOWN, role ablation and overlength rejection/drop-oldest policy before implementation.
- [x] Implement explicit Qwen2.5-VL class loading, pinned dependencies, language-only LoRA, actual optimizer/train/dev/checkpoint/resume and inference. Lazy imports; --help and dry-run do not load models.
- [x] CPU toy LoRA gradient/save-load and fake processor verification; report real processor not run if unavailable.
- [x] Deliver owned paths to the parent for the combined implementation commit.

## Task 3: integration, configurations and delivery

Files: pyproject.toml, egrs/cli.py, configs/method*.json, README.md, docs/runtime.md, tests/test_core_integration.py, collaboration/responses/016_round1.md.

- [x] Exercise actual pinned reference core runner/evidence/metrics with synthetic env and EGRS policy; no native simulator.
- [x] Verify malformed/failed predictions yield technical partial, query sidecar joins original queries, no scoring copies.
- [x] Implement inspect/catalog/export/import/build/train/worker/sidecar entry points and document actor/selector installation isolation.
- [x] Provide baseline, no-LoRA, full, no-history and no-role configurations with operational switches.
- [x] Final fresh review, targeted suite, build/import/help checks and credential/path scan; prepare archive/PR delivery. Do not merge.

## Review focus

1. Masked answer fields can still leak through teacher forcing: replace values/derived explanations before tokenization.
2. BPE boundaries and multimodal image expansion can misalign masks: require final IDs alignment; reject ambiguity.
3. Held identity changes must invalidate prior carry without globally resetting actor RNG.
4. Partial writes/worker crashes must never appear as a complete run; close failures remain visible.
5. Pinned eval dependency and OFT transfer identity must stay original beneath facade; batch 014 gap disclosed.

## Execution record

Baseline main: 891ef36. Repository was documentation-only; no baseline code/test suite.
Ruling: approved 016 plus direct user instruction supplies implementation approval; no repeated design approval gate.
Ruling: use existing .release-work isolation convention; preserve task015 local commit/PR.
Ruling: source-attribution metadata may name inaccessible eval pin but must distinguish verified export reference.

Implementation record: 17d94eb2d8ac5bbd7fadadea281b1747b4bc2ffa. Targeted verification: 20 runtime/config + 24 data/train + 2 original-core fake + 1 installed-wheel worker = 47 passed in separate processes. Fresh independent review fixes are recorded in collaboration/responses/016_round1.md. PR/archive publication is tracked separately by the final external publication record; do not infer actual research runs from checked software items.
