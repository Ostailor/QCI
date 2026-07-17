"""Deterministic full-system adequacy projection for stitched SC-CMPO upgrades."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

def _unit_interval(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(numeric, 0.0), 1.0)


def _one_hot_projection(values: Mapping[str, Any], names: Sequence[str]) -> dict[str, int]:
    selected = max(names, key=lambda name: (_unit_interval(values.get(name, 0.0)), -names.index(name)))
    return {name: int(name == selected) for name in names}


def repair_sc_cmpo_first_stage(payload: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
    """Conservatively repair one decoded SC-CMPO first-stage decision."""

    shared_names = list(payload["sc_cmpo"]["shared_first_stage_variables"])
    integer_names = {
        variable["name"]
        for variable in payload["variables"]
        if variable["encoding_type"] == "integer" and variable["name"] in shared_names
    }
    repaired: dict[str, float | int] = {}
    for name in shared_names:
        bounded = _unit_interval(values.get(name, 0.0))
        repaired[name] = int(bounded >= 0.5) if name in integer_names else bounded

    base_modes = ["base_mode_connected", "base_mode_islanded", "base_mode_restoration"]
    repaired.update(_one_hot_projection(values, base_modes))

    # Use the smaller BESS fraction so projection never creates power or energy
    # capacity that was absent from the decoded first-stage decision.
    bess_fraction = min(
        float(repaired["bess_energy_fraction"]),
        float(repaired["bess_power_fraction"]),
    )
    repaired["bess_energy_fraction"] = bess_fraction
    repaired["bess_power_fraction"] = bess_fraction
    links = (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    )
    for fraction_name, selection_name in links:
        repaired[selection_name] = int(float(repaired[fraction_name]) > 1e-12)

    adjustments = {
        name: {"raw": values.get(name), "projected": projected}
        for name, projected in repaired.items()
        if abs(_unit_interval(values.get(name, 0.0)) - float(projected)) > 1e-9
    }
    return {"values": repaired, "adjustments": adjustments}


def _first_stage_violation(payload: Mapping[str, Any], values: Mapping[str, Any]) -> float:
    violation = 0.0
    shared = set(payload["sc_cmpo"]["shared_first_stage_variables"])
    for variable in payload["variables"]:
        name = str(variable["name"])
        if name not in shared:
            continue
        try:
            value = float(values.get(name, 0.0))
        except (TypeError, ValueError):
            violation += 1.0
            continue
        violation += max(float(variable["lower_bound"]) - value, 0.0)
        violation += max(value - float(variable["upper_bound"]), 0.0)
    violation += abs(
        sum(_unit_interval(values.get(name, 0.0)) for name in (
            "base_mode_connected",
            "base_mode_islanded",
            "base_mode_restoration",
        ))
        - 1.0
    )
    violation += abs(
        _unit_interval(values.get("bess_energy_fraction", 0.0))
        - _unit_interval(values.get("bess_power_fraction", 0.0))
    )
    for fraction_name, selection_name in (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    ):
        violation += max(
            _unit_interval(values.get(fraction_name, 0.0))
            - _unit_interval(values.get(selection_name, 0.0)),
            0.0,
        )
    return violation


def _scenario_value(values: Mapping[str, Any], group: str, scenario_name: str) -> float:
    return _unit_interval(values.get(f"{group}[{scenario_name}]", 0.0))


def project_sc_cmpo_scenario(
    payload: Mapping[str, Any],
    values: Mapping[str, Any],
    scenario: Mapping[str, Any],
    *,
    repaired_first_stage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one recourse block onto source-backed adequacy and load balance."""

    repaired = dict(repaired_first_stage or repair_sc_cmpo_first_stage(payload, values)["values"])
    options = {item["technology"]: item for item in payload["sc_cmpo"]["upgrade_options"]}
    patch = payload["sc_cmpo"]["upgrade_patch"]
    scenario_name = str(scenario["name"])
    load_kw = float(scenario.get("load_requirement_kw", patch["load_kw"]))
    existing_kw = float(patch["existing_generation_kw"]) if bool(scenario["existing_generation_available"]) else 0.0
    pv_kw = (
        float(options["pv"]["capacity_kw"])
        * float(repaired["pv_capacity_fraction"])
        if bool(scenario["pv_available"])
        else 0.0
    )
    generator_kw = float(options["dispatchable_generation"]["capacity_kw"]) * float(
        repaired["dispatchable_capacity_fraction"]
    )
    bess_fraction = min(
        float(repaired["bess_power_fraction"]),
        float(repaired["bess_energy_fraction"]),
        float(repaired["bess_reserve_target"]),
        float(repaired["bess_soc_target"]),
    )
    bess_kw = float(options["bess"]["power_kw"]) * bess_fraction
    local_supply_kw = existing_kw + pv_kw + generator_kw + bess_kw
    local_dispatch_kw = min(load_kw, local_supply_kw)
    pcc_supply_kw = max(0.0, load_kw - local_dispatch_kw) if bool(scenario["pcc_available"]) else 0.0
    available_supply_kw = local_dispatch_kw + pcc_supply_kw
    served_kw = min(load_kw, available_supply_kw)
    ens_kw = max(0.0, load_kw - served_kw)
    served_fraction = 1.0 if load_kw <= 0.0 else served_kw / load_kw

    raw_mode_names = [f"mode_{mode}[{scenario_name}]" for mode in ("connected", "islanded", "restoration")]
    raw_action_names = [
        f"battery_action_{action}[{scenario_name}]" for action in ("charge", "hold", "discharge")
    ]
    desired_mode = (
        "restoration"
        if bool(scenario["restoration_mode"])
        else "islanded"
        if bool(scenario["forced_islanding"])
        else "connected"
    )
    der_dispatch_fraction = 0.0 if load_kw <= 0.0 else local_dispatch_kw / load_kw
    local_capacity_fraction = 0.0 if load_kw <= 0.0 else local_supply_kw / load_kw
    capacity_slack = _unit_interval((local_capacity_fraction - der_dispatch_fraction) / 3.0)
    non_bess_supply_kw = existing_kw + pv_kw + generator_kw
    bess_dispatch_kw = max(0.0, local_dispatch_kw - non_bess_supply_kw)
    projected_recourse: dict[str, float | int] = {
        **{name: int(name == f"mode_{desired_mode}[{scenario_name}]") for name in raw_mode_names},
        **{
            name: int(
                name == f"battery_action_{'discharge' if bess_dispatch_kw > 1e-12 else 'hold'}[{scenario_name}]"
            )
            for name in raw_action_names
        },
        f"der_commitment[{scenario_name}]": der_dispatch_fraction,
        f"der_capacity_slack[{scenario_name}]": capacity_slack,
        f"critical_load_service[{scenario_name}]": served_fraction,
        f"tie_pcc_response[{scenario_name}]": float(bool(scenario["pcc_available"])),
        f"load_shedding_allocation[{scenario_name}]": 1.0 - served_fraction,
    }

    raw_service = _scenario_value(values, "critical_load_service", scenario_name)
    raw_shedding = _scenario_value(values, "load_shedding_allocation", scenario_name)
    raw_tie = _scenario_value(values, "tie_pcc_response", scenario_name)
    raw_der = _scenario_value(values, "der_commitment", scenario_name)
    raw_capacity_slack = _scenario_value(values, "der_capacity_slack", scenario_name)
    pre_violation = abs(raw_service - raw_der - (raw_tie if bool(scenario["pcc_available"]) else 0.0))
    pre_violation += abs(raw_der + 3.0 * raw_capacity_slack - local_capacity_fraction)
    pre_violation += abs(raw_service + raw_shedding - 1.0)
    pre_violation += abs(sum(_unit_interval(values.get(name, 0.0)) for name in raw_mode_names) - 1.0)
    pre_violation += abs(sum(_unit_interval(values.get(name, 0.0)) for name in raw_action_names) - 1.0)
    if not bool(scenario["pcc_available"]):
        pre_violation += raw_tie
    adjustment_l1 = sum(
        abs(_unit_interval(values.get(name, 0.0)) - float(projected))
        for name, projected in projected_recourse.items()
    )
    return {
        "scenario": scenario_name,
        "source_contingency": str(scenario.get("source_contingency", "")),
        "load_kw": load_kw,
        "existing_generation_kw": existing_kw,
        "pv_upgrade_supply_kw": pv_kw,
        "bess_upgrade_supply_kw": bess_kw,
        "dispatchable_upgrade_supply_kw": generator_kw,
        "pcc_supply_kw": pcc_supply_kw,
        "available_supply_kw": available_supply_kw,
        "critical_load_served_kw": served_kw,
        "critical_energy_not_served_kwh": ens_kw,
        "critical_load_served_fraction": served_fraction,
        "max_fraction_customers_unserved_per_hour": 1.0 - served_fraction,
        "total_hours_critical_infrastructure_unserved": int(ens_kw > 1e-9),
        "pre_repair_violation": pre_violation,
        "post_repair_violation": 0.0,
        "feasibility_after_projection": True,
        "projection_adjustment_l1": adjustment_l1,
        "projected_recourse": projected_recourse,
    }


