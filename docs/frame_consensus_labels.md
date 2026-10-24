# Frame/view/field consensus supervision (024)

This is a versioned offline supervision protocol, not a change to benchmark
success or a claim of unique physical alignment. It keeps RGB threshold 0.03,
minimum visible support 16 pixels, native task predicates, frozen images,
registries, 200 sources and the original 160/40 source split.

For every requested nonterminal frame, restore each of the three original
candidate rules. Render each original camera once and compare both orientations.
A camera supports a candidate only when exactly one orientation passes the
original whole/foreground RGB gate. At least one supporting camera admits a
candidate; both cameras measurably failing exclude it. Unmeasured/failed operations
remain indeterminate rather than silently disappearing from the candidate set.

Each field requires a defined and identical value across every admitted candidate
and one common, matched camera with the existing field-specific visibility and
physics certificates. Agreement on relation does not imply release or interaction.
Indeterminate candidates, disagreement, unsupported fields and the final-frame
boundary remain UNKNOWN. Bounding-box selection uses RGB residual and a fixed
rule order, never label value. No state, candidate, segmentation or certificate
is added to student input/history or the action policy.

The verified 022 parent supplies the 14 already accepted sources without new
simulation. Reuse retains the original fact, parent manifest and code identity.
The remaining sources are recomputed under this protocol in a new output directory.
Export revalidates both proof types and reconstructs labels before producing the
usable subset. `ready=false` still means incomplete annotation coverage, not that
a nonempty, validated train/dev subset is forbidden for training.

Explicit entry points:

```bash
python -m egrs.offline label-consensus --parent PARENT_MANIFEST \
  --windows FROZEN_WINDOWS --output NEW_ANNOTATIONS
python -m egrs.offline export-sim --annotations NEW_ANNOTATIONS/manifest.json \
  --windows FROZEN_WINDOWS --attestation EXCLUSION_ATTESTATION --output NEW_DATASET
```

Progress summaries are rate-limited to three seconds (first frame and source
completion force an update); frame journals are flushed immediately. This avoids
recomputing full-dataset coverage for every native stage notification.

On 2026-10-24 the user explicitly authorized Codex to implement and run this
repair through training readiness. Formal training is not automatically started.
Old outputs and X's historical delivery remain unchanged.
