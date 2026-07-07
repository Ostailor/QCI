#!/usr/bin/env python
"""Run Phase 3 public benchmark payload and baseline sweeps."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, prepare_phase3_payloads, run_classical_baseline_sweep  # noqa: E402
from cmpo.benchmark_validation import normalize_pglib_benchmark_outputs, write_public_benchmark_manifests  # noqa: E402

DEFAULT_CONFIGS = {
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
    parser = argparse.ArgumentParser(description="Prepare and run Phase 3 public benchmark baselines.")
    parser.add_argument(
        "--suite",
        default="pglib_case5,pglib_case14,pglib_case30,pglib_case57",
        help="Comma-separated public benchmark suite names.",
    )
    parser.add_argument("--repeats", type=int, default=10, help="Baseline repeats per benchmark.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned benchmark runs without writing files.")
    return parser


def _write_benchmark_manifest(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = build_parser().parse_args()
    outputs = []
    for name in [item.strip() for item in args.suite.split(",") if item.strip()]:
        if name not in DEFAULT_CONFIGS:
            raise SystemExit(f"unknown benchmark suite item: {name}")
        config = load_phase3_config(DEFAULT_CONFIGS[name])
        prepare = prepare_phase3_payloads(config, dry_run=args.dry_run)
        baselines = run_classical_baseline_sweep(config, repeats=args.repeats, dry_run=args.dry_run)
        outputs.append({"benchmark": name, "prepare": prepare, "baselines": baselines})
    if not args.dry_run:
        manifest_rows = []
        for output in outputs:
            prepare = output["prepare"]
            baselines = output["baselines"]
            manifest_rows.append(
                {
                    "benchmark": output["benchmark"],
                    "output_dir": prepare.get("output_dir", ""),
                    "payload_dir": prepare.get("payload_dir", ""),
                    "payload_count": prepare.get("payload_count", 0),
                    "selected_patches": json.dumps(prepare.get("selected_patches", [])),
                    "scenario_count": prepare.get("scenario_count", 0),
                    "repeat_metrics": baselines.get("repeat_metrics", ""),
                    "payload_summary": baselines.get("payload_summary", ""),
                    "baseline_summary": baselines.get("summary_path", ""),
                    "skip_report": baselines.get("skip_report", ""),
                    "baseline_rows": baselines.get("rows", 0),
                    "baseline_skips": baselines.get("skipped", 0),
                    "description": "PGLib-derived microgrid stress adapter; not an AC OPF reproduction.",
                }
            )
        _write_benchmark_manifest(manifest_rows, Path("results/phase3/public_benchmarks/benchmark_manifest.csv"))
        normalize_pglib_benchmark_outputs()
        write_public_benchmark_manifests()
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
