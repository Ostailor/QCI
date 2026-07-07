"""IEEE distribution feeder benchmark bridge for Phase 3."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from cmpo.benchmark_registry import DATA_PUBLIC_ROOT, PHASE3_PUBLIC_ROOT


IEEE_DATA_DIR = DATA_PUBLIC_ROOT / "ieee_distribution"
IEEE_RESULT_DIR = PHASE3_PUBLIC_ROOT / "ieee_distribution"


BRIDGE_SCRIPT = """# PowerModelsDistribution bridge placeholder for CMPO Phase 3
#
# Usage after installing Julia + PowerModelsDistribution:
#   julia data/public_benchmarks/ieee_distribution/powermodels_distribution_bridge.jl path/to/Master.dss
#
# This script intentionally stays lightweight in the Python repo. It records the
# expected bridge entrypoint so judges can connect IEEE OpenDSS feeders without
# changing the CMPO benchmark ladder.

using JSON

function main()
    if length(ARGS) < 1
        error("Pass an OpenDSS feeder Master.dss path")
    end
    feeder = ARGS[1]
    out = Dict(
        "source_file" => feeder,
        "bridge" => "PowerModelsDistribution/OpenDSS",
        "cmpo_transformation" => [
            "parse feeder buses/lines/loads/regulators",
            "select candidate microgrid/PCC buses deterministically",
            "add seeded CMPO PV/BESS/critical-load overlays",
            "export CMPO payload input YAML/JSON"
        ]
    )
    println(JSON.json(out))
end

main()
"""


def discover_distribution_files(data_dir: Path = IEEE_DATA_DIR) -> list[Path]:
    if not data_dir.exists():
        return []
    suffixes = {".dss", ".json", ".m", ".csv"}
    return sorted(path for path in data_dir.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def write_distribution_bridge_and_status(
    data_dir: Path = IEEE_DATA_DIR,
    result_dir: Path = IEEE_RESULT_DIR,
) -> dict[str, Any]:
    """Write feeder bridge script plus explicit available/missing benchmark status."""

    data_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = data_dir / "powermodels_distribution_bridge.jl"
    bridge_path.write_text(BRIDGE_SCRIPT, encoding="utf-8")
    files = [path for path in discover_distribution_files(data_dir) if path != bridge_path]
    if files:
        sample = files[0]
        bridge_copy = result_dir / "powermodels_distribution_bridge.jl"
        shutil.copy2(bridge_path, bridge_copy)
        status = {
            "benchmark": "ieee_distribution",
            "status": "available",
            "source_name": "IEEE distribution feeder OpenDSS/PowerModelsDistribution-compatible data",
            "upstream_url": "https://github.com/tshort/OpenDSS",
            "license": "Depends on selected feeder source",
            "version": "local public feeder file",
            "local_path": str(sample),
            "qci_execution_was_run": False,
            "only_classical_baselines_were_run": False,
            "transformation_notes": "Distribution feeder bridge available; CMPO overlay required before payload export.",
            "fields_inherited_from_benchmark": ["buses", "lines", "loads", "transformers/regulators"],
            "fields_added_by_cmpo_adapter": [
                "critical_load_fraction",
                "BESS_capacity_and_power_limits",
                "PV_DER_profile",
                "PCC_tie_availability",
                "islanding_mode_eligibility",
                "restoration_scenario_tags",
            ],
            "bridge_script": str(bridge_copy),
        }
    else:
        status = {
            "benchmark": "ieee_distribution",
            "status": "benchmark_missing",
            "source_name": "IEEE 13/34/123-bus distribution feeder public data",
            "upstream_url": "https://github.com/tshort/OpenDSS",
            "missing_file": "IEEE13/IEEE34/IEEE123 OpenDSS Master.dss or equivalent feeder data",
            "command": "Place feeder files under data/public_benchmarks/ieee_distribution/ and rerun python scripts/phase3_validate_benchmark_ladder.py",
            "reason": "No OpenDSS/PowerModelsDistribution-compatible feeder files found.",
            "bridge_script": str(bridge_path),
            "transformation_notes": "Benchmark missing report is explicit; this path is not silently skipped.",
        }
        (result_dir / "benchmark_missing.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        (result_dir / "benchmark_missing.md").write_text(
            "# IEEE Distribution Benchmark Missing\n\n"
            f"- Missing file: {status['missing_file']}\n"
            f"- Command to complete: {status['command']}\n"
            f"- Bridge script: {bridge_path}\n",
            encoding="utf-8",
        )
    (result_dir / "benchmark_provenance.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status
