# 030 v2 implementation ledger

Approved scope: the 2026-11-02 v2 work order and plan. Implementation and CPU/fake
checks only; no downloads of data/weights, real export, simulator, training or eval.

1. Export indexed RAW/PROGRESS/ATOMIC windows from explicitly bound ordinary-demo
   manifests. Preserve trajectory groups and original base split; ambiguous
   enhancement evidence falls back to RAW. Test time/action/normalization,
   duplicate groups, leakage, boundary masks and coverage with synthetic HDF.
2. Implement fixed SOG10 language-attention LoRA training, original head/proprio,
   scalar-masked chunk L1, shared RAW dev selection, exact resume and two configs.
   Test tiny differentiable models, sampler coverage and adapter round trips.
3. Reuse accepted benchmark source/runner/evidence/scoring modules from pinned
   d8541ef4, without merging its PR or editing it. Bind method adapter identity
   independently of the base loader identity. A uses90, C uses36 fixed indices.
   The historical six retain their accepted legacy source and endpoint; new three
   retain their nine-task source protocol. No source reconstruction.
4. Task034 runs in a separate benchmark PR. Its pure binary report API is the
   only method report mapping; missing/error episodes retain the fixed denominator
   and prevent a formal complete score. Test synthetic22/90 and incomplete inputs.
5. Check only affected paths, independent review, record actual results and
   remaining resource/data prerequisites, then publish two PRs without merging.

Review focus: a duplicate demo split across train/dev; t versus t+1 misalignment;
atomic tail padding lowering loss; a frozen head disconnecting LoRA gradients;
adapter provenance omitted from evaluation or an incomplete batch reported full.

Interfaces: data exports sources.json/windows.jsonl/report.json and
AugmentationDataset; model loader exposes attach_trained_adapter and
read_adapter_identity; benchmark reporting exposes map_verified_results.
Root owns packaging/evaluation/integration; independent agents own data, training,
and Task034 respectively. No shared file editing or subagent commits.
