"""Deterministic SC-CMPO consensus stitching for overlapping payload solutions."""

from __future__ import annotations

from statistics import median, pstdev
from typing import Any, Mapping, Sequence


def _extract_solution_values(solution: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("first_stage", "solution_values", "values", "stitched_values"):
        values = solution.get(key)
        if isinstance(values, Mapping):
            return values
    if all(isinstance(value, (int, float)) for value in solution.values()):
        return solution
    raise ValueError("payload solution does not contain a supported first-stage variable mapping")


def _clamp(value: float, bounds: tuple[float, float] | None) -> float:
    if bounds is None:
        return value
    lower, upper = bounds
    return min(max(value, float(lower)), float(upper))


def _majority_vote(values: Sequence[float]) -> int:
    votes = [1 if float(value) >= 0.5 else 0 for value in values]
    ones = sum(votes)
    zeros = len(votes) - ones
    if ones > zeros:
        return 1
    if zeros > ones:
        return 0
    return 1 if median(values) >= 0.5 else 0


def stitch_shared_first_stage(
    payload_solutions: Sequence[Mapping[str, Any]],
    variable_specs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Stitch shared first-stage variables across overlapping payload solutions.

    Continuous variables use a deterministic median consensus and are clamped
    to their documented bounds. Binary variables use majority vote with a
    median-based tie break. Linked capacity/selection pairs are then made
    consistent so a positive normalized capacity implies an active selection and
    zero capacity implies an inactive selection.
    """

    observed: dict[str, list[float]] = {name: [] for name in variable_specs}
    for solution in payload_solutions:
        values = _extract_solution_values(solution)
        for variable_name, raw_value in values.items():
            if variable_name in observed and isinstance(raw_value, (int, float)):
                observed[variable_name].append(float(raw_value))

    stitched_values: dict[str, float | int] = {}
    support = {name: len(values) for name, values in observed.items() if values}
    for variable_name, values in observed.items():
        if not values:
            continue
        spec = variable_specs[variable_name]
        kind = str(spec.get("kind", "continuous"))
        if kind == "binary":
            stitched_values[variable_name] = _majority_vote(values)
            continue
        bounds = tuple(spec["bounds"]) if "bounds" in spec else None
        stitched_values[variable_name] = round(_clamp(float(median(values)), bounds), 6)

    consistency_adjustments: dict[str, dict[str, Any]] = {}
    applied_capacities: dict[str, float] = {}
    for variable_name, spec in variable_specs.items():
        if spec.get("kind", "continuous") == "binary" or variable_name not in stitched_values:
            continue
        bounds = tuple(spec["bounds"]) if "bounds" in spec else None
        fraction = float(stitched_values[variable_name])
        normalized_fraction = round(_clamp(fraction, bounds), 6)
        stitched_values[variable_name] = normalized_fraction
        capacity = max(0.0, float(spec.get("capacity", 0.0)))
        applied_capacities[variable_name] = round(normalized_fraction * capacity, 6)

        selection_variable = spec.get("selection_variable")
        if not selection_variable:
            continue
        consistent_selection = 1 if applied_capacities[variable_name] > 0.0 else 0
        previous = stitched_values.get(selection_variable)
        if previous != consistent_selection:
            consistency_adjustments[str(selection_variable)] = {
                "previous": previous,
                "updated": consistent_selection,
                "fraction_variable": variable_name,
            }
        stitched_values[str(selection_variable)] = consistent_selection

    base_modes = ["base_mode_connected", "base_mode_islanded", "base_mode_restoration"]
    if all(name in stitched_values for name in base_modes):
        selected_mode = max(base_modes, key=lambda name: (float(stitched_values[name]), -base_modes.index(name)))
        for name in base_modes:
            updated = int(name == selected_mode)
            previous = stitched_values[name]
            if previous != updated:
                consistency_adjustments[name] = {"previous": previous, "updated": updated, "rule": "one_hot"}
            stitched_values[name] = updated

    if "bess_energy_fraction" in stitched_values and "bess_power_fraction" in stitched_values:
        conservative_fraction = min(
            float(stitched_values["bess_energy_fraction"]),
            float(stitched_values["bess_power_fraction"]),
        )
        for name in ("bess_energy_fraction", "bess_power_fraction"):
            previous = stitched_values[name]
            if previous != conservative_fraction:
                consistency_adjustments[name] = {
                    "previous": previous,
                    "updated": conservative_fraction,
                    "rule": "conservative_energy_power_consistency",
                }
            stitched_values[name] = conservative_fraction
            capacity = max(0.0, float(variable_specs[name].get("capacity", 0.0)))
            applied_capacities[name] = round(conservative_fraction * capacity, 6)

    dispersion = {
        name: {
            "minimum": min(values),
            "maximum": max(values),
            "median": median(values),
            "population_standard_deviation": pstdev(values) if len(values) > 1 else 0.0,
        }
        for name, values in observed.items()
        if values
    }
    return {
        "stitched_values": stitched_values,
        "support": support,
        "applied_capacities": applied_capacities,
        "consistency_adjustments": consistency_adjustments,
        "dispersion": dispersion,
    }


def sc_cmpo_variable_specs(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build consensus specifications directly from an SC-CMPO payload."""

    shared = set(payload["sc_cmpo"]["shared_first_stage_variables"])
    specs: dict[str, dict[str, Any]] = {}
    selection_links = {
        "pv_capacity_fraction": "upgrade_select_pv",
        "bess_energy_fraction": "upgrade_select_bess",
        "bess_power_fraction": "upgrade_select_bess",
        "dispatchable_capacity_fraction": "upgrade_select_dispatchable",
    }
    for variable in payload["variables"]:
        name = str(variable["name"])
        if name not in shared:
            continue
        specs[name] = {
            "kind": "binary" if variable["encoding_type"] == "integer" else "continuous",
            "bounds": (float(variable["lower_bound"]), float(variable["upper_bound"])),
        }
        if name in selection_links:
            specs[name]["selection_variable"] = selection_links[name]
            specs[name]["capacity"] = 1.0
    return specs
