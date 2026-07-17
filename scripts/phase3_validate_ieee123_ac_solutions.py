#!/usr/bin/env python
"""Run unbalanced OpenDSS validation for every budget-frontier system plan."""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cmpo.ieee123_ac_validation import copy_pinned_feeder, validate_ieee123_scenario  # noqa: E402
from cmpo.ieee123_sc_cmpo_adapter import parse_ieee123_sc_cmpo_case  # noqa: E402
from cmpo.scenario_coupled_model import load_sc_cmpo_config  # noqa: E402


QCI_METHOD = "QCi SC-CMPO"
DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123.yaml")
DEFAULT_BUDGET_DIR = Path("results/phase3/sc_cmpo/budget_frontier")
DEFAULT_OUTPUT_DIR = Path("results/phase3/sc_cmpo/ac_validation")
RESULT_FILE = "ac_validation_results.csv"
FRONTIER_FILE = "ac_valid_budget_frontier.csv"
SUMMARY_FILE = "ac_validation_summary.md"
FIGURES = (
    "voltage_profiles.png",
    "losses_by_method.png",
    "ac_valid_cost_resilience_frontier.png",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _natural_bus_key(value: str) -> tuple[int, str]:
    try:
        return int(value), value
    except ValueError:
        return sys.maxsize, value


def _critical_nodes(payload_dir: Path) -> set[str]:
    paths = sorted(payload_dir.glob("*.json"))
    if len(paths) != 12:
        raise ValueError(f"AC validation requires the same 12 IEEE123 payloads, found {len(paths)}")
    critical: set[str] = set()
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        critical.update(str(node) for node in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])
    return critical


def _headline_rows(budget_dir: Path) -> pd.DataFrame:
    table_path = budget_dir / "table_budget_matched_results.csv"
    if not table_path.is_file():
        raise FileNotFoundError(table_path)
    frame = pd.read_csv(table_path)
    required = {"budget_id", "budget", "method", "system_trace_id", "trace_path"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"budget table lacks AC trace fields: {sorted(missing)}")
    if frame.duplicated(["budget_id", "method"]).any():
        raise ValueError("budget table has duplicate method/budget headline plans")
    missing_traces = [str(path) for path in frame["trace_path"] if not Path(str(path)).is_file()]
    if missing_traces:
        raise FileNotFoundError(f"missing system traces: {missing_traces[:3]}")
    return frame.sort_values(["budget", "method"]).reset_index(drop=True)


