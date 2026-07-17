from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from cmpo.heldout_evaluation import evaluate_sc_cmpo_heldout
from cmpo.qci_result_decode import decode_qci_experiment
from cmpo.scenario_coupled_model import build_sc_cmpo_from_config, load_public_grid, load_sc_cmpo_config
from cmpo.system_level_projection import project_sc_cmpo_payload


def _dispatchable_solution(payload: dict) -> dict[str, float]:
    values = {str(variable["name"]): 0.0 for variable in payload["variables"]}
    values.update(
        {
            "upgrade_select_dispatchable": 1.0,
            "dispatchable_capacity_fraction": 1.0,
            "islanding_eligibility": 1.0,
            "base_mode_connected": 1.0,
            "bess_reserve_target": 1.0,
            "bess_soc_target": 1.0,
            "critical_load_priority": 1.0,
            "tie_pcc_reserve_target": 1.0,
        }
    )
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = str(scenario["name"])
        desired_mode = (
            "restoration"
            if scenario["restoration_mode"]
            else "islanded"
            if scenario["forced_islanding"]
            else "connected"
        )
        values[f"mode_{desired_mode}[{name}]"] = 1.0
        values[f"battery_action_hold[{name}]"] = 1.0
        der_dispatch = 0.0 if scenario["pcc_available"] else 1.0
        values[f"der_commitment[{name}]"] = der_dispatch
        values[f"der_capacity_slack[{name}]"] = (1.0 - der_dispatch) / 3.0
        values[f"critical_load_service[{name}]"] = 1.0
        values[f"tie_pcc_response[{name}]"] = float(bool(scenario["pcc_available"]))
    return values


def _payload_energy(payload: dict, values: dict[str, float]) -> float:
    total = 0.0
    for term in payload["polynomial_terms"]:
        value = float(term["coefficient"])
        for name, power in term["powers"].items():
            value *= values.get(name, 0.0) ** int(power)
        total += value
    return total


def test_sc_cmpo_projection_exposes_deficit_and_dispatchable_upgrade_closes_it() -> None:
    payload = build_sc_cmpo_from_config("configs/phase3_sc_cmpo_case14.yaml")[0].payload

    without_upgrade = project_sc_cmpo_payload(payload, {})
    with_upgrade = project_sc_cmpo_payload(payload, _dispatchable_solution(payload))

    assert without_upgrade["critical_energy_not_served_kwh"] > 0.0
    assert without_upgrade["critical_load_served_fraction"] < 1.0
    assert with_upgrade["critical_energy_not_served_kwh"] == 0.0
    assert with_upgrade["critical_load_served_fraction"] == 1.0
    assert with_upgrade["upgrade_cost"] > 0.0
    assert with_upgrade["post_repair_violation"] == 0.0


def test_sc_cmpo_hamiltonian_prefers_adequate_upgrade_to_no_service() -> None:
    payload = build_sc_cmpo_from_config("configs/phase3_sc_cmpo_case14.yaml")[0].payload
    no_upgrade = {str(variable["name"]): 0.0 for variable in payload["variables"]}
    no_upgrade.update(
        {
            "base_mode_connected": 1.0,
            "islanding_eligibility": 1.0,
            "bess_reserve_target": 1.0,
            "bess_soc_target": 1.0,
            "critical_load_priority": 1.0,
            "tie_pcc_reserve_target": 1.0,
        }
    )
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = str(scenario["name"])
        desired_mode = (
            "restoration"
            if scenario["restoration_mode"]
            else "islanded"
            if scenario["forced_islanding"]
            else "connected"
        )
        served = float(bool(scenario["pcc_available"]))
        no_upgrade[f"mode_{desired_mode}[{name}]"] = 1.0
        no_upgrade[f"battery_action_hold[{name}]"] = 1.0
        no_upgrade[f"critical_load_service[{name}]"] = served
        no_upgrade[f"load_shedding_allocation[{name}]"] = 1.0 - served
        no_upgrade[f"tie_pcc_response[{name}]"] = served

    assert _payload_energy(payload, _dispatchable_solution(payload)) < _payload_energy(payload, no_upgrade)


