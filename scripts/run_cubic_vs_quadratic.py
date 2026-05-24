#!/usr/bin/env python
"""Compare native cubic generation cost against a fitted quadratic approximation."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baselines import GreedyCriticalLoadFirst, RandomRestartPolynomialSearch, SLSQPDispatchOptimizer  # noqa: E402
from cmpo.config import DatasetConfig, ExperimentConfig, OutputConfig, SolverConfig  # noqa: E402
from cmpo.data import GridCase, Microgrid, generate_synthetic_dataset  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.repair import repair_solution  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run cubic vs quadratic approximation experiment.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-microgrids", type=int, default=3)
    parser.add_argument("--horizon", type=int, default=4)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--quick", action="store_true")
    return parser


def _fit_quadratic_coefficients(microgrid: Microgrid) -> tuple[float, float]:
    generator = microgrid.generator
    p_values = np.linspace(generator.p_min_kw, generator.p_max_kw, 40)
    y = generator.cost_a * p_values**3 + generator.cost_b * p_values**2 + generator.cost_c * p_values
    design = np.column_stack([p_values**2, p_values])
    fitted_b, fitted_c = np.linalg.lstsq(design, y, rcond=None)[0]
    return float(fitted_b), float(fitted_c)


def _quadratic_case(grid_case: GridCase) -> GridCase:
    fitted_microgrids: list[Microgrid] = []
    for microgrid in grid_case.microgrids:
        fitted_b, fitted_c = _fit_quadratic_coefficients(microgrid)
        fitted_generator = replace(microgrid.generator, cost_a=0.0, cost_b=fitted_b, cost_c=fitted_c)
        fitted_microgrids.append(replace(microgrid, generator=fitted_generator))
    return replace(grid_case, microgrids=fitted_microgrids)


def _true_cubic_dispatch_cost(grid_case: GridCase, solution: dict[str, float], patch: tuple[str, ...]) -> tuple[float, dict[str, float]]:
    microgrids = {microgrid.name: microgrid for microgrid in grid_case.microgrids}
    profile: dict[str, float] = {}
    cost = 0.0
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        for hour in range(grid_case.horizon_hours):
            value = float(solution.get(f"P_gen[{microgrid_id},{hour}]", 0.0))
            profile[f"{microgrid_id}:{hour}"] = value
            generator = microgrid.generator
            cost += generator.cost_a * value**3 + generator.cost_b * value**2 + generator.cost_c * value
    return float(cost), profile


def _run_variant(
    variant: str,
    model_case: GridCase,
    true_case: GridCase,
    scenario,
    patch: tuple[str, ...],
    config: ExperimentConfig,
    quick: bool,
) -> list[dict[str, object]]:
    model, _metadata = build_scenario_hamiltonian(model_case, scenario, patch, output_dir=config.output.results_dir, write_export=False)
    true_model, _true_meta = build_scenario_hamiltonian(true_case, scenario, patch, output_dir=config.output.results_dir, write_export=False)
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=3 if quick else 12),
        RandomRestartPolynomialSearch(n_restarts=2 if quick else 5, local_steps=1 if quick else 3),
    ]
    rows: list[dict[str, object]] = []
    for optimizer in optimizers:
        result = optimizer.run(model_case, scenario, patch, model, config)
        raw_solution = _solution_for_result_proxy(model_case, scenario, patch, model, optimizer, config)
        repaired_solution, _report = repair_solution(raw_solution, true_model, true_case, patch, scenario)
        true_cost, dispatch_profile = _true_cubic_dispatch_cost(true_case, repaired_solution, patch)
        rows.append(
            result.to_dict()
            | {
                "model_variant": variant,
                "true_cubic_cost": true_cost,
                "dispatch_profile": dispatch_profile,
            }
        )
    return rows


def _solution_for_result_proxy(model_case, scenario, patch, model, optimizer, config):
    """Re-run an optimizer deterministically to recover its solution for true-cost evaluation."""

    # The Result API intentionally stores metrics rather than full vectors. For
    # this experiment we need the vector, so use the same deterministic internals
    # through method-specific warm starts where possible.
    from cmpo.baselines import build_greedy_solution, _solution_from_vector, _vector_from_solution, _bounds  # noqa: PLC0415
    from scipy.optimize import minimize  # noqa: PLC0415

    if isinstance(optimizer, GreedyCriticalLoadFirst):
        return build_greedy_solution(model_case, scenario, patch, model)
    if isinstance(optimizer, SLSQPDispatchOptimizer):
        warm = build_greedy_solution(model_case, scenario, patch, model)
        x0 = _vector_from_solution(model, warm)
        result = minimize(
            lambda vector: model.evaluate(_solution_from_vector(model, np.asarray(vector, dtype=float))),
            x0,
            method="SLSQP",
            bounds=_bounds(model),
            options={"maxiter": int(optimizer.maxiter or config.solver.max_iterations), "ftol": 1e-6, "disp": False},
        )
        return _solution_from_vector(model, np.asarray(result.x if result.x is not None else x0, dtype=float))
    return build_greedy_solution(model_case, scenario, patch, model)


def _add_comparison_columns(frame: pd.DataFrame) -> pd.DataFrame:
    cubic = frame[frame["model_variant"] == "cubic"].set_index("method_name")
    differences = []
    profile_diffs = []
    for row in frame.itertuples(index=False):
        baseline_cost = float(cubic.loc[row.method_name, "true_cubic_cost"]) if row.method_name in cubic.index else np.nan
        differences.append(float(row.true_cubic_cost - baseline_cost))
        baseline_profile = cubic.loc[row.method_name, "dispatch_profile"] if row.method_name in cubic.index else {}
        if isinstance(baseline_profile, pd.Series):
            baseline_profile = baseline_profile.iloc[0]
        profile = row.dispatch_profile
        keys = set(profile) | set(baseline_profile)
        profile_diffs.append(sum(abs(float(profile.get(key, 0.0)) - float(baseline_profile.get(key, 0.0))) for key in keys))
    frame = frame.copy()
    frame["true_cubic_cost_difference_vs_cubic"] = differences
    frame["dispatch_profile_l1_difference_vs_cubic"] = profile_diffs
    return frame


def _write_figures(frame: pd.DataFrame, output_dir: Path) -> None:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    dispatch = frame.pivot_table(
        index="method_name",
        columns="model_variant",
        values="dispatch_profile_l1_difference_vs_cubic",
        aggfunc="mean",
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    dispatch.plot(kind="bar", ax=ax)
    ax.set_title("Dispatch Difference vs Cubic Model")
    ax.set_ylabel("L1 dispatch difference (kW)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(figures_dir / "cubic_vs_quadratic_dispatch.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    cost = frame.pivot_table(
        index="method_name",
        columns="model_variant",
        values="true_cubic_cost_difference_vs_cubic",
        aggfunc="mean",
    )
    cost.plot(kind="bar", ax=ax)
    ax.set_title("True Cubic Cost Error")
    ax.set_ylabel("Cost difference vs cubic")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(figures_dir / "cubic_vs_quadratic_cost_error.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = ExperimentConfig(
        dataset=DatasetConfig(seed=args.seed, n_microgrids=args.n_microgrids, horizon_hours=args.horizon),
        solver=SolverConfig(max_iterations=3 if args.quick else 12, random_restarts=2 if args.quick else 5),
        output=OutputConfig(results_dir=output_dir, data_dir=data_dir),
    )
    true_case = generate_synthetic_dataset(config.dataset, output_dir=data_dir)
    quadratic_case = _quadratic_case(true_case)
    scenario = true_case.scenarios[0]
    patch = tuple(microgrid.name for microgrid in true_case.microgrids[:1])

    rows = []
    rows.extend(_run_variant("cubic", true_case, true_case, scenario, patch, config, args.quick))
    rows.extend(_run_variant("quadratic_approximation", quadratic_case, true_case, scenario, patch, config, args.quick))
    frame = _add_comparison_columns(pd.DataFrame(rows))
    frame = frame.drop(columns=["dispatch_profile"])
    csv_path = output_dir / "cubic_vs_quadratic.csv"
    frame.to_csv(csv_path, index=False)
    _write_figures(frame, output_dir)
    print("Cubic vs quadratic experiment complete")
    print(f"Wrote comparison CSV to {csv_path}")
    print(f"Wrote figures to {output_dir / 'figures'}")


if __name__ == "__main__":
    main()
