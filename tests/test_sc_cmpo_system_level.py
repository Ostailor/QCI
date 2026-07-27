from __future__ import annotations

import json
import csv
from pathlib import Path

import pytest

from cmpo.full_system_dispatch import (
    evaluate_full_system,
    evaluate_full_system_heldout,
    scenario_probability_map,
)
from cmpo.matched_problem_baselines import (
    FULL_SYSTEM_REFERENCE_METHODS,
    REQUIRED_MATCHED_METHODS,
    solve_coordinated_reference,
    solve_matched_payload,
)
from cmpo.overlap_consensus import (
    reconstruct_patch_values,
    run_method_consensus,
    validate_reconstructed_overlap,
)
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config
from scripts.phase3_run_overlap_consensus import run_overlap_consensus
from scripts.phase3_run_matched_baselines import run_matched_baselines


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "results" / "phase3" / "sc_cmpo" / "qci_payloads"


def _case14_payloads(limit: int | None = None) -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for path in sorted(PAYLOAD_DIR.glob("pglib_case14_ieee__*.json"))[:limit]:
        payloads[path.name] = json.loads(path.read_text(encoding="utf-8"))
    assert payloads
    return payloads


def _complete_values(payload: dict, fraction: float) -> dict[str, float]:
    values = {str(variable["name"]): 0.0 for variable in payload["variables"]}
    values.update(
        {
            "upgrade_select_dispatchable": float(fraction > 0.0),
            "dispatchable_capacity_fraction": fraction,
            "islanding_eligibility": 1.0,
            "base_mode_connected": 1.0,
            "bess_reserve_target": 1.0,
            "bess_soc_target": 1.0,
            "critical_load_priority": 1.0,
            "tie_pcc_reserve_target": 1.0,
        }
    )
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = str(scenario["name"])
        mode = "restoration" if scenario["restoration_mode"] else "islanded" if scenario["forced_islanding"] else "connected"
        values[f"mode_{mode}[{name}]"] = 1.0
        values[f"battery_action_hold[{name}]"] = 1.0
        values[f"der_commitment[{name}]"] = 1.0
        values[f"critical_load_service[{name}]"] = 1.0
        values[f"tie_pcc_response[{name}]"] = float(bool(scenario["pcc_available"]))
    return values


def _solution_rows(payloads: dict[str, dict], fraction: float = 1.0) -> list[dict]:
    return [
        {
            "method": "unit_method",
            "benchmark": payload["sc_cmpo"]["public_benchmark"],
            "payload_name": name,
            "solution_id": f"unit::{name}",
            "solution_values": _complete_values(payload, fraction),
            "runtime_seconds": 0.01,
        }
        for name, payload in payloads.items()
    ]


def test_overlap_consensus_tracks_residuals_and_reconstructs_patch_values() -> None:
    payloads = _case14_payloads(limit=2)
    rows = _solution_rows(payloads)
    rows[0]["solution_values"]["critical_load_priority"] = 0.2
    rows[1]["solution_values"]["critical_load_priority"] = 0.8

    result = run_method_consensus(payloads, rows, tolerance=1e-7, max_iterations=200)

    assert result["status"] == "completed"
    assert result["converged"]
    assert result["iteration_count"] > 0
    assert result["primal_residual"] <= 1e-7
    assert result["dual_residual"] <= 1e-7
    assert result["raw_conflict_count"] >= 1
    assert result["unresolved_conflicts"] == []
    assert result["consensus_values"]["pglib_case14_ieee::first_stage::critical_load_priority"] == pytest.approx(0.5)

    reconstructed = reconstruct_patch_values(payloads, result["consensus_values"])
    assert set(reconstructed) == set(payloads)
    assert all(values["critical_load_priority"] == pytest.approx(0.5) for values in reconstructed.values())
    assert validate_reconstructed_overlap(payloads, reconstructed) == []


def test_post_repair_overlap_validator_detects_conflicting_battery_actions() -> None:
    payloads = _case14_payloads(limit=2)
    consensus = run_method_consensus(payloads, _solution_rows(payloads))
    reconstructed = reconstruct_patch_values(payloads, consensus["consensus_values"])
    second = sorted(reconstructed)[1]
    reconstructed[second]["battery_action_hold[forced_islanding]"] = 0
    reconstructed[second]["battery_action_charge[forced_islanding]"] = 1

    conflicts = validate_reconstructed_overlap(payloads, reconstructed)

    assert conflicts
    assert any("storage::battery_action" in conflict["global_key"] for conflict in conflicts)


def test_overlap_consensus_rejects_incomplete_patch_coverage() -> None:
    payloads = _case14_payloads(limit=2)
    rows = _solution_rows(payloads)[:1]

    result = run_method_consensus(payloads, rows)

    assert result["status"] == "failed"
    assert not result["converged"]
    assert result["missing_payloads"]
    assert "consensus_values" not in result


