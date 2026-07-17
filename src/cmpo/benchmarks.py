"""Public-benchmark adapters for CMPO Phase 2 evidence.

The adapter in this module intentionally keeps public benchmark provenance at
the boundary. It maps a small PGLib-OPF transmission benchmark into the CMPO
microgrid data contract for stress testing the workflow; it is not an AC OPF
solver and does not claim to reproduce PGLib reference objective values.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from cmpo.data import Battery, Generator, GridCase, LoadProfile, Microgrid, PCC, TieLine, UpgradeOptions
from cmpo.scenarios import build_default_scenarios


PGLIB_VERSION = "v23.07"
PGLIB_COMMIT = "dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3"
PGLIB_LICENSE = "Creative Commons Attribution 4.0 International"
PGLIB_RAW_DIR = Path("data") / "upstream" / "pglib-opf" / PGLIB_VERSION

PGLIB_CASES: dict[str, dict[str, Any]] = {
    "pglib_case5": {
        "label": "PGLib case5-PJM",
        "manifest_name": "pglib-opf-case5-pjm",
        "case_file": "pglib_opf_case5_pjm.m",
        "default_microgrids": 5,
        "output_prefix": "pglib_case5",
    },
    "pglib_case14": {
        "label": "PGLib case14 IEEE",
        "manifest_name": "pglib-opf-case14-ieee",
        "case_file": "pglib_opf_case14_ieee.m",
        "default_microgrids": 6,
        "output_prefix": "pglib_case14",
    },
    "pglib_case30": {
        "label": "PGLib case30 IEEE",
        "manifest_name": "pglib-opf-case30-ieee",
        "case_file": "pglib_opf_case30_ieee.m",
        "default_microgrids": 8,
        "output_prefix": "pglib_case30",
    },
    "pglib_case57": {
        "label": "PGLib case57 IEEE",
        "manifest_name": "pglib-opf-case57-ieee",
        "case_file": "pglib_opf_case57_ieee.m",
        "default_microgrids": 10,
        "output_prefix": "pglib_case57",
    },
}


def _case_file_url(case_file: str) -> str:
    return f"https://raw.githubusercontent.com/power-grid-lib/pglib-opf/{PGLIB_VERSION}/{case_file}"


def _case_provenance(case_name: str) -> dict[str, Any]:
    case = PGLIB_CASES[case_name]
    manifest_path = Path("manifests") / "upstream" / f"{case['manifest_name']}.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_path = PGLIB_RAW_DIR / case["case_file"]
    checksum = "sha256:unfetched"
    if raw_path.exists():
        import hashlib

        checksum = f"sha256:{hashlib.sha256(raw_path.read_bytes()).hexdigest()}"
    return {
        "name": case["manifest_name"],
        "kind": "dataset",
        "upstream": {
            "url": "https://github.com/power-grid-lib/pglib-opf",
            "case_file_url": _case_file_url(case["case_file"]),
            "version": PGLIB_VERSION,
            "commit": PGLIB_COMMIT,
            "license": PGLIB_LICENSE,
            "checksum": checksum,
        },
        "local_adapter": {
            "adapter_module": "src/cmpo/benchmarks.py",
            "download_hook": "python scripts/fetch_pglib_benchmarks.py",
            "local_path": f"data/benchmarks/{case['output_prefix']}_adapted.yaml",
            "exact_source_path": str(raw_path),
        },
        "adaptation": {
            "purpose": "PGLib-derived microgrid stress adapter for CMPO Phase 3.",
            "not_claimed": "Not an AC OPF reproduction and not a live QCi hardware run.",
            "changes": [
                "Parses PGLib buses, branches, active loads, generators, and generator cost rows.",
                "Selects representative buses as candidate microgrids using generator presence and load ranking.",
                "Adds deterministic PV, BESS, PCC, critical-load, and upgrade fields required by CMPO.",
                "Creates CMPO contingencies from the same scenario generator used for QCi payloads and baselines.",
            ],
        },
    }


PGLIB_CASE5_PJM_PROVENANCE: dict[str, Any] = _case_provenance("pglib_case5")


def _hourly_shape(horizon_hours: int, base: list[float]) -> list[float]:
    return [base[index % len(base)] for index in range(horizon_hours)]


def _parse_matrix(text: str, section: str) -> list[list[float]]:
    match = re.search(rf"mpc\.{section}\s*=\s*\[(.*?)\];", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"PGLib MATPOWER section not found: {section}")
    rows: list[list[float]] = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.split("%", 1)[0].strip().rstrip(";")
        if not line:
            continue
        rows.append([float(value) for value in line.split()])
    return rows


def parse_pglib_matpower_case(path: Path | str) -> dict[str, list[dict[str, Any]]]:
    """Parse the MATPOWER fields needed by CMPO from a local PGLib `.m` file."""

    text = Path(path).read_text(encoding="utf-8")
    bus_rows = _parse_matrix(text, "bus")
    gen_rows = _parse_matrix(text, "gen")
    branch_rows = _parse_matrix(text, "branch")
    gencost_rows = _parse_matrix(text, "gencost")
    buses = [
        {
            "bus": int(row[0]),
            "type": int(row[1]),
            "pd": float(row[2]),
            "qd": float(row[3]),
            "base_kv": float(row[9]) if len(row) > 9 else 0.0,
        }
        for row in bus_rows
    ]
    generators = []
    for index, row in enumerate(gen_rows):
        cost_row = gencost_rows[index] if index < len(gencost_rows) else []
        n_cost = int(cost_row[3]) if len(cost_row) > 3 else 0
        coefficients = [float(value) for value in cost_row[4 : 4 + n_cost]] if n_cost else []
        generators.append(
            {
                "bus": int(row[0]),
                "pg": float(row[1]),
                "pmax": float(row[8]),
                "pmin": float(row[9]),
                "status": int(row[7]) if len(row) > 7 else 1,
                "cost_model": int(cost_row[0]) if cost_row else 0,
                "cost_coefficients": coefficients,
            }
        )
    branches = [
        {
            "source": int(row[0]),
            "target": int(row[1]),
            "rate": float(row[5]) if len(row) > 5 and float(row[5]) > 0.0 else 0.0,
            "x": float(row[3]) if len(row) > 3 else 0.0,
            "status": int(row[10]) if len(row) > 10 else 1,
        }
        for row in branch_rows
    ]
    return {"buses": buses, "generators": generators, "branches": branches, "gencosts": [{"row": row} for row in gencost_rows]}


def _select_microgrid_buses(parsed: dict[str, list[dict[str, Any]]], count: int) -> list[int]:
    generator_buses = [int(row["bus"]) for row in parsed["generators"] if row.get("status", 1) != 0 and row.get("pmax", 0.0) > 0.0]
    load_rank = sorted(parsed["buses"], key=lambda row: (float(row["pd"]), -int(row["bus"])), reverse=True)
    selected: list[int] = []
    for bus_id in generator_buses + [int(row["bus"]) for row in load_rank]:
        if bus_id not in selected:
            selected.append(bus_id)
        if len(selected) >= count:
            break
    return sorted(selected)


def _generator_anchor(bus_id: int, load_anchor_kw: float, generators: list[dict[str, Any]]) -> tuple[float, float, float, float, float]:
    rows = [row for row in generators if int(row["bus"]) == bus_id and int(row.get("status", 1)) != 0]
    if not rows:
        return max(25.0, 0.08 * load_anchor_kw), 0.0, 0.0000015, 0.001, 0.45
    pmax = sum(float(row["pmax"]) for row in rows)
    pmin = sum(float(row["pmin"]) for row in rows)
    cost_a = 0.0
    cost_b = 0.0
    cost_c = 0.0
    for row in rows:
        weight = float(row["pmax"]) / max(pmax, 1e-9)
        coeffs = list(row.get("cost_coefficients", []))
        if len(coeffs) >= 3:
            cost_b += weight * abs(float(coeffs[-3])) / 1000.0
            cost_c += weight * abs(float(coeffs[-2])) / 100.0
        elif len(coeffs) >= 2:
            cost_c += weight * abs(float(coeffs[-2])) / 100.0
        if len(coeffs) >= 4:
            cost_a += weight * abs(float(coeffs[-4])) / 10000.0
    if cost_c <= 0.0:
        cost_c = 0.45
    if cost_b <= 0.0:
        cost_b = 0.001
    if cost_a <= 0.0:
        cost_a = 0.0000015 + 0.00000008 * (bus_id % 7)
    return pmax, pmin, cost_a, cost_b, cost_c


def _incident_branch_capacity(bus_id: int, branches: list[dict[str, Any]]) -> float:
    incident = [float(row["rate"]) for row in branches if int(row["source"]) == bus_id or int(row["target"]) == bus_id]
    positive = [value for value in incident if value > 0.0]
    if positive:
        return sum(positive)
    return max(100.0, 100.0 * max(len(incident), 1))


def _build_microgrid(
    bus_id: int,
    horizon_hours: int,
    parsed: dict[str, list[dict[str, Any]]],
    selected_index: int,
) -> Microgrid:
    bus_loads = {int(row["bus"]): float(row["pd"]) for row in parsed["buses"]}
    nonzero_loads = [value for value in bus_loads.values() if value > 0.0]
    avg_nonzero = sum(nonzero_loads) / max(len(nonzero_loads), 1)
    load_anchor = bus_loads.get(bus_id, 0.0) if bus_loads.get(bus_id, 0.0) > 0.0 else 0.35 * avg_nonzero
    load_shape = _hourly_shape(horizon_hours, [0.88, 0.96, 1.04, 1.08, 1.0, 0.92])
    solar_shape = _hourly_shape(horizon_hours, [0.0, 0.25, 0.72, 0.95, 0.55, 0.10])
    base_load = [round(load_anchor * factor, 3) for factor in load_shape]
    pv_peak = load_anchor * (0.16 + 0.015 * ((selected_index + bus_id) % 6))
    pv_profile = [round(pv_peak * factor, 3) for factor in solar_shape]
    pmax, pmin, cost_a, cost_b, cost_c = _generator_anchor(bus_id, load_anchor, parsed["generators"])
    battery_capacity = max(60.0, 0.55 * load_anchor)
    battery_power = max(25.0, 0.18 * load_anchor)
    pcc_import = max(80.0, min(_incident_branch_capacity(bus_id, parsed["branches"]) * 0.35, 420.0))

    return Microgrid(
        name=f"BUS{bus_id}_MG",
        load_profile=LoadProfile(
            base_kw=base_load,
            critical_fraction=round(0.38 + 0.035 * (selected_index % 6), 4),
            flexible_fraction=round(0.12 + 0.015 * (bus_id % 4), 4),
        ),
        pv_availability_kw=pv_profile,
        generator=Generator(
            name=f"BUS{bus_id}_thermal",
            p_min_kw=round(pmin, 3),
            p_max_kw=round(pmax, 3),
            cost_a=round(cost_a, 8),
            cost_b=round(cost_b, 6),
            cost_c=round(cost_c, 5),
        ),
        battery=Battery(
            name=f"BUS{bus_id}_bess",
            capacity_kwh=round(battery_capacity, 3),
            max_charge_kw=round(battery_power, 3),
            max_discharge_kw=round(battery_power, 3),
            initial_soc_kwh=round(0.55 * battery_capacity, 3),
            round_trip_efficiency=0.91,
        ),
        pcc=PCC(
            name=f"BUS{bus_id}_pcc",
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


def _raw_case_path(case_name: str, raw_dir: Path | str | None = None) -> Path:
    case = PGLIB_CASES[case_name]
    path = (Path(raw_dir) if raw_dir is not None else PGLIB_RAW_DIR) / str(case["case_file"])
    if not path.exists():
        raise FileNotFoundError(
            f"Missing exact PGLib file for {case_name}: {path}. "
            "Run `python scripts/fetch_pglib_benchmarks.py` to fetch pinned upstream cases."
        )
    return path


def _tie_lines_for_selected_buses(
    case_name: str,
    selected_buses: list[int],
    parsed: dict[str, list[dict[str, Any]]],
) -> list[TieLine]:
    selected = set(selected_buses)
    tie_lines: list[TieLine] = []
    for row in parsed["branches"]:
        source = int(row["source"])
        target = int(row["target"])
        if source not in selected or target not in selected:
            continue
        rate = float(row["rate"]) if float(row["rate"]) > 0.0 else 100.0
        tie_lines.append(
            TieLine(
                name=f"{case_name.upper()}_TIE_{source}_{target}",
                source_microgrid=f"BUS{source}_MG",
                target_microgrid=f"BUS{target}_MG",
                capacity_kw=round(rate, 3),
            )
        )
    if tie_lines:
        return tie_lines
    for source, target in zip(selected_buses, selected_buses[1:]):
        tie_lines.append(
            TieLine(
                name=f"{case_name.upper()}_TIE_{source}_{target}",
                source_microgrid=f"BUS{source}_MG",
                target_microgrid=f"BUS{target}_MG",
                capacity_kw=100.0,
            )
        )
    return tie_lines


def build_pglib_microgrid_case(
    case_name: str,
    horizon_hours: int = 6,
    seed: int = 42,
    scenario_count: int = 8,
    output_dir: Path | str | None = None,
    raw_dir: Path | str | None = None,
    max_microgrids: int | None = None,
) -> GridCase:
    """Build a deterministic PGLib-derived CMPO microgrid stress adapter.

    The adapter parses public PGLib topology, load, generator, and cost anchors
    into CMPO microgrid fields. Added DER/storage fields are deterministic
    synthetic extensions documented in the provenance manifest.
    """

    if case_name not in PGLIB_CASES:
        raise ValueError(f"unsupported PGLib benchmark: {case_name}")
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    if scenario_count <= 0:
        raise ValueError("scenario_count must be positive")

    raw_path = _raw_case_path(case_name, raw_dir)
    parsed = parse_pglib_matpower_case(raw_path)
    selected_buses = _select_microgrid_buses(parsed, int(max_microgrids or PGLIB_CASES[case_name]["default_microgrids"]))
    microgrids = [_build_microgrid(bus_id, horizon_hours, parsed, index) for index, bus_id in enumerate(selected_buses)]
    tie_lines = _tie_lines_for_selected_buses(case_name, selected_buses, parsed)
    scenarios = build_default_scenarios(len(microgrids), horizon_hours)[:scenario_count]
    label = PGLIB_CASES[case_name]["label"]
    case = GridCase(
        seed=seed,
        horizon_hours=horizon_hours,
        microgrids=microgrids,
        tie_lines=tie_lines,
        scenarios=scenarios,
        documentation=(
            f"{label} PGLib-derived microgrid stress adapter. Public PGLib bus, load, "
            "generator, gencost, and branch anchors are normalized into CMPO research units; "
            "PV/BESS/PCC/critical-load fields are deterministic synthetic additions. "
            "This is not an AC OPF reproduction."
        ),
    )
    if output_dir is not None:
        write_benchmark_case_files(case, Path(output_dir), case_name=case_name, parsed=parsed, selected_buses=selected_buses)
    return case


def build_pglib_case5_pjm_microgrid_case(
    horizon_hours: int = 6,
    seed: int = 42,
    scenario_count: int = 8,
    output_dir: Path | str | None = None,
) -> GridCase:
    """Compatibility wrapper for the PGLib case5-PJM-derived adapter."""

    return build_pglib_microgrid_case(
        "pglib_case5",
        horizon_hours=horizon_hours,
        seed=seed,
        scenario_count=scenario_count,
        output_dir=output_dir,
    )


def write_benchmark_case_files(
    case: GridCase,
    output_dir: Path,
    *,
    case_name: str = "pglib_case5",
    parsed: dict[str, list[dict[str, Any]]] | None = None,
    selected_buses: list[int] | None = None,
) -> dict[str, Path]:
    """Persist benchmark case files and provenance manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = str(PGLIB_CASES[case_name]["output_prefix"])
    manifest_path = output_dir / f"{prefix}_manifest.json"
    case_path = output_dir / f"{prefix}_adapted.yaml"
    microgrid_path = output_dir / f"{prefix}_microgrids.csv"
    tie_path = output_dir / f"{prefix}_ties.csv"
    parsed_path = output_dir / f"{prefix}_parsed_summary.json"

    manifest_path.write_text(json.dumps(_case_provenance(case_name), indent=2), encoding="utf-8")
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
            lineterminator="\n",
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
        writer = csv.DictWriter(
            handle,
            fieldnames=["name", "source_microgrid", "target_microgrid", "capacity_kw"],
            lineterminator="\n",
        )
        writer.writeheader()
        for tie_line in case.tie_lines:
            writer.writerow(asdict(tie_line))

    if parsed is not None:
        parsed_summary = {
            "case_name": case_name,
            "selected_buses": selected_buses or [],
            "bus_count": len(parsed["buses"]),
            "branch_count": len(parsed["branches"]),
            "generator_count": len(parsed["generators"]),
            "gencost_count": len(parsed["gencosts"]),
            "transformation_notes": "PGLib-derived microgrid stress adapter; not an AC OPF reproduction.",
        }
        parsed_path.write_text(json.dumps(parsed_summary, indent=2), encoding="utf-8")

    if case_name == "pglib_case5":
        legacy_paths = {
            output_dir / "pglib_case5_pjm_manifest.json": manifest_path,
            output_dir / "pglib_case5_pjm_adapted.yaml": case_path,
            output_dir / "pglib_case5_pjm_microgrids.csv": microgrid_path,
            output_dir / "pglib_case5_pjm_ties.csv": tie_path,
        }
        for legacy_path, source_path in legacy_paths.items():
            shutil.copyfile(source_path, legacy_path)

    return {
        "manifest": manifest_path,
        "case_yaml": case_path,
        "microgrids_csv": microgrid_path,
        "ties_csv": tie_path,
        "parsed_summary_json": parsed_path,
    }
