"""Typed ARPA-E GO Challenge 1 public adapter for SC-CMPO tests and tooling."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cmpo.upgrade_planning import (
    PublicContingency,
    PublicEdge,
    PublicGridData,
    PublicNode,
    UpgradePatch,
    select_upgrade_patches,
    sha256_file,
)


@dataclass(frozen=True)
class ArpaeSCBus:
    bus_id: str
    base_kv: float
    bus_type: int
    area: int
    zone: int
    owner: int
    voltage_magnitude_pu: float
    voltage_angle_degrees: float
    normal_voltage_high_pu: float
    normal_voltage_low_pu: float
    emergency_voltage_high_pu: float
    emergency_voltage_low_pu: float
    source_record: str


@dataclass(frozen=True)
class ArpaeSCLoad:
    bus_id: str
    load_id: str
    in_service: bool
    area: int
    zone: int
    active_power_kw: float
    reactive_power_kvar: float
    source_record: str


@dataclass(frozen=True)
class ArpaeSCGenerator:
    bus_id: str
    generator_id: str
    in_service: bool
    active_power_kw: float
    reactive_power_kvar: float
    maximum_active_power_kw: float
    minimum_active_power_kw: float
    maximum_reactive_power_kvar: float
    minimum_reactive_power_kvar: float
    regulated_voltage_pu: float
    source_record: str


@dataclass(frozen=True)
class ArpaeSCBranch:
    from_bus_id: str
    to_bus_id: str
    circuit_id: str
    resistance_pu: float
    reactance_pu: float
    charging_b_pu: float
    rating_a_mva: float
    rating_b_mva: float
    rating_c_mva: float
    in_service: bool
    source_record: str


@dataclass(frozen=True)
class ArpaeSCTransformer:
    from_bus_id: str
    to_bus_id: str
    circuit_id: str
    in_service: bool
    third_winding_bus_id: str | None
    resistance_pu: float
    reactance_pu: float
    rating_a_mva: float
    rating_b_mva: float
    rating_c_mva: float
    winding1_nominal_kv: float
    winding2_nominal_kv: float
    source_records: tuple[str, ...]


@dataclass(frozen=True)
class ArpaeSCGeneratorCost:
    bus_id: str
    generator_id: str
    active_dispatch_table_id: int
    piecewise_cost_table_id: int
    points_mw_cost: tuple[tuple[float, float], ...]
    source_records: tuple[str, ...]


@dataclass(frozen=True)
class ArpaeSCTimePeriod:
    period_id: str
    duration_hours: float | None
    temporal_profile_available: bool
    source_record: str


@dataclass(frozen=True)
class SourceAwarePublicGridData(PublicGridData):
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class ArpaeSCCMPOCase:
    buses: tuple[ArpaeSCBus, ...]
    loads: tuple[ArpaeSCLoad, ...]
    generators: tuple[ArpaeSCGenerator, ...]
    branches: tuple[ArpaeSCBranch, ...]
    transformers: tuple[ArpaeSCTransformer, ...]
    generator_costs: tuple[ArpaeSCGeneratorCost, ...]
    time_periods: tuple[ArpaeSCTimePeriod, ...]
    grid: SourceAwarePublicGridData
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class _PiecewiseCostTable:
    table_id: int
    name: str
    points_mw_cost: tuple[tuple[float, float], ...]
    source_records: tuple[str, ...]


def _csv_row(line: str) -> list[str]:
    return [item.strip().strip("'") for item in next(csv.reader([line], skipinitialspace=True))]


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def _require_sha(path: Path, expected: str | None) -> str:
    digest = sha256_file(path)
    if expected:
        normalized = expected.removeprefix("sha256:")
        if digest != normalized:
            raise ValueError(f"checksum mismatch for {path}: expected {normalized}, got {digest}")
    return digest


def _split_raw_sections(path: Path) -> dict[str, list[str]]:
    section_names = ("bus", "load", "fixed_shunt", "generator", "branch", "transformer")
    sections = {name: [] for name in section_names}
    current = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[3:]:
        if re.match(r"^\s*0\s*/", line):
            current += 1
            if current >= len(section_names):
                break
            continue
        sections[section_names[current]].append(line)
    return sections


def _parse_buses(lines: list[str]) -> tuple[ArpaeSCBus, ...]:
    records: list[ArpaeSCBus] = []
    for line in lines:
        row = _csv_row(line)
        if len(row) < 13:
            continue
        records.append(
            ArpaeSCBus(
                bus_id=str(int(float(row[0]))),
                base_kv=float(row[2]),
                bus_type=int(float(row[3])),
                area=int(float(row[4])),
                zone=int(float(row[5])),
                owner=int(float(row[6])),
                voltage_magnitude_pu=float(row[7]),
                voltage_angle_degrees=float(row[8]),
                normal_voltage_high_pu=float(row[9]),
                normal_voltage_low_pu=float(row[10]),
                emergency_voltage_high_pu=float(row[11]),
                emergency_voltage_low_pu=float(row[12]),
                source_record=line.strip(),
            )
        )
    return tuple(records)


def _parse_loads(lines: list[str]) -> tuple[ArpaeSCLoad, ...]:
    records: list[ArpaeSCLoad] = []
    for line in lines:
        row = _csv_row(line)
        if len(row) < 7:
            continue
        records.append(
            ArpaeSCLoad(
                bus_id=str(int(float(row[0]))),
                load_id=row[1],
                in_service=int(float(row[2])) != 0,
                area=int(float(row[3])),
                zone=int(float(row[4])),
                active_power_kw=float(row[5]) * 1000.0,
                reactive_power_kvar=float(row[6]) * 1000.0,
                source_record=line.strip(),
            )
        )
    return tuple(records)


def _parse_generators(lines: list[str]) -> tuple[ArpaeSCGenerator, ...]:
    records: list[ArpaeSCGenerator] = []
    for line in lines:
        row = _csv_row(line)
        if len(row) < 18:
            continue
        records.append(
            ArpaeSCGenerator(
                bus_id=str(int(float(row[0]))),
                generator_id=row[1],
                active_power_kw=float(row[2]) * 1000.0,
                reactive_power_kvar=float(row[3]) * 1000.0,
                maximum_reactive_power_kvar=float(row[4]) * 1000.0,
                minimum_reactive_power_kvar=float(row[5]) * 1000.0,
                regulated_voltage_pu=float(row[6]),
                in_service=int(float(row[14])) != 0,
                maximum_active_power_kw=float(row[16]) * 1000.0,
                minimum_active_power_kw=float(row[17]) * 1000.0,
                source_record=line.strip(),
            )
        )
    return tuple(records)


def _parse_branches(lines: list[str]) -> tuple[ArpaeSCBranch, ...]:
    records: list[ArpaeSCBranch] = []
    for line in lines:
        row = _csv_row(line)
        if len(row) < 14:
            continue
        records.append(
            ArpaeSCBranch(
                from_bus_id=str(int(float(row[0]))),
                to_bus_id=str(int(float(row[1]))),
                circuit_id=row[2],
                resistance_pu=float(row[3]),
                reactance_pu=float(row[4]),
                charging_b_pu=float(row[5]),
                rating_a_mva=float(row[6]),
                rating_b_mva=float(row[7]),
                rating_c_mva=float(row[8]),
                in_service=int(float(row[13])) != 0,
                source_record=line.strip(),
            )
        )
    return tuple(records)


def _parse_transformers(lines: list[str]) -> tuple[ArpaeSCTransformer, ...]:
    records: list[ArpaeSCTransformer] = []
    index = 0
    while index < len(lines):
        block = tuple(lines[index : index + 4])
        if len(block) < 4:
            raise ValueError(f"incomplete transformer record near line offset {index}")
        row1 = _csv_row(block[0])
        row2 = _csv_row(block[1])
        row3 = _csv_row(block[2])
        row4 = _csv_row(block[3])
        if len(row1) < 12 or len(row2) < 3 or len(row3) < 6 or len(row4) < 2:
            raise ValueError(f"invalid transformer record near line offset {index}")
        third_winding = int(float(row1[2]))
        records.append(
            ArpaeSCTransformer(
                from_bus_id=str(int(float(row1[0]))),
                to_bus_id=str(int(float(row1[1]))),
                third_winding_bus_id=None if third_winding == 0 else str(third_winding),
                circuit_id=row1[3],
                in_service=int(float(row1[11])) != 0,
                resistance_pu=float(row2[0]),
                reactance_pu=float(row2[1]),
                rating_a_mva=float(row3[3]),
                rating_b_mva=float(row3[4]),
                rating_c_mva=float(row3[5]),
                winding1_nominal_kv=float(row3[1]),
                winding2_nominal_kv=float(row4[1]),
                source_records=tuple(item.strip() for item in block),
            )
        )
        index += 4
    return tuple(records)


def _parse_rop_sections(path: Path) -> dict[str, list[str]]:
    sections = {
        "generator_dispatch": [],
        "active_dispatch": [],
        "piecewise_linear_costs": [],
    }
    current: str | None = None
    markers = {
        "BEGIN Generator Dispatch Data": "generator_dispatch",
        "BEGIN Active Power Dispatch Table Data": "active_dispatch",
        "BEGIN Piece-wise Linear Cost Tables": "piecewise_linear_costs",
    }
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.strip()
        if "BEGIN " in stripped:
            current = None
            for marker, name in markers.items():
                if marker in stripped:
                    current = name
                    break
            continue
        if current is not None and stripped:
            sections[current].append(raw_line)
    return sections


def _parse_generator_dispatch(lines: list[str]) -> dict[tuple[str, str], tuple[int, str]]:
    mapping: dict[tuple[str, str], tuple[int, str]] = {}
    for line in lines:
        row = _csv_row(line)
        if len(row) < 4:
            continue
        key = (str(int(float(row[0]))), row[1])
        mapping[key] = (int(float(row[3])), line.strip())
    return mapping


def _parse_active_dispatch(lines: list[str]) -> dict[int, tuple[int, str]]:
    mapping: dict[int, tuple[int, str]] = {}
    for line in lines:
        row = _csv_row(line)
        if len(row) < 2:
            continue
        mapping[int(float(row[0]))] = (int(float(row[-1])), line.strip())
    return mapping


def _parse_piecewise_cost_tables(lines: list[str]) -> dict[int, _PiecewiseCostTable]:
    tables: dict[int, _PiecewiseCostTable] = {}
    index = 0
    while index < len(lines):
        header = _csv_row(lines[index])
        if len(header) < 3:
            raise ValueError(f"invalid piecewise cost header at ROP section offset {index}")
        table_id = int(float(header[0]))
        name = header[1]
        point_count = int(float(header[2]))
        if point_count <= 0:
            raise ValueError(f"piecewise cost table {table_id} must have at least one point")
        raw_records = [lines[index].strip()]
        points: list[tuple[float, float]] = []
        for point_index in range(point_count):
            source_line = lines[index + 1 + point_index]
            raw_records.append(source_line.strip())
            row = _csv_row(source_line)
            if len(row) < 2:
                raise ValueError(f"invalid point row for piecewise cost table {table_id}")
            points.append((float(row[0]), float(row[1])))
        points.sort(key=lambda item: item[0])
        tables[table_id] = _PiecewiseCostTable(
            table_id=table_id,
            name=name,
            points_mw_cost=tuple(points),
            source_records=tuple(raw_records),
        )
        index += 1 + point_count
    return tables


def _parse_generator_costs(
    generators: tuple[ArpaeSCGenerator, ...],
    cost_path: Path,
) -> tuple[ArpaeSCGeneratorCost, ...]:
    sections = _parse_rop_sections(cost_path)
    generator_dispatch = _parse_generator_dispatch(sections["generator_dispatch"])
    active_dispatch = _parse_active_dispatch(sections["active_dispatch"])
    cost_tables = _parse_piecewise_cost_tables(sections["piecewise_linear_costs"])
    records: list[ArpaeSCGeneratorCost] = []
    for generator in generators:
        key = (generator.bus_id, generator.generator_id)
        active_dispatch_entry = generator_dispatch.get(key)
        if active_dispatch_entry is None:
            raise ValueError(f"missing ROP generator dispatch mapping for generator {key}")
        active_dispatch_table_id, generator_dispatch_record = active_dispatch_entry
        cost_mapping = active_dispatch.get(active_dispatch_table_id)
        if cost_mapping is None:
            raise ValueError(f"missing active dispatch table {active_dispatch_table_id} for generator {key}")
        piecewise_cost_table_id, active_dispatch_record = cost_mapping
        cost_table = cost_tables.get(piecewise_cost_table_id)
        if cost_table is None:
            raise ValueError(
                f"missing piecewise cost table {piecewise_cost_table_id} for generator {key}"
            )
        records.append(
            ArpaeSCGeneratorCost(
                bus_id=generator.bus_id,
                generator_id=generator.generator_id,
                active_dispatch_table_id=active_dispatch_table_id,
                piecewise_cost_table_id=piecewise_cost_table_id,
                points_mw_cost=cost_table.points_mw_cost,
                source_records=(
                    generator.source_record,
                    generator_dispatch_record,
                    active_dispatch_record,
                    *cost_table.source_records,
                ),
            )
        )
    return tuple(records)


def _parse_arpae_contingencies(path: Path) -> tuple[PublicContingency, ...]:
    contingencies: list[PublicContingency] = []
    current = ""
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("CONTINGENCY "):
            current = line.removeprefix("CONTINGENCY ").strip()
            continue
        generator_match = re.search(r"REMOVE\s+UNIT\s+(\S+)\s+FROM\s+BUS\s+(\d+)", line, flags=re.IGNORECASE)
        if generator_match:
            contingencies.append(
                PublicContingency(
                    contingency_id=current or f"generator_bus_{generator_match.group(2)}",
                    component_kind="generator",
                    component_id=f"bus_{generator_match.group(2)}_unit_{generator_match.group(1)}",
                    action=line,
                    source_record=f"{path}:{line}",
                )
            )
            continue
        branch_match = re.search(
            r"(?:OPEN|REMOVE)\s+(?:BRANCH|LINE).*?BUS\s+(\d+).*?BUS\s+(\d+)(?:.*?(?:CIRCUIT|CKT)\s+(\S+))?",
            line,
            flags=re.IGNORECASE,
        )
        if branch_match:
            contingencies.append(
                PublicContingency(
                    contingency_id=current or f"branch_{branch_match.group(1)}_{branch_match.group(2)}",
                    component_kind="branch",
                    component_id=(
                        f"branch_{branch_match.group(1)}_{branch_match.group(2)}_{branch_match.group(3) or '1'}"
                    ),
                    action=line,
                    source_record=f"{path}:{line}",
                )
            )
    return tuple(contingencies)


def _build_grid(
    config: Mapping[str, Any],
    source_path: Path,
    contingency_path: Path,
    cost_path: Path,
    inl_path: Path,
    buses: tuple[ArpaeSCBus, ...],
    loads: tuple[ArpaeSCLoad, ...],
    generators: tuple[ArpaeSCGenerator, ...],
    branches: tuple[ArpaeSCBranch, ...],
    transformers: tuple[ArpaeSCTransformer, ...],
    generator_costs: tuple[ArpaeSCGeneratorCost, ...],
) -> SourceAwarePublicGridData:
    source = config["source"]
    raw_sha = _require_sha(source_path, str(source.get("sha256", "")) or None)
    contingency_sha = _require_sha(contingency_path, str(source.get("contingency_sha256", "")) or None)
    cost_sha = _require_sha(cost_path, str(source.get("cost_sha256", "")) or None)
    inl_sha = _require_sha(inl_path, str(source.get("inl_sha256", "")) or None)
    load_by_bus: dict[str, float] = {}
    generation_by_bus: dict[str, float] = {}
    source_records: dict[str, list[str]] = {bus.bus_id: [bus.source_record] for bus in buses}
    for load in loads:
        if load.in_service:
            load_by_bus[load.bus_id] = load_by_bus.get(load.bus_id, 0.0) + max(0.0, load.active_power_kw)
        source_records.setdefault(load.bus_id, []).append(load.source_record)
    for generator in generators:
        if generator.in_service:
            generation_by_bus[generator.bus_id] = generation_by_bus.get(generator.bus_id, 0.0) + max(
                0.0, generator.maximum_active_power_kw
            )
        source_records.setdefault(generator.bus_id, []).append(generator.source_record)
    nodes = tuple(
        PublicNode(
            node_id=bus.bus_id,
            load_kw=load_by_bus.get(bus.bus_id, 0.0),
            generation_kw=generation_by_bus.get(bus.bus_id, 0.0),
            source_record=" | ".join(source_records.get(bus.bus_id, (bus.source_record,))),
        )
        for bus in sorted(buses, key=lambda item: int(item.bus_id))
    )
    edges = tuple(
        [
            *(
                PublicEdge(
                    edge_id=f"branch_{branch.from_bus_id}_{branch.to_bus_id}_{branch.circuit_id}",
                    source=branch.from_bus_id,
                    target=branch.to_bus_id,
                    capacity_kw=None,
                    in_service=branch.in_service,
                    source_record=branch.source_record,
                )
                for branch in branches
            ),
            *(
                PublicEdge(
                    edge_id=f"transformer_{transformer.from_bus_id}_{transformer.to_bus_id}_{transformer.circuit_id}",
                    source=transformer.from_bus_id,
                    target=transformer.to_bus_id,
                    capacity_kw=None,
                    in_service=transformer.in_service,
                    source_record=" | ".join(transformer.source_records),
                )
                for transformer in transformers
            ),
        ]
    )
    published_contingencies = _parse_arpae_contingencies(contingency_path)
    metadata = {
        "adapter": "arpae_go_psse",
        "generator_cost_mapping": "ARPA-E Challenge 1 ROP piece-wise linear tables",
        "generator_dispatch_mapping": "generator dispatch fourth field -> active dispatch table; active dispatch last field -> piecewise cost table",
        "time_period_count": 1,
        "published_transformer_mva_ratings_converted_to_kw": False,
        "raw_path": str(source_path),
        "contingency_path": str(contingency_path),
        "cost_path": str(cost_path),
        "rop_path": str(cost_path),
        "inl_path": str(inl_path),
        "raw_sha256": raw_sha,
        "contingency_sha256": contingency_sha,
        "cost_sha256": cost_sha,
        "rop_sha256": cost_sha,
        "inl_sha256": inl_sha,
        "source_version": str(source.get("version", "")),
        "source_url": str(source.get("url", "")),
        "source_license": str(source.get("license", "")),
        "transformation": str(source.get("transformation", "")),
        "inl_response_limit_provenance": "Published INL file retained as source provenance and checksum-verified; no synthetic response limits are added.",
        "time_period_duration_statement": "Challenge 1 is represented as a single steady-state period with no published duration, so duration_hours is intentionally unset.",
        "bus_count": len(buses),
        "load_count": len(loads),
        "generator_count": len(generators),
        "branch_count": len(branches),
        "transformer_count": len(transformers),
        "generator_cost_count": len(generator_costs),
        "contingency_count": len(published_contingencies),
        "contingency_rule": "published ARPA-E Challenge 1 CON actions only",
    }
    return SourceAwarePublicGridData(
        benchmark=str(config["benchmark"]["id"]),
        family=str(config["benchmark"]["family"]),
        nodes=nodes,
        edges=edges,
        contingencies=published_contingencies,
        source_path=str(source_path),
        source_sha256=raw_sha,
        source_version=metadata["source_version"],
        source_url=metadata["source_url"],
        source_license=metadata["source_license"],
        transformation=metadata["transformation"],
        metadata=metadata,
    )


def parse_arpae_sc_cmpo_case(config: Mapping[str, Any]) -> ArpaeSCCMPOCase:
    """Parse the configured ARPA-E GO public benchmark into typed SC-CMPO records."""

    adapter = str(config.get("benchmark", {}).get("adapter", ""))
    if adapter and adapter != "arpae_go_psse":
        raise ValueError(f"unsupported ARPA-E SC-CMPO adapter: {adapter}")
    source_path = _resolve_path(str(config["source"]["local_path"]))
    contingency_path = _resolve_path(str(config["source"]["contingency_path"]))
    cost_path = _resolve_path(str(config["source"]["cost_path"]))
    inl_path = _resolve_path(str(config["source"]["inl_path"]))
    if not cost_path.exists():
        raise FileNotFoundError(f"missing configured ARPA-E cost file: {cost_path}")
    if not inl_path.exists():
        raise FileNotFoundError(f"missing configured ARPA-E INL file: {inl_path}")
    sections = _split_raw_sections(source_path)
    buses = _parse_buses(sections["bus"])
    loads = _parse_loads(sections["load"])
    generators = _parse_generators(sections["generator"])
    branches = _parse_branches(sections["branch"])
    transformers = _parse_transformers(sections["transformer"])
    generator_costs = _parse_generator_costs(generators, cost_path)
    time_periods = (
        ArpaeSCTimePeriod(
            period_id="single_steady_state",
            duration_hours=None,
            temporal_profile_available=False,
            source_record=(
                "Configured SC-CMPO horizon=1 from phase3_sc_cmpo_arpae.yaml; "
                "RAW/ROP/CON inputs provide a single steady-state operating point."
            ),
        ),
    )
    grid = _build_grid(
        config,
        source_path,
        contingency_path,
        cost_path,
        inl_path,
        buses,
        loads,
        generators,
        branches,
        transformers,
        generator_costs,
    )
    metadata = {
        "benchmark": grid.benchmark,
        "family": grid.family,
        "source_files": {
            "raw": str(source_path),
            "contingency": str(contingency_path),
            "cost": str(cost_path),
            "rop": str(cost_path),
            "inl": str(inl_path),
        },
    }
    return ArpaeSCCMPOCase(
        buses=buses,
        loads=loads,
        generators=generators,
        branches=branches,
        transformers=transformers,
        generator_costs=generator_costs,
        time_periods=time_periods,
        grid=grid,
        metadata=metadata,
    )


def build_arpae_microgrid_candidates(
    case: ArpaeSCCMPOCase,
    *,
    count: int,
    patch_size: int,
    deterministic_seed: int,
) -> list[UpgradePatch]:
    """Select deterministic connected public-grid patches from the parsed ARPA-E case."""

    patches = select_upgrade_patches(
        case.grid,
        count=count,
        patch_size=patch_size,
        deterministic_seed=deterministic_seed,
    )
    result: list[UpgradePatch] = []
    for patch in patches:
        selection_rule = patch.selection_rule
        if "connected" not in selection_rule.lower():
            selection_rule = f"connected public-grid patch; {selection_rule}"
        result.append(
            UpgradePatch(
                patch_id=patch.patch_id,
                node_ids=patch.node_ids,
                load_kw=patch.load_kw,
                existing_generation_kw=patch.existing_generation_kw,
                islanded_deficit_kw=patch.islanded_deficit_kw,
                boundary_edge_ids=patch.boundary_edge_ids,
                selection_rule=selection_rule,
            )
        )
    return result


__all__ = [
    "ArpaeSCBranch",
    "ArpaeSCBus",
    "ArpaeSCCMPOCase",
    "ArpaeSCGenerator",
    "ArpaeSCGeneratorCost",
    "ArpaeSCLoad",
    "ArpaeSCTimePeriod",
    "ArpaeSCTransformer",
    "SourceAwarePublicGridData",
    "build_arpae_microgrid_candidates",
    "parse_arpae_sc_cmpo_case",
]
