#!/usr/bin/env bash
# User invokes this explicitly. No eval, retries, or implicit overwrites.
set -euo pipefail
lna043_phase=setup
trap 'lna043_exit=$?; if (( lna043_exit )); then printf "FAILED phase=%s exit=%s; preserve outputs, no retry/next arm\n" "$lna043_phase" "$lna043_exit" >&2; fi' EXIT
: "${LNA043_ROOT:?source the deployed session043.sh first}"
: "${LNA043_CODE:?}" "${LNA043_CONFIG:?}"
for arm in h0 h1; do
  if [[ -e "$LNA043_ROOT/runs/task043-$arm-train-001" ]]; then
    echo "Existing $arm run; preserve it. No automatic restart." >&2
    exit 2
  fi
done
if [[ -e "$LNA043_ROOT/annotations/task043/status-001" ]]; then
  echo "Existing status production; preserve it. Use explicit documented train commands if already ready." >&2
  exit 2
fi
mkdir "$LNA043_ROOT/runs/task043-train-launch-pathfix1"
cd "$LNA043_CODE"
echo "START status text; current recorded JSON only"
lna043_phase=prepare
python -u -m egrs.hint043 prepare \
  --index-dir "$LNA043_ROOT/data/coverage040/production-001/indices/task_control" \
  --output "$LNA043_ROOT/annotations/task043/status-001" \
  >> "$LNA043_ROOT/runs/task043-prepare-pathfix1.console.log" 2>&1
for arm in h0 h1; do
  lna043_phase="train-$arm"
  echo "START train $arm updates=1000 original_base=true"
  python -u -m egrs.hint043 train \
    --config "$LNA043_CONFIG/training.$arm.json" \
    --output "$LNA043_ROOT/runs/task043-$arm-train-001" \
    >> "$LNA043_ROOT/runs/task043-$arm-train-001.console.log" 2>&1
  test -f "$LNA043_ROOT/runs/task043-$arm-train-001/update-001000/identity.json"
  test -f "$LNA043_ROOT/runs/task043-$arm-train-001/selected_checkpoint.json"
  echo "COMPLETE train $arm"
done
echo "COMPLETE both; formal evaluation remains a separate user launch"
lna043_phase=complete
