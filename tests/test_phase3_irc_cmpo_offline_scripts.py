from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from cmpo.irc_cmpo_feasibility import AnchorFeasibility, FeasibilityTerm, LocalPattern
from cmpo.irc_cmpo_master import IRCAsset


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assets() -> tuple[IRCAsset, ...]:
    return (
        IRCAsset("a::pv", "a", "pv", 4.0, capacity_kw=4.0),
        IRCAsset("a::bess", "a", "bess", 5.0, power_kw=5.0, energy_kwh=20.0),
        IRCAsset("a::gen", "a", "dispatchable_generation", 3.0, capacity_kw=3.0),
    )


def _feasibility() -> tuple[AnchorFeasibility, ...]:
    patterns = tuple(
        LocalPattern(pattern, any(pattern), float(5 * sum(pattern)), ("island",))
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
    asset_keys = tuple(asset.asset_key for asset in _assets())
    penalty_terms = (
        FeasibilityTerm(1.0, (), 0, "a", (0, 0, 0)),
        *(
            FeasibilityTerm(-1.0, (key,), 1, "a", (0, 0, 0))
            for key in asset_keys
        ),
        *(
            FeasibilityTerm(1.0, tuple(sorted((asset_keys[left], asset_keys[right]))), 2, "a", (0, 0, 0))
            for left, right in ((0, 1), (0, 2), (1, 2))
        ),
        FeasibilityTerm(-1.0, tuple(sorted(asset_keys)), 3, "a", (0, 0, 0)),
    )
    return (
        AnchorFeasibility(
            anchor_node="a",
            base_load_kw=5.0,
            existing_generation_kw=0.0,
            islanded_base_load_shortfall_kw=5.0,
            asset_keys=asset_keys,
            patterns=patterns,
            penalty_terms=penalty_terms,
            rho_feasibility=1.0,
            source_patch_ids=("patch-a",),
        ),
    )


def _write_inputs(tmp_path: Path, *, gates_passed: bool = True) -> tuple[Path, Path, Path, Path]:
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            (
                f"source_asset_catalog: {tmp_path / 'catalog.csv'}",
                f"source_payload_dir: {tmp_path / 'public-payloads'}",
                f"output_dir: {tmp_path / 'results'}",
                "model:",
                "  core_binary_variables: 3",
                "scalarization:",
                "  cost_weights: [0.0, 0.04, 0.08, 0.16, 0.32, 0.64]",
                "  cost_weight_multipliers: [0, 2, 4, 8, 16, 32]",
                "  hard_budget: false",
                "surrogate:",
                "  master_objective_target: total_ens",
                "  gates:",
                "    total_ens_spearman_minimum: 0.8",
                "    normalized_rmse_maximum: 0.2",
                "    top_decile_recall_minimum: 0.7",
                "    pareto_front_recall_minimum: 0.7",
                "scaling:",
                "  maximum_dynamic_range: 200",
                "offline_validation:",
                "  exact_top_k: 10",
                "  stochastic:",
                "    methods: [integer_simulated_annealing, random_restart, local_coordinate_search]",
            )
        ),
        encoding="utf-8",
    )
    pd.DataFrame([asset.to_dict() for asset in _assets()]).to_csv(tmp_path / "catalog.csv", index=False)
    public_payloads = tmp_path / "public-payloads"
    public_payloads.mkdir()
    for index in range(12):
        (public_payloads / f"patch-{index}.json").write_text("{}", encoding="utf-8")
    rows = []
    for index, bits in enumerate(
        ((0, 0, 1), (0, 1, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1))
    ):
        selected = [asset.asset_key for asset, bit in zip(_assets(), bits, strict=True) if bit]
        rows.append(
            {
                "portfolio_signature": f"p-{index}",
                "selected_asset_keys": json.dumps(selected),
                "upgrade_cost": sum(asset.total_cost for asset, bit in zip(_assets(), bits, strict=True) if bit),
                "total_ens": 100.0 - 10.0 * sum(bits),
                **{asset.asset_key: bit for asset, bit in zip(_assets(), bits, strict=True)},
            }
        )
    dataset = tmp_path / "labels.csv"
    pd.DataFrame(rows).to_csv(dataset, index=False)
    split = tmp_path / "split.csv"
    pd.DataFrame(
        {
            "portfolio_signature": [row["portfolio_signature"] for row in rows],
            "split": ["train"] * 3 + ["test"] * 4,
        }
    ).to_csv(split, index=False)
    metrics = {
        "normalized_rmse": 0.0,
        "spearman_rank_correlation": 1.0,
        "top_decile_recall": 1.0,
        "pareto_front_recall": 1.0,
        "gate_passed": gates_passed,
        "all_coefficients_finite": True,
        "degree": 1,
    }
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "schema": "cmpo.irc_cmpo.multi_target_surrogate.final_prequeue.v1",
                "gates_passed": gates_passed,
                "maximum_degree": 1,
                "targets": {
                    target: {
                        "terms": (
                            [
                                {"coefficient": 100.0, "asset_keys": [], "degree": 0},
                                *[
                                    {"coefficient": -10.0, "asset_keys": [asset.asset_key], "degree": 1}
                                    for asset in _assets()
                                ],
                            ]
                            if target == "total_ens"
                            else [{"coefficient": 1.0, "asset_keys": [], "degree": 0}]
                        ),
                        "metrics": metrics,
                    }
                    for target in (
                        "critical_ens",
                        "total_ens",
                        "maximum_customers_unserved",
                        "critical_infrastructure_outage_hours",
                        "heldout_total_ens",
                    )
                },
            }
        ),
        encoding="utf-8",
    )
    return config, dataset, split, model


