"""Conservative integer encoding and validation for hard upgrade budgets."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, MutableSequence, Sequence


@dataclass(frozen=True)
class CurrencyEncoding:
    unit: float
    maximum_slack_bit_count: int
    fixed_variable_count: int
    maximum_variable_count: int
    minimum_normalized_violation_resolution: float
    worst_case_normalized_violation_proxy: float
    selection_rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BudgetEncoding:
    unit: float
    actual_budget: float
    encoded_budget: int
    encoded_costs: dict[str, int]
    slack_bit_weights: tuple[int, ...]
    maximum_per_asset_upward_rounding: float
    maximum_portfolio_conservatism: float

    @property
    def slack_bit_count(self) -> int:
        return len(self.slack_bit_weights)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "slack_bit_weights": list(self.slack_bit_weights),
            "slack_bit_count": self.slack_bit_count,
            "rounding_guarantee": (
                "asset costs are rounded upward and the budget downward; "
                "encoded feasibility cannot permit a real-dollar overrun"
            ),
        }


@dataclass(frozen=True)
class BudgetCheck:
    passed: bool
    measured: float
    limit: float
    reason: str


@dataclass(frozen=True)
class BudgetPayloadValidation:
    passed: bool
    budget_present_in_metadata: bool
    budget_present_in_polynomial: bool
    budget_polynomial_term_count: int
    failure_reason: str


def _slack_bit_count(encoded_budget: int) -> int:
    if encoded_budget < 0:
        raise ValueError("encoded budget must be nonnegative")
    return max(1, int(math.ceil(math.log2(encoded_budget + 1))))


def _ceil_units(value: float, unit: float) -> int:
    quotient = float(value) / unit
    nearest = round(quotient)
    return int(nearest if abs(quotient - nearest) <= 1e-9 else math.ceil(quotient))


def _floor_units(value: float, unit: float) -> int:
    quotient = float(value) / unit
    nearest = round(quotient)
    return int(nearest if abs(quotient - nearest) <= 1e-9 else math.floor(quotient))


def choose_currency_unit(
    costs: Sequence[float],
    budgets: Sequence[float],
    *,
    fixed_variables: int,
    max_variables: int = 132,
    minimum_normalized_violation_resolution: float = 1e-12,
    candidate_units: Sequence[float] = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0),
    required_portfolio_costs: Sequence[Sequence[float]] = (),
) -> CurrencyEncoding:
    """Choose the smallest unit satisfying size and numerical-resolution gates."""

    if fixed_variables < 0 or max_variables <= 0:
        raise ValueError("variable counts must be nonnegative and bounded")
    if (
        not math.isfinite(minimum_normalized_violation_resolution)
        or minimum_normalized_violation_resolution <= 0.0
    ):
        raise ValueError("minimum normalized violation resolution must be finite and positive")
    values = [float(value) for value in (*costs, *budgets)]
    if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("costs and budgets must be finite and nonnegative")
    candidates = sorted({float(unit) for unit in candidate_units})
    if not candidates or any(not math.isfinite(unit) or unit <= 0.0 for unit in candidates):
        raise ValueError("candidate currency units must be finite and positive")
    for unit in candidates:
        encoded_budgets = [_floor_units(float(budget), unit) for budget in budgets]
        maximum = max(_slack_bit_count(value) for value in encoded_budgets)
        worst_case_budget = max(encoded_budgets)
        resolution_proxy = 1.0 / max(float(worst_case_budget) ** 2, 1.0)
        required_feasible = all(
            sum(_ceil_units(float(cost), unit) for cost in portfolio)
            <= min(encoded_budgets)
            for portfolio in required_portfolio_costs
        )
        if (
            fixed_variables + maximum <= max_variables
            and resolution_proxy >= minimum_normalized_violation_resolution
            and required_feasible
        ):
            return CurrencyEncoding(
                unit=unit,
                maximum_slack_bit_count=maximum,
                fixed_variable_count=fixed_variables,
                maximum_variable_count=fixed_variables + maximum,
                minimum_normalized_violation_resolution=minimum_normalized_violation_resolution,
                worst_case_normalized_violation_proxy=resolution_proxy,
                selection_rule=(
                    "smallest standard currency denomination, beginning at one cent, "
                    "whose worst-case slack encoding remains within the 132-variable limit and whose "
                    "1/(largest encoded budget)^2 separation proxy meets the configured double-precision "
                    "floor while retaining an encoded-feasible minimum anchor-covering portfolio"
                ),
            )
    raise ValueError("no supported currency unit satisfies the QCi variable limit")


def encode_budget(costs: Mapping[str, float], budget: float, unit: float) -> BudgetEncoding:
    if not math.isfinite(unit) or unit <= 0.0:
        raise ValueError("currency unit must be finite and positive")
    if not math.isfinite(budget) or budget < 0.0:
        raise ValueError("budget must be finite and nonnegative")
    encoded_costs: dict[str, int] = {}
    rounding: list[float] = []
    for key, raw in sorted(costs.items()):
        cost = float(raw)
        if not math.isfinite(cost) or cost < 0.0:
            raise ValueError(f"invalid asset cost for {key}: {cost}")
        encoded = _ceil_units(cost, unit)
        encoded_costs[str(key)] = encoded
        rounding.append(encoded * unit - cost)
    encoded_budget = _floor_units(float(budget), unit)
    count = _slack_bit_count(encoded_budget)
    return BudgetEncoding(
        unit=float(unit),
        actual_budget=float(budget),
        encoded_budget=encoded_budget,
        encoded_costs=encoded_costs,
        slack_bit_weights=tuple(1 << index for index in range(count)),
        maximum_per_asset_upward_rounding=max(rounding, default=0.0),
        maximum_portfolio_conservatism=math.fsum(rounding),
    )


def validate_encoded_cost(encoded_cost: int, encoding: BudgetEncoding) -> BudgetCheck:
    passed = int(encoded_cost) <= encoding.encoded_budget
    return BudgetCheck(
        passed=passed,
        measured=float(encoded_cost),
        limit=float(encoding.encoded_budget),
        reason="encoded cost is within budget" if passed else "encoded cost exceeds budget",
    )


def validate_actual_cost(actual_cost: float, budget: float, *, tolerance: float = 1e-9) -> BudgetCheck:
    cost = float(actual_cost)
    limit = float(budget)
    passed = math.isfinite(cost) and cost <= limit + tolerance
    return BudgetCheck(
        passed=passed,
        measured=cost,
        limit=limit,
        reason="actual cost is within budget" if passed else "actual-dollar cost exceeds budget",
    )


def add_squared_equality_terms(
    terms: MutableSequence[dict[str, Any]],
    weights: Mapping[str, int | float],
    rhs: int | float,
    rho: float,
    *,
    component: str,
) -> None:
    """Append the binary-reduced expansion of ``rho * (w*x - rhs)^2``."""

    ordered = [(str(name), float(weight)) for name, weight in sorted(weights.items())]
    right = float(rhs)
    terms.append(
        {
            "coefficient": float(rho * right * right),
            "powers": {},
            "degree": 0,
            "component": component,
        }
    )
    for index, (name, weight) in enumerate(ordered):
        terms.append(
            {
                "coefficient": float(rho * (weight * weight - 2.0 * right * weight)),
                "powers": {name: 1},
                "degree": 1,
                "component": component,
            }
        )
        for other_name, other_weight in ordered[index + 1 :]:
            terms.append(
                {
                    "coefficient": float(2.0 * rho * weight * other_weight),
                    "powers": {name: 1, other_name: 1},
                    "degree": 2,
                    "component": component,
                }
            )


def validate_budget_payload(payload: Mapping[str, Any]) -> BudgetPayloadValidation:
    metadata = payload.get("budget_constraint") or payload.get("budget_encoding")
    terms = list(payload.get("polynomial_terms", ()))
    budget_terms = [term for term in terms if str(term.get("component", "")) == "hard_budget"]
    finite = all(math.isfinite(float(term.get("coefficient", math.nan))) for term in budget_terms)
    polynomial = bool(budget_terms) and finite
    metadata_present = bool(metadata)
    passed = metadata_present and polynomial
    if not metadata_present:
        reason = "hard budget metadata is missing"
    elif not budget_terms:
        reason = "budget constraint missing from polynomial Hamiltonian; budget is metadata only"
    elif not finite:
        reason = "hard budget polynomial contains non-finite coefficients"
    else:
        reason = ""
    return BudgetPayloadValidation(
        passed=passed,
        budget_present_in_metadata=metadata_present,
        budget_present_in_polynomial=polynomial,
        budget_polynomial_term_count=len(budget_terms),
        failure_reason=reason,
    )
