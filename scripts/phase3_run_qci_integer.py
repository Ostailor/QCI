#!/usr/bin/env python
"""Prepare or explicitly execute one strict QCi Dirac-3 integer job."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_client_adapter import validate_qci_environment  # noqa: E402
from cmpo.qci_integer_adapter import (  # noqa: E402
    INTEGER_JOB_TYPE,
    build_integer_job_body,
    installed_qci_versions,
    load_integer_payload,
    validate_integer_response,
    validate_num_levels,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a Dirac-3 integer request. No QCi job is submitted unless --execute is supplied; "
            "all output files are create-only."
        )
    )
    parser.add_argument("payload", type=Path, help="Integer CMPO payload JSON.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New raw-artifact directory for this job.")
    parser.add_argument("--num-samples", type=int, default=30)
    parser.add_argument("--relaxation-schedule", type=int, default=1)
    parser.add_argument("--job-name", default=None)
    parser.add_argument("--job-tag", action="append", default=[])
    parser.add_argument(
        "--max-total-num-levels",
        type=int,
        help="Pinned Dirac-3 total-level capacity from experiment/device configuration.",
    )
    parser.add_argument("--limit-source", help="Human-readable provenance for --max-total-num-levels.")
    parser.add_argument("--execute", action="store_true", help="Explicitly authorize one paid QCi submission.")
    return parser


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
    except FileExistsError as exc:
        raise RuntimeError(f"Will not overwrite existing raw artifact: {path}") from exc


def _preview(args: argparse.Namespace, qci_file: dict[str, Any], levels: list[int]) -> dict[str, Any]:
    level_audit = validate_num_levels(
        levels,
        max_total_num_levels=args.max_total_num_levels,
        limit_source=args.limit_source,
    )
    return {
        "payload": str(args.payload),
        "job_type": INTEGER_JOB_TYPE,
        "job_name": args.job_name or f"irc-cmpo-{args.payload.stem}",
        "job_tags": args.job_tag or ["phase3", "irc-cmpo", "integer", "dirac-3"],
        "job_params": {
            "device_type": "dirac-3",
            "num_samples": args.num_samples,
            "relaxation_schedule": args.relaxation_schedule,
            "num_levels": levels,
        },
        "polynomial": qci_file["file_config"]["polynomial"],
        "level_audit": level_audit,
        "versions": installed_qci_versions(),
        "execute": False,
    }


def _allocation(client: Any) -> dict[str, Any]:
    allocation = client.get_allocations().get("allocations", {}).get("dirac", {})
    if allocation.get("metered", True) and float(allocation.get("seconds", 0.0)) <= 0.0:
        raise RuntimeError("QCi Dirac allocation has no remaining seconds")
    return dict(allocation)


def main() -> int:
    args = build_parser().parse_args()
    _, qci_file, levels = load_integer_payload(args.payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.execute:
        if args.max_total_num_levels is None:
            raise SystemExit("--max-total-num-levels is required for an offline request preview")
        preview = _preview(args, qci_file, levels)
        preview_path = args.output_dir / "request_preview.json"
        try:
            _write_new_json(preview_path, preview)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps({"dry_run": True, "request_preview": str(preview_path), "versions": preview["versions"]}, indent=2))
        return 0

    request_path = args.output_dir / "request.json"
    response_path = args.output_dir / "response.json"
    validation_path = args.output_dir / "response_validation.json"
    existing = [path for path in (request_path, response_path, validation_path) if path.exists()]
    if existing:
        print(f"Refusing to overwrite existing raw artifacts: {', '.join(map(str, existing))}", file=sys.stderr)
        return 1

    validate_qci_environment()
    import qci_client as qc  # noqa: PLC0415

    client = qc.QciClient()
    allocation = _allocation(client)
    level_audit = validate_num_levels(
        levels,
        client=client,
        max_total_num_levels=args.max_total_num_levels,
        limit_source=args.limit_source,
    )
    file_response = client.upload_file(file=qci_file)
    job_body = build_integer_job_body(
        client,
        polynomial_file_id=str(file_response["file_id"]),
        job_name=args.job_name or f"irc-cmpo-{args.payload.stem}",
        job_tags=args.job_tag or ["phase3", "irc-cmpo", "integer", "dirac-3"],
        num_samples=args.num_samples,
        relaxation_schedule=args.relaxation_schedule,
        num_levels=levels,
        max_total_num_levels=level_audit["limit"],
        limit_source=level_audit["limit_source"],
    )
    request_record = {
        "payload": str(args.payload),
        "qci_file": qci_file,
        "file_response": file_response,
        "job_body": job_body,
        "allocation_before_submission": allocation,
        "level_audit": level_audit,
        "versions": installed_qci_versions(),
    }
    _write_new_json(request_path, request_record)
    try:
        response = client.process_job(job_body=job_body)
    except Exception as exc:
        _write_new_json(response_path, {"status": "CLIENT_ERROR", "error_type": type(exc).__name__, "error": str(exc)})
        raise
    _write_new_json(response_path, response)
    validation = validate_integer_response(response, expected_num_levels=levels)
    _write_new_json(validation_path, validation.to_dict())
    print(
        json.dumps(
            {
                "request": str(request_path),
                "response": str(response_path),
                "validation": str(validation_path),
                "integer_response_valid": validation.valid,
                "native_feasible_rate": (
                    validation.native_integer_in_domain_count / validation.native_sample_count
                    if validation.native_sample_count
                    else 0.0
                ),
                "projection_used": False,
            },
            indent=2,
        )
    )
    return 0 if validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
