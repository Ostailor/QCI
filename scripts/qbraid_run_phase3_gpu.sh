#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/phase3_qci_small.yaml}"
REPEATS="${2:-50}"
QBRAID_CONFIG="${QBRAID_CONFIG:-results/phase3/qbraid_gpu_only_config.yaml}"

echo "qBraid Phase 3 GPU baseline entrypoint"
echo "Config: ${CONFIG}"
echo "Repeats: ${REPEATS}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi is not available. Launch this repository from a qBraid GPU instance, not a CPU Lab instance." >&2
  exit 2
fi

nvidia-smi

python -m pip install --no-input --progress-bar off --break-system-packages "cupy-cuda12x[ctk]"

python - <<'PY'
import importlib.util

if importlib.util.find_spec("torch") is not None:
    import torch
    print("torch.cuda.is_available =", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("torch.cuda.device =", torch.cuda.get_device_name(0))
        raise SystemExit(0)

if importlib.util.find_spec("cupy") is not None:
    import cupy as cp
    print("cupy.cuda.device_count =", cp.cuda.runtime.getDeviceCount())
    if cp.cuda.runtime.getDeviceCount() > 0:
        raise SystemExit(0)

raise SystemExit("ERROR: no CUDA-enabled torch or cupy backend is available in this qBraid environment.")
PY

python - "${CONFIG}" "${QBRAID_CONFIG}" <<'PY'
from pathlib import Path
import sys

import yaml

source = Path(sys.argv[1])
target = Path(sys.argv[2])
config = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
config["name"] = f"{config.get('name', source.stem)}_qbraid_gpu"
base_output = Path(config.get("output_dir", f"results/phase3/{source.stem}"))
config["output_dir"] = str(base_output.with_name(f"{base_output.name}_qbraid_gpu"))
baselines = config.setdefault("baselines", {})
baselines.update(
    {
        "include_greedy": False,
        "include_slsqp": False,
        "include_differential_evolution": False,
        "include_cmpo_local": False,
        "include_piecewise_milp": False,
        "include_qubo_quadratized": False,
        "include_gpu_random_restart": True,
        "include_ipopt_pyomo": False,
        "include_stress_reserve": False,
        "gpu_restarts": max(int(baselines.get("gpu_restarts", 0) or 0), 512),
        "gpu_local_steps": 0,
    }
)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
print(target)
PY

python scripts/phase3_prepare_payloads.py --config "${QBRAID_CONFIG}"
python scripts/phase3_run_gpu_baselines.py --config "${QBRAID_CONFIG}" --repeats "${REPEATS}"
