#!/usr/bin/env python
"""Verify checked-in Phase 3 evidence and regenerate the final IRC-CMPO tables."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.phase3_monitor_irc_cmpo_final_batch import (  # noqa: E402
    generate_final_artifacts,
)
from scripts.qbraid_phase3_autorun import verify_checked_in_artifacts  # noqa: E402


PHASE3 = ROOT / "results/phase3"
IRC = PHASE3 / "irc_cmpo"
SC = PHASE3 / "sc_cmpo"
DEFAULT_OUTPUT = PHASE3 / "reproduced/irc_cmpo"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _result_sample_count(response: Mapping[str, Any]) -> int:
    results = response.get("results")
    if not isinstance(results, Mapping):
        raise ValueError("QCi response has no results object")
    counts = results.get("counts")
    if isinstance(counts, list) and counts:
        return sum(int(value) for value in counts)
    solutions = results.get("solutions")
    if isinstance(solutions, list):
        return len(solutions)
    raise ValueError("QCi response has neither counts nor solutions")


def _verify_compressed_consensus() -> dict[str, Any]:
    trace_dir = SC / "system_summary"
    rows = list(
        csv.DictReader(
            (trace_dir / "compressed_artifact_manifest.csv").open(encoding="utf-8")
        )
    )
    if len(rows) != 2:
        raise ValueError("SC-CMPO consensus archive manifest must contain two rows")
    verified = []
    for row in rows:
        archive = trace_dir / row["compressed_path"]
        if _sha256(archive) != row["compressed_sha256"]:
            raise ValueError(f"compressed consensus checksum mismatch: {archive}")
        digest = hashlib.sha256()
        size = 0
        with gzip.open(archive, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(block)
                digest.update(block)
        if size != int(row["original_size_bytes"]):
            raise ValueError(f"uncompressed consensus size mismatch: {archive}")
        if digest.hexdigest() != row["original_sha256"]:
            raise ValueError(f"uncompressed consensus checksum mismatch: {archive}")
        verified.append(row["original_path"])
    return {"archives": verified, "archive_count": len(verified)}


def _verify_artifact_manifest() -> dict[str, Any]:
    path = PHASE3 / "artifact_manifest.csv"
    if not path.is_file():
        return {"present": False, "verified_files": 0}
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for row in rows:
        artifact = ROOT / row["path"]
        if not artifact.is_file():
            raise FileNotFoundError(f"artifact manifest entry is missing: {artifact}")
        if artifact.stat().st_size != int(row["size_bytes"]):
            raise ValueError(f"artifact size mismatch: {artifact}")
        if _sha256(artifact) != row["sha256"]:
            raise ValueError(f"artifact checksum mismatch: {artifact}")
    return {"present": True, "verified_files": len(rows)}


def verify_phase3_artifacts() -> dict[str, Any]:
    """Validate the exact retained hardware evidence without running an experiment."""

    payload_rows = list(
        csv.DictReader((IRC / "payload_manifest.csv").open(encoding="utf-8"))
    )
    if len(payload_rows) != 6:
        raise ValueError("IRC-CMPO requires six lambda payloads")
    for row in payload_rows:
        index = int(row["lambda_index"])
        payload = _read_json(IRC / "payloads" / f"lambda_{index:02d}.json")
        if payload.get("num_variables") != 33 or payload.get("max_degree") != 3:
            raise ValueError(f"lambda {index} is not the final 33-variable cubic payload")
        if payload.get("num_levels") != [2] * 33:
            raise ValueError(f"lambda {index} does not use native binary levels")
        if payload["irc_cmpo"].get("projection_permitted") is not False:
            raise ValueError(f"lambda {index} permits projection")
        audit = payload["dirac3_scaling"]["audit"]
        if audit.get("passed") is not True or float(audit["dynamic_range"]) > 200:
            raise ValueError(f"lambda {index} failed coefficient scaling validation")

    status_rows = list(csv.DictReader((IRC / "qci/job_status.csv").open(encoding="utf-8")))
    if len(status_rows) != 8 or any(row["status"] != "COMPLETED" for row in status_rows):
        raise ValueError("the final IRC-CMPO QCi batch is not 8/8 completed")
    completed_samples = 0
    for row in status_rows:
        name = row["name"]
        expected = int(row["num_samples"])
        response = _read_json(IRC / "qci/responses" / f"{name}.result.json")
        actual = _result_sample_count(response)
        if actual != expected:
            raise ValueError(f"{name} returned {actual} samples, expected {expected}")
        validation = _read_json(IRC / "qci/validations" / f"{name}.json")
        if validation.get("passed") is not True or validation.get("projection_used") is not False:
            raise ValueError(f"{name} failed native no-projection validation")
        completed_samples += actual
    native_summary = _read_json(IRC / "qci/native_evaluation_summary.json")
    if native_summary.get("full_jobs_completed") != 6:
        raise ValueError("native evaluation summary does not contain all six lambda jobs")
    if native_summary.get("full_jobs_failed") != 0:
        raise ValueError("native evaluation summary records failed full jobs")
    if native_summary.get("native_projection_used") is not False:
        raise ValueError("native evaluation summary records projection")

    gpu = verify_checked_in_artifacts(
        manifest_path=IRC / "payload_manifest.csv",
        payload_dir=IRC / "payloads",
        artifact_dir=IRC / "baselines/gpu",
    )
    sc_status = list(csv.DictReader((SC / "qci/job_status.csv").open(encoding="utf-8")))
    if len(sc_status) != 43 or any(row["status"] != "COMPLETED" for row in sc_status):
        raise ValueError("the retained SC-CMPO QCi evidence is not 43/43 completed")
    sc_payloads = list((SC / "qci_payloads").glob("*.json"))
    if len(sc_payloads) != 43:
        raise ValueError("the retained SC-CMPO payload bundle must contain 43 payloads")

    return {
        "status": "verified",
        "irc_payloads": len(payload_rows),
        "irc_qci_jobs_completed": len(status_rows),
        "irc_qci_jobs_failed": 0,
        "irc_returned_samples": completed_samples,
        "irc_projection_used": False,
        "gpu": gpu,
        "sc_qci_jobs_completed": len(sc_status),
        "sc_qci_jobs_failed": 0,
        "sc_consensus": _verify_compressed_consensus(),
        "artifact_manifest": _verify_artifact_manifest(),
    }


def _compare_csv_outputs(reproduced: Path, checked_in: Path) -> list[str]:
    compared = []
    for expected in sorted(checked_in.glob("*.csv")):
        actual = reproduced / expected.name
        if not actual.is_file():
            raise FileNotFoundError(f"regeneration did not create {actual.name}")
        left = pd.read_csv(expected)
        right = pd.read_csv(actual)
        try:
            pd.testing.assert_frame_equal(
                left,
                right,
                check_dtype=False,
                check_exact=False,
                rtol=1e-12,
                atol=1e-12,
            )
        except AssertionError as exc:
            raise ValueError(f"regenerated table differs from {expected}: {exc}") from exc
        compared.append(expected.name)
    return compared


def reproduce(output_dir: Path, *, overwrite: bool) -> dict[str, Any]:
    verification = verify_phase3_artifacts()
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(f"reproduction output already exists: {output_dir}")
        shutil.rmtree(output_dir)
    summary = _read_json(IRC / "qci/native_evaluation_summary.json")
    generated = generate_final_artifacts(
        batch_dir=IRC / "qci",
        evaluations=summary["evaluations"],
        gpu_dir=IRC / "baselines/gpu",
        output_dir=output_dir,
        dataset_path=IRC / "dataset/portfolio_labels.csv",
        exact_validation_path=IRC / "validation/exact_validation.json",
    )
    if generated.get("ready") is not True:
        raise RuntimeError(f"final artifact regeneration failed: {generated}")
    compared = _compare_csv_outputs(output_dir, IRC / "final")
    try:
        reported_output = output_dir.relative_to(ROOT).as_posix()
    except ValueError:
        reported_output = str(output_dir)
    return {
        **verification,
        "reproduced_output": reported_output,
        "tables_matched": compared,
        "generated": generated,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Create-only directory for regenerated tables and figures.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate checked-in evidence without regenerating tables or figures.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace only the requested reproduction output directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the artifact-first plan without reading or writing results.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "artifact-first",
                    "runs_qci": False,
                    "runs_gpu": False,
                    "verify_only": args.verify_only,
                    "output_dir": str(output),
                },
                indent=2,
            )
        )
        return 0
    result = verify_phase3_artifacts() if args.verify_only else reproduce(
        output, overwrite=args.overwrite
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
