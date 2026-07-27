#!/usr/bin/env python
"""Fetch or verify the pinned public inputs used by the final Phase 3 experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family",
        action="append",
        choices=("pglib", "arpae_go", "ieee123", "all"),
        help="Family to fetch or verify; repeatable and defaults to all.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace downloaded PGLib/ARPA-E files and ARPA-E extraction output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and checksum checks without writing files.",
    )
    return parser


def _selected(values: list[str] | None) -> set[str]:
    if not values or "all" in values:
        return {"pglib", "arpae_go", "ieee123"}
    return set(values)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_ieee123() -> dict[str, object]:
    manifest_path = ROOT / "data/upstream/ieee123/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked = []
    for row in manifest["files"]:
        path = ROOT / row["local_path"]
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned IEEE 123 input: {path}")
        actual = _sha256(path)
        if actual != row["sha256"]:
            raise ValueError(f"IEEE 123 checksum mismatch for {path}")
        checked.append(row["local_path"])
    return {"status": "verified", "files": checked, "manifest": str(manifest_path.relative_to(ROOT))}


def main() -> None:
    args = build_parser().parse_args()
    selected = _selected(args.family)
    output: dict[str, object] = {"dry_run": args.dry_run}

    if "pglib" in selected:
        command = [
            sys.executable,
            "scripts/fetch_pglib_benchmarks.py",
            "--raw-dir",
            "data/upstream/pglib-opf/v23.07",
            "--summary",
            "data/upstream/pglib-opf/manifest.csv",
        ]
        if args.dry_run:
            command.append("--dry-run")
        subprocess.run(command, cwd=ROOT, check=True)
        output["pglib"] = "planned" if args.dry_run else "downloaded_and_checksum_recorded"

    if "arpae_go" in selected:
        command = [
            sys.executable,
            "scripts/phase3_check_arpae_go.py",
            "--data-dir",
            "data/upstream/arpae-go",
            "--report",
            "results/phase3/reproduced/public_data/arpae_go_feasibility.md",
            "--instructions",
            "data/README_ARPAE_GO.md",
        ]
        if args.overwrite:
            command.append("--overwrite")
        if args.dry_run:
            command.append("--dry-run")
        subprocess.run(command, cwd=ROOT, check=True)
        output["arpae_go"] = "planned" if args.dry_run else "available_and_extracted"

    if "ieee123" in selected:
        output["ieee123"] = (
            {"status": "planned", "manifest": "data/upstream/ieee123/manifest.json"}
            if args.dry_run
            else _verify_ieee123()
        )

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
