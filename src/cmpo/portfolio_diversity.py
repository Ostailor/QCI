"""Deterministic uniqueness and diversity selection for master portfolios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from typing import Sequence

from cmpo.portfolio_decode import DecodedPortfolio


@dataclass(frozen=True)
class ScoredPortfolio:
    portfolio: DecodedPortfolio
    critical_service_proxy: float
    reserve_preparedness: float
    estimated_recourse_score: float
    upgrade_utilization: float
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def quality_key(self) -> tuple[float, float, float, float, float]:
        return (
            float(self.critical_service_proxy),
            float(self.reserve_preparedness),
            float(self.estimated_recourse_score),
            float(self.upgrade_utilization),
            -float(self.portfolio.energy),
        )


def hamming_distance(left: DecodedPortfolio, right: DecodedPortfolio) -> int:
    return len(set(left.selected_asset_keys) ^ set(right.selected_asset_keys))


def select_unique_feasible_portfolios(
    portfolios: Sequence[DecodedPortfolio], *, limit: int = 10
) -> list[DecodedPortfolio]:
    if limit <= 0:
        raise ValueError("portfolio limit must be positive")
    best_by_signature: dict[tuple[str, ...], DecodedPortfolio] = {}
    for portfolio in portfolios:
        if not portfolio.feasible:
            continue
        key = portfolio.selected_asset_keys
        current = best_by_signature.get(key)
        if current is None or (portfolio.energy, portfolio.total_upgrade_cost) < (
            current.energy,
            current.total_upgrade_cost,
        ):
            best_by_signature[key] = portfolio
    candidates = sorted(
        best_by_signature.values(),
        key=lambda item: (item.energy, item.total_upgrade_cost, item.selected_asset_keys),
    )
    if len(candidates) <= limit:
        return candidates
    selected = [candidates.pop(0)]
    while candidates and len(selected) < limit:
        candidate = max(
            candidates,
            key=lambda item: (
                min(hamming_distance(item, chosen) for chosen in selected),
                -item.energy,
                item.selected_asset_keys,
            ),
        )
        selected.append(candidate)
        candidates.remove(candidate)
    return selected


def select_scored_diverse_portfolios(
    candidates: Sequence[ScoredPortfolio], *, limit: int = 10
) -> list[ScoredPortfolio]:
    """Select unique feasible portfolios in the documented challenge order."""

    if limit <= 0:
        raise ValueError("portfolio limit must be positive")
    best_by_assets: dict[tuple[str, ...], ScoredPortfolio] = {}
    for candidate in candidates:
        if not candidate.portfolio.feasible:
            continue
        assets = candidate.portfolio.selected_asset_keys
        current = best_by_assets.get(assets)
        if current is None or candidate.quality_key > current.quality_key:
            best_by_assets[assets] = candidate
    remaining = list(best_by_assets.values())
    selected: list[ScoredPortfolio] = []
    while remaining and len(selected) < limit:
        candidate = max(
            remaining,
            key=lambda item: (
                item.quality_key,
                min(
                    (
                        hamming_distance(item.portfolio, chosen.portfolio)
                        for chosen in selected
                    ),
                    default=len(item.portfolio.selected_asset_keys),
                ),
                item.portfolio.selected_asset_keys,
            ),
        )
        selected.append(candidate)
        remaining.remove(candidate)
    return selected
