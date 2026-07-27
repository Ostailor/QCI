from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import GridCase, generate_synthetic_dataset


def test_default_case_writes_required_data_files(tmp_path: Path) -> None:
    case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path)

    assert isinstance(case, GridCase)
    assert case.seed == 42
    assert case.horizon_hours == 6
    assert len(case.microgrids) == 4
    assert len(case.scenarios) == 8
    assert (tmp_path / "generated_case.yaml").exists()
    assert (tmp_path / "scenarios.csv").exists()
    assert (tmp_path / "microgrids.csv").exists()


def test_all_capacities_and_loads_are_positive(tmp_path: Path) -> None:
    case = generate_synthetic_dataset(DatasetConfig(seed=13), output_dir=tmp_path)

    for microgrid in case.microgrids:
        assert all(load > 0 for load in microgrid.load_profile.base_kw)
        assert 0.35 <= microgrid.load_profile.critical_fraction <= 0.65
        assert 0.0 < microgrid.load_profile.flexible_fraction < 0.5
        assert all(pv >= 0 for pv in microgrid.pv_availability_kw)
        assert microgrid.generator.p_min_kw >= 0
        assert microgrid.generator.p_max_kw > microgrid.generator.p_min_kw
        assert microgrid.generator.cost_a > 0
        assert microgrid.generator.cost_b > 0
        assert microgrid.generator.cost_c > 0
        assert microgrid.battery.capacity_kwh > 0
        assert microgrid.battery.max_charge_kw > 0
        assert microgrid.battery.max_discharge_kw > 0
        assert microgrid.pcc.import_limit_kw > 0
        assert microgrid.pcc.export_limit_kw > 0
        assert microgrid.upgrade_options.added_pv_kw > 0
        assert microgrid.upgrade_options.added_bess_kwh > 0
        assert microgrid.upgrade_options.added_generator_kw > 0
