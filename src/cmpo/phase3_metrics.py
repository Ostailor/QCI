"""Phase 3 metric aggregation for QCi and classical result sweeps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cmpo.data import GridCase


def scenario_probability_map(grid_case: GridCase) -> dict[str, float]:
    """Return scenario probability by scenario name."""

    return {scenario.name: scenario.probability for scenario in grid_case.scenarios}


def scenario_load_totals(grid_case: GridCase) -> dict[str, float]:
    """Return total load by scenario across all microgrids and hours."""

    totals: dict[str, float] = {}
    for scenario in grid_case.scenarios:
        total = 0.0
        for microgrid in grid_case.microgrids:
            for hour in range(grid_case.horizon_hours):
                total += microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
        totals[scenario.name] = total
    return totals


def add_phase3_columns(
    rows: list[dict[str, Any]] | pd.DataFrame,
    grid_case: GridCase,
    *,
    dataset_name: str,
    total_upgrade_cost: float = 0.0,
) -> pd.DataFrame:
    """Normalize Phase 3 rows and add judge-facing metric columns."""

    frame = pd.DataFrame(rows).copy()
    if frame.empty:
        return pd.DataFrame()

    probabilities = scenario_probability_map(grid_case)
    load_totals = scenario_load_totals(grid_case)
    frame["dataset"] = frame.get("dataset", dataset_name)
    frame["scenario_probability"] = frame["scenario"].map(probabilities).fillna(0.0)
    frame["scenario_total_load_kwh"] = frame["scenario"].map(load_totals).fillna(0.0)
    frame["total_upgrade_cost"] = float(total_upgrade_cost)
    if "wall_clock_runtime_seconds" not in frame.columns:
        frame["wall_clock_runtime_seconds"] = frame.get("runtime_seconds", 0.0)
    if "repeat" not in frame.columns:
        frame["repeat"] = 0
    if "backend" not in frame.columns:
        frame["backend"] = "classical"

    frame["max_fraction_customers_unserved_per_hour"] = (
        frame["energy_not_served_kwh"] / frame["scenario_total_load_kwh"].replace(0.0, np.nan)
    ).fillna(0.0).clip(lower=0.0, upper=1.0)
    frame["total_hours_critical_infrastructure_unserved"] = np.where(
        frame["critical_energy_not_served_kwh"] > 1e-9,
        grid_case.horizon_hours,
        0,
    )
    frame["critical_load_served_fraction"] = frame["critical_load_served_fraction"].clip(lower=0.0, upper=1.0)
    return frame


def summarize_phase3_results(frame: pd.DataFrame, risk_lambda: float = 0.25) -> pd.DataFrame:
    """Aggregate repeated Phase 3 rows into method-level comparison metrics."""

    if frame.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for (dataset, method), group in frame.groupby(["dataset", "method_name"], sort=True):
        expected_cost = float((group["expected_cost_component"] * group["scenario_probability"]).sum())
        cvar_threshold = group["expected_cost_component"].quantile(0.90)
        cvar = float(group.loc[group["expected_cost_component"] >= cvar_threshold, "expected_cost_component"].mean())
        feasible = group[group["feasibility_pass"].astype(bool)]
        rows.append(
            {
                "dataset": dataset,
                "method_name": method,
                "expected_operating_cost": expected_cost,
                "best_cost_by_method": float(group["expected_cost_component"].min()),
                "median_cost_by_method": float(group["expected_cost_component"].median()),
                "risk_adjusted_cost": expected_cost + risk_lambda * cvar,
                "total_upgrade_cost": float(group["total_upgrade_cost"].max()),
                "max_fraction_customers_unserved_per_hour": float(group["max_fraction_customers_unserved_per_hour"].max()),
                "total_hours_critical_infrastructure_unserved": int(
                    group["total_hours_critical_infrastructure_unserved"].sum()
                ),
                "critical_load_served_fraction": float(group["critical_load_served_fraction"].mean()),
                "critical_energy_not_served_kwh": float(group["critical_energy_not_served_kwh"].sum()),
                "energy_not_served_kwh": float(group["energy_not_served_kwh"].sum()),
                "feasibility_after_repair": float(group["feasibility_pass"].mean()),
                "wall_clock_runtime_seconds": float(group["wall_clock_runtime_seconds"].sum()),
                "median_runtime_seconds": float(group["runtime_seconds"].median()),
                "time_to_good_solution": float(feasible["runtime_seconds"].min()) if not feasible.empty else -1.0,
                "repeat_count": int(group["repeat"].nunique()),
                "scenario_count": int(group["scenario"].nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "risk_adjusted_cost", "expected_operating_cost"]).reset_index(drop=True)


def qci_repeat_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute repeat-distribution statistics for QCi rows."""

    if frame.empty:
        return pd.DataFrame()
    qci = frame[frame["backend"].astype(str).str.contains("qci|mock|dirac", case=False, regex=True)]
    if qci.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for keys, group in qci.groupby(["dataset", "scenario", "patch", "method_name"], sort=True):
        dataset, scenario, patch, method = keys
        costs = group["expected_cost_component"]
        rows.append(
            {
                "dataset": dataset,
                "scenario": scenario,
                "patch": patch,
                "method_name": method,
                "repeat_count": int(len(group)),
                "best_cost": float(costs.min()),
                "median_cost": float(costs.median()),
                "p10_cost": float(costs.quantile(0.10)),
                "p90_cost": float(costs.quantile(0.90)),
                "std_cost": float(costs.std(ddof=0)),
                "best_critical_load_served_fraction": float(group["critical_load_served_fraction"].max()),
                "median_runtime_seconds": float(group["runtime_seconds"].median()),
                "feasibility_rate": float(group["feasibility_pass"].mean()),
            }
        )
    return pd.DataFrame(rows)


def write_phase3_metric_outputs(frame: pd.DataFrame, output_dir: Path | str) -> dict[str, Path]:
    """Write normalized rows, summary metrics, and QCi repeat distribution."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "combined_results_csv": out_dir / "combined_results.csv",
        "summary_metrics_csv": out_dir / "summary_metrics.csv",
        "qci_repeat_distribution_csv": out_dir / "qci_repeat_distribution.csv",
    }
    frame.to_csv(paths["combined_results_csv"], index=False)
    summarize_phase3_results(frame).to_csv(paths["summary_metrics_csv"], index=False)
    qci_repeat_distribution(frame).to_csv(paths["qci_repeat_distribution_csv"], index=False)
    return paths