def test_overlap_consensus_selects_qci_by_challenge_metrics_and_retains_replicates(
    tmp_path: Path,
) -> None:
    payloads = _case14_payloads(limit=2)
    payload_dir = tmp_path / "qci_payloads"
    payload_dir.mkdir()
    for name, payload in payloads.items():
        (payload_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    decoded_path = tmp_path / "decoded" / "qci_repeat_metrics.csv"
    decoded_path.parent.mkdir()
    rows = []
    for name, payload in payloads.items():
        for repeat, energy, upgrade_fraction in ((0, -2.0, 0.0), (1, -1.0, 1.0)):
            values = _complete_values(payload, upgrade_fraction)
            rows.append(
                {
                    "payload_name": name,
                    "status": "COMPLETED",
                    "job_id": f"job-{repeat}",
                    "repeat": repeat,
                    "sample_index": 0,
                    "qci_energy": energy,
                    "decoded_objective": energy,
                    "runtime_seconds": 0.1,
                    "decoded_variables": json.dumps(values),
                }
            )
    with decoded_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = run_overlap_consensus(
        payload_dir,
        tmp_path / "missing_baselines.csv",
        [str(decoded_path)],
        tmp_path / "system_level",
        rho=1.0,
        tolerance=1e-6,
        max_iterations=200,
        overwrite=False,
        dry_run=False,
    )

    assert result["selected_qci_patch_solutions"] == len(payloads)
    assert result["completed_consensus_groups"] == 3
    selected = list(csv.DictReader((tmp_path / "system_level" / "qci_patch_solutions.csv").open()))
    headline = [row for row in selected if row["headline_selection"] == "True"]
    assert len(headline) == len(payloads)
    assert {float(row["qci_energy"]) for row in headline} == {-1.0}
    assert all(
        json.loads(row["solution_values_json"])["dispatchable_capacity_fraction"] == 1.0
        for row in headline
    )
    assert {row["consensus_replicate"] for row in selected} == {
        "challenge_selected",
        "qci_sample_000",
        "qci_sample_001",
    }


def test_matched_baseline_runner_repeats_only_stochastic_methods(tmp_path: Path) -> None:
    payload_name, payload = next(iter(_case14_payloads(limit=1).items()))
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / payload_name).write_text(json.dumps(payload), encoding="utf-8")

    result = run_matched_baselines(
        payload_dir,
        tmp_path / "system_level",
        methods=["CMPO-local polynomial search", "SLSQP"],
        benchmarks=None,
        seed=123,
        repeats=3,
        workers=1,
        overwrite=False,
        dry_run=False,
    )

    rows = list(
        csv.DictReader(
            (tmp_path / "system_level" / "baseline_patch_solutions.csv").open()
        )
    )
    local_rows = [row for row in rows if row["method"] == "CMPO-local polynomial search"]
    slsqp_rows = [row for row in rows if row["method"] == "SLSQP"]
    assert len(local_rows) == 3
    assert {row["repeat"] for row in local_rows} == {"0", "1", "2"}
    assert len({row["seed"] for row in local_rows}) == 3
    assert len(slsqp_rows) == 1
    assert slsqp_rows[0]["repeat"] == "deterministic"
    assert result["completed"] == 4


def test_matched_pyomo_backends_run_in_isolated_processes(tmp_path: Path) -> None:
    payload_name, payload = next(iter(_case14_payloads(limit=1).items()))
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / payload_name).write_text(json.dumps(payload), encoding="utf-8")

    result = run_matched_baselines(
        payload_dir,
        tmp_path / "system_level",
        methods=["IPOPT/Pyomo nonlinear", "piecewise-linear MILP"],
        benchmarks=None,
        seed=123,
        repeats=1,
        workers=2,
        overwrite=False,
        dry_run=False,
    )

    assert result["completed"] == 2
    assert result["failed"] == 0
    rows = list(
        csv.DictReader(
            (tmp_path / "system_level" / "baseline_patch_solutions.csv").open()
        )
    )
    assert {row["method"] for row in rows} == {
        "IPOPT/Pyomo nonlinear",
        "piecewise-linear MILP",
    }


def test_scenario_probabilities_are_equal_and_sum_to_one() -> None:
    payloads = _case14_payloads(limit=2)

    probabilities = scenario_probability_map(list(payloads.values()))

    assert set(probabilities) == set(payloads[next(iter(payloads))]["sc_cmpo"]["scenario_names"])
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert all(value == pytest.approx(0.125) for value in probabilities.values())