def test_payload_builder_refuses_failed_surrogate_before_writing(tmp_path: Path) -> None:
    module = _load_script("phase3_build_irc_cmpo_payloads.py")
    config, dataset, split, model = _write_inputs(tmp_path, gates_passed=False)

    with pytest.raises(ValueError, match="surrogate gates"):
        module.build_payloads(
            config,
            dataset_path=dataset,
            split_manifest_path=split,
            surrogate_model_path=model,
            output_dir=tmp_path / "out",
        )

    assert not (tmp_path / "out").exists()


def test_payload_builder_recomputes_surrogate_metric_gate_contract(tmp_path: Path) -> None:
    module = _load_script("phase3_build_irc_cmpo_payloads.py")
    config, dataset, split, model = _write_inputs(tmp_path)
    value = json.loads(model.read_text(encoding="utf-8"))
    value["targets"]["total_ens"]["metrics"]["spearman_rank_correlation"] = 0.79
    value["targets"]["total_ens"]["metrics"]["gate_passed"] = True
    value["gates_passed"] = True
    model.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="surrogate gates failed for total_ens"):
        module.build_payloads(
            config,
            dataset_path=dataset,
            split_manifest_path=split,
            surrogate_model_path=model,
            output_dir=tmp_path / "out",
        )


def test_post_quantization_actual_includes_lambda_normalized_catalog_cost() -> None:
    module = _load_script("phase3_build_irc_cmpo_payloads.py")

    values = module._scalarized_validation_actual(
        [100.0, 80.0], [20.0, 50.0], cost_weight=0.5, maximum_catalog_cost=100.0
    )

    assert values == pytest.approx([100.1, 80.25])


def test_payload_builder_writes_six_scaled_create_only_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script("phase3_build_irc_cmpo_payloads.py")
    config, dataset, split, model = _write_inputs(tmp_path)
    monkeypatch.setattr(module, "derive_local_feasibility", lambda *args, **kwargs: _feasibility())
    output = tmp_path / "out"
    output.mkdir()
    failed_v1 = output / "payload_manifest_final_prequeue_v1.csv"
    failed_v1.write_text("status\nfailed\n", encoding="utf-8")

    result = module.build_payloads(
        config,
        dataset_path=dataset,
        split_manifest_path=split,
        surrogate_model_path=model,
        output_dir=output,
    )

    assert result["payload_count"] == 6
    assert result["qci_jobs_submitted"] == 0
    assert failed_v1.read_text(encoding="utf-8") == "status\nfailed\n"
    manifest = pd.read_csv(output / "payload_manifest_final_prequeue_v3.csv")
    assert len(manifest) == 6
    assert manifest["post_quantization_gates_passed"].all()
    for path in manifest["scaled_payload_path"]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert payload["num_variables"] == 3
        assert payload["max_degree"] <= 3
        assert payload["dirac3_scaling"]["audit"]["dynamic_range"] <= 200
        assert payload["cost_scalarization"]["hard_budget"] is False
    with pytest.raises(FileExistsError):
        module.build_payloads(
            config,
            dataset_path=dataset,
            split_manifest_path=split,
            surrogate_model_path=model,
            output_dir=output,
        )


