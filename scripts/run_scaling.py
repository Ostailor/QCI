#!/usr/bin/env python
"""Generate CMPO Phase 2 scaling and Phase 3 resource evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baselines import GreedyCriticalLoadFirst, RandomRestartPolynomialSearch, SLSQPDispatchOptimizer, DifferentialEvolutionOptimizer  # noqa: E402
from cmpo.config import DatasetConfig, ExperimentConfig, OutputConfig, SolverConfig  # noqa: E402
from cmpo.data import generate_synthetic_dataset  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.microgrid_design import generate_candidate_patches  # noqa: E402


DEFAULT_SCENARIO_COUNTS = (2, 4, 8, 12)
DEFAULT_HORIZONS = (4, 6)
DEFAULT_MICROGRIDS = (3, 4)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CMPO scaling evidence study.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--quick", action="store_true", help="Run a smaller subset for fast local verification.")
    parser.add_argument("--include-de", action="store_true", help="Include differential evolution beyond tiny cases.")
    return parser


def _case_grid(args: argparse.Namespace):
    if args.quick:
        return ((2,), (4,), (3,))
    return (DEFAULT_SCENARIO_COUNTS, DEFAULT_HORIZONS, DEFAULT_MICROGRIDS)


def _optimizers(config: ExperimentConfig, include_de: bool, tiny_case: bool):
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=config.solver.max_iterations),
        RandomRestartPolynomialSearch(n_restarts=config.solver.random_restarts, local_steps=1),
    ]
    if include_de or tiny_case:
        optimizers.append(DifferentialEvolutionOptimizer(maxiter=1, popsize=1))
    return optimizers


def _summarize_case(records: list[dict], n_scenarios: int, n_microgrids: int, horizon: int, variable_count: int, term_count: int, payload_count: int):
    frame = pd.DataFrame(records)
    rows = []
    for method, group in frame.groupby("method_name", sort=True):
        rows.append(
            {
                "n_scenarios": n_scenarios,
                "n_microgrids": n_microgrids,
                "horizon": horizon,
                "method": method,
                "expected_cost": float(group["expected_cost_component"].mean()),
                "critical_load_served_fraction": float(group["critical_load_served_fraction"].mean()),
                "critical_energy_not_served_kwh": float(group["critical_energy_not_served_kwh"].sum()),
                "feasibility_rate": float(group["feasibility_pass"].mean()),
                "median_runtime_seconds": float(group["runtime_seconds"].median()),
                "variable_count_per_hamiltonian": variable_count,
                "term_count_per_hamiltonian": term_count,
                "payload_count": payload_count,
            }
        )
    return rows


def _write_plots(scaling: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "scenario_scaling": figures_dir / "scenario_scaling.png",
        "runtime_scaling": figures_dir / "runtime_scaling.png",
    }

    fig, ax = plt.subplots(figsize=(9, 5))
    for method, group in scaling.groupby("method"):
        ordered = group.sort_values(["n_microgrids", "horizon", "n_scenarios"])
        labels = [f"{row.n_microgrids}MG-{row.horizon}h-{row.n_scenarios}s" for row in ordered.itertuples()]
        ax.plot(labels, ordered["expected_cost"], marker="o", label=method)
    ax.set_title("Scenario Scaling Cost")
    ax.set_ylabel("Expected cost")
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["scenario_scaling"], dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    for method, group in scaling.groupby("method"):
        ordered = group.sort_values(["n_microgrids", "horizon", "n_scenarios"])
        labels = [f"{row.n_microgrids}MG-{row.horizon}h-{row.n_scenarios}s" for row in ordered.itertuples()]
        ax.plot(labels, ordered["median_runtime_seconds"], marker="o", label=method)
    ax.set_title("Runtime Scaling")
    ax.set_ylabel("Median runtime seconds")
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["runtime_scaling"], dpi=160)
    plt.close(fig)
    return paths


def _write_resource_estimate(scaling: pd.DataFrame, output_dir: Path) -> Path:
    max_payloads = int(scaling["payload_count"].max()) if not scaling.empty else 0
    max_variables = int(scaling["variable_count_per_hamiltonian"].max()) if not scaling.empty else 0
    max_terms = int(scaling["term_count_per_hamiltonian"].max()) if not scaling.empty else 0
    typical_patch_size = "1-3 microgrids"
    text = f"""# Phase 3 Resource Estimate

