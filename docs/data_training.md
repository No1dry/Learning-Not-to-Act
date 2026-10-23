# Offline data and selector training

The software supports local stored RGBs, external annotations, group-separated datasets, actual Qwen2.5-VL language LoRA optimization/dev/checkpoints/resume, and independent inference. This implementation ran CPU toy and fake-processor checks only. Real datasets, annotations, research training, model forward, teacher calls and evaluation completed in this task: **0**. Transformers and PEFT were unavailable in the verification interpreter; the actual pinned processor and model have **not** been tested here.

Use a separate selector environment. Keep every actor interpreter and its dependencies independent:

```sh
python -m venv .venv-selector
# Activate this environment using your platform's standard activation command.
python -m pip install -r requirements-selector.txt
python -m pip install -e .
python -m egrs.datacli --help
python -m egrs.selector.train --help
python -m egrs.selector.train --config configs/selector.json --dry-run
python -m egrs.selector.infer --help
```

The pinned base and processor are both `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`. The loader explicitly uses `Qwen2_5_VLForConditionalGeneration`. The reference training-source identity is `QwenLM/Qwen3-VL@96588727e44c78b25ba03ea03b8e12f7e64fd0da`; this package implements its own field-aware preparation and optimizer loop, rather than importing that repository. Dependencies are pinned in `requirements-selector.txt`; this is a direct dependency pin list, not a wheel-hash lock or a claim that a given GPU/CUDA installation was validated.

Defaults are language attention q/k/v/o LoRA r16, alpha32, bf16, learning rate 1e-4, global batch16, and at most three epochs. The current loop uses **one device, microbatch1 and accumulation16**. A short final accumulation group is normalized to its actual size. Vision, base language weights and all non-LoRA parameters remain frozen. Loading identifies full language module names and checks the actual trainable parameter list; it fails if no language projections or any unexpected trainable parameters are found. `trainable_parameters.json` lists their names and sizes. Packing and flattening are disabled. No VLA or action labels are imported by the selector.

## Candidate catalog and existing images

```sh
python -m egrs.datacli catalog
python -m egrs.datacli extract-images --hdf5 local/demo.hdf5 --episode demo_0 --frames 0,10,20 --output prepared-images
```

`data/catalog.json` preserves the approved Goal10 + Object10 candidate filenames and fixed dataset revision `147fa5eb607bb696dd922c3518084a90954cd2f3`. Filename provenance comes from the fixed 015 review. The catalog does not download files or claim episode validation. The extractor reads only already-stored `data/<episode>/obs/agentview_rgb` and `eye_in_hand_rgb` uint8 HWC datasets. Missing images fail with no rendering or state-restoration fallback. Output directories must be new; a failure preserves partial files. The resulting `images.json` maps stored frame indices to local PNG paths.

Create a JSON array, a `{"samples":[...]}` object, or JSONL source manifest. One record represents one query of one short window. Source IDs identify **entire original episodes**, not frames. Window IDs are distinct within a source. Give all known same-source, repeated-initial-state, paraphrase, paired and augmented variants shared `group_ids`. These aliases are connected transitively before splitting. `task_group` supplies task stratification; aliases spanning multiple tasks remain one component. Unknown physical ancestry stays disclosed. No extra ancestry reconstruction is required.

The following is an unlabeled record. Use real local paths when preparing actual data; query IDs start at 1 and increase with source observation time. Neither a path nor a query ID authorizes reading a future frame.

```json
{
  "sample_id":"source-a/window-0/query-1",
  "source_id":"dataset-revision/libero_goal/file/demo_0",
  "window_id":"window-0",
  "task_group":"put_bowl_in_drawer",
  "group_ids":["known-initial-state-a"],
  "ancestry_known":false,
  "payload":{
    "sensor":[{"query_id":1,"snapshot_id":"q1","observation":{
      "agentview_image":"prepared-images/demo_0_0_agentview_rgb.png",
      "robot0_eye_in_hand_image":"prepared-images/demo_0_0_eye_in_hand_rgb.png"
    }}],
    "context":{
      "query_id":1,
      "instruction":"put bowl in drawer",
      "registry":{"instruction":"put bowl in drawer","goals":[{
        "goal_ref":"g0","source_text":"put bowl in drawer",
        "actor_text":"put bowl in drawer","target":"bowl",
        "destination":"drawer","kind":"transport"
      }]},
      "history":[],"commands":[]
    }
  },
  "answer":null,"provenance":{},
  "physical_truth":null
}
```

