from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cmpo.arpae_sc_cmpo_adapter import (
    build_arpae_microgrid_candidates,
    parse_arpae_sc_cmpo_case,
)
from cmpo.ieee123_sc_cmpo_adapter import (
    build_ieee123_microgrid_candidates,
    parse_ieee123_sc_cmpo_case,
    validate_ieee123_powerflow,
)
from cmpo.scenario_coupled_model import load_sc_cmpo_config
from scripts.phase3_build_arpae_sc_cmpo import build_arpae_sc_cmpo
from scripts.phase3_build_ieee123_sc_cmpo import build_ieee123_sc_cmpo
from scripts.phase3_validate_distribution_powerflow import validate_distribution_powerflow


ROOT = Path(__file__).resolve().parents[1]
ARPAE_CONFIG = ROOT / "configs" / "phase3_sc_cmpo_arpae.yaml"
IEEE123_CONFIG = ROOT / "configs" / "phase3_sc_cmpo_ieee123.yaml"


def test_arpae_adapter_maps_network_costs_and_single_period() -> None:
    case = parse_arpae_sc_cmpo_case(load_sc_cmpo_config(ARPAE_CONFIG))

    assert len(case.buses) == 500
    assert len(case.loads) == 200
    assert len(case.generators) == 90
    assert sum(record.in_service for record in case.generators) == 80
    assert len(case.branches) == 468
    assert len(case.transformers) == 131
    assert len(case.grid.edges) == 599
    assert len(case.generator_costs) == 90
    assert len(case.grid.contingencies) > 0
    assert all("case.con" in record.source_record for record in case.grid.contingencies)
    assert sum(record.active_power_kw for record in case.loads) == pytest.approx(4_774_182.0)
    assert sum(record.maximum_active_power_kw for record in case.generators if record.in_service) == pytest.approx(
        6_267_403.0
    )
    assert case.time_periods[0].period_id == "single_steady_state"
    assert case.time_periods[0].duration_hours is None
    assert not case.time_periods[0].temporal_profile_available
    assert all(len(record.points_mw_cost) >= 2 for record in case.generator_costs)
    assert all(
        list(point[0] for point in record.points_mw_cost)
        == sorted(point[0] for point in record.points_mw_cost)
        for record in case.generator_costs
    )
    assert case.grid.metadata["generator_cost_mapping"] == "ARPA-E Challenge 1 ROP piece-wise linear tables"
    assert case.grid.metadata["time_period_count"] == 1


def test_arpae_microgrid_candidates_are_deterministic_graph_partitions() -> None:
    case = parse_arpae_sc_cmpo_case(load_sc_cmpo_config(ARPAE_CONFIG))

    first = build_arpae_microgrid_candidates(case, count=8, patch_size=2, deterministic_seed=1020)
    second = build_arpae_microgrid_candidates(case, count=8, patch_size=2, deterministic_seed=1020)

    assert first == second
    assert len(first) == 8
    assert all(candidate.node_ids for candidate in first)
    assert all(candidate.boundary_edge_ids for candidate in first)
    assert all(candidate.islanded_deficit_kw > 0.0 for candidate in first)
    assert all("connected" in candidate.selection_rule.lower() for candidate in first)


def test_ieee123_adapter_preserves_published_distribution_fields() -> None:
    case = parse_ieee123_sc_cmpo_case(load_sc_cmpo_config(IEEE123_CONFIG))

    assert len(case.grid.nodes) == 132
    assert len(case.lines) == 126
    assert len(case.loads) == 91
    assert len(case.transformers) == 8
    assert len(case.regulators) == 7
    assert len(case.capacitors) == 4
    assert len(case.line_codes) >= 12
    assert sum(record.active_power_kw for record in case.loads) == pytest.approx(3490.0)
    assert sum(record.reactive_power_kvar for record in case.loads) == pytest.approx(1920.0)
    assert all(record.phases for record in case.lines)
    assert all(record.resistance_matrix for record in case.lines if not record.is_switch)
    assert all(record.reactance_matrix for record in case.lines if not record.is_switch)
    assert all(record.normal_amps is None for record in case.lines)
    assert case.grid.metadata["published_line_ratings_available"] is False
    assert case.grid.metadata["phase_connections_preserved"] is True
    assert set(case.grid.metadata["auxiliary_source_sha256"]) == {
        "license_path",
        "linecode_path",
        "load_path",
        "regulator_path",
        "switch_path",
    }


