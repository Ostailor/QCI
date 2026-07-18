from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmpo.irc_cmpo_feasibility import (
    derive_local_feasibility,
    ineffective_assets,
    verify_local_feasibility_encoding,
)
from cmpo.irc_cmpo_master import load_catalog
from cmpo.irc_cmpo_recourse import (
    FixedRecourseCache,
    evaluate_fixed_upgrade_recourse,
    fix_upgrade_bounds,
    portfolio_scenario_effects,
)
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "results/phase3/sc_cmpo/ieee123/qci_payloads"
CONFIG = ROOT / "configs/phase3_sc_cmpo_ieee123.yaml"


@pytest.fixture(scope="module")
def public_case() -> tuple[dict[str, dict], tuple, object]:
    payloads = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(PAYLOAD_DIR.glob("*.json"))
    }
    assets = load_catalog(PAYLOAD_DIR)
    grid = load_public_grid(load_sc_cmpo_config(CONFIG))
    assert len(payloads) == 12
    assert len(assets) == 33
    return payloads, assets, grid


def _asset_keys(assets: tuple, technology: str) -> tuple[str, ...]:
    return tuple(asset.asset_key for asset in assets if asset.technology == technology)


def test_local_feasibility_exactly_encodes_all_eight_public_patterns(public_case) -> None:
    payloads, assets, _grid = public_case
    anchors = derive_local_feasibility(payloads, assets, rho_feasibility=7.0)

    assert len(anchors) == 11
    assert all(len(anchor.patterns) == 8 for anchor in anchors)
    assert all(max(term.degree for term in anchor.penalty_terms) <= 3 for anchor in anchors)
    assert all(verify_local_feasibility_encoding(anchor) for anchor in anchors)
    assert all(anchor.existing_generation_kw == 0.0 for anchor in anchors)

    sample = next(anchor for anchor in anchors if anchor.anchor_node == "76")
    by_pattern = {row.pattern: row for row in sample.patterns}
    assert by_pattern[(0, 0, 0)].adequate is False
    assert by_pattern[(0, 0, 1)].adequate is True
    assert by_pattern[(0, 1, 0)].adequate is True
    assert by_pattern[(1, 0, 0)].adequate is False  # PV is unavailable in combined stress.


def test_upgrade_fixes_are_real_equal_bounds_and_never_fraction_completion(public_case) -> None:
    payloads, assets, _grid = public_case
    selected = {_asset_keys(assets, "dispatchable_generation")[0]}
    fixed = fix_upgrade_bounds(payloads, assets, selected)

    assert len(fixed) == 12
    for record in fixed.values():
        variables = {row["name"]: row for row in record.payload["variables"]}
        for name in (
            "upgrade_select_pv",
            "upgrade_select_bess",
            "upgrade_select_dispatchable",
            "pv_capacity_fraction",
            "bess_energy_fraction",
            "bess_power_fraction",
            "dispatchable_capacity_fraction",
        ):
            assert variables[name]["lower_bound"] == variables[name]["upper_bound"]
        assert record.fixed_by == "exact_variable_bounds"
        assert record.used_fraction_completion is False


def test_materially_different_portfolios_do_not_automatically_match_recourse(public_case) -> None:
    payloads, assets, grid = public_case
    empty = evaluate_fixed_upgrade_recourse(payloads, assets, (), grid=grid, heldout_limit=10)
    dispatch = evaluate_fixed_upgrade_recourse(
        payloads,
        assets,
        _asset_keys(assets, "dispatchable_generation"),
        grid=grid,
        heldout_limit=10,
    )

    assert empty.total_ens != dispatch.total_ens
    assert empty.metric_signature != dispatch.metric_signature
    assert dispatch.patch_count == 12
    assert dispatch.training_scenario_count == 8
    assert dispatch.heldout_contingency_count == 10
    assert dispatch.consensus_algorithm == "overlap_consensus_admm"
    assert dispatch.projection_scope == "full_system_active_power_projection"


def test_adding_useful_dispatchable_asset_does_not_worsen_ens(public_case) -> None:
    payloads, assets, grid = public_case
    key = next(asset.asset_key for asset in assets if asset.anchor_node == "76" and asset.technology == "dispatchable_generation")
    without = evaluate_fixed_upgrade_recourse(payloads, assets, (), grid=grid, heldout_limit=10)
    with_asset = evaluate_fixed_upgrade_recourse(payloads, assets, (key,), grid=grid, heldout_limit=10)

    assert with_asset.total_ens <= without.total_ens + 1e-8
    assert with_asset.critical_ens <= without.critical_ens + 1e-8


def test_removing_capacity_from_binding_island_cannot_improve_ens(public_case) -> None:
    payloads, assets, grid = public_case
    key = next(asset.asset_key for asset in assets if asset.anchor_node == "76" and asset.technology == "dispatchable_generation")
    full = evaluate_fixed_upgrade_recourse(payloads, assets, (key,), grid=grid, heldout_limit=10)
    reduced = evaluate_fixed_upgrade_recourse(
        payloads,
        assets,
        (key,),
        grid=grid,
        capacity_fractions={key: 0.25},
        heldout_limit=10,
    )

    assert reduced.total_ens >= full.total_ens - 1e-8
    assert reduced.critical_ens >= full.critical_ens - 1e-8


def test_every_public_master_asset_changes_a_recourse_metric(public_case) -> None:
    payloads, assets, _grid = public_case
    effects = portfolio_scenario_effects(payloads, assets)

    assert set(effects) == {asset.asset_key for asset in assets}
    assert all(effect.measurable for effect in effects.values())
    assert all(effect.affected_scenarios for effect in effects.values())


def test_ineffective_assets_are_identified_for_master_removal(public_case) -> None:
    payloads, assets, _grid = public_case
    assert ineffective_assets(portfolio_scenario_effects(payloads, assets)) == ()


def test_fixed_patch_solver_cache_reuses_identical_public_subproblems(
    public_case, monkeypatch
) -> None:
    import cmpo.irc_cmpo_recourse as recourse

    payloads, assets, grid = public_case
    original = recourse._solve_patch
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(recourse, "_solve_patch", counted)
    cache = FixedRecourseCache()
    evaluate_fixed_upgrade_recourse(payloads, assets, (), grid=grid, solver_cache=cache)
    first_calls = calls
    evaluate_fixed_upgrade_recourse(payloads, assets, (), grid=grid, solver_cache=cache)

    assert first_calls == 24  # 12 patches times two independent solver paths.
    assert calls == first_calls
    assert cache.hits == 24
