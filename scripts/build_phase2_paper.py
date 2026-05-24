#!/usr/bin/env python
"""Build paper-facing Phase 2 artifacts from saved CMPO result manifests."""

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


def build_parser() -> argparse.ArgumentParser:
    """Build the paper-artifact CLI."""

    parser = argparse.ArgumentParser(description="Generate Phase 2 paper artifacts from result manifests.")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--analysis-dir", default="analysis/paper")
    return parser


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"required table not found: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"required table is empty: {path}")
    if frame.isna().any().any():
        columns = frame.columns[frame.isna().any()].tolist()
        raise ValueError(f"table contains NaN values in {columns}: {path}")
    return frame


def _markdown_table(frame: pd.DataFrame, float_digits: int = 4) -> str:
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.{float_digits}g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _manifest_rows(results_dir: Path) -> pd.DataFrame:
    main_manifest = _read_json(results_dir / "run_manifest.json")
    benchmark_manifest_path = results_dir / "benchmarks" / "pglib_case5_pjm" / "benchmark_manifest.json"
    benchmark_manifest = _read_json(benchmark_manifest_path)
    rows = [
        {
            "run_name": "synthetic_default",
            "manifest_path": str(results_dir / "run_manifest.json"),
            "dataset_source": "deterministic synthetic CMPO case",
            "seed": main_manifest["seed"],
            "horizon": main_manifest["horizon"],
            "n_scenarios": main_manifest["n_scenarios"],
            "quick": main_manifest["quick"],
            "payload_count": main_manifest["payload_count"],
            "summary_metrics_csv": main_manifest["metric_outputs"]["summary_metrics_csv"],
            "scenario_results_csv": main_manifest["metric_outputs"]["scenario_results_csv"],
            "model_stats_csv": main_manifest["metric_outputs"]["model_stats_csv"],
            "phase2_headlines_md": main_manifest["metric_outputs"]["phase2_headlines_md"],
        },
        {
            "run_name": "pglib_case5_pjm_adapted",
            "manifest_path": str(benchmark_manifest_path),
            "dataset_source": "PGLib-OPF case5-PJM adapted CMPO benchmark",
            "seed": benchmark_manifest["seed"],
            "horizon": benchmark_manifest["horizon"],
            "n_scenarios": benchmark_manifest["n_scenarios"],
            "quick": benchmark_manifest["quick"],
            "payload_count": benchmark_manifest["payload_count"],
            "summary_metrics_csv": benchmark_manifest["metric_outputs"]["summary_metrics_csv"],
            "scenario_results_csv": benchmark_manifest["metric_outputs"]["scenario_results_csv"],
            "model_stats_csv": benchmark_manifest["metric_outputs"]["model_stats_csv"],
            "phase2_headlines_md": benchmark_manifest["metric_outputs"]["phase2_headlines_md"],
        },
    ]
    return pd.DataFrame(rows)


def _paper_table(summary: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "method_name",
        "expected_operating_cost",
        "risk_adjusted_cost",
        "critical_load_served_fraction",
        "energy_not_served_kwh",
        "feasibility_rate",
        "median_runtime_seconds",
    ]
    return summary[columns].sort_values(["risk_adjusted_cost", "expected_operating_cost"]).reset_index(drop=True)


def _model_summary(model_stats: pd.DataFrame) -> dict[str, Any]:
    return {
        "payloads": int(len(model_stats)),
        "max_degree": int(model_stats["degree"].max()),
        "max_variables": int(model_stats["variable_count"].max()),
        "max_terms": int(model_stats["term_count"].max()),
        "median_variables": float(model_stats["variable_count"].median()),
        "median_terms": float(model_stats["term_count"].median()),
        "max_abs_coefficient": float(model_stats["max_abs_coefficient"].max())
        if "max_abs_coefficient" in model_stats.columns
        else 0.0,
    }


def _scenario_stress_summary(scenarios: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        scenarios.groupby("scenario", as_index=False)
        .agg(
            critical_load_served_fraction=("critical_load_served_fraction", "mean"),
            energy_not_served_kwh=("energy_not_served_kwh", "sum"),
            critical_energy_not_served_kwh=("critical_energy_not_served_kwh", "sum"),
            feasibility_rate=("feasibility_pass", "mean"),
        )
        .sort_values("energy_not_served_kwh", ascending=False)
    )
    return grouped.head(8).reset_index(drop=True)


def _cubic_summary(cubic: pd.DataFrame) -> pd.DataFrame:
    return (
        cubic.groupby(["method_name", "model_variant"], as_index=False)
        .agg(
            true_cubic_cost=("true_cubic_cost", "mean"),
            true_cubic_cost_difference_vs_cubic=("true_cubic_cost_difference_vs_cubic", "mean"),
            dispatch_profile_l1_difference_vs_cubic=("dispatch_profile_l1_difference_vs_cubic", "mean"),
            critical_load_served_fraction=("critical_load_served_fraction", "mean"),
            energy_not_served_kwh=("energy_not_served_kwh", "sum"),
        )
        .sort_values(["method_name", "model_variant"])
    )


