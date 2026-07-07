import pandas as pd

from cmpo.qci_sample_selection import select_qci_samples, summarize_qci_selection


def _repeat_rows() -> pd.DataFrame:
    base = {
        "benchmark": "bench",
        "dataset": "bench_adapted",
        "method_name": "CMPO + QCi Dirac-3",
        "payload_name": "payload_a.json",
        "scenario": "storm",
        "patch": "MG1",
        "job_id": "job",
        "feasibility_after_repair": 1.0,
        "pre_repair_violation": True,
        "post_repair_violation": False,
        "raw_solution": '{"x": 1}',
        "repaired_solution": '{"x": 0}',
        "expected_operating_cost": 10.0,
        "risk_adjusted_cost": 10.0,
        "runtime_seconds": 1.0,
        "time_to_good_solution": 1.0,
        "energy_not_served_kwh": 0.0,
        "total_critical_infrastructure_unserved_hours_proxy": 0.0,
    }
    rows = [
        base
        | {
            "repeat": 0,
            "sample_index": 0,
            "qci_energy": -100.0,
            "critical_energy_not_served_kwh": 50.0,
            "max_fraction_customers_unserved_per_hour": 0.5,
            "critical_load_served_fraction": 0.5,
            "energy_not_served_kwh": 60.0,
            "total_critical_infrastructure_unserved_hours_proxy": 6.0,
        },
        base
        | {
            "repeat": 1,
            "sample_index": 0,
            "qci_energy": -10.0,
            "critical_energy_not_served_kwh": 0.0,
            "max_fraction_customers_unserved_per_hour": 0.0,
            "critical_load_served_fraction": 1.0,
        },
        base
        | {
            "repeat": 2,
            "sample_index": 0,
            "qci_energy": -20.0,
            "critical_energy_not_served_kwh": 10.0,
            "max_fraction_customers_unserved_per_hour": 0.1,
            "critical_load_served_fraction": 0.9,
        },
    ]
    return pd.DataFrame(rows)


def test_select_qci_samples_keeps_energy_and_challenge_selectors_separate() -> None:
    selected = select_qci_samples(_repeat_rows())

    by_reason = selected.set_index("selection_reason")
    assert by_reason.loc["best_by_qci_energy", "repeat"] == 0
    assert by_reason.loc["best_by_challenge_score", "repeat"] == 1
    assert by_reason.loc["best_by_critical_ENS", "repeat"] == 1
    assert by_reason.loc["median_by_challenge_score", "selection_rank_within_payload"] == 2
    assert by_reason.loc["best_by_challenge_score", "raw_solution"] == '{"x": 1}'
    assert by_reason.loc["best_by_challenge_score", "repaired_solution"] == '{"x": 0}'


def test_qci_selection_summary_reports_improvement_and_remaining_failures() -> None:
    selected = select_qci_samples(_repeat_rows())
    summary = summarize_qci_selection(selected)

    assert len(summary) == 1
    row = summary.iloc[0]
    assert bool(row["challenge_improves_critical_ENS"]) is True
    assert bool(row["challenge_reduces_max_customers_unserved"]) is True
    assert row["critical_ENS_delta_challenge_minus_energy"] == -50.0
    assert bool(row["best_selector_still_fails"]) is False
