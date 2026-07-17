"""Dominance certificates for the global budget-master penalty."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PenaltyCertificate:
    maximum_nonbudget_objective_variation: float
    minimum_encoded_budget_violation: int
    required_lower_bound_on_rho_budget: float
    rho_budget: float
    safety_multiplier: float
    minimum_violation_penalty: float
    passed: bool
    bound_method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def nonbudget_variation_bound(terms: Sequence[Mapping[str, Any]]) -> float:
    """Bound binary-polynomial variation by the coefficient absolute sum."""

    values = [
        abs(float(term.get("coefficient", 0.0)))
        for term in terms
        if term.get("powers") and str(term.get("component", "")) != "hard_budget"
    ]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("non-budget polynomial coefficients must be finite")
    return float(math.fsum(values))


def build_penalty_certificate(
    terms: Sequence[Mapping[str, Any]], *, safety_multiplier: float = 2.0
) -> PenaltyCertificate:
    if not math.isfinite(safety_multiplier) or safety_multiplier <= 1.0:
        raise ValueError("penalty safety multiplier must exceed one")
    variation = nonbudget_variation_bound(terms)
    required = math.nextafter(variation, math.inf)
    rho = float(safety_multiplier * max(variation, 1.0))
    minimum_penalty = rho
    return PenaltyCertificate(
        maximum_nonbudget_objective_variation=variation,
        minimum_encoded_budget_violation=1,
        required_lower_bound_on_rho_budget=required,
        rho_budget=rho,
        safety_multiplier=float(safety_multiplier),
        minimum_violation_penalty=minimum_penalty,
        passed=bool(minimum_penalty > variation and rho >= required),
        bound_method=(
            "sum of absolute non-budget coefficients; every binary monomial lies in [0,1]"
        ),
    )