def _scaling_summary(scaling: pd.DataFrame) -> pd.DataFrame:
    return (
        scaling.groupby(["n_microgrids", "horizon", "n_scenarios"], as_index=False)
        .agg(
            payload_count=("payload_count", "max"),
            max_variables=("variable_count_per_hamiltonian", "max"),
            max_terms=("term_count_per_hamiltonian", "max"),
            max_median_runtime_seconds=("median_runtime_seconds", "max"),
            best_expected_cost=("expected_cost", "min"),
        )
        .sort_values(["n_microgrids", "horizon", "n_scenarios"])
    )


def _optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    return None if frame.empty else frame


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _method_comparison_table(summary: pd.DataFrame) -> pd.DataFrame:
    return (
        summary[
            [
                "method_name",
                "expected_operating_cost",
                "risk_adjusted_cost",
                "critical_load_served_fraction",
                "energy_not_served_kwh",
                "feasibility_rate",
                "median_runtime_seconds",
            ]
        ]
        .rename(
            columns={
                "method_name": "method",
                "expected_operating_cost": "expected operating cost",
                "risk_adjusted_cost": "risk-adjusted cost",
                "critical_load_served_fraction": "critical-load served fraction",
                "energy_not_served_kwh": "energy not served",
                "feasibility_rate": "feasibility rate",
                "median_runtime_seconds": "median runtime",
            }
        )
        .sort_values(["expected operating cost", "risk-adjusted cost"])
        .reset_index(drop=True)
    )


def _scenario_submission_table(scenarios: pd.DataFrame) -> pd.DataFrame:
    return (
        scenarios.groupby("scenario", as_index=False)
        .agg(
            **{
                "critical-load served fraction": ("critical_load_served_fraction", "mean"),
                "energy not served": ("energy_not_served_kwh", "sum"),
                "critical energy not served": ("critical_energy_not_served_kwh", "sum"),
                "feasibility rate": ("feasibility_pass", "mean"),
            }
        )
        .sort_values("energy not served", ascending=False)
        .reset_index(drop=True)
    )


def _resource_summary_table(
    results_dir: Path,
    main_models: pd.DataFrame,
    benchmark_models: pd.DataFrame,
    scaling_summary: pd.DataFrame,
    qci_small_models: pd.DataFrame | None,
) -> pd.DataFrame:
    main_manifest = _read_json(results_dir / "run_manifest.json")
    benchmark_manifest = _read_json(results_dir / "benchmarks" / "pglib_case5_pjm" / "benchmark_manifest.json")
    rows: list[dict[str, Any]] = [
        {
            "experiment": "main synthetic run",
            "payload count": int(main_manifest["payload_count"]),
            "max variables": int(main_models["variable_count"].max()),
            "median variables": float(main_models["variable_count"].median()),
            "max terms": int(main_models["term_count"].max()),
            "max degree": int(main_models["degree"].max()),
            "intended Phase 3 use": "full synthetic evidence sweep; larger honest Hamiltonian reference",
        },
        {
            "experiment": "scaling study",
            "payload count": int(scaling_summary["payload_count"].max()),
            "max variables": int(scaling_summary["max_variables"].max()),
            "median variables": float(scaling_summary["max_variables"].median()),
            "max terms": int(scaling_summary["max_terms"].max()),
            "max degree": 3,
            "intended Phase 3 use": "size trend only; smaller than the main selected-patch run when patch sizes differ",
        },
        {
            "experiment": "PGLib case5-PJM adapted benchmark",
            "payload count": int(benchmark_manifest["payload_count"]),
            "max variables": int(benchmark_models["variable_count"].max()),
            "median variables": float(benchmark_models["variable_count"].median()),
            "max terms": int(benchmark_models["term_count"].max()),
            "max degree": int(benchmark_models["degree"].max()),
            "intended Phase 3 use": "public-benchmark-derived stress case; not an AC OPF reproduction",
        },
    ]
    if qci_small_models is not None:
        qci_small_manifest = _optional_json(results_dir / "qci_small" / "run_manifest.json") or {}
        rows.append(
            {
                "experiment": "qci_small conservative payload",
                "payload count": int(qci_small_manifest.get("payload_count", len(qci_small_models))),
                "max variables": int(qci_small_models["variable_count"].max()),
                "median variables": float(qci_small_models["variable_count"].median()),
                "max terms": int(qci_small_models["term_count"].max()),
                "max degree": int(qci_small_models["degree"].max()),
                "intended Phase 3 use": "initial QCi Dirac-3 smoke test before full main-run payloads",
            }
        )
    return pd.DataFrame(rows)


