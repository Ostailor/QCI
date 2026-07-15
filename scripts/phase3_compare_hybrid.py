#!/usr/bin/env python
"""Compare hybrid projection metrics after hybrid QCi decoding has been run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_DIR = Path("results") / "phase3" / "hybrid"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build hybrid comparison tables from existing projection metrics. Does not run QCi."
    )
    parser.add_argument("--hybrid-dir", default=str(DEFAULT_DIR), help="Hybrid result directory.")
    parser.add_argument("--dry-run", action="store_true", help="Report available inputs without writing outputs.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    hybrid_dir = Path(args.hybrid_dir)
    projection_path = hybrid_dir / "projection_metrics.csv"
    projection = pd.read_csv(projection_path) if projection_path.exists() and projection_path.stat().st_size else pd.DataFrame()
    completed = projection[~projection.get("status", pd.Series(dtype=str)).astype(str).eq("not_run_build_only")]
    result = {
        "hybrid_dir": str(hybrid_dir),
        "projection_rows": int(len(projection)),
        "completed_projection_rows": int(len(completed)),
        "status": "ready_for_comparison" if not completed.empty else "no_completed_hybrid_projection_metrics",
    }
    if args.dry_run:
        print(json.dumps(result, indent=2))
        return
    if completed.empty:
        print(json.dumps(result, indent=2))
        return
    # The concrete comparison is intentionally deferred until real projected
    # dispatch metrics exist; this keeps the script from inventing results.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
