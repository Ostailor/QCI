"""Ex-post unbalanced OpenDSS validation for IEEE 123 SC-CMPO plans.

The validator uses only the pinned public feeder and published equipment
ratings.  The optimization trace stores aggregate critical and noncritical
load service, so those exact totals are mapped proportionally within each
class while retaining every public load's phase connection and power factor.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from cmpo.ieee123_sc_cmpo_adapter import IEEE123SCMPOCase


_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ACValidationLimits:
    """Checkable ex-post AC limits and numerical balance tolerance."""

    minimum_voltage_pu: float = 0.95
    maximum_voltage_pu: float = 1.05
    maximum_equipment_loading_percent: float = 100.0
    absolute_balance_tolerance_kw: float = 0.1
    relative_balance_tolerance: float = 1e-4


def load_service_fractions(
    *,
    total_load_kw: float,
    critical_load_kw: float,
    total_served_kw: float,
    critical_served_kw: float,
) -> tuple[float, float]:
    """Return class-level fractions that reproduce both recorded totals."""

    values = (total_load_kw, critical_load_kw, total_served_kw, critical_served_kw)
    if any(not math.isfinite(value) or value < -_TOLERANCE for value in values):
        raise ValueError("load and service totals must be finite and nonnegative")
    noncritical_load = total_load_kw - critical_load_kw
    noncritical_served = total_served_kw - critical_served_kw
    if critical_load_kw > total_load_kw + _TOLERANCE:
        raise ValueError("critical load exceeds total load")
    if critical_served_kw > critical_load_kw + _TOLERANCE:
        raise ValueError("critical served load exceeds critical load")
    if noncritical_served < -_TOLERANCE or noncritical_served > noncritical_load + _TOLERANCE:
        raise ValueError("noncritical served load is inconsistent with recorded totals")
    critical_fraction = 0.0 if critical_load_kw <= _TOLERANCE else critical_served_kw / critical_load_kw
    noncritical_fraction = 0.0 if noncritical_load <= _TOLERANCE else noncritical_served / noncritical_load
    return min(1.0, max(0.0, critical_fraction)), min(1.0, max(0.0, noncritical_fraction))


def allocate_dispatch_by_capacity(
    assets: Sequence[Mapping[str, Any]],
    *,
    requested_kw: float,
    eligible: Callable[[Mapping[str, Any]], bool] | None = None,
) -> dict[str, float]:
    """Allocate one recorded technology dispatch over eligible installed assets."""

    if not math.isfinite(requested_kw) or requested_kw < -_TOLERANCE:
        raise ValueError("requested dispatch must be finite and nonnegative")
    predicate = eligible or (lambda _asset: True)
    capacities = {
        str(asset["asset_key"]): max(0.0, float(asset.get("installed_power_kw", 0.0)))
        if predicate(asset)
        else 0.0
        for asset in assets
    }
    available = math.fsum(capacities.values())
    if requested_kw > available + max(_TOLERANCE, available * 1e-9):
        raise ValueError(
            f"requested dispatch {requested_kw:.12g} kW exceeds eligible installed power {available:.12g} kW"
        )
    if requested_kw <= _TOLERANCE or available <= _TOLERANCE:
        return {key: 0.0 for key in capacities}
    scale = min(1.0, requested_kw / available)
    return {key: capacity * scale for key, capacity in capacities.items()}


def copy_pinned_feeder(source_master: Path | str, destination: Path | str) -> Path:
    """Copy the pinned feeder directory without modifying the public source."""

    source = Path(source_master).resolve()
    target_root = Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_bundle = source.parent.parent
    target = target_root / "ieee123_source_copy"
    if target.exists():
        raise FileExistsError(target)
    shutil.copytree(source_bundle, target)
    copied_master = target / source.relative_to(source_bundle)
    if hashlib.sha256(copied_master.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
        raise ValueError("copied IEEE123 master digest differs from pinned source")
    return copied_master


def assess_ac_validity(
    *,
    converged: bool,
    voltage_violation_count: int,
    transformer_loading_available: bool,
    maximum_transformer_loading_percent: float | None,
    line_loading_available: bool,
    maximum_line_loading_percent: float | None,
    island_balance_residual_kw: float,
    served_load_kw: float,
    limits: ACValidationLimits,
) -> dict[str, Any]:
    """Apply only limits that are checkable from the pinned public data."""

    transformer_passed = (
        not transformer_loading_available
        or maximum_transformer_loading_percent is not None
        and maximum_transformer_loading_percent <= limits.maximum_equipment_loading_percent + _TOLERANCE
    )
    line_passed = (
        not line_loading_available
        or maximum_line_loading_percent is not None
        and maximum_line_loading_percent <= limits.maximum_equipment_loading_percent + _TOLERANCE
    )
    balance_tolerance = max(
        limits.absolute_balance_tolerance_kw,
        limits.relative_balance_tolerance * max(0.0, served_load_kw),
    )
    balance_passed = island_balance_residual_kw <= balance_tolerance
    checks = {
        "convergence_check": "passed" if converged else "failed",
        "voltage_check": "passed" if voltage_violation_count == 0 else "failed",
        "transformer_loading_check": (
            "unavailable" if not transformer_loading_available else "passed" if transformer_passed else "failed"
        ),
        "line_loading_check": "unavailable" if not line_loading_available else "passed" if line_passed else "failed",
        "island_balance_check": "passed" if balance_passed else "failed",
        "island_balance_tolerance_kw": balance_tolerance,
    }
    checks["ac_valid"] = bool(
        converged and voltage_violation_count == 0 and transformer_passed and line_passed and balance_passed
    )
    return checks


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def _bus_spec(case: IEEE123SCMPOCase, bus_id: str, dss: Any) -> tuple[str, int, float]:
    bus = next(item for item in case.buses if item.bus_id.lower() == bus_id.lower())
    phases = bus.phases or ("1", "2", "3")
    dss.Circuit.SetActiveBus(bus.bus_id)
    base_ln_kv = float(dss.Bus.kVBase())
    nominal_kv = base_ln_kv if len(phases) == 1 else base_ln_kv * math.sqrt(3.0)
    return f"{bus.bus_id}." + ".".join(phases), len(phases), nominal_kv


def _terminal_active_power_kw(dss: Any, element_name: str) -> float:
    if not dss.Circuit.SetActiveElement(element_name):
        return 0.0
    powers = [float(value) for value in dss.CktElement.Powers()]
    conductor_count = int(dss.CktElement.NumConductors())
    return math.fsum(powers[index] for index in range(0, min(len(powers), 2 * conductor_count), 2))


def _transformer_loading(case: IEEE123SCMPOCase, dss: Any) -> tuple[bool, float | None, dict[str, float]]:
    loading: dict[str, float] = {}
    for transformer in case.transformers:
        ratings = [winding.rated_kva for winding in transformer.windings if winding.rated_kva is not None]
        if not ratings or not dss.Circuit.SetActiveElement(f"Transformer.{transformer.name}"):
            continue
        powers = [float(value) for value in dss.CktElement.Powers()]
        conductor_count = int(dss.CktElement.NumConductors())
        terminal_count = int(dss.CktElement.NumTerminals())
        terminal_loadings: list[float] = []
        for terminal in range(terminal_count):
            start = terminal * conductor_count * 2
            stop = start + conductor_count * 2
            terminal_powers = powers[start:stop]
            active = math.fsum(terminal_powers[index] for index in range(0, len(terminal_powers), 2))
            reactive = math.fsum(terminal_powers[index] for index in range(1, len(terminal_powers), 2))
            rating = ratings[min(terminal, len(ratings) - 1)]
            if rating > 0.0:
                terminal_loadings.append(100.0 * math.hypot(active, reactive) / rating)
        if terminal_loadings:
            loading[transformer.name] = max(terminal_loadings)
    return bool(loading), max(loading.values()) if loading else None, loading


def _line_loading(case: IEEE123SCMPOCase, dss: Any) -> tuple[bool, float | None, dict[str, float]]:
    loading: dict[str, float] = {}
    for line in case.lines:
        if line.normal_amps is None or line.normal_amps <= 0.0:
            continue
        if not dss.Circuit.SetActiveElement(f"Line.{line.name}"):
            continue
        currents = [float(value) for value in dss.CktElement.CurrentsMagAng()[::2]]
        if currents:
            loading[line.name] = 100.0 * max(currents) / line.normal_amps
    return bool(loading), max(loading.values()) if loading else None, loading


def _state_records(dss: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    regulators: dict[str, Any] = {}
    for name in dss.RegControls.AllNames():
        dss.RegControls.Name(name)
        regulators[name] = {
            "transformer": dss.RegControls.Transformer(),
            "tap_number": int(dss.RegControls.TapNumber()),
        }
    capacitors: dict[str, Any] = {}
    for name in dss.Capacitors.AllNames():
        dss.Capacitors.Name(name)
        capacitors[name] = [int(value) for value in dss.Capacitors.States()]
    return regulators, capacitors


def _voltage_records(
    case: IEEE123SCMPOCase,
    dss: Any,
    *,
    critical_nodes: set[str],
    critical_fraction: float,
    noncritical_fraction: float,
    limits: ACValidationLimits,
) -> tuple[float | None, float | None, int, dict[str, dict[str, Any]]]:
    served_by_bus: dict[str, float] = {}
    for load in case.loads:
        fraction = critical_fraction if load.bus.bus_id in critical_nodes else noncritical_fraction
        served_by_bus[load.bus.bus_id.lower()] = served_by_bus.get(load.bus.bus_id.lower(), 0.0) + (
            load.active_power_kw * fraction
        )
    grouped: dict[str, list[float]] = {}
    for node_name, magnitude in zip(dss.Circuit.AllNodeNames(), dss.Circuit.AllBusMagPu(), strict=True):
        bus_name = str(node_name).split(".", 1)[0].lower()
        grouped.setdefault(bus_name, []).append(float(magnitude))
    checked: dict[str, dict[str, Any]] = {}
    for bus_name, magnitudes in sorted(grouped.items()):
        energized = max(magnitudes, default=0.0) > 1e-4
        has_served_load = served_by_bus.get(bus_name, 0.0) > _TOLERANCE
        if not energized and not has_served_load:
            continue
        violation = any(
            value < limits.minimum_voltage_pu - _TOLERANCE or value > limits.maximum_voltage_pu + _TOLERANCE
            for value in magnitudes
        )
        checked[bus_name] = {
            "minimum_pu": min(magnitudes),
            "maximum_pu": max(magnitudes),
            "phase_values_pu": magnitudes,
            "served_load_kw": served_by_bus.get(bus_name, 0.0),
            "violation": violation,
        }
    values = [value for record in checked.values() for value in record["phase_values_pu"]]
    return (
        min(values) if values else None,
        max(values) if values else None,
        sum(bool(record["violation"]) for record in checked.values()),
        checked,
    )


def validate_ieee123_scenario(
    *,
    case: IEEE123SCMPOCase,
    copied_master: Path | str,
    method: str,
    budget_id: str,
    budget: float,
    system_trace_id: str,
    system_trace_path: str,
    scenario: Mapping[str, Any],
    upgrade_plan: Sequence[Mapping[str, Any]],
    critical_nodes: set[str],
    limits: ACValidationLimits | None = None,
) -> dict[str, Any]:
    """Apply one saved scenario decision to the copied feeder and solve it."""

    try:
        import opendssdirect as dss
    except ImportError as exc:  # pragma: no cover - dependency is pinned in this project
        raise RuntimeError("IEEE123 AC validation requires OpenDSSDirect.py") from exc

    active_limits = limits or ACValidationLimits()
    critical_fraction, noncritical_fraction = load_service_fractions(
        total_load_kw=float(scenario["total_load_kwh"]),
        critical_load_kw=float(scenario["critical_load_kwh"]),
        total_served_kw=float(scenario["total_load_served_kwh"]),
        critical_served_kw=float(scenario["critical_load_served_kwh"]),
    )
    master = Path(copied_master).resolve()
    original_directory = Path.cwd()
    try:
        dss.Basic.ClearAll()
        dss.Command(f"Compile [{master}]")
        compile_error = dss.Error.Description() if dss.Error.Number() else ""
    finally:
        os.chdir(original_directory)
    if compile_error:
        return {
            "method": method,
            "budget_id": budget_id,
            "budget": budget,
            "scenario": str(scenario["scenario"]),
            "scenario_trace_id": str(scenario.get("scenario_trace_id", "")),
            "system_trace_id": system_trace_id,
            "system_trace_path": system_trace_path,
            "converged": False,
            "ac_valid": False,
            "failure_reason": compile_error,
        }

    applied_commands: list[str] = []
    for load in case.loads:
        fraction = critical_fraction if load.bus.bus_id in critical_nodes else noncritical_fraction
        command = (
            f"Edit Load.{load.name} kW={load.active_power_kw * fraction:.12g} "
            f"kvar={load.reactive_power_kvar * fraction:.12g}"
        )
        dss.Command(command)
        applied_commands.append(command)

    for edge_id in scenario.get("unavailable_edge_ids", []):
        edge = str(edge_id)
        if edge.lower().startswith("line_"):
            command = f"Edit Line.{edge[5:]} enabled=no"
        elif edge.lower().startswith("transformer_"):
            command = f"Edit Transformer.{edge[12:]} enabled=no"
        else:
            continue
        dss.Command(command)
        applied_commands.append(command)

    pcc_enabled = float(scenario.get("public_pcc_import_kwh", 0.0)) > _TOLERANCE
    if not pcc_enabled:
        command = "Edit Vsource.source enabled=no"
        dss.Command(command)
        applied_commands.append(command)

    by_technology = {
        technology: [asset for asset in upgrade_plan if str(asset["technology"]) == technology]
        for technology in ("pv", "dispatchable_generation", "bess")
    }
    pv_dispatch = allocate_dispatch_by_capacity(
        by_technology["pv"], requested_kw=float(scenario.get("pv_dispatch_kwh", 0.0))
    )
    dispatchable_dispatch = allocate_dispatch_by_capacity(
        by_technology["dispatchable_generation"],
        requested_kw=float(scenario.get("dispatchable_upgrade_dispatch_kwh", 0.0)),
    )
    battery_actions = {str(key): str(value) for key, value in scenario.get("selected_battery_actions_by_node", {}).items()}
    bess_discharge = allocate_dispatch_by_capacity(
        by_technology["bess"],
        requested_kw=float(scenario.get("bess_discharge_kwh", 0.0)),
        eligible=lambda asset: battery_actions.get(str(asset["anchor_node"]), "hold") == "discharge",
    )
    bess_charge = allocate_dispatch_by_capacity(
        by_technology["bess"],
        requested_kw=float(scenario.get("bess_charge_kwh", 0.0)),
        eligible=lambda asset: battery_actions.get(str(asset["anchor_node"]), "hold") == "charge",
    )

    generator_elements: list[str] = []
    storage_elements: list[str] = []
    for technology, allocation in (("pv", pv_dispatch), ("dispatchable", dispatchable_dispatch)):
        assets = by_technology["pv" if technology == "pv" else "dispatchable_generation"]
        for asset in assets:
            dispatch = allocation[str(asset["asset_key"])]
            if dispatch <= _TOLERANCE:
                continue
            bus, phases, nominal_kv = _bus_spec(case, str(asset["anchor_node"]), dss)
            name = f"ac_{technology}_{_safe_name(str(asset['asset_key']))}"
            command = (
                f"New Generator.{name} phases={phases} bus1={bus} kv={nominal_kv:.12g} "
                f"kW={dispatch:.12g} pf=1 model=1"
            )
            dss.Command(command)
            applied_commands.append(command)
            generator_elements.append(f"Generator.{name}")

    for asset in by_technology["bess"]:
        key = str(asset["asset_key"])
        discharge = bess_discharge[key]
        charge = bess_charge[key]
        if discharge <= _TOLERANCE and charge <= _TOLERANCE:
            continue
        bus, phases, nominal_kv = _bus_spec(case, str(asset["anchor_node"]), dss)
        name = f"ac_bess_{_safe_name(key)}"
        installed_power = float(asset["installed_power_kw"])
        installed_energy = float(asset["installed_energy_kwh"])
        state = "DISCHARGING" if discharge > _TOLERANCE else "CHARGING"
        dispatch = discharge if discharge > _TOLERANCE else -charge
        initial_energy = installed_energy * min(
            max(0.0, float(asset.get("bess_reserve_target", 0.0))),
            max(0.0, float(asset.get("bess_soc_target", 0.0))),
        )
        command = (
            f"New Storage.{name} phases={phases} bus1={bus} kv={nominal_kv:.12g} "
            f"kWrated={installed_power:.12g} kWhrated={installed_energy:.12g} "
            f"kWhstored={initial_energy:.12g} State={state} kW={dispatch:.12g} pf=1"
        )
        dss.Command(command)
        applied_commands.append(command)
        storage_elements.append(f"Storage.{name}")

    dss.Solution.Solve()
    converged = bool(dss.Solution.Converged())
    solver_iterations = int(dss.Solution.Iterations())
    solve_error = dss.Error.Description() if dss.Error.Number() else ""
    minimum_voltage, maximum_voltage, voltage_violations, voltage_profile = _voltage_records(
        case,
        dss,
        critical_nodes=critical_nodes,
        critical_fraction=critical_fraction,
        noncritical_fraction=noncritical_fraction,
        limits=active_limits,
    )
    active_losses_w, reactive_losses_var = (float(value) for value in dss.Circuit.Losses())
    active_losses_kw = active_losses_w / 1000.0
    transformer_available, transformer_maximum, transformer_loading = _transformer_loading(case, dss)
    line_available, line_maximum, line_loading = _line_loading(case, dss)
    regulators, capacitors = _state_records(dss)
    actual_load_kw = math.fsum(_terminal_active_power_kw(dss, f"Load.{load.name}") for load in case.loads)
    generator_terminal_kw = math.fsum(_terminal_active_power_kw(dss, name) for name in generator_elements)
    storage_terminal_kw = math.fsum(_terminal_active_power_kw(dss, name) for name in storage_elements)
    source_active_kw, _source_reactive_kvar = (float(value) for value in dss.Circuit.TotalPower())
    actual_pcc_import_kw = -source_active_kw if pcc_enabled else 0.0
    island_balance_residual = abs(
        actual_pcc_import_kw - generator_terminal_kw - storage_terminal_kw - actual_load_kw - active_losses_kw
    )
    validity = assess_ac_validity(
        converged=converged,
        voltage_violation_count=voltage_violations,
        transformer_loading_available=transformer_available,
        maximum_transformer_loading_percent=transformer_maximum,
        line_loading_available=line_available,
        maximum_line_loading_percent=line_maximum,
        island_balance_residual_kw=island_balance_residual,
        served_load_kw=float(scenario["total_load_served_kwh"]),
        limits=active_limits,
    )
    return {
        "method": method,
        "budget_id": budget_id,
        "budget": float(budget),
        "scenario": str(scenario["scenario"]),
        "scenario_trace_id": str(scenario.get("scenario_trace_id", "")),
        "system_trace_id": system_trace_id,
        "system_trace_path": system_trace_path,
        "source_master_path": str(Path(case.metadata["master_path"])),
        "source_sha256": str(case.grid.source_sha256),
        "feeder_copy_master": str(master),
        "engine": "OpenDSSDirect.py",
        "engine_version": " ".join(dss.Basic.Version().split()),
        "converged": converged,
        "solver_iterations": solver_iterations,
        "minimum_voltage_pu": minimum_voltage,
        "maximum_voltage_pu": maximum_voltage,
        "voltage_violation_count": voltage_violations,
        "feeder_real_power_losses_kw": active_losses_kw,
        "feeder_reactive_power_losses_kvar": reactive_losses_var / 1000.0,
        "transformer_loading_available": transformer_available,
        "maximum_transformer_loading_percent": transformer_maximum,
        "line_loading_available": line_available,
        "maximum_line_loading_percent": line_maximum,
        "island_balance_residual_kw": island_balance_residual,
        "planned_pcc_import_kw": float(scenario.get("public_pcc_import_kwh", 0.0)),
        "actual_pcc_import_kw": actual_pcc_import_kw,
        "pcc_enabled": pcc_enabled,
        "pcc_dispatch_model": "saved on/off state with OpenDSS source as the AC slack; actual import includes feeder losses",
        "grid_forming_model": "none_not_published",
        "critical_load_service_fraction": critical_fraction,
        "noncritical_load_service_fraction": noncritical_fraction,
        "load_service_mapping": "proportional within saved critical/noncritical classes; exact class totals, public phases and power factors retained",
        "applied_pv_dispatch_kw": math.fsum(pv_dispatch.values()),
        "applied_dispatchable_generation_kw": math.fsum(dispatchable_dispatch.values()),
        "applied_bess_discharge_kw": math.fsum(bess_discharge.values()),
        "applied_bess_charge_kw": math.fsum(bess_charge.values()),
        "selected_patch_modes_json": json.dumps(scenario.get("selected_patch_modes", {}), sort_keys=True),
        "unavailable_edge_ids_json": json.dumps(scenario.get("unavailable_edge_ids", []), sort_keys=True),
        "regulator_states_json": json.dumps(regulators, sort_keys=True),
        "capacitor_states_json": json.dumps(capacitors, sort_keys=True),
        "transformer_loading_json": json.dumps(transformer_loading, sort_keys=True),
        "line_loading_json": json.dumps(line_loading, sort_keys=True),
        "voltage_profile_json": json.dumps(voltage_profile, sort_keys=True),
        "applied_commands_json": json.dumps(applied_commands),
        "failure_reason": solve_error,
        **validity,
    }


__all__ = [
    "ACValidationLimits",
    "allocate_dispatch_by_capacity",
    "assess_ac_validity",
    "copy_pinned_feeder",
    "load_service_fractions",
    "validate_ieee123_scenario",
]
