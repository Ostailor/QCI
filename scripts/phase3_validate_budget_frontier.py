#!/usr/bin/env python
"""Validate matched budgets, provenance, traces, and acceptance gates for IEEE123."""

from __future__ import annotations

import argparse
import hashlib
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

from cmpo.budget_frontier import validate_matched_budget_results  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_sweep.yaml")
GATES = (
    "equal_budget_method_coverage",
    "no_over_budget_rows",
    "identical_patch_scenario_consensus_projection_heldout",
    "csv_and_system_trace_for_every_point",
    "matched_cost_claim_reported",
    "existing_sc_cmpo_artifacts_untouched",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_budget_frontier(
    config_path: Path | str,
    output_dir: Path | str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir)
    plan = {"output_dir": str(output), "acceptance_gates": list(GATES)}
    if dry_run:
        return {"dry_run": True, **plan}
    required = [
        "table_budget_matched_results.csv",
        "table_heldout_budget_results.csv",
        "table_budget_win_tie_loss.csv",
        "pareto_frontier.csv",
        "upgrade_cost_vs_total_ens.png",
        "upgrade_cost_vs_critical_ens.png",
        "upgrade_cost_vs_max_unserved.png",
        "heldout_upgrade_cost_vs_ens.png",
        "budget_frontier_summary.json",
        "budget_frontier_report.md",
        "budget_manifest.csv",
        "qci_job_status.csv",
    ]
    missing = [name for name in required if not (output / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing budget-frontier artifacts: {missing}")
    methods = {str(item) for item in config["methods"]}
    system = pd.read_csv(output / "table_budget_matched_results.csv")
    heldout = pd.read_csv(output / "table_heldout_budget_results.csv")
    validate_matched_budget_results(system, expected_methods=methods)
    validate_matched_budget_results(heldout, expected_methods=methods)

    checks: dict[str, Any] = {}
    budget_count = int(system["budget"].nunique())
    checks["equal_budget_method_coverage"] = len(system) == budget_count * len(methods)
    checks["no_over_budget_rows"] = bool(
        (pd.to_numeric(system["total_upgrade_cost"]) <= pd.to_numeric(system["budget"]) + 1e-6).all()
        and (pd.to_numeric(heldout["total_upgrade_cost"]) <= pd.to_numeric(heldout["budget"]) + 1e-6).all()
    )
    consistency = (
        set(pd.to_numeric(system["patch_count"])) == {12}
        and set(pd.to_numeric(system["training_scenario_count"])) == {8}
        and system["consensus_algorithm"].nunique() == 1
        and system["projection"].nunique() == 1
        and set(pd.to_numeric(heldout["heldout_count"])) == {10}
        and system["physical_asset_deduplication"].astype(str).str.lower().isin({"true", "1"}).all()
    )
    checks["identical_patch_scenario_consensus_projection_heldout"] = bool(consistency)

    trace_ok = True
    for row in system.to_dict("records"):
        trace_path = _resolve(str(row["trace_path"]))
        if not trace_path.exists():
            trace_ok = False
            break
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        hard = trace.get("hard_budget_check", {})
        trace_ok = trace_ok and bool(hard.get("passed"))
        trace_ok = trace_ok and float(hard.get("charged_cost", float("inf"))) <= float(hard.get("budget", 0.0)) + 1e-6
        trace_ok = trace_ok and trace.get("system", {}).get("system_metrics", {}).get("system_trace_id") == row["system_trace_id"]
    checks["csv_and_system_trace_for_every_point"] = bool(trace_ok)

    summary = json.loads((output / "budget_frontier_summary.json").read_text(encoding="utf-8"))
    report = (output / "budget_frontier_report.md").read_text(encoding="utf-8")
    claim = str(summary.get("strongest_supported_claim", "")).strip()
    checks["matched_cost_claim_reported"] = bool(claim and claim in report and "identical hard upgrade budgets" in claim)

    manifest = pd.read_csv(output / "budget_manifest.csv")
    untouched = True
    output_resolved = output.resolve()
    for row in manifest.to_dict("records"):
        source = _resolve(str(row["source_payload"]))
        budgeted = _resolve(str(row["budgeted_payload"]))
        untouched = untouched and source.resolve() != budgeted.resolve()
        untouched = untouched and output_resolved in budgeted.resolve().parents
        untouched = untouched and output_resolved not in source.resolve().parents
        untouched = untouched and _sha256(source) == str(row["source_payload_sha256"])
    checks["existing_sc_cmpo_artifacts_untouched"] = bool(untouched)

    jobs = pd.read_csv(output / "qci_job_status.csv")
    qci_raw_ok = True
    for row in jobs.to_dict("records"):
        if str(row["status"]).upper() == "COMPLETED":
            qci_raw_ok = qci_raw_ok and int(row["sample_count"]) == 30
            qci_raw_ok = qci_raw_ok and _resolve(str(row["request_json"])).exists()
            qci_raw_ok = qci_raw_ok and _resolve(str(row["response_json"])).exists()
    checks["qci_raw_requests_responses_and_30_samples"] = bool(qci_raw_ok)
    checks["all_required_figures_nonempty"] = all((output / name).stat().st_size > 0 for name in required if name.endswith(".png"))
    valid = all(checks.values())
    result = {**plan, "valid": valid, "budget_count": budget_count, "method_count": len(methods), "checks": checks}
    (output / "validation_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "validation_report.md").write_text(
        "# IEEE123 Budget Frontier Validation\n\n"
        + "\n".join(f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items())
        + f"\n\nOverall valid: **{valid}**\n",
        encoding="utf-8",
    )
    if not valid:
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"budget-frontier validation failed: {failed}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default="results/phase3/sc_cmpo/budget_frontier")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = validate_budget_frontier(args.config, args.output_dir, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
