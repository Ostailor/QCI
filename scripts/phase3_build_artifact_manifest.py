#!/usr/bin/env python
"""Build the checksum inventory for the retained Phase 3 artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/phase3/artifact_manifest.csv"
INVENTORY_PATHS = (
    Path(".gitattributes"),
    Path(".gitignore"),
    Path("README.md"),
    Path("pyproject.toml"),
    Path("requirements.txt"),
    Path("configs"),
    Path("data"),
    Path("scripts"),
    Path("src"),
    Path("submission"),
    Path("tests"),
    Path("results/README.md"),
    Path("results/phase3/README.md"),
    Path("results/phase3/irc_cmpo"),
    Path("results/phase3/sc_cmpo"),
)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", "reproduced"}
FINAL_PAPER = Path("submission/TheRestorers__Phase3_Version1.pdf")


def _is_excluded(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_PARTS or part.endswith(".pyc") for part in relative.parts):
        return True
    if relative.parts[:1] == ("submission",):
        return relative != FINAL_PAPER
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _role(path: Path) -> str:
    first = path.parts[0]
    if first == "data":
        return "public_input"
    if first == "results":
        if "qci" in path.parts:
            return "hardware_evidence"
        if "final" in path.parts:
            return "paper_result"
        return "derived_evidence"
    if first in {"scripts", "src", "tests"}:
        return "reproduction_code"
    if first == "configs":
        return "configuration"
    return "documentation"


def inventory_files(root: Path = ROOT, paths: Iterable[Path] = INVENTORY_PATHS) -> list[Path]:
    files: set[Path] = set()
    for relative in paths:
        candidate = root / relative
        if candidate.is_file():
            files.add(candidate)
            continue
        if not candidate.is_dir():
            raise FileNotFoundError(f"inventory path is missing: {relative}")
        files.update(path for path in candidate.rglob("*") if path.is_file())
    output = root / "results/phase3/artifact_manifest.csv"
    return sorted(
        path
        for path in files
        if path != output
        and not _is_excluded(root, path)
    )


def build_rows(root: Path = ROOT) -> list[dict[str, object]]:
    rows = []
    for path in inventory_files(root):
        relative = path.relative_to(root)
        rows.append(
            {
                "path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "role": _role(relative),
            }
        )
    return rows


def write_manifest(path: Path, rows: Sequence[dict[str, object]], *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"artifact manifest already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("path", "size_bytes", "sha256", "role"))
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Checksum manifest CSV path.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing checksum manifest.")
    parser.add_argument("--dry-run", action="store_true", help="Count inventory files without writing the manifest.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    rows = build_rows(ROOT)
    if not args.dry_run:
        write_manifest(output, rows, overwrite=args.overwrite)
    print(json.dumps({"output": str(output), "file_count": len(rows), "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
