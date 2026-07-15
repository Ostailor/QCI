#!/usr/bin/env python
"""Decode raw Phase 3 QCi results into repaired CMPO metric rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, phase3_output_dir  # noqa: E402
from cmpo.qci_result_decode import decode_qci_experiment  # noqa: E402


PUBLIC_BENCHMARKS = {
    "pglib_case5_pjm": {
        "config": "configs/phase3_pglib_case5.yaml",
        "experiment_dir": "results/phase3/public_benchmarks/pglib_case5_pjm",
    },
    "pglib_case14_ieee": {
        "config": "configs/phase3_pglib_case14.yaml",
        "experiment_dir": "results/phase3/public_benchmarks/pglib_case14_ieee",
    },
    "pglib_case30_ieee": {
        "config": "configs/phase3_pglib_case30.yaml",
        "experiment_dir": "results/phase3/public_benchmarks/pglib_case30_ieee",
    },
    "pglib_case57_ieee": {
        "config": "configs/phase3_pglib_case57.yaml",
        "experiment_dir": "results/phase3/public_benchmarks/pglib_case57_ieee",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Decode raw QCi Dirac-3 Phase 3 JSON responses, map vectors back to CMPO variables, "
            "apply Phase 2 repair logic, and write repaired repeat metrics."
        )
    )
    parser.add_argument("--config", required=False, help="Path to a Phase 3 YAML config.")
    parser.add_argument(
        "--all-public-benchmarks",
        action="store_true",
        help="Decode every public benchmark QCi directory that exists under results/phase3/public_benchmarks.",
    )
    parser.add_argument(
        "--experiment-dir",
        default=None,
        help="Phase 3 experiment directory containing qci/raw JSON or qci/<payload>/repeat_*/response.json. Defaults to the config output_dir.",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Explicit QCi input directory containing response JSON files, including qci/<payload>/repeat_*/response.json layouts.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Explicit decoded output directory. Defaults to <experiment-dir>/decoded.",
    )
    parser.add_argument(
        "--payload-manifest",
        default=None,
        help="Optional payload_manifest.json mapping response payload names to original CMPO payload JSON files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the decode plan without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.all_public_benchmarks:
        outputs = {}
        for benchmark, spec in PUBLIC_BENCHMARKS.items():
            experiment_dir = Path(spec["experiment_dir"])
            if not (experiment_dir / "qci").exists():
                outputs[benchmark] = {"skipped": True, "reason": f"No QCi directory found at {experiment_dir / 'qci'}"}
                continue
            config = load_phase3_config(spec["config"])
            outputs[benchmark] = decode_qci_experiment(
                experiment_dir=experiment_dir,
                config=config,
                input_dir=None if args.input_dir is None else Path(args.input_dir),
                output_dir=None if args.output_dir is None else Path(args.output_dir),
                payload_manifest=None if args.payload_manifest is None else Path(args.payload_manifest),
                dry_run=args.dry_run,
            )
        print(json.dumps(outputs, indent=2))
        return
    if not args.config and not args.input_dir:
        raise SystemExit("--config is required unless --all-public-benchmarks or --input-dir is supplied.")
    config = load_phase3_config(args.config) if args.config else None
    if args.experiment_dir:
        experiment_dir = Path(args.experiment_dir)
    elif args.input_dir:
        input_path = Path(args.input_dir)
        experiment_dir = input_path.parent if input_path.name in {"qci", "raw"} else input_path
    else:
        experiment_dir = phase3_output_dir(config or {})
    print(
        json.dumps(
            decode_qci_experiment(
                experiment_dir=experiment_dir,
                config=config,
                input_dir=None if args.input_dir is None else Path(args.input_dir),
                output_dir=None if args.output_dir is None else Path(args.output_dir),
                payload_manifest=None if args.payload_manifest is None else Path(args.payload_manifest),
                dry_run=args.dry_run,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
