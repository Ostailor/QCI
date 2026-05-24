"""Repair and decode raw continuous CMPO solutions.

Search methods can return values that violate variable bounds or operational
interpretability. The functions here project those raw values into a dispatch
dictionary that is easier to evaluate and explain.
"""

from __future__ import annotations

import re
from typing import Any

from cmpo.data import GridCase, Microgrid
from cmpo.polynomial import PolynomialModel
from cmpo.scenarios import Scenario

MODE_NAMES = ("grid", "island", "restore")
_VAR_RE = re.compile(r"^(?P<prefix>[A-Za-z_]+)\[(?P<microgrid>[^,]+),(?P<hour>\d+)\]$")


def _parse_var_name(name: str) -> tuple[str, str, int] | None:
    match = _VAR_RE.match(name)
    if not match:
        return None
    return match.group("prefix"), match.group("microgrid"), int(match.group("hour"))


def _var(prefix: str, microgrid_id: str, hour: int) -> str:
    return f"{prefix}[{microgrid_id},{hour}]"


def _microgrid_map(grid_case: GridCase) -> dict[str, Microgrid]:
    return {microgrid.name: microgrid for microgrid in grid_case.microgrids}


def _microgrid_index(grid_case: GridCase | None, microgrid_id: str) -> int:
    if grid_case is not None:
        for index, microgrid in enumerate(grid_case.microgrids):
            if microgrid.name == microgrid_id:
                return index
    suffix = microgrid_id.removeprefix("MG")
    return max(0, int(suffix) - 1) if suffix.isdigit() else 0


def clip_to_bounds(solution: dict[str, float], model: PolynomialModel) -> dict[str, float]:
    """Clip all model variables to their lower/upper bounds."""

    repaired = dict(solution)
    for name, variable in model.variables.items():
        value = float(repaired.get(name, 0.0))
        repaired[name] = min(max(value, variable.lower_bound), variable.upper_bound)
    return repaired


def normalize_modes(solution: dict[str, float], microgrids: list[str] | tuple[str, ...], horizon: int) -> dict[str, float]:
    """Normalize grid/island/restore mode weights for each microgrid-hour."""

    repaired = dict(solution)
    for microgrid_id in microgrids:
        for hour in range(horizon):
            keys = {mode: _var(f"z_{mode}", microgrid_id, hour) for mode in MODE_NAMES}
            values = {mode: max(0.0, float(repaired.get(key, 0.0))) for mode, key in keys.items()}
            total = sum(values.values())
            if total <= 1e-12:
                values = {"grid": 1.0, "island": 0.0, "restore": 0.0}
            else:
                values = {mode: value / total for mode, value in values.items()}
            for mode, key in keys.items():
                repaired[key] = values[mode]
    return repaired


def decode_mode(solution: dict[str, float]) -> dict[tuple[str, int], str]:
    """Return the dominant mode by argmax for each microgrid-hour."""

    grouped: dict[tuple[str, int], dict[str, float]] = {}
    for name, value in solution.items():
        parsed = _parse_var_name(name)
        if parsed is None:
            continue
        prefix, microgrid_id, hour = parsed
        if prefix not in {"z_grid", "z_island", "z_restore"}:
            continue
        grouped.setdefault((microgrid_id, hour), {})[prefix.removeprefix("z_")] = float(value)
    decoded: dict[tuple[str, int], str] = {}
    for key, values in grouped.items():
        decoded[key] = max(MODE_NAMES, key=lambda mode: values.get(mode, 0.0))
    return decoded


def repair_storage(
    solution: dict[str, float],
    grid_case: GridCase,
    patch: list[str] | tuple[str, ...],
    scenario: Scenario,
) -> dict[str, float]:
    """Enforce SOC bounds forward in time by adjusting charge/discharge."""

    del scenario
    repaired = dict(solution)
    microgrids = _microgrid_map(grid_case)
    for microgrid_id in patch:
        battery = microgrids[microgrid_id].battery
        soc = battery.initial_soc_kwh
        eta_c = battery.round_trip_efficiency**0.5
        eta_d = battery.round_trip_efficiency**0.5
        for hour in range(grid_case.horizon_hours):
            charge_key = _var("charge", microgrid_id, hour)
            discharge_key = _var("discharge", microgrid_id, hour)
            soc_key = _var("soc", microgrid_id, hour)

            charge = min(max(float(repaired.get(charge_key, 0.0)), 0.0), battery.max_charge_kw)
            discharge = min(max(float(repaired.get(discharge_key, 0.0)), 0.0), battery.max_discharge_kw)
            available_discharge = soc * eta_d
            if discharge > available_discharge:
                discharge = available_discharge
            projected_soc = soc + eta_c * charge - discharge / eta_d
            if projected_soc > battery.capacity_kwh:
                excess = projected_soc - battery.capacity_kwh
                charge = max(0.0, charge - excess / max(eta_c, 1e-12))
                projected_soc = battery.capacity_kwh
            if projected_soc < 0.0:
                discharge = max(0.0, discharge + projected_soc * eta_d)
                projected_soc = 0.0

            repaired[charge_key] = charge
            repaired[discharge_key] = discharge
            repaired[soc_key] = min(max(projected_soc, 0.0), battery.capacity_kwh)
            soc = repaired[soc_key]
    return repaired


