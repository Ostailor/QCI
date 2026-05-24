import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.repair import repair_solution


@pytest.fixture(scope="module")
def quick_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase2_run")
    results = root / "results"
    data = root / "data"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_all.py",
            "--seed",
            "42",
            "--n-microgrids",
            "3",
            "--horizon",
            "4",
            "--n-scenarios",
            "2",
            "--quick",
            "--output-dir",
            str(results),
            "--data-dir",
            str(data),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return {"root": root, "results": results, "data": data}


def test_run_all_quick_creates_all_required_output_files(quick_run) -> None:
    results = quick_run["results"]
    required = [
        "summary_metrics.csv",
        "scenario_results.csv",
        "scaling_results.csv",
        "model_stats.csv",
        "phase2_headlines.md",
        "run_manifest.json",
        "microgrid_design.csv",
        "upgrade_plan.csv",
        "design_summary.json",
        "figures/cost_by_method.png",
        "figures/critical_load_served_by_method.png",
        "figures/energy_not_served_by_scenario.png",
        "figures/feasibility_rate_by_method.png",
        "figures/runtime_by_method.png",
        "figures/scenario_scaling.png",
        "figures/cubic_vs_quadratic_dispatch.png",
    ]

    for relative in required:
        assert (results / relative).exists(), relative
    assert list((results / "qci_payloads").glob("*.json"))


def test_generated_csvs_have_expected_columns_and_no_nan_values(quick_run) -> None:
    results = quick_run["results"]
    expected_columns = {
        "summary_metrics.csv": {
            "method_name",
            "expected_operating_cost",
            "risk_adjusted_cost",
            "critical_load_served_fraction",
            "energy_not_served_kwh",
            "feasibility_rate",
            "median_runtime_seconds",
        },
        "scenario_results.csv": {
            "method_name",
            "scenario",
            "patch",
            "expected_cost_component",
            "critical_load_served_fraction",
            "energy_not_served_kwh",
            "critical_energy_not_served_kwh",
            "scenario_probability",
        },
        "scaling_results.csv": {
            "method_name",
            "scenario",
            "patch",
            "scenario_scaling_runtime",
            "scenario_scaling_cost_degradation",
            "horizon_hours",
            "n_microgrids",
        },
        "model_stats.csv": {"scenario", "patch", "horizon", "variable_count", "term_count", "degree"},
        "microgrid_design.csv": {"patch_id", "microgrid_ids", "patch_size", "before_feasible", "after_feasible"},
        "upgrade_plan.csv": {"microgrid_id", "upgrade", "added_capacity_equivalent_kw", "cost", "patch_trigger"},
    }

    for filename, columns in expected_columns.items():
        frame = pd.read_csv(results / filename)
        assert columns.issubset(frame.columns), filename
        assert not frame.isna().any().any(), filename


def test_hamiltonian_degree_never_exceeds_three_in_outputs(quick_run) -> None:
    results = quick_run["results"]
    stats = pd.read_csv(results / "model_stats.csv")
    assert (stats["degree"] <= 3).all()

    for payload_path in (results / "qci_payloads").glob("*.json"):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        assert payload["max_degree"] <= 3
        assert payload["model_statistics"]["degree"] <= 3


def test_mode_variables_are_normalized_after_repair(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4), output_dir=tmp_path / "data")
    scenario = grid_case.scenarios[0]
    patch = ("MG1",)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results", write_export=False)
    solution = {name: 0.0 for name in model.variables}

    repaired, _report = repair_solution(solution, model, grid_case, patch, scenario)

    for hour in range(grid_case.horizon_hours):
        total = sum(repaired[f"z_{mode}[MG1,{hour}]"] for mode in ("grid", "island", "restore"))
        assert abs(total - 1.0) < 1e-9


def test_load_served_fractions_and_energy_not_served_ranges(quick_run) -> None:
    scenario_results = pd.read_csv(quick_run["results"] / "scenario_results.csv")

    assert scenario_results["critical_load_served_fraction"].between(0.0, 1.0).all()
    assert scenario_results["noncritical_load_served_fraction"].between(0.0, 1.0).all()
    assert (scenario_results["energy_not_served_kwh"] >= 0.0).all()
    assert (scenario_results["critical_energy_not_served_kwh"] >= 0.0).all()


def test_scenario_probabilities_sum_to_one_for_generated_case(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")

    assert sum(scenario.probability for scenario in grid_case.scenarios) == 1.0


def test_qci_payload_terms_contain_no_unknown_variables(quick_run) -> None:
    for payload_path in (quick_run["results"] / "qci_payloads").glob("*.json"):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        variables = {variable["name"] for variable in payload["variables"]}
        for term in payload["polynomial_terms"]:
            assert set(term["powers"]).issubset(variables), payload_path.name


def test_rerun_same_seed_reproduces_summary_except_runtime_columns(tmp_path: Path) -> None:
    first_results = tmp_path / "first" / "results"
    second_results = tmp_path / "second" / "results"
    common_args = [
        sys.executable,
        "scripts/run_all.py",
        "--seed",
        "42",
        "--n-microgrids",
        "3",
        "--horizon",
        "4",
        "--n-scenarios",
        "2",
        "--quick",
        "--skip-plots",
    ]
    subprocess.run(common_args + ["--output-dir", str(first_results), "--data-dir", str(tmp_path / "first" / "data")], check=True)
    subprocess.run(common_args + ["--output-dir", str(second_results), "--data-dir", str(tmp_path / "second" / "data")], check=True)

    first = pd.read_csv(first_results / "summary_metrics.csv")
    second = pd.read_csv(second_results / "summary_metrics.csv")
    runtime_columns = [column for column in first.columns if "runtime" in column or column == "time_to_good_solution"]

    pd.testing.assert_frame_equal(
        first.drop(columns=runtime_columns),
        second.drop(columns=runtime_columns),
        check_exact=False,
        atol=1e-9,
        rtol=1e-9,
    )


def test_summary_metrics_derive_from_saved_scenario_results(quick_run) -> None:
    results = quick_run["results"]
    summary = pd.read_csv(results / "summary_metrics.csv").set_index("method_name")
    scenarios = pd.read_csv(results / "scenario_results.csv")

    for method, group in scenarios.groupby("method_name"):
        expected_cost = float((group["expected_cost_component"] * group["scenario_probability"]).sum())
        feasibility_rate = float(group["feasibility_pass"].mean())
        critical_served = float(group["critical_load_served_fraction"].mean())
        energy_not_served = float(group["energy_not_served_kwh"].sum())

        assert abs(summary.loc[method, "expected_operating_cost"] - expected_cost) < 1e-9
        assert abs(summary.loc[method, "feasibility_rate"] - feasibility_rate) < 1e-9
        assert abs(summary.loc[method, "critical_load_served_fraction"] - critical_served) < 1e-9
        assert abs(summary.loc[method, "energy_not_served_kwh"] - energy_not_served) < 1e-9
