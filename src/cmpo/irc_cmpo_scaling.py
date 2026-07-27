"""Dirac-3 coefficient scaling for IRC-CMPO Hamiltonians.

The hardware polynomial is formed only after algebraically combining like
binary monomials.  Constant offsets are retained for prediction, but omitted
from the submitted material polynomial because they cannot change a minimizer.
"""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import spearmanr


class ScalingError(ValueError):
    """Raised when a polynomial cannot satisfy the Dirac-3 numerical gate."""


@dataclass(frozen=True)
class ScalingAudit:
    passed: bool
    input_term_count: int
    material_term_count: int
    constant_term_count: int
    removed_zero_monomial_count: int
    normalization_scale: float
    quantization_grid: float
    maximum_material_coefficient: float
    minimum_material_coefficient: float
    dynamic_range: float
    minimum_distinct_level_separation: float
    distinct_coefficient_level_count: int
    degree_distribution: dict[int, int]
    component_statistics: dict[str, dict[str, float | int]]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScaledHamiltonian:
    """Quantized material polynomial plus its original-unit prediction map."""

    terms: tuple[dict[str, Any], ...]
    combined_terms: tuple[dict[str, Any], ...]
    constant_offset: float
    normalization_scale: float
    audit: ScalingAudit

    def energy(self, state: Mapping[str, int | bool]) -> float:
        """Return the constant-free energy that is sent to the hardware."""

        return evaluate_polynomial(self.terms, state)

    def predict_original_units(self, state: Mapping[str, int | bool]) -> float:
        """Return the post-quantization prediction in pre-scaling units."""

        return self.constant_offset + self.normalization_scale * self.energy(state)

    def unquantized_prediction(self, state: Mapping[str, int | bool]) -> float:
        return self.constant_offset + evaluate_polynomial(self.combined_terms, state)

    def to_dict(self) -> dict[str, Any]:
        return {
            "terms": list(self.terms),
            "combined_terms": list(self.combined_terms),
            "constant_offset": self.constant_offset,
            "normalization_scale": self.normalization_scale,
            "audit": self.audit.to_dict(),
        }


def _canonical_monomial(term: Mapping[str, Any]) -> tuple[str, ...]:
    powers = term.get("powers", {})
    names: list[str] = []
    if isinstance(powers, Mapping):
        for raw_name, raw_power in powers.items():
            power = int(raw_power)
            if power != raw_power or power < 0:
                raise ScalingError("binary monomial powers must be nonnegative integers")
            if power:
                # For binary variables x**k == x for every positive integer k.
                names.append(str(raw_name))
    elif isinstance(powers, Sequence) and not isinstance(powers, (str, bytes)):
        names.extend(str(name) for name in powers)
    else:
        raise ScalingError("term powers must be a mapping or variable-name sequence")
    monomial = tuple(sorted(set(names)))
    if len(monomial) > 3:
        raise ScalingError("Dirac-3 material monomial degree exceeds three")
    return monomial


def _validate_state_value(name: str, raw_value: int | bool) -> int:
    if isinstance(raw_value, (bool, np.bool_)):
        return int(raw_value)
    if isinstance(raw_value, (int, np.integer)) and int(raw_value) in {0, 1}:
        return int(raw_value)
    raise ValueError(f"state coordinate {name!r} is not natively binary")


def evaluate_polynomial(
    terms: Sequence[Mapping[str, Any]], state: Mapping[str, int | bool]
) -> float:
    """Evaluate a degree-three binary polynomial without rounding or projection."""

    total = 0.0
    for term in terms:
        coefficient = float(term["coefficient"])
        if not math.isfinite(coefficient):
            raise ValueError("polynomial contains a non-finite coefficient")
        product = 1
        for name in _canonical_monomial(term):
            if name not in state:
                raise KeyError(f"state is missing variable {name!r}")
            product *= _validate_state_value(name, state[name])
        total += coefficient * product
    return float(total)


def _minimum_level_separation(values: Sequence[float]) -> float:
    levels = sorted(set(values))
    if len(levels) < 2:
        return 1.0
    return min(right - left for left, right in zip(levels, levels[1:]))


