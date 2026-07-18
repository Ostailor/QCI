from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from cmpo.irc_cmpo_feasibility import AnchorFeasibility, LocalPattern
from cmpo.irc_cmpo_master import IRCAsset


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_catalog() -> tuple[tuple[IRCAsset, ...], tuple[AnchorFeasibility, ...]]:
    assets: list[IRCAsset] = []
    anchors: list[AnchorFeasibility] = []
    for anchor_index, anchor in enumerate(("10", "20")):
        rows = (
            IRCAsset(f"{anchor}::pv", anchor, "pv", 10.0 + anchor_index, capacity_kw=5.0),
            IRCAsset(f"{anchor}::bess", anchor, "bess", 12.0 + anchor_index, power_kw=5.0),
            IRCAsset(
                f"{anchor}::gen",
                anchor,
                "dispatchable_generation",
                14.0 + anchor_index,
                capacity_kw=5.0,
            ),
        )
        assets.extend(rows)
        patterns = tuple(
            LocalPattern(pattern, any(pattern), float(sum(pattern) * 5), ("forced_islanding",))
            for pattern in (
                (0, 0, 0),
                (0, 0, 1),
                (0, 1, 0),
                (0, 1, 1),
                (1, 0, 0),
                (1, 0, 1),
                (1, 1, 0),
                (1, 1, 1),
            )
        )
        anchors.append(
            AnchorFeasibility(
                anchor_node=anchor,
                base_load_kw=5.0,
                existing_generation_kw=0.0,
                islanded_base_load_shortfall_kw=5.0,
                asset_keys=tuple(row.asset_key for row in rows),
                patterns=patterns,
                penalty_terms=(),
                rho_feasibility=1.0,
                source_patch_ids=(f"patch-{anchor}",),
            )
        )
    return tuple(assets), tuple(anchors)


def test_candidate_generation_covers_all_seven_public_search_families() -> None:
    module = _load_script("phase3_build_irc_cmpo_dataset.py")
    assets, feasibility = _fixture_catalog()

    frame = module.generate_candidate_portfolios(
        assets,
        feasibility,
        minimum_unique=40,
        random_seed=7,
    )

    assert frame["portfolio_signature"].is_unique
    assert len(frame) == 40
    assert set(module.REQUIRED_PROVENANCE_FAMILIES) <= set(frame["generation_method"])
    exact = frame[frame["generation_method"] == "exact_milp_or_cp_sat"]
    assert not exact.empty
    assert exact["exact_solver_success"].all()
    assert exact["generation_detail"].str.contains("scipy.optimize.milp").all()
    assert not frame["generation_method"].str.contains("synthetic", case=False).any()
    for row in frame.to_dict("records"):
        selected = set(json.loads(row["selected_asset_keys"]))
        for anchor in feasibility:
            pattern = tuple(int(key in selected) for key in anchor.asset_keys)
            assert next(item for item in anchor.patterns if item.pattern == pattern).adequate


def test_dataset_labels_every_row_with_true_recourse_and_writes_create_only(tmp_path: Path) -> None:
    module = _load_script("phase3_build_irc_cmpo_dataset.py")
    assets, feasibility = _fixture_catalog()
    candidates = module.generate_candidate_portfolios(
        assets,
        feasibility,
        minimum_unique=20,
        random_seed=11,
    )
    calls: list[tuple[str, ...]] = []

    def evaluator(selected: tuple[str, ...]):
        calls.append(selected)
        count = len(selected)
        cost = sum(asset.total_cost for asset in assets if asset.asset_key in selected)
        return SimpleNamespace(
            critical_ens=float(20 - count),
            total_ens=float(40 - 2 * count),
            maximum_customers_unserved=float(1 - count / 10),
            critical_infrastructure_outage_hours=float(8 - count / 2),
            critical_load_served_fraction=float(count / 10),
            operating_cost=float(100 - count),
            upgrade_cost=cost,
            heldout_critical_ens=float(22 - count),
            heldout_total_ens=float(44 - 2 * count),
            feasibility=True,
            solver_status="completed",
            selected_solver="SLSQP nonlinear recourse",
            runtime_seconds=0.01,
            patch_count=12,
            training_scenario_count=8,
            heldout_contingency_count=10,
            consensus_algorithm="overlap_consensus_admm",
            projection_scope="full_system_active_power_projection",
            consensus_trace_id="consensus",
            system_trace_id="system",
            heldout_trace_id="heldout",
            solver_paths=(
                "SLSQP nonlinear recourse:completed",
                "piecewise-linear MILP recourse:completed",
            ),
            open_dss_replay="separate",
            selected_asset_keys=selected,
            to_dict=lambda: {},
        )

    result = module.write_labeled_dataset(
        candidates,
        assets=assets,
        evaluator=evaluator,
        output_dir=tmp_path,
        minimum_required=20,
        random_seed=11,
    )

    assert len(calls) == 20
    assert result["successful_true_recourse_labels"] == 20
    labels = pd.read_csv(tmp_path / "portfolio_labels.csv")
    manifest = pd.read_csv(tmp_path / "split_manifest.csv")
    failures = pd.read_csv(tmp_path / "recourse_failures.csv")
    assert len(labels) == 20
    assert failures.empty
    assert set(manifest["split"]) == {"train", "validation", "test"}
    assert manifest["portfolio_signature"].is_unique
    assert labels["true_fixed_upgrade_recourse"].all()
    assert not labels["used_fraction_completion"].any()
    with pytest.raises(FileExistsError):
        module.write_labeled_dataset(
            candidates,
            assets=assets,
            evaluator=evaluator,
            output_dir=tmp_path,
            minimum_required=20,
            random_seed=11,
        )


