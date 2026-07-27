"""Matched full-system active-power projection for SC-CMPO decisions.

The patch Hamiltonians choose planning and recourse signals.  This module does
not average their independent resilience metrics.  It reconstructs one set of
physical upgrades, projects every scenario over the complete public topology,
and scores the resulting system once.

The network model is a lossless, capacitated active-power flow model.  It is
deliberately not an AC OPF reproduction: voltage, reactive power, and thermal
conversion from MVA to kW are outside the information carried by
``PublicGridData``.  Missing active-power edge ratings therefore use the full
public-system active load as a documented finite upper bound.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import OptimizeResult, linprog
from scipy.sparse import csr_matrix, lil_matrix, vstack

from cmpo.benchmarks import parse_pglib_matpower_case
from cmpo.upgrade_planning import PublicGridData


PROJECTION_SCOPE = (
    "lossless capacitated active-power network flow over the complete public benchmark; "
    "not AC OPF; voltage, reactive power, and losses are not modeled"
)
EDGE_CAPACITY_FALLBACK = (
    "when PublicEdge.capacity_kw is absent, use the complete public-system nominal "
    "active load as a finite kW upper bound; published MVA is not reinterpreted as kW"
)
STORAGE_ACCOUNTING_SCOPE = (
    "one-hour lossless SOC balance because the public inputs contain no charge/discharge efficiency; "
    "restoration cannot end below its scenario-start SOC"
)
RISK_WEIGHT = 0.25
_EPS = 1e-9
_PROJECTION_TOLERANCE = 1e-6


@dataclass(frozen=True)
class _Generator:
    resource_id: str
    node_id: str
    capacity_kw: float
    minimum_kw: float
    cost_model: int | None
    cost_coefficients: tuple[float, ...]
    source_record: str

    @property
    def has_public_operating_cost(self) -> bool:
        return self.cost_model == 2 and bool(self.cost_coefficients)


@dataclass
class _VariableBook:
    names: list[str]
    bounds: list[tuple[float, float]]
    positions: dict[tuple[str, str], int]

    @classmethod
    def create(cls) -> _VariableBook:
        return cls(names=[], bounds=[], positions={})

    def add(self, group: str, key: str, lower: float, upper: float) -> int:
        position = len(self.names)
        self.names.append(f"{group}::{key}")
        self.bounds.append((float(lower), float(upper)))
        self.positions[(group, key)] = position
        return position

    def at(self, group: str, key: str) -> int:
        return self.positions[(group, key)]


def _bounded(value: Any, lower: float = 0.0, upper: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return lower
    if not math.isfinite(numeric):
        return lower
    return min(max(numeric, lower), upper)


def _named_payloads(payloads: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    if isinstance(payloads, Mapping):
        named = {str(name): payload for name, payload in payloads.items()}
    else:
        named = {}
        for index, payload in enumerate(payloads):
            patch = payload.get("sc_cmpo", {}).get("upgrade_patch", {})
            name = str(patch.get("patch_id") or f"payload_{index:04d}")
            if name in named:
                raise ValueError(f"duplicate SC-CMPO payload identifier: {name}")
            named[name] = payload
    if not named:
        raise ValueError("at least one SC-CMPO payload is required")
    return named


def _scenario_records(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    metadata = payload.get("scenario_metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("SC-CMPO payload is missing scenario_metadata")
    records = metadata.get("scenarios")
    if not isinstance(records, list) or not records:
        raise ValueError("SC-CMPO payload has no scenario records")
    names = [str(record.get("name", "")) for record in records]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("SC-CMPO scenario names must be nonempty and unique")
    return records


def scenario_probability_map(payloads: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    """Return validated benchmark-level scenario probabilities.

    Current SC-CMPO payloads record equally weighted robust recourse blocks,
    so each unique scenario receives ``1 / scenario_count``.  Explicit
    probabilities are also accepted when every payload records the same values
    and those values already sum to one; they are never silently normalized.
    """

    named = _named_payloads(payloads)
    reference_names: tuple[str, ...] | None = None
    reference_explicit: dict[str, float] | None = None
    uses_equal_weighting = False

    for payload_name, payload in named.items():
        records = _scenario_records(payload)
        names = tuple(str(record["name"]) for record in records)
        if reference_names is None:
            reference_names = names
        elif set(names) != set(reference_names):
            raise ValueError(f"scenario set differs in payload {payload_name}")

        explicit: dict[str, float] = {}
        for record in records:
            candidates = [record.get(key) for key in ("probability", "scenario_probability", "weight")]
            present = [candidate for candidate in candidates if candidate is not None]
            if present:
                probability = float(present[0])
                if not math.isfinite(probability) or probability < 0.0:
                    raise ValueError(f"invalid scenario probability in payload {payload_name}")
                explicit[str(record["name"])] = probability
        if explicit and len(explicit) != len(records):
            raise ValueError(f"payload {payload_name} mixes explicit and implicit scenario probabilities")
        if explicit:
            if reference_explicit is None:
                reference_explicit = explicit
            elif any(
                not math.isclose(explicit[name], reference_explicit[name], rel_tol=0.0, abs_tol=1e-12)
                for name in reference_explicit
            ):
                raise ValueError(f"explicit scenario probabilities differ in payload {payload_name}")
        else:
            weighting = str(payload.get("scenario_metadata", {}).get("weighting", "")).lower()
            if "equal" not in weighting:
                raise ValueError(
                    f"payload {payload_name} has neither explicit probabilities nor documented equal weighting"
                )
            uses_equal_weighting = True

    assert reference_names is not None
    if reference_explicit is not None and uses_equal_weighting:
        raise ValueError("SC-CMPO payload collection mixes explicit and equal scenario weighting")
    if reference_explicit is not None:
        probabilities = {name: reference_explicit[name] for name in reference_names}
    else:
        equal = 1.0 / len(reference_names)
        probabilities = {name: equal for name in reference_names}
    total = math.fsum(probabilities.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"scenario probabilities must sum to one, got {total:.16g}")
    return probabilities


def _trace_id(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:20]}"


def _failure(method: str, benchmark: str, stage: str, reason: str, trace_id: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "method": method,
        "benchmark": benchmark,
        "failure_stage": stage,
        "failure_reason": reason,
        "system_trace_id": trace_id,
        "system_metrics_produced": False,
        "projection_scope": PROJECTION_SCOPE,
    }


def _canonical_scenarios(named: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    canonical: dict[str, dict[str, Any]] = {}
    semantic_fields = (
        "pcc_available",
        "pv_available",
        "existing_generation_available",
        "forced_islanding",
        "restoration_mode",
    )
    for payload_name, payload in named.items():
        for record in _scenario_records(payload):
            name = str(record["name"])
            semantics = {field: bool(record.get(field, False)) for field in semantic_fields}
            if name not in canonical:
                canonical[name] = {
                    "name": name,
                    **semantics,
                    "source_contingencies": [],
                    "construction_rules": [],
                }
            elif any(canonical[name][field] != semantics[field] for field in semantic_fields):
                raise ValueError(f"scenario semantics for {name} differ in payload {payload_name}")
            source = str(record.get("source_contingency", ""))
            if source and source not in canonical[name]["source_contingencies"]:
                canonical[name]["source_contingencies"].append(source)
            rule = str(record.get("construction_rule", ""))
            if rule and rule not in canonical[name]["construction_rules"]:
                canonical[name]["construction_rules"].append(rule)
    return canonical


def _validate_grid(grid: PublicGridData) -> None:
    node_ids = [node.node_id for node in grid.nodes]
    if not node_ids or len(node_ids) != len(set(node_ids)):
        raise ValueError("PublicGridData must contain unique public nodes")
    for node in grid.nodes:
        if not math.isfinite(node.load_kw) or not math.isfinite(node.generation_kw):
            raise ValueError(f"public node {node.node_id} has non-finite load or generation")
        if node.load_kw < 0.0 or node.generation_kw < 0.0:
            raise ValueError(f"public node {node.node_id} has negative load or generation")
    edge_ids = [edge.edge_id for edge in grid.edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError("PublicGridData edge identifiers must be unique")
    node_id_set = set(node_ids)
    for edge in grid.edges:
        if edge.source not in node_id_set or edge.target not in node_id_set:
            raise ValueError(f"public edge {edge.edge_id} references an unknown endpoint")
        if edge.capacity_kw is not None and (not math.isfinite(edge.capacity_kw) or edge.capacity_kw <= 0.0):
            raise ValueError(f"public edge {edge.edge_id} has an invalid active-power rating")


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    sc = payload.get("sc_cmpo", {})
    patch = sc.get("upgrade_patch", {})
    node_ids = [str(node_id) for node_id in patch.get("node_ids", [])]
    public_nodes = sc.get("patch_public_nodes", [])
    candidates: list[tuple[float, float, str]] = []
    for node in public_nodes:
        node_id = str(node.get("node_id", ""))
        if not node_id:
            continue
        load = max(0.0, float(node.get("load_kw", 0.0)))
        generation = max(0.0, float(node.get("generation_kw", 0.0)))
        candidates.append((load - generation, load, node_id))
    if candidates:
        return sorted(candidates, key=lambda item: (-item[0], -item[1], item[2]))[0][2]
    if node_ids:
        return sorted(node_ids)[0]
    raise ValueError("SC-CMPO upgrade patch has no physical node anchor")


def _build_upgrade_plan(
    grid: PublicGridData,
    named: Mapping[str, Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grid_nodes = {node.node_id for node in grid.nodes}
    assets: dict[str, dict[str, Any]] = {}
    variable_map = {
        "pv": ("pv_capacity_fraction", "pv_capacity_fraction", "upgrade_select_pv"),
        "bess": ("bess_energy_fraction", "bess_power_fraction", "upgrade_select_bess"),
        "dispatchable_generation": (
            "dispatchable_capacity_fraction",
            "dispatchable_capacity_fraction",
            "upgrade_select_dispatchable",
        ),
    }
    for payload_name, payload in named.items():
        sc = payload["sc_cmpo"]
        patch = sc["upgrade_patch"]
        values = patch_values[payload_name]
        anchor = _physical_anchor(payload)
        if anchor not in grid_nodes:
            raise ValueError(f"payload {payload_name} anchors an upgrade at unknown public node {anchor}")
        options = {str(option["technology"]): option for option in sc.get("upgrade_options", [])}
        for technology, (energy_name, power_name, selection_name) in variable_map.items():
            if technology not in options:
                raise ValueError(f"payload {payload_name} is missing {technology} upgrade metadata")
            option = options[technology]
            energy_fraction = _bounded(values.get(energy_name, 0.0))
            power_fraction = _bounded(values.get(power_name, 0.0))
            installed_fraction = max(energy_fraction, power_fraction)
            if installed_fraction <= _EPS:
                continue
            asset_key = f"{grid.benchmark}::{anchor}::{technology}"
            candidate = {
                "asset_key": asset_key,
                "benchmark": grid.benchmark,
                "anchor_node": anchor,
                "technology": technology,
                "installed_capacity_kw": float(option.get("capacity_kw", 0.0)) * installed_fraction,
                "installed_power_kw": float(option.get("power_kw", 0.0)) * power_fraction,
                "installed_energy_kwh": float(option.get("energy_kwh", 0.0)) * energy_fraction,
                "installed_fraction": installed_fraction,
                "installed_cost": float(option.get("total_cost", 0.0)) * installed_fraction,
                "selection_value": _bounded(values.get(selection_name, 0.0)),
                "selection_projected": bool(
                    _bounded(values.get(selection_name, 0.0)) >= 0.5 or installed_fraction > _EPS
                ),
                "bess_reserve_target": _bounded(values.get("bess_reserve_target", 0.0)),
                "bess_soc_target": _bounded(values.get("bess_soc_target", 0.0)),
                "unit_cost_per_kw": float(option.get("unit_cost_per_kw", 0.0)),
                "unit_cost_per_kwh": option.get("unit_cost_per_kwh"),
                "source_row": str(option.get("source_row", "")),
                "source_payload_ids": [payload_name],
                "source_patch_ids": [str(patch.get("patch_id", payload_name))],
                "source_sha256": str(sc.get("cost_catalog", {}).get(technology, {}).get("source_sha256", "")),
                "cost_source_url": str(sc.get("cost_catalog", {}).get(technology, {}).get("source_url", "")),
                "deduplication_rule": (
                    "one physical asset per public benchmark anchor and technology; overlapping patch proposals "
                    "are reconciled by the maximum installed physical capacity and charged once"
                ),
            }
            existing = assets.get(asset_key)
            if existing is None:
                assets[asset_key] = candidate
                continue
            existing["installed_capacity_kw"] = max(
                float(existing["installed_capacity_kw"]), float(candidate["installed_capacity_kw"])
            )
            existing["installed_power_kw"] = max(
                float(existing["installed_power_kw"]), float(candidate["installed_power_kw"])
            )
            existing["installed_energy_kwh"] = max(
                float(existing["installed_energy_kwh"]), float(candidate["installed_energy_kwh"])
            )
            existing["installed_fraction"] = max(
                float(existing["installed_fraction"]), float(candidate["installed_fraction"])
            )
            existing["installed_cost"] = max(float(existing["installed_cost"]), float(candidate["installed_cost"]))
            existing["selection_value"] = max(
                float(existing["selection_value"]), float(candidate["selection_value"])
            )
            existing["selection_projected"] = bool(
                existing["selection_projected"] or candidate["selection_projected"]
            )
            existing["bess_reserve_target"] = min(
                float(existing["bess_reserve_target"]), float(candidate["bess_reserve_target"])
            )
            existing["bess_soc_target"] = min(
                float(existing["bess_soc_target"]), float(candidate["bess_soc_target"])
            )
            existing["source_payload_ids"].append(payload_name)
            existing["source_patch_ids"].append(str(patch.get("patch_id", payload_name)))

    result = []
    for asset_key in sorted(assets):
        row = assets[asset_key]
        row["source_payload_ids"] = sorted(set(row["source_payload_ids"]))
        row["source_patch_ids"] = sorted(set(row["source_patch_ids"]))
        row["public_cost_documented"] = bool(
            row["source_row"] and row["cost_source_url"] and row["source_sha256"] and row["installed_cost"] >= 0.0
        )
        result.append(row)
    return result


def _existing_generators(grid: PublicGridData) -> list[_Generator]:
    source_path = Path(grid.source_path)
    if source_path.suffix.lower() == ".m" and source_path.exists():
        parsed = parse_pglib_matpower_case(source_path)
        resources: list[_Generator] = []
        for index, row in enumerate(parsed["generators"]):
            if int(row.get("status", 1)) == 0 or float(row.get("pmax", 0.0)) <= 0.0:
                continue
            resources.append(
                _Generator(
                    resource_id=f"generator_{index}_bus_{row['bus']}",
                    node_id=str(row["bus"]),
                    capacity_kw=max(0.0, float(row["pmax"]) * 1000.0),
                    minimum_kw=max(0.0, float(row.get("pmin", 0.0)) * 1000.0),
                    cost_model=int(row.get("cost_model", 0)),
                    cost_coefficients=tuple(float(value) for value in row.get("cost_coefficients", [])),
                    source_record=f"{grid.source_path}: MATPOWER generator row {index}",
                )
            )
        if resources:
            return resources
    return [
        _Generator(
            resource_id=f"aggregate_generator_node_{node.node_id}",
            node_id=node.node_id,
            capacity_kw=max(0.0, node.generation_kw),
            minimum_kw=0.0,
            cost_model=None,
            cost_coefficients=(),
            source_record=node.source_record,
        )
        for node in grid.nodes
        if node.generation_kw > _EPS
    ]


def _public_pcc_sources(grid: PublicGridData, total_load_kw: float) -> list[dict[str, Any]]:
    if any(node.generation_kw > _EPS for node in grid.nodes):
        return []
    source_path = Path(grid.source_path)
    if not source_path.exists():
        return []
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    circuit = re.search(
        r"new\s+(?:object\s*=\s*)?circuit\.[^\n]*(?:\n\s*~[^\n]*)*",
        text,
        flags=re.IGNORECASE,
    )
    if circuit is None:
        return []
    bus = re.search(r"\bbus1\s*=\s*([^\s!]+)", circuit.group(0), flags=re.IGNORECASE)
    if bus is None:
        return []
    node_id = bus.group(1).split(".", 1)[0].strip("[]\"'")
    if node_id not in {node.node_id for node in grid.nodes}:
        return []
    return [
        {
            "source_id": f"public_pcc_{node_id}",
            "node_id": node_id,
            "capacity_kw": total_load_kw,
            "source_record": f"{grid.source_path}: public OpenDSS circuit source Bus1={node_id}",
        }
    ]


def _critical_nodes(named: Mapping[str, Mapping[str, Any]], grid: PublicGridData) -> set[str]:
    grid_nodes = {node.node_id for node in grid.nodes}
    selected: set[str] = set()
    for payload_name, payload in named.items():
        node_ids = {str(node_id) for node_id in payload["sc_cmpo"]["upgrade_patch"].get("node_ids", [])}
        unknown = node_ids - grid_nodes
        if unknown:
            raise ValueError(f"payload {payload_name} references unknown public nodes: {sorted(unknown)}")
        selected.update(node_ids)
    return selected


def _critical_priority_by_node(
    named: Mapping[str, Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
) -> dict[str, float]:
    priorities: dict[str, list[float]] = defaultdict(list)
    for payload_name, payload in named.items():
        priority = _bounded(patch_values[payload_name].get("critical_load_priority", 0.0))
        for node_id in payload["sc_cmpo"]["upgrade_patch"].get("node_ids", []):
            priorities[str(node_id)].append(priority)
    return {
        node_id: float(np.mean(node_priorities))
        for node_id, node_priorities in priorities.items()
    }


def _selected_mode(values: Mapping[str, Any], scenario: str) -> str:
    modes = ("connected", "islanded", "restoration")
    return max(modes, key=lambda mode: (_bounded(values.get(f"mode_{mode}[{scenario}]", 0.0)), -modes.index(mode)))


def _scenario_outages(
    grid: PublicGridData,
    named: Mapping[str, Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
    scenario: Mapping[str, Any],
) -> tuple[set[str], set[str], dict[str, Any]]:
    scenario_name = str(scenario["name"])
    edge_ids = {edge.edge_id for edge in grid.edges}
    contingencies = {item.contingency_id: item for item in grid.contingencies}
    unavailable_edges = {edge.edge_id for edge in grid.edges if not edge.in_service}
    unavailable_generators: set[str] = set()
    boundary_edges: set[str] = set()
    modes: dict[str, str] = {}
    tie_targets: list[float] = []
    der_commitments: list[float] = []
    critical_priorities: list[float] = []
    boundary_capacity_factors: dict[str, list[float]] = defaultdict(list)
    patch_der_caps: list[dict[str, Any]] = []
    battery_actions_by_node: dict[str, list[str]] = defaultdict(list)

    def apply_token(token: str) -> None:
        clean = token.strip()
        if not clean or clean in {"none", "candidate_pv_binary_availability_lower_bound"}:
            return
        if clean in edge_ids:
            unavailable_edges.add(clean)
            return
        contingency = contingencies.get(clean)
        if contingency is None:
            return
        if contingency.component_kind in {"branch", "transformer"}:
            unavailable_edges.add(contingency.component_id)
        elif contingency.component_kind == "generator":
            unavailable_generators.add(contingency.component_id)

    for payload_name, payload in named.items():
        values = patch_values[payload_name]
        patch = payload["sc_cmpo"]["upgrade_patch"]
        boundaries = {str(edge_id) for edge_id in patch.get("boundary_edge_ids", [])}
        boundary_edges.update(boundaries)
        mode = _selected_mode(values, scenario_name)
        modes[payload_name] = mode
        payload_scenario = next(
            record for record in _scenario_records(payload) if str(record["name"]) == scenario_name
        )
        tie_target = min(
            _bounded(values.get("tie_pcc_reserve_target", 0.0)),
            _bounded(values.get(f"tie_pcc_response[{scenario_name}]", 0.0)),
        )
        if mode == "islanded" or not bool(payload_scenario.get("pcc_available", False)):
            tie_target = 0.0
        tie_targets.append(tie_target)
        for edge_id in boundaries:
            boundary_capacity_factors[edge_id].append(tie_target)
        der_commitment = _bounded(values.get(f"der_commitment[{scenario_name}]", 0.0))
        der_commitments.append(der_commitment)
        patch_der_caps.append(
            {
                "payload_name": payload_name,
                "node_ids": [str(node_id) for node_id in patch.get("node_ids", [])],
                "dispatch_cap_kw": der_commitment * max(0.0, float(patch.get("load_kw", 0.0))),
            }
        )
        critical_priorities.append(_bounded(values.get("critical_load_priority", 0.0)))
        actions = ("charge", "hold", "discharge")
        selected_action = max(
            actions,
            key=lambda action: (
                _bounded(values.get(f"battery_action_{action}[{scenario_name}]", 0.0)),
                -actions.index(action),
            ),
        )
        for node_id in patch.get("node_ids", []):
            battery_actions_by_node[str(node_id)].append(selected_action)
        if mode == "islanded" or scenario_name in {"forced_islanding", "combined_high_stress"}:
            unavailable_edges.update(boundaries)
        if not bool(payload_scenario.get("restoration_mode", False)) and not bool(
            scenario.get("override_source_contingencies", False)
        ):
            for token in re.split(r"[;,]", str(payload_scenario.get("source_contingency", ""))):
                apply_token(token)

    if bool(scenario.get("override_source_contingencies", False)):
        for token in scenario.get("source_contingencies", []):
            apply_token(str(token))

    conflicting_actions = {
        node_id: sorted(set(actions))
        for node_id, actions in battery_actions_by_node.items()
        if len(set(actions)) > 1
    }
    if conflicting_actions:
        raise ValueError(f"post-consensus battery-action conflicts remain: {conflicting_actions}")
    return unavailable_edges, unavailable_generators, {
        "boundary_edge_ids": sorted(boundary_edges),
        "selected_modes": modes,
        "tie_target_mean": float(np.mean(tie_targets)) if tie_targets else 0.0,
        "der_commitment_mean": float(np.mean(der_commitments)) if der_commitments else 0.0,
        "critical_priority_mean": float(np.mean(critical_priorities)) if critical_priorities else 0.0,
        "boundary_capacity_factors": {
            edge_id: min(factors) for edge_id, factors in boundary_capacity_factors.items()
        },
        "patch_der_caps": patch_der_caps,
        "battery_actions_by_node": {
            node_id: actions[0] for node_id, actions in battery_actions_by_node.items()
        },
    }


def _generator_is_unavailable(generator: _Generator, unavailable: set[str]) -> bool:
    if generator.resource_id in unavailable:
        return True
    for component in unavailable:
        bus_match = re.search(r"(?:bus_|_bus_)([^_]+)", component)
        if bus_match and bus_match.group(1) == generator.node_id:
            return True
    return False


def _edge_capacity(edge_capacity_kw: float | None, public_system_load_kw: float) -> tuple[float, str]:
    if edge_capacity_kw is not None and math.isfinite(edge_capacity_kw) and edge_capacity_kw > 0.0:
        return float(edge_capacity_kw), "published_active_power_rating"
    return max(float(public_system_load_kw), 1.0), "public_system_load_upper_bound"


def _polynomial_cost(generator: _Generator, dispatch_kw: float) -> float | None:
    if not generator.has_public_operating_cost:
        return None
    dispatch_mw = max(0.0, dispatch_kw) / 1000.0
    if dispatch_mw <= _EPS:
        return 0.0
    value = 0.0
    degree = len(generator.cost_coefficients) - 1
    for index, coefficient in enumerate(generator.cost_coefficients):
        value += coefficient * dispatch_mw ** (degree - index)
    return max(0.0, float(value))


def _solver_residual(result: OptimizeResult) -> float:
    residuals: list[float] = []
    eqlin = getattr(result, "eqlin", None)
    if eqlin is not None and getattr(eqlin, "residual", None) is not None:
        residuals.extend(abs(float(value)) for value in np.asarray(eqlin.residual).ravel())
    ineqlin = getattr(result, "ineqlin", None)
    if ineqlin is not None and getattr(ineqlin, "residual", None) is not None:
        residuals.extend(max(0.0, -float(value)) for value in np.asarray(ineqlin.residual).ravel())
    return max(residuals, default=0.0)


def _solve_scenario(
    *,
    method: str,
    grid: PublicGridData,
    named: Mapping[str, Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
    scenario: Mapping[str, Any],
    probability: float,
    upgrade_plan: Sequence[Mapping[str, Any]],
    generators: Sequence[_Generator],
    critical_nodes: set[str],
    critical_priorities: Mapping[str, float],
    system_trace_id: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    scenario_name = str(scenario["name"])
    nodes = {node.node_id: node for node in grid.nodes}
    total_load_kw = math.fsum(max(0.0, node.load_kw) for node in grid.nodes)
    critical_load_kw = math.fsum(max(0.0, nodes[node_id].load_kw) for node_id in critical_nodes)
    unavailable_edges, unavailable_generators, recourse_trace = _scenario_outages(
        grid, named, patch_values, scenario
    )
    pcc_sources = _public_pcc_sources(grid, total_load_kw)
    book = _VariableBook.create()

    for node in grid.nodes:
        book.add("served", node.node_id, 0.0, max(0.0, node.load_kw))
    for generator in generators:
        upper = 0.0 if _generator_is_unavailable(generator, unavailable_generators) else generator.capacity_kw
        # Unit commitment is not introduced into this LP.  Zero is the valid
        # off state and a dispatched unit remains within its public pmax.
        book.add("generator", generator.resource_id, 0.0, max(0.0, upper))

    edge_capacity_sources: dict[str, str] = {}
    effective_edge_capacities: dict[str, float] = {}
    for edge in grid.edges:
        capacity, source = _edge_capacity(edge.capacity_kw, total_load_kw)
        edge_capacity_sources[edge.edge_id] = source
        effective_capacity = capacity * float(
            recourse_trace["boundary_capacity_factors"].get(edge.edge_id, 1.0)
        )
        effective_edge_capacities[edge.edge_id] = effective_capacity
        if edge.edge_id in unavailable_edges or not edge.in_service:
            book.add("flow", edge.edge_id, 0.0, 0.0)
        else:
            book.add("flow", edge.edge_id, -effective_capacity, effective_capacity)

    assets_by_node: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for asset in upgrade_plan:
        assets_by_node[str(asset["anchor_node"])].append(asset)
        technology = str(asset["technology"])
        key = str(asset["asset_key"])
        if technology == "pv":
            upper = float(asset["installed_power_kw"]) if bool(scenario["pv_available"]) else 0.0
            book.add("pv", key, 0.0, max(0.0, upper))
        elif technology == "dispatchable_generation":
            book.add("candidate_generator", key, 0.0, max(0.0, float(asset["installed_power_kw"])))
        elif technology == "bess":
            power = max(0.0, float(asset["installed_power_kw"]))
            energy = max(0.0, float(asset["installed_energy_kwh"]))
            action = str(recourse_trace["battery_actions_by_node"].get(str(asset["anchor_node"]), "hold"))
            book.add("bess_discharge", key, 0.0, power if action == "discharge" else 0.0)
            book.add("bess_charge", key, 0.0, power if action == "charge" else 0.0)
            book.add("bess_soc_end", key, 0.0, energy)
    for source in pcc_sources:
        book.add("pcc_import", str(source["source_id"]), 0.0, max(0.0, float(source["capacity_kw"])))

    node_row = {node.node_id: index for index, node in enumerate(grid.nodes)}
    bess_assets = [asset for asset in upgrade_plan if str(asset["technology"]) == "bess"]
    equality_count = len(grid.nodes) + len(bess_assets)
    a_eq = lil_matrix((equality_count, len(book.names)), dtype=float)
    b_eq = np.zeros(equality_count, dtype=float)

    for node in grid.nodes:
        row = node_row[node.node_id]
        a_eq[row, book.at("served", node.node_id)] = -1.0
    for generator in generators:
        a_eq[node_row[generator.node_id], book.at("generator", generator.resource_id)] += 1.0
    for edge in grid.edges:
        position = book.at("flow", edge.edge_id)
        a_eq[node_row[edge.source], position] -= 1.0
        a_eq[node_row[edge.target], position] += 1.0
    for source in pcc_sources:
        a_eq[node_row[str(source["node_id"])], book.at("pcc_import", str(source["source_id"]))] += 1.0

    for asset in upgrade_plan:
        key = str(asset["asset_key"])
        node_row_index = node_row[str(asset["anchor_node"])]
        technology = str(asset["technology"])
        if technology == "pv":
            a_eq[node_row_index, book.at("pv", key)] += 1.0
        elif technology == "dispatchable_generation":
            a_eq[node_row_index, book.at("candidate_generator", key)] += 1.0
        elif technology == "bess":
            a_eq[node_row_index, book.at("bess_discharge", key)] += 1.0
            a_eq[node_row_index, book.at("bess_charge", key)] -= 1.0

    operational_rows: list[np.ndarray] = []
    operational_rhs: list[float] = []
    initial_bess_soc: dict[str, float] = {}
    for offset, asset in enumerate(bess_assets, start=len(grid.nodes)):
        key = str(asset["asset_key"])
        initial_soc = float(asset["installed_energy_kwh"]) * min(
            _bounded(asset.get("bess_reserve_target", 0.0)),
            _bounded(asset.get("bess_soc_target", 0.0)),
        )
        initial_bess_soc[key] = initial_soc
        a_eq[offset, book.at("bess_soc_end", key)] = 1.0
        a_eq[offset, book.at("bess_charge", key)] = -1.0
        a_eq[offset, book.at("bess_discharge", key)] = 1.0
        b_eq[offset] = initial_soc
        if bool(scenario["restoration_mode"]):
            row = np.zeros(len(book.names), dtype=float)
            row[book.at("bess_soc_end", key)] = -1.0
            operational_rows.append(row)
            operational_rhs.append(-initial_soc)

    for patch_cap in recourse_trace["patch_der_caps"]:
        patch_nodes = set(patch_cap["node_ids"])
        row = np.zeros(len(book.names), dtype=float)
        for generator in generators:
            if generator.node_id in patch_nodes:
                row[book.at("generator", generator.resource_id)] += 1.0
        for asset in upgrade_plan:
            if str(asset["anchor_node"]) not in patch_nodes:
                continue
            key = str(asset["asset_key"])
            technology = str(asset["technology"])
            if technology == "pv":
                row[book.at("pv", key)] += 1.0
            elif technology == "dispatchable_generation":
                row[book.at("candidate_generator", key)] += 1.0
            elif technology == "bess":
                row[book.at("bess_discharge", key)] += 1.0
        if np.any(row):
            operational_rows.append(row)
            operational_rhs.append(float(patch_cap["dispatch_cap_kw"]))

    base_a_ub = csr_matrix(np.vstack(operational_rows)) if operational_rows else None
    base_b_ub = np.asarray(operational_rhs, dtype=float) if operational_rhs else None
    a_eq_csr = a_eq.tocsr()

    critical_positions = [
        book.at("served", node_id)
        for node_id in sorted(critical_nodes)
        if nodes[node_id].load_kw > _EPS
    ]
    if critical_positions:
        critical_objective = np.zeros(len(book.names), dtype=float)
        for node_id in sorted(critical_nodes):
            if nodes[node_id].load_kw > _EPS:
                critical_objective[book.at("served", node_id)] = -(
                    1.0 + _bounded(critical_priorities.get(node_id, 0.0))
                )
        priority_result = linprog(
            critical_objective,
            A_ub=base_a_ub,
            b_ub=base_b_ub,
            A_eq=a_eq_csr,
            b_eq=b_eq,
            bounds=book.bounds,
            method="highs",
        )
        if not priority_result.success:
            return {
                "projection_status": "failed",
                "scenario": scenario_name,
                "failure_reason": str(priority_result.message),
                "runtime_seconds": time.perf_counter() - started,
            }
        best_critical_served = math.fsum(float(priority_result.x[position]) for position in critical_positions)
        critical_floor = max(0.0, best_critical_served - max(_PROJECTION_TOLERANCE, critical_load_kw * 1e-9))
        floor_row = lil_matrix((1, len(book.names)), dtype=float)
        for position in critical_positions:
            floor_row[0, position] = -1.0
        if base_a_ub is None:
            stage_two_a_ub = floor_row.tocsr()
            stage_two_b_ub = np.asarray([-critical_floor], dtype=float)
        else:
            stage_two_a_ub = vstack([base_a_ub, floor_row.tocsr()], format="csr")
            stage_two_b_ub = np.concatenate([base_b_ub, np.asarray([-critical_floor])])
    else:
        priority_result = None
        stage_two_a_ub = base_a_ub
        stage_two_b_ub = base_b_ub

    objective = np.zeros(len(book.names), dtype=float)
    for node in grid.nodes:
        objective[book.at("served", node.node_id)] = -1.0
    for generator in generators:
        hint = 0.0
        if generator.has_public_operating_cost and len(generator.cost_coefficients) >= 2:
            hint = max(0.0, generator.cost_coefficients[-2])
        objective[book.at("generator", generator.resource_id)] = 1e-9 * (1.0 + hint)
    for asset in upgrade_plan:
        key = str(asset["asset_key"])
        technology = str(asset["technology"])
        if technology == "pv":
            objective[book.at("pv", key)] = 1e-9
        elif technology == "dispatchable_generation":
            objective[book.at("candidate_generator", key)] = 1e-9
        elif technology == "bess":
            objective[book.at("bess_discharge", key)] = 2e-9
            objective[book.at("bess_charge", key)] = 2e-9
    for source in pcc_sources:
        objective[book.at("pcc_import", str(source["source_id"]))] = 1e-9

    result = linprog(
        objective,
        A_ub=stage_two_a_ub,
        b_ub=stage_two_b_ub,
        A_eq=a_eq_csr,
        b_eq=b_eq,
        bounds=book.bounds,
        method="highs",
    )
    runtime = time.perf_counter() - started
    if not result.success:
        return {
            "projection_status": "failed",
            "scenario": scenario_name,
            "failure_reason": str(result.message),
            "runtime_seconds": runtime,
        }
    residual = _solver_residual(result)
    if residual > _PROJECTION_TOLERANCE:
        return {
            "projection_status": "failed",
            "scenario": scenario_name,
            "failure_reason": f"HiGHS projection residual {residual:.6g} exceeds {_PROJECTION_TOLERANCE:.6g}",
            "runtime_seconds": runtime,
        }

    served_by_node = {node_id: float(result.x[book.at("served", node_id)]) for node_id in nodes}
    total_served_kw = math.fsum(served_by_node.values())
    critical_served_kw = math.fsum(served_by_node[node_id] for node_id in critical_nodes)
    total_ens = max(0.0, total_load_kw - total_served_kw)
    critical_ens = max(0.0, critical_load_kw - critical_served_kw)
    max_node_unserved = max(
        (
            max(0.0, 1.0 - served_by_node[node.node_id] / node.load_kw)
            for node in grid.nodes
            if node.load_kw > _EPS
        ),
        default=0.0,
    )
    critical_infra_hours = sum(
        1
        for node_id in critical_nodes
        if nodes[node_id].load_kw - served_by_node[node_id] > _PROJECTION_TOLERANCE
    )
    generator_dispatch = {
        generator.resource_id: float(result.x[book.at("generator", generator.resource_id)])
        for generator in generators
    }
    existing_dispatch_kw = math.fsum(generator_dispatch.values())
    public_operating_cost = 0.0
    covered_dispatch_kw = 0.0
    for generator in generators:
        dispatch = generator_dispatch[generator.resource_id]
        cost = _polynomial_cost(generator, dispatch)
        if cost is not None:
            public_operating_cost += cost
            covered_dispatch_kw += dispatch

    pv_dispatch_kw = math.fsum(
        float(result.x[book.at("pv", str(asset["asset_key"]))])
        for asset in upgrade_plan
        if str(asset["technology"]) == "pv"
    )
    candidate_generator_dispatch_kw = math.fsum(
        float(result.x[book.at("candidate_generator", str(asset["asset_key"]))])
        for asset in upgrade_plan
        if str(asset["technology"]) == "dispatchable_generation"
    )
    bess_discharge_kw = math.fsum(
        float(result.x[book.at("bess_discharge", str(asset["asset_key"]))]) for asset in bess_assets
    )
    bess_charge_kw = math.fsum(
        float(result.x[book.at("bess_charge", str(asset["asset_key"]))]) for asset in bess_assets
    )
    pcc_import_kw = math.fsum(
        float(result.x[book.at("pcc_import", str(source["source_id"]))]) for source in pcc_sources
    )
    total_supply_dispatch_kw = (
        existing_dispatch_kw + pv_dispatch_kw + candidate_generator_dispatch_kw + bess_discharge_kw + pcc_import_kw
    )
    boundary_flow_kw = math.fsum(
        abs(float(result.x[book.at("flow", edge_id)]))
        for edge_id in recourse_trace["boundary_edge_ids"]
        if ("flow", edge_id) in book.positions
    )
    projected_der_fraction = (
        (existing_dispatch_kw + pv_dispatch_kw + candidate_generator_dispatch_kw + bess_discharge_kw)
        / max(total_load_kw, _EPS)
    )
    projected_tie_fraction = boundary_flow_kw / max(
        math.fsum(
            effective_edge_capacities.get(edge_id, 0.0)
            for edge_id in recourse_trace["boundary_edge_ids"]
        ),
        _EPS,
    )
    final_bess_soc = {
        str(asset["asset_key"]): float(result.x[book.at("bess_soc_end", str(asset["asset_key"]))])
        for asset in bess_assets
    }
    scenario_trace_id = _trace_id(
        "scenario",
        {
            "system": system_trace_id,
            "scenario": scenario_name,
            "out_edges": sorted(unavailable_edges),
            "out_generators": sorted(unavailable_generators),
        },
    )
    return {
        "projection_status": "completed",
        "method": method,
        "benchmark": grid.benchmark,
        "scenario": scenario_name,
        "scenario_probability": probability,
        "scenario_trace_id": scenario_trace_id,
        "system_trace_id": system_trace_id,
        "source_payload_ids": sorted(named),
        "source_patch_ids": sorted(
            str(payload["sc_cmpo"]["upgrade_patch"].get("patch_id", payload_name))
            for payload_name, payload in named.items()
        ),
        "source_contingencies": list(scenario["source_contingencies"]),
        "unavailable_edge_ids": sorted(unavailable_edges),
        "unavailable_generator_ids": sorted(unavailable_generators),
        "selected_patch_modes": recourse_trace["selected_modes"],
        "selected_battery_actions_by_node": recourse_trace["battery_actions_by_node"],
        "total_load_kwh": total_load_kw,
        "total_load_served_kwh": total_served_kw,
        "critical_load_kwh": critical_load_kw,
        "critical_load_served_kwh": critical_served_kw,
        "critical_energy_not_served_kwh": critical_ens,
        "total_energy_not_served_kwh": total_ens,
        "energy_not_served_kwh": total_ens,
        "critical_load_served_fraction": 1.0 if critical_load_kw <= _EPS else critical_served_kw / critical_load_kw,
        "fraction_customers_unserved_per_hour": 0.0 if total_load_kw <= _EPS else total_ens / total_load_kw,
        "max_node_load_unserved_fraction": max_node_unserved,
        "total_hours_critical_infrastructure_unserved": critical_infra_hours,
        "existing_generation_dispatch_kwh": existing_dispatch_kw,
        "pv_dispatch_kwh": pv_dispatch_kw,
        "dispatchable_upgrade_dispatch_kwh": candidate_generator_dispatch_kw,
        "bess_discharge_kwh": bess_discharge_kw,
        "bess_charge_kwh": bess_charge_kw,
        "bess_initial_soc_kwh": math.fsum(initial_bess_soc.values()),
        "bess_final_soc_kwh": math.fsum(final_bess_soc.values()),
        "restoration_non_depletion_satisfied": (
            not bool(scenario["restoration_mode"])
            or all(final_bess_soc[key] + _PROJECTION_TOLERANCE >= initial for key, initial in initial_bess_soc.items())
        ),
        "public_pcc_import_kwh": pcc_import_kw,
        "tie_pcc_flow_kwh": boundary_flow_kw,
        "consensus_tie_response_mean": recourse_trace["tie_target_mean"],
        "projected_tie_response_fraction": projected_tie_fraction,
        "consensus_der_commitment_mean": recourse_trace["der_commitment_mean"],
        "projected_der_commitment_fraction": projected_der_fraction,
        "consensus_critical_load_priority_mean": recourse_trace["critical_priority_mean"],
        "public_operating_cost": public_operating_cost,
        "public_operating_cost_covered_dispatch_kwh": covered_dispatch_kw,
        "total_supply_dispatch_kwh": total_supply_dispatch_kw,
        "public_operating_cost_coverage_fraction": (
            1.0 if total_supply_dispatch_kw <= _EPS else covered_dispatch_kw / total_supply_dispatch_kw
        ),
        "full_system_feasibility": True,
        "post_projection_violation": residual,
        "solver": "scipy.optimize.linprog(method='highs')",
        "solver_iterations": int(result.nit) + (int(priority_result.nit) if priority_result is not None else 0),
        "runtime_seconds": runtime,
        "published_edge_capacity_count": sum(
            source == "published_active_power_rating" for source in edge_capacity_sources.values()
        ),
        "fallback_edge_capacity_count": sum(
            source == "public_system_load_upper_bound" for source in edge_capacity_sources.values()
        ),
        "edge_capacity_policy": EDGE_CAPACITY_FALLBACK,
        "storage_accounting_scope": STORAGE_ACCOUNTING_SCOPE,
        "projection_scope": PROJECTION_SCOPE,
        "generator_bounds_enforced": True,
        "tie_line_capacity_bounds_enforced": True,
        "contingency_availability_enforced": True,
        "critical_node_priority_enforced": True,
        "island_balance_enforced": True,
        "battery_action_consistency_enforced": True,
    }


def evaluate_full_system(
    method: str,
    grid: PublicGridData,
    payloads: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
    consensus: Mapping[str, Any],
    patch_runtime_seconds: float = 0,
) -> dict[str, Any]:
    """Reconstruct, project, and score one complete public benchmark system.

    A failed or unresolved consensus returns only a failure record.  Likewise,
    any failed HiGHS scenario discards all partial scenario and system metrics,
    preventing incomplete reconstructions from entering comparison tables.
    """

    started = time.perf_counter()
    benchmark = grid.benchmark
    pretrace = _trace_id(
        "system",
        {
            "method": method,
            "benchmark": benchmark,
            "source_sha256": grid.source_sha256,
            "payloads": sorted(str(name) for name in payloads) if isinstance(payloads, Mapping) else len(payloads),
        },
    )
    if str(consensus.get("status", "")) != "completed" or not bool(consensus.get("converged", False)):
        return _failure(method, benchmark, "consensus", "consensus did not complete and converge", pretrace)
    unresolved = consensus.get("unresolved_conflicts", [])
    if unresolved:
        return _failure(method, benchmark, "consensus", f"unresolved consensus conflicts: {unresolved}", pretrace)
    try:
        consensus_tolerance = float(
            consensus.get("tolerance", consensus.get("convergence_tolerance", _PROJECTION_TOLERANCE))
        )
        initial_primal = float(consensus.get("primal_residual", 0.0) or 0.0)
        initial_dual = float(consensus.get("dual_residual", 0.0) or 0.0)
    except (TypeError, ValueError):
        return _failure(method, benchmark, "consensus", "consensus residual metadata is not numeric", pretrace)
    if (
        not math.isfinite(consensus_tolerance)
        or consensus_tolerance < 0.0
        or not math.isfinite(initial_primal)
        or not math.isfinite(initial_dual)
        or max(abs(initial_primal), abs(initial_dual)) > consensus_tolerance + _EPS
    ):
        return _failure(
            method,
            benchmark,
            "consensus",
            "consensus residual exceeds the recorded convergence tolerance",
            pretrace,
        )

    try:
        named = _named_payloads(payloads)
        _validate_grid(grid)
        values_by_name = {str(name): values for name, values in patch_values.items()}
        missing_values = sorted(set(named) - set(values_by_name))
        if missing_values:
            raise ValueError(f"missing reconstructed values for payloads: {missing_values}")
        normalized_values = {name: values_by_name[name] for name in named}
        if any(
            str(payload.get("sc_cmpo", {}).get("public_benchmark", "")) != benchmark
            for payload in named.values()
        ):
            raise ValueError("payload benchmark does not match PublicGridData benchmark")
        probabilities = scenario_probability_map(named)
        scenarios = _canonical_scenarios(named)
        if set(scenarios) != set(probabilities):
            raise ValueError("scenario metadata and probability map differ")
        critical_nodes = _critical_nodes(named, grid)
        critical_priorities = _critical_priority_by_node(named, normalized_values)
        upgrade_plan = _build_upgrade_plan(grid, named, normalized_values)
    except (KeyError, TypeError, ValueError) as exc:
        return _failure(method, benchmark, "input_validation", str(exc), pretrace)

    consensus_trace_id = str(consensus.get("consensus_trace_id") or consensus.get("trace_id") or "")
    if not consensus_trace_id:
        consensus_trace_id = _trace_id(
            "consensus",
            {
                "benchmark": benchmark,
                "values": consensus.get("consensus_values", {}),
                "iterations": consensus.get("iteration_count", 0),
                "primal": consensus.get("primal_residual", 0.0),
                "dual": consensus.get("dual_residual", 0.0),
            },
        )
    system_trace_id = _trace_id(
        "system",
        {
            "method": method,
            "benchmark": benchmark,
            "source_sha256": grid.source_sha256,
            "payloads": sorted(named),
            "consensus_trace_id": consensus_trace_id,
            "assets": [asset["asset_key"] for asset in upgrade_plan],
        },
    )
    generators = _existing_generators(grid)
    scenario_results: list[dict[str, Any]] = []
    for scenario_name in probabilities:
        scenario = scenarios[scenario_name]
        try:
            result = _solve_scenario(
                method=method,
                grid=grid,
                named=named,
                patch_values=normalized_values,
                scenario=scenario,
                probability=probabilities[scenario_name],
                upgrade_plan=upgrade_plan,
                generators=generators,
                critical_nodes=critical_nodes,
                critical_priorities=critical_priorities,
                system_trace_id=system_trace_id,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return _failure(
                method,
                benchmark,
                f"scenario_projection:{scenario_name}",
                str(exc),
                system_trace_id,
            )
        if result["projection_status"] != "completed":
            return _failure(
                method,
                benchmark,
                f"scenario_projection:{scenario_name}",
                str(result.get("failure_reason", "unknown HiGHS failure")),
                system_trace_id,
            )
        result["consensus_trace_id"] = consensus_trace_id
        scenario_results.append(result)

    projection_runtime = time.perf_counter() - started
    consensus_runtime = max(
        0.0,
        float(consensus.get("runtime_seconds", consensus.get("consensus_runtime_seconds", 0.0)) or 0.0),
    )
    patch_runtime = max(0.0, float(patch_runtime_seconds))
    end_to_end_runtime = patch_runtime + consensus_runtime + projection_runtime
    total_upgrade_cost = math.fsum(float(asset["installed_cost"]) for asset in upgrade_plan)
    expected_operating_cost = math.fsum(
        float(row["scenario_probability"]) * float(row["public_operating_cost"])
        for row in scenario_results
    )
    worst_operating_cost = max((float(row["public_operating_cost"]) for row in scenario_results), default=0.0)
    expected_critical_ens = math.fsum(
        float(row["scenario_probability"]) * float(row["critical_energy_not_served_kwh"])
        for row in scenario_results
    )
    expected_total_ens = math.fsum(
        float(row["scenario_probability"]) * float(row["total_energy_not_served_kwh"])
        for row in scenario_results
    )
    expected_critical_served = math.fsum(
        float(row["scenario_probability"]) * float(row["critical_load_served_kwh"])
        for row in scenario_results
    )
    expected_critical_load = math.fsum(
        float(row["scenario_probability"]) * float(row["critical_load_kwh"])
        for row in scenario_results
    )
    expected_critical_infra_hours = math.fsum(
        float(row["scenario_probability"]) * float(row["total_hours_critical_infrastructure_unserved"])
        for row in scenario_results
    )
    covered_dispatch = math.fsum(
        float(row["scenario_probability"]) * float(row["public_operating_cost_covered_dispatch_kwh"])
        for row in scenario_results
    )
    total_dispatch = math.fsum(
        float(row["scenario_probability"]) * float(row["total_supply_dispatch_kwh"])
        for row in scenario_results
    )
    public_cost_coverage = 1.0 if total_dispatch <= _EPS else covered_dispatch / total_dispatch
    primal_residual = max(0.0, float(consensus.get("primal_residual", 0.0) or 0.0))
    dual_residual = max(0.0, float(consensus.get("dual_residual", 0.0) or 0.0))
    consensus_residual = max(primal_residual, dual_residual)
    full_feasibility = all(bool(row["full_system_feasibility"]) for row in scenario_results)
    cost_documented = math.fsum(
        float(asset["installed_cost"]) for asset in upgrade_plan if bool(asset["public_cost_documented"])
    )
    upgrade_cost_coverage = 1.0 if total_upgrade_cost <= _EPS else cost_documented / total_upgrade_cost
    metrics = {
        "method": method,
        "benchmark": benchmark,
        "system_trace_id": system_trace_id,
        "consensus_trace_id": consensus_trace_id,
        "source_payload_ids": sorted(named),
        "source_patch_ids": sorted(
            str(payload["sc_cmpo"]["upgrade_patch"].get("patch_id", payload_name))
            for payload_name, payload in named.items()
        ),
        "public_source_path": grid.source_path,
        "public_source_sha256": grid.source_sha256,
        "public_source_version": grid.source_version,
        "public_source_url": grid.source_url,
        "payload_count": len(named),
        "scenario_count": len(scenario_results),
        "scenario_probability_sum": math.fsum(probabilities.values()),
        "total_upgrade_cost": total_upgrade_cost,
        "expected_operating_cost": expected_operating_cost,
        "risk_adjusted_cost": total_upgrade_cost + expected_operating_cost + RISK_WEIGHT * worst_operating_cost,
        "risk_adjusted_cost_formula": (
            "deduplicated upgrade cost + expected source-covered operating cost + "
            "0.25 * worst-scenario source-covered operating cost"
        ),
        "critical_energy_not_served_kwh": expected_critical_ens,
        "total_energy_not_served_kwh": expected_total_ens,
        "total_energy_not_served": expected_total_ens,
        "unweighted_critical_energy_not_served_kwh": math.fsum(
            float(row["critical_energy_not_served_kwh"]) for row in scenario_results
        ),
        "unweighted_total_energy_not_served_kwh": math.fsum(
            float(row["total_energy_not_served_kwh"]) for row in scenario_results
        ),
        "max_fraction_customers_unserved_per_hour": max(
            (float(row["fraction_customers_unserved_per_hour"]) for row in scenario_results),
            default=0.0,
        ),
        "max_node_load_unserved_fraction": max(
            (float(row["max_node_load_unserved_fraction"]) for row in scenario_results),
            default=0.0,
        ),
        "total_hours_critical_infrastructure_unserved": sum(
            int(row["total_hours_critical_infrastructure_unserved"]) for row in scenario_results
        ),
        "expected_critical_infrastructure_unserved_hours": expected_critical_infra_hours,
        "critical_load_served_fraction": (
            1.0 if expected_critical_load <= _EPS else expected_critical_served / expected_critical_load
        ),
        "full_system_feasibility": full_feasibility,
        "feasibility_after_repair": float(full_feasibility),
        "consensus_iterations": int(consensus.get("iteration_count", 0) or 0),
        "consensus_iteration_count": int(consensus.get("iteration_count", 0) or 0),
        "consensus_primal_residual": primal_residual,
        "consensus_dual_residual": dual_residual,
        "consensus_residual": consensus_residual,
        "unresolved_conflict_count": len(consensus.get("unresolved_conflicts", [])),
        "time_to_good_solution": end_to_end_runtime if full_feasibility else -1.0,
        "end_to_end_runtime": end_to_end_runtime,
        "end_to_end_runtime_seconds": end_to_end_runtime,
        "wall_clock_runtime_seconds": end_to_end_runtime,
        "runtime_seconds": end_to_end_runtime,
        "patch_runtime_seconds": patch_runtime,
        "consensus_runtime_seconds": consensus_runtime,
        "full_system_projection_runtime_seconds": projection_runtime,
        "upgrade_asset_count": len(upgrade_plan),
        "upgrade_cost_scored_once_per_physical_asset": True,
        "public_upgrade_cost_coverage_fraction": upgrade_cost_coverage,
        "public_operating_cost_coverage_fraction": public_cost_coverage,
        "expected_operating_cost_is_source_covered_lower_bound": public_cost_coverage < 1.0 - _EPS,
        "patch_metrics_aggregated": False,
        "comparison_unit": "one reconstructed complete public benchmark system",
        "customer_fraction_scope": "public active-load-weighted customer proxy; no customer-count data were invented",
        "projection_scope": PROJECTION_SCOPE,
        "edge_capacity_policy": EDGE_CAPACITY_FALLBACK,
        "storage_accounting_scope": STORAGE_ACCOUNTING_SCOPE,
    }
    artifact_trace = {
        "system_trace_id": system_trace_id,
        "consensus_trace_id": consensus_trace_id,
        "source_payload_ids": sorted(named),
        "scenario_trace_ids": [row["scenario_trace_id"] for row in scenario_results],
        "upgrade_asset_keys": [asset["asset_key"] for asset in upgrade_plan],
        "public_grid_sha256": grid.source_sha256,
    }
    return {
        "status": "completed",
        "method": method,
        "benchmark": benchmark,
        "system_metrics": metrics,
        "scenario_results": scenario_results,
        "upgrade_plan": upgrade_plan,
        "artifact_trace": artifact_trace,
    }


def evaluate_full_system_heldout(
    method: str,
    grid: PublicGridData,
    payloads: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
    consensus: Mapping[str, Any],
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Project unused public N-1 records over the reconstructed complete system."""

    if limit <= 0:
        raise ValueError("held-out contingency limit must be positive")
    benchmark = grid.benchmark
    trace_id = _trace_id(
        "heldout",
        {
            "method": method,
            "benchmark": benchmark,
            "limit": limit,
            "consensus": consensus.get("run_id", ""),
        },
    )
    if str(consensus.get("status", "")) != "completed" or not bool(
        consensus.get("converged", False)
    ):
        return _failure(method, benchmark, "heldout_consensus", "consensus did not converge", trace_id)
    try:
        named = _named_payloads(payloads)
        _validate_grid(grid)
        normalized_values = {name: patch_values[name] for name in named}
        canonical = _canonical_scenarios(named)
        recourse_name = "normal" if "normal" in canonical else sorted(canonical)[0]
        recourse_template = canonical[recourse_name]
        critical_nodes = _critical_nodes(named, grid)
        critical_priorities = _critical_priority_by_node(named, normalized_values)
        upgrade_plan = _build_upgrade_plan(grid, named, normalized_values)
        generators = _existing_generators(grid)
    except (KeyError, TypeError, ValueError) as exc:
        return _failure(method, benchmark, "heldout_input_validation", str(exc), trace_id)

    used_tokens: set[str] = set()
    for payload in named.values():
        for scenario in _scenario_records(payload):
            used_tokens.update(
                token.strip()
                for token in re.split(r"[;,]", str(scenario.get("source_contingency", "")))
                if token.strip()
            )
    candidates = [
        contingency
        for contingency in sorted(
            grid.contingencies,
            key=lambda item: (item.component_kind, item.contingency_id, item.component_id),
        )
        if contingency.component_kind in {"branch", "transformer", "generator"}
        and contingency.contingency_id not in used_tokens
        and contingency.component_id not in used_tokens
    ][:limit]
    if not candidates:
        return {
            "status": "completed",
            "method": method,
            "benchmark": benchmark,
            "heldout_summary": {
                "method": method,
                "benchmark": benchmark,
                "heldout_count": 0,
                "heldout_data_available": False,
                "full_system_feasibility": True,
            },
            "contingency_results": [],
        }

    probability = 1.0 / len(candidates)
    rows: list[dict[str, Any]] = []
    for contingency in candidates:
        scenario = {
            **recourse_template,
            "name": recourse_name,
            "source_contingencies": [contingency.contingency_id],
            "override_source_contingencies": True,
        }
        try:
            result = _solve_scenario(
                method=method,
                grid=grid,
                named=named,
                patch_values=normalized_values,
                scenario=scenario,
                probability=probability,
                upgrade_plan=upgrade_plan,
                generators=generators,
                critical_nodes=critical_nodes,
                critical_priorities=critical_priorities,
                system_trace_id=trace_id,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return _failure(
                method,
                benchmark,
                f"heldout_projection:{contingency.contingency_id}",
                str(exc),
                trace_id,
            )
        if result.get("projection_status") != "completed":
            return _failure(
                method,
                benchmark,
                f"heldout_projection:{contingency.contingency_id}",
                str(result.get("failure_reason", "full-system held-out projection failed")),
                trace_id,
            )
        rows.append(
            {
                **result,
                "heldout_contingency_id": contingency.contingency_id,
                "heldout_component_kind": contingency.component_kind,
                "heldout_component_id": contingency.component_id,
                "heldout_source_record": contingency.source_record,
                "heldout_recourse_template": recourse_name,
            }
        )

    expected_critical_ens = math.fsum(
        probability * float(row["critical_energy_not_served_kwh"]) for row in rows
    )
    expected_total_ens = math.fsum(
        probability * float(row["total_energy_not_served_kwh"]) for row in rows
    )
    expected_critical_served = math.fsum(
        probability * float(row["critical_load_served_kwh"]) for row in rows
    )
    expected_critical_load = math.fsum(
        probability * float(row["critical_load_kwh"]) for row in rows
    )
    summary = {
        "method": method,
        "benchmark": benchmark,
        "heldout_count": len(rows),
        "heldout_data_available": True,
        "heldout_probability_sum": math.fsum(probability for _ in rows),
        "critical_energy_not_served_kwh": expected_critical_ens,
        "total_energy_not_served_kwh": expected_total_ens,
        "critical_load_served_fraction": (
            1.0
            if expected_critical_load <= _EPS
            else expected_critical_served / expected_critical_load
        ),
        "max_fraction_customers_unserved_per_hour": max(
            float(row["fraction_customers_unserved_per_hour"]) for row in rows
        ),
        "total_hours_critical_infrastructure_unserved": sum(
            int(row["total_hours_critical_infrastructure_unserved"]) for row in rows
        ),
        "full_system_feasibility": all(bool(row["full_system_feasibility"]) for row in rows),
        "projection_scope": PROJECTION_SCOPE,
        "heldout_rule": (
            "deterministic unused public N-1 records, equal weighted, projected over the complete public "
            "topology using the normal recourse block and the reconstructed consensus upgrade plan"
        ),
        "heldout_trace_id": trace_id,
    }
    return {
        "status": "completed",
        "method": method,
        "benchmark": benchmark,
        "heldout_summary": summary,
        "contingency_results": rows,
    }
