#!/usr/bin/env python
"""Preflight and asynchronously submit the eight final IRC-CMPO QCi jobs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_batch import (  # noqa: E402
    build_final_job_specs,
    submit_final_batch,
    validate_final_preflight,
)
from cmpo.qci_client_adapter import (  # noqa: E402
    _client_from_environment,
    validate_qci_environment,
)
from cmpo.qci_integer_adapter import installed_qci_versions  # noqa: E402


DEFAULT_OUTPUT = ROOT / "results/phase3/reproduced/irc_cmpo/qci_live"
DEFAULT_ARTIFACT_ROOT = ROOT / "results/phase3/irc_cmpo"


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="IRC-CMPO artifact tree containing preflight, smoke, and full payloads.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement that this command submits eight QCi jobs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the eight-job submission plan without checking credentials or contacting QCi.",
    )
    args = parser.parse_args()
    if args.dry_run and args.execute:
        raise SystemExit("--dry-run and --execute are mutually exclusive")
    if args.dry_run:
        specs = build_final_job_specs(ROOT, artifact_root=args.artifact_root)
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "action": "submit_irc_cmpo_final_batch",
                    "output_dir": str(args.output_dir),
                    "artifact_root": str(args.artifact_root),
                    "job_count": len(specs),
                    "jobs": [spec.name for spec in specs],
                    "qci_jobs_submitted": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if not args.execute:
        raise SystemExit("refusing paid submission without --execute")

    validate_qci_environment()
    versions = installed_qci_versions()
    client = _client_from_environment()
    allocations = client.get_allocations().get("allocations", {})
    allocation = allocations.get("dirac", {}) if isinstance(allocations, dict) else {}
    preflight = validate_final_preflight(
        ROOT,
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
        versions=versions,
        allocation=allocation,
    )
    commit = _git_commit()
    manifest = submit_final_batch(
        client,
        build_final_job_specs(
            ROOT,
            artifact_root=args.artifact_root,
            evidence_tag=f"evidence-{commit[:8]}",
        ),
        output_dir=args.output_dir,
        preflight=preflight,
        git_commit=commit,
        relaxation_schedule=2,
        maximum_total_num_levels=954,
        num_levels_limit_source=(
            "configs/phase3_irc_cmpo_ieee123.yaml:qci.maximum_total_num_levels"
        ),
    )
    print(
        json.dumps(
            {
                "BATCH_JOB_COUNT": len(manifest["jobs"]),
                "TOY_JOB_ID": manifest["jobs"][0]["job_id"],
                "REDUCED_JOB_ID": manifest["jobs"][1]["job_id"],
                "FULL_JOB_IDS": [
                    row["job_id"] for row in manifest["jobs"] if row["name"].startswith("lambda_")
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