def test_ieee123_open_dss_powerflow_matches_repository_parser() -> None:
    case = parse_ieee123_sc_cmpo_case(load_sc_cmpo_config(IEEE123_CONFIG))
    original_working_directory = Path.cwd()

    report = validate_ieee123_powerflow(case)

    assert Path.cwd() == original_working_directory
    assert report["passed"]
    assert report["solver_converged"]
    assert report["engine"] == "OpenDSSDirect.py"
    assert report["engine_counts"]["buses"] == len(case.grid.nodes)
    assert report["engine_counts"]["lines"] == len(case.lines)
    assert report["engine_counts"]["loads"] == len(case.loads)
    assert report["engine_counts"]["transformers"] == len(case.transformers)
    assert report["engine_counts"]["regulators"] == len(case.regulators)
    assert report["engine_counts"]["capacitors"] == len(case.capacitors)
    assert report["engine_total_load_kw"] == pytest.approx(3490.0)
    assert report["engine_total_load_kvar"] == pytest.approx(1920.0)
    assert report["solver_iterations"] > 0
    assert report["active_losses_kw"] > 0.0
    assert report["reactive_losses_kvar"] > 0.0
    assert 0.9 <= report["minimum_voltage_pu"] <= report["maximum_voltage_pu"] <= 1.1
    assert all(check["passed"] for check in report["checks"])


def test_ieee123_microgrid_candidates_are_deterministic_graph_partitions() -> None:
    case = parse_ieee123_sc_cmpo_case(load_sc_cmpo_config(IEEE123_CONFIG))

    candidates = build_ieee123_microgrid_candidates(case, count=12, patch_size=3, deterministic_seed=123)

    assert candidates == build_ieee123_microgrid_candidates(
        case,
        count=12,
        patch_size=3,
        deterministic_seed=123,
    )
    assert len(candidates) == 12
    assert all(candidate.boundary_edge_ids for candidate in candidates)
    assert all(candidate.islanded_deficit_kw > 0.0 for candidate in candidates)


def test_ieee123_source_manifest_includes_redirect_target() -> None:
    manifest = json.loads((ROOT / "data" / "upstream" / "ieee123" / "manifest.json").read_text(encoding="utf-8"))
    paths = {record["local_path"] for record in manifest["files"]}

    assert "data/upstream/ieee123/IEEELineCodes.DSS" in paths


def test_public_builders_write_isolated_payloads_and_merged_provenance(tmp_path: Path) -> None:
    provenance_path = tmp_path / "public_benchmark_provenance.csv"
    validation_path = tmp_path / "distribution_validation.md"

    arpae = build_arpae_sc_cmpo(
        ARPAE_CONFIG,
        tmp_path / "arpae_go",
        provenance_path,
        overwrite=False,
        dry_run=False,
    )
    ieee123 = build_ieee123_sc_cmpo(
        IEEE123_CONFIG,
        tmp_path / "ieee123",
        provenance_path,
        validation_path,
        overwrite=False,
        dry_run=False,
    )

    assert arpae["payload_count"] == 8
    assert ieee123["payload_count"] == 12
    assert not arpae["qci_was_run"]
    assert not ieee123["qci_was_run"]
    assert (tmp_path / "arpae_go" / "generator_costs.csv").is_file()
    assert (tmp_path / "arpae_go" / "microgrid_candidates.csv").is_file()
    assert (tmp_path / "ieee123" / "feeder_lines.csv").is_file()
    assert (tmp_path / "ieee123" / "regulators.csv").is_file()
    assert (tmp_path / "ieee123" / "capacitors.csv").is_file()
    assert len(list((tmp_path / "arpae_go" / "qci_payloads").glob("*.json"))) == 8
    assert len(list((tmp_path / "ieee123" / "qci_payloads").glob("*.json"))) == 12
    assert validation_path.read_text(encoding="utf-8").startswith("# IEEE 123-Bus Distribution Validation")
    provenance_text = provenance_path.read_text(encoding="utf-8")
    assert "arpae_go_network_01o_020" in provenance_text
    assert "ieee123_opendss" in provenance_text
    with provenance_path.open(newline="", encoding="utf-8") as handle:
        provenance_rows = list(csv.DictReader(handle))
    exact_rows = [row for row in provenance_rows if row["source_role"] != "upgrade_costs"]
    assert all(row["sha256"] == row["local_sha256"] for row in exact_rows)
    assert all("full upstream ATB source" in row["checksum_scope"] for row in provenance_rows if row["source_role"] == "upgrade_costs")


def test_distribution_validation_dry_run_executes_engine_without_writing(tmp_path: Path) -> None:
    output_path = tmp_path / "distribution_validation.md"

    result = validate_distribution_powerflow(IEEE123_CONFIG, output_path, dry_run=True)

    assert result["passed"]
    assert result["solver_converged"]
    assert not output_path.exists()
