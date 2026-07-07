#!/usr/bin/env python
"""Fetch public benchmark data into the Phase 3 benchmark-first tree."""

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

from cmpo.arpae_go_adapter import write_arpae_go_status  # noqa: E402
from cmpo.ieee_distribution_adapter import write_distribution_bridge_and_status  # noqa: E402
from cmpo.pglib_adapter import mirror_pglib_sources  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Phase 3 public benchmark data and write provenance/status files.")
    parser.add_argument(
        "--family",
        action="append",
        choices=["pglib", "arpae_go", "ieee_distribution", "all"],
        help="Benchmark family to fetch/check. Repeatable; defaults to all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned fetch/check actions without writing files.")
    parser.add_argument("--overwrite", action="store_true", help="Allow public dataset downloads to overwrite local archives.")
    parser.add_argument(
        "--arpae-resource-key",
        default="challenge1_original_dataset_2",
        help="Built-in ARPA-E GO resource key to download/check.",
    )
    return parser


def _selected(raw: list[str] | None) -> set[str]:
    if not raw or "all" in raw:
        return {"pglib", "arpae_go", "ieee_distribution"}
    return set(raw)


def main() -> None:
    args = build_parser().parse_args()
    selected = _selected(args.family)
    outputs: dict[str, object] = {"dry_run": args.dry_run}

    if "pglib" in selected:
        if args.dry_run:
            outputs["pglib"] = "python scripts/fetch_pglib_benchmarks.py --raw-dir data/public_benchmarks/pglib"
        else:
            subprocess.run(
                [
                    sys.executable,
                    "scripts/fetch_pglib_benchmarks.py",
                    "--raw-dir",
                    "data/public_benchmarks/pglib",
                    "--summary",
                    "data/public_benchmarks/provenance/pglib_manifest.csv",
                ],
                check=True,
            )
            outputs["pglib"] = mirror_pglib_sources(upstream_dir=Path("data/public_benchmarks/pglib"))

    if "arpae_go" in selected:
        if args.dry_run:
            outputs["arpae_go"] = (
                "python scripts/phase3_check_arpae_go.py "
                "--data-dir data/public_benchmarks/arpae_go "
                "--report results/phase3/public_benchmarks/arpae_go/benchmark_report.md"
            )
        else:
            cmd = [
                sys.executable,
                "scripts/phase3_check_arpae_go.py",
                "--data-dir",
                "data/public_benchmarks/arpae_go",
                "--report",
                "results/phase3/public_benchmarks/arpae_go/benchmark_report.md",
                "--instructions",
                "data/README_ARPAE_GO.md",
                "--resource-key",
                args.arpae_resource_key,
            ]
            if args.overwrite:
                cmd.append("--overwrite")
            subprocess.run(cmd, check=True)
            outputs["arpae_go"] = write_arpae_go_status(data_dir=Path("data/public_benchmarks/arpae_go"))

    if "ieee_distribution" in selected:
        outputs["ieee_distribution"] = (
            "write bridge/status"
            if args.dry_run
            else write_distribution_bridge_and_status()
        )

    print(json.dumps(outputs, indent=2, default=str))


if __name__ == "__main__":
    main()
