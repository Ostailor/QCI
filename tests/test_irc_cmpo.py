from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "results/phase3/sc_cmpo/budget_master_v2/public_asset_catalog.csv"


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _toy_assets():
    from cmpo.irc_cmpo_master import IRCAsset

    return (
        IRCAsset("a::pv", "a", "pv", 4.0),
        IRCAsset("a::bess", "a", "bess", 5.0),
        IRCAsset("a::gen", "a", "dispatchable_generation", 3.0),
        IRCAsset("b::pv", "b", "pv", 4.0),
        IRCAsset("b::bess", "b", "bess", 5.0),
        IRCAsset("b::gen", "b", "dispatchable_generation", 3.0),
    )


def test_master_uses_one_binary_per_physical_asset_and_cubic_coverage() -> None:
    from cmpo.irc_cmpo_master import build_irc_master, load_catalog

    assets = load_catalog(CATALOG)
    payload = build_irc_master(
        assets,
        budget=2_000_000.0,
        lagrange_lambda=0.25,
        surrogate_terms=[{"coefficient": -1.0, "asset_keys": [assets[0].asset_key]}],
    )
    assert len(assets) == len(payload["variables"]) == 33
    assert all(v["encoding_type"] == "binary" for v in payload["variables"])
    assert all(v["lower_bound"] == 0 and v["upper_bound"] == 1 for v in payload["variables"])
    assert all("not_selected" not in v["name"] and "slack" not in v["name"] for v in payload["variables"])
    assert payload["num_levels"] == [2] * 33
    assert payload["max_degree"] == 3
    coverage = [t for t in payload["polynomial_terms"] if t["component"] == "coverage"]
    assert any(t["degree"] == 3 for t in coverage)
    assert not any(t["component"] == "hard_budget" for t in payload["polynomial_terms"])
    cost = [t for t in payload["polynomial_terms"] if t["component"] == "normalized_cost"]
    expected = 0.25 * assets[0].total_cost / 2_000_000.0
    first = next(t for t in cost if list(t["powers"]) == [f"y::{assets[0].asset_key}"])
    assert first["coefficient"] == pytest.approx(expected)


def test_native_decode_never_projects_and_rejects_budget_or_coverage() -> None:
    from cmpo.irc_cmpo_decode import decode_native_sample
    from cmpo.irc_cmpo_master import build_irc_master

    payload = build_irc_master(_toy_assets(), budget=6.0, lagrange_lambda=1.0, surrogate_terms=[])
    valid = {v["name"]: 0 for v in payload["variables"]}
    valid["y::a::gen"] = 1
    valid["y::b::gen"] = 1
    decoded = decode_native_sample(payload, valid)
    assert decoded.selected_asset_keys == ("a::gen", "b::gen")
    assert decoded.total_cost == 6.0
    assert decoded.projection_used is False
    with pytest.raises(ValueError, match="integer"):
        decode_native_sample(payload, {**valid, "y::a::gen": 0.9})
    with pytest.raises(ValueError, match="boolean"):
        decode_native_sample(payload, {**valid, "y::a::gen": True})
    with pytest.raises(ValueError, match="coverage"):
        decode_native_sample(payload, {name: 0 for name in valid})
    with pytest.raises(ValueError, match="budget"):
        decode_native_sample(
            payload,
            {**{name: 0 for name in valid}, "y::a::pv": 1, "y::b::pv": 1},
        )