def test_full_system_dispatch_scores_upgrade_assets_once() -> None:
    payloads = _case14_payloads()
    rows = _solution_rows(payloads)
    consensus = run_method_consensus(payloads, rows)
    reconstructed = reconstruct_patch_values(payloads, consensus["consensus_values"])
    config = load_sc_cmpo_config(ROOT / "configs" / "phase3_sc_cmpo_case14.yaml")
    grid = load_public_grid(config)

    result = evaluate_full_system(
        method="unit_method",
        grid=grid,
        payloads=payloads,
        patch_values=reconstructed,
        consensus=consensus,
        patch_runtime_seconds=0.1,
    )

    assert result["status"] == "completed"
    metrics = result["system_metrics"]
    assert metrics["full_system_feasibility"]
    assert metrics["scenario_probability_sum"] == pytest.approx(1.0)
    assert metrics["scenario_count"] == 8
    assert metrics["total_upgrade_cost"] > 0.0
    asset_keys = [row["asset_key"] for row in result["upgrade_plan"]]
    assert len(asset_keys) == len(set(asset_keys))
    assert metrics["total_upgrade_cost"] == pytest.approx(
        sum(float(row["installed_cost"]) for row in result["upgrade_plan"])
    )
    assert all(row["projection_status"] == "completed" for row in result["scenario_results"])


def test_full_system_heldout_uses_unused_public_contingencies() -> None:
    payloads = _case14_payloads(limit=2)
    consensus = run_method_consensus(payloads, _solution_rows(payloads))
    reconstructed = reconstruct_patch_values(payloads, consensus["consensus_values"])
    config = load_sc_cmpo_config(ROOT / "configs" / "phase3_sc_cmpo_case14.yaml")
    grid = load_public_grid(config)

    result = evaluate_full_system_heldout(
        "unit_method",
        grid,
        payloads,
        reconstructed,
        consensus,
        limit=2,
    )

    assert result["status"] == "completed"
    assert result["heldout_summary"]["heldout_count"] == 2
    assert result["heldout_summary"]["heldout_probability_sum"] == pytest.approx(1.0)
    assert len(result["contingency_results"]) == 2
    assert all(row["projection_status"] == "completed" for row in result["contingency_results"])


def test_full_system_dispatch_suppresses_metrics_after_consensus_failure() -> None:
    payloads = _case14_payloads(limit=1)
    config = load_sc_cmpo_config(ROOT / "configs" / "phase3_sc_cmpo_case14.yaml")
    grid = load_public_grid(config)

    result = evaluate_full_system(
        method="failed_method",
        grid=grid,
        payloads=payloads,
        patch_values={name: _complete_values(payload, 1.0) for name, payload in payloads.items()},
        consensus={"status": "failed", "converged": False},
    )

    assert result["status"] == "failed"
    assert not result["system_metrics_produced"]
    assert "system_metrics" not in result


def test_full_system_dispatch_enforces_consensus_battery_hold_action() -> None:
    payloads = _case14_payloads(limit=1)
    rows = _solution_rows(payloads)
    for row in rows:
        values = row["solution_values"]
        values["upgrade_select_dispatchable"] = 0.0
        values["dispatchable_capacity_fraction"] = 0.0
        values["upgrade_select_bess"] = 1.0
        values["bess_energy_fraction"] = 1.0
        values["bess_power_fraction"] = 1.0
    consensus = run_method_consensus(payloads, rows)
    reconstructed = reconstruct_patch_values(payloads, consensus["consensus_values"])
    config = load_sc_cmpo_config(ROOT / "configs" / "phase3_sc_cmpo_case14.yaml")
    grid = load_public_grid(config)

    result = evaluate_full_system(
        method="battery_hold_method",
        grid=grid,
        payloads=payloads,
        patch_values=reconstructed,
        consensus=consensus,
    )

    assert result["status"] == "completed"
    assert all(row["battery_action_consistency_enforced"] for row in result["scenario_results"])
    assert all(row["bess_discharge_kwh"] == pytest.approx(0.0) for row in result["scenario_results"])
    assert all(row["bess_charge_kwh"] == pytest.approx(0.0) for row in result["scenario_results"])


@pytest.mark.parametrize("method", sorted(REQUIRED_MATCHED_METHODS))
def test_all_required_matched_baselines_return_complete_patch_solutions(method: str) -> None:
    payload_name, payload = next(iter(_case14_payloads(limit=1).items()))

    row = solve_matched_payload(payload_name, payload, method=method, seed=123)

    assert row["status"] == "completed"
    assert row["method"] == method
    assert set(payload["sc_cmpo"]["shared_first_stage_variables"]).issubset(row["solution_values"])
    assert row["runtime_seconds"] >= 0.0


@pytest.mark.parametrize("method", FULL_SYSTEM_REFERENCE_METHODS)
def test_full_system_references_coordinate_one_decision_across_patches(method: str) -> None:
    payloads = _case14_payloads(limit=2)

    rows = solve_coordinated_reference(payloads, method, seed=123)

    assert len(rows) == len(payloads)
    assert all(row["status"] == "completed" for row in rows)
    fractions = {
        (
            row["solution_values"]["pv_capacity_fraction"],
            row["solution_values"]["bess_energy_fraction"],
            row["solution_values"]["dispatchable_capacity_fraction"],
        )
        for row in rows
    }
    assert len(fractions) == 1
    assert all(
        row["trace_metadata"]["reference_scope"]
        == "one shared first-stage solve across every benchmark patch"
        for row in rows
    )
