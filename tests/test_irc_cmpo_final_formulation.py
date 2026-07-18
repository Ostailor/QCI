from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "results/phase3/sc_cmpo/budget_master_v2/public_asset_catalog.csv"


def _toy_assets():
    from cmpo.irc_cmpo_master import IRCAsset

    return (
        IRCAsset("a::pv", "a", "pv", 4.0, capacity_kw=4.0, power_kw=4.0),
        IRCAsset("a::bess", "a", "bess", 5.0, power_kw=5.0, energy_kwh=20.0),
        IRCAsset("a::gen", "a", "dispatchable_generation", 3.0, capacity_kw=3.0, power_kw=3.0),
    )


def test_scalarized_master_uses_catalog_cost_and_no_budget_or_blanket_coverage() -> None:
    from cmpo.irc_cmpo_master import build_scalarized_irc_master, load_catalog

    assets = load_catalog(CATALOG)
    maximum_cost = sum(asset.total_cost for asset in assets)
    feasibility_terms = [
        {
            "coefficient": 1.0,
            "asset_keys": [assets[0].asset_key, assets[1].asset_key, assets[2].asset_key],
            "pattern": [0, 0, 0],
            "anchor_node": assets[0].anchor_node,
        }
    ]
    payload = build_scalarized_irc_master(
        assets,
        cost_weight=0.25,
        surrogate_terms=[{"coefficient": -1.0, "asset_keys": [assets[0].asset_key]}],
        local_feasibility_terms=feasibility_terms,
    )

    assert payload["num_variables"] == 33
    assert payload["num_levels"] == [2] * 33
    assert payload["max_degree"] <= 3
    assert "exact_budget_constraint" not in payload
    assert not any(term["component"] in {"coverage", "hard_budget"} for term in payload["polynomial_terms"])
    assert any(term["component"] == "local_feasibility" for term in payload["polynomial_terms"])
    assert payload["cost_scalarization"]["maximum_catalog_portfolio_cost"] == pytest.approx(maximum_cost)
    cost_term = next(
        term
        for term in payload["polynomial_terms"]
        if term["component"] == "normalized_cost"
        and list(term["powers"]) == [f"y::{assets[0].asset_key}"]
    )
    assert cost_term["coefficient"] == pytest.approx(0.25 * assets[0].total_cost / maximum_cost)


def test_scalarized_decode_accepts_data_derived_feasibility_without_budget_projection() -> None:
    from cmpo.irc_cmpo_decode import decode_native_sample
    from cmpo.irc_cmpo_master import build_scalarized_irc_master

    assets = _toy_assets()
    payload = build_scalarized_irc_master(
        assets,
        cost_weight=1.0,
        surrogate_terms=[],
        local_feasibility_terms=[
            {
                "coefficient": 1.0,
                "asset_keys": [asset.asset_key for asset in assets],
                "pattern": [0, 0, 0],
                "anchor_node": "a",
            }
        ],
    )
    empty = [0, 0, 0]
    with pytest.raises(ValueError, match="local feasibility"):
        decode_native_sample(payload, empty)
    selected = decode_native_sample(payload, [0, 0, 1])
    assert selected.selected_asset_keys == ("a::pv",)
    assert selected.total_cost == 4.0
    assert selected.projection_used is False


