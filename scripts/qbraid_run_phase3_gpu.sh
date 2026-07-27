#!/usr/bin/env bash
set -euo pipefail

PORTABLE_MANIFEST="${1:?portable manifest path required}"
OUTPUT_DIR="${2:?output directory required}"
CANDIDATE_COUNT="${3:-10000}"
CONFIG_PATH="${4:-configs/phase3_irc_cmpo_ieee123.yaml}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi is not available. CPU fallback must not be labeled as a GPU run." >&2
  exit 2
fi

nvidia-smi

python -m pip install --no-input --progress-bar off "cupy-cuda12x[ctk]" \
  || python -m pip install --no-input --progress-bar off --break-system-packages "cupy-cuda12x[ctk]"

python - "${PORTABLE_MANIFEST}" "${OUTPUT_DIR}" "${CANDIDATE_COUNT}" "${CONFIG_PATH}" <<'PY'
import subprocess
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
candidate_count = sys.argv[3]
config_path = Path(sys.argv[4])

subprocess.run(
    [
        sys.executable,
        str(Path("scripts") / "phase3_run_irc_cmpo_gpu_final.py"),
        "--manifest",
        str(manifest),
        "--output-dir",
        str(output_dir),
        "--candidate-count",
        str(candidate_count),
        "--config",
        str(config_path),
    ],
    check=True,
)
PY
