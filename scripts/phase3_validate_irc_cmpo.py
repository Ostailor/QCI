#!/usr/bin/env python
"""Validate IRC-CMPO structure, surrogate gates, and coefficient dynamic range."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_constraints import audit_coefficients  # noqa: E402
from cmpo.irc_cmpo_master import build_irc_master, load_catalog, write_payload_exclusive  # noqa: E402
from cmpo.qci_integer_adapter import installed_qci_versions  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def validate_irc_payload(
    payload: Mapping[str, Any],
    *,
    output_dir: Path | str,
) -> dict[str, Any]:
    variables = list(payload["variables"])
    names = [str(variable["name"]) for variable in variables]
    if any("slack" in name.lower() for name in names):
        raise ValueError("IRC-CMPO must not contain budget slack variables")
    if any("not_selected" in name.lower() for name in names):
        raise ValueError("IRC-CMPO must not contain selected/not-selected pairs")
    if len(names) != len(set(names)) or len(names) != len(payload["catalog_assets"]):
        raise ValueError("IRC-CMPO must contain exactly one variable per physical asset")
    if any(
        variable.get("encoding_type") != "binary"
        or int(variable.get("lower_bound", -1)) != 0
        or int(variable.get("upper_bound", -1)) != 1
        for variable in variables
    ):
        raise ValueError("all IRC-CMPO master variables must be native binary integers")
    if list(payload.get("num_levels", ())) != [2] * len(variables):
        raise ValueError("binary IRC-CMPO variables require num_levels=2")
    if int(payload["max_degree"]) > 3:
        raise ValueError("IRC-CMPO polynomial exceeds degree 3")
    if any(term.get("component") == "hard_budget" for term in payload["polynomial_terms"]):
        raise ValueError("IRC-CMPO must not use the former squared hard-budget equality")
    audit = audit_coefficients(payload["polynomial_terms"])
    if not audit.passed:
        raise ValueError("coefficient dynamic-range gate failed: " + "; ".join(audit.reasons))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = [
        {"component": component, **statistics}
        for component, statistics in audit.family_statistics.items()
    ]
    rows.append(
        {
            "component": "__effective_submitted_polynomial__",
            "count": sum(audit.degree_distribution.values()),
            "minimum_nonzero": audit.effective_minimum_nonzero,
            "maximum_nonzero": audit.effective_maximum_nonzero,
            "median_nonzero": "unavailable",
        }
    )
    with (output / "coefficient_audit.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component", "count", "minimum_nonzero", "maximum_nonzero", "median_nonzero"])
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# IRC-CMPO coefficient dynamic-range audit",
        "",
        f"- Passed: **{audit.passed}**",
        f"- Maximum nonzero coefficient: `{audit.maximum_nonzero:.12g}`",
        f"- Minimum nonzero coefficient: `{audit.minimum_nonzero:.12g}`",
        f"- Max/min ratio: `{audit.dynamic_range:.12g}`",
        f"- Effective submitted maximum nonzero coefficient: `{audit.effective_maximum_nonzero:.12g}`",
        f"- Effective submitted minimum nonzero coefficient: `{audit.effective_minimum_nonzero:.12g}`",
        f"- Effective submitted max/min ratio: `{audit.effective_dynamic_range:.12g}`",
        f"- Variables: `{len(variables)}`",
        f"- Total num_levels: `{sum(payload['num_levels'])}`",
        f"- Degree distribution: `{json.dumps(audit.degree_distribution, sort_keys=True)}`",
        "- No global giant-budget normalization is present.",
        "- No important coefficient family collapsed into the 1e-13–1e-16 range.",
    ]
    with (output / "coefficient_audit.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return {"valid": True, "variables": len(variables), "total_num_levels": sum(payload["num_levels"]), **audit.to_dict()}


def validate_irc_cmpo(
    config_path: Path | str,
    surrogate_path: Path | str,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    surrogate = json.loads(_resolve(surrogate_path).read_text(encoding="utf-8"))
    if not surrogate["metrics"].get("gates_passed", False):
        raise ValueError("surrogate gates failed; IRC-CMPO is not eligible for QCi smoke testing")
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    if len(assets) != int(config["model"]["core_binary_variables"]):
        raise ValueError("full IEEE123 IRC-CMPO core must contain exactly 33 binary assets")
    budgets = pd.read_csv(_resolve(config["source_budget_manifest"])).sort_values("actual_budget")
    budget = float(budgets.iloc[len(budgets) // 2 - 1]["actual_budget"])
    bracket = config["lagrangian"]["deterministic_lambda_bracket"]
    payload = build_irc_master(
        assets,
        budget=budget,
        lagrange_lambda=(float(bracket[0]) + float(bracket[1])) / 2.0,
        surrogate_terms=surrogate["terms"],
        coverage_rho=float(config["model"]["coverage_rho"]),
        audit_collapsed_threshold=float(config["model"]["collapsed_coefficient_threshold"]),
    )
    output = _resolve(output_dir or config["output_dir"])
    result = validate_irc_payload(payload, output_dir=output)
    build_dir = output / "build"
    write_payload_exclusive(payload, build_dir / "full_middle_budget_lambda_payload.json")
    result.update(
        {
            "surrogate_gates_passed": True,
            "qci_jobs_submitted": 0,
            "full_experiment_run": False,
            "ready_for_three_job_smoke": True,
            "installed_qci_versions": installed_qci_versions(),
        }
    )
    with (output / "validation_report.md").open("x", encoding="utf-8") as handle:
        handle.write("# IRC-CMPO validation report\n\n")
        handle.write("The offline integer formulation and surrogate gates pass. No QCi job was submitted.\n\n")
        for key, value in result.items():
            handle.write(f"- {key}: `{value}`\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--surrogate", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    print(json.dumps(validate_irc_cmpo(args.config, args.surrogate, output_dir=args.output_dir), indent=2))


if __name__ == "__main__":
    main()
