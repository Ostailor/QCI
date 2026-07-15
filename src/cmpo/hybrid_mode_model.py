"""Hybrid QCi mode-selection model for Phase 3 build-only experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cmpo.data import GridCase
from cmpo.polynomial import PolynomialModel
from cmpo.qci_export import build_polynomial_model_payload
from cmpo.scenarios import Scenario


MODES = ("connected", "islanded", "restoration")
PRIORITY_BUCKETS = ("standard", "critical_first")
RESERVE_BUCKETS = ("normal_reserve", "holdback_reserve")
DER_BUCKETS = ("economic_der", "resilience_der")
RESPONSE_MODES = ("cost_control", "shed_avoidance", "reserve_rebuild")


@dataclass(frozen=True)
class HybridPayloadResult:
    """Built hybrid payload plus stats and provenance."""

    payload: dict[str, Any]
    model_stats: dict[str, Any]


def _var(kind: str, label: str, microgrid: str | None = None, hour: int | None = None) -> str:
    if microgrid is None:
        return f"{kind}[{label}]"
    return f"{kind}_{label}[{microgrid},{hour}]"


def _add_simplex(model: PolynomialModel, variables: list[str], weight: float) -> None:
    for var in variables:
        model.add_linear(-weight, var)
        model.add_quadratic(weight, var, var)
    for i, left in enumerate(variables):
        for right in variables[i + 1 :]:
            model.add_quadratic(2.0 * weight, left, right)


def _severity_weight(scenario: Scenario) -> float:
    return {
        "low": 1.0,
        "medium": 1.7,
        "high": 2.6,
        "extreme": 3.5,
    }.get(scenario.severity_label, 1.5)


def build_hybrid_mode_payload(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: list[str],
    *,
    source_payload_path: str,
    source_payload_id: str,
    max_variables: int = 132,
) -> HybridPayloadResult:
    """Build a QCi payload over discrete operating-mode and reserve decisions."""

    patch = [mg for mg in patch_ids if mg in {item.name for item in grid_case.microgrids}]
    model = PolynomialModel(name=f"hybrid_{scenario.name}_{'-'.join(patch)}")
    severity = _severity_weight(scenario)
    response_vars = [_var("scenario_response", response) for response in RESPONSE_MODES]
    for var in response_vars:
        model.add_variable(var, 0.0, 1.0, "integer")
    _add_simplex(model, response_vars, 18.0)
    if scenario.severity_label in {"high", "extreme"}:
        model.add_linear(-12.0 * severity, _var("scenario_response", "shed_avoidance"))
        model.add_linear(-9.0 * severity, _var("scenario_response", "reserve_rebuild"))
    else:
        model.add_linear(-3.0, _var("scenario_response", "cost_control"))

    microgrid_index_by_name = {microgrid.name: idx for idx, microgrid in enumerate(grid_case.microgrids)}
    for microgrid in grid_case.microgrids:
        if microgrid.name not in patch:
            continue
        mg_index = microgrid_index_by_name[microgrid.name]
        for hour in range(grid_case.horizon_hours):
            mode_vars = [_var("mode", mode, microgrid.name, hour) for mode in MODES]
            priority_vars = [_var("critical_priority", bucket, microgrid.name, hour) for bucket in PRIORITY_BUCKETS]
            reserve_vars = [_var("battery_reserve", bucket, microgrid.name, hour) for bucket in RESERVE_BUCKETS]
            der_vars = [_var("der_commitment", bucket, microgrid.name, hour) for bucket in DER_BUCKETS]
            tie_var = _var("tie_pcc_available", "decision", microgrid.name, hour)

            for var in mode_vars + priority_vars + reserve_vars + der_vars + [tie_var]:
                model.add_variable(var, 0.0, 1.0, "integer")
            _add_simplex(model, mode_vars, 25.0)
            _add_simplex(model, priority_vars, 15.0)
            _add_simplex(model, reserve_vars, 15.0)
            _add_simplex(model, der_vars, 10.0)

            forced_island = scenario.forced_islanding[mg_index][hour]
            tie_available = scenario.tie_availability[mg_index][hour] and not forced_island
            if forced_island:
                model.add_linear(-22.0 * severity, _var("mode", "islanded", microgrid.name, hour))
                model.add_linear(30.0 * severity, tie_var)
            elif tie_available:
                model.add_linear(-6.0, _var("mode", "connected", microgrid.name, hour))
                model.add_linear(-4.0, tie_var)
            else:
                model.add_linear(18.0 * severity, tie_var)
                model.add_linear(-10.0 * severity, _var("mode", "restoration", microgrid.name, hour))

            critical_load = (
                microgrid.load_profile.base_kw[hour]
                * scenario.load_multiplier_by_hour[hour]
                * microgrid.load_profile.critical_fraction
            )
            model.add_linear(-severity * max(critical_load, 1.0) / 100.0, _var("critical_priority", "critical_first", microgrid.name, hour))
            model.add_quadratic(
                8.0 * severity,
                _var("mode", "islanded", microgrid.name, hour),
                _var("battery_reserve", "normal_reserve", microgrid.name, hour),
            )
            model.add_quadratic(
                -7.0 * severity,
                _var("mode", "islanded", microgrid.name, hour),
                _var("battery_reserve", "holdback_reserve", microgrid.name, hour),
            )
            model.add_linear(-5.0 * severity, _var("der_commitment", "resilience_der", microgrid.name, hour))

            if hour > 0:
                for mode in MODES:
                    model.add_quadratic(
                        -2.0,
                        _var("mode", mode, microgrid.name, hour - 1),
                        _var("mode", mode, microgrid.name, hour),
                    )

    if model.variable_count() > max_variables:
        raise ValueError(f"hybrid payload has {model.variable_count()} variables > max_variables={max_variables}")
    model.validate_degree(3)
    metadata = {
        "scenario": scenario.name,
        "patch": "-".join(patch),
        "patch_ids": patch,
        "horizon": grid_case.horizon_hours,
        "penalty_weights": {
            "mode_switching": 2.0,
            "critical_outage": "severity_and_critical_load_weighted",
            "reserve_inadequacy": "islanded reserve bucket interaction",
            "pcc_tie_contingency": "scenario availability weighted",
            "scenario_risk": severity,
        },
    }
    payload = build_polynomial_model_payload(model, metadata)
    payload["schema"] = "cmpo.hybrid_qci_mode_payload.v1"
    payload["hybrid_model"] = {
        "source_payload_path": source_payload_path,
        "source_payload_id": source_payload_id,
        "qci_decision_variables": [
            "microgrid operating mode",
            "critical load priority bucket",
            "battery reserve allocation bucket",
            "DER commitment bucket",
            "tie/PCC availability decision",
            "scenario response mode",
        ],
        "classical_projection_variables": [
            "thermal generation",
            "battery charge/discharge",
            "state of charge",
            "load shed",
            "tie/PCC flow",
        ],
        "projection_status": "not_run_build_only",
    }
    stats = dict(payload["model_statistics"])
    stats.update(
        {
            "scenario": scenario.name,
            "patch": "-".join(patch),
            "source_payload_id": source_payload_id,
            "source_payload_path": source_payload_path,
            "qci_executable": stats["variable_count"] <= max_variables and stats["degree"] <= 3,
        }
    )
    return HybridPayloadResult(payload=payload, model_stats=stats)