def repair_pcc(solution: dict[str, float], scenario: Scenario, grid_case: GridCase | None = None) -> dict[str, float]:
    """Zero PCC import/export when unavailable or decoded mode is islanded."""

    repaired = dict(solution)
    modes = decode_mode(repaired)
    for name in list(repaired):
        parsed = _parse_var_name(name)
        if parsed is None:
            continue
        prefix, microgrid_id, hour = parsed
        if prefix not in {"import_pcc", "export_pcc"}:
            continue
        mg_index = _microgrid_index(grid_case, microgrid_id)
        tie_available = scenario.tie_availability[mg_index][hour]
        islanded = modes.get((microgrid_id, hour)) == "island" or scenario.forced_islanding[mg_index][hour]
        if not tie_available or islanded:
            repaired[name] = 0.0
    return repaired


def compute_balance_residuals(
    solution: dict[str, float],
    grid_case: GridCase,
    patch: list[str] | tuple[str, ...],
    scenario: Scenario,
) -> dict[tuple[str, int], float]:
    """Return supply-demand balance residuals by microgrid-hour."""

    microgrids = _microgrid_map(grid_case)
    residuals: dict[tuple[str, int], float] = {}
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        for hour in range(grid_case.horizon_hours):
            load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
            residual = (
                float(solution.get(_var("P_gen", microgrid_id, hour), 0.0))
                + pv
                + float(solution.get(_var("discharge", microgrid_id, hour), 0.0))
                + float(solution.get(_var("import_pcc", microgrid_id, hour), 0.0))
                - load
                + float(solution.get(_var("shed_noncritical", microgrid_id, hour), 0.0))
                + float(solution.get(_var("shed_critical", microgrid_id, hour), 0.0))
                - float(solution.get(_var("charge", microgrid_id, hour), 0.0))
                - float(solution.get(_var("export_pcc", microgrid_id, hour), 0.0))
            )
            residuals[(microgrid_id, hour)] = residual
    return residuals


def _count_mode_violations(solution: dict[str, float], patch: list[str] | tuple[str, ...], horizon: int) -> int:
    violations = 0
    for microgrid_id in patch:
        for hour in range(horizon):
            total = sum(float(solution.get(_var(f"z_{mode}", microgrid_id, hour), 0.0)) for mode in MODE_NAMES)
            if abs(total - 1.0) > 1e-6:
                violations += 1
    return violations


def _count_storage_violations(solution: dict[str, float], grid_case: GridCase, patch: list[str] | tuple[str, ...]) -> int:
    microgrids = _microgrid_map(grid_case)
    violations = 0
    for microgrid_id in patch:
        capacity = microgrids[microgrid_id].battery.capacity_kwh
        for hour in range(grid_case.horizon_hours):
            soc = float(solution.get(_var("soc", microgrid_id, hour), 0.0))
            if soc < -1e-6 or soc > capacity + 1e-6:
                violations += 1
    return violations


def _count_pcc_violations(solution: dict[str, float], scenario: Scenario, grid_case: GridCase, patch: list[str] | tuple[str, ...]) -> int:
    modes = decode_mode(solution)
    violations = 0
    for microgrid_id in patch:
        mg_index = _microgrid_index(grid_case, microgrid_id)
        for hour in range(grid_case.horizon_hours):
            tie_available = scenario.tie_availability[mg_index][hour]
            islanded = modes.get((microgrid_id, hour)) == "island" or scenario.forced_islanding[mg_index][hour]
            if not tie_available or islanded:
                pcc = abs(float(solution.get(_var("import_pcc", microgrid_id, hour), 0.0))) + abs(
                    float(solution.get(_var("export_pcc", microgrid_id, hour), 0.0))
                )
                if pcc > 1e-6:
                    violations += 1
    return violations


def repair_solution(
    solution: dict[str, float],
    model: PolynomialModel,
    grid_case: GridCase,
    patch: list[str] | tuple[str, ...],
    scenario: Scenario,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Apply all repair steps and return a repaired solution plus diagnostics."""

    mode_violations_before = _count_mode_violations(solution, patch, grid_case.horizon_hours)
    repaired = clip_to_bounds(solution, model)
    repaired = normalize_modes(repaired, patch, grid_case.horizon_hours)
    repaired = repair_storage(repaired, grid_case, patch, scenario)
    repaired = repair_pcc(repaired, scenario, grid_case=grid_case)

    residuals = compute_balance_residuals(repaired, grid_case, patch, scenario)
    max_balance_residual = max((abs(value) for value in residuals.values()), default=0.0)
    storage_violations = _count_storage_violations(repaired, grid_case, patch)
    pcc_violations = _count_pcc_violations(repaired, scenario, grid_case, patch)
    mode_violations = _count_mode_violations(repaired, patch, grid_case.horizon_hours)
    repair_report = {
        "max_balance_residual": round(max_balance_residual, 6),
        "storage_violations": storage_violations,
        "pcc_violations": pcc_violations,
        "mode_violations": mode_violations,
        "feasibility_pass": storage_violations == 0 and pcc_violations == 0 and mode_violations == 0,
    }
    if mode_violations_before and repair_report["mode_violations"] == 0:
        repair_report["mode_violations"] = 0
    return repaired, repair_report


def repair_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for older scaffold callers."""

    repaired = dict(candidate)
    repaired["repair_status"] = "not_implemented_without_model_context"
    return repaired
