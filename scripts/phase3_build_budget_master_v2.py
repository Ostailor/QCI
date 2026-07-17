#!/usr/bin/env python
"""Build six non-submitting IEEE123 global hard-budget master payloads."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_encoding import choose_currency_unit  # noqa: E402
from cmpo.global_upgrade_master import build_global_upgrade_master  # noqa: E402
from cmpo.upgrade_budget import (  # noqa: E402
    derive_ieee123_budget_sweep,
    load_ieee123_upgrade_catalog,
)


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml")


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _write_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_budget_master_v2(
    config_path: Path | str,
    *,
    output_dir: Path | str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    source_dir = _resolve(config["source_payload_dir"])
    output = _resolve(output_dir or config["output_dir"])
    targets = [
        output / "build_summary.json",
        output / "budget_master_manifest.csv",
        output / "model_stats.csv",
        output / "budget_encoding_report.csv",
        output / "budget_penalty_certificate.csv",
        output / "public_asset_catalog.csv",
        output / "recourse_manifest.csv",
    ]
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError(f"V2 build artifacts already exist under {output}; use --overwrite only for V2 regeneration")
    catalog = load_ieee123_upgrade_catalog(source_dir)
    if len(catalog) != 33 or len({asset.anchor_node for asset in catalog}) != 11:
        raise ValueError("V2 requires exactly 33 deduplicated assets at 11 physical anchors")
    budgets = derive_ieee123_budget_sweep(
        catalog,
        qci_metrics_path=_resolve(config["source_qci_metrics"]),
        baseline_metrics_path=_resolve(config["source_baseline_metrics"]),
    )
    if len(budgets) != 6:
        raise ValueError(f"V2 requires exactly six hard budgets, found {len(budgets)}")
    fixed_variables = (
        2 * len(catalog)
        + int(config["model"]["coverage_slack_variables_per_anchor"])
        * len({asset.anchor_node for asset in catalog})
        + int(config["model"]["policy_variable_count"])
    )
    currency = choose_currency_unit(
        [asset.total_cost for asset in catalog],
        [budget.amount for budget in budgets],
        fixed_variables=fixed_variables,
        max_variables=int(config["model"]["maximum_variables"]),
        minimum_normalized_violation_resolution=float(
            config["model"]["minimum_normalized_violation_resolution"]
        ),
        candidate_units=[float(value) for value in config["model"]["cost_unit_candidates_dollars"]],
        required_portfolio_costs=[
            [
                asset.total_cost
                for asset in catalog
                if asset.technology == "dispatchable_generation"
            ]
        ],
    )
    output.mkdir(parents=True, exist_ok=True)
    payload_dir = output / "qci_master_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    if not overwrite and any(payload_dir.glob("*.json")):
        raise FileExistsError(f"V2 master payloads already exist under {payload_dir}")

    manifest_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    encoding_rows: list[dict[str, Any]] = []
    certificate_rows: list[dict[str, Any]] = []
    recourse_rows: list[dict[str, Any]] = []
    for budget in budgets:
        built = build_global_upgrade_master(
            catalog,
            budget,
            currency_unit=currency.unit,
            safety_multiplier=float(config["model"]["budget_penalty_safety_multiplier"]),
            source_payload_dir=source_dir,
        )
        path = payload_dir / f"{budget.budget_id}.json"
        path.write_text(json.dumps(built.payload, indent=2, sort_keys=True), encoding="utf-8")
        stats = built.payload["model_statistics"]
        encoding = built.payload["budget_encoding"]
        certificate = built.payload["budget_penalty_certificate"]
        manifest_rows.append(
            {
                "budget_id": budget.budget_id,
                "actual_budget": budget.amount,
                "payload_path": str(path),
                "variable_count": stats["variable_count"],
                "maximum_degree": stats["degree"],
                "hard_budget_polynomial_term_count": sum(
                    term.get("component") == "hard_budget"
                    for term in built.payload["polynomial_terms"]
                ),
                "penalty_certificate_pass": certificate["passed"],
                "local_validation_pass": built.local_validation["passed"],
                "qci_submission_performed": False,
            }
        )
        stats_rows.append({"budget_id": budget.budget_id, **stats})
        encoding_rows.append(
            {
                "budget_id": budget.budget_id,
                "chosen_currency_unit": encoding["unit"],
                "actual_budget": encoding["actual_budget"],
                "encoded_budget": encoding["encoded_budget"],
                "slack_bit_count": encoding["slack_bit_count"],
                "maximum_per_asset_upward_rounding": encoding["maximum_per_asset_upward_rounding"],
                "maximum_portfolio_conservatism": encoding["maximum_portfolio_conservatism"],
                "rounding_guarantee": encoding["rounding_guarantee"],
                "unit_selection_rule": currency.selection_rule,
                "minimum_normalized_violation_resolution": (
                    currency.minimum_normalized_violation_resolution
                ),
                "worst_case_normalized_violation_proxy": (
                    currency.worst_case_normalized_violation_proxy
                ),
            }
        )
        certificate_rows.append(
            {
                "budget_id": budget.budget_id,
                **certificate,
            }
        )
        recourse_rows.append(
            {
                "budget_id": budget.budget_id,
                "portfolio_source": "top ten unique exact-budget-validated QCi master portfolios after approved run",
                "portfolio_count_limit": config["recourse"]["top_unique_portfolios_per_budget"],
                "patch_count": config["recourse"]["patch_count"],
                "training_scenario_count": config["recourse"]["training_scenario_count"],
                "heldout_n_1_count": config["recourse"]["heldout_n_1_count"],
                "consensus_algorithm": config["recourse"]["consensus_algorithm"],
                "projection": config["recourse"]["projection"],
                "ac_validation": config["recourse"]["ac_validation"],
                "portfolio_fixed_across_all_patches": True,
                "gpu_parallel_dimensions": ",".join(config["recourse"]["gpu_parallel_dimensions"]),
                "execution_status": "awaiting approved QCi master results",
            }
        )

    catalog_rows = [
        {
            **asset.__dict__,
            "source_payload_ids": json.dumps(list(asset.source_payload_ids)),
            "source_patch_ids": json.dumps(list(asset.source_patch_ids)),
            "deduplication_rule": config["model"]["physical_asset_deduplication"],
        }
        for asset in catalog
    ]
    _write_csv(manifest_rows, output / "budget_master_manifest.csv")
    _write_csv(stats_rows, output / "model_stats.csv")
    _write_csv(encoding_rows, output / "budget_encoding_report.csv")
    _write_csv(certificate_rows, output / "budget_penalty_certificate.csv")
    _write_csv(catalog_rows, output / "public_asset_catalog.csv")
    _write_csv(recourse_rows, output / "recourse_manifest.csv")
    summary = {
        "schema": "cmpo.budget_master.v2.build",
        "strict_stop_v1_audit_required": True,
        "master_payload_count": len(manifest_rows),
        "public_asset_count": len(catalog),
        "physical_anchor_count": len({asset.anchor_node for asset in catalog}),
        "selected_currency_unit": currency.unit,
        "maximum_cost_rounding_conservatism": max(
            row["maximum_portfolio_conservatism"] for row in encoding_rows
        ),
        "qci_submission_performed": False,
        "qci_upload_performed": False,
        "output_dir": str(output),
    }
    (output / "build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = build_budget_master_v2(
        args.config,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
