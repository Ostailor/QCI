from __future__ import annotations

import json
import hashlib
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from cmpo.budget_frontier import (
    add_marginal_ens_reduction,
    budget_win_tie_loss,
    frontier_hypervolume,
    pareto_frontier,
    validate_matched_budget_results,
)
from cmpo.budgeted_portfolio import (
    BudgetExceededError,
    deduplicate_upgrade_assets,
    enforce_hard_budget,
)
from cmpo.upgrade_budget import derive_ieee123_budget_sweep, load_ieee123_upgrade_catalog


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "results" / "phase3" / "sc_cmpo" / "ieee123" / "qci_payloads"
SYSTEM_DIR = ROOT / "results" / "phase3" / "sc_cmpo" / "final_public_experiment" / "system_level"


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ieee123_budget_sweep_uses_deduplicated_public_catalog_and_reference_costs() -> None:
    catalog = load_ieee123_upgrade_catalog(PAYLOAD_DIR)

    assert len(catalog) == 33
    assert len({asset.asset_key for asset in catalog}) == 33
    assert {asset.technology for asset in catalog} == {
        "pv",
        "bess",
        "dispatchable_generation",
    }
    assert all(asset.source_row.startswith("ATBe.csv row") for asset in catalog)

    budgets = derive_ieee123_budget_sweep(
        catalog,
        qci_metrics_path=SYSTEM_DIR / "qci_system_metrics.csv",
        baseline_metrics_path=SYSTEM_DIR / "baseline_system_metrics.csv",
    )
    amounts = [level.amount for level in budgets]

    assert len(budgets) >= 6
    assert amounts == sorted(set(amounts))
    assert amounts[0] == pytest.approx(2_032_032.0)
    assert any(amount == pytest.approx(4_532_906.712497371) for amount in amounts)
    assert amounts[-1] == pytest.approx(5_602_175.318543635)
    assert all(level.derivation and level.source_refs for level in budgets)
    assert all(level.amount >= level.discrete_portfolio_cost for level in budgets)


def test_physical_assets_are_deduplicated_and_charged_once() -> None:
    rows = [
        {
            "asset_key": "ieee123::65::bess",
            "installed_fraction": 0.4,
            "installed_cost": 40.0,
            "source_payload_ids": ["patch-a"],
        },
        {
            "asset_key": "ieee123::65::bess",
            "installed_fraction": 0.8,
            "installed_cost": 80.0,
            "source_payload_ids": ["patch-b"],
        },
        {
            "asset_key": "ieee123::76::pv",
            "installed_fraction": 1.0,
            "installed_cost": 20.0,
            "source_payload_ids": ["patch-c"],
        },
    ]

    deduplicated = deduplicate_upgrade_assets(rows)

    assert len(deduplicated) == 2
    bess = next(row for row in deduplicated if row["asset_key"] == "ieee123::65::bess")
    assert bess["installed_cost"] == 80.0
    assert bess["source_payload_ids"] == ["patch-a", "patch-b"]
    assert enforce_hard_budget(deduplicated, 100.0) == pytest.approx(100.0)


def test_hard_budget_rejects_reconstructed_portfolio_over_limit() -> None:
    with pytest.raises(BudgetExceededError, match="exceeds hard budget"):
        enforce_hard_budget(
            [{"asset_key": "asset", "installed_cost": 100.01}],
            100.0,
            tolerance=1e-9,
        )


def test_hard_budget_clamps_only_floating_point_noise_to_exact_cap() -> None:
    charged = enforce_hard_budget(
        [
            {"asset_key": "a", "installed_cost": 33.3},
            {"asset_key": "b", "installed_cost": 66.7000000001},
        ],
        100.0,
        tolerance=1e-6,
    )

    assert charged == 100.0


