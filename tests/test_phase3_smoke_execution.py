import json
from pathlib import Path

import pandas as pd

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.hybrid_mode_model import build_hybrid_mode_payload
from cmpo.qci_result_decode import decode_qci_experiment


def _hybrid_fixture(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    grid_case = generate_synthetic_dataset(
        DatasetConfig(seed=42, n_microgrids=2, horizon_hours=2),
        output_dir=tmp_path / "source_data",
    )
    scenario = grid_case.scenarios[0]
    patch = ["MG1"]
    built = build_hybrid_mode_payload(
        grid_case,
        scenario,
        patch,
        source_payload_path="source.json",
        source_payload_id="source",
    )
    payload_path = tmp_path / "hybrid_payload.json"
    payload_path.write_text(json.dumps(built.payload), encoding="utf-8")
    variable_order = [str(variable["name"]) for variable in built.payload["variables"]]
    raw = {
        name: float(
            "mode_connected" in name
            or "critical_priority_critical_first" in name
            or "battery_reserve_holdback_reserve" in name
            or "der_commitment_resilience_der" in name
            or "tie_pcc_available_decision" in name
            or name == "scenario_response[shed_avoidance]"
        )
        for name in variable_order
    }
    input_dir = tmp_path / "experiment" / "qci"
    repeat_dir = input_dir / payload_path.stem / "repeat_000"
    repeat_dir.mkdir(parents=True)
    request = {
        "payload_path": str(payload_path),
        "qci_file": {"cmpo_metadata": {"variable_order": variable_order}},
    }
    response = {
        "status": "COMPLETED",
        "job_info": {"job_id": "hybrid-job", "job_result": {"device_usage_s": 1.25}},
        "results": {
            "energies": [-4.5],
            "solutions": [[raw[name] for name in variable_order]],
        },
    }
    (repeat_dir / "request.json").write_text(json.dumps(request), encoding="utf-8")
    (repeat_dir / "response.json").write_text(json.dumps(response), encoding="utf-8")
    config = {
        "name": "hybrid_fixture",
        "dataset": {
            "source": "synthetic",
            "name": "hybrid_fixture",
            "seed": 42,
            "n_microgrids": 2,
            "horizon_hours": 2,
        },
    }
    return input_dir, payload_path, config, raw


def test_run_qci_payload_list_selects_exact_paths(tmp_path: Path) -> None:
    import scripts.phase3_run_qci as run_qci

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    payload_list = tmp_path / "smoke_payloads.txt"
    payload_list.write_text(f"# paired smoke payloads\n{first}\n\n{second}\n", encoding="utf-8")

    args = run_qci.build_parser().parse_args(
        ["--payload-list", str(payload_list), "--output-dir", str(tmp_path / "qci"), "--repeats", "10"]
    )
    payloads = run_qci.resolve_payload_paths(
        payload_dir=None,
        payload_list=Path(args.payload_list),
    )

    assert payloads == [first, second]


def test_decode_qci_experiment_accepts_direct_input_and_output_dirs(tmp_path: Path) -> None:
    input_dir, _payload_path, config, _raw = _hybrid_fixture(tmp_path)
    output_dir = tmp_path / "explicit_decoded"

    result = decode_qci_experiment(
        experiment_dir=input_dir.parent,
        input_dir=input_dir,
        output_dir=output_dir,
        config=config,
    )

    assert Path(result["qci_repeat_metrics_csv"]).parent == output_dir
    assert result["decoded_rows"] == 1


def test_hybrid_decode_preserves_qci_mode_variables_for_projection(tmp_path: Path) -> None:
    input_dir, _payload_path, config, _raw = _hybrid_fixture(tmp_path)
    output_dir = tmp_path / "decoded"

    result = decode_qci_experiment(
        experiment_dir=input_dir.parent,
        input_dir=input_dir,
        output_dir=output_dir,
        config=config,
    )
    decoded = pd.read_csv(result["qci_repeat_metrics_csv"])

    assert decoded.loc[0, "projection_required"]
    assert decoded.loc[0, "payload_schema"] == "cmpo.hybrid_qci_mode_payload.v1"
    assert decoded.loc[0, "qci_energy"] == -4.5
    assert "mode_connected[MG1,0]" in decoded.loc[0, "decoded_variables"]


def test_hybrid_decode_infers_public_benchmark_config_without_cli_config(tmp_path: Path) -> None:
    payload_path = Path(
        "results/phase3/hybrid/qci_payloads/"
        "pglib_case5_pjm__hybrid__pcc_failure_BUS3_MG-BUS4_MG.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    variable_order = [str(variable["name"]) for variable in payload["variables"]]
    repeat_dir = tmp_path / "qci" / payload_path.stem / "repeat_000"
    repeat_dir.mkdir(parents=True)
    (repeat_dir / "request.json").write_text(
        json.dumps(
            {
                "payload_path": str(payload_path),
                "qci_file": {"cmpo_metadata": {"variable_order": variable_order}},
            }
        ),
        encoding="utf-8",
    )
    (repeat_dir / "response.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "job_info": {"job_id": "public-hybrid-job"},
                "results": {"energies": [0.0], "solutions": [[0.0] * len(variable_order)]},
            }
        ),
        encoding="utf-8",
    )

    result = decode_qci_experiment(
        experiment_dir=tmp_path,
        input_dir=tmp_path / "qci",
        output_dir=tmp_path / "decoded",
        config=None,
    )
    decoded = pd.read_csv(result["qci_repeat_metrics_csv"])

    assert decoded.loc[0, "dataset"] == "pglib_case5_pjm"


