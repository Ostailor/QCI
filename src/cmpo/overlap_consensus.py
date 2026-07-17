"""Deterministic overlap consensus for system-level SC-CMPO reconstruction.

Patch variables are expanded onto public-system consensus keys before a
scaled-ADMM iteration.  Shared first-stage decisions have benchmark scope,
node recourse has public-node scope, and PCC recourse has public boundary-edge
scope.  This prevents independent patch metrics from being treated as a
full-system result.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Any


_SCENARIO_VARIABLE = re.compile(r"^(?P<group>[^\[]+)\[(?P<scenario>[^\]]+)\]$")
_MODE_GROUPS = ("mode_connected", "mode_islanded", "mode_restoration")
_BATTERY_GROUPS = (
    "battery_action_charge",
    "battery_action_hold",
    "battery_action_discharge",
)
_GENERATION_GROUPS = {"der_commitment", "der_capacity_slack"}
_SERVICE_GROUPS = {"critical_load_service", "load_shedding_allocation"}
_RAW_CONFLICT_EPSILON = 1e-12
_SELECTION_EPSILON = 1e-12


@dataclass(frozen=True)
class _LocalCopy:
    payload_name: str
    variable_name: str
    global_key: str
    value: float

    @property
    def copy_id(self) -> tuple[str, str, str]:
        return (self.payload_name, self.variable_name, self.global_key)


def _failed_result(reason: str, **details: Any) -> dict[str, Any]:
    return {
        "status": "failed",
        "converged": False,
        "failure_reason": reason,
        "iteration_count": 0,
        "iterations": 0,
        "primal_residual": math.inf,
        "dual_residual": math.inf,
        "consensus_residual": math.inf,
        "raw_conflict_count": 0,
        "raw_conflicts": [],
        "unresolved_conflicts": [],
        "convergence_trace": [],
        "residual_trace": [],
        **details,
    }


def _payload_benchmark(payload: Mapping[str, Any]) -> str:
    try:
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
    except (KeyError, TypeError) as exc:
        raise ValueError("payload lacks sc_cmpo.public_benchmark") from exc
    if not benchmark:
        raise ValueError("payload has an empty public benchmark name")
    return benchmark


def _patch_scope(payload: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        patch = payload["sc_cmpo"]["upgrade_patch"]
        nodes = tuple(sorted({str(node) for node in patch["node_ids"]}))
        edges = tuple(sorted({str(edge) for edge in patch["boundary_edge_ids"]}))
    except (KeyError, TypeError) as exc:
        raise ValueError("payload lacks public patch node or boundary-edge metadata") from exc
    if not nodes:
        raise ValueError("payload patch has no public nodes")
    if not edges:
        raise ValueError("payload patch has no public boundary edges for PCC consensus")
    return nodes, edges


def _scenario_parts(variable_name: str) -> tuple[str, str]:
    match = _SCENARIO_VARIABLE.fullmatch(variable_name)
    if match is None:
        raise ValueError(f"unsupported non-shared SC-CMPO variable: {variable_name}")
    return match.group("group"), match.group("scenario")


def _global_keys(payload: Mapping[str, Any], variable_name: str) -> tuple[str, ...]:
    """Map one patch variable to its benchmark, node, or boundary scope."""

    sc_cmpo = payload.get("sc_cmpo")
    if not isinstance(sc_cmpo, Mapping):
        raise ValueError("payload lacks SC-CMPO metadata")
    benchmark = _payload_benchmark(payload)
    shared = {str(name) for name in sc_cmpo.get("shared_first_stage_variables", [])}
    if variable_name in shared:
        return (f"{benchmark}::first_stage::{variable_name}",)

    group, scenario = _scenario_parts(variable_name)
    scenarios = {str(name) for name in sc_cmpo.get("scenario_names", [])}
    if scenario not in scenarios:
        raise ValueError(f"variable {variable_name} names an undocumented scenario")
    nodes, edges = _patch_scope(payload)
    prefix = f"{benchmark}::scenario::{scenario}"
    if group in _MODE_GROUPS:
        return tuple(f"{prefix}::node::{node}::mode::{group}" for node in nodes)
    if group in _GENERATION_GROUPS:
        return tuple(f"{prefix}::node::{node}::generation::{group}" for node in nodes)
    if group in _BATTERY_GROUPS:
        return tuple(f"{prefix}::node::{node}::storage::{group}" for node in nodes)
    if group in _SERVICE_GROUPS:
        return tuple(f"{prefix}::node::{node}::service::{group}" for node in nodes)
    if group == "tie_pcc_response":
        return tuple(f"{prefix}::boundary_edge::{edge}::tie_pcc_response" for edge in edges)
    raise ValueError(f"unsupported SC-CMPO recourse group: {group}")


def _variable_specs(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    variables = payload.get("variables")
    if not isinstance(variables, Sequence) or isinstance(variables, (str, bytes)):
        raise ValueError("payload variables must be a sequence")
    specs: dict[str, Mapping[str, Any]] = {}
    for variable in variables:
        if not isinstance(variable, Mapping) or "name" not in variable:
            raise ValueError("payload contains malformed variable metadata")
        name = str(variable["name"])
        if name in specs:
            raise ValueError(f"payload declares duplicate variable {name}")
        specs[name] = variable
    if not specs:
        raise ValueError("payload declares no variables")
    return specs


def _row_payload_name(row: Mapping[str, Any], aliases: Mapping[str, str]) -> str | None:
    raw_name = row.get("payload_name", row.get("payload_id", row.get("payload")))
    if raw_name is None:
        return None
    name = str(raw_name)
    for alias in (name, Path(name).name, Path(name).stem):
        if alias in aliases:
            return aliases[alias]
    return None


def _payload_aliases(payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    ambiguous: set[str] = set()
    for payload_name in payloads:
        name = str(payload_name)
        for alias in (name, Path(name).name, Path(name).stem):
            if alias in aliases and aliases[alias] != name:
                ambiguous.add(alias)
            else:
                aliases[alias] = name
    for alias in ambiguous:
        aliases.pop(alias, None)
    return aliases


def _solution_values(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("solution_values", "repaired_variables", "decoded_variables", "values"):
        values = row.get(key)
        if isinstance(values, Mapping):
            return values
    return None


def _finite_number(value: Any) -> float:
    if isinstance(value, (str, bytes)) or value is None:
        raise ValueError("solution value is not numeric")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("solution value is not numeric") from exc
    if not math.isfinite(numeric):
        raise ValueError("solution value is not finite")
    return numeric


def _collect_local_copies(
    payloads: Mapping[str, Mapping[str, Any]],
    rows_by_payload: Mapping[str, Mapping[str, Any]],
) -> tuple[list[_LocalCopy], list[dict[str, Any]]]:
    copies: list[_LocalCopy] = []
    traceability: list[dict[str, Any]] = []
    for payload_name in sorted(payloads):
        payload = payloads[payload_name]
        specs = _variable_specs(payload)
        values = _solution_values(rows_by_payload[payload_name])
        if values is None:
            raise ValueError(f"{payload_name}: solution variable mapping is missing")
        normalized_values = {str(name): value for name, value in values.items()}
        missing = sorted(set(specs).difference(normalized_values))
        if missing:
            raise ValueError(f"{payload_name}: missing variables: {', '.join(missing)}")
        for variable_name in specs:
            value = _finite_number(normalized_values[variable_name])
            keys = _global_keys(payload, variable_name)
            traceability.append(
                {
                    "payload_name": payload_name,
                    "variable_name": variable_name,
                    "global_keys": list(keys),
                }
            )
            copies.extend(
                _LocalCopy(payload_name, variable_name, global_key, value)
                for global_key in keys
            )
    return copies, traceability


def _raw_conflicts(copies_by_key: Mapping[str, Sequence[_LocalCopy]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for global_key in sorted(copies_by_key):
        copies = copies_by_key[global_key]
        values = [copy.value for copy in copies]
        spread = max(values) - min(values)
        if len(values) > 1 and spread > _RAW_CONFLICT_EPSILON:
            conflicts.append(
                {
                    "global_key": global_key,
                    "support": len(values),
                    "minimum": min(values),
                    "maximum": max(values),
                    "spread": spread,
                    "sources": [
                        {
                            "payload_name": copy.payload_name,
                            "variable_name": copy.variable_name,
                            "value": copy.value,
                        }
                        for copy in copies
                    ],
                }
            )
    return conflicts


def _unresolved_conflicts(
    copies_by_key: Mapping[str, Sequence[_LocalCopy]],
    local_values: Mapping[tuple[str, str, str], float],
    consensus_values: Mapping[str, float],
    tolerance: float,
) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    for global_key in sorted(copies_by_key):
        deviations = [
            abs(local_values[copy.copy_id] - consensus_values[global_key])
            for copy in copies_by_key[global_key]
        ]
        maximum = max(deviations, default=0.0)
        if maximum > tolerance:
            unresolved.append(
                {
                    "global_key": global_key,
                    "maximum_local_deviation": maximum,
                    "support": len(deviations),
                }
            )
    return unresolved


def _run_admm(
    copies_by_key: Mapping[str, Sequence[_LocalCopy]],
    tolerance: float,
    max_iterations: int,
    rho: float,
) -> dict[str, Any]:
    consensus = {
        key: math.fsum(copy.value for copy in copies) / len(copies)
        for key, copies in copies_by_key.items()
    }
    local = {copy.copy_id: copy.value for copies in copies_by_key.values() for copy in copies}
    dual = {copy_id: 0.0 for copy_id in local}
    trace: list[dict[str, Any]] = []
    converged = False

    for iteration in range(1, max_iterations + 1):
        previous_consensus = dict(consensus)
        for global_key in sorted(copies_by_key):
            for copy in copies_by_key[global_key]:
                local[copy.copy_id] = (
                    copy.value + rho * (previous_consensus[global_key] - dual[copy.copy_id])
                ) / (1.0 + rho)
        for global_key in sorted(copies_by_key):
            copies = copies_by_key[global_key]
            consensus[global_key] = math.fsum(
                local[copy.copy_id] + dual[copy.copy_id] for copy in copies
            ) / len(copies)
        for global_key in sorted(copies_by_key):
            for copy in copies_by_key[global_key]:
                dual[copy.copy_id] += local[copy.copy_id] - consensus[global_key]

        primal = math.sqrt(
            math.fsum(
                (local[copy.copy_id] - consensus[global_key]) ** 2
                for global_key, copies in copies_by_key.items()
                for copy in copies
            )
        )
        dual_residual = rho * math.sqrt(
            math.fsum(
                len(copies) * (consensus[key] - previous_consensus[key]) ** 2
                for key, copies in copies_by_key.items()
            )
        )
        trace.append(
            {
                "iteration": iteration,
                "primal_residual": primal,
                "dual_residual": dual_residual,
            }
        )
        if primal <= tolerance and dual_residual <= tolerance:
            converged = True
            break

    return {
        "converged": converged,
        "consensus_values": dict(sorted(consensus.items())),
        "local_values": local,
        "trace": trace,
    }


def run_method_consensus(
    payloads: Mapping[str, Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    tolerance: float = 1e-6,
    max_iterations: int = 200,
    rho: float = 1.0,
) -> dict[str, Any]:
    """Reconcile one method's complete patch solution set using scaled ADMM.

    A failed or incomplete input returns diagnostics without consensus values,
    preventing downstream code from emitting a partial system-level result.
    """

    if not payloads:
        return _failed_result("no payloads supplied", missing_payloads=[])
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        return _failed_result("tolerance must be a positive finite number", missing_payloads=[])
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        return _failed_result("max_iterations must be a positive integer", missing_payloads=[])
    if not math.isfinite(rho) or rho <= 0.0:
        return _failed_result("rho must be a positive finite number", missing_payloads=[])

    aliases = _payload_aliases(payloads)
    rows_by_payload: dict[str, Mapping[str, Any]] = {}
    unexpected_rows: list[str] = []
    duplicate_payloads: list[str] = []
    for index, row in enumerate(rows):
        payload_name = _row_payload_name(row, aliases)
        if payload_name is None:
            unexpected_rows.append(str(row.get("payload_name", f"row[{index}]")))
            continue
        if payload_name in rows_by_payload:
            duplicate_payloads.append(payload_name)
            continue
        rows_by_payload[payload_name] = row
    missing_payloads = sorted(set(payloads).difference(rows_by_payload))
    if missing_payloads or unexpected_rows or duplicate_payloads:
        return _failed_result(
            "incomplete or ambiguous payload solution coverage",
            missing_payloads=missing_payloads,
            unexpected_rows=sorted(unexpected_rows),
            duplicate_payloads=sorted(set(duplicate_payloads)),
        )

    try:
        benchmarks = {_payload_benchmark(payload) for payload in payloads.values()}
        if len(benchmarks) != 1:
            raise ValueError("one consensus run must contain exactly one public benchmark")
        methods = {str(row.get("method", "unknown")) for row in rows_by_payload.values()}
        if len(methods) != 1:
            raise ValueError("one consensus run must contain exactly one method")
        copies, traceability = _collect_local_copies(payloads, rows_by_payload)
        source_runtime = math.fsum(
            max(0.0, _finite_number(row.get("runtime_seconds", 0.0)))
            for row in rows_by_payload.values()
        )
    except ValueError as exc:
        return _failed_result(
            str(exc),
            missing_payloads=[],
            invalid_payloads=sorted(payloads),
        )
    if not copies:
        return _failed_result("no consensus variables were mapped", missing_payloads=[])

    copies_by_key: dict[str, list[_LocalCopy]] = defaultdict(list)
    for copy in copies:
        copies_by_key[copy.global_key].append(copy)
    conflicts = _raw_conflicts(copies_by_key)
    admm = _run_admm(copies_by_key, tolerance, max_iterations, rho=rho)
    trace = admm["trace"]
    final_trace = trace[-1]
    unresolved = _unresolved_conflicts(
        copies_by_key,
        admm["local_values"],
        admm["consensus_values"],
        tolerance,
    )
    common = {
        "benchmark": next(iter(benchmarks)),
        "method": next(iter(methods)),
        "payload_count": len(payloads),
        "solution_row_count": len(rows_by_payload),
        "consensus_key_count": len(copies_by_key),
        "local_copy_count": len(copies),
        "tolerance": tolerance,
        "rho": rho,
        "iteration_count": len(trace),
        "iterations": len(trace),
        "primal_residual": final_trace["primal_residual"],
        "dual_residual": final_trace["dual_residual"],
        "consensus_residual": max(
            final_trace["primal_residual"], final_trace["dual_residual"]
        ),
        "raw_conflict_count": len(conflicts),
        "raw_conflicts": conflicts,
        "unresolved_conflicts": unresolved,
        "convergence_trace": trace,
        "residual_trace": trace,
        "traceability": traceability,
        "support_by_key": {
            key: len(copies_by_key[key]) for key in sorted(copies_by_key)
        },
        "support": {key: len(copies_by_key[key]) for key in sorted(copies_by_key)},
        "source_runtime_seconds": source_runtime,
        "missing_payloads": [],
    }
    if not admm["converged"] or unresolved:
        return {
            "status": "failed",
            "converged": False,
            "failure_reason": "overlap consensus did not converge",
            **common,
        }
    try:
        reconstructed = reconstruct_patch_values(payloads, admm["consensus_values"])
        post_reconstruction_conflicts = validate_reconstructed_overlap(
            payloads,
            reconstructed,
            tolerance=tolerance,
        )
    except ValueError as exc:
        return {
            "status": "failed",
            "converged": False,
            "failure_reason": str(exc),
            "post_reconstruction_conflicts": [],
            **common,
        }
    if post_reconstruction_conflicts:
        return {
            "status": "failed",
            "converged": False,
            "failure_reason": "post-reconstruction overlap conflicts remain",
            "post_reconstruction_conflicts": post_reconstruction_conflicts,
            **common,
        }
    return {
        "status": "completed",
        "converged": True,
        "post_reconstruction_conflicts": [],
        **common,
        "consensus_values": admm["consensus_values"],
    }


def _bounded_value(spec: Mapping[str, Any], value: float) -> float:
    lower = float(spec.get("lower_bound", spec.get("bounds", [0.0, 1.0])[0]))
    upper = float(spec.get("upper_bound", spec.get("bounds", [0.0, 1.0])[1]))
    return min(max(value, lower), upper)


def _repair_one_hot(values: dict[str, float | int], names: Sequence[str]) -> None:
    if not all(name in values for name in names):
        raise ValueError(f"one-hot group is incomplete: {', '.join(names)}")
    selected = max(names, key=lambda name: (float(values[name]), -names.index(name)))
    values.update({name: int(name == selected) for name in names})


def _repair_patch_semantics(
    payload: Mapping[str, Any], values: dict[str, float | int]
) -> dict[str, float | int]:
    _repair_one_hot(
        values,
        ("base_mode_connected", "base_mode_islanded", "base_mode_restoration"),
    )
    scenarios = [str(name) for name in payload["sc_cmpo"]["scenario_names"]]
    for scenario in scenarios:
        _repair_one_hot(values, tuple(f"{group}[{scenario}]" for group in _MODE_GROUPS))
        _repair_one_hot(values, tuple(f"{group}[{scenario}]" for group in _BATTERY_GROUPS))

    links = (
        ("pv_capacity_fraction", "upgrade_select_pv"),
        ("bess_energy_fraction", "upgrade_select_bess"),
        ("dispatchable_capacity_fraction", "upgrade_select_dispatchable"),
    )
    upgrade_names = {"bess_power_fraction", *(name for pair in links for name in pair)}
    if upgrade_names.issubset(values):
        bess_fraction = min(
            float(values["bess_energy_fraction"]),
            float(values["bess_power_fraction"]),
        )
        values["bess_energy_fraction"] = bess_fraction
        values["bess_power_fraction"] = bess_fraction
        for fraction_name, selection_name in links:
            values[selection_name] = int(float(values[fraction_name]) > _SELECTION_EPSILON)

    for variable_name, spec in _variable_specs(payload).items():
        if str(spec.get("encoding_type", "")) != "integer":
            continue
        lower = float(spec.get("lower_bound", spec.get("bounds", [0.0, 1.0])[0]))
        upper = float(spec.get("upper_bound", spec.get("bounds", [0.0, 1.0])[1]))
        values[variable_name] = int(float(values[variable_name]) >= (lower + upper) / 2.0)
    return values


def _overlap_components(
    payloads: Mapping[str, Mapping[str, Any]],
) -> list[tuple[str, ...]]:
    scopes: dict[str, tuple[set[str], set[str]]] = {}
    for payload_name, payload in payloads.items():
        nodes, edges = _patch_scope(payload)
        scopes[payload_name] = (set(nodes), set(edges))
    remaining = set(payloads)
    components: list[tuple[str, ...]] = []
    while remaining:
        component = {min(remaining)}
        frontier = list(component)
        remaining.difference_update(component)
        while frontier:
            current = frontier.pop()
            current_nodes, current_edges = scopes[current]
            neighbors = {
                candidate
                for candidate in remaining
                if current_nodes.intersection(scopes[candidate][0])
                or current_edges.intersection(scopes[candidate][1])
            }
            component.update(neighbors)
            frontier.extend(sorted(neighbors))
            remaining.difference_update(neighbors)
        components.append(tuple(sorted(component)))
    return sorted(components)


def validate_reconstructed_overlap(
    payloads: Mapping[str, Mapping[str, Any]],
    patch_values: Mapping[str, Mapping[str, Any]],
    *,
    tolerance: float = 1e-9,
) -> list[dict[str, Any]]:
    """Return any shared/node/edge conflicts remaining after reconstruction."""

    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("overlap validation tolerance must be finite and nonnegative")
    missing_payloads = sorted(set(payloads) - set(patch_values))
    if missing_payloads:
        raise ValueError(f"reconstructed values are missing payloads: {missing_payloads}")
    observed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload_name, payload in payloads.items():
        values = patch_values[payload_name]
        specs = _variable_specs(payload)
        missing_variables = sorted(set(specs) - set(values))
        if missing_variables:
            raise ValueError(f"{payload_name}: reconstructed values are incomplete: {missing_variables}")
        for variable_name in specs:
            value = _finite_number(values[variable_name])
            for global_key in _global_keys(payload, variable_name):
                observed[global_key].append(
                    {
                        "payload_name": payload_name,
                        "variable_name": variable_name,
                        "value": value,
                    }
                )
    conflicts: list[dict[str, Any]] = []
    for global_key, rows in sorted(observed.items()):
        values = [float(row["value"]) for row in rows]
        spread = max(values) - min(values)
        if len(values) > 1 and spread > tolerance:
            conflicts.append(
                {
                    "global_key": global_key,
                    "support": len(values),
                    "minimum": min(values),
                    "maximum": max(values),
                    "spread": spread,
                    "sources": rows,
                }
            )
    return conflicts


def reconstruct_patch_values(
    payloads: Mapping[str, Mapping[str, Any]],
    consensus_values: Mapping[str, Any],
) -> dict[str, dict[str, float | int]]:
    """Map converged global consensus back to complete repaired patch vectors."""

    if not payloads:
        raise ValueError("no payloads supplied for reconstruction")
    finite_consensus: dict[str, float] = {}
    for key, value in consensus_values.items():
        finite_consensus[str(key)] = _finite_number(value)

    preliminary: dict[str, dict[str, float | int]] = {}
    for payload_name in sorted(payloads):
        payload = payloads[payload_name]
        specs = _variable_specs(payload)
        values: dict[str, float | int] = {}
        for variable_name, spec in specs.items():
            keys = _global_keys(payload, variable_name)
            missing = [key for key in keys if key not in finite_consensus]
            if missing:
                raise ValueError(
                    f"{payload_name}: consensus is missing keys for {variable_name}: "
                    + ", ".join(missing)
                )
            consensus_mean = math.fsum(finite_consensus[key] for key in keys) / len(keys)
            values[variable_name] = _bounded_value(spec, consensus_mean)
        preliminary[payload_name] = values

    reconstructed: dict[str, dict[str, float | int]] = {}
    for component in _overlap_components(payloads):
        representative = payloads[component[0]]
        names = set(_variable_specs(representative))
        for payload_name in component[1:]:
            if set(_variable_specs(payloads[payload_name])) != names:
                raise ValueError("overlapping SC-CMPO payloads have different variable schemas")
        component_values = {
            variable_name: math.fsum(float(preliminary[name][variable_name]) for name in component)
            / len(component)
            for variable_name in sorted(names)
        }
        repaired = _repair_patch_semantics(representative, component_values)
        for payload_name in component:
            reconstructed[payload_name] = dict(repaired)

    conflicts = validate_reconstructed_overlap(payloads, reconstructed)
    if conflicts:
        raise ValueError(f"post-reconstruction overlap conflicts remain: {conflicts}")
    return reconstructed
