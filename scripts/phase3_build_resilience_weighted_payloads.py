#!/usr/bin/env python
"""Build CMPO-V2 resilience-weighted QCi-fit payloads without running QCi."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import build_grid_case_from_config, load_phase3_config  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.hamiltonian_weights import (  # noqa: E402
    add_normalized_components,
    build_resilience_components,
    penalty_weights_from_config,
)
from cmpo.qci_export import build_polynomial_model_payload  # noqa: E402
from cmpo.qci_fit_decomposition import BENCHMARK_CONFIGS, BENCHMARK_RESULT_DIRS  # noqa: E402


DEFAULT_CONFIG = Path("configs") / "phase3_cmpo_v2_resilience.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate CMPO-V2 resilience-weighted QCi executable payloads for public benchmarks."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="CMPO-V2 resilience YAML config.")
    parser.add_argument("--output-dir", default=None, help="Override output directory from config.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned payload inputs without writing.")
    parser.add_argument("--no-overwrite", action="store_true", help="Keep existing output directory contents.")
    return parser


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _source_payload_dir(benchmark: str) -> Path:
    case_dir = BENCHMARK_RESULT_DIRS[benchmark]
    fit_dir = case_dir / "qci_fit_payloads"
    if fit_dir.exists() and any(fit_dir.glob("*.json")):
        return fit_dir
    return case_dir / "qci_payloads"


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_name(payload: dict[str, Any]) -> str:
    if "qci_fit_decomposition" in payload:
        return str(payload["qci_fit_decomposition"].get("scenario", ""))
    return str(payload.get("scenario_metadata", {}).get("scenario", ""))


def _patch_ids(payload: dict[str, Any]) -> list[str]:
    if "qci_fit_decomposition" in payload:
        return [str(item) for item in payload["qci_fit_decomposition"].get("patch_ids", [])]
    return [str(item) for item in payload.get("patch_metadata", {}).get("patch_ids", [])]


def _horizon(payload: dict[str, Any], fallback: int) -> int:
    if "qci_fit_decomposition" in payload:
        return int(payload["qci_fit_decomposition"].get("horizon", fallback))
    return int(payload.get("scenario_metadata", {}).get("horizon", fallback))


def _safe_name(value: str) -> str:
    return value.replace("/", "_").replace(" ", "_").replace("|", "-")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _config_for_benchmark(benchmark: str, horizon: int) -> dict[str, Any]:
    config = load_phase3_config(BENCHMARK_CONFIGS[benchmark])
    config.setdefault("dataset", {})["horizon_hours"] = horizon
    return config


def build_payloads(config_path: Path, output_dir: Path | None, *, dry_run: bool, overwrite: bool) -> dict[str, Any]:
    config = _read_yaml(config_path)
    out_dir = output_dir or Path(str(config.get("output_dir", "results/phase3/cmpo_v2")))
    payload_dir = out_dir / "qci_payloads"
    benchmarks = [str(item) for item in config.get("benchmarks", [])]
    max_variables = int(config.get("qci_fit", {}).get("max_variables", 132))
    max_degree = int(config.get("qci_fit", {}).get("max_degree", 3))
    source_paths = {benchmark: sorted(_source_payload_dir(benchmark).glob("*.json")) for benchmark in benchmarks}
    if dry_run:
        return {
            "config": str(config_path),
            "output_dir": str(out_dir),
            "benchmarks": benchmarks,
            "planned_payloads": {benchmark: len(paths) for benchmark, paths in source_paths.items()},
            "dry_run": True,
        }

    if overwrite and out_dir.exists():
        shutil.rmtree(out_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)

    penalty_weights = penalty_weights_from_config(config.get("weights", {}))
    resilience_weights = {str(k): float(v) for k, v in config.get("resilience_components", {}).items()}
    high_stress = {str(item) for item in config.get("high_stress_scenarios", [])}
    manifest_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    scaling_rows: list[dict[str, Any]] = []

    grids: dict[tuple[str, int], Any] = {}
    for benchmark, paths in source_paths.items():
        for source_path in paths:
            source = _load_payload(source_path)
            horizon = _horizon(source, 6)
            key = (benchmark, horizon)
            if key not in grids:
                phase_config = _config_for_benchmark(benchmark, horizon)
                grids[key] = build_grid_case_from_config(phase_config, out_dir / "data" / benchmark / f"horizon_{horizon}")
            grid_case = grids[key]
            scenario_name = _scenario_name(source)
            scenario = next((item for item in grid_case.scenarios if item.name == scenario_name), None)
            if scenario is None:
                raise ValueError(f"scenario {scenario_name!r} from {source_path} was not found for {benchmark}")
            patch = _patch_ids(source)
            model, metadata = build_scenario_hamiltonian(
                grid_case,
                scenario,
                patch,
                output_dir=out_dir,
                penalty_weights=penalty_weights,
                write_export=False,
            )
            components = build_resilience_components(
                grid_case,
                scenario,
                patch,
                high_stress_scenarios=high_stress,
            )
            reports = add_normalized_components(model, components, resilience_weights)
            model.validate_degree(max_degree)
            payload = build_polynomial_model_payload(model, metadata)
            variable_count = int(payload["model_statistics"]["variable_count"])
            degree = int(payload["model_statistics"]["degree"])
            if variable_count > max_variables:
                raise ValueError(f"{source_path} produced {variable_count} variables > {max_variables}")
            if degree > max_degree:
                raise ValueError(f"{source_path} produced degree {degree} > {max_degree}")
            payload["schema"] = "cmpo.qci_payload.v2.resilience_weighted"
            payload["cmpo_v2"] = {
                "source_benchmark": benchmark,
                "source_payload_path": str(source_path),
                "source_payload_id": source_path.stem,
                "formulation": "resilience_weighted_direct_qci",
                "new_penalty_components": sorted(components),
                "critical_shed_to_noncritical_shed_ratio": penalty_weights.critical_shed / penalty_weights.noncritical_shed,
                "component_normalization": [asdict(report) for report in reports],
                "qci_executable_reason": f"variable_count={variable_count} <= {max_variables}; degree={degree} <= {max_degree}",
            }
            payload_name = f"{benchmark}__{_safe_name(source_path.stem)}.json"
            payload_path = payload_dir / payload_name
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            manifest_rows.append(
                {
                    "payload_name": payload_name,
                    "payload_path": str(payload_path),
                    "source_benchmark": benchmark,
                    "source_payload_id": source_path.stem,
                    "source_payload_path": str(source_path),
                    "scenario": scenario.name,
                    "patch_ids": json.dumps(patch),
                    "horizon": horizon,
                    "variable_count": variable_count,
                    "term_count": int(payload["model_statistics"]["term_count"]),
                    "degree": degree,
                    "coefficient_scaling_factor": float(payload["scaling_information"]["coefficient_scaling_factor"]),
                    "contains_challenge_penalty_components": True,
                    "qci_executable": True,
                }
            )
            stats_rows.append({"payload_name": payload_name, **payload["model_statistics"]})
            for report in reports:
                scaling_rows.append({"payload_name": payload_name, "benchmark": benchmark, **asdict(report)})

    _write_csv(manifest_rows, out_dir / "payload_manifest.csv")
    _write_csv(stats_rows, out_dir / "model_stats.csv")
    _write_csv(scaling_rows, out_dir / "component_scaling_report.csv")
    return {
        "output_dir": str(out_dir),
        "payload_count": len(manifest_rows),
        "max_variables": max((int(row["variable_count"]) for row in manifest_rows), default=0),
        "max_degree": max((int(row["degree"]) for row in manifest_rows), default=0),
        "qci_executable": all(bool(row["qci_executable"]) for row in manifest_rows),
        "payload_manifest": str(out_dir / "payload_manifest.csv"),
        "model_stats": str(out_dir / "model_stats.csv"),
        "component_scaling_report": str(out_dir / "component_scaling_report.csv"),
    }


def main() -> None:
    args = build_parser().parse_args()
    result = build_payloads(
        Path(args.config),
        None if args.output_dir is None else Path(args.output_dir),
        dry_run=args.dry_run,
        overwrite=not args.no_overwrite,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
