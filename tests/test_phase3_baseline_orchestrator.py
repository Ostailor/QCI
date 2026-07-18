from pathlib import Path

import pandas as pd

from cmpo.baseline_orchestrator import prepare_phase3_payloads, run_classical_baseline_sweep


def test_phase3_baseline_sweep_writes_qci_shaped_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = {
        "name": "baseline_fixture",
        "seed": 42,
        "output_dir": "results/phase3/baseline_fixture",
        "dataset": {
            "name": "baseline_fixture",
            "source": "synthetic",
            "n_microgrids": 3,
            "horizon_hours": 4,
            "n_scenarios": 1,
        },
        "payloads": {"max_patch_size": 1, "max_patches": 1},
        "baselines": {
            "max_iterations": 2,
            "random_restarts": 2,
            "local_steps": 1,
            "include_differential_evolution": False,
            "include_piecewise_milp": True,
            "include_qubo_quadratized": True,
            "qubo_sweeps": 2,
            "include_gpu_random_restart": True,
            "gpu_restarts": 3,
            "include_ipopt_pyomo": True,
            "include_stress_reserve": True,
        },
    }

    prepare_phase3_payloads(config)
    result = run_classical_baseline_sweep(config, repeats=1)

    repeat_metrics = pd.read_csv(result["repeat_metrics"])
    payload_summary = pd.read_csv(result["payload_summary"])
    skip_report = pd.read_csv(result["skip_report"])

    assert not repeat_metrics.empty
    assert not payload_summary.empty
    for column in [
        "payload_name",
        "expected_operating_cost",
        "risk_adjusted_cost",
        "critical_load_served_fraction",
        "total_critical_infrastructure_unserved_hours_proxy",
        "runtime",
        "time_to_good_solution",
        "pre_repair_violation_magnitude",
        "post_repair_violation_magnitude",
        "feasibility_after_repair",
    ]:
        assert column in repeat_metrics.columns
    for column in [
        "expected_operating_cost_best",
        "expected_operating_cost_median",
        "expected_operating_cost_mean",
        "expected_operating_cost_std",
        "runtime_seconds_median",
        "feasibility_rate",
    ]:
        assert column in payload_summary.columns
    assert "QUBO/quadratized local search baseline" in set(repeat_metrics["method_name"])
    methods = set(repeat_metrics["method_name"])
    assert "GPU-parallel random restart baseline" in methods
    assert "IPOPT/Pyomo nonlinear baseline" in set(repeat_metrics["method_name"])
    assert "Stress-only reserve heuristic baseline" in set(repeat_metrics["method_name"])
    assert set(skip_report.columns) == {"method_name", "payload_name", "scenario", "patch", "repeat", "status", "skip_reason"}
