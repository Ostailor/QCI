import math
from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian, save_model_stats
from cmpo.polynomial import PolynomialModel


def test_polynomial_model_core_api_and_degree_validation(tmp_path: Path) -> None:
    model = PolynomialModel(name="unit")
    model.add_variable("x", lower_bound=0.0, upper_bound=2.0)
    model.add_linear(1.0, "x")
    model.add_quadratic(2.0, "x", "x")
    model.add_cubic(3.0, "x", "x", "x")

    assert model.variable_count() == 1
    assert model.term_count() == 3
    assert model.degree() == 3
    assert model.validate_degree(3)
    assert model.evaluate({"x": 0.5}) == 1.375

    path = tmp_path / "model.json"
    model.save_json(path)
    assert path.exists()


def test_scenario_hamiltonian_degree_and_variable_bounds(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    scenario = grid_case.scenarios[0]
    patch = ("MG1", "MG2")

    model, metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results")

    assert model.degree() <= 3
    assert metadata["degree"] <= 3
    assert metadata["variable_count"] == model.variable_count()
    assert metadata["term_count"] == model.term_count()
    assert all(variable.lower_bound is not None and variable.upper_bound is not None for variable in model.variables.values())
    assert (tmp_path / "results" / "qci_payloads" / "normal_MG1-MG2.json").exists()


def test_zero_solution_evaluation_is_finite(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    model, _metadata = build_scenario_hamiltonian(grid_case, grid_case.scenarios[0], ("MG1",), output_dir=tmp_path / "results")
    zero_solution = {name: 0.0 for name in model.variables}

    assert math.isfinite(model.evaluate(zero_solution))


def test_model_stats_records_variable_count(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    model, metadata = build_scenario_hamiltonian(grid_case, grid_case.scenarios[0], ("MG1",), output_dir=tmp_path / "results")
    stats_path = save_model_stats([metadata], tmp_path / "results")

    text = stats_path.read_text(encoding="utf-8")
    assert "variable_count" in text
    assert str(model.variable_count()) in text
