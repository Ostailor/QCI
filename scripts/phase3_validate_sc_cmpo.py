#!/usr/bin/env python
"""Validate SC-CMPO public provenance, scenario coupling, and QCi fit constraints."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_client_adapter import convert_cmpo_payload_to_qci_file  # noqa: E402
from cmpo.upgrade_planning import sha256_file  # noqa: E402


REQUIRED_MANIFESTS = (
    "payload_manifest.csv",
    "model_stats.csv",
    "upgrade_options.csv",
    "scenario_coupling_manifest.csv",
    "provenance_manifest.csv",
)
REQUIRED_STAGES = {"upgrade_planning", "pre_event_preparedness", "emergency_response", "restoration"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that SC-CMPO uses documented public inputs, shares first-stage decisions across at least "
            "six scenarios, and keeps every normalized degree-3 payload within 132 variables."
        )
    )
    parser.add_argument(
        "--result-dir",
        default="results/phase3/sc_cmpo",
        help="SC-CMPO artifact directory to validate.",
    )
    parser.add_argument("--max-variables", type=int, default=132, help="Maximum permitted Dirac-3 variable count.")
    parser.add_argument("--max-degree", type=int, default=3, help="Maximum permitted polynomial degree.")
    parser.add_argument("--dry-run", action="store_true", help="Run read-only validation without writing reports.")
    return parser


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})


def _payload_checks(path: Path, max_variables: int, max_degree: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    payload = json.loads(path.read_text(encoding="utf-8"))
    sc = payload.get("sc_cmpo", {})
    stats = payload.get("model_statistics", {})
    variables = payload.get("variables", [])
    terms = payload.get("polynomial_terms", [])
    scenarios = payload.get("scenario_metadata", {}).get("scenarios", [])
    names = [str(variable.get("name", "")) for variable in variables]
    term_degree = max((sum(int(power) for power in term.get("powers", {}).values()) for term in terms), default=0)
    finite_coefficients = all(math.isfinite(float(term.get("coefficient", math.nan))) for term in terms)
    max_coefficient = max((abs(float(term["coefficient"])) for term in terms), default=0.0)
    bounded = all(
        math.isfinite(float(variable.get("lower_bound", math.nan)))
        and math.isfinite(float(variable.get("upper_bound", math.nan)))
        and float(variable["lower_bound"]) == 0.0
        and float(variable["upper_bound"]) == 1.0
        for variable in variables
    )
    scenario_names = [str(scenario.get("name", "")) for scenario in scenarios]
    shared = list(sc.get("shared_first_stage_variables", []))
    recourse_groups = list(sc.get("recourse_variable_groups", []))
    expected_variable_count = len(shared) + len(recourse_groups) * len(scenarios)
    input_policy = sc.get("input_policy", {})
    options = {option.get("technology"): option for option in sc.get("upgrade_options", [])}
    robust_island = any(
        not bool(scenario.get("pcc_available"))
        and not bool(scenario.get("pv_available"))
        and not bool(scenario.get("existing_generation_available"))
        for scenario in scenarios
    )
    nonzero_upgrade_structural = (
        float(sc.get("upgrade_patch", {}).get("islanded_deficit_kw", 0.0)) > 0.0
        and float(sc.get("minimum_resilient_upgrade_cost", 0.0)) > 0.0
        and robust_island
        and float(options.get("bess", {}).get("power_kw", 0.0)) > 0.0
        and float(options.get("dispatchable_generation", {}).get("capacity_kw", 0.0)) > 0.0
    )
    qci_file = convert_cmpo_payload_to_qci_file(payload)
    qci_polynomial = qci_file["file_config"]["polynomial"]
    _check(checks, "schema", payload.get("schema") == "cmpo.sc_cmpo.v1", str(payload.get("schema")))
    _check(checks, "variable_count", len(variables) == int(stats.get("variable_count", -1)) <= max_variables, f"{len(variables)} <= {max_variables}")
    _check(checks, "variable_count_contract", len(variables) == expected_variable_count, f"actual={len(variables)} expected={expected_variable_count}")
    _check(checks, "unique_variable_names", len(names) == len(set(names)), f"unique={len(set(names))} total={len(names)}")
    _check(checks, "bounded_variables", bounded, "all variables must have exact [0,1] bounds")
    _check(checks, "degree", term_degree == int(stats.get("degree", -1)) == max_degree, f"degree={term_degree}")
    _check(checks, "finite_coefficients", finite_coefficients, f"term_count={len(terms)}")
    _check(checks, "normalized_coefficients", max_coefficient <= 1.0 + 1e-12, f"max_abs={max_coefficient:.12g}")
    _check(
        checks,
        "qci_export_contract",
        int(qci_polynomial["num_variables"]) == len(variables)
        and int(qci_polynomial["max_degree"]) == term_degree,
        f"num_variables={qci_polynomial['num_variables']}; max_degree={qci_polynomial['max_degree']}",
    )
    _check(checks, "scenario_count", 6 <= len(scenarios) <= 10, f"scenario_count={len(scenarios)}")
    _check(checks, "unique_scenarios", len(scenario_names) == len(set(scenario_names)), ",".join(scenario_names))
    _check(checks, "shared_first_stage", len(shared) > 0 and all(name in names for name in shared), f"count={len(shared)}")
    _check(checks, "challenge_stages", set(sc.get("challenge_stages", [])) == REQUIRED_STAGES, ",".join(sc.get("challenge_stages", [])))
    _check(checks, "public_inputs_only", input_policy.get("public_inputs_only") is True, str(input_policy))
    _check(checks, "no_random_grid_values", input_policy.get("random_topology_or_asset_values") is False, str(input_policy))
    _check(checks, "no_undocumented_synthetic_values", input_policy.get("undocumented_synthetic_values") == [], str(input_policy.get("undocumented_synthetic_values")))
    _check(checks, "nonzero_upgrade_structural", nonzero_upgrade_structural, f"robust_island={robust_island}; min_cost={sc.get('minimum_resilient_upgrade_cost')}")
    _check(checks, "qci_not_mislabeled", sc.get("qci_executed", False) is False and "not submitted" in str(payload.get("phase2_notice", "")).lower(), str(payload.get("phase2_notice", "")))
    _check(checks, "source_provenance", all(str(sc.get(key, "")) for key in ("source_url", "source_version", "source_sha256", "source_transformation")), str(sc.get("source_url", "")))
    summary = {
        "payload_name": path.name,
        "benchmark": sc.get("public_benchmark"),
        "benchmark_family": sc.get("public_benchmark_family"),
        "scenario_count": len(scenarios),
        "variable_count": len(variables),
        "degree": term_degree,
        "shared_first_stage_variable_count": len(shared),
        "recourse_variable_count": len(recourse_groups) * len(scenarios),
        "minimum_resilient_upgrade_cost": float(sc.get("minimum_resilient_upgrade_cost", 0.0)),
        "maximum_upgrade_cost": float(sc.get("maximum_upgrade_cost", 0.0)),
        "nonzero_upgrade_structural": nonzero_upgrade_structural,
    }
    return checks, summary


def validate(result_dir: Path, *, max_variables: int, max_degree: int, dry_run: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    missing = [str(result_dir / name) for name in REQUIRED_MANIFESTS if not (result_dir / name).exists()]
    payload_dir = result_dir / "qci_payloads"
    if not payload_dir.is_dir():
        missing.append(str(payload_dir))
    if missing:
        result = {"ready": False, "missing_artifacts": missing, "checks": checks}
        if not dry_run:
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / "validation_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    manifest_rows = _read_csv(result_dir / "payload_manifest.csv")
    payload_paths = [Path(row["payload_path"]) for row in manifest_rows]
    _check(checks, "payload_manifest_nonempty", bool(payload_paths), f"payload_count={len(payload_paths)}")
    _check(checks, "all_payload_files_exist", all(path.exists() for path in payload_paths), ", ".join(str(path) for path in payload_paths if not path.exists()) or "all present")
    payload_summaries: list[dict[str, Any]] = []
    per_payload_checks: dict[str, list[dict[str, Any]]] = {}
    for path in payload_paths:
        if not path.exists():
            continue
        local_checks, summary = _payload_checks(path, max_variables, max_degree)
        per_payload_checks[path.name] = local_checks
        payload_summaries.append(summary)
        for item in local_checks:
            _check(checks, f"{path.name}:{item['check']}", bool(item["passed"]), str(item["detail"]))

    families = {str(row["benchmark_family"]) for row in manifest_rows}
    _check(checks, "at_least_three_public_families", len(families) >= 3, ",".join(sorted(families)))
    _check(checks, "manifest_qci_not_executed", all(str(row.get("qci_executed", "")).lower() == "false" for row in manifest_rows), "all rows must remain build-only")
    _check(checks, "positive_upgrade_case", any(row["nonzero_upgrade_structural"] for row in payload_summaries), "at least one robust island requires a nonzero upgrade")

    provenance_rows = _read_csv(result_dir / "provenance_manifest.csv")
    required_provenance = {"source_url", "version", "license", "sha256", "local_path", "local_sha256", "transformation"}
    provenance_complete = bool(provenance_rows) and all(
        all(str(row.get(field, "")).strip() for field in required_provenance) for row in provenance_rows
    )
    _check(checks, "provenance_complete", provenance_complete, f"rows={len(provenance_rows)}")
    local_checksums_match = True
    source_checksums_valid = True
    for row in provenance_rows:
        local_path = Path(row["local_path"])
        local_checksums_match = local_checksums_match and local_path.exists()
        if local_path.exists():
            local_checksums_match = local_checksums_match and sha256_file(local_path) == row["local_sha256"]
        source_checksums_valid = source_checksums_valid and len(row["sha256"]) == 64
        source_checksums_valid = source_checksums_valid and all(character in "0123456789abcdef" for character in row["sha256"].lower())
    _check(checks, "local_provenance_checksums", local_checksums_match, "every local provenance file matches its recorded checksum")
    _check(checks, "source_checksums_recorded", source_checksums_valid, "every upstream source checksum is a SHA-256 digest")

    baseline_path = result_dir / "baselines" / "robust_lp" / "payload_summary.csv"
    baseline_nonzero = False
    if baseline_path.exists():
        baseline_rows = _read_csv(baseline_path)
        baseline_nonzero = any(
            float(row.get("upgrade_cost", 0.0)) > 0.0
            and (
                float(row.get("pv_capacity_fraction", 0.0))
                + float(row.get("bess_energy_fraction", row.get("bess_capacity_fraction", 0.0)))
                + float(row.get("dispatchable_capacity_fraction", 0.0))
                > 0.0
            )
            for row in baseline_rows
        )
    _check(
        checks,
        "nonzero_stage1_decision_evidence",
        baseline_nonzero or any(row["nonzero_upgrade_structural"] for row in payload_summaries),
        f"robust_lp_present={baseline_path.exists()}; robust_lp_nonzero={baseline_nonzero}",
    )

    ready = all(bool(item["passed"]) for item in checks)
    counts = Counter(str(row["benchmark"]) for row in payload_summaries)
    result = {
        "ready": ready,
        "payload_count": len(payload_summaries),
        "payload_count_by_benchmark": dict(sorted(counts.items())),
        "benchmark_family_count": len(families),
        "max_variables": max((int(row["variable_count"]) for row in payload_summaries), default=0),
        "max_degree": max((int(row["degree"]) for row in payload_summaries), default=0),
        "minimum_upgrade_cost": min((float(row["minimum_resilient_upgrade_cost"]) for row in payload_summaries), default=0.0),
        "maximum_upgrade_cost": max((float(row["maximum_upgrade_cost"]) for row in payload_summaries), default=0.0),
        "checks": checks,
        "payloads": payload_summaries,
        "per_payload_checks": per_payload_checks,
        "qci_was_run": False,
    }
    if not dry_run:
        report_json = result_dir / "validation_report.json"
        report_md = result_dir / "validation_report.md"
        report_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
        lines = [
            "# SC-CMPO Validation",
            "",
            f"Overall: **{'PASS' if ready else 'FAIL'}**",
            "",
            "| Check | Result | Detail |",
            "|---|---:|---|",
        ]
        lines.extend(
            f"| {item['check']} | {'PASS' if item['passed'] else 'FAIL'} | {str(item['detail']).replace('|', '/')} |"
            for item in checks
        )
        report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result["validation_report_json"] = str(report_json)
        result["validation_report_md"] = str(report_md)
    return result


def main() -> None:
    args = build_parser().parse_args()
    result = validate(
        Path(args.result_dir),
        max_variables=args.max_variables,
        max_degree=args.max_degree,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"checks", "payloads", "per_payload_checks"}
            }
            | {
                "check_count": len(result.get("checks", [])),
                "failed_check_count": sum(not bool(item["passed"]) for item in result.get("checks", [])),
            },
            indent=2,
        )
    )
    if not result["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
