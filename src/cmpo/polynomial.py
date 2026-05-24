"""Degree-bounded polynomial model for CMPO Hamiltonians."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Variable:
    """A bounded optimization variable.

    ``encoding_type`` is kept intentionally close to the expected QCi payload
    vocabulary for Phase 3 adaptation.
    """

    name: str
    lower_bound: float
    upper_bound: float
    encoding_type: str = "quasi_continuous"

    def __post_init__(self) -> None:
        if self.encoding_type not in {"quasi_continuous", "integer"}:
            raise ValueError(f"unsupported encoding_type: {self.encoding_type}")
        if self.upper_bound < self.lower_bound:
            raise ValueError(f"upper_bound must be >= lower_bound for {self.name}")


@dataclass(frozen=True)
class PolynomialTerm:
    """A monomial coefficient multiplied by variable powers."""

    coefficient: float
    powers: dict[str, int]

    def __post_init__(self) -> None:
        if any(exponent <= 0 for exponent in self.powers.values()):
            raise ValueError("term exponents must be positive")

    @property
    def degree(self) -> int:
        """Return the total polynomial degree of this term."""

        return sum(self.powers.values())

    def evaluate(self, solution: dict[str, float]) -> float:
        """Evaluate the term under a solution dictionary."""

        value = self.coefficient
        for var_name, exponent in self.powers.items():
            value *= solution.get(var_name, 0.0) ** exponent
        return float(value)


class PolynomialModel:
    """Container for bounded variables and polynomial objective terms."""

    def __init__(self, name: str = "cmpo_polynomial") -> None:
        self.name = name
        self.variables: dict[str, Variable] = {}
        self.terms: list[PolynomialTerm] = []

    def add_variable(
        self,
        name: str,
        lower_bound: float,
        upper_bound: float,
        encoding_type: str = "quasi_continuous",
    ) -> Variable:
        """Add a bounded variable or verify an existing matching variable."""

        variable = Variable(name, float(lower_bound), float(upper_bound), encoding_type)
        existing = self.variables.get(name)
        if existing is not None:
            if existing != variable:
                raise ValueError(f"variable {name} already exists with different bounds or encoding")
            return existing
        self.variables[name] = variable
        return variable

    def add_term(self, coefficient: float, powers: dict[str, int] | None = None) -> PolynomialTerm:
        """Add a polynomial term.

        An empty powers dictionary represents a constant offset.
        """

        compact_powers = {name: int(power) for name, power in (powers or {}).items() if power != 0}
        for var_name in compact_powers:
            if var_name not in self.variables:
                raise KeyError(f"unknown variable in term: {var_name}")
        term = PolynomialTerm(float(coefficient), compact_powers)
        self.terms.append(term)
        return term

    def add_linear(self, coefficient: float, var_name: str) -> PolynomialTerm:
        """Add ``coefficient * var_name``."""

        return self.add_term(coefficient, {var_name: 1})

    def add_quadratic(self, coefficient: float, var_a: str, var_b: str) -> PolynomialTerm:
        """Add a quadratic term, combining powers when variables match."""

        powers = {var_a: 1}
        powers[var_b] = powers.get(var_b, 0) + 1
        return self.add_term(coefficient, powers)

    def add_cubic(self, coefficient: float, var_a: str, var_b: str, var_c: str) -> PolynomialTerm:
        """Add a cubic term, combining powers when variables repeat."""

        powers: dict[str, int] = {}
        for var_name in (var_a, var_b, var_c):
            powers[var_name] = powers.get(var_name, 0) + 1
        return self.add_term(coefficient, powers)

    def evaluate(self, solution_dict: dict[str, float]) -> float:
        """Evaluate the objective energy under a solution dictionary."""

        return float(sum(term.evaluate(solution_dict) for term in self.terms))

    def degree(self) -> int:
        """Return the maximum term degree."""

        return max((term.degree for term in self.terms), default=0)

    def term_count(self) -> int:
        """Return the number of polynomial terms."""

        return len(self.terms)

    def variable_count(self) -> int:
        """Return the number of variables."""

        return len(self.variables)

    def validate_degree(self, max_degree: int = 3) -> bool:
        """Raise if the model exceeds ``max_degree``; return True otherwise."""

        degree = self.degree()
        if degree > max_degree:
            raise ValueError(f"polynomial degree {degree} exceeds max_degree={max_degree}")
        return True

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable model representation."""

        return {
            "name": self.name,
            "variables": [asdict(variable) for variable in self.variables.values()],
            "terms": [asdict(term) | {"degree": term.degree} for term in self.terms],
            "degree": self.degree(),
            "term_count": self.term_count(),
            "variable_count": self.variable_count(),
        }

    def save_json(self, path: Path | str) -> Path:
        """Write the model to JSON and return the output path."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_json_dict(), indent=2), encoding="utf-8")
        return output_path


def max_polynomial_degree(terms: list[dict[str, object]]) -> int:
    """Compatibility helper for older scaffold tests."""

    return max((int(term.get("degree", 0)) for term in terms), default=0)


def cubic_generation_cost_terms() -> list[dict[str, object]]:
    """Return a documented cubic generation-cost schema snippet."""

    return [{"name": "cubic_generation_cost", "degree": 3}]


def mode_selection_terms() -> list[dict[str, object]]:
    """Return a documented mode-selection schema snippet."""

    return [{"name": "mode_selection", "degree": 3}]
