#!/usr/bin/env python
"""Compare Phase 3 QCi and classical baseline result rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, phase3_output_dir, read_optional_csv  # noqa: E402
from cmpo.phase3_metrics import qci_repeat_distribution, summarize_phase3_results, write_phase3_metric_outputs  # noqa: E402
from cmpo.qci_result_decode import decode_qci_results  # noqa: E402
from cmpo.statistical_tests import pairwise_method_deltas  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Combine decoded QCi and baseline outputs into Phase 3 comparison tables.")
    parser.add_argument("--config", required=True, help="Path to a Phase 3 YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Print expected input/output paths without writing tables.")
    return parser


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows available._\n"
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False):
        values = [f"{value:.6g}" if isinstance(value, float) else str(value) for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = build_parser().parse_args()
    config = load_phase3_config(args.config)
    out_dir = phase3_output_dir(config)
    qci_path = out_dir / "qci_decoded" / "qci_decoded_results.csv"
    baseline_path = out_dir / "baselines" / "baseline_results.csv"
    comparison_dir = out_dir / "comparison"
    if args.dry_run:
        print(
            json.dumps(
                {
                    "qci_results": str(qci_path),
                    "baseline_results": str(baseline_path),
                    "output_dir": str(comparison_dir),
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return
    if not qci_path.exists() and (out_dir / "qci_raw" / "qci_results.jsonl").exists():
        decode_qci_results(config, dry_run=False)
    frames = [read_optional_csv(qci_path), read_optional_csv(baseline_path)]
    combined = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True)
    if combined.empty:
        raise SystemExit("No Phase 3 QCi or baseline rows found to compare.")
    comparison_dir.mkdir(parents=True, exist_ok=True)
    paths = write_phase3_metric_outputs(combined, comparison_dir)
    stats = pairwise_method_deltas(combined)
    stats_path = comparison_dir / "pairwise_cost_deltas.csv"
    stats.to_csv(stats_path, index=False)
    report_path = comparison_dir / "phase3_comparison.md"
    report_path.write_text(
        "# Phase 3 Comparison\n\n"
        "## Method Summary\n\n"
        f"{_markdown_table(summarize_phase3_results(combined))}\n"
        "## QCi Repeat Distribution\n\n"
        f"{_markdown_table(qci_repeat_distribution(combined))}\n",
        encoding="utf-8",
    )
    print(json.dumps({**{key: str(path) for key, path in paths.items()}, "pairwise_cost_deltas_csv": str(stats_path), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
