#!/usr/bin/env python
"""Build the ARPA-E GO public SC-CMPO benchmark path without running QCi."""

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

from cmpo.arpae_sc_cmpo_adapter import (  # noqa: E402
    build_arpae_microgrid_candidates,
    parse_arpae_sc_cmpo_case,
)
from cmpo.scenario_coupled_model import load_sc_cmpo_config  # noqa: E402
from scripts.phase3_build_sc_cmpo_payloads import (  # noqa: E402
    _write_csv,
    build_sc_cmpo_artifacts,
    merge_public_provenance,
)


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_arpae.yaml")
DEFAULT_OUTPUT = Path("results/phase3/sc_cmpo/arpae_go")
DEFAULT_PROVENANCE = Path("results/phase3/sc_cmpo/public_benchmark_provenance.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse the pinned ARPA-E GO RAW/ROP/INL/CON case, construct deterministic graph-partition "
            "microgrid candidates, and export bounded SC-CMPO payloads. This script never runs QCi."
        )
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="ARPA-E SC-CMPO YAML config.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Isolated ARPA-E artifact directory.")
    parser.add_argument(
        "--provenance",
        default=str(DEFAULT_PROVENANCE),
        help="Consolidated public benchmark provenance CSV.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace only the ARPA-E output directory.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate sources and print the planned build without writing artifacts.",
    )
    return parser


def _rows(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def build_arpae_sc_cmpo(
    config_path: Path,
    output_dir: Path,
    provenance_path: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build one source-faithful ARPA-E GO SC-CMPO family."""

    config = load_sc_cmpo_config(config_path)
    case = parse_arpae_sc_cmpo_case(config)
    candidates = build_arpae_microgrid_candidates(
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
        "source_counts": {
            "buses": len(case.buses),
            "loads": len(case.loads),
            "generators": len(case.generators),
            "generator_costs": len(case.generator_costs),
            "branches": len(case.branches),
            "transformers": len(case.transformers),
            "contingencies": len(case.grid.contingencies),
            "time_periods": len(case.time_periods),
        },
        "microgrid_candidate_rule": "deterministic connected public-topology load-deficit partitions",
        "qci_was_run": False,
    }
    if dry_run:
        return summary

    _write_csv(_rows(case.buses), output_dir / "buses.csv")
    _write_csv(_rows(case.loads), output_dir / "loads.csv")
    _write_csv(_rows(case.generators), output_dir / "generators.csv")
    _write_csv(_rows(case.generator_costs), output_dir / "generator_costs.csv")
    _write_csv(_rows(case.branches), output_dir / "branches.csv")
    _write_csv(_rows(case.transformers), output_dir / "transformers.csv")
    _write_csv(_rows(case.grid.contingencies), output_dir / "contingencies.csv")
    _write_csv(_rows(case.time_periods), output_dir / "time_periods.csv")
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
    result = build_arpae_sc_cmpo(
        Path(args.config),
        Path(args.output_dir),
        Path(args.provenance),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
