"""True fixed-upgrade recourse for public IEEE 123 IRC-CMPO portfolios.

The master decisions are fixed through equal lower/upper bounds.  Patch service
and dispatch are then optimized independently by SciPy SLSQP and HiGHS MILP,
reconciled with the established overlap consensus, and projected over the full
public feeder.  This module deliberately does not import or call
``_fractions_to_values``.
"""

from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp, minimize

from cmpo.full_system_dispatch import evaluate_full_system, evaluate_full_system_heldout
from cmpo.overlap_consensus import reconstruct_patch_values, run_method_consensus
from cmpo.upgrade_planning import PublicGridData

if TYPE_CHECKING:
    from cmpo.irc_cmpo_master import IRCAsset


FIXED_UPGRADE_VARIABLES = frozenset(
    {
        "upgrade_select_pv",
        "upgrade_select_bess",
        "upgrade_select_dispatchable",
        "pv_capacity_fraction",
        "bess_energy_fraction",
        "bess_power_fraction",
        "dispatchable_capacity_fraction",
    }
)
TECHNOLOGY_VARIABLES = {
    "pv": ("upgrade_select_pv", "pv_capacity_fraction"),
    "bess": ("upgrade_select_bess", "bess_energy_fraction", "bess_power_fraction"),
    "dispatchable_generation": (
        "upgrade_select_dispatchable",
        "dispatchable_capacity_fraction",
    ),
}
_TOLERANCE = 1e-7


@dataclass(frozen=True)
class FixedPatch:
    payload_name: str
    anchor_node: str
    payload: dict[str, Any]
    fixed_values: dict[str, float]
    fixed_by: str = "exact_variable_bounds"
    used_fraction_completion: bool = False


@dataclass(frozen=True)
class AssetScenarioEffect:
    asset_key: str
    measurable: bool
    affected_scenarios: tuple[str, ...]
    maximum_ens_reduction_kwh: float
    metric_deltas: dict[str, float]


@dataclass(frozen=True)
class FixedUpgradeRecourseResult:
    selected_asset_keys: tuple[str, ...]
    critical_ens: float
    total_ens: float
    maximum_customers_unserved: float
    critical_infrastructure_outage_hours: float
    critical_load_served_fraction: float
    operating_cost: float
    upgrade_cost: float
    heldout_critical_ens: float
    heldout_total_ens: float
    feasibility: bool
    solver_status: str
    selected_solver: str
    runtime_seconds: float
    patch_count: int
    training_scenario_count: int
    heldout_contingency_count: int
    consensus_algorithm: str
    projection_scope: str
    consensus_trace_id: str
    system_trace_id: str
    heldout_trace_id: str
    solver_paths: tuple[str, ...]
    open_dss_replay: str

    @property
    def metric_signature(self) -> tuple[float, ...]:
        return (
            self.critical_ens,
            self.total_ens,
            self.maximum_customers_unserved,
            self.critical_infrastructure_outage_hours,
            self.critical_load_served_fraction,
            self.operating_cost,
            self.upgrade_cost,
            self.heldout_critical_ens,
            self.heldout_total_ens,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_asset_keys": list(self.selected_asset_keys),
            "critical_ens": self.critical_ens,
            "total_ens": self.total_ens,
            "maximum_customers_unserved": self.maximum_customers_unserved,
            "critical_infrastructure_outage_hours": self.critical_infrastructure_outage_hours,
            "critical_load_served_fraction": self.critical_load_served_fraction,
            "operating_cost": self.operating_cost,
            "upgrade_cost": self.upgrade_cost,
            "heldout_critical_ens": self.heldout_critical_ens,
            "heldout_total_ens": self.heldout_total_ens,
            "feasibility": self.feasibility,
            "solver_status": self.solver_status,
            "selected_solver": self.selected_solver,
            "runtime_seconds": self.runtime_seconds,
            "patch_count": self.patch_count,
            "training_scenario_count": self.training_scenario_count,
            "heldout_contingency_count": self.heldout_contingency_count,
            "consensus_algorithm": self.consensus_algorithm,
            "projection_scope": self.projection_scope,
            "consensus_trace_id": self.consensus_trace_id,
            "system_trace_id": self.system_trace_id,
            "heldout_trace_id": self.heldout_trace_id,
            "solver_paths": list(self.solver_paths),
            "open_dss_replay": self.open_dss_replay,
        }


