#!/usr/bin/env bash
# User explicitly launches in the existing simulation environment.
set -euo pipefail
lna043_phase=setup
trap 'lna043_exit=$?; if (( lna043_exit )); then printf "FAILED phase=%s exit=%s; preserve outputs, no retry/next arm\n" "$lna043_phase" "$lna043_exit" >&2; fi' EXIT
: "${LNA043_ROOT:?source session043.sh first}"
: "${LNA043_CODE:?}" "${LNA043_CONFIG:?}"
for arm in h0 h1; do
  test -f "$LNA043_ROOT/runs/task043-$arm-train-001/update-001000/identity.json"
  if [[ -e "$LNA043_ROOT/runs/task043-$arm-eval-001" ]]; then
    echo "Existing $arm eval; preserve outputs; no automatic restart." >&2
    exit 2
  fi
done
mkdir "$LNA043_ROOT/runs/task043-eval-launch-001"
cd "$LNA043_CODE"
for arm in h0 h1; do
  echo "START formal $arm: 10/00 each90, unhinted"
  lna043_phase="eval-$arm"
  python -u -m egrs.hint043 evaluate --arm "$arm" \
    --config "$LNA043_CONFIG/evaluation.$arm.json" \
    --output "$LNA043_ROOT/runs/task043-$arm-eval-001" \
    >> "$LNA043_ROOT/runs/task043-$arm-eval-001.console.log" 2>&1
  test -f "$LNA043_ROOT/runs/task043-$arm-eval-001/summary.json"
  echo "COMPLETE formal $arm"
done
echo "COMPLETE both formal evaluations"
lna043_phase=complete
