#!/usr/bin/env python
"""Build hybrid QCi mode-selection payloads without running QCi."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import build_grid_case_from_config, load_phase3_config  # noqa: E402
from cmpo.hybrid_dispatch_projection import ProjectionRecord  # noqa: E402
from cmpo.hybrid_mode_model import build_hybrid_mode_payload  # noqa: E402
from cmpo.qci_fit_decomposition import BENCHMARK_CONFIGS, BENCHMARK_RESULT_DIRS  # noqa: E402


DEFAULT_BENCHMARKS = ("pglib_case5_pjm", "pglib_case14_ieee", "pglib_case30_ieee")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate hybrid mode-selection QCi payloads for public benchmarks.")
    parser.add_argument("--benchmarks", nargs="+", default=list(DEFAULT_BENCHMARKS), choices=sorted(BENCHMARK_RESULT_DIRS))
    parser.add_argument("--max-variables", type=int, default=132, help="Maximum QCi variables per hybrid payload.")
    parser.add_argument("--output-dir", default="results/phase3/hybrid", help="Hybrid output directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned payload inputs without writing.")
    parser.add_argument("--no-overwrite", action="store_true", help="Keep existing output directory contents.")
    return parser


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


def build_hybrid_payloads(
    benchmarks: list[str],
    *,
    max_variables: int,
    output_dir: Path,
    dry_run: bool,
    overwrite: bool,
) -> dict[str, Any]:
    source_paths = {benchmark: sorted(_source_payload_dir(benchmark).glob("*.json")) for benchmark in benchmarks}
    if dry_run:
        return {
            "output_dir": str(output_dir),
            "benchmarks": benchmarks,
            "planned_payloads": {benchmark: len(paths) for benchmark, paths in source_paths.items()},
            "max_variables": max_variables,
            "dry_run": True,
        }
    if overwrite and output_dir.exists():
        shutil.rmtree(output_dir)
    payload_dir = output_dir / "qci_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    grids: dict[tuple[str, int], Any] = {}
    stats_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    direct_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []

    for benchmark, paths in source_paths.items():
        for source_path in paths:
            source = _load_payload(source_path)
            horizon = _horizon(source, 6)
            key = (benchmark, horizon)
            if key not in grids:
                config = _config_for_benchmark(benchmark, horizon)
                grids[key] = build_grid_case_from_config(config, output_dir / "data" / benchmark / f"horizon_{horizon}")
            grid_case = grids[key]
            scenario_name = _scenario_name(source)
            scenario = next((item for item in grid_case.scenarios if item.name == scenario_name), None)
            if scenario is None:
                raise ValueError(f"scenario {scenario_name!r} from {source_path} was not found for {benchmark}")
            patch = _patch_ids(source)
            result = build_hybrid_mode_payload(
                grid_case,
                scenario,
                patch,
                source_payload_path=str(source_path),
                source_payload_id=source_path.stem,
                max_variables=max_variables,
            )
            payload_name = f"{benchmark}__hybrid__{_safe_name(source_path.stem)}.json"
            payload_path = payload_dir / payload_name
            result.payload["hybrid_model"]["benchmark"] = benchmark
            result.payload["hybrid_model"]["payload_name"] = payload_name
            payload_path.write_text(json.dumps(result.payload, indent=2), encoding="utf-8")
            stats_rows.append(
                {
                    "payload_name": payload_name,
                    "payload_path": str(payload_path),
                    "benchmark": benchmark,
                    **result.model_stats,
                }
            )
            projection_rows.append(ProjectionRecord(payload_name, str(source_path)).to_row())
            direct_rows.append(
                {
                    "payload_name": payload_name,
                    "benchmark": benchmark,
                    "source_direct_qci_payload": str(source_path),
                    "status": "not_run_build_only",
                    "reason": "Hybrid QCi jobs and decoded projection metrics have not been run.",
                }
            )
            baseline_rows.append(
                {
                    "payload_name": payload_name,
                    "benchmark": benchmark,
                    "status": "not_run_build_only",
                    "reason": "Hybrid dispatch projection must be run before comparing with baselines.",
                }
            )

    _write_csv(stats_rows, output_dir / "model_stats.csv")
    _write_csv(projection_rows, output_dir / "projection_metrics.csv")
    _write_csv(direct_rows, output_dir / "hybrid_vs_direct_qci.csv")
    _write_csv(baseline_rows, output_dir / "hybrid_vs_baselines.csv")
    return {
        "output_dir": str(output_dir),
        "payload_count": len(stats_rows),
        "max_variables": max((int(row["variable_count"]) for row in stats_rows), default=0),
        "max_degree": max((int(row["degree"]) for row in stats_rows), default=0),
        "qci_executable": all(int(row["variable_count"]) <= max_variables and int(row["degree"]) <= 3 for row in stats_rows),
        "qci_payload_dir": str(payload_dir),
        "model_stats": str(output_dir / "model_stats.csv"),
        "projection_metrics": str(output_dir / "projection_metrics.csv"),
        "hybrid_vs_direct_qci": str(output_dir / "hybrid_vs_direct_qci.csv"),
        "hybrid_vs_baselines": str(output_dir / "hybrid_vs_baselines.csv"),
    }


def main() -> None:
    args = build_parser().parse_args()
    result = build_hybrid_payloads(
        list(args.benchmarks),
        max_variables=args.max_variables,
        output_dir=Path(args.output_dir),
        dry_run=args.dry_run,
        overwrite=not args.no_overwrite,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
