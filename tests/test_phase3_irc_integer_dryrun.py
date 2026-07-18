from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from cmpo.qci_integer_adapter import installed_qci_versions


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    payload = {
        "schema": "cmpo.irc_cmpo.integer_master.v1",
        "objective_sense": "minimize",
        "max_degree": 3,
        "variables": [
            {
                "name": f"y::{index}",
                "encoding_type": "binary",
                "lower_bound": 0,
                "upper_bound": 1,
                "num_levels": 2,
            }
            for index in range(4)
        ],
        "polynomial_terms": [
            {"coefficient": -1.0, "powers": {"y::0": 1}, "degree": 1},
            {"coefficient": 0.5, "powers": {"y::1": 1, "y::2": 1}, "degree": 2},
        ],
    }
    payload_path = tmp_path / "integer_payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    config = {
        "qci": {
            "job_type": "sample-hamiltonian-integer",
            "device_type": "dirac-3",
            "relaxation_schedule": 2,
            "samples_per_job": 30,
            "maximum_total_num_levels": 12,
            "num_levels_limit_source": "test-pinned-device-config",
            "pinned_qci_client_version": installed_qci_versions()["qci-client"],
            "pinned_eqc_models_version": installed_qci_versions()["eqc-models"],
        }
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    results_root = tmp_path / "historical_results"
    continuous_dir = results_root / "continuous" / "repeat_000"
    integer_dir = results_root / "integer" / "repeat_000"
    continuous_dir.mkdir(parents=True)
    integer_dir.mkdir(parents=True)
    (continuous_dir / "response.json").write_text(
        json.dumps(
            {
                "job_info": {
                    "job_id": "old-continuous",
                    "job_submission": {
                        "problem_config": {"normalized_qudit_hamiltonian_optimization": {}},
                        "device_config": {"dirac-3_normalized_qudit": {"sum_constraint": 10000}},
                    },
                },
                "status": "COMPLETED",
                "results": {"solutions": [[0.25, 9999.75]]},
            }
        ),
        encoding="utf-8",
    )
    (integer_dir / "response.json").write_text(
        json.dumps(
            {
                "job_info": {
                    "job_id": "old-integer",
                    "job_submission": {
                        "problem_config": {"qudit_hamiltonian_optimization": {}},
                        "device_config": {"dirac-3_qudit": {"num_levels": [2, 2]}},
                    },
                },
                "status": "COMPLETED",
                "results": {"solutions": [[0, 1]]},
            }
        ),
        encoding="utf-8",
    )
    return payload_path, config_path, results_root


def test_offline_integer_audit_writes_strict_create_only_job_body(tmp_path: Path) -> None:
    payload, config, results_root = _write_fixture(tmp_path)
    output = tmp_path / "integer_adapter_dry_run.json"
    command = [
        sys.executable,
        "scripts/phase3_audit_qci_modes.py",
        "--payload",
        str(payload),
        "--config",
        str(config),
        "--results-root",
        str(results_root),
        "--output",
        str(output),
    ]

    first = subprocess.run(command, cwd=Path(__file__).parents[1], check=False, capture_output=True, text=True)
    second = subprocess.run(command, cwd=Path(__file__).parents[1], check=False, capture_output=True, text=True)

    assert first.returncode == 0, first.stderr
    artifact = json.loads(output.read_text(encoding="utf-8"))
    submission = artifact["job_body"]["job_submission"]
    assert submission["problem_config"] == {
        "qudit_hamiltonian_optimization": {"polynomial_file_id": "OFFLINE_DRY_RUN_NOT_UPLOADED"}
    }
    assert submission["device_config"]["dirac-3_qudit"] == {
        "num_samples": 30,
        "relaxation_schedule": 2,
        "num_levels": [2, 2, 2, 2],
    }
    assert artifact["requested_job_type"] == "sample-hamiltonian-integer"
    assert artifact["requested_job_params"]["device_type"] == "dirac-3"
    assert artifact["requested_job_params"]["num_levels"] == [2, 2, 2, 2]
    assert "sum_constraint" not in json.dumps(artifact["job_body"])
    assert "sum_constraint" not in artifact["requested_job_params"]
    assert artifact["num_levels_audit"] == {
        "limit": 12,
        "limit_source": "test-pinned-device-config",
        "num_levels": [2, 2, 2, 2],
        "total_num_levels": 8,
    }
    assert artifact["versions"] == installed_qci_versions()
    assert artifact["historical_response_mode_audit"]["counts"] == {
        "integer_qudit": 1,
        "normalized_continuous_qudit": 1,
        "unknown": 0,
    }
    assert artifact["strict_response_expectations"] == {
        "required_problem_config": "qudit_hamiltonian_optimization",
        "required_device_config": "dirac-3_qudit",
        "required_num_levels": [2, 2, 2, 2],
        "forbidden": [
            "normalized_qudit_hamiltonian_optimization",
            "dirac-3_normalized_qudit",
            "sum_constraint",
        ],
        "native_coordinates_must_be_integer": True,
        "native_coordinates_must_be_in_domain": True,
        "rounding_or_projection_permitted": False,
    }
    assert artifact["offline_only"] is True
    assert artifact["qci_network_calls"] == 0
    assert artifact["qci_jobs_submitted"] == 0
    assert second.returncode != 0
    assert "overwrite" in second.stderr.lower()


def test_offline_integer_audit_rejects_nonbinary_payload_before_artifact(tmp_path: Path) -> None:
    payload, config, results_root = _write_fixture(tmp_path)
    document = json.loads(payload.read_text(encoding="utf-8"))
    document["variables"][0].update({"encoding_type": "integer", "upper_bound": 2, "num_levels": 3})
    payload.write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "integer_adapter_dry_run.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase3_audit_qci_modes.py",
            "--payload",
            str(payload),
            "--config",
            str(config),
            "--results-root",
            str(results_root),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "binary" in completed.stderr.lower()
    assert not output.exists()
