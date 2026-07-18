"""Constraint and numerical-audit primitives for IRC-CMPO integer masters."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence


IMPORTANT_COMPONENTS = frozenset({"surrogate", "interaction", "normalized_cost", "coverage"})


@dataclass(frozen=True)
class CoefficientAudit:
    passed: bool
    maximum_nonzero: float
    minimum_nonzero: float
    dynamic_range: float
    effective_maximum_nonzero: float
    effective_minimum_nonzero: float
    effective_dynamic_range: float
    family_statistics: dict[str, dict[str, float | int]]
    degree_distribution: dict[int, int]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def coverage_penalty_terms(
    anchor: str,
    variables_by_technology: Mapping[str, str],
    rho: float,
) -> list[dict[str, Any]]:
    """Expand rho(1-pv)(1-bess)(1-gen) without auxiliary variables."""

    if not math.isfinite(rho) or rho <= 0.0:
        raise ValueError("coverage penalty rho must be finite and positive")
    required = ("pv", "bess", "dispatchable_generation")
    if set(variables_by_technology) != set(required):
        raise ValueError(f"anchor {anchor} must expose exactly PV, BESS, and dispatchable generation")
    pv, bess, gen = (variables_by_technology[name] for name in required)
    specs = (
        (rho, ()),
        (-rho, (pv,)),
        (-rho, (bess,)),
        (-rho, (gen,)),
        (rho, (pv, bess)),
        (rho, (pv, gen)),
        (rho, (bess, gen)),
        (-rho, (pv, bess, gen)),
    )
    return [
        {
            "coefficient": float(coefficient),
            "powers": {name: 1 for name in names},
            "degree": len(names),
            "component": "coverage",
            "anchor_node": str(anchor),
        }
        for coefficient, names in specs
    ]


def uncovered_anchors(
    selected_asset_keys: Iterable[str],
    assets: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    selected = set(selected_asset_keys)
    anchors = {str(asset["anchor_node"]) for asset in assets}
    covered = {
        str(asset["anchor_node"])
        for asset in assets
        if str(asset["asset_key"]) in selected
    }
    return tuple(sorted(anchors - covered))


def audit_coefficients(
    terms: Sequence[Mapping[str, Any]],
    *,
    collapsed_threshold: float = 1e-12,
    maximum_dynamic_range: float = 1e12,
) -> CoefficientAudit:
    """Reject silent coefficient collapse and report family/degree statistics."""

    family_values: dict[str, list[float]] = {}
    monomial_values: dict[tuple[tuple[str, int], ...], list[float]] = {}
    degree_distribution: dict[int, int] = {}
    reasons: list[str] = []
    for term in terms:
        value = float(term["coefficient"])
        if not math.isfinite(value):
            reasons.append("non-finite coefficient")
            continue
        degree = int(term.get("degree", sum(int(v) for v in term.get("powers", {}).values())))
        degree_distribution[degree] = degree_distribution.get(degree, 0) + 1
        if value != 0.0:
            family_values.setdefault(str(term.get("component", "unclassified")), []).append(abs(value))
            monomial = tuple(sorted((str(name), int(power)) for name, power in term.get("powers", {}).items()))
            monomial_values.setdefault(monomial, []).append(value)
    values = [value for family in family_values.values() for value in family]
    maximum = max(values, default=0.0)
    minimum = min(values, default=0.0)
    ratio = maximum / minimum if minimum else math.inf
    if not values:
        reasons.append("polynomial has no finite nonzero coefficients")
    if ratio > maximum_dynamic_range:
        reasons.append(f"coefficient dynamic range {ratio:.6g} exceeds {maximum_dynamic_range:.6g}")
    for family, family_coefficients in sorted(family_values.items()):
        if family in IMPORTANT_COMPONENTS and min(family_coefficients) < collapsed_threshold:
            reasons.append(
                f"important coefficient family {family} collapses below {collapsed_threshold:.1e}"
            )
    effective_values: list[float] = []
    for monomial, contributions in monomial_values.items():
        effective = math.fsum(contributions)
        if abs(effective) < collapsed_threshold and max(map(abs, contributions)) >= collapsed_threshold:
            reasons.append(
                f"effective submitted coefficient for monomial {dict(monomial)} collapses through cancellation"
            )
        elif effective != 0.0:
            effective_values.append(abs(effective))
    effective_maximum = max(effective_values, default=0.0)
    effective_minimum = min(effective_values, default=0.0)
    effective_ratio = (
        effective_maximum / effective_minimum if effective_minimum else math.inf
    )
    if effective_values and effective_ratio > maximum_dynamic_range:
        reasons.append(
            f"effective submitted coefficient dynamic range {effective_ratio:.6g} exceeds {maximum_dynamic_range:.6g}"
        )
    statistics = {
        family: {
            "count": len(coefficients),
            "minimum_nonzero": min(coefficients),
            "maximum_nonzero": max(coefficients),
            "median_nonzero": sorted(coefficients)[len(coefficients) // 2],
        }
        for family, coefficients in sorted(family_values.items())
    }
    return CoefficientAudit(
        passed=not reasons,
        maximum_nonzero=maximum,
        minimum_nonzero=minimum,
        dynamic_range=ratio,
        effective_maximum_nonzero=effective_maximum,
        effective_minimum_nonzero=effective_minimum,
        effective_dynamic_range=effective_ratio,
        family_statistics=statistics,
        degree_distribution=dict(sorted(degree_distribution.items())),
        reasons=tuple(dict.fromkeys(reasons)),
    )
