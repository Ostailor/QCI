#!/usr/bin/env python
"""Validate the Phase 3 benchmark-first ladder and print readiness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.arpae_go_adapter import write_arpae_go_status  # noqa: E402
from cmpo.benchmark_validation import (  # noqa: E402
    normalize_pglib_benchmark_outputs,
    validate_benchmark_ladder,
    write_public_benchmark_manifests,
)
from cmpo.ieee_distribution_adapter import write_distribution_bridge_and_status  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate required public benchmark outputs, provenance, final tables/figures, and QCi evidence."
    )
    parser.add_argument("--no-refresh", action="store_true", help="Do not refresh normalized benchmark manifests before validating.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable findings JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned validation steps without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "refresh": not args.no_refresh,
                    "checks": [
                        "pglib required output files",
                        "baseline suite coverage",
                        "QUBO auxiliary-variable blowup",
                        "PGLib case5 completed QCi Dirac-3 result",
                        "PGLib case14 QCi-fit payloads <=132 variables",
                        "PGLib case30 QCi-fit payloads <=132 variables",
                        "PGLib case57 QCi-fit payloads <=132 variables or decomposition failure report",
                        "QCi-fit payload degree is 3",
                        "oversize full payloads are not mislabeled as QCi-executed",
                        "ARPA-E GO parser/status",
                        "IEEE distribution bridge/status",
                        "final tables",
                        "final figures",
                    ],
                },
                indent=2,
            )
        )
        return
    if not args.no_refresh:
        normalize_pglib_benchmark_outputs()
        write_arpae_go_status(data_dir=Path("data/public_benchmarks/arpae_go"))
        write_distribution_bridge_and_status()
        write_public_benchmark_manifests()
    ok, findings = validate_benchmark_ladder()
    status = "YES" if ok else "NO"
    if args.json:
        print(json.dumps({"ready": ok, "findings": findings}, indent=2))
    else:
        print(f"BENCHMARK-FIRST PHASE 3 READY: {status}")
        if findings:
            print("Remaining blockers/findings:")
            for item in findings:
                print(f"- [{item['severity']}] {item['benchmark']} {item['requirement']}: {item['message']}")
        else:
            print("All benchmark-first acceptance checks passed.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