def _platform_comparison_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "platform": "QCi Dirac-3",
                "fit for cubic continuous model": "Strong: accepts bounded degree-3 polynomial structure directly after eqc-models adaptation.",
                "encoding overhead": "Low to moderate: preserve quasi-continuous variables and cubic terms.",
                "Phase 2 role": "offline payload target only; no hardware execution yet.",
                "Phase 3 role": "priority platform for repeated stochastic solves on exported payloads.",
            },
            {
                "platform": "classical NLP/MILP",
                "fit for cubic continuous model": "Strong for NLP heuristics; exact MILP would need linearization or approximation.",
                "encoding overhead": "Low for SLSQP/differential evolution; higher for MILP linearization.",
                "Phase 2 role": "baseline evidence and feasibility repair comparison.",
                "Phase 3 role": "fair rerun baseline with identical seeds, scenarios, patches, and metrics.",
            },
            {
                "platform": "D-Wave/QUBO",
                "fit for cubic continuous model": "Weaker fit because cubic and continuous terms require reduction and discretization.",
                "encoding overhead": "High: binary expansion plus quadratization introduces auxiliary variables.",
                "Phase 2 role": "not used.",
                "Phase 3 role": "secondary comparator only if a reduced QUBO formulation is created.",
            },
            {
                "platform": "IBM gate-based",
                "fit for cubic continuous model": "Research fit, but needs circuit ansatz, encoding, and measurement design.",
                "encoding overhead": "High: discretization and circuit resources are not yet estimated.",
                "Phase 2 role": "not used.",
                "Phase 3 role": "not the initial request; possible future algorithmic comparison.",
            },
        ]
    )


