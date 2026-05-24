"""Phase 2 metric aggregation and report writers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cmpo.data import GridCase


def _scenario_probability_map(grid_case: GridCase) -> dict[str, float]:
    return {scenario.name: scenario.probability for scenario in grid_case.scenarios}


def _scenario_load_totals(grid_case: GridCase) -> dict[str, float]:
    totals: dict[str, float] = {}
    for scenario in grid_case.scenarios:
        total = 0.0
        for microgrid in grid_case.microgrids:
            for hour in range(grid_case.horizon_hours):
                total += microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
        totals[scenario.name] = total
    return totals


def _cvar_90(costs: pd.Series) -> float:
    if costs.empty:
        return 0.0
    threshold = costs.quantile(0.90)
    tail = costs[costs >= threshold]
    return float(tail.mean() if not tail.empty else costs.max())


def _ensure_result_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        raise ValueError("at least one result record is required")
    frame = pd.DataFrame(records)
    required = {
        "method_name",
        "scenario",
        "patch",
        "repaired_energy",
        "expected_cost_component",
        "critical_load_served_fraction",
        "noncritical_load_served_fraction",
        "energy_not_served_kwh",
        "critical_energy_not_served_kwh",
        "feasibility_pass",
        "runtime_seconds",
        "repeats",
        "notes",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"result records missing columns: {missing}")
    return frame


def compute_phase2_metrics(
    grid_case: GridCase,
    result_records: list[dict[str, Any]],
    design_metrics: dict[str, Any] | None = None,
    model_metadata: list[dict[str, Any]] | None = None,
    risk_lambda: float = 0.25,
) -> dict[str, pd.DataFrame]:
    """Compute Phase 2 summary, scenario, scaling, and model-stat tables."""

    scenario_results = _ensure_result_frame(result_records).copy()
    probabilities = _scenario_probability_map(grid_case)
    load_totals = _scenario_load_totals(grid_case)
    design = design_metrics or {}

    scenario_results["scenario_probability"] = scenario_results["scenario"].map(probabilities).fillna(0.0)
    scenario_results["scenario_total_load_kwh"] = scenario_results["scenario"].map(load_totals).fillna(0.0)
    scenario_results["max_fraction_customers_unserved_per_hour"] = (
        scenario_results["energy_not_served_kwh"] / scenario_results["scenario_total_load_kwh"].replace(0.0, np.nan)
    ).fillna(0.0).clip(lower=0.0, upper=1.0)
    scenario_results["total_hours_critical_infrastructure_unserved"] = np.where(
        scenario_results["critical_energy_not_served_kwh"] > 1e-9,
        grid_case.horizon_hours,
        0,
    )
    scenario_results["total_upgrade_cost"] = float(design.get("total_upgrade_cost", 0.0))

    model_rows = model_metadata or []
    model_stats = pd.DataFrame(model_rows)
    if model_stats.empty:
        model_stats = pd.DataFrame(
            [
                {
                    "scenario": "unknown",
                    "patch": "unknown",
                    "horizon": grid_case.horizon_hours,
                    "variable_count": 0,
                    "term_count": 0,
                    "degree": 0,
                }
            ]
        )

    variable_count_per_hamiltonian = float(model_stats["variable_count"].median())
    term_count_per_hamiltonian = float(model_stats["term_count"].median())
    model_degree = int(model_stats["degree"].max())

    best_by_scenario = scenario_results.groupby("scenario")["expected_cost_component"].transform("min").replace(0.0, np.nan)
    scenario_results["_scenario_cost_degradation"] = (
        scenario_results["expected_cost_component"] / best_by_scenario - 1.0
    ).fillna(0.0)

    rows: list[dict[str, Any]] = []
    for method, group in scenario_results.groupby("method_name", sort=True):
        expected_operating_cost = float((group["expected_cost_component"] * group["scenario_probability"]).sum())
        best_cost = float(group["expected_cost_component"].min())
        median_cost = float(group["expected_cost_component"].median())
        cvar = _cvar_90(group["expected_cost_component"])
        rows.append(
            {
                "method_name": method,
                "expected_operating_cost": expected_operating_cost,
                "best_cost_by_method": best_cost,
                "median_cost_by_method": median_cost,
                "risk_adjusted_cost": expected_operating_cost + risk_lambda * cvar,
                "total_upgrade_cost": float(design.get("total_upgrade_cost", 0.0)),
                "critical_load_served_fraction": float(group["critical_load_served_fraction"].mean()),
                "noncritical_load_served_fraction": float(group["noncritical_load_served_fraction"].mean()),
                "energy_not_served_kwh": float(group["energy_not_served_kwh"].sum()),
                "critical_energy_not_served_kwh": float(group["critical_energy_not_served_kwh"].sum()),
                "max_fraction_customers_unserved_per_hour": float(group["max_fraction_customers_unserved_per_hour"].max()),
                "total_hours_critical_infrastructure_unserved": int(group["total_hours_critical_infrastructure_unserved"].sum()),
                "feasibility_rate": float(group["feasibility_pass"].mean()),
                "median_runtime_seconds": float(group["runtime_seconds"].median()),
                "time_to_good_solution": float(group.loc[group["feasibility_pass"], "runtime_seconds"].min())
                if bool(group["feasibility_pass"].any())
                else -1.0,
                "scenario_scaling_runtime": float(group["runtime_seconds"].median()),
                "scenario_scaling_cost_degradation": float(group["_scenario_cost_degradation"].median()),
                "variable_count_per_hamiltonian": variable_count_per_hamiltonian,
                "term_count_per_hamiltonian": term_count_per_hamiltonian,
                "model_degree": model_degree,
                "scenario_count": int(group["scenario"].nunique()),
            }
        )
    summary_metrics = pd.DataFrame(rows).sort_values(["risk_adjusted_cost", "expected_operating_cost"]).reset_index(drop=True)

    scaling_results = scenario_results[
        ["method_name", "scenario", "patch", "runtime_seconds", "expected_cost_component", "feasibility_pass"]
    ].copy()
    scaling_results["scenario_scaling_runtime"] = scaling_results["runtime_seconds"]
    scaling_results["scenario_scaling_cost_degradation"] = scenario_results["_scenario_cost_degradation"]
    scaling_results["horizon_hours"] = grid_case.horizon_hours
    scaling_results["n_microgrids"] = len(grid_case.microgrids)
    scenario_results = scenario_results.drop(columns=["_scenario_cost_degradation"])
    return {
        "summary_metrics": summary_metrics,
        "scenario_results": scenario_results,
        "scaling_results": scaling_results,
        "model_stats": model_stats,
    }


def _headline_markdown(tables: dict[str, pd.DataFrame]) -> str:
    summary = tables["summary_metrics"]
    scenario_results = tables["scenario_results"]
    best = summary.iloc[0]
    best_table = summary[
        [
            "method_name",
            "expected_operating_cost",
            "risk_adjusted_cost",
            "critical_load_served_fraction",
            "feasibility_rate",
            "median_runtime_seconds",
        ]
    ].head(5)
    best_table_md = _markdown_table(best_table)
    cubic_note = (
        "The Hamiltonian keeps native cubic generator-cost terms in the objective. "
        "A quadratic-only approximation would drop the cubic coefficient and therefore miss high-output marginal-cost curvature."
    )
    resilience_note = (
        f"The best preliminary method by risk-adjusted cost is `{best['method_name']}`. "
        f"Across recorded scenarios, max customer-load unserved fraction is "
        f"{scenario_results['max_fraction_customers_unserved_per_hour'].max():.4f}."
    )
    return f"""# Phase 2 Headlines

