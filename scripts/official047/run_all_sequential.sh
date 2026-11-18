#!/usr/bin/env bash
set -euo pipefail
: "$LNA047_CONFIG" "$LNA047_ROOT"
exec python -u -m egrs.official047 run-all \
  --config-dir "$LNA047_CONFIG" \
  --output "$LNA047_ROOT/runs/task047-official-three-suite-001"
