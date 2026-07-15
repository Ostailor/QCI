#!/usr/bin/env python
"""Project decoded hybrid QCi mode samples through the common CMPO repair stack."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import build_grid_case_from_config, load_phase3_config  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.hybrid_dispatch_projection import (  # noqa: E402
    decode_hybrid_mode_decisions,
    project_dispatch_from_hybrid_modes,
)
from cmpo.qci_fit_decomposition import BENCHMARK_CONFIGS  # noqa: E402


DEFAULT_DIR = Path("results") / "phase3" / "hybrid"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Decode hybrid QCi mode selections into repaired classical dispatch metrics. "
            "No QCi jobs are submitted by this script."
        )
    )
    parser.add_argument(
        "--qci-dir",
        default=None,
        help="Decoded hybrid QCi directory containing qci_repeat_metrics.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for projection_metrics.csv, projection_summary.csv, and projection_failures.csv.",
    )
    parser.add_argument(
        "--hybrid-dir",
        default=str(DEFAULT_DIR),
        help="Legacy build-only hybrid directory used when --qci-dir is omitted.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report available inputs without writing outputs.")
    return parser


def _decoded_metrics_path(qci_dir: Path) -> Path:
    direct = qci_dir / "qci_repeat_metrics.csv"
    return direct if direct.exists() else qci_dir / "decoded" / "qci_repeat_metrics.csv"


def _payload_context(payload: dict[str, Any], fallback_dataset: str) -> tuple[str, str, list[str], int]:
    benchmark = str(payload.get("hybrid_model", {}).get("benchmark") or fallback_dataset)
    scenario = str(payload.get("scenario_metadata", {}).get("scenario", ""))
    patch = [str(item) for item in payload.get("patch_metadata", {}).get("patch_ids", [])]
    horizon = int(payload.get("scenario_metadata", {}).get("horizon", 6))
    return benchmark, scenario, patch, horizon


def _projection_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(["dataset", "scenario", "patch"], sort=True, dropna=False):
        dataset, scenario, patch = keys
        rows.append(
            {
                "dataset": dataset,
                "scenario": scenario,
                "patch": patch,
                "sample_count": int(len(group)),
                "job_count": int(group["job_id"].nunique()),
                "feasibility_rate": float(group["feasibility_after_repair"].astype(bool).mean()),
                "critical_energy_not_served_best": float(group["critical_energy_not_served_kwh"].min()),
                "critical_energy_not_served_median": float(group["critical_energy_not_served_kwh"].median()),
                "critical_load_served_fraction_best": float(group["critical_load_served_fraction"].max()),
                "critical_load_served_fraction_median": float(group["critical_load_served_fraction"].median()),
                "max_customers_unserved_best": float(group["max_fraction_customers_unserved_per_hour"].min()),
                "risk_adjusted_cost_best": float(group["risk_adjusted_cost"].min()),
                "risk_adjusted_cost_median": float(group["risk_adjusted_cost"].median()),
                "runtime_seconds_median": float(group["runtime_seconds"].median()),
                "qci_energy_variance": float(group["qci_energy"].var(ddof=0)),
            }
        )
    return pd.DataFrame(rows)


def project_hybrid_results(qci_dir: Path, output_dir: Path, *, dry_run: bool = False) -> dict[str, Any]:
    metrics_path = _decoded_metrics_path(qci_dir)
    decoded = pd.read_csv(metrics_path) if metrics_path.exists() and metrics_path.stat().st_size else pd.DataFrame()
    plan = {
        "qci_dir": str(qci_dir),
        "decoded_metrics": str(metrics_path),
        "decoded_rows": int(len(decoded)),
        "output_dir": str(output_dir),
        "dry_run": dry_run,
    }
    if dry_run:
        return plan
    if decoded.empty:
        raise ValueError(f"No decoded hybrid QCi rows found at {metrics_path}")

    grid_cache: dict[tuple[str, int], Any] = {}
    projection_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for row in decoded.to_dict("records"):
        payload_path = Path(str(row.get("payload", "")))
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            if not str(payload.get("schema", "")).startswith("cmpo.hybrid_qci_mode_payload"):
                raise ValueError(f"not a hybrid QCi payload: {payload_path}")
            benchmark, scenario_name, patch, horizon = _payload_context(payload, str(row.get("dataset", "")))
            if benchmark not in BENCHMARK_CONFIGS:
                raise ValueError(f"unsupported hybrid benchmark context: {benchmark}")
            key = (benchmark, horizon)
            if key not in grid_cache:
                config = load_phase3_config(BENCHMARK_CONFIGS[benchmark])
                config.setdefault("dataset", {})["horizon_hours"] = horizon
                grid_cache[key] = build_grid_case_from_config(
                    config,
                    output_dir / "data" / benchmark / f"horizon_{horizon}",
                )
            grid_case = grid_cache[key]
            scenario = next(item for item in grid_case.scenarios if item.name == scenario_name)
            model, _metadata = build_scenario_hamiltonian(
                grid_case,
                scenario,
                patch,
                output_dir=output_dir,
                write_export=False,
            )
            decoded_variables = json.loads(str(row.get("decoded_variables") or row.get("raw_solution") or "{}"))
            decisions = decode_hybrid_mode_decisions(decoded_variables, payload)
            projection_started = time.perf_counter()
            projected = project_dispatch_from_hybrid_modes(
                grid_case,
                scenario,
                patch,
                decisions,
                model=model,
                payload_name=payload_path.name,
                source_payload_path=str(payload_path),
                dataset=benchmark,
            )
            projection_runtime = time.perf_counter() - projection_started
            qci_runtime = float(row.get("runtime_seconds", 0.0) or 0.0)
            projected.update(
                {
                    "job_id": row.get("job_id", ""),
                    "repeat": int(row.get("repeat", 0)),
                    "sample_index": int(row.get("sample_index", 0)),
                    "qci_energy": float(row.get("qci_energy", float("nan"))),
                    "decoded_objective": float(row.get("decoded_objective", float("nan"))),
                    "qci_runtime_seconds": qci_runtime,
                    "projection_runtime_seconds": projection_runtime,
                    "runtime_seconds": qci_runtime + projection_runtime,
                    "wall_clock_runtime_seconds": qci_runtime + projection_runtime,
                    "payload_schema": payload.get("schema", ""),
                }
            )
            projection_rows.append(projected)
        except Exception as exc:  # noqa: BLE001 - retain every failed projection.
            failure_rows.append(
                {
                    "payload": str(payload_path),
                    "job_id": row.get("job_id", ""),
                    "repeat": row.get("repeat", ""),
                    "sample_index": row.get("sample_index", ""),
                    "failure_reason": str(exc),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    projection = pd.DataFrame(projection_rows)
    failures = pd.DataFrame(
        failure_rows,
        columns=["payload", "job_id", "repeat", "sample_index", "failure_reason"],
    )
    summary = _projection_summary(projection)
    projection.to_csv(output_dir / "projection_metrics.csv", index=False)
    summary.to_csv(output_dir / "projection_summary.csv", index=False)
    failures.to_csv(output_dir / "projection_failures.csv", index=False)
    return plan | {
        "projected_rows": int(len(projection)),
        "failed_projection_rows": int(len(failures)),
        "projection_metrics": str(output_dir / "projection_metrics.csv"),
        "projection_summary": str(output_dir / "projection_summary.csv"),
        "projection_failures": str(output_dir / "projection_failures.csv"),
        "hybrid_projection_success": bool(not projection.empty and failures.empty),
    }


def main() -> None:
    args = build_parser().parse_args()
    if args.qci_dir:
        qci_dir = Path(args.qci_dir)
        output_dir = Path(args.output_dir) if args.output_dir else qci_dir.parent / "comparison"
        try:
            result = project_hybrid_results(qci_dir, output_dir, dry_run=args.dry_run)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(result, indent=2))
        return

    hybrid_dir = Path(args.hybrid_dir)
    projection_path = hybrid_dir / "projection_metrics.csv"
    projection = pd.read_csv(projection_path) if projection_path.exists() and projection_path.stat().st_size else pd.DataFrame()
    completed = projection[~projection.get("status", pd.Series(dtype=str)).astype(str).eq("not_run_build_only")]
    print(
        json.dumps(
            {
                "hybrid_dir": str(hybrid_dir),
                "projection_rows": int(len(projection)),
                "completed_projection_rows": int(len(completed)),
                "status": "ready_for_comparison" if not completed.empty else "no_completed_hybrid_projection_metrics",
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
