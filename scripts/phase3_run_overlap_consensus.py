#!/usr/bin/env python
"""Reconcile overlapping SC-CMPO patch decisions before system scoring."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.overlap_consensus import run_method_consensus  # noqa: E402
from cmpo.system_level_projection import project_sc_cmpo_payload  # noqa: E402


QCI_METHOD = "QCi SC-CMPO"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select the challenge-aligned QCi headline sample and retain every complete QCi/baseline repeat, "
            "then run deterministic ADMM overlap consensus for each matched reconstruction. No system metric "
            "is emitted by this command."
        )
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="Directory containing the original SC-CMPO payload JSON files.",
    )
    parser.add_argument(
        "--baseline-patch-solutions",
        default="results/phase3/sc_cmpo/system_level/baseline_patch_solutions.csv",
        help="Matched classical patch-solution CSV.",
    )
    parser.add_argument(
        "--qci-decoded",
        action="append",
        default=None,
        help="Decoded SC-CMPO qci_repeat_metrics.csv; repeat for multiple benchmark output trees.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/system_level",
        help="System-level reconstruction workspace.",
    )
    parser.add_argument("--rho", type=float, default=1.0, help="ADMM penalty parameter.")
    parser.add_argument("--tolerance", type=float, default=1e-6, help="Primal and dual convergence tolerance.")
    parser.add_argument("--max-iterations", type=int, default=200, help="Maximum ADMM iterations.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing consensus artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve inputs without running consensus.")
    return parser


def _load_payloads(payload_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(payload_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("schema", "")).startswith("cmpo.sc_cmpo"):
            payloads[path.name] = payload
    if not payloads:
        raise FileNotFoundError(f"no SC-CMPO payloads found under {payload_dir}")
    return payloads


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _solution_values(row: Mapping[str, str], payload: Mapping[str, Any]) -> dict[str, float]:
    for column in (
        "solution_values_json",
        "repaired_solution",
        "decoded_variables",
        "raw_solution",
        "solution",
    ):
        raw = row.get(column, "")
        if not raw:
            continue
        decoded = json.loads(raw)
        if isinstance(decoded, Mapping):
            return {
                str(name): float(value)
                for name, value in decoded.items()
                if isinstance(value, (int, float)) and math.isfinite(float(value))
            }
        if isinstance(decoded, list):
            names = [str(variable["name"]) for variable in payload["variables"]]
            return {name: float(value) for name, value in zip(names, decoded, strict=False)}
    return {}


def _float(row: Mapping[str, str], column: str, default: float = math.inf) -> float:
    try:
        value = float(row.get(column, ""))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def _qci_paths(explicit: list[str] | None, root: Path) -> list[Path]:
    if explicit:
        return [Path(item) for item in explicit]
    paths = []
    for path in root.rglob("qci_repeat_metrics.csv"):
        if "system_level" not in path.parts:
            paths.append(path)
    return sorted(set(paths))


def _repeat_sort_key(row: Mapping[str, str]) -> tuple[float, float, float, str]:
    return (
        _float(row, "repeat"),
        _float(row, "sample_index"),
        _float(row, "qci_energy"),
        str(row.get("job_id", "")),
    )


def _challenge_selection_key(
    row: Mapping[str, str], payload: Mapping[str, Any]
) -> tuple[Any, ...]:
    values = _solution_values(row, payload)
    if not values:
        return (True, math.inf, math.inf, math.inf, math.inf, math.inf, *_repeat_sort_key(row))
    projection = project_sc_cmpo_payload(payload, values)
    risk_cost = _float(row, "risk_adjusted_cost", float(projection["upgrade_cost"]))
    return (
        not bool(projection["feasibility_after_projection"]),
        float(projection["critical_energy_not_served_kwh"]),
        float(projection["total_hours_critical_infrastructure_unserved"]),
        float(projection["max_fraction_customers_unserved_per_hour"]),
        -float(projection["critical_load_served_fraction"]),
        risk_cost,
        _float(row, "qci_energy"),
        *_repeat_sort_key(row),
    )


def _qci_solution_row(
    row: Mapping[str, str],
    payload_name: str,
    payload: Mapping[str, Any],
    source_artifact: str,
    *,
    consensus_replicate: str,
    headline_selection: bool,
    selection_rule: str,
) -> dict[str, Any]:
    return {
        "method": QCI_METHOD,
        "benchmark": payload["sc_cmpo"]["public_benchmark"],
        "payload_name": payload_name,
        "solution_id": (
            f"qci::{row.get('job_id', '')}::{row.get('repeat', '')}::"
            f"{row.get('sample_index', '')}::{consensus_replicate}"
        ),
        "solution_values": _solution_values(row, payload),
        "runtime_seconds": _float(row, "runtime_seconds", _float(row, "runtime", 0.0)),
        "qci_energy": _float(row, "qci_energy"),
        "decoded_objective": _float(row, "decoded_objective"),
        "job_id": row.get("job_id", ""),
        "repeat": row.get("repeat", ""),
        "sample_index": row.get("sample_index", ""),
        "source_artifact": source_artifact,
        "consensus_replicate": consensus_replicate,
        "headline_selection": headline_selection,
        "selection_rule": selection_rule,
    }


def _select_qci_rows(paths: Iterable[Path], payloads: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: dict[str, list[dict[str, str]]] = {}
    source_paths: dict[int, str] = {}
    for path in paths:
        for row in _read_rows(path):
            status = str(row.get("status", "")).lower()
            if status and "complete" not in status and "success" not in status:
                continue
            payload_name = Path(row.get("payload_name") or row.get("payload") or "").name
            if payload_name not in payloads:
                continue
            candidates.setdefault(payload_name, []).append(row)
            source_paths[id(row)] = str(path)

    selected: list[dict[str, Any]] = []
    for payload_name, rows in sorted(candidates.items()):
        payload = payloads[payload_name]
        row = min(rows, key=lambda item: _challenge_selection_key(item, payload))
        selected.append(
            _qci_solution_row(
                row,
                payload_name,
                payload,
                source_paths[id(row)],
                consensus_replicate="challenge_selected",
                headline_selection=True,
                selection_rule=(
                    "lexicographic challenge selector: feasibility, critical ENS, critical infrastructure "
                    "hours, maximum customers unserved, critical-load served, risk cost, native QCi energy"
                ),
            )
        )

    payloads_by_benchmark: dict[str, list[str]] = {}
    for payload_name, payload in payloads.items():
        payloads_by_benchmark.setdefault(
            str(payload["sc_cmpo"]["public_benchmark"]), []
        ).append(payload_name)
    for benchmark, benchmark_payload_names in sorted(payloads_by_benchmark.items()):
        if any(name not in candidates for name in benchmark_payload_names):
            continue
        ordered_candidates = {
            name: sorted(candidates[name], key=_repeat_sort_key)
            for name in benchmark_payload_names
        }
        common_count = min(len(rows) for rows in ordered_candidates.values())
        for sample_ordinal in range(common_count):
            replicate = f"qci_sample_{sample_ordinal:03d}"
            for payload_name in sorted(benchmark_payload_names):
                row = ordered_candidates[payload_name][sample_ordinal]
                selected.append(
                    _qci_solution_row(
                        row,
                        payload_name,
                        payloads[payload_name],
                        source_paths[id(row)],
                        consensus_replicate=replicate,
                        headline_selection=False,
                        selection_rule=(
                            "unselected repeat-distribution sample aligned by repeat and sample index; "
                            "no objective sorting"
                        ),
                    )
                )
    return selected


def _baseline_rows(path: Path, payloads: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _read_rows(path):
        if str(raw.get("status", "")).lower() != "completed":
            continue
        payload_name = Path(raw.get("payload_name", "")).name
        if payload_name not in payloads:
            continue
        rows.append(
            {
                **raw,
                "benchmark": raw.get("benchmark") or payloads[payload_name]["sc_cmpo"]["public_benchmark"],
                "payload_name": payload_name,
                "solution_id": raw.get("solution_id") or f"baseline::{raw.get('method', '')}::{payload_name}",
                "solution_values": _solution_values(raw, payloads[payload_name]),
                "runtime_seconds": _float(raw, "runtime_seconds", 0.0),
                "source_artifact": str(path),
                "consensus_replicate": (
                    "deterministic"
                    if str(raw.get("repeat", "deterministic")) == "deterministic"
                    else f"baseline_repeat_{int(float(raw['repeat'])):03d}"
                ),
                "headline_selection": str(raw.get("repeat", "deterministic")) == "deterministic",
                "selection_rule": "matched baseline repeat; no patch-level metric selection",
            }
        )
    return rows


def _write_csv(rows: list[dict[str, Any]], path: Path, empty_columns: list[str]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else empty_columns
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _flat_solution_row(row: Mapping[str, Any]) -> dict[str, Any]:
    flat = dict(row)
    flat["solution_values_json"] = json.dumps(flat.pop("solution_values", {}), sort_keys=True, separators=(",", ":"))
    return flat


def run_overlap_consensus(
    payload_dir: Path,
    baseline_path: Path,
    qci_decoded: list[str] | None,
    output_dir: Path,
    *,
    rho: float,
    tolerance: float,
    max_iterations: int,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(payload_dir)
    qci_paths = _qci_paths(qci_decoded, payload_dir.parent)
    plan = {
        "payload_count": len(payloads),
        "benchmark_count": len({p["sc_cmpo"]["public_benchmark"] for p in payloads.values()}),
        "baseline_patch_solutions": str(baseline_path),
        "baseline_patch_solutions_exists": baseline_path.exists(),
        "qci_decoded_paths": [str(path) for path in qci_paths],
        "output_dir": str(output_dir),
    }
    if dry_run:
        return {"dry_run": True, **plan}

    targets = {
        "convergence": output_dir / "consensus_convergence.csv",
        "values": output_dir / "consensus_values.csv",
        "qci": output_dir / "qci_patch_solutions.csv",
        "manifest": output_dir / "consensus_manifest.json",
        "failures": output_dir / "consensus_failures.csv",
    }
    if not overwrite and any(path.exists() for path in targets.values()):
        raise FileExistsError(f"consensus artifacts already exist under {output_dir}; pass --overwrite")

    qci_rows = _select_qci_rows(qci_paths, payloads)
    baseline_rows = _baseline_rows(baseline_path, payloads)
    all_rows = baseline_rows + qci_rows
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in all_rows:
        groups.setdefault(
            (
                str(row["method"]),
                str(row["benchmark"]),
                str(row["consensus_replicate"]),
            ),
            [],
        ).append(row)

    payloads_by_benchmark: dict[str, dict[str, dict[str, Any]]] = {}
    for name, payload in payloads.items():
        payloads_by_benchmark.setdefault(str(payload["sc_cmpo"]["public_benchmark"]), {})[name] = payload

    started = time.perf_counter()
    manifest_entries: list[dict[str, Any]] = []
    convergence_rows: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for (method, benchmark, consensus_replicate), rows in sorted(groups.items()):
        method_payloads = payloads_by_benchmark[benchmark]
        run_started = time.perf_counter()
        result = run_method_consensus(
            method_payloads,
            rows,
            rho=rho,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
        consensus_runtime = time.perf_counter() - run_started
        trace = result.get("convergence_trace") or result.get("trace") or []
        for trace_row in trace:
            is_final_iteration = int(trace_row.get("iteration", 0)) == int(result.get("iteration_count", 0))
            convergence_rows.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "consensus_replicate": consensus_replicate,
                    **trace_row,
                    "rho": rho,
                    "convergence_tolerance": tolerance,
                    "maximum_iterations": max_iterations,
                    "iteration_count": int(result.get("iteration_count", 0)),
                    "converged": bool(result.get("converged", False) and is_final_iteration),
                    "raw_conflict_count": int(result.get("raw_conflict_count", 0)),
                    "final_status": result["status"],
                    "unresolved_conflict_count": len(result.get("unresolved_conflicts", [])),
                }
            )
        entry = {
            "run_id": f"consensus::{benchmark}::{method}::{consensus_replicate}",
            "method": method,
            "benchmark": benchmark,
            "consensus_replicate": consensus_replicate,
            "headline_selection": any(bool(row.get("headline_selection")) for row in rows),
            "selection_mode": str(rows[0].get("selection_rule", "")),
            "status": result["status"],
            "converged": bool(result.get("converged", False)),
            "iteration_count": int(result.get("iteration_count", 0)),
            "primal_residual": result.get("primal_residual"),
            "dual_residual": result.get("dual_residual"),
            "raw_conflict_count": int(result.get("raw_conflict_count", 0)),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "post_reconstruction_conflicts": result.get("post_reconstruction_conflicts", []),
            "missing_payloads": result.get("missing_payloads", []),
            "consensus_runtime_seconds": consensus_runtime,
            "patch_runtime_seconds": sum(float(row.get("runtime_seconds", 0.0)) for row in rows),
            "wall_clock_budget_seconds_per_patch": max(
                (_float(row, "wall_clock_budget_seconds", 0.0) for row in rows),
                default=0.0,
            ),
            "patch_solution_ids": [str(row.get("solution_id", "")) for row in rows],
            "source_artifacts": sorted({str(row.get("source_artifact", "")) for row in rows}),
        }
        if result["status"] == "completed" and result.get("converged"):
            entry["consensus_values"] = result["consensus_values"]
            for key, value in sorted(result["consensus_values"].items()):
                value_rows.append(
                    {
                        "run_id": entry["run_id"],
                        "method": method,
                        "benchmark": benchmark,
                        "consensus_replicate": consensus_replicate,
                        "consensus_key": key,
                        "consensus_value": value,
                        "support": result.get("support", {}).get(key, 0),
                    }
                )
        else:
            conflicts = result.get("post_reconstruction_conflicts") or result.get("unresolved_conflicts") or []
            missing_payloads = result.get("missing_payloads", [])
            failure_reason = str(result.get("failure_reason", ""))
            if not failure_reason and conflicts:
                failure_reason = json.dumps(conflicts, sort_keys=True)
            if not failure_reason and missing_payloads:
                failure_reason = f"missing payloads: {missing_payloads}"
            if not failure_reason:
                failure_reason = "consensus did not converge"
            failure_rows.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "consensus_replicate": consensus_replicate,
                    "failure_reason": failure_reason,
                }
            )
        manifest_entries.append(entry)

    # Record absent QCi explicitly without creating a consensus or system result.
    qci_benchmarks = {str(row["benchmark"]) for row in qci_rows}
    for benchmark in sorted(payloads_by_benchmark):
        if benchmark not in qci_benchmarks:
            failure_rows.append(
                {
                    "method": QCI_METHOD,
                    "benchmark": benchmark,
                    "failure_reason": "no decoded SC-CMPO QCi patch solutions; system result intentionally suppressed",
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        convergence_rows,
        targets["convergence"],
        ["method", "benchmark", "iteration", "primal_residual", "dual_residual", "converged"],
    )
    _write_csv(value_rows, targets["values"], ["run_id", "method", "benchmark", "consensus_key", "consensus_value"])
    _write_csv(
        [_flat_solution_row(row) for row in qci_rows],
        targets["qci"],
        ["method", "benchmark", "payload_name", "solution_id", "solution_values_json"],
    )
    _write_csv(failure_rows, targets["failures"], ["method", "benchmark", "failure_reason"])
    manifest = {
        "schema": "cmpo.sc_cmpo.system_consensus.v1",
        "payload_dir": str(payload_dir),
        "baseline_patch_solutions": str(baseline_path),
        "qci_decoded_paths": [str(path) for path in qci_paths],
        "qci_selection_rule": (
            "headline selection is lexicographic challenge-aligned per payload; all complete samples are also "
            "retained as repeat-distribution consensus replicates without objective sorting"
        ),
        "consensus_algorithm": "deterministic scaled consensus ADMM with bounded final semantic projection",
        "rho": rho,
        "tolerance": tolerance,
        "max_iterations": max_iterations,
        "entries": manifest_entries,
        "runtime_seconds": time.perf_counter() - started,
    }
    targets["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        **plan,
        "method_benchmark_groups": len(manifest_entries),
        "completed_consensus_groups": sum(entry["status"] == "completed" for entry in manifest_entries),
        "failed_consensus_groups": sum(entry["status"] != "completed" for entry in manifest_entries),
        "selected_qci_patch_solutions": sum(bool(row.get("headline_selection")) for row in qci_rows),
        "qci_repeat_patch_solutions": sum(not bool(row.get("headline_selection")) for row in qci_rows),
        "qci_available": bool(qci_rows),
        "consensus_manifest": str(targets["manifest"]),
    }


def main() -> None:
    args = build_parser().parse_args()
    result = run_overlap_consensus(
        Path(args.payload_dir),
        Path(args.baseline_patch_solutions),
        args.qci_decoded,
        Path(args.output_dir),
        rho=args.rho,
        tolerance=args.tolerance,
        max_iterations=args.max_iterations,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
