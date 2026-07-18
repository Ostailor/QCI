from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cmpo.qci_integer_adapter import (
    build_integer_job_body,
    derive_num_levels,
    installed_qci_versions,
    native_integer_samples,
    resolve_dirac3_num_levels_limit,
    solve_with_eqc_models,
    submit_integer_job,
    validate_integer_response,
)


def _variables() -> list[dict[str, object]]:
    return [
        {"name": "binary", "encoding_type": "binary", "lower_bound": 0, "upper_bound": 1},
        {"name": "integer", "encoding_type": "integer", "lower_bound": 0, "upper_bound": 3},
    ]


def _valid_response() -> dict[str, object]:
    return {
        "status": "COMPLETED",
        "job_info": {
            "job_id": "integer-job",
            "job_submission": {
                "problem_config": {"qudit_hamiltonian_optimization": {"polynomial_file_id": "poly"}},
                "device_config": {
                    "dirac-3_qudit": {
                        "num_samples": 2,
                        "relaxation_schedule": 1,
                        "num_levels": [2, 4],
                    }
                },
            },
        },
        "results": {"energies": [-2.0, -1.0], "solutions": [[1, 3], [0, 2]]},
    }


class FakeClient:
    dirac3_num_levels_limit = 12

    def __init__(self) -> None:
        self.built: dict[str, object] | None = None

    def build_job_body(self, **kwargs: object) -> dict[str, object]:
        self.built = kwargs
        return {"job_submission": kwargs}


def test_binary_and_general_integer_domains_derive_num_levels() -> None:
    assert derive_num_levels(_variables()) == [2, 4]
    assert derive_num_levels(_variables()[:1]) == [2]


@pytest.mark.parametrize(
    "variable, message",
    [
        ({"name": "x", "encoding_type": "continuous", "lower_bound": 0, "upper_bound": 1}, "integer"),
        ({"name": "x", "encoding_type": "integer", "lower_bound": 1, "upper_bound": 2}, "lower_bound"),
        ({"name": "x", "encoding_type": "integer", "lower_bound": 0, "upper_bound": 1.5}, "upper_bound"),
    ],
)
def test_invalid_integer_domains_are_rejected(variable: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        derive_num_levels([variable])


def test_integer_job_body_uses_integer_job_type_and_never_sum_constraint() -> None:
    client = FakeClient()

    body = build_integer_job_body(
        client,
        polynomial_file_id="poly",
        job_name="integer-test",
        job_tags=["phase3", "integer"],
        num_samples=30,
        relaxation_schedule=2,
        num_levels=[2, 4],
    )

    assert body["job_submission"]["job_type"] == "sample-hamiltonian-integer"
    params = body["job_submission"]["job_params"]
    assert params == {
        "device_type": "dirac-3",
        "num_samples": 30,
        "relaxation_schedule": 2,
        "num_levels": [2, 4],
    }
    assert "sum_constraint" not in json.dumps(body)


def test_integer_job_body_rejects_unsupported_relaxation_schedule() -> None:
    with pytest.raises(ValueError, match="between 1 and 4"):
        build_integer_job_body(
            FakeClient(),
            polynomial_file_id="poly",
            job_name="integer-test",
            job_tags=["phase3"],
            num_samples=30,
            relaxation_schedule=5,
            num_levels=[2, 2],
        )


def test_num_levels_limit_is_discovered_from_client_and_enforced() -> None:
    client = FakeClient()
    assert resolve_dirac3_num_levels_limit(client=client) == (12, "client.dirac3_num_levels_limit")

    with pytest.raises(ValueError, match="exceed.*12"):
        build_integer_job_body(
            client,
            polynomial_file_id="poly",
            job_name="too-large",
            job_tags=[],
            num_samples=30,
            relaxation_schedule=1,
            num_levels=[7, 6],
        )


def test_missing_device_limit_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="num_levels limit"):
        resolve_dirac3_num_levels_limit(client=object())


