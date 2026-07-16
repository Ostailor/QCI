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
    parser.add_argument("--include-direct-qci", action="store_true", help="Include direct-QCi rows already present in final tables.")
    parser.add_argument("--include-cmpo-v2", action="store_true", help="Include CMPO-V2 rows already present in final tables.")
    parser.add_argument("--include-hybrid", action="store_true", help="Include full hybrid rows when present in final tables.")
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


def _short_method_name(method: object) -> str:
    aliases = {
        "CMPO + QCi Dirac-3": "Direct CMPO QCi",
        "CMPO-V2 + QCi Dirac-3": "CMPO-V2 QCi",
        "CMPO Hybrid QCi + Classical Projection": "Hybrid QCi + projection",
        "Piecewise-linear MILP baseline": "MILP",
        "GPU-parallel random restart baseline": "GPU restarts",
        "QUBO/quadratized local search baseline": "QUBO local search",
        "IPOPT/Pyomo nonlinear baseline": "IPOPT/Pyomo",
        "Stress-only reserve heuristic baseline": "Reserve heuristic",
    }
    value = str(method)
    return aliases.get(value, value)


def _scatter_v2(challenge: pd.DataFrame, pareto: pd.DataFrame, path: Path) -> None:
    required = {"dataset", "method_name", "risk_adjusted_cost", "critical_energy_not_served_kwh"}
    if challenge.empty or not required.issubset(challenge.columns):
        _save_empty(path, "Final Cost-Resilience Pareto")
        return
    frame = challenge[challenge.get("score_mode", pd.Series("weighted", index=challenge.index)) == "weighted"].copy()
    if frame.empty:
        _save_empty(path, "Final Cost-Resilience Pareto")
        return
    datasets = sorted(frame["dataset"].astype(str).unique())
    methods = sorted(frame["method_name"].astype(str).unique())
    colors = {method: plt.get_cmap("tab20")(index % 20) for index, method in enumerate(methods)}
    pareto_keys = (
        set(zip(pareto["dataset"].astype(str), pareto["method_name"].astype(str), strict=False))
        if not pareto.empty and {"dataset", "method_name"}.issubset(pareto.columns)
        else set()
    )
    fig, axes = plt.subplots(1, len(datasets), figsize=(5.2 * len(datasets), 5.3), squeeze=False)
    for axis, dataset in zip(axes[0], datasets, strict=False):
        group = frame[frame["dataset"].astype(str) == dataset]
        for _, row in group.iterrows():
            method = str(row["method_name"])
            is_qci = bool(pd.Series([method]).str.contains("qci|dirac", case=False, regex=True).iloc[0])
            on_frontier = (dataset, method) in pareto_keys
            axis.scatter(
                float(row["risk_adjusted_cost"]),
                float(row["critical_energy_not_served_kwh"]),
                color=colors[method],
                marker="*" if is_qci else "o",
                s=150 if is_qci else 58,
                edgecolor="black" if on_frontier else "none",
                linewidth=1.2,
                label=_short_method_name(method),
                zorder=3 if is_qci else 2,
            )
            if is_qci:
                axis.annotate(
                    _short_method_name(method),
                    (float(row["risk_adjusted_cost"]), float(row["critical_energy_not_served_kwh"])),
                    xytext=(4, 5),
                    textcoords="offset points",
                    fontsize=7,
                )
        axis.set_title(dataset.replace("_adapted", "").replace("pglib_", "PGLib "))
        axis.set_xlabel("Risk-adjusted cost")
        axis.set_ylabel("Critical ENS (kWh)")
        axis.grid(alpha=0.2)
    handles, labels = axes[0][0].get_legend_handles_labels()
    unique = dict(zip(labels, handles, strict=False))
    fig.legend(unique.values(), unique.keys(), loc="lower center", ncol=4, fontsize=7, frameon=False)
    fig.suptitle("Final Cost-Resilience Pareto (lower-left is better)")
    fig.tight_layout(rect=(0, 0.14, 1, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _critical_ens_v2(stress: pd.DataFrame, challenge: pd.DataFrame, path: Path) -> None:
    required = {"dataset", "scenario", "method_name", "critical_energy_not_served_kwh"}
    if stress.empty or challenge.empty or not required.issubset(stress.columns):
        _save_empty(path, "Final Critical ENS By Scenario")
        return
    scored = challenge[challenge.get("score_mode", pd.Series("weighted", index=challenge.index)) == "weighted"].copy()
    datasets = sorted(set(stress["dataset"].astype(str)) & set(scored["dataset"].astype(str)))
    if not datasets:
        _save_empty(path, "Final Critical ENS By Scenario")
        return
    fig, axes = plt.subplots(len(datasets), 1, figsize=(13, 4.2 * len(datasets)), squeeze=False)
    for axis, dataset in zip(axes[:, 0], datasets, strict=False):
        dataset_scores = scored[scored["dataset"].astype(str) == dataset]
        qci_methods = sorted(
            dataset_scores.loc[
                dataset_scores["method_name"].astype(str).str.contains("qci|dirac", case=False, regex=True),
                "method_name",
            ].astype(str)
        )
        classical = dataset_scores[
            ~dataset_scores["method_name"].astype(str).str.contains("qci|dirac", case=False, regex=True)
        ].sort_values("challenge_score")
        selected = qci_methods + ([] if classical.empty else [str(classical.iloc[0]["method_name"])])
        selected = list(dict.fromkeys(selected))
        group = stress[
            (stress["dataset"].astype(str) == dataset) & stress["method_name"].astype(str).isin(selected)
        ].copy()
        scenarios = sorted(group["scenario"].astype(str).unique())
        width = 0.8 / max(1, len(selected))
        x_positions = list(range(len(scenarios)))
        for offset, method in enumerate(selected):
            method_rows = group[group["method_name"].astype(str) == method].set_index("scenario")
            values = [float(method_rows.loc[item, "critical_energy_not_served_kwh"]) if item in method_rows.index else 0.0 for item in scenarios]
            positions = [value - 0.4 + width / 2 + offset * width for value in x_positions]
            axis.bar(positions, values, width=width, label=_short_method_name(method))
        axis.set_xticks(x_positions, scenarios, rotation=25, ha="right")
        axis.set_ylabel("Median critical ENS (kWh)")
        axis.set_title(dataset.replace("_adapted", "").replace("pglib_", "PGLib "))
        axis.grid(axis="y", alpha=0.2)
        axis.legend(fontsize=8, frameon=False)
    fig.suptitle("Critical Energy Not Served By Scenario")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=180)
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
        "final_cost_resilience_pareto_v2": figure_dir / "final_cost_resilience_pareto_v2.png",
        "final_critical_ens_by_scenario_v2": figure_dir / "final_critical_ens_by_scenario_v2.png",
    }
    if args.dry_run:
        print(json.dumps({"input_dir": str(table_dir), "outputs": {k: str(v) for k, v in outputs.items()}}, indent=2))
        return
    figure_dir.mkdir(parents=True, exist_ok=True)
    pareto = _read(table_dir / "pareto_frontier.csv")
    stress = _read(table_dir / "table3_scenario_stress.csv")
    cubic = _read(table_dir / "table4_native_cubic_vs_qubo.csv")
    qci = _read(table_dir / "qci_repeat_distribution.csv")
    challenge = _read(table_dir / "final_challenge_score_table.csv")
    final_pareto = _read(table_dir / "final_pareto_frontier_v2.csv")
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
    _scatter_v2(challenge, final_pareto, outputs["final_cost_resilience_pareto_v2"])
    _critical_ens_v2(stress, challenge, outputs["final_critical_ens_by_scenario_v2"])
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