def test_lambda_targeting_is_deterministic_bounded_and_filters_exact_budget() -> None:
    from cmpo.irc_cmpo_lagrangian import target_budget
    from cmpo.irc_cmpo_master import build_irc_master

    payload_factory = lambda value: build_irc_master(  # noqa: E731
        _toy_assets(), budget=7.0, lagrange_lambda=value, surrogate_terms=[]
    )

    def sampler(payload):
        lam = payload["irc_cmpo"]["lagrange_lambda"]
        def portfolio(*keys):
            values = {v["name"]: 0 for v in payload["variables"]}
            values.update({f"y::{key}": 1 for key in keys})
            return values
        if lam < 1.0:
            return [portfolio("a::pv", "b::pv")] * 3  # cost 8, over budget
        return [portfolio("a::gen", "b::gen"), portfolio("a::pv", "b::gen")]  # 6 and 7

    result = target_budget(payload_factory, sampler, bracket=(0.0, 2.0), max_iterations=5)
    assert len(result.trajectory) <= 5
    assert [row.lagrange_lambda for row in result.trajectory][:2] == [1.0, 0.5]
    assert all(item.total_cost <= 7.0 for item in result.feasible_portfolios)
    assert all(item.projection_used is False for item in result.feasible_portfolios)


def test_grouped_surrogate_fit_has_no_leakage_degree_at_most_three_and_passes_gates() -> None:
    from cmpo.irc_cmpo_surrogate import fit_recourse_surrogate

    rng = np.random.default_rng(17)
    rows = []
    for index in range(500):
        bits = rng.integers(0, 2, size=6)
        target = 20.0 - 3.0 * bits[0] - 2.0 * bits[1] - 4.0 * bits[0] * bits[2]
        rows.append(
                {
                    "portfolio_signature": f"p{index:04d}",
                    **{f"x{i}": int(value) for i, value in enumerate(bits)},
                    "recourse_objective": target,
                    "heldout_recourse_objective": 1.2 * target + 1.0,
                    "upgrade_cost": 5.0 + float(bits.sum()),
                }
        )
    result = fit_recourse_surrogate(
        pd.DataFrame(rows),
        asset_columns=[f"x{i}" for i in range(6)],
        pair_interactions=[("x0", "x2")],
        cubic_interactions=[],
        random_seed=11,
        minimum_portfolios=100,
        heldout_target_column="heldout_recourse_objective",
        cost_column="upgrade_cost",
    )
    assert result.metrics["no_train_test_leakage"] is True
    assert result.metrics["degree"] <= 3
    assert result.metrics["spearman_rank_correlation"] >= 0.70
    assert result.metrics["top_decile_recall"] >= 0.60
    assert result.metrics["normalized_rmse"] <= 0.25
    assert result.metrics["heldout_rank_correlation"] >= 0.70
    assert 0.0 <= result.metrics["pareto_front_recall"] <= 1.0
    assert set(result.split_groups["train"]).isdisjoint(result.split_groups["test"])

    broken = pd.DataFrame(rows)
    broken["x0"] = broken["x0"].astype(float)
    broken.loc[0, "x0"] = 0.5
    with pytest.raises(ValueError, match="binary"):
        fit_recourse_surrogate(
            broken,
            asset_columns=[f"x{i}" for i in range(6)],
            pair_interactions=[],
            cubic_interactions=[],
            minimum_portfolios=100,
        )


def test_candidate_generator_produces_unique_exact_budget_feasible_portfolios() -> None:
    from cmpo.irc_cmpo_surrogate import generate_feasible_candidates

    candidates = generate_feasible_candidates(
        _toy_assets(), budgets=[6.0, 7.0, 8.0, 9.0], minimum_unique=8, random_seed=3
    )
    assert candidates["portfolio_signature"].nunique() == 8
    assert (candidates["upgrade_cost"] <= candidates["budget"] + 1e-9).all()
    assert set(candidates["generation_method"]) == {"deterministic_random_feasible"}
    for keys in candidates["selected_asset_keys"]:
        assert any(key.startswith("a::") for key in keys)
        assert any(key.startswith("b::") for key in keys)


