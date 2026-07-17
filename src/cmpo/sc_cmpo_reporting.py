"""Final system-level reporting for SC-CMPO Phase 3 artifacts."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

from cmpo.challenge_score import score_challenge_summary


matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


QCI_METHOD = "QCi SC-CMPO"
TABLE_FILENAMES = (
    "table1_system_level_qci_vs_baselines.csv",
    "table2_upgrade_cost_and_resilience.csv",
    "table3_heldout_contingencies.csv",
    "table4_public_benchmark_ladder.csv",
    "table5_encoding_efficiency.csv",
    "table6_resource_usage.csv",
    "win_tie_loss_system_level.csv",
    "pareto_frontier_system_level.csv",
)
FIGURE_FILENAMES = (
    "system_cost_vs_resilience_pareto.png",
    "upgrade_cost_vs_outage_reduction.png",
    "heldout_critical_ens.png",
    "customer_unserved_by_scenario.png",
    "consensus_convergence.png",
    "native_cubic_vs_qubo_encoding.png",
    "qci_repeat_distribution.png",
)
_NUMERIC_COLUMNS = (
    "total_upgrade_cost",
    "expected_operating_cost",
    "risk_adjusted_cost",
    "max_fraction_customers_unserved_per_hour",
    "total_hours_critical_infrastructure_unserved",
    "critical_energy_not_served_kwh",
    "total_energy_not_served_kwh",
    "critical_load_served_fraction",
    "consensus_iterations",
    "consensus_residual",
    "time_to_good_solution",
    "end_to_end_runtime_seconds",
    "wall_clock_runtime_seconds",
    "patch_runtime_seconds",
    "consensus_runtime_seconds",
    "runtime_seconds",
    "wall_clock_budget_seconds_per_patch",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read SC-CMPO system-level CSV artifacts and produce the final eight tables and seven figures "
            "without mutating raw result files."
        )
    )
    parser.add_argument(
        "--system-level-dir",
        default="results/phase3/sc_cmpo/system_level",
        help="Directory containing full-system projection CSV artifacts.",
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="Directory containing SC-CMPO payload JSON files; sibling manifests are read from its parent.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/final_reporting",
        help="Destination for the final reporting tables and figures.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate resolved inputs and planned outputs without writing files.",
    )
    return parser


def _read_csv(path: Path, *, required_columns: list[str] | None = None, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"required artifact not found: {path}")
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        frame = pd.DataFrame()
    if required_columns:
        missing = sorted(set(required_columns) - set(frame.columns))
        if missing:
            raise ValueError(f"artifact {path} is missing required columns: {missing}")
    return frame


def _resolve_payload_root(payload_dir: Path) -> Path:
    candidates = [payload_dir, payload_dir.parent]
    for candidate in candidates:
        if all((candidate / name).exists() for name in ("model_stats.csv", "payload_manifest.csv")):
            return candidate
    return payload_dir.parent if payload_dir.name == "qci_payloads" else payload_dir


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    converted = frame.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = pd.to_numeric(converted[column], errors="coerce")
    return converted


def _coerce_bool(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().str.lower()
    return values.isin({"1", "true", "yes", "y"})


def _normalize_system_metrics(frame: pd.DataFrame, *, is_qci: bool, source_name: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    normalized = frame.copy()
    if "benchmark" not in normalized.columns:
        raise ValueError(f"{source_name} must contain a benchmark column")
    if "method" not in normalized.columns:
        normalized["method"] = QCI_METHOD if is_qci else "unlabeled_method"
    if is_qci:
        normalized["method"] = QCI_METHOD
    for column in _NUMERIC_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    if "full_system_feasibility" in normalized.columns:
        normalized["full_system_feasibility"] = _coerce_bool(normalized["full_system_feasibility"])
    else:
        normalized["full_system_feasibility"] = True
    if "headline_selection" in normalized.columns:
        normalized["headline_selection"] = _coerce_bool(normalized["headline_selection"])
    else:
        normalized["headline_selection"] = False
    if "consensus_replicate" not in normalized.columns:
        normalized["consensus_replicate"] = "unlabeled"
    normalized["dataset"] = normalized["benchmark"].astype(str)
    normalized["method_name"] = normalized["method"].astype(str)
    normalized["feasibility_after_repair"] = normalized["full_system_feasibility"].astype(float)
    normalized["runtime_seconds"] = normalized.get("end_to_end_runtime_seconds", normalized.get("runtime_seconds"))
    normalized["total_energy_not_served"] = normalized.get(
        "total_energy_not_served",
        normalized.get("total_energy_not_served_kwh"),
    )
    normalized["wall_clock_runtime_seconds"] = normalized.get(
        "wall_clock_runtime_seconds",
        normalized.get("end_to_end_runtime_seconds"),
    )
    normalized["total_system_cost"] = normalized["total_upgrade_cost"].fillna(0.0) + normalized[
        "expected_operating_cost"
    ].fillna(0.0)
    normalized["trace_source"] = str(source_name)
    return normalized


def _representative_system_metrics(system_metrics: pd.DataFrame) -> pd.DataFrame:
    """Select one challenge-aligned system row per benchmark and method."""

    if system_metrics.empty:
        return system_metrics.copy()
    rows: list[pd.Series] = []
    for (_benchmark, method), group in system_metrics.groupby(
        ["benchmark", "method"], sort=True, dropna=False
    ):
        candidates = group
        rule = "lexicographic best reconstructed repeat"
        if str(method) == QCI_METHOD:
            rule = (
                "system-level lexicographic best across the patchwise challenge-selected consensus and "
                "all unselected QCi repeat consensuses"
            )
        ordered = candidates.assign(
            _infeasible=~candidates["full_system_feasibility"].astype(bool),
            _negative_served=-pd.to_numeric(
                candidates["critical_load_served_fraction"], errors="coerce"
            ),
        ).sort_values(
            [
                "_infeasible",
                "critical_energy_not_served_kwh",
                "total_hours_critical_infrastructure_unserved",
                "max_fraction_customers_unserved_per_hour",
                "_negative_served",
                "risk_adjusted_cost",
                "runtime_seconds",
                "consensus_replicate",
            ],
            ascending=True,
            kind="stable",
        )
        selected = ordered.iloc[0].drop(labels=["_infeasible", "_negative_served"]).copy()
        selected["representative_rule"] = rule
        selected["available_system_repeat_count"] = len(group)
        rows.append(selected)
    return pd.DataFrame(rows).reset_index(drop=True)


def _filter_to_representatives(
    frame: pd.DataFrame, representatives: pd.DataFrame
) -> pd.DataFrame:
    if frame.empty or representatives.empty:
        return frame.copy()
    keys = [
        column
        for column in ("benchmark", "method", "consensus_replicate")
        if column in frame.columns and column in representatives.columns
    ]
    if set(keys) != {"benchmark", "method", "consensus_replicate"}:
        return frame.copy()
    selected = representatives[keys].drop_duplicates()
    return frame.merge(selected, on=keys, how="inner")


def _bootstrap_mean_ci(values: pd.Series, *, metric: str) -> dict[str, Any]:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if numeric.size == 0:
        return {
            f"{metric}_mean": math.nan,
            f"{metric}_ci_low": math.nan,
            f"{metric}_ci_high": math.nan,
            f"{metric}_repeat_n": 0,
            f"{metric}_ci_method": "unavailable_no_repeat_metrics",
        }
    mean = float(numeric.mean())
    if numeric.size == 1:
        return {
            f"{metric}_mean": mean,
            f"{metric}_ci_low": mean,
            f"{metric}_ci_high": mean,
            f"{metric}_repeat_n": 1,
            f"{metric}_ci_method": "degenerate_single_repeat",
        }
    rng = np.random.default_rng(0)
    samples = rng.choice(numeric, size=(4096, numeric.size), replace=True).mean(axis=1)
    low, high = np.quantile(samples, [0.025, 0.975])
    return {
        f"{metric}_mean": mean,
        f"{metric}_ci_low": float(low),
        f"{metric}_ci_high": float(high),
        f"{metric}_repeat_n": int(numeric.size),
        f"{metric}_ci_method": "deterministic_bootstrap_mean_95",
    }


def _qci_repeat_summary(repeat_metrics: pd.DataFrame, trace_source: str) -> pd.DataFrame:
    if repeat_metrics.empty:
        return pd.DataFrame(
            columns=[
                "benchmark",
                "qci_critical_ens_mean",
                "qci_critical_ens_ci_low",
                "qci_critical_ens_ci_high",
                "qci_critical_ens_repeat_n",
                "qci_risk_adjusted_cost_mean",
                "qci_risk_adjusted_cost_ci_low",
                "qci_risk_adjusted_cost_ci_high",
                "qci_risk_adjusted_cost_repeat_n",
                "qci_runtime_mean",
                "qci_runtime_ci_low",
                "qci_runtime_ci_high",
                "qci_runtime_repeat_n",
                "qci_ci_method",
                "trace_source",
            ]
        )
    required = {"benchmark", "risk_adjusted_cost", "critical_energy_not_served_kwh"}
    missing = sorted(required - set(repeat_metrics.columns))
    if missing:
        raise ValueError(f"qci_repeat_system_metrics.csv is missing required columns: {missing}")
    repeated = repeat_metrics.copy()
    if "method" not in repeated.columns:
        repeated["method"] = QCI_METHOD
    repeated["method"] = QCI_METHOD
    rows: list[dict[str, Any]] = []
    for benchmark, group in repeated.groupby("benchmark", sort=True):
        critical = _bootstrap_mean_ci(group["critical_energy_not_served_kwh"], metric="qci_critical_ens")
        risk = _bootstrap_mean_ci(group["risk_adjusted_cost"], metric="qci_risk_adjusted_cost")
        runtime_column = (
            "end_to_end_runtime_seconds"
            if "end_to_end_runtime_seconds" in group.columns
            else "runtime_seconds"
            if "runtime_seconds" in group.columns
            else None
        )
        runtime = (
            _bootstrap_mean_ci(group[runtime_column], metric="qci_runtime")
            if runtime_column
            else _bootstrap_mean_ci(pd.Series(dtype=float), metric="qci_runtime")
        )
        method_names = {value for value in {critical["qci_critical_ens_ci_method"], risk["qci_risk_adjusted_cost_ci_method"]} if value}
        rows.append(
            {
                "benchmark": benchmark,
                **critical,
                **risk,
                **runtime,
                "qci_ci_method": "; ".join(sorted(method_names)) if method_names else "unavailable_no_repeat_metrics",
                "trace_source": trace_source,
            }
        )
    return pd.DataFrame(rows)


def _method_repeat_summary(system_metrics: pd.DataFrame) -> pd.DataFrame:
    """Compute deterministic 95% bootstrap intervals for every method."""

    if system_metrics.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (benchmark, method), raw_group in system_metrics.groupby(
        ["benchmark", "method"], sort=True, dropna=False
    ):
        group = raw_group
        if str(method) == QCI_METHOD and raw_group["headline_selection"].astype(bool).any():
            repeat_rows = raw_group[~raw_group["headline_selection"].astype(bool)]
            if not repeat_rows.empty:
                group = repeat_rows
        row: dict[str, Any] = {
            "benchmark": benchmark,
            "method": method,
            "repeat_n": len(group),
        }
        for column, label in (
            ("critical_energy_not_served_kwh", "critical_ens"),
            ("max_fraction_customers_unserved_per_hour", "max_customers_unserved"),
            ("total_hours_critical_infrastructure_unserved", "critical_infra_hours"),
            ("risk_adjusted_cost", "risk_adjusted_cost"),
            ("runtime_seconds", "runtime_seconds"),
        ):
            row.update(_bootstrap_mean_ci(group[column], metric=label))
        rows.append(row)
    return pd.DataFrame(rows)


def _prepare_scored_frame(system_metrics: pd.DataFrame) -> pd.DataFrame:
    if system_metrics.empty:
        return pd.DataFrame()
    scored_input = system_metrics.copy()
    scored_input["critical_energy_not_served_kwh"] = pd.to_numeric(
        scored_input["critical_energy_not_served_kwh"], errors="coerce"
    )
    scored_input["max_fraction_customers_unserved_per_hour"] = pd.to_numeric(
        scored_input["max_fraction_customers_unserved_per_hour"], errors="coerce"
    )
    scored_input["total_hours_critical_infrastructure_unserved"] = pd.to_numeric(
        scored_input["total_hours_critical_infrastructure_unserved"], errors="coerce"
    )
    scored_input["risk_adjusted_cost"] = pd.to_numeric(scored_input["risk_adjusted_cost"], errors="coerce")
    scored_input["expected_operating_cost"] = pd.to_numeric(scored_input["expected_operating_cost"], errors="coerce")
    scored_input["total_upgrade_cost"] = pd.to_numeric(scored_input["total_upgrade_cost"], errors="coerce")
    scored_input["critical_load_served_fraction"] = pd.to_numeric(
        scored_input["critical_load_served_fraction"], errors="coerce"
    )
    scored_input["total_energy_not_served"] = pd.to_numeric(
        scored_input["total_energy_not_served"], errors="coerce"
    )
    scored_input["runtime"] = pd.to_numeric(scored_input["runtime_seconds"], errors="coerce")
    scored_input["feasibility_after_repair"] = pd.to_numeric(
        scored_input["feasibility_after_repair"], errors="coerce"
    )
    return score_challenge_summary(scored_input, mode="both")


def _outcome(value: float | None, best: float | None) -> str:
    if value is None or best is None or not math.isfinite(value) or not math.isfinite(best):
        return "unavailable"
    tolerance = max(1e-9, abs(best) * 1e-9)
    if value < best - tolerance:
        return "win"
    if abs(value - best) <= tolerance:
        return "tie"
    return "loss"


def _build_table1(
    system_metrics: pd.DataFrame,
    scored: pd.DataFrame,
    repeat_summary: pd.DataFrame,
    method_repeat_summary: pd.DataFrame,
    qci_trace: str,
    baseline_trace: str,
) -> pd.DataFrame:
    benchmarks = sorted(system_metrics["benchmark"].astype(str).unique()) if not system_metrics.empty else []
    rows: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        group = system_metrics[system_metrics["benchmark"].astype(str) == benchmark]
        qci = group[group["method"].astype(str) == QCI_METHOD]
        baselines = group[group["method"].astype(str) != QCI_METHOD]
        repeat = repeat_summary[repeat_summary["benchmark"].astype(str) == benchmark]
        row: dict[str, Any] = {
            "benchmark": benchmark,
            "qci_method": QCI_METHOD,
            "qci_available": not qci.empty,
            "baseline_available": not baselines.empty,
            "trace_source": "; ".join(part for part in (qci_trace, baseline_trace, repeat.get("trace_source", pd.Series(dtype=str)).astype(str).iloc[0] if not repeat.empty else "") if part),
        }
        if qci.empty:
            row.update(
                {
                    "status": "unavailable_no_qci_system_row",
                    "qci_vs_best_outcome_lexicographic": "unavailable",
                    "qci_vs_best_outcome_weighted": "unavailable",
                }
            )
            rows.append(row)
            continue
        qci_row = qci.iloc[0]
        row.update(
            {
                "status": "ok" if not baselines.empty else "unavailable_no_baseline_system_row",
                "qci_system_trace_id": qci_row.get("system_trace_id", ""),
                "qci_total_system_cost": qci_row.get("total_system_cost", math.nan),
                "qci_total_upgrade_cost": qci_row.get("total_upgrade_cost", math.nan),
                "qci_expected_operating_cost": qci_row.get("expected_operating_cost", math.nan),
                "qci_critical_energy_not_served_kwh": qci_row.get("critical_energy_not_served_kwh", math.nan),
            }
        )
        if not repeat.empty:
            repeat_row = repeat.iloc[0].to_dict()
            row.update(repeat_row)
        else:
            row.update(_bootstrap_mean_ci(pd.Series(dtype=float), metric="qci_critical_ens"))
            row.update(_bootstrap_mean_ci(pd.Series(dtype=float), metric="qci_risk_adjusted_cost"))
            row["qci_ci_method"] = "unavailable_no_repeat_metrics"
        qci_method_ci = method_repeat_summary[
            (method_repeat_summary["benchmark"].astype(str) == benchmark)
            & (method_repeat_summary["method"].astype(str) == QCI_METHOD)
        ]
        if not qci_method_ci.empty:
            for key, value in qci_method_ci.iloc[0].items():
                if key not in {"benchmark", "method"}:
                    row[f"qci_{key}"] = value
        for score_mode in ("weighted", "lexicographic"):
            mode_rows = scored[
                (scored["dataset"].astype(str) == benchmark) & (scored["score_mode"].astype(str) == score_mode)
            ]
            qci_mode = mode_rows[mode_rows["method_name"].astype(str) == QCI_METHOD]
            baseline_mode = mode_rows[mode_rows["method_name"].astype(str) != QCI_METHOD]
            if baseline_mode.empty or qci_mode.empty:
                row[f"best_baseline_method_{score_mode}"] = ""
                row[f"best_baseline_score_{score_mode}"] = math.nan
                row[f"qci_score_{score_mode}"] = math.nan
                row[f"qci_vs_best_outcome_{score_mode}"] = "unavailable"
                continue
            baseline_best = baseline_mode.sort_values(["challenge_score", "method_name"], ascending=[True, True]).iloc[0]
            qci_score = float(pd.to_numeric(qci_mode["challenge_score"], errors="coerce").min())
            baseline_score = float(pd.to_numeric(baseline_best["challenge_score"], errors="coerce"))
            row[f"best_baseline_method_{score_mode}"] = str(baseline_best["method_name"])
            row[f"best_baseline_score_{score_mode}"] = baseline_score
            row[f"qci_score_{score_mode}"] = qci_score
            row[f"qci_vs_best_outcome_{score_mode}"] = _outcome(qci_score, baseline_score)
            baseline_ci = method_repeat_summary[
                (method_repeat_summary["benchmark"].astype(str) == benchmark)
                & (
                    method_repeat_summary["method"].astype(str)
                    == str(baseline_best["method_name"])
                )
            ]
            if not baseline_ci.empty:
                for key, value in baseline_ci.iloc[0].items():
                    if key not in {"benchmark", "method"}:
                        row[f"{score_mode}_best_baseline_{key}"] = value
        rows.append(row)
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(
        [
            {
                "status": "unavailable_no_system_metrics",
                "trace_source": "; ".join(part for part in (qci_trace, baseline_trace) if part),
            }
        ]
    )


def _build_table2(system_metrics: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    if system_metrics.empty:
        return pd.DataFrame([{"status": "unavailable_no_system_metrics", "trace_source": ""}])
    baseline_best: dict[tuple[str, str], pd.Series] = {}
    for benchmark in sorted(system_metrics["benchmark"].astype(str).unique()):
        for score_mode in ("weighted", "lexicographic"):
            mode_rows = scored[
                (scored["dataset"].astype(str) == benchmark)
                & (scored["score_mode"].astype(str) == score_mode)
                & (scored["method_name"].astype(str) != QCI_METHOD)
            ]
            if not mode_rows.empty:
                baseline_best[(benchmark, score_mode)] = mode_rows.sort_values(
                    ["challenge_score", "method_name"], ascending=[True, True]
                ).iloc[0]
    rows: list[dict[str, Any]] = []
    for _, row in system_metrics.sort_values(["benchmark", "total_system_cost", "method"]).iterrows():
        benchmark = str(row["benchmark"])
        weighted = baseline_best.get((benchmark, "weighted"))
        weighted_ens = float(weighted["critical_energy_not_served_kwh"]) if weighted is not None else math.nan
        rows.append(
            {
                "benchmark": benchmark,
                "method": row["method"],
                "total_upgrade_cost": row.get("total_upgrade_cost", math.nan),
                "expected_operating_cost": row.get("expected_operating_cost", math.nan),
                "total_system_cost": row.get("total_system_cost", math.nan),
                "critical_energy_not_served_kwh": row.get("critical_energy_not_served_kwh", math.nan),
                "total_energy_not_served_kwh": row.get("total_energy_not_served_kwh", math.nan),
                "critical_load_served_fraction": row.get("critical_load_served_fraction", math.nan),
                "weighted_reference_baseline_method": "" if weighted is None else str(weighted["method_name"]),
                "weighted_reference_baseline_critical_ens_kwh": weighted_ens,
                "outage_reduction_vs_weighted_best_baseline_kwh": (
                    math.nan
                    if weighted is None
                    else float(weighted_ens - float(row["critical_energy_not_served_kwh"]))
                ),
                "system_trace_id": row.get("system_trace_id", ""),
                "trace_source": row.get("trace_source", ""),
            }
        )
    return pd.DataFrame(rows)


def _build_table3(
    heldout_summary: pd.DataFrame,
    heldout_detail: pd.DataFrame,
    benchmarks: list[str],
    trace_source: str,
) -> pd.DataFrame:
    if heldout_summary.empty:
        rows = [
            {
                "benchmark": benchmark,
                "status": "unavailable_missing_heldout_summary",
                "trace_source": trace_source,
            }
            for benchmark in benchmarks
        ]
        return pd.DataFrame(rows or [{"status": "unavailable_missing_heldout_summary", "trace_source": trace_source}])
    summary = heldout_summary.copy()
    detail = heldout_detail.copy()
    if not detail.empty and {"benchmark", "patch_id", "critical_energy_not_served_kwh"}.issubset(detail.columns):
        aggregated = (
            detail.groupby(["benchmark", "patch_id"], sort=True)
            .agg(
                heldout_detail_count=("critical_energy_not_served_kwh", "count"),
                worst_contingency_critical_ens_kwh=("critical_energy_not_served_kwh", "max"),
                mean_contingency_critical_ens_kwh=("critical_energy_not_served_kwh", "mean"),
            )
            .reset_index()
        )
        summary = summary.merge(aggregated, on=["benchmark", "patch_id"], how="left")
    summary["trace_source"] = trace_source
    return summary


def _build_table4(
    benchmarks: list[str],
    scored: pd.DataFrame,
    provenance: pd.DataFrame,
    trace_source: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        weighted = scored[
            (scored["dataset"].astype(str) == benchmark) & (scored["score_mode"].astype(str) == "weighted")
        ]
        lexicographic = scored[
            (scored["dataset"].astype(str) == benchmark) & (scored["score_mode"].astype(str) == "lexicographic")
        ]
        weighted_best = (
            weighted.sort_values(["challenge_score", "method_name"], ascending=[True, True]).iloc[0]
            if not weighted.empty
            else None
        )
        lex_best = (
            lexicographic.sort_values(["challenge_score", "method_name"], ascending=[True, True]).iloc[0]
            if not lexicographic.empty
            else None
        )
        provenance_rows = provenance[provenance["benchmark"].astype(str) == benchmark] if not provenance.empty else pd.DataFrame()
        first_source = provenance_rows.iloc[0] if not provenance_rows.empty else pd.Series(dtype=object)
        rows.append(
            {
                "benchmark": benchmark,
                "source_name": first_source.get("source_name", ""),
                "source_url": first_source.get("source_url", ""),
                "local_sha256": first_source.get("local_sha256", ""),
                "source_version": first_source.get("version", ""),
                "weighted_best_method": "" if weighted_best is None else weighted_best["method_name"],
                "weighted_best_score": math.nan if weighted_best is None else weighted_best["challenge_score"],
                "lexicographic_best_method": "" if lex_best is None else lex_best["method_name"],
                "lexicographic_best_score": math.nan if lex_best is None else lex_best["challenge_score"],
                "qci_available": bool(
                    not weighted[weighted["method_name"].astype(str) == QCI_METHOD].empty
                    or not lexicographic[lexicographic["method_name"].astype(str) == QCI_METHOD].empty
                ),
                "trace_source": trace_source,
            }
        )
    ladder = pd.DataFrame(rows)
    if not ladder.empty and "weighted_best_score" in ladder.columns:
        ladder = ladder.sort_values(["weighted_best_score", "lexicographic_best_score", "benchmark"]).reset_index(drop=True)
        ladder["ladder_position"] = np.arange(1, len(ladder) + 1)
    return ladder if not ladder.empty else pd.DataFrame([{"status": "unavailable", "trace_source": trace_source}])


def _build_table5(
    model_stats: pd.DataFrame,
    payload_manifest: pd.DataFrame,
    baseline_patch_solutions: pd.DataFrame,
    trace_source: str,
) -> pd.DataFrame:
    if model_stats.empty:
        return pd.DataFrame([{"status": "unavailable_missing_model_stats", "trace_source": trace_source}])
    stats = _coerce_numeric(model_stats, ["variable_count", "term_count", "degree"])
    native = (
        stats.groupby("benchmark", sort=True)
        .agg(
            native_payload_count=("payload_name", "count"),
            native_cubic_variable_count_median=("variable_count", "median"),
            native_cubic_term_count_median=("term_count", "median"),
            native_cubic_degree_max=("degree", "max"),
        )
        .reset_index()
    )
    manifest = pd.DataFrame()
    if not payload_manifest.empty:
        manifest = payload_manifest.copy()
        if "qci_executable" in manifest.columns:
            manifest["qci_executable"] = _coerce_bool(manifest["qci_executable"])
        manifest = (
            manifest.groupby("benchmark", sort=True)
            .agg(
                payload_manifest_count=("payload_name", "count"),
                qci_executable_payload_count=("qci_executable", "sum"),
            )
            .reset_index()
        )
    qubo = pd.DataFrame()
    if not baseline_patch_solutions.empty:
        qubo_rows = baseline_patch_solutions[
            baseline_patch_solutions["method"].astype(str).str.contains("qubo", case=False, regex=False, na=False)
        ].copy()
        if not qubo_rows.empty:
            encoded_rows: list[dict[str, Any]] = []
            for _, row in qubo_rows.iterrows():
                raw_metadata = row.get("trace_metadata_json", row.get("trace_metadata", ""))
                try:
                    metadata = json.loads(str(raw_metadata)) if raw_metadata else {}
                except json.JSONDecodeError:
                    metadata = {}
                binary_count = pd.to_numeric(
                    pd.Series([metadata.get("binary_variable_count")]), errors="coerce"
                ).iloc[0]
                auxiliary_count = pd.to_numeric(
                    pd.Series([metadata.get("auxiliary_variable_count")]), errors="coerce"
                ).iloc[0]
                encoded_rows.append(
                    {
                        "benchmark": row.get("benchmark", ""),
                        "payload_name": row.get("payload_name", ""),
                        "quadratized_variable_count": (
                            float(binary_count + auxiliary_count)
                            if pd.notna(binary_count) and pd.notna(auxiliary_count)
                            else math.nan
                        ),
                        "auxiliary_variable_count": auxiliary_count,
                        "variable_blowup": metadata.get("variable_blowup", math.nan),
                        "approximation_error": metadata.get("approximation_error", math.nan),
                    }
                )
            encoded = _coerce_numeric(
                pd.DataFrame(encoded_rows),
                [
                    "quadratized_variable_count",
                    "auxiliary_variable_count",
                    "variable_blowup",
                    "approximation_error",
                ],
            )
            qubo = (
                encoded.groupby("benchmark", sort=True)
                .agg(
                    qubo_patch_solution_count=("payload_name", "count"),
                    qubo_variable_count_median=("quadratized_variable_count", "median"),
                    qubo_auxiliary_variable_count_median=("auxiliary_variable_count", "median"),
                    qubo_reported_blowup_median=("variable_blowup", "median"),
                    qubo_approximation_error_median=("approximation_error", "median"),
                )
                .reset_index()
            )
    table = native.merge(manifest, on="benchmark", how="left") if not manifest.empty else native
    table = table.merge(qubo, on="benchmark", how="left") if not qubo.empty else table
    if "qubo_variable_count_median" not in table.columns:
        table["qubo_variable_count_median"] = math.nan
    table["qubo_encoding_status"] = np.where(
        table["qubo_variable_count_median"].notna(),
        "available",
        "unavailable_no_qubo_patch_encoding_metrics",
    )
    table["qubo_variable_blowup_ratio"] = np.where(
        table["qubo_variable_count_median"].notna() & table["native_cubic_variable_count_median"].gt(0),
        table["qubo_variable_count_median"] / table["native_cubic_variable_count_median"],
        np.nan,
    )
    table["trace_source"] = trace_source
    return table


def _build_table6(
    system_metrics: pd.DataFrame, method_repeat_summary: pd.DataFrame
) -> pd.DataFrame:
    if system_metrics.empty:
        return pd.DataFrame([{"status": "unavailable_no_system_metrics", "trace_source": ""}])
    rows: list[dict[str, Any]] = []
    for (benchmark, method), group in system_metrics.groupby(
        ["benchmark", "method"], sort=True, dropna=False
    ):
        measured_group = group
        derived_headline_count = 0
        if str(method) == QCI_METHOD and "headline_selection" in group.columns:
            headline_mask = group["headline_selection"].astype(bool)
            derived_headline_count = int(headline_mask.sum())
            repeat_rows = group[~headline_mask]
            if not repeat_rows.empty:
                measured_group = repeat_rows
        repeat = method_repeat_summary[
            (method_repeat_summary["benchmark"].astype(str) == str(benchmark))
            & (method_repeat_summary["method"].astype(str) == str(method))
        ]
        ci = repeat.iloc[0] if not repeat.empty else pd.Series(dtype=object)
        wall_clock_budget = pd.to_numeric(
            measured_group.get(
                "wall_clock_budget_seconds_per_patch",
                pd.Series(math.nan, index=measured_group.index),
            ),
            errors="coerce",
        ).max()
        if not math.isfinite(float(wall_clock_budget)) or float(wall_clock_budget) <= 0:
            wall_clock_budget = math.nan
        if str(method) == QCI_METHOD:
            budget_basis = f"{len(measured_group)} completed Dirac-3 samples per payload"
            runtime_accounting_basis = (
                "batched QCi samples share the same device jobs; shared end-to-end runtime counted once"
            )
            end_to_end_runtime_total = pd.to_numeric(
                measured_group["end_to_end_runtime_seconds"], errors="coerce"
            ).mean()
        elif len(measured_group) > 1:
            budget_basis = f"{len(measured_group)} matched stochastic repeats; common per-patch wall-clock cap"
            runtime_accounting_basis = "independent stochastic repeats; measured runtimes summed"
            end_to_end_runtime_total = pd.to_numeric(
                measured_group["end_to_end_runtime_seconds"], errors="coerce"
            ).sum()
        else:
            budget_basis = "one deterministic solve; common per-patch wall-clock cap"
            runtime_accounting_basis = "single deterministic solve; measured runtime counted once"
            end_to_end_runtime_total = pd.to_numeric(
                measured_group["end_to_end_runtime_seconds"], errors="coerce"
            ).sum()
        rows.append(
            {
                "benchmark": benchmark,
                "method": method,
                "system_repeat_count": len(measured_group),
                "derived_headline_candidate_count": derived_headline_count,
                "budget_basis": budget_basis,
                "runtime_accounting_basis": runtime_accounting_basis,
                "end_to_end_runtime_seconds_mean": pd.to_numeric(
                    measured_group["end_to_end_runtime_seconds"], errors="coerce"
                ).mean(),
                "end_to_end_runtime_seconds_total": end_to_end_runtime_total,
                "wall_clock_runtime_seconds_mean": pd.to_numeric(
                    measured_group["wall_clock_runtime_seconds"], errors="coerce"
                ).mean(),
                "patch_runtime_seconds_mean": pd.to_numeric(
                    measured_group["patch_runtime_seconds"], errors="coerce"
                ).mean(),
                "consensus_runtime_seconds_mean": pd.to_numeric(
                    measured_group["consensus_runtime_seconds"], errors="coerce"
                ).mean(),
                "time_to_good_solution_mean": pd.to_numeric(
                    measured_group["time_to_good_solution"], errors="coerce"
                ).mean(),
                "consensus_iterations_mean": pd.to_numeric(
                    measured_group["consensus_iterations"], errors="coerce"
                ).mean(),
                "wall_clock_budget_seconds_per_patch": wall_clock_budget,
                "runtime_seconds_ci_low": ci.get("runtime_seconds_ci_low", math.nan),
                "runtime_seconds_ci_high": ci.get("runtime_seconds_ci_high", math.nan),
                "runtime_seconds_ci_method": ci.get("runtime_seconds_ci_method", "unavailable"),
                "trace_source": "; ".join(sorted(set(group["trace_source"].astype(str)))),
            }
        )
    return pd.DataFrame(rows)


def _build_win_tie_loss(scored: pd.DataFrame, trace_source: str) -> pd.DataFrame:
    columns = ["score_mode", "method", "wins", "ties", "losses", "benchmarks_evaluated", "trace_source"]
    if scored.empty:
        return pd.DataFrame([{"status": "unavailable_no_scored_system_metrics", "trace_source": trace_source}])
    rows: list[dict[str, Any]] = []
    for (score_mode, method_name), method_rows in scored.groupby(["score_mode", "method_name"], sort=True):
        wins = ties = losses = 0
        mode_scored = scored[scored["score_mode"].astype(str) == str(score_mode)]
        for benchmark, benchmark_rows in mode_scored.groupby("dataset", sort=True):
            current = method_rows[method_rows["dataset"].astype(str) == str(benchmark)]
            if current.empty:
                continue
            scores = pd.to_numeric(benchmark_rows["challenge_score"], errors="coerce")
            if scores.dropna().empty:
                continue
            best = float(scores.min())
            tolerance = max(1e-9, abs(best) * 1e-9)
            current_score = float(pd.to_numeric(current["challenge_score"], errors="coerce").min())
            best_count = int(((scores - best).abs() <= tolerance).sum())
            if abs(current_score - best) <= tolerance:
                if best_count == 1:
                    wins += 1
                else:
                    ties += 1
            else:
                losses += 1
        rows.append(
            {
                "score_mode": score_mode,
                "method": method_name,
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "benchmarks_evaluated": wins + ties + losses,
                "trace_source": trace_source,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _build_pareto_frontier(system_metrics: pd.DataFrame) -> pd.DataFrame:
    if system_metrics.empty:
        return pd.DataFrame([{"status": "unavailable_no_system_metrics", "trace_source": ""}])
    rows: list[dict[str, Any]] = []
    for benchmark, group in system_metrics.groupby("benchmark", sort=True):
        valid = group.dropna(subset=["total_system_cost", "critical_energy_not_served_kwh"]).copy()
        for _, row in valid.iterrows():
            dominated = valid[
                (valid["total_system_cost"] <= row["total_system_cost"])
                & (valid["critical_energy_not_served_kwh"] <= row["critical_energy_not_served_kwh"])
                & (
                    (valid["total_system_cost"] < row["total_system_cost"])
                    | (valid["critical_energy_not_served_kwh"] < row["critical_energy_not_served_kwh"])
                )
            ]
            if dominated.empty:
                rows.append(
                    {
                        "benchmark": benchmark,
                        "method": row["method"],
                        "total_upgrade_cost": row["total_upgrade_cost"],
                        "expected_operating_cost": row["expected_operating_cost"],
                        "total_system_cost": row["total_system_cost"],
                        "critical_energy_not_served_kwh": row["critical_energy_not_served_kwh"],
                        "pareto_frontier": True,
                        "trace_source": row.get("trace_source", ""),
                    }
                )
    return pd.DataFrame(rows)


def _write_placeholder_figure(path: Path, title: str, message: str) -> None:
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.axis("off")
    axis.text(0.5, 0.62, title, ha="center", va="center", fontsize=14, fontweight="bold")
    axis.text(0.5, 0.38, message, ha="center", va="center", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _scatter_pareto(table2: pd.DataFrame, frontier: pd.DataFrame, path: Path) -> None:
    valid = table2.dropna(subset=["total_system_cost", "critical_energy_not_served_kwh"])
    if valid.empty:
        _write_placeholder_figure(path, "System Cost vs Resilience Pareto", "No full-system cost/resilience rows available.")
        return
    figure, axis = plt.subplots(figsize=(8, 5))
    for method, group in valid.groupby("method", sort=True):
        axis.scatter(group["total_system_cost"], group["critical_energy_not_served_kwh"], label=method, alpha=0.8)
    if not frontier.empty:
        axis.scatter(
            frontier["total_system_cost"],
            frontier["critical_energy_not_served_kwh"],
            facecolors="none",
            edgecolors="black",
            s=120,
            linewidths=1.3,
            label="Pareto frontier",
        )
    axis.set_xlabel("Upgrade + expected operating cost")
    axis.set_ylabel("Critical ENS (kWh)")
    axis.set_title("System Cost vs Resilience Pareto")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _scatter_upgrade_reduction(table2: pd.DataFrame, path: Path) -> None:
    valid = table2.dropna(subset=["total_upgrade_cost", "outage_reduction_vs_weighted_best_baseline_kwh"])
    if valid.empty:
        _write_placeholder_figure(
            path,
            "Upgrade Cost vs Outage Reduction",
            "No weighted-baseline comparison rows available.",
        )
        return
    figure, axis = plt.subplots(figsize=(8, 5))
    for method, group in valid.groupby("method", sort=True):
        axis.scatter(group["total_upgrade_cost"], group["outage_reduction_vs_weighted_best_baseline_kwh"], label=method)
    axis.axhline(0.0, color="black", linewidth=0.8, alpha=0.5)
    axis.set_xlabel("Upgrade cost")
    axis.set_ylabel("Critical ENS reduction vs weighted-best baseline (kWh)")
    axis.set_title("Upgrade Cost vs Outage Reduction")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _bar_heldout(table3: pd.DataFrame, path: Path) -> None:
    valid = table3.dropna(subset=["critical_energy_not_served_kwh"]) if "critical_energy_not_served_kwh" in table3.columns else pd.DataFrame()
    if valid.empty:
        _write_placeholder_figure(path, "Held-Out Critical ENS", "Held-out contingency artifacts are unavailable.")
        return
    labels = valid["benchmark"].astype(str) + "\n" + valid.get("patch_id", pd.Series([""] * len(valid))).astype(str)
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(labels, valid["critical_energy_not_served_kwh"])
    axis.set_ylabel("Critical ENS (kWh)")
    axis.set_title("Held-Out Critical ENS")
    axis.tick_params(axis="x", rotation=20)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _bar_scenarios(scenarios: pd.DataFrame, path: Path) -> None:
    required = {"benchmark", "method", "scenario", "fraction_customers_unserved_per_hour"}
    if scenarios.empty or not required.issubset(scenarios.columns):
        _write_placeholder_figure(path, "Customers Unserved by Scenario", "Scenario-level system results are unavailable.")
        return
    summary = (
        scenarios.groupby(["benchmark", "scenario", "method"], sort=True)["fraction_customers_unserved_per_hour"]
        .mean()
        .reset_index()
    )
    methods = list(summary["method"].astype(str).unique())
    width = 0.8 / max(len(methods), 1)
    x = np.arange(len(summary.groupby(["benchmark", "scenario"])))
    grouped = summary.groupby(["benchmark", "scenario"], sort=True)
    categories = list(grouped.groups.keys())
    figure, axis = plt.subplots(figsize=(10, 5.5))
    for offset, method in enumerate(methods):
        values: list[float] = []
        for benchmark, scenario in categories:
            matches = summary[
                (summary["benchmark"].astype(str) == str(benchmark))
                & (summary["scenario"].astype(str) == str(scenario))
                & (summary["method"].astype(str) == str(method))
            ]
            values.append(float(matches["fraction_customers_unserved_per_hour"].iloc[0]) if not matches.empty else 0.0)
        axis.bar(x - 0.4 + width / 2 + offset * width, values, width=width, label=method)
    axis.set_xticks(x, [f"{benchmark}\n{scenario}" for benchmark, scenario in categories], rotation=20, ha="right")
    axis.set_ylabel("Fraction customers unserved per hour")
    axis.set_title("Customers Unserved by Scenario")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _bar_convergence(convergence: pd.DataFrame, path: Path) -> None:
    required = {"benchmark", "method", "primal_residual", "dual_residual", "iteration_count"}
    if convergence.empty or not required.issubset(convergence.columns):
        _write_placeholder_figure(path, "Consensus Convergence", "Consensus convergence rows are unavailable.")
        return
    data = convergence.copy()
    data = _coerce_numeric(data, ["primal_residual", "dual_residual", "iteration_count"])
    labels = data["benchmark"].astype(str) + "\n" + data["method"].astype(str)
    figure, axis = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(data))
    axis.bar(x - 0.2, data["primal_residual"], width=0.2, label="Primal residual")
    axis.bar(x, data["dual_residual"], width=0.2, label="Dual residual")
    axis.bar(x + 0.2, data["iteration_count"], width=0.2, label="Iterations")
    axis.set_xticks(x, labels, rotation=25, ha="right")
    axis.set_title("Consensus Convergence")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _bar_encoding(table5: pd.DataFrame, path: Path) -> None:
    required = {"benchmark", "native_cubic_variable_count_median"}
    if table5.empty or not required.issubset(table5.columns):
        _write_placeholder_figure(path, "Native Cubic vs QUBO Encoding", "Encoding-efficiency rows are unavailable.")
        return
    table = table5.copy()
    labels = table["benchmark"].astype(str)
    qubo_values = table.get("qubo_variable_count_median", pd.Series([math.nan] * len(table)))
    figure, axis = plt.subplots(figsize=(8, 5))
    x = np.arange(len(table))
    axis.bar(x - 0.15, table["native_cubic_variable_count_median"], width=0.3, label="Native cubic")
    axis.bar(x + 0.15, qubo_values.fillna(0.0), width=0.3, label="QUBO/quadratized")
    axis.set_xticks(x, labels)
    axis.set_ylabel("Median variable count")
    axis.set_title("Native Cubic vs QUBO Encoding")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _box_qci_repeats(repeat_metrics: pd.DataFrame, path: Path) -> None:
    if repeat_metrics.empty or "risk_adjusted_cost" not in repeat_metrics.columns:
        _write_placeholder_figure(path, "QCi Repeat Distribution", "Repeat-level QCi system metrics are unavailable.")
        return
    data = repeat_metrics.copy()
    data = _coerce_numeric(data, ["risk_adjusted_cost"])
    grouped = [group["risk_adjusted_cost"].dropna().to_numpy() for _, group in data.groupby("benchmark", sort=True)]
    labels = [benchmark for benchmark, _ in data.groupby("benchmark", sort=True)]
    if not grouped or all(len(values) == 0 for values in grouped):
        _write_placeholder_figure(path, "QCi Repeat Distribution", "Repeat-level QCi system metrics are unavailable.")
        return
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.boxplot(grouped, labels=labels, patch_artist=True)
    axis.set_ylabel("Risk-adjusted cost")
    axis.set_title("QCi Repeat Distribution")
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _write_tables(output_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    for filename, frame in tables.items():
        frame.to_csv(output_dir / filename, index=False)


def _write_figures(
    output_dir: Path,
    table2: pd.DataFrame,
    table3: pd.DataFrame,
    scenarios: pd.DataFrame,
    convergence: pd.DataFrame,
    table5: pd.DataFrame,
    repeat_metrics: pd.DataFrame,
    frontier: pd.DataFrame,
) -> None:
    _scatter_pareto(table2, frontier, output_dir / "system_cost_vs_resilience_pareto.png")
    _scatter_upgrade_reduction(table2, output_dir / "upgrade_cost_vs_outage_reduction.png")
    _bar_heldout(table3, output_dir / "heldout_critical_ens.png")
    _bar_scenarios(scenarios, output_dir / "customer_unserved_by_scenario.png")
    _bar_convergence(convergence, output_dir / "consensus_convergence.png")
    _bar_encoding(table5, output_dir / "native_cubic_vs_qubo_encoding.png")
    _box_qci_repeats(repeat_metrics, output_dir / "qci_repeat_distribution.png")


def finalize_sc_cmpo_reporting(
    system_level_dir: Path | str,
    payload_dir: Path | str,
    output_dir: Path | str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    system_dir = Path(system_level_dir)
    payload_path = Path(payload_dir)
    output_path = Path(output_dir)
    payload_root = _resolve_payload_root(payload_path)
    required_system_artifacts = {
        "qci_system_metrics.csv": system_dir / "qci_system_metrics.csv",
        "baseline_system_metrics.csv": system_dir / "baseline_system_metrics.csv",
        "scenario_results.csv": system_dir / "scenario_results.csv",
        "upgrade_plan_comparison.csv": system_dir / "upgrade_plan_comparison.csv",
        "consensus_convergence.csv": system_dir / "consensus_convergence.csv",
        "baseline_patch_solutions.csv": system_dir / "baseline_patch_solutions.csv",
        "qci_patch_solutions.csv": system_dir / "qci_patch_solutions.csv",
        "consensus_manifest.json": system_dir / "consensus_manifest.json",
    }
    required_payload_artifacts = {
        "model_stats.csv": payload_root / "model_stats.csv",
        "payload_manifest.csv": payload_root / "payload_manifest.csv",
        "public_benchmark_provenance.csv": payload_root / "public_benchmark_provenance.csv",
    }
    optional_artifacts = {
        "qci_repeat_system_metrics.csv": system_dir / "qci_repeat_system_metrics.csv",
        "heldout_summary.csv": system_dir / "heldout_summary.csv",
        "heldout_contingencies.csv": system_dir / "heldout_contingencies.csv",
    }
    plan = {
        "dry_run": dry_run,
        "system_level_dir": str(system_dir),
        "payload_dir": str(payload_path),
        "payload_root": str(payload_root),
        "output_dir": str(output_path),
        "tables": list(TABLE_FILENAMES),
        "figures": list(FIGURE_FILENAMES),
        "required_inputs": {
            name: str(path)
            for name, path in {**required_system_artifacts, **required_payload_artifacts}.items()
        },
        "optional_inputs": {name: str(path) for name, path in optional_artifacts.items()},
    }
    if dry_run:
        for path in list(required_system_artifacts.values()) + list(required_payload_artifacts.values()):
            if not path.exists():
                raise FileNotFoundError(f"required artifact not found: {path}")
        return plan

    qci_system = _normalize_system_metrics(
        _read_csv(required_system_artifacts["qci_system_metrics.csv"], required=True),
        is_qci=True,
        source_name="qci_system_metrics.csv",
    )
    baseline_system = _normalize_system_metrics(
        _read_csv(required_system_artifacts["baseline_system_metrics.csv"], required=True),
        is_qci=False,
        source_name="baseline_system_metrics.csv",
    )
    scenarios = _read_csv(required_system_artifacts["scenario_results.csv"], required=True)
    if "fraction_customers_unserved_per_hour" not in scenarios.columns and "max_fraction_customers_unserved_per_hour" in scenarios.columns:
        scenarios["fraction_customers_unserved_per_hour"] = scenarios["max_fraction_customers_unserved_per_hour"]
    _read_csv(required_system_artifacts["upgrade_plan_comparison.csv"], required=True)
    convergence = _read_csv(required_system_artifacts["consensus_convergence.csv"], required=True)
    baseline_patch_solutions = _read_csv(required_system_artifacts["baseline_patch_solutions.csv"], required=True)
    _read_csv(required_system_artifacts["qci_patch_solutions.csv"], required=True)
    json.loads(required_system_artifacts["consensus_manifest.json"].read_text(encoding="utf-8"))
    model_stats = _read_csv(required_payload_artifacts["model_stats.csv"], required=True)
    payload_manifest = _read_csv(required_payload_artifacts["payload_manifest.csv"], required=True)
    provenance = _read_csv(required_payload_artifacts["public_benchmark_provenance.csv"], required=True)
    repeat_metrics = _read_csv(optional_artifacts["qci_repeat_system_metrics.csv"], required=False)
    heldout_summary = _read_csv(optional_artifacts["heldout_summary.csv"], required=False)
    heldout_detail = _read_csv(optional_artifacts["heldout_contingencies.csv"], required=False)

    all_system_metrics = pd.concat([qci_system, baseline_system], ignore_index=True, sort=False)
    all_system_metrics = _coerce_numeric(
        all_system_metrics, list(_NUMERIC_COLUMNS) + ["total_system_cost"]
    )
    system_metrics = _representative_system_metrics(all_system_metrics)
    benchmarks = sorted(system_metrics["benchmark"].astype(str).unique()) if not system_metrics.empty else []
    repeat_summary = _qci_repeat_summary(repeat_metrics, "qci_repeat_system_metrics.csv")
    method_repeat_summary = _method_repeat_summary(all_system_metrics)
    scored = _prepare_scored_frame(system_metrics)

    scenarios = _filter_to_representatives(scenarios, system_metrics)
    heldout_summary = _filter_to_representatives(heldout_summary, system_metrics)
    heldout_detail = _filter_to_representatives(heldout_detail, system_metrics)
    convergence = _filter_to_representatives(convergence, system_metrics)
    if not convergence.empty and {
        "benchmark",
        "method",
        "consensus_replicate",
        "iteration",
    }.issubset(convergence.columns):
        convergence["iteration"] = pd.to_numeric(convergence["iteration"], errors="coerce")
        convergence = (
            convergence.sort_values("iteration")
            .groupby(["benchmark", "method", "consensus_replicate"], sort=True)
            .tail(1)
        )

    table1 = _build_table1(
        system_metrics,
        scored,
        repeat_summary,
        method_repeat_summary,
        "qci_system_metrics.csv",
        "baseline_system_metrics.csv",
    )
    table2 = _build_table2(system_metrics, scored)
    table3 = _build_table3(
        heldout_summary,
        heldout_detail,
        benchmarks,
        "; ".join(
            name
            for name, frame in (
                ("heldout_summary.csv", heldout_summary),
                ("heldout_contingencies.csv", heldout_detail),
            )
            if not frame.empty or name in optional_artifacts
        ),
    )
    table4 = _build_table4(benchmarks, scored, provenance, "public_benchmark_provenance.csv;system_metrics")
    table5 = _build_table5(model_stats, payload_manifest, baseline_patch_solutions, "model_stats.csv;payload_manifest.csv;baseline_patch_solutions.csv")
    table6 = _build_table6(all_system_metrics, method_repeat_summary)
    win_tie_loss = _build_win_tie_loss(scored, "system_metrics")
    pareto = _build_pareto_frontier(system_metrics)

    output_path.mkdir(parents=True, exist_ok=True)
    tables = {
        "table1_system_level_qci_vs_baselines.csv": table1,
        "table2_upgrade_cost_and_resilience.csv": table2,
        "table3_heldout_contingencies.csv": table3,
        "table4_public_benchmark_ladder.csv": table4,
        "table5_encoding_efficiency.csv": table5,
        "table6_resource_usage.csv": table6,
        "win_tie_loss_system_level.csv": win_tie_loss,
        "pareto_frontier_system_level.csv": pareto,
    }
    _write_tables(output_path, tables)
    _write_figures(output_path, table2, table3, scenarios, convergence, table5, repeat_metrics, pareto)
    return {
        **plan,
        "dry_run": False,
        "tables": list(tables),
        "figures": list(FIGURE_FILENAMES),
    }
