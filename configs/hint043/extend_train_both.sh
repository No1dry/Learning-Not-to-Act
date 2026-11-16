#!/usr/bin/env bash
# User starts the two full-state continuations. No automatic evaluation/retry.
set -euo pipefail
: "${LNA045_ROOT:?source session045.sh}" "${LNA045_CODE:?}" "${LNA045_CONFIG:?}"
phase=setup
trap 'code=$?; if (( code )); then echo "FAILED $phase exit=$code; preserve all outputs; no retry/next arm" >&2; fi' EXIT
for arm in h0 h1; do
  test -f "$LNA045_ROOT/runs/task043-$arm-train-001/update-001000/training_state.pt"
  if [[ -e "$LNA045_ROOT/runs/task045-$arm-train-001" ]]; then
    echo "Existing $arm output; preserve it and do not restart." >&2; exit 2
  fi
done
mkdir "$LNA045_ROOT/launches/task045-train-001"
cd "$LNA045_CODE"
for arm in h0 h1; do
  phase="train-$arm"
  echo "START $arm full-state1000 ->3000; fixed evaluation snapshots2000/3000"
  python -u -m egrs.hint043 train \
    --config "$LNA045_CONFIG/training.$arm.json" \
    --output "$LNA045_ROOT/runs/task045-$arm-train-001" \
    --target-updates 3000 \
    --init-from "$LNA045_ROOT/runs/task043-$arm-train-001/update-001000"
  for step in 002000 003000; do
    test -f "$LNA045_ROOT/runs/task045-$arm-train-001/update-$step/identity.json"
  done
  echo "COMPLETE train $arm"
done
phase=complete
echo "COMPLETE both training continuations; user launches evaluation separately"
