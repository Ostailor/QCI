from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from cmpo import irc_cmpo_batch as batch
import scripts.phase3_monitor_irc_cmpo_final_batch as monitor


ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self) -> None:
        self.submitted: list[dict[str, object]] = []
        self.uploaded: list[dict[str, object]] = []
        self.process_job_called = False

    def get_allocations(self) -> dict[str, object]:
        return {"allocations": {"dirac": {"metered": True, "seconds": 123.0}}}

    def upload_file(self, *, file: dict[str, object]) -> dict[str, str]:
        self.uploaded.append(file)
        return {"file_id": f"file-{len(self.uploaded):02d}"}

    def build_job_body(self, **kwargs: object) -> dict[str, object]:
        return dict(kwargs)

    def submit_job(self, *, job_body: dict[str, object]) -> dict[str, str]:
        self.submitted.append(job_body)
        return {"job_id": f"job-{len(self.submitted):02d}", "status": "SUBMITTED"}

    def process_job(self, **_: object) -> None:
        self.process_job_called = True
        raise AssertionError("the final batch must never call process_job")


class CancelClient:
    def __init__(self, statuses: dict[str, str]) -> None:
        self.statuses = statuses
        self.cancelled: list[str] = []

    def get_job_status(self, *, job_id: str) -> dict[str, str]:
        return {"status": self.statuses[job_id]}

    def cancel_job(self, *, job_id: str) -> dict[str, str]:
        self.cancelled.append(job_id)
        self.statuses[job_id] = "CANCELLED"
        return {"job_id": job_id, "status": "CANCELLED"}


def test_final_job_specs_have_required_order_samples_and_tags() -> None:
    specs = batch.build_final_job_specs(ROOT)

    assert [spec.name for spec in specs] == [
        "toy",
        "reduced",
        "lambda_03",
        "lambda_00",
        "lambda_01",
        "lambda_02",
        "lambda_04",
        "lambda_05",
    ]
    assert [spec.num_samples for spec in specs] == [30, 30, 100, 100, 100, 100, 100, 100]
    for spec in specs:
        assert {"phase3", "irc-cmpo", "integer", "final", spec.name} <= set(spec.tags)
        assert any(tag.startswith("evidence-") for tag in spec.tags)
    assert "canary" in specs[0].tags
    assert "canary" in specs[1].tags
    assert "canary" in specs[2].tags


def test_final_job_specs_support_fresh_artifact_root(tmp_path: Path) -> None:
    artifact_root = tmp_path / "irc_cmpo"
    specs = batch.build_final_job_specs(
        ROOT,
        artifact_root=artifact_root,
        evidence_tag="evidence-deadbeef",
    )

    assert specs[0].payload_path == artifact_root / "smoke/payloads/toy.json"
    assert specs[1].payload_path == artifact_root / "smoke/payloads/reduced_ieee123.json"
    assert specs[2].payload_path == artifact_root / "payloads/lambda_03.json"
    assert specs[-1].payload_path == artifact_root / "payloads/lambda_05.json"
    assert all("evidence-deadbeef" in spec.tags for spec in specs)


def test_preflight_accepts_checked_in_final_payloads(tmp_path: Path) -> None:
    output = tmp_path / "final_qci_batch"
    result = batch.validate_final_preflight(
        ROOT,
        output_dir=output,
        environ={"QCI_API_URL": "https://example.invalid", "QCI_TOKEN": "secret"},
        versions={"qci-client": "5.0.0", "eqc-models": "0.20.2"},
        allocation={"metered": True, "seconds": 100.0},
    )

    assert result["passed"] is True
    assert result["full_payload_count"] == 6
    assert result["full_payload_gates_passed"] is True


def test_preflight_reads_fresh_artifact_root(tmp_path: Path) -> None:
    artifact_root = tmp_path / "irc_cmpo"
    source_root = ROOT / "results/phase3/irc_cmpo"
    for relative in (
        "preflight_summary.json",
        "smoke/smoke_plan.json",
        "smoke/payloads/toy.json",
        "smoke/payloads/reduced_ieee123.json",
        "payloads/lambda_00.json",
        "payloads/lambda_01.json",
        "payloads/lambda_02.json",
        "payloads/lambda_03.json",
        "payloads/lambda_04.json",
        "payloads/lambda_05.json",
    ):
        source = source_root / relative
        target = artifact_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    result = batch.validate_final_preflight(
        ROOT,
        artifact_root=artifact_root,
        output_dir=tmp_path / "qci",
        environ={"QCI_API_URL": "https://example.invalid", "QCI_TOKEN": "secret"},
        versions={"qci-client": "5.0.0", "eqc-models": "0.20.2"},
        allocation={"metered": True, "seconds": 100.0},
    )

    assert result["passed"] is True
    assert result["artifact_root"] == str(artifact_root)


