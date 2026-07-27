from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_runner():
    path = ROOT / "scripts" / "phase3_run_irc_cmpo_gpu_final.py"
    spec = importlib.util.spec_from_file_location("phase3_run_irc_cmpo_gpu_final", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeGPUBackend:
    backend_name = "fake_cupy_cuda"
    gpu_model = "Fake NVIDIA A100"
    cuda_runtime = "12.4"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def generate_candidates(self, method, terms, variable_names, *, candidate_count, seed):
        self.calls.append((method, candidate_count, seed))
        candidates = np.zeros((candidate_count, len(variable_names)), dtype=np.int8)
        candidates[:, 0] = np.arange(candidate_count) % 2
        candidates[:, 1] = (np.arange(candidate_count) // 2) % 2
        candidates[0, :] = 1
        return candidates


def _payload(path: Path, *, valid: bool = True) -> None:
    payload = {
        "schema": "cmpo.irc_cmpo.scalarized_integer_master.v1",
        "num_variables": 2,
        "num_levels": [2, 2],
        "variables": [
            {"name": "y::a", "lower_bound": 0, "upper_bound": 1, "num_levels": 2},
            {"name": "y::b", "lower_bound": 0, "upper_bound": 1, "num_levels": 2},
        ],
        "polynomial_terms": [
            {"coefficient": -2.0, "powers": {"y::a": 1}, "degree": 1},
            {"coefficient": -1.0, "powers": {"y::b": 1}, "degree": 1},
        ],
        "local_feasibility_constraints": [
            {"asset_keys": ["a", "b"], "pattern": [0, 0], "coefficient": 1.0}
        ],
        "dirac3_scaling": {
            "projection_used": False,
            "post_quantization_validation": {"gates_passed": valid},
        },
        "qci_submission": {"permitted": False, "jobs_submitted": 0},
        "resilience_normalization": {"offset": 0.0, "scale": 1.0},
        "cost_scalarization": {
            "lambda": 0.0,
            "maximum_catalog_portfolio_cost": 100.0,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _manifest(tmp_path: Path, *, valid: bool = True) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "payload_manifest_final_prequeue_v3.csv"
    rows = []
    for index in range(6):
        payload_path = tmp_path / f"lambda_{index:02d}.json"
        _payload(payload_path, valid=valid or index != 5)
        rows.append(
            {
                "lambda_index": index,
                "cost_weight": float(index),
                "scaled_payload_path": str(payload_path),
                "post_quantization_gates_passed": valid or index != 5,
                "projection_used": False,
                "qci_jobs_submitted": 0,
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_cuda_backend_failure_is_explicit_and_has_no_cpu_fallback(monkeypatch) -> None:
    runner = _load_runner()

    def missing_cupy(name):
        assert name == "cupy"
        raise ModuleNotFoundError("cupy unavailable")

    monkeypatch.setattr(runner.importlib, "import_module", missing_cupy)

    with pytest.raises(RuntimeError, match="CUDA/CuPy.*CPU fallback is forbidden"):
        runner.require_cupy_backend()


def test_manifest_absolute_payload_path_rebinds_to_portable_results_tree(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _load_runner()
    portable_root = tmp_path / "remote-repo"
    payload = portable_root / "results/phase3/irc_cmpo/payloads_final_prequeue_v3/lambda_00.json"
    payload.parent.mkdir(parents=True)
    payload.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", portable_root)
    stale = "/Users/local/QCI/results/phase3/irc_cmpo/payloads_final_prequeue_v3/lambda_00.json"

    resolved = runner._resolve_input(stale, relative_to=portable_root / "results/phase3/irc_cmpo")

    assert resolved == payload


def test_gpu_final_runner_records_publication_metrics_for_all_six_lambdas(tmp_path: Path) -> None:
    runner = _load_runner()
    backend = FakeGPUBackend()
    output = tmp_path / "final_gpu_baselines"
    recourse_calls = []

    def recourse(payload, state):
        recourse_calls.append((payload, dict(state)))
        return {
            "feasibility": True,
            "selected_solver": "fake shared recourse",
            "total_ens": 12.0,
            "critical_ens": 3.0,
            "upgrade_cost": 7.0,
            "maximum_customers_unserved": 0.2,
            "critical_infrastructure_outage_hours": 1.0,
            "critical_load_served_fraction": 0.9,
            "heldout_critical_ens": 4.0,
            "heldout_total_ens": 14.0,
        }

    result = runner.run_final_gpu_baselines(
        manifest_path=_manifest(tmp_path),
        output_dir=output,
        candidate_count=10_000,
        backend=backend,
        recourse_evaluator=recourse,
    )

    assert result["lambda_count"] == 6
    assert result["projection_used"] is False
    assert result["cpu_fallback_used"] is False
    assert result["gpu_model"] == "Fake NVIDIA A100"
    assert len(backend.calls) == 18
    assert {call[0] for call in backend.calls} == {
        "gpu_simulated_annealing",
        "gpu_random_restart",
        "gpu_parallel_local_search",
    }
    assert {call[1] for call in backend.calls} == {10_000}
    assert len(recourse_calls) == 42
    assert (output / "gpu_baseline_summary.json").exists()
    assert (output / "gpu_baseline_metrics.csv").exists()
    assert (output / "exact_milp_references.json").exists()

    rows = list(csv.DictReader((output / "gpu_baseline_metrics.csv").open(encoding="utf-8")))
    assert len(rows) == 18
    required = {
        "gpu_model",
        "gpu_backend",
        "cuda_runtime",
        "runtime_seconds",
        "candidate_count",
        "native_feasibility_rate",
        "exact_optimum_hit_rate",
        "best_hamiltonian_regret",
        "median_hamiltonian_regret",
        "portfolio_diversity",
        "time_to_good_solution_seconds",
        "best_candidate_recourse_solver",
        "best_candidate_total_ens",
        "best_candidate_critical_ens",
        "best_candidate_upgrade_cost",
        "best_candidate_heldout_critical_ens",
        "best_candidate_heldout_total_ens",
        "best_true_recourse_regret",
        "median_true_recourse_regret",
        "projection_used",
    }
    assert required <= set(rows[0])
    assert all(int(row["candidate_count"]) == 10_000 for row in rows)
    assert all(row["projection_used"] == "False" for row in rows)
    assert all(float(row["best_hamiltonian_regret"]) == pytest.approx(0.0) for row in rows)

    with pytest.raises(FileExistsError, match="create-only"):
        runner.run_final_gpu_baselines(
            manifest_path=_manifest(tmp_path),
            output_dir=output,
            candidate_count=10_000,
            backend=backend,
            recourse_evaluator=recourse,
        )


def test_gpu_final_runner_rejects_unvalidated_payload_and_small_batches(tmp_path: Path) -> None:
    runner = _load_runner()
    backend = FakeGPUBackend()

    with pytest.raises(ValueError, match="at least 10,000"):
        runner.run_final_gpu_baselines(
            manifest_path=_manifest(tmp_path),
            output_dir=tmp_path / "small",
            candidate_count=9_999,
            backend=backend,
            recourse_evaluator=lambda _payload, _state: {},
        )

    with pytest.raises(ValueError, match="quantization gate"):
        runner.run_final_gpu_baselines(
            manifest_path=_manifest(tmp_path / "invalid", valid=False),
            output_dir=tmp_path / "invalid-output",
            candidate_count=10_000,
            backend=backend,
            recourse_evaluator=lambda _payload, _state: {},
        )
    assert not (tmp_path / "invalid-output").exists()
