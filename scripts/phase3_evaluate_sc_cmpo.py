#!/usr/bin/env python
"""Project stitched SC-CMPO decisions and evaluate held-out public N-1 outages."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.heldout_evaluation import evaluate_sc_cmpo_heldout  # noqa: E402
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402
from cmpo.system_level_projection import project_sc_cmpo_system  # noqa: E402


DEFAULT_CONFIGS = (
    Path("configs/phase3_sc_cmpo_case14.yaml"),
    Path("configs/phase3_sc_cmpo_case30.yaml"),
    Path("configs/phase3_sc_cmpo_arpae.yaml"),
    Path("configs/phase3_sc_cmpo_ieee123.yaml"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply benchmark-wide SC-CMPO consensus to every public patch, project load balance and bounds, "
            "and evaluate unused public branch N-1 contingencies."
        )
    )
    parser.add_argument("--config", action="append", default=None, help="SC-CMPO config; repeat as needed.")
    parser.add_argument(
        "--consensus-json",
        default="results/phase3/sc_cmpo/consensus/stitched_first_stage.json",
        help="Stitched benchmark consensus JSON.",
    )
    parser.add_argument(
        "--payload-dir",
        default="results/phase3/sc_cmpo/qci_payloads",
        help="SC-CMPO payload directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/evaluation",
        help="Projection and held-out evaluation output directory.",
    )
    parser.add_argument(
        "--heldout-limit",
        type=int,
        default=None,
        help="Optional deterministic per-payload cap on unused public branch outages (default: all).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing SC-CMPO evaluation files.")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved inputs without evaluating or writing.")
    return parser


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _payloads(payload_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(payload_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("schema", "")).startswith("cmpo.sc_cmpo"):
            rows.append((path.name, payload))
    if not rows:
        raise FileNotFoundError(f"no SC-CMPO payloads found under {payload_dir}")
    return rows


def _consensus_values(path: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(benchmark): dict(record.get("stitched_values", record))
        for benchmark, record in raw.items()
    }


def _summary_markdown(system_rows: list[dict[str, Any]], heldout_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# SC-CMPO Consensus Projection and Held-Out Evaluation",
        "",
        "The projection evaluates the unique-node union of selected public benchmark islands. It is an "
        "active-power adequacy and load-balance projection, not an AC OPF reproduction; unmodeled load is "
        "reported through the coverage fraction rather than assigned synthetic behavior.",
        "",
        "| Benchmark | Coverage | Critical ENS (kWh) | Critical served | Upgrade cost | Feasible |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in system_rows:
        lines.append(
            f"| {row['benchmark']} | {float(row['modeled_load_coverage_fraction']):.4f} | "
            f"{float(row['critical_energy_not_served_kwh']):.6g} | "
            f"{float(row['critical_load_served_fraction']):.4f} | "
            f"{float(row['upgrade_cost']):.6g} | {bool(row['feasibility_after_projection'])} |"
        )
    lines.extend(
        [
            "",
            "| Benchmark | Patch | Held-out N-1 | Islanding N-1 | Critical served | Feasibility rate |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in heldout_rows:
        lines.append(
            f"| {row['benchmark']} | {row['patch_id']} | {row['heldout_count']} | "
            f"{row['islanding_contingency_count']} | {float(row['critical_load_served_fraction']):.4f} | "
            f"{float(row['feasibility_rate']):.4f} |"
        )
    lines.extend(
        [
            "",
            "Held-out branch/transformer outages come only from published cases or deterministic N-1 opening of "
            "listed public components. No outage probability, load multiplier, threshold, or network value is sampled.",
            "",
        ]
    )
    return "\n".join(lines)


def evaluate(
    config_paths: list[Path],
    consensus_path: Path,
    payload_dir: Path,
    output_dir: Path,
    *,
    heldout_limit: int | None,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    named_payloads = _payloads(payload_dir)
    configs = {str(config["benchmark"]["id"]): config for config in map(load_sc_cmpo_config, config_paths)}
    plan = {
        "consensus_json": str(consensus_path),
        "consensus_exists": consensus_path.exists(),
        "payload_count": len(named_payloads),
        "benchmarks": sorted({payload["sc_cmpo"]["public_benchmark"] for _, payload in named_payloads}),
        "heldout_limit": heldout_limit,
        "output_dir": str(output_dir),
    }
    if dry_run:
        return {"dry_run": True, **plan}
    if not consensus_path.exists():
        raise FileNotFoundError(f"SC-CMPO consensus JSON not found: {consensus_path}")
    targets = {
        "payload": output_dir / "payload_projection.csv",
        "scenario": output_dir / "scenario_projection.csv",
        "system": output_dir / "system_projection.csv",
        "heldout_summary": output_dir / "heldout_summary.csv",
        "heldout_detail": output_dir / "heldout_contingencies.csv",
        "markdown": output_dir / "evaluation_summary.md",
    }
    if not overwrite and any(path.exists() for path in targets.values()):
        raise FileExistsError(f"SC-CMPO evaluation outputs already exist under {output_dir}; pass --overwrite")

    consensus = _consensus_values(consensus_path)
    system = project_sc_cmpo_system(named_payloads, consensus)
    payload_rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []
    heldout_rows: list[dict[str, Any]] = []
    heldout_details: list[dict[str, Any]] = []
    for row in system["payload_results"]:
        payload_rows.append(
            {
                key: value
                for key, value in row.items()
                if key not in {"scenario_results", "repaired_first_stage", "first_stage_adjustments"}
            }
            | {
                "repaired_first_stage_json": json.dumps(row["repaired_first_stage"], sort_keys=True),
                "first_stage_adjustments_json": json.dumps(row["first_stage_adjustments"], sort_keys=True),
            }
        )
        for scenario in row["scenario_results"]:
            scenario_rows.append(
                {
                    "payload_name": row["payload_name"],
                    "benchmark": row["benchmark"],
                    "patch_id": row["patch_id"],
                    **{key: value for key, value in scenario.items() if key != "projected_recourse"},
                    "projected_recourse_json": json.dumps(scenario["projected_recourse"], sort_keys=True),
                }
            )

    grids = {benchmark: load_public_grid(config) for benchmark, config in configs.items()}
    for payload_name, payload in named_payloads:
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
        if benchmark not in grids:
            raise KeyError(f"no SC-CMPO public config supplied for {benchmark}")
        result = evaluate_sc_cmpo_heldout(
            grids[benchmark],
            payload,
            consensus[benchmark],
            limit=heldout_limit,
        )
        heldout_rows.append({key: value for key, value in result.items() if key != "results"} | {"payload_name": payload_name})
        heldout_details.extend(
            {"payload_name": payload_name, "benchmark": benchmark, "patch_id": result["patch_id"], **detail}
            for detail in result["results"]
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(payload_rows, targets["payload"])
    _write_csv(scenario_rows, targets["scenario"])
    _write_csv(system["benchmark_results"], targets["system"])
    _write_csv(heldout_rows, targets["heldout_summary"])
    _write_csv(heldout_details, targets["heldout_detail"])
    targets["markdown"].write_text(
        _summary_markdown(system["benchmark_results"], heldout_rows),
        encoding="utf-8",
    )
    summary = {
        **plan,
        "system_projection_csv": str(targets["system"]),
        "heldout_summary_csv": str(targets["heldout_summary"]),
        "evaluation_summary_md": str(targets["markdown"]),
    }
    (output_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    config_paths = [Path(path) for path in args.config] if args.config else list(DEFAULT_CONFIGS)
    result = evaluate(
        config_paths,
        Path(args.consensus_json),
        Path(args.payload_dir),
        Path(args.output_dir),
        heldout_limit=args.heldout_limit,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
