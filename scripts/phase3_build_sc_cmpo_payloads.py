#!/usr/bin/env python
"""Build public-data Scenario-Coupled Consensus CMPO payloads without QCi execution."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.scenario_coupled_model import (  # noqa: E402
    build_sc_cmpo_from_config,
    load_sc_cmpo_config,
    payload_json,
)
from cmpo.upgrade_planning import sha256_file  # noqa: E402


DEFAULT_CONFIGS = (
    Path("configs/phase3_sc_cmpo_case14.yaml"),
    Path("configs/phase3_sc_cmpo_case30.yaml"),
    Path("configs/phase3_sc_cmpo_arpae.yaml"),
    Path("configs/phase3_sc_cmpo_ieee123.yaml"),
)
DEFAULT_OUTPUT_DIR = Path("results/phase3/sc_cmpo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build normalized <=132-variable degree-3 SC-CMPO payloads from pinned public PGLib, "
            "ARPA-E GO, and IEEE 123 inputs. This script never submits QCi jobs."
        )
    )
    parser.add_argument(
        "--config",
        action="append",
        default=None,
        help="SC-CMPO YAML config; repeat for multiple families (default: all four public configs).",
    )
    parser.add_argument(
        "--benchmark",
        action="append",
        default=None,
        help="Only build matching benchmark id/family; repeat to select multiple benchmarks.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="SC-CMPO result directory.")
    parser.add_argument("--overwrite", action="store_true", help="Replace only the existing SC-CMPO output tree.")
    parser.add_argument("--dry-run", action="store_true", help="Validate sources and print the planned build without writing.")
    return parser


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {
                key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list, tuple)) else value
                for key, value in row.items()
            }
            for row in rows
        )


def merge_public_provenance(
    source_path: Path,
    destination_path: Path,
    *,
    benchmark: str,
) -> None:
    """Replace one benchmark's rows in the consolidated public provenance table."""

    incoming = list(csv.DictReader(source_path.open(newline="", encoding="utf-8")))
    retained: list[dict[str, Any]] = []
    if destination_path.is_file():
        with destination_path.open(newline="", encoding="utf-8") as handle:
            retained = [row for row in csv.DictReader(handle) if row.get("benchmark") != benchmark]
    rows = retained + incoming
    rows.sort(key=lambda row: (str(row.get("benchmark", "")), str(row.get("source_role", ""))))
    _write_csv(rows, destination_path)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _selected_configs(config_paths: list[Path], benchmark_filters: list[str] | None) -> list[tuple[Path, dict[str, Any]]]:
    selected: list[tuple[Path, dict[str, Any]]] = []
    filters = set(benchmark_filters or [])
    for path in config_paths:
        config = load_sc_cmpo_config(path)
        benchmark = str(config["benchmark"]["id"])
        family = str(config["benchmark"]["family"])
        if filters and benchmark not in filters and family not in filters:
            continue
        selected.append((path, config))
    if not selected:
        raise ValueError("no SC-CMPO configs matched the requested benchmark filters")
    return selected


