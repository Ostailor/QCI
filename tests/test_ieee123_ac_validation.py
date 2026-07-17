from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import pandas as pd

from cmpo.ieee123_ac_validation import (
    ACValidationLimits,
    allocate_dispatch_by_capacity,
    assess_ac_validity,
    copy_pinned_feeder,
    load_service_fractions,
    validate_ieee123_scenario,
)
from cmpo.ieee123_sc_cmpo_adapter import parse_ieee123_sc_cmpo_case
from cmpo.scenario_coupled_model import load_sc_cmpo_config
from scripts.phase3_validate_ieee123_ac_solutions import (
    aggregate_ac_validation,
    build_ac_valid_budget_frontier,
    validate_ieee123_ac_solutions,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "phase3_sc_cmpo_ieee123.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_service_fractions_reproduce_critical_and_total_dispatch() -> None:
    critical_fraction, noncritical_fraction = load_service_fractions(
        total_load_kw=3490.0,
        critical_load_kw=1850.0,
        total_served_kw=2646.46952125,
        critical_served_kw=1066.46952125,
    )

    assert critical_fraction == pytest.approx(1066.46952125 / 1850.0)
    assert noncritical_fraction == pytest.approx(1580.0 / 1640.0)
    assert critical_fraction * 1850.0 + noncritical_fraction * 1640.0 == pytest.approx(2646.46952125)


def test_dispatch_allocation_uses_only_eligible_assets_and_respects_capacity() -> None:
    assets = [
        {"asset_key": "a", "installed_power_kw": 20.0, "anchor_node": "1"},
        {"asset_key": "b", "installed_power_kw": 30.0, "anchor_node": "2"},
        {"asset_key": "c", "installed_power_kw": 50.0, "anchor_node": "3"},
    ]

    allocation = allocate_dispatch_by_capacity(
        assets,
        requested_kw=40.0,
        eligible=lambda asset: asset["anchor_node"] != "3",
    )

    assert allocation == pytest.approx({"a": 16.0, "b": 24.0, "c": 0.0})
    assert sum(allocation.values()) == pytest.approx(40.0)


def test_dispatch_allocation_rejects_unrepresentable_decision() -> None:
    with pytest.raises(ValueError, match="exceeds eligible installed power"):
        allocate_dispatch_by_capacity(
            [{"asset_key": "a", "installed_power_kw": 10.0}],
            requested_kw=10.1,
        )


def test_ac_validity_ignores_unpublished_ratings_but_enforces_checkable_limits() -> None:
    limits = ACValidationLimits()
    valid = assess_ac_validity(
        converged=True,
        voltage_violation_count=0,
        transformer_loading_available=True,
        maximum_transformer_loading_percent=99.9,
        line_loading_available=False,
        maximum_line_loading_percent=None,
        island_balance_residual_kw=0.0001,
        served_load_kw=1000.0,
        limits=limits,
    )
    invalid = assess_ac_validity(
        converged=True,
        voltage_violation_count=1,
        transformer_loading_available=True,
        maximum_transformer_loading_percent=99.9,
        line_loading_available=False,
        maximum_line_loading_percent=None,
        island_balance_residual_kw=0.0001,
        served_load_kw=1000.0,
        limits=limits,
    )

    assert valid["ac_valid"] is True
    assert valid["line_loading_check"] == "unavailable"
    assert invalid["ac_valid"] is False
    assert invalid["voltage_check"] == "failed"


def test_copy_pinned_feeder_preserves_source_and_resolves_redirects(tmp_path: Path) -> None:
    source_master = ROOT / "data" / "upstream" / "ieee123" / "opendss" / "IEEE123Master.dss"
    copied_master = copy_pinned_feeder(source_master, tmp_path)

    assert copied_master != source_master
    assert _sha256(copied_master) == _sha256(source_master)
    assert (copied_master.parent / "IEEELineCodes.DSS").is_file()
    assert (copied_master.parent / "IEEE123Loads.DSS").is_file()
    assert (copied_master.parent / "IEEE123Regulators.DSS").is_file()


def test_nominal_unbalanced_feeder_validation_reports_public_rating_availability(tmp_path: Path) -> None:
    case = parse_ieee123_sc_cmpo_case(load_sc_cmpo_config(CONFIG))
    copied_master = copy_pinned_feeder(Path(case.metadata["master_path"]), tmp_path)
    scenario = {
        "scenario": "nominal_test",
        "scenario_trace_id": "nominal-test",
        "unavailable_edge_ids": ["line_Sw7", "line_Sw8"],
        "selected_patch_modes": {},
        "selected_battery_actions_by_node": {},
        "total_load_kwh": 3490.0,
        "total_load_served_kwh": 3490.0,
        "critical_load_kwh": 0.0,
        "critical_load_served_kwh": 0.0,
        "pv_dispatch_kwh": 0.0,
        "dispatchable_upgrade_dispatch_kwh": 0.0,
        "bess_discharge_kwh": 0.0,
        "bess_charge_kwh": 0.0,
        "public_pcc_import_kwh": 3490.0,
    }

    result = validate_ieee123_scenario(
        case=case,
        copied_master=copied_master,
        method="test",
        budget_id="test",
        budget=0.0,
        system_trace_id="system-test",
        system_trace_path="trace.json",
        scenario=scenario,
        upgrade_plan=[],
        critical_nodes=set(),
    )

    assert result["converged"] is True
    assert result["minimum_voltage_pu"] == pytest.approx(0.979211, abs=1e-4)
    assert result["maximum_voltage_pu"] <= 1.05
    assert result["line_loading_available"] is False
    assert result["maximum_line_loading_percent"] is None
    assert result["transformer_loading_available"] is True
    assert result["maximum_transformer_loading_percent"] < 100.0
    assert result["regulator_states_json"]
    assert result["capacitor_states_json"]
    assert result["grid_forming_model"] == "none_not_published"
    assert "\n" not in result["engine_version"]
    assert result["engine_version"] == result["engine_version"].strip()
    assert result["ac_valid"] is True


def test_ac_frontier_requires_every_training_scenario_to_be_valid() -> None:
    scenario_rows = pd.DataFrame(
        [
            {
                "budget_id": "b1",
                "budget": 10.0,
                "method": "QCi SC-CMPO",
                "scenario": "s1",
                "ac_valid": True,
                "converged": True,
                "minimum_voltage_pu": 0.96,
                "maximum_voltage_pu": 1.02,
                "voltage_violation_count": 0,
                "feeder_real_power_losses_kw": 2.0,
                "maximum_transformer_loading_percent": 50.0,
                "maximum_line_loading_percent": None,
                "island_balance_residual_kw": 0.01,
                "system_trace_path": "qci.json",
            },
            {
                "budget_id": "b1",
                "budget": 10.0,
                "method": "QCi SC-CMPO",
                "scenario": "s2",
                "ac_valid": False,
                "converged": True,
                "minimum_voltage_pu": 0.94,
                "maximum_voltage_pu": 1.02,
                "voltage_violation_count": 1,
                "feeder_real_power_losses_kw": 3.0,
                "maximum_transformer_loading_percent": 55.0,
                "maximum_line_loading_percent": None,
                "island_balance_residual_kw": 0.02,
                "system_trace_path": "qci.json",
            },
            {
                "budget_id": "b1",
                "budget": 10.0,
                "method": "SLSQP",
                "scenario": "s1",
                "ac_valid": True,
                "converged": True,
                "minimum_voltage_pu": 0.97,
                "maximum_voltage_pu": 1.01,
                "voltage_violation_count": 0,
                "feeder_real_power_losses_kw": 2.5,
                "maximum_transformer_loading_percent": 45.0,
                "maximum_line_loading_percent": None,
                "island_balance_residual_kw": 0.01,
                "system_trace_path": "slsqp.json",
            },
        ]
    )
    budget_rows = pd.DataFrame(
        [
            {"budget_id": "b1", "budget": 10.0, "method": "QCi SC-CMPO", "total_ens": 1.0},
            {"budget_id": "b1", "budget": 10.0, "method": "SLSQP", "total_ens": 2.0},
        ]
    )

    plan_rows = aggregate_ac_validation(scenario_rows)
    frontier = build_ac_valid_budget_frontier(budget_rows, plan_rows)

    assert plan_rows.set_index("method").loc["QCi SC-CMPO", "ac_valid"] == False  # noqa: E712
    assert plan_rows.set_index("method").loc["SLSQP", "ac_valid"] == True  # noqa: E712
    assert frontier["method"].tolist() == ["SLSQP"]
    assert frontier.iloc[0]["ac_scenario_count"] == 1


def test_ac_validation_dry_run_finds_all_headline_budget_plans(tmp_path: Path) -> None:
    result = validate_ieee123_ac_solutions(
        config_path=CONFIG,
        budget_dir=ROOT / "results" / "phase3" / "sc_cmpo" / "budget_frontier",
        output_dir=tmp_path,
        dry_run=True,
    )

    assert result["plan_count"] == 48
    assert result["scenario_validation_count"] == 384
    assert result["method_count"] == 8
    assert result["budget_count"] == 6
    assert not list(tmp_path.iterdir())