def scale_for_dirac3(
    terms: Sequence[Mapping[str, Any]],
    *,
    effective_dynamic_range: int = 200,
    collapsed_lower: float = 1e-16,
    collapsed_upper: float = 1e-13,
) -> ScaledHamiltonian:
    """Combine, normalize, and quantize a binary Hamiltonian for Dirac-3.

    Every surviving material coefficient is placed on the signed integer grid
    ``1 / effective_dynamic_range``.  A nonzero coefficient that would round to
    zero is conservatively clipped to the first resolvable level; callers must
    then recompute prediction gates with :func:`recompute_surrogate_gates`.
    """

    if effective_dynamic_range < 2:
        raise ScalingError("effective dynamic range must be at least two")
    combined: dict[tuple[str, ...], list[float]] = {}
    components: dict[tuple[str, ...], set[str]] = {}
    constant_term_count = 0
    for term in terms:
        coefficient = float(term["coefficient"])
        if not math.isfinite(coefficient):
            raise ScalingError("polynomial contains a non-finite coefficient")
        monomial = _canonical_monomial(term)
        if not monomial:
            constant_term_count += 1
        combined.setdefault(monomial, []).append(coefficient)
        components.setdefault(monomial, set()).add(str(term.get("component", "unclassified")))

    effective = {monomial: math.fsum(values) for monomial, values in combined.items()}
    constant_offset = effective.pop((), 0.0)
    zero_monomials = [monomial for monomial, coefficient in effective.items() if coefficient == 0.0]
    for monomial in zero_monomials:
        del effective[monomial]
    if not effective:
        raise ScalingError("polynomial has no nonzero material coefficients")

    collapsed = [
        (monomial, coefficient)
        for monomial, coefficient in effective.items()
        if collapsed_lower <= abs(coefficient) <= collapsed_upper
    ]
    if collapsed:
        rendered = ", ".join(f"{'*'.join(key)}={value:.3g}" for key, value in collapsed)
        raise ScalingError(f"collapsed material coefficient in forbidden 1e-16..1e-13 band: {rendered}")

    scale = max(abs(value) for value in effective.values())
    grid = 1.0 / effective_dynamic_range
    quantized: dict[tuple[str, ...], float] = {}
    for monomial, coefficient in effective.items():
        normalized = coefficient / scale
        level = max(1, min(effective_dynamic_range, int(math.floor(abs(normalized) / grid + 0.5))))
        quantized[monomial] = math.copysign(level * grid, normalized)

    magnitudes = [abs(value) for value in quantized.values()]
    maximum = max(magnitudes)
    minimum = min(magnitudes)
    ratio = maximum / minimum
    signed_separation = _minimum_level_separation(list(quantized.values()))
    degree_distribution: dict[int, int] = {}
    component_values: dict[str, list[float]] = {}
    for monomial, coefficient in quantized.items():
        degree_distribution[len(monomial)] = degree_distribution.get(len(monomial), 0) + 1
        for component in components[monomial]:
            component_values.setdefault(component, []).append(abs(coefficient))
    component_statistics = {
        component: {
            "material_monomial_count": len(values),
            "minimum_abs_coefficient": min(values),
            "maximum_abs_coefficient": max(values),
        }
        for component, values in sorted(component_values.items())
    }
    reasons: list[str] = []
    if maximum != 1.0:
        reasons.append("largest absolute material coefficient is not normalized to one")
    if ratio > effective_dynamic_range + 1e-12:
        reasons.append("material coefficient dynamic range exceeds hardware limit")
    if signed_separation + 1e-12 < grid:
        reasons.append("distinct material coefficient levels are not hardware resolvable")

    combined_terms = tuple(
        {
            "coefficient": float(coefficient),
            "powers": {name: 1 for name in monomial},
            "degree": len(monomial),
            "component": "combined",
            "source_components": tuple(sorted(components[monomial])),
        }
        for monomial, coefficient in sorted(effective.items())
    )
    quantized_terms = tuple(
        {
            "coefficient": float(coefficient),
            "powers": {name: 1 for name in monomial},
            "degree": len(monomial),
            "component": "quantized_combined",
            "source_components": tuple(sorted(components[monomial])),
        }
        for monomial, coefficient in sorted(quantized.items())
    )
    audit = ScalingAudit(
        passed=not reasons,
        input_term_count=len(terms),
        material_term_count=len(quantized_terms),
        constant_term_count=constant_term_count,
        removed_zero_monomial_count=len(zero_monomials),
        normalization_scale=scale,
        quantization_grid=grid,
        maximum_material_coefficient=maximum,
        minimum_material_coefficient=minimum,
        dynamic_range=ratio,
        minimum_distinct_level_separation=signed_separation,
        distinct_coefficient_level_count=len(set(quantized.values())),
        degree_distribution=dict(sorted(degree_distribution.items())),
        component_statistics=component_statistics,
        reasons=tuple(reasons),
    )
    if reasons:
        raise ScalingError("; ".join(reasons))
    return ScaledHamiltonian(
        terms=quantized_terms,
        combined_terms=combined_terms,
        constant_offset=float(constant_offset),
        normalization_scale=scale,
        audit=audit,
    )


