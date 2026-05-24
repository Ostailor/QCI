"""Microgrid design-stage heuristics.

This module provides a simple, defensible Phase 2 design stage: form
overlapping islandable candidate patches, estimate whether they can serve
critical load while islanded, and select low-cost upgrades to improve coverage.
The method is intentionally heuristic and transparent rather than a full
planning optimizer.
"""

from __future__ import annotations

import csv
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import networkx as nx

from cmpo.data import GridCase, Microgrid

Patch = tuple[str, ...]


def _microgrid_map(grid_case: GridCase) -> dict[str, Microgrid]:
    return {microgrid.name: microgrid for microgrid in grid_case.microgrids}


def _build_grid_graph(grid_case: GridCase) -> nx.Graph:
    """Build a small synthetic topology graph from tie-lines plus ring closure."""

    graph = nx.Graph()
    graph.add_nodes_from(microgrid.name for microgrid in grid_case.microgrids)
    for tie_line in grid_case.tie_lines:
        graph.add_edge(tie_line.source_microgrid, tie_line.target_microgrid, capacity_kw=tie_line.capacity_kw)
    if len(grid_case.microgrids) > 2:
        first = grid_case.microgrids[0].name
        last = grid_case.microgrids[-1].name
        if not graph.has_edge(first, last):
            graph.add_edge(first, last, capacity_kw=0.0, synthetic_ring_closure=True)
    return graph


def _normalize_patch(patch: tuple[str, ...] | list[str]) -> Patch:
    return tuple(sorted(patch, key=lambda value: int(value.removeprefix("MG")) if value.removeprefix("MG").isdigit() else value))


def generate_candidate_patches(grid_case: GridCase, max_patch_size: int = 3) -> list[Patch]:
    """Return overlapping connected candidate patches of microgrid IDs.

    Candidate patches are all connected subgraphs up to ``max_patch_size``.
    Single-microgrid patches are included so the coverage heuristic always has
    a fallback. Multi-microgrid patches may overlap by construction.
    """

    if max_patch_size <= 0:
        raise ValueError("max_patch_size must be positive")

    graph = _build_grid_graph(grid_case)
    names = [microgrid.name for microgrid in grid_case.microgrids]
    patches: set[Patch] = set()
    for size in range(1, min(max_patch_size, len(names)) + 1):
        for nodes in combinations(names, size):
            if size == 1 or nx.is_connected(graph.subgraph(nodes)):
                patches.add(_normalize_patch(tuple(nodes)))
    return sorted(patches, key=lambda patch: (len(patch), patch))


def _hour_indices(grid_case: GridCase, hours: list[int] | tuple[int, ...] | None) -> list[int]:
    if hours is None:
        return list(range(grid_case.horizon_hours))
    selected = list(hours)
    if not selected:
        raise ValueError("hours must not be empty")
    if min(selected) < 0 or max(selected) >= grid_case.horizon_hours:
        raise ValueError("hours contains an index outside the grid case horizon")
    return selected


def _patch_hour_balance(
    grid_case: GridCase,
    patch: Patch,
    hour: int,
    upgrades: dict[str, set[str]] | None = None,
) -> tuple[float, float]:
    microgrids = _microgrid_map(grid_case)
    local_supply_kw = 0.0
    critical_load_kw = 0.0
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        selected_upgrades = upgrades.get(microgrid_id, set()) if upgrades else set()
        critical_load_kw += microgrid.load_profile.base_kw[hour] * microgrid.load_profile.critical_fraction
        local_supply_kw += microgrid.generator.p_max_kw
        local_supply_kw += microgrid.pv_availability_kw[hour]
        local_supply_kw += min(
            microgrid.battery.max_discharge_kw,
            microgrid.battery.initial_soc_kwh * microgrid.battery.round_trip_efficiency,
        )
        if "added_generator_kw" in selected_upgrades:
            local_supply_kw += microgrid.upgrade_options.added_generator_kw
        if "added_pv_kw" in selected_upgrades:
            local_supply_kw += microgrid.upgrade_options.added_pv_kw
        if "added_bess_kwh" in selected_upgrades:
            # Treat one-sixth of added storage as usable hourly reserve for the
            # default 4-8 hour planning horizon.
            local_supply_kw += microgrid.upgrade_options.added_bess_kwh / max(grid_case.horizon_hours, 1)
    return local_supply_kw, critical_load_kw


