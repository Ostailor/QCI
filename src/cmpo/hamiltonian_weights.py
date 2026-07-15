"""Challenge-aligned Hamiltonian component weighting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cmpo.data import GridCase
from cmpo.hamiltonian_builder import PenaltyWeights
from cmpo.polynomial import PolynomialModel
from cmpo.scenarios import Scenario


@dataclass(frozen=True)
class ComponentTerm:
    """One unnormalized monomial belonging to a named Hamiltonian component."""

    coefficient: float
    powers: dict[str, int]


@dataclass(frozen=True)
class ComponentScaling:
    """Scaling actually applied to a named Hamiltonian component."""

    component: str
    raw_term_count: int
    raw_max_abs_coefficient: float
    target_weight: float
    applied_scale: float
    normalized_max_abs_coefficient: float


def penalty_weights_from_config(config: dict[str, object]) -> PenaltyWeights:
    """Build ``PenaltyWeights`` while enforcing critical-shed priority."""

    weights = dict(config)
    noncritical = float(weights.get("noncritical_shed", PenaltyWeights.noncritical_shed))
    critical = float(weights.get("critical_shed", PenaltyWeights.critical_shed))
    weights["critical_shed"] = max(critical, 10.0 * noncritical)
    allowed = PenaltyWeights.__dataclass_fields__.keys()
    return PenaltyWeights(**{key: float(weights.get(key, getattr(PenaltyWeights(), key))) for key in allowed})


def _var(prefix: str, microgrid_id: str, hour: int) -> str:
    return f"{prefix}[{microgrid_id},{hour}]"


def _severity_multiplier(scenario: Scenario) -> float:
    return {
        "low": 1.0,
        "medium": 1.4,
        "high": 2.0,
        "extreme": 2.8,
    }.get(scenario.severity_label, 1.5)


def _add_component(
    components: dict[str, list[ComponentTerm]],
    name: str,
    coefficient: float,
    powers: dict[str, int],
) -> None:
    components.setdefault(name, []).append(ComponentTerm(coefficient=float(coefficient), powers=dict(powers)))


def build_resilience_components(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: Iterable[str],
    *,
    high_stress_scenarios: set[str],
) -> dict[str, list[ComponentTerm]]:
    """Return CMPO-V2 challenge-aligned penalty components.

    The terms use existing dispatch/mode variables, so they do not increase
    QCi variable count. They are normalized by component before being added.
    """

    patch = set(patch_ids)
    components: dict[str, list[ComponentTerm]] = {}
    severity = _severity_multiplier(scenario)
    high_stress = scenario.name in high_stress_scenarios or scenario.severity_label in {"high", "extreme"}

    for mg_index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name not in patch:
            continue
        for hour in range(grid_case.horizon_hours):
            load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            critical_load = load * microgrid.load_profile.critical_fraction
            noncritical_load = max(0.0, load - critical_load)
            total_load = max(load, 1.0)
            critical_share = critical_load / total_load
            shed_critical = _var("shed_critical", microgrid.name, hour)
            shed_noncritical = _var("shed_noncritical", microgrid.name, hour)
            z_island = _var("z_island", microgrid.name, hour)
            z_restore = _var("z_restore", microgrid.name, hour)
            soc = _var("soc", microgrid.name, hour)

            _add_component(
                components,
                "max_customers_unserved_surrogate",
                severity * critical_share / max(critical_load, 1.0),
                {shed_critical: 1},
            )
            _add_component(
                components,
                "max_customers_unserved_surrogate",
                severity * (1.0 - critical_share) / max(noncritical_load, 1.0),
                {shed_noncritical: 1},
            )
            _add_component(
                components,
                "critical_infra_outage_hours_proxy",
                severity / max(critical_load, 1.0),
                {shed_critical: 1},
            )
            _add_component(
                components,
                "critical_infra_outage_hours_proxy",
                0.35 * severity,
                {z_island: 1},
            )
            _add_component(
                components,
                "critical_infra_outage_hours_proxy",
                0.20 * severity,
                {z_restore: 1},
            )

            pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
            reserve_capacity = microgrid.generator.p_max_kw + microgrid.battery.max_discharge_kw + pv
            reserve_requirement = load * scenario.critical_load_requirement * 1.10
            reserve_gap_fraction = max(0.0, reserve_requirement - reserve_capacity) / max(reserve_requirement, 1.0)
            _add_component(
                components,
                "islanded_reserve_margin",
                severity * max(reserve_gap_fraction, 0.05 if scenario.forced_islanding[mg_index][hour] else 0.02),
                {z_island: 1},
            )

            stress_factor = 1.0 if high_stress else 0.2
            reserve_floor = (0.55 if high_stress else 0.35) * microgrid.battery.capacity_kwh
            _add_component(
                components,
                "battery_reserve_holdback_high_stress",
                stress_factor,
                {},
            )
            _add_component(
                components,
                "battery_reserve_holdback_high_stress",
                -stress_factor / max(reserve_floor, 1.0),
                {soc: 1},
            )

    return components


def add_normalized_components(
    model: PolynomialModel,
    components: dict[str, list[ComponentTerm]],
    target_weights: dict[str, float],
) -> list[ComponentScaling]:
    """Normalize each component to unit max coefficient, then apply weight."""

    reports: list[ComponentScaling] = []
    for component, terms in components.items():
        raw_max = max((abs(term.coefficient) for term in terms), default=0.0)
        target = float(target_weights.get(component, 1.0))
        scale = target / raw_max if raw_max > 0 else 0.0
        for term in terms:
            model.add_term(term.coefficient * scale, term.powers)
        reports.append(
            ComponentScaling(
                component=component,
                raw_term_count=len(terms),
                raw_max_abs_coefficient=raw_max,
                target_weight=target,
                applied_scale=scale,
                normalized_max_abs_coefficient=target if raw_max > 0 else 0.0,
            )
        )
    return reports
