"""Scenario-Coupled Consensus CMPO built only from pinned public inputs."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from cmpo.benchmarks import parse_pglib_matpower_case
from cmpo.polynomial import PolynomialModel
from cmpo.qci_export import build_polynomial_model_payload
from cmpo.upgrade_planning import (
    PublicContingency,
    PublicEdge,
    PublicGridData,
    PublicNode,
    TechnologyCost,
    UpgradePlan,
    build_upgrade_plan,
    load_atb_cost_catalog,
    select_upgrade_patches,
    sha256_file,
)


SCENARIO_NAMES = (
    "normal",
    "renewable_shortfall",
    "demand_surge",
    "pcc_loss",
    "local_generator_loss",
    "forced_islanding",
    "restoration",
    "combined_high_stress",
)

SHARED_VARIABLES = (
    "upgrade_select_pv",
    "upgrade_select_bess",
    "upgrade_select_dispatchable",
    "pv_capacity_fraction",
    "bess_energy_fraction",
    "bess_power_fraction",
    "dispatchable_capacity_fraction",
    "islanding_eligibility",
    "base_mode_connected",
    "base_mode_islanded",
    "base_mode_restoration",
    "bess_reserve_target",
    "bess_soc_target",
    "critical_load_priority",
    "tie_pcc_reserve_target",
)

RECOURSE_GROUPS = (
    "mode_connected",
    "mode_islanded",
    "mode_restoration",
    "der_commitment",
    "der_capacity_slack",
    "battery_action_charge",
    "battery_action_hold",
    "battery_action_discharge",
    "critical_load_service",
    "tie_pcc_response",
    "load_shedding_allocation",
)


@dataclass(frozen=True)
class CoupledScenario:
    """One robust recourse block linked to the shared upgrade variables."""

    name: str
    pcc_available: bool
    pv_available: bool
    existing_generation_available: bool
    forced_islanding: bool
    restoration_mode: bool
    load_requirement_kw: float
    source_contingency: str
    construction_rule: str


@dataclass(frozen=True)
class SCCMPOBuildResult:
    """Payload and row-oriented manifests for one public benchmark patch."""

    payload: dict[str, Any]
    upgrade_plan: UpgradePlan
    scenarios: tuple[CoupledScenario, ...]
    pre_normalization_max_abs_coefficient: float


def load_sc_cmpo_config(path: Path | str) -> dict[str, Any]:
    """Load and validate one SC-CMPO benchmark configuration."""

    config = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    required = {"benchmark", "source", "model", "qci", "cost_catalog"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"SC-CMPO config is missing sections: {sorted(missing)}")
    scenario_names = tuple(config["model"].get("scenarios", ()))
    if not 6 <= len(scenario_names) <= 10:
        raise ValueError("SC-CMPO requires 6-10 scenarios per Hamiltonian")
    unknown = set(scenario_names) - set(SCENARIO_NAMES)
    if unknown:
        raise ValueError(f"unsupported SC-CMPO scenarios: {sorted(unknown)}")
    return config


def _source_metadata(config: dict[str, Any], source_path: Path) -> dict[str, str]:
    source = config["source"]
    digest = sha256_file(source_path)
    expected = str(source.get("sha256", "")).removeprefix("sha256:")
    if expected and expected != digest:
        raise ValueError(f"checksum mismatch for {source_path}: expected {expected}, got {digest}")
    fields = {
        "source_sha256": digest,
        "source_version": str(source.get("version", "")),
        "source_url": str(source.get("url", "")),
        "source_license": str(source.get("license", "")),
        "transformation": str(source.get("transformation", "")),
    }
    if any(not value for value in fields.values()):
        raise ValueError(f"incomplete public-source provenance for {source_path}")
    return fields


def _build_nodes(
    loads_kw: dict[str, float],
    generation_kw: dict[str, float],
    source_records: dict[str, list[str]],
) -> tuple[PublicNode, ...]:
    node_ids = sorted(
        set(loads_kw) | set(generation_kw) | set(source_records),
        key=lambda value: (len(value), value),
    )
    return tuple(
        PublicNode(
            node_id=node_id,
            load_kw=max(0.0, loads_kw.get(node_id, 0.0)),
            generation_kw=max(0.0, generation_kw.get(node_id, 0.0)),
            source_record=" | ".join(source_records.get(node_id, [f"public node {node_id}"])),
        )
        for node_id in node_ids
    )


def _parse_pglib_grid(config: dict[str, Any]) -> PublicGridData:
    source_path = Path(config["source"]["local_path"])
    parsed = parse_pglib_matpower_case(source_path)
    loads_kw = {str(row["bus"]): float(row["pd"]) * 1000.0 for row in parsed["buses"]}
    generation_kw: dict[str, float] = {}
    records: dict[str, list[str]] = {}
    for row in parsed["buses"]:
        records.setdefault(str(row["bus"]), []).append(
            f"PGLib bus={row['bus']} pd_mw={row['pd']} base_kv={row['base_kv']}"
        )
    contingencies: list[PublicContingency] = []
    for index, row in enumerate(parsed["generators"]):
        node_id = str(row["bus"])
        if int(row.get("status", 1)) != 0:
            generation_kw[node_id] = generation_kw.get(node_id, 0.0) + float(row["pmax"]) * 1000.0
        records.setdefault(node_id, []).append(
            f"PGLib generator row={index} pmax_mw={row['pmax']} status={row.get('status', 1)}"
        )
        if int(row.get("status", 1)) != 0:
            contingencies.append(
                PublicContingency(
                    contingency_id=f"deterministic_n_1_generator_{index}",
                    component_kind="generator",
                    component_id=f"generator_{index}_bus_{node_id}",
                    action="remove one listed in-service PGLib generator",
                    source_record=f"PGLib generator row={index}; deterministic N-1 construction",
                )
            )
    edges: list[PublicEdge] = []
    for index, row in enumerate(parsed["branches"]):
        edge_id = f"branch_{index}_{row['source']}_{row['target']}"
        in_service = int(row.get("status", 1)) != 0
        edges.append(
            PublicEdge(
                edge_id=edge_id,
                source=str(row["source"]),
                target=str(row["target"]),
                capacity_kw=None,
                in_service=in_service,
                source_record=(
                    f"PGLib branch row={index} rate_mva={row['rate']} x={row['x']} status={row.get('status', 1)}"
                ),
            )
        )
        if in_service:
            contingencies.append(
                PublicContingency(
                    contingency_id=f"deterministic_n_1_{edge_id}",
                    component_kind="branch",
                    component_id=edge_id,
                    action="open one listed in-service PGLib branch",
                    source_record=f"PGLib branch row={index}; deterministic N-1 construction",
                )
            )
    meta = _source_metadata(config, source_path)
    return PublicGridData(
        benchmark=str(config["benchmark"]["id"]),
        family=str(config["benchmark"]["family"]),
        nodes=_build_nodes(loads_kw, generation_kw, records),
        edges=tuple(edges),
        contingencies=tuple(contingencies),
        source_path=str(source_path),
        **meta,
    )


def _split_raw_sections(path: Path) -> dict[str, list[str]]:
    section_names = (
        "bus",
        "load",
        "fixed_shunt",
        "generator",
        "branch",
        "transformer",
    )
    sections = {name: [] for name in section_names}
    current = 0
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[3:]
    for line in lines:
        if re.match(r"^\s*0\s*/", line):
            current += 1
            if current >= len(section_names):
                break
            continue
        sections[section_names[current]].append(line)
    return sections


def _csv_row(line: str) -> list[str]:
    return [item.strip().strip("'") for item in next(csv.reader([line], skipinitialspace=True))]


def _parse_arpae_contingencies(path: Path) -> tuple[PublicContingency, ...]:
    contingencies: list[PublicContingency] = []
    current = ""
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("CONTINGENCY "):
            current = line.removeprefix("CONTINGENCY ").strip()
            continue
        unit_match = re.search(r"REMOVE\s+UNIT\s+(\S+)\s+FROM\s+BUS\s+(\d+)", line, flags=re.IGNORECASE)
        if unit_match:
            contingencies.append(
                PublicContingency(
                    contingency_id=current or f"generator_bus_{unit_match.group(2)}",
                    component_kind="generator",
                    component_id=f"bus_{unit_match.group(2)}_unit_{unit_match.group(1)}",
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
            component = f"branch_{branch_match.group(1)}_{branch_match.group(2)}_{branch_match.group(3) or '1'}"
            contingencies.append(
                PublicContingency(
                    contingency_id=current or component,
                    component_kind="branch",
                    component_id=component,
                    action=line,
                    source_record=f"{path}:{line}",
                )
            )
    return tuple(contingencies)


def _parse_arpae_grid(config: dict[str, Any]) -> PublicGridData:
    source_path = Path(config["source"]["local_path"])
    contingency_path = Path(config["source"]["contingency_path"])
    sections = _split_raw_sections(source_path)
    loads_kw: dict[str, float] = {}
    generation_kw: dict[str, float] = {}
    records: dict[str, list[str]] = {}
    for index, line in enumerate(sections["bus"]):
        row = _csv_row(line)
        if not row:
            continue
        node_id = str(int(float(row[0])))
        records.setdefault(node_id, []).append(f"ARPA-E RAW bus row={index}")
    for index, line in enumerate(sections["load"]):
        row = _csv_row(line)
        if len(row) < 7 or int(float(row[2])) == 0:
            continue
        node_id = str(int(float(row[0])))
        loads_kw[node_id] = loads_kw.get(node_id, 0.0) + max(0.0, float(row[5])) * 1000.0
        records.setdefault(node_id, []).append(f"ARPA-E RAW load row={index} id={row[1]} pl_mw={row[5]}")
    for index, line in enumerate(sections["generator"]):
        row = _csv_row(line)
        if len(row) < 18 or int(float(row[14])) == 0:
            continue
        node_id = str(int(float(row[0])))
        generation_kw[node_id] = generation_kw.get(node_id, 0.0) + max(0.0, float(row[16])) * 1000.0
        records.setdefault(node_id, []).append(f"ARPA-E RAW generator row={index} id={row[1]} pt_mw={row[16]}")
    edges: list[PublicEdge] = []
    for index, line in enumerate(sections["branch"]):
        row = _csv_row(line)
        if len(row) < 14:
            continue
        source = str(int(float(row[0])))
        target = str(int(float(row[1])))
        circuit = row[2]
        edge_id = f"branch_{source}_{target}_{circuit}"
        rate = max(0.0, float(row[6]))
        edges.append(
            PublicEdge(
                edge_id=edge_id,
                source=source,
                target=target,
                capacity_kw=None,
                in_service=int(float(row[13])) != 0,
                source_record=f"ARPA-E RAW branch row={index} rate_a_mva={rate} status={row[13]}",
            )
        )
    transformer_contingencies: list[PublicContingency] = []
    transformer_lines = sections["transformer"]
    transformer_index = 0
    line_index = 0
    while line_index < len(transformer_lines):
        row = _csv_row(transformer_lines[line_index])
        if len(row) < 12:
            raise ValueError(f"invalid ARPA-E RAW transformer record at line {line_index}")
        source = str(int(float(row[0])))
        target = str(int(float(row[1])))
        third_winding = int(float(row[2]))
        if third_winding != 0:
            raise ValueError("SC-CMPO ARPA-E adapter currently requires two-winding public transformer records")
        circuit = row[3]
        edge_id = f"transformer_{source}_{target}_{circuit}"
        in_service = int(float(row[11])) != 0
        edges.append(
            PublicEdge(
                edge_id=edge_id,
                source=source,
                target=target,
                capacity_kw=None,
                in_service=in_service,
                source_record=(
                    f"ARPA-E RAW transformer record={transformer_index} status={row[11]}; "
                    "MVA ratings retained in the source file and not converted to active-power limits"
                ),
            )
        )
        if in_service:
            transformer_contingencies.append(
                PublicContingency(
                    contingency_id=f"deterministic_n_1_{edge_id}",
                    component_kind="transformer",
                    component_id=edge_id,
                    action="open one listed in-service ARPA-E RAW transformer",
                    source_record=(
                        f"ARPA-E RAW transformer record={transformer_index}; deterministic N-1 construction"
                    ),
                )
            )
        transformer_index += 1
        line_index += 4
    meta = _source_metadata(config, source_path)
    return PublicGridData(
        benchmark=str(config["benchmark"]["id"]),
        family=str(config["benchmark"]["family"]),
        nodes=_build_nodes(loads_kw, generation_kw, records),
        edges=tuple(edges),
        contingencies=_parse_arpae_contingencies(contingency_path) + tuple(transformer_contingencies),
        source_path=str(source_path),
        **meta,
    )


def _dss_property(line: str, name: str) -> str | None:
    match = re.search(rf"(?:^|\s){re.escape(name)}\s*=\s*([^\s!]+)", line, flags=re.IGNORECASE)
    return match.group(1).strip("[]\"'") if match else None


def _dss_bus(value: str) -> str:
    return value.split(".", 1)[0]


def _parse_ieee123_grid(config: dict[str, Any]) -> PublicGridData:
    source_path = Path(config["source"]["local_path"])
    load_path = Path(config["source"]["load_path"])
    regulator_path = Path(config["source"]["regulator_path"])
    loads_kw: dict[str, float] = {}
    records: dict[str, list[str]] = {}
    for index, raw_line in enumerate(load_path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        line = raw_line.split("!", 1)[0].strip()
        if not re.match(r"^new\s+load\.", line, flags=re.IGNORECASE):
            continue
        bus = _dss_bus(_dss_property(line, "Bus1") or "")
        kw = float(_dss_property(line, "kW") or 0.0)
        loads_kw[bus] = loads_kw.get(bus, 0.0) + max(0.0, kw)
        records.setdefault(bus, []).append(f"IEEE123 load line={index + 1} kw={kw}")
    edges: list[PublicEdge] = []
    for index, raw_line in enumerate(source_path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        line = raw_line.split("!", 1)[0].strip()
        match = re.match(r"^new\s+line\.([^\s]+)", line, flags=re.IGNORECASE)
        if match is None:
            continue
        bus1 = _dss_bus(_dss_property(line, "Bus1") or "")
        bus2 = _dss_bus(_dss_property(line, "Bus2") or "")
        if not bus1 or not bus2:
            continue
        enabled = (_dss_property(line, "enabled") or "yes").lower() not in {"no", "false", "0"}
        in_service = enabled and not bus2.lower().endswith("_open")
        edges.append(
            PublicEdge(
                edge_id=f"line_{match.group(1)}",
                source=bus1,
                target=bus2,
                capacity_kw=None,
                in_service=in_service,
                source_record=f"IEEE123Master.dss line={index + 1}: {line}",
            )
        )
    transformer_contingencies: list[PublicContingency] = []
    transformer_sources = (source_path, regulator_path)
    for transformer_source in transformer_sources:
        current_name: str | None = None
        current_buses: list[str] = []
        current_line = 0

        def append_transformer() -> None:
            if current_name is None or len(current_buses) < 2:
                return
            source_bus, target_bus = (_dss_bus(value) for value in current_buses[:2])
            edges.append(
                PublicEdge(
                    edge_id=f"transformer_{current_name}",
                    source=source_bus,
                    target=target_bus,
                    capacity_kw=None,
                    in_service=True,
                    source_record=f"{transformer_source.name} line={current_line}: public transformer buses",
                )
            )
            transformer_contingencies.append(
                PublicContingency(
                    contingency_id=f"deterministic_n_1_transformer_{current_name}",
                    component_kind="transformer",
                    component_id=f"transformer_{current_name}",
                    action="open one listed in-service IEEE123 transformer",
                    source_record=f"{transformer_source.name} line={current_line}; deterministic N-1 construction",
                )
            )

        for index, raw_line in enumerate(
            transformer_source.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            line = raw_line.split("!", 1)[0].strip()
            match = re.match(r"^new\s+transformer\.([^\s]+)", line, flags=re.IGNORECASE)
            if match is not None:
                append_transformer()
                current_name = match.group(1)
                current_line = index
                buses_match = re.search(r"\bbuses\s*=\s*\[([^\]]+)\]", line, flags=re.IGNORECASE)
                current_buses = buses_match.group(1).split() if buses_match else []
                continue
            if current_name is not None and line.startswith("~"):
                bus = _dss_property(line, "bus")
                if bus:
                    current_buses.append(bus)
                continue
            if line and current_name is not None:
                append_transformer()
                current_name = None
                current_buses = []
        append_transformer()
    generation_kw: dict[str, float] = {}
    node_ids = set(loads_kw)
    for edge in edges:
        node_ids.update((edge.source, edge.target))
    for node_id in node_ids:
        records.setdefault(node_id, []).append(f"IEEE123 public feeder node={node_id}")
    contingencies = tuple(
        PublicContingency(
            contingency_id=f"deterministic_n_1_{edge.edge_id}",
            component_kind="branch",
            component_id=edge.edge_id,
            action="open one in-service IEEE123 feeder line",
            source_record=edge.source_record,
        )
        for edge in edges
        if edge.in_service
    ) + tuple(transformer_contingencies)
    meta = _source_metadata(config, source_path)
    return PublicGridData(
        benchmark=str(config["benchmark"]["id"]),
        family=str(config["benchmark"]["family"]),
        nodes=_build_nodes(loads_kw, generation_kw, records),
        edges=tuple(edges),
        contingencies=contingencies,
        source_path=str(source_path),
        **meta,
    )


def load_public_grid(config: dict[str, Any]) -> PublicGridData:
    """Parse one configured public benchmark without synthetic overlays."""

    adapter = str(config["benchmark"]["adapter"])
    if adapter == "pglib_matpower":
        return _parse_pglib_grid(config)
    if adapter == "arpae_go_psse":
        from cmpo.arpae_sc_cmpo_adapter import parse_arpae_sc_cmpo_case

        return parse_arpae_sc_cmpo_case(config).grid
    if adapter == "ieee123_opendss":
        from cmpo.ieee123_sc_cmpo_adapter import parse_ieee123_sc_cmpo_case

        return parse_ieee123_sc_cmpo_case(config).grid
    raise ValueError(f"unsupported SC-CMPO public adapter: {adapter}")


def _first_contingency(grid: PublicGridData, kind: str) -> PublicContingency | None:
    return next((item for item in grid.contingencies if item.component_kind == kind), None)


def build_coupled_scenarios(
    grid: PublicGridData,
    plan: UpgradePlan,
    scenario_names: tuple[str, ...],
) -> tuple[CoupledScenario, ...]:
    """Construct robust recourse blocks from public outages and exact bounds."""

    branch_outage = _first_contingency(grid, "branch")
    generator_outage = _first_contingency(grid, "generator")
    boundary = ",".join(plan.patch.boundary_edge_ids) or "public PCC boundary"
    boundary_n_1 = plan.patch.boundary_edge_ids[0] if plan.patch.boundary_edge_ids else None
    result: list[CoupledScenario] = []
    for name in scenario_names:
        pcc_available = name not in {"pcc_loss", "forced_islanding", "combined_high_stress"}
        pv_available = name not in {"renewable_shortfall", "combined_high_stress"}
        existing_generation_available = name not in {"local_generator_loss", "combined_high_stress"}
        forced_islanding = name in {"pcc_loss", "forced_islanding", "combined_high_stress"}
        restoration_mode = name == "restoration"
        if name == "normal":
            source_contingency = "none"
            rule = "Published nominal active load and all listed components in service."
        elif name == "renewable_shortfall":
            source_contingency = "candidate_pv_binary_availability_lower_bound"
            rule = "Candidate PV availability is set to its exact lower bound zero; no weather multiplier is invented."
        elif name == "demand_surge":
            source_contingency = f"published_peak_patch_load={plan.patch.load_kw:.12g}_kw"
            rule = (
                "The full published nominal patch load is treated as simultaneously non-sheddable; "
                "no load multiplier or synthetic profile is added."
            )
        elif name == "pcc_loss":
            source_contingency = boundary_n_1 or (branch_outage.contingency_id if branch_outage else boundary)
            rule = "Deterministic loss of the lexicographically first public patch-boundary/PCC supply indicator."
        elif name == "local_generator_loss":
            source_contingency = generator_outage.contingency_id if generator_outage else "no_local_public_generator"
            rule = "Published generator contingency when available; otherwise the patch's zero native generation is retained."
        elif name == "forced_islanding":
            source_contingency = boundary
            rule = "All public boundary branches are unavailable, yielding a deterministic island."
        elif name == "restoration":
            source_contingency = branch_outage.contingency_id if branch_outage else boundary
            rule = "The lexicographically first public N-1 boundary outage is returned to service in restoration mode."
        else:
            source_contingency = ";".join(
                item for item in (boundary, generator_outage.contingency_id if generator_outage else "") if item
            )
            rule = "PCC loss, candidate-PV lower-bound availability, and published generator N-1 are combined."
        result.append(
            CoupledScenario(
                name=name,
                pcc_available=pcc_available,
                pv_available=pv_available,
                existing_generation_available=existing_generation_available,
                forced_islanding=forced_islanding,
                restoration_mode=restoration_mode,
                load_requirement_kw=plan.patch.load_kw,
                source_contingency=source_contingency,
                construction_rule=rule,
            )
        )
    return tuple(result)


def _add_square(model: PolynomialModel, constant: float, coefficients: dict[str, float], weight: float) -> None:
    """Add ``weight * (constant + sum(coeff[var] * var))**2``."""

    model.add_term(weight * constant * constant)
    items = list(coefficients.items())
    for variable, coefficient in items:
        model.add_linear(2.0 * weight * constant * coefficient, variable)
        model.add_quadratic(weight * coefficient * coefficient, variable, variable)
    for index, (left, left_coefficient) in enumerate(items):
        for right, right_coefficient in items[index + 1 :]:
            model.add_quadratic(2.0 * weight * left_coefficient * right_coefficient, left, right)


def _add_one_hot(model: PolynomialModel, variables: list[str], weight: float) -> None:
    _add_square(model, -1.0, {variable: 1.0 for variable in variables}, weight)


def _scenario_var(group: str, scenario: str) -> str:
    return f"{group}[{scenario}]"


def _add_binary(model: PolynomialModel, name: str) -> None:
    model.add_variable(name, 0.0, 1.0, "integer")


def _add_continuous(model: PolynomialModel, name: str) -> None:
    model.add_variable(name, 0.0, 1.0, "quasi_continuous")


def _normalize_model(model: PolynomialModel) -> tuple[PolynomialModel, float]:
    pre_max = max((abs(term.coefficient) for term in model.terms), default=0.0)
    scale = 1.0 / pre_max if pre_max > 1.0 else 1.0
    normalized = PolynomialModel(name=model.name)
    for variable in model.variables.values():
        normalized.add_variable(
            variable.name,
            variable.lower_bound,
            variable.upper_bound,
            variable.encoding_type,
        )
    for term in model.terms:
        normalized.add_term(term.coefficient * scale, dict(term.powers))
    return normalized, pre_max


def _option_by_technology(plan: UpgradePlan, technology: str) -> Any:
    return next(option for option in plan.options if option.technology == technology)


def build_sc_cmpo_payload(
    grid: PublicGridData,
    plan: UpgradePlan,
    catalog: dict[str, TechnologyCost],
    config: dict[str, Any],
) -> SCCMPOBuildResult:
    """Build one normalized degree-3 multi-scenario Hamiltonian."""

    scenario_names = tuple(str(item) for item in config["model"]["scenarios"])
    scenarios = build_coupled_scenarios(grid, plan, scenario_names)
    weights = {
        "simplex": 30.0,
        "adequacy": 90.0,
        "critical_service": 120.0,
        "mode": 35.0,
        "activation": 25.0,
        "preparedness": 18.0,
        "cost": 8.0,
        "coupling": 12.0,
        **{str(key): float(value) for key, value in config["model"].get("weights", {}).items()},
    }
    model = PolynomialModel(name=f"sc_cmpo__{plan.patch.patch_id}")
    integer_shared = {
        "upgrade_select_pv",
        "upgrade_select_bess",
        "upgrade_select_dispatchable",
        "islanding_eligibility",
        "base_mode_connected",
        "base_mode_islanded",
        "base_mode_restoration",
    }
    for variable in SHARED_VARIABLES:
        (_add_binary if variable in integer_shared else _add_continuous)(model, variable)
    _add_one_hot(
        model,
        ["base_mode_connected", "base_mode_islanded", "base_mode_restoration"],
        weights["simplex"],
    )

    pv = _option_by_technology(plan, "pv")
    bess = _option_by_technology(plan, "bess")
    generator = _option_by_technology(plan, "dispatchable_generation")
    total_upgrade_cost = max(plan.maximum_upgrade_cost, 1.0)
    model.add_linear(weights["cost"] * pv.total_cost / total_upgrade_cost, "pv_capacity_fraction")
    model.add_linear(weights["cost"] * bess.total_cost / total_upgrade_cost, "bess_energy_fraction")
    model.add_linear(weights["cost"] * generator.total_cost / total_upgrade_cost, "dispatchable_capacity_fraction")

    activation_pairs = (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("bess_power_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    )
    for capacity, selection in activation_pairs:
        # capacity**2 * (1-selection) is zero only when unused or explicitly selected.
        model.add_quadratic(weights["activation"], capacity, capacity)
        model.add_cubic(-weights["activation"], capacity, capacity, selection)
    _add_square(
        model,
        0.0,
        {"bess_energy_fraction": 1.0, "bess_power_fraction": -1.0},
        weights["activation"],
    )
    for preparedness in (
        "islanding_eligibility",
        "bess_reserve_target",
        "bess_soc_target",
        "critical_load_priority",
        "tie_pcc_reserve_target",
    ):
        _add_square(model, -1.0, {preparedness: 1.0}, weights["preparedness"])

    load = max(plan.patch.load_kw, 1e-9)
    deficit_fraction = min(1.0, plan.patch.islanded_deficit_kw / load)
    existing_fraction = min(1.0, plan.patch.existing_generation_kw / load)
    for scenario in scenarios:
        for group in RECOURSE_GROUPS:
            name = _scenario_var(group, scenario.name)
            if group.startswith("mode_") or group.startswith("battery_action_"):
                _add_binary(model, name)
            else:
                _add_continuous(model, name)
        mode_vars = [_scenario_var(f"mode_{mode}", scenario.name) for mode in ("connected", "islanded", "restoration")]
        action_vars = [
            _scenario_var(f"battery_action_{action}", scenario.name)
            for action in ("charge", "hold", "discharge")
        ]
        _add_one_hot(model, mode_vars, weights["simplex"])
        _add_one_hot(model, action_vars, weights["simplex"])
        if scenario.name == "normal":
            for mode in ("connected", "islanded", "restoration"):
                _add_square(
                    model,
                    0.0,
                    {
                        f"base_mode_{mode}": 1.0,
                        _scenario_var(f"mode_{mode}", scenario.name): -1.0,
                    },
                    weights["coupling"],
                )
        desired_mode = "restoration" if scenario.restoration_mode else "islanded" if scenario.forced_islanding else "connected"
        _add_square(model, -1.0, {_scenario_var(f"mode_{desired_mode}", scenario.name): 1.0}, weights["mode"])
        service = _scenario_var("critical_load_service", scenario.name)
        shedding = _scenario_var("load_shedding_allocation", scenario.name)
        tie_response = _scenario_var("tie_pcc_response", scenario.name)
        der_commitment = _scenario_var("der_commitment", scenario.name)
        _add_square(model, -1.0, {service: 1.0}, weights["critical_service"])
        _add_square(model, -1.0, {service: 1.0, shedding: 1.0}, weights["critical_service"])
        if not scenario.pcc_available:
            _add_square(model, 0.0, {tie_response: 1.0}, weights["mode"])
        if scenario.forced_islanding:
            _add_square(
                model,
                0.0,
                {
                    _scenario_var("mode_islanded", scenario.name): 1.0,
                    "islanding_eligibility": -1.0,
                },
                weights["mode"],
            )
        capacity_slack = _scenario_var("der_capacity_slack", scenario.name)
        existing = existing_fraction if scenario.existing_generation_available else 0.0
        # DER commitment is normalized dispatched local power. The slack allows
        # installed capacity to be curtailed, avoiding a false conflict between
        # connected and islanded scenarios. A coefficient of three spans the
        # maximum unused normalized capacity from the three candidate assets.
        _add_square(
            model,
            -existing,
            {
                der_commitment: 1.0,
                capacity_slack: 3.0,
                "pv_capacity_fraction": -deficit_fraction if scenario.pv_available else 0.0,
                "bess_power_fraction": -deficit_fraction,
                "dispatchable_capacity_fraction": -deficit_fraction,
            },
            weights["adequacy"],
        )
        _add_square(
            model,
            0.0,
            {
                service: 1.0,
                der_commitment: -1.0,
                tie_response: -1.0 if scenario.pcc_available else 0.0,
            },
            weights["adequacy"],
        )
        model.add_quadratic(-weights["coupling"], "critical_load_priority", service)
        model.add_quadratic(-weights["coupling"], "tie_pcc_reserve_target", tie_response)
        model.add_quadratic(-weights["coupling"], "dispatchable_capacity_fraction", der_commitment)
        model.add_cubic(
            -weights["coupling"],
            "dispatchable_capacity_fraction",
            der_commitment,
            service,
        )
        model.add_cubic(
            -weights["coupling"],
            "bess_power_fraction",
            _scenario_var("battery_action_discharge", scenario.name),
            service,
        )
        if scenario.pv_available:
            model.add_cubic(-weights["coupling"], "pv_capacity_fraction", der_commitment, service)

    normalized, pre_max = _normalize_model(model)
    max_variables = int(config["qci"].get("max_variables", 132))
    max_degree = int(config["qci"].get("max_degree", 3))
    if normalized.variable_count() > max_variables:
        raise ValueError(f"SC-CMPO payload has {normalized.variable_count()} variables > {max_variables}")
    normalized.validate_degree(max_degree)
    if normalized.degree() != 3:
        raise ValueError("SC-CMPO must retain native degree-3 coupling terms")
    metadata = {
        "scenario": f"scenario_coupled_{len(scenarios)}",
        "horizon": int(config["model"].get("horizon", 1)),
        "penalty_weights": weights,
        "patch": plan.patch.patch_id,
        "patch_ids": list(plan.patch.node_ids),
    }
    payload = build_polynomial_model_payload(normalized, metadata)
    post_max = max((abs(term["coefficient"]) for term in payload["polynomial_terms"]), default=0.0)
    payload["schema"] = "cmpo.sc_cmpo.v1"
    payload["phase2_notice"] = "SC-CMPO build-only public-data artifact; not submitted to QCi."
    payload["scenario_metadata"].update(
        {
            "scenarios": [asdict(scenario) for scenario in scenarios],
            "scenario_count": len(scenarios),
            "weighting": "equal robust recourse blocks; not empirical probabilities",
        }
    )
    payload["scaling_information"] = {
        "normalization_applied": True,
        "coefficient_scaling_factor": 1.0 / pre_max if pre_max > 1.0 else 1.0,
        "pre_normalization_max_abs_coefficient": pre_max,
        "post_normalization_max_abs_coefficient": post_max,
        "variable_bounds": [0.0, 1.0],
    }
    payload["sc_cmpo"] = {
        "formulation": "Scenario-Coupled Consensus CMPO",
        "abbreviation": "SC-CMPO",
        "public_benchmark": grid.benchmark,
        "public_benchmark_family": grid.family,
        "source_path": grid.source_path,
        "source_sha256": grid.source_sha256,
        "source_version": grid.source_version,
        "source_url": grid.source_url,
        "source_license": grid.source_license,
        "source_transformation": grid.transformation,
        "public_adapter_metadata": dict(getattr(grid, "metadata", {})),
        "shared_first_stage_variables": list(SHARED_VARIABLES),
        "shared_first_stage_scope": (
            "one benchmark-level technology/reserve policy shared by every scenario; "
            "independent patch estimates are reconciled before system projection"
        ),
        "consensus_keys": {
            variable: f"{grid.benchmark}::{variable}" for variable in SHARED_VARIABLES
        },
        "shared_first_stage_variable_count": len(SHARED_VARIABLES),
        "recourse_variable_groups": list(RECOURSE_GROUPS),
        "recourse_variable_semantics": {
            "der_commitment": "normalized dispatched local active power, not installed capacity",
            "der_capacity_slack": (
                "normalized unused available local capacity; coefficient three spans all candidate technologies"
            ),
            "tie_pcc_response": "normalized active-power supply from an available public-grid connection",
            "critical_load_service": "served fraction of the selected island's public active load",
            "load_shedding_allocation": "unserved fraction complementing critical-load service",
        },
        "recourse_variable_count": len(RECOURSE_GROUPS) * len(scenarios),
        "scenario_names": [scenario.name for scenario in scenarios],
        "scenario_count": len(scenarios),
        "upgrade_patch": asdict(plan.patch),
        "patch_public_nodes": [
            asdict(node) for node in grid.nodes if node.node_id in set(plan.patch.node_ids)
        ],
        "public_system_summary": {
            "node_count": len(grid.nodes),
            "edge_count": len(grid.edges),
            "contingency_count": len(grid.contingencies),
            "total_active_load_kw": sum(node.load_kw for node in grid.nodes),
            "total_dispatchable_capacity_kw": sum(node.generation_kw for node in grid.nodes),
            "selected_patch_load_fraction": plan.patch.load_kw
            / max(sum(node.load_kw for node in grid.nodes), 1e-9),
        },
        "upgrade_options": [asdict(option) for option in plan.options],
        "minimum_resilient_upgrade_cost": plan.minimum_resilient_upgrade_cost,
        "maximum_upgrade_cost": plan.maximum_upgrade_cost,
        "critical_load_definition": "all active load in the selected public benchmark island",
        "input_policy": {
            "public_inputs_only": True,
            "random_topology_or_asset_values": False,
            "undocumented_synthetic_values": [],
            "deterministic_seed": int(config["model"].get("deterministic_seed", 0)),
            "seed_use": "SHA-256 tie-breaking only; no random-number generator is invoked",
        },
        "challenge_stages": list(config["model"].get("challenge_stages", [])),
        "qci_executable_reason": (
            f"bounded normalized variables={normalized.variable_count()} <= {max_variables}; "
            f"degree={normalized.degree()} <= {max_degree}; scenarios={len(scenarios)}"
        ),
        "cost_catalog": {technology: asdict(cost) for technology, cost in catalog.items()},
    }
    return SCCMPOBuildResult(
        payload=payload,
        upgrade_plan=plan,
        scenarios=scenarios,
        pre_normalization_max_abs_coefficient=pre_max,
    )


def build_sc_cmpo_from_config(config_path: Path | str) -> list[SCCMPOBuildResult]:
    """Build every configured patch for one benchmark family."""

    config = load_sc_cmpo_config(config_path)
    grid = load_public_grid(config)
    catalog = load_atb_cost_catalog(config["cost_catalog"]["local_path"])
    patches = select_upgrade_patches(
        grid,
        count=int(config["model"].get("patch_count", 1)),
        patch_size=int(config["model"].get("patch_size", 1)),
        deterministic_seed=int(config["model"].get("deterministic_seed", 0)),
    )
    return [build_sc_cmpo_payload(grid, build_upgrade_plan(patch, catalog), catalog, config) for patch in patches]


def payload_json(result: SCCMPOBuildResult) -> str:
    """Serialize one deterministic payload for reproducibility checks."""

    return json.dumps(result.payload, indent=2, sort_keys=False)
