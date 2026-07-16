import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result_row(method: str, *, dataset: str = "pglib_case5_pjm_adapted", repeat: int = 0) -> dict[str, object]:
    return {
        "dataset": dataset,
        "method_name": method,
        "scenario": "pcc_failure",
        "patch": "BUS1_MG-BUS2_MG",
        "payload_name": "pcc_failure_BUS1_MG-BUS2_MG.json",
        "scenario_probability": 0.25,
        "expected_cost_component": 100.0,
        "critical_load_served_fraction": 0.9,
        "energy_not_served_kwh": 12.0,
        "critical_energy_not_served_kwh": 3.0,
        "max_fraction_customers_unserved_per_hour": 0.1,
        "total_hours_critical_infrastructure_unserved": 2.0,
        "feasibility_pass": True,
        "runtime_seconds": 4.0,
        "wall_clock_runtime_seconds": 4.0,
        "total_upgrade_cost": 0.0,
        "repeat": repeat,
        "backend": "classical",
    }


def test_final_v2_parsers_accept_formulation_flags() -> None:
    dominance = _load_script("phase3_dominance_analysis")
    figures = _load_script("phase3_make_figures")
    tables = _load_script("phase3_make_tables")

    arguments = ["--include-direct-qci", "--include-cmpo-v2", "--include-hybrid"]

    for parser in (tables.build_parser(), figures.build_parser(), dominance.build_parser()):
        parsed = parser.parse_args(arguments)
        assert parsed.include_direct_qci
        assert parsed.include_cmpo_v2
        assert parsed.include_hybrid


def test_collect_rows_includes_requested_formulations_without_duplicate_baselines(tmp_path: Path) -> None:
    tables = _load_script("phase3_make_tables")

    root = tmp_path / "phase3"
    scenario_path = root / "public_benchmarks" / "pglib_case5_pjm" / "scenario_results.csv"
    duplicate_path = root / "public_benchmarks" / "pglib_case5" / "baselines" / "repeat_metrics.csv"
    direct_path = root / "public_benchmarks" / "pglib_case5_pjm" / "decoded" / "qci_repeat_metrics.csv"
    cmpo_v2_path = root / "cmpo_v2" / "decoded" / "qci_repeat_metrics.csv"
    hybrid_path = root / "hybrid" / "comparison" / "projection_metrics.csv"
    for path in (scenario_path, duplicate_path, direct_path, cmpo_v2_path, hybrid_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    baseline = pd.DataFrame([_result_row("GreedyCriticalLoadFirst")])
    baseline.to_csv(scenario_path, index=False)
    baseline.to_csv(duplicate_path, index=False)
    pd.DataFrame([_result_row("CMPO + QCi Dirac-3")]).to_csv(direct_path, index=False)
    pd.DataFrame([_result_row("CMPO + QCi Dirac-3", dataset="pglib_case5_pjm")]).to_csv(
        cmpo_v2_path,
        index=False,
    )
    pd.DataFrame([_result_row("CMPO Hybrid QCi + Classical Projection", dataset="pglib_case5_pjm")]).to_csv(
        hybrid_path,
        index=False,
    )

    collected = tables._collect_rows(
        root,
        include_direct_qci=True,
        include_cmpo_v2=True,
        include_hybrid=True,
    )

    assert len(collected[collected["method_name"] == "GreedyCriticalLoadFirst"]) == 1
    assert set(collected["method_name"]) == {
        "GreedyCriticalLoadFirst",
        "CMPO + QCi Dirac-3",
        "CMPO-V2 + QCi Dirac-3",
        "CMPO Hybrid QCi + Classical Projection",
    }
    assert set(collected["dataset"]) == {"pglib_case5_pjm_adapted"}


def test_balanced_summary_is_invariant_to_repeat_count() -> None:
    tables = _load_script("phase3_make_tables")

    one_repeat = [_result_row("one-repeat", repeat=0)]
    thirty_repeats = [_result_row("thirty-repeats", repeat=repeat) for repeat in range(30)]

    summary = tables._balanced_summary(pd.DataFrame(one_repeat + thirty_repeats)).set_index("method_name")

    for metric in (
        "expected_operating_cost",
        "risk_adjusted_cost",
        "critical_energy_not_served_kwh",
        "energy_not_served_kwh",
        "critical_load_served_fraction",
    ):
        assert summary.loc["one-repeat", metric] == summary.loc["thirty-repeats", metric]
    assert summary.loc["one-repeat", "samples_per_payload_median"] == 1
    assert summary.loc["thirty-repeats", "samples_per_payload_median"] == 30


def test_challenge_win_tie_loss_distinguishes_sole_wins_and_ties() -> None:
    tables = _load_script("phase3_make_tables")

    scored = pd.DataFrame(
        [
            {"score_mode": "weighted", "dataset": "d1", "method_name": "A", "challenge_score": 0.0},
            {"score_mode": "weighted", "dataset": "d1", "method_name": "B", "challenge_score": 0.0},
            {"score_mode": "weighted", "dataset": "d1", "method_name": "C", "challenge_score": 1.0},
            {"score_mode": "weighted", "dataset": "d2", "method_name": "A", "challenge_score": 0.0},
            {"score_mode": "weighted", "dataset": "d2", "method_name": "B", "challenge_score": 1.0},
        ]
    )

    result = tables._challenge_win_tie_loss(scored).set_index("method_name")

    assert result.loc["A", ["wins", "ties", "losses"]].tolist() == [1, 1, 0]
    assert result.loc["B", ["wins", "ties", "losses"]].tolist() == [0, 1, 1]
    assert result.loc["C", ["wins", "ties", "losses"]].tolist() == [0, 0, 1]


def test_final_v2_pareto_uses_cost_and_critical_ens() -> None:
    tables = _load_script("phase3_make_tables")

    summary = pd.DataFrame(
        [
            {"dataset": "d", "method_name": "low-cost", "risk_adjusted_cost": 1.0, "critical_energy_not_served_kwh": 5.0},
            {"dataset": "d", "method_name": "low-ens", "risk_adjusted_cost": 5.0, "critical_energy_not_served_kwh": 1.0},
            {"dataset": "d", "method_name": "dominated", "risk_adjusted_cost": 6.0, "critical_energy_not_served_kwh": 6.0},
        ]
    )

    frontier = tables._pareto_v2(summary)

    assert set(frontier["method_name"]) == {"low-cost", "low-ens"}
    assert frontier["pareto_frontier"].all()