def test_preflight_rejects_existing_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "final_qci_batch"
    output.mkdir()

    with pytest.raises(FileExistsError):
        batch.validate_final_preflight(
            ROOT,
            output_dir=output,
            environ={"QCI_API_URL": "x", "QCI_TOKEN": "y"},
            versions={"qci-client": "5.0.0", "eqc-models": "0.20.2"},
            allocation={"metered": True, "seconds": 1.0},
        )


def test_submit_batch_queues_all_eight_without_process_job(tmp_path: Path) -> None:
    client = FakeClient()
    output = tmp_path / "final_qci_batch"
    specs = batch.build_final_job_specs(ROOT)
    preflight = batch.validate_final_preflight(
        ROOT,
        output_dir=output,
        environ={"QCI_API_URL": "x", "QCI_TOKEN": "y"},
        versions={"qci-client": "5.0.0", "eqc-models": "0.20.2"},
        allocation=client.get_allocations()["allocations"]["dirac"],
    )

    manifest = batch.submit_final_batch(
        client,
        specs,
        output_dir=output,
        preflight=preflight,
        git_commit="31e8c858deadbeef",
    )

    assert client.process_job_called is False
    assert len(client.submitted) == 8
    assert len(manifest["jobs"]) == 8
    assert (output / "batch_manifest.json").is_file()
    assert (output / "job_status.csv").is_file()
    assert (output / "allocation_snapshot.json").is_file()
    assert len(list((output / "requests").glob("*.json"))) == 8
    assert len(list((output / "responses").glob("*.submit.json"))) == 8
    assert not list((output / "validations").iterdir())
    for body in client.submitted:
        assert body["job_type"] == "sample-hamiltonian-integer"
        assert "sum_constraint" not in json.dumps(body)


def test_canary_integer_gate_uses_counts_and_rejects_projection() -> None:
    payload = json.loads(
        (ROOT / "results/phase3/irc_cmpo/smoke/payloads/toy.json").read_text()
    )
    optimum = json.loads(
        (ROOT / "results/phase3/irc_cmpo/smoke/smoke_plan.json").read_text()
    )["jobs"][0]["known_exact_optimum"]
    response = {
        "status": "COMPLETED",
        "job_info": {
            "job_submission": {
                "job_type": "sample-hamiltonian-integer",
                "problem_config": {"qudit_hamiltonian_optimization": {}},
                "device_config": {"dirac-3_qudit": {"num_levels": payload["num_levels"]}},
            }
        },
        "results": {
            "counts": [30],
            "energies": [optimum["energy"]],
            "solutions": [optimum["coordinates"]],
        },
    }

    accepted = batch.validate_canary_response(
        "toy", payload, response, known_exact_optimum=optimum
    )
    response["projected_solutions"] = [optimum["coordinates"]]
    rejected = batch.validate_canary_response(
        "toy", payload, response, known_exact_optimum=optimum
    )

    assert accepted["passed"] is True
    assert accepted["raw_sample_count"] == 30
    assert rejected["passed"] is False


def test_failed_canary_cancels_only_active_full_jobs() -> None:
    jobs = [
        {"name": "lambda_00", "job_id": "a"},
        {"name": "lambda_01", "job_id": "b"},
        {"name": "lambda_02", "job_id": "c"},
        {"name": "toy", "job_id": "toy"},
    ]
    client = CancelClient({"a": "QUEUED", "b": "COMPLETED", "c": "RUNNING", "toy": "ERRORED"})

    report = batch.cancel_active_full_jobs(client, jobs, reason="toy canary failed")

    assert client.cancelled == ["a", "c"]
    assert report["cancelled_job_ids"] == ["a", "c"]
    assert report["reason"] == "toy canary failed"