Only the shared sensor/context envelope is model input. Observation keys must pass the original eval core's whitelist. RGB alias forms accepted by the runtime are normalized to the two named cameras before prompt construction. Images stay unannotated: no truth masks, rendered overlays, extra views or simulator coordinates are introduced. The registry is validated against the exact original instruction and remains fixed across the source episode.

Historical records use the exact runtime wire shape, with past prediction fields and `complete`/`carrying` belief booleans. For each nonempty training history, also provide a record-level `history_provenance` map, e.g. `{"1":"human_visual","2":"model_prediction"}`. Allowed sources are `human_visual`, `reviewed_candidate`, or `model_prediction`; physical oracle history is rejected. This attests the origin of the record; it does not manufacture that evidence or run a prefix model. History cannot contain current/future predictions. Commands use `returned_chunk_length` and `semantics:"command_not_execution"`, with the exact stable registry/original language; returned length is never treated as executed length.

## External annotations and exclusion attestation

```sh
python -m egrs.datacli export --manifest source.json --output annotations.json
# An externally authorized human/reviewer edits answer/provenance/physical_truth.
python -m egrs.datacli import --manifest source.json --annotations annotations.json --output labeled.json
python -m egrs.datacli build --manifest labeled.json --attestation exclusion.json --seed 0 --output dataset
```

Export produces `format:"egrs.annotations.v1"` and leaves absent answers null. Import rejects changed source/window/payload/group identity, duplicate or missing sample IDs and invalid answer schemas. A prediction answer must include every fixed goal and all schema fields. For a completely ambiguous visible case, a valid answer is:

```json
{"query_id":1,"goals":[{
  "goal_ref":"g0","entity_ref":null,"association":"UNKNOWN",
  "role":"UNKNOWN","relation":"UNKNOWN","release":"UNKNOWN",
  "interaction":"UNKNOWN","evidence":[]
}]}
```

Use field-level JSON pointers for provenance, e.g. `{"/goals/0/relation":"human"}` to confirm this UNKNOWN, or `{"":"human"}` only when **every** answer field is confirmed. Allowed values are `human`, `reviewed_candidate`, and `weak`. Pointers inherit to descendants; a more specific pointer overrides its parent. `reviewed_candidate` means a human has reviewed the candidate, not that an unreviewed teacher output is trusted. Evidence is checked per item: `{"/goals/0/evidence/0":"human"}` confirms that item without requiring a parent-list annotation. Every leaf must resolve to `human` or `reviewed_candidate` after inheritance and overrides (empty containers require inherited confirmation too). An item with any effectively weak or unconfirmed field is removed before tokenization; fully confirmed siblings remain. Provenance is read at the original item index, while supervised pointers are remapped to the retained answer's compacted indices. `role_supervision=false` still removes all evidence. Every non-UNKNOWN visual claim requires goal/entity-bound regional evidence with normalized xyxy coordinates, supplied query/snapshot and camera, and appropriate `supports` fields. Mechanism release is always `NOT_APPLICABLE`.

`physical_truth` is an optional offline audit column and may be missing or null. It never enters built training examples, messages, or assistant answers. It cannot stand in for visible evidence. Extra explanation fields in answers are rejected by the strict schema. Unconfirmed entity/state values are replaced by null/UNKNOWN/empty evidence **before** teacher forcing, and receive no loss. A confirmed human UNKNOWN retains both its value and supervision.

`exclusion.json` must explicitly attest all three exclusions:

```json
{
  "six_composites_excluded":true,
  "semantic_equivalents_excluded":true,
  "eval_sources_excluded":true
}
```

The six excluded combinations are soup + tomato sauce in basket, stove + moka pot, cheese + butter in basket, soup + cheese in basket, two mugs on left/right plates, and white mug on plate + pudding to its right. Exclude their semantic equivalents, frozen eval official-init 0..9, known equivalent states and all derived samples. The attestation is an explicit external provenance assertion; software does not infer physical ancestry or semantic equivalence from filenames. Atomic goal overlap does not imply unseen objects/scenes or a never-exposed frozen base.

Build produces `train.jsonl`, `dev.jsonl` and `report.json` in a new directory. Whole connected source/alias components split approximately 80/20 within task strata. Small strata may have only train; a missing labeled split is a gap, not ready. Reports distinguish independent sources, windows and queries, per-split counts, confirmed and unsupervised fields, missing labels and unknown ancestry. Unlabeled records are reported, never filled, duplicated or replaced. Training also checks direct source and known-alias overlap across the supplied train/dev files.

