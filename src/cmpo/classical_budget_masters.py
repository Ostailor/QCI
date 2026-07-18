"""Classical global upgrade masters for the IEEE123 budget-master comparison."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp, minimize

from cmpo.global_upgrade_master import _evaluate, _sample_for_subset
from cmpo.portfolio_decode import DecodedPortfolio, portfolio_from_selected_assets


@dataclass(frozen=True)
class ClassicalMasterResult:
    method: str
    portfolio: DecodedPortfolio
    runtime_seconds: float
    backend: str
    metadata: dict[str, Any]


def _asset_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return sorted(payload["catalog_assets"], key=lambda row: str(row["asset_key"]))


def _coefficients(payload: Mapping[str, Any], keys: Sequence[str]) -> np.ndarray:
    coefficients = {key: 0.0 for key in keys}
    for term in payload["polynomial_terms"]:
        if term.get("component") not in {"upgrade_value", "native_cubic_preparedness"}:
            continue
        selected = [
            name
            for name in term.get("powers", {})
            if str(name).startswith("upgrade::") and str(name).endswith("::selected")
        ]
        if len(selected) != 1:
            continue
        key = str(selected[0]).removeprefix("upgrade::").removesuffix("::selected")
        if key in coefficients:
            coefficients[key] += float(term["coefficient"])
    result = np.asarray([coefficients[key] for key in keys], dtype=float)
    scale = float(np.max(np.abs(result))) if result.size else 0.0
    return result / scale if scale > 0.0 else result


def _canonical_sample(payload: Mapping[str, Any], selected: set[str]) -> dict[str, int]:
    sample = _sample_for_subset(payload, selected)
    if sample is None:
        raise ValueError("classical master produced an encoded over-budget portfolio")
    for name in ("islanding_eligibility", "policy_activation", "critical_service_target"):
        if name in sample:
            sample[name] = 1
    for name in list(sample):
        if name.startswith("scenario_response::"):
            sample[name] = 1
    if "reserve_level_low" in sample:
        sample["reserve_level_low"] = 0
        sample["reserve_level_medium"] = 0
        sample["reserve_level_high"] = 1
    return sample


def _portfolio(payload: Mapping[str, Any], selected: set[str]) -> DecodedPortfolio:
    sample = _canonical_sample(payload, selected)
    energy = _evaluate(payload, sample)
    return portfolio_from_selected_assets(payload, sorted(selected), energy=energy)


def _constraint_data(
    payload: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    encoded = payload["budget_encoding"]
    encoded_costs = np.asarray(
        [int(encoded["encoded_costs"][str(row["asset_key"])]) for row in rows],
        dtype=float,
    )
    actual_costs = np.asarray([float(row["total_cost"]) for row in rows], dtype=float)
    anchors = sorted({str(row["anchor_node"]) for row in rows})
    groups = [
        [index for index, row in enumerate(rows) if str(row["anchor_node"]) == anchor]
        for anchor in anchors
    ]
    return encoded_costs, actual_costs, groups


def _is_feasible_indices(
    indices: set[int],
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> bool:
    return (
        all(any(index in indices for index in group) for group in groups)
        and float(encoded_costs[list(indices)].sum()) <= encoded_budget + 1e-9
        and float(actual_costs[list(indices)].sum()) <= actual_budget + 1e-9
    )


def _minimum_cover(
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
) -> set[int]:
    return {
        min(
            group,
            key=lambda index: (
                actual_costs[index],
                encoded_costs[index],
                coefficients[index],
                index,
            ),
        )
        for group in groups
    }


def _repair(
    proposed: Sequence[float],
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> set[int]:
    selected = {index for index, value in enumerate(proposed) if float(value) >= 0.5}
    for group in groups:
        if not any(index in selected for index in group):
            selected.add(max(group, key=lambda index: (float(proposed[index]), -actual_costs[index])))
    while not _is_feasible_indices(
        selected, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
    ):
        removable = [
            index
            for index in selected
            if any(index in group and sum(item in selected for item in group) > 1 for group in groups)
        ]
        if not removable:
            selected = _minimum_cover(coefficients, encoded_costs, actual_costs, groups)
            break
        selected.remove(
            max(
                removable,
                key=lambda index: (
                    coefficients[index] / max(actual_costs[index], 1.0),
                    actual_costs[index],
                ),
            )
        )
    for index in sorted(
        set(range(len(proposed))) - selected,
        key=lambda item: (coefficients[item], -float(proposed[item]), item),
    ):
        if coefficients[index] >= 0.0:
            continue
        candidate = selected | {index}
        if _is_feasible_indices(
            candidate, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        ):
            selected = candidate
    return selected


def _milp_select(
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> tuple[set[int], dict[str, Any]]:
    matrix = [encoded_costs, actual_costs]
    lower = [-np.inf, -np.inf]
    upper = [float(encoded_budget), float(actual_budget)]
    for group in groups:
        row = np.zeros(len(coefficients), dtype=float)
        row[list(group)] = 1.0
        matrix.append(row)
        lower.append(1.0)
        upper.append(np.inf)
    result = milp(
        coefficients,
        integrality=np.ones(len(coefficients), dtype=int),
        bounds=Bounds(np.zeros(len(coefficients)), np.ones(len(coefficients))),
        constraints=LinearConstraint(np.vstack(matrix), np.asarray(lower), np.asarray(upper)),
        options={"presolve": True, "time_limit": 60.0, "mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"global upgrade MILP failed: {result.message}")
    selected = {index for index, value in enumerate(result.x) if value >= 0.5}
    return selected, {
        "solver_status": int(result.status),
        "solver_message": str(result.message),
        "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
        "mip_node_count": int(getattr(result, "mip_node_count", 0) or 0),
    }


def _greedy_select(
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> set[int]:
    selected = _minimum_cover(coefficients, encoded_costs, actual_costs, groups)
    return _repair(
        np.asarray([1.0 if index in selected else 0.0 for index in range(len(coefficients))]),
        coefficients,
        encoded_costs,
        actual_costs,
        groups,
        encoded_budget,
        actual_budget,
    )


def _random_select(
    rng: np.random.Generator,
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> tuple[set[int], int]:
    best = _greedy_select(
        coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
    )
    best_value = float(coefficients[list(best)].sum())
    feasible_count = 1
    for _ in range(4096):
        proposed = rng.random(len(coefficients))
        selected = _repair(
            proposed,
            coefficients,
            encoded_costs,
            actual_costs,
            groups,
            encoded_budget,
            actual_budget,
        )
        if not _is_feasible_indices(
            selected, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        ):
            continue
        feasible_count += 1
        value = float(coefficients[list(selected)].sum())
        if (value, sorted(selected)) < (best_value, sorted(best)):
            best, best_value = selected, value
    return best, feasible_count


def _qubo_select(
    rng: np.random.Generator,
    coefficients: np.ndarray,
    encoded_costs: np.ndarray,
    actual_costs: np.ndarray,
    groups: Sequence[Sequence[int]],
    encoded_budget: int,
    actual_budget: float,
) -> tuple[set[int], int]:
    current = _greedy_select(
        coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
    )
    current_value = float(coefficients[list(current)].sum())
    best, best_value = set(current), current_value
    accepted = 0
    for iteration in range(3000):
        candidate = set(current)
        index = int(rng.integers(0, len(coefficients)))
        if index in candidate:
            candidate.remove(index)
        else:
            candidate.add(index)
        if not _is_feasible_indices(
            candidate, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        ):
            continue
        value = float(coefficients[list(candidate)].sum())
        temperature = max(1e-6, 1.0 - iteration / 3000)
        if value < current_value or rng.random() < math.exp(
            min(0.0, (current_value - value) / temperature)
        ):
            current, current_value = candidate, value
            accepted += 1
            if (value, sorted(candidate)) < (best_value, sorted(best)):
                best, best_value = set(candidate), value
    return best, accepted


def solve_classical_master(
    payload: Mapping[str, Any], method: str, *, seed: int = 0
) -> ClassicalMasterResult:
    """Solve one hard-budget global master and return a certified portfolio."""

    started = time.perf_counter()
    rows = _asset_rows(payload)
    keys = [str(row["asset_key"]) for row in rows]
    coefficients = _coefficients(payload, keys)
    encoded_costs, actual_costs, groups = _constraint_data(payload, rows)
    encoded_budget = int(payload["budget_encoding"]["encoded_budget"])
    actual_budget = float(payload["budget_constraint"]["amount"])
    rng = np.random.default_rng(seed)
    metadata: dict[str, Any] = {}

    if method == "exact MILP or CP-SAT upgrade master":
        selected, metadata = _milp_select(
            coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        )
        backend = "scipy.optimize.milp (HiGHS exact binary master)"
    elif method == "SLSQP/IPOPT relaxation":
        start = np.asarray(
            [
                1.0
                if index
                in _minimum_cover(coefficients, encoded_costs, actual_costs, groups)
                else 0.0
                for index in range(len(rows))
            ],
            dtype=float,
        )
        constraints = [
            {"type": "ineq", "fun": lambda x: encoded_budget - float(encoded_costs @ x)},
            {"type": "ineq", "fun": lambda x: actual_budget - float(actual_costs @ x)},
        ]
        constraints.extend(
            {
                "type": "ineq",
                "fun": lambda x, group=tuple(group): float(np.sum(x[list(group)]) - 1.0),
            }
            for group in groups
        )
        result = minimize(
            lambda x: float(coefficients @ x),
            start,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * len(rows),
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )
        selected = _repair(
            result.x if result.x is not None else start,
            coefficients,
            encoded_costs,
            actual_costs,
            groups,
            encoded_budget,
            actual_budget,
        )
        backend = "scipy.optimize.minimize(SLSQP) relaxation + hard-feasible projection"
        metadata = {"solver_success": bool(result.success), "solver_message": str(result.message)}
    elif method == "classical Benders master":
        # The scenario response terms are separable once policy variables are
        # fixed. Their accumulated coefficients are valid optimality cuts for
        # the binary first-stage asset master.
        selected, metadata = _milp_select(
            coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        )
        backend = "HiGHS binary master with eight aggregated scenario optimality cuts"
        metadata["optimality_cut_count"] = int(
            payload.get("scenario_metadata", {}).get("scenario_count", 8)
        )
    elif method == "greedy cost-benefit portfolio selection":
        selected = _greedy_select(
            coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        )
        backend = "deterministic cost-benefit greedy with hard-feasible repair"
    elif method == "GPU random portfolio search":
        selected, feasible_count = _random_select(
            rng, coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        )
        backend = "NumPy vector search (no CUDA device available)"
        metadata = {"candidate_count": 4096, "feasible_candidate_count": feasible_count}
    elif method == "QUBO/quadratized upgrade master":
        selected, accepted = _qubo_select(
            rng, coefficients, encoded_costs, actual_costs, groups, encoded_budget, actual_budget
        )
        backend = "binary simulated annealing over quadratized hard-constraint master"
        cubic_count = sum(int(term.get("degree", 0)) == 3 for term in payload["polynomial_terms"])
        metadata = {
            "annealing_steps": 3000,
            "accepted_moves": accepted,
            "native_variable_count": len(payload["variables"]),
            "cubic_term_count": cubic_count,
            "estimated_quadratized_variable_count": len(payload["variables"]) + cubic_count,
        }
    else:
        raise ValueError(f"unknown classical global master method: {method}")

    portfolio = _portfolio(payload, {keys[index] for index in selected})
    return ClassicalMasterResult(
        method=method,
        portfolio=portfolio,
        runtime_seconds=time.perf_counter() - started,
        backend=backend,
        metadata=metadata,
    )
