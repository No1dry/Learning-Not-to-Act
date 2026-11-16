#!/usr/bin/env bash
# User-started only. Each new process must finish formal90 before the next arm.
set -euo pipefail
: "${LNA_P1_CONFIG:?Set the prepared P1 evaluation JSON path}"
: "${LNA_P2_CONFIG:?Set the prepared P2 evaluation JSON path}"
: "${LNA_P1_OUTPUT:?Set a new P1 output directory}"
: "${LNA_P2_OUTPUT:?Set a new P2 output directory}"
: "${LNA_044_MARKER:?Set a new persistent launch marker directory}"
exec "${LNA_PYTHON:-python}" -u -m egrs.prompt044 run-both \
  --p1-config "$LNA_P1_CONFIG" --p2-config "$LNA_P2_CONFIG" \
  --p1-output "$LNA_P1_OUTPUT" --p2-output "$LNA_P2_OUTPUT" \
  --marker "$LNA_044_MARKER"
