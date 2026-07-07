#!/usr/bin/env python
"""Run Phase 3 classical baselines with a GPU-ready orchestration contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, prepare_phase3_payloads, run_classical_baseline_sweep  # noqa: E402


BENCHMARK_CONFIGS = {
    "pglib_case5": "configs/phase3_pglib_case5.yaml",
    "pglib_case5_pjm": "configs/phase3_pglib_case5.yaml",
    "pglib_case14": "configs/phase3_pglib_case14.yaml",
    "pglib_case14_ieee": "configs/phase3_pglib_case14.yaml",
    "pglib_case30": "configs/phase3_pglib_case30.yaml",
    "pglib_case30_ieee": "configs/phase3_pglib_case30.yaml",
    "pglib_case57": "configs/phase3_pglib_case57.yaml",
    "pglib_case57_ieee": "configs/phase3_pglib_case57.yaml",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run repeated Phase 3 baselines on the same payloads as QCi: greedy, SLSQP, differential evolution, "
            "CMPO-local search, optional Pyomo MILP, QUBO/quadratized search, "
            "GPU/CPU random restarts, IPOPT-or-SLSQP nonlinear dispatch, and stress reserve heuristic."
        )
    )
    parser.add_argument("--config", required=False, help="Path to a Phase 3 YAML config.")
    parser.add_argument(
        "--benchmarks",
        nargs="+",
        default=None,
        help="Public benchmark names to run, for example: pglib_case5_pjm pglib_case14_ieee pglib_case30_ieee.",
    )
    parser.add_argument("--repeats", type=int, default=50, help="Number of repeats per scenario/patch/method.")
    parser.add_argument(
        "--budget-hours",
        type=float,
        default=None,
        help="Wall-clock budget reserved for the sweep. The current local runner records this value for provenance.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the baseline sweep plan without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.benchmarks:
        outputs = {}
        for benchmark in args.benchmarks:
            config_path = BENCHMARK_CONFIGS.get(benchmark)
            if config_path is None:
                raise SystemExit(f"Unknown benchmark {benchmark!r}. Known: {', '.join(sorted(BENCHMARK_CONFIGS))}")
            config = load_phase3_config(config_path)
            config.setdefault("run_metadata", {})["requested_benchmark"] = benchmark
            if args.budget_hours is not None:
                config["run_metadata"]["budget_hours"] = args.budget_hours
            if not args.dry_run:
                prepare_phase3_payloads(config, dry_run=False)
            outputs[benchmark] = run_classical_baseline_sweep(config, repeats=args.repeats, dry_run=args.dry_run)
        print(json.dumps(outputs, indent=2))
        return
    if not args.config:
        raise SystemExit("--config is required unless --benchmarks is supplied.")
    config = load_phase3_config(args.config)
    if args.budget_hours is not None:
        config.setdefault("run_metadata", {})["budget_hours"] = args.budget_hours
    if not args.dry_run:
        prepare_phase3_payloads(config, dry_run=False)
    result = run_classical_baseline_sweep(config, repeats=args.repeats, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
