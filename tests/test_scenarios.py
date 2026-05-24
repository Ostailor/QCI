from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset


def test_scenario_probabilities_sum_to_one(tmp_path: Path) -> None:
    case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path)

    assert sum(scenario.probability for scenario in case.scenarios) == 1.0


def test_scenario_arrays_have_expected_shapes(tmp_path: Path) -> None:
    case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path)
    expected_names = {
        "normal",
        "renewable_shortfall",
        "demand_surge",
        "pcc_failure",
        "local_generator_failure",
        "storm_forced_islanding",
        "restoration",
        "combined_high_stress",
    }

    assert {scenario.name for scenario in case.scenarios} == expected_names
    for scenario in case.scenarios:
        assert len(scenario.load_multiplier_by_hour) == case.horizon_hours
        assert len(scenario.pv_multiplier_by_hour) == case.horizon_hours
        assert len(scenario.tie_availability) == len(case.microgrids)
        assert len(scenario.generator_availability) == len(case.microgrids)
        assert len(scenario.forced_islanding) == len(case.microgrids)
        for row in scenario.tie_availability:
            assert len(row) == case.horizon_hours
        for row in scenario.generator_availability:
            assert len(row) == case.horizon_hours
        for row in scenario.forced_islanding:
            assert len(row) == case.horizon_hours
        assert scenario.severity_label in {"low", "medium", "high", "extreme"}
        assert 0.0 < scenario.critical_load_requirement <= 1.0