@dataclass
class FixedRecourseCache:
    """Cache exact fixed-patch solver results across portfolio evaluations."""

    solutions: dict[tuple[Any, ...], dict[str, float]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    @staticmethod
    def key(record: FixedPatch, backend: str) -> tuple[Any, ...]:
        return (
            record.payload_name,
            backend,
            tuple(sorted((name, round(float(value), 12)) for name, value in record.fixed_values.items())),
        )

    def solve(self, record: FixedPatch, backend: str) -> dict[str, float]:
        key = self.key(record, backend)
        if key in self.solutions:
            self.hits += 1
            return dict(self.solutions[key])
        values, _status = _solve_patch(record, backend)
        self.solutions[key] = dict(values)
        self.misses += 1
        return dict(values)


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    nodes = payload["sc_cmpo"].get("patch_public_nodes", ())
    if nodes:
        return sorted(
            (
                (
                    float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                    float(node.get("load_kw", 0.0)),
                    str(node["node_id"]),
                )
                for node in nodes
            ),
            key=lambda row: (-row[0], -row[1], row[2]),
        )[0][2]
    return sorted(str(node) for node in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])[0]


def fix_upgrade_bounds(
    payloads: Mapping[str, Mapping[str, Any]],
    assets: Sequence[IRCAsset],
    selected_asset_keys: Sequence[str] | set[str],
    *,
    capacity_fractions: Mapping[str, float] | None = None,
) -> dict[str, FixedPatch]:
    """Copy payloads and fix every physical upgrade with exact equal bounds."""

    selected = {str(key) for key in selected_asset_keys}
    catalog = {asset.asset_key: asset for asset in assets}
    unknown = selected - set(catalog)
    if unknown:
        raise ValueError(f"portfolio references unknown public assets: {sorted(unknown)}")
    fractions = {str(key): float(value) for key, value in (capacity_fractions or {}).items()}
    if set(fractions) - selected:
        raise ValueError("capacity fractions may only be supplied for selected assets")
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in fractions.values()):
        raise ValueError("capacity fractions must be finite values in [0, 1]")
    by_anchor: dict[str, dict[str, IRCAsset]] = {}
    for asset in assets:
        by_anchor.setdefault(asset.anchor_node, {})[asset.technology] = asset

    result: dict[str, FixedPatch] = {}
    for name, source_payload in sorted(payloads.items()):
        payload = copy.deepcopy(dict(source_payload))
        anchor = _physical_anchor(payload)
        if anchor not in by_anchor:
            raise ValueError(f"patch {name} has no matching physical upgrade anchor")
        fixed_values: dict[str, float] = {}
        for technology, variable_names in TECHNOLOGY_VARIABLES.items():
            asset = by_anchor[anchor][technology]
            is_selected = asset.asset_key in selected
            capacity = fractions.get(asset.asset_key, 1.0) if is_selected else 0.0
            fixed_values[variable_names[0]] = float(is_selected)
            for variable_name in variable_names[1:]:
                fixed_values[variable_name] = capacity
        specs = {str(row["name"]): row for row in payload["variables"]}
        missing = FIXED_UPGRADE_VARIABLES - set(specs)
        if missing:
            raise ValueError(f"patch {name} lacks fixed-upgrade variables: {sorted(missing)}")
        for variable_name, value in fixed_values.items():
            specs[variable_name]["lower_bound"] = value
            specs[variable_name]["upper_bound"] = value
            specs[variable_name]["bounds"] = [value, value]
            specs[variable_name]["fixed_parameter_value"] = value
        result[str(name)] = FixedPatch(str(name), anchor, payload, fixed_values)
    return result


