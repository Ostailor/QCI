"""Hard-budget portfolio construction for reconstructed SC-CMPO systems."""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

from cmpo.matched_problem_baselines import _compile_payload, _fractions_to_values
from cmpo.upgrade_budget import UpgradeAssetOption, technology_cost_totals


class BudgetExceededError(ValueError):
    """Raised when a reconstructed physical portfolio exceeds its hard cap."""


def deduplicate_upgrade_assets(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Charge each physical asset once, retaining its maximum installed size."""

    merged: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = copy.deepcopy(dict(raw))
        key = str(row["asset_key"])
        cost = float(row["installed_cost"])
        if not math.isfinite(cost) or cost < 0.0:
            raise ValueError(f"invalid installed cost for {key}: {cost}")
        row.setdefault("source_payload_ids", [])
        existing = merged.get(key)
        if existing is None:
            row["source_payload_ids"] = sorted(set(row["source_payload_ids"]))
            merged[key] = row
            continue
        sources = set(existing.get("source_payload_ids", ())) | set(row.get("source_payload_ids", ()))
        if cost > float(existing["installed_cost"]):
            row["source_payload_ids"] = sorted(sources)
            merged[key] = row
        else:
            existing["source_payload_ids"] = sorted(sources)
    return [merged[key] for key in sorted(merged)]


def enforce_hard_budget(
    rows: Sequence[Mapping[str, Any]],
    budget: float,
    *,
    tolerance: float = 1e-6,
) -> float:
    """Return charge-once portfolio cost or reject an over-budget reconstruction."""

    if not math.isfinite(budget) or budget < 0.0:
        raise ValueError("budget must be finite and nonnegative")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and nonnegative")
    cost = math.fsum(float(row["installed_cost"]) for row in deduplicate_upgrade_assets(rows))
    if cost > budget + tolerance:
        raise BudgetExceededError(
            f"reconstructed portfolio cost {cost:.9f} exceeds hard budget {budget:.9f}"
        )
    return min(cost, budget)


def portfolio_from_shared_fractions(
    catalog: Sequence[UpgradeAssetOption],
    fractions: Mapping[str, float],
) -> list[dict[str, Any]]:
    """Materialize one charge-once physical portfolio from shared technology fractions."""

    rows: list[dict[str, Any]] = []
    for asset in catalog:
        fraction = min(1.0, max(0.0, float(fractions.get(asset.technology, 0.0))))
        if fraction <= 1e-12:
            continue
        rows.append(
            {
                "asset_key": asset.asset_key,
                "benchmark": asset.benchmark,
                "anchor_node": asset.anchor_node,
                "technology": asset.technology,
                "installed_fraction": fraction,
                "installed_cost": asset.total_cost * fraction,
                "installed_capacity_kw": asset.capacity_kw * fraction,
                "installed_power_kw": asset.power_kw * fraction,
                "installed_energy_kwh": asset.energy_kwh * fraction,
                "source_row": asset.source_row,
                "source_payload_ids": list(asset.source_payload_ids),
                "source_patch_ids": list(asset.source_patch_ids),
                "deduplication_rule": "one physical benchmark-anchor/technology asset charged once",
            }
        )
    return deduplicate_upgrade_assets(rows)


def allocate_shared_fractions(
    catalog: Sequence[UpgradeAssetOption],
    budget: float,
    *,
    preference: Mapping[str, float],
    priority: Sequence[str] = ("dispatchable_generation", "bess", "pv"),
) -> dict[str, float]:
    """Project a method preference onto the common hard budget.

    A full dispatchable portfolio is installed first because it is the catalog's
    minimum feasible islanding portfolio.  Remaining dollars follow the method's
    normalized technology preference and deterministic priority order.
    """

    totals = technology_cost_totals(catalog)
    minimum = totals["dispatchable_generation"]
    if budget + 1e-6 < minimum:
        raise BudgetExceededError(
            f"budget {budget:.9f} is below minimum feasible islanding cost {minimum:.9f}"
        )
    fractions = {technology: 0.0 for technology in totals}
    fractions["dispatchable_generation"] = 1.0
    remaining = max(0.0, budget - minimum)
    ordered = [technology for technology in priority if technology != "dispatchable_generation"]
    ordered.sort(key=lambda technology: (-float(preference.get(technology, 0.0)), priority.index(technology)))
    for technology in ordered:
        desired = min(1.0, max(0.0, float(preference.get(technology, 0.0))))
        spend = min(remaining, totals[technology] * desired)
        fractions[technology] = spend / totals[technology] if totals[technology] > 0.0 else 0.0
        remaining -= spend
    if remaining > 1e-9:
        for technology in ordered:
            headroom = totals[technology] * (1.0 - fractions[technology])
            spend = min(remaining, headroom)
            fractions[technology] += spend / totals[technology] if totals[technology] > 0.0 else 0.0
            remaining -= spend
            if remaining <= 1e-9:
                break
    portfolio = portfolio_from_shared_fractions(catalog, fractions)
    enforce_hard_budget(portfolio, budget)
    return fractions


def build_budgeted_patch_values(
    payloads: Mapping[str, Mapping[str, Any]],
    fractions: Mapping[str, float],
) -> dict[str, dict[str, float]]:
    """Create complete patch vectors with identical shared first-stage fractions."""

    vector = (
        float(fractions.get("pv", 0.0)),
        float(fractions.get("bess", 0.0)),
        float(fractions.get("dispatchable_generation", 0.0)),
    )
    result: dict[str, dict[str, float]] = {}
    for name, payload in payloads.items():
        compiled = _compile_payload(payload)
        result[name] = _fractions_to_values(payload, compiled, vector)
    return result