def test_fit_script_requires_true_recourse_contract_and_writes_versioned_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script("phase3_fit_irc_cmpo_surrogate.py")
    assets, _ = _fixture_catalog()
    catalog = tmp_path / "catalog.csv"
    pd.DataFrame([asset.to_dict() for asset in assets]).to_csv(catalog, index=False)
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "a.json").write_text(
        json.dumps(
            {
                "sc_cmpo": {
                    "upgrade_patch": {"node_ids": ["10"]},
                    "patch_public_nodes": [{"node_id": "10"}],
                }
            }
        ),
        encoding="utf-8",
    )
    rows = []
    for index in range(20):
        selected = tuple(asset.asset_key for bit, asset in enumerate(assets) if (index >> bit) & 1)
        row = {
            "portfolio_signature": f"sig-{index}",
            "selected_asset_keys": json.dumps(selected),
            "upgrade_cost": float(index + 1),
            "critical_ens": float(20 - index),
            "total_ens": float(40 - index),
            "maximum_customers_unserved": float(1 - index / 40),
            "critical_infrastructure_outage_hours": float(10 - index / 4),
            "heldout_total_ens": float(45 - index),
            "technology_mix": "mixed",
            "selected_asset_count": len(selected),
            "true_fixed_upgrade_recourse": True,
            "used_fraction_completion": False,
            "feasibility": True,
            **{asset.asset_key: int(asset.asset_key in selected) for asset in assets},
        }
        rows.append(row)
    labels = tmp_path / "labels.csv"
    pd.DataFrame(rows).to_csv(labels, index=False)
    split = pd.DataFrame(
        {
            "portfolio_signature": [f"sig-{index}" for index in range(20)],
            "split": ["train"] * 12 + ["validation"] * 4 + ["test"] * 4,
        }
    )
    split_path = tmp_path / "split.csv"
    split.to_csv(split_path, index=False)
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            (
                f"source_asset_catalog: {catalog}",
                f"source_payload_dir: {payload_dir}",
                f"output_dir: {tmp_path / 'results'}",
                "surrogate:",
                "  minimum_unique_portfolios: 20",
                "  random_seed: 2026",
                "  group_column: portfolio_signature",
                "  targets: [critical_ens, total_ens, maximum_customers_unserved, critical_infrastructure_outage_hours, heldout_total_ens]",
            )
        ),
        encoding="utf-8",
    )

    fake_manifest = pd.DataFrame(
        {
            "portfolio_signature": [f"sig-{index}" for index in range(20)],
            "split": ["train"] * 12 + ["validation"] * 4 + ["test"] * 4,
        }
    )
    fake_model = SimpleNamespace(
        targets={
            target: SimpleNamespace(
                terms=({"coefficient": 1.0, "asset_keys": [], "degree": 0},),
                metrics={
                    "mae": 0.0,
                    "normalized_rmse": 0.0,
                    "r2": 1.0,
                    "spearman_rank_correlation": 1.0,
                    "top_decile_recall": 1.0,
                    "pareto_front_recall": 1.0,
                    "calibration_by_upgrade_cost_band": [],
                    "gate_passed": True,
                },
                target_column=target,
                ridge=1e-6,
            )
            for target in module.REQUIRED_TARGETS
        },
        split_manifest=fake_manifest,
        gates_passed=True,
        to_dict=lambda: {"targets": {}, "gates_passed": True},
    )
    monkeypatch.setattr(module, "fit_multi_target_surrogates", lambda *args, **kwargs: fake_model)
    monkeypatch.setattr(module, "physical_interactions", lambda *args, **kwargs: ([], [], {}))
    output = tmp_path / "surrogate"
    output.mkdir()
    failed_v1 = output / "surrogate_model_final_prequeue_v1.json"
    failed_v1.write_text('{"gates_passed": false}\n', encoding="utf-8")

    result = module.fit_surrogate_file(
        config,
        labels,
        split_manifest_path=split_path,
        output_dir=output,
    )

    assert result["surrogate_valid"] is True
    assert failed_v1.read_text(encoding="utf-8") == '{"gates_passed": false}\n'
    assert (output / "surrogate_model_final_prequeue_v2.json").exists()
    assert (output / "surrogate_metrics_final_prequeue_v2.csv").exists()
    assert (output / "surrogate_calibration_final_prequeue_v2.csv").exists()
    assert (output / "split_manifest_final_prequeue_v2.csv").exists()
    with pytest.raises(FileExistsError):
        module.fit_surrogate_file(
            config,
            labels,
            split_manifest_path=split_path,
            output_dir=output,
        )

    broken = pd.read_csv(labels)
    broken.loc[0, "true_fixed_upgrade_recourse"] = False
    broken_path = tmp_path / "broken.csv"
    broken.to_csv(broken_path, index=False)
    with pytest.raises(ValueError, match="true fixed-upgrade recourse"):
        module.fit_surrogate_file(
            config,
            broken_path,
            split_manifest_path=split_path,
            output_dir=tmp_path / "broken-output",
        )