def estimate_islanding_feasibility(
    grid_case: GridCase,
    patch: tuple[str, ...] | list[str],
    hours: list[int] | tuple[int, ...] | None = None,
) -> dict[str, Any]:
    """Estimate whether a patch can serve base critical load while islanded."""

    selected_patch = _normalize_patch(tuple(patch))
    selected_hours = _hour_indices(grid_case, hours)
    feasible_hours = 0
    worst_margin_kw = float("inf")
    total_supply_kw = 0.0
    total_critical_kw = 0.0
    for hour in selected_hours:
        supply_kw, critical_kw = _patch_hour_balance(grid_case, selected_patch, hour)
        margin_kw = supply_kw - critical_kw
        feasible_hours += int(margin_kw >= 0.0)
        worst_margin_kw = min(worst_margin_kw, margin_kw)
        total_supply_kw += supply_kw
        total_critical_kw += critical_kw
    coverage_fraction = min(1.0, total_supply_kw / max(total_critical_kw, 1e-9))
    return {
        "patch": selected_patch,
        "hours": selected_hours,
        "feasible": feasible_hours == len(selected_hours),
        "feasible_hours": feasible_hours,
        "total_hours": len(selected_hours),
        "coverage_fraction": round(coverage_fraction, 6),
        "worst_margin_kw": round(worst_margin_kw, 6),
        "total_supply_kw": round(total_supply_kw, 6),
        "total_critical_load_kw": round(total_critical_kw, 6),
    }


def _estimate_with_upgrades(grid_case: GridCase, patch: Patch, upgrades: dict[str, set[str]]) -> dict[str, Any]:
    feasible_hours = 0
    worst_margin_kw = float("inf")
    total_supply_kw = 0.0
    total_critical_kw = 0.0
    for hour in range(grid_case.horizon_hours):
        supply_kw, critical_kw = _patch_hour_balance(grid_case, patch, hour, upgrades=upgrades)
        margin_kw = supply_kw - critical_kw
        feasible_hours += int(margin_kw >= 0.0)
        worst_margin_kw = min(worst_margin_kw, margin_kw)
        total_supply_kw += supply_kw
        total_critical_kw += critical_kw
    return {
        "patch": patch,
        "feasible": feasible_hours == grid_case.horizon_hours,
        "feasible_hours": feasible_hours,
        "total_hours": grid_case.horizon_hours,
        "coverage_fraction": round(min(1.0, total_supply_kw / max(total_critical_kw, 1e-9)), 6),
        "worst_margin_kw": round(worst_margin_kw, 6),
        "total_supply_kw": round(total_supply_kw, 6),
        "total_critical_load_kw": round(total_critical_kw, 6),
    }


def _upgrade_catalog(microgrid: Microgrid) -> list[tuple[str, float, float]]:
    return [
        ("added_generator_kw", microgrid.upgrade_options.added_generator_kw, microgrid.upgrade_options.added_generator_cost),
        ("added_pv_kw", microgrid.upgrade_options.added_pv_kw, microgrid.upgrade_options.added_pv_cost),
        (
            "added_bess_kwh",
            microgrid.upgrade_options.added_bess_kwh / 6.0,
            microgrid.upgrade_options.added_bess_cost,
        ),
    ]


def _select_covering_patches(grid_case: GridCase, candidate_patches: list[Patch]) -> list[Patch]:
    uncovered = {microgrid.name for microgrid in grid_case.microgrids}
    selected: list[Patch] = []
    ordered = sorted(candidate_patches, key=lambda patch: (-len(set(patch) & uncovered), len(patch), patch))
    while uncovered:
        best = max(ordered, key=lambda patch: (len(set(patch) & uncovered), len(patch)))
        newly_covered = set(best) & uncovered
        if not newly_covered:
            missing = sorted(uncovered)
            raise ValueError(f"candidate patches do not cover all microgrids: {missing}")
        selected.append(best)
        uncovered -= newly_covered
        ordered = [patch for patch in ordered if set(patch) & uncovered]
    return selected


