#!/usr/bin/env python
"""Run classical methods on the exact SC-CMPO patch decomposition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.matched_problem_baselines import (  # noqa: E402
    ALL_MATCHED_METHODS,
    FULL_SYSTEM_REFERENCE_METHODS,
    STOCHASTIC_MATCHED_METHODS,
    solve_coordinated_reference,
    solve_matched_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run every requested classical method against the same SC-CMPO payloads, scenarios, bounds, "
            "and deterministic seeds. This command writes patch solutions only; it does not compare patch metrics."
        )
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="Directory containing SC-CMPO payload JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/system_level",
        help="System-level reconstruction workspace.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=sorted(ALL_MATCHED_METHODS),
        help="Matched baseline method labels to run (default: all required methods).",
    )
    parser.add_argument("--benchmarks", nargs="*", default=None, help="Optional benchmark IDs to include.")
    parser.add_argument("--seed", type=int, default=20260716, help="Base deterministic seed.")
    parser.add_argument(
        "--repeats",
        type=int,
        default=50,
        help="Independent repeats for stochastic methods; deterministic methods run once (default: 50).",
    )
    parser.add_argument(
        "--wall-clock-budget-seconds",
        type=float,
        default=30.0,
        help="Common per-payload solver budget recorded for every method (default: 30 seconds).",
    )
    parser.add_argument("--workers", type=int, default=1, help="Independent patch solves to run concurrently.")
    parser.add_argument("--overwrite", action="store_true", help="Replace the patch-solution CSV if it exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved solver plan without solving.")
    return parser


def _load_payloads(payload_dir: Path, benchmarks: set[str] | None) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(payload_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not str(payload.get("schema", "")).startswith("cmpo.sc_cmpo"):
            continue
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
        if benchmarks and benchmark not in benchmarks:
            continue
        payloads[path.name] = payload
    if not payloads:
        raise FileNotFoundError(f"no matching SC-CMPO payloads found under {payload_dir}")
    return payloads


def _stable_seed(base_seed: int, method: str, payload_name: str, repeat: str | int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{method}:{payload_name}:{repeat}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _csv_row(row: dict[str, Any]) -> dict[str, Any]:
    converted = dict(row)
    values = converted.pop("solution_values", {})
    converted["solution_values_json"] = json.dumps(values, sort_keys=True, separators=(",", ":"))
    for key, value in list(converted.items()):
        if isinstance(value, (dict, list, tuple)):
            converted[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return converted


def _solve_patch_task(
    task: tuple[str, str, dict[str, Any], str | int, int, float],
) -> dict[str, Any]:
    """Run one isolated patch solve; process isolation keeps Pyomo streams safe."""

    method, payload_name, payload, repeat, base_seed, wall_clock_budget_seconds = task
    row = solve_matched_payload(
        payload_name,
        payload,
        method=method,
        seed=_stable_seed(base_seed, method, payload_name, repeat),
    )
    row["repeat"] = repeat
    row["solution_id"] = f"baseline::{method}::{payload_name}::{repeat}"
    row["wall_clock_budget_seconds"] = wall_clock_budget_seconds
    return row


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_matched_baselines(
    payload_dir: Path,
    output_dir: Path,
    *,
    methods: list[str],
    benchmarks: set[str] | None,
    seed: int,
    repeats: int = 50,
    wall_clock_budget_seconds: float = 30.0,
    workers: int,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    unknown = sorted(set(methods) - set(ALL_MATCHED_METHODS))
    if unknown:
        raise ValueError(f"unknown matched baseline methods: {unknown}")
    payloads = _load_payloads(payload_dir, benchmarks)
    target = output_dir / "baseline_patch_solutions.csv"
    reference_methods = [method for method in methods if method in FULL_SYSTEM_REFERENCE_METHODS]
    patch_methods = [method for method in methods if method not in FULL_SYSTEM_REFERENCE_METHODS]
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    if wall_clock_budget_seconds <= 0:
        raise ValueError("wall-clock budget must be positive")
    tasks = [
        (method, name, payloads[name], repeat)
        for method in patch_methods
        for name in sorted(payloads)
        for repeat in (
            range(repeats) if method in STOCHASTIC_MATCHED_METHODS else ("deterministic",)
        )
    ]
    benchmark_count = len({p["sc_cmpo"]["public_benchmark"] for p in payloads.values()})
    plan = {
        "payload_count": len(payloads),
        "method_count": len(methods),
        "solver_call_count": len(tasks) + len(reference_methods) * benchmark_count,
        "solution_row_count": len(tasks) + len(reference_methods) * len(payloads),
        "methods": methods,
        "benchmarks": sorted({p["sc_cmpo"]["public_benchmark"] for p in payloads.values()}),
        "output": str(target),
        "workers": max(1, workers),
        "stochastic_repeats": repeats,
        "stochastic_methods": sorted(set(patch_methods) & set(STOCHASTIC_MATCHED_METHODS)),
        "wall_clock_budget_seconds_per_payload": wall_clock_budget_seconds,
    }
    if dry_run:
        return {"dry_run": True, **plan}
    if target.exists() and not overwrite:
        raise FileExistsError(f"matched baseline output exists: {target}; pass --overwrite")

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    process_tasks = [
        (*task, seed, wall_clock_budget_seconds)
        for task in tasks
    ]

    if workers > 1:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            futures = {
                executor.submit(_solve_patch_task, process_task): task
                for process_task, task in zip(process_tasks, tasks, strict=True)
            }
            for future in as_completed(futures):
                method, payload_name, payload, repeat = futures[future]
                try:
                    row = future.result()
                except Exception as exc:  # preserve failed methods for the reconstruction gate
                    row = {
                        "method": method,
                        "benchmark": payload["sc_cmpo"]["public_benchmark"],
                        "payload_name": payload_name,
                        "status": "failed",
                        "failure_reason": f"{type(exc).__name__}: {exc}",
                        "runtime_seconds": 0.0,
                        "repeat": repeat,
                        "solution_id": f"baseline::{method}::{payload_name}::{repeat}",
                        "wall_clock_budget_seconds": wall_clock_budget_seconds,
                        "solution_values": {},
                    }
                rows.append(row)
    else:
        for task in tasks:
            method, payload_name, payload, repeat = task
            try:
                row = _solve_patch_task(
                    (*task, seed, wall_clock_budget_seconds)
                )
            except Exception as exc:
                row = {
                    "method": method,
                    "benchmark": payload["sc_cmpo"]["public_benchmark"],
                    "payload_name": payload_name,
                    "status": "failed",
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                    "runtime_seconds": 0.0,
                    "repeat": repeat,
                    "solution_id": f"baseline::{method}::{payload_name}::{repeat}",
                    "wall_clock_budget_seconds": wall_clock_budget_seconds,
                    "solution_values": {},
                }
            rows.append(row)

    payloads_by_benchmark: dict[str, dict[str, dict[str, Any]]] = {}
    for payload_name, payload in payloads.items():
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
        payloads_by_benchmark.setdefault(benchmark, {})[payload_name] = payload
    for method in reference_methods:
        for benchmark, benchmark_payloads in sorted(payloads_by_benchmark.items()):
            reference_seed = _stable_seed(seed, method, benchmark, "deterministic")
            try:
                reference_rows = solve_coordinated_reference(benchmark_payloads, method, reference_seed)
                for row in reference_rows:
                    row["repeat"] = "deterministic"
                    row["solution_id"] = (
                        f"baseline::{method}::{row['payload_name']}::deterministic"
                    )
                    row["wall_clock_budget_seconds"] = wall_clock_budget_seconds
                rows.extend(reference_rows)
            except Exception as exc:
                for payload_name in sorted(benchmark_payloads):
                    rows.append(
                        {
                            "method": method,
                            "benchmark": benchmark,
                            "payload_name": payload_name,
                            "status": "failed",
                            "failure_reason": f"{type(exc).__name__}: {exc}",
                            "runtime_seconds": 0.0,
                            "repeat": "deterministic",
                            "solution_id": f"baseline::{method}::{payload_name}::deterministic",
                            "wall_clock_budget_seconds": wall_clock_budget_seconds,
                            "solution_values": {},
                        }
                    )

    rows.sort(
        key=lambda row: (
            str(row.get("benchmark", "")),
            str(row["method"]),
            str(row.get("repeat", "")),
            str(row["payload_name"]),
        )
    )
    _write_csv([_csv_row(row) for row in rows], target)
    summary = {
        **plan,
        "completed": sum(row.get("status") == "completed" for row in rows),
        "failed": sum(row.get("status") != "completed" for row in rows),
        "wall_clock_seconds": time.perf_counter() - started,
    }
    (output_dir / "matched_baseline_run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    result = run_matched_baselines(
        Path(args.payload_dir),
        Path(args.output_dir),
        methods=list(args.methods),
        benchmarks=set(args.benchmarks) if args.benchmarks else None,
        seed=args.seed,
        repeats=args.repeats,
        wall_clock_budget_seconds=args.wall_clock_budget_seconds,
        workers=max(1, args.workers),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
