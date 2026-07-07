#!/usr/bin/env python
"""Prepare Phase 3 QCi payloads without modifying Phase 2 outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, prepare_phase3_payloads  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Phase 3 payloads under results/phase3/ from a YAML config.")
    parser.add_argument("--config", required=True, help="Path to a Phase 3 YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned payload output locations without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_phase3_config(args.config)
    result = prepare_phase3_payloads(config, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
