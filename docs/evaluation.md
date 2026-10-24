# Full EGRS + frozen OFT: fixed mask10 evaluation

The method-side `python -m egrs.evaluate` entry composes the trained selector with
the original OFT runtime for the existing 100 sources. Only `run` creates model
workers or a native environment. `plan`, `--help` and `inspect` are file-only.

Use the fixed eval core at 515e87d, not the annotation reference. Supply the old
mask10-accepted batch configuration and the original baseline run directory.
The baseline's recorded loaded asset/statistics identity is checked against the
new nested actor before any action; both suites keep the same SOG10 weights and
libero_10_no_noops statistics. LIBERO-90 remains a separately labelled zero-shot
extension. This entry does not modify core code, normalization, action chunks,
goal/violation measurements or success/distance metrics.

```json
{
  "format": "egrs.evaluation.config.v1",
  "core": {"root": "/path/to/clean/eval-core", "revision": "515e87d9b93ab838428791273a0f3020d6f56e9c"},
  "baseline_batch": "/path/to/existing/mask10-batch.json",
  "baseline_run": "/path/to/existing/baseline-run",
  "selector_config": "/path/to/selector.json",
  "selector_python": "/path/to/selector/env/bin/python",
  "checkpoint": "/path/to/selector-run/checkpoint-3",
  "checkpoint_state_sha256": "9ee11b8c28e9dbecd2f48b81762ea46bbe1eb38310ea0f0878b13ff241632867"
}
```

Install the same method wheel without dependencies in the controller, selector
and actor interpreters. Do not assume a controller PYTHONPATH propagates to the
isolated workers. The selector uses its pinned 3B base plus the selected LoRA;
the instruction-only registry, bounded original RGBs, generated evidence memory
and original-language fallback retain their existing behavior. No simulator
truth, mask or evaluator metric is provided to the policy. Lazy selector metadata
records its validated configured checkpoint, not a fabricated eager model load.

```bash
python -m egrs.evaluate plan --config evaluation.json --output plan.json
python -u -m egrs.evaluate run --config evaluation.json --output NEW_RUN_DIRECTORY
python -m egrs.evaluate inspect --run NEW_RUN_DIRECTORY --output NEW_REPORT_DIRECTORY
```

Plan confirms the accepted source files/checkpoint, never replays or rebuilds
states. Run preserves the exact ten tasks, init 0..9, H520/K4/chunk8, policy seed7,
and complete two-camera videos. It calls the original core runner and metrics;
there is no new scorer, STOP token or model-assisted evaluator.

Console and progress.json show completed episodes/100 and percent, the current
task/episode/query and initialization phase. Query is not called physical step.
The output contains plan/batch/task identities, original raw/evidence/videos,
per-episode method sidecars, summary.json, report.md and episodes.csv. Method and
selector identities are explicitly separate from the original actor identity;
the method is not mislabelled as a baseline run.

Technical errors stop the batch and retain the attempted episode and fixed
100-entry denominator; unstarted episodes remain missing. A task-level cleanup
failure is disclosed even when individual completed rollouts retain valid scores.
Missing/tampered video, sidecar, source or raw data is not scored as verified
success. No automatic retry, baseline substitution, source replacement, existing
directory overwrite or hidden resume occurs. New commands are user-started; do
not restart completed episodes without explicit new authorization.

Only affected CPU/fake tests are required for this delivery. Fake model/source
integration results are not real task success or physical source certification.
