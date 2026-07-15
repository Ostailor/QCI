import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from cmpo.qci_client_adapter import (
    convert_cmpo_payload_to_qci_file,
    load_qci_dotenv,
    load_cmpo_payload,
    run_payload_repeats,
    validate_qci_environment,
    write_job_status_csv,
)


def _payload() -> dict:
    return {
        "schema": "cmpo.qci_payload.v1",
        "objective_sense": "minimize",
        "max_degree": 3,
        "variables": [
            {"name": "x", "lower_bound": 0.0, "upper_bound": 1.0},
            {"name": "y", "lower_bound": 0.0, "upper_bound": 1.0},
        ],
        "polynomial_terms": [
            {"coefficient": -1.0, "powers": {"x": 2}, "degree": 2},
            {"coefficient": 2.0, "powers": {"x": 1, "y": 1}, "degree": 2},
            {"coefficient": -0.5, "powers": {"y": 3}, "degree": 3},
        ],
        "scenario_metadata": {"scenario": "normal"},
        "patch_metadata": {"patch": "MG1", "patch_ids": ["MG1"]},
        "model_statistics": {"variable_count": 2, "term_count": 3, "degree": 3},
    }


def _write_payload(path: Path) -> Path:
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    return path


class MockQciClient:
    def __init__(self) -> None:
        self.jobs = []

    def get_allocations(self):
        return {"allocations": {"dirac": {"metered": True, "seconds": 100}}}

    def upload_file(self, *, file):
        assert file["file_config"]["polynomial"]["num_variables"] == 2
        return {"file_id": "file-123"}

    def build_job_body(self, **kwargs):
        assert kwargs["job_type"] == "sample-hamiltonian"
        assert kwargs["job_params"]["device_type"] == "dirac-3"
        assert "relaxation_schedule" in kwargs["job_params"]
        if "sum_constraint" in kwargs["job_params"]:
            assert kwargs["job_params"]["sum_constraint"] == 1
        assert kwargs["polynomial_file_id"] == "file-123"
        return {"job_submission": kwargs}

    def process_job(self, *, job_body):
        self.jobs.append(job_body)
        return {
            "job_info": {"job_id": f"job-{len(self.jobs)}"},
            "status": "COMPLETED",
            "results": {"energies": [-1.0], "solutions": [[1, 0]]},
        }


def _install_mock_qci(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(QciClient=MockQciClient)
    monkeypatch.setitem(sys.modules, "qci_client", module)
    monkeypatch.setenv("QCI_API_URL", "https://api.qci-prod.com")
    monkeypatch.setenv("QCI_TOKEN", "token")


def test_validate_qci_environment_requires_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QCI_API_URL", raising=False)
    monkeypatch.delenv("QCI_TOKEN", raising=False)
    monkeypatch.setenv("QCI_ENV_FILE", str(Path("missing.env")))

    with pytest.raises(RuntimeError, match="QCI_API_URL"):
        validate_qci_environment()


def test_validate_qci_environment_loads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(QciClient=MockQciClient)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        'QCI_API_URL="https://api.qci-prod.com"\nQCI_TOKEN="token-from-dotenv"\n',
        encoding="utf-8",
    )
    monkeypatch.setitem(sys.modules, "qci_client", module)
    monkeypatch.delenv("QCI_API_URL", raising=False)
    monkeypatch.delenv("QCI_TOKEN", raising=False)
    monkeypatch.setenv("QCI_ENV_FILE", str(dotenv))

    loaded = load_qci_dotenv(dotenv)
    validated = validate_qci_environment()

    assert loaded["QCI_API_URL"] == "https://api.qci-prod.com"
    assert loaded["QCI_TOKEN"] == "token-from-dotenv"
    assert validated == {"QCI_API_URL": "https://api.qci-prod.com", "QCI_TOKEN": "***"}


def test_convert_cmpo_payload_to_qci_file_uses_one_based_repeated_indices() -> None:
    qci_file = convert_cmpo_payload_to_qci_file(_payload())

    polynomial = qci_file["file_config"]["polynomial"]
    assert polynomial["num_variables"] == 2
    assert polynomial["min_degree"] == 2
    assert polynomial["max_degree"] == 3
    assert polynomial["data"] == [
        {"idx": [0, 1, 1], "val": -1.0},
        {"idx": [0, 1, 2], "val": 2.0},
        {"idx": [2, 2, 2], "val": -0.5},
    ]
    assert qci_file["cmpo_metadata"]["variable_order"] == ["x", "y"]


def test_run_payload_repeats_writes_request_response_and_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_mock_qci(monkeypatch)
    payload_path = _write_payload(tmp_path / "payload.json")
    output_dir = tmp_path / "qci"
    config = {
        "name": "test_phase3",
        "qci": {"relaxation_schedule": 2, "sum_constraint": 1, "job_tags": ["cmpo-test"]},
        "overwrite": False,
    }

    records = run_payload_repeats(payload_path, 2, output_dir, config)
    status_path = write_job_status_csv(records, output_dir / "job_status.csv")

    assert len(records) == 2
    assert status_path.exists()
    assert b"\r\n" not in status_path.read_bytes()
    assert records[0]["job_id"] == "job-1"
    assert records[0]["status"] == "COMPLETED"
    assert json.loads(records[0]["raw_energies"]) == [-1.0]
    assert json.loads(records[0]["raw_solutions"]) == [[1, 0]]
    assert Path(records[0]["request_json"]).exists()
    assert Path(records[0]["response_json"]).exists()
    request = json.loads(Path(records[0]["request_json"]).read_text(encoding="utf-8"))
    assert request["job_body"]["job_submission"]["job_params"]["device_type"] == "dirac-3"


def test_run_payload_repeats_does_not_overwrite_existing_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_mock_qci(monkeypatch)
    payload_path = _write_payload(tmp_path / "payload.json")
    output_dir = tmp_path / "qci"
    config = {"name": "test_phase3", "qci": {"relaxation_schedule": 1}, "overwrite": False}

    first = run_payload_repeats(payload_path, 1, output_dir, config)
    second = run_payload_repeats(payload_path, 1, output_dir, config)

    assert first[0]["status"] == "COMPLETED"
    assert second[0]["status"] == "SKIPPED_COMPLETED"
    assert "not overwritten" in second[0]["failure_reason"]


def test_load_cmpo_payload_rejects_missing_keys(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required keys"):
        load_cmpo_payload(path)
