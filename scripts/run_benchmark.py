#!/usr/bin/env python
"""Run the PGLib case5-PJM adapted benchmark through the CMPO workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baselines import GreedyCriticalLoadFirst, RandomRestartPolynomialSearch, SLSQPDispatchOptimizer  # noqa: E402
from cmpo.benchmarks import PGLIB_CASE5_PJM_PROVENANCE, build_pglib_case5_pjm_microgrid_case  # noqa: E402
from cmpo.config import DatasetConfig, ExperimentConfig, OutputConfig, SolverConfig  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.metrics import compute_phase2_metrics, write_phase2_outputs  # noqa: E402
from cmpo.microgrid_design import choose_min_cost_upgrades, generate_candidate_patches, save_design_outputs  # noqa: E402
from cmpo.plotting import write_phase2_plots  # noqa: E402
from cmpo.qci_export import export_polynomial_model_payload, model_statistics  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the benchmark CLI parser."""

    parser = argparse.ArgumentParser(description="Run the adapted PGLib case5-PJM CMPO benchmark.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--n-scenarios", type=int, default=4)
    parser.add_argument("--quick", action="store_true", help="Use lower optimizer limits.")
    parser.add_argument("--output-dir", default="results/benchmarks/pglib_case5_pjm")
    parser.add_argument("--data-dir", default="data/benchmarks")
    parser.add_argument("--skip-plots", action="store_true")
    return parser


def _benchmark_report(tables, payload_count: int) -> str:
    summary = tables["summary_metrics"]
    best = summary.sort_values("expected_operating_cost").iloc[0]
    rows = [
        "| method | expected_cost | critical_load_served | feasibility_rate | median_runtime_seconds |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.sort_values("expected_operating_cost").itertuples(index=False):
        rows.append(
            f"| {row.method_name} | {row.expected_operating_cost:.6g} | "
            f"{row.critical_load_served_fraction:.4f} | {row.feasibility_rate:.4f} | "
            f"{row.median_runtime_seconds:.6g} |"
        )

    return f"""# PGLib Case5-PJM Adapted Benchmark

## Benchmark Source

This benchmark adapts PGLib-OPF `pglib_opf_case5_pjm.m` version `{PGLIB_CASE5_PJM_PROVENANCE['upstream']['version']}` into the CMPO microgrid data contract. The upstream case is public and licensed under Creative Commons Attribution 4.0 International. The local adapter records provenance in `manifests/upstream/pglib-opf-case5-pjm.json`.

## Adaptation Scope

The adapter uses PGLib bus active loads, generator capacities, generator linear cost slopes, and branch endpoints/ratings as anchors. CMPO-specific fields such as PV, BESS, PCC limits, critical-load fractions, and upgrade options are deterministic synthetic additions. This is a benchmark-derived stress case, not an AC OPF reproduction.

## Result Table

{chr(10).join(rows)}

## Benchmark Interpretation

Best expected operating cost in this benchmark run: `{best['method_name']}` at `{best['expected_operating_cost']:.6g}` computed cost units. Payloads exported: `{payload_count}`.

## Non-Claims

This is still a CPU-only pre-QCi run. It does not claim live QCi hardware execution or quantum advantage.
"""


def main() -> None:
    """Execute the benchmark workflow and write benchmark-specific outputs."""

    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = output_dir / "qci_payloads"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)

    max_iterations = 3 if args.quick else 15
    random_restarts = 2 if args.quick else 5
    config = ExperimentConfig(
        dataset=DatasetConfig(seed=args.seed, n_microgrids=5, horizon_hours=args.horizon),
        solver=SolverConfig(max_iterations=max_iterations, random_restarts=random_restarts),
        output=OutputConfig(results_dir=output_dir, data_dir=data_dir),
    )
    grid_case = build_pglib_case5_pjm_microgrid_case(
        horizon_hours=args.horizon,
        seed=args.seed,
        scenario_count=args.n_scenarios,
        output_dir=data_dir,
    )

    candidate_patches = generate_candidate_patches(grid_case, max_patch_size=3)
    design = choose_min_cost_upgrades(grid_case, candidate_patches)
    design_paths = save_design_outputs(design, output_dir)
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=max_iterations),
        RandomRestartPolynomialSearch(n_restarts=random_restarts, local_steps=1 if args.quick else 3),
    ]

    records: list[dict] = []
    metadata_rows: list[dict] = []
    payloads: list[Path] = []
    for patch in design["selected_patches"]:
        for scenario in grid_case.scenarios:
            model, metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=output_dir, write_export=False)
            payloads.append(export_polynomial_model_payload(model, metadata, output_dir))
            metadata_rows.append(metadata | model_statistics(model))
            for optimizer in optimizers:
                records.append(optimizer.run(grid_case, scenario, patch, model, config).to_dict())

    tables = compute_phase2_metrics(grid_case, records, design_metrics=design["metrics"], model_metadata=metadata_rows)
    output_paths = write_phase2_outputs(tables, output_dir)
    figure_paths = {} if args.skip_plots else write_phase2_plots(tables, grid_case, output_dir)
    report_path = output_dir / "benchmark_report.md"
    report_path.write_text(_benchmark_report(tables, len(payloads)), encoding="utf-8")
    manifest = {
        "benchmark": "pglib_case5_pjm_adapted",
        "seed": args.seed,
        "horizon": args.horizon,
        "n_scenarios": len(grid_case.scenarios),
        "quick": args.quick,
        "selected_patches": [list(patch) for patch in design["selected_patches"]],
        "payload_count": len(payloads),
        "provenance": PGLIB_CASE5_PJM_PROVENANCE,
        "design_outputs": {key: str(path) for key, path in design_paths.items()},
        "metric_outputs": {key: str(path) for key, path in output_paths.items()},
        "figure_outputs": {key: str(path) for key, path in figure_paths.items()},
        "payloads": [str(path) for path in payloads],
    }
    (output_dir / "benchmark_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    best = tables["summary_metrics"].sort_values("expected_operating_cost").iloc[0]
    print("Benchmark run complete")
    print("Benchmark: PGLib case5-PJM adapted CMPO stress case")
    print(f"Best method by expected cost: {best['method_name']} ({best['expected_operating_cost']:.3f})")
    print(f"Payloads exported: {len(payloads)}")
    print(f"Benchmark report: {report_path}")


if __name__ == "__main__":
    main()
