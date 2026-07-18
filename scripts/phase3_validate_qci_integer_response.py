#!/usr/bin/env python
"""Validate that a QCi response is natively integer Dirac-3 output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_integer_adapter import validate_integer_response  # noqa: E402


def _num_levels(raw: str) -> list[int]:
    try:
        levels = [int(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("num levels must be comma-separated integers") from exc
    if not levels or any(level < 2 for level in levels):
        raise argparse.ArgumentTypeError("num levels must contain values >= 2")
    return levels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("response", type=Path, help="Raw QCi response JSON.")
    parser.add_argument("--num-levels", type=_num_levels, required=True, help="Declared domains, e.g. 2,2,4.")
    parser.add_argument("--output", type=Path, help="Optional validation JSON; an existing file is never overwritten.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    response = json.loads(args.response.read_text(encoding="utf-8"))
    validation = validate_integer_response(response, expected_num_levels=args.num_levels)
    report = validation.to_dict() | {"response": str(args.response)}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except FileExistsError as exc:
            raise SystemExit(f"Refusing to overwrite existing validation file: {args.output}") from exc
    print(rendered)
    return 0 if validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