def test_coefficient_audit_rejects_collapsed_important_family() -> None:
    from cmpo.irc_cmpo_constraints import audit_coefficients

    healthy = [
        {"coefficient": -1.0, "powers": {"x": 1}, "component": "surrogate"},
        {"coefficient": 0.2, "powers": {"x": 1}, "component": "normalized_cost"},
        {"coefficient": 2.0, "powers": {"x": 1, "y": 1}, "component": "coverage"},
    ]
    assert audit_coefficients(healthy).passed
    collapsed = [*healthy, {"coefficient": 1e-14, "powers": {"z": 1}, "component": "interaction"}]
    assert not audit_coefficients(collapsed).passed
    cancelled = [
        {"coefficient": 1.0, "powers": {"x": 1}, "component": "surrogate"},
        {"coefficient": -1.0, "powers": {"x": 1}, "component": "normalized_cost"},
    ]
    cancellation_audit = audit_coefficients(cancelled)
    assert not cancellation_audit.passed
    assert any("effective" in reason for reason in cancellation_audit.reasons)


def test_smoke_orchestrator_has_exactly_three_jobs_and_strict_stops(tmp_path: Path) -> None:
    from cmpo.irc_cmpo_lagrangian import SmokeGateFailure, run_three_job_smoke
    from cmpo.irc_cmpo_constraints import audit_coefficients

    jobs = [
        {"name": "toy", "payload": {"variables": []}},
        {"name": "reduced_ieee123", "payload": {"variables": []}},
        {"name": "full_ieee123", "payload": {"variables": []}},
    ]
    calls = []

    def submit(job):
        calls.append(job["name"])
        return {
            "passed": job["name"] != "reduced_ieee123",
            "job_id": job["name"],
            "versions": {"qci-client": "5.0.0", "eqc-models": "0.20.2"},
            "validation": audit_coefficients(
                [{"coefficient": 1.0, "powers": {"x": 1}, "component": "surrogate"}]
            ),
        }

    with pytest.raises(SmokeGateFailure, match="reduced_ieee123"):
        run_three_job_smoke(jobs, submit, output_dir=tmp_path)
    assert calls == ["toy", "reduced_ieee123"]
    manifest = json.loads((tmp_path / "smoke_manifest.json").read_text())
    assert manifest["full_experiment_run"] is False
    assert manifest["versions"] == {"qci-client": "5.0.0", "eqc-models": "0.20.2"}


def test_smoke_orchestrator_records_transport_exception_and_stops(tmp_path: Path) -> None:
    from cmpo.irc_cmpo_lagrangian import SmokeGateFailure, run_three_job_smoke

    jobs = [{"name": name, "payload": {}} for name in ("toy", "reduced_ieee123", "full_ieee123")]
    calls = []

    def submit(job):
        calls.append(job["name"])
        raise RuntimeError("transport down")

    with pytest.raises(SmokeGateFailure, match="transport"):
        run_three_job_smoke(jobs, submit, output_dir=tmp_path)
    manifest = json.loads((tmp_path / "smoke_manifest.json").read_text())
    assert manifest["failed_job"] == "toy"
    assert calls == ["toy"]


def test_build_script_creates_3000_unlabeled_candidates_without_qci(tmp_path: Path) -> None:
    builder = _load_script("phase3_build_irc_cmpo")
    result = builder.build_irc_cmpo(
        ROOT / "configs/phase3_irc_cmpo_ieee123.yaml", output_dir=tmp_path
    )
    candidates = pd.read_csv(tmp_path / "candidate_portfolios.csv")
    assert result["core_binary_variables"] == 33
    assert result["candidate_portfolios"] == candidates["portfolio_signature"].nunique() == 3000
    assert result["qci_jobs_submitted"] == 0
    provenance_sources = set().union(
        *(set(json.loads(value)) for value in candidates["candidate_provenance_sources"])
    )
    assert {
        "exact_milp_or_cp_sat",
        "classical_benders",
        "gpu_random_feasible",
        "greedy",
        "qubo",
        "historical_qci_projected_examples",
    } <= provenance_sources