def choose_min_cost_upgrades(grid_case: GridCase, candidate_patches: list[Patch]) -> dict[str, Any]:
    """Greedily select covering patches and low-cost upgrades for islanding."""

    if not candidate_patches:
        raise ValueError("candidate_patches must not be empty")

    microgrids = _microgrid_map(grid_case)
    normalized_candidates = {_normalize_patch(patch) for patch in candidate_patches}
    normalized_candidates.update((microgrid.name,) for microgrid in grid_case.microgrids)
    selected_patches = _select_covering_patches(grid_case, sorted(normalized_candidates, key=lambda patch: (len(patch), patch)))
    selected_upgrades: dict[str, set[str]] = {name: set() for name in microgrids}
    upgrade_records: list[dict[str, Any]] = []
    feasibility_summary: dict[Patch, dict[str, Any]] = {}

    for patch in selected_patches:
        before = estimate_islanding_feasibility(grid_case, patch)
        after = _estimate_with_upgrades(grid_case, patch, selected_upgrades)
        while not after["feasible"]:
            catalog: list[tuple[float, str, str, float, float]] = []
            for microgrid_id in patch:
                microgrid = microgrids[microgrid_id]
                for option_name, added_kw, cost in _upgrade_catalog(microgrid):
                    if option_name not in selected_upgrades[microgrid_id]:
                        catalog.append((cost / max(added_kw, 1e-9), microgrid_id, option_name, added_kw, cost))
            if not catalog:
                break
            _ratio, microgrid_id, option_name, added_kw, cost = min(catalog, key=lambda item: (item[0], item[4], item[1]))
            selected_upgrades[microgrid_id].add(option_name)
            upgrade_records.append(
                {
                    "microgrid_id": microgrid_id,
                    "upgrade": option_name,
                    "added_capacity_equivalent_kw": round(added_kw, 6),
                    "cost": round(cost, 2),
                    "patch_trigger": patch,
                }
            )
            after = _estimate_with_upgrades(grid_case, patch, selected_upgrades)
        feasibility_summary[patch] = {"before": before, "after": after}

    total_microgrids = len(grid_case.microgrids)
    covered = {microgrid_id for patch in selected_patches for microgrid_id in patch}
    total_patch_hours = len(selected_patches) * grid_case.horizon_hours
    feasible_patch_hours = sum(summary["after"]["feasible_hours"] for summary in feasibility_summary.values())
    metrics = {
        "total_upgrade_cost": round(sum(record["cost"] for record in upgrade_records), 2),
        "customers_covered_fraction": round(len(covered) / max(total_microgrids, 1), 6),
        "critical_load_coverage_fraction": round(feasible_patch_hours / max(total_patch_hours, 1), 6),
        "selected_patch_count": len(selected_patches),
        "average_patch_size": round(sum(len(patch) for patch in selected_patches) / max(len(selected_patches), 1), 6),
    }
    return {
        "selected_patches": selected_patches,
        "upgrades": upgrade_records,
        "total_upgrade_cost": metrics["total_upgrade_cost"],
        "feasibility_summary": feasibility_summary,
        "metrics": metrics,
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {("|".join(key) if isinstance(key, tuple) else key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def save_design_outputs(design: dict[str, Any], output_dir: Path | str = Path("results")) -> dict[str, Path]:
    """Write design-stage CSV and JSON outputs."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    design_csv = out_dir / "microgrid_design.csv"
    upgrade_csv = out_dir / "upgrade_plan.csv"
    summary_json = out_dir / "design_summary.json"

    with design_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "patch_id",
                "microgrid_ids",
                "patch_size",
                "before_feasible",
                "after_feasible",
                "before_coverage_fraction",
                "after_coverage_fraction",
                "after_worst_margin_kw",
            ],
        )
        writer.writeheader()
        for index, patch in enumerate(design["selected_patches"], start=1):
            summary = design["feasibility_summary"][patch]
            writer.writerow(
                {
                    "patch_id": f"P{index}",
                    "microgrid_ids": "|".join(patch),
                    "patch_size": len(patch),
                    "before_feasible": summary["before"]["feasible"],
                    "after_feasible": summary["after"]["feasible"],
                    "before_coverage_fraction": summary["before"]["coverage_fraction"],
                    "after_coverage_fraction": summary["after"]["coverage_fraction"],
                    "after_worst_margin_kw": summary["after"]["worst_margin_kw"],
                }
            )

    with upgrade_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["microgrid_id", "upgrade", "added_capacity_equivalent_kw", "cost", "patch_trigger"])
        writer.writeheader()
        for record in design["upgrades"]:
            row = dict(record)
            row["patch_trigger"] = "|".join(record["patch_trigger"])
            writer.writerow(row)

    summary_json.write_text(json.dumps(_json_ready(design), indent=2), encoding="utf-8")
    return {
        "microgrid_design_csv": design_csv,
        "upgrade_plan_csv": upgrade_csv,
        "design_summary_json": summary_json,
    }


def design_microgrid_patch(dataset: GridCase) -> dict[str, Any]:
    """Run the default design-stage workflow for scripts."""

    return choose_min_cost_upgrades(dataset, generate_candidate_patches(dataset))
