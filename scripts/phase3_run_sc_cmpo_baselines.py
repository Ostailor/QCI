#!/usr/bin/env python
"""Run a deterministic two-stage linear planning baseline on SC-CMPO payload metadata."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.system_level_projection import project_sc_cmpo_payload  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a deterministic robust LP upgrade baseline against the same SC-CMPO scenarios and costs."
    )
    parser.add_argument("--payload-dir", default="results/phase3/sc_cmpo/qci_payloads", help="SC-CMPO payload directory.")
    parser.add_argument(
        "--output-dir", default="results/phase3/sc_cmpo/baselines/robust_lp", help="Baseline result directory."
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing SC-CMPO baseline CSV files.")
    parser.add_argument("--dry-run", action="store_true", help="List payloads and planned solver calls without solving.")
    return parser


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def solve_payload(payload: dict[str, Any], payload_name: str) -> dict[str, Any]:
    """Solve the continuous shared upgrade problem for all recourse scenarios."""

    sc = payload["sc_cmpo"]
    patch = sc["upgrade_patch"]
    options = {option["technology"]: option for option in sc["upgrade_options"]}
    technologies = ("pv", "bess", "dispatchable_generation")
    costs = np.array([float(options[technology]["total_cost"]) for technology in technologies])
    load_kw = float(patch["load_kw"])
    existing_kw = float(patch["existing_generation_kw"])
    scenarios = payload["scenario_metadata"]["scenarios"]
    constraints: list[list[float]] = []
    rhs: list[float] = []
    for scenario in scenarios:
        if bool(scenario["pcc_available"]):
            continue
        existing = existing_kw if bool(scenario["existing_generation_available"]) else 0.0
        capacities = [
            float(options["pv"]["capacity_kw"]) if bool(scenario["pv_available"]) else 0.0,
            float(options["bess"]["power_kw"]),
            float(options["dispatchable_generation"]["capacity_kw"]),
        ]
        constraints.append([-value for value in capacities])
        rhs.append(-(load_kw - existing))
    started = time.perf_counter()
    result = linprog(costs, A_ub=constraints or None, b_ub=rhs or None, bounds=[(0.0, 1.0)] * 3, method="highs")
    runtime = time.perf_counter() - started
    fractions = result.x if result.success else np.zeros(3)
    values: dict[str, float] = {
        "upgrade_select_pv": float(fractions[0] > 1e-12),
        "upgrade_select_bess": float(fractions[1] > 1e-12),
        "upgrade_select_dispatchable": float(fractions[2] > 1e-12),
        "pv_capacity_fraction": float(fractions[0]),
        "bess_energy_fraction": float(fractions[1]),
        "bess_power_fraction": float(fractions[1]),
        "dispatchable_capacity_fraction": float(fractions[2]),
        "islanding_eligibility": 1.0,
        "base_mode_connected": 1.0,
        "base_mode_islanded": 0.0,
        "base_mode_restoration": 0.0,
        "bess_reserve_target": 1.0,
        "bess_soc_target": 1.0,
        "critical_load_priority": 1.0,
        "tie_pcc_reserve_target": 1.0,
    }
    for scenario in scenarios:
        name = str(scenario["name"])
        desired_mode = "restoration" if scenario["restoration_mode"] else "islanded" if scenario["forced_islanding"] else "connected"
        for mode in ("connected", "islanded", "restoration"):
            values[f"mode_{mode}[{name}]"] = float(mode == desired_mode)
        for action in ("charge", "hold", "discharge"):
            values[f"battery_action_{action}[{name}]"] = float(
                action == ("discharge" if not scenario["pcc_available"] and fractions[1] > 1e-12 else "hold")
            )
        existing_fraction = existing_kw / max(load_kw, 1e-9) if scenario["existing_generation_available"] else 0.0
        capacity_fraction = existing_fraction
        if scenario["pv_available"]:
            capacity_fraction += fractions[0] * float(options["pv"]["capacity_kw"]) / max(load_kw, 1e-9)
        capacity_fraction += fractions[1] * float(options["bess"]["power_kw"]) / max(load_kw, 1e-9)
        capacity_fraction += (
            fractions[2] * float(options["dispatchable_generation"]["capacity_kw"]) / max(load_kw, 1e-9)
        )
        der_dispatch = 0.0 if scenario["pcc_available"] else min(1.0, capacity_fraction)
        values[f"der_commitment[{name}]"] = der_dispatch
        values[f"der_capacity_slack[{name}]"] = max(0.0, capacity_fraction - der_dispatch) / 3.0
        values[f"critical_load_service[{name}]"] = 1.0
        values[f"tie_pcc_response[{name}]"] = float(bool(scenario["pcc_available"]))
        values[f"load_shedding_allocation[{name}]"] = 0.0
    projection = project_sc_cmpo_payload(payload, values)
    scenario_ens = {
        str(row["scenario"]): float(row["critical_energy_not_served_kwh"])
        for row in projection["scenario_results"]
    }
    feasible = bool(
        result.success
        and projection["feasibility_after_projection"]
        and float(projection["critical_energy_not_served_kwh"]) <= 1e-6
    )
    return {
        "payload_name": payload_name,
        "benchmark": sc["public_benchmark"],
        "method": "SC-CMPO robust LP metadata baseline",
        "status": "completed" if result.success else "failed",
        "failure_reason": "" if result.success else str(result.message),
        "feasibility_after_projection": feasible,
        "critical_energy_not_served_kwh": projection["critical_energy_not_served_kwh"],
        "critical_load_served_fraction": projection["critical_load_served_fraction"],
        "max_fraction_customers_unserved_per_hour": projection["max_fraction_customers_unserved_per_hour"],
        "total_hours_critical_infrastructure_unserved": projection[
            "total_hours_critical_infrastructure_unserved"
        ],
        "upgrade_cost": projection["upgrade_cost"],
        "runtime_seconds": runtime,
        "pre_repair_violation": projection["pre_repair_violation"],
        "post_repair_violation": projection["post_repair_violation"],
        "pv_capacity_fraction": float(fractions[0]),
        "bess_energy_fraction": float(fractions[1]),
        "bess_power_fraction": float(fractions[1]),
        "dispatchable_capacity_fraction": float(fractions[2]),
        "scenario_critical_ens_json": json.dumps(scenario_ens, sort_keys=True),
    }


def run_baselines(payload_dir: Path, output_dir: Path, *, overwrite: bool, dry_run: bool) -> dict[str, Any]:
    paths = sorted(payload_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no SC-CMPO payloads found under {payload_dir}")
    if dry_run:
        return {
            "dry_run": True,
            "payload_count": len(paths),
            "payloads": [str(path) for path in paths],
            "solver": "scipy.optimize.linprog(method='highs')",
        }
    targets = (output_dir / "repeat_metrics.csv", output_dir / "payload_summary.csv")
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError(f"baseline outputs already exist under {output_dir}; pass --overwrite")
    rows = [solve_payload(json.loads(path.read_text(encoding="utf-8")), path.name) for path in paths]
    _write_csv(rows, targets[0])
    _write_csv(rows, targets[1])
    return {
        "payload_count": len(rows),
        "completed": sum(row["status"] == "completed" for row in rows),
        "feasible": sum(bool(row["feasibility_after_projection"]) for row in rows),
        "repeat_metrics": str(targets[0]),
        "payload_summary": str(targets[1]),
    }


def main() -> None:
    args = build_parser().parse_args()
    result = run_baselines(Path(args.payload_dir), Path(args.output_dir), overwrite=args.overwrite, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