## QCi Dirac-3 Jobs Needed

The scaling study estimates one Dirac-3 job per scenario/patch Hamiltonian. The largest evaluated case generated `{max_payloads}` payloads, so Phase 3 should budget at least that many jobs per full benchmark sweep before repeats.

## Repeats Per Scenario/Patch

Because the target solver path is stochastic, each scenario/patch should use repeated samples. A starting plan is 10-30 repeats per payload, with the same repeat budget used for the pre-QCi polynomial search proxy.

## Expected Patch Sizes

Expected patch sizes are {typical_patch_size}. The largest Hamiltonian observed here has `{max_variables}` variables and `{max_terms}` polynomial terms.

## Quasi-Continuous Encoding Need

Generation, battery charge/discharge, SOC, PCC import/export, and load shedding are naturally bounded continuous quantities. Quasi-continuous encoding preserves this physical meaning without forcing a large binary expansion during Phase 2/3 handoff.

## Integer/Discrete Encoding Opportunity

Mode and islanding decisions may benefit from integer or discrete encoding in Phase 3 because grid, islanded, and restoration states are operationally categorical even though Phase 2 uses quasi-continuous simplex variables.

## Fair Classical Comparison

Classical baselines will be rerun with the same synthetic data, scenario set, patch set, repeat budgets, random seeds, repair logic, and metric aggregation used for QCi payload evaluation.
"""
    path = output_dir / "phase3_resource_estimate.md"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    scenario_counts, horizons, microgrid_counts = _case_grid(args)
    all_rows: list[dict] = []
    for n_microgrids in microgrid_counts:
        for horizon in horizons:
            case_config = DatasetConfig(seed=args.seed, n_microgrids=n_microgrids, horizon_hours=horizon)
            solver_config = SolverConfig(max_iterations=3 if args.quick else 8, random_restarts=2 if args.quick else 3)
            experiment_config = ExperimentConfig(dataset=case_config, solver=solver_config, output=OutputConfig(results_dir=output_dir, data_dir=data_dir))
            grid_case = generate_synthetic_dataset(case_config, output_dir=data_dir)
            patch = generate_candidate_patches(grid_case, max_patch_size=1)[0]
            for n_scenarios in scenario_counts:
                selected_scenarios = grid_case.scenarios[: min(n_scenarios, len(grid_case.scenarios))]
                records: list[dict] = []
                variable_counts: list[int] = []
                term_counts: list[int] = []
                payload_count = 0
                tiny_case = n_microgrids == min(DEFAULT_MICROGRIDS) and horizon == min(DEFAULT_HORIZONS) and n_scenarios <= 2
                optimizers = _optimizers(experiment_config, args.include_de, tiny_case)
                for scenario in selected_scenarios:
                    model, _metadata = build_scenario_hamiltonian(
                        grid_case,
                        scenario,
                        patch,
                        output_dir=output_dir,
                        write_export=False,
                    )
                    payload_count += 1
                    variable_counts.append(model.variable_count())
                    term_counts.append(model.term_count())
                    for optimizer in optimizers:
                        records.append(optimizer.run(grid_case, scenario, patch, model, experiment_config).to_dict())
                all_rows.extend(
                    _summarize_case(
                        records,
                        n_scenarios=len(selected_scenarios),
                        n_microgrids=n_microgrids,
                        horizon=horizon,
                        variable_count=max(variable_counts),
                        term_count=max(term_counts),
                        payload_count=payload_count,
                    )
                )

    scaling = pd.DataFrame(all_rows)
    scaling_path = output_dir / "scaling_results.csv"
    scaling.to_csv(scaling_path, index=False)
    figures = _write_plots(scaling, output_dir)
    estimate_path = _write_resource_estimate(scaling, output_dir)
    print("Scaling study complete")
    print(f"Wrote scaling results to {scaling_path}")
    print(f"Wrote figures to {figures['scenario_scaling']} and {figures['runtime_scaling']}")
    print(f"Wrote Phase 3 estimate to {estimate_path}")


if __name__ == "__main__":
    main()
