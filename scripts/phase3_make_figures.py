#!/usr/bin/env python
"""Build required benchmark-first Phase 3 final figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


PHASE3_ROOT = Path("results") / "phase3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate required Phase 3 final PNG figures from final tables.")
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 final tables.")
    parser.add_argument(
        "--public-benchmarks",
        action="store_true",
        help="Generate the judge-facing public benchmark figure set. The flag is accepted for command reproducibility.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned figure outputs without writing files.")
    return parser


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _save_empty(path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center")
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _bar(frame: pd.DataFrame, x: str, y: str, path: Path, title: str, ylabel: str) -> None:
    if frame.empty or x not in frame or y not in frame:
        _save_empty(path, title)
        return
    plot = frame.copy().head(40)
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.bar(plot[x].astype(str), plot[y])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=55)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _scatter(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or not {"risk_adjusted_cost", "critical_load_served_fraction", "method_name"}.issubset(frame.columns):
        _save_empty(path, "Cost vs Resilience Pareto")
        return
    fig, ax = plt.subplots(figsize=(9, 6))
    for method, group in frame.groupby("method_name"):
        ax.scatter(group["risk_adjusted_cost"], group["critical_load_served_fraction"], label=str(method), s=36)
    ax.set_title("Cost vs Resilience Pareto")
    ax.set_xlabel("Risk-adjusted cost")
    ax.set_ylabel("Critical-load served fraction")
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _qci_distribution(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or "best_cost" not in frame.columns:
        _save_empty(path, "QCi Repeat Distribution")
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = frame["dataset"].astype(str) + "\n" + frame["scenario"].astype(str)
    ax.errorbar(labels, frame["best_cost"], yerr=frame.get("std_cost", 0.0), fmt="o")
    ax.set_title("QCi Repeat Distribution")
    ax.set_ylabel("Best QCi cost")
    ax.tick_params(axis="x", rotation=55)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.phase3_root)
    table_dir = root / "final_tables"
    figure_dir = root / "final_figures"
    outputs = {
        "cost_vs_resilience_pareto": figure_dir / "cost_vs_resilience_pareto.png",
        "critical_ens_by_scenario": figure_dir / "critical_ens_by_scenario.png",
        "max_customers_unserved_by_scenario": figure_dir / "max_customers_unserved_by_scenario.png",
        "time_to_good_solution": figure_dir / "time_to_good_solution.png",
        "native_cubic_vs_qubo_size": figure_dir / "native_cubic_vs_qubo_size.png",
        "qci_repeat_distribution": figure_dir / "qci_repeat_distribution.png",
    }
    if args.dry_run:
        print(json.dumps({"input_dir": str(table_dir), "outputs": {k: str(v) for k, v in outputs.items()}}, indent=2))
        return
    figure_dir.mkdir(parents=True, exist_ok=True)
    pareto = _read(table_dir / "pareto_frontier.csv")
    stress = _read(table_dir / "table3_scenario_stress.csv")
    cubic = _read(table_dir / "table4_native_cubic_vs_qubo.csv")
    qci = _read(table_dir / "qci_repeat_distribution.csv")
    _scatter(pareto, outputs["cost_vs_resilience_pareto"])
    stress_labels = stress.copy()
    if not stress_labels.empty:
        stress_labels["label"] = stress_labels["dataset"].astype(str) + "\n" + stress_labels["scenario"].astype(str)
    _bar(
        stress_labels.sort_values("critical_energy_not_served_kwh", ascending=False)
        if "critical_energy_not_served_kwh" in stress_labels
        else stress_labels,
        "label",
        "critical_energy_not_served_kwh",
        outputs["critical_ens_by_scenario"],
        "Critical Energy Not Served By Scenario",
        "Critical ENS (kWh)",
    )
    _bar(
        stress_labels.sort_values("max_fraction_customers_unserved_per_hour", ascending=False)
        if "max_fraction_customers_unserved_per_hour" in stress_labels
        else stress_labels,
        "label",
        "max_fraction_customers_unserved_per_hour",
        outputs["max_customers_unserved_by_scenario"],
        "Maximum Customers Unserved By Scenario",
        "Max fraction unserved",
    )
    _bar(
        pareto,
        "method_name",
        "time_to_good_solution",
        outputs["time_to_good_solution"],
        "Time To Good Solution",
        "Seconds",
    )
    size = cubic.copy()
    if not size.empty:
        size["qubo_size_proxy"] = size.get("qubo_auxiliary_variable_count_median", pd.Series([0] * len(size))).fillna(0) + size.get(
            "native_cubic_variable_count_median", pd.Series([0] * len(size))
        ).fillna(0)
    _bar(
        size,
        "dataset",
        "qubo_size_proxy",
        outputs["native_cubic_vs_qubo_size"],
        "Native Cubic vs QUBO Size",
        "Variables plus auxiliary variables",
    )
    _qci_distribution(qci, outputs["qci_repeat_distribution"])
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