def test_sc_cmpo_public_topology_includes_arpae_and_ieee_transformers() -> None:
    arpae = load_public_grid(load_sc_cmpo_config("configs/phase3_sc_cmpo_arpae.yaml"))
    ieee123 = load_public_grid(load_sc_cmpo_config("configs/phase3_sc_cmpo_ieee123.yaml"))

    assert sum(edge.edge_id.startswith("transformer_") for edge in arpae.edges) == 131
    assert any(edge.edge_id == "transformer_reg1a" for edge in ieee123.edges)
    assert any(edge.edge_id == "transformer_XFM1" for edge in ieee123.edges)


def test_sc_cmpo_heldout_evaluation_uses_unused_public_n_minus_one_records() -> None:
    config = load_sc_cmpo_config("configs/phase3_sc_cmpo_case14.yaml")
    grid = load_public_grid(config)
    payload = build_sc_cmpo_from_config("configs/phase3_sc_cmpo_case14.yaml")[0].payload

    result = evaluate_sc_cmpo_heldout(grid, payload, _dispatchable_solution(payload), limit=5)

    assert result["heldout_count"] == 5
    assert result["critical_load_served_fraction"] == 1.0
    assert all("source_record" in row for row in result["results"])
    assert "no sampled thresholds or multipliers" in result["evaluation_rule"]


def test_sc_cmpo_qci_decode_preserves_raw_vector_for_projection(tmp_path: Path) -> None:
    payload = build_sc_cmpo_from_config("configs/phase3_sc_cmpo_case14.yaml")[0].payload
    payload_path = tmp_path / "sc_payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    order = [str(variable["name"]) for variable in payload["variables"]]
    solution = _dispatchable_solution(payload)
    repeat_dir = tmp_path / "qci" / payload_path.stem / "repeat_000"
    repeat_dir.mkdir(parents=True)
    (repeat_dir / "request.json").write_text(
        json.dumps(
            {
                "payload_path": str(payload_path),
                "qci_file": {"cmpo_metadata": {"variable_order": order}},
            }
        ),
        encoding="utf-8",
    )
    (repeat_dir / "response.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "job_info": {"job_id": "sc-job", "job_result": {"device_usage_s": 2.0}},
                "results": {"energies": [-1.0], "solutions": [[solution[name] for name in order]]},
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

    assert result["decoded_rows"] == 1
    assert decoded.loc[0, "dataset"] == "pglib_case14_ieee"
    assert decoded.loc[0, "backend"] == "qci_dirac3_sc_cmpo"
    assert decoded.loc[0, "projection_required"]
    assert "dispatchable_capacity_fraction" in decoded.loc[0, "raw_solution"]


def test_sc_cmpo_build_baseline_and_validation_pipeline(tmp_path: Path) -> None:
    import scripts.phase3_build_sc_cmpo_payloads as builder
    import scripts.phase3_run_sc_cmpo_baselines as baselines
    import scripts.phase3_validate_sc_cmpo as validator

    output_dir = tmp_path / "sc_cmpo"
    summary = builder.build_sc_cmpo_artifacts(list(builder.DEFAULT_CONFIGS), output_dir)
    baseline = baselines.run_baselines(
        output_dir / "qci_payloads",
        output_dir / "baselines" / "robust_lp",
        overwrite=False,
        dry_run=False,
    )
    validation = validator.validate(output_dir, max_variables=132, max_degree=3, dry_run=False)

    assert summary["payload_count"] == 43
    assert summary["payload_count_by_benchmark"] == {
        "arpae_go_network_01o_020": 8,
        "ieee123_opendss": 12,
        "pglib_case14_ieee": 9,
        "pglib_case30_ieee": 14,
    }
    with (output_dir / "public_benchmark_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_benchmarks = {row["benchmark"] for row in csv.DictReader(handle)}
    assert provenance_benchmarks == set(summary["payload_count_by_benchmark"])
    assert baseline["completed"] == 43
    assert baseline["feasible"] == 43
    assert validation["ready"] is True
    assert validation["max_variables"] == 103
    assert validation["max_degree"] == 3