def _best_methods(summary: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    return (
        summary.sort_values("expected_operating_cost").iloc[0],
        summary.sort_values("critical_load_served_fraction", ascending=False).iloc[0],
    )


def _write_tables(analysis_dir: Path, tables: dict[str, pd.DataFrame]) -> dict[str, Path]:
    table_dir = analysis_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, frame in tables.items():
        csv_path = table_dir / f"{name}.csv"
        md_path = table_dir / f"{name}.md"
        frame.to_csv(csv_path, index=False)
        md_path.write_text(_markdown_table(frame), encoding="utf-8")
        paths[f"{name}_csv"] = csv_path
        paths[f"{name}_md"] = md_path
    return paths


def _artifact_index(results_dir: Path, analysis_dir: Path, manifest_rows: pd.DataFrame, table_paths: dict[str, Path]) -> str:
    rows_md = _markdown_table(manifest_rows)
    table_lines = "\n".join(f"- `{key}`: `{path}`" for key, path in sorted(table_paths.items()))
    return f"""# Phase 2 Paper Artifact Index

## Manifest Rows

{rows_md}

## Generated Tables

{table_lines}

## Primary Result Files

- `results/summary_metrics.csv`
- `results/scenario_results.csv`
- `results/model_stats.csv`
- `results/scaling_results.csv`
- `results/cubic_vs_quadratic.csv`
- `results/phase2_headlines.md`
- `results/phase3_resource_estimate.md`
- `results/benchmarks/pglib_case5_pjm/benchmark_report.md`

## Regeneration Command

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
python scripts/build_phase2_paper.py
```

All tables in `{analysis_dir}` are derived from manifests and CSV outputs under `{results_dir}`.
"""


def _write_phase2_headlines(results_dir: Path, main_summary: pd.DataFrame, main_models: pd.DataFrame) -> Path:
    best_cost, best_critical = _best_methods(main_summary)
    comparison = _method_comparison_table(main_summary)
    max_variables = int(main_models["variable_count"].max())
    max_terms = int(main_models["term_count"].max())
    max_degree = int(main_models["degree"].max())
    text = f"""# Phase 2 Headlines

## Evidence Boundary

The prototype uses synthetic, reproducible data and no proprietary grid data. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed. CMPO-local is a pre-QCi local polynomial-search proxy only.

## Main Benchmark Method Comparison

{_markdown_table(comparison)}

## Current Main-Run Finding

Best expected operating cost is `{best_cost['method_name']}` at `{best_cost['expected_operating_cost']:.6g}`. Best critical-load served fraction is `{best_critical['method_name']}` at `{best_critical['critical_load_served_fraction']:.4f}`.

The main result is mixed: differential evolution is strongest on expected cost in the full main run when enabled, while CMPO-local is strongest on critical-load-served fraction but still needs better feasibility repair before any hardware-performance claim.

## Hamiltonian Size And Export Readiness

The main run exports degree-{max_degree} polynomial payloads for later QCi Dirac-3 / `eqc-models` adaptation. Main-run Hamiltonians reach `{max_variables}` variables and `{max_terms}` terms, so those larger sizes should be stated honestly and not replaced by smaller scaling-study figures.

## Phase 3 Direction

The Phase 3 resource request should prioritize QCi Dirac-3 because the model preserves cubic generator costs and higher-order mode-selection terms directly. Classical baselines for fair comparison include greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search.
"""
    path = results_dir / "phase2_headlines.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_phase3_resource_estimate(
    results_dir: Path,
    main_models: pd.DataFrame,
    scaling_summary: pd.DataFrame,
    qci_small_models: pd.DataFrame | None,
) -> Path:
    main_manifest = _read_json(results_dir / "run_manifest.json")
    main_max_variables = int(main_models["variable_count"].max())
    main_median_variables = float(main_models["variable_count"].median())
    main_max_terms = int(main_models["term_count"].max())
    main_max_degree = int(main_models["degree"].max())
    scaling_max_payloads = int(scaling_summary["payload_count"].max())
    scaling_max_variables = int(scaling_summary["max_variables"].max())
    scaling_max_terms = int(scaling_summary["max_terms"].max())
    if qci_small_models is None:
        qci_small_text = "The optional `results/qci_small` run has not been generated in this artifact set."
    else:
        qci_small_manifest = _optional_json(results_dir / "qci_small" / "run_manifest.json") or {}
        qci_small_summary = _optional_csv(results_dir / "qci_small" / "summary_metrics.csv")
        small_best_cost = None if qci_small_summary is None else qci_small_summary.sort_values("expected_operating_cost").iloc[0]
        small_best_critical = (
            None
            if qci_small_summary is None
            else qci_small_summary.sort_values("critical_load_served_fraction", ascending=False).iloc[0]
        )
        metric_sentence = (
            "Small-run metrics are available in `results/qci_small/summary_metrics.csv`."
            if small_best_cost is None
            else (
                f"On `qci_small`, best expected cost is `{small_best_cost['method_name']}` "
                f"({small_best_cost['expected_operating_cost']:.6g}) and best critical-load served fraction is "
                f"`{small_best_critical['method_name']}` ({small_best_critical['critical_load_served_fraction']:.4f})."
            )
        )
        qci_small_text = (
            f"The conservative `qci_small` run exports `{int(qci_small_manifest.get('payload_count', len(qci_small_models)))}` "
            f"payloads with max `{int(qci_small_models['variable_count'].max())}` variables, median "
            f"`{qci_small_models['variable_count'].median():.0f}` variables, max `{int(qci_small_models['term_count'].max())}` "
            f"terms, and max degree `{int(qci_small_models['degree'].max())}`. {metric_sentence}"
        )
    text = f"""# Phase 3 Resource Estimate

## Evidence Boundary

This is a pre-QCi local evidence package. It uses synthetic, reproducible data; no proprietary grid data is used. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.

## Main Run Versus Scaling Study

The main Phase 2 run generated `{int(main_manifest['payload_count'])}` scenario/patch payloads with max `{main_max_variables}` variables, median `{main_median_variables:.0f}` variables, max `{main_max_terms}` polynomial terms, and max degree `{main_max_degree}`.

The largest scaling-study row generated `{scaling_max_payloads}` payloads with up to `{scaling_max_variables}` variables and `{scaling_max_terms}` terms per Hamiltonian. If the scaling study reports `{scaling_max_variables}` variables, that number refers to the scaling-study one-patch cases only; it is not the largest observed main-run Hamiltonian when the main selected patches use more microgrids.

## Conservative Initial QCi Request

{qci_small_text}

## Platform Request

Phase 3 should prioritize QCi Dirac-3 because the CMPO formulation preserves cubic generator costs and higher-order mode-selection terms directly as degree-3 polynomial payloads. The first hardware request should run repeated stochastic solves on `qci_small` payloads, then expand to the full main-run payload set if job limits and runtime behavior are acceptable.

## Fair Classical Comparison

Classical baselines should be rerun with identical seeds, scenarios, patches, repair logic, and metric aggregation. The comparison set is greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search. CMPO-local remains a pre-QCi local polynomial-search proxy, not a quantum result.
"""
    path = results_dir / "phase3_resource_estimate.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_submission_tables(results_dir: Path, tables: dict[str, pd.DataFrame]) -> Path:
    text = f"""# Submission Tables

## Main Benchmark Method Comparison

{_markdown_table(tables["submission_method_comparison"])}

## Scenario Stress Summary

{_markdown_table(tables["submission_scenario_stress"])}

## QCi Payload/Resource Summary

{_markdown_table(tables["submission_resource_summary"])}

## Platform Comparison

{_markdown_table(tables["submission_platform_comparison"])}
"""
    path = results_dir / "submission_tables.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_submission_key_findings(results_dir: Path, main_summary: pd.DataFrame, qci_small_summary: pd.DataFrame | None) -> Path:
    best_cost, best_critical = _best_methods(main_summary)
    small_text = ""
    if qci_small_summary is not None:
        small_cost, small_critical = _best_methods(qci_small_summary)
        small_text = (
            f"\n- The optional `qci_small` run provides a conservative hardware-start payload set; "
            f"its best expected-cost method is `{small_cost['method_name']}` and its best critical-load method is "
            f"`{small_critical['method_name']}`."
        )
    text = f"""# Submission Key Findings

- The prototype uses deterministic synthetic data and no proprietary grid data.
- No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.
- The repository exports degree-3 polynomial payloads for later Dirac-3 / `eqc-models` adaptation.
- Classical baselines include greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search.
- Main-run results are mixed: `{best_cost['method_name']}` is best by expected operating cost, while `{best_critical['method_name']}` is best by critical-load served fraction.
- The Phase 3 resource request should prioritize QCi Dirac-3 because CMPO preserves cubic generator costs and higher-order mode-selection terms directly.
{small_text}
"""
    path = results_dir / "submission_key_findings.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_submission_limitations(results_dir: Path) -> Path:
    text = """# Submission Limitations

## Judge Risk Checklist

- Feasibility rate currently below ideal for SLSQP and CMPO-local.
- CMPO-local is not yet a quantum hardware result.
- Synthetic data is useful for reproducibility but not a full utility-grade AC-SCUC model.
- Main payload sizes may differ from conservative qci_small payload sizes.
- The final paper must not overstate QCi performance before hardware access.

## Non-Claims

The Phase 2 evidence does not claim live QCi hardware execution, quantum advantage, proprietary grid validation, operational grid readiness, or a full AC-SCUC formulation.
"""
    path = results_dir / "submission_limitations.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_submission_package(
    results_dir: Path,
    analysis_dir: Path,
    submission_tables: dict[str, pd.DataFrame],
    main_summary: pd.DataFrame,
    main_models: pd.DataFrame,
    qci_small_summary: pd.DataFrame | None,
    qci_small_models: pd.DataFrame | None,
) -> dict[str, Path]:
    package_dir = results_dir.parent / "submission_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    best_cost, best_critical = _best_methods(main_summary)
    small_section = "The optional `qci_small` artifact set was not present when this package was built."
    if qci_small_summary is not None and qci_small_models is not None:
        small_cost, small_critical = _best_methods(qci_small_summary)
        small_manifest = _optional_json(results_dir / "qci_small" / "run_manifest.json") or {}
        small_section = (
            f"`qci_small` was generated with `{int(small_manifest.get('payload_count', len(qci_small_models)))}` payloads, "
            f"max `{int(qci_small_models['variable_count'].max())}` variables, max `{int(qci_small_models['term_count'].max())}` "
            f"terms, max degree `{int(qci_small_models['degree'].max())}`. Its best expected-cost method is "
            f"`{small_cost['method_name']}` and its best critical-load method is `{small_critical['method_name']}`."
        )

    methods = f"""# Phase 2 Methods

CMPO is a pre-QCi local prototype for resilient microgrid cost optimization. It generates deterministic synthetic microgrid cases, selects overlapping islandable patches, builds per-scenario degree-3 polynomial Hamiltonians, repairs decoded dispatches, and aggregates cost/resilience metrics.

Classical baselines are greedy critical-load-first dispatch, SLSQP local optimization, differential evolution when enabled, and CMPO-local polynomial search. CMPO-local is a CPU-only local polynomial-search proxy and is not a QCi hardware result.

The polynomial model preserves cubic generator costs and higher-order mode-selection terms directly. Payloads are exported for later QCi Dirac-3 / `eqc-models` adaptation, but no live QCi execution has been performed yet.
"""

    results_summary = f"""# Phase 2 Results Summary

The prototype uses synthetic, reproducible data and no proprietary grid data. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.

## Main Benchmark Method Comparison

{_markdown_table(submission_tables["submission_method_comparison"])}

Main-run results are mixed: `{best_cost['method_name']}` is strongest by expected operating cost, while `{best_critical['method_name']}` is strongest by critical-load served fraction. CMPO-local needs better feasibility repair before any stronger performance claim.

## Scenario Stress Summary

{_markdown_table(submission_tables["submission_scenario_stress"])}

## Conservative QCi-Friendly Run

{small_section}
"""

    platform_request = f"""# Phase 2 Platform Request

## QCi Payload/Resource Summary

{_markdown_table(submission_tables["submission_resource_summary"])}

## Platform Comparison

{_markdown_table(submission_tables["submission_platform_comparison"])}

Phase 3 should prioritize QCi Dirac-3 because the CMPO model preserves cubic generator costs and higher-order mode-selection terms directly. The conservative request is to start with `results/qci_small/qci_payloads/*.json`, then expand to the full main-run payloads after job behavior is understood.

The main run reaches `{int(main_models['variable_count'].max())}` variables and `{int(main_models['term_count'].max())}` terms per Hamiltonian. Smaller `qci_small` payload sizes should be described as conservative initial hardware requests, not as the maximum observed model size.
"""

    artifact_rows = [
        ("results/run_manifest.json", "main synthetic run manifest"),
        ("results/summary_metrics.csv", "main method metrics"),
        ("results/scenario_results.csv", "scenario-level metrics"),
        ("results/model_stats.csv", "main Hamiltonian sizes"),
        ("results/qci_small/summary_metrics.csv", "small QCi-friendly method metrics"),
        ("results/qci_small/model_stats.csv", "small QCi-friendly Hamiltonian sizes"),
        ("results/submission_tables.md", "judge-ready tables"),
        ("results/submission_key_findings.md", "concise findings and claim boundaries"),
        ("results/submission_limitations.md", "judge risk checklist"),
        ("results/phase3_resource_estimate.md", "main/scaling/qci_small resource comparison"),
        ("analysis/paper/artifact_index.md", "derived paper artifact index"),
    ]
    artifact_table = pd.DataFrame(artifact_rows, columns=["artifact", "purpose"])
    artifacts_manifest = f"""# Artifacts Manifest

All listed artifacts are generated from repository scripts and saved CSV/JSON manifests.

{_markdown_table(artifact_table)}

## Reproduction Commands

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
python scripts/build_phase2_paper.py
pytest -q
```

The standalone export command writes to `results/qci_export/` so it does not overwrite main-run `results/model_stats.csv` or `results/qci_payloads/`.
"""

    outputs = {
        "phase2_methods": package_dir / "phase2_methods.md",
        "phase2_results_summary": package_dir / "phase2_results_summary.md",
        "phase2_platform_request": package_dir / "phase2_platform_request.md",
        "artifacts_manifest": package_dir / "artifacts_manifest.md",
    }
    outputs["phase2_methods"].write_text(methods, encoding="utf-8")
    outputs["phase2_results_summary"].write_text(results_summary, encoding="utf-8")
    outputs["phase2_platform_request"].write_text(platform_request, encoding="utf-8")
    outputs["artifacts_manifest"].write_text(artifacts_manifest, encoding="utf-8")
    return outputs


