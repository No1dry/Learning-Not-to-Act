#!/usr/bin/env bash
# User-launched orchestration only; unchanged039 C0/C1 algorithms and budgets.
set -eo pipefail
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/session039.sh
cd "$LNA039_CODE"

# Only check completion and duplicate launch; trainer owns data validation.
python - "$LNA039_PRODUCTION/preparation_report.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    report = json.load(stream)
if report.get('training_ready') is not True or report.get('new_qualified_train10', 0) <= 0:
    raise SystemExit('Preparation is not training-ready; no training was started.')
PY

for task039_arm in c0 c1; do
  if [[ -e "$LNA039_ROOT/runs/task039-$task039_arm-train-001" ]]; then
    echo "Refusing duplicate/overwrite: task039-$task039_arm-train-001 already exists." >&2
    exit 1
  fi
done
task039_launch="$LNA039_ROOT/runs/task039-parallel-001.launch"
# Atomic and retained even after failure: no silent retries or budget refunds.
if ! mkdir "$task039_launch"; then
  echo "Launch already reserved. Do not delete the marker or repeat training; inspect the existing logs." >&2
  exit 1
fi
echo "Starting C0 and C1 on GPU 0. No automatic evaluation or retries."
for task039_arm in c0 c1; do
  python -u -m egrs.coverage039 train --arm "$task039_arm" \
    --config "$LNA039_CODE/configs/task_control/task_control_factorization.json" \
    --runtime "$LNA039_RUNTIME" \
    --benchmark-root "$LNA039_CORE" \
    --index-dir "$LNA039_INDEX" \
    --output-dir "$LNA039_ROOT/runs/task039-$task039_arm-train-001" \
    >> "$LNA039_ROOT/runs/task039-$task039_arm-train-001.console.log" 2>&1 &
  task039_pid=$!
  echo "$task039_arm PID=$task039_pid"
  printf '%s %s\n' "$task039_arm" "$task039_pid" >> "$task039_launch/pids.txt"
  if [[ "$task039_arm" == c0 ]]; then
    task039_c0_pid=$task039_pid
  else
    task039_c1_pid=$task039_pid
  fi
done

task039_c0_status=0
task039_c1_status=0
wait "$task039_c0_pid" || task039_c0_status=$?
echo "C0 exit=$task039_c0_status"
wait "$task039_c1_pid" || task039_c1_status=$?
echo "C1 exit=$task039_c1_status"
printf 'c0=%s\nc1=%s\n' "$task039_c0_status" "$task039_c1_status" > "$task039_launch/exit_status.txt"
if [[ "$task039_c0_status" -ne 0 || "$task039_c1_status" -ne 0 ]]; then
  echo "At least one arm failed. Preserve outputs/ledgers; no automatic retry was performed." >&2
  exit 1
fi
echo "Both arms completed. Fixed final checkpoints: update-001000. Evaluation was not started."
