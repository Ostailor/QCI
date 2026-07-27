#!/usr/bin/env python3
"""Build traceable LaTeX assets for the Phase 3 paper.

The script reads a selected Phase 3 result tree and emits compact LaTeX
tables/macros plus a checksum manifest. It never changes raw experiment data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHASE3_ROOT = REPO_ROOT / "results" / "phase3"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "submission" / "paper" / "generated"

SOURCE_FILES = {
    "irc_comparison": Path(
        "results/phase3/irc_cmpo/final/table1_qci_vs_exact_and_gpu.csv"
    ),
    "irc_sweep": Path(
        "results/phase3/irc_cmpo/final/table2_cost_resilience_lambda_sweep.csv"
    ),
    "irc_resources": Path(
        "results/phase3/irc_cmpo/final/table5_resource_usage.csv"
    ),
    "irc_sample_quality": Path(
        "results/phase3/irc_cmpo/final/table3_native_sample_quality.csv"
    ),
    "irc_surrogate_metrics": Path(
        "results/phase3/irc_cmpo/surrogate/metrics.csv"
    ),
    "irc_surrogate_manifest": Path(
        "results/phase3/irc_cmpo/surrogate/fit_manifest.json"
    ),
    "irc_encoding": Path(
        "results/phase3/irc_cmpo/final/table6_encoding_comparison.csv"
    ),
    "irc_jobs": Path("results/phase3/irc_cmpo/qci/job_status.csv"),
    "irc_native_summary": Path(
        "results/phase3/irc_cmpo/qci/native_evaluation_summary.json"
    ),
    "sc_payload_manifest": Path("results/phase3/sc_cmpo/payload_manifest.csv"),
    "sc_jobs": Path("results/phase3/sc_cmpo/qci/job_status.csv"),
}

OUTPUT_FILES = (
    "asset_sources.json",
    "encoding_efficiency.tex",
    "headline_results.tex",
    "paper_macros.tex",
)

EXPECTED_SC_BENCHMARKS = {
    "pglib_case14_ieee",
    "pglib_case30_ieee",
    "arpae_go_network_01o_020",
    "ieee123_opendss",
}


def _source_path(relative_path: Path, phase3_root: Path) -> Path:
    prefix = Path("results/phase3")
    try:
        suffix = relative_path.relative_to(prefix)
    except ValueError as exc:
        raise ValueError(f"paper source is not under {prefix}: {relative_path}") from exc
    return phase3_root / suffix


def _read_csv(
    relative_path: Path, phase3_root: Path = DEFAULT_PHASE3_ROOT
) -> list[dict[str, str]]:
    path = _source_path(relative_path, phase3_root)
    if not path.is_file():
        raise FileNotFoundError(f"Required paper source is missing: {relative_path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(
    relative_path: Path, phase3_root: Path = DEFAULT_PHASE3_ROOT
) -> dict[str, Any]:
    path = _source_path(relative_path, phase3_root)
    if not path.is_file():
        raise FileNotFoundError(f"Required paper source is missing: {relative_path}")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {relative_path}")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _float(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    if value in {"", None}:
        raise ValueError(f"Missing numeric field {field!r} in row: {row}")
    return float(value)


def _pick(
    rows: Iterable[dict[str, str]], **criteria: str
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if all(str(row.get(field, "")) == expected for field, expected in criteria.items())
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def _format_millions(value: float) -> str:
    return f"{value / 1_000_000:.3f}"


def _headline_table(
    rows: list[dict[str, str]],
    sample_quality: list[dict[str, str]],
) -> tuple[str, dict[str, dict[str, str]]]:
    selected = {
        "QCi IRC-CMPO": _pick(
            rows, lambda_index="1", method="QCi IRC-CMPO"
        ),
        "Exact MILP": _pick(
            rows, lambda_index="1", method="exact MILP ground state"
        ),
        "GPU local search": _pick(
            rows, lambda_index="1", method="gpu_parallel_local_search"
        ),
        "QUBO/quadratized": _pick(
            rows, lambda_index="1", method="QUBO/quadratized master"
        ),
    }
    def emphasize(value: str, *, is_qci: bool) -> str:
        return rf"\textbf{{{value}}}" if is_qci else value

    lines = [
        r"\begin{tabular}{@{}lrr@{}}",
        r"\toprule",
        r"Method & Exact hit (\%) & Feasible (\%) \\",
        r"\midrule",
    ]
    quality_labels = (
        ("QCi IRC-CMPO", "QCi Dirac-3"),
        ("gpu_parallel_local_search", "L4 local search"),
        ("gpu_random_restart", "L4 random restart"),
        ("gpu_simulated_annealing", "L4 annealing"),
    )
    for method, display_label in quality_labels:
        method_rows = [
            row
            for row in sample_quality
            if row["method"] == method and int(row["lambda_index"]) > 0
        ]
        if len(method_rows) != 5:
            raise ValueError(
                f"Expected five positive-weight quality rows for {method}, "
                f"found {len(method_rows)}"
            )
        evaluations = sum(int(row["returned_sample_count"]) for row in method_rows)
        exact_rate = math.fsum(
            int(row["returned_sample_count"])
            * _float(row, "exact_optimum_hit_rate")
            for row in method_rows
        ) / evaluations
        feasible_rate = math.fsum(
            int(row["returned_sample_count"])
            * _float(row, "native_local_feasibility_rate")
            for row in method_rows
        ) / evaluations
        is_qci = method == "QCi IRC-CMPO"
        lines.append(
            "{} & {} & {} \\\\".format(
                emphasize(_latex_escape(display_label), is_qci=is_qci),
                emphasize(f"{100.0 * exact_rate:.1f}", is_qci=is_qci),
                emphasize(f"{100.0 * feasible_rate:.1f}", is_qci=is_qci),
            )
        )
    lines.extend((r"\bottomrule", r"\end{tabular}", ""))
    return "\n".join(lines), selected


def _encoding_table(
    rows: list[dict[str, str]],
) -> tuple[str, dict[str, dict[str, str]]]:
    selected = {
        "Native cubic": _pick(
            rows, lambda_index="1", encoding="native cubic integer"
        ),
        "Quadratized": _pick(
            rows,
            lambda_index="1",
            encoding="MILP/QUBO quadratized comparison",
        ),
    }
    lines = [
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Encoding & Logical & Auxiliary & Total & Degree \\",
        r"\midrule",
    ]
    for label, row in selected.items():
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                _latex_escape(label),
                row["logical_variables"],
                row["auxiliary_variables"],
                row["total_variables"],
                row["maximum_degree"],
            )
        )
    lines.extend((r"\bottomrule", r"\end{tabular}", ""))
    return "\n".join(lines), selected


def _benchmark_summary(
    payloads: list[dict[str, str]],
) -> dict[str, dict[str, object]]:
    observed = {row["benchmark"] for row in payloads}
    if observed != EXPECTED_SC_BENCHMARKS:
        raise ValueError(
            "SC-CMPO benchmark coverage mismatch: "
            f"expected {sorted(EXPECTED_SC_BENCHMARKS)}, found {sorted(observed)}"
        )

    summary: dict[str, dict[str, object]] = {}
    for benchmark in sorted(EXPECTED_SC_BENCHMARKS):
        benchmark_payloads = [
            row for row in payloads if row["benchmark"] == benchmark
        ]
        scenarios = {int(row["scenario_count"]) for row in benchmark_payloads}
        variables = {int(row["variable_count"]) for row in benchmark_payloads}
        degrees = {int(row["degree"]) for row in benchmark_payloads}
        if len(scenarios) != 1 or len(variables) != 1 or len(degrees) != 1:
            raise ValueError(f"Inconsistent SC-CMPO dimensions for {benchmark}")
        completed = sum(
            row.get("qci_execution_status", "").lower() == "completed"
            for row in benchmark_payloads
        )
        summary[benchmark] = {
            "payloads": len(benchmark_payloads),
            "scenarios": next(iter(scenarios)),
            "variables": next(iter(variables)),
            "degree": next(iter(degrees)),
            "completed_jobs": completed,
        }
    return summary


def _paper_macros(
    headline: dict[str, dict[str, str]],
    encoding: dict[str, dict[str, str]],
    benchmark_summary: dict[str, dict[str, object]],
    irc_jobs: list[dict[str, str]],
    sample_quality: list[dict[str, str]],
    sc_jobs: list[dict[str, str]],
    sc_payloads: list[dict[str, str]],
    resources: list[dict[str, str]],
    surrogate_metrics: list[dict[str, str]],
    surrogate_manifest: dict[str, Any],
) -> str:
    irc_completed = [
        row for row in irc_jobs if row.get("status", "").upper() == "COMPLETED"
    ]
    sc_completed = [
        row for row in sc_jobs if row.get("status", "").upper() == "COMPLETED"
    ]
    irc_samples = sum(int(row["num_samples"]) for row in irc_completed)
    qci_quality = [
        row for row in sample_quality if row.get("method") == "QCi IRC-CMPO"
    ]
    production_samples = sum(
        int(row["returned_sample_count"]) for row in qci_quality
    )
    exact_ground_state_samples = sum(
        round(
            int(row["returned_sample_count"])
            * float(row["exact_optimum_hit_rate"])
        )
        for row in qci_quality
    )
    positive_weight_rows = [
        row for row in qci_quality if int(row["lambda_index"]) > 0
    ]
    positive_weight_samples = sum(
        int(row["returned_sample_count"]) for row in positive_weight_rows
    )
    positive_weight_exact_samples = sum(
        round(
            int(row["returned_sample_count"])
            * float(row["exact_optimum_hit_rate"])
        )
        for row in positive_weight_rows
    )
    positive_l4_rates: dict[str, float] = {}
    for method in {
        row["method"]
        for row in sample_quality
        if row.get("method", "").startswith("gpu_")
    }:
        method_rows = [
            row
            for row in sample_quality
            if row["method"] == method and int(row["lambda_index"]) > 0
        ]
        evaluations = sum(int(row["returned_sample_count"]) for row in method_rows)
        positive_l4_rates[method] = math.fsum(
            int(row["returned_sample_count"])
            * float(row["exact_optimum_hit_rate"])
            for row in method_rows
        ) / evaluations
    best_l4_positive_rate = max(positive_l4_rates.values())
    native_integer_samples = sum(
        round(
            int(row["returned_sample_count"]) * float(row["native_integer_rate"])
        )
        for row in qci_quality
    )
    native_feasible_samples = sum(
        round(
            int(row["returned_sample_count"])
            * float(row["native_local_feasibility_rate"])
        )
        for row in qci_quality
    )
    exact_rates = [float(row["exact_optimum_hit_rate"]) for row in qci_quality]
    sc_repeat_budgets = [
        int(row["qci_repeat_budget"])
        for row in sc_payloads
        if row.get("qci_execution_status", "").lower() == "completed"
    ]
    sc_samples = sum(sc_repeat_budgets)

    qci_resources = [
        row
        for row in resources
        if row.get("method") == "QCi IRC-CMPO"
        and row.get("device_usage_seconds", "")
    ]
    device_seconds = [_float(row, "device_usage_seconds") for row in qci_resources]
    time_to_good_seconds = [
        _float(row, "time_to_good_solution_seconds") for row in qci_resources
    ]
    l4_seconds = [
        _float(row, "runtime_seconds")
        for row in resources
        if row.get("method", "").startswith("gpu_")
    ]

    qci = headline["QCi IRC-CMPO"]
    qubo = headline["QUBO/quadratized"]
    native = encoding["Native cubic"]
    quadratized = encoding["Quadratized"]
    scenario_counts = {int(row["scenario_count"]) for row in sc_payloads}
    if scenario_counts != {8}:
        raise ValueError(
            f"Paper headline requires eight common scenarios, found {scenario_counts}"
        )
    scenario_count = next(iter(scenario_counts))
    qci_expected_infrastructure_hours = _float(
        qci, "critical_infrastructure_outage_hours"
    )
    qubo_expected_infrastructure_hours = _float(
        qubo, "critical_infrastructure_outage_hours"
    )

    def percentage_reduction(smaller: float, larger: float) -> float:
        if larger <= 0.0:
            raise ValueError("percentage reduction requires a positive reference")
        return 100.0 * (larger - smaller) / larger
    critical_ens_surrogate = _pick(surrogate_metrics, target="critical_ens")
    maximum_unserved_surrogate = _pick(
        surrogate_metrics, target="maximum_customers_unserved"
    )
    infrastructure_hours_surrogate = _pick(
        surrogate_metrics, target="critical_infrastructure_outage_hours"
    )
    primary_surrogate_rows = (
        critical_ens_surrogate,
        maximum_unserved_surrogate,
        infrastructure_hours_surrogate,
    )
    split_counts = surrogate_manifest.get("split_counts")
    if not isinstance(split_counts, dict):
        raise ValueError("IRC-CMPO surrogate manifest is missing split_counts")
    values: list[tuple[str, object]] = [
        ("IrcQciJobs", len(irc_completed)),
        ("IrcQciSamples", irc_samples),
        ("IrcProductionSamples", production_samples),
        ("IrcExactGroundStateSamples", exact_ground_state_samples),
        (
            "IrcExactGroundStatePercent",
            f"{100.0 * exact_ground_state_samples / production_samples:.1f}",
        ),
        ("IrcPositiveWeightSamples", positive_weight_samples),
        ("IrcPositiveWeightExactSamples", positive_weight_exact_samples),
        (
            "IrcPositiveWeightExactPercent",
            f"{100.0 * positive_weight_exact_samples / positive_weight_samples:.1f}",
        ),
        (
            "IrcBestLFourPositiveWeightExactPercent",
            f"{100.0 * best_l4_positive_rate:.1f}",
        ),
        (
            "IrcPositiveWeightExactAdvantagePoints",
            f"{100.0 * (positive_weight_exact_samples / positive_weight_samples - best_l4_positive_rate):.1f}",
        ),
        (
            "IrcMinimumExactGroundStatePercent",
            f"{100.0 * min(exact_rates):.0f}",
        ),
        (
            "IrcMaximumExactGroundStatePercent",
            f"{100.0 * max(exact_rates):.0f}",
        ),
        ("IrcNativeIntegerSamples", native_integer_samples),
        ("IrcNativeFeasibleSamples", native_feasible_samples),
        ("IrcLogicalVariables", native["logical_variables"]),
        ("IrcMaximumDegree", native["maximum_degree"]),
        ("QuboAuxiliaryVariables", quadratized["auxiliary_variables"]),
        ("QuboTotalVariables", quadratized["total_variables"]),
        ("IrcUpgradeCostMillions", _format_millions(_float(qci, "upgrade_cost"))),
        (
            "IrcMaximumUnservedPercent",
            f"{100.0 * _float(qci, 'maximum_customers_unserved'):.2f}",
        ),
        (
            "IrcExpectedCriticalInfrastructureHours",
            f"{qci_expected_infrastructure_hours:.3f}",
        ),
        (
            "IrcTotalCriticalInfrastructureHours",
            f"{scenario_count * qci_expected_infrastructure_hours:.1f}",
        ),
        ("IrcCriticalENS", f"{_float(qci, 'critical_ens'):.3f}"),
        ("IrcTotalENS", f"{_float(qci, 'total_ens'):.3f}"),
        (
            "IrcCriticalLoadServedPercent",
            f"{100.0 * _float(qci, 'critical_load_served_fraction'):.2f}",
        ),
        ("QuboUpgradeCostMillions", _format_millions(_float(qubo, "upgrade_cost"))),
        ("QuboCriticalENS", f"{_float(qubo, 'critical_ens'):.3f}"),
        (
            "QuboTotalCriticalInfrastructureHours",
            f"{scenario_count * qubo_expected_infrastructure_hours:.1f}",
        ),
        (
            "QuboMaximumUnservedPercent",
            f"{100.0 * _float(qubo, 'maximum_customers_unserved'):.2f}",
        ),
        (
            "IrcVariableReductionPercent",
            f"{percentage_reduction(float(native['total_variables']), float(quadratized['total_variables'])):.1f}",
        ),
        (
            "IrcCostReductionVsQuboPercent",
            f"{percentage_reduction(_float(qci, 'upgrade_cost'), _float(qubo, 'upgrade_cost')):.1f}",
        ),
        (
            "IrcCriticalEnsReductionVsQuboPercent",
            f"{percentage_reduction(_float(qci, 'critical_ens'), _float(qubo, 'critical_ens')):.1f}",
        ),
        (
            "IrcMaximumUnservedReductionVsQuboPercent",
            f"{percentage_reduction(_float(qci, 'maximum_customers_unserved'), _float(qubo, 'maximum_customers_unserved')):.1f}",
        ),
        (
            "IrcCriticalInfraReductionVsQuboPercent",
            f"{percentage_reduction(qci_expected_infrastructure_hours, qubo_expected_infrastructure_hours):.1f}",
        ),
        ("ScQciJobs", len(sc_completed)),
        ("ScQciSamples", sc_samples),
        ("ScBenchmarkFamilies", len(benchmark_summary)),
        ("ScPayloads", len(sc_payloads)),
        ("ScVariables", max(int(row["variable_count"]) for row in sc_payloads)),
        ("ScScenarios", max(int(row["scenario_count"]) for row in sc_payloads)),
        ("ScMaximumDegree", max(int(row["degree"]) for row in sc_payloads)),
        ("QciDeviceSecondsMinimum", f"{min(device_seconds):.0f}"),
        ("QciDeviceSecondsMaximum", f"{max(device_seconds):.0f}"),
        ("QciTimeToGoodSecondsMinimum", f"{min(time_to_good_seconds):.0f}"),
        ("QciTimeToGoodSecondsMaximum", f"{max(time_to_good_seconds):.0f}"),
        ("LFourRuntimeSecondsMinimum", f"{min(l4_seconds):.2f}"),
        ("LFourRuntimeSecondsMaximum", f"{max(l4_seconds):.2f}"),
        ("IrcSurrogateTrainPortfolios", int(split_counts["train"])),
        ("IrcSurrogateValidationPortfolios", int(split_counts["validation"])),
        ("IrcSurrogateTestPortfolios", int(split_counts["test"])),
        (
            "IrcCriticalEnsNrmsePercent",
            f"{100.0 * _float(critical_ens_surrogate, 'normalized_rmse'):.2f}",
        ),
        (
            "IrcMaximumUnservedNrmsePercent",
            f"{100.0 * _float(maximum_unserved_surrogate, 'normalized_rmse'):.2f}",
        ),
        (
            "IrcInfrastructureHoursNrmsePercent",
            f"{100.0 * _float(infrastructure_hours_surrogate, 'normalized_rmse'):.2f}",
        ),
        (
            "IrcSurrogateSpearmanMinimum",
            f"{min(_float(row, 'spearman_rank_correlation') for row in primary_surrogate_rows):.3f}",
        ),
        (
            "IrcSurrogateSpearmanMaximum",
            f"{max(_float(row, 'spearman_rank_correlation') for row in primary_surrogate_rows):.3f}",
        ),
        (
            "IrcSurrogateParetoRecallPercent",
            f"{100.0 * min(_float(row, 'pareto_front_recall') for row in primary_surrogate_rows):.0f}",
        ),
    ]
    return "\n".join(
        rf"\newcommand{{\{name}}}{{{value}}}" for name, value in values
    ) + "\n"


def _source_manifest(phase3_root: Path) -> str:
    roles = {
        "irc_comparison": "focused IRC-CMPO method comparison",
        "irc_sweep": "cost-resilience sweep and QUBO comparison",
        "irc_resources": "QCi and qBraid GPU resource usage",
        "irc_sample_quality": "native feasibility and exact-ground-state yield",
        "irc_surrogate_metrics": "held-out surrogate approximation quality",
        "irc_surrogate_manifest": "surrogate split sizes and validity gate",
        "irc_encoding": "native cubic and quadratized encoding sizes",
        "irc_jobs": "IRC-CMPO QCi completion and sample counts",
        "irc_native_summary": "native sample quality and exact-optimum checks",
        "sc_payload_manifest": "SC-CMPO benchmark dimensions and repeat budgets",
        "sc_jobs": "SC-CMPO QCi completion records",
    }
    sources = []
    for key, relative_path in SOURCE_FILES.items():
        absolute_path = _source_path(relative_path, phase3_root)
        if not absolute_path.is_file():
            raise FileNotFoundError(f"Required paper source is missing: {relative_path}")
        try:
            display_path = absolute_path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display_path = str(absolute_path)
        sources.append(
            {
                "id": key,
                "path": display_path,
                "sha256": _sha256(absolute_path),
                "role": roles[key],
            }
        )
    manifest = {
        "schema": "cmpo.phase3.paper_assets.v1",
        "generation_rule": (
            "Derived LaTeX only; selected experiment files are read without mutation."
        ),
        "sources": sources,
    }
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def build_paper_assets(
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    *,
    phase3_root: Path | str = DEFAULT_PHASE3_ROOT,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, object]:
    """Build paper assets and return a compact execution summary."""

    output_dir = Path(output_dir)
    phase3_root = Path(phase3_root)
    sweep_rows = _read_csv(SOURCE_FILES["irc_sweep"], phase3_root)
    encoding_rows = _read_csv(SOURCE_FILES["irc_encoding"], phase3_root)
    resource_rows = _read_csv(SOURCE_FILES["irc_resources"], phase3_root)
    sample_quality_rows = _read_csv(SOURCE_FILES["irc_sample_quality"], phase3_root)
    surrogate_metric_rows = _read_csv(
        SOURCE_FILES["irc_surrogate_metrics"], phase3_root
    )
    surrogate_manifest = _read_json(
        SOURCE_FILES["irc_surrogate_manifest"], phase3_root
    )
    irc_jobs = _read_csv(SOURCE_FILES["irc_jobs"], phase3_root)
    sc_jobs = _read_csv(SOURCE_FILES["sc_jobs"], phase3_root)
    sc_payloads = _read_csv(SOURCE_FILES["sc_payload_manifest"], phase3_root)
    _read_csv(SOURCE_FILES["irc_comparison"], phase3_root)
    _read_json(SOURCE_FILES["irc_native_summary"], phase3_root)

    encoding_tex, encoding_selected = _encoding_table(encoding_rows)
    headline_tex, headline_rows = _headline_table(
        sweep_rows,
        sample_quality_rows,
    )
    benchmark_summary = _benchmark_summary(sc_payloads)
    macros_tex = _paper_macros(
        headline_rows,
        encoding_selected,
        benchmark_summary,
        irc_jobs,
        sample_quality_rows,
        sc_jobs,
        sc_payloads,
        resource_rows,
        surrogate_metric_rows,
        surrogate_manifest,
    )
    contents = {
        "asset_sources.json": _source_manifest(phase3_root),
        "encoding_efficiency.tex": encoding_tex,
        "headline_results.tex": headline_tex,
        "paper_macros.tex": macros_tex,
    }

    if dry_run:
        return {
            "dry_run": True,
            "output_dir": str(output_dir),
            "files": list(contents),
        }

    existing = [output_dir / name for name in contents if (output_dir / name).exists()]
    if existing and not overwrite:
        paths = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Refusing to overwrite generated paper assets: {paths}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return {
        "dry_run": False,
        "output_dir": str(output_dir),
        "files": list(contents),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate traceable LaTeX tables and macros from Phase 3 "
            "result artifacts without modifying raw results."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated LaTeX assets (default: submission/paper/generated).",
    )
    parser.add_argument(
        "--phase3-root",
        type=Path,
        default=DEFAULT_PHASE3_ROOT,
        help="Phase 3 result root containing irc_cmpo/ and sc_cmpo/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate all inputs and report outputs without writing files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace previously generated paper assets.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = build_paper_assets(
        output_dir=args.output_dir,
        phase3_root=args.phase3_root,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