def test_submit_integer_job_uses_direct_qci_client_body() -> None:
    class SubmittingClient(FakeClient):
        def get_allocations(self) -> dict[str, object]:
            return {"allocations": {"dirac": {"metered": True, "seconds": 10}}}

        def upload_file(self, *, file: dict[str, object]) -> dict[str, str]:
            assert "file_config" in file
            return {"file_id": "poly"}

        def process_job(self, *, job_body: dict[str, object]) -> dict[str, object]:
            assert job_body["job_submission"]["job_type"] == "sample-hamiltonian-integer"
            return _valid_response()

    result = submit_integer_job(
        SubmittingClient(),
        qci_file={"file_name": "integer", "file_config": {"polynomial": {}}},
        job_name="integer-test",
        job_tags=["phase3"],
        num_samples=30,
        relaxation_schedule=1,
        num_levels=[2, 4],
    )

    assert result["response"]["job_info"]["job_id"] == "integer-job"
    assert result["requested_job_type"] == "sample-hamiltonian-integer"
    assert result["requested_job_params"]["num_levels"] == [2, 4]
    assert "sum_constraint" not in result["requested_job_params"]
    assert result["validation"].valid


def test_eqc_models_path_uses_integer_solver_without_sum_constraint() -> None:
    calls: dict[str, object] = {}

    class FakeModel:
        upper_bound = [1, 3]

    class FakeIntegerSolver:
        dirac3_num_levels_limit = 12

        def __init__(self, url: str | None = None, api_token: str | None = None) -> None:
            calls["init"] = {"url": url, "api_token": api_token}

        def solve(self, model: object, **kwargs: object) -> dict[str, object]:
            calls["solve"] = kwargs
            return _valid_response()

    result = solve_with_eqc_models(
        FakeModel(),
        num_samples=30,
        relaxation_schedule=2,
        num_levels=[2, 4],
        job_name="eqc-integer",
        job_tags=["phase3"],
        api_url="https://example.invalid",
        api_token="secret",
        solver_class=FakeIntegerSolver,
    )

    assert calls["solve"] == {
        "name": "eqc-integer",
        "tags": ["phase3"],
        "num_samples": 30,
        "relaxation_schedule": 2,
        "wait": True,
    }
    assert "sum_constraint" not in calls["solve"]
    assert result["validation"].valid


def test_eqc_models_path_unwraps_solution_results_raw_response() -> None:
    class FakeModel:
        upper_bound = [1, 3]

    class SolutionResultsLike:
        response = _valid_response()

        def to_dict(self) -> dict[str, object]:
            return {"solutions": [[1, 3]], "response": self.response}

    class FakeIntegerSolver:
        dirac3_num_levels_limit = 954

        def __init__(self, url: str | None = None, api_token: str | None = None) -> None:
            pass

        def solve(self, model: object, **kwargs: object) -> SolutionResultsLike:
            return SolutionResultsLike()

    result = solve_with_eqc_models(
        FakeModel(),
        num_samples=30,
        relaxation_schedule=1,
        num_levels=[2, 4],
        job_name="eqc-integer",
        job_tags=["phase3"],
        solver_class=FakeIntegerSolver,
    )

    assert result["response"]["job_info"]["job_id"] == "integer-job"
    assert result["validation"].valid


def test_valid_integer_response_accepts_native_in_domain_samples_without_projection() -> None:
    validation = validate_integer_response(_valid_response(), expected_num_levels=[2, 4])

    assert validation.valid
    assert validation.native_sample_count == 2
    assert validation.native_integer_in_domain_count == 2
    assert validation.projected_sample_count == 0
    assert native_integer_samples(_valid_response(), expected_num_levels=[2, 4]) == [[1, 3], [0, 2]]


@pytest.mark.parametrize(
    "mutate, message",
    [
        (
            lambda response: response["job_info"]["job_submission"]["problem_config"].update(
                {"normalized_qudit_hamiltonian_optimization": {}}
            ),
            "normalized_qudit_hamiltonian_optimization",
        ),
        (
            lambda response: response["job_info"]["job_submission"]["device_config"].update(
                {"dirac-3_normalized_qudit": {}}
            ),
            "dirac-3_normalized_qudit",
        ),
        (
            lambda response: response["job_info"]["job_submission"]["device_config"]["dirac-3_qudit"].update(
                {"sum_constraint": 10}
            ),
            "sum_constraint",
        ),
    ],
)
def test_normalized_or_sum_constrained_responses_are_rejected(mutate, message: str) -> None:
    response = _valid_response()
    mutate(response)

    validation = validate_integer_response(response, expected_num_levels=[2, 4])

    assert not validation.valid
    assert message in " ".join(validation.errors)


