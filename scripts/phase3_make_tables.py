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
DATASET_ALIASES = {
    "pglib_case5_pjm": "pglib_case5_pjm_adapted",
    "pglib_case14_ieee": "pglib_case14_adapted",
    "pglib_case30_ieee": "pglib_case30_adapted",
    "pglib_case57_ieee": "pglib_case57_adapted",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Phase 3 benchmark-first outputs and write final tables.")
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 outputs.")
    parser.add_argument(
        "--public-benchmarks",
        action="store_true",
        help="Build the judge-facing public benchmark table set. Kept as an explicit flag for reproducible command logs.",
    )
    parser.add_argument(
        "--include-direct-qci",
        action="store_true",
        help="Include the existing direct CMPO + QCi public-benchmark results.",
    )
    parser.add_argument(
        "--include-cmpo-v2",
        action="store_true",
        help="Include full CMPO-V2 decoded results from results/phase3/cmpo_v2/decoded.",
    )
    parser.add_argument(
        "--include-hybrid",
        action="store_true",
        help="Include full hybrid projection metrics when results/phase3/hybrid/comparison exists.",
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


def _collect_rows(
    root: Path,
    *,
    include_direct_qci: bool = True,
    include_cmpo_v2: bool = False,
    include_hybrid: bool = False,
) -> pd.DataFrame:
    paths: list[tuple[Path, str]] = []
    paths += [(path, "classical_baseline") for path in (root / "public_benchmarks").glob("*/scenario_results.csv")]
    paths += [(path, "classical_baseline") for path in root.glob("*/baselines/repeat_metrics.csv")]
    paths += [
        (path, "classical_baseline")
        for path in (root / "public_benchmarks").glob("*/baselines/repeat_metrics.csv")
    ]
    if include_direct_qci:
        paths += [
            (path, "direct_qci")
            for path in (root / "public_benchmarks").glob("*/decoded/qci_repeat_metrics.csv")
        ]
    if include_cmpo_v2:
        paths.append((root / "cmpo_v2" / "decoded" / "qci_repeat_metrics.csv", "cmpo_v2"))
    if include_hybrid:
        paths.append((root / "hybrid" / "comparison" / "projection_metrics.csv", "hybrid"))

    frames: list[pd.DataFrame] = []
    for path, source_formulation in sorted(set(paths), key=lambda item: (str(item[0]), item[1])):
        try:
            frame = pd.read_csv(path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
        if frame.empty:
            continue
        if "dataset" not in frame.columns:
            frame["dataset"] = path.parts[-3] if "public_benchmarks" in path.parts else path.parts[-3]
        frame["dataset"] = frame["dataset"].astype(str).replace(DATASET_ALIASES)
        frame["source_formulation"] = source_formulation
        if source_formulation == "cmpo_v2":
            frame["method_name"] = "CMPO-V2 + QCi Dirac-3"
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False).drop_duplicates(ignore_index=True)


def _summary(frame: pd.DataFrame) -> pd.DataFrame:
    needed = {"scenario_probability", "expected_cost_component", "method_name", "dataset"}
    if needed.issubset(frame.columns):
        return summarize_phase3_results(frame)
    return pd.DataFrame()


def _balanced_summary(frame: pd.DataFrame, risk_lambda: float = 0.25) -> pd.DataFrame:
    """Summarize methods without allowing repeat counts to scale physical metrics."""

    required = {
        "dataset",
        "method_name",
        "scenario",
        "scenario_probability",
        "expected_cost_component",
        "critical_load_served_fraction",
        "energy_not_served_kwh",
        "critical_energy_not_served_kwh",
        "feasibility_pass",
        "runtime_seconds",
    }
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame()

    rows = frame.copy()
    if "payload_name" not in rows.columns:
        rows["payload_name"] = (
            rows["scenario"].astype(str) + "__" + rows.get("patch", pd.Series("patch", index=rows.index)).astype(str)
        )
    if "max_fraction_customers_unserved_per_hour" not in rows.columns:
        rows["max_fraction_customers_unserved_per_hour"] = 0.0
    if "total_hours_critical_infrastructure_unserved" not in rows.columns:
        rows["total_hours_critical_infrastructure_unserved"] = rows.get(
            "total_critical_infrastructure_unserved_hours_proxy",
            0.0,
        )
    if "wall_clock_runtime_seconds" not in rows.columns:
        rows["wall_clock_runtime_seconds"] = rows["runtime_seconds"]
    if "total_upgrade_cost" not in rows.columns:
        rows["total_upgrade_cost"] = 0.0

    numeric_columns = [
        "scenario_probability",
        "expected_cost_component",
        "critical_load_served_fraction",
        "energy_not_served_kwh",
        "critical_energy_not_served_kwh",
        "max_fraction_customers_unserved_per_hour",
        "total_hours_critical_infrastructure_unserved",
        "runtime_seconds",
        "wall_clock_runtime_seconds",
        "total_upgrade_cost",
    ]
    for column in numeric_columns:
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    rows["_feasible"] = rows["feasibility_pass"].astype(bool).astype(float)

    keys = ["dataset", "method_name", "payload_name"]
    representatives = (
        rows.groupby(keys, dropna=False)
        .agg(
            scenario=("scenario", "first"),
            patch=("patch", "first") if "patch" in rows.columns else ("scenario", "first"),
            scenario_probability=("scenario_probability", "median"),
            expected_cost_component=("expected_cost_component", "median"),
            critical_load_served_fraction=("critical_load_served_fraction", "median"),
            energy_not_served_kwh=("energy_not_served_kwh", "median"),
            critical_energy_not_served_kwh=("critical_energy_not_served_kwh", "median"),
            max_fraction_customers_unserved_per_hour=("max_fraction_customers_unserved_per_hour", "median"),
            total_hours_critical_infrastructure_unserved=("total_hours_critical_infrastructure_unserved", "median"),
            feasibility_after_repair=("_feasible", "mean"),
            median_runtime_seconds=("runtime_seconds", "median"),
            wall_clock_runtime_seconds=("wall_clock_runtime_seconds", "sum"),
            total_upgrade_cost=("total_upgrade_cost", "max"),
            sample_count=("method_name", "size"),
        )
        .reset_index()
    )

    summaries: list[dict[str, object]] = []
    weighted_metrics = [
        "expected_cost_component",
        "critical_load_served_fraction",
        "energy_not_served_kwh",
        "critical_energy_not_served_kwh",
        "total_hours_critical_infrastructure_unserved",
    ]
    for (dataset, method), group in representatives.groupby(["dataset", "method_name"], sort=True):
        scenario = (
            group.groupby("scenario", dropna=False)
            .agg(
                scenario_probability=("scenario_probability", "median"),
                **{metric: (metric, "mean") for metric in weighted_metrics},
            )
            .reset_index()
        )
        probability = scenario["scenario_probability"].fillna(0.0).clip(lower=0.0)
        probability_mass = float(probability.sum())
        if probability_mass <= 0.0:
            weights = pd.Series(1.0 / len(scenario), index=scenario.index)
        else:
            weights = probability / probability_mass
        weighted = {metric: float((scenario[metric] * weights).sum()) for metric in weighted_metrics}
        tail_threshold = float(scenario["expected_cost_component"].quantile(0.90))
        tail = scenario.loc[scenario["expected_cost_component"] >= tail_threshold, "expected_cost_component"]
        cvar = float(tail.mean()) if not tail.empty else weighted["expected_cost_component"]
        feasible_runtime = group.loc[group["feasibility_after_repair"] > 0.0, "median_runtime_seconds"]
        summaries.append(
            {
                "dataset": dataset,
                "method_name": method,
                "expected_operating_cost": weighted["expected_cost_component"],
                "best_cost_by_method": float(group["expected_cost_component"].min()),
                "median_cost_by_method": float(group["expected_cost_component"].median()),
                "risk_adjusted_cost": weighted["expected_cost_component"] + risk_lambda * cvar,
                "total_upgrade_cost": float(group["total_upgrade_cost"].max()),
                "max_fraction_customers_unserved_per_hour": float(
                    group["max_fraction_customers_unserved_per_hour"].max()
                ),
                "total_hours_critical_infrastructure_unserved": weighted[
                    "total_hours_critical_infrastructure_unserved"
                ],
                "critical_load_served_fraction": weighted["critical_load_served_fraction"],
                "critical_energy_not_served_kwh": weighted["critical_energy_not_served_kwh"],
                "energy_not_served_kwh": weighted["energy_not_served_kwh"],
                "feasibility_after_repair": float(group["feasibility_after_repair"].mean()),
                "wall_clock_runtime_seconds": float(group["wall_clock_runtime_seconds"].sum()),
                "median_runtime_seconds": float(group["median_runtime_seconds"].median()),
                "time_to_good_solution": float(feasible_runtime.min()) if not feasible_runtime.empty else -1.0,
                "repeat_count": int(group["sample_count"].max()),
                "samples_per_payload_median": float(group["sample_count"].median()),
                "payload_count": int(len(group)),
                "scenario_count": int(group["scenario"].nunique()),
                "scenario_probability_mass": probability_mass,
                "aggregation": "median_per_payload_then_probability_weighted_scenario_mean",
            }
        )
    return pd.DataFrame(summaries).sort_values(
        ["dataset", "risk_adjusted_cost", "expected_operating_cost"],
        kind="stable",
    )


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


def _challenge_win_tie_loss(scored: pd.DataFrame) -> pd.DataFrame:
    """Count sole wins, shared-best ties, and losses for each score mode."""

    columns = ["score_mode", "method_name", "wins", "ties", "losses", "datasets_evaluated"]
    if scored.empty or not {"score_mode", "dataset", "method_name", "challenge_score"}.issubset(scored.columns):
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for (score_mode, method), method_rows in scored.groupby(["score_mode", "method_name"], sort=True):
        wins = ties = losses = 0
        for dataset, group in scored[scored["score_mode"] == score_mode].groupby("dataset", sort=True):
            row = method_rows[method_rows["dataset"] == dataset]
            if row.empty:
                continue
            scores = pd.to_numeric(group["challenge_score"], errors="coerce")
            if scores.dropna().empty:
                continue
            best = float(scores.min())
            tolerance = max(1e-9, abs(best) * 1e-9)
            best_count = int(((scores - best).abs() <= tolerance).sum())
            value = float(pd.to_numeric(row["challenge_score"], errors="coerce").min())
            if abs(value - best) <= tolerance:
                if best_count == 1:
                    wins += 1
                else:
                    ties += 1
            else:
                losses += 1
        rows.append(
            {
                "score_mode": score_mode,
                "method_name": method,
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "datasets_evaluated": wins + ties + losses,
            }
        )
    return pd.DataFrame(rows, columns=columns)


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


def _pareto_v2(summary: pd.DataFrame) -> pd.DataFrame:
    """Return the per-dataset cost/critical-ENS Pareto frontier."""

    required = {"dataset", "method_name", "risk_adjusted_cost", "critical_energy_not_served_kwh"}
    if summary.empty or not required.issubset(summary.columns):
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for dataset, group in summary.groupby("dataset", sort=True):
        costs = pd.to_numeric(group["risk_adjusted_cost"], errors="coerce")
        critical_ens = pd.to_numeric(group["critical_energy_not_served_kwh"], errors="coerce")
        valid = group.loc[costs.notna() & critical_ens.notna()].copy()
        for index, row in valid.iterrows():
            dominated = valid[
                (valid["risk_adjusted_cost"] <= row["risk_adjusted_cost"])
                & (valid["critical_energy_not_served_kwh"] <= row["critical_energy_not_served_kwh"])
                & (
                    (valid["risk_adjusted_cost"] < row["risk_adjusted_cost"])
                    | (valid["critical_energy_not_served_kwh"] < row["critical_energy_not_served_kwh"])
                )
            ]
            if dominated.empty:
                rows.append(
                    row.to_dict()
                    | {
                        "dataset": dataset,
                        "pareto_frontier": True,
                        "cost_objective": "risk_adjusted_cost_min",
                        "resilience_objective": "critical_energy_not_served_kwh_min",
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.phase3_root)
    inputs = [str(path) for path in sorted(root.glob("**/*.csv"))]
    output_dir = root / "final_tables"
    explicit_formulations = bool(args.include_direct_qci or args.include_cmpo_v2 or args.include_hybrid)
    include_direct_qci = bool(args.include_direct_qci or not explicit_formulations)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "inputs": inputs,
                    "output_dir": str(output_dir),
                    "include_direct_qci": include_direct_qci,
                    "include_cmpo_v2": bool(args.include_cmpo_v2),
                    "include_hybrid": bool(args.include_hybrid),
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return
    normalize_pglib_benchmark_outputs()
    manifest_paths = write_public_benchmark_manifests()
    combined = _collect_rows(
        root,
        include_direct_qci=include_direct_qci,
        include_cmpo_v2=bool(args.include_cmpo_v2),
        include_hybrid=bool(args.include_hybrid),
    )
    analysis_frame = combined
    if explicit_formulations and not combined.empty and "source_formulation" in combined.columns:
        selected_sources = {
            source
            for source, enabled in (
                ("direct_qci", include_direct_qci),
                ("cmpo_v2", bool(args.include_cmpo_v2)),
                ("hybrid", bool(args.include_hybrid)),
            )
            if enabled
        }
        selected_datasets = set(
            combined.loc[combined["source_formulation"].isin(selected_sources), "dataset"].astype(str)
        )
        if selected_datasets:
            analysis_frame = combined[combined["dataset"].astype(str).isin(selected_datasets)].copy()
    summary = _balanced_summary(analysis_frame) if explicit_formulations else _summary(analysis_frame)
    ladder = pd.read_csv(manifest_paths["manifest"]) if Path(manifest_paths["manifest"]).exists() else pd.DataFrame()
    challenge_scores = score_challenge_summary(summary, mode="both")
    final_pareto = _pareto_v2(summary)
    tables = {
        "table1_qci_vs_best_baselines": _table1(summary),
        "table2_public_benchmark_ladder": ladder,
        "table3_scenario_stress": _table3(analysis_frame),
        "table4_native_cubic_vs_qubo": _table4(analysis_frame, root),
        "table5_resource_usage": _resource_usage(analysis_frame, root),
        "win_tie_loss_matrix": _win_tie_loss(summary),
        "pareto_frontier": _pareto(summary),
        "encoding_efficiency": _encoding_efficiency(analysis_frame, root),
        "qci_repeat_distribution": qci_repeat_distribution(analysis_frame),
        "challenge_score_summary": challenge_scores,
        "final_challenge_score_table": challenge_scores,
        "final_win_tie_loss_by_challenge_score": _challenge_win_tie_loss(challenge_scores),
        "final_pareto_frontier_v2": final_pareto,
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