def _frontier_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"budget": 100.0, "method": "QCi SC-CMPO", "total_upgrade_cost": 90.0, "total_ens": 8.0},
            {"budget": 100.0, "method": "SLSQP", "total_upgrade_cost": 100.0, "total_ens": 10.0},
            {"budget": 200.0, "method": "QCi SC-CMPO", "total_upgrade_cost": 190.0, "total_ens": 4.0},
            {"budget": 200.0, "method": "SLSQP", "total_upgrade_cost": 180.0, "total_ens": 4.0},
            {"budget": 300.0, "method": "QCi SC-CMPO", "total_upgrade_cost": 290.0, "total_ens": 3.0},
            {"budget": 300.0, "method": "SLSQP", "total_upgrade_cost": 280.0, "total_ens": 2.0},
        ]
    )


def test_pareto_hypervolume_marginal_efficiency_and_budget_outcomes() -> None:
    frame = _frontier_frame()
    frontier = pareto_frontier(frame, cost_col="total_upgrade_cost", resilience_col="total_ens")

    assert set(frontier["method"]) == {"QCi SC-CMPO", "SLSQP"}
    assert frontier["pareto_frontier"].all()
    assert frontier_hypervolume(
        frame[frame["method"] == "QCi SC-CMPO"],
        cost_col="total_upgrade_cost",
        resilience_col="total_ens",
        reference_cost=300.0,
        reference_resilience=12.0,
    ) > 0.0

    marginal = add_marginal_ens_reduction(frame)
    qci = marginal[marginal["method"] == "QCi SC-CMPO"].sort_values("budget")
    assert pd.isna(qci.iloc[0]["marginal_ens_reduction_per_dollar"])
    assert qci.iloc[1]["marginal_ens_reduction_per_dollar"] == pytest.approx(0.04)

    outcomes = budget_win_tie_loss(frame, qci_method="QCi SC-CMPO", metric="total_ens")
    assert outcomes.set_index("budget")["outcome"].to_dict() == {
        100.0: "win",
        200.0: "tie",
        300.0: "loss",
    }


def test_matched_budget_validation_requires_equal_budgets_and_traceability() -> None:
    valid = _frontier_frame().assign(
        feasibility=True,
        system_trace_id=lambda data: [f"trace-{index}" for index in range(len(data))],
    )
    validate_matched_budget_results(valid, expected_methods={"QCi SC-CMPO", "SLSQP"})

    over = valid.copy()
    over.loc[0, "total_upgrade_cost"] = 100.01
    with pytest.raises(ValueError, match="over-budget"):
        validate_matched_budget_results(over, expected_methods={"QCi SC-CMPO", "SLSQP"})

    missing = valid[valid["method"] != "SLSQP"].copy()
    with pytest.raises(ValueError, match="method coverage"):
        validate_matched_budget_results(missing, expected_methods={"QCi SC-CMPO", "SLSQP"})