def _provenance_rows(config_path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    source = config["source"]
    benchmark = str(config["benchmark"]["id"])
    source_digest = str(source["sha256"]).removeprefix("sha256:")
    local_source_digest = sha256_file(source["local_path"])
    if source_digest != local_source_digest:
        raise ValueError(
            f"checksum mismatch for exact public source {source['local_path']}: "
            f"expected {source_digest}, got {local_source_digest}"
        )
    rows = [
        {
            "benchmark": benchmark,
            "source_role": "grid_topology_load_generation",
            "source_name": benchmark,
            "source_url": str(source["url"]),
            "version": str(source["version"]),
            "license": str(source["license"]),
            "sha256": source_digest,
            "local_path": str(source["local_path"]),
            "local_sha256": local_source_digest,
            "checksum_scope": "exact vendored public source; sha256 equals local_sha256",
            "transformation": str(source["transformation"]),
            "config_path": str(config_path),
        }
    ]
    auxiliary = (
        ("contingency_path", "contingency_sha256", "published_contingencies"),
        ("cost_path", "cost_sha256", "published_generator_costs"),
        ("inl_path", "inl_sha256", "published_generator_response_limits"),
        ("load_path", "load_sha256", "published_feeder_loads"),
        ("regulator_path", "regulator_sha256", "published_feeder_regulators"),
        ("switch_path", "switch_sha256", "published_feeder_switches"),
        ("linecode_path", "linecode_sha256", "published_line_impedances"),
        ("license_path", "license_sha256", "source_license_text"),
    )
    for path_key, checksum_key, role in auxiliary:
        if path_key not in source:
            continue
        expected_digest = str(source[checksum_key]).removeprefix("sha256:")
        local_digest = sha256_file(source[path_key])
        if expected_digest != local_digest:
            raise ValueError(
                f"checksum mismatch for exact public source {source[path_key]}: "
                f"expected {expected_digest}, got {local_digest}"
            )
        rows.append(
            {
                "benchmark": benchmark,
                "source_role": role,
                "source_name": Path(source[path_key]).name,
                "source_url": str(source["url"]),
                "version": str(source["version"]),
                "license": str(source["license"]),
                "sha256": expected_digest,
                "local_path": str(source[path_key]),
                "local_sha256": local_digest,
                "checksum_scope": "exact vendored public source; sha256 equals local_sha256",
                "transformation": str(source["transformation"]),
                "config_path": str(config_path),
            }
        )
    cost_manifest = json.loads(Path(config["cost_catalog"]["manifest_path"]).read_text(encoding="utf-8"))
    cost_path = str(config["cost_catalog"]["local_path"])
    rows.append(
        {
            "benchmark": benchmark,
            "source_role": "upgrade_costs",
            "source_name": str(cost_manifest["name"]),
            "source_url": str(cost_manifest["data_url"]),
            "version": str(cost_manifest["version"]),
            "license": str(cost_manifest["license"]),
            "sha256": str(cost_manifest["full_source_sha256"]),
            "local_path": cost_path,
            "local_sha256": sha256_file(cost_path),
            "checksum_scope": (
                "sha256 covers the full upstream ATB source; local_sha256 covers the documented "
                "selected-row derived artifact"
            ),
            "transformation": str(cost_manifest["transformation"]),
            "config_path": str(config_path),
        }
    )
    return rows


def build_sc_cmpo_artifacts(
    config_paths: list[Path],
    output_dir: Path,
    *,
    benchmark_filters: list[str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build payloads plus all provenance and coupling manifests."""

    selected = _selected_configs(config_paths, benchmark_filters)
    planned = {
        str(config["benchmark"]["id"]): {
            "config": str(path),
            "source": str(config["source"]["local_path"]),
            "source_exists": Path(config["source"]["local_path"]).exists(),
            "scenario_count": len(config["model"]["scenarios"]),
            "patch_count": int(config["model"].get("patch_count", 1)),
        }
        for path, config in selected
    }
    if dry_run:
        provenance = [row for path, config in selected for row in _provenance_rows(path, config)]
        return {
            "dry_run": True,
            "output_dir": str(output_dir),
            "planned": planned,
            "provenance_rows_checked": len(provenance),
            "all_local_sources_present": all(Path(row["local_path"]).is_file() for row in provenance),
            "qci_was_run": False,
        }
    existing_artifacts = output_dir.exists() and any(output_dir.iterdir())
    if existing_artifacts and not overwrite:
        raise FileExistsError(f"{output_dir} already contains SC-CMPO artifacts; pass --overwrite to replace only this tree")
    if overwrite and output_dir.exists():
        shutil.rmtree(output_dir)
    payload_dir = output_dir / "qci_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    payload_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    upgrade_rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    payload_lists: dict[str, list[str]] = {}
    for config_path, config in selected:
        benchmark = str(config["benchmark"]["id"])
        results = build_sc_cmpo_from_config(config_path)
        provenance_rows.extend(_provenance_rows(config_path, config))
        for result in results:
            payload = result.payload
            stats = payload["model_statistics"]
            sc_cmpo = payload["sc_cmpo"]
            patch = result.upgrade_plan.patch
            payload_name = f"{_safe_name(benchmark)}__{_safe_name(patch.patch_id)}.json"
            payload_path = payload_dir / payload_name
            payload_path.write_text(payload_json(result), encoding="utf-8")
            payload_lists.setdefault(benchmark, []).append(str(payload_path))
            payload_rows.append(
                {
                    "payload_name": payload_name,
                    "payload_path": str(payload_path),
                    "benchmark": benchmark,
                    "benchmark_family": str(config["benchmark"]["family"]),
                    "patch_id": patch.patch_id,
                    "patch_ids": json.dumps(patch.node_ids),
                    "scenario_count": sc_cmpo["scenario_count"],
                    "scenarios": json.dumps(sc_cmpo["scenario_names"]),
                    "variable_count": stats["variable_count"],
                    "degree": stats["degree"],
                    "term_count": stats["term_count"],
                    "shared_first_stage_variable_count": sc_cmpo["shared_first_stage_variable_count"],
                    "recourse_variable_count": sc_cmpo["recourse_variable_count"],
                    "islanded_load_kw": patch.load_kw,
                    "existing_generation_kw": patch.existing_generation_kw,
                    "islanded_deficit_kw": patch.islanded_deficit_kw,
                    "minimum_resilient_upgrade_cost": result.upgrade_plan.minimum_resilient_upgrade_cost,
                    "maximum_upgrade_cost": result.upgrade_plan.maximum_upgrade_cost,
                    "bounded": True,
                    "normalized": True,
                    "qci_executable": stats["variable_count"] <= 132 and stats["degree"] <= 3,
                    "qci_executed": False,
                    "qci_execution_status": "not_run_build_only",
                    "qci_executable_reason": sc_cmpo["qci_executable_reason"],
                }
            )
            stats_rows.append(
                {
                    "payload_name": payload_name,
                    "benchmark": benchmark,
                    **stats,
                    "scenario_count": sc_cmpo["scenario_count"],
                    "shared_first_stage_variable_count": sc_cmpo["shared_first_stage_variable_count"],
                    "recourse_variable_count": sc_cmpo["recourse_variable_count"],
                    "pre_normalization_max_abs_coefficient": result.pre_normalization_max_abs_coefficient,
                    "post_normalization_max_abs_coefficient": payload["scaling_information"][
                        "post_normalization_max_abs_coefficient"
                    ],
                }
            )
            for option in result.upgrade_plan.options:
                upgrade_rows.append(
                    {
                        "payload_name": payload_name,
                        "benchmark": benchmark,
                        "patch_id": patch.patch_id,
                        "islanded_deficit_kw": patch.islanded_deficit_kw,
                        "minimum_resilient_upgrade_cost": result.upgrade_plan.minimum_resilient_upgrade_cost,
                        "maximum_upgrade_cost": result.upgrade_plan.maximum_upgrade_cost,
                        **asdict(option),
                    }
                )
            for scenario in result.scenarios:
                scenario_rows.append(
                    {
                        "payload_name": payload_name,
                        "benchmark": benchmark,
                        "patch_id": patch.patch_id,
                        "shared_first_stage_variables": json.dumps(sc_cmpo["shared_first_stage_variables"]),
                        **asdict(scenario),
                    }
                )
    for benchmark, paths in payload_lists.items():
        (output_dir / f"{benchmark}_payloads.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")
    _write_csv(payload_rows, output_dir / "payload_manifest.csv")
    _write_csv(stats_rows, output_dir / "model_stats.csv")
    _write_csv(upgrade_rows, output_dir / "upgrade_options.csv")
    _write_csv(scenario_rows, output_dir / "scenario_coupling_manifest.csv")
    unique_provenance = {tuple(sorted(row.items())): row for row in provenance_rows}
    consolidated_provenance = list(unique_provenance.values())
    _write_csv(consolidated_provenance, output_dir / "provenance_manifest.csv")
    _write_csv(consolidated_provenance, output_dir / "public_benchmark_provenance.csv")
    commands = [
        (
            "python scripts/phase3_run_qci.py "
            f"--config {next(path for path, config in selected if config['benchmark']['id'] == benchmark)} "
            f"--payload-list {output_dir / f'{benchmark}_payloads.txt'} "
            f"--output-dir {output_dir / 'qci' / benchmark} --repeats 30"
        )
        for benchmark in sorted(payload_lists)
    ]
    summary = {
        "output_dir": str(output_dir),
        "payload_count": len(payload_rows),
        "payload_count_by_benchmark": {
            benchmark: sum(row["benchmark"] == benchmark for row in payload_rows) for benchmark in sorted(payload_lists)
        },
        "scenarios_per_payload": sorted({int(row["scenario_count"]) for row in payload_rows}),
        "max_variables": max(int(row["variable_count"]) for row in payload_rows),
        "max_degree": max(int(row["degree"]) for row in payload_rows),
        "shared_first_stage_variable_count": sorted(
            {int(row["shared_first_stage_variable_count"]) for row in payload_rows}
        ),
        "recourse_variable_count": sorted({int(row["recourse_variable_count"]) for row in payload_rows}),
        "minimum_upgrade_cost": min(float(row["minimum_resilient_upgrade_cost"]) for row in payload_rows),
        "maximum_upgrade_cost": max(float(row["maximum_upgrade_cost"]) for row in payload_rows),
        "all_challenge_stages_represented": all(
            set(config["model"]["challenge_stages"])
            == {"upgrade_planning", "pre_event_preparedness", "emergency_response", "restoration"}
            for _, config in selected
        ),
        "qci_was_run": False,
        "qci_run_commands": commands,
    }
    (output_dir / "build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    config_paths = [Path(path) for path in args.config] if args.config else list(DEFAULT_CONFIGS)
    result = build_sc_cmpo_artifacts(
        config_paths,
        Path(args.output_dir),
        benchmark_filters=args.benchmark,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
