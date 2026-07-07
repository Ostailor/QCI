#!/usr/bin/env python
"""Select QCi repeat samples using challenge-aligned selectors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_sample_selection import (  # noqa: E402
    discover_qci_repeat_metric_paths,
    load_qci_repeat_metrics,
    select_qci_samples,
    summarize_qci_selection,
    write_qci_selection_outputs,
)


PHASE3_ROOT = Path("results") / "phase3"
OUTPUT_DIR = PHASE3_ROOT / "qci_selection"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline QCi repeat selector. Reads existing decoded qci_repeat_metrics.csv files and writes "
            "challenge-aligned selected-sample diagnostics without rerunning QCi."
        )
    )
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 outputs.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directory for QCi selection outputs.")
    parser.add_argument(
        "--repeat-metrics",
        nargs="*",
        default=None,
        help="Explicit qci_repeat_metrics.csv files. Defaults to public benchmark decoded QCi metrics.",
    )
    parser.add_argument(
        "--include-non-public",
        action="store_true",
        help="When --repeat-metrics is omitted, include all decoded QCi metrics under phase3-root, not only public benchmarks.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned inputs/outputs without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    phase3_root = Path(args.phase3_root)
    output_dir = Path(args.output_dir)
    paths = (
        [Path(item) for item in args.repeat_metrics]
        if args.repeat_metrics
        else discover_qci_repeat_metric_paths(phase3_root, include_non_public=args.include_non_public)
    )
    rows = load_qci_repeat_metrics(paths)
    selected = select_qci_samples(rows)
    summary = summarize_qci_selection(selected)
    payload = {
        "phase3_root": str(phase3_root),
        "output_dir": str(output_dir),
        "repeat_metric_inputs": [str(path) for path in paths],
        "input_rows": int(len(rows)),
        "selected_rows": int(len(selected)),
        "summary_rows": int(len(summary)),
        "dry_run": bool(args.dry_run),
        "outputs": {
            "selected_samples_csv": str(output_dir / "qci_selected_samples.csv"),
            "selection_summary_csv": str(output_dir / "qci_selection_summary.csv"),
            "selection_effect_md": str(output_dir / "qci_selection_effect.md"),
        },
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return
    paths_written = write_qci_selection_outputs(selected, summary, output_dir)
    payload["outputs"] = {key: str(value) for key, value in paths_written.items()}
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