def test_budgeted_payload_builder_preserves_sources_and_records_qci_jobs(tmp_path: Path) -> None:
    builder = _load_script("phase3_build_budgeted_ieee123_payloads")
    source_hashes = {path.name: _sha256(path) for path in PAYLOAD_DIR.glob("*.json")}

    result = builder.build_budgeted_ieee123_payloads(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_sweep.yaml",
        tmp_path / "budget_frontier",
        overwrite=False,
        dry_run=False,
    )

    assert result["budget_count"] >= 6
    assert result["source_payload_count"] == 12
    assert result["budgeted_payload_count"] == result["budget_count"] * 12
    assert result["qci_jobs_completed"] == 12
    assert result["qci_jobs_failed"] == 0
    assert source_hashes == {path.name: _sha256(path) for path in PAYLOAD_DIR.glob("*.json")}

    payload_path = next((tmp_path / "budget_frontier" / "payloads").glob("*/*.json"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["source_payload_sha256"] == source_hashes[payload_path.name]
    assert payload["budget_constraint"]["hard_constraint"] is True
    assert payload["budget_constraint"]["samples_per_payload"] == 30
    assert payload["budget_constraint"]["reject_over_budget_reconstruction"] is True


def test_budgeted_baseline_runner_resolves_every_classical_method_and_budget() -> None:
    runner = _load_script("phase3_run_budgeted_baselines")

    result = runner.run_budgeted_baselines(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_sweep.yaml",
        ROOT / "results" / "phase3" / "sc_cmpo" / "budget_frontier",
        overwrite=False,
        dry_run=True,
    )

    assert result["budget_count"] >= 6
    assert result["method_count"] == 7
    assert result["comparison_point_count"] == result["budget_count"] * 7
    assert set(result["methods"]) == {
        "SLSQP",
        "IPOPT/Pyomo nonlinear",
        "piecewise-linear MILP",
        "CMPO-local polynomial search",
        "differential evolution",
        "QUBO/quadratized search",
        "greedy resilience heuristic",
    }


def test_budget_projection_preserves_method_specific_recourse_values() -> None:
    runner = _load_script("phase3_run_budgeted_baselines")
    payload_path = next(PAYLOAD_DIR.glob("*.json"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    source = {str(variable["name"]): 0.0 for variable in payload["variables"]}
    source["critical_load_priority"] = 0.37
    source["critical_load_service[forced_islanding]"] = 0.42

    projected = runner._apply_budget_fractions(
        payload,
        source,
        {"pv": 0.2, "bess": 0.3, "dispatchable_generation": 1.0},
    )

    assert projected["pv_capacity_fraction"] == 0.2
    assert projected["bess_energy_fraction"] == 0.3
    assert projected["bess_power_fraction"] == 0.3
    assert projected["dispatchable_capacity_fraction"] == 1.0
    assert projected["critical_load_priority"] == 0.37
    assert projected["critical_load_service[forced_islanding]"] == 0.42


def test_classical_payload_hard_fixes_upgrade_fractions_without_mutating_source() -> None:
    runner = _load_script("phase3_run_budgeted_baselines")
    payload_path = next(PAYLOAD_DIR.glob("*.json"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    original = json.dumps(payload, sort_keys=True)

    fixed = runner._fix_payload_upgrade_fractions(
        payload,
        {"pv": 0.2, "bess": 0.3, "dispatchable_generation": 1.0},
    )

    bounds = {variable["name"]: (variable["lower_bound"], variable["upper_bound"]) for variable in fixed["variables"]}
    assert bounds["pv_capacity_fraction"] == (0.2, 0.2)
    assert bounds["bess_energy_fraction"] == (0.3, 0.3)
    assert bounds["bess_power_fraction"] == (0.3, 0.3)
    assert bounds["dispatchable_capacity_fraction"] == (1.0, 1.0)
    assert bounds["upgrade_select_pv"] == (1.0, 1.0)
    assert json.dumps(payload, sort_keys=True) == original


def test_frontier_evaluator_dry_run_resolves_all_methods_and_outputs() -> None:
    evaluator = _load_script("phase3_evaluate_budget_frontier")

    result = evaluator.evaluate_budget_frontier(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_sweep.yaml",
        ROOT / "results" / "phase3" / "sc_cmpo" / "budget_frontier",
        overwrite=False,
        dry_run=True,
    )

    assert result["method_count"] == 8
    assert result["budget_count"] >= 6
    assert result["comparison_point_count"] == result["method_count"] * result["budget_count"]
    assert set(result["final_tables"]) == {
        "table_budget_matched_results.csv",
        "table_heldout_budget_results.csv",
        "table_budget_win_tie_loss.csv",
        "pareto_frontier.csv",
    }
    assert len(result["figures"]) == 4


def test_negative_paper_claim_explicitly_states_identical_hard_budgets() -> None:
    evaluator = _load_script("phase3_evaluate_budget_frontier")

    claim = evaluator._claim_from_outcomes(pd.Series(["loss", "tie", "loss"]))

    assert "identical hard upgrade budgets" in claim
    assert "does not support" in claim


def test_frontier_validator_dry_run_covers_acceptance_gates(tmp_path: Path) -> None:
    validator = _load_script("phase3_validate_budget_frontier")

    result = validator.validate_budget_frontier(
        ROOT / "configs" / "phase3_sc_cmpo_ieee123_budget_sweep.yaml",
        tmp_path,
        dry_run=True,
    )

    assert set(result["acceptance_gates"]) == {
        "equal_budget_method_coverage",
        "no_over_budget_rows",
        "identical_patch_scenario_consensus_projection_heldout",
        "csv_and_system_trace_for_every_point",
        "matched_cost_claim_reported",
        "existing_sc_cmpo_artifacts_untouched",
    }
