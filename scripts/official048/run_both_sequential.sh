#!/usr/bin/env bash
set -euo pipefail
: "$LNA048_CONFIG" "$LNA048_ROOT"
exec python -u -m egrs.official048 run-all \
  --config-dir "$LNA048_CONFIG" \
  --output "$LNA048_ROOT/runs/task048-official-libero10-001"