def _scenario_capacity_fraction(payload: Mapping[str, Any], fixed: Mapping[str, float], scenario: Mapping[str, Any]) -> float:
    options = {str(row["technology"]): row for row in payload["sc_cmpo"]["upgrade_options"]}
    patch = payload["sc_cmpo"]["upgrade_patch"]
    load = max(float(scenario.get("load_requirement_kw", patch["load_kw"])), 1e-12)
    capacity = (
        float(patch.get("existing_generation_kw", 0.0))
        if bool(scenario.get("existing_generation_available", True))
        else 0.0
    )
    if bool(scenario.get("pv_available", True)):
        capacity += fixed["pv_capacity_fraction"] * float(options["pv"]["capacity_kw"])
    capacity += fixed["bess_power_fraction"] * float(options["bess"]["power_kw"])
    capacity += fixed["dispatchable_capacity_fraction"] * float(
        options["dispatchable_generation"]["capacity_kw"]
    )
    return max(0.0, capacity / load)


def _solve_service_slsqp(capacity: float, pcc_available: bool, load_kw: float) -> tuple[np.ndarray, dict[str, Any]]:
    # x = DER dispatch, PCC dispatch, served fraction, shed fraction.
    tie_cap = 1.0 if pcc_available else 0.0
    bounds = Bounds(np.zeros(4), np.array([capacity, tie_cap, 1.0, 1.0]))
    constraints = (
        {"type": "eq", "fun": lambda x: x[2] + x[3] - 1.0},
        {"type": "ineq", "fun": lambda x: x[0] + x[1] - x[2]},
    )
    start = np.array(
        [min(capacity, 1.0), min(tie_cap, max(0.0, 1.0 - capacity)), min(1.0, capacity + tie_cap), max(0.0, 1.0 - capacity - tie_cap)]
    )
    result = minimize(
        lambda x: load_kw * (1.0 - x[2]) + 1e-6 * load_kw * (x[0] ** 2 + x[1] ** 2),
        start,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 100, "ftol": 1e-10, "disp": False},
    )
    if result.x is None or np.any(~np.isfinite(result.x)):
        raise RuntimeError(f"SLSQP recourse returned no finite dispatch: {result.message}")
    vector = np.asarray(result.x, dtype=float)
    feasible = (
        abs(vector[2] + vector[3] - 1.0) <= _TOLERANCE
        and vector[2] <= vector[0] + vector[1] + _TOLERANCE
    )
    return vector, {
        "success": bool(result.success) and feasible,
        "status": int(result.status),
        "message": str(result.message),
        "iterations": int(result.nit),
    }


def _solve_service_milp(capacity: float, pcc_available: bool, load_kw: float) -> tuple[np.ndarray, dict[str, Any]]:
    # Exact piecewise-linear form of the service/shedding recourse block.
    objective = np.array([1e-6 * load_kw, 1e-6 * load_kw, -load_kw, 0.0])
    matrix = np.array([[0.0, 0.0, 1.0, 1.0], [-1.0, -1.0, 1.0, 0.0]])
    constraint = LinearConstraint(matrix, np.array([1.0, -np.inf]), np.array([1.0, 0.0]))
    result = milp(
        objective,
        integrality=np.zeros(4),
        bounds=Bounds(np.zeros(4), np.array([capacity, float(pcc_available), 1.0, 1.0])),
        constraints=constraint,
        options={"presolve": True},
    )
    if not result.success or result.x is None or np.any(~np.isfinite(result.x)):
        raise RuntimeError(f"piecewise-linear MILP recourse failed: {result.message}")
    return np.asarray(result.x, dtype=float), {
        "success": True,
        "status": int(result.status),
        "message": str(result.message),
        "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
    }


