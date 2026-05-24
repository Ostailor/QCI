"""Public-benchmark adapters for CMPO Phase 2 evidence.

The adapter in this module intentionally keeps public benchmark provenance at
the boundary. It maps a small PGLib-OPF transmission benchmark into the CMPO
microgrid data contract for stress testing the workflow; it is not an AC OPF
solver and does not claim to reproduce PGLib reference objective values.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from cmpo.data import Battery, Generator, GridCase, LoadProfile, Microgrid, PCC, TieLine, UpgradeOptions
from cmpo.scenarios import build_default_scenarios


PGLIB_CASE5_PJM_PROVENANCE: dict[str, Any] = {
    "name": "pglib-opf-case5-pjm",
    "kind": "dataset",
    "upstream": {
        "url": "https://github.com/power-grid-lib/pglib-opf",
        "case_file_url": "https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case5_pjm.m",
        "version": "v23.07",
        "commit": "dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3",
        "license": "Creative Commons Attribution 4.0 International",
        "checksum": "sha256:cadf7501a15c2d508820493cef6acc85757274197e74c40bcec4fc4ecf619e6f",
    },
    "local_adapter": {
        "adapter_module": "src/cmpo/benchmarks.py",
        "download_hook": "manual optional: fetch the case_file_url if exact upstream inspection is needed",
        "local_path": "data/benchmarks/pglib_case5_pjm_adapted.yaml",
    },
    "adaptation": {
        "purpose": "CMPO microgrid stress benchmark derived from a public OPF case.",
        "not_claimed": "Not an AC OPF reproduction and not a live QCi hardware run.",
        "changes": [
            "Uses PGLib bus active loads as normalized microgrid load anchors.",
            "Uses PGLib generator capacities and linear cost slopes as thermal generator anchors.",
            "Adds PV, BESS, PCC, critical-load, and upgrade fields required by the CMPO workflow.",
            "Uses PGLib branch endpoints and ratings as microgrid tie-line topology anchors.",
        ],
    },
}


_BUS_LOAD_MW = {
    1: 0.0,
    2: 300.0,
    3: 300.0,
    4: 400.0,
    5: 0.0,
}

_GENERATOR_ROWS = [
    {"bus": 1, "pmax": 40.0, "pmin": 0.0, "linear_cost": 14.0},
    {"bus": 1, "pmax": 170.0, "pmin": 0.0, "linear_cost": 15.0},
    {"bus": 3, "pmax": 520.0, "pmin": 0.0, "linear_cost": 30.0},
    {"bus": 4, "pmax": 200.0, "pmin": 0.0, "linear_cost": 40.0},
    {"bus": 5, "pmax": 600.0, "pmin": 0.0, "linear_cost": 10.0},
]

_BRANCH_ROWS = [
    {"source": 1, "target": 2, "rate": 400.0},
    {"source": 1, "target": 4, "rate": 426.0},
    {"source": 1, "target": 5, "rate": 426.0},
    {"source": 2, "target": 3, "rate": 426.0},
    {"source": 3, "target": 4, "rate": 426.0},
    {"source": 4, "target": 5, "rate": 240.0},
]


def _hourly_shape(horizon_hours: int, base: list[float]) -> list[float]:
    return [base[index % len(base)] for index in range(horizon_hours)]


def _generator_anchor(bus_id: int, load_anchor_kw: float) -> tuple[float, float, float]:
    rows = [row for row in _GENERATOR_ROWS if row["bus"] == bus_id]
    if not rows:
        return max(25.0, 0.08 * load_anchor_kw), 0.0, 45.0
    pmax = sum(float(row["pmax"]) for row in rows)
    pmin = sum(float(row["pmin"]) for row in rows)
    weighted_cost = sum(float(row["pmax"]) * float(row["linear_cost"]) for row in rows) / max(pmax, 1e-9)
    return pmax, pmin, weighted_cost


def _build_microgrid(bus_id: int, horizon_hours: int) -> Microgrid:
    nonzero_loads = [value for value in _BUS_LOAD_MW.values() if value > 0.0]
    load_anchor = _BUS_LOAD_MW[bus_id] if _BUS_LOAD_MW[bus_id] > 0.0 else 0.35 * sum(nonzero_loads) / len(nonzero_loads)
    load_shape = _hourly_shape(horizon_hours, [0.88, 0.96, 1.04, 1.08, 1.0, 0.92])
    solar_shape = _hourly_shape(horizon_hours, [0.0, 0.25, 0.72, 0.95, 0.55, 0.10])
    base_load = [round(load_anchor * factor, 3) for factor in load_shape]
    pv_peak = load_anchor * (0.18 + 0.025 * bus_id)
    pv_profile = [round(pv_peak * factor, 3) for factor in solar_shape]
    pmax, pmin, linear_cost = _generator_anchor(bus_id, load_anchor)
    battery_capacity = max(60.0, 0.55 * load_anchor)
    battery_power = max(25.0, 0.18 * load_anchor)
    connected_rates = [
        row["rate"]
        for row in _BRANCH_ROWS
        if int(row["source"]) == bus_id or int(row["target"]) == bus_id
    ]
    pcc_import = max(80.0, min(sum(connected_rates) * 0.35, 420.0))

    return Microgrid(
        name=f"PGLIB5_MG{bus_id}",
        load_profile=LoadProfile(
            base_kw=base_load,
            critical_fraction=round(0.38 + 0.045 * ((bus_id - 1) % 5), 4),
            flexible_fraction=round(0.12 + 0.015 * (bus_id % 4), 4),
        ),
        pv_availability_kw=pv_profile,
        generator=Generator(
            name=f"PGLIB5_MG{bus_id}_thermal",
            p_min_kw=round(pmin, 3),
            p_max_kw=round(pmax, 3),
            cost_a=round(0.0000015 + 0.00000018 * bus_id, 8),
            cost_b=round(0.001 + linear_cost / 20000.0, 6),
            cost_c=round(linear_cost / 100.0, 5),
        ),
        battery=Battery(
            name=f"PGLIB5_MG{bus_id}_bess",
            capacity_kwh=round(battery_capacity, 3),
            max_charge_kw=round(battery_power, 3),
            max_discharge_kw=round(battery_power, 3),
            initial_soc_kwh=round(0.55 * battery_capacity, 3),
            round_trip_efficiency=0.91,
        ),
        pcc=PCC(
            name=f"PGLIB5_MG{bus_id}_pcc",
            import_limit_kw=round(pcc_import, 3),
            export_limit_kw=round(0.45 * pcc_import, 3),
        ),
        upgrade_options=UpgradeOptions(
            added_pv_kw=round(0.22 * load_anchor, 3),
            added_pv_cost=round(0.22 * load_anchor * 980.0, 2),
            added_bess_kwh=round(0.32 * load_anchor, 3),
            added_bess_cost=round(0.32 * load_anchor * 430.0, 2),
            added_generator_kw=round(0.16 * load_anchor, 3),
            added_generator_cost=round(0.16 * load_anchor * 720.0, 2),
        ),
    )


def build_pglib_case5_pjm_microgrid_case(
    horizon_hours: int = 6,
    seed: int = 42,
    scenario_count: int = 8,
    output_dir: Path | str | None = None,
) -> GridCase:
    """Build a deterministic PGLib case5-PJM-derived CMPO benchmark case.

    The case adapts public PGLib topology, load, generator, and cost anchors
    into the microgrid fields required by CMPO. Added DER/storage fields are
    deterministic synthetic extensions documented in the provenance manifest.
    """

    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    if scenario_count <= 0:
        raise ValueError("scenario_count must be positive")

    microgrids = [_build_microgrid(bus_id, horizon_hours) for bus_id in sorted(_BUS_LOAD_MW)]
    tie_lines = [
        TieLine(
            name=f"PGLIB5_TIE_{row['source']}_{row['target']}",
            source_microgrid=f"PGLIB5_MG{row['source']}",
            target_microgrid=f"PGLIB5_MG{row['target']}",
            capacity_kw=round(float(row["rate"]), 3),
        )
        for row in _BRANCH_ROWS
    ]
    scenarios = build_default_scenarios(len(microgrids), horizon_hours)[:scenario_count]
    case = GridCase(
        seed=seed,
        horizon_hours=horizon_hours,
        microgrids=microgrids,
        tie_lines=tie_lines,
        scenarios=scenarios,
        documentation=(
            "PGLib-OPF case5-PJM adapted CMPO benchmark. Public PGLib load, "
            "generator, cost, and branch anchors are normalized into microgrid "
            "research units; PV/BESS/PCC/critical-load fields are deterministic "
            "synthetic additions for resilient microgrid dispatch experiments."
        ),
    )
    if output_dir is not None:
        write_benchmark_case_files(case, Path(output_dir))
    return case


def write_benchmark_case_files(case: GridCase, output_dir: Path) -> dict[str, Path]:
    """Persist benchmark case files and provenance manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "pglib_case5_pjm_manifest.json"
    case_path = output_dir / "pglib_case5_pjm_adapted.yaml"
    microgrid_path = output_dir / "pglib_case5_pjm_microgrids.csv"
    tie_path = output_dir / "pglib_case5_pjm_ties.csv"

    manifest_path.write_text(json.dumps(PGLIB_CASE5_PJM_PROVENANCE, indent=2), encoding="utf-8")
    case_path.write_text(yaml.safe_dump(asdict(case), sort_keys=False), encoding="utf-8")

    with microgrid_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "avg_base_load_kw",
                "critical_fraction",
                "pv_peak_kw",
                "generator_p_max_kw",
                "generator_cost_c",
                "battery_capacity_kwh",
                "pcc_import_limit_kw",
            ],
        )
        writer.writeheader()
        for microgrid in case.microgrids:
            writer.writerow(
                {
                    "name": microgrid.name,
                    "avg_base_load_kw": round(sum(microgrid.load_profile.base_kw) / len(microgrid.load_profile.base_kw), 3),
                    "critical_fraction": microgrid.load_profile.critical_fraction,
                    "pv_peak_kw": max(microgrid.pv_availability_kw),
                    "generator_p_max_kw": microgrid.generator.p_max_kw,
                    "generator_cost_c": microgrid.generator.cost_c,
                    "battery_capacity_kwh": microgrid.battery.capacity_kwh,
                    "pcc_import_limit_kw": microgrid.pcc.import_limit_kw,
                }
            )

    with tie_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "source_microgrid", "target_microgrid", "capacity_kw"])
        writer.writeheader()
        for tie_line in case.tie_lines:
            writer.writerow(asdict(tie_line))

    return {
        "manifest": manifest_path,
        "case_yaml": case_path,
        "microgrids_csv": microgrid_path,
        "ties_csv": tie_path,
    }
