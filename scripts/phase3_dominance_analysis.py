#!/usr/bin/env python
"""Analyze Phase 3 QCi/CMPO dominance against classical baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PHASE3_ROOT = Path("results") / "phase3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build win/loss/inconclusive and Pareto-frontier evidence from Phase 3 final tables."
    )
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 final tables.")
    parser.add_argument(
        "--public-benchmarks",
        action="store_true",
        help="Analyze the judge-facing public benchmark table set.",
    )
    parser.add_argument("--include-direct-qci", action="store_true", help="Include direct-QCi rows already present in final tables.")
    parser.add_argument("--include-cmpo-v2", action="store_true", help="Include CMPO-V2 rows already present in final tables.")
    parser.add_argument("--include-hybrid", action="store_true", help="Include full hybrid rows when present in final tables.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned inputs and outputs without writing files.")
    return parser


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _classify(row: pd.Series) -> str:
    qci = row.get("qci_risk_adjusted_cost")
    baseline = row.get("best_baseline_risk_adjusted_cost")
    if pd.isna(qci) or pd.isna(baseline):
        return "inconclusive"
    tolerance = max(1e-9, abs(float(baseline)) * 1e-6)
    delta = float(qci) - float(baseline)
    if abs(delta) <= tolerance:
        return "tie"
    return "qci_win" if delta < 0 else "qci_loss"


def _analysis(table1: pd.DataFrame, pareto: pd.DataFrame) -> pd.DataFrame:
    if table1.empty:
        return pd.DataFrame(
            columns=[
                "dataset",
                "qci_method",
                "best_baseline_method",
                "qci_risk_adjusted_cost",
                "best_baseline_risk_adjusted_cost",
                "qci_minus_best_baseline",
                "outcome",
                "qci_on_pareto_frontier",
            ]
        )
    rows = table1.copy()
    rows["outcome"] = rows.apply(_classify, axis=1)
    qci_pareto_datasets = set()
    if not pareto.empty and {"dataset", "method_name"}.issubset(pareto.columns):
        qci_pareto = pareto[pareto["method_name"].astype(str).str.contains("qci|dirac", case=False, regex=True)]
        qci_pareto_datasets = set(qci_pareto["dataset"].astype(str))
    rows["qci_on_pareto_frontier"] = rows["dataset"].astype(str).isin(qci_pareto_datasets)
    return rows


def _write_markdown(frame: pd.DataFrame, path: Path) -> None:
    counts = frame["outcome"].value_counts().to_dict() if "outcome" in frame else {}
    qci_pareto = bool(frame.get("qci_on_pareto_frontier", pd.Series(dtype=bool)).astype(bool).any()) if not frame.empty else False
    lines = [
        "# Phase 3 Dominance Analysis",
        "",
        f"- QCi wins: {counts.get('qci_win', 0)}",
        f"- QCi ties: {counts.get('tie', 0)}",
        f"- QCi losses: {counts.get('qci_loss', 0)}",
        f"- Inconclusive datasets: {counts.get('inconclusive', 0)}",
        f"- QCi/CMPO appears on cost-resilience Pareto frontier: {qci_pareto}",
        "",
        "## Dataset Outcomes",
        "",
    ]
    if frame.empty:
        lines.append("_No dominance rows available._")
    else:
        columns = [
            "dataset",
            "qci_method",
            "best_baseline_method",
            "qci_risk_adjusted_cost",
            "best_baseline_risk_adjusted_cost",
            "qci_minus_best_baseline",
            "outcome",
            "qci_on_pareto_frontier",
        ]
        available = [column for column in columns if column in frame.columns]
        view = frame[available]
        lines.append("| " + " | ".join(available) + " |")
        lines.append("| " + " | ".join("---" for _ in available) + " |")
        for row in view.itertuples(index=False):
            values = [f"{value:.6g}" if isinstance(value, float) else str(value) for value in row]
            lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _challenge_analysis(scored: pd.DataFrame, pareto: pd.DataFrame) -> pd.DataFrame:
    required = {"score_mode", "dataset", "method_name", "challenge_score"}
    if scored.empty or not required.issubset(scored.columns):
        return pd.DataFrame()
    pareto_keys = (
        set(zip(pareto["dataset"].astype(str), pareto["method_name"].astype(str), strict=False))
        if not pareto.empty and {"dataset", "method_name"}.issubset(pareto.columns)
        else set()
    )
    rows: list[dict[str, object]] = []
    for (score_mode, dataset), group in scored.groupby(["score_mode", "dataset"], sort=True):
        qci_mask = group["method_name"].astype(str).str.contains("qci|dirac", case=False, regex=True)
        qci = group[qci_mask].sort_values(["challenge_score", "method_name"])
        classical = group[~qci_mask].sort_values(["challenge_score", "method_name"])
        if qci.empty or classical.empty:
            continue
        best_qci = qci.iloc[0]
        best_classical = classical.iloc[0]
        delta = float(best_qci["challenge_score"]) - float(best_classical["challenge_score"])
        tolerance = max(1e-9, abs(float(best_classical["challenge_score"])) * 1e-9)
        outcome = "qci_tie" if abs(delta) <= tolerance else ("qci_win" if delta < 0 else "qci_loss")
        row: dict[str, object] = {
            "score_mode": score_mode,
            "dataset": dataset,
            "best_qci_method": best_qci["method_name"],
            "best_classical_method": best_classical["method_name"],
            "qci_challenge_score": float(best_qci["challenge_score"]),
            "best_classical_challenge_score": float(best_classical["challenge_score"]),
            "qci_minus_best_classical_challenge_score": delta,
            "outcome": outcome,
            "qci_on_cost_critical_ens_pareto_frontier": (
                str(dataset),
                str(best_qci["method_name"]),
            )
            in pareto_keys,
        }
        for metric in (
            "critical_energy_not_served_kwh",
            "critical_load_served_fraction",
            "max_fraction_customers_unserved_per_hour",
            "risk_adjusted_cost",
            "feasibility_after_repair",
        ):
            if metric in group.columns:
                row[f"qci_{metric}"] = best_qci[metric]
                row[f"best_classical_{metric}"] = best_classical[metric]
        rows.append(row)
    return pd.DataFrame(rows)


def _write_challenge_markdown(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Final Challenge-Aligned Dominance Analysis",
        "",
        "Comparisons use repeat-balanced, per-benchmark normalization. Lower challenge scores are better.",
        "The Pareto flag uses risk-adjusted cost and critical energy not served.",
        "",
    ]
    if frame.empty:
        lines.append("_No matched QCi/classical dominance rows available._")
    else:
        for score_mode, group in frame.groupby("score_mode", sort=True):
            counts = group["outcome"].value_counts().to_dict()
            lines += [
                f"## {str(score_mode).title()} Score",
                "",
                f"- QCi wins: {counts.get('qci_win', 0)}",
                f"- QCi ties: {counts.get('qci_tie', 0)}",
                f"- QCi losses: {counts.get('qci_loss', 0)}",
                "",
            ]
        columns = [
            "score_mode",
            "dataset",
            "best_qci_method",
            "best_classical_method",
            "qci_challenge_score",
            "best_classical_challenge_score",
            "qci_minus_best_classical_challenge_score",
            "outcome",
            "qci_on_cost_critical_ens_pareto_frontier",
        ]
        available = [column for column in columns if column in frame.columns]
        lines += ["## Dataset Outcomes", "", "| " + " | ".join(available) + " |"]
        lines.append("| " + " | ".join("---" for _ in available) + " |")
        for row in frame[available].itertuples(index=False):
            values = [f"{value:.6g}" if isinstance(value, float) else str(value) for value in row]
            lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.phase3_root)
    table_dir = root / "final_tables"
    outputs = {
        "dominance_csv": table_dir / "dominance_analysis.csv",
        "dominance_md": table_dir / "dominance_analysis.md",
        "final_dominance_v2_csv": table_dir / "final_dominance_v2.csv",
        "final_dominance_v2_md": table_dir / "final_dominance_v2.md",
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "inputs": [str(table_dir / "table1_qci_vs_best_baselines.csv"), str(table_dir / "pareto_frontier.csv")],
                    "outputs": {key: str(value) for key, value in outputs.items()},
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return
    table_dir.mkdir(parents=True, exist_ok=True)
    frame = _analysis(_read(table_dir / "table1_qci_vs_best_baselines.csv"), _read(table_dir / "pareto_frontier.csv"))
    frame.to_csv(outputs["dominance_csv"], index=False)
    _write_markdown(frame, outputs["dominance_md"])
    challenge = _challenge_analysis(
        _read(table_dir / "final_challenge_score_table.csv"),
        _read(table_dir / "final_pareto_frontier_v2.csv"),
    )
    challenge.to_csv(outputs["final_dominance_v2_csv"], index=False)
    _write_challenge_markdown(challenge, outputs["final_dominance_v2_md"])
    print(
        json.dumps(
            {key: str(value) for key, value in outputs.items()}
            | {"risk_cost_rows": len(frame), "challenge_rows": len(challenge)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
