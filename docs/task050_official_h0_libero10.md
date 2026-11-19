# 050: H0@3000 on official LIBERO-10, exactly500 new episodes

User approved H0 first: ten tasks including task5, each50 official initial
states0..49, same complete task instruction, native520 horizon /10 wait /chunk8 /
policy seed7 /env seed0 /two RGB+proprio /crop /libero_10_no_noops as048.
Official env.done, full videos and per-episode live SR. No Remain score, hints,
new training/data generation, scale changes, original/H1 reruns or extra seeds.

Fixed original045 H0@3000 SHA:
`e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20`.
H0 is the matched no-status-text training arm, not the official base or H1.
The separate050 schema allows onlyh0/libero_10/total500. Original047/048 scopes
and H1 identity stay strict. H0 reuses the exact existing tensor/RNG/native
LoRA loader after explicit H0 checks; no relabelled identity or edited weights.

The user activates the existing conda/simulation environment and deployed
session050, then starts one ordinary Python command:

~~~bash
python -u -m egrs.official050 run --config CONFIG --output NEW_OUTPUT
~~~

The run refuses existing output. Original native episodes/actions/videos run
unchanged; no model or physics preflight is required. Final summary contains
500 official results and ten per-task aggregates, ready to compare against
existing048 original94.80%/H1 88.80% with no repeat of those1000 trajectories.
Metadata/progress use realh0, noth1. Natural model-query ceiling32500.
Technical errors retain partial evidence, not false policy-failure scores.
Only the user starts the real500; Codex prepares/tests/deploys. No automatic
merge, dependency upgrades, cleanup, or interruption of other user work.
