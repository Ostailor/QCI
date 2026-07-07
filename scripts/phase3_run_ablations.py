#!/usr/bin/env python
"""Build lightweight Phase 3 ablation summaries from prepared payload metadata."""

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

from cmpo.baseline_orchestrator import load_phase3_config, phase3_output_dir, prepare_phase3_payloads  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Phase 3 ablation tables for model size and cubic-term readiness.")
    parser.add_argument("--config", default="configs/phase3_qci_small.yaml", help="Path to a Phase 3 YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Print the ablation plan without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_phase3_config(args.config)
    out_dir = phase3_output_dir(config)
    ablation_dir = out_dir / "ablations"
    plan = {"config": config["name"], "model_stats": str(out_dir / "model_stats.csv"), "output_dir": str(ablation_dir)}
    if args.dry_run:
        print(json.dumps(plan | {"dry_run": True}, indent=2))
        return
    prepare_phase3_payloads(config, dry_run=False)
    stats = pd.read_csv(out_dir / "model_stats.csv")
    rows = [
        {
            "ablation": "native_degree3",
            "max_degree": int(stats["degree"].max()),
            "max_variables": int(stats["variable_count"].max()),
            "max_terms": int(stats["term_count"].max()),
            "interpretation": "Primary CMPO payload preserving cubic terms.",
        },
        {
            "ablation": "quadratic_reduction_required",
            "max_degree": 2,
            "max_variables": int(stats["variable_count"].max()),
            "max_terms": int(stats["term_count"].max()),
            "interpretation": "Control condition requiring approximation or term reduction before non-cubic solvers.",
        },
    ]
    ablation_dir.mkdir(parents=True, exist_ok=True)
    path = ablation_dir / "ablation_summary.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    print(json.dumps({"ablation_summary": str(path)}, indent=2))


if __name__ == "__main__":
    main()