def test_payload_builder_refuses_unverified_local_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script("phase3_build_irc_cmpo_payloads.py")
    config, dataset, split, model = _write_inputs(tmp_path)
    broken = _feasibility()[0]
    broken = AnchorFeasibility(
        anchor_node=broken.anchor_node,
        base_load_kw=broken.base_load_kw,
        existing_generation_kw=broken.existing_generation_kw,
        islanded_base_load_shortfall_kw=broken.islanded_base_load_shortfall_kw,
        asset_keys=broken.asset_keys,
        patterns=broken.patterns,
        penalty_terms=(),
        rho_feasibility=broken.rho_feasibility,
        source_patch_ids=broken.source_patch_ids,
    )
    monkeypatch.setattr(module, "derive_local_feasibility", lambda *args, **kwargs: (broken,))

    with pytest.raises(ValueError, match="local-feasibility encoding"):
        module.build_payloads(
            config,
            dataset_path=dataset,
            split_manifest_path=split,
            surrogate_model_path=model,
            output_dir=tmp_path / "out",
        )


def test_offline_validator_uses_shared_recourse_cache_and_never_submits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_script("phase3_build_irc_cmpo_payloads.py")
    validator = _load_script("phase3_validate_irc_cmpo_offline.py")
    config, dataset, split, model = _write_inputs(tmp_path)
    monkeypatch.setattr(builder, "derive_local_feasibility", lambda *args, **kwargs: _feasibility())
    built = builder.build_payloads(
        config,
        dataset_path=dataset,
        split_manifest_path=split,
        surrogate_model_path=model,
        output_dir=tmp_path / "build",
    )
    cache_ids: list[int] = []

    def fake_recourse(_payloads, assets, selected, *, grid, heldout_limit, solver_cache):
        cache_ids.append(id(solver_cache))
        count = len(selected)
        return SimpleNamespace(
            total_ens=100.0 - 10.0 * count,
            critical_ens=20.0 - count,
            maximum_customers_unserved=1.0 - count / 10.0,
            critical_infrastructure_outage_hours=8.0 - count,
            heldout_total_ens=110.0 - 10.0 * count,
            heldout_critical_ens=22.0 - count,
            upgrade_cost=sum(asset.total_cost for asset in assets if asset.asset_key in selected),
            feasibility=True,
        )

    monkeypatch.setattr(validator, "evaluate_fixed_upgrade_recourse", fake_recourse)
    monkeypatch.setattr(validator, "load_public_grid", lambda _config: object())
    monkeypatch.setattr(validator, "load_sc_cmpo_config", lambda _path: object())
    validation_output = tmp_path / "validation"
    validation_output.mkdir()
    failed_v1 = validation_output / "exact_validation_final_prequeue_v1.json"
    failed_v1.write_text('{"suite": "failed"}\n', encoding="utf-8")

    result = validator.validate_offline(
        config,
        manifest_path=built["manifest_path"],
        dataset_path=dataset,
        output_dir=validation_output,
        stochastic_samples_per_method=2,
        stochastic_sweeps=3,
    )

    assert result["lambda_count"] == 6
    assert result["qci_jobs_submitted"] == 0
    assert len(set(cache_ids)) == 1
    assert failed_v1.read_text(encoding="utf-8") == '{"suite": "failed"}\n'
    assert (validation_output / "exact_validation_final_prequeue_v4.json").exists()
    assert (validation_output / "stochastic_validation_final_prequeue_v4.json").exists()
    assert (validation_output / "exact_candidates_final_prequeue_v4.csv").exists()
    assert (validation_output / "stochastic_samples_final_prequeue_v4.csv").exists()
    with pytest.raises(FileExistsError):
        validator.validate_offline(
            config,
            manifest_path=built["manifest_path"],
            dataset_path=dataset,
            output_dir=validation_output,
            stochastic_samples_per_method=2,
            stochastic_sweeps=3,
        )


def test_offline_validator_rejects_infeasible_true_recourse() -> None:
    module = _load_script("phase3_validate_irc_cmpo_offline.py")
    result = SimpleNamespace(
        total_ens=10.0,
        critical_ens=2.0,
        maximum_customers_unserved=0.2,
        critical_infrastructure_outage_hours=1.0,
        heldout_total_ens=11.0,
        heldout_critical_ens=2.2,
        upgrade_cost=5.0,
        feasibility=False,
    )

    with pytest.raises(ValueError, match="infeasible"):
        module._result_metrics(result, cost_weight=0.1, maximum_catalog_cost=20.0)
