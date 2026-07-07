#!/usr/bin/env python
"""Build and normalize Phase 3 public benchmark payload artifacts."""

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
from cmpo.baseline_orchestrator import load_phase3_config, prepare_phase3_payloads  # noqa: E402
from cmpo.benchmark_validation import normalize_pglib_benchmark_outputs, write_public_benchmark_manifests  # noqa: E402
from cmpo.ieee_distribution_adapter import write_distribution_bridge_and_status  # noqa: E402


CONFIGS = {
    "pglib_case5_pjm": "configs/phase3_pglib_case5.yaml",
    "pglib_case14_ieee": "configs/phase3_pglib_case14.yaml",
    "pglib_case30_ieee": "configs/phase3_pglib_case30.yaml",
    "pglib_case57_ieee": "configs/phase3_pglib_case57.yaml",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CMPO payload JSONs for public-benchmark-derived Phase 3 cases.")
    parser.add_argument(
        "--suite",
        default="pglib_case5_pjm,pglib_case14_ieee,pglib_case30_ieee,pglib_case57_ieee,arpae_go,ieee_distribution",
        help="Comma-separated benchmark keys to build/check.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned build actions without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    selected = [item.strip() for item in args.suite.split(",") if item.strip()]
    outputs: dict[str, object] = {"dry_run": args.dry_run}
    for key in selected:
        if key in CONFIGS:
            config = load_phase3_config(CONFIGS[key])
            outputs[key] = prepare_phase3_payloads(config, dry_run=args.dry_run)
        elif key == "arpae_go":
            outputs[key] = "write ARPA-E GO status" if args.dry_run else write_arpae_go_status(data_dir=Path("data/public_benchmarks/arpae_go"))
        elif key == "ieee_distribution":
            outputs[key] = "write IEEE distribution bridge/status" if args.dry_run else write_distribution_bridge_and_status()
        else:
            raise SystemExit(f"unknown benchmark key: {key}")
    if not args.dry_run:
        outputs["normalized_pglib_outputs"] = normalize_pglib_benchmark_outputs()
        outputs["manifest_paths"] = write_public_benchmark_manifests()
    print(json.dumps(outputs, indent=2, default=str))


if __name__ == "__main__":
    main()
