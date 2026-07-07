"""ARPA-E GO public benchmark feasibility adapter helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cmpo.benchmark_registry import DATA_PUBLIC_ROOT, PHASE3_PUBLIC_ROOT


ARPAE_DATA_DIR = DATA_PUBLIC_ROOT / "arpae_go"
ARPAE_RESULT_DIR = PHASE3_PUBLIC_ROOT / "arpae_go"
ARPAE_SOURCE_URL = "https://data.openei.org/submissions/6153"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_arpae_go_files(data_dir: Path = Path("data/upstream/arpae-go")) -> list[Path]:
    if not data_dir.exists():
        return []
    suffixes = {".raw", ".con", ".rop", ".inl", ".json", ".csv", ".zip", ".gz", ".tgz", ".tar"}
    return sorted(path for path in data_dir.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def parse_raw_section_counts(path: Path) -> dict[str, int]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    sections = [
        "bus",
        "load",
        "fixed_shunt",
        "generator",
        "non_transformer_branch",
        "transformer",
        "area",
        "two_terminal_dc",
        "vsc_dc",
        "transformer_impedance",
        "multi_terminal_dc",
        "multi_section_line",
        "zone",
        "interarea",
        "owner",
        "facts",
        "switched_shunt",
        "gne",
        "induction",
    ]
    counts: dict[str, int] = {}
    section_index = 0
    count = 0
    for line in lines[3:]:
        if re.match(r"^0\s*(/.*)?$", line) and "END" in line.upper():
            if section_index < len(sections):
                counts[sections[section_index]] = count
            section_index += 1
            count = 0
        elif section_index < len(sections):
            count += 1
    return counts


def write_arpae_go_status(
    data_dir: Path = Path("data/upstream/arpae-go"),
    result_dir: Path = ARPAE_RESULT_DIR,
    public_data_dir: Path = ARPAE_DATA_DIR,
) -> dict[str, Any]:
    """Write ARPA-E GO feasibility status and provenance into benchmark-first paths."""

    result_dir.mkdir(parents=True, exist_ok=True)
    public_data_dir.mkdir(parents=True, exist_ok=True)
    files = find_arpae_go_files(data_dir)
    raw_files = [path for path in files if path.suffix.lower() == ".raw"]
    archive_files = [path for path in files if path.name.lower().endswith((".zip", ".tar.gz", ".tgz", ".tar"))]
    if not files:
        status = {
            "benchmark": "arpae_go",
            "status": "benchmark_missing",
            "source_name": "ARPA-E Grid Optimization Challenge public data",
            "upstream_url": ARPAE_SOURCE_URL,
            "missing_file": str(data_dir),
            "command": "python scripts/phase3_fetch_public_benchmarks.py --family arpae_go",
            "reason": "No ARPA-E GO raw/archive files found locally.",
        }
        (result_dir / "benchmark_missing.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    else:
        sample = raw_files[0] if raw_files else files[0]
        status = {
            "benchmark": "arpae_go",
            "status": "available",
            "source_name": "ARPA-E Grid Optimization Challenge public data",
            "upstream_url": ARPAE_SOURCE_URL,
            "license": "See OEDI dataset terms",
            "version": "OEDI public submission 6153/6197/5997 resource snapshot",
            "sha256": sha256_file(archive_files[0]) if archive_files else sha256_file(sample),
            "local_path": str(sample),
            "file_count": len(files),
            "raw_file_count": len(raw_files),
            "parsed_sample": str(sample),
            "section_counts": parse_raw_section_counts(sample) if sample.suffix.lower() == ".raw" else {},
            "qci_execution_was_run": False,
            "only_classical_baselines_were_run": False,
            "transformation_notes": "ARPA-E GO-derived microgrid stress adapter feasibility path.",
            "fields_inherited_from_benchmark": ["buses", "loads", "generators", "branches", "contingencies"],
            "fields_added_by_cmpo_adapter": [
                "critical_load_fraction",
                "BESS_capacity_and_power_limits",
                "PV_DER_profile",
                "PCC_tie_availability",
                "islanding_mode_eligibility",
                "restoration_scenario_tags",
            ],
        }
    (result_dir / "benchmark_provenance.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    with (result_dir / "benchmark_status.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(status))
        writer.writeheader()
        writer.writerow(status)
    return status
