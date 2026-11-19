# 048: LIBERO-10, 500 episodes per model, same official pipeline

User requested the same pipeline for LIBERO-10: all10 tasks x50 official initial
states x2 models =1000 new episodes. The additional task5 book/caddy task is
included; this is not the historical nine-task Remain population or450 per arm.

The original047 evaluator is extended by an explicit protocol descriptor.
Its default three-suite schema, horizons, cells and3000 denominator remain
unchanged;048 has a separate schema, onlylibero_10, two cells and1000 total.
The new module only selects this scope. Original native OFT source, environment,
initial states, image/action processing, success bool and video generation are
still delegated unchanged. H1 loader and weights are unchanged.

Native LIBERO-10 horizon520, waiting10/chunk8/seed7/env0, two images/proprio,
center crop, normalization libero_10_no_noops and all50 default init states
remain native. Base then H1@3000 each500. Natural request ceiling65000.
No new training/data/labels, Remain scoring, prompt changes, MVP or extra seeds.

User starts once after sourcing the deployed session048.sh:

    python -u -m egrs.official048 run-all --config-dir "$LNA048_CONFIG" --output "$LNA048_ROOT/runs/task048-official-libero10-001"

Read-only progress:

    python -m egrs.official048 progress --output "$LNA048_ROOT/runs/task048-official-libero10-001"

Completed047 source/install/run and all earlier results are not overwritten.
Deploy048 into a separate source/config directory with explicitPYTHONPATH.
The final report compares two official500 SRs plus all10 task results and
same-initial-state gains/losses. Only after completed results may it be combined
with047's other three official500 results; never pool historical nine-task
compliance scores into a four-suite official average.