def aggregate_ac_validation(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scenario validation into a conservative system-plan gate."""

    group_keys = ["budget_id", "budget", "method"]
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(group_keys, sort=True, dropna=False):
        rows.append(
            {
                **dict(zip(group_keys, keys, strict=True)),
                "ac_scenario_count": int(len(group)),
                "ac_valid_scenario_count": int(group["ac_valid"].fillna(False).astype(bool).sum()),
                "ac_valid": bool(group["ac_valid"].fillna(False).astype(bool).all()),
                "all_scenarios_converged": bool(group["converged"].fillna(False).astype(bool).all()),
                "minimum_voltage_pu": pd.to_numeric(group["minimum_voltage_pu"], errors="coerce").min(),
                "maximum_voltage_pu": pd.to_numeric(group["maximum_voltage_pu"], errors="coerce").max(),
                "voltage_violation_count": int(
                    pd.to_numeric(group["voltage_violation_count"], errors="coerce").fillna(0).sum()
                ),
                "mean_feeder_real_power_losses_kw": pd.to_numeric(
                    group["feeder_real_power_losses_kw"], errors="coerce"
                ).mean(),
                "maximum_feeder_real_power_losses_kw": pd.to_numeric(
                    group["feeder_real_power_losses_kw"], errors="coerce"
                ).max(),
                "maximum_transformer_loading_percent": pd.to_numeric(
                    group["maximum_transformer_loading_percent"], errors="coerce"
                ).max(),
                "maximum_line_loading_percent": pd.to_numeric(
                    group["maximum_line_loading_percent"], errors="coerce"
                ).max(),
                "maximum_island_balance_residual_kw": pd.to_numeric(
                    group["island_balance_residual_kw"], errors="coerce"
                ).max(),
                "system_trace_path": str(group["system_trace_path"].iloc[0]),
            }
        )
    return pd.DataFrame(rows).sort_values(["budget", "method"]).reset_index(drop=True)


def _pareto_flags(frame: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=frame.index)
    cost_column = "total_upgrade_cost" if "total_upgrade_cost" in frame.columns else "budget"
    for _method, group in frame.groupby("method", sort=True):
        for index, row in group.iterrows():
            dominated = (
                (group[cost_column] <= row[cost_column] + 1e-9)
                & (group["total_ens"] <= row["total_ens"] + 1e-9)
                & (
                    (group[cost_column] < row[cost_column] - 1e-9)
                    | (group["total_ens"] < row["total_ens"] - 1e-9)
                )
            ).any()
            flags.loc[index] = not dominated
    return flags


def build_ac_valid_budget_frontier(budget_frame: pd.DataFrame, plan_frame: pd.DataFrame) -> pd.DataFrame:
    """Regenerate the budget comparison after the all-scenario AC gate."""

    merged = budget_frame.merge(
        plan_frame,
        on=["budget_id", "budget", "method"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_ac"),
    )
    if merged["ac_valid"].isna().any():
        raise ValueError("one or more budget headline plans lack AC validation")
    valid = merged[merged["ac_valid"].astype(bool)].copy()
    valid["ac_pareto_by_method"] = _pareto_flags(valid) if not valid.empty else False
    return valid.sort_values(["budget", "method"]).reset_index(drop=True)


def _failed_record(
    *,
    row: Any,
    scenario: dict[str, Any],
    reason: str,
    runtime: float,
) -> dict[str, Any]:
    return {
        "budget_id": str(row.budget_id),
        "budget": float(row.budget),
        "method": str(row.method),
        "scenario": str(scenario.get("scenario", "unknown")),
        "scenario_trace_id": str(scenario.get("scenario_trace_id", "")),
        "system_trace_id": str(row.system_trace_id),
        "system_trace_path": str(row.trace_path),
        "converged": False,
        "minimum_voltage_pu": math.nan,
        "maximum_voltage_pu": math.nan,
        "voltage_violation_count": 0,
        "feeder_real_power_losses_kw": math.nan,
        "maximum_transformer_loading_percent": math.nan,
        "maximum_line_loading_percent": math.nan,
        "island_balance_residual_kw": math.nan,
        "ac_valid": False,
        "failure_reason": reason,
        "ac_runtime_seconds": runtime,
    }


def _plot_voltage_profiles(frame: pd.DataFrame, path: Path) -> None:
    methods = sorted(frame["method"].unique())
    columns = 2
    rows = math.ceil(len(methods) / columns)
    figure, axes = plt.subplots(rows, columns, figsize=(13, 3.1 * rows), sharey=True)
    axes_array = np.asarray(axes).reshape(-1)
    for axis, method in zip(axes_array, methods, strict=False):
        values_by_bus: dict[str, list[float]] = {}
        for raw in frame.loc[frame["method"] == method, "voltage_profile_json"].dropna():
            for bus, record in json.loads(str(raw)).items():
                values_by_bus.setdefault(bus, []).extend(float(value) for value in record["phase_values_pu"])
        buses = sorted(values_by_bus, key=_natural_bus_key)
        positions = np.arange(len(buses))
        minimum = np.asarray([min(values_by_bus[bus]) for bus in buses])
        median = np.asarray([np.median(values_by_bus[bus]) for bus in buses])
        maximum = np.asarray([max(values_by_bus[bus]) for bus in buses])
        axis.fill_between(positions, minimum, maximum, alpha=0.2, color="#276FBF")
        axis.plot(positions, median, linewidth=1.0, color="#164B7A")
        axis.axhspan(0.95, 1.05, alpha=0.08, color="#2A9D8F")
        axis.axhline(0.95, linestyle="--", linewidth=0.7, color="#B23A48")
        axis.axhline(1.05, linestyle="--", linewidth=0.7, color="#B23A48")
        axis.set_title(method, fontsize=9)
        axis.set_xlabel("Public feeder buses (natural order)")
        axis.grid(alpha=0.15)
    for axis in axes_array[len(methods) :]:
        axis.set_visible(False)
    for axis in axes_array[::columns]:
        axis.set_ylabel("Voltage (pu)")
    figure.suptitle("IEEE 123 unbalanced voltage envelopes across budgets and scenarios")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_losses(frame: pd.DataFrame, path: Path) -> None:
    summary = (
        frame.groupby("method", sort=True)["feeder_real_power_losses_kw"]
        .agg(["mean", "min", "max"])
        .sort_values("mean")
    )
    figure, axis = plt.subplots(figsize=(9.5, 5.4))
    positions = np.arange(len(summary))
    errors = np.vstack([summary["mean"] - summary["min"], summary["max"] - summary["mean"]])
    axis.bar(positions, summary["mean"], color="#276FBF", alpha=0.85, yerr=errors, capsize=3)
    axis.set_xticks(positions, summary.index, rotation=25, ha="right")
    axis.set_ylabel("Feeder real-power losses (kW)")
    axis.set_title("Mean and range across all budget/scenario AC solves")
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_ac_frontier(frame: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.4, 5.3))
    if frame.empty:
        axis.text(
            0.5,
            0.55,
            "No system plan passed every checkable AC limit",
            ha="center",
            va="center",
            fontsize=14,
            transform=axis.transAxes,
        )
        axis.text(
            0.5,
            0.45,
            "0 of 48 plans passed all eight training-scenario AC checks",
            ha="center",
            va="center",
            fontsize=10,
            color="#555555",
            transform=axis.transAxes,
        )
        axis.set_axis_off()
    else:
        for method, group in frame.groupby("method", sort=True):
            ordered = group.sort_values("total_upgrade_cost")
            axis.plot(
                ordered["total_upgrade_cost"],
                ordered["total_ens"],
                marker="o",
                linewidth=1.3,
                markersize=4,
                label=method,
            )
        axis.legend(fontsize=7, ncol=2)
    if not frame.empty:
        axis.set_xlabel("Deduplicated upgrade cost (2022 USD)")
        axis.set_ylabel("Expected total ENS (kWh)")
    axis.set_title("Budget-matched frontier after all-scenario AC validation")
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _qci_advantage(frontier: pd.DataFrame) -> tuple[bool, list[float]]:
    budgets: list[float] = []
    for budget, group in frontier.groupby("budget", sort=True):
        qci = group[group["method"] == QCI_METHOD]
        baselines = group[group["method"] != QCI_METHOD]
        if qci.empty or baselines.empty:
            continue
        if float(qci.iloc[0]["total_ens"]) < float(baselines["total_ens"].min()) - 1e-9:
            budgets.append(float(budget))
    return bool(budgets), budgets


def _summary_markdown(
    *,
    scenario_frame: pd.DataFrame,
    plan_frame: pd.DataFrame,
    frontier: pd.DataFrame,
    qci_advantage: bool,
    advantage_budgets: list[float],
) -> str:
    qci_valid = int(plan_frame[(plan_frame["method"] == QCI_METHOD) & plan_frame["ac_valid"]].shape[0])
    baseline_valid = int(plan_frame[(plan_frame["method"] != QCI_METHOD) & plan_frame["ac_valid"]].shape[0])
    line_available = bool(scenario_frame.get("line_loading_available", pd.Series(dtype=bool)).fillna(False).any())
    claim = (
        f"QCi retains a strict total-ENS advantage at {len(advantage_budgets)} matched AC-valid budget level(s)."
        if qci_advantage
        else "No strict QCi total-ENS advantage is supported among matched budgets with AC-valid QCi and baseline plans."
    )
    return "\n".join(
        [
            "# IEEE123 Budget-Sweep Unbalanced AC Validation",
            "",
            "This report is generated from `ac_validation_results.csv` and the saved budget system traces.",
            "Every plan is accepted only when all eight training-scenario OpenDSS solves converge and all checkable limits pass.",
            "",
            "## Method",
            "",
            "- The complete pinned IEEE123 source bundle is copied before each validation run; source artifacts are not edited.",
            "- Saved critical and noncritical served-load totals are mapped proportionally within those public node classes, preserving phase connections and power factors.",
            "- Saved topology/PCC states and aggregate generation/storage dispatch are applied; technology dispatch is allocated pro rata over eligible installed physical assets.",
            "- No grid-forming inverter or island slack model is added because none is published in the upgrade catalog; disconnected served buses therefore fail the voltage check rather than receiving an invented voltage source.",
            "- Voltage limits are 0.95–1.05 pu. Published transformer kVA ratings are enforced at 100% loading.",
            f"- Published line ampacity available: {line_available}. Missing ratings are unavailable, never replaced by engine defaults.",
            "- Regulator taps, capacitor states, feeder losses, and numerical island/system balance residuals are retained in the scenario table.",
            "",
            "## Results",
            "",
            f"- Scenario solves: {len(scenario_frame)}",
            f"- AC-valid QCi system plans: {qci_valid}",
            f"- AC-valid baseline system plans: {baseline_valid}",
            f"- AC-valid comparison rows: {len(frontier)}",
            "- All forced-islanding-family cases de-energize served buses under the published controls; this prevents every eight-scenario plan from passing the AC gate.",
            f"- QCi strict advantage budgets: {advantage_budgets}",
            f"- Supported conclusion: {claim}",
            "",
            "## Reproduction",
            "",
            "`python scripts/phase3_validate_ieee123_ac_solutions.py`",
            "",
        ]
    )


def validate_ieee123_ac_solutions(
    *,
    config_path: Path | str = DEFAULT_CONFIG,
    budget_dir: Path | str = DEFAULT_BUDGET_DIR,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate and report all 48 selected budget/method system plans."""

    config = _resolve(config_path)
    budgets = _resolve(budget_dir)
    output = _resolve(output_dir)
    headline = _headline_rows(budgets)
    payload_dir = ROOT / "results" / "phase3" / "sc_cmpo" / "ieee123" / "qci_payloads"
    critical_nodes = _critical_nodes(payload_dir)
    scenario_count = 0
    for row in headline.itertuples(index=False):
        trace = json.loads(Path(str(row.trace_path)).read_text(encoding="utf-8"))
        scenarios = trace["system"]["scenario_results"]
        if len(scenarios) != 8:
            raise ValueError(f"{row.trace_path} has {len(scenarios)} scenarios instead of eight")
        scenario_count += len(scenarios)
    plan = {
        "plan_count": int(len(headline)),
        "scenario_validation_count": scenario_count,
        "method_count": int(headline["method"].nunique()),
        "budget_count": int(headline["budget_id"].nunique()),
    }
    if dry_run:
        return {"dry_run": True, **plan}

    targets = [output / name for name in (RESULT_FILE, FRONTIER_FILE, SUMMARY_FILE, *FIGURES)]
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError(f"AC validation outputs already exist under {output}; pass --overwrite to regenerate them")
    output.mkdir(parents=True, exist_ok=True)
    case = parse_ieee123_sc_cmpo_case(load_sc_cmpo_config(config))
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ieee123-ac-validation-") as temporary_directory:
        copied_master = copy_pinned_feeder(Path(case.metadata["master_path"]), temporary_directory)
        for row in headline.itertuples(index=False):
            trace = json.loads(Path(str(row.trace_path)).read_text(encoding="utf-8"))
            if str(trace["system"]["system_metrics"]["system_trace_id"]) != str(row.system_trace_id):
                raise ValueError(f"system trace ID mismatch for {row.trace_path}")
            for scenario in trace["system"]["scenario_results"]:
                started = time.perf_counter()
                try:
                    record = validate_ieee123_scenario(
                        case=case,
                        copied_master=copied_master,
                        method=str(row.method),
                        budget_id=str(row.budget_id),
                        budget=float(row.budget),
                        system_trace_id=str(row.system_trace_id),
                        system_trace_path=str(row.trace_path),
                        scenario=scenario,
                        upgrade_plan=trace["system"]["upgrade_plan"],
                        critical_nodes=critical_nodes,
                    )
                    record["ac_runtime_seconds"] = time.perf_counter() - started
                except Exception as exc:  # retain every failed validation point in the result table
                    record = _failed_record(
                        row=row,
                        scenario=scenario,
                        reason=f"{type(exc).__name__}: {exc}",
                        runtime=time.perf_counter() - started,
                    )
                records.append(record)

    scenario_frame = pd.DataFrame(records).sort_values(["budget", "method", "scenario"]).reset_index(drop=True)
    if len(scenario_frame) != scenario_count:
        raise ValueError("not every headline plan/scenario produced an AC record")
    scenario_frame.to_csv(output / RESULT_FILE, index=False)
    plan_frame = aggregate_ac_validation(scenario_frame)
    if set(plan_frame["ac_scenario_count"]) != {8}:
        raise ValueError("every AC plan gate must contain exactly eight training scenarios")
    frontier = build_ac_valid_budget_frontier(headline, plan_frame)
    frontier.to_csv(output / FRONTIER_FILE, index=False)
    qci_advantage, advantage_budgets = _qci_advantage(frontier)
    (output / SUMMARY_FILE).write_text(
        _summary_markdown(
            scenario_frame=scenario_frame,
            plan_frame=plan_frame,
            frontier=frontier,
            qci_advantage=qci_advantage,
            advantage_budgets=advantage_budgets,
        ),
        encoding="utf-8",
    )
    _plot_voltage_profiles(scenario_frame, output / FIGURES[0])
    _plot_losses(scenario_frame, output / FIGURES[1])
    _plot_ac_frontier(frontier, output / FIGURES[2])

    qci_valid_count = int(plan_frame[(plan_frame["method"] == QCI_METHOD) & plan_frame["ac_valid"]].shape[0])
    baseline_valid_count = int(plan_frame[(plan_frame["method"] != QCI_METHOD) & plan_frame["ac_valid"]].shape[0])
    voltage_by_method = {
        str(key): int(value)
        for key, value in scenario_frame.groupby("method")["voltage_violation_count"].sum().sort_index().items()
    }
    losses_by_method = {
        str(key): float(value)
        for key, value in scenario_frame.groupby("method")["feeder_real_power_losses_kw"].mean().sort_index().items()
    }
    return {
        **plan,
        "ac_valid_qci_solution_count": qci_valid_count,
        "ac_valid_baseline_solution_count": baseline_valid_count,
        "voltage_violation_counts_by_method": voltage_by_method,
        "mean_losses_kw_by_method": losses_by_method,
        "qci_retains_budget_matched_advantage": qci_advantage,
        "qci_advantage_budgets": advantage_budgets,
        "output_dir": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--budget-dir", default=str(DEFAULT_BUDGET_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = validate_ieee123_ac_solutions(
        config_path=args.config,
        budget_dir=args.budget_dir,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"AC-valid QCi solution count: {result['ac_valid_qci_solution_count']}")
    print(f"AC-valid baseline solution count: {result['ac_valid_baseline_solution_count']}")
    print(f"Voltage violation counts by method: {json.dumps(result['voltage_violation_counts_by_method'], sort_keys=True)}")
    print(f"Losses by method (mean kW): {json.dumps(result['mean_losses_kw_by_method'], sort_keys=True)}")
    print(f"QCi retains any budget-matched advantage after AC validation: {result['qci_retains_budget_matched_advantage']}")


if __name__ == "__main__":
    main()
