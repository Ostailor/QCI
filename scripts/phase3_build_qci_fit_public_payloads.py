#!/usr/bin/env python
"""Build QCi-fit decomposed public benchmark payloads without running QCi."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.benchmark_validation import normalize_pglib_benchmark_outputs, write_public_benchmark_manifests  # noqa: E402
from cmpo.qci_fit_decomposition import (  # noqa: E402
    BENCHMARK_RESULT_DIRS,
    DEFAULT_MAX_DEGREE,
    DEFAULT_MAX_VARIABLES,
    DecompositionSettings,
    build_qci_fit_payloads,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate <=max-variable QCi-fit decompositions linked to full public benchmark payloads."
    )
    parser.add_argument("--benchmark", required=True, choices=sorted(BENCHMARK_RESULT_DIRS), help="Public benchmark key.")
    parser.add_argument("--max-variables", type=int, default=DEFAULT_MAX_VARIABLES, help="Maximum QCi variables per payload.")
    parser.add_argument("--max-degree", type=int, default=DEFAULT_MAX_DEGREE, help="Maximum polynomial degree per payload.")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic seed override.")
    parser.add_argument(
        "--scenario-filter",
        default="all",
        help="Scenario filter: all, hardest, or a comma-separated list such as pcc_failure,demand_surge.",
    )
    parser.add_argument("--max-scenarios", type=int, default=None, help="Limit hardest scenario names when --scenario-filter hardest.")
    parser.add_argument("--rolling-horizon", type=int, default=None, help="Optional maximum rolling horizon to try.")
    parser.add_argument("--output-dir", default=None, help="Override qci_fit payload output directory.")
    parser.add_argument("--no-overwrite", action="store_true", help="Do not clear existing qci_fit payloads first.")
    parser.add_argument("--dry-run", action="store_true", help="Print decomposition plan without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = DecompositionSettings(
        benchmark=args.benchmark,
        max_variables=args.max_variables,
        max_degree=args.max_degree,
        seed=args.seed,
        scenario_filter=args.scenario_filter,
        max_scenarios=args.max_scenarios,
        rolling_horizon=args.rolling_horizon,
    )
    result = build_qci_fit_payloads(
        settings,
        output_dir=None if args.output_dir is None else Path(args.output_dir),
        overwrite=not args.no_overwrite,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        normalize_pglib_benchmark_outputs()
        write_public_benchmark_manifests()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
