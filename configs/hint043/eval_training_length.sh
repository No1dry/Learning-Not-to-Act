#!/usr/bin/env bash
# User starts the four fixed snapshots, each original10/00=90/90. No training.
set -euo pipefail
: "${LNA045_ROOT:?source session045.sh}" "${LNA045_CODE:?}" "${LNA045_CONFIG:?}"
phase=setup
trap 'code=$?; if (( code )); then echo "FAILED $phase exit=$code; preserve outputs; no retry/next snapshot" >&2; fi' EXIT
for step in 2000 3000; do
  for arm in h0 h1; do
    test -f "$LNA045_ROOT/runs/task045-$arm-train-001/update-00$step/identity.json"
    if [[ -e "$LNA045_ROOT/runs/task045-$arm-step$step-eval-001" ]]; then
      echo "Existing evaluation; do not repeat." >&2; exit 2
    fi
  done
done
mkdir "$LNA045_ROOT/launches/task045-eval-001"
cd "$LNA045_CODE"
for step in 2000 3000; do
  for arm in h0 h1; do
    phase="eval-$arm-$step"
    echo "START formal $arm step$step: original10/00 each90"
    python -u -m egrs.hint043 evaluate \
      --config "$LNA045_CONFIG/evaluation.$arm.step$step.json" \
      --arm "$arm" --checkpoint-step "$step" \
      --output "$LNA045_ROOT/runs/task045-$arm-step$step-eval-001"
    test -f "$LNA045_ROOT/runs/task045-$arm-step$step-eval-001/summary.json"
    echo "COMPLETE formal $arm step$step"
  done
done
phase=complete
echo "COMPLETE four formal evaluations total720"
