from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from cmpo.sc_cmpo_reporting import _build_table6, _method_repeat_summary, finalize_sc_cmpo_reporting


TABLE_FILENAMES = (
    "table1_system_level_qci_vs_baselines.csv",
    "table2_upgrade_cost_and_resilience.csv",
    "table3_heldout_contingencies.csv",
    "table4_public_benchmark_ladder.csv",
    "table5_encoding_efficiency.csv",
    "table6_resource_usage.csv",
    "win_tie_loss_system_level.csv",
    "pareto_frontier_system_level.csv",
)

FIGURE_FILENAMES = (
    "system_cost_vs_resilience_pareto.png",
    "upgrade_cost_vs_outage_reduction.png",
    "heldout_critical_ens.png",
    "customer_unserved_by_scenario.png",
    "consensus_convergence.png",
    "native_cubic_vs_qubo_encoding.png",
    "qci_repeat_distribution.png",
)


def test_resource_table_does_not_count_derived_qci_headline_as_repeat() -> None:
    rows = []
    for repeat in range(3):
        rows.append(
            {
                "benchmark": "bench",
                "method": "QCi SC-CMPO",
                "headline_selection": False,
                "end_to_end_runtime_seconds": 10.0,
                "wall_clock_runtime_seconds": 10.0,
                "patch_runtime_seconds": 9.0,
                "consensus_runtime_seconds": 1.0,
                "time_to_good_solution": 10.0,
                "consensus_iterations": 2,
                "wall_clock_budget_seconds_per_patch": 0.0,
                "critical_energy_not_served_kwh": float(repeat),
                "max_fraction_customers_unserved_per_hour": 0.1,
                "total_hours_critical_infrastructure_unserved": 1.0,
                "risk_adjusted_cost": 100.0,
                "runtime_seconds": 10.0,
                "trace_source": "qci_system_metrics.csv",
            }
        )
    rows.append({**rows[0], "headline_selection": True})
    metrics = pd.DataFrame(rows)

    table = _build_table6(metrics, _method_repeat_summary(metrics))

    assert table.loc[0, "system_repeat_count"] == 3
    assert table.loc[0, "derived_headline_candidate_count"] == 1
    assert table.loc[0, "budget_basis"] == "3 completed Dirac-3 samples per payload"
    assert table.loc[0, "end_to_end_runtime_seconds_total"] == 10.0
    assert "counted once" in table.loc[0, "runtime_accounting_basis"]
    assert pd.isna(table.loc[0, "wall_clock_budget_seconds_per_patch"])


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _build_fixture(root: Path) -> tuple[Path, Path, Path]:
    phase3_root = root / "phase3" / "sc_cmpo"
    system_level_dir = phase3_root / "system_level"
    payload_dir = phase3_root / "qci_payloads"
    output_dir = root / "reporting"
    payload_dir.mkdir(parents=True, exist_ok=True)

    qci_rows = [
        {
            "benchmark": "bench_a",
            "method": "QCi SC-CMPO",
            "total_upgrade_cost": 90.0,
            "expected_operating_cost": 20.0,
            "risk_adjusted_cost": 25.0,
            "max_fraction_customers_unserved_per_hour": 0.10,
            "total_hours_critical_infrastructure_unserved": 2.0,
            "critical_energy_not_served_kwh": 12.0,
            "total_energy_not_served_kwh": 18.0,
            "critical_load_served_fraction": 0.92,
            "full_system_feasibility": True,
            "consensus_iterations": 3,
            "consensus_residual": 0.001,
            "time_to_good_solution": 6.0,
            "end_to_end_runtime_seconds": 11.0,
            "system_trace_id": "sys-qci-a",
            "wall_clock_runtime_seconds": 11.0,
            "patch_runtime_seconds": 4.0,
            "consensus_runtime_seconds": 1.0,
        },
        {
            "benchmark": "bench_b",
            "method": "QCi SC-CMPO",
            "total_upgrade_cost": 80.0,
            "expected_operating_cost": 24.0,
            "risk_adjusted_cost": 30.0,
            "max_fraction_customers_unserved_per_hour": 0.12,
            "total_hours_critical_infrastructure_unserved": 3.0,
            "critical_energy_not_served_kwh": 15.0,
            "total_energy_not_served_kwh": 19.0,
            "critical_load_served_fraction": 0.89,
            "full_system_feasibility": True,
            "consensus_iterations": 4,
            "consensus_residual": 0.002,
            "time_to_good_solution": 7.0,
            "end_to_end_runtime_seconds": 12.0,
            "system_trace_id": "sys-qci-b",
            "wall_clock_runtime_seconds": 12.0,
            "patch_runtime_seconds": 4.5,
            "consensus_runtime_seconds": 1.5,
        },
    ]
    _write_csv(system_level_dir / "qci_system_metrics.csv", qci_rows)

    baseline_rows = [
        {
            "benchmark": "bench_a",
            "method": "piecewise-linear MILP",
            "total_upgrade_cost": 95.0,
            "expected_operating_cost": 30.0,
            "risk_adjusted_cost": 34.0,
            "max_fraction_customers_unserved_per_hour": 0.16,
            "total_hours_critical_infrastructure_unserved": 3.0,
            "critical_energy_not_served_kwh": 20.0,
            "total_energy_not_served_kwh": 28.0,
            "critical_load_served_fraction": 0.84,
            "full_system_feasibility": True,
            "consensus_iterations": 3,
            "consensus_residual": 0.003,
            "time_to_good_solution": 8.0,
            "end_to_end_runtime_seconds": 14.0,
            "system_trace_id": "sys-milp-a",
            "wall_clock_runtime_seconds": 14.0,
            "patch_runtime_seconds": 5.0,
            "consensus_runtime_seconds": 1.2,
        },
        {
            "benchmark": "bench_a",
            "method": "QUBO/quadratized search",
            "total_upgrade_cost": 110.0,
            "expected_operating_cost": 35.0,
            "risk_adjusted_cost": 42.0,
            "max_fraction_customers_unserved_per_hour": 0.18,
            "total_hours_critical_infrastructure_unserved": 4.0,
            "critical_energy_not_served_kwh": 24.0,
            "total_energy_not_served_kwh": 31.0,
            "critical_load_served_fraction": 0.80,
            "full_system_feasibility": True,
            "consensus_iterations": 3,
            "consensus_residual": 0.005,
            "time_to_good_solution": 9.0,
            "end_to_end_runtime_seconds": 16.0,
            "system_trace_id": "sys-qubo-a",
            "wall_clock_runtime_seconds": 16.0,
            "patch_runtime_seconds": 6.0,
            "consensus_runtime_seconds": 1.5,
        },
        {
            "benchmark": "bench_b",
            "method": "piecewise-linear MILP",
            "total_upgrade_cost": 70.0,
            "expected_operating_cost": 18.0,
            "risk_adjusted_cost": 22.0,
            "max_fraction_customers_unserved_per_hour": 0.08,
            "total_hours_critical_infrastructure_unserved": 1.0,
            "critical_energy_not_served_kwh": 8.0,
            "total_energy_not_served_kwh": 10.0,
            "critical_load_served_fraction": 0.95,
            "full_system_feasibility": True,
            "consensus_iterations": 2,
            "consensus_residual": 0.001,
            "time_to_good_solution": 5.0,
            "end_to_end_runtime_seconds": 10.0,
            "system_trace_id": "sys-milp-b",
            "wall_clock_runtime_seconds": 10.0,
            "patch_runtime_seconds": 3.0,
            "consensus_runtime_seconds": 1.0,
        },
        {
            "benchmark": "bench_b",
            "method": "QUBO/quadratized search",
            "total_upgrade_cost": 88.0,
            "expected_operating_cost": 26.0,
            "risk_adjusted_cost": 31.0,
            "max_fraction_customers_unserved_per_hour": 0.14,
            "total_hours_critical_infrastructure_unserved": 2.0,
            "critical_energy_not_served_kwh": 17.0,
            "total_energy_not_served_kwh": 21.0,
            "critical_load_served_fraction": 0.88,
            "full_system_feasibility": True,
            "consensus_iterations": 4,
            "consensus_residual": 0.004,
            "time_to_good_solution": 8.0,
            "end_to_end_runtime_seconds": 15.0,
            "system_trace_id": "sys-qubo-b",
            "wall_clock_runtime_seconds": 15.0,
            "patch_runtime_seconds": 5.5,
            "consensus_runtime_seconds": 1.4,
        },
    ]
    _write_csv(system_level_dir / "baseline_system_metrics.csv", baseline_rows)

    scenario_rows: list[dict[str, object]] = []
    for benchmark, method, critical_ens, fraction in (
        ("bench_a", "QCi SC-CMPO", 4.0, 0.04),
        ("bench_a", "piecewise-linear MILP", 6.0, 0.08),
        ("bench_b", "QCi SC-CMPO", 5.0, 0.06),
        ("bench_b", "piecewise-linear MILP", 2.0, 0.02),
    ):
        for scenario, multiplier in (("normal", 1.0), ("forced_islanding", 1.5)):
            scenario_rows.append(
                {
                    "benchmark": benchmark,
                    "method": method,
                    "scenario": scenario,
                    "critical_energy_not_served_kwh": critical_ens * multiplier,
                    "fraction_customers_unserved_per_hour": fraction * multiplier,
                    "scenario_probability": 0.5,
                    "projection_status": "completed",
                    "system_trace_id": f"{benchmark}-{method}-{scenario}",
                }
            )
    _write_csv(system_level_dir / "scenario_results.csv", scenario_rows)

    upgrade_rows = [
        {
            "benchmark": "bench_a",
            "method": "QCi SC-CMPO",
            "asset_key": "bench_a::dispatchable",
            "technology": "dispatchable_generation",
            "installed_cost": 90.0,
            "system_trace_id": "sys-qci-a",
        },
        {
            "benchmark": "bench_a",
            "method": "piecewise-linear MILP",
            "asset_key": "bench_a::dispatchable",
            "technology": "dispatchable_generation",
            "installed_cost": 95.0,
            "system_trace_id": "sys-milp-a",
        },
        {
            "benchmark": "bench_b",
            "method": "QUBO/quadratized search",
            "asset_key": "bench_b::dispatchable",
            "technology": "dispatchable_generation",
            "installed_cost": 88.0,
            "system_trace_id": "sys-qubo-b",
        },
    ]
    _write_csv(system_level_dir / "upgrade_plan_comparison.csv", upgrade_rows)

    convergence_rows = [
        {
            "benchmark": "bench_a",
            "method": "QCi SC-CMPO",
            "primal_residual": 0.001,
            "dual_residual": 0.0005,
            "iteration_count": 3,
            "converged": True,
        },
        {
            "benchmark": "bench_b",
            "method": "piecewise-linear MILP",
            "primal_residual": 0.0007,
            "dual_residual": 0.0003,
            "iteration_count": 2,
            "converged": True,
        },
    ]
    _write_csv(system_level_dir / "consensus_convergence.csv", convergence_rows)

    _write_csv(
        system_level_dir / "qci_patch_solutions.csv",
        [
            {
                "benchmark": "bench_a",
                "method": "QCi SC-CMPO",
                "payload_name": "bench_a_patch_01.json",
                "solution_id": "qci-sol-1",
                "solution_values_json": "{}",
            }
        ],
    )
    _write_csv(
        system_level_dir / "baseline_patch_solutions.csv",
        [
            {
                "benchmark": "bench_a",
                "method": "QUBO/quadratized search",
                "payload_name": "bench_a_patch_01.json",
                "runtime_seconds": 1.2,
                "variable_count": 18,
                "status": "completed",
            },
            {
                "benchmark": "bench_b",
                "method": "QUBO/quadratized search",
                "payload_name": "bench_b_patch_01.json",
                "runtime_seconds": 1.0,
                "variable_count": 24,
                "status": "completed",
            },
        ],
    )

    _write_csv(
        system_level_dir / "qci_repeat_system_metrics.csv",
        [
            {
                "benchmark": "bench_a",
                "method": "QCi SC-CMPO",
                "repeat": 0,
                "risk_adjusted_cost": 24.0,
                "critical_energy_not_served_kwh": 11.0,
                "end_to_end_runtime_seconds": 10.0,
            },
            {
                "benchmark": "bench_a",
                "method": "QCi SC-CMPO",
                "repeat": 1,
                "risk_adjusted_cost": 25.0,
                "critical_energy_not_served_kwh": 12.0,
                "end_to_end_runtime_seconds": 11.0,
            },
            {
                "benchmark": "bench_a",
                "method": "QCi SC-CMPO",
                "repeat": 2,
                "risk_adjusted_cost": 26.0,
                "critical_energy_not_served_kwh": 13.0,
                "end_to_end_runtime_seconds": 12.0,
            },
            {
                "benchmark": "bench_b",
                "method": "QCi SC-CMPO",
                "repeat": 0,
                "risk_adjusted_cost": 29.0,
                "critical_energy_not_served_kwh": 14.0,
                "end_to_end_runtime_seconds": 11.0,
            },
            {
                "benchmark": "bench_b",
                "method": "QCi SC-CMPO",
                "repeat": 1,
                "risk_adjusted_cost": 30.0,
                "critical_energy_not_served_kwh": 15.0,
                "end_to_end_runtime_seconds": 12.0,
            },
        ],
    )

    _write_csv(
        system_level_dir / "heldout_summary.csv",
        [
            {
                "benchmark": "bench_a",
                "patch_id": "bench_a_patch_01",
                "heldout_count": 4,
                "critical_energy_not_served_kwh": 9.0,
                "critical_load_served_fraction": 0.93,
                "feasibility_rate": 1.0,
            },
            {
                "benchmark": "bench_b",
                "patch_id": "bench_b_patch_01",
                "heldout_count": 3,
                "critical_energy_not_served_kwh": 7.0,
                "critical_load_served_fraction": 0.95,
                "feasibility_rate": 1.0,
            },
        ],
    )
    _write_csv(
        system_level_dir / "heldout_contingencies.csv",
        [
            {
                "benchmark": "bench_a",
                "patch_id": "bench_a_patch_01",
                "contingency_id": "c1",
                "critical_energy_not_served_kwh": 4.0,
                "feasibility_after_projection": True,
            },
            {
                "benchmark": "bench_b",
                "patch_id": "bench_b_patch_01",
                "contingency_id": "c2",
                "critical_energy_not_served_kwh": 3.0,
                "feasibility_after_projection": True,
            },
        ],
    )

    (system_level_dir / "consensus_manifest.json").write_text(
        json.dumps({"schema": "cmpo.sc_cmpo.system_consensus.v1", "entries": [], "qci_decoded_paths": []}),
        encoding="utf-8",
    )

    _write_csv(
        phase3_root / "model_stats.csv",
        [
            {
                "benchmark": "bench_a",
                "payload_name": "bench_a_patch_01.json",
                "variable_count": 10,
                "term_count": 21,
                "degree": 3,
            },
            {
                "benchmark": "bench_b",
                "payload_name": "bench_b_patch_01.json",
                "variable_count": 12,
                "term_count": 25,
                "degree": 3,
            },
        ],
    )
    _write_csv(
        phase3_root / "payload_manifest.csv",
        [
            {
                "benchmark": "bench_a",
                "payload_name": "bench_a_patch_01.json",
                "qci_executable": True,
                "variable_count": 10,
                "degree": 3,
            },
            {
                "benchmark": "bench_b",
                "payload_name": "bench_b_patch_01.json",
                "qci_executable": True,
                "variable_count": 12,
                "degree": 3,
            },
        ],
    )
    _write_csv(
        phase3_root / "public_benchmark_provenance.csv",
        [
            {
                "benchmark": "bench_a",
                "source_name": "Benchmark A",
                "source_url": "https://example.com/a",
                "local_sha256": "sha-a",
                "version": "v1",
            },
            {
                "benchmark": "bench_b",
                "source_name": "Benchmark B",
                "source_url": "https://example.com/b",
                "local_sha256": "sha-b",
                "version": "v1",
            },
        ],
    )

    return system_level_dir, payload_dir, output_dir


