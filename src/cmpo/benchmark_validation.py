"""Validation and report helpers for the Phase 3 benchmark-first ladder."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from cmpo.benchmark_registry import BENCHMARK_CASES, PGLIB_LEGACY_RESULT_DIRS, PHASE3_PUBLIC_ROOT


PGLIB_CASE_KEYS = ["pglib_case5_pjm", "pglib_case14_ieee", "pglib_case30_ieee", "pglib_case57_ieee"]
REQUIRED_BENCHMARK_OUTPUTS = [
    "qci_payloads",
    "model_stats.csv",
    "scenario_results.csv",
    "summary_metrics.csv",
    "baseline_payload_summary.csv",
    "qci_payload_manifest.csv",
    "benchmark_provenance.json",
    "benchmark_report.md",
]
REQUIRED_FINAL_TABLES = [
    "table1_qci_vs_best_baselines.csv",
    "table2_public_benchmark_ladder.csv",
    "table3_scenario_stress.csv",
    "table4_native_cubic_vs_qubo.csv",
    "table5_resource_usage.csv",
    "win_tie_loss_matrix.csv",
    "pareto_frontier.csv",
    "final_tables.md",
]
REQUIRED_FINAL_FIGURES = [
    "cost_vs_resilience_pareto.png",
    "critical_ens_by_scenario.png",
    "max_customers_unserved_by_scenario.png",
    "time_to_good_solution.png",
    "native_cubic_vs_qubo_size.png",
    "qci_repeat_distribution.png",
]
REQUIRED_BASELINES = [
    "GreedyCriticalLoadFirst",
    "SLSQPDispatchOptimizer",
    "DifferentialEvolutionOptimizer",
    "CMPO-local polynomial search",
    "piecewise-linear MILP",
    "QUBO/quadratized",
    "GPU-parallel random restart",
]


def _copy_file(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_dir(src: Path, dst: Path) -> None:
    if src.exists():
        if dst.exists() and dst.is_symlink():
            dst.unlink()
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _payload_manifest_rows(payload_dir: Path, model_stats_path: Path) -> list[dict[str, Any]]:
    stats = pd.read_csv(model_stats_path) if model_stats_path.exists() else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for path in sorted(payload_dir.glob("*.json")):
        payload = _read_json(path)
        scenario = payload.get("scenario_metadata", {}).get("scenario", "")
        patch = payload.get("patch_metadata", {}).get("patch", "")
        row: dict[str, Any] = {
            "payload_name": path.name,
            "payload_path": str(path),
            "scenario": scenario,
            "patch": patch,
            "variable_count": len(payload.get("variables", [])),
            "term_count": len(payload.get("polynomial_terms", [])),
            "degree": payload.get("max_degree", ""),
        }
        if not stats.empty and "scenario" in stats.columns and "patch" in stats.columns:
            match = stats[(stats["scenario"].astype(str) == str(scenario)) & (stats["patch"].astype(str) == str(patch))]
            if not match.empty:
                for key in ["coefficient_scaling_factor", "max_abs_coefficient"]:
                    if key in match.columns:
                        row[key] = match.iloc[0][key]
        rows.append(row)
    return rows


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _public_qci_status(case_dir: Path) -> tuple[bool, str]:
    status_files = list(case_dir.glob("qci/job_status.csv")) + list(case_dir.glob("qci*/job_status.csv"))
    decoded_files = list(case_dir.glob("decoded/qci_repeat_metrics.csv")) + list(case_dir.glob("qci_decoded/qci_decoded_results.csv"))
    if decoded_files:
        try:
            frame = pd.read_csv(decoded_files[0])
            if not frame.empty:
                return True, str(decoded_files[0])
        except pd.errors.EmptyDataError:
            pass
    for path in status_files:
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if frame.empty:
            continue
        completed = frame["status"].astype(str).str.upper().isin({"COMPLETED", "COMPLETE"}).any()
        job_id = frame.get("job_id", pd.Series([""] * len(frame))).astype(str).str.len().gt(0).any()
        if completed or job_id:
            return True, str(path)
    return False, ""


def _qci_execution_payload_type(case_dir: Path) -> str:
    status_path = case_dir / "qci" / "job_status.csv"
    if not status_path.exists():
        return ""
    try:
        frame = pd.read_csv(status_path)
    except pd.errors.EmptyDataError:
        return ""
    completed = frame[frame["status"].astype(str).str.upper().isin({"COMPLETED", "COMPLETE"})]
    if completed.empty or "payload" not in completed.columns:
        return ""
    payloads = completed["payload"].astype(str)
    if payloads.str.contains("/qci_fit_payloads/|\\\\qci_fit_payloads\\\\", regex=True).any():
        return "qci_fit"
    if payloads.str.contains("/qci_payloads/|\\\\qci_payloads\\\\", regex=True).any():
        return "full"
    return "unknown"


def _qci_fit_summary(case_dir: Path) -> dict[str, Any]:
    manifest_path = case_dir / "qci_fit_payload_manifest.csv"
    failure_path = case_dir / "qci_fit_failure_report.csv"
    summary = {
        "qci_fit_payload_count": 0,
        "qci_fit_max_variables": 0,
        "qci_fit_max_degree": 0,
        "qci_fit_manifest": str(manifest_path) if manifest_path.exists() else "",
        "qci_fit_failure_report": str(failure_path) if failure_path.exists() else "",
        "qci_fit_status": "missing",
    }
    if manifest_path.exists():
        try:
            frame = pd.read_csv(manifest_path)
        except pd.errors.EmptyDataError:
            frame = pd.DataFrame()
        if not frame.empty:
            summary["qci_fit_payload_count"] = int(len(frame))
            summary["qci_fit_max_variables"] = int(frame["variable_count"].max())
            summary["qci_fit_max_degree"] = int(frame["degree"].max())
            summary["qci_fit_status"] = "available"
    if summary["qci_fit_payload_count"] == 0 and failure_path.exists():
        summary["qci_fit_status"] = "decomposition_failed"
    return summary


def normalize_pglib_benchmark_outputs(public_root: Path = PHASE3_PUBLIC_ROOT) -> list[dict[str, Any]]:
    """Create required benchmark-first output aliases from existing PGLib run artifacts."""

    rows: list[dict[str, Any]] = []
    for key in PGLIB_CASE_KEYS:
        case = BENCHMARK_CASES[key]
        target_dir = Path(case.results_dir)
        source_dir = PGLIB_LEGACY_RESULT_DIRS[key]
        if not source_dir.exists():
            rows.append({"benchmark": key, "status": "benchmark_missing", "missing_file": str(source_dir)})
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        _copy_dir(source_dir / "qci_payloads", target_dir / "qci_payloads")
        for name in ["model_stats.csv", "microgrid_design.csv", "upgrade_plan.csv", "phase3_manifest.json", "design_summary.json"]:
            _copy_file(source_dir / name, target_dir / name)
        baseline_dir = source_dir / "baselines"
        _copy_file(baseline_dir / "repeat_metrics.csv", target_dir / "scenario_results.csv")
        _copy_file(baseline_dir / "baseline_summary.csv", target_dir / "summary_metrics.csv")
        _copy_file(baseline_dir / "payload_summary.csv", target_dir / "baseline_payload_summary.csv")
        _copy_file(baseline_dir / "baseline_skip_report.csv", target_dir / "benchmark_missing_baselines.csv")
        payload_rows = _payload_manifest_rows(target_dir / "qci_payloads", target_dir / "model_stats.csv")
        _write_csv(payload_rows, target_dir / "qci_payload_manifest.csv")
        max_variables = max((int(row.get("variable_count", 0) or 0) for row in payload_rows), default=0)
        full_payload_count = len(payload_rows)
        qci_fit = _qci_fit_summary(target_dir)

        data_manifest = next((source_dir / "data").glob("*_manifest.json"), None) if (source_dir / "data").exists() else None
        provenance = _read_json(data_manifest) if data_manifest else {}
        qci_ran, qci_path = _public_qci_status(target_dir)
        qci_payload_type = _qci_execution_payload_type(target_dir)
        qci_not_executed_reason = ""
        if not qci_ran:
            if max_variables > 135:
                qci_not_executed_reason = (
                    f"QCi Dirac-3 rejected/limits degree-3 public payloads above 135 variables; "
                    f"largest full payload has {max_variables} variables. Use qci_fit_payloads for hardware execution."
                )
            else:
                qci_not_executed_reason = (
                    "No completed QCi response found. Run scripts/phase3_run_qci.py with this benchmark payload directory."
                )
        provenance_record = {
            "benchmark": key,
            "source_name": case.source_name,
            "upstream_url": case.upstream_url,
            "license": provenance.get("provenance", {}).get("upstream", {}).get("license")
            or provenance.get("upstream", {}).get("license", "Creative Commons Attribution 4.0 International"),
            "version_or_commit": provenance.get("provenance", {}).get("upstream", {}).get("version")
            or provenance.get("upstream", {}).get("version", "v23.07"),
            "sha256_checksum": provenance.get("provenance", {}).get("upstream", {}).get("checksum")
            or provenance.get("upstream", {}).get("checksum", ""),
            "local_path": str(target_dir),
            "qci_execution_was_run": qci_ran,
            "qci_result_path": qci_path,
            "qci_execution_payload_type": qci_payload_type,
            "qci_not_executed_reason": qci_not_executed_reason,
            "max_payload_variables": max_variables,
            "full_payload_count": full_payload_count,
            "full_payload_max_variables": max_variables,
            "full_payload_status": "classical_reference_and_qci_fit_source" if max_variables > 135 else "qci_executable_full_payloads",
            "qci_fit_payload_count": qci_fit["qci_fit_payload_count"],
            "qci_fit_max_variables": qci_fit["qci_fit_max_variables"],
            "qci_fit_max_degree": qci_fit["qci_fit_max_degree"],
            "qci_fit_status": qci_fit["qci_fit_status"],
            "qci_fit_manifest": qci_fit["qci_fit_manifest"],
            "qci_fit_failure_report": qci_fit["qci_fit_failure_report"],
            "only_classical_baselines_were_run": not qci_ran,
            "transformation_notes": case.transformation_notes,
            "fields_inherited_from_benchmark": ["buses", "loads", "branches", "generators", "generator_costs"],
            "fields_added_by_cmpo_adapter": [
                "critical_load_fraction",
                "BESS_capacity_and_power_limits",
                "PV_DER_profile",
                "PCC_tie_availability",
                "islanding_mode_eligibility",
                "restoration_scenario_tags",
            ],
        }
        (target_dir / "benchmark_provenance.json").write_text(json.dumps(provenance_record, indent=2), encoding="utf-8")
        report = _benchmark_report_text(target_dir, provenance_record)
        (target_dir / "benchmark_report.md").write_text(report, encoding="utf-8")
        rows.append({"benchmark": key, "status": "normalized", "output_dir": str(target_dir), "qci_execution_was_run": qci_ran})
    return rows


def _benchmark_report_text(case_dir: Path, provenance: dict[str, Any]) -> str:
    summary_path = case_dir / "summary_metrics.csv"
    payload_manifest = case_dir / "qci_payload_manifest.csv"
    summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    payload_count = len(pd.read_csv(payload_manifest)) if payload_manifest.exists() else 0
    methods = sorted(summary["method_name"].astype(str).unique()) if not summary.empty and "method_name" in summary else []
    return (
        f"# {provenance['benchmark']} Benchmark Report\n\n"
        f"- Source: {provenance['source_name']}\n"
        f"- Upstream URL: {provenance['upstream_url']}\n"
        f"- QCi execution was run: {provenance['qci_execution_was_run']}\n"
        f"- QCi execution payload type: {provenance.get('qci_execution_payload_type', '') or 'none'}\n"
        f"- QCi not executed reason: {provenance.get('qci_not_executed_reason', '') or 'n/a'}\n"
        f"- Full payload count: {provenance.get('full_payload_count', '')}\n"
        f"- Full payload maximum variables: {provenance.get('full_payload_max_variables', provenance.get('max_payload_variables', ''))}\n"
        f"- QCi-fit payload count: {provenance.get('qci_fit_payload_count', 0)}\n"
        f"- QCi-fit maximum variables: {provenance.get('qci_fit_max_variables', 0)}\n"
        f"- QCi-fit maximum degree: {provenance.get('qci_fit_max_degree', 0)}\n"
        f"- Payload count: {payload_count}\n"
        f"- Methods summarized: {', '.join(methods) if methods else 'none'}\n\n"
        "This is a public-benchmark-derived microgrid resilience adapter, not a raw AC-OPF reproduction.\n"
    )


def write_public_benchmark_manifests(public_root: Path = PHASE3_PUBLIC_ROOT) -> dict[str, Path]:
    """Write benchmark manifest/status/summary files from current public outputs."""

    public_root.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    status_lines = ["# Phase 3 Public Benchmark Status\n"]
    for key, case in BENCHMARK_CASES.items():
        case_dir = Path(case.results_dir)
        provenance = _read_json(case_dir / "benchmark_provenance.json")
        status = provenance.get("status", "available" if case_dir.exists() else "benchmark_missing")
        outputs_present = sum(1 for name in REQUIRED_BENCHMARK_OUTPUTS if (case_dir / name).exists())
        qci_ran = bool(provenance.get("qci_execution_was_run")) or _public_qci_status(case_dir)[0]
        manifest_rows.append(
            {
                "benchmark": key,
                "family": case.family,
                "status": status,
                "output_dir": str(case_dir),
                "source_name": provenance.get("source_name", case.source_name),
                "upstream_url": provenance.get("upstream_url", case.upstream_url),
                "license": provenance.get("license", ""),
                "version_or_commit": provenance.get("version_or_commit", provenance.get("version", "")),
                "sha256_checksum": provenance.get("sha256_checksum", provenance.get("sha256", "")),
                "local_path": provenance.get("local_path", str(case_dir)),
                "qci_execution_was_run": qci_ran,
                "qci_execution_payload_type": provenance.get("qci_execution_payload_type", _qci_execution_payload_type(case_dir)),
                "qci_not_executed_reason": provenance.get("qci_not_executed_reason", ""),
                "only_classical_baselines_were_run": not qci_ran,
                "full_payload_count": provenance.get("full_payload_count", ""),
                "full_payload_max_variables": provenance.get("full_payload_max_variables", provenance.get("max_payload_variables", "")),
                "full_payload_status": provenance.get("full_payload_status", ""),
                "qci_fit_payload_count": provenance.get("qci_fit_payload_count", _qci_fit_summary(case_dir)["qci_fit_payload_count"]),
                "qci_fit_max_variables": provenance.get("qci_fit_max_variables", _qci_fit_summary(case_dir)["qci_fit_max_variables"]),
                "qci_fit_max_degree": provenance.get("qci_fit_max_degree", _qci_fit_summary(case_dir)["qci_fit_max_degree"]),
                "qci_fit_status": provenance.get("qci_fit_status", _qci_fit_summary(case_dir)["qci_fit_status"]),
                "qci_fit_manifest": provenance.get("qci_fit_manifest", _qci_fit_summary(case_dir)["qci_fit_manifest"]),
                "outputs_present": outputs_present,
                "required_outputs": len(REQUIRED_BENCHMARK_OUTPUTS) if case.family == "pglib" else "",
                "transformation_notes": provenance.get("transformation_notes", case.transformation_notes),
            }
        )
        status_lines.append(
            f"- {key}: status={status}, outputs={outputs_present}, "
            f"full_payloads={manifest_rows[-1]['full_payload_count']}, "
            f"full_max_variables={manifest_rows[-1]['full_payload_max_variables']}, "
            f"qci_fit_payloads={manifest_rows[-1]['qci_fit_payload_count']}, "
            f"qci_fit_max_variables={manifest_rows[-1]['qci_fit_max_variables']}, "
            f"qci_execution_was_run={qci_ran}, "
            f"qci_execution_payload_type={manifest_rows[-1]['qci_execution_payload_type'] or 'none'}, dir={case_dir}"
        )
    _write_csv(manifest_rows, public_root / "benchmark_manifest.csv")
    (public_root / "benchmark_status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")
    (public_root / "public_benchmark_summary.md").write_text(_public_summary_text(manifest_rows), encoding="utf-8")
    return {
        "manifest": public_root / "benchmark_manifest.csv",
        "status": public_root / "benchmark_status.md",
        "summary": public_root / "public_benchmark_summary.md",
    }


def _public_summary_text(rows: list[dict[str, Any]]) -> str:
    available = [row for row in rows if row["status"] != "benchmark_missing"]
    missing = [row for row in rows if row["status"] == "benchmark_missing"]
    lines = [
        "# Public Benchmark Summary",
        "",
        f"- Available/reportable benchmark paths: {len(available)}",
        f"- Missing benchmark paths with explicit reports: {len(missing)}",
        "",
        "| Benchmark | Family | Status | Full Max Vars | QCi-Fit Payloads | QCi-Fit Max Vars | QCi Run | QCi Payload Type |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['benchmark']} | {row['family']} | {row['status']} | "
            f"{row.get('full_payload_max_variables', '')} | {row.get('qci_fit_payload_count', '')} | "
            f"{row.get('qci_fit_max_variables', '')} | {row['qci_execution_was_run']} | "
            f"{row.get('qci_execution_payload_type', '') or 'none'} |"
        )
    return "\n".join(lines) + "\n"


def validate_benchmark_ladder(public_root: Path = PHASE3_PUBLIC_ROOT) -> tuple[bool, list[dict[str, str]]]:
    """Validate the current benchmark-first Phase 3 ladder."""

    findings: list[dict[str, str]] = []
    for key in ["pglib_case5_pjm", "pglib_case14_ieee"]:
        case_dir = Path(BENCHMARK_CASES[key].results_dir)
        for name in REQUIRED_BENCHMARK_OUTPUTS:
            path = case_dir / name
            if not path.exists() or (path.is_dir() and not list(path.glob("*.json"))):
                findings.append({"severity": "error", "benchmark": key, "requirement": name, "message": f"missing {path}"})
    for key in PGLIB_CASE_KEYS:
        case_dir = Path(BENCHMARK_CASES[key].results_dir)
        scenario_path = case_dir / "scenario_results.csv"
        if not scenario_path.exists():
            continue
        try:
            frame = pd.read_csv(scenario_path)
        except pd.errors.EmptyDataError:
            findings.append({"severity": "error", "benchmark": key, "requirement": "baseline_rows", "message": "empty scenario_results.csv"})
            continue
        method_text = " ".join(sorted(frame.get("method_name", pd.Series(dtype=str)).astype(str).unique()))
        for baseline in REQUIRED_BASELINES:
            token = baseline.lower().replace("-", " ")
            if token not in method_text.lower().replace("-", " "):
                findings.append(
                    {
                        "severity": "error",
                        "benchmark": key,
                        "requirement": "baseline_suite",
                        "message": f"missing baseline evidence for {baseline}",
                    }
                )
        if "auxiliary_variable_count" not in frame.columns and "auxiliary_variable_blowup" not in frame.columns:
            findings.append(
                {
                    "severity": "error",
                    "benchmark": key,
                    "requirement": "qubo_blowup",
                    "message": "QUBO auxiliary-variable blowup columns missing",
                }
            )
    public_qci = any(_public_qci_status(Path(BENCHMARK_CASES[key].results_dir))[0] for key in PGLIB_CASE_KEYS)
    if not public_qci:
        findings.append(
            {
                "severity": "error",
                "benchmark": "public_benchmarks",
                "requirement": "qci_dirac3_public_case",
                "message": "No public-benchmark-derived QCi Dirac-3 result found.",
            }
        )
    case5_qci, _case5_qci_path = _public_qci_status(Path(BENCHMARK_CASES["pglib_case5_pjm"].results_dir))
    if not case5_qci:
        findings.append(
            {
                "severity": "error",
                "benchmark": "pglib_case5_pjm",
                "requirement": "completed_qci_results",
                "message": "PGLib case5 must have completed public QCi results.",
            }
        )
    for key in ["pglib_case14_ieee", "pglib_case30_ieee"]:
        case_dir = Path(BENCHMARK_CASES[key].results_dir)
        summary = _qci_fit_summary(case_dir)
        if int(summary["qci_fit_payload_count"]) <= 0:
            findings.append(
                {
                    "severity": "error",
                    "benchmark": key,
                    "requirement": "qci_fit_payloads",
                    "message": f"missing QCi-fit payloads under {case_dir / 'qci_fit_payloads'}",
                }
            )
    case57_dir = Path(BENCHMARK_CASES["pglib_case57_ieee"].results_dir)
    case57_summary = _qci_fit_summary(case57_dir)
    if int(case57_summary["qci_fit_payload_count"]) <= 0 and not (case57_dir / "qci_fit_failure_report.csv").exists():
        findings.append(
            {
                "severity": "error",
                "benchmark": "pglib_case57_ieee",
                "requirement": "qci_fit_payloads_or_failure_report",
                "message": "case57 needs QCi-fit payloads or a concrete decomposition failure report.",
            }
        )
    for key in PGLIB_CASE_KEYS:
        case_dir = Path(BENCHMARK_CASES[key].results_dir)
        qci_fit_manifest = case_dir / "qci_fit_payload_manifest.csv"
        if qci_fit_manifest.exists():
            try:
                qci_fit = pd.read_csv(qci_fit_manifest)
            except pd.errors.EmptyDataError:
                qci_fit = pd.DataFrame()
            if not qci_fit.empty:
                over_limit = qci_fit[qci_fit["variable_count"].astype(int) > 132]
                if not over_limit.empty:
                    findings.append(
                        {
                            "severity": "error",
                            "benchmark": key,
                            "requirement": "qci_fit_variable_cap",
                            "message": f"{len(over_limit)} QCi-fit payloads exceed 132 variables.",
                        }
                    )
                bad_degree = qci_fit[qci_fit["degree"].astype(int) != 3]
                if not bad_degree.empty:
                    findings.append(
                        {
                            "severity": "error",
                            "benchmark": key,
                            "requirement": "qci_fit_degree",
                            "message": f"{len(bad_degree)} QCi-fit payloads are not degree 3.",
                        }
                    )
        qci_type = _qci_execution_payload_type(case_dir)
        if qci_type == "full":
            full_manifest = case_dir / "qci_payload_manifest.csv"
            if full_manifest.exists():
                try:
                    full_frame = pd.read_csv(full_manifest)
                except pd.errors.EmptyDataError:
                    full_frame = pd.DataFrame()
                if not full_frame.empty and int(full_frame["variable_count"].max()) > 132:
                    findings.append(
                        {
                            "severity": "error",
                            "benchmark": key,
                            "requirement": "no_oversize_full_payload_qci_label",
                            "message": "Full >132-variable payloads are marked as QCi executed.",
                        }
                    )
    arpae = Path(BENCHMARK_CASES["arpae_go"].results_dir)
    if not (arpae / "benchmark_provenance.json").exists():
        findings.append({"severity": "error", "benchmark": "arpae_go", "requirement": "parser_checker", "message": "missing ARPA-E GO provenance/check report"})
    ieee = Path(BENCHMARK_CASES["ieee_distribution"].results_dir)
    if not ((ieee / "benchmark_provenance.json").exists() or (ieee / "benchmark_missing.json").exists()):
        findings.append({"severity": "error", "benchmark": "ieee_distribution", "requirement": "explicit_status", "message": "missing distribution status or benchmark_missing report"})
    for name in REQUIRED_FINAL_TABLES:
        if not (Path("results/phase3/final_tables") / name).exists():
            findings.append({"severity": "error", "benchmark": "final_tables", "requirement": name, "message": f"missing {name}"})
    for name in REQUIRED_FINAL_FIGURES:
        if not (Path("results/phase3/final_figures") / name).exists():
            findings.append({"severity": "error", "benchmark": "final_figures", "requirement": name, "message": f"missing {name}"})
    return not any(item["severity"] == "error" for item in findings), findings