def _paper_text(
    main_results: pd.DataFrame,
    benchmark_results: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    cubic_results: pd.DataFrame,
    scaling_summary: pd.DataFrame,
    main_model: dict[str, Any],
    benchmark_model: dict[str, Any],
    manifest_rows: pd.DataFrame,
    resource_summary: pd.DataFrame,
    qci_small_summary: pd.DataFrame | None,
) -> str:
    best_cost = main_results.sort_values("expected_operating_cost").iloc[0]
    best_critical = main_results.sort_values("critical_load_served_fraction", ascending=False).iloc[0]
    best_benchmark = benchmark_results.sort_values("expected_operating_cost").iloc[0]
    max_payload_count = int(scaling_summary["payload_count"].max())
    max_variables = int(scaling_summary["max_variables"].max())
    max_terms = int(scaling_summary["max_terms"].max())
    qci_small_sentence = (
        "The optional `qci_small` conservative hardware-start run was not present when this draft was built."
        if qci_small_summary is None
        else "The optional `qci_small` conservative hardware-start run is included in the resource summary and has its own metrics under `results/qci_small/`."
    )
    cubic_nonzero = cubic_results[abs(cubic_results["true_cubic_cost_difference_vs_cubic"]) > 1e-9]
    cubic_sentence = (
        "The cubic-vs-quadratic experiment produced nonzero true-cubic cost differences for at least one optimized solution, "
        "showing that approximation choice can change dispatch economics under the true cubic objective."
        if not cubic_nonzero.empty
        else "The cubic-vs-quadratic experiment found no nonzero true-cubic cost difference in this small instance; the larger value is preserving the degree-3 export path."
    )

    return f"""# Restorers CMPO Phase 2 Paper Draft

## Abstract

Restorers proposes the Cubic Microgrid Patch Optimizer (CMPO) as a Phase 2 pre-QCi workflow for resilient microgrid cost optimization. The prototype generates deterministic synthetic microgrid patch cases, evaluates contingencies, builds degree-3 Hamiltonian/polynomial models with native cubic generator costs, compares classical baselines, and exports QCi/Dirac-3-ready JSON payloads. The main synthetic run used seed 42, four microgrids, a six-hour horizon, eight scenarios, two selected overlapping patches, and 16 exported payloads. No proprietary grid data is used, no live QCi hardware execution has been performed, and no quantum advantage is claimed. A public-benchmark-derived PGLib case5-PJM adapter adds an external reference stress case without claiming AC OPF reproduction.

## Contributions

1. A reproducible resilient microgrid dataset and scenario generator covering normal operation, renewable shortfall, demand surge, PCC failure, local generator failure, forced islanding, restoration, and combined stress.
2. A microgrid design stage that selects overlapping islandable patches and records upgrade-cost and coverage metrics.
3. A bounded polynomial/Hamiltonian builder that preserves cubic generation costs while keeping exported instances at degree <= 3.
4. Classical baselines and a clearly labeled pre-QCi CMPO-local polynomial search proxy.
5. A QCi export layer with model statistics, coefficient-scaling metadata, and a documented Phase 3 `eqc-models` adapter path.
6. A PGLib-OPF case5-PJM-derived benchmark adapter with pinned provenance and benchmark-specific results.

## Experimental Setup

The main case is deterministic synthetic research data. It does not use private utility data. The benchmark case adapts public PGLib-OPF case5-PJM anchors into the CMPO microgrid contract: bus active loads, generator capacities/cost slopes, and branch ratings are reused as anchors; PV, BESS, PCC, critical-load, and upgrade fields are deterministic synthetic additions. The benchmark provenance is recorded in `manifests/upstream/pglib-opf-case5-pjm.json`.

The compared methods are GreedyCriticalLoadFirst, SLSQPDispatchOptimizer, DifferentialEvolutionOptimizer on the main non-quick run, and CMPO-local polynomial search. CMPO-local is a CPU-only pre-QCi local polynomial-search proxy, not QCi hardware execution.

## Main Results

{_markdown_table(main_results)}

Best expected operating cost in the main run is `{best_cost['method_name']}` at `{best_cost['expected_operating_cost']:.6g}` computed cost units. Best average critical-load served fraction is `{best_critical['method_name']}` at `{best_critical['critical_load_served_fraction']:.4f}`. Results are mixed: differential evolution is strongest on expected cost in the main non-quick run, while CMPO-local is strongest on critical-load-served fraction but needs better feasibility repair. This separation is useful for Phase 3: the cheapest repaired dispatch is not automatically the best resilience outcome, so QCi evaluation should compare both cost and resilience metrics.

## Scenario Stress Summary

{_markdown_table(scenario_summary)}

The scenario table is derived from `results/scenario_results.csv`. It highlights where unserved energy and critical-energy-not-served appear after repair, rather than relying only on aggregate expected cost.

## Public Benchmark Result

{_markdown_table(benchmark_results)}

The adapted PGLib case5-PJM run exports `{int(manifest_rows.loc[manifest_rows['run_name'] == 'pglib_case5_pjm_adapted', 'payload_count'].iloc[0])}` benchmark payloads. Best expected operating cost on the benchmark is `{best_benchmark['method_name']}` at `{best_benchmark['expected_operating_cost']:.6g}` computed cost units. This strengthens Phase 2 by showing the CMPO workflow can ingest a public benchmark-derived case while preserving the same metrics and export contract.

## Cubic Cost Evidence

{_markdown_table(cubic_results)}

{cubic_sentence} Final comparisons evaluate both variants under the true cubic objective in `results/cubic_vs_quadratic.csv`.

## Scaling And Phase 3 Resource Need

{_markdown_table(scaling_summary.tail(8).reset_index(drop=True))}

The largest scaling case in `results/scaling_results.csv` uses `{max_payload_count}` scenario/patch payloads with up to `{max_variables}` variables and `{max_terms}` polynomial terms per Hamiltonian. That `{max_variables}`-variable figure is a scaling-study one-patch figure, not the maximum main-run Hamiltonian if the main selected patches are larger. The main run reaches `{main_model['max_variables']}` variables and `{main_model['max_terms']}` terms per Hamiltonian. The resource estimate in `results/phase3_resource_estimate.md` recommends one Dirac-3 job per scenario/patch payload and repeated stochastic solves per payload for fair comparison.

## QCi Payload Resource Summary

{_markdown_table(resource_summary)}

{qci_small_sentence}

## Hamiltonian And Export Readiness

The main run exported `{main_model['payloads']}` payloads with max degree `{main_model['max_degree']}`, max `{main_model['max_variables']}` variables, max `{main_model['max_terms']}` terms, median `{main_model['median_variables']:.0f}` variables, and median `{main_model['median_terms']:.0f}` terms. The public-benchmark run exported `{benchmark_model['payloads']}` payloads with max degree `{benchmark_model['max_degree']}`. Payload terms reference declared variables and include bounds, encoding type, objective sense, scaling metadata, and scenario/patch metadata.

## Phase 3 Plan

Phase 3 should prioritize QCi Dirac-3 because CMPO preserves cubic generator costs and higher-order mode-selection terms directly. The implementation path is to connect `cmpo.qci_export.convert_to_eqc_models_format()` to the confirmed QCi `eqc-models` API, run repeated Dirac-3 solves per scenario/patch payload, and rerun the same classical baselines with identical seeds, scenarios, patches, repair logic, and metrics. The primary success criterion should be multi-metric: expected cost, critical load served, energy not served, feasibility rate, runtime, and model size.

## Non-Claims

This paper draft does not claim live QCi hardware execution, hardware quantum advantage, operational grid readiness, or private/proprietary data use. All reported numbers are generated by repository scripts and trace back to CSV files and manifests.

## Reproduction

```bash
pip install -r requirements.txt
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/build_phase2_paper.py
pytest -q
```
"""


