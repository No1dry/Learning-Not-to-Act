#!/usr/bin/env bash
# User starts this launcher. Reuse unchanged039/038 formal evaluation, sequentially.
set -eo pipefail
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/session039.sh
cd "$LNA039_CORE"

for task039_arm in c0 c1; do
  if [[ -e "$LNA039_ROOT/runs/task039-$task039_arm-eval-001" ]]; then
    echo "Refusing duplicate/overwrite: task039-$task039_arm-eval-001 already exists." >&2
    exit 1
  fi
  test -s "$LNA039_ROOT/runs/task039-$task039_arm-train-001/update-001000/identity.json"
  test -s "$LNA039_ROOT/runs/task039-$task039_arm-train-001/update-001000/adapter.pt"
done
task039_launch="$LNA039_ROOT/runs/task039-eval-both-001.launch"
if ! mkdir "$task039_launch"; then
  echo "Evaluation launch already reserved; preserve marker/results and inspect, do not repeat." >&2
  exit 1
fi

for task039_arm in c0 c1; do
  echo "Starting $task039_arm formal evaluation: 10 x90 + 00 x90; all videos."
  if python -u -m egrs.coverage039 eval --arm "$task039_arm" --mode run \
    --config "$LNA039_CONFIG/evaluation.$task039_arm.json" \
    --out "$LNA039_ROOT/runs/task039-$task039_arm-eval-001" \
    >> "$LNA039_ROOT/runs/task039-$task039_arm-eval-001.console.log" 2>&1; then
    if [[ ! -s "$LNA039_ROOT/runs/task039-$task039_arm-eval-001/summary.json" ]]; then
      echo "$task039_arm returned without a formal summary; do not start another arm." >&2
      exit 1
    fi
    echo "$task039_arm completed including formal report."
    printf '%s=0\n' "$task039_arm" >> "$task039_launch/exit_status.txt"
  else
    task039_status=$?
    printf '%s=%s\n' "$task039_arm" "$task039_status" >> "$task039_launch/exit_status.txt"
    echo "$task039_arm failed; preserve all outputs/ledgers. No retry or next arm was started." >&2
    exit "$task039_status"
  fi
done
echo "Both formal evaluations completed. No training, state regeneration or additional report job was started."
