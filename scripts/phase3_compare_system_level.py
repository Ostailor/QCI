#!/usr/bin/env python
"""Project matched SC-CMPO consensus decisions and compare complete systems."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.full_system_dispatch import evaluate_full_system, evaluate_full_system_heldout  # noqa: E402
from cmpo.overlap_consensus import reconstruct_patch_values, validate_reconstructed_overlap  # noqa: E402
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402


QCI_METHOD = "QCi SC-CMPO"
DEFAULT_CONFIGS = (
    "configs/phase3_sc_cmpo_case14.yaml",
    "configs/phase3_sc_cmpo_case30.yaml",
    "configs/phase3_sc_cmpo_arpae.yaml",
    "configs/phase3_sc_cmpo_ieee123.yaml",
)
SYSTEM_COLUMNS = [
    "method",
    "benchmark",
    "consensus_replicate",
    "headline_selection",
    "total_upgrade_cost",
    "expected_operating_cost",
    "risk_adjusted_cost",
    "max_fraction_customers_unserved_per_hour",
    "total_hours_critical_infrastructure_unserved",
    "critical_energy_not_served_kwh",
    "total_energy_not_served_kwh",
    "critical_load_served_fraction",
    "full_system_feasibility",
    "consensus_iterations",
    "consensus_residual",
    "time_to_good_solution",
    "end_to_end_runtime_seconds",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate only completed SC-CMPO overlap consensuses through one common full-public-system projection. "
            "Independent patch metrics are never averaged or compared by this command."
        )
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="Directory containing SC-CMPO payload JSON files.",
    )
    parser.add_argument(
        "--consensus-manifest",
        default="results/phase3/sc_cmpo/system_level/consensus_manifest.json",
        help="Completed overlap-consensus manifest.",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=list(DEFAULT_CONFIGS),
        help="SC-CMPO public benchmark configuration files.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/system_level",
        help="Destination for matched system-level artifacts.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing system-level comparison files.")
    parser.add_argument(
        "--heldout-limit",
        type=int,
        default=10,
        help="Maximum unused public N-1 records evaluated per reconstructed system (default: 10).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without running projections.")
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


def _load_grids(config_paths: list[Path]) -> dict[str, Any]:
    grids: dict[str, Any] = {}
    for path in config_paths:
        config = load_sc_cmpo_config(path)
        grid = load_public_grid(config)
        grids[grid.benchmark] = grid
    return grids


def _write_csv(rows: list[dict[str, Any]], path: Path, empty_columns: list[str]) -> None:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        converted = dict(row)
        for key, value in list(converted.items()):
            if isinstance(value, (dict, list, tuple)):
                converted[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        flattened.append(converted)
    fieldnames = sorted({key for row in flattened for key in row}) if flattened else empty_columns
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(flattened)


def _is_qci(method: str) -> bool:
    return method == QCI_METHOD or "qci" in method.lower() or "dirac" in method.lower()


def _metric_rank_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        not bool(row["full_system_feasibility"]),
        float(row["critical_energy_not_served_kwh"]),
        float(row["total_hours_critical_infrastructure_unserved"]),
        float(row["max_fraction_customers_unserved_per_hour"]),
        -float(row["critical_load_served_fraction"]),
        float(row["risk_adjusted_cost"]),
        float(row["end_to_end_runtime_seconds"]),
    )


def _rank_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (*_metric_rank_key(row), str(row["method"]))


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "NA" if not math.isfinite(number) else f"{number:.6g}"


def _comparison_markdown(
    system_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    payload_dir: Path,
) -> str:
    lines = [
        "# SC-CMPO Matched Full-System Comparison",
        "",
        "Every row below is produced after the same public benchmark, eight-scenario set, patch decomposition, "
        "overlap consensus, and classical active-power network projection. Patch-level resilience metrics are not "
        "averaged and payload counts are not treated as performance measurements. Upgrade assets are deduplicated "
        "and charged once per reconstructed system.",
        "",
        "## System Results",
        "",
        "| Benchmark | Method | Feasible | Critical ENS (kWh) | Total ENS (kWh) | Critical served | Max unserved | Upgrade cost | Risk-adjusted cost | Consensus residual |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(system_rows, key=lambda item: (str(item["benchmark"]), _rank_key(item))):
        lines.append(
            f"| {row['benchmark']} | {row['method']} | {bool(row['full_system_feasibility'])} | "
            f"{_format_number(row['critical_energy_not_served_kwh'])} | "
            f"{_format_number(row['total_energy_not_served_kwh'])} | "
            f"{_format_number(row['critical_load_served_fraction'])} | "
            f"{_format_number(row['max_fraction_customers_unserved_per_hour'])} | "
            f"{_format_number(row['total_upgrade_cost'])} | {_format_number(row['risk_adjusted_cost'])} | "
            f"{_format_number(row['consensus_residual'])} |"
        )

    lines.extend(["", "## QCi Versus Matched Classical", ""])
    benchmarks = sorted({str(row["benchmark"]) for row in system_rows} | {str(row["benchmark"]) for row in failures})
    for benchmark in benchmarks:
        rows = [row for row in system_rows if row["benchmark"] == benchmark]
        qci = [row for row in rows if _is_qci(str(row["method"]))]
        classical = [row for row in rows if not _is_qci(str(row["method"]))]
        if not qci:
            lines.append(
                f"- `{benchmark}`: inconclusive; no complete decoded SC-CMPO QCi patch set passed consensus, so no QCi system score was produced."
            )
            continue
        best_qci = min(qci, key=_rank_key)
        best_classical = min(classical, key=_rank_key) if classical else None
        if best_classical is None:
            lines.append(f"- `{benchmark}`: QCi reconstructed, but no matched classical system result is available.")
            continue
        qci_key = _metric_rank_key(best_qci)
        classical_key = _metric_rank_key(best_classical)
        outcome = "wins" if qci_key < classical_key else "ties" if qci_key == classical_key else "loses"
        lines.append(
            f"- `{benchmark}`: QCi {outcome} lexicographically against `{best_classical['method']}` after full-system reconstruction."
        )

    lines.extend(
        [
            "",
            "## Failure Gate",
            "",
            "No metric row is written when patch coverage is incomplete, ADMM does not converge, unresolved "
            "consensus conflicts remain, scenario probabilities do not sum to one, or any scenario projection fails.",
        ]
    )
    if failures:
        for row in failures:
            lines.append(f"- `{row['benchmark']}` / `{row['method']}`: {row['failure_reason']}")
    else:
        lines.append("- No consensus or projection failures.")
    lines.extend(
        [
            "",
            "## Traceability",
            "",
            f"- Payload source: `{payload_dir}`",
            "- Patch solution IDs, consensus run IDs, projection run IDs, public source checksums, scenario probabilities, "
            "and upgrade asset source payloads are retained in the CSV artifacts.",
            "- The projection is a bounded active-power network-flow feasibility reconstruction, not an AC OPF reproduction.",
            "",
        ]
    )
    return "\n".join(lines)


def compare_system_level(
    payload_dir: Path,
    consensus_path: Path,
    config_paths: list[Path],
    output_dir: Path,
    *,
    heldout_limit: int = 10,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(payload_dir)
    if not consensus_path.exists():
        raise FileNotFoundError(f"consensus manifest not found: {consensus_path}")
    manifest = json.loads(consensus_path.read_text(encoding="utf-8"))
    grids = _load_grids(config_paths)
    payloads_by_benchmark: dict[str, dict[str, dict[str, Any]]] = {}
    for name, payload in payloads.items():
        payloads_by_benchmark.setdefault(str(payload["sc_cmpo"]["public_benchmark"]), {})[name] = payload
    missing_grids = sorted(set(payloads_by_benchmark) - set(grids))
    if missing_grids:
        raise ValueError(f"no public-grid configuration supplied for: {missing_grids}")
    plan = {
        "payload_count": len(payloads),
        "consensus_group_count": len(manifest.get("entries", [])),
        "benchmarks": sorted(payloads_by_benchmark),
        "output_dir": str(output_dir),
        "heldout_limit": heldout_limit,
    }
    if dry_run:
        return {"dry_run": True, **plan}

    targets = {
        "qci": output_dir / "qci_system_metrics.csv",
        "qci_repeats": output_dir / "qci_repeat_system_metrics.csv",
        "baseline": output_dir / "baseline_system_metrics.csv",
        "upgrade": output_dir / "upgrade_plan_comparison.csv",
        "scenario": output_dir / "scenario_results.csv",
        "comparison": output_dir / "matched_comparison.md",
        "failures": output_dir / "system_level_failures.csv",
        "heldout_summary": output_dir / "heldout_summary.csv",
        "heldout": output_dir / "heldout_contingencies.csv",
    }
    if not overwrite and any(path.exists() for path in targets.values()):
        raise FileExistsError(f"system-level outputs already exist under {output_dir}; pass --overwrite")

    system_rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []
    upgrade_rows: list[dict[str, Any]] = []
    heldout_summary_rows: list[dict[str, Any]] = []
    heldout_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        method = str(entry["method"])
        benchmark = str(entry["benchmark"])
        if entry.get("status") != "completed" or not entry.get("converged"):
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "failure_reason": "consensus gate failed; no system-level result produced",
                }
            )
            continue
        if entry.get("unresolved_conflicts"):
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "failure_reason": f"unresolved consensus conflicts: {entry['unresolved_conflicts']}",
                }
            )
            continue
        benchmark_payloads = payloads_by_benchmark[benchmark]
        try:
            patch_values = reconstruct_patch_values(benchmark_payloads, entry["consensus_values"])
            post_repair_conflicts = validate_reconstructed_overlap(benchmark_payloads, patch_values)
        except ValueError as exc:
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "failure_reason": f"post-consensus reconstruction failed: {exc}",
                }
            )
            continue
        if post_repair_conflicts:
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "failure_reason": f"post-repair overlap conflicts: {post_repair_conflicts}",
                }
            )
            continue
        result = evaluate_full_system(
            method=method,
            grid=grids[benchmark],
            payloads=benchmark_payloads,
            patch_values=patch_values,
            consensus=entry,
            patch_runtime_seconds=float(entry.get("patch_runtime_seconds", 0.0)),
        )
        if result.get("status") != "completed":
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "failure_reason": str(result.get("failure_reason", "full-system projection failed")),
                }
            )
            continue
        heldout = evaluate_full_system_heldout(
            method,
            grids[benchmark],
            benchmark_payloads,
            patch_values,
            entry,
            limit=heldout_limit,
        )
        if heldout.get("status") != "completed":
            failures.append(
                {
                    "method": method,
                    "benchmark": benchmark,
                    "consensus_replicate": entry.get("consensus_replicate", ""),
                    "failure_reason": str(
                        heldout.get("failure_reason", "held-out full-system projection failed")
                    ),
                }
            )
            continue
        row = dict(result["system_metrics"])
        row.setdefault("method", method)
        row.setdefault("benchmark", benchmark)
        row["consensus_replicate"] = str(entry.get("consensus_replicate", ""))
        row["headline_selection"] = bool(entry.get("headline_selection", False))
        row["selection_mode"] = str(entry.get("selection_mode", ""))
        row["consensus_run_id"] = str(entry.get("run_id", ""))
        row["wall_clock_budget_seconds_per_patch"] = float(
            entry.get("wall_clock_budget_seconds_per_patch", 0.0) or 0.0
        )
        row["patch_solution_artifact"] = str(entry.get("source_artifacts", []))
        row["consensus_artifact"] = str(consensus_path)
        row["scenario_artifact"] = str(targets["scenario"])
        system_rows.append(row)
        scenario_rows.extend(
            {
                "method": method,
                "benchmark": benchmark,
                "consensus_replicate": row["consensus_replicate"],
                "headline_selection": row["headline_selection"],
                **scenario,
            }
            for scenario in result["scenario_results"]
        )
        upgrade_rows.extend(
            {
                "method": method,
                "benchmark": benchmark,
                "consensus_replicate": row["consensus_replicate"],
                "headline_selection": row["headline_selection"],
                "system_trace_id": row["system_trace_id"],
                **upgrade,
            }
            for upgrade in result["upgrade_plan"]
        )
        heldout_summary_rows.append(
            {
                **heldout["heldout_summary"],
                "consensus_replicate": row["consensus_replicate"],
                "headline_selection": row["headline_selection"],
                "consensus_run_id": row["consensus_run_id"],
            }
        )
        heldout_rows.extend(
            {
                "method": method,
                "benchmark": benchmark,
                "consensus_replicate": row["consensus_replicate"],
                "headline_selection": row["headline_selection"],
                "consensus_run_id": row["consensus_run_id"],
                **contingency,
            }
            for contingency in heldout["contingency_results"]
        )

    qci_rows = [row for row in system_rows if _is_qci(str(row["method"]))]
    baseline_rows = [row for row in system_rows if not _is_qci(str(row["method"]))]
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(qci_rows, targets["qci"], SYSTEM_COLUMNS)
    _write_csv(
        [row for row in qci_rows if not bool(row.get("headline_selection", False))],
        targets["qci_repeats"],
        SYSTEM_COLUMNS,
    )
    _write_csv(baseline_rows, targets["baseline"], SYSTEM_COLUMNS)
    _write_csv(
        upgrade_rows,
        targets["upgrade"],
        ["method", "benchmark", "asset_key", "technology", "installed_cost", "source_payloads"],
    )
    _write_csv(
        scenario_rows,
        targets["scenario"],
        ["method", "benchmark", "scenario", "scenario_probability", "projection_status"],
    )
    _write_csv(failures, targets["failures"], ["method", "benchmark", "failure_reason"])
    _write_csv(
        heldout_summary_rows,
        targets["heldout_summary"],
        ["method", "benchmark", "consensus_replicate", "heldout_count"],
    )
    _write_csv(
        heldout_rows,
        targets["heldout"],
        ["method", "benchmark", "consensus_replicate", "heldout_contingency_id"],
    )
    targets["comparison"].write_text(
        _comparison_markdown(system_rows, failures, payload_dir),
        encoding="utf-8",
    )
    return {
        **plan,
        "qci_system_results": len(qci_rows),
        "baseline_system_results": len(baseline_rows),
        "suppressed_failed_results": len(failures),
        "heldout_system_results": len(heldout_summary_rows),
        "heldout_contingency_results": len(heldout_rows),
        "qci_system_metrics": str(targets["qci"]),
        "qci_repeat_system_metrics": str(targets["qci_repeats"]),
        "baseline_system_metrics": str(targets["baseline"]),
        "matched_comparison": str(targets["comparison"]),
    }


def main() -> None:
    args = build_parser().parse_args()
    result = compare_system_level(
        Path(args.payload_dir),
        Path(args.consensus_manifest),
        [Path(item) for item in args.configs],
        Path(args.output_dir),
        heldout_limit=args.heldout_limit,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
