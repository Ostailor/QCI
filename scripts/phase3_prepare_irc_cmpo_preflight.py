#!/usr/bin/env python
"""Build the IRC-CMPO QCi readiness decision from freshly generated artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = ROOT / "results/phase3/irc_cmpo"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required IRC-CMPO artifact is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"required IRC-CMPO artifact is missing: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _write(path: Path, text: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(text)


def inspect_preflight(artifact_root: Path | str) -> dict[str, Any]:
    """Validate all offline gates and return a serializable readiness record."""

    artifacts = Path(artifact_root).resolve()
    labels = _read_csv(artifacts / "dataset/portfolio_labels.csv")
    failures_path = artifacts / "dataset/recourse_failures.csv"
    failures = _read_csv(failures_path) if failures_path.is_file() else []
    fit = _read_json(artifacts / "surrogate/fit_manifest.json")
    surrogate_metrics = _read_csv(artifacts / "surrogate/metrics.csv")
    payloads = _read_csv(artifacts / "payload_manifest.csv")
    exact = _read_json(artifacts / "validation/exact_validation.json")
    stochastic = _read_json(artifacts / "validation/stochastic_validation.json")
    validation = _read_json(artifacts / "validation/manifest.json")

    errors: list[str] = []
    signatures = {
        str(row.get("portfolio_signature", "")).strip()
        for row in labels
        if str(row.get("portfolio_signature", "")).strip()
    }
    dataset_valid = len(labels) >= 3000 and len(signatures) == len(labels) and not failures
    if not dataset_valid:
        errors.append(
            "true-recourse dataset must contain at least 3,000 unique successful "
            "labels and zero failures"
        )

    surrogate_valid = (
        fit.get("surrogate_valid") is True
        and fit.get("payload_build_permitted") is True
        and int(fit.get("unique_portfolios", 0)) >= 3000
        and bool(surrogate_metrics)
        and all(_as_bool(row.get("gate_passed")) for row in surrogate_metrics)
        and all(_as_bool(row.get("all_coefficients_finite")) for row in surrogate_metrics)
        and all(int(float(row.get("degree", 99))) <= 3 for row in surrogate_metrics)
    )
    if not surrogate_valid:
        errors.append("surrogate fit or one of its metric gates failed")

    ordered_lambdas = [int(row.get("lambda_index", -1)) for row in payloads]
    payloads_valid = (
        ordered_lambdas == list(range(6))
        and all(int(float(row.get("num_variables", 0))) == 33 for row in payloads)
        and all(int(float(row.get("total_num_levels", 0))) == 66 for row in payloads)
        and all(int(float(row.get("maximum_degree", 99))) <= 3 for row in payloads)
        and all(float(row.get("dynamic_range", float("inf"))) <= 200.0 for row in payloads)
        and all(_as_bool(row.get("post_quantization_gates_passed")) for row in payloads)
        and all(not _as_bool(row.get("projection_used")) for row in payloads)
    )
    if not payloads_valid:
        errors.append(
            "the six payloads must be 33-variable native-binary degree-3 "
            "Hamiltonians with passing scaling gates and no projection"
        )

    exact_valid = (
        exact.get("suite", {}).get("gates_passed") is True
        and exact.get("suite", {}).get("lambda_count") == 6
        and exact.get("projection_used") is False
    )
    stochastic_valid = (
        stochastic.get("suite", {}).get("gates_passed") is True
        and stochastic.get("suite", {}).get("passed_lambda_count") == 6
        and stochastic.get("projection_used") is False
    )
    validation_valid = (
        validation.get("exact_hamiltonian_valid") is True
        and validation.get("local_stochastic_valid") is True
        and validation.get("projection_used") is False
        and validation.get("lambda_count") == 6
    )
    if not (exact_valid and stochastic_valid and validation_valid):
        errors.append("exact or stochastic offline validation failed")

    ready = not errors
    return {
        "schema": "cmpo.irc_cmpo.preflight.v1",
        "IRC_CMPO_READY_FOR_QCI": "YES" if ready else "NO",
        "artifact_root": str(artifacts),
        "dataset": {
            "successful_labels": len(labels),
            "unique_signatures": len(signatures),
            "failures": len(failures),
            "passed": dataset_valid,
        },
        "surrogate": {
            "target_count": len(surrogate_metrics),
            "unique_portfolios": int(fit.get("unique_portfolios", 0)),
            "passed": surrogate_valid,
        },
        "payloads": {
            "payload_count": len(payloads),
            "maximum_variables": max(
                (int(float(row.get("num_variables", 0))) for row in payloads),
                default=0,
            ),
            "maximum_degree": max(
                (int(float(row.get("maximum_degree", 0))) for row in payloads),
                default=0,
            ),
            "maximum_dynamic_range": max(
                (float(row.get("dynamic_range", 0.0)) for row in payloads),
                default=0.0,
            ),
            "projection_used": any(
                _as_bool(row.get("projection_used")) for row in payloads
            ),
            "passed": payloads_valid,
        },
        "offline_validation": {
            "exact_hamiltonian_valid": exact_valid,
            "local_stochastic_valid": stochastic_valid,
            "projection_used": validation.get("projection_used"),
            "passed": validation_valid,
        },
        "errors": errors,
    }


def _report(summary: dict[str, Any]) -> str:
    dataset = summary["dataset"]
    surrogate = summary["surrogate"]
    payloads = summary["payloads"]
    validation = summary["offline_validation"]
    errors = summary["errors"]
    lines = [
        "# IRC-CMPO Preflight",
        "",
        f"**IRC_CMPO_READY_FOR_QCI: {summary['IRC_CMPO_READY_FOR_QCI']}**",
        "",
        "| Gate | Evidence | Status |",
        "|---|---:|---|",
        (
            f"| True-recourse dataset | {dataset['successful_labels']} labels, "
            f"{dataset['failures']} failures | {'PASS' if dataset['passed'] else 'FAIL'} |"
        ),
        (
            f"| Surrogate | {surrogate['target_count']} targets, "
            f"{surrogate['unique_portfolios']} portfolios | "
            f"{'PASS' if surrogate['passed'] else 'FAIL'} |"
        ),
        (
            f"| Native payloads | {payloads['payload_count']} payloads, "
            f"{payloads['maximum_variables']} variables, degree "
            f"{payloads['maximum_degree']} | {'PASS' if payloads['passed'] else 'FAIL'} |"
        ),
        (
            f"| Exact validation | {validation['exact_hamiltonian_valid']} | "
            f"{'PASS' if validation['exact_hamiltonian_valid'] else 'FAIL'} |"
        ),
        (
            f"| Stochastic validation | {validation['local_stochastic_valid']} | "
            f"{'PASS' if validation['local_stochastic_valid'] else 'FAIL'} |"
        ),
        (
            f"| Portfolio projection | {payloads['projection_used']} | "
            f"{'PASS' if not payloads['projection_used'] else 'FAIL'} |"
        ),
        "",
    ]
    if errors:
        lines.extend(["## Blocking Errors", "", *[f"- {error}" for error in errors], ""])
    return "\n".join(lines)


def prepare_preflight(
    artifact_root: Path | str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate and write the machine-readable and judge-readable preflight."""

    artifacts = Path(artifact_root).resolve()
    summary = inspect_preflight(artifacts)
    if summary["IRC_CMPO_READY_FOR_QCI"] != "YES":
        raise ValueError("IRC-CMPO preflight failed: " + "; ".join(summary["errors"]))
    _write(
        artifacts / "preflight_summary.json",
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        overwrite=overwrite,
    )
    _write(
        artifacts / "preflight_report.md",
        _report(summary),
        overwrite=overwrite,
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="Fresh IRC-CMPO tree containing dataset, surrogate, payload, and validation artifacts.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace only existing preflight_summary.json and preflight_report.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate all preflight gates without writing files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        summary = inspect_preflight(args.artifact_root)
        summary["dry_run"] = True
    else:
        summary = prepare_preflight(args.artifact_root, overwrite=args.overwrite)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
