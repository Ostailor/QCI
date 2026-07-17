"""Deterministic held-out N-1 evaluation using public contingency records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from cmpo.system_level_projection import project_sc_cmpo_scenario, repair_sc_cmpo_first_stage
from cmpo.upgrade_planning import PublicGridData


CONTINGENCY_RE = re.compile(r"^CONTINGENCY\s+(?P<contingency_id>\S+)$")
OPEN_BRANCH_RE = re.compile(
    r"^OPEN BRANCH FROM BUS (?P<from_bus>\d+) TO BUS (?P<to_bus>\d+) CIRCUIT (?P<circuit>\S+)$"
)


def _read_lines(source: Path | str | Iterable[str]) -> list[str]:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8").splitlines()
    if isinstance(source, str):
        candidate = Path(source)
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").splitlines()
        return source.splitlines()
    return [str(line) for line in source]


def parse_public_contingencies(source: Path | str | Iterable[str]) -> list[dict[str, Any]]:
    """Parse branch IDs from public PSS/E contingency files without invention."""

    records: list[dict[str, Any]] = []
    current_contingency_id: str | None = None
    for raw_line in _read_lines(source):
        line = raw_line.strip()
        if not line:
            continue
        contingency_match = CONTINGENCY_RE.match(line)
        if contingency_match:
            current_contingency_id = contingency_match.group("contingency_id")
            continue
        if line == "END":
            current_contingency_id = None
            continue
        branch_match = OPEN_BRANCH_RE.match(line)
        if current_contingency_id and branch_match:
            from_bus = int(branch_match.group("from_bus"))
            to_bus = int(branch_match.group("to_bus"))
            circuit = branch_match.group("circuit")
            records.append(
                {
                    "branch_id": f"{from_bus}-{to_bus}-{circuit}",
                    "contingency_id": current_contingency_id,
                    "from_bus": from_bus,
                    "to_bus": to_bus,
                    "circuit": circuit,
                }
            )
    return records


def _used_contingency_ids(payload: Mapping[str, Any]) -> set[str]:
    used: set[str] = set()
    for scenario in payload["scenario_metadata"]["scenarios"]:
        source = str(scenario.get("source_contingency", ""))
        used.update(item.strip() for item in re.split(r"[,;]", source) if item.strip())
    return used


def select_heldout_public_contingencies(
    grid: PublicGridData,
    payload: Mapping[str, Any],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Select unused public branch/transformer contingencies deterministically."""

    used = _used_contingency_ids(payload)
    rows = [
        {
            "contingency_id": contingency.contingency_id,
            "component_kind": contingency.component_kind,
            "component_id": contingency.component_id,
            "action": contingency.action,
            "source_record": contingency.source_record,
        }
        for contingency in sorted(
            grid.contingencies,
            key=lambda item: (item.component_kind, item.contingency_id, item.component_id),
        )
        if contingency.component_kind in {"branch", "transformer"}
        and contingency.contingency_id not in used
        and contingency.component_id not in used
    ]
    return rows[:limit] if limit is not None else rows


def _patch_retains_grid_connection(
    grid: PublicGridData,
    patch_nodes: set[str],
    removed_component_id: str,
) -> bool:
    adjacency: dict[str, set[str]] = {node.node_id: set() for node in grid.nodes}
    for edge in grid.edges:
        if not edge.in_service or edge.edge_id == removed_component_id:
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)
    outside = set(adjacency) - patch_nodes
    if not outside:
        return False
    for start in patch_nodes:
        visited = {start}
        frontier = [start]
        reaches_outside = False
        while frontier:
            current = frontier.pop()
            if current in outside:
                reaches_outside = True
                break
            for neighbor in adjacency.get(current, set()) - visited:
                visited.add(neighbor)
                frontier.append(neighbor)
        if not reaches_outside:
            return False
    return True


def evaluate_sc_cmpo_heldout(
    grid: PublicGridData,
    payload: Mapping[str, Any],
    values: Mapping[str, Any],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Evaluate unused public branch/transformer N-1 records without invented thresholds."""

    patch = payload["sc_cmpo"]["upgrade_patch"]
    patch_nodes = {str(node_id) for node_id in patch["node_ids"]}
    repaired = repair_sc_cmpo_first_stage(payload, values)["values"]
    heldout = select_heldout_public_contingencies(grid, payload, limit=limit)
    results: list[dict[str, Any]] = []
    for contingency in heldout:
        connected = _patch_retains_grid_connection(grid, patch_nodes, str(contingency["component_id"]))
        scenario = {
            "name": f"heldout_{contingency['contingency_id']}",
            "pcc_available": connected,
            "pv_available": True,
            "existing_generation_available": True,
            "forced_islanding": not connected,
            "restoration_mode": False,
            "load_requirement_kw": float(patch["load_kw"]),
            "source_contingency": str(contingency["contingency_id"]),
        }
        projection = project_sc_cmpo_scenario(
            payload,
            values,
            scenario,
            repaired_first_stage=repaired,
        )
        results.append(
            {
                **contingency,
                "patch_retains_grid_connection": connected,
                "critical_energy_not_served_kwh": projection["critical_energy_not_served_kwh"],
                "critical_load_served_fraction": projection["critical_load_served_fraction"],
                "feasibility_after_projection": projection["feasibility_after_projection"],
                "post_repair_violation": projection["post_repair_violation"],
            }
        )
    total_load = float(patch["load_kw"]) * len(results)
    total_ens = sum(float(row["critical_energy_not_served_kwh"]) for row in results)
    return {
        "benchmark": payload["sc_cmpo"]["public_benchmark"],
        "patch_id": patch["patch_id"],
        "heldout_count": len(results),
        "islanding_contingency_count": sum(not bool(row["patch_retains_grid_connection"]) for row in results),
        "critical_energy_not_served_kwh": total_ens,
        "critical_load_served_fraction": 1.0 if total_load <= 0.0 else 1.0 - total_ens / total_load,
        "feasibility_rate": (
            1.0
            if not results
            else sum(bool(row["feasibility_after_projection"]) for row in results) / len(results)
        ),
        "evaluation_rule": (
            "remove each unused public branch or transformer; require every selected-island node to retain a "
            "public-topology path outside the island; evaluate nominal public load with no sampled thresholds "
            "or multipliers"
        ),
        "results": results,
    }