def _base_values(fixed_patch: FixedPatch) -> dict[str, float]:
    payload = fixed_patch.payload
    values = {
        str(variable["name"]): float(variable["lower_bound"])
        for variable in payload["variables"]
    }
    values.update(fixed_patch.fixed_values)
    values.update(
        {
            "islanding_eligibility": 1.0,
            "base_mode_connected": 1.0,
            "base_mode_islanded": 0.0,
            "base_mode_restoration": 0.0,
            "bess_reserve_target": float(fixed_patch.fixed_values["bess_power_fraction"] > 0.0),
            "bess_soc_target": float(fixed_patch.fixed_values["bess_energy_fraction"] > 0.0),
            "critical_load_priority": 1.0,
            "tie_pcc_reserve_target": 1.0,
        }
    )
    return values


def _solve_patch(fixed_patch: FixedPatch, backend: str) -> tuple[dict[str, float], dict[str, Any]]:
    payload = fixed_patch.payload
    values = _base_values(fixed_patch)
    trace: list[dict[str, Any]] = []
    all_feasible = True
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = str(scenario["name"])
        load = float(scenario.get("load_requirement_kw", payload["sc_cmpo"]["upgrade_patch"]["load_kw"]))
        capacity = _scenario_capacity_fraction(payload, fixed_patch.fixed_values, scenario)
        if backend == "SLSQP nonlinear recourse":
            solution, status = _solve_service_slsqp(capacity, bool(scenario["pcc_available"]), load)
        elif backend == "piecewise-linear MILP recourse":
            solution, status = _solve_service_milp(capacity, bool(scenario["pcc_available"]), load)
        else:  # pragma: no cover - internal caller is closed over known paths
            raise ValueError(f"unknown recourse backend: {backend}")
        der, tie, served, shed = (float(value) for value in solution)
        desired_mode = "restoration" if bool(scenario.get("restoration_mode", False)) else (
            "islanded" if bool(scenario.get("forced_islanding", False)) else "connected"
        )
        for mode in ("connected", "islanded", "restoration"):
            values[f"mode_{mode}[{name}]"] = float(mode == desired_mode)
        action = "discharge" if not bool(scenario["pcc_available"]) and values["bess_power_fraction"] > 0.0 else "hold"
        for candidate in ("charge", "hold", "discharge"):
            values[f"battery_action_{candidate}[{name}]"] = float(candidate == action)
        values[f"der_commitment[{name}]"] = min(max(der, 0.0), 1.0)
        values[f"der_capacity_slack[{name}]"] = min(max(capacity - der, 0.0) / 3.0, 1.0)
        values[f"critical_load_service[{name}]"] = min(max(served, 0.0), 1.0)
        values[f"tie_pcc_response[{name}]"] = min(max(tie, 0.0), 1.0)
        values[f"load_shedding_allocation[{name}]"] = min(max(shed, 0.0), 1.0)
        all_feasible = all_feasible and bool(status["success"])
        trace.append({"scenario": name, "capacity_fraction": capacity, **status})
    return values, {"backend": backend, "feasible": all_feasible, "scenario_trace": trace}


def _consensus_and_projection(
    fixed: Mapping[str, FixedPatch],
    values: Mapping[str, Mapping[str, float]],
    grid: PublicGridData,
    backend: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, float | int]]]:
    views: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for name, record in sorted(fixed.items()):
        view = copy.deepcopy(record.payload)
        view["variables"] = [
            variable for variable in view["variables"] if str(variable["name"]) not in FIXED_UPGRADE_VARIABLES
        ]
        view["sc_cmpo"]["shared_first_stage_variables"] = [
            variable
            for variable in view["sc_cmpo"].get("shared_first_stage_variables", ())
            if str(variable) not in FIXED_UPGRADE_VARIABLES
        ]
        views[name] = view
        rows.append(
            {
                "payload_name": name,
                "method": backend,
                "runtime_seconds": 0.0,
                "solution_values": {
                    key: value for key, value in values[name].items() if key not in FIXED_UPGRADE_VARIABLES
                },
            }
        )
    consensus = run_method_consensus(views, rows)
    if consensus.get("status") != "completed" or not consensus.get("converged"):
        return consensus, {"status": "failed", "failure_reason": consensus.get("failure_reason", "consensus failed")}, {}
    reconstructed = reconstruct_patch_values(views, consensus["consensus_values"])
    for name, record in fixed.items():
        reconstructed[name].update(record.fixed_values)
    system = evaluate_full_system(
        backend,
        grid,
        {name: record.payload for name, record in fixed.items()},
        reconstructed,
        consensus,
    )
    return consensus, system, reconstructed


