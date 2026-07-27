from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.repair import (
    clip_to_bounds,
    compute_balance_residuals,
    normalize_modes,
    repair_pcc,
    repair_solution,
    repair_storage,
)


def _raw_solution_with_violations(tmp_path):
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    scenario = next(item for item in grid_case.scenarios if item.name == "storm_forced_islanding")
    patch = ("MG1", "MG2")
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results")
    solution = {name: variable.upper_bound * 2.0 + 10.0 for name, variable in model.variables.items()}
    for microgrid_id in patch:
        for hour in range(grid_case.horizon_hours):
            solution[f"z_grid[{microgrid_id},{hour}]"] = 0.0
            solution[f"z_island[{microgrid_id},{hour}]"] = 0.0
            solution[f"z_restore[{microgrid_id},{hour}]"] = 0.0
            solution[f"import_pcc[{microgrid_id},{hour}]"] = 25.0
            solution[f"export_pcc[{microgrid_id},{hour}]"] = 25.0
            solution[f"charge[{microgrid_id},{hour}]"] = grid_case.microgrids[0].battery.max_charge_kw * 5.0
            solution[f"discharge[{microgrid_id},{hour}]"] = grid_case.microgrids[0].battery.max_discharge_kw * 5.0
    return grid_case, scenario, patch, model, solution


def test_modes_sum_to_one_after_repair(tmp_path) -> None:
    grid_case, scenario, patch, model, solution = _raw_solution_with_violations(tmp_path)
    repaired, _report = repair_solution(solution, model, grid_case, patch, scenario)

    for microgrid_id in patch:
        for hour in range(grid_case.horizon_hours):
            total = (
                repaired[f"z_grid[{microgrid_id},{hour}]"]
                + repaired[f"z_island[{microgrid_id},{hour}]"]
                + repaired[f"z_restore[{microgrid_id},{hour}]"]
            )
            assert abs(total - 1.0) < 1e-9


def test_storage_repair_keeps_soc_within_capacity(tmp_path) -> None:
    grid_case, scenario, patch, model, solution = _raw_solution_with_violations(tmp_path)
    clipped = clip_to_bounds(solution, model)
    normalized = normalize_modes(clipped, patch, grid_case.horizon_hours)
    repaired = repair_storage(normalized, grid_case, patch, scenario)

    microgrids = {microgrid.name: microgrid for microgrid in grid_case.microgrids}
    for microgrid_id in patch:
        battery = microgrids[microgrid_id].battery
        for hour in range(grid_case.horizon_hours):
            soc = repaired[f"soc[{microgrid_id},{hour}]"]
            assert 0.0 <= soc <= battery.capacity_kwh


def test_pcc_is_zero_when_tie_unavailable(tmp_path) -> None:
    grid_case, scenario, patch, model, solution = _raw_solution_with_violations(tmp_path)
    repaired = repair_pcc(normalize_modes(clip_to_bounds(solution, model), patch, grid_case.horizon_hours), scenario)

    for microgrid_id in patch:
        for hour in range(grid_case.horizon_hours):
            assert repaired[f"import_pcc[{microgrid_id},{hour}]"] == 0.0
            assert repaired[f"export_pcc[{microgrid_id},{hour}]"] == 0.0


def test_repair_report_contains_required_fields(tmp_path) -> None:
    grid_case, scenario, patch, model, solution = _raw_solution_with_violations(tmp_path)
    _repaired, report = repair_solution(solution, model, grid_case, patch, scenario)

    assert {
        "max_balance_residual",
        "storage_violations",
        "pcc_violations",
        "mode_violations",
        "load_shed_violations",
        "charge_discharge_violations",
        "generator_availability_violations",
        "implicit_pv_curtailment_kwh",
        "feasibility_pass",
    }.issubset(report)


def test_hamiltonian_bounds_follow_scenario_availability_and_load(tmp_path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    scenario = next(item for item in grid_case.scenarios if item.name == "local_generator_failure")
    patch = ("MG2",)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results")
    failed_hour = grid_case.horizon_hours // 3
    microgrid = grid_case.microgrids[1]
    critical_load = (
        microgrid.load_profile.base_kw[failed_hour]
        * scenario.load_multiplier_by_hour[failed_hour]
        * microgrid.load_profile.critical_fraction
    )

    assert model.variables[f"P_gen[MG2,{failed_hour}]"].lower_bound == 0.0
    assert model.variables[f"P_gen[MG2,{failed_hour}]"].upper_bound == 0.0
    assert model.variables[f"shed_critical[MG2,{failed_hour}]"].upper_bound == critical_load


def test_repair_removes_simultaneous_charge_discharge_and_shed_overage(tmp_path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    scenario = next(item for item in grid_case.scenarios if item.name == "demand_surge")
    patch = ("MG1",)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results")
    solution = {name: 0.0 for name in model.variables}
    microgrid = grid_case.microgrids[0]
    for hour in range(grid_case.horizon_hours):
        solution[f"z_grid[MG1,{hour}]"] = 1.0
        solution[f"charge[MG1,{hour}]"] = microgrid.battery.max_charge_kw
        solution[f"discharge[MG1,{hour}]"] = microgrid.battery.max_discharge_kw
        solution[f"shed_critical[MG1,{hour}]"] = 10_000.0
        solution[f"shed_noncritical[MG1,{hour}]"] = 10_000.0

    repaired, report = repair_solution(solution, model, grid_case, patch, scenario)

    assert report["charge_discharge_violations"] == 0
    assert report["load_shed_violations"] == 0
    for hour in range(grid_case.horizon_hours):
        assert repaired[f"charge[MG1,{hour}]"] == 0.0 or repaired[f"discharge[MG1,{hour}]"] == 0.0
        load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
        critical = load * microgrid.load_profile.critical_fraction
        noncritical = max(0.0, load - critical)
        assert repaired[f"shed_critical[MG1,{hour}]"] <= critical + 1e-6
        assert repaired[f"shed_noncritical[MG1,{hour}]"] <= noncritical + 1e-6


def test_repair_balances_zero_vector_by_shedding_load(tmp_path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    scenario = next(item for item in grid_case.scenarios if item.name == "storm_forced_islanding")
    patch = ("MG1",)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=tmp_path / "results")
    solution = {name: 0.0 for name in model.variables}

    repaired, report = repair_solution(solution, model, grid_case, patch, scenario)
    residuals = compute_balance_residuals(repaired, grid_case, patch, scenario)

    assert report["feasibility_pass"] is True
    assert max(abs(value) for value in residuals.values()) <= 1e-4
    for hour in range(grid_case.horizon_hours):
        assert repaired[f"import_pcc[MG1,{hour}]"] == 0.0
        assert repaired[f"export_pcc[MG1,{hour}]"] == 0.0