def _prediction_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    costs: np.ndarray | None,
    tie_keys: Sequence[tuple[tuple[str, int], ...]],
) -> dict[str, float]:
    if actual.ndim != 1 or len(actual) != len(predicted) or len(actual) < 2:
        raise ValueError("prediction validation requires equally sized one-dimensional arrays")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("prediction validation contains non-finite values")
    # Use the same physical solver tolerance as surrogate fitting.  IEEE123
    # recourse values that differ by less than this are the same solved
    # operating point, not evidence for a distinct ranking.
    tolerance = 1e-6
    canonical_actual = np.round(actual / tolerance) * tolerance
    canonical_predicted = np.round(predicted / tolerance) * tolerance
    error = predicted - actual
    rmse = float(np.sqrt(np.mean(error**2)))
    scale = max(float(np.ptp(actual)), 1e-12)
    residual_sum = float(np.sum(error**2))
    total_sum = float(np.sum((actual - np.mean(actual)) ** 2))
    r2 = 1.0 - residual_sum / total_sum if total_sum > 1e-12 else float(residual_sum <= 1e-12)
    if float(np.ptp(actual)) <= 1e-12 or float(np.ptp(predicted)) <= 1e-12:
        spearman = 0.0
    else:
        spearman = float(spearmanr(canonical_actual, canonical_predicted).statistic)
        if not math.isfinite(spearman):
            spearman = 0.0
    top_count = max(1, math.ceil(0.1 * len(actual)))
    if len(tie_keys) != len(actual) or len(set(tie_keys)) != len(tie_keys):
        raise ValueError("prediction validation requires unique state signatures for tie-breaking")

    actual_cutoff = float(np.partition(canonical_actual, top_count - 1)[top_count - 1])
    actual_top = set(np.flatnonzero(canonical_actual <= actual_cutoff).tolist())
    predicted_count = min(len(canonical_predicted), len(actual_top))
    predicted_cutoff = float(
        np.partition(canonical_predicted, predicted_count - 1)[predicted_count - 1]
    )
    predicted_top = set(np.flatnonzero(canonical_predicted <= predicted_cutoff).tolist())
    if costs is None:
        pareto_recall = len(actual_top & predicted_top) / len(actual_top)
    else:
        if costs.shape != actual.shape or not np.isfinite(costs).all():
            raise ValueError("cost validation values must match predictions and be finite")

        def frontier(values: np.ndarray) -> set[int]:
            result: set[int] = set()
            for index, (cost, loss) in enumerate(zip(costs, values, strict=True)):
                dominated = np.any(
                    (costs <= cost)
                    & (values <= loss)
                    & ((costs < cost) | (values < loss))
                )
                if not dominated:
                    result.add(index)
            return result

        actual_front = frontier(canonical_actual)
        predicted_front = frontier(canonical_predicted)
        pareto_recall = len(actual_front & predicted_front) / len(actual_front) if actual_front else 1.0
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": rmse,
        "normalized_rmse": rmse / scale,
        "r2": r2,
        "spearman_rank_correlation": spearman,
        "top_decile_count": top_count,
        "top_decile_recall": len(actual_top & predicted_top) / len(actual_top),
        "pareto_front_recall": float(pareto_recall),
    }


