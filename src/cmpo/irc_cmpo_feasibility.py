"""Exact cubic local-feasibility encoding for the IEEE 123 IRC-CMPO master."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from cmpo.irc_cmpo_master import IRCAsset


TECHNOLOGIES = ("pv", "bess", "dispatchable_generation")
_TOLERANCE = 1e-9


@dataclass(frozen=True)
class LocalPattern:
    pattern: tuple[int, int, int]
    adequate: bool
    minimum_available_capacity_kw: float
    binding_scenarios: tuple[str, ...]


@dataclass(frozen=True)
class FeasibilityTerm:
    coefficient: float
    powers: tuple[str, ...]
    degree: int
    anchor_node: str
    invalid_pattern: tuple[int, int, int]

    def to_payload_term(self) -> dict[str, Any]:
        return {
            "coefficient": self.coefficient,
            "powers": {name: 1 for name in self.powers},
            "degree": self.degree,
            "component": "local_feasibility",
            "anchor_node": self.anchor_node,
            "invalid_pattern": list(self.invalid_pattern),
        }


@dataclass(frozen=True)
class AnchorFeasibility:
    anchor_node: str
    base_load_kw: float
    existing_generation_kw: float
    islanded_base_load_shortfall_kw: float
    asset_keys: tuple[str, str, str]
    patterns: tuple[LocalPattern, ...]
    penalty_terms: tuple[FeasibilityTerm, ...]
    rho_feasibility: float
    source_patch_ids: tuple[str, ...]

    @property
    def invalid_patterns(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(row.pattern for row in self.patterns if not row.adequate)


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    nodes = payload["sc_cmpo"].get("patch_public_nodes", ())
    if nodes:
        return sorted(
            (
                (
                    float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                    float(node.get("load_kw", 0.0)),
                    str(node["node_id"]),
                )
                for node in nodes
            ),
            key=lambda row: (-row[0], -row[1], row[2]),
        )[0][2]
    return sorted(str(node) for node in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])[0]


def _indicator_expansion(
    anchor: str,
    asset_keys: tuple[str, str, str],
    pattern: tuple[int, int, int],
    rho: float,
) -> list[FeasibilityTerm]:
    """Expand rho * product(y_j if p_j else 1-y_j) exactly."""

    terms: dict[tuple[str, ...], float] = {(): rho}
    for asset_key, bit in zip(asset_keys, pattern, strict=True):
        expanded: dict[tuple[str, ...], float] = {}
        for powers, coefficient in terms.items():
            if bit:
                new_powers = tuple(sorted((*powers, asset_key)))
                expanded[new_powers] = math.fsum((expanded.get(new_powers, 0.0), coefficient))
            else:
                expanded[powers] = math.fsum((expanded.get(powers, 0.0), coefficient))
                new_powers = tuple(sorted((*powers, asset_key)))
                expanded[new_powers] = math.fsum((expanded.get(new_powers, 0.0), -coefficient))
        terms = expanded
    return [
        FeasibilityTerm(coefficient, powers, len(powers), anchor, pattern)
        for powers, coefficient in sorted(terms.items(), key=lambda item: (len(item[0]), item[0]))
        if abs(coefficient) > _TOLERANCE
    ]


def derive_local_feasibility(
    payloads: Mapping[str, Mapping[str, Any]],
    assets: Sequence[IRCAsset],
    *,
    rho_feasibility: float,
) -> tuple[AnchorFeasibility, ...]:
    """Derive exact inadequate technology patterns from pinned public records."""

    if not math.isfinite(rho_feasibility) or rho_feasibility <= 0.0:
        raise ValueError("rho_feasibility must be finite and positive")
    assets_by_anchor: dict[str, dict[str, IRCAsset]] = {}
    for asset in assets:
        assets_by_anchor.setdefault(asset.anchor_node, {})[asset.technology] = asset
    payloads_by_anchor: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for name, payload in payloads.items():
        payloads_by_anchor.setdefault(_physical_anchor(payload), []).append((str(name), payload))
    if set(assets_by_anchor) != set(payloads_by_anchor):
        raise ValueError("public payload anchors and upgrade-catalog anchors differ")

    result: list[AnchorFeasibility] = []
    for anchor in sorted(assets_by_anchor):
        technology_assets = assets_by_anchor[anchor]
        if set(technology_assets) != set(TECHNOLOGIES):
            raise ValueError(f"anchor {anchor} lacks a complete public technology catalog")
        records = payloads_by_anchor[anchor]
        base_load = max(float(payload["sc_cmpo"]["upgrade_patch"]["load_kw"]) for _, payload in records)
        existing = max(
            float(payload["sc_cmpo"]["upgrade_patch"].get("existing_generation_kw", 0.0))
            for _, payload in records
        )
        asset_keys = tuple(technology_assets[name].asset_key for name in TECHNOLOGIES)
        pattern_rows: list[LocalPattern] = []
        invalid_patterns: list[tuple[int, int, int]] = []
        for raw_pattern in itertools.product((0, 1), repeat=3):
            pattern = tuple(int(value) for value in raw_pattern)
            scenario_capacities: list[tuple[str, float, float]] = []
            for _payload_name, payload in records:
                for scenario in payload["scenario_metadata"]["scenarios"]:
                    if bool(scenario.get("pcc_available", False)) and not bool(
                        scenario.get("forced_islanding", False)
                    ):
                        continue
                    required = float(scenario.get("load_requirement_kw", base_load))
                    capacity = existing if bool(scenario.get("existing_generation_available", True)) else 0.0
                    if pattern[0] and bool(scenario.get("pv_available", True)):
                        capacity += technology_assets["pv"].capacity_kw
                    if pattern[1]:
                        capacity += technology_assets["bess"].power_kw
                    if pattern[2]:
                        capacity += technology_assets["dispatchable_generation"].capacity_kw
                    scenario_capacities.append((str(scenario["name"]), capacity, required))
            if not scenario_capacities:
                scenario_capacities.append(("base_island", existing, base_load))
            adequate = all(capacity + _TOLERANCE >= required for _, capacity, required in scenario_capacities)
            minimum_capacity = min(capacity for _, capacity, _ in scenario_capacities)
            minimum_margin = min(capacity - required for _, capacity, required in scenario_capacities)
            binding = tuple(
                sorted(
                    {
                        name
                        for name, capacity, required in scenario_capacities
                        if abs((capacity - required) - minimum_margin) <= _TOLERANCE
                    }
                )
            )
            pattern_rows.append(LocalPattern(pattern, adequate, minimum_capacity, binding))
            if not adequate:
                invalid_patterns.append(pattern)
        terms = tuple(
            term
            for pattern in invalid_patterns
            for term in _indicator_expansion(anchor, asset_keys, pattern, rho_feasibility)
        )
        result.append(
            AnchorFeasibility(
                anchor_node=anchor,
                base_load_kw=base_load,
                existing_generation_kw=existing,
                islanded_base_load_shortfall_kw=max(0.0, base_load - existing),
                asset_keys=asset_keys,
                patterns=tuple(pattern_rows),
                penalty_terms=terms,
                rho_feasibility=float(rho_feasibility),
                source_patch_ids=tuple(
                    sorted(
                        str(payload["sc_cmpo"]["upgrade_patch"]["patch_id"])
                        for _, payload in records
                    )
                ),
            )
        )
    return tuple(result)


def _encoded_penalty(anchor: AnchorFeasibility, pattern: tuple[int, int, int]) -> float:
    selected = dict(zip(anchor.asset_keys, pattern, strict=True))
    return math.fsum(
        term.coefficient * math.prod(selected[name] for name in term.powers)
        for term in anchor.penalty_terms
    )


def verify_local_feasibility_encoding(anchor: AnchorFeasibility) -> bool:
    """Exhaustively verify polynomial penalties against direct enumeration."""

    expected = {row.pattern: row for row in anchor.patterns}
    if set(expected) != set(itertools.product((0, 1), repeat=3)):
        return False
    if any(term.degree > 3 for term in anchor.penalty_terms):
        return False
    for pattern, row in expected.items():
        target = anchor.rho_feasibility if not row.adequate else 0.0
        if not math.isclose(_encoded_penalty(anchor, pattern), target, abs_tol=1e-8):
            return False
    return True


def ineffective_assets(effects: Mapping[str, Any]) -> tuple[str, ...]:
    """Return assets that must be removed because no public recourse effect exists."""

    return tuple(sorted(key for key, effect in effects.items() if not bool(effect.measurable)))


__all__ = [
    "AnchorFeasibility",
    "FeasibilityTerm",
    "LocalPattern",
    "derive_local_feasibility",
    "ineffective_assets",
    "verify_local_feasibility_encoding",
]
