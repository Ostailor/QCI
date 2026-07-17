"""Matched-budget resilience frontier analytics and validation."""

from __future__ import annotations

import math
from typing import Iterable

import pandas as pd


def pareto_frontier(
    frame: pd.DataFrame,
    *,
    cost_col: str = "total_upgrade_cost",
    resilience_col: str = "total_ens",
) -> pd.DataFrame:
    """Return nondominated cost/resilience points for a minimization frontier."""

    required = {cost_col, resilience_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"frontier input missing columns: {sorted(missing)}")
    clean = frame.dropna(subset=[cost_col, resilience_col]).copy()
    costs = pd.to_numeric(clean[cost_col], errors="raise")
    resilience = pd.to_numeric(clean[resilience_col], errors="raise")
    keep = []
    for index in clean.index:
        dominated = ((costs <= costs[index]) & (resilience <= resilience[index]) & ((costs < costs[index]) | (resilience < resilience[index]))).any()
        keep.append(not dominated)
    result = clean.loc[[index for index, selected in zip(clean.index, keep, strict=True) if selected]].copy()
    result["pareto_frontier"] = True
    return result.sort_values([cost_col, resilience_col]).reset_index(drop=True)


def frontier_hypervolume(
    frame: pd.DataFrame,
    *,
    cost_col: str = "total_upgrade_cost",
    resilience_col: str = "total_ens",
    reference_cost: float,
    reference_resilience: float,
) -> float:
    """Compute dominated 2-D hypervolume for a minimization frontier."""

    frontier = pareto_frontier(frame, cost_col=cost_col, resilience_col=resilience_col)
    points = [
        (float(row[cost_col]), float(row[resilience_col]))
        for _, row in frontier.iterrows()
        if float(row[cost_col]) <= reference_cost and float(row[resilience_col]) <= reference_resilience
    ]
    volume = 0.0
    best_resilience = reference_resilience
    previous_cost = reference_cost
    for cost, resilience in sorted(points, reverse=True):
        if resilience < best_resilience:
            volume += max(0.0, previous_cost - cost) * max(0.0, reference_resilience - best_resilience)
            best_resilience = resilience
            previous_cost = cost
    if points:
        volume += max(0.0, previous_cost - min(cost for cost, _ in points)) * max(0.0, reference_resilience - best_resilience)
    # Exact union of lower-left rectangles; the direct sweep below avoids any
    # dependence on point ordering in the compact accumulation above.
    volume = 0.0
    xs = sorted({cost for cost, _ in points} | {reference_cost})
    for left, right in zip(xs, xs[1:]):
        eligible = [resilience for cost, resilience in points if cost <= left]
        if eligible:
            volume += (right - left) * max(0.0, reference_resilience - min(eligible))
    return float(volume)


def add_marginal_ens_reduction(
    frame: pd.DataFrame,
    *,
    method_col: str = "method",
    budget_col: str = "budget",
    ens_col: str = "total_ens",
) -> pd.DataFrame:
    """Add ENS reduction per additional budget dollar within each method."""

    result = frame.copy()
    result["marginal_ens_reduction_per_dollar"] = math.nan
    for _, group in result.groupby(method_col, sort=False):
        ordered = group.sort_values(budget_col)
        budgets = pd.to_numeric(ordered[budget_col], errors="raise")
        ens = pd.to_numeric(ordered[ens_col], errors="raise")
        delta_budget = budgets.diff()
        marginal = -ens.diff() / delta_budget.where(delta_budget > 0.0)
        result.loc[ordered.index, "marginal_ens_reduction_per_dollar"] = marginal.values
    return result


def budget_win_tie_loss(
    frame: pd.DataFrame,
    *,
    qci_method: str = "QCi SC-CMPO",
    metric: str = "total_ens",
    tolerance: float = 1e-9,
) -> pd.DataFrame:
    """Classify QCi against the best classical value at every common budget."""

    rows = []
    for budget, group in frame.groupby("budget", sort=True):
        qci = group[group["method"] == qci_method]
        classical = group[group["method"] != qci_method]
        if len(qci) != 1 or classical.empty:
            raise ValueError(f"budget {budget} lacks one QCi row or classical comparators")
        qci_value = float(qci.iloc[0][metric])
        best = float(pd.to_numeric(classical[metric], errors="raise").min())
        if qci_value < best - tolerance:
            outcome = "win"
        elif qci_value > best + tolerance:
            outcome = "loss"
        else:
            outcome = "tie"
        rows.append({"budget": float(budget), "metric": metric, "qci_value": qci_value, "best_classical_value": best, "outcome": outcome})
    return pd.DataFrame(rows)


def validate_matched_budget_results(
    frame: pd.DataFrame,
    *,
    expected_methods: Iterable[str],
    tolerance: float = 1e-6,
) -> None:
    """Reject incomplete, untraceable, infeasible, or over-budget final rows."""

    required = {"budget", "method", "total_upgrade_cost", "feasibility", "system_trace_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"result table missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("result table is empty")
    expected = set(expected_methods)
    for budget, group in frame.groupby("budget"):
        methods = set(group["method"])
        if methods != expected:
            raise ValueError(f"method coverage mismatch at budget {budget}: {sorted(methods)}")
        if len(group) != len(expected):
            raise ValueError(f"duplicate method rows at budget {budget}")
    costs = pd.to_numeric(frame["total_upgrade_cost"], errors="raise")
    budgets = pd.to_numeric(frame["budget"], errors="raise")
    if (costs > budgets + tolerance).any():
        offenders = frame.loc[costs > budgets + tolerance, ["budget", "method", "total_upgrade_cost"]]
        raise ValueError(f"over-budget final rows: {offenders.to_dict('records')}")
    if not frame["feasibility"].map(lambda value: str(value).lower() in {"true", "1"} if not isinstance(value, bool) else value).all():
        raise ValueError("infeasible rows may not enter final tables")
    if frame["system_trace_id"].fillna("").astype(str).str.strip().eq("").any():
        raise ValueError("every result row must have a system trace ID")