def test_response_declaring_continuous_job_type_is_rejected() -> None:
    response = _valid_response()
    response["job_info"]["job_submission"]["job_type"] = "sample-hamiltonian"

    validation = validate_integer_response(response, expected_num_levels=[2, 4])

    assert not validation.valid
    assert "sample-hamiltonian-integer" in " ".join(validation.errors)


def test_noncompleted_integer_response_is_rejected() -> None:
    response = _valid_response()
    response["status"] = "FAILED"

    validation = validate_integer_response(response, expected_num_levels=[2, 4])

    assert not validation.valid
    assert "COMPLETED" in " ".join(validation.errors)


def test_expected_num_levels_must_be_integral() -> None:
    with pytest.raises(ValueError, match="expected_num_levels"):
        validate_integer_response(_valid_response(), expected_num_levels=[2, 4.5])


@pytest.mark.parametrize("solutions", [[[0.5, 2]], [[2, 1]], [[1, -1]], [[1]], [[True, 1]]])
def test_noninteger_or_out_of_domain_native_samples_are_rejected(solutions: list[list[object]]) -> None:
    response = _valid_response()
    response["results"]["solutions"] = solutions

    validation = validate_integer_response(response, expected_num_levels=[2, 4])

    assert not validation.valid
    assert validation.native_integer_in_domain_count == 0


def test_projected_samples_are_never_counted_as_native() -> None:
    response = _valid_response()
    response["results"]["solutions"] = [[0.4, 2.2]]
    response["projected_solutions"] = [[0, 2]]

    validation = validate_integer_response(response, expected_num_levels=[2, 4])

    assert validation.native_integer_in_domain_count == 0
    assert validation.projected_sample_count == 1
    with pytest.raises(ValueError, match="native integer"):
        native_integer_samples(response, expected_num_levels=[2, 4])


def test_installed_versions_report_pinned_qci_packages() -> None:
    versions = installed_qci_versions()
    assert versions["qci-client"] == "5.0.0"
    assert versions["eqc-models"] == "0.20.2"


def test_response_validation_cli_rejects_normalized_mode(tmp_path: Path) -> None:
    response = _valid_response()
    response["job_info"]["job_submission"]["problem_config"] = {
        "normalized_qudit_hamiltonian_optimization": {}
    }
    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase3_validate_qci_integer_response.py",
            str(response_path),
            "--num-levels",
            "2,4",
        ],
        cwd=Path(__file__).parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "normalized_qudit_hamiltonian_optimization" in completed.stdout


def test_integer_runner_dry_run_writes_non_overwriting_request_preview(tmp_path: Path) -> None:
    payload = {
        "schema": "irc_cmpo.qci_payload.v1",
        "objective_sense": "minimize",
        "max_degree": 1,
        "variables": [
            {"name": "x", "encoding_type": "binary", "lower_bound": 0, "upper_bound": 1},
            {"name": "z", "encoding_type": "integer", "lower_bound": 0, "upper_bound": 3},
        ],
        "polynomial_terms": [
            {"coefficient": -1.0, "powers": {"x": 1}, "degree": 1},
            {"coefficient": 0.5, "powers": {"z": 1}, "degree": 1},
        ],
    }
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    output_dir = tmp_path / "raw"
    command = [
        sys.executable,
        "scripts/phase3_run_qci_integer.py",
        str(payload_path),
        "--output-dir",
        str(output_dir),
        "--num-samples",
        "30",
        "--relaxation-schedule",
        "1",
        "--max-total-num-levels",
        "12",
        "--limit-source",
        "test-fixture",
    ]

    first = subprocess.run(
        command,
        cwd=Path(__file__).parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        command,
        cwd=Path(__file__).parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0
    preview = json.loads((output_dir / "request_preview.json").read_text(encoding="utf-8"))
    assert preview["job_type"] == "sample-hamiltonian-integer"
    assert preview["job_params"]["num_levels"] == [2, 4]
    assert "sum_constraint" not in json.dumps(preview)
    assert second.returncode == 1
    assert "not overwrite" in second.stderr
