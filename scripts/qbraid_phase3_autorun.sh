#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${QBRAID_API_KEY:-}" ]]; then
  echo "ERROR: set QBRAID_API_KEY before running qBraid Phase 3 autorun." >&2
  exit 2
fi

python -m pip install --no-input --progress-bar off qbraid-core websocket-client \
  || python -m pip install --no-input --progress-bar off --break-system-packages qbraid-core websocket-client
python scripts/qbraid_phase3_autorun.py "$@"
