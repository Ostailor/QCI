from __future__ import annotations

from pathlib import Path

from cmpo.consensus_stitching import stitch_shared_first_stage
from cmpo.heldout_evaluation import parse_public_contingencies


def test_stitch_shared_first_stage_uses_median_majority_and_consistency() -> None:
    payload_solutions = [
        {
            "payload_name": "patch_mg1_mg2",
            "first_stage": {
                "frac_MG1_gen": 0.2,
                "sel_MG1_gen": 0.0,
                "frac_MG2_gen": 1.0,
                "sel_MG2_gen": 1.0,
            },
        },
        {
            "payload_name": "patch_mg1_mg3",
            "first_stage": {
                "frac_MG1_gen": 1.4,
                "sel_MG1_gen": 1.0,
                "frac_MG3_bess": -0.1,
                "sel_MG3_bess": 1.0,
            },
        },
        {
            "payload_name": "patch_mg1_mg4",
            "first_stage": {
                "frac_MG1_gen": 0.8,
                "sel_MG1_gen": 0.0,
            },
        },
    ]
    variable_specs = {
        "frac_MG1_gen": {
            "kind": "continuous",
            "bounds": (0.0, 1.0),
            "selection_variable": "sel_MG1_gen",
            "capacity": 20.0,
        },
        "sel_MG1_gen": {"kind": "binary", "linked_fraction_variable": "frac_MG1_gen"},
        "frac_MG2_gen": {
            "kind": "continuous",
            "bounds": (0.0, 1.0),
            "selection_variable": "sel_MG2_gen",
            "capacity": 10.0,
        },
        "sel_MG2_gen": {"kind": "binary", "linked_fraction_variable": "frac_MG2_gen"},
        "frac_MG3_bess": {
            "kind": "continuous",
            "bounds": (0.0, 1.0),
            "selection_variable": "sel_MG3_bess",
            "capacity": 6.0,
        },
        "sel_MG3_bess": {"kind": "binary", "linked_fraction_variable": "frac_MG3_bess"},
    }

    stitched = stitch_shared_first_stage(payload_solutions, variable_specs)

    assert stitched["stitched_values"]["frac_MG1_gen"] == 0.8
    assert stitched["stitched_values"]["sel_MG1_gen"] == 1
    assert stitched["applied_capacities"]["frac_MG1_gen"] == 16.0
    assert stitched["stitched_values"]["frac_MG2_gen"] == 1.0
    assert stitched["stitched_values"]["sel_MG2_gen"] == 1
    assert stitched["stitched_values"]["frac_MG3_bess"] == 0.0
    assert stitched["stitched_values"]["sel_MG3_bess"] == 0
    assert stitched["support"]["frac_MG1_gen"] == 3
    assert stitched["support"]["sel_MG1_gen"] == 3
    assert "sel_MG1_gen" in stitched["consistency_adjustments"]
    assert "sel_MG3_bess" in stitched["consistency_adjustments"]


def test_parse_public_contingencies_extracts_branch_ids_from_public_records() -> None:
    path = Path(
        "data/public_benchmarks/arpae_go/extracted/"
        "Challenge_1_Original_Dataset_2_Scenarios/Original_Dataset_Real-Time_Edition_2/"
        "Network_03R-020/scenario_1/case.con"
    )

    records = parse_public_contingencies(path)

    assert records[:3] == [
        {"branch_id": "95-96-1", "contingency_id": "LINE-95-96-1", "from_bus": 95, "to_bus": 96, "circuit": "1"},
        {"branch_id": "95-99-1", "contingency_id": "LINE-95-99-1", "from_bus": 95, "to_bus": 99, "circuit": "1"},
        {"branch_id": "97-98-1", "contingency_id": "LINE-97-98-1", "from_bus": 97, "to_bus": 98, "circuit": "1"},
    ]
