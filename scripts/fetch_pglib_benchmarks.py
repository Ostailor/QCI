#!/usr/bin/env python
"""Fetch pinned PGLib-OPF MATPOWER cases and write provenance manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.request import urlopen

VERSION = "v23.07"
COMMIT = "dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3"
LICENSE = "Creative Commons Attribution 4.0 International"
BASE_URL = f"https://raw.githubusercontent.com/power-grid-lib/pglib-opf/{VERSION}"

CASES = {
    "pglib_case14": {
        "case_file": "pglib_opf_case14_ieee.m",
        "notes": "PGLib-derived microgrid stress adapter from case14 IEEE; not an AC OPF reproduction.",
    },
    "pglib_case30": {
        "case_file": "pglib_opf_case30_ieee.m",
        "notes": "PGLib-derived microgrid stress adapter from case30 IEEE; not an AC OPF reproduction.",
    },
}


def _download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:  # noqa: S310 - pinned public benchmark URL.
        return response.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch pinned PGLib-OPF cases used by Phase 3 public adapters.")
    parser.add_argument("--case", action="append", choices=sorted(CASES), help="Case to fetch. Repeatable; defaults to all.")
    parser.add_argument("--raw-dir", default=f"data/upstream/pglib-opf/{VERSION}", help="Directory for exact upstream .m files.")
    parser.add_argument(
        "--summary",
        default="data/upstream/pglib-opf/manifest.csv",
        help="CSV summary of fetched PGLib files and checksums.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned downloads without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    selected = args.case or sorted(CASES)
    raw_dir = Path(args.raw_dir)
    summary_path = Path(args.summary)
    rows: list[dict[str, str]] = []
    if not args.dry_run:
        raw_dir.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)

    for case_name in selected:
        case = CASES[case_name]
        url = f"{BASE_URL}/{case['case_file']}"
        exact_path = raw_dir / case["case_file"]
        if args.dry_run:
            print(f"{case_name}: {url} -> {exact_path}")
            continue
        content = _download(url)
        checksum = hashlib.sha256(content).hexdigest()
        exact_path.write_bytes(content)
        rows.append(
            {
                "benchmark": case_name,
                "case_file": case["case_file"],
                "source_url": url,
                "version": VERSION,
                "license": LICENSE,
                "sha256": checksum,
                "local_path": str(exact_path),
                "transformation_notes": case["notes"],
            }
        )

    if not args.dry_run:
        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)
        print(f"fetched {len(rows)} pinned PGLib cases; summary={summary_path}")


if __name__ == "__main__":
    main()
