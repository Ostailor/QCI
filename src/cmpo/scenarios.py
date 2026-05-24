"""Scenario generation for resilient microgrid evaluation.

The scenarios in this module are synthetic and documented for Phase 2
benchmarking only. They do not use proprietary utility data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Scenario:
    """A disruption or operating condition applied to a microgrid patch."""

    name: str
    probability: float
    load_multiplier_by_hour: list[float]
    pv_multiplier_by_hour: list[float]
    tie_availability: list[list[bool]]
    generator_availability: list[list[bool]]
    forced_islanding: list[list[bool]]
    severity_label: str
    critical_load_requirement: float

    def to_dict(self) -> dict[str, object]:
        """Return a YAML/CSV-friendly representation."""

        return asdict(self)


def _matrix(n_microgrids: int, horizon_hours: int, value: bool) -> list[list[bool]]:
    return [[value for _ in range(horizon_hours)] for _ in range(n_microgrids)]


def _hourly(horizon_hours: int, value: float) -> list[float]:
    return [round(value, 4) for _ in range(horizon_hours)]


def _ramp(horizon_hours: int, start: float, stop: float) -> list[float]:
    if horizon_hours == 1:
        return [round(stop, 4)]
    return [round(start + (stop - start) * i / (horizon_hours - 1), 4) for i in range(horizon_hours)]


def build_default_scenarios(n_microgrids: int = 4, horizon_hours: int = 6) -> list[Scenario]:
    """Create the default eight synthetic disruption scenarios.

    Scenario arrays are shaped as ``n_microgrids x horizon_hours`` for
    microgrid-specific availability flags and as ``horizon_hours`` for shared
    hourly load/PV multipliers.
    """

    probabilities = [0.375, 0.125, 0.125, 0.0625, 0.0625, 0.0625, 0.125, 0.0625]
    normal_ties = _matrix(n_microgrids, horizon_hours, True)
    normal_gens = _matrix(n_microgrids, horizon_hours, True)
    no_islanding = _matrix(n_microgrids, horizon_hours, False)

    pcc_failure_ties = _matrix(n_microgrids, horizon_hours, True)
    for hour in range(horizon_hours):
        pcc_failure_ties[0][hour] = False

    gen_failure = _matrix(n_microgrids, horizon_hours, True)
    failed_mg = min(1, n_microgrids - 1)
    for hour in range(max(1, horizon_hours // 3), horizon_hours):
        gen_failure[failed_mg][hour] = False

    storm_ties = _matrix(n_microgrids, horizon_hours, False)
    storm_islanding = _matrix(n_microgrids, horizon_hours, True)

    restoration_ties = _matrix(n_microgrids, horizon_hours, False)
    restoration_islanding = _matrix(n_microgrids, horizon_hours, True)
    for mg_idx in range(n_microgrids):
        for hour in range(horizon_hours):
            if hour >= horizon_hours // 2 and mg_idx % 2 == 0:
                restoration_ties[mg_idx][hour] = True
                restoration_islanding[mg_idx][hour] = False

    combined_ties = _matrix(n_microgrids, horizon_hours, True)
    combined_gens = _matrix(n_microgrids, horizon_hours, True)
    combined_islanding = _matrix(n_microgrids, horizon_hours, False)
    for mg_idx in range(n_microgrids):
        for hour in range(horizon_hours):
            if mg_idx in {0, n_microgrids - 1} or hour >= horizon_hours // 2:
                combined_ties[mg_idx][hour] = False
            if mg_idx == 0 and hour >= horizon_hours // 3:
                combined_gens[mg_idx][hour] = False
            if hour >= horizon_hours // 2:
                combined_islanding[mg_idx][hour] = True

    return [
        Scenario(
            name="normal",
            probability=probabilities[0],
            load_multiplier_by_hour=_hourly(horizon_hours, 1.0),
            pv_multiplier_by_hour=_hourly(horizon_hours, 1.0),
            tie_availability=normal_ties,
            generator_availability=normal_gens,
            forced_islanding=no_islanding,
            severity_label="low",
            critical_load_requirement=0.98,
        ),
        Scenario(
            name="renewable_shortfall",
            probability=probabilities[1],
            load_multiplier_by_hour=_hourly(horizon_hours, 1.02),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.42),
            tie_availability=normal_ties,
            generator_availability=normal_gens,
            forced_islanding=no_islanding,
            severity_label="medium",
            critical_load_requirement=0.96,
        ),
        Scenario(
            name="demand_surge",
            probability=probabilities[2],
            load_multiplier_by_hour=_ramp(horizon_hours, 1.12, 1.32),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.95),
            tie_availability=normal_ties,
            generator_availability=normal_gens,
            forced_islanding=no_islanding,
            severity_label="medium",
            critical_load_requirement=0.96,
        ),
        Scenario(
            name="pcc_failure",
            probability=probabilities[3],
            load_multiplier_by_hour=_hourly(horizon_hours, 1.05),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.9),
            tie_availability=pcc_failure_ties,
            generator_availability=normal_gens,
            forced_islanding=no_islanding,
            severity_label="high",
            critical_load_requirement=0.94,
        ),
        Scenario(
            name="local_generator_failure",
            probability=probabilities[4],
            load_multiplier_by_hour=_hourly(horizon_hours, 1.04),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.9),
            tie_availability=normal_ties,
            generator_availability=gen_failure,
            forced_islanding=no_islanding,
            severity_label="high",
            critical_load_requirement=0.94,
        ),
        Scenario(
            name="storm_forced_islanding",
            probability=probabilities[5],
            load_multiplier_by_hour=_hourly(horizon_hours, 1.18),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.55),
            tie_availability=storm_ties,
            generator_availability=normal_gens,
            forced_islanding=storm_islanding,
            severity_label="high",
            critical_load_requirement=0.92,
        ),
        Scenario(
            name="restoration",
            probability=probabilities[6],
            load_multiplier_by_hour=_ramp(horizon_hours, 0.82, 1.15),
            pv_multiplier_by_hour=_ramp(horizon_hours, 0.6, 0.9),
            tie_availability=restoration_ties,
            generator_availability=normal_gens,
            forced_islanding=restoration_islanding,
            severity_label="medium",
            critical_load_requirement=0.95,
        ),
        Scenario(
            name="combined_high_stress",
            probability=probabilities[7],
            load_multiplier_by_hour=_ramp(horizon_hours, 1.18, 1.42),
            pv_multiplier_by_hour=_hourly(horizon_hours, 0.35),
            tie_availability=combined_ties,
            generator_availability=combined_gens,
            forced_islanding=combined_islanding,
            severity_label="extreme",
            critical_load_requirement=0.90,
        ),
    ]


def list_default_scenarios() -> list[str]:
    """Return the default scenario names."""

    return [scenario.name for scenario in build_default_scenarios()]
