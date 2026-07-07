#!/usr/bin/env python
"""Build required benchmark-first Phase 3 final tables from result CSVs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.benchmark_validation import normalize_pglib_benchmark_outputs, write_public_benchmark_manifests  # noqa: E402
from cmpo.challenge_score import score_challenge_summary  # noqa: E402
from cmpo.phase3_metrics import qci_repeat_distribution, summarize_phase3_results  # noqa: E402


PHASE3_ROOT = Path("results") / "phase3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Phase 3 benchmark-first outputs and write final tables.")
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 outputs.")
    parser.add_argument(
        "--public-benchmarks",
        action="store_true",
        help="Build the judge-facing public benchmark table set. Kept as an explicit flag for reproducible command logs.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print table inputs without writing files.")
    return parser


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows available._\n"
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False):
        values = [f"{value:.6g}" if isinstance(value, float) else str(value) for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _collect_rows(root: Path) -> pd.DataFrame:
    paths = list((root / "public_benchmarks").glob("*/scenario_results.csv"))
    paths += list(root.glob("*/baselines/repeat_metrics.csv"))
    paths += list((root / "public_benchmarks").glob("*/baselines/repeat_metrics.csv"))
    paths += list((root / "public_benchmarks").glob("*/decoded/qci_repeat_metrics.csv"))
    frames: list[pd.DataFrame] = []
    for path in sorted(set(paths)):
        try:
            frame = pd.read_csv(path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        if frame.empty:
            continue
        if "dataset" not in frame.columns:
            frame["dataset"] = path.parts[-3] if "public_benchmarks" in path.parts else path.parts[-3]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _summary(frame: pd.DataFrame) -> pd.DataFrame:
    needed = {"scenario_probability", "expected_cost_component", "method_name", "dataset"}
    if needed.issubset(frame.columns):
        return summarize_phase3_results(frame)
    return pd.DataFrame()


def _table1(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(
            columns=[
                "dataset",
                "qci_method",
                "qci_risk_adjusted_cost",
                "best_baseline_method",
                "best_baseline_risk_adjusted_cost",
                "qci_minus_best_baseline",
                "qci_on_pareto_frontier",
            ]
        )
    rows = []
    for dataset, group in summary.groupby("dataset", sort=True):
        qci = group[group["method_name"].astype(str).str.contains("qci|dirac", case=False, regex=True)]
        baselines = group[~group.index.isin(qci.index)]
        best_baseline = baselines.sort_values("risk_adjusted_cost").head(1)
        best_qci = qci.sort_values("risk_adjusted_cost").head(1)
        rows.append(
            {
                "dataset": dataset,
                "qci_method": "" if best_qci.empty else best_qci.iloc[0]["method_name"],
                "qci_risk_adjusted_cost": float("nan") if best_qci.empty else float(best_qci.iloc[0]["risk_adjusted_cost"]),
                "best_baseline_method": "" if best_baseline.empty else best_baseline.iloc[0]["method_name"],
                "best_baseline_risk_adjusted_cost": float("nan")
                if best_baseline.empty
                else float(best_baseline.iloc[0]["risk_adjusted_cost"]),
                "qci_minus_best_baseline": float("nan")
                if best_qci.empty or best_baseline.empty
                else float(best_qci.iloc[0]["risk_adjusted_cost"] - best_baseline.iloc[0]["risk_adjusted_cost"]),
                "qci_on_pareto_frontier": False,
            }
        )
    return pd.DataFrame(rows)


def _table3(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "scenario" not in frame.columns:
        return pd.DataFrame()
    metrics = [
        "expected_operating_cost",
        "risk_adjusted_cost",
        "critical_load_served_fraction",
        "critical_energy_not_served_kwh",
        "energy_not_served_kwh",
        "max_fraction_customers_unserved_per_hour",
        "total_critical_infrastructure_unserved_hours_proxy",
        "runtime_seconds",
    ]
    present = [item for item in metrics if item in frame.columns]
    return (
        frame.groupby(["dataset", "scenario", "method_name"], dropna=False)[present]
        .median(numeric_only=True)
        .reset_index()
        .sort_values(["dataset", "scenario", "risk_adjusted_cost" if "risk_adjusted_cost" in present else present[0]])
    )


def _table4(frame: pd.DataFrame, root: Path) -> pd.DataFrame:
    rows = []
    model_stats_paths = list((root / "public_benchmarks").glob("*/model_stats.csv")) + list(root.glob("*/model_stats.csv"))
    for path in sorted(set(model_stats_paths)):
        try:
            stats = pd.read_csv(path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        dataset = path.parent.name
        if "dataset" in stats.columns:
            dataset = str(stats["dataset"].iloc[0])
        rows.append(
            {
                "dataset": dataset,
                "payload_count": len(stats),
                "native_cubic_variable_count_median": float(stats.get("variable_count", pd.Series([0])).median()),
                "native_cubic_term_count_median": float(stats.get("term_count", pd.Series([0])).median()),
                "native_max_degree": float(stats.get("degree", pd.Series([0])).max()),
            }
        )
    table = pd.DataFrame(rows)
    if not frame.empty and "auxiliary_variable_count" in frame.columns:
        qubo = frame[frame["method_name"].astype(str).str.contains("qubo", case=False, regex=False)]
        if not qubo.empty:
            q = (
                qubo.groupby("dataset")
                .agg(
                    qubo_auxiliary_variable_count_median=("auxiliary_variable_count", "median"),
                    qubo_variable_blowup_median=("variable_blowup", "median"),
                    qubo_approximation_error_median=("approximation_error", "median"),
                )
                .reset_index()
            )
            table = table.merge(q, on="dataset", how="outer") if not table.empty else q
    return table


def _encoding_efficiency(frame: pd.DataFrame, root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    benchmark_root = root / "public_benchmarks"
    for benchmark_dir in sorted(path for path in benchmark_root.glob("pglib_case*") if path.is_dir()):
        full_manifest = benchmark_dir / "qci_payload_manifest.csv"
        qci_fit_manifest = benchmark_dir / "qci_fit_payload_manifest.csv"
        full = _read_frame(full_manifest)
        qci_fit = _read_frame(qci_fit_manifest)
        if full.empty and qci_fit.empty:
            continue
        row: dict[str, object] = {
            "benchmark": benchmark_dir.name,
            "full_payload_count": int(len(full)),
            "qci_fit_payload_count": int(len(qci_fit)),
            "full_max_variables": float(full["variable_count"].max()) if "variable_count" in full else float("nan"),
            "qci_fit_max_variables": float(qci_fit["variable_count"].max()) if "variable_count" in qci_fit else float("nan"),
            "full_max_degree": float(full["degree"].max()) if "degree" in full else float("nan"),
            "qci_fit_max_degree": float(qci_fit["degree"].max()) if "degree" in qci_fit else float("nan"),
            "qci_executable": bool(not qci_fit.empty and qci_fit.get("variable_count", pd.Series([999])).max() <= 132 and qci_fit.get("degree", pd.Series([99])).max() <= 3),
        }
        if row["full_max_variables"] == row["full_max_variables"] and row["qci_fit_max_variables"] == row["qci_fit_max_variables"]:
            full_max = float(row["full_max_variables"])
            fit_max = float(row["qci_fit_max_variables"])
            row["variable_reduction_fraction"] = 0.0 if full_max <= 0 else max(0.0, (full_max - fit_max) / full_max)
        rows.append(row)
    table = pd.DataFrame(rows)
    if not frame.empty and "auxiliary_variable_count" in frame.columns:
        qubo = frame[frame["method_name"].astype(str).str.contains("qubo", case=False, regex=False)]
        if not qubo.empty:
            q = (
                qubo.groupby("dataset")
                .agg(
                    qubo_auxiliary_variable_count_median=("auxiliary_variable_count", "median"),
                    qubo_variable_blowup_median=("variable_blowup", "median"),
                    qubo_approximation_error_median=("approximation_error", "median"),
                )
                .reset_index()
                .rename(columns={"dataset": "benchmark_dataset"})
            )
            table = table.merge(q, left_on="benchmark", right_on="benchmark_dataset", how="outer") if not table.empty else q
    return table


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _resource_usage(frame: pd.DataFrame, root: Path) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    aggregations = {
        "runtime_seconds": "sum",
        "wall_clock_runtime_seconds": "sum" if "wall_clock_runtime_seconds" in frame.columns else "sum",
        "repeat": "nunique" if "repeat" in frame.columns else "count",
    }
    present = {key: value for key, value in aggregations.items() if key in frame.columns}
    usage = frame.groupby(["dataset", "method_name"], dropna=False).agg(present).reset_index()
    usage = usage.rename(columns={"repeat": "repeat_count", "runtime_seconds": "runtime_seconds_total"})
    return usage


def _win_tie_loss(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=["method_name", "wins", "ties", "losses"])
    rows = []
    methods = sorted(summary["method_name"].astype(str).unique())
    for method in methods:
        wins = ties = losses = 0
        for _dataset, group in summary.groupby("dataset"):
            best = float(group["risk_adjusted_cost"].min())
            row = group[group["method_name"].astype(str) == method]
            if row.empty:
                continue
            value = float(row.iloc[0]["risk_adjusted_cost"])
            if abs(value - best) <= max(1e-9, abs(best) * 1e-6):
                ties += 1
            elif value < best:
                wins += 1
            else:
                losses += 1
        rows.append({"method_name": method, "wins": wins, "ties": ties, "losses": losses})
    return pd.DataFrame(rows)


def _pareto(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    rows = []
    for dataset, group in summary.groupby("dataset", sort=True):
        for _, row in group.iterrows():
            dominated = group[
                (group["risk_adjusted_cost"] <= row["risk_adjusted_cost"])
                & (group["critical_load_served_fraction"] >= row["critical_load_served_fraction"])
                & (
                    (group["risk_adjusted_cost"] < row["risk_adjusted_cost"])
                    | (group["critical_load_served_fraction"] > row["critical_load_served_fraction"])
                )
            ]
            if dominated.empty:
                rows.append(row.to_dict() | {"pareto_frontier": True, "dataset": dataset})
    return pd.DataFrame(rows)


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.phase3_root)
    inputs = [str(path) for path in sorted(root.glob("**/*.csv"))]
    output_dir = root / "final_tables"
    if args.dry_run:
        print(json.dumps({"inputs": inputs, "output_dir": str(output_dir), "dry_run": True}, indent=2))
        return
    normalize_pglib_benchmark_outputs()
    manifest_paths = write_public_benchmark_manifests()
    combined = _collect_rows(root)
    summary = _summary(combined)
    ladder = pd.read_csv(manifest_paths["manifest"]) if Path(manifest_paths["manifest"]).exists() else pd.DataFrame()
    tables = {
        "table1_qci_vs_best_baselines": _table1(summary),
        "table2_public_benchmark_ladder": ladder,
        "table3_scenario_stress": _table3(combined),
        "table4_native_cubic_vs_qubo": _table4(combined, root),
        "table5_resource_usage": _resource_usage(combined, root),
        "win_tie_loss_matrix": _win_tie_loss(summary),
        "pareto_frontier": _pareto(summary),
        "encoding_efficiency": _encoding_efficiency(combined, root),
        "qci_repeat_distribution": qci_repeat_distribution(combined),
        "challenge_score_summary": score_challenge_summary(summary, mode="both"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, frame in tables.items():
        csv_path = output_dir / f"{name}.csv"
        frame.to_csv(csv_path, index=False)
        manifest.append({"table": name, "path": str(csv_path), "rows": len(frame)})
    final_md = output_dir / "final_tables.md"
    final_md.write_text(
        "# Phase 3 Final Tables\n\n"
        + "\n".join(f"## {item['table']}\n\n{_markdown_table(tables[item['table']])}" for item in manifest),
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), "tables": manifest}, indent=2))


if __name__ == "__main__":
    main()