def _surrogate_frame(count: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    rows = []
    for index in range(count):
        bits = rng.integers(0, 2, size=6)
        total = 100.0 - 12.0 * bits[0] - 8.0 * bits[1] - 14.0 * bits[2] * bits[3]
        maximum = 0.8 - 0.15 * bits[0] - 0.10 * bits[4]
        outage = 8.0 - 2.0 * bits[1] - 1.0 * bits[2] * bits[5]
        rows.append(
            {
                "portfolio_signature": f"p{index:04d}",
                **{f"x{i}": int(value) for i, value in enumerate(bits)},
                "upgrade_cost": 10.0 + float(np.dot(bits, np.arange(1, 7))),
                "technology_mix": f"{bits[0]}{bits[1]}{bits[2]}",
                "selected_asset_count": int(bits.sum()),
                "critical_ens": 25.0,
                "total_ens": total,
                "maximum_customers_unserved": maximum,
                "critical_infrastructure_outage_hours": outage,
                "heldout_total_ens": 1.1 * total + 2.0,
            }
        )
    return pd.DataFrame(rows)


def test_multitarget_surrogate_uses_60_20_20_split_and_required_metrics() -> None:
    from cmpo.irc_cmpo_surrogate import fit_multi_target_surrogates

    frame = _surrogate_frame()
    fit = fit_multi_target_surrogates(
        frame,
        asset_columns=[f"x{i}" for i in range(6)],
        pair_interactions=[("x2", "x3")],
        cubic_interactions=[],
        target_columns=[
            "critical_ens",
            "total_ens",
            "maximum_customers_unserved",
            "critical_infrastructure_outage_hours",
            "heldout_total_ens",
        ],
        minimum_portfolios=100,
        random_seed=9,
    )

    manifest = fit.split_manifest
    assert manifest["portfolio_signature"].nunique() == len(frame)
    assert manifest.groupby("portfolio_signature")["split"].nunique().max() == 1
    assert manifest["split"].value_counts().to_dict() == {"train": 300, "validation": 100, "test": 100}
    assert fit.targets["critical_ens"].metrics["nearly_constant"] is True
    for target, model in fit.targets.items():
        assert model.metrics["degree"] <= 3
        assert "mae" in model.metrics
        assert "normalized_rmse" in model.metrics
        assert "r2" in model.metrics
        assert "spearman_rank_correlation" in model.metrics
        assert "top_decile_recall" in model.metrics
        assert "pareto_front_recall" in model.metrics
        assert model.metrics["calibration_by_upgrade_cost_band"]
        if target != "critical_ens":
            assert model.metrics["normalized_rmse"] <= 0.20
    assert fit.gates_passed is True


def test_final_config_declares_six_cost_weights_and_no_hard_budget() -> None:
    import yaml

    config = yaml.safe_load((ROOT / "configs/phase3_irc_cmpo_ieee123.yaml").read_text())
    assert len(config["scalarization"]["cost_weights"]) == 6
    assert config["scalarization"]["cost_weight_derivation"] == (
        "catalog_minimum_cost_fraction_times_two_or_more_dirac3_200_level_grid_steps"
    )
    assert config["scalarization"]["cost_weight_multipliers"] == [0, 2, 4, 8, 16, 32]
    assert config["scalarization"]["resilience_normalization"] == "training_total_ens_range"
    assert config["scalarization"]["cost_denominator"] == "maximum_catalog_portfolio_cost"
    assert config["scalarization"]["hard_budget"] is False
    assert config["surrogate"]["split_fractions"] == {"train": 0.6, "validation": 0.2, "test": 0.2}
    assert config["scaling"]["maximum_dynamic_range"] == 200
    assert config["qci"]["submission_permitted"] is False


def test_training_normalization_and_cost_weights_are_data_derived(tmp_path: Path) -> None:
    import importlib.util

    path = ROOT / "scripts/phase3_build_irc_cmpo_payloads.py"
    spec = importlib.util.spec_from_file_location("irc_payload_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    dataset = tmp_path / "labels.csv"
    split = tmp_path / "split.csv"
    pd.DataFrame(
        [
            {"portfolio_signature": "a", "total_ens": 20.0},
            {"portfolio_signature": "b", "total_ens": 50.0},
            {"portfolio_signature": "c", "total_ens": 999.0},
        ]
    ).to_csv(dataset, index=False)
    pd.DataFrame(
        [
            {"portfolio_signature": "a", "split": "train"},
            {"portfolio_signature": "b", "split": "train"},
            {"portfolio_signature": "c", "split": "test"},
        ]
    ).to_csv(split, index=False)

    normalization = module.derive_training_target_normalization(dataset, split)
    assert normalization["offset"] == 20.0
    assert normalization["scale"] == 30.0
    normalized = module.normalize_surrogate_terms(
        [
            {"coefficient": 50.0, "asset_keys": []},
            {"coefficient": -15.0, "asset_keys": ["a"]},
        ],
        offset=normalization["offset"],
        scale=normalization["scale"],
    )
    assert normalized[0]["coefficient"] == pytest.approx(1.0)
    assert normalized[1]["coefficient"] == pytest.approx(-0.5)

    assets = _toy_assets()
    weights = module.derive_hardware_resolvable_cost_weights(
        assets, effective_dynamic_range=200, multipliers=[0, 2, 4, 8, 16, 32]
    )
    expected_minimum = sum(asset.total_cost for asset in assets) / (200.0 * 3.0)
    assert weights["minimum_resolvable_lambda"] == pytest.approx(expected_minimum)
    assert weights["weights"] == pytest.approx(
        [0.0, 2 * expected_minimum, 4 * expected_minimum, 8 * expected_minimum,
         16 * expected_minimum, 32 * expected_minimum]
    )


def test_smoke_commands_require_final_offline_yes() -> None:
    import importlib.util

    path = ROOT / "scripts/phase3_run_irc_cmpo_smoke.py"
    spec = importlib.util.spec_from_file_location("irc_smoke_commands", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payloads = {
        "toy": "toy.json",
        "reduced_ieee123": "reduced.json",
        "full_ieee123": "full.json",
    }
    with pytest.raises(ValueError, match="not ready"):
        module.generate_approved_commands(
            {"IRC_CMPO_READY_FOR_QCI": "NO"}, payloads, config_path="config.yaml"
        )
    commands = module.generate_approved_commands(
        {"IRC_CMPO_READY_FOR_QCI": "YES"}, payloads, config_path="config.yaml"
    )
    assert len(commands) == 3
    assert all("--num-samples 30" in command for command in commands)
    assert all("phase3_run_qci_integer.py" in command for command in commands)
    assert not any("six-lambda" in command for command in commands)
