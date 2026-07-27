from __future__ import annotations

from cmpo.irc_cmpo_master import IRCAsset, build_irc_master, build_scalarized_irc_master

import scripts.phase3_run_irc_cmpo_smoke as smoke


def _assets() -> tuple[IRCAsset, ...]:
    return (
        IRCAsset("a::pv", "a", "pv", 4.0),
        IRCAsset("a::bess", "a", "bess", 5.0),
        IRCAsset("a::gen", "a", "dispatchable_generation", 3.0),
    )


def _scalarized_payload() -> dict[str, object]:
    assets = _assets()
    return build_scalarized_irc_master(
        assets,
        cost_weight=0.25,
        surrogate_terms=[{"coefficient": -1.0, "asset_keys": ["a::pv"]}],
        local_feasibility_terms=[
            {
                "coefficient": 1.0,
                "asset_keys": [asset.asset_key for asset in assets],
                "pattern": [0, 0, 0],
                "anchor_node": "a",
            }
        ],
    )


def _integer_response(
    solutions: list[list[int | float]],
    *,
    num_levels: list[int],
) -> dict[str, object]:
    return {
        "status": "COMPLETED",
        "job_info": {
            "job_id": "smoke-job",
            "job_submission": {
                "job_type": "sample-hamiltonian-integer",
                "problem_config": {
                    "qudit_hamiltonian_optimization": {"polynomial_file_id": "poly"}
                },
                "device_config": {
                    "dirac-3_qudit": {
                        "num_samples": len(solutions),
                        "relaxation_schedule": 1,
                        "num_levels": num_levels,
                    }
                },
            },
        },
        "results": {
            "energies": [float(index) for index in range(len(solutions))],
            "solutions": solutions,
        },
    }


def _job(payload: dict[str, object]) -> dict[str, object]:
    return {
        "name": "full_ieee123",
        "payload": payload,
        "known_exact_optimum": None,
    }


def test_scalarized_payload_accepts_native_integer_without_a_budget_gate() -> None:
    payload = _scalarized_payload()
    response = _integer_response([[1, 0, 0]], num_levels=payload["num_levels"])

    result = smoke.evaluate_smoke_response(_job(payload), response)

    assert result["passed"] is True
    assert result["budget_constraint_applicable"] is False
    assert result["native_exact_budget_feasible_count"] is None


def test_legacy_hard_budget_payload_applies_budget_gate_and_count() -> None:
    payload = build_irc_master(
        _assets(),
        budget=4.0,
        lagrange_lambda=0.25,
        surrogate_terms=[],
    )
    response = _integer_response(
        [[1, 0, 0], [0, 1, 0]],
        num_levels=payload["num_levels"],
    )

    result = smoke.evaluate_smoke_response(_job(payload), response)

    assert result["passed"] is True
    assert result["budget_constraint_applicable"] is True
    assert result["native_exact_budget_feasible_count"] == 1
    assert result["native_combined_feasible_count"] == 1


def test_continuous_normalized_response_is_rejected() -> None:
    payload = _scalarized_payload()
    response = _integer_response([[0.75, 0.0, 0.0]], num_levels=payload["num_levels"])
    response["job_info"]["job_submission"]["job_type"] = "sample-hamiltonian"
    response["job_info"]["job_submission"]["problem_config"] = {
        "normalized_qudit_hamiltonian_optimization": {}
    }
    response["job_info"]["job_submission"]["device_config"] = {
        "dirac-3_normalized_qudit": {"sum_constraint": 1}
    }

    result = smoke.evaluate_smoke_response(_job(payload), response)

    assert result["passed"] is False
    assert result["validation"].valid is False
    assert result["native_coverage_feasible_count"] == 0


def test_response_with_projected_samples_is_not_accepted() -> None:
    payload = _scalarized_payload()
    response = _integer_response([[1, 0, 0]], num_levels=payload["num_levels"])
    response["projected_solutions"] = [[1, 0, 0]]

    result = smoke.evaluate_smoke_response(_job(payload), response)

    assert result["validation"].projected_sample_count == 1
    assert result["passed"] is False
    assert result["projection_used"] is False
