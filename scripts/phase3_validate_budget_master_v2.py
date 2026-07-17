#!/usr/bin/env python
"""Validate all non-submission gates for IEEE123 global budget masters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_encoding import validate_budget_payload  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml")
CHECK_NAMES = (
    "exactly_six_global_master_payloads",
    "budget_encoded_in_polynomial_terms",
    "no_metadata_only_budget",
    "qci_variable_limit",
    "qci_degree_limit",
    "low_energy_local_portfolios_real_budget_feasible",
    "conservative_rounding_prevents_real_overrun",
    "upgrade_one_hot_constraints_encoded",
    "physical_assets_deduplicated_before_costing",
    "same_portfolio_fixed_across_twelve_patch_recourse",
    "upgrade_cost_charged_once_per_physical_system",
    "penalty_dominance_certificate_passes",
    "public_checksums_and_cost_provenance_preserved",
    "no_v1_posthoc_rows_in_v2_outputs",
    "no_qci_submission_during_build_or_validation",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def validate_budget_master_v2(
    config_path: Path | str,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or config["output_dir"])
    payload_paths = sorted((output / "qci_master_payloads").glob("*.json"))
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in payload_paths]
    manifest = pd.read_csv(output / "budget_master_manifest.csv")
    catalog = pd.read_csv(output / "public_asset_catalog.csv")
    recourse = pd.read_csv(output / "recourse_manifest.csv")
    encoding_report = pd.read_csv(output / "budget_encoding_report.csv")
    certificate_report = pd.read_csv(output / "budget_penalty_certificate.csv")
    summary = json.loads((output / "build_summary.json").read_text(encoding="utf-8"))

    validations = [validate_budget_payload(payload) for payload in payloads]
    checks: dict[str, bool] = {}
    checks[CHECK_NAMES[0]] = len(payloads) == 6 and len(manifest) == 6
    checks[CHECK_NAMES[1]] = bool(payloads) and all(
        validation.budget_present_in_polynomial and validation.budget_polynomial_term_count > 0
        for validation in validations
    )
    checks[CHECK_NAMES[2]] = bool(payloads) and all(validation.passed for validation in validations)
    checks[CHECK_NAMES[3]] = bool(payloads) and all(
        len(payload["variables"]) <= int(config["model"]["maximum_variables"])
        for payload in payloads
    )
    checks[CHECK_NAMES[4]] = bool(payloads) and all(
        int(payload["max_degree"]) <= int(config["model"]["maximum_degree"])
        for payload in payloads
    )
    checks[CHECK_NAMES[5]] = bool(payloads) and all(
        bool(payload.get("local_validation", {}).get("passed"))
        and float(payload["local_validation"]["actual_cost"])
        <= float(payload["budget_constraint"]["amount"]) + 1e-9
        and len(
            {
                str(asset["anchor_node"])
                for asset in payload["catalog_assets"]
                if str(asset["asset_key"])
                in set(payload["local_validation"]["selected_asset_keys"])
            }
        )
        == int(payload["provenance"]["physical_anchor_count"])
        for payload in payloads
    )
    checks[CHECK_NAMES[6]] = bool(payloads) and all(
        float(row["maximum_per_asset_upward_rounding"]) < float(row["unit"]) + 1e-12
        and float(payload["budget_penalty_certificate"]["normalized_minimum_violation_penalty"])
        >= float(config["model"]["minimum_normalized_violation_resolution"])
        and int(row["encoded_budget"])
        * float(row["unit"])
        <= float(row["actual_budget"]) + 1e-9
        and (int(row["encoded_budget"]) + 1) * float(row["unit"])
        > float(row["actual_budget"]) - 1e-9
        and all(
            int(row["encoded_costs"][asset["asset_key"]]) * float(row["unit"])
            >= float(asset["total_cost"]) - 1e-9
            and (int(row["encoded_costs"][asset["asset_key"]]) - 1)
            * float(row["unit"])
            < float(asset["total_cost"]) + 1e-9
            for asset in payload["catalog_assets"]
        )
        for payload in payloads
        for row in [payload["budget_encoding"]]
    )
    checks[CHECK_NAMES[7]] = bool(payloads) and all(
        len(payload["one_hot_groups"]) == len(payload["catalog_assets"])
        and all(len(group["variables"]) == 2 for group in payload["one_hot_groups"])
        and any(term.get("component") == "upgrade_one_hot" for term in payload["polynomial_terms"])
        and len(payload["anchor_coverage_constraints"]) == 11
        and any(term.get("component") == "anchor_coverage" for term in payload["polynomial_terms"])
        for payload in payloads
    )
    checks[CHECK_NAMES[8]] = (
        len(catalog) == 33
        and catalog["asset_key"].nunique() == 33
        and catalog["anchor_node"].astype(str).nunique() == 11
    )
    checks[CHECK_NAMES[9]] = (
        len(recourse) == 6
        and set(recourse["patch_count"].astype(int)) == {12}
        and recourse["portfolio_fixed_across_all_patches"].astype(bool).all()
    )
    checks[CHECK_NAMES[10]] = bool(payloads) and all(
        len({asset["asset_key"] for asset in payload["catalog_assets"]})
        == len(payload["catalog_assets"])
        for payload in payloads
    )
    checks[CHECK_NAMES[11]] = bool(payloads) and all(
        bool(payload["budget_penalty_certificate"]["passed"])
        and float(payload["budget_penalty_certificate"]["minimum_violation_penalty"])
        > float(payload["budget_penalty_certificate"]["maximum_nonbudget_objective_variation"])
        for payload in payloads
    )
    checks[CHECK_NAMES[12]] = bool(payloads) and all(
        len(payload["provenance"]["source_payload_checksums"]) == 12
        and all(
            row["sha256"] != "unavailable"
            for row in payload["provenance"]["source_payload_checksums"]
        )
        and len(payload["provenance"]["cost_sources"]) > 0
        for payload in payloads
    )
    v1_source = "final_public_experiment/system_level/qci_repeat_system_metrics.csv"
    checks[CHECK_NAMES[13]] = all(
        v1_source not in path.read_text(encoding="utf-8")
        and "posthoc_existing_sample_budget_filter" not in path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file() and path.suffix in {".json", ".csv", ".md"}
    )
    checks[CHECK_NAMES[14]] = (
        summary.get("qci_submission_performed") is False
        and summary.get("qci_upload_performed") is False
        and all(
            payload["execution_provenance"].get("qci_submission_performed") is False
            and payload["execution_provenance"].get("qci_job_id") is None
            and payload["execution_provenance"].get("qci_file_id") is None
            for payload in payloads
        )
        and not (output / "actual_qci").exists()
    )
    checks = {name: bool(passed) for name, passed in checks.items()}
    if tuple(checks) != CHECK_NAMES:
        raise AssertionError("V2 validation gate order changed")
    valid = all(checks.values())
    command = (
        "python scripts/phase3_run_qci.py "
        "--config configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml "
        "--payload-dir results/phase3/sc_cmpo/budget_master_v2/qci_master_payloads "
        "--output-dir results/phase3/sc_cmpo/budget_master_v2/actual_qci "
        "--repeats 30"
    )
    v1_manifest_path = (
        _resolve(config["source_budget_frontier"])
        / "failed_v1_audit"
        / "payload_validation_manifest.csv"
    )
    if v1_manifest_path.is_file():
        v1_manifest = pd.read_csv(v1_manifest_path)
        v1_checked = len(v1_manifest)
        v1_failed = int(
            (~v1_manifest["validation_pass"].astype(str).str.lower().isin({"true", "1"})).sum()
        )
    else:
        v1_checked = 0
        v1_failed = 0
    payload_by_budget = {
        str(payload["budget_constraint"]["budget_id"]): payload for payload in payloads
    }
    result = {
        "valid": valid,
        "checks": checks,
        "strict_stop_v1_audit_status": (
            "FAILED_AS_EXPECTED_NO_SUBMISSION"
            if v1_checked == 72 and v1_failed == 72
            else "INCOMPLETE"
        ),
        "v1_payloads_checked": v1_checked,
        "v1_payloads_failed": v1_failed,
        "master_payload_count": len(payloads),
        "variable_count_by_budget": dict(
            zip(
                manifest["budget_id"].astype(str).tolist(),
                manifest["variable_count"].astype(int).tolist(),
                strict=True,
            )
        ),
        "degree_by_budget": dict(
            zip(
                manifest["budget_id"].astype(str).tolist(),
                manifest["maximum_degree"].astype(int).tolist(),
                strict=True,
            )
        ),
        "selected_cost_unit": float(encoding_report["chosen_currency_unit"].iloc[0]),
        "slack_bit_count_by_budget": dict(
            zip(
                encoding_report["budget_id"].astype(str).tolist(),
                encoding_report["slack_bit_count"].astype(int).tolist(),
                strict=True,
            )
        ),
        "maximum_cost_rounding_conservatism": float(
            encoding_report["maximum_portfolio_conservatism"].max()
        ),
        "rho_budget_by_budget": dict(
            zip(
                certificate_report["budget_id"].astype(str).tolist(),
                certificate_report["rho_budget"].astype(float).tolist(),
                strict=True,
            )
        ),
        "penalty_certificate_status_by_budget": dict(
            zip(
                certificate_report["budget_id"].astype(str).tolist(),
                certificate_report["passed"].astype(bool).tolist(),
                strict=True,
            )
        ),
        "exact_local_validation_results": {
            budget_id: payload["local_validation"]
            for budget_id, payload in sorted(payload_by_budget.items())
        },
        "qci_submission_performed": False,
        "exact_qci_commands_after_approval": [
            "python scripts/phase3_validate_budget_master_v2.py",
            command,
        ],
        "BUDGET_MASTER_V2_READY_FOR_QCI": "YES" if valid else "NO",
    }
    lines = [
        "# IEEE123 Global Budget Master V2 Validation",
        "",
        *(f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items()),
        "",
        f"Overall valid: **{valid}**",
        "",
        f"Strict-stop V1 audit: **{result['strict_stop_v1_audit_status']}** "
        f"({v1_failed}/{v1_checked} payloads failed as required).",
        "",
        f"Selected cost unit: **${result['selected_cost_unit']:.2f}**; maximum full-catalog rounding "
        f"conservatism: **${result['maximum_cost_rounding_conservatism']:.6f}**.",
        "",
        "No QCi upload or job submission was performed.",
        "",
        "## Exact commands after approval",
        "",
        "```bash",
        *result["exact_qci_commands_after_approval"],
        "```",
        "",
        f"`BUDGET_MASTER_V2_READY_FOR_QCI: {result['BUDGET_MASTER_V2_READY_FOR_QCI']}`",
        "",
    ]
    (output / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "validation_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not valid:
        raise ValueError(f"V2 validation failed: {[name for name, passed in checks.items() if not passed]}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    result = validate_budget_master_v2(args.config, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
