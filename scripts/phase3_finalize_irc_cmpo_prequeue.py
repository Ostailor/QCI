#!/usr/bin/env python
"""Create the final create-only IRC-CMPO offline go/no-go report."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


SUMMARY_KEYS = (
    "HISTORICAL_MODE_AUDIT:",
    "INTEGER_ADAPTER_DRY_RUN:",
    "TRUE_RECOURSE_VALID:",
    "SURROGATE_VALID:",
    "DYNAMIC_RANGE_VALID:",
    "EXACT_HAMILTONIAN_VALID:",
    "LOCAL_STOCHASTIC_VALID:",
    "IRC_CMPO_READY_FOR_QCI:",
)
GATE_KEYS = tuple(key.rstrip(":").lower() for key in SUMMARY_KEYS[:-1])
REPORT_NAME = "final_prequeue_report_v4.md"
SUMMARY_NAME = "final_prequeue_summary_v4.json"
PRIOR_REPORT_NAME = "final_prequeue_report.md"
PRIOR_SUMMARY_NAME = "final_prequeue_summary.json"
SURROGATE_MODEL_V2 = "surrogate/surrogate_model_final_prequeue_v2.json"
SURROGATE_MODEL_V1 = "surrogate/surrogate_model_final_prequeue_v1.json"
PAYLOAD_MANIFEST_V2 = "payload_manifest_final_prequeue_v3.csv"
PAYLOAD_MANIFEST_V1 = "payload_manifest_final_prequeue_v1.csv"
OFFLINE_MANIFEST_V4 = (
    "offline_validation_final_prequeue_v4/"
    "offline_validation_manifest_final_prequeue_v4.json"
)
OFFLINE_MANIFEST_V1 = (
    "offline_validation_final_prequeue_v1/"
    "offline_validation_manifest_final_prequeue_v1.json"
)


def readiness_from_evidence(evidence: Mapping[str, Any]) -> str:
    if isinstance(evidence.get("gate_status"), Mapping):
        return (
            "YES"
            if all(evidence["gate_status"].get(key) == "PASS" for key in GATE_KEYS)
            else "NO"
        )
    return "YES" if all(bool(evidence.get(key, False)) for key in GATE_KEYS) else "NO"


def summary_lines(evidence: Mapping[str, Any]) -> list[str]:
    readiness = readiness_from_evidence(evidence)
    statuses = evidence.get("gate_status", {})
    values = [
        str(statuses.get(key, "PASS" if bool(evidence.get(key, False)) else "FAIL"))
        for key in GATE_KEYS
    ]
    return [
        *(f"{key} {value}" for key, value in zip(SUMMARY_KEYS[:-1], values, strict=True)),
        f"{SUMMARY_KEYS[-1]} {readiness}",
    ]


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def collect_evidence(base: Path) -> dict[str, Any]:
    """Collect v2 evidence while retaining explicit provenance for the failed v1 audit."""

    root_cause = ROOT / "results/phase3/root_cause_integer_encoding"
    response_path = root_cause / "response_mode_audit.csv"
    response = pd.read_csv(response_path) if response_path.is_file() else pd.DataFrame()
    modes = response.get("effective_mode", pd.Series(dtype=str)).astype(str).value_counts().to_dict()
    continuous = int(modes.get("normalized_continuous_qudit", 0))
    integer = int(modes.get("integer_qudit", 0))
    unknown = int(modes.get("unknown", 0))
    historical_valid = bool(len(response) and continuous + integer + unknown == len(response))

    dry = _read_json(base / "integer_adapter_dry_run.json") or {}
    requested = dry.get("requested_job_params", {})
    job_body_text = json.dumps(dry.get("job_body", {}), sort_keys=True)
    dry_valid = bool(
        dry.get("requested_job_type") == "sample-hamiltonian-integer"
        and requested.get("device_type") == "dirac-3"
        and requested.get("num_levels") == [2] * 33
        and "sum_constraint" not in job_body_text
        and "qudit_hamiltonian_optimization" in job_body_text
        and "dirac-3_qudit" in job_body_text
        and int(dry.get("qci_network_calls", -1)) == 0
        and int(dry.get("qci_jobs_submitted", -1)) == 0
    )

    labels_path = base / "dataset/portfolio_labels.csv"
    failures_path = base / "dataset/recourse_failures.csv"
    labels = pd.read_csv(labels_path) if labels_path.is_file() else pd.DataFrame()
    failures = pd.read_csv(failures_path) if failures_path.is_file() else pd.DataFrame()
    true_recourse_valid = bool(
        len(labels) >= 3000
        and labels.get("portfolio_signature", pd.Series(dtype=str)).astype(str).nunique() >= 3000
        and labels.get("true_fixed_upgrade_recourse", pd.Series(dtype=bool)).astype(bool).all()
        and not labels.get("used_fraction_completion", pd.Series([True])).astype(bool).any()
        and labels.get("feasibility", pd.Series(dtype=bool)).astype(bool).all()
        and set(labels.get("patch_count", ())) == {12}
        and set(labels.get("training_scenario_count", ())) == {8}
        and set(labels.get("heldout_contingency_count", ())) == {10}
        and len(failures) == 0
    )

    surrogate_v2_path = base / SURROGATE_MODEL_V2
    surrogate_v1_path = base / SURROGATE_MODEL_V1
    surrogate = _read_json(surrogate_v2_path) or {}
    target_models = surrogate.get("targets", {})
    surrogate_valid = bool(
        surrogate.get("gates_passed", False)
        and len(target_models) == 5
        and all(bool(model.get("metrics", {}).get("gate_passed", False)) for model in target_models.values())
    )

    payload_manifest_path = base / PAYLOAD_MANIFEST_V2
    payload_manifest = (
        pd.read_csv(payload_manifest_path) if payload_manifest_path.is_file() else pd.DataFrame()
    )
    dynamic_range_valid = bool(
        len(payload_manifest) == 6
        and payload_manifest.get("post_quantization_gates_passed", pd.Series(dtype=bool)).astype(bool).all()
        and (payload_manifest.get("dynamic_range", pd.Series([math.inf])).astype(float) <= 200.0 + 1e-12).all()
        and (
            payload_manifest.get("minimum_level_separation", pd.Series([0.0])).astype(float)
            >= 1.0 / 200.0 - 1e-12
        ).all()
    )

    offline_path = base / OFFLINE_MANIFEST_V4
    offline = _read_json(offline_path) or {}
    exact_valid = bool(offline.get("exact_hamiltonian_valid", False))
    stochastic_valid = bool(offline.get("local_stochastic_valid", False))
    gate_status = {
        "historical_mode_audit": "PASS" if historical_valid else "FAIL",
        "integer_adapter_dry_run": "PASS" if dry_valid else "FAIL",
        "true_recourse_valid": "PASS" if true_recourse_valid else "FAIL",
        "surrogate_valid": (
            "PASS" if surrogate_valid else "FAIL" if surrogate_v2_path.is_file() else "NOT RUN"
        ),
        "dynamic_range_valid": (
            "PASS"
            if dynamic_range_valid
            else "FAIL"
            if payload_manifest_path.is_file()
            else "NOT RUN"
        ),
        "exact_hamiltonian_valid": (
            "PASS" if exact_valid else "FAIL" if offline_path.is_file() else "NOT RUN"
        ),
        "local_stochastic_valid": (
            "PASS" if stochastic_valid else "FAIL" if offline_path.is_file() else "NOT RUN"
        ),
    }
    prior_surrogate = _read_json(surrogate_v1_path) or {}
    prior_payload_path = base / PAYLOAD_MANIFEST_V1
    prior_offline_path = base / OFFLINE_MANIFEST_V1
    evidence: dict[str, Any] = {
        "historical_mode_audit": historical_valid,
        "integer_adapter_dry_run": dry_valid,
        "true_recourse_valid": true_recourse_valid,
        "surrogate_valid": surrogate_valid,
        "dynamic_range_valid": dynamic_range_valid,
        "exact_hamiltonian_valid": exact_valid,
        "local_stochastic_valid": stochastic_valid,
        "historical_counts": {
            "normalized_continuous_qudit": continuous,
            "integer_qudit": integer,
            "unknown": unknown,
        },
        "dataset": {
            "successful_labels": int(len(labels)),
            "failures": int(len(failures)),
            "unique_signatures": int(
                labels.get("portfolio_signature", pd.Series(dtype=str)).astype(str).nunique()
            ),
        },
        "surrogate_metrics": {
            name: model.get("metrics", {}) for name, model in target_models.items()
        },
        "coefficient_audit": payload_manifest.to_dict("records"),
        "offline_validation": offline,
        "gate_status": gate_status,
        "evidence_sources": {
            "surrogate": str(surrogate_v2_path),
            "payload_manifest": str(payload_manifest_path),
            "offline_validation": str(offline_path),
        },
        "prior_v1_evidence": {
            "surrogate_present": surrogate_v1_path.is_file(),
            "surrogate_gates_passed": bool(prior_surrogate.get("gates_passed", False)),
            "surrogate_path": str(surrogate_v1_path),
            "payload_manifest_present": prior_payload_path.is_file(),
            "payload_manifest_path": str(prior_payload_path),
            "offline_manifest_present": prior_offline_path.is_file(),
            "offline_manifest_path": str(prior_offline_path),
            "final_report_present": (base / PRIOR_REPORT_NAME).is_file(),
            "final_report_path": str(base / PRIOR_REPORT_NAME),
            "final_summary_present": (base / PRIOR_SUMMARY_NAME).is_file(),
            "final_summary_path": str(base / PRIOR_SUMMARY_NAME),
        },
        "qci_jobs_submitted_during_final_prequeue_audit": 0,
        "projection_used_for_integer_samples": False,
        "strict_stop_reason": _strict_stop_reason(gate_status),
    }
    evidence["irc_cmpo_ready_for_qci"] = readiness_from_evidence(evidence) == "YES"
    evidence["IRC_CMPO_READY_FOR_QCI"] = readiness_from_evidence(evidence)
    return evidence


def _strict_stop_reason(gate_status: Mapping[str, str]) -> str:
    if gate_status.get("surrogate_valid") != "PASS":
        return (
            "surrogate_v2_not_passed; payload construction, coefficient quantization, "
            "exact Hamiltonian solving, and stochastic proxy were not run"
        )
    if gate_status.get("dynamic_range_valid") != "PASS":
        return "dynamic_range_v2_not_passed; exact and stochastic validation were not run"
    if any(
        gate_status.get(key) != "PASS"
        for key in ("exact_hamiltonian_valid", "local_stochastic_valid")
    ):
        return "offline_validation_v2_not_passed"
    return "none"


def write_final_report(base: Path, evidence: Mapping[str, Any]) -> tuple[Path, Path]:
    report = base / REPORT_NAME
    summary = base / SUMMARY_NAME
    if existing := [str(path) for path in (report, summary) if path.exists()]:
        raise FileExistsError(f"final prequeue artifacts are create-only: {existing}")
    base.mkdir(parents=True, exist_ok=True)
    metrics = evidence.get("surrogate_metrics", {})
    lines = [
        "# IRC-CMPO Final Pre-Queue Root-Cause Repair and Go/No-Go Audit",
        "",
        f"**IRC_CMPO_READY_FOR_QCI: {evidence['IRC_CMPO_READY_FOR_QCI']}**",
        "",
        "No QCi job was submitted during this audit. Historical artifacts remain untouched.",
        "",
        "## Historical mode and integer transport",
        "",
        f"- Historical response modes: `{json.dumps(evidence['historical_counts'], sort_keys=True)}`.",
        f"- Integer adapter dry run: `{evidence.get('gate_status', {}).get('integer_adapter_dry_run', 'PASS' if evidence['integer_adapter_dry_run'] else 'FAIL')}`.",
        "- Final master domains: `33` binary variables, `66` total num_levels.",
        "- Requested integer mode: `sample-hamiltonian-integer` / `dirac-3`; no `sum_constraint`.",
        "",
        "## True recourse dataset",
        "",
        f"- Evidence: `{json.dumps(evidence['dataset'], sort_keys=True)}`.",
        f"- Gate: `{evidence.get('gate_status', {}).get('true_recourse_valid', 'PASS' if evidence['true_recourse_valid'] else 'FAIL')}`.",
        "- Labels use fixed public upgrades, both SLSQP and piecewise-linear MILP paths, overlap consensus, full-system active-power projection, eight training scenarios, and ten held-out contingencies.",
        "",
        "## Surrogate gates",
        "",
    ]
    if metrics:
        for target, row in metrics.items():
            lines.append(
                f"- `{target}`: nRMSE `{row.get('normalized_rmse', 'unavailable')}`, "
                f"Spearman `{row.get('spearman_rank_correlation', 'unavailable')}`, "
                f"top-decile recall `{row.get('top_decile_recall', 'unavailable')}`, "
                f"Pareto recall `{row.get('pareto_front_recall', 'unavailable')}`, "
                f"gate `{'PASS' if row.get('gate_passed', False) else 'FAIL'}`."
            )
    else:
        surrogate_status = evidence.get("gate_status", {}).get("surrogate_valid", "FAIL")
        lines.append(
            f"- Final multi-target surrogate artifacts are unavailable; gate `{surrogate_status}`."
        )
    lines.extend(
        [
            "",
            "## Hardware scaling and offline ground-state validation",
            "",
            f"- Dynamic-range gate: `{evidence.get('gate_status', {}).get('dynamic_range_valid', 'PASS' if evidence['dynamic_range_valid'] else 'FAIL')}`.",
            f"- Exact Hamiltonian gate: `{evidence.get('gate_status', {}).get('exact_hamiltonian_valid', 'PASS' if evidence['exact_hamiltonian_valid'] else 'FAIL')}`.",
            f"- Local stochastic gate: `{evidence.get('gate_status', {}).get('local_stochastic_valid', 'PASS' if evidence['local_stochastic_valid'] else 'FAIL')}`.",
            f"- Strict-stop disposition: `{evidence['strict_stop_reason']}`.",
            "- No returned or local sample was rounded, repaired, or projected into a binary portfolio.",
            "",
            "## Remaining known limitations",
            "",
            "- Paid Dirac-3 integer behavior remains untested until the three smoke jobs are explicitly run after a YES decision.",
            "- OpenDSS unbalanced-AC replay is recorded separately from this active-power recourse dataset and is not a surrogate label.",
            "- The GPU-compatible random feasible generator used its deterministic NumPy CPU path on this workstation.",
            "- Earlier normalized-continuous QCi results remain valid only as a continuous-solver misconfiguration ablation.",
            "",
            "## Gate summary",
            "",
            "```text",
            *summary_lines(evidence),
            "```",
            "",
        ]
    )
    with report.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    with summary.open("x", encoding="utf-8") as handle:
        json.dump(dict(evidence), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return report, summary


def write_strict_stop_coefficient_audit(base: Path, evidence: Mapping[str, Any]) -> None:
    """Record why no payload coefficient distribution exists after a strict stop."""

    if bool(evidence.get("surrogate_valid", False)):
        return
    csv_path = base / "coefficient_audit_final_prequeue_v3.csv"
    md_path = base / "coefficient_audit_final_prequeue_v3.md"
    if csv_path.exists() or md_path.exists():
        return
    with csv_path.open("x", encoding="utf-8") as handle:
        handle.write(
            "status,payload_count,reason,qci_jobs_submitted\n"
            "not_run,0,surrogate_test_gates_failed,0\n"
        )
    with md_path.open("x", encoding="utf-8") as handle:
        handle.write(
            "# IRC-CMPO Final Prequeue Coefficient Audit\n\n"
            "Status: **NOT RUN**. The multi-target surrogate failed required test-set gates, "
            "so the strict-stop rule prohibited payload construction and coefficient "
            "quantization. No dynamic-range result is claimed and no QCi job was submitted.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="results/phase3/irc_cmpo")
    args = parser.parse_args()
    base = Path(args.base)
    if not base.is_absolute():
        base = ROOT / base
    evidence = collect_evidence(base)
    write_strict_stop_coefficient_audit(base, evidence)
    write_final_report(base, evidence)
    print("\n".join(summary_lines(evidence)))


if __name__ == "__main__":
    main()
