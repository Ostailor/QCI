from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
V1 = ROOT / "results" / "phase3" / "sc_cmpo" / "budget_frontier"


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _metadata_only_payload(tmp_path: Path) -> Path:
    path = tmp_path / "metadata_only.json"
    path.write_text(
        json.dumps(
            {
                "schema": "cmpo.test.v1",
                "objective_sense": "minimize",
                "max_degree": 1,
                "variables": [
                    {
                        "name": "x",
                        "lower_bound": 0.0,
                        "upper_bound": 1.0,
                        "encoding_type": "integer",
                    }
                ],
                "polynomial_terms": [
                    {"coefficient": 1.0, "powers": {"x": 1}, "degree": 1}
                ],
                "budget_constraint": {"amount": 10.0, "hard_constraint": True},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_metadata_only_budget_payload_is_rejected_before_qci_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from cmpo import qci_client_adapter as adapter

    monkeypatch.setattr(
        adapter,
        "validate_qci_environment",
        lambda: pytest.fail("QCi environment validation must not run"),
    )
    monkeypatch.setattr(
        adapter,
        "_client_from_environment",
        lambda: pytest.fail("QCi client must not be created"),
    )
    with pytest.raises(ValueError, match="metadata only"):
        adapter.run_payload_repeats(
            _metadata_only_payload(tmp_path),
            1,
            tmp_path / "raw",
            {"qci": {"samples_per_job": 1}},
        )


def test_v1_audit_reports_all_72_payloads_as_failed(tmp_path: Path) -> None:
    audit = _load_script("phase3_audit_budget_frontier_v1")
    result = audit.audit_budget_frontier_v1(V1, output_root=tmp_path)
    assert result["payloads_checked"] == 72
    assert result["payloads_passed"] == 0
    assert result["payloads_failed"] == 72

    manifest = (tmp_path / "failed_v1_audit" / "payload_validation_manifest.csv").read_text()
    assert manifest.count("budget constraint missing from polynomial Hamiltonian") == 72
    report = (tmp_path / "posthoc_filter" / "posthoc_budget_frontier_report.md").read_text()
    assert "post-hoc sample filter and not a budget-constrained hardware experiment" in report


def test_conservative_currency_encoding_rounds_costs_up_and_budget_down() -> None:
    from cmpo.budget_encoding import choose_currency_unit, encode_budget

    choice = choose_currency_unit([10.001, 20.009], [25.007], fixed_variables=66)
    assert choice.unit == pytest.approx(0.01)
    encoded = encode_budget({"a": 10.001, "b": 20.009}, 25.007, choice.unit)
    assert encoded.encoded_costs == {"a": 1001, "b": 2001}
    assert encoded.encoded_budget == 2500
    assert encoded.slack_bit_count == math.ceil(math.log2(2501))
    assert encoded.maximum_portfolio_conservatism < 0.02


def test_encoded_and_actual_budget_boundaries() -> None:
    from cmpo.budget_encoding import (
        encode_budget,
        validate_actual_cost,
        validate_encoded_cost,
    )

    encoded = encode_budget({"a": 4.001, "b": 5.999}, 10.00, 0.01)
    assert validate_encoded_cost(encoded.encoded_budget, encoded).passed
    assert not validate_encoded_cost(encoded.encoded_budget + 1, encoded).passed
    assert validate_actual_cost(10.0, 10.0).passed
    assert not validate_actual_cost(10.000001, 10.0).passed


def test_penalty_certificate_dominates_nonbudget_variation() -> None:
    from cmpo.budget_penalty_certificate import build_penalty_certificate

    terms = [
        {"coefficient": -2.0, "powers": {"x": 1}, "component": "service"},
        {"coefficient": 3.0, "powers": {"x": 1, "y": 1}, "component": "coverage"},
    ]
    certificate = build_penalty_certificate(terms, safety_multiplier=2.0)
    assert certificate.maximum_nonbudget_objective_variation == pytest.approx(5.0)
    assert certificate.rho_budget > 5.0
    assert certificate.minimum_violation_penalty > 5.0
    assert certificate.passed


def test_global_master_payloads_fit_qci_and_encode_budget(tmp_path: Path) -> None:
    builder = _load_script("phase3_build_budget_master_v2")
    result = builder.build_budget_master_v2(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_master_v2.yaml",
        output_dir=tmp_path,
    )
    payloads = sorted((tmp_path / "qci_master_payloads").glob("*.json"))
    assert result["master_payload_count"] == 6
    assert len(payloads) == 6
    for path in payloads:
        payload = json.loads(path.read_text())
        assert len(payload["variables"]) <= 132
        assert payload["max_degree"] <= 3
        assert all(variable["encoding_type"] == "integer" for variable in payload["variables"])
        assert any(
            term.get("component") == "hard_budget"
            for term in payload["polynomial_terms"]
        )
        assert payload["budget_penalty_certificate"]["passed"] is True
        assert payload["execution_provenance"]["qci_submission_performed"] is False


def test_polynomial_budget_payload_passes_and_toy_optimum_agrees() -> None:
    from cmpo.budget_encoding import validate_budget_payload
    from cmpo.global_upgrade_master import build_toy_master, brute_force_master

    payload = build_toy_master(costs={"a": 2.0, "b": 3.0}, benefits={"a": 2.5, "b": 4.0}, budget=3.0)
    validation = validate_budget_payload(payload)
    assert validation.passed
    optimum = brute_force_master(payload)
    assert optimum.selected_asset_keys == ("b",)
    assert optimum.actual_cost == pytest.approx(3.0)


def test_decode_rejects_overbudget_and_charges_duplicate_asset_once() -> None:
    from cmpo.global_upgrade_master import build_toy_master
    from cmpo.portfolio_decode import decode_master_sample

    payload = build_toy_master(costs={"a": 2.0, "b": 3.0}, benefits={"a": 2.5, "b": 4.0}, budget=3.0)
    variables = [variable["name"] for variable in payload["variables"]]
    sample = {name: 0 for name in variables}
    for asset in ("a", "b"):
        sample[f"upgrade::{asset}::selected"] = 1
        sample[f"upgrade::{asset}::not_selected"] = 0
    with pytest.raises(ValueError, match="budget"):
        decode_master_sample(payload, sample)

    sample["upgrade::a::selected"] = 0
    sample["upgrade::a::not_selected"] = 1
    remaining = payload["budget_encoding"]["encoded_budget"] - payload["budget_encoding"]["encoded_costs"]["b"]
    for index, weight in enumerate(payload["budget_encoding"]["slack_bit_weights"]):
        sample[f"budget_slack_bit_{index}"] = int(bool(remaining & weight))
    decoded = decode_master_sample(payload, sample)
    duplicate = list(decoded.upgrade_rows) + [dict(decoded.upgrade_rows[0])]
    assert decoded.charge_once_cost(duplicate) == pytest.approx(3.0)


def test_challenge_aligned_decode_projects_pairs_and_repairs_missing_coverage() -> None:
    from cmpo.global_upgrade_master import build_toy_master
    from cmpo.portfolio_decode import decode_challenge_aligned_sample

    payload = build_toy_master(
        costs={"a": 2.0, "b": 3.0},
        benefits={"a": 2.5, "b": 4.0},
        budget=3.0,
    )
    for asset in payload["catalog_assets"]:
        asset["anchor_node"] = "shared"
    coverage = dict(payload["anchor_coverage_constraints"][0])
    coverage["anchor_node"] = "shared"
    coverage["upgrade_variables"] = [
        "upgrade::a::selected",
        "upgrade::b::selected",
    ]
    payload["anchor_coverage_constraints"] = [coverage]
    variables = [variable["name"] for variable in payload["variables"]]
    raw = {name: 0.0 for name in variables}
    raw["upgrade::a::selected"] = 0.2
    raw["upgrade::a::not_selected"] = 0.8
    raw["upgrade::b::selected"] = 0.9
    raw["upgrade::b::not_selected"] = 0.1
    decoded, diagnostics = decode_challenge_aligned_sample(payload, raw, energy=-1.25)
    assert decoded.selected_asset_keys == ("b",)
    assert decoded.total_upgrade_cost == pytest.approx(3.0)
    assert (
        diagnostics["projection_rule"]
        == "pairwise_preference_then_hard_feasible_binary_milp_projection"
    )
    assert diagnostics["one_hot_valid"] is True
    assert diagnostics["coverage_valid"] is True

    raw["upgrade::b::selected"] = 0.1
    raw["upgrade::b::not_selected"] = 0.9
    repaired, repaired_diagnostics = decode_challenge_aligned_sample(payload, raw)
    assert repaired.selected_asset_keys == ("a",)
    assert repaired_diagnostics["raw_coverage_valid"] is False
    assert repaired_diagnostics["coverage_repair_count"] == 1


def test_portfolio_diversity_returns_unique_signatures() -> None:
    from cmpo.portfolio_decode import DecodedPortfolio
    from cmpo.portfolio_diversity import select_unique_feasible_portfolios

    one = DecodedPortfolio.testing(("a",), 2.0, energy=1.0)
    duplicate = DecodedPortfolio.testing(("a",), 2.0, energy=0.5)
    two = DecodedPortfolio.testing(("b",), 3.0, energy=0.7)
    selected = select_unique_feasible_portfolios([one, duplicate, two], limit=10)
    assert [item.selected_asset_keys for item in selected] == [("a",), ("b",)]
    assert selected[0].energy == pytest.approx(0.5)


def test_scored_portfolio_selection_uses_challenge_priority_order() -> None:
    from cmpo.portfolio_decode import DecodedPortfolio
    from cmpo.portfolio_diversity import (
        ScoredPortfolio,
        select_scored_diverse_portfolios,
    )

    lower_energy = ScoredPortfolio(
        DecodedPortfolio.testing(("a",), 2.0, energy=-100.0),
        critical_service_proxy=0.5,
        reserve_preparedness=1.0,
        estimated_recourse_score=1.0,
        upgrade_utilization=1.0,
        provenance={"sample": 0},
    )
    stronger_service = ScoredPortfolio(
        DecodedPortfolio.testing(("b",), 2.0, energy=10.0),
        critical_service_proxy=1.0,
        reserve_preparedness=0.0,
        estimated_recourse_score=0.0,
        upgrade_utilization=0.5,
        provenance={"sample": 1},
    )
    selected = select_scored_diverse_portfolios(
        [lower_energy, stronger_service], limit=1
    )
    assert selected[0].portfolio.selected_asset_keys == ("b",)


@pytest.mark.parametrize(
    "method",
    [
        "exact MILP or CP-SAT upgrade master",
        "SLSQP/IPOPT relaxation",
        "classical Benders master",
        "greedy cost-benefit portfolio selection",
        "GPU random portfolio search",
        "QUBO/quadratized upgrade master",
    ],
)
def test_classical_global_masters_return_hard_feasible_portfolios(method: str) -> None:
    from cmpo.classical_budget_masters import solve_classical_master
    from cmpo.global_upgrade_master import build_toy_master

    payload = build_toy_master(
        costs={"a": 2.0, "b": 3.0},
        benefits={"a": 2.5, "b": 4.0},
        budget=3.0,
    )
    for asset in payload["catalog_assets"]:
        asset["anchor_node"] = "shared"
    coverage = dict(payload["anchor_coverage_constraints"][0])
    coverage["anchor_node"] = "shared"
    coverage["upgrade_variables"] = [
        "upgrade::a::selected",
        "upgrade::b::selected",
    ]
    payload["anchor_coverage_constraints"] = [coverage]
    result = solve_classical_master(payload, method, seed=7)
    assert result.portfolio.total_upgrade_cost <= 3.0
    assert result.portfolio.selected_asset_keys
    assert result.runtime_seconds >= 0.0


def test_master_portfolio_is_fixed_across_all_twelve_patches(tmp_path: Path) -> None:
    from cmpo.budget_master_recourse import fix_portfolio_across_patches
    from cmpo.portfolio_decode import DecodedPortfolio

    payload_paths = sorted((ROOT / "results/phase3/sc_cmpo/ieee123/qci_payloads").glob("*.json"))
    payloads = {path.name: json.loads(path.read_text()) for path in payload_paths}
    portfolio = DecodedPortfolio.testing(("ieee123_opendss::76::pv",), 416812.4520828953)
    fixed = fix_portfolio_across_patches(portfolio, payloads)
    assert len(fixed) == 12
    assert {row["portfolio_signature"] for row in fixed.values()} == {portfolio.signature}
    assert {tuple(row["fixed_portfolio_asset_keys"]) for row in fixed.values()} == {
        portfolio.selected_asset_keys
    }


def test_full_v2_validation_gates_pass(tmp_path: Path) -> None:
    builder = _load_script("phase3_build_budget_master_v2")
    validator = _load_script("phase3_validate_budget_master_v2")
    config = ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_master_v2.yaml"
    builder.build_budget_master_v2(config, output_dir=tmp_path)
    result = validator.validate_budget_master_v2(config, output_dir=tmp_path)
    assert result["valid"] is True
    assert len(result["checks"]) == 15
    assert all(result["checks"].values())
    assert result["qci_submission_performed"] is False


def test_budget_master_experiment_artifact_runner_is_non_submitting() -> None:
    evaluator = _load_script("phase3_evaluate_budget_master_v2_experiment")
    result = evaluator.evaluate_experiment(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_master_v2.yaml",
        dry_run=True,
    )
    assert result["qci_submission_performed"] is False
    assert result["expected_qci_jobs"] == 18
    assert result["budget_count"] == 6
    assert result["retained_per_budget"] == 10