def test_hybrid_projection_decodes_modes_and_passes_common_repair(tmp_path: Path) -> None:
    from cmpo.hybrid_dispatch_projection import (
        decode_hybrid_mode_decisions,
        project_dispatch_from_hybrid_modes,
    )

    input_dir, payload_path, config, raw = _hybrid_fixture(tmp_path)
    del input_dir, config
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    grid_case = generate_synthetic_dataset(
        DatasetConfig(seed=42, n_microgrids=2, horizon_hours=2),
        output_dir=tmp_path / "projection_data",
    )
    scenario = grid_case.scenarios[0]
    patch = ["MG1"]
    model, _ = build_scenario_hamiltonian(
        grid_case,
        scenario,
        patch,
        output_dir=tmp_path / "projection_model",
        write_export=False,
    )

    decisions = decode_hybrid_mode_decisions(raw, payload)
    projected = project_dispatch_from_hybrid_modes(
        grid_case,
        scenario,
        patch,
        decisions,
        model=model,
        payload_name=payload_path.name,
        source_payload_path=str(payload_path),
    )

    assert decisions["mode[MG1,0]"] == "connected"
    assert decisions["battery_reserve[MG1,0]"] == "holdback_reserve"
    assert projected["status"] == "projected"
    assert projected["feasibility_after_repair"]
    assert projected["max_balance_residual"] <= 1e-4
    assert projected["post_repair_violation"] is False


def test_smoke_comparison_uses_challenge_score_without_claiming_from_cost_alone() -> None:
    import scripts.phase3_compare_smoke as compare_smoke

    common = {
        "dataset": "pglib_case5_pjm",
        "scenario": "pcc_failure",
        "patch": "BUS1_MG-BUS2_MG",
        "payload_name": "payload.json",
        "feasibility_after_repair": 1.0,
        "energy_not_served_kwh": 10.0,
        "total_hours_critical_infrastructure_unserved": 0.0,
        "runtime_seconds": 2.0,
        "job_id": "job",
        "qci_energy": -1.0,
    }
    direct = pd.DataFrame(
        [
            common
            | {
                "critical_energy_not_served_kwh": 5.0,
                "critical_load_served_fraction": 0.9,
                "max_fraction_customers_unserved_per_hour": 0.1,
                "risk_adjusted_cost": 50.0,
                "expected_operating_cost": 40.0,
            }
        ]
    )
    hybrid = pd.DataFrame(
        [
            common
            | {
                "critical_energy_not_served_kwh": 0.0,
                "critical_load_served_fraction": 1.0,
                "max_fraction_customers_unserved_per_hour": 0.0,
                "risk_adjusted_cost": 100.0,
                "expected_operating_cost": 90.0,
            }
        ]
    )

    scored = compare_smoke.score_smoke_samples(direct, hybrid)

    best = scored.sort_values("challenge_score").iloc[0]
    assert best["formulation"] == "hybrid"
    assert best["risk_adjusted_cost"] > direct.loc[0, "risk_adjusted_cost"]
