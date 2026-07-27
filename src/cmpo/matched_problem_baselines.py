"""Matched patch-level classical solvers for SC-CMPO payloads.

Every method in this module consumes the same bounded polynomial payload.  The
returned vectors retain every payload variable so the downstream overlap
consensus and full-system projection can treat classical and QCi patches in
exactly the same way.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.optimize import (
    Bounds,
    LinearConstraint,
    differential_evolution,
    linprog,
    milp,
    minimize,
)
from scipy.sparse import coo_matrix


REQUIRED_MATCHED_METHODS = (
    "CMPO-local polynomial search",
    "IPOPT/Pyomo nonlinear",
    "SLSQP",
    "piecewise-linear MILP",
    "differential evolution",
    "QUBO/quadratized search",
    "greedy resilience heuristic",
)
STOCHASTIC_MATCHED_METHODS = frozenset(
    {
        "CMPO-local polynomial search",
        "differential evolution",
        "QUBO/quadratized search",
    }
)
FULL_SYSTEM_REFERENCE_METHODS = (
    "coordinated first-stage MILP + full-system projection reference",
    "coordinated first-stage NLP + full-system projection reference",
)
ALL_MATCHED_METHODS = REQUIRED_MATCHED_METHODS + FULL_SYSTEM_REFERENCE_METHODS


@dataclass(frozen=True)
class _CompiledPolynomial:
    names: tuple[str, ...]
    lower: np.ndarray
    upper: np.ndarray
    integer: np.ndarray
    coefficients: dict[int, np.ndarray]
    indices: dict[int, np.ndarray]

    def evaluate(self, vector: Sequence[float] | np.ndarray) -> float:
        values = np.asarray(vector, dtype=float)
        energy = float(self.coefficients[0].sum())
        for degree in (1, 2, 3):
            coefficients = self.coefficients[degree]
            if coefficients.size:
                products = np.prod(values[self.indices[degree]], axis=1)
                energy += float(np.dot(coefficients, products))
        return energy

    def gradient(self, vector: Sequence[float] | np.ndarray) -> np.ndarray:
        values = np.asarray(vector, dtype=float)
        gradient = np.zeros(len(self.names), dtype=float)
        for degree in (1, 2, 3):
            coefficients = self.coefficients[degree]
            term_indices = self.indices[degree]
            for position in range(degree):
                if degree == 1:
                    contributions = coefficients
                else:
                    other_positions = [
                        index for index in range(degree) if index != position
                    ]
                    contributions = coefficients * np.prod(
                        values[term_indices[:, other_positions]], axis=1
                    )
                np.add.at(gradient, term_indices[:, position], contributions)
        return gradient

    def vector(self, values: Mapping[str, Any]) -> np.ndarray:
        return np.array(
            [
                float(values.get(name, self.lower[index]))
                for index, name in enumerate(self.names)
            ]
        )

    def values(self, vector: Sequence[float] | np.ndarray) -> dict[str, float]:
        return {
            name: float(value) for name, value in zip(self.names, vector, strict=True)
        }


@dataclass(frozen=True)
class _SolveOutcome:
    values: dict[str, float]
    backend: str
    metadata: dict[str, Any]
    raw_objective: float | None = None


class _SolverFailure(RuntimeError):
    """Raised when a backend returns no usable candidate vector."""


def _compile_payload(payload: Mapping[str, Any]) -> _CompiledPolynomial:
    variables = list(payload.get("variables", ()))
    if not variables:
        raise ValueError("SC-CMPO payload has no variables")
    names = tuple(str(variable["name"]) for variable in variables)
    if len(set(names)) != len(names):
        raise ValueError("SC-CMPO payload contains duplicate variable names")
    name_to_index = {name: index for index, name in enumerate(names)}
    lower = np.array(
        [float(variable["lower_bound"]) for variable in variables], dtype=float
    )
    upper = np.array(
        [float(variable["upper_bound"]) for variable in variables], dtype=float
    )
    if (
        np.any(~np.isfinite(lower))
        or np.any(~np.isfinite(upper))
        or np.any(upper < lower)
    ):
        raise ValueError("SC-CMPO payload contains invalid variable bounds")
    integer = np.array(
        [str(variable.get("encoding_type", "")) == "integer" for variable in variables]
    )

    coefficients: dict[int, list[float]] = {0: [], 1: [], 2: [], 3: []}
    indices: dict[int, list[list[int]]] = {0: [], 1: [], 2: [], 3: []}
    for term in payload.get("polynomial_terms", ()):
        expanded: list[int] = []
        for name, exponent_value in dict(term.get("powers", {})).items():
            if str(name) not in name_to_index:
                raise ValueError(
                    f"polynomial term references unknown variable {name!r}"
                )
            exponent = int(exponent_value)
            if exponent <= 0:
                raise ValueError("polynomial exponents must be positive")
            expanded.extend([name_to_index[str(name)]] * exponent)
        degree = len(expanded)
        if degree > 3:
            raise ValueError(
                f"matched baseline only supports degree <= 3, got {degree}"
            )
        coefficients[degree].append(float(term["coefficient"]))
        indices[degree].append(expanded)

    coefficient_arrays = {
        degree: np.asarray(coefficients[degree], dtype=float) for degree in range(4)
    }
    index_arrays = {
        0: np.empty((len(indices[0]), 0), dtype=int),
        **{
            degree: np.asarray(indices[degree], dtype=int).reshape(-1, degree)
            for degree in (1, 2, 3)
        },
    }
    return _CompiledPolynomial(
        names, lower, upper, integer, coefficient_arrays, index_arrays
    )


def _scenario_name(scenario: Mapping[str, Any]) -> str:
    return str(scenario["name"])


def _desired_mode(scenario: Mapping[str, Any]) -> str:
    if bool(scenario.get("restoration_mode", False)):
        return "restoration"
    if bool(scenario.get("forced_islanding", False)):
        return "islanded"
    return "connected"


def _option_map(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    options = {
        str(option["technology"]): option
        for option in payload["sc_cmpo"]["upgrade_options"]
    }
    required = {"pv", "bess", "dispatchable_generation"}
    missing = required - set(options)
    if missing:
        raise ValueError(
            f"SC-CMPO payload is missing upgrade options: {sorted(missing)}"
        )
    return options


def _clip_and_complete(
    compiled: _CompiledPolynomial, values: Mapping[str, Any]
) -> dict[str, float]:
    vector = compiled.vector(values)
    vector = np.clip(vector, compiled.lower, compiled.upper)
    vector[compiled.integer] = np.rint(vector[compiled.integer])
    completed = compiled.values(vector)

    def make_one_hot(names: Sequence[str]) -> None:
        present = [name for name in names if name in completed]
        if not present:
            return
        selected = max(
            present, key=lambda name: (completed[name], -present.index(name))
        )
        for name in present:
            completed[name] = float(name == selected)

    make_one_hot(("base_mode_connected", "base_mode_islanded", "base_mode_restoration"))
    scenarios = sorted(
        name.removeprefix("mode_connected[").removesuffix("]")
        for name in compiled.names
        if name.startswith("mode_connected[")
    )
    for scenario in scenarios:
        make_one_hot(
            tuple(
                f"mode_{mode}[{scenario}]"
                for mode in ("connected", "islanded", "restoration")
            )
        )
        make_one_hot(
            tuple(
                f"battery_action_{action}[{scenario}]"
                for action in ("charge", "hold", "discharge")
            )
        )
        service_name = f"critical_load_service[{scenario}]"
        shedding_name = f"load_shedding_allocation[{scenario}]"
        if service_name in completed and shedding_name in completed:
            completed[shedding_name] = 1.0 - completed[service_name]

    links = (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("bess_power_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    )
    for capacity, selection in links:
        if capacity not in completed or selection not in completed:
            continue
        if completed[selection] < 0.5:
            completed[capacity] = 0.0
        elif completed[capacity] > 1e-12:
            completed[selection] = 1.0
    return completed


def _fractions_to_values(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    fractions: Sequence[float],
) -> dict[str, float]:
    pv_fraction, bess_fraction, dispatchable_fraction = (
        min(max(float(value), 0.0), 1.0) for value in fractions
    )
    values = {
        name: float(compiled.lower[index]) for index, name in enumerate(compiled.names)
    }
    values.update(
        {
            "upgrade_select_pv": float(pv_fraction > 1e-12),
            "upgrade_select_bess": float(bess_fraction > 1e-12),
            "upgrade_select_dispatchable": float(dispatchable_fraction > 1e-12),
            "pv_capacity_fraction": pv_fraction,
            "bess_energy_fraction": bess_fraction,
            "bess_power_fraction": bess_fraction,
            "dispatchable_capacity_fraction": dispatchable_fraction,
            "islanding_eligibility": 1.0,
            "base_mode_connected": 1.0,
            "base_mode_islanded": 0.0,
            "base_mode_restoration": 0.0,
            "bess_reserve_target": 1.0,
            "bess_soc_target": 1.0,
            "critical_load_priority": 1.0,
            "tie_pcc_reserve_target": 1.0,
        }
    )
    options = _option_map(payload)
    patch = payload["sc_cmpo"]["upgrade_patch"]
    load_kw = max(float(patch["load_kw"]), 1e-12)
    existing_kw = float(patch["existing_generation_kw"])
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = _scenario_name(scenario)
        desired_mode = _desired_mode(scenario)
        for mode in ("connected", "islanded", "restoration"):
            values[f"mode_{mode}[{name}]"] = float(mode == desired_mode)

        existing_fraction = (
            existing_kw / load_kw
            if bool(scenario["existing_generation_available"])
            else 0.0
        )
        capacity_fraction = existing_fraction
        if bool(scenario["pv_available"]):
            capacity_fraction += (
                pv_fraction * float(options["pv"]["capacity_kw"]) / load_kw
            )
        capacity_fraction += (
            bess_fraction * float(options["bess"]["power_kw"]) / load_kw
        )
        capacity_fraction += (
            dispatchable_fraction
            * float(options["dispatchable_generation"]["capacity_kw"])
            / load_kw
        )
        pcc_available = bool(scenario["pcc_available"])
        der_dispatch = min(1.0, capacity_fraction)
        tie_response = max(0.0, 1.0 - der_dispatch) if pcc_available else 0.0
        served_fraction = min(1.0, der_dispatch + tie_response)
        values[f"der_commitment[{name}]"] = der_dispatch
        values[f"der_capacity_slack[{name}]"] = min(
            1.0,
            max(0.0, capacity_fraction - der_dispatch) / 3.0,
        )
        values[f"critical_load_service[{name}]"] = served_fraction
        values[f"tie_pcc_response[{name}]"] = tie_response
        values[f"load_shedding_allocation[{name}]"] = 1.0 - served_fraction
        action = "discharge" if not pcc_available and bess_fraction > 1e-12 else "hold"
        for candidate in ("charge", "hold", "discharge"):
            values[f"battery_action_{candidate}[{name}]"] = float(candidate == action)
    return _clip_and_complete(compiled, values)


def _robust_capacity_problem(
    payload: Mapping[str, Any],
) -> tuple[np.ndarray, list[list[float]], list[float]]:
    options = _option_map(payload)
    patch = payload["sc_cmpo"]["upgrade_patch"]
    technologies = ("pv", "bess", "dispatchable_generation")
    costs = np.array(
        [float(options[name]["total_cost"]) for name in technologies], dtype=float
    )
    load_kw = float(patch["load_kw"])
    existing_kw = float(patch["existing_generation_kw"])
    constraints: list[list[float]] = []
    right_hand_side: list[float] = []
    for scenario in payload["scenario_metadata"]["scenarios"]:
        if bool(scenario["pcc_available"]):
            continue
        available_existing = (
            existing_kw if bool(scenario["existing_generation_available"]) else 0.0
        )
        capacities = (
            float(options["pv"]["capacity_kw"])
            if bool(scenario["pv_available"])
            else 0.0,
            float(options["bess"]["power_kw"]),
            float(options["dispatchable_generation"]["capacity_kw"]),
        )
        constraints.append([-capacity for capacity in capacities])
        right_hand_side.append(-(load_kw - available_existing))
    return costs, constraints, right_hand_side


def _robust_warm_start(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
) -> tuple[dict[str, float], dict[str, Any]]:
    costs, constraints, right_hand_side = _robust_capacity_problem(payload)
    result = linprog(
        costs,
        A_ub=constraints or None,
        b_ub=right_hand_side or None,
        bounds=[(0.0, 1.0)] * 3,
        method="highs",
    )
    if result.success and result.x is not None and np.all(np.isfinite(result.x)):
        fractions = np.asarray(result.x, dtype=float)
        fallback_used = False
    else:
        cheapest = int(np.argmin(costs))
        fractions = np.zeros(3, dtype=float)
        fractions[cheapest] = 1.0
        fallback_used = True
    values = _fractions_to_values(payload, compiled, fractions)
    metadata = {
        "linprog_success": bool(result.success),
        "linprog_status": int(result.status),
        "linprog_message": str(result.message),
        "fallback_used": fallback_used,
        "capacity_fractions": [float(value) for value in fractions],
    }
    return values, metadata


def _solve_greedy(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    _seed: int,
) -> _SolveOutcome:
    costs, constraints, right_hand_side = _robust_capacity_problem(payload)
    order = sorted(range(3), key=lambda index: (costs[index], index))
    fractions = np.zeros(3, dtype=float)
    remaining = [max(0.0, -rhs) for rhs in right_hand_side]
    capacities = (
        -np.asarray(constraints, dtype=float) if constraints else np.zeros((0, 3))
    )
    for technology_index in order:
        if all(deficit <= 1e-9 for deficit in remaining):
            break
        useful_capacity = max(
            (capacities[row, technology_index] for row in range(len(remaining))),
            default=0.0,
        )
        if useful_capacity <= 0.0:
            continue
        required_fraction = max(
            (
                remaining[row] / capacities[row, technology_index]
                for row in range(len(remaining))
                if capacities[row, technology_index] > 0.0
            ),
            default=0.0,
        )
        fractions[technology_index] = min(1.0, required_fraction)
        remaining = [
            max(
                0.0,
                deficit
                - capacities[row, technology_index] * fractions[technology_index],
            )
            for row, deficit in enumerate(remaining)
        ]
    values = _fractions_to_values(payload, compiled, fractions)
    return _SolveOutcome(
        values,
        "deterministic published-cost greedy heuristic",
        {
            "technology_order": [int(index) for index in order],
            "capacity_fractions": [float(value) for value in fractions],
            "remaining_worst_case_deficit_kw": float(max(remaining, default=0.0)),
            "objective_trace": [compiled.evaluate(compiled.vector(values))],
        },
    )


def _coordinate_improve(
    compiled: _CompiledPolynomial,
    initial: Mapping[str, Any],
    rng: np.random.Generator,
    *,
    sweeps: int,
    levels: int,
) -> tuple[dict[str, float], list[float], int]:
    current_values = _clip_and_complete(compiled, initial)
    current = compiled.vector(current_values)
    current_energy = compiled.evaluate(current)
    trace = [current_energy]
    evaluations = 1
    for _ in range(max(1, sweeps)):
        changed = False
        order = rng.permutation(len(compiled.names))
        for index in order:
            lower = compiled.lower[index]
            upper = compiled.upper[index]
            if upper <= lower:
                continue
            candidates = (
                np.array([lower, upper], dtype=float)
                if compiled.integer[index]
                else np.unique(
                    np.append(np.linspace(lower, upper, levels), current[index])
                )
            )
            best_energy = current_energy
            for candidate in candidates:
                trial = current.copy()
                trial[index] = float(candidate)
                trial_values = _clip_and_complete(compiled, compiled.values(trial))
                trial = compiled.vector(trial_values)
                energy = compiled.evaluate(trial)
                evaluations += 1
                if energy < best_energy - 1e-12:
                    best_energy = energy
                    best_trial = trial
            if best_energy < current_energy - 1e-12:
                current = best_trial
                current_energy = best_energy
                changed = True
        trace.append(current_energy)
        if not changed:
            break
    return _clip_and_complete(compiled, compiled.values(current)), trace, evaluations


def _solve_cmpo_local(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    seed: int,
) -> _SolveOutcome:
    rng = np.random.default_rng(seed)
    warm, warm_metadata = _robust_warm_start(payload, compiled)
    starts = [warm]
    for _ in range(3):
        vector = rng.uniform(compiled.lower, compiled.upper)
        vector[compiled.integer] = rng.integers(0, 2, size=int(compiled.integer.sum()))
        starts.append(_clip_and_complete(compiled, compiled.values(vector)))
    best_values = warm
    best_energy = compiled.evaluate(compiled.vector(warm))
    restart_traces: list[list[float]] = []
    evaluation_count = 0
    for start in starts:
        candidate, trace, evaluations = _coordinate_improve(
            compiled,
            start,
            rng,
            sweeps=2,
            levels=3,
        )
        restart_traces.append(trace)
        evaluation_count += evaluations
        energy = compiled.evaluate(compiled.vector(candidate))
        if energy < best_energy:
            best_values, best_energy = candidate, energy
    return _SolveOutcome(
        best_values,
        "deterministic CPU random-restart coordinate search",
        {
            "search_seed": int(seed),
            "restart_count": len(starts),
            "local_sweeps": 2,
            "evaluation_count": evaluation_count,
            "restart_objective_traces": restart_traces,
            "objective_trace": [trace[-1] for trace in restart_traces],
            "warm_start": warm_metadata,
            "uses_payload_polynomial": True,
        },
        best_energy,
    )


def _logical_linear_constraints(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    index = {name: position for position, name in enumerate(compiled.names)}
    rows: list[np.ndarray] = []
    lower: list[float] = []
    upper: list[float] = []

    def add(
        coefficients: Mapping[str, float], lower_bound: float, upper_bound: float
    ) -> None:
        row = np.zeros(len(compiled.names), dtype=float)
        for name, coefficient in coefficients.items():
            if name in index:
                row[index[name]] = float(coefficient)
        rows.append(row)
        lower.append(lower_bound)
        upper.append(upper_bound)

    add(
        {
            name: 1.0
            for name in (
                "base_mode_connected",
                "base_mode_islanded",
                "base_mode_restoration",
            )
        },
        1.0,
        1.0,
    )
    add({"bess_energy_fraction": 1.0, "bess_power_fraction": -1.0}, 0.0, 0.0)
    for capacity, selection in (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("bess_power_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    ):
        add({capacity: 1.0, selection: -1.0}, -np.inf, 0.0)
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = _scenario_name(scenario)
        modes = {
            f"mode_{mode}[{name}]": 1.0
            for mode in ("connected", "islanded", "restoration")
        }
        actions = {
            f"battery_action_{action}[{name}]": 1.0
            for action in ("charge", "hold", "discharge")
        }
        add(modes, 1.0, 1.0)
        add(actions, 1.0, 1.0)
        add(
            {
                f"critical_load_service[{name}]": 1.0,
                f"load_shedding_allocation[{name}]": 1.0,
            },
            1.0,
            1.0,
        )
        if not bool(scenario["pcc_available"]):
            add({f"tie_pcc_response[{name}]": 1.0}, 0.0, 0.0)
    return np.asarray(rows), np.asarray(lower), np.asarray(upper)


def _solve_slsqp(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    _seed: int,
) -> _SolveOutcome:
    warm, warm_metadata = _robust_warm_start(payload, compiled)
    warm_vector = compiled.vector(warm)
    matrix, constraint_lower, constraint_upper = _logical_linear_constraints(
        payload, compiled
    )
    trace = [compiled.evaluate(warm_vector)]
    equality = np.isclose(constraint_lower, constraint_upper)
    constraints: list[LinearConstraint] = []
    if np.any(equality):
        constraints.append(
            LinearConstraint(
                matrix[equality],
                constraint_lower[equality],
                constraint_upper[equality],
            )
        )
    if np.any(~equality):
        constraints.append(
            LinearConstraint(
                matrix[~equality],
                constraint_lower[~equality],
                constraint_upper[~equality],
            )
        )

    def callback(vector: np.ndarray) -> None:
        trace.append(compiled.evaluate(vector))

    result = minimize(
        compiled.evaluate,
        warm_vector,
        method="SLSQP",
        jac=compiled.gradient,
        bounds=Bounds(compiled.lower, compiled.upper),
        constraints=constraints,
        callback=callback,
        options={"maxiter": 35, "ftol": 1e-9, "disp": False},
    )
    usable = result.x is not None and np.all(np.isfinite(result.x))
    candidate = (
        _clip_and_complete(compiled, compiled.values(result.x)) if usable else warm
    )
    candidate_energy = compiled.evaluate(compiled.vector(candidate))
    warm_energy = compiled.evaluate(warm_vector)
    fallback_used = not usable or candidate_energy > warm_energy
    if fallback_used:
        candidate = warm
        candidate_energy = warm_energy
    return _SolveOutcome(
        candidate,
        "scipy.optimize.minimize(method='SLSQP')",
        {
            "optimizer_converged": bool(result.success),
            "solver_status": int(result.status),
            "solver_message": str(result.message),
            "solver_iterations": int(result.nit),
            "function_evaluations": int(result.nfev),
            "gradient_evaluations": int(result.njev),
            "fallback_used": fallback_used,
            "integer_variables_relaxed_then_projected": True,
            "objective_trace": trace,
            "warm_start": warm_metadata,
        },
        candidate_energy,
    )


def _solve_ipopt_pyomo(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    _seed: int,
) -> _SolveOutcome:
    """Solve the native degree-three relaxation with Pyomo and IPOPT."""

    try:
        import pyomo.environ as pyo
    except ImportError as exc:  # pragma: no cover - exercised in dependency checks
        raise _SolverFailure("Pyomo is unavailable") from exc

    solver = pyo.SolverFactory("ipopt")
    if solver is None or not solver.available(exception_flag=False):
        raise _SolverFailure(
            "Pyomo IPOPT solver is unavailable; install the ipopt executable before the final run"
        )

    warm, warm_metadata = _robust_warm_start(payload, compiled)
    warm_vector = compiled.vector(warm)
    model = pyo.ConcreteModel()
    model.variable_index = pyo.RangeSet(0, len(compiled.names) - 1)

    def bounds_rule(_model: Any, index: int) -> tuple[float, float]:
        return float(compiled.lower[index]), float(compiled.upper[index])

    model.x = pyo.Var(model.variable_index, domain=pyo.Reals, bounds=bounds_rule)
    for index, value in enumerate(warm_vector):
        model.x[index].value = float(value)

    expression: Any = float(compiled.coefficients[0].sum())
    for degree in (1, 2, 3):
        for coefficient, term_indices in zip(
            compiled.coefficients[degree], compiled.indices[degree], strict=True
        ):
            term: Any = float(coefficient)
            for index in term_indices:
                term *= model.x[int(index)]
            expression += term
    model.objective = pyo.Objective(expr=expression, sense=pyo.minimize)

    matrix, constraint_lower, constraint_upper = _logical_linear_constraints(
        payload, compiled
    )
    model.constraints = pyo.ConstraintList()
    for row, lower, upper in zip(
        matrix, constraint_lower, constraint_upper, strict=True
    ):
        linear_expression = sum(
            float(row[index]) * model.x[index]
            for index in np.flatnonzero(row)
        )
        if math.isfinite(float(lower)) and math.isfinite(float(upper)) and np.isclose(lower, upper):
            model.constraints.add(linear_expression == float(lower))
        else:
            if math.isfinite(float(lower)):
                model.constraints.add(linear_expression >= float(lower))
            if math.isfinite(float(upper)):
                model.constraints.add(linear_expression <= float(upper))

    solver.options["max_iter"] = 200
    solver.options["max_cpu_time"] = 30
    solver.options["tol"] = 1e-8
    result = solver.solve(model, tee=False, load_solutions=True)
    termination = str(result.solver.termination_condition)
    status = str(result.solver.status)
    vector = np.array(
        [pyo.value(model.x[index], exception=False) for index in range(len(compiled.names))],
        dtype=float,
    )
    if np.any(~np.isfinite(vector)):
        raise _SolverFailure(
            f"Pyomo/IPOPT returned no finite vector (status={status}, termination={termination})"
        )
    candidate = _clip_and_complete(compiled, compiled.values(vector))
    candidate_energy = compiled.evaluate(compiled.vector(candidate))
    warm_energy = compiled.evaluate(warm_vector)
    fallback_used = candidate_energy > warm_energy
    if fallback_used:
        candidate = warm
        candidate_energy = warm_energy
    return _SolveOutcome(
        candidate,
        "Pyomo SolverFactory('ipopt') native nonlinear relaxation",
        {
            "solver_status": status,
            "termination_condition": termination,
            "integer_variables_relaxed_then_projected": True,
            "fallback_to_robust_warm_start": fallback_used,
            "objective_trace": [warm_energy, candidate_energy],
            "warm_start": warm_metadata,
            "solver_is_ipopt": True,
        },
        candidate_energy,
    )


def _encoded_milp(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    reference: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    LinearConstraint,
    Callable[[np.ndarray], np.ndarray],
    dict[str, Any],
]:
    breakpoint_count = 3
    expressions: dict[str, tuple[float, dict[int, float]]] = {}
    objective: list[float] = []
    encoded_integrality: list[int] = []
    continuous_one_hot: list[list[int]] = []
    reference_energy = compiled.evaluate(reference)
    surrogate_constant = reference_energy
    for variable_index, name in enumerate(compiled.names):
        lower = compiled.lower[variable_index]
        upper = compiled.upper[variable_index]
        if compiled.integer[variable_index]:
            column = len(objective)
            low_trial = reference.copy()
            high_trial = reference.copy()
            low_trial[variable_index] = lower
            high_trial[variable_index] = upper
            low_delta = compiled.evaluate(low_trial) - reference_energy
            high_delta = compiled.evaluate(high_trial) - reference_energy
            objective.append(high_delta - low_delta)
            surrogate_constant += low_delta
            encoded_integrality.append(1)
            expressions[name] = (float(lower), {column: float(upper - lower)})
            continue
        levels = np.linspace(lower, upper, breakpoint_count)
        columns: list[int] = []
        expression: dict[int, float] = {}
        for level in levels:
            column = len(objective)
            trial = reference.copy()
            trial[variable_index] = float(level)
            objective.append(compiled.evaluate(trial) - reference_energy)
            encoded_integrality.append(1)
            columns.append(column)
            expression[column] = float(level)
        continuous_one_hot.append(columns)
        expressions[name] = (0.0, expression)

    constraint_rows: list[dict[int, float]] = []
    constraint_lower: list[float] = []
    constraint_upper: list[float] = []

    def add_encoded(coefficients: Mapping[str, float], low: float, high: float) -> None:
        constant = 0.0
        row: dict[int, float] = {}
        for name, coefficient in coefficients.items():
            expression_constant, expression = expressions[name]
            constant += float(coefficient) * expression_constant
            for column, value in expression.items():
                row[column] = row.get(column, 0.0) + float(coefficient) * value
        constraint_rows.append(row)
        constraint_lower.append(low - constant)
        constraint_upper.append(high - constant)

    for columns in continuous_one_hot:
        constraint_rows.append({column: 1.0 for column in columns})
        constraint_lower.append(1.0)
        constraint_upper.append(1.0)

    add_encoded(
        {
            name: 1.0
            for name in (
                "base_mode_connected",
                "base_mode_islanded",
                "base_mode_restoration",
            )
        },
        1.0,
        1.0,
    )
    add_encoded({"bess_energy_fraction": 1.0, "bess_power_fraction": -1.0}, 0.0, 0.0)
    for capacity, selection in (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("bess_power_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    ):
        add_encoded({capacity: 1.0, selection: -1.0}, -np.inf, 0.0)
    for scenario in payload["scenario_metadata"]["scenarios"]:
        name = _scenario_name(scenario)
        add_encoded(
            {
                f"mode_{mode}[{name}]": 1.0
                for mode in ("connected", "islanded", "restoration")
            },
            1.0,
            1.0,
        )
        add_encoded(
            {
                f"battery_action_{action}[{name}]": 1.0
                for action in ("charge", "hold", "discharge")
            },
            1.0,
            1.0,
        )
        add_encoded(
            {
                f"critical_load_service[{name}]": 1.0,
                f"load_shedding_allocation[{name}]": 1.0,
            },
            1.0,
            1.0,
        )
        desired_name = f"mode_{_desired_mode(scenario)}[{name}]"
        add_encoded({desired_name: 1.0}, 1.0, 1.0)
        if not bool(scenario["pcc_available"]):
            add_encoded({f"tie_pcc_response[{name}]": 1.0}, 0.0, 0.0)

    sparse_rows: list[int] = []
    sparse_columns: list[int] = []
    sparse_values: list[float] = []
    for row_index, row in enumerate(constraint_rows):
        for column, value in row.items():
            sparse_rows.append(row_index)
            sparse_columns.append(column)
            sparse_values.append(value)
    matrix = coo_matrix(
        (sparse_values, (sparse_rows, sparse_columns)),
        shape=(len(constraint_rows), len(objective)),
    ).tocsr()

    def decode(encoded: np.ndarray) -> np.ndarray:
        result = np.zeros(len(compiled.names), dtype=float)
        for index, name in enumerate(compiled.names):
            constant, expression = expressions[name]
            result[index] = constant + sum(
                value * encoded[column] for column, value in expression.items()
            )
        return result

    metadata = {
        "breakpoint_count": breakpoint_count,
        "encoded_variable_count": len(objective),
        "encoded_binary_variable_count": len(objective),
        "original_integer_variable_count": int(compiled.integer.sum()),
        "original_continuous_variable_count": int((~compiled.integer).sum()),
        "surrogate": "additive breakpoint response around a common robust feasible reference",
        "surrogate_constant_offset": surrogate_constant,
    }
    constraints = LinearConstraint(
        matrix, np.asarray(constraint_lower), np.asarray(constraint_upper)
    )
    return (
        np.asarray(objective),
        np.asarray(encoded_integrality),
        constraints,
        decode,
        metadata,
    )


def _solve_piecewise_milp(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    _seed: int,
) -> _SolveOutcome:
    warm, warm_metadata = _robust_warm_start(payload, compiled)
    reference = compiled.vector(warm)
    objective, integrality, constraints, decode, formulation_metadata = _encoded_milp(
        payload,
        compiled,
        reference,
    )
    encoded_solution: np.ndarray | None = None
    solver_backend = ""
    solver_metadata: dict[str, Any] = {}
    solver_attempts: list[str] = []
    try:
        import pyomo.environ as pyo

        for solver_name in ("gurobi", "appsi_highs", "highs"):
            solver = pyo.SolverFactory(solver_name)
            if solver is None or not solver.available(exception_flag=False):
                solver_attempts.append(f"{solver_name}: unavailable")
                continue
            model = pyo.ConcreteModel()
            model.variable_index = pyo.RangeSet(0, len(objective) - 1)
            model.x = pyo.Var(model.variable_index, domain=pyo.Binary)
            model.objective = pyo.Objective(
                expr=sum(float(objective[index]) * model.x[index] for index in range(len(objective))),
                sense=pyo.minimize,
            )
            model.constraints = pyo.ConstraintList()
            matrix = constraints.A.tocsr()
            for row_index in range(matrix.shape[0]):
                sparse_row = matrix.getrow(row_index)
                expression = sum(
                    float(value) * model.x[int(column)]
                    for column, value in zip(sparse_row.indices, sparse_row.data, strict=True)
                )
                lower = float(constraints.lb[row_index])
                upper = float(constraints.ub[row_index])
                if math.isfinite(lower) and math.isfinite(upper) and np.isclose(lower, upper):
                    model.constraints.add(expression == lower)
                else:
                    if math.isfinite(lower):
                        model.constraints.add(expression >= lower)
                    if math.isfinite(upper):
                        model.constraints.add(expression <= upper)
            solver.options["time_limit"] = 30.0
            solver.options["mip_rel_gap"] = 0.01
            try:
                result = solver.solve(model, tee=False, load_solutions=True)
                candidate = np.array(
                    [pyo.value(model.x[index], exception=False) for index in range(len(objective))],
                    dtype=float,
                )
                if np.any(~np.isfinite(candidate)):
                    raise _SolverFailure("solver returned a non-finite encoded vector")
                encoded_solution = candidate
                solver_backend = f"Pyomo SolverFactory('{solver_name}')"
                solver_metadata = {
                    "solver_status": str(result.solver.status),
                    "termination_condition": str(result.solver.termination_condition),
                    "solver_name": solver_name,
                }
                solver_attempts.append(f"{solver_name}: completed")
                break
            except Exception as exc:
                solver_attempts.append(f"{solver_name}: {type(exc).__name__}: {exc}")
    except ImportError:
        solver_attempts.append("pyomo: unavailable")

    if encoded_solution is None:
        result = milp(
            objective,
            integrality=integrality,
            bounds=Bounds(np.zeros(len(objective)), np.ones(len(objective))),
            constraints=constraints,
            options={"presolve": True, "time_limit": 30.0, "mip_rel_gap": 0.01},
        )
        if not result.success or result.x is None or not np.all(np.isfinite(result.x)):
            raise _SolverFailure(f"piecewise MILP failed after {solver_attempts}: {result.message}")
        encoded_solution = np.asarray(result.x, dtype=float)
        solver_backend = "scipy.optimize.milp (HiGHS fallback)"
        solver_metadata = {
            "solver_status": int(result.status),
            "termination_condition": str(result.message),
            "mip_node_count": int(getattr(result, "mip_node_count", 0) or 0),
            "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
            "solver_name": "scipy_highs",
        }
        solver_attempts.append("scipy_highs: completed")

    raw_vector = decode(encoded_solution)
    values = _clip_and_complete(compiled, compiled.values(raw_vector))
    actual_objective = compiled.evaluate(compiled.vector(values))
    surrogate_objective = float(np.dot(objective, encoded_solution)) + float(
        formulation_metadata["surrogate_constant_offset"]
    )
    metadata = {
        **formulation_metadata,
        **solver_metadata,
        "solver_success": True,
        "solver_attempts": solver_attempts,
        "surrogate_objective": surrogate_objective,
        "actual_payload_objective": actual_objective,
        "approximation_error": abs(actual_objective - surrogate_objective),
        "objective_trace": [compiled.evaluate(reference), actual_objective],
        "warm_start": warm_metadata,
    }
    return _SolveOutcome(values, solver_backend, metadata, actual_objective)


def _solve_differential_evolution(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    seed: int,
) -> _SolveOutcome:
    warm, warm_metadata = _robust_warm_start(payload, compiled)
    warm_vector = compiled.vector(warm)
    generation_trace: list[float] = []

    def callback(vector: np.ndarray, _convergence: float) -> bool:
        generation_trace.append(compiled.evaluate(vector))
        return False

    result = differential_evolution(
        compiled.evaluate,
        list(zip(compiled.lower, compiled.upper, strict=True)),
        maxiter=2,
        popsize=2,
        tol=0.05,
        polish=False,
        rng=np.random.default_rng(seed),
        callback=callback,
        updating="immediate",
        workers=1,
        integrality=compiled.integer,
        x0=warm_vector,
    )
    if result.x is None or not np.all(np.isfinite(result.x)):
        raise _SolverFailure(
            f"SciPy differential evolution returned no usable vector: {result.message}"
        )
    candidate = _clip_and_complete(compiled, compiled.values(result.x))
    candidate_energy = compiled.evaluate(compiled.vector(candidate))
    warm_energy = compiled.evaluate(warm_vector)
    fallback_used = candidate_energy > warm_energy
    if fallback_used:
        candidate = warm
        candidate_energy = warm_energy
    return _SolveOutcome(
        candidate,
        "scipy.optimize.differential_evolution",
        {
            "optimizer_converged": bool(result.success),
            "solver_message": str(result.message),
            "function_evaluations": int(result.nfev),
            "solver_iterations": int(result.nit),
            "population_size_multiplier": 2,
            "maximum_generations": 2,
            "integrality_enforced_by_solver": True,
            "fallback_to_robust_warm_start": fallback_used,
            "objective_trace": [warm_energy, *generation_trace, candidate_energy],
            "warm_start": warm_metadata,
        },
        candidate_energy,
    )


def _expanded_term_names(
    payload: Mapping[str, Any], term: Mapping[str, Any]
) -> list[str]:
    expanded: list[str] = []
    for name, exponent in dict(term.get("powers", {})).items():
        expanded.extend([str(name)] * int(exponent))
    return expanded


def _quadratization_statistics(
    payload: Mapping[str, Any], compiled: _CompiledPolynomial
) -> dict[str, Any]:
    auxiliary_pairs: set[tuple[str, str]] = set()
    cubic_term_count = 0
    for term in payload.get("polynomial_terms", ()):
        expanded = _expanded_term_names(payload, term)
        if len(expanded) == 3:
            cubic_term_count += 1
            auxiliary_pairs.add(tuple(sorted((expanded[0], expanded[1]))))
    levels = 3
    bits_per_continuous = math.ceil(math.log2(levels))
    binary_variable_count = (
        int(compiled.integer.sum())
        + int((~compiled.integer).sum()) * bits_per_continuous
    )
    auxiliary_count = len(auxiliary_pairs)
    return {
        "discrete_levels": levels,
        "bits_per_continuous_variable": bits_per_continuous,
        "binary_variable_count": binary_variable_count,
        "auxiliary_variable_count": auxiliary_count,
        "cubic_term_count": cubic_term_count,
        "quadratized_term_count": len(payload.get("polynomial_terms", ()))
        + cubic_term_count,
        "variable_blowup": (binary_variable_count + auxiliary_count)
        / max(len(compiled.names), 1),
        "auxiliary_definition": "one product auxiliary for each unique first variable pair in a cubic monomial",
    }


def _quadratized_energy(
    payload: Mapping[str, Any], values: Mapping[str, float]
) -> float:
    energy = 0.0
    for term in payload.get("polynomial_terms", ()):
        coefficient = float(term["coefficient"])
        expanded = _expanded_term_names(payload, term)
        if len(expanded) <= 2:
            product = math.prod(float(values[name]) for name in expanded)
        elif len(expanded) == 3:
            auxiliary = float(values[expanded[0]]) * float(values[expanded[1]])
            product = auxiliary * float(values[expanded[2]])
        else:
            raise ValueError(
                f"QUBO quadratization supports degree <= 3, got {len(expanded)}"
            )
        energy += coefficient * product
    return energy


def _solve_qubo(
    payload: Mapping[str, Any],
    compiled: _CompiledPolynomial,
    seed: int,
) -> _SolveOutcome:
    warm, warm_metadata = _robust_warm_start(payload, compiled)
    warm_vector = compiled.vector(warm)
    quantized_vector = warm_vector.copy()
    levels = 3
    for index in range(len(compiled.names)):
        grid = (
            np.array([compiled.lower[index], compiled.upper[index]])
            if compiled.integer[index]
            else np.linspace(compiled.lower[index], compiled.upper[index], levels)
        )
        quantized_vector[index] = float(
            grid[int(np.argmin(np.abs(grid - warm_vector[index])))]
        )
    quantized = _clip_and_complete(compiled, compiled.values(quantized_vector))
    values, trace, evaluation_count = _coordinate_improve(
        compiled,
        quantized,
        np.random.default_rng(seed),
        sweeps=2,
        levels=levels,
    )
    native_energy = compiled.evaluate(compiled.vector(values))
    quadratized_energy = _quadratized_energy(payload, values)
    warm_energy = compiled.evaluate(warm_vector)
    quantized_warm_energy = compiled.evaluate(compiled.vector(quantized))
    metadata = {
        **_quadratization_statistics(payload, compiled),
        "search_seed": int(seed),
        "search": "deterministic low-resolution coordinate search",
        "evaluation_count": evaluation_count,
        "approximation_error": abs(warm_energy - quantized_warm_energy),
        "quadratization_consistency_error": abs(quadratized_energy - native_energy),
        "quadratized_objective": quadratized_energy,
        "native_payload_objective": native_energy,
        "objective_trace": trace,
        "warm_start": warm_metadata,
    }
    return _SolveOutcome(
        values,
        "deterministic quadratized low-resolution search",
        metadata,
        native_energy,
    )


_SOLVERS: dict[
    str, Callable[[Mapping[str, Any], _CompiledPolynomial, int], _SolveOutcome]
] = {
    "CMPO-local polynomial search": _solve_cmpo_local,
    "IPOPT/Pyomo nonlinear": _solve_ipopt_pyomo,
    "SLSQP": _solve_slsqp,
    "piecewise-linear MILP": _solve_piecewise_milp,
    "differential evolution": _solve_differential_evolution,
    "QUBO/quadratized search": _solve_qubo,
    "greedy resilience heuristic": _solve_greedy,
}


def _reference_anchor(payload: Mapping[str, Any]) -> str:
    nodes = list(payload["sc_cmpo"].get("patch_public_nodes", []))
    if nodes:
        ranked = sorted(
            (
                (
                    float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                    float(node.get("load_kw", 0.0)),
                    str(node["node_id"]),
                )
                for node in nodes
            ),
            key=lambda item: (-item[0], -item[1], item[2]),
        )
        return ranked[0][2]
    node_ids = sorted(str(item) for item in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])
    if not node_ids:
        raise ValueError("coordinated reference payload has no public anchor node")
    return node_ids[0]


def _coordinated_reference_problem(
    payloads: Mapping[str, Mapping[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    technologies = ("pv", "bess", "dispatchable_generation")
    physical_costs: dict[tuple[str, str], float] = {}
    constraint_rows: list[list[float]] = []
    right_hand_side: list[float] = []
    for payload in payloads.values():
        anchor = _reference_anchor(payload)
        options = _option_map(payload)
        for technology in technologies:
            key = (anchor, technology)
            physical_costs[key] = max(
                physical_costs.get(key, 0.0),
                float(options[technology]["total_cost"]),
            )
        _costs, constraints, rhs = _robust_capacity_problem(payload)
        constraint_rows.extend(constraints)
        right_hand_side.extend(rhs)
    costs = np.array(
        [
            math.fsum(cost for (anchor, item), cost in physical_costs.items() if item == technology)
            for technology in technologies
        ],
        dtype=float,
    )
    return costs, np.asarray(constraint_rows, dtype=float), np.asarray(right_hand_side, dtype=float)


def _solve_coordinated_fractions(
    payloads: Mapping[str, Mapping[str, Any]],
    method: str,
) -> tuple[np.ndarray, str, dict[str, Any]]:
    costs, matrix, rhs = _coordinated_reference_problem(payloads)
    if method == "coordinated first-stage MILP + full-system projection reference":
        objective = np.concatenate((costs, np.zeros(3)))
        rows = []
        lower = []
        upper = []
        for constraint, bound in zip(matrix, rhs, strict=True):
            rows.append(np.concatenate((constraint, np.zeros(3))))
            lower.append(-np.inf)
            upper.append(bound)
        for index in range(3):
            row = np.zeros(6)
            row[index] = 1.0
            row[index + 3] = -1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)
        result = milp(
            objective,
            integrality=np.array([0, 0, 0, 1, 1, 1]),
            bounds=Bounds(np.zeros(6), np.ones(6)),
            constraints=LinearConstraint(np.asarray(rows), np.asarray(lower), np.asarray(upper)),
            options={"presolve": True, "mip_rel_gap": 1e-9},
        )
        if not result.success or result.x is None or not np.all(np.isfinite(result.x)):
            raise _SolverFailure(f"coordinated SciPy/HiGHS MILP failed: {result.message}")
        fractions = np.asarray(result.x[:3], dtype=float)
        return fractions, "scipy.optimize.milp (HiGHS) coordinated benchmark reference", {
            "solver_status": int(result.status),
            "solver_message": str(result.message),
            "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
            "mip_node_count": int(getattr(result, "mip_node_count", 0) or 0),
            "coordinated_upgrade_cost_objective": float(result.fun),
        }
    if method == "coordinated first-stage NLP + full-system projection reference":
        objective_scale = max(float(np.max(np.abs(costs))), 1.0)
        scaled_costs = costs / objective_scale
        warm = linprog(
            costs,
            A_ub=matrix if len(matrix) else None,
            b_ub=rhs if len(rhs) else None,
            bounds=[(0.0, 1.0)] * 3,
            method="highs",
        )
        if not warm.success or warm.x is None:
            raise _SolverFailure(f"coordinated NLP warm-start LP failed: {warm.message}")
        constraints = []
        if len(matrix):
            constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda values: rhs - matrix @ values,
                    "jac": lambda _values: -matrix,
                }
            )
        result = minimize(
            lambda values: float(np.dot(scaled_costs, values)),
            np.asarray(warm.x, dtype=float),
            method="SLSQP",
            jac=lambda _values: scaled_costs,
            bounds=Bounds(np.zeros(3), np.ones(3)),
            constraints=constraints,
            options={"maxiter": 100, "ftol": 1e-9, "disp": False},
        )
        if not result.success or result.x is None or not np.all(np.isfinite(result.x)):
            raise _SolverFailure(f"coordinated SciPy SLSQP NLP failed: {result.message}")
        fractions = np.asarray(result.x, dtype=float)
        return fractions, "scipy.optimize.minimize(method='SLSQP') coordinated benchmark NLP reference", {
            "solver_status": int(result.status),
            "solver_message": str(result.message),
            "solver_iterations": int(result.nit),
            "function_evaluations": int(result.nfev),
            "objective_scaling_factor": 1.0 / objective_scale,
            "coordinated_upgrade_cost_objective": float(np.dot(costs, fractions)),
        }
    raise ValueError(f"unknown coordinated reference method: {method}")


def solve_coordinated_reference(
    payloads: Mapping[str, Mapping[str, Any]],
    method: str,
    seed: int,
) -> list[dict[str, Any]]:
    """Solve one benchmark-wide first-stage reference and emit matched patch vectors."""

    if method not in FULL_SYSTEM_REFERENCE_METHODS:
        raise ValueError(f"unknown coordinated reference method: {method}")
    if not payloads:
        raise ValueError("coordinated reference requires at least one payload")
    benchmarks = {str(payload["sc_cmpo"]["public_benchmark"]) for payload in payloads.values()}
    if len(benchmarks) != 1:
        raise ValueError("coordinated reference requires exactly one benchmark")
    started = time.perf_counter()
    fractions, backend, solver_metadata = _solve_coordinated_fractions(payloads, method)
    runtime = time.perf_counter() - started
    rows: list[dict[str, Any]] = []
    for payload_name, payload in sorted(payloads.items()):
        compiled = _compile_payload(payload)
        values = _fractions_to_values(payload, compiled, fractions)
        objective = compiled.evaluate(compiled.vector(values))
        rows.append(
            {
                "payload_name": payload_name,
                "payload_id": payload_name.removesuffix(".json"),
                "benchmark": next(iter(benchmarks)),
                "method": method,
                "backend": backend,
                "status": "completed",
                "failure_reason": "",
                "runtime_seconds": runtime / len(payloads),
                "seed": int(seed),
                "solution_values": values,
                "variable_count": len(values),
                "objective": objective,
                "objective_energy": objective,
                "raw_objective": objective,
                "trace_metadata": {
                    **solver_metadata,
                    "reference_scope": "one shared first-stage solve across every benchmark patch",
                    "coordinated_payload_count": len(payloads),
                    "capacity_fractions": [float(value) for value in fractions],
                    "seed": int(seed),
                },
            }
        )
    return rows


def solve_matched_payload(
    payload_name: str,
    payload: Mapping[str, Any],
    method: str,
    seed: int,
) -> dict[str, Any]:
    """Solve one SC-CMPO patch with a named matched classical method.

    Backend non-convergence is recorded in ``trace_metadata`` when a usable
    bounded candidate exists.  ``status='failed'`` is reserved for calls that
    produce no usable complete solution.
    """

    if method not in _SOLVERS:
        raise ValueError(
            f"unknown matched baseline {method!r}; expected one of {list(REQUIRED_MATCHED_METHODS)}"
        )
    compiled = _compile_payload(payload)
    if tuple(_SOLVERS) != REQUIRED_MATCHED_METHODS:
        raise RuntimeError(
            "matched baseline registry does not match REQUIRED_MATCHED_METHODS"
        )
    warm, _warm_metadata = _robust_warm_start(payload, compiled)
    started = time.perf_counter()
    try:
        outcome = _SOLVERS[method](payload, compiled, int(seed))
        values = _clip_and_complete(compiled, outcome.values)
        missing = set(compiled.names) - set(values)
        if missing:
            raise _SolverFailure(f"solver omitted variables: {sorted(missing)}")
        objective = compiled.evaluate(compiled.vector(values))
        runtime = time.perf_counter() - started
        trace_metadata = {
            **outcome.metadata,
            "payload_polynomial_degree": int(payload.get("max_degree", 0)),
            "payload_term_count": len(payload.get("polynomial_terms", ())),
            "payload_variable_count": len(compiled.names),
            "seed": int(seed),
            "reported_objective_recomputed_from_complete_vector": True,
        }
        return {
            "payload_name": str(payload_name),
            "payload_id": str(payload_name).removesuffix(".json"),
            "benchmark": str(payload["sc_cmpo"]["public_benchmark"]),
            "method": method,
            "backend": outcome.backend,
            "status": "completed",
            "failure_reason": "",
            "runtime_seconds": runtime,
            "seed": int(seed),
            "solution_values": values,
            "variable_count": len(values),
            "objective": objective,
            "objective_energy": objective,
            "raw_objective": objective
            if outcome.raw_objective is None
            else float(outcome.raw_objective),
            "trace_metadata": trace_metadata,
        }
    except Exception as exc:
        runtime = time.perf_counter() - started
        fallback_values = _clip_and_complete(compiled, warm)
        fallback_objective = compiled.evaluate(compiled.vector(fallback_values))
        return {
            "payload_name": str(payload_name),
            "payload_id": str(payload_name).removesuffix(".json"),
            "benchmark": str(payload["sc_cmpo"]["public_benchmark"]),
            "method": method,
            "backend": "failed before producing a method result",
            "status": "failed",
            "failure_reason": f"{type(exc).__name__}: {exc}",
            "runtime_seconds": runtime,
            "seed": int(seed),
            "solution_values": fallback_values,
            "variable_count": len(fallback_values),
            "objective": fallback_objective,
            "objective_energy": fallback_objective,
            "raw_objective": fallback_objective,
            "trace_metadata": {
                "payload_polynomial_degree": int(payload.get("max_degree", 0)),
                "payload_term_count": len(payload.get("polynomial_terms", ())),
                "payload_variable_count": len(compiled.names),
                "seed": int(seed),
                "fallback_vector_is_not_a_method_result": True,
            },
        }
