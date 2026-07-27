import math

from cmpo.config import DatasetConfig, ExperimentConfig, SolverConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.baselines import (
    BaselineSkipped,
    DifferentialEvolutionOptimizer,
    GPUParallelRandomRestartBaseline,
    GreedyCriticalLoadFirst,
    PiecewiseLinearMILPBaseline,
    PyomoIPOPTNonlinearBaseline,
    QUBOQuadratizedBaseline,
    RandomRestartPolynomialSearch,
    Result,
    SLSQPDispatchOptimizer,
    StressReserveHeuristicBaseline,
)
from cmpo.hamiltonian_builder import build_scenario_hamiltonian


def _case_model(tmp_path):
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4), output_dir=tmp_path / "data")
    scenario = grid_case.scenarios[0]
    patch = ("MG1",)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results", write_export=False)
    return grid_case, scenario, patch, model


def test_every_baseline_returns_result_without_nan_metrics(tmp_path) -> None:
    grid_case, scenario, patch, model = _case_model(tmp_path)
    config = ExperimentConfig(
        dataset=DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4),
        solver=SolverConfig(max_iterations=4, random_restarts=3),
    )
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=3),
        DifferentialEvolutionOptimizer(maxiter=1, popsize=2),
        RandomRestartPolynomialSearch(n_restarts=3, local_steps=2),
        QUBOQuadratizedBaseline(levels=3, sweeps=4),
        PyomoIPOPTNonlinearBaseline(maxiter=3),
        StressReserveHeuristicBaseline(),
    ]

    for optimizer in optimizers:
        result = optimizer.run(grid_case, scenario, patch, model, config)
        assert isinstance(result, Result)
        assert result.runtime_seconds >= 0.0
        for value in (
            result.raw_energy,
            result.repaired_energy,
            result.expected_cost_component,
            result.critical_load_served_fraction,
            result.noncritical_load_served_fraction,
            result.energy_not_served_kwh,
            result.critical_energy_not_served_kwh,
        ):
            assert math.isfinite(value)


def test_optional_piecewise_milp_baseline_runs_or_skips_cleanly(tmp_path) -> None:
    grid_case, scenario, patch, model = _case_model(tmp_path)
    config = ExperimentConfig(dataset=DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4))
    optimizer = PiecewiseLinearMILPBaseline(breakpoints=3)

    try:
        result = optimizer.run(grid_case, scenario, patch, model, config)
    except BaselineSkipped as exc:
        assert exc.method_name == optimizer.method_name
        assert exc.reason
    else:
        assert isinstance(result, Result)
        assert result.feasibility_pass


def test_qubo_baseline_reports_quadratization_metadata(tmp_path) -> None:
    grid_case, scenario, patch, model = _case_model(tmp_path)
    config = ExperimentConfig(dataset=DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4))
    optimizer = QUBOQuadratizedBaseline(levels=3, sweeps=2)

    optimizer.run(grid_case, scenario, patch, model, config)

    assert optimizer.last_metadata["binary_variable_count"] > 0
    assert optimizer.last_metadata["auxiliary_variable_count"] >= 0
    assert optimizer.last_metadata["variable_blowup"] >= 1.0


def test_gpu_baseline_uses_available_backend_or_cpu_fallback(tmp_path) -> None:
    grid_case, scenario, patch, model = _case_model(tmp_path)
    config = ExperimentConfig(dataset=DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4))
    optimizer = GPUParallelRandomRestartBaseline(restarts=4, local_steps=0)

    result = optimizer.run(grid_case, scenario, patch, model, config)

    assert isinstance(result, Result)
    assert optimizer.last_metadata["gpu_backend"]
    assert optimizer.last_metadata["restart_count"] == 4


def test_greedy_baseline_is_reproducible_under_seed(tmp_path) -> None:
    grid_case, scenario, patch, model = _case_model(tmp_path)
    config = ExperimentConfig(dataset=DatasetConfig(seed=7, n_microgrids=3, horizon_hours=4))
    optimizer = GreedyCriticalLoadFirst()

    first = optimizer.run(grid_case, scenario, patch, model, config)
    second = optimizer.run(grid_case, scenario, patch, model, config)

    assert first == second
