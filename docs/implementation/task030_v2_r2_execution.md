# 030 v2 R2 execution ledger

Approved scope: consolidated R2 work order and R1 review. Keep training, adapter,
evaluation and034 unchanged. User starts all real restoration/export/experiments.

1. Reproduce the legitimate sensor-field rejection. Limit the exception to the
   proprio role and real ee/gripper sensor paths. Test3+3+2 and6+2 synthetic HDF.
2. Add a deterministic sparse-anchor plan, explicit state/observation/action
   bindings and an executable backend reusing pinned accepted restoration/XML,
   native predicate and original-image correspondence components. Planning is
   pure metadata; production is explicit and local to selected anchors.
3. Emit one PROGRESS index per verified nonterminal anchor, preserving full
   instruction and original chunk8/tail mask. No interpolation, no inferred
   ATOMIC ownership; missing/unreliable anchors retain RAW and diagnostics.
4. Integrate the producer in the existing export entry. Test the entire exporter
   with a synthetic backend and immutable source/split/whitelist contracts.
5. Independently review the changed paths, run only related CPU/fake tests,
   update PR9 and responses/030_v2_round2.md with exact commands and limitations.

Interfaces: progress.py owns plan/production/report and validated anchor records;
progress_native.py owns an isolated native worker adapter and pinned legacy
component loader. data.py remains the single indexed dataset/export contract.
Known base sources may produce progress only with two or more complete native
final goals; single-goal sources remain RAW. Compound definitions stay fixed to
the existing nine-task scope. Source/task bindings avoid hand-written200 rows.