def evaluate_fixed_upgrade_recourse(
    payloads: Mapping[str, Mapping[str, Any]],
    assets: Sequence[IRCAsset],
    selected_asset_keys: Sequence[str],
    *,
    grid: PublicGridData,
    capacity_fractions: Mapping[str, float] | None = None,
    heldout_limit: int = 10,
    solver_cache: FixedRecourseCache | None = None,
) -> FixedUpgradeRecourseResult:
    """Evaluate a fixed public-catalog portfolio through both true recourse paths."""

    if len(payloads) != 12:
        raise ValueError(f"IEEE 123 true recourse requires 12 patches, found {len(payloads)}")
    scenario_counts = {len(payload["scenario_metadata"]["scenarios"]) for payload in payloads.values()}
    if scenario_counts != {8}:
        raise ValueError(f"IEEE 123 true recourse requires 8 common training scenarios, found {scenario_counts}")
    if heldout_limit != 10:
        raise ValueError("headline IEEE 123 true recourse requires exactly 10 held-out contingencies")
    started = time.perf_counter()
    fixed = fix_upgrade_bounds(
        payloads,
        assets,
        selected_asset_keys,
        capacity_fractions=capacity_fractions,
    )
    candidates: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, dict[str, float | int]]]] = []
    path_statuses: list[str] = []
    for backend in ("SLSQP nonlinear recourse", "piecewise-linear MILP recourse"):
        try:
            solved = {
                name: (
                    solver_cache.solve(record, backend)
                    if solver_cache is not None
                    else _solve_patch(record, backend)[0]
                )
                for name, record in fixed.items()
            }
            consensus, system, reconstructed = _consensus_and_projection(fixed, solved, grid, backend)
            if system.get("status") == "completed":
                candidates.append((backend, consensus, system, reconstructed))
                path_statuses.append(f"{backend}:completed")
            else:
                path_statuses.append(f"{backend}:failed:{system.get('failure_reason', '')}")
        except (RuntimeError, ValueError) as exc:
            path_statuses.append(f"{backend}:failed:{exc}")
    if not candidates:
        raise RuntimeError("no fixed-upgrade recourse solver produced a feasible full-system projection: " + " | ".join(path_statuses))

    def rank(candidate: tuple[str, dict[str, Any], dict[str, Any], dict[str, dict[str, float | int]]]) -> tuple[Any, ...]:
        metrics = candidate[2]["system_metrics"]
        return (
            not bool(metrics["full_system_feasibility"]),
            float(metrics["critical_energy_not_served_kwh"]),
            float(metrics["total_energy_not_served_kwh"]),
            float(metrics["max_fraction_customers_unserved_per_hour"]),
            float(metrics["expected_operating_cost"]),
            candidate[0],
        )

    backend, consensus, system, reconstructed = min(candidates, key=rank)
    heldout = evaluate_full_system_heldout(
        backend,
        grid,
        {name: record.payload for name, record in fixed.items()},
        reconstructed,
        consensus,
        limit=heldout_limit,
    )
    if heldout.get("status") != "completed":
        raise RuntimeError(f"held-out fixed-upgrade recourse failed: {heldout.get('failure_reason', '')}")
    metrics = system["system_metrics"]
    heldout_metrics = heldout["heldout_summary"]
    selected = set(str(key) for key in selected_asset_keys)
    fractions = capacity_fractions or {}
    upgrade_cost = math.fsum(
        asset.total_cost * float(fractions.get(asset.asset_key, 1.0))
        for asset in assets
        if asset.asset_key in selected
    )
    runtime = time.perf_counter() - started
    return FixedUpgradeRecourseResult(
        selected_asset_keys=tuple(sorted(selected)),
        critical_ens=float(metrics["critical_energy_not_served_kwh"]),
        total_ens=float(metrics["total_energy_not_served_kwh"]),
        maximum_customers_unserved=float(metrics["max_fraction_customers_unserved_per_hour"]),
        critical_infrastructure_outage_hours=float(metrics["expected_critical_infrastructure_unserved_hours"]),
        critical_load_served_fraction=float(metrics["critical_load_served_fraction"]),
        operating_cost=float(metrics["expected_operating_cost"]),
        upgrade_cost=upgrade_cost,
        heldout_critical_ens=float(heldout_metrics["critical_energy_not_served_kwh"]),
        heldout_total_ens=float(heldout_metrics["total_energy_not_served_kwh"]),
        feasibility=bool(metrics["full_system_feasibility"] and heldout_metrics["full_system_feasibility"]),
        solver_status="completed",
        selected_solver=backend,
        runtime_seconds=runtime,
        patch_count=12,
        training_scenario_count=8,
        heldout_contingency_count=int(heldout_metrics["heldout_count"]),
        consensus_algorithm="overlap_consensus_admm",
        projection_scope="full_system_active_power_projection",
        consensus_trace_id=str(metrics["consensus_trace_id"]),
        system_trace_id=str(metrics["system_trace_id"]),
        heldout_trace_id=str(heldout_metrics["heldout_trace_id"]),
        solver_paths=tuple(path_statuses),
        open_dss_replay="reported_separately_not_part_of_active_power_recourse",
    )


