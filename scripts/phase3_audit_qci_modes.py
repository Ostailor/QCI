#!/usr/bin/env python
"""Audit historical QCi modes and create an offline integer job-body proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_integer_adapter import (  # noqa: E402
    build_integer_job_body,
    installed_qci_versions,
    load_integer_payload,
    validate_num_levels,
)
from cmpo.qci_response_audit import audit_tree, coefficient_dynamic_range  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
DEFAULT_PAYLOAD = Path("results/phase3/irc_cmpo/build/full_middle_budget_lambda_payload.json")
DEFAULT_OUTPUT = Path("results/phase3/irc_cmpo/integer_adapter_dry_run.json")


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_binary_levels(payload: Mapping[str, Any], derived_levels: list[int]) -> list[int]:
    variables = payload.get("variables")
    if not isinstance(variables, list) or not variables:
        raise ValueError("IRC-CMPO dry-run payload must contain binary variables")
    for index, variable in enumerate(variables):
        if not isinstance(variable, Mapping):
            raise ValueError(f"IRC-CMPO variable {index} is not a binary variable record")
        if str(variable.get("encoding_type", "")).lower() != "binary":
            raise ValueError(f"IRC-CMPO variable {index} must use binary encoding_type")
        if variable.get("lower_bound") != 0 or variable.get("upper_bound") != 1:
            raise ValueError(f"IRC-CMPO binary variable {index} must have bounds [0, 1]")
        if variable.get("num_levels", 2) != 2:
            raise ValueError(f"IRC-CMPO binary variable {index} must declare num_levels=2")
    expected = [2] * len(variables)
    if derived_levels != expected:
        raise ValueError("IRC-CMPO binary payload did not derive the full [2] * num_variables num_levels list")
    declared = payload.get("num_levels")
    if declared is not None and list(declared) != expected:
        raise ValueError("payload-level num_levels must equal the full binary domain list")
    return expected


def _version_audit(config: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    qci = config.get("qci", {})
    if not isinstance(qci, Mapping):
        raise ValueError("configuration must contain a qci mapping")
    installed = installed_qci_versions()
    pins = {
        "qci-client": str(qci.get("pinned_qci_client_version", "")),
        "eqc-models": str(qci.get("pinned_eqc_models_version", "")),
    }
    missing = [distribution for distribution, version in pins.items() if not version]
    if missing:
        raise ValueError(f"missing exact version pins for: {', '.join(missing)}")
    mismatches = {
        distribution: {"pinned": pins[distribution], "installed": installed[distribution]}
        for distribution in pins
        if pins[distribution] != installed[distribution]
    }
    if mismatches:
        raise ValueError(f"installed QCi package versions do not match pins: {mismatches}")
    return installed, {"pinned": pins, "installed": installed, "all_pins_match": True}


def _historical_audit(results_root: Path) -> dict[str, Any]:
    rows = audit_tree(results_root)
    counts = Counter(str(row["response_mode"]) for row in rows)
    ordered_counts = {
        "integer_qudit": counts["integer_qudit"],
        "normalized_continuous_qudit": counts["normalized_continuous_qudit"],
        "unknown": counts["unknown"],
    }
    return {
        "results_root": str(results_root),
        "response_count": len(rows),
        "counts": ordered_counts,
        "responses": [
            {
                "response_path": row["response_path"],
                "job_id": row["job_id"],
                "status": row["status"],
                "response_mode": row["response_mode"],
                "problem_config": row["problem_config"],
                "device_config": row["device_config"],
                "sum_constraint": row["sum_constraint"],
                "num_levels": json.loads(row["num_levels"]),
                "native_integral_sample_count": row["native_integral_sample_count"],
                "native_in_domain_sample_count": row["native_in_domain_sample_count"],
                "native_feasible_sample_count": row["native_feasible_sample_count"],
                "projected_sample_counted_native": row["projected_sample_counted_native"],
            }
            for row in rows
        ],
    }


def build_offline_audit(
    *,
    payload_path: Path,
    config_path: Path,
    results_root: Path,
) -> dict[str, Any]:
    """Build a local job body and historical audit without contacting QCi."""

    payload, qci_file, derived_levels = load_integer_payload(payload_path)
    num_levels = _strict_binary_levels(payload, derived_levels)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("IRC-CMPO configuration must be a mapping")
    qci = config.get("qci", {})
    if not isinstance(qci, Mapping):
        raise ValueError("IRC-CMPO configuration must contain qci settings")
    if qci.get("job_type") != "sample-hamiltonian-integer":
        raise ValueError("IRC-CMPO qci.job_type must be sample-hamiltonian-integer")
    if qci.get("device_type") != "dirac-3":
        raise ValueError("IRC-CMPO qci.device_type must be dirac-3")
    if qci.get("sum_constraint") is not None:
        raise ValueError("integer QCi configuration must not pass sum_constraint")
    versions, version_pin_audit = _version_audit(config)
    limit = int(qci["maximum_total_num_levels"])
    limit_source = str(qci["num_levels_limit_source"])
    if not limit_source:
        raise ValueError("qci.num_levels_limit_source must record device-limit provenance")
    level_audit = validate_num_levels(
        num_levels,
        max_total_num_levels=limit,
        limit_source=limit_source,
    )

    # QciClient.build_job_body is a local serializer. Constructing it with an
    # inert URL/token performs no query, upload, allocation check, or submission.
    import qci_client as qc  # noqa: PLC0415

    offline_client = qc.QciClient(url="https://offline.invalid", api_token="OFFLINE_NOT_A_TOKEN")
    num_samples = int(qci["samples_per_job"])
    relaxation_schedule = int(qci["relaxation_schedule"])
    job_body = build_integer_job_body(
        offline_client,
        polynomial_file_id="OFFLINE_DRY_RUN_NOT_UPLOADED",
        job_name="phase3-irc-cmpo-integer-offline-dry-run",
        job_tags=["phase3", "irc-cmpo", "integer", "offline-dry-run"],
        num_samples=num_samples,
        relaxation_schedule=relaxation_schedule,
        num_levels=num_levels,
        max_total_num_levels=limit,
        limit_source=limit_source,
    )
    return {
        "schema": "cmpo.irc_cmpo.integer_adapter_dry_run.v1",
        "offline_only": True,
        "qci_network_calls": 0,
        "qci_jobs_submitted": 0,
        "payload": {
            "path": str(payload_path),
            "sha256": _sha256(payload_path),
            "num_variables": len(num_levels),
            "maximum_degree": int(payload.get("max_degree", 0)),
        },
        "requested_job_type": "sample-hamiltonian-integer",
        "requested_job_params": {
            "device_type": "dirac-3",
            "num_samples": num_samples,
            "relaxation_schedule": relaxation_schedule,
            "num_levels": num_levels,
        },
        "job_body": job_body,
        "num_levels_audit": level_audit,
        "versions": versions,
        "version_pin_audit": version_pin_audit,
        "coefficient_dynamic_range": coefficient_dynamic_range(qci_file),
        "strict_response_expectations": {
            "required_problem_config": "qudit_hamiltonian_optimization",
            "required_device_config": "dirac-3_qudit",
            "required_num_levels": num_levels,
            "forbidden": [
                "normalized_qudit_hamiltonian_optimization",
                "dirac-3_normalized_qudit",
                "sum_constraint",
            ],
            "native_coordinates_must_be_integer": True,
            "native_coordinates_must_be_in_domain": True,
            "rounding_or_projection_permitted": False,
        },
        "historical_response_mode_audit": _historical_audit(results_root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--results-root", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config_path = _resolve(args.config)
    payload_path = _resolve(args.payload)
    results_root = _resolve(args.results_root)
    output = _resolve(args.output)
    if output.exists():
        print(f"Refusing to overwrite existing audit artifact: {output}", file=sys.stderr)
        return 1
    try:
        artifact = build_offline_audit(
            payload_path=payload_path,
            config_path=config_path,
            results_root=results_root,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(artifact, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "artifact": str(output),
                "historical_modes": artifact["historical_response_mode_audit"]["counts"],
                "qci_network_calls": 0,
                "qci_jobs_submitted": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
