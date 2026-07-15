"""Challenge-aligned scoring for Phase 3 result summaries.

The score is a derived comparison layer. It does not replace or mutate raw
decoded QCi or baseline metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from cmpo.phase3_metrics import summarize_phase3_results


ScoreMode = Literal["weighted", "lexicographic", "both"]

QCI_METHOD_PATTERN = r"qci|dirac"
INFEASIBILITY_PENALTY_WEIGHT = 10_000.0


WEIGHTED_TERMS: tuple[tuple[str, float], ...] = (
    ("critical_energy_not_served_kwh", 1000.0),
    ("total_hours_critical_infrastructure_unserved", 1000.0),
    ("max_fraction_customers_unserved_per_hour", 500.0),
    ("total_energy_not_served", 100.0),
    ("risk_adjusted_cost", 10.0),
    ("runtime", 1.0),
)

LEXICOGRAPHIC_ORDER: tuple[tuple[str, bool], ...] = (
    ("feasibility_after_repair", False),
    ("critical_energy_not_served_kwh", True),
    ("total_hours_critical_infrastructure_unserved", True),
    ("max_fraction_customers_unserved_per_hour", True),
    ("critical_load_served_fraction", False),
    ("risk_adjusted_cost", True),
    ("runtime", True),
)


def collect_phase3_result_rows(phase3_root: Path | str) -> pd.DataFrame:
    """Collect Phase 3 repeat/result rows using the final-table input layout."""

    root = Path(phase3_root)
    paths = list((root / "public_benchmarks").glob("*/scenario_results.csv"))
    paths += list(root.glob("*/baselines/repeat_metrics.csv"))
    paths += list((root / "public_benchmarks").glob("*/baselines/repeat_metrics.csv"))
    paths += list((root / "public_benchmarks").glob("*/decoded/qci_repeat_metrics.csv"))

    frames: list[pd.DataFrame] = []
    for path in sorted(set(paths)):
        try:
            frame = pd.read_csv(path)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            continue
        if frame.empty:
            continue
        if "dataset" not in frame.columns:
            frame["dataset"] = path.parts[-3] if "public_benchmarks" in path.parts else path.parent.parent.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def build_phase3_method_summary(phase3_root: Path | str) -> pd.DataFrame:
    """Build method-level Phase 3 metrics from existing result rows."""

    rows = collect_phase3_result_rows(phase3_root)
    required = {"scenario_probability", "expected_cost_component", "method_name", "dataset"}
    if rows.empty or not required.issubset(rows.columns):
        return pd.DataFrame()
    return summarize_phase3_results(rows)


def canonicalize_challenge_metrics(summary: pd.DataFrame) -> pd.DataFrame:
    """Add canonical challenge scoring metric columns with stable fallbacks."""

    frame = summary.copy()
    if frame.empty:
        return frame

    def ensure_column(target: str, candidates: list[str], default: float = 0.0) -> None:
        if target in frame.columns:
            frame[target] = pd.to_numeric(frame[target], errors="coerce")
            return
        for candidate in candidates:
            if candidate in frame.columns:
                frame[target] = pd.to_numeric(frame[candidate], errors="coerce")
                return
        frame[target] = float(default)

    ensure_column("critical_energy_not_served_kwh", ["critical_ens_kwh"], 0.0)
    ensure_column("max_fraction_customers_unserved_per_hour", ["max_customers_unserved"], 0.0)
    ensure_column(
        "total_hours_critical_infrastructure_unserved",
        ["total_critical_infrastructure_unserved_hours_proxy", "critical_infra_unserved_hours"],
        0.0,
    )
    ensure_column("feasibility_after_repair", ["feasibility_rate", "feasibility_pass"], 0.0)
    ensure_column("risk_adjusted_cost", ["risk_cost"], 0.0)
    ensure_column("expected_operating_cost", ["expected_cost_component"], 0.0)
    ensure_column("total_energy_not_served", ["energy_not_served_kwh", "total_energy_not_served_kwh"], 0.0)
    ensure_column("critical_load_served_fraction", ["critical_served_fraction"], 0.0)

    runtime = pd.Series(np.nan, index=frame.index, dtype="float64")
    if "time_to_good_solution" in frame.columns:
        time_to_good = pd.to_numeric(frame["time_to_good_solution"], errors="coerce").mask(lambda values: values < 0)
        runtime = runtime.fillna(time_to_good)
    for candidate in ("median_runtime_seconds", "runtime_seconds", "wall_clock_runtime_seconds"):
        if candidate in frame.columns:
            runtime = runtime.fillna(pd.to_numeric(frame[candidate], errors="coerce"))
    if runtime.isna().all():
        runtime = pd.Series(0.0, index=frame.index)
    frame["runtime"] = runtime

    for column in [
        "critical_energy_not_served_kwh",
        "max_fraction_customers_unserved_per_hour",
        "total_hours_critical_infrastructure_unserved",
        "feasibility_after_repair",
        "risk_adjusted_cost",
        "expected_operating_cost",
        "total_energy_not_served",
        "critical_load_served_fraction",
        "runtime",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame


def _normalized_badness(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(0.0, index=values.index)
    minimum = float(numeric.min(skipna=True))
    maximum = float(numeric.max(skipna=True))
    if np.isclose(maximum, minimum):
        return pd.Series(0.0, index=values.index)
    normalized = (numeric - minimum) / (maximum - minimum)
    return normalized.fillna(1.0).clip(lower=0.0, upper=1.0)


def add_weighted_scores(summary: pd.DataFrame) -> pd.DataFrame:
    """Add lower-is-better weighted challenge scores per dataset."""

    frame = canonicalize_challenge_metrics(summary)
    if frame.empty:
        return frame

    score = pd.Series(0.0, index=frame.index)
    for metric, weight in WEIGHTED_TERMS:
        normalized_column = f"normalized_{metric}"
        frame[normalized_column] = frame.groupby("dataset", group_keys=False)[metric].transform(_normalized_badness)
        score = score + weight * frame[normalized_column]

    feasibility = frame["feasibility_after_repair"].fillna(0.0).clip(lower=0.0, upper=1.0)
    frame["infeasibility_penalty"] = INFEASIBILITY_PENALTY_WEIGHT * (1.0 - feasibility)
    frame["weighted_challenge_score"] = score + frame["infeasibility_penalty"]
    frame["weighted_challenge_rank"] = frame.groupby("dataset")["weighted_challenge_score"].rank(
        method="min",
        ascending=True,
    )
    return frame


def add_lexicographic_scores(summary: pd.DataFrame) -> pd.DataFrame:
    """Add lower-is-better lexicographic ordinal scores per dataset."""

    frame = canonicalize_challenge_metrics(summary)
    if frame.empty:
        return frame

    rank = pd.Series(index=frame.index, dtype="float64")
    for _dataset, group in frame.groupby("dataset", sort=True):
        sort_frame = group.copy()
        sort_columns: list[str] = []
        ascending: list[bool] = []
        for metric, asc in LEXICOGRAPHIC_ORDER:
            column = f"_lex_{metric}"
            values = pd.to_numeric(sort_frame[metric], errors="coerce")
            fill = -np.inf if not asc else np.inf
            sort_frame[column] = values.fillna(fill)
            sort_columns.append(column)
            ascending.append(asc)
        sort_frame["_lex_method_name"] = sort_frame["method_name"].astype(str)
        ordered = sort_frame.sort_values(sort_columns + ["_lex_method_name"], ascending=ascending + [True])
        rank.loc[ordered.index] = np.arange(1, len(ordered) + 1, dtype=float)

    frame["lexicographic_challenge_score"] = rank - 1.0
    frame["lexicographic_challenge_rank"] = rank
    return frame


def _annotate_best_methods(frame: pd.DataFrame, *, score_column: str, rank_column: str) -> pd.DataFrame:
    annotated = frame.copy()
    annotated["challenge_rank"] = annotated[rank_column].astype(float)
    annotated["challenge_score"] = pd.to_numeric(annotated[score_column], errors="coerce")
    annotated["best_method_by_challenge_score"] = ""
    annotated["qci_minus_best_challenge_score"] = np.nan
    annotated["qci_outcome_by_challenge_score"] = "inconclusive_no_qci"

    for dataset, group in annotated.groupby("dataset", sort=True):
        scores = pd.to_numeric(group["challenge_score"], errors="coerce")
        if scores.dropna().empty:
            continue
        best = float(scores.min())
        tolerance = max(1e-9, abs(best) * 1e-9)
        best_mask = (scores - best).abs() <= tolerance
        best_methods = sorted(group.loc[best_mask, "method_name"].astype(str).unique())
        qci = group[group["method_name"].astype(str).str.contains(QCI_METHOD_PATTERN, case=False, regex=True, na=False)]
        outcome = "inconclusive_no_qci"
        qci_minus = np.nan
        if not qci.empty:
            qci_score = float(pd.to_numeric(qci["challenge_score"], errors="coerce").min())
            qci_minus = qci_score - best
            if qci_minus <= tolerance:
                non_qci_best = group.loc[best_mask & ~group.index.isin(qci.index)]
                outcome = "qci_tie" if not non_qci_best.empty else "qci_win"
            else:
                outcome = "qci_loss"
        annotated.loc[group.index, "best_method_by_challenge_score"] = "; ".join(best_methods)
        annotated.loc[group.index, "qci_minus_best_challenge_score"] = qci_minus
        annotated.loc[group.index, "qci_outcome_by_challenge_score"] = outcome

    annotated["challenge_rank"] = annotated["challenge_rank"].astype("Int64")
    return annotated


def score_challenge_summary(summary: pd.DataFrame, mode: ScoreMode = "both") -> pd.DataFrame:
    """Return challenge-scored method summaries.

    If ``mode`` is ``both``, the returned frame contains one row per
    dataset/method/score_mode pair.
    """

    if summary.empty:
        return pd.DataFrame()
    modes = ["weighted", "lexicographic"] if mode == "both" else [mode]
    frames: list[pd.DataFrame] = []
    for item in modes:
        if item == "weighted":
            scored = add_weighted_scores(summary)
            scored = _annotate_best_methods(
                scored,
                score_column="weighted_challenge_score",
                rank_column="weighted_challenge_rank",
            )
        elif item == "lexicographic":
            scored = add_lexicographic_scores(summary)
            scored = _annotate_best_methods(
                scored,
                score_column="lexicographic_challenge_score",
                rank_column="lexicographic_challenge_rank",
            )
        else:
            raise ValueError(f"Unsupported challenge score mode: {item}")
        scored["score_mode"] = item
        frames.append(scored)
    result = pd.concat(frames, ignore_index=True, sort=False)
    preferred = [
        "score_mode",
        "dataset",
        "method_name",
        "challenge_score",
        "challenge_rank",
        "best_method_by_challenge_score",
        "qci_minus_best_challenge_score",
        "qci_outcome_by_challenge_score",
        "critical_energy_not_served_kwh",
        "total_hours_critical_infrastructure_unserved",
        "max_fraction_customers_unserved_per_hour",
        "total_energy_not_served",
        "critical_load_served_fraction",
        "feasibility_after_repair",
        "risk_adjusted_cost",
        "expected_operating_cost",
        "runtime",
        "weighted_challenge_score",
        "weighted_challenge_rank",
        "lexicographic_challenge_score",
        "lexicographic_challenge_rank",
    ]
    remaining = [column for column in result.columns if column not in preferred]
    return result[[column for column in preferred if column in result.columns] + remaining].sort_values(
        ["score_mode", "dataset", "challenge_rank", "method_name"],
        kind="stable",
    )


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a compact GitHub-flavored Markdown table."""

    if frame.empty:
        return "_No rows available._\n"
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False):
        values: list[str] = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def challenge_score_markdown(scored: pd.DataFrame) -> str:
    """Build the judge-facing Markdown challenge score summary."""

    if scored.empty:
        return "# Challenge Score Summary\n\n_No challenge score rows available._\n"
    display_columns = [
        "score_mode",
        "dataset",
        "method_name",
        "challenge_score",
        "challenge_rank",
        "best_method_by_challenge_score",
        "qci_minus_best_challenge_score",
        "qci_outcome_by_challenge_score",
        "critical_energy_not_served_kwh",
        "total_hours_critical_infrastructure_unserved",
        "max_fraction_customers_unserved_per_hour",
        "critical_load_served_fraction",
        "risk_adjusted_cost",
        "runtime",
    ]
    display = scored[[column for column in display_columns if column in scored.columns]].copy()
    return (
        "# Challenge Score Summary\n\n"
        "Lower challenge scores are better. Weighted scores normalize every metric within each benchmark dataset; "
        "lexicographic scores follow feasibility, critical ENS, critical infrastructure outage hours, max customers "
        "unserved, critical-load served, risk cost, and runtime in that order.\n\n"
        + markdown_table(display)
    )
