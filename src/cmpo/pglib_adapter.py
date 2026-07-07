"""PGLib public-benchmark adapter facade for Phase 3."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from cmpo.benchmarks import PGLIB_CASES, build_pglib_microgrid_case, parse_pglib_matpower_case
from cmpo.benchmark_registry import DATA_PUBLIC_ROOT


PGLIB_PUBLIC_DATA_DIR = DATA_PUBLIC_ROOT / "pglib"
PGLIB_PROVENANCE_DIR = DATA_PUBLIC_ROOT / "provenance"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mirror_pglib_sources(
    upstream_dir: Path = Path("data/upstream/pglib-opf/v23.07"),
    public_dir: Path = PGLIB_PUBLIC_DATA_DIR,
    provenance_dir: Path = PGLIB_PROVENANCE_DIR,
) -> list[dict[str, Any]]:
    """Copy pinned PGLib source files into the benchmark-first data tree."""

    public_dir.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for key, case in PGLIB_CASES.items():
        source = upstream_dir / str(case["case_file"])
        target = public_dir / str(case["case_file"])
        if not source.exists():
            rows.append(
                {
                    "benchmark": key,
                    "status": "benchmark_missing",
                    "missing_file": str(source),
                    "command": "python scripts/phase3_fetch_public_benchmarks.py --family pglib",
                }
            )
            continue
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        parsed = parse_pglib_matpower_case(target)
        row = {
            "benchmark": key,
            "status": "available",
            "source_name": case["label"],
            "upstream_url": f"https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/{case['case_file']}",
            "license": "Creative Commons Attribution 4.0 International",
            "version": "v23.07",
            "sha256": sha256_file(target),
            "local_path": str(target),
            "bus_count": len(parsed["buses"]),
            "generator_count": len(parsed["generators"]),
            "branch_count": len(parsed["branches"]),
            "transformation_notes": "PGLib-derived microgrid resilience adapter; deterministic CMPO overlay added.",
            "fields_inherited_from_benchmark": [
                "buses",
                "loads",
                "branches",
                "generators",
                "generator_costs",
            ],
            "fields_added_by_cmpo_adapter": [
                "critical_load_fraction",
                "BESS_capacity_and_power_limits",
                "PV_DER_profile",
                "PCC_tie_availability",
                "islanding_mode_eligibility",
                "restoration_scenario_tags",
            ],
        }
        rows.append(row)
        (provenance_dir / f"{key}_provenance.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    return rows


def build_case(*args: Any, **kwargs: Any) -> Any:
    """Compatibility wrapper around the existing PGLib-to-CMPO adapter."""

    return build_pglib_microgrid_case(*args, **kwargs)