def main() -> None:
    """Generate paper-facing artifacts from saved run outputs."""

    args = build_parser().parse_args()
    results_dir = Path(args.results_dir)
    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = _manifest_rows(results_dir)
    manifest_rows_path = analysis_dir / "manifest_rows.csv"
    manifest_rows.to_csv(manifest_rows_path, index=False)

    main_summary = _read_csv(results_dir / "summary_metrics.csv")
    main_scenarios = _read_csv(results_dir / "scenario_results.csv")
    main_models = _read_csv(results_dir / "model_stats.csv")
    benchmark_summary = _read_csv(results_dir / "benchmarks" / "pglib_case5_pjm" / "summary_metrics.csv")
    benchmark_models = _read_csv(results_dir / "benchmarks" / "pglib_case5_pjm" / "model_stats.csv")
    scaling = _read_csv(results_dir / "scaling_results.csv")
    cubic = _read_csv(results_dir / "cubic_vs_quadratic.csv")
    qci_small_summary = _optional_csv(results_dir / "qci_small" / "summary_metrics.csv")
    qci_small_models = _optional_csv(results_dir / "qci_small" / "model_stats.csv")

    main_model_summary = _model_summary(main_models)
    benchmark_model_summary = _model_summary(benchmark_models)

    tables = {
        "main_results": _paper_table(main_summary),
        "benchmark_results": _paper_table(benchmark_summary),
        "scenario_stress_summary": _scenario_stress_summary(main_scenarios),
        "cubic_vs_quadratic": _cubic_summary(cubic),
        "scaling_resource_summary": _scaling_summary(scaling),
    }
    tables["submission_method_comparison"] = _method_comparison_table(main_summary)
    tables["submission_scenario_stress"] = _scenario_submission_table(main_scenarios)
    tables["submission_resource_summary"] = _resource_summary_table(
        results_dir,
        main_models,
        benchmark_models,
        tables["scaling_resource_summary"],
        qci_small_models,
    )
    tables["submission_platform_comparison"] = _platform_comparison_table()
    table_paths = _write_tables(analysis_dir, tables)
    index_path = analysis_dir / "artifact_index.md"
    index_path.write_text(_artifact_index(results_dir, analysis_dir, manifest_rows, table_paths), encoding="utf-8")

    _write_phase2_headlines(results_dir, main_summary, main_models)
    _write_phase3_resource_estimate(results_dir, main_models, tables["scaling_resource_summary"], qci_small_models)
    _write_submission_tables(results_dir, tables)
    _write_submission_key_findings(results_dir, main_summary, qci_small_summary)
    _write_submission_limitations(results_dir)
    package_paths = _write_submission_package(
        results_dir,
        analysis_dir,
        tables,
        main_summary,
        main_models,
        qci_small_summary,
        qci_small_models,
    )

    paper_path = results_dir / "phase2_paper.md"
    paper_path.write_text(
        _paper_text(
            main_results=tables["main_results"],
            benchmark_results=tables["benchmark_results"],
            scenario_summary=tables["scenario_stress_summary"],
            cubic_results=tables["cubic_vs_quadratic"],
            scaling_summary=tables["scaling_resource_summary"],
            main_model=main_model_summary,
            benchmark_model=benchmark_model_summary,
            manifest_rows=manifest_rows,
            resource_summary=tables["submission_resource_summary"],
            qci_small_summary=qci_small_summary,
        ),
        encoding="utf-8",
    )
    print("Phase 2 paper artifacts built")
    print(f"Manifest rows: {manifest_rows_path}")
    print(f"Artifact index: {index_path}")
    print(f"Paper draft: {paper_path}")
    print(f"Submission package: {package_paths['artifacts_manifest'].parent}")


if __name__ == "__main__":
    main()