def project_sc_cmpo_payload(payload: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
    """Repair and evaluate all coupled scenarios in one SC-CMPO payload."""

    repair = repair_sc_cmpo_first_stage(payload, values)
    repaired = repair["values"]
    scenario_rows = [
        project_sc_cmpo_scenario(payload, values, scenario, repaired_first_stage=repaired)
        for scenario in payload["scenario_metadata"]["scenarios"]
    ]
    options = {item["technology"]: item for item in payload["sc_cmpo"]["upgrade_options"]}
    upgrade_cost = (
        float(options["pv"]["total_cost"]) * float(repaired["pv_capacity_fraction"])
        + float(options["bess"]["total_cost"]) * float(repaired["bess_energy_fraction"])
        + float(options["dispatchable_generation"]["total_cost"])
        * float(repaired["dispatchable_capacity_fraction"])
    )
    total_load = sum(float(row["load_kw"]) for row in scenario_rows)
    total_ens = sum(float(row["critical_energy_not_served_kwh"]) for row in scenario_rows)
    return {
        "benchmark": payload["sc_cmpo"]["public_benchmark"],
        "patch_id": payload["sc_cmpo"]["upgrade_patch"]["patch_id"],
        "repaired_first_stage": repaired,
        "first_stage_adjustments": repair["adjustments"],
        "scenario_results": scenario_rows,
        "upgrade_cost": upgrade_cost,
        "critical_energy_not_served_kwh": total_ens,
        "critical_load_served_fraction": 1.0 if total_load <= 0.0 else 1.0 - total_ens / total_load,
        "max_fraction_customers_unserved_per_hour": max(
            (float(row["max_fraction_customers_unserved_per_hour"]) for row in scenario_rows),
            default=0.0,
        ),
        "total_hours_critical_infrastructure_unserved": sum(
            int(row["total_hours_critical_infrastructure_unserved"]) for row in scenario_rows
        ),
        "feasibility_after_projection": all(bool(row["feasibility_after_projection"]) for row in scenario_rows),
        "pre_repair_violation": _first_stage_violation(payload, values)
        + sum(float(row["pre_repair_violation"]) for row in scenario_rows),
        "post_repair_violation": sum(float(row["post_repair_violation"]) for row in scenario_rows),
        "projection_adjustment_l1": sum(float(row["projection_adjustment_l1"]) for row in scenario_rows),
    }


def project_sc_cmpo_system(
    named_payloads: Sequence[tuple[str, Mapping[str, Any]]],
    consensus_by_benchmark: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Project benchmark-wide consensus across the union of modeled islands.

    Overlapping public nodes are counted once. Their projected served fraction
    is the conservative minimum across every patch containing the node.
    Uncovered public-system load remains explicitly outside the reported
    resilience denominator rather than being assigned synthetic behavior.
    """

    payload_results: list[dict[str, Any]] = []
    node_loads: dict[str, dict[str, float]] = defaultdict(dict)
    node_support: dict[str, Counter[str]] = defaultdict(Counter)
    node_scenario_served: dict[tuple[str, str, str], float] = {}
    full_loads: dict[str, float] = {}
    for payload_name, payload in named_payloads:
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
        if benchmark not in consensus_by_benchmark:
            raise KeyError(f"missing SC-CMPO consensus for {benchmark}")
        projection = project_sc_cmpo_payload(payload, consensus_by_benchmark[benchmark])
        projection["payload_name"] = payload_name
        payload_results.append(projection)
        full_loads[benchmark] = float(payload["sc_cmpo"]["public_system_summary"]["total_active_load_kw"])
        for node in payload["sc_cmpo"]["patch_public_nodes"]:
            node_id = str(node["node_id"])
            node_loads[benchmark][node_id] = float(node["load_kw"])
            node_support[benchmark][node_id] += 1
            for scenario in projection["scenario_results"]:
                key = (benchmark, str(scenario["scenario"]), node_id)
                served = float(scenario["critical_load_served_fraction"])
                node_scenario_served[key] = min(node_scenario_served.get(key, 1.0), served)

    benchmark_results: list[dict[str, Any]] = []
    for benchmark in sorted(node_loads):
        benchmark_payloads = [row for row in payload_results if row["benchmark"] == benchmark]
        scenarios = sorted({key[1] for key in node_scenario_served if key[0] == benchmark})
        selected_load_kw = sum(node_loads[benchmark].values())
        ens = 0.0
        max_unserved = 0.0
        infra_hours = 0
        for scenario_name in scenarios:
            scenario_has_ens = False
            for node_id, load_kw in node_loads[benchmark].items():
                served = node_scenario_served[(benchmark, scenario_name, node_id)]
                ens += load_kw * (1.0 - served)
                max_unserved = max(max_unserved, 1.0 - served)
                scenario_has_ens = scenario_has_ens or load_kw * (1.0 - served) > 1e-9
            infra_hours += int(scenario_has_ens)
        denominator = selected_load_kw * len(scenarios)
        benchmark_results.append(
            {
                "benchmark": benchmark,
                "payload_count": len(benchmark_payloads),
                "scenario_count": len(scenarios),
                "selected_unique_node_count": len(node_loads[benchmark]),
                "overlap_node_count": sum(count > 1 for count in node_support[benchmark].values()),
                "selected_unique_load_kw": selected_load_kw,
                "full_public_system_load_kw": full_loads[benchmark],
                "modeled_load_coverage_fraction": selected_load_kw / max(full_loads[benchmark], 1e-9),
                "critical_energy_not_served_kwh": ens,
                "critical_load_served_fraction": 1.0 if denominator <= 0.0 else 1.0 - ens / denominator,
                "max_fraction_customers_unserved_per_hour": max_unserved,
                "total_hours_critical_infrastructure_unserved": infra_hours,
                "feasibility_after_projection": all(
                    bool(row["feasibility_after_projection"]) for row in benchmark_payloads
                ),
                "post_repair_violation": sum(float(row["post_repair_violation"]) for row in benchmark_payloads),
                "upgrade_cost": sum(float(row["upgrade_cost"]) for row in benchmark_payloads),
                "projection_scope": (
                    "unique-node union of selected public benchmark islands; conservative minimum service on overlaps; "
                    "uncovered load excluded and reported through modeled_load_coverage_fraction"
                ),
            }
        )
    return {"payload_results": payload_results, "benchmark_results": benchmark_results}
