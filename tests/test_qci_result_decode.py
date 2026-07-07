import json
from pathlib import Path

import pandas as pd

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.qci_export import export_polynomial_model_payload
from cmpo.qci_result_decode import decode_qci_experiment


def _write_qci_fixture(tmp_path: Path) -> tuple[Path, dict]:
    grid_case = generate_synthetic_dataset(
        DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4),
        output_dir=tmp_path / "payload_data",
    )
    scenario = grid_case.scenarios[0]
    patch = ("MG1",)
    model, metadata = build_scenario_hamiltonian(
        grid_case,
        scenario,
        patch,
        output_dir=tmp_path / "payloads",
        write_export=False,
    )
    payload_path = export_polynomial_model_payload(model, metadata, tmp_path / "payloads")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    experiment_dir = tmp_path / "results" / "phase3" / "decode_fixture"
    raw_dir = experiment_dir / "qci" / "raw"
    raw_dir.mkdir(parents=True)
    variable_order = [variable["name"] for variable in payload["variables"]]
    request = {
        "payload_path": str(payload_path),
        "qci_file": {
            "cmpo_metadata": {
                "variable_order": variable_order,
                "scenario_metadata": payload["scenario_metadata"],
                "patch_metadata": payload["patch_metadata"],
            }
        },
    }
    response = {
        "status": "COMPLETED",
        "job_info": {"job_id": "job-ok", "job_result": {"device_usage_s": 3.5}},
        "results": {"energies": [-1.25], "solutions": [[0.0] * len(variable_order)]},
    }
    (raw_dir / "repeat_000_request.json").write_text(json.dumps(request), encoding="utf-8")
    (raw_dir / "repeat_000_response.json").write_text(json.dumps(response), encoding="utf-8")
    (raw_dir / "repeat_001_response.json").write_text(
        json.dumps({"status": "FAILED", "job_info": {"job_id": "job-fail"}, "failure_reason": "capacity exhausted"}),
        encoding="utf-8",
    )
    config = {
        "name": "decode_fixture",
        "dataset": {"source": "synthetic", "name": "decode_fixture", "seed": 42, "n_microgrids": 3, "horizon_hours": 4},
    }
    return experiment_dir, config


def test_decode_qci_experiment_writes_metrics_and_failure_report(tmp_path: Path) -> None:
    experiment_dir, config = _write_qci_fixture(tmp_path)

    result = decode_qci_experiment(experiment_dir=experiment_dir, config=config)

    repeat_metrics = pd.read_csv(result["qci_repeat_metrics_csv"])
    payload_summary = pd.read_csv(result["qci_payload_summary_csv"])
    best_solutions = pd.read_csv(result["qci_best_solutions_csv"])
    failure_report = pd.read_csv(result["qci_failure_report_csv"])

    assert result["decoded_rows"] == 1
    assert result["failed_rows"] == 1
    assert repeat_metrics.loc[0, "job_id"] == "job-ok"
    assert repeat_metrics.loc[0, "qci_energy"] == -1.25
    assert repeat_metrics.loc[0, "runtime_seconds"] == 3.5
    assert "expected_operating_cost" in repeat_metrics.columns
    assert "risk_adjusted_cost" in repeat_metrics.columns
    assert "critical_load_served_fraction" in repeat_metrics.columns
    assert "total_critical_infrastructure_unserved_hours_proxy" in repeat_metrics.columns
    assert "P_gen[MG1,0]" in repeat_metrics.loc[0, "raw_solution"]
    assert payload_summary.loc[0, "sample_count"] == 1
    assert best_solutions.loc[0, "job_id"] == "job-ok"
    assert failure_report.loc[0, "job_id"] == "job-fail"
    assert failure_report.loc[0, "failure_reason"] == "capacity exhausted"


def test_decode_qci_experiment_dry_run_counts_raw_responses(tmp_path: Path) -> None:
    experiment_dir, config = _write_qci_fixture(tmp_path)

    result = decode_qci_experiment(experiment_dir=experiment_dir, config=config, dry_run=True)

    assert result["dry_run"] is True
    assert result["response_files"] == 2


def test_decode_qci_experiment_maps_raw_response_filename_through_manifest(tmp_path: Path) -> None:
    experiment_dir, config = _write_qci_fixture(tmp_path)
    raw_dir = experiment_dir / "qci" / "raw"
    request_path = raw_dir / "repeat_000_request.json"
    payload_path = Path(json.loads(request_path.read_text(encoding="utf-8"))["payload_path"])
    request_path.unlink()
    (raw_dir / "repeat_000_response.json").rename(raw_dir / f"{payload_path.stem}_repeat_000_response.json")
    (experiment_dir / "payload_manifest.json").write_text(
        json.dumps({"payloads": [{"path": str(payload_path)}]}),
        encoding="utf-8",
    )

    result = decode_qci_experiment(experiment_dir=experiment_dir, config=config)
    repeat_metrics = pd.read_csv(result["qci_repeat_metrics_csv"])

    assert result["decoded_rows"] == 1
    assert repeat_metrics.loc[0, "payload_name"] == payload_path.name