def portfolio_scenario_effects(
    payloads: Mapping[str, Mapping[str, Any]],
    assets: Sequence[IRCAsset],
) -> dict[str, AssetScenarioEffect]:
    """Prove every master asset changes public-scenario optimized service."""

    payload_by_anchor: dict[str, Mapping[str, Any]] = {}
    for payload in payloads.values():
        anchor = _physical_anchor(payload)
        current = payload_by_anchor.get(anchor)
        if current is None or float(payload["sc_cmpo"]["upgrade_patch"]["load_kw"]) > float(
            current["sc_cmpo"]["upgrade_patch"]["load_kw"]
        ):
            payload_by_anchor[anchor] = payload
    effects: dict[str, AssetScenarioEffect] = {}
    for asset in assets:
        payload = payload_by_anchor[asset.anchor_node]
        fixed_zero = {name: 0.0 for name in FIXED_UPGRADE_VARIABLES}
        technology_names = TECHNOLOGY_VARIABLES[asset.technology]
        fixed_asset = dict(fixed_zero)
        fixed_asset[technology_names[0]] = 1.0
        for name in technology_names[1:]:
            fixed_asset[name] = 1.0
        affected: list[str] = []
        maximum_reduction = 0.0
        for scenario in payload["scenario_metadata"]["scenarios"]:
            if bool(scenario.get("pcc_available", False)):
                continue
            load = float(scenario.get("load_requirement_kw", payload["sc_cmpo"]["upgrade_patch"]["load_kw"]))
            baseline_capacity = _scenario_capacity_fraction(payload, fixed_zero, scenario)
            asset_capacity = _scenario_capacity_fraction(payload, fixed_asset, scenario)
            baseline_ens = load * (1.0 - min(1.0, baseline_capacity))
            asset_ens = load * (1.0 - min(1.0, asset_capacity))
            reduction = baseline_ens - asset_ens
            if reduction > _TOLERANCE:
                affected.append(str(scenario["name"]))
                maximum_reduction = max(maximum_reduction, reduction)
        effects[asset.asset_key] = AssetScenarioEffect(
            asset_key=asset.asset_key,
            measurable=bool(affected),
            affected_scenarios=tuple(sorted(set(affected))),
            maximum_ens_reduction_kwh=maximum_reduction,
            metric_deltas={"total_ens_reduction_kwh": maximum_reduction},
        )
    return effects


__all__ = [
    "AssetScenarioEffect",
    "FixedPatch",
    "FixedRecourseCache",
    "FixedUpgradeRecourseResult",
    "evaluate_fixed_upgrade_recourse",
    "fix_upgrade_bounds",
    "portfolio_scenario_effects",
]
