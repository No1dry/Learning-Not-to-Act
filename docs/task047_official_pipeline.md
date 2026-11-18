# 047: original OFT evaluation, base versus H1@3000

The user requested direct Codex implementation. X need not implement the older
047 dispatch. Real evaluations remain user-started.

This entry imports the pinned official OFT runner and calls its unwrapped
eval_libero body. Original run_task/run_episode, observation/action processing,
done-based success and video saving are delegated unchanged. Thin observers
record native outcomes and files. A native-caught Episode error is surfaced as
a software failure, not silently published as a valid failed policy episode.

Only the model initialization hook differs by arm: base gets the original
model; H1 gets exactly the frozen rank16 LoRA after the same initialization.
The original published LoRA is already merged. The native cfg.lora_rank stays32.
Old043/045 code and identity files are unchanged. A separate047 restore checks
the same original base/components and original10 statistics, then independently
binds the current suite's native normalization. It never fakes training lineage
or forces10 statistics on Spatial/Object/Goal.

Six isolated, sequential processes evaluate base/H1 on each of Spatial, Object,
Goal, 500 each (10 tasks x50 default init states), total3000. Native horizons
220/280/300, waiting10, env seed0, policy seed7, center crop, two images/proprio
and chunk8 remain native. No prompt changes, Remaining scorer, FINISH, teacher,
training state, new data or extra model/physics smoke test.

Deployment passes an isolated PYTHONPATH and reuses the current simulation
venv with the existing Torch/Transformers/TF packages; no dependency upgrade
or global editable-package remapping is needed. Source code stays pinned.
Checkpoint metadata/code are copied into a temporary view because the native
local loader may synchronize them; original large weights are only linked.
Each cell has its own cwd so native relative video paths cannot collide.

Run once after sourcing the deployed session:

    python -u -m egrs.official047 run-all --config-dir "$LNA047_CONFIG" --output "$LNA047_ROOT/runs/task047-official-three-suite-001"

Read-only progress (no model/native imports):

    python -m egrs.official047 progress --output "$LNA047_ROOT/runs/task047-official-three-suite-001"

Existing output is never reused. Errors preserve summaries, unfinished episode,
launch status and videos and stop subsequent cells. A partial run has no full
formal SR. Valid ordinary policy failures retain the native false outcome.
No automatic retries, changed initial states or score filtering.

CPU/fake tests execute an unchanged licensed upstream runner fixture with
fake dependencies plus tiny CPU LoRA tensors. They are software self-tests,
not an independent review or evidence of real model SR/physics performance.
