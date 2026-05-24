from pathlib import Path

from cmpo.config import DatasetConfig, ExperimentConfig, SolverConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.baselines import GreedyCriticalLoadFirst, RandomRestartPolynomialSearch
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.metrics import compute_phase2_metrics, write_phase2_outputs
from cmpo.plotting import write_phase2_plots


def _sample_records(tmp_path: Path):
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4), output_dir=tmp_path / "data")
    config = ExperimentConfig(
        dataset=DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4),
        solver=SolverConfig(max_iterations=3, random_restarts=2),
    )
    scenario = grid_case.scenarios[0]
    patch = ("MG1",)
    model, metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results", write_export=False)
    records = [
        GreedyCriticalLoadFirst().run(grid_case, scenario, patch, model, config).to_dict(),
        RandomRestartPolynomialSearch(n_restarts=2, local_steps=1).run(grid_case, scenario, patch, model, config).to_dict(),
    ]
    return grid_case, records, [metadata]


def test_compute_phase2_metrics_contains_required_columns(tmp_path: Path) -> None:
    grid_case, records, metadata = _sample_records(tmp_path)
    tables = compute_phase2_metrics(grid_case, records, design_metrics={"total_upgrade_cost": 10.0}, model_metadata=metadata)

    assert "summary_metrics" in tables
    assert "scenario_results" in tables
    assert "scaling_results" in tables
    assert "model_stats" in tables
    assert "risk_adjusted_cost" in tables["summary_metrics"].columns
    assert "scenario_scaling_cost_degradation" in tables["scaling_results"].columns


def test_write_phase2_outputs_and_plots(tmp_path: Path) -> None:
    grid_case, records, metadata = _sample_records(tmp_path)
    tables = compute_phase2_metrics(grid_case, records, design_metrics={"total_upgrade_cost": 10.0}, model_metadata=metadata)
    output_paths = write_phase2_outputs(tables, tmp_path / "results")
    figure_paths = write_phase2_plots(tables, grid_case, tmp_path / "results")

    for key in (
        "summary_metrics_csv",
        "scenario_results_csv",
        "scaling_results_csv",
        "model_stats_csv",
        "phase2_headlines_md",
    ):
        assert output_paths[key].exists()
    for path in figure_paths.values():
        assert path.exists()
