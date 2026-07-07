import pandas as pd

from cmpo.challenge_score import score_challenge_summary


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset": "case_a",
                "method_name": "CMPO + QCi Dirac-3",
                "critical_energy_not_served_kwh": 5.0,
                "total_hours_critical_infrastructure_unserved": 1.0,
                "max_fraction_customers_unserved_per_hour": 0.1,
                "energy_not_served_kwh": 20.0,
                "critical_load_served_fraction": 0.9,
                "feasibility_after_repair": 1.0,
                "risk_adjusted_cost": 100.0,
                "expected_operating_cost": 90.0,
                "time_to_good_solution": 3.0,
            },
            {
                "dataset": "case_a",
                "method_name": "Strong resilience baseline",
                "critical_energy_not_served_kwh": 0.0,
                "total_hours_critical_infrastructure_unserved": 0.0,
                "max_fraction_customers_unserved_per_hour": 0.0,
                "energy_not_served_kwh": 10.0,
                "critical_load_served_fraction": 1.0,
                "feasibility_after_repair": 1.0,
                "risk_adjusted_cost": 200.0,
                "expected_operating_cost": 150.0,
                "time_to_good_solution": 5.0,
            },
            {
                "dataset": "case_b",
                "method_name": "CMPO + QCi Dirac-3",
                "critical_energy_not_served_kwh": 0.0,
                "total_hours_critical_infrastructure_unserved": 0.0,
                "max_fraction_customers_unserved_per_hour": 0.0,
                "energy_not_served_kwh": 0.0,
                "critical_load_served_fraction": 1.0,
                "feasibility_after_repair": 1.0,
                "risk_adjusted_cost": 10.0,
                "expected_operating_cost": 9.0,
                "time_to_good_solution": 1.0,
            },
            {
                "dataset": "case_b",
                "method_name": "Infeasible cheap baseline",
                "critical_energy_not_served_kwh": 0.0,
                "total_hours_critical_infrastructure_unserved": 0.0,
                "max_fraction_customers_unserved_per_hour": 0.0,
                "energy_not_served_kwh": 0.0,
                "critical_load_served_fraction": 1.0,
                "feasibility_after_repair": 0.0,
                "risk_adjusted_cost": 0.0,
                "expected_operating_cost": 0.0,
                "time_to_good_solution": 0.5,
            },
        ]
    )


def test_weighted_score_prioritizes_resilience_before_cost() -> None:
    scored = score_challenge_summary(_rows(), mode="weighted")
    case_a = scored[scored["dataset"].eq("case_a")].sort_values("challenge_rank")

    assert case_a.iloc[0]["method_name"] == "Strong resilience baseline"
    assert case_a.iloc[0]["best_method_by_challenge_score"] == "Strong resilience baseline"
    qci = case_a[case_a["method_name"].str.contains("QCi")].iloc[0]
    assert qci["qci_outcome_by_challenge_score"] == "qci_loss"
    assert qci["qci_minus_best_challenge_score"] > 0


def test_infeasibility_penalty_beats_lower_cost() -> None:
    scored = score_challenge_summary(_rows(), mode="weighted")
    case_b = scored[scored["dataset"].eq("case_b")].sort_values("challenge_rank")

    assert case_b.iloc[0]["method_name"] == "CMPO + QCi Dirac-3"
    assert case_b.iloc[0]["qci_outcome_by_challenge_score"] == "qci_win"


def test_lexicographic_score_uses_declared_priority_order() -> None:
    scored = score_challenge_summary(_rows(), mode="lexicographic")
    case_a = scored[scored["dataset"].eq("case_a")].sort_values("challenge_rank")

    assert case_a.iloc[0]["method_name"] == "Strong resilience baseline"
    assert list(case_a["challenge_rank"]) == [1, 2]
