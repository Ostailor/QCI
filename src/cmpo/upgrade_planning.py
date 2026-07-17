"""Public-data upgrade planning primitives for Scenario-Coupled Consensus CMPO."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PublicNode:
    """One public benchmark node with active load and dispatchable capacity."""

    node_id: str
    load_kw: float
    generation_kw: float
    source_record: str


@dataclass(frozen=True)
class PublicEdge:
    """One public benchmark branch or feeder line."""

    edge_id: str
    source: str
    target: str
    capacity_kw: float | None
    in_service: bool
    source_record: str


@dataclass(frozen=True)
class PublicContingency:
    """A published or deterministic N-1 component outage."""

    contingency_id: str
    component_kind: str
    component_id: str
    action: str
    source_record: str


@dataclass(frozen=True)
class PublicGridData:
    """Minimal source-faithful grid representation used by SC-CMPO."""

    benchmark: str
    family: str
    nodes: tuple[PublicNode, ...]
    edges: tuple[PublicEdge, ...]
    contingencies: tuple[PublicContingency, ...]
    source_path: str
    source_sha256: str
    source_version: str
    source_url: str
    source_license: str
    transformation: str


@dataclass(frozen=True)
class TechnologyCost:
    """A selected NREL ATB overnight-capital-cost record."""

    technology: str
    cost_per_kw: float
    cost_per_kwh: float | None
    duration_hours: float | None
    source_row: str
    source_url: str
    source_version: str
    source_sha256: str
    transformation: str


@dataclass(frozen=True)
class UpgradePatch:
    """A connected public-grid island whose nominal supply has a deficit."""

    patch_id: str
    node_ids: tuple[str, ...]
    load_kw: float
    existing_generation_kw: float
    islanded_deficit_kw: float
    boundary_edge_ids: tuple[str, ...]
    selection_rule: str


@dataclass(frozen=True)
class UpgradeOption:
    """One published-cost capacity option sized from the benchmark deficit."""

    technology: str
    capacity_kw: float
    energy_kwh: float
    power_kw: float
    unit_cost_per_kw: float
    unit_cost_per_kwh: float | None
    total_cost: float
    source_row: str
    sizing_rule: str


@dataclass(frozen=True)
class UpgradePlan:
    """Upgrade menu and nonzero adequacy requirement for one patch."""

    patch: UpgradePatch
    options: tuple[UpgradeOption, ...]
    minimum_resilient_upgrade_cost: float
    maximum_upgrade_cost: float


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 digest of a local public source."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_atb_cost_catalog(path: Path | str) -> dict[str, TechnologyCost]:
    """Load the pinned, selected-row NREL ATB cost snapshot."""

    catalog: dict[str, TechnologyCost] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            technology = str(row["technology"])
            catalog[technology] = TechnologyCost(
                technology=technology,
                cost_per_kw=float(row["cost_per_kw_2022_usd"]),
                cost_per_kwh=float(row["cost_per_kwh_2022_usd"]) if row.get("cost_per_kwh_2022_usd") else None,
                duration_hours=float(row["duration_hours"]) if row.get("duration_hours") else None,
                source_row=str(row["source_row"]),
                source_url=str(row["source_url"]),
                source_version=str(row["source_version"]),
                source_sha256=str(row["source_sha256"]),
                transformation=str(row["transformation"]),
            )
    required = {"pv", "bess", "dispatchable_generation"}
    missing = required - set(catalog)
    if missing:
        raise ValueError(f"NREL ATB catalog is missing technologies: {sorted(missing)}")
    if any(item.cost_per_kw <= 0.0 for item in catalog.values()):
        raise ValueError("NREL ATB costs must be positive")
    return catalog


def _neighbors(grid: PublicGridData) -> dict[str, set[str]]:
    adjacency = {node.node_id: set() for node in grid.nodes}
    for edge in grid.edges:
        if not edge.in_service:
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)
    return adjacency


def _stable_tiebreak(seed: int, node_id: str) -> str:
    return hashlib.sha256(f"{seed}:{node_id}".encode("utf-8")).hexdigest()


def select_upgrade_patches(
    grid: PublicGridData,
    *,
    count: int,
    patch_size: int,
    deterministic_seed: int,
) -> list[UpgradePatch]:
    """Select connected load-heavy islands without sampling or invented values."""

    if count <= 0 or patch_size <= 0:
        raise ValueError("count and patch_size must be positive")
    by_id = {node.node_id: node for node in grid.nodes}
    adjacency = _neighbors(grid)
    anchors = sorted(
        (node for node in grid.nodes if node.load_kw > node.generation_kw and node.load_kw > 0.0),
        key=lambda node: (
            -(node.load_kw - node.generation_kw),
            -node.load_kw,
            _stable_tiebreak(deterministic_seed, node.node_id),
            node.node_id,
        ),
    )
    patches: list[UpgradePatch] = []
    seen: set[tuple[str, ...]] = set()
    for anchor in anchors:
        selected = [anchor.node_id]
        frontier = set(adjacency.get(anchor.node_id, set()))
        while len(selected) < patch_size and frontier:
            candidates = sorted(
                (by_id[node_id] for node_id in frontier if node_id in by_id and node_id not in selected),
                key=lambda node: (
                    -(node.load_kw - node.generation_kw),
                    -node.load_kw,
                    _stable_tiebreak(deterministic_seed, node.node_id),
                    node.node_id,
                ),
            )
            if not candidates:
                break
            candidate = candidates[0]
            selected.append(candidate.node_id)
            frontier.remove(candidate.node_id)
            frontier.update(adjacency.get(candidate.node_id, set()) - set(selected))
        node_ids = tuple(sorted(selected))
        if node_ids in seen:
            continue
        load_kw = sum(by_id[node_id].load_kw for node_id in node_ids)
        generation_kw = sum(by_id[node_id].generation_kw for node_id in node_ids)
        deficit_kw = max(0.0, load_kw - generation_kw)
        if deficit_kw <= 0.0:
            continue
        selected_set = set(node_ids)
        boundary = tuple(
            sorted(
                edge.edge_id
                for edge in grid.edges
                if edge.in_service and ((edge.source in selected_set) != (edge.target in selected_set))
            )
        )
        patches.append(
            UpgradePatch(
                patch_id=f"{grid.benchmark}__patch_{len(patches) + 1:02d}__{'-'.join(node_ids)}",
                node_ids=node_ids,
                load_kw=load_kw,
                existing_generation_kw=generation_kw,
                islanded_deficit_kw=deficit_kw,
                boundary_edge_ids=boundary,
                selection_rule=(
                    "highest public nominal active-load deficit anchor; expand through in-service public topology; "
                    f"SHA-256 seed={deterministic_seed} used only for deterministic tie-breaking"
                ),
            )
        )
        seen.add(node_ids)
        if len(patches) >= count:
            break
    if not patches:
        raise ValueError(f"{grid.benchmark} has no connected public-data patch with an islanded supply deficit")
    return patches


def build_upgrade_plan(patch: UpgradePatch, catalog: dict[str, TechnologyCost]) -> UpgradePlan:
    """Size three comparable upgrade choices directly from the public-load deficit."""

    deficit = patch.islanded_deficit_kw
    if deficit <= 0.0:
        raise ValueError("SC-CMPO requires a positive pre-upgrade islanded deficit")
    pv = catalog["pv"]
    bess = catalog["bess"]
    generator = catalog["dispatchable_generation"]
    duration = bess.duration_hours
    if duration is None or duration <= 0.0:
        raise ValueError("BESS cost record must define a positive duration")
    options = (
        UpgradeOption(
            technology="pv",
            capacity_kw=deficit,
            energy_kwh=0.0,
            power_kw=deficit,
            unit_cost_per_kw=pv.cost_per_kw,
            unit_cost_per_kwh=None,
            total_cost=deficit * pv.cost_per_kw,
            source_row=pv.source_row,
            sizing_rule="PV nameplate upper bound equals the benchmark-derived islanded active-power deficit.",
        ),
        UpgradeOption(
            technology="bess",
            capacity_kw=deficit,
            energy_kwh=deficit * duration,
            power_kw=deficit,
            unit_cost_per_kw=bess.cost_per_kw,
            unit_cost_per_kwh=bess.cost_per_kwh,
            total_cost=deficit * bess.cost_per_kw,
            source_row=bess.source_row,
            sizing_rule=(
                f"BESS power equals the benchmark deficit and energy equals the published {duration:g}-hour duration."
            ),
        ),
        UpgradeOption(
            technology="dispatchable_generation",
            capacity_kw=deficit,
            energy_kwh=0.0,
            power_kw=deficit,
            unit_cost_per_kw=generator.cost_per_kw,
            unit_cost_per_kwh=None,
            total_cost=deficit * generator.cost_per_kw,
            source_row=generator.source_row,
            sizing_rule="Dispatchable nameplate upper bound equals the benchmark-derived islanded active-power deficit.",
        ),
    )
    # PV is unavailable in the renewable-shortfall and combined-stress recourse blocks.
    resilient_candidates = [option.total_cost for option in options if option.technology != "pv"]
    return UpgradePlan(
        patch=patch,
        options=options,
        minimum_resilient_upgrade_cost=min(resilient_candidates),
        maximum_upgrade_cost=sum(option.total_cost for option in options),
    )