def test_monitor_cli_imports_repo_scripts_when_run_by_path() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/phase3_monitor_irc_cmpo_final_batch.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_final_artifact_generator_writes_complete_create_only_set(
    tmp_path: Path, monkeypatch
) -> None:
    fake_root = tmp_path / "repo"
    gpu_dir = fake_root / "results/phase3/irc_cmpo/baselines/gpu"
    gpu_dir.mkdir(parents=True)
    (gpu_dir / "gpu_baseline_summary.json").write_text("{}", encoding="utf-8")
    (gpu_dir / "exact_milp_references.json").write_text("{}", encoding="utf-8")
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    jobs = []
    evaluations = {}
    exact_reports = {}
    gpu_rows = []
    base_metrics = {
        "upgrade_cost": 2_000_000.0,
        "critical_ens": 100.0,
        "total_ens": 500.0,
        "maximum_customers_unserved": 0.2,
        "critical_infrastructure_outage_hours": 2.0,
        "critical_load_served_fraction": 0.9,
        "heldout_critical_ens": 120.0,
        "heldout_total_ens": 550.0,
        "feasibility": True,
    }
    for index in range(6):
        name = f"lambda_{index:02d}"
        payload_path = ROOT / f"results/phase3/irc_cmpo/payloads/{name}.json"
        jobs.append({"name": name, "payload_path": str(payload_path), "job_id": f"job-{index}"})
        evaluations[name] = {
            "best_true_recourse_portfolio": dict(base_metrics),
            "best_hamiltonian_regret": 0.0,
            "median_hamiltonian_regret": 0.1,
            "best_true_recourse_regret": 0.0,
            "returned_sample_count": 100,
            "native_integer_rate": 1.0,
            "native_local_feasibility_rate": 0.8,
            "unique_feasible_portfolios": 5,
            "exact_optimum_hit_rate": 0.1,
            "projection_used": False,
            "device_usage_seconds": 1.0,
            "end_to_end_wall_clock_seconds": 2.0,
            "time_to_good_solution_seconds": 1.0,
        }
        exact_reports[index] = {
            "exact_optimum_recourse": dict(base_metrics),
            "true_recourse_regret": 0.0,
        }
        for method in (
            "gpu_simulated_annealing",
            "gpu_random_restart",
            "gpu_parallel_local_search",
        ):
            gpu_rows.append(
                {
                    "lambda_index": index,
                    "method": method,
                    "best_candidate_upgrade_cost": base_metrics["upgrade_cost"],
                    "best_candidate_critical_ens": base_metrics["critical_ens"],
                    "best_candidate_total_ens": base_metrics["total_ens"],
                    "best_candidate_recourse_feasible": True,
                    "best_hamiltonian_regret": 0.0,
                    "median_hamiltonian_regret": 0.1,
                    "native_feasibility_rate": 0.8,
                    "portfolio_diversity": 5,
                    "exact_optimum_hit_rate": 0.1,
                    "candidate_count": 10_000,
                    "gpu_model": "NVIDIA L4",
                    "gpu_backend": "cupy_cuda",
                    "runtime_seconds": 1.0,
                    "time_to_good_solution_seconds": 1.0,
                }
            )
    (batch_dir / "batch_manifest.json").write_text(
        json.dumps({"jobs": jobs}), encoding="utf-8"
    )
    import pandas as pd

    pd.DataFrame(gpu_rows).to_csv(gpu_dir / "gpu_baseline_metrics.csv", index=False)
    dataset = pd.DataFrame(
        [
            {**base_metrics, "generation_method": "qubo"},
            {
                **base_metrics,
                "upgrade_cost": 2_100_000.0,
                "total_ens": 490.0,
                "generation_method": "gpu_random_feasible",
            },
        ]
    )
    dataset_path = tmp_path / "dataset.csv"
    dataset.to_csv(dataset_path, index=False)
    output = tmp_path / "generated-final"
    exact_path = tmp_path / "exact.json"
    exact_path.write_text(
        json.dumps(
            {
                "reports": [
                    {"lambda_index": index, **report}
                    for index, report in exact_reports.items()
                ]
            }
        ),
        encoding="utf-8",
    )

    result = monitor.generate_final_artifacts(
        batch_dir=batch_dir,
        evaluations=evaluations,
        gpu_dir=gpu_dir,
        output_dir=output,
        dataset_path=dataset_path,
        exact_validation_path=exact_path,
    )

    assert result["ready"] is True
    assert len(list(output.glob("*.csv"))) == 8
    assert len(list(output.glob("*.png"))) == 8
    assert (output / "final_results.md").is_file()
    assert (output / "final_handoff.md").is_file()
    reused = monitor.generate_final_artifacts(
        batch_dir=batch_dir,
        evaluations=evaluations,
        gpu_dir=gpu_dir,
        output_dir=output,
        dataset_path=dataset_path,
        exact_validation_path=exact_path,
    )
    assert reused["existing_create_only_artifacts_reused"] is True
