#!/usr/bin/env python
"""One-command reproduction workflow for CMPO Phase 2 evidence."""

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

from cmpo.baselines import (  # noqa: E402
    DifferentialEvolutionOptimizer,
    GreedyCriticalLoadFirst,
    RandomRestartPolynomialSearch,
    SLSQPDispatchOptimizer,
)
from cmpo.config import DatasetConfig, ExperimentConfig, OutputConfig, SolverConfig  # noqa: E402
from cmpo.data import generate_synthetic_dataset  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.metrics import compute_phase2_metrics, write_phase2_outputs  # noqa: E402
from cmpo.microgrid_design import generate_candidate_patches, choose_min_cost_upgrades, save_design_outputs  # noqa: E402
from cmpo.plotting import write_phase2_plots  # noqa: E402
from cmpo.qci_export import export_polynomial_model_payload, model_statistics  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the judge-facing reproduction CLI."""

    parser = argparse.ArgumentParser(description="Run the full CMPO Phase 2 evidence pipeline.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-microgrids", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=6, help="Dispatch horizon in hours.")
    parser.add_argument("--n-scenarios", type=int, default=8, help="Number of generated scenarios to evaluate.")
    parser.add_argument("--quick", action="store_true", help="Use laptop-friendly optimizer limits and skip differential evolution.")
    parser.add_argument("--output-dir", default="results", help="Directory for reports, plots, and QCi payloads.")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory for generated synthetic data files. Defaults to data/ for the main results run and output-dir/data for custom output directories.",
    )
    parser.add_argument("--skip-plots", action="store_true", help="Skip matplotlib figure generation.")
    return parser


def _experiment_config(args: argparse.Namespace) -> ExperimentConfig:
    max_iterations = 4 if args.quick else 25
    random_restarts = 2 if args.quick else 5
    results_dir = Path(args.output_dir)
    if args.data_dir is not None:
        data_dir = Path(args.data_dir)
    elif results_dir == Path("results"):
        data_dir = Path("data")
    else:
        data_dir = results_dir / "data"
    return ExperimentConfig(
        dataset=DatasetConfig(seed=args.seed, n_microgrids=args.n_microgrids, horizon_hours=args.horizon),
        solver=SolverConfig(max_iterations=max_iterations, random_restarts=random_restarts),
        output=OutputConfig(results_dir=results_dir, data_dir=data_dir),
    )


def _optimizers(config: ExperimentConfig, quick: bool):
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=config.solver.max_iterations),
    ]
    if not quick:
        optimizers.append(DifferentialEvolutionOptimizer(maxiter=2, popsize=2))
    optimizers.append(
        RandomRestartPolynomialSearch(
            n_restarts=config.solver.random_restarts,
            local_steps=1 if quick else 3,
        )
    )
    return optimizers


def _clean_payload_dir(results_dir: Path) -> None:
    payload_dir = results_dir / "qci_payloads"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)


def _print_summary(tables, design: dict, payload_count: int, headlines_path: Path) -> None:
    summary = tables["summary_metrics"]
    best_cost = summary.sort_values("expected_operating_cost").iloc[0]
    best_critical = summary.sort_values("critical_load_served_fraction", ascending=False).iloc[0]
    print("CMPO Phase 2 reproduction complete")
    print(f"Best method by expected cost: {best_cost['method_name']} ({best_cost['expected_operating_cost']:.3f})")
    print(
        "Best method by critical load served: "
        f"{best_critical['method_name']} ({best_critical['critical_load_served_fraction']:.4f})"
    )
    print("Feasibility rate by method:")
    for row in summary.sort_values("method_name").itertuples(index=False):
        print(f"  {row.method_name}: {row.feasibility_rate:.3f}")
    print(f"Total upgrade cost: {design['total_upgrade_cost']:.2f}")
    print(f"Payloads exported: {payload_count}")
    print(f"Phase 2 headlines: {headlines_path}")


def main() -> None:
    """Execute the full Phase 2 evidence workflow."""

    args = build_parser().parse_args()
    config = _experiment_config(args)
    config.output.results_dir.mkdir(parents=True, exist_ok=True)
    config.output.data_dir.mkdir(parents=True, exist_ok=True)
    legacy_manifest = config.output.results_dir / "placeholder_manifest.json"
    if legacy_manifest.exists():
        legacy_manifest.unlink()
    _clean_payload_dir(config.output.results_dir)

    grid_case = generate_synthetic_dataset(config.dataset, output_dir=config.output.data_dir)
    selected_scenarios = grid_case.scenarios[: max(1, min(args.n_scenarios, len(grid_case.scenarios)))]

    candidate_patches = generate_candidate_patches(grid_case, max_patch_size=3)
    design = choose_min_cost_upgrades(grid_case, candidate_patches)
    design_outputs = save_design_outputs(design, config.output.results_dir)
    selected_patches = design["selected_patches"]

    result_records: list[dict] = []
    model_metadata: list[dict] = []
    exported_payloads: list[Path] = []
    optimizers = _optimizers(config, args.quick)

    for patch in selected_patches:
        for scenario in selected_scenarios:
            model, metadata = build_scenario_hamiltonian(
                grid_case,
                scenario,
                patch,
                output_dir=config.output.results_dir,
                write_export=False,
            )
            payload_path = export_polynomial_model_payload(model, metadata, config.output.results_dir)
            exported_payloads.append(payload_path)
            model_metadata.append(metadata | model_statistics(model))
            for optimizer in optimizers:
                result_records.append(optimizer.run(grid_case, scenario, patch, model, config).to_dict())

    tables = compute_phase2_metrics(
        grid_case,
        result_records,
        design_metrics=design["metrics"],
        model_metadata=model_metadata,
    )
    output_paths = write_phase2_outputs(tables, config.output.results_dir)
    figure_paths = {} if args.skip_plots else write_phase2_plots(tables, grid_case, config.output.results_dir)

    manifest = {
        "seed": config.dataset.seed,
        "n_microgrids": config.dataset.n_microgrids,
        "horizon": config.dataset.horizon_hours,
        "n_scenarios": len(selected_scenarios),
        "quick": args.quick,
        "data_dir": str(config.output.data_dir),
        "selected_patches": [list(patch) for patch in selected_patches],
        "payload_count": len(exported_payloads),
        "design_outputs": {key: str(path) for key, path in design_outputs.items()},
        "metric_outputs": {key: str(path) for key, path in output_paths.items()},
        "figure_outputs": {key: str(path) for key, path in figure_paths.items()},
        "payloads": [str(path) for path in exported_payloads],
    }
    manifest_path = config.output.results_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _print_summary(tables, design, len(exported_payloads), output_paths["phase2_headlines_md"])


if __name__ == "__main__":
    main()
