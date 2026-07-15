#!/usr/bin/env python
"""Compare existing CMPO-V2 and hybrid QCi smoke results without rerunning QCi."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.challenge_score import add_weighted_scores, markdown_table  # noqa: E402


DEFAULT_DIRECT = Path("results/phase3/cmpo_v2_smoke/decoded")
DEFAULT_HYBRID = Path("results/phase3/hybrid_smoke/comparison")
DEFAULT_OUTPUT = Path("results/phase3/smoke_comparison")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an evidence-based CMPO-V2 versus hybrid QCi smoke comparison from existing decoded metrics."
    )
    parser.add_argument("--cmpo-v2-dir", default=str(DEFAULT_DIRECT), help="CMPO-V2 decoded result directory.")
    parser.add_argument("--hybrid-dir", default=str(DEFAULT_HYBRID), help="Hybrid projection result directory.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Smoke comparison output directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print input availability without writing outputs.")
    return parser


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def score_smoke_samples(direct: pd.DataFrame, hybrid: pd.DataFrame) -> pd.DataFrame:
    """Apply the challenge-weighted score jointly within each benchmark."""

    frames: list[pd.DataFrame] = []
    for formulation, source in (("cmpo_v2", direct), ("hybrid", hybrid)):
        if source.empty:
            continue
        frame = source.copy()
        frame["formulation"] = formulation
        frame["method_name"] = "CMPO-V2 Direct QCi" if formulation == "cmpo_v2" else "Hybrid QCi + Projection"
        if "total_hours_critical_infrastructure_unserved" not in frame.columns:
            frame["total_hours_critical_infrastructure_unserved"] = frame.get(
                "total_critical_infrastructure_unserved_hours_proxy",
                0.0,
            )
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    scored = add_weighted_scores(combined)
    scored["challenge_score"] = scored["weighted_challenge_score"]
    return scored


def _failure_count(path: Path) -> int:
    frame = _read_csv(path)
    if frame.empty:
        return 0
    if "job_id" in frame.columns:
        populated = frame["job_id"].fillna("").astype(str)
        unique = populated[populated.ne("")].nunique()
        return int(unique if unique else len(frame))
    return int(len(frame))


def _summary_rows(scored: pd.DataFrame, failure_counts: dict[str, int]) -> pd.DataFrame:
    if scored.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (dataset, formulation), group in scored.groupby(["dataset", "formulation"], sort=True):
        rows.append(_summary_row(dataset, formulation, group, failure_counts.get(formulation, 0)))
    for formulation, group in scored.groupby("formulation", sort=True):
        rows.append(_summary_row("ALL", formulation, group, failure_counts.get(formulation, 0)))
    return pd.DataFrame(rows)


def _summary_row(dataset: str, formulation: str, group: pd.DataFrame, failed_jobs: int) -> dict[str, Any]:
    completed_jobs = int(group["job_id"].fillna("").astype(str).replace("", pd.NA).nunique())
    return {
        "dataset": dataset,
        "formulation": formulation,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs if dataset == "ALL" else 0,
        "sample_count": int(len(group)),
        "feasibility_rate": float(group["feasibility_after_repair"].astype(float).mean()),
        "challenge_score_best": float(group["challenge_score"].min()),
        "challenge_score_median": float(group["challenge_score"].median()),
        "challenge_score_mean": float(group["challenge_score"].mean()),
        "challenge_score_std": float(group["challenge_score"].std(ddof=0)),
        "challenge_score_variance": float(group["challenge_score"].var(ddof=0)),
        "critical_energy_not_served_best": float(group["critical_energy_not_served_kwh"].min()),
        "critical_energy_not_served_median": float(group["critical_energy_not_served_kwh"].median()),
        "critical_load_served_fraction_best": float(group["critical_load_served_fraction"].max()),
        "critical_load_served_fraction_median": float(group["critical_load_served_fraction"].median()),
        "max_customers_unserved_best": float(group["max_fraction_customers_unserved_per_hour"].min()),
        "max_customers_unserved_median": float(group["max_fraction_customers_unserved_per_hour"].median()),
        "critical_infrastructure_outage_proxy_best": float(
            group["total_hours_critical_infrastructure_unserved"].min()
        ),
        "critical_infrastructure_outage_proxy_median": float(
            group["total_hours_critical_infrastructure_unserved"].median()
        ),
        "risk_adjusted_cost_best": float(group["risk_adjusted_cost"].min()),
        "risk_adjusted_cost_median": float(group["risk_adjusted_cost"].median()),
        "runtime_seconds_median": float(group["runtime"].median()),
        "qci_energy_variance": float(pd.to_numeric(group["qci_energy"], errors="coerce").var(ddof=0)),
    }


def _better(summary: pd.DataFrame, column: str, *, higher: bool = False) -> str:
    overall = summary[summary["dataset"].eq("ALL")].set_index("formulation")
    if not {"cmpo_v2", "hybrid"}.issubset(overall.index):
        return "inconclusive"
    direct = float(overall.loc["cmpo_v2", column])
    hybrid = float(overall.loc["hybrid", column])
    tolerance = max(1e-9, max(abs(direct), abs(hybrid)) * 1e-9)
    if abs(direct - hybrid) <= tolerance:
        return "tie"
    if higher:
        return "cmpo_v2" if direct > hybrid else "hybrid"
    return "cmpo_v2" if direct < hybrid else "hybrid"


def _recommendation(summary: pd.DataFrame) -> str:
    median_winner = _better(summary, "challenge_score_median")
    best_winner = _better(summary, "challenge_score_best")
    ens_winner = _better(summary, "critical_energy_not_served_median")
    served_winner = _better(summary, "critical_load_served_fraction_median", higher=True)
    if median_winner == best_winner == ens_winner == served_winner == "cmpo_v2":
        return "run full CMPO-V2"
    if median_winner == best_winner == ens_winner == served_winner == "hybrid":
        return "run full hybrid"
    return "run both"


def _markdown(summary: pd.DataFrame, verdict: dict[str, Any]) -> str:
    return (
        "# CMPO-V2 vs Hybrid QCi Smoke Comparison\n\n"
        "This report compares only completed, decoded smoke samples. Lower challenge score is better. "
        "No superiority claim is made when the evidence is mixed or incomplete.\n\n"
        "## Verdict\n\n"
        f"- Better median challenge score: `{verdict['better_median_challenge_score']}`\n"
        f"- Better best challenge score: `{verdict['better_best_challenge_score']}`\n"
        f"- Lower median critical ENS: `{verdict['lower_critical_ens']}`\n"
        f"- Higher median critical-load served: `{verdict['higher_critical_load_served']}`\n"
        f"- Hybrid projection successful: `{str(verdict['hybrid_projection_success']).lower()}`\n"
        f"- Recommendation: **{verdict['recommendation']}**\n\n"
        "## Results\n\n"
        + markdown_table(summary)
    )


def build_smoke_comparison(
    direct_dir: Path,
    hybrid_dir: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    direct_path = direct_dir / "qci_repeat_metrics.csv"
    hybrid_path = hybrid_dir / "projection_metrics.csv"
    direct = _read_csv(direct_path)
    hybrid = _read_csv(hybrid_path)
    plan = {
        "cmpo_v2_metrics": str(direct_path),
        "hybrid_metrics": str(hybrid_path),
        "cmpo_v2_rows": int(len(direct)),
        "hybrid_rows": int(len(hybrid)),
        "output_dir": str(output_dir),
        "dry_run": dry_run,
    }
    if dry_run:
        return plan
    if direct.empty or hybrid.empty:
        raise ValueError("Both CMPO-V2 decoded metrics and hybrid projection metrics are required.")
    scored = score_smoke_samples(direct, hybrid)
    failure_counts = {
        "cmpo_v2": _failure_count(direct_dir / "qci_failure_report.csv"),
        "hybrid": _failure_count(hybrid_dir / "projection_failures.csv"),
    }
    summary = _summary_rows(scored, failure_counts)
    hybrid_projection_success = bool(
        len(hybrid) > 0
        and failure_counts["hybrid"] == 0
        and hybrid.get("feasibility_after_repair", pd.Series(dtype=bool)).astype(bool).all()
    )
    verdict = {
        "better_median_challenge_score": _better(summary, "challenge_score_median"),
        "better_best_challenge_score": _better(summary, "challenge_score_best"),
        "lower_critical_ens": _better(summary, "critical_energy_not_served_median"),
        "higher_critical_load_served": _better(
            summary,
            "critical_load_served_fraction_median",
            higher=True,
        ),
        "hybrid_projection_success": hybrid_projection_success,
        "recommendation": _recommendation(summary),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cmpo_v2_vs_hybrid.csv"
    md_path = output_dir / "cmpo_v2_vs_hybrid.md"
    summary.to_csv(csv_path, index=False)
    md_path.write_text(_markdown(summary, verdict), encoding="utf-8")
    return plan | verdict | {"comparison_csv": str(csv_path), "comparison_md": str(md_path)}


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = build_smoke_comparison(
            Path(args.cmpo_v2_dir),
            Path(args.hybrid_dir),
            Path(args.output_dir),
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
