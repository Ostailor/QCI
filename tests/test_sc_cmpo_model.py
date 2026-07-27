from __future__ import annotations

from pathlib import Path

import pytest

from cmpo.scenario_coupled_model import (
    RECOURSE_GROUPS,
    SHARED_VARIABLES,
    build_sc_cmpo_from_config,
    load_public_grid,
    load_sc_cmpo_config,
)
from cmpo.upgrade_planning import load_atb_cost_catalog


CONFIGS = (
    Path("configs/phase3_sc_cmpo_case14.yaml"),
    Path("configs/phase3_sc_cmpo_case30.yaml"),
    Path("configs/phase3_sc_cmpo_arpae.yaml"),
    Path("configs/phase3_sc_cmpo_ieee123.yaml"),
)


def test_pinned_atb_catalog_has_three_positive_public_costs() -> None:
    catalog = load_atb_cost_catalog("data/upstream/nrel-atb/ATBe_2024_v3_selected_costs.csv")

    assert set(catalog) == {"pv", "bess", "dispatchable_generation"}
    assert all(cost.cost_per_kw > 0.0 for cost in catalog.values())
    assert catalog["bess"].duration_hours == 4.0
    assert catalog["bess"].cost_per_kwh == pytest.approx(481.68)
    assert all(len(cost.source_sha256) == 64 for cost in catalog.values())


@pytest.mark.parametrize("config_path", CONFIGS)
def test_public_adapters_build_source_faithful_grids(config_path: Path) -> None:
    config = load_sc_cmpo_config(config_path)
    grid = load_public_grid(config)

    assert grid.nodes
    assert grid.edges
    assert len(grid.source_sha256) == 64
    assert grid.source_url.startswith("https://")
    assert grid.source_version
    assert grid.source_license
    assert grid.transformation
    assert any(node.load_kw > 0.0 for node in grid.nodes)


@pytest.mark.parametrize("config_path", CONFIGS)
def test_sc_cmpo_payload_is_multiscenario_normalized_and_qci_fit(config_path: Path) -> None:
    results = build_sc_cmpo_from_config(config_path)

    assert results
    for result in results:
        payload = result.payload
        stats = payload["model_statistics"]
        sc_cmpo = payload["sc_cmpo"]
        assert payload["schema"] == "cmpo.sc_cmpo.v1"
        assert stats["variable_count"] <= 132
        assert stats["degree"] == 3
        assert sc_cmpo["scenario_count"] >= 6
        assert sc_cmpo["shared_first_stage_variable_count"] == len(SHARED_VARIABLES)
        assert sc_cmpo["recourse_variable_count"] == len(RECOURSE_GROUPS) * sc_cmpo["scenario_count"]
        assert stats["variable_count"] == sc_cmpo["shared_first_stage_variable_count"] + sc_cmpo["recourse_variable_count"]
        assert result.upgrade_plan.patch.islanded_deficit_kw > 0.0
        assert result.upgrade_plan.minimum_resilient_upgrade_cost > 0.0
        assert set(sc_cmpo["challenge_stages"]) == {
            "upgrade_planning",
            "pre_event_preparedness",
            "emergency_response",
            "restoration",
        }
        assert sc_cmpo["input_policy"]["public_inputs_only"] is True
        assert sc_cmpo["input_policy"]["random_topology_or_asset_values"] is False
        assert sc_cmpo["input_policy"]["undocumented_synthetic_values"] == []
        assert all(variable["bounds"] == [0.0, 1.0] for variable in payload["variables"])
        assert max(abs(term["coefficient"]) for term in payload["polynomial_terms"]) <= 1.0 + 1e-12


def test_sc_cmpo_build_is_deterministic() -> None:
    first = build_sc_cmpo_from_config(CONFIGS[0])
    second = build_sc_cmpo_from_config(CONFIGS[0])

    assert [result.payload for result in first] == [result.payload for result in second]