## Final-token masks, history and budget

Training and inference use the same complete wire-schema prompt builder. The processor first applies the actual chat template and expands images. The encoder reconstructs image expansion from `image_grid_thw` and the processor merge factor, retokenizes with fast-tokenizer offsets, and requires **exact equality with final processor input IDs**. Scalar JSON spans define eligible field tokens; prompt, keys, unconfirmed fields and any BPE token crossing a field boundary are masked. A confirmed field without an unambiguous eligible token rejects the sample. No character-to-token size approximation is used.

The full budget is 4096 final tokens, at most six images and 256 visual tokens per image. The complete answer has a separate 1024-token ceiling. Training allocates the answer's actual final token count and all actual visual tokens first; original instruction/current sensor/schema prompt then occupy the remaining context budget, and historical text/images use the remaining space. Inference reserves the full 1024-token generation budget before accepting its prompt. Oldest historical snapshots and their corresponding text/commands are dropped first on overflow. Current images, registry and the complete answer are never truncated. If they still do not fit, or dropping history removes an answer's cited evidence, the named sample fails; there is no replacement. `encoding.jsonl` records final/answer/visual/context tokens, field masks, image counts and dropped snapshot queries for every encoded sample.

`configs/selector_no_history.json` removes both historical images and text/command context. `configs/selector_no_role.json` neutralizes and masks `entity_ref`, association and role supervision, and removes entity-bound evidence supervision before tokenization. Adapter inference requires matching saved `use_history` and `role_supervision` settings, so these trained variants use their separately trained adapters. The checkpoint guard runs before processor/model loading; a configured ablation flag alone does not certify its training identity.

## User-started training, resume and inference

The following commands perform real model work and are for the user's separately authorized research stage. A configured pinned eval core is needed for sensor validation. Either install that core in this interpreter or pass `--core-config core.json`, whose shape is described in the runtime documentation. Reference-export use must explicitly set its revision and `allow_reference:true`; it does not verify the inaccessible eval repository pin.

```sh
python -m egrs.selector.train --config configs/selector.json --train dataset/train.jsonl --dev dataset/dev.jsonl --output runs/selector --core-config core.json --dry-run
python -m egrs.selector.train --config configs/selector.json --train dataset/train.jsonl --dev dataset/dev.jsonl --output runs/selector --core-config core.json
python -m egrs.selector.train --config configs/selector.json --train dataset/train.jsonl --dev dataset/dev.jsonl --resume runs/selector/checkpoint-1 --output runs/selector-resumed --core-config core.json
```

Each epoch performs train and dev passes, writes losses and exact counters, then saves `checkpoint-N/adapter`, the processor configuration, optimizer/trainable parameter/RNG state, config identity and input-file SHA256 hashes. Resume accepts complete **trusted local** checkpoints at epoch boundaries into a new output directory. It rejects changed data/config and restores optimizer, Python/NumPy/PyTorch/CUDA RNG state. `COMPLETE` marks a completed checkpoint. Failures retain `status:"partial"`; no retry or baseline substitution occurs. These are SFT dev losses, not task-success metrics.

For adapter inference, copy the selector config and set `"adapter":"runs/selector/checkpoint-3/adapter"` (the alias `lora_path` is also accepted). The adapter must retain its sibling `state.json` and `COMPLETE` checkpoint files. Saved base/processor pins and training ablation settings must match. Saved adapter-file hashes are checked when present, and checkpoint identity appears in selector metadata. Omitting an adapter is explicitly the base model without task LoRA; a path alone is not a training/effectiveness claim.

```sh
python -m egrs.selector.infer --config selector-infer.json --mode registry --input instruction.json --output registry.json --dry-run
python -m egrs.selector.infer --config selector-infer.json --mode registry --input instruction.json --output registry.json
python -m egrs.selector.infer --config selector-infer.json --mode predict --input payload.json --output prediction.json --core-config core.json
```

`instruction.json` has exactly `{"instruction":"..."}`. `payload.json` is the sensor/context envelope above with local image paths and a validated fixed registry. Generation is deterministic (`do_sample:false`), followed by strict schema/reference validation. Invalid JSON, missing goals, unavailable evidence and model errors are technical failures with no repair or retry. The process-facing API is `egrs.selector.QwenSelector(config)`, with `registry(instruction)`, `predict(payload)`, `reset()`, `close()`, and `metadata`; ordinary module imports and help/dry-run paths do not load weights.
