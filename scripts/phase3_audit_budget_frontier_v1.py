#!/usr/bin/env python
"""Create the immutable strict-stop audit for the metadata-only V1 budget sweep."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_encoding import validate_budget_payload  # noqa: E402


DISCLAIMER = (
    "The existing budget rows select previously generated QCi solutions whose reconstructed portfolios fit each "
    "budget. The budget was not encoded in the submitted Hamiltonian; these rows are therefore a post-hoc sample "
    "filter and not a budget-constrained hardware experiment."
)
ANALYSIS_TYPE = "posthoc_existing_sample_budget_filter"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(rows: list[dict[str, Any]], path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _posthoc_copy(source: Path, target: Path) -> pd.DataFrame:
    frame = pd.read_csv(source)
    frame["analysis_type"] = ANALYSIS_TYPE
    if "method_solution_source" in frame:
        frame["method_solution_source"] = ANALYSIS_TYPE
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return frame


def audit_budget_frontier_v1(
    budget_frontier: Path | str,
    *,
    output_root: Path | str | None = None,
) -> dict[str, Any]:
    frontier = Path(budget_frontier)
    root = Path(output_root) if output_root is not None else frontier
    posthoc_dir = root / "posthoc_filter"
    audit_dir = root / "failed_v1_audit"
    source_results = frontier / "qci_budgeted_results.csv"
    source_heldout = frontier / "qci_budgeted_heldout_results.csv"
    results = _posthoc_copy(source_results, posthoc_dir / "posthoc_qci_budgeted_results.csv")
    heldout = _posthoc_copy(
        source_heldout,
        posthoc_dir / "posthoc_qci_budgeted_heldout_results.csv",
    )

    trace_rows: list[dict[str, Any]] = []
    for source, frame, kind in (
        (source_results, results, "training"),
        (source_heldout, heldout, "heldout"),
    ):
        source_hash = _sha256(source)
        for row_number, row in enumerate(frame.to_dict("records"), start=2):
            trace_path = Path(str(row.get("trace_path", "")))
            if not trace_path.is_absolute():
                trace_path = ROOT / trace_path
            trace_rows.append(
                {
                    "analysis_type": ANALYSIS_TYPE,
                    "result_kind": kind,
                    "budget_id": row.get("budget_id", ""),
                    "system_trace_id": row.get("system_trace_id", ""),
                    "source_result_csv": str(source),
                    "source_result_sha256": source_hash,
                    "source_row_number": row_number,
                    "trace_path": str(trace_path),
                    "trace_sha256": _sha256(trace_path) if trace_path.is_file() else "unavailable",
                }
            )
    _write_csv(
        trace_rows,
        posthoc_dir / "posthoc_trace_manifest.csv",
        [
            "analysis_type",
            "result_kind",
            "budget_id",
            "system_trace_id",
            "source_result_csv",
            "source_result_sha256",
            "source_row_number",
            "trace_path",
            "trace_sha256",
        ],
    )
    (posthoc_dir / "posthoc_budget_frontier_report.md").write_text(
        "# IEEE123 Post-hoc Budget Filter\n\n"
        f"Analysis label: `{ANALYSIS_TYPE}`\n\n"
        f"{DISCLAIMER}\n\n"
        "All numerical values are copied from the existing V1 QCi budget rows. Only provenance labels were added.\n",
        encoding="utf-8",
    )

    manifest_rows: list[dict[str, Any]] = []
    for path in sorted((frontier / "payloads").glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        budget = payload.get("budget_constraint", {})
        validation = validate_budget_payload(payload)
        terms = list(payload.get("polynomial_terms", ()))
        maximum_degree = max(
            (int(term.get("degree", sum(term.get("powers", {}).values()))) for term in terms),
            default=0,
        )
        coefficients_finite = all(math.isfinite(float(term.get("coefficient", math.nan))) for term in terms)
        reason = validation.failure_reason
        if not coefficients_finite:
            reason = f"{reason}; non-finite polynomial coefficient".strip("; ")
        manifest_rows.append(
            {
                "budget_id": path.parent.name,
                "budget_amount": budget.get("amount", ""),
                "payload_path": str(path),
                "source_payload_path": payload.get("source_payload", ""),
                "variable_count": len(payload.get("variables", ())),
                "maximum_degree": maximum_degree,
                "budget_present_in_metadata": validation.budget_present_in_metadata,
                "budget_present_in_polynomial": validation.budget_present_in_polynomial,
                "budget_polynomial_term_count": validation.budget_polynomial_term_count,
                "validation_pass": validation.passed,
                "failure_reason": reason,
            }
        )
    fields = [
        "budget_id",
        "budget_amount",
        "payload_path",
        "source_payload_path",
        "variable_count",
        "maximum_degree",
        "budget_present_in_metadata",
        "budget_present_in_polynomial",
        "budget_polynomial_term_count",
        "validation_pass",
        "failure_reason",
    ]
    _write_csv(manifest_rows, audit_dir / "payload_validation_manifest.csv", fields)
    passed = sum(bool(row["validation_pass"]) for row in manifest_rows)
    failed = len(manifest_rows) - passed
    (audit_dir / "validation_report.md").write_text(
        "# V1 Budget Payload Validation\n\n"
        f"- Payloads checked: {len(manifest_rows)}\n"
        f"- Payloads passed: {passed}\n"
        f"- Payloads failed: {failed}\n"
        "- QCi upload attempted: no\n"
        "- QCi job submitted: no\n\n"
        "**STRICT-STOP: FAILED.** Every V1 payload stores the budget in metadata but contains no hard-budget "
        "Hamiltonian component. Submission is refused before QCi environment or client initialization.\n",
        encoding="utf-8",
    )
    (audit_dir / "root_cause.md").write_text(
        "# V1 Root Cause\n\n"
        "The V1 builder copied each patch Hamiltonian and added a `budget_constraint` metadata object. It did not "
        "add variables or polynomial terms for the budget. Reconstruction later filtered portfolios by cost, which "
        "is valid as a post-hoc analysis but is not a budget-constrained hardware experiment. Encoding the full-system "
        "budget independently in twelve patch Hamiltonians would also be invalid because each patch could spend the "
        "entire system budget. V2 therefore uses one deduplicated global upgrade master per budget.\n",
        encoding="utf-8",
    )
    return {
        "strict_stop": True,
        "payloads_checked": len(manifest_rows),
        "payloads_passed": passed,
        "payloads_failed": failed,
        "qci_submission_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--budget-frontier",
        default="results/phase3/sc_cmpo/budget_frontier",
    )
    args = parser.parse_args()
    frontier = Path(args.budget_frontier)
    if not frontier.is_absolute():
        frontier = ROOT / frontier
    result = audit_budget_frontier_v1(frontier)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
