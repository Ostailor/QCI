#!/usr/bin/env python
"""Validate and build the IEEE 123-bus public SC-CMPO benchmark path."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.ieee123_sc_cmpo_adapter import (  # noqa: E402
    build_ieee123_microgrid_candidates,
    parse_ieee123_sc_cmpo_case,
)
from cmpo.scenario_coupled_model import load_sc_cmpo_config  # noqa: E402
from scripts.phase3_build_sc_cmpo_payloads import (  # noqa: E402
    _write_csv,
    build_sc_cmpo_artifacts,
    merge_public_provenance,
)
from scripts.phase3_validate_distribution_powerflow import validate_distribution_powerflow  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123.yaml")
DEFAULT_OUTPUT = Path("results/phase3/sc_cmpo/ieee123")
DEFAULT_PROVENANCE = Path("results/phase3/sc_cmpo/public_benchmark_provenance.csv")
DEFAULT_VALIDATION = Path("results/phase3/sc_cmpo/distribution_validation.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Gate the pinned IEEE 123-bus feeder through OpenDSS, then build deterministic "
            "distribution SC-CMPO payloads. Payload generation is refused when validation fails."
        )
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="IEEE123 SC-CMPO YAML config.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Isolated IEEE123 artifact directory.")
    parser.add_argument(
        "--provenance",
        default=str(DEFAULT_PROVENANCE),
        help="Consolidated public benchmark provenance CSV.",
    )
    parser.add_argument(
        "--validation-output",
        default=str(DEFAULT_VALIDATION),
        help="Required pre-optimization OpenDSS validation report.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace only the IEEE123 output directory.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the OpenDSS gate and validate the planned build without writing artifacts.",
    )
    return parser


def _rows(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def build_ieee123_sc_cmpo(
    config_path: Path,
    output_dir: Path,
    provenance_path: Path,
    validation_markdown_path: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate and build the source-faithful IEEE123 SC-CMPO family."""

    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite and not dry_run:
        raise FileExistsError(f"{output_dir} already contains IEEE123 artifacts; pass --overwrite")
    validation = validate_distribution_powerflow(
        config_path,
        validation_markdown_path,
        dry_run=dry_run,
    )
    if not validation.get("passed"):
        raise RuntimeError("IEEE123 OpenDSS validation failed; SC-CMPO payloads were not generated")

    config = load_sc_cmpo_config(config_path)
    case = parse_ieee123_sc_cmpo_case(config)
    candidates = build_ieee123_microgrid_candidates(
        case,
        count=int(config["model"]["patch_count"]),
        patch_size=int(config["model"]["patch_size"]),
        deterministic_seed=int(config["model"]["deterministic_seed"]),
    )
    result = build_sc_cmpo_artifacts(
        [config_path],
        output_dir,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    summary = {
        **result,
        "benchmark": str(config["benchmark"]["id"]),
        "payload_count": len(candidates) if dry_run else result["payload_count"],
        "distribution_validation_passed": True,
        "distribution_validation_path": str(validation_markdown_path),
        "source_counts": {
            "buses": len(case.grid.nodes),
            "loads": len(case.loads),
            "lines": len(case.lines),
            "line_codes": len(case.line_codes),
            "transformers": len(case.transformers),
            "regulators": len(case.regulators),
            "capacitors": len(case.capacitors),
        },
        "microgrid_candidate_rule": "deterministic connected public-topology load-deficit partitions",
        "qci_was_run": False,
    }
    if dry_run:
        return summary

    _write_csv(_rows(case.grid.nodes), output_dir / "feeder_buses.csv")
    _write_csv(_rows(case.loads), output_dir / "feeder_loads.csv")
    _write_csv(_rows(case.lines), output_dir / "feeder_lines.csv")
    _write_csv(_rows(case.line_codes), output_dir / "line_codes.csv")
    _write_csv(_rows(case.transformers), output_dir / "transformers.csv")
    _write_csv(_rows(case.regulators), output_dir / "regulators.csv")
    _write_csv(_rows(case.capacitors), output_dir / "capacitors.csv")
    _write_csv(_rows(candidates), output_dir / "microgrid_candidates.csv")
    (output_dir / "adapter_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    merge_public_provenance(
        output_dir / "provenance_manifest.csv",
        provenance_path,
        benchmark=str(config["benchmark"]["id"]),
    )
    return summary


def main() -> None:
    args = build_parser().parse_args()
    result = build_ieee123_sc_cmpo(
        Path(args.config),
        Path(args.output_dir),
        Path(args.provenance),
        Path(args.validation_output),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