def test_smoke_plan_has_only_toy_reduced_and_full_payloads() -> None:
    smoke = _load_script("phase3_run_irc_cmpo_smoke")
    assets = _toy_assets()
    jobs = smoke.build_smoke_jobs(
        assets=assets,
        full_assets=assets,
        budget=9.0,
        surrogate_terms=[{"coefficient": -1.0, "asset_keys": ["a::pv"]}],
        lagrange_lambda=1.0,
    )
    assert [job["name"] for job in jobs] == ["toy", "reduced_ieee123", "full_ieee123"]
    assert all(job["num_samples"] == 30 for job in jobs)
    assert all(job["payload"]["max_degree"] <= 3 for job in jobs)


def test_validation_script_writes_coefficient_audit_and_rejects_bad_payload(tmp_path: Path) -> None:
    validator = _load_script("phase3_validate_irc_cmpo")
    from cmpo.irc_cmpo_master import build_irc_master

    payload = build_irc_master(
        _toy_assets(),
        budget=9.0,
        lagrange_lambda=1.0,
        surrogate_terms=[{"coefficient": -1.0, "asset_keys": ["a::pv"]}],
    )
    result = validator.validate_irc_payload(payload, output_dir=tmp_path)
    assert result["valid"] is True
    assert (tmp_path / "coefficient_audit.csv").is_file()
    assert (tmp_path / "coefficient_audit.md").is_file()
    broken = json.loads(json.dumps(payload))
    broken["variables"].append({**broken["variables"][0], "name": "slack_bit_0"})
    with pytest.raises(ValueError, match="slack"):
        validator.validate_irc_payload(broken, output_dir=tmp_path / "bad")


def test_recourse_dataset_builder_freshly_labels_and_preserves_contract(tmp_path: Path) -> None:
    fitter = _load_script("phase3_fit_recourse_surrogate")
    candidates = pd.DataFrame(
        [
            {
                "portfolio_signature": "p1",
                "selected_asset_keys": json.dumps(["a::gen", "b::gen"]),
                "upgrade_cost": 6.0,
                "budget": 6.0,
                "generation_method": "historical_qci_projected_examples",
            },
            {
                "portfolio_signature": "p2",
                "selected_asset_keys": json.dumps(["a::pv", "b::gen"]),
                "upgrade_cost": 7.0,
                "budget": 7.0,
                "generation_method": "gpu_random_feasible",
            },
        ]
    )

    def evaluator(row, *, rank):
        assert rank in {1, 2}
        return {
            "critical_ens": float(rank),
            "total_ens": float(rank + 1),
            "maximum_customers_unserved": 0.1 * rank,
            "critical_infrastructure_outage_hours": 0.0,
            "critical_load_served": 0.9,
            "heldout_critical_ens": float(rank + 2),
            "heldout_total_ens": float(rank + 3),
            "feasibility": True,
            "training_scenario_count": 8,
            "heldout_contingency_count": 10,
            "trace_path": f"trace-{rank}.json",
        }

    result = fitter.evaluate_recourse_candidates(
        candidates,
        output_dir=tmp_path,
        evaluator=evaluator,
    )
    labeled = pd.read_csv(result["dataset_path"])
    assert len(labeled) == 2
    assert labeled["recourse_evaluated"].astype(bool).all()
    assert set(labeled["training_scenario_count"]) == {8}
    assert set(labeled["heldout_contingency_count"]) == {10}
    assert not any("proxy" in column for column in labeled.columns)


def test_cubic_surrogate_interactions_record_physical_stress_rationale() -> None:
    fitter = _load_script("phase3_fit_recourse_surrogate")
    pairs, cubics, metadata = fitter.physical_interactions(
        _toy_assets(), related_anchor_pairs=[("a", "b")]
    )
    assert pairs
    assert cubics
    for cubic in cubics:
        record = metadata[cubic]
        assert set(record["anchor_nodes"]) == {"a", "b"}
        assert "stress_preparedness_category" in record
        assert "physical_rationale" in record
