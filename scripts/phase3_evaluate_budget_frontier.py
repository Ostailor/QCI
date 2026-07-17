#!/usr/bin/env python
"""Evaluate, tabulate, and plot the matched-budget IEEE123 resilience frontier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cmpo.budget_frontier import (  # noqa: E402
    add_marginal_ens_reduction,
    budget_win_tie_loss,
    frontier_hypervolume,
    pareto_frontier,
    validate_matched_budget_results,
)
from scripts.phase3_run_budgeted_baselines import (  # noqa: E402
    QCI_METHOD,
    evaluate_budgeted_methods,
)


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_sweep.yaml")
TABLES = (
    "table_budget_matched_results.csv",
    "table_heldout_budget_results.csv",
    "table_budget_win_tie_loss.csv",
    "pareto_frontier.csv",
)
FIGURES = (
    "upgrade_cost_vs_total_ens.png",
    "upgrade_cost_vs_critical_ens.png",
    "upgrade_cost_vs_max_unserved.png",
    "heldout_upgrade_cost_vs_ens.png",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _config(path: Path | str) -> dict[str, Any]:
    return yaml.safe_load(_resolve(path).read_text(encoding="utf-8"))


def _plot(frame: pd.DataFrame, y: str, ylabel: str, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    for method, group in frame.groupby("method", sort=True):
        ordered = group.sort_values("total_upgrade_cost")
        axis.plot(ordered["total_upgrade_cost"], ordered[y], marker="o", linewidth=1.4, markersize=4, label=method)
    axis.set_xlabel("Deduplicated upgrade cost (2022 USD)")
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _frontier_table(system: pd.DataFrame, heldout: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[pd.DataFrame] = []
    hypervolumes: dict[str, dict[str, float]] = {}
    objectives = [
        (system, "total_ens", "in_sample_total_ens"),
        (system, "critical_ens", "in_sample_critical_ens"),
        (heldout, "heldout_total_ens", "heldout_total_ens"),
    ]
    for frame, metric, objective in objectives:
        reference_cost = float(frame["budget"].max()) * 1.01
        reference_resilience = max(1e-9, float(frame[metric].max()) * 1.05)
        hypervolumes[objective] = {}
        for method, group in frame.groupby("method", sort=True):
            frontier = pareto_frontier(group, cost_col="total_upgrade_cost", resilience_col=metric)
            volume = frontier_hypervolume(
                group,
                cost_col="total_upgrade_cost",
                resilience_col=metric,
                reference_cost=reference_cost,
                reference_resilience=reference_resilience,
            )
            hypervolumes[objective][method] = volume
            frontier = frontier.assign(
                frontier_objective=objective,
                resilience_metric=metric,
                method_hypervolume=volume,
                hypervolume_reference_cost=reference_cost,
                hypervolume_reference_resilience=reference_resilience,
            )
            rows.append(frontier)
    return pd.concat(rows, ignore_index=True, sort=False), hypervolumes


def _lowest_budgets(frame: pd.DataFrame, metric: str, tolerance: float = 1e-9) -> list[float]:
    budgets = []
    for budget, group in frame.groupby("budget", sort=True):
        qci = float(group[group["method"] == QCI_METHOD].iloc[0][metric])
        best = float(group[metric].min())
        if qci <= best + tolerance:
            budgets.append(float(budget))
    return budgets


def _claim_from_outcomes(qci_total_outcomes: pd.Series) -> str:
    if (qci_total_outcomes == "win").any():
        return (
            "At identical hard upgrade budgets, QCi SC-CMPO attains the lowest IEEE123 total ENS at "
            f"{int((qci_total_outcomes == 'win').sum())} tested budget level(s); ties and losses are reported "
            "without extrapolation."
        )
    if (qci_total_outcomes == "tie").all():
        return "At identical hard upgrade budgets, QCi SC-CMPO ties the best classical IEEE123 total ENS across all tested levels."
    return (
        "At identical hard upgrade budgets, the IEEE123 sweep does not support a claim that QCi SC-CMPO "
        "reduces total ENS versus every classical method."
    )


def evaluate_budget_frontier(
    config_path: Path | str,
    output_dir: Path | str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = _config(config_path)
    output = _resolve(output_dir)
    methods = [str(item) for item in config["methods"]]
    budget_count = evaluate_budgeted_methods(
        config_path,
        output,
        methods=[QCI_METHOD],
        result_prefix="qci",
        overwrite=overwrite,
        dry_run=True,
    )["budget_count"]
    plan = {
        "budget_count": budget_count,
        "method_count": len(methods),
        "comparison_point_count": budget_count * len(methods),
        "final_tables": list(TABLES),
        "figures": list(FIGURES),
    }
    if dry_run:
        return {"dry_run": True, **plan}
    final_targets = [output / name for name in (*TABLES, *FIGURES)]
    if not overwrite and any(path.exists() for path in final_targets):
        raise FileExistsError(f"final budget-frontier outputs already exist under {output}")
    classical_path = output / "classical_budgeted_results.csv"
    classical_heldout_path = output / "classical_budgeted_heldout_results.csv"
    if not classical_path.exists() or not classical_heldout_path.exists():
        raise FileNotFoundError("run scripts/phase3_run_budgeted_baselines.py before frontier evaluation")
    qci_run = evaluate_budgeted_methods(
        config_path,
        output,
        methods=[QCI_METHOD],
        result_prefix="qci",
        overwrite=overwrite,
        dry_run=False,
    )
    if qci_run["failed"]:
        raise ValueError(f"QCi budget reconstruction has {qci_run['failed']} failed points")

    system = pd.concat([pd.read_csv(classical_path), pd.read_csv(output / "qci_budgeted_results.csv")], ignore_index=True)
    heldout = pd.concat([pd.read_csv(classical_heldout_path), pd.read_csv(output / "qci_budgeted_heldout_results.csv")], ignore_index=True)
    validate_matched_budget_results(system, expected_methods=methods)
    validate_matched_budget_results(heldout, expected_methods=methods)
    if set(pd.to_numeric(heldout["heldout_count"], errors="raise")) != {10}:
        raise ValueError("every method/budget point must use the same ten held-out N-1 contingencies")
    system = add_marginal_ens_reduction(system)
    system = system.sort_values(["budget", "method"]).reset_index(drop=True)
    heldout = heldout.sort_values(["budget", "method"]).reset_index(drop=True)
    system.to_csv(output / TABLES[0], index=False)
    heldout.to_csv(output / TABLES[1], index=False)

    outcome_frames = []
    for metric in ("total_ens", "critical_ens", "maximum_customers_unserved_per_hour"):
        outcome_frames.append(budget_win_tie_loss(system, qci_method=QCI_METHOD, metric=metric))
    outcomes = pd.concat(outcome_frames, ignore_index=True)
    outcomes.to_csv(output / TABLES[2], index=False)
    frontier, hypervolumes = _frontier_table(system, heldout)
    frontier.to_csv(output / TABLES[3], index=False)

    _plot(system, "total_ens", "Expected total ENS (kWh)", output / FIGURES[0])
    _plot(system, "critical_ens", "Expected critical ENS (kWh)", output / FIGURES[1])
    _plot(
        system,
        "maximum_customers_unserved_per_hour",
        "Maximum fraction customers unserved per hour",
        output / FIGURES[2],
    )
    _plot(heldout, "heldout_total_ens", "Held-out expected total ENS (kWh)", output / FIGURES[3])

    qci_jobs = pd.read_csv(output / "qci_job_status.csv")
    completed = int(qci_jobs["status"].astype(str).str.upper().eq("COMPLETED").sum())
    failed = int(len(qci_jobs) - completed)
    total_lowest = _lowest_budgets(system, "total_ens")
    critical_lowest = _lowest_budgets(system, "critical_ens")
    max_unserved_lowest = _lowest_budgets(system, "maximum_customers_unserved_per_hour")
    heldout_hv = hypervolumes["heldout_total_ens"]
    best_heldout = max(heldout_hv.values())
    qci_best_heldout = heldout_hv[QCI_METHOD] >= best_heldout - 1e-9
    qci_total_outcomes = outcomes[outcomes["metric"] == "total_ens"]["outcome"]
    claim = _claim_from_outcomes(qci_total_outcomes)
    summary = {
        **plan,
        "qci_jobs_completed": completed,
        "qci_jobs_failed": failed,
        "qci_lowest_total_ens_budgets": total_lowest,
        "qci_lowest_critical_ens_budgets": critical_lowest,
        "qci_lowest_max_unserved_budgets": max_unserved_lowest,
        "qci_best_heldout_pareto_hypervolume": qci_best_heldout,
        "hypervolumes": hypervolumes,
        "strongest_supported_claim": claim,
    }
    (output / "budget_frontier_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "budget_frontier_report.md").write_text(
        "\n".join(
            [
                "# IEEE 123 Budget-Matched SC-CMPO Frontier",
                "",
                f"- Common hard budgets: {budget_count}",
                f"- QCi jobs completed/failed: {completed}/{failed}",
                f"- QCi lowest total ENS budgets: {total_lowest}",
                f"- QCi lowest critical ENS budgets: {critical_lowest}",
                f"- QCi lowest maximum unserved budgets: {max_unserved_lowest}",
                f"- QCi best held-out Pareto hypervolume: {qci_best_heldout}",
                "",
                f"Strongest supported claim: {claim}",
                "",
                "Every point uses the same 12 patches, eight training scenarios, overlap-consensus reconstruction, "
                "full-system projection, ten deterministic held-out N-1 contingencies, and charge-once physical-asset accounting.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default="results/phase3/sc_cmpo/budget_frontier")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = evaluate_budget_frontier(args.config, args.output_dir, overwrite=args.overwrite, dry_run=args.dry_run)
    print(f"number of budgets: {result['budget_count']}")
    print(f"QCi jobs completed and failed: {result.get('qci_jobs_completed', 0)} completed, {result.get('qci_jobs_failed', 0)} failed")
    print(f"budget levels where QCi has the lowest total ENS: {result.get('qci_lowest_total_ens_budgets', [])}")
    print(f"budget levels where QCi has the lowest critical ENS: {result.get('qci_lowest_critical_ens_budgets', [])}")
    print(f"budget levels where QCi has the lowest maximum unserved fraction: {result.get('qci_lowest_max_unserved_budgets', [])}")
    print(f"whether QCi has the best held-out Pareto hypervolume: {result.get('qci_best_heldout_pareto_hypervolume', False)}")
    print(f"strongest supported budget-matched paper claim: {result.get('strongest_supported_claim', 'dry run; no claim computed')}")


if __name__ == "__main__":
    main()