def recompute_surrogate_gates(
    scaled: ScaledHamiltonian,
    states: Sequence[Mapping[str, int | bool]],
    actual_values: Sequence[float],
    *,
    costs: Sequence[float] | None = None,
    minimum_spearman: float = 0.8,
    maximum_normalized_rmse: float = 0.2,
    minimum_top_decile_recall: float = 0.7,
    minimum_pareto_recall: float = 0.7,
) -> dict[str, Any]:
    """Recompute surrogate quality in original units after quantization."""

    actual = np.asarray(actual_values, dtype=float)
    cost_array = np.asarray(costs, dtype=float) if costs is not None else None
    tie_keys = [
        tuple(
            sorted(
                (str(name), _validate_state_value(str(name), value))
                for name, value in state.items()
            )
        )
        for state in states
    ]
    unquantized = np.asarray([scaled.unquantized_prediction(state) for state in states])
    quantized = np.asarray([scaled.predict_original_units(state) for state in states])
    before = _prediction_metrics(actual, unquantized, cost_array, tie_keys)
    after = _prediction_metrics(actual, quantized, cost_array, tie_keys)
    passed = bool(
        after["spearman_rank_correlation"] >= minimum_spearman
        and after["normalized_rmse"] <= maximum_normalized_rmse
        and after["top_decile_recall"] >= minimum_top_decile_recall
        and after["pareto_front_recall"] >= minimum_pareto_recall
    )
    return {
        "unquantized": before,
        "quantized": after,
        "thresholds": {
            "minimum_spearman": minimum_spearman,
            "maximum_normalized_rmse": maximum_normalized_rmse,
            "minimum_top_decile_recall": minimum_top_decile_recall,
            "minimum_pareto_recall": minimum_pareto_recall,
        },
        "gates_passed": passed,
    }


def require_quantized_surrogate_gates(report: Mapping[str, Any]) -> None:
    """Reject a payload whose recomputed post-quantization gates do not pass."""

    if not bool(report.get("gates_passed", False)):
        raise ScalingError("post-quantization surrogate gate failed")


def scale_payload_for_dirac3(
    payload: Mapping[str, Any],
    *,
    validation_states: Sequence[Mapping[str, int | bool]],
    validation_actual_values: Sequence[float],
    validation_costs: Sequence[float] | None = None,
    gate_thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return a validated, quantized payload copy suitable for offline solving.

    Supplying the validation set is mandatory for this payload-level API so a
    caller cannot accidentally emit final hardware terms without recomputing
    the post-quantization surrogate gates.  The input payload is never mutated.
    """

    raw_terms = payload.get("polynomial_terms")
    if not isinstance(raw_terms, Sequence) or isinstance(raw_terms, (str, bytes)):
        raise ScalingError("payload polynomial_terms must be a sequence")
    scaled = scale_for_dirac3(raw_terms)
    thresholds = dict(gate_thresholds or {})
    unexpected = set(thresholds) - {
        "minimum_spearman",
        "maximum_normalized_rmse",
        "minimum_top_decile_recall",
        "minimum_pareto_recall",
    }
    if unexpected:
        raise ScalingError(f"unknown post-quantization gate thresholds: {sorted(unexpected)}")
    validation = recompute_surrogate_gates(
        scaled,
        validation_states,
        validation_actual_values,
        costs=validation_costs,
        **thresholds,
    )
    require_quantized_surrogate_gates(validation)
    result = deepcopy(dict(payload))
    result["polynomial_terms"] = [deepcopy(term) for term in scaled.terms]
    degrees = [int(term["degree"]) for term in scaled.terms]
    result["min_degree"] = min(degrees)
    result["max_degree"] = max(degrees)
    result["objective_constant_offset_original_units"] = scaled.constant_offset
    result["dirac3_scaling"] = {
        "audit": scaled.audit.to_dict(),
        "post_quantization_validation": validation,
        "material_terms_combined_before_scaling": True,
        "constants_submitted": False,
        "projection_used": False,
    }
    return result
