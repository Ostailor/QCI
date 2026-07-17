"""Deterministic uniqueness and diversity selection for master portfolios."""

from __future__ import annotations

from typing import Sequence

from cmpo.portfolio_decode import DecodedPortfolio


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
