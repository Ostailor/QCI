import json
from pathlib import Path

import pytest

from cmpo.qci_response_audit import (
    audit_response_file,
    classify_response_mode,
    coefficient_dynamic_range,
    write_root_cause_artifacts,
)


def _continuous_response() -> dict:
    return {
        "job_info": {
            "job_id": "continuous-job",
            "job_submission": {
                "problem_config": {"normalized_qudit_hamiltonian_optimization": {}},
                "device_config": {
                    "dirac-3_normalized_qudit": {
                        "num_samples": 1,
                        "sum_constraint": 10000,
                    }
                },
            },
        },
        "status": "COMPLETED",
        "results": {"solutions": [[0.25, 9999.75]], "energies": [-1.0]},
    }


def _integer_response() -> dict:
    return {
        "job_info": {
            "job_id": "integer-job",
            "job_submission": {
                "problem_config": {"qudit_hamiltonian_optimization": {}},
                "device_config": {
                    "dirac-3_qudit": {
                        "num_samples": 2,
                        "num_levels": [2, 3],
                    }
                },
            },
        },
        "status": "COMPLETED",
        "results": {"solutions": [[0, 2], [1, 1]], "energies": [-2.0, -1.0]},
    }


def test_classifies_normalized_and_integer_response_modes() -> None:
    assert classify_response_mode(_continuous_response()) == "normalized_continuous_qudit"
    assert classify_response_mode(_integer_response()) == "integer_qudit"
    conflicting = _integer_response()
    conflicting["job_info"]["job_submission"]["problem_config"][
        "normalized_qudit_hamiltonian_optimization"
    ] = {}
    assert classify_response_mode(conflicting) == "unknown"
    assert (
        classify_response_mode(
            {"results_metadata": {"qudit_hamiltonian_optimization_results": {}}}
        )
        == "integer_qudit"
    )
    assert (
        classify_response_mode(
            {
                "results_metadata": {
                    "normalized_qudit_hamiltonian_optimization_integer_results": {}
                }
            }
        )
        == "integer_qudit"
    )
    assert classify_response_mode({"status": "FAILED"}) == "unknown"


def test_coefficient_dynamic_range_ignores_zero_and_preserves_small_values() -> None:
    stats = coefficient_dynamic_range(
        {
            "file_config": {
                "polynomial": {
                    "data": [
                        {"idx": [0, 0, 1], "val": 0.0},
                        {"idx": [0, 0, 2], "val": 2.0},
                        {"idx": [1, 2, 3], "val": -1.0e-15},
                    ]
                }
            }
        }
    )

    assert stats["maximum_nonzero_coefficient"] == 2.0
    assert stats["minimum_nonzero_coefficient"] == 1.0e-15
    assert stats["coefficient_dynamic_range"] == pytest.approx(2.0e15)


def test_audit_counts_only_native_integer_in_domain_samples(tmp_path: Path) -> None:
    run_dir = tmp_path / "repeat_000"
    run_dir.mkdir()
    response_path = run_dir / "response.json"
    request_path = run_dir / "request.json"
    response = _integer_response()
    response["results"]["solutions"].append([0.0, 1.5])
    response_path.write_text(json.dumps(response), encoding="utf-8")
    request_path.write_text(
        json.dumps(
            {
                "job_body": response["job_info"]["job_submission"],
                "qci_file": {
                    "file_config": {
                        "polynomial": {
                            "data": [
                                {"idx": [0, 0, 1], "val": -1.0},
                                {"idx": [1, 1, 2], "val": 0.5},
                            ]
                        }
                    }
                },
                "projected_solutions": [[1, 2]],
            }
        ),
        encoding="utf-8",
    )

    row = audit_response_file(response_path)

    assert row["response_mode"] == "integer_qudit"
    assert row["raw_sample_count"] == 3
    assert row["native_integral_sample_count"] == 2
    assert row["native_in_domain_sample_count"] == 2
    assert row["native_feasible_sample_count"] == 2
    assert row["raw_coordinate_count"] == 6
    assert row["integral_coordinate_count"] == 5
    assert row["fractional_or_invalid_coordinate_count"] == 1
    assert row["bounds_check_available"] is True
    assert row["projected_sample_counted_native"] is False
    assert row["all_raw_coordinates_integral"] is False
    assert row["all_raw_coordinates_in_bounds"] is False


def test_integer_domain_bounds_are_num_levels_minus_one(tmp_path: Path) -> None:
    path = tmp_path / "response.json"
    response = _integer_response()
    response["results"]["solutions"] = [[1, 3]]
    path.write_text(json.dumps(response), encoding="utf-8")

    row = audit_response_file(path)

    assert row["declared_upper_bounds"] == "[1, 2]"
    assert row["native_in_domain_sample_count"] == 0
    assert row["solution_maximum"] == 3.0


def test_boolean_coordinates_are_not_accepted_as_native_integer_samples(tmp_path: Path) -> None:
    path = tmp_path / "response.json"
    response = _integer_response()
    response["results"]["solutions"] = [[True, 1]]
    path.write_text(json.dumps(response), encoding="utf-8")

    row = audit_response_file(path)

    assert row["native_integral_sample_count"] == 0
    assert row["native_in_domain_sample_count"] == 0


def test_root_cause_artifacts_are_derived_from_preserved_responses(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    continuous_dir = results_root / "qci" / "continuous" / "repeat_000"
    integer_dir = results_root / "qci" / "integer" / "repeat_000"
    continuous_dir.mkdir(parents=True)
    integer_dir.mkdir(parents=True)
    (continuous_dir / "response.json").write_text(json.dumps(_continuous_response()), encoding="utf-8")
    (integer_dir / "response.json").write_text(json.dumps(_integer_response()), encoding="utf-8")
    output_dir = results_root / "phase3" / "root_cause_integer_encoding"

    summary = write_root_cause_artifacts(results_root, output_dir)

    assert summary["historical_continuous_mode_qci_job_count"] == 1
    assert summary["historical_integer_mode_qci_job_count"] == 1
    assert (output_dir / "affected_qci_runs.csv").exists()
    assert (output_dir / "response_mode_audit.csv").exists()
    assert (output_dir / "coefficient_dynamic_range_audit.csv").exists()
    report = (output_dir / "root_cause_report.md").read_text(encoding="utf-8")
    assert "continuous-solver misconfiguration ablation" in report
    assert "normalized_qudit_hamiltonian_optimization" in report
    assert "qudit_hamiltonian_optimization" in report


def test_request_only_submission_is_included_in_affected_job_count(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    run_dir = results_root / "qci" / "partial" / "repeat_000"
    run_dir.mkdir(parents=True)
    request = {
        "job_body": _continuous_response()["job_info"]["job_submission"],
        "qci_file": {
            "file_config": {
                "polynomial": {"data": [{"idx": [0, 0, 1], "val": 1.0e-14}]}
            }
        },
    }
    (run_dir / "request.json").write_text(json.dumps(request), encoding="utf-8")
    output_dir = results_root / "phase3" / "root_cause_integer_encoding"

    summary = write_root_cause_artifacts(results_root, output_dir)

    assert summary["historical_continuous_mode_qci_job_count"] == 1
    affected = (output_dir / "affected_qci_runs.csv").read_text(encoding="utf-8")
    assert "repeat_000/request.json" in affected
    assert "normalized_continuous_qudit" in affected