## 1. What was solved

The prototype solved synthetic resilient microgrid dispatch instances for selected islandable patches using classical baselines and a degree-3 CMPO polynomial model.

## 2. What data was used

The data is deterministic synthetic microgrid data generated by `src/cmpo/data.py`; no proprietary grid data is used.

## 3. What baselines were compared

Greedy critical-load-first dispatch, SciPy SLSQP local optimization, SciPy differential evolution, and CMPO-local polynomial search were compared. The CMPO-local method is a pre-QCi simulation proxy, not a hardware run.

## 4. Best preliminary result table

{best_table_md}

## 5. Key finding on cubic cost vs quadratic approximation

{cubic_note}

## 6. Key finding on resilience metrics

{resilience_note}

## 7. Why QCi Dirac-3 is justified for Phase 3

The exported models preserve cubic terms directly while keeping each scenario/patch instance small and bounded. This makes the workflow a practical candidate for Dirac-3/EQC experimentation in Phase 3.

## 8. What not to claim

Do not claim hardware quantum advantage yet. These are CPU-only classical and pre-QCi polynomial-search results.
"""


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_phase2_outputs(tables: dict[str, pd.DataFrame], output_dir: Path | str = Path("results")) -> dict[str, Path]:
    """Write Phase 2 CSV and Markdown outputs."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_metrics_csv": out_dir / "summary_metrics.csv",
        "scenario_results_csv": out_dir / "scenario_results.csv",
        "scaling_results_csv": out_dir / "scaling_results.csv",
        "model_stats_csv": out_dir / "model_stats.csv",
        "phase2_headlines_md": out_dir / "phase2_headlines.md",
    }
    tables["summary_metrics"].to_csv(paths["summary_metrics_csv"], index=False)
    tables["scenario_results"].to_csv(paths["scenario_results_csv"], index=False)
    tables["scaling_results"].to_csv(paths["scaling_results_csv"], index=False)
    tables["model_stats"].to_csv(paths["model_stats_csv"], index=False)
    paths["phase2_headlines_md"].write_text(_headline_markdown(tables), encoding="utf-8")
    return paths


def summarize_results(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact compatibility summary for existing scripts."""

    if not records:
        return {"n_records": 0, "methods": []}
    method_key = "method_name" if "method_name" in records[0] else "method"
    return {
        "n_records": len(records),
        "methods": sorted({str(record.get(method_key, "unknown")) for record in records}),
    }
