#!/usr/bin/env python
"""Finalize SC-CMPO system-level reporting artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.sc_cmpo_reporting import build_parser, finalize_sc_cmpo_reporting  # noqa: E402


def main() -> None:
    args = build_parser().parse_args()
    result = finalize_sc_cmpo_reporting(
        args.system_level_dir,
        args.payload_dir,
        args.output_dir,
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
