#!/usr/bin/env python
"""Package Phase 3 tables, figures, manifests, and summaries for submission."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PHASE3_ROOT = Path("results") / "phase3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copy Phase 3 judge-facing artifacts into a submission package.")
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Print package contents without copying files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.phase3_root)
    package_dir = root / "submission_package"
    candidates = []
    for pattern in ["tables/*", "figures/*.png", "*/phase3_manifest.json", "*/comparison/phase3_comparison.md"]:
        candidates.extend(sorted(root.glob(pattern)))
    if args.dry_run:
        print(json.dumps({"files": [str(path) for path in candidates], "output_dir": str(package_dir), "dry_run": True}, indent=2))
        return
    package_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in candidates:
        target = package_dir / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(str(target))
    manifest_path = package_dir / "package_manifest.json"
    manifest_path.write_text(json.dumps({"copied": copied}, indent=2), encoding="utf-8")
    print(json.dumps({"package_dir": str(package_dir), "manifest": str(manifest_path), "file_count": len(copied)}, indent=2))


if __name__ == "__main__":
    main()
