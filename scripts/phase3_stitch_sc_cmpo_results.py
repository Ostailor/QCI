#!/usr/bin/env python
"""Stitch decoded SC-CMPO first-stage decisions into benchmark consensus policies."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.consensus_stitching import sc_cmpo_variable_specs, stitch_shared_first_stage  # noqa: E402
from cmpo.system_level_projection import project_sc_cmpo_payload  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read decoded SC-CMPO QCi solutions, reconcile shared first-stage decisions across public-grid "
            "patches, and write deterministic benchmark consensus artifacts."
        )
    )
    parser.add_argument(
        "--decoded-dir",
        default="results/phase3/sc_cmpo/decoded",
        help="Directory containing qci_best_solutions.csv.",
    )
    parser.add_argument("--best-solutions", default=None, help="Explicit decoded best-solution CSV path.")
    parser.add_argument(
        "--decoded-samples",
        default=None,
        help=(
            "Decoded sample CSV to select lexicographically by projected challenge metrics before stitching "
            "(default: qci_repeat_metrics.csv when present)."
        ),
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="Directory containing the original SC-CMPO payload JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/consensus",
        help="Consensus output directory.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing SC-CMPO consensus files.")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved inputs without writing consensus files.")
    return parser


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _load_payloads(payload_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(payload_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("schema", "")).startswith("cmpo.sc_cmpo"):
            payloads[path.name] = payload
    if not payloads:
        raise FileNotFoundError(f"no SC-CMPO payloads found under {payload_dir}")
    return payloads


def _parse_solution(row: Mapping[str, str], payload: Mapping[str, Any]) -> dict[str, float]:
    for column in ("repaired_solution", "decoded_variables", "raw_solution", "solution"):
        raw = row.get(column, "")
        if not raw:
            continue
        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            return {str(name): float(value) for name, value in decoded.items() if isinstance(value, (int, float))}
        if isinstance(decoded, list):
            names = [str(variable["name"]) for variable in payload["variables"]]
            return {name: float(value) for name, value in zip(names, decoded, strict=False)}
    raise ValueError("decoded row has no supported solution column")


def stitch_results(
    decoded_samples_path: Path,
    payload_dir: Path,
    output_dir: Path,
    *,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(payload_dir)
    plan = {
        "decoded_samples": str(decoded_samples_path),
        "decoded_samples_exists": decoded_samples_path.exists(),
        "payload_dir": str(payload_dir),
        "payload_count": len(payloads),
        "output_dir": str(output_dir),
    }
    if dry_run:
        return {"dry_run": True, **plan}
    if not decoded_samples_path.exists():
        raise FileNotFoundError(f"decoded SC-CMPO samples not found: {decoded_samples_path}")
    targets = (
        output_dir / "stitched_first_stage.csv",
        output_dir / "stitched_first_stage.json",
        output_dir / "consensus_dispersion.csv",
        output_dir / "selected_payload_solutions.csv",
    )
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError(f"SC-CMPO consensus outputs already exist under {output_dir}; pass --overwrite")

    candidates_by_payload: dict[str, list[dict[str, Any]]] = {}
    payload_support: dict[str, set[str]] = {}
    with decoded_samples_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            payload_name = Path(row.get("payload_name") or row.get("payload") or "").name
            payload = payloads.get(payload_name)
            if payload is None:
                continue
            benchmark = str(payload["sc_cmpo"]["public_benchmark"])
            values = _parse_solution(row, payload)
            projection = project_sc_cmpo_payload(payload, values)
            try:
                qci_energy = float(row.get("qci_energy", "nan"))
            except (TypeError, ValueError):
                qci_energy = float("nan")
            candidates_by_payload.setdefault(payload_name, []).append(
                {
                    "benchmark": benchmark,
                    "payload_name": payload_name,
                    "values": values,
                    "projection": projection,
                    "qci_energy": qci_energy,
                    "job_id": row.get("job_id", ""),
                    "repeat": row.get("repeat", ""),
                    "sample_index": row.get("sample_index", ""),
                }
            )
    missing_payloads = sorted(set(payloads) - set(candidates_by_payload))
    if missing_payloads:
        raise ValueError(f"decoded solutions are missing SC-CMPO payloads: {missing_payloads}")

    def selection_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
        projection = candidate["projection"]
        qci_energy = float(candidate["qci_energy"])
        finite_energy = qci_energy if qci_energy == qci_energy else float("inf")
        return (
            not bool(projection["feasibility_after_projection"]),
            float(projection["critical_energy_not_served_kwh"]),
            int(projection["total_hours_critical_infrastructure_unserved"]),
            float(projection["max_fraction_customers_unserved_per_hour"]),
            -float(projection["critical_load_served_fraction"]),
            float(projection["upgrade_cost"]),
            finite_energy,
        )

    selected = {name: min(candidates, key=selection_key) for name, candidates in candidates_by_payload.items()}
    rows_by_benchmark: dict[str, list[dict[str, Any]]] = {}
    selection_rows: list[dict[str, Any]] = []
    for payload_name, candidate in sorted(selected.items()):
        payload = payloads[payload_name]
        benchmark = str(candidate["benchmark"])
        shared = set(payload["sc_cmpo"]["shared_first_stage_variables"])
        rows_by_benchmark.setdefault(benchmark, []).append(
            {"values": {name: candidate["values"][name] for name in shared if name in candidate["values"]}}
        )
        payload_support.setdefault(benchmark, set()).add(payload_name)
        projection = candidate["projection"]
        selection_rows.append(
            {
                "benchmark": benchmark,
                "payload_name": payload_name,
                "job_id": candidate["job_id"],
                "repeat": candidate["repeat"],
                "sample_index": candidate["sample_index"],
                "qci_energy": candidate["qci_energy"],
                "feasibility_after_projection": projection["feasibility_after_projection"],
                "critical_energy_not_served_kwh": projection["critical_energy_not_served_kwh"],
                "total_hours_critical_infrastructure_unserved": projection[
                    "total_hours_critical_infrastructure_unserved"
                ],
                "max_fraction_customers_unserved_per_hour": projection[
                    "max_fraction_customers_unserved_per_hour"
                ],
                "critical_load_served_fraction": projection["critical_load_served_fraction"],
                "upgrade_cost": projection["upgrade_cost"],
                "selection_reason": "lexicographic projected challenge metrics, then upgrade cost, then QCi energy",
            }
        )
    missing = sorted(
        set(payload["sc_cmpo"]["public_benchmark"] for payload in payloads.values()) - set(rows_by_benchmark)
    )
    if missing:
        raise ValueError(f"decoded solutions are missing SC-CMPO benchmarks: {missing}")

    consensus: dict[str, dict[str, Any]] = {}
    value_rows: list[dict[str, Any]] = []
    dispersion_rows: list[dict[str, Any]] = []
    for benchmark in sorted(rows_by_benchmark):
        representative = next(
            payload for payload in payloads.values() if payload["sc_cmpo"]["public_benchmark"] == benchmark
        )
        result = stitch_shared_first_stage(rows_by_benchmark[benchmark], sc_cmpo_variable_specs(representative))
        result["payload_count"] = len(payload_support[benchmark])
        result["solution_count"] = len(rows_by_benchmark[benchmark])
        consensus[benchmark] = result
        for variable, value in result["stitched_values"].items():
            value_rows.append(
                {
                    "benchmark": benchmark,
                    "variable": variable,
                    "stitched_value": value,
                    "support": result["support"].get(variable, 0),
                    "payload_count": result["payload_count"],
                    "solution_count": result["solution_count"],
                }
            )
        for variable, statistics in result["dispersion"].items():
            dispersion_rows.append({"benchmark": benchmark, "variable": variable, **statistics})

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(value_rows, targets[0])
    targets[1].write_text(json.dumps(consensus, indent=2, sort_keys=True), encoding="utf-8")
    _write_csv(dispersion_rows, targets[2])
    _write_csv(selection_rows, targets[3])
    summary = {
        **plan,
        "benchmark_count": len(consensus),
        "benchmarks": sorted(consensus),
        "stitched_first_stage_csv": str(targets[0]),
        "stitched_first_stage_json": str(targets[1]),
        "consensus_dispersion_csv": str(targets[2]),
        "selected_payload_solutions_csv": str(targets[3]),
    }
    (output_dir / "stitch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    decoded_dir = Path(args.decoded_dir)
    repeat_metrics = decoded_dir / "qci_repeat_metrics.csv"
    decoded_samples = (
        Path(args.decoded_samples)
        if args.decoded_samples
        else Path(args.best_solutions)
        if args.best_solutions
        else repeat_metrics
        if repeat_metrics.exists()
        else decoded_dir / "qci_best_solutions.csv"
    )
    result = stitch_results(
        decoded_samples,
        Path(args.payload_dir),
        Path(args.output_dir),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
