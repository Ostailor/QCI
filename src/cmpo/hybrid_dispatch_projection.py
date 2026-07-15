"""Classical dispatch projection interface for hybrid QCi decisions."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from cmpo.baselines import _dispatch_metrics
from cmpo.data import GridCase
from cmpo.phase3_metrics import add_phase3_columns
from cmpo.polynomial import PolynomialModel
from cmpo.repair import compute_balance_residuals, repair_solution
from cmpo.scenarios import Scenario


MODE_LABELS = ("connected", "islanded", "restoration")
PRIORITY_LABELS = ("standard", "critical_first")
RESERVE_LABELS = ("normal_reserve", "holdback_reserve")
DER_LABELS = ("economic_der", "resilience_der")
RESPONSE_LABELS = ("cost_control", "shed_avoidance", "reserve_rebuild")
GROUPED_VAR_RE = re.compile(
    r"^(?P<kind>mode|critical_priority|battery_reserve|der_commitment)_(?P<label>.+)"
    r"\[(?P<microgrid>[^,]+),(?P<hour>\d+)\]$"
)
TIE_VAR_RE = re.compile(r"^tie_pcc_available_decision\[(?P<microgrid>[^,]+),(?P<hour>\d+)\]$")
RESPONSE_VAR_RE = re.compile(r"^scenario_response\[(?P<label>[^]]+)\]$")


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


def _best_label(values: dict[str, float], labels: tuple[str, ...], default: str) -> str:
    if not values:
        return default
    return max(labels, key=lambda label: (float(values.get(label, float("-inf"))), -labels.index(label)))


def decode_hybrid_mode_decisions(
    decoded_variables: dict[str, float],
    payload: dict[str, Any],
) -> dict[str, str]:
    """Project raw QCi mode-vector values to deterministic discrete decisions."""

    grouped: dict[tuple[str, str, int], dict[str, float]] = {}
    ties: dict[tuple[str, int], float] = {}
    responses: dict[str, float] = {}
    for name, raw_value in decoded_variables.items():
        value = float(raw_value)
        grouped_match = GROUPED_VAR_RE.match(name)
        if grouped_match:
            key = (
                grouped_match.group("kind"),
                grouped_match.group("microgrid"),
                int(grouped_match.group("hour")),
            )
            grouped.setdefault(key, {})[grouped_match.group("label")] = value
            continue
        tie_match = TIE_VAR_RE.match(name)
        if tie_match:
            ties[(tie_match.group("microgrid"), int(tie_match.group("hour")))] = value
            continue
        response_match = RESPONSE_VAR_RE.match(name)
        if response_match:
            responses[response_match.group("label")] = value

    patch = [str(item) for item in payload.get("patch_metadata", {}).get("patch_ids", [])]
    horizon = int(payload.get("scenario_metadata", {}).get("horizon", 0))
    decisions: dict[str, str] = {
        "scenario_response": _best_label(responses, RESPONSE_LABELS, "shed_avoidance")
    }
    specs = {
        "mode": (MODE_LABELS, "connected"),
        "critical_priority": (PRIORITY_LABELS, "critical_first"),
        "battery_reserve": (RESERVE_LABELS, "normal_reserve"),
        "der_commitment": (DER_LABELS, "resilience_der"),
    }
    for microgrid in patch:
        for hour in range(horizon):
            for kind, (labels, default) in specs.items():
                decisions[f"{kind}[{microgrid},{hour}]"] = _best_label(
                    grouped.get((kind, microgrid, hour), {}),
                    labels,
                    default,
                )
            decisions[f"tie_pcc_available[{microgrid},{hour}]"] = (
                "enabled" if ties.get((microgrid, hour), 0.0) >= 0.5 else "disabled"
            )
    return decisions


def _direct_mode(mode: str) -> str:
    return {"connected": "grid", "islanded": "island", "restoration": "restore"}.get(mode, "grid")


def _seed_dispatch(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: list[str],
    decisions: dict[str, Any],
) -> dict[str, float]:
    patch = set(patch_ids)
    response_mode = _decision(decisions, "scenario_response", "shed_avoidance")
    solution: dict[str, float] = {}
    for mg_index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name not in patch:
            continue
        soc = microgrid.battery.initial_soc_kwh
        eta = max(microgrid.battery.round_trip_efficiency**0.5, 1e-12)
        for hour in range(grid_case.horizon_hours):
            prefix = f"{microgrid.name},{hour}"
            mode = _decision(decisions, f"mode[{prefix}]", "connected")
            direct_mode = _direct_mode(mode)
            priority = _decision(decisions, f"critical_priority[{prefix}]", "critical_first")
            reserve = _decision(decisions, f"battery_reserve[{prefix}]", "normal_reserve")
            der = _decision(decisions, f"der_commitment[{prefix}]", "resilience_der")
            tie_decision = _decision(decisions, f"tie_pcc_available[{prefix}]", "disabled")
            tie_available = (
                scenario.tie_availability[mg_index][hour]
                and not scenario.forced_islanding[mg_index][hour]
                and direct_mode != "island"
                and tie_decision == "enabled"
            )
            generator_available = scenario.generator_availability[mg_index][hour]
            load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            critical_load = load * microgrid.load_profile.critical_fraction
            noncritical_load = max(0.0, load - critical_load)
            pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]

            deficit = max(0.0, load - pv)
            generator_target = deficit if der == "resilience_der" else max(0.0, critical_load - pv)
            generator = min(microgrid.generator.p_max_kw, generator_target) if generator_available else 0.0
            deficit = max(0.0, deficit - generator)

            reserve_fraction = 0.55 if reserve == "holdback_reserve" else 0.25
            if response_mode == "shed_avoidance":
                reserve_fraction = min(reserve_fraction, 0.20)
            usable_soc = max(0.0, soc - reserve_fraction * microgrid.battery.capacity_kwh)
            battery_allowed = direct_mode == "island" or response_mode != "cost_control" or deficit > noncritical_load
            discharge = min(microgrid.battery.max_discharge_kw, usable_soc * eta, deficit) if battery_allowed else 0.0
            deficit = max(0.0, deficit - discharge)

            import_pcc = min(microgrid.pcc.import_limit_kw, deficit) if tie_available else 0.0
            deficit = max(0.0, deficit - import_pcc)
            if priority == "critical_first":
                shed_noncritical = min(noncritical_load, deficit)
                shed_critical = min(critical_load, max(0.0, deficit - shed_noncritical))
            else:
                shed_critical = deficit * critical_load / load if load > 0.0 else 0.0
                shed_noncritical = max(0.0, deficit - shed_critical)

            surplus = max(0.0, pv + generator + discharge + import_pcc - load + shed_critical + shed_noncritical)
            charge_room = max(0.0, (microgrid.battery.capacity_kwh - soc) / eta)
            charge = min(microgrid.battery.max_charge_kw, charge_room, surplus)
            surplus -= charge
            export_pcc = min(microgrid.pcc.export_limit_kw, surplus) if tie_available else 0.0
            soc = min(
                microgrid.battery.capacity_kwh,
                max(0.0, soc + eta * charge - discharge / eta),
            )

            for candidate in ("grid", "island", "restore"):
                solution[f"z_{candidate}[{prefix}]"] = 1.0 if candidate == direct_mode else 0.0
            solution[f"P_gen[{prefix}]"] = generator
            solution[f"charge[{prefix}]"] = charge
            solution[f"discharge[{prefix}]"] = discharge
            solution[f"soc[{prefix}]"] = soc
            solution[f"import_pcc[{prefix}]"] = import_pcc
            solution[f"export_pcc[{prefix}]"] = export_pcc
            solution[f"shed_critical[{prefix}]"] = shed_critical
            solution[f"shed_noncritical[{prefix}]"] = shed_noncritical
    return solution


def project_dispatch_from_hybrid_modes(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: list[str],
    decisions: dict[str, Any] | None = None,
    *,
    model: PolynomialModel,
    payload_name: str = "",
    source_payload_path: str = "",
    dataset: str = "hybrid_smoke",
) -> dict[str, Any]:
    """Project hybrid mode decisions into a feasible critical-first dispatch.

    This is a deterministic classical projection, not a QCi result. It uses
    decoded hybrid decisions when provided and otherwise defaults to a
    conservative critical-first policy. It intentionally reports provenance so
    downstream tables can distinguish projected dispatch metrics from raw QCi
    energies.
    """

    decisions = decisions or {}
    raw_dispatch = _seed_dispatch(grid_case, scenario, patch_ids, decisions)
    repaired_dispatch, repair_report = repair_solution(raw_dispatch, model, grid_case, patch_ids, scenario)
    dispatch_metrics = _dispatch_metrics(repaired_dispatch, grid_case, scenario, patch_ids)
    metric_row = add_phase3_columns(
        [
            {
                "method_name": "CMPO Hybrid QCi + Classical Projection",
                "scenario": scenario.name,
                "patch": "-".join(patch_ids),
                "expected_cost_component": dispatch_metrics["expected_cost_component"],
                "critical_load_served_fraction": dispatch_metrics["critical_load_served_fraction"],
                "noncritical_load_served_fraction": dispatch_metrics["noncritical_load_served_fraction"],
                "energy_not_served_kwh": dispatch_metrics["energy_not_served_kwh"],
                "critical_energy_not_served_kwh": dispatch_metrics["critical_energy_not_served_kwh"],
                "feasibility_pass": bool(repair_report["feasibility_pass"]),
                "runtime_seconds": 0.0,
                "repeat": 0,
                "backend": "qci_dirac3_hybrid_projection",
            }
        ],
        grid_case,
        dataset_name=dataset,
    ).iloc[0].to_dict()
    balance_residuals = compute_balance_residuals(repaired_dispatch, grid_case, patch_ids, scenario)
    max_balance_residual = max((abs(value) for value in balance_residuals.values()), default=0.0)
    expected_cost = float(metric_row["expected_cost_component"])
    critical_ens = float(metric_row["critical_energy_not_served_kwh"])
    metric_row.update(
        {
        "payload_name": payload_name,
        "source_payload_path": source_payload_path,
        "status": "projected",
        "projection_method": "critical_first_classical_dispatch_projection",
            "expected_operating_cost": expected_cost,
            "risk_adjusted_cost": expected_cost + 0.25 * max(critical_ens, 0.0),
            "total_critical_infrastructure_unserved_hours_proxy": metric_row[
                "total_hours_critical_infrastructure_unserved"
            ],
            "feasibility_after_repair": bool(repair_report["feasibility_pass"]),
            "post_repair_violation": not bool(repair_report["feasibility_pass"]),
            "max_balance_residual": float(max_balance_residual),
            "repair_report": json.dumps(repair_report, sort_keys=True, separators=(",", ":")),
            "decoded_mode_decisions": json.dumps(decisions, sort_keys=True, separators=(",", ":")),
            "raw_dispatch_variables": json.dumps(raw_dispatch, sort_keys=True, separators=(",", ":")),
            "dispatch_variables": json.dumps(repaired_dispatch, sort_keys=True, separators=(",", ":")),
        }
    )
    return metric_row
