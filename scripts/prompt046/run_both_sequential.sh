#!/usr/bin/env bash
set -euo pipefail
: "${LNA046_ROOT:?source session046.sh first}"
: "${LNA046_CONFIG:?source session046.sh first}"
python -u -m egrs.prompt046 run-both \
  --p1-config "$LNA046_CONFIG/evaluation.p1.json" \
  --p2-config "$LNA046_CONFIG/evaluation.p2.json" \
  --p1-output "$LNA046_ROOT/runs/task046-p1-eval-001" \
  --p2-output "$LNA046_ROOT/runs/task046-p2-eval-001" \
  --marker "$LNA046_ROOT/launches/task046-p1-p2-001"