def test_finalize_sc_cmpo_reporting_writes_all_expected_outputs(tmp_path: Path) -> None:
    system_level_dir, payload_dir, output_dir = _build_fixture(tmp_path)

    result = finalize_sc_cmpo_reporting(system_level_dir, payload_dir, output_dir)

    assert result["dry_run"] is False
    assert set(result["tables"]) == set(TABLE_FILENAMES)
    assert set(result["figures"]) == set(FIGURE_FILENAMES)

    for filename in TABLE_FILENAMES:
        path = output_dir / filename
        assert path.exists(), filename
        frame = pd.read_csv(path)
        assert not frame.empty, filename
        assert "trace_source" in frame.columns, filename
        assert frame["trace_source"].astype(str).str.len().gt(0).all(), filename

    for filename in FIGURE_FILENAMES:
        path = output_dir / filename
        assert path.exists(), filename
        assert path.stat().st_size > 0, filename

    table1 = pd.read_csv(output_dir / "table1_system_level_qci_vs_baselines.csv")
    assert set(table1["benchmark"]) == {"bench_a", "bench_b"}
    assert "qci_vs_best_outcome_lexicographic" in table1.columns
    assert "qci_critical_ens_ci_low" in table1.columns
    assert "qci_critical_ens_repeat_n" in table1.columns

    wtl = pd.read_csv(output_dir / "win_tie_loss_system_level.csv")
    assert set(wtl["score_mode"]) == {"lexicographic", "weighted"}

    pareto = pd.read_csv(output_dir / "pareto_frontier_system_level.csv")
    assert pareto["pareto_frontier"].all()


def test_phase3_finalize_sc_cmpo_dry_run_writes_nothing(tmp_path: Path) -> None:
    system_level_dir, payload_dir, output_dir = _build_fixture(tmp_path)

    command = [
        sys.executable,
        "scripts/phase3_finalize_sc_cmpo.py",
        "--system-level-dir",
        str(system_level_dir),
        "--payload-dir",
        str(payload_dir),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    ]
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["dry_run"] is True
    assert payload["output_dir"] == str(output_dir)
    assert not output_dir.exists()
