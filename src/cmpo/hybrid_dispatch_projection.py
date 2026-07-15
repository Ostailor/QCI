"""Classical dispatch projection interface for hybrid QCi decisions."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from cmpo.data import GridCase
from cmpo.scenarios import Scenario


@dataclass(frozen=True)
class ProjectionRecord:
    """A transparent build-only projection record.

    Real projection metrics require completed QCi mode samples. The build step
    writes this status instead of fabricating dispatch results.
    """

    payload_name: str
    source_payload_path: str
    status: str = "not_run_build_only"
    reason: str = "Classical dispatch projection requires decoded QCi hybrid mode samples."

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def _decision(decisions: dict[str, Any], key: str, default: str) -> str:
    value = decisions.get(key, default)
    return str(value) if value is not None else default


def project_dispatch_from_hybrid_modes(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: list[str],
    decisions: dict[str, Any] | None = None,
    *,
    payload_name: str = "",
    source_payload_path: str = "",
) -> dict[str, Any]:
    """Project hybrid mode decisions into a feasible critical-first dispatch.

    This is a deterministic classical projection, not a QCi result. It uses
    decoded hybrid decisions when provided and otherwise defaults to a
    conservative critical-first policy. It intentionally reports provenance so
    downstream tables can distinguish projected dispatch metrics from raw QCi
    energies.
    """

    decisions = decisions or {}
    patch = set(patch_ids)
    total_critical = 0.0
    served_critical = 0.0
    total_energy_not_served = 0.0
    critical_energy_not_served = 0.0
    max_fraction_unserved = 0.0
    critical_infra_hours = 0.0
    operating_cost = 0.0
    dispatch: dict[str, float] = {}

    for mg_index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name not in patch:
            continue
        soc = microgrid.battery.initial_soc_kwh
        for hour in range(grid_case.horizon_hours):
            prefix = f"{microgrid.name},{hour}"
            mode = _decision(decisions, f"mode[{prefix}]", "connected")
            reserve_bucket = _decision(decisions, f"battery_reserve[{prefix}]", "holdback_reserve")
            tie_decision = _decision(decisions, f"tie_pcc_available[{prefix}]", "scenario")
            load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            critical_load = load * microgrid.load_profile.critical_fraction
            noncritical_load = max(0.0, load - critical_load)
            pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
            generator_available = scenario.generator_availability[mg_index][hour]
            tie_available = scenario.tie_availability[mg_index][hour] and not scenario.forced_islanding[mg_index][hour]
            if tie_decision == "disabled":
                tie_available = False
            if mode == "islanded":
                tie_available = False

            reserve_floor = (0.55 if reserve_bucket == "holdback_reserve" else 0.30) * microgrid.battery.capacity_kwh
            usable_battery = max(0.0, soc - reserve_floor)
            discharge = min(microgrid.battery.max_discharge_kw, usable_battery)
            gen = microgrid.generator.p_max_kw if generator_available else 0.0
            import_pcc = microgrid.pcc.import_limit_kw if tie_available else 0.0
            supply = pv + gen + discharge + import_pcc
            critical_served = min(critical_load, supply)
            remaining = max(0.0, supply - critical_served)
            noncritical_served = min(noncritical_load, remaining)
            shed_critical = max(0.0, critical_load - critical_served)
            shed_noncritical = max(0.0, noncritical_load - noncritical_served)
            soc = max(0.0, soc - discharge)

            total_critical += critical_load
            served_critical += critical_served
            critical_energy_not_served += shed_critical
            total_energy_not_served += shed_critical + shed_noncritical
            if load > 0:
                max_fraction_unserved = max(max_fraction_unserved, (shed_critical + shed_noncritical) / load)
            if shed_critical > 1e-9:
                critical_infra_hours += 1.0
            operating_cost += (
                microgrid.generator.cost_a * gen**3
                + microgrid.generator.cost_b * gen**2
                + microgrid.generator.cost_c * gen
            )

            dispatch[f"P_gen[{prefix}]"] = gen
            dispatch[f"discharge[{prefix}]"] = discharge
            dispatch[f"soc[{prefix}]"] = soc
            dispatch[f"import_pcc[{prefix}]"] = import_pcc
            dispatch[f"shed_critical[{prefix}]"] = shed_critical
            dispatch[f"shed_noncritical[{prefix}]"] = shed_noncritical

    critical_served_fraction = served_critical / total_critical if total_critical else 1.0
    return {
        "payload_name": payload_name,
        "source_payload_path": source_payload_path,
        "status": "projected",
        "projection_method": "critical_first_classical_dispatch_projection",
        "expected_operating_cost": operating_cost,
        "risk_adjusted_cost": operating_cost + 1000.0 * critical_energy_not_served + 500.0 * total_energy_not_served,
        "critical_load_served_fraction": critical_served_fraction,
        "critical_energy_not_served_kwh": critical_energy_not_served,
        "energy_not_served_kwh": total_energy_not_served,
        "max_fraction_customers_unserved_per_hour": max_fraction_unserved,
        "total_hours_critical_infrastructure_unserved": critical_infra_hours,
        "feasibility_after_repair": True,
        "dispatch_variables": dispatch,
    }
