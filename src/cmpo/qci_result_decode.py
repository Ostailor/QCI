"""Decode raw QCi Dirac-3 responses and apply CMPO repair/metrics."""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from cmpo.baseline_orchestrator import (
    build_grid_case_from_config,
    load_phase3_config,
    load_phase3_manifest,
    phase3_output_dir,
)
from cmpo.baselines import _make_result
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.phase3_metrics import add_phase3_columns
from cmpo.qci_fit_decomposition import BENCHMARK_CONFIGS
from cmpo.repair import compute_balance_residuals, repair_solution

MODE_NAMES = ("grid", "island", "restore")
FAILURE_COLUMNS = [
    "response_json",
    "request_json",
    "payload",
    "job_id",
    "status",
    "repeat",
    "failure_reason",
]
REPEAT_METRIC_COLUMNS = [
    "method_name",
    "scenario",
    "patch",
    "expected_operating_cost",
    "risk_adjusted_cost",
    "critical_load_served_fraction",
    "critical_energy_not_served_kwh",
    "energy_not_served_kwh",
    "max_fraction_customers_unserved_per_hour",
    "total_critical_infrastructure_unserved_hours_proxy",
    "feasibility_after_repair",
    "pre_repair_violation",
    "post_repair_violation",
    "qci_energy",
    "decoded_objective",
    "runtime_seconds",
    "time_to_good_solution",
]
PAYLOAD_SUMMARY_COLUMNS = [
    "dataset",
    "payload_name",
    "scenario",
    "patch",
    "sample_count",
    "repeat_count",
    "job_count",
    "expected_operating_cost_best",
    "expected_operating_cost_median",
    "risk_adjusted_cost_best",
    "risk_adjusted_cost_median",
    "critical_load_served_fraction_best",
    "critical_load_served_fraction_median",
    "critical_energy_not_served_best",
    "total_energy_not_served_best",
    "max_fraction_customers_unserved_per_hour_best",
    "total_critical_infrastructure_unserved_hours_proxy_best",
    "feasibility_after_repair_rate",
    "pre_repair_violation_rate",
    "post_repair_violation_rate",
    "pre_repair_violation_median",
    "post_repair_violation_median",
    "qci_energy_best",
    "qci_energy_median",
    "decoded_objective_best",
    "runtime_seconds_total",
    "runtime_seconds_median",
    "time_to_good_solution",
]
BEST_SOLUTION_COLUMNS = [
    "dataset",
    "payload_name",
    "scenario",
    "patch",
    "job_id",
    "repeat",
    "sample_index",
    "qci_energy",
    "decoded_objective",
    "repaired_objective",
    "expected_cost_component",
    "critical_load_served_fraction",
    "energy_not_served_kwh",
    "feasibility_pass",
    "pre_repair_violation_count",
    "post_repair_violation_count",
    "raw_solution",
    "repaired_solution",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _safe_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _parse_repeat(path: Path, fallback: int = 0) -> int:
    for part in reversed(path.parts):
        match = re.search(r"repeat[_-](\d+)", part)
        if match:
            return int(match.group(1))
    match = re.search(r"(?:repeat|r)[_-]?(\d+)", path.stem)
    return int(match.group(1)) if match else fallback


def _request_for_response(response_path: Path) -> Path | None:
    sibling = response_path.with_name("request.json")
    if sibling.exists():
        return sibling
    stem_candidate = response_path.with_name(response_path.stem.replace("response", "request") + response_path.suffix)
    return stem_candidate if stem_candidate.exists() else None


def _discover_response_files(experiment_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    search_dirs = [
        experiment_dir,
        experiment_dir / "qci" / "raw",
        experiment_dir / "qci_raw",
        experiment_dir / "qci",
    ]
    for raw_dir in search_dirs:
        if raw_dir.exists():
            candidates.extend(sorted(raw_dir.glob("*.json")))
            candidates.extend(sorted(raw_dir.glob("**/response.json")))
    unique = []
    seen = set()
    for path in candidates:
        lower_name = path.name.lower()
        if "request" in lower_name or "manifest" in lower_name or path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _payload_manifest_paths(experiment_dir: Path, explicit: Path | None) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    manifest_path = explicit or experiment_dir / "payload_manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        manifest_dir = manifest_path.parent
        payloads = manifest.get("payloads", manifest if isinstance(manifest, list) else [])
        for item in payloads:
            if isinstance(item, str):
                path = Path(item)
                if not path.is_absolute():
                    path = manifest_dir / path
                paths[path.name] = path
            elif isinstance(item, dict):
                raw_path = item.get("path") or item.get("payload_path") or item.get("payload")
                if raw_path:
                    path = Path(raw_path)
                    if not path.is_absolute():
                        path = manifest_dir / path
                    paths[path.name] = path
    return paths


def _payload_name_candidates(response_path: Path) -> list[str]:
    stems = [response_path.stem]
    if response_path.parent.name.startswith("repeat_"):
        stems.append(response_path.parent.parent.name)
    if response_path.parent.name == "raw":
        stems.extend(
            [
                re.sub(r"[_-]?response$", "", response_path.stem),
                re.sub(r"[_-]?repeat[_-]?\d+$", "", response_path.stem),
                re.sub(r"[_-]?r\d+$", "", response_path.stem),
            ]
        )
        stems.append(re.sub(r"[_-]?repeat[_-]?\d+[_-]?response$", "", response_path.stem))
    candidates: list[str] = []
    for stem in stems:
        if stem and stem not in candidates:
            candidates.extend([stem, f"{stem}.json"])
    return candidates


def _payload_path_from_context(
    request: dict[str, Any],
    response: dict[str, Any],
    response_path: Path,
    manifest_paths: dict[str, Path],
) -> Path | None:
    raw = request.get("payload_path") or request.get("payload") or response.get("payload_path") or response.get("payload")
    if raw:
        return Path(raw)
    metadata = (
        request.get("qci_file", {}).get("cmpo_metadata")
        or response.get("qci_file", {}).get("cmpo_metadata")
        or response.get("cmpo_metadata")
        or {}
    )
    patch = metadata.get("patch_metadata", {}).get("patch")
    scenario = metadata.get("scenario_metadata", {}).get("scenario")
    if scenario and patch:
        return manifest_paths.get(f"{scenario}_{patch}.json")
    for candidate in _payload_name_candidates(response_path):
        if candidate in manifest_paths:
            return manifest_paths[candidate]
    return None


def _variable_order(request: dict[str, Any], payload: dict[str, Any] | None) -> list[str]:
    order = request.get("qci_file", {}).get("cmpo_metadata", {}).get("variable_order")
    if order:
        return [str(name) for name in order]
    if payload is not None:
        return [str(variable["name"]) for variable in payload.get("variables", [])]
    return []


def _solutions(response: dict[str, Any]) -> list[list[float]]:
    results = response.get("results", {})
    solutions = results.get("solutions") or results.get("samples") or response.get("solutions") or []
    return [[float(value) for value in solution] for solution in solutions]


def _energies(response: dict[str, Any]) -> list[float]:
    results = response.get("results", {})
    energies = results.get("energies") or results.get("energy") or response.get("energies") or []
    return [float(value) for value in energies]


def _job_id(response: dict[str, Any]) -> str:
    return str(
        response.get("job_id")
        or response.get("job_info", {}).get("job_id")
        or response.get("job_info", {}).get("job_submission_id")
        or ""
    )


def _status(response: dict[str, Any]) -> str:
    return str(response.get("status") or response.get("job_status") or response.get("job_info", {}).get("status") or "UNKNOWN")


def _runtime_from_response(response: dict[str, Any], fallback: float = 0.0) -> float:
    for key in ["runtime_seconds", "runtime", "wall_clock_runtime_seconds"]:
        if response.get(key) is not None:
            return float(response[key])
    usage = response.get("job_info", {}).get("job_result", {}).get("device_usage_s")
    if usage is not None:
        return float(usage)
    status = response.get("job_info", {}).get("job_status", {})
    start = status.get("running_at_rfc3339nano") or status.get("submitted_at_rfc3339nano")
    end = status.get("completed_at_rfc3339nano")
    if start and end:
        try:
            return max(pd.Timestamp(end).timestamp() - pd.Timestamp(start).timestamp(), 0.0)
        except Exception:
            return fallback
    return fallback


def _microgrid_index(grid_case, microgrid_id: str) -> int:
    for index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name == microgrid_id:
            return index
    raise KeyError(microgrid_id)


def _var(prefix: str, microgrid_id: str, hour: int) -> str:
    return f"{prefix}[{microgrid_id},{hour}]"


def _violation_report(solution: dict[str, float], model, grid_case, patch: tuple[str, ...], scenario) -> dict[str, Any]:
    bounds_count = 0
    bounds_magnitude = 0.0
    for name, variable in model.variables.items():
        value = float(solution.get(name, 0.0))
        if value < variable.lower_bound:
            bounds_count += 1
            bounds_magnitude += variable.lower_bound - value
        elif value > variable.upper_bound:
            bounds_count += 1
            bounds_magnitude += value - variable.upper_bound

    mode_violations = 0
    mode_magnitude = 0.0
    pcc_violations = 0
    charge_discharge_violations = 0
    charge_discharge_magnitude = 0.0
    storage_violations = 0
    load_shed_violations = 0
    generator_availability_violations = 0
    microgrids = {microgrid.name: microgrid for microgrid in grid_case.microgrids}
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        mg_index = _microgrid_index(grid_case, microgrid_id)
        for hour in range(grid_case.horizon_hours):
            mode_total = sum(float(solution.get(_var(f"z_{mode}", microgrid_id, hour), 0.0)) for mode in MODE_NAMES)
            if abs(mode_total - 1.0) > 1e-6:
                mode_violations += 1
                mode_magnitude += abs(mode_total - 1.0)
            charge = max(float(solution.get(_var("charge", microgrid_id, hour), 0.0)), 0.0)
            discharge = max(float(solution.get(_var("discharge", microgrid_id, hour), 0.0)), 0.0)
            if charge > 1e-6 and discharge > 1e-6:
                charge_discharge_violations += 1
                charge_discharge_magnitude += min(charge, discharge)
            soc = float(solution.get(_var("soc", microgrid_id, hour), 0.0))
            if soc < -1e-6 or soc > microgrid.battery.capacity_kwh + 1e-6:
                storage_violations += 1
            critical_limit = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour] * microgrid.load_profile.critical_fraction
            noncritical_limit = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour] - critical_limit
            if float(solution.get(_var("shed_critical", microgrid_id, hour), 0.0)) > critical_limit + 1e-6:
                load_shed_violations += 1
            if float(solution.get(_var("shed_noncritical", microgrid_id, hour), 0.0)) > noncritical_limit + 1e-6:
                load_shed_violations += 1
            if (
                not scenario.generator_availability[mg_index][hour]
                and float(solution.get(_var("P_gen", microgrid_id, hour), 0.0)) > 1e-6
            ):
                generator_availability_violations += 1
            tie_available = scenario.tie_availability[mg_index][hour]
            forced_islanding = scenario.forced_islanding[mg_index][hour]
            pcc = abs(float(solution.get(_var("import_pcc", microgrid_id, hour), 0.0))) + abs(
                float(solution.get(_var("export_pcc", microgrid_id, hour), 0.0))
            )
            if (not tie_available or forced_islanding) and pcc > 1e-6:
                pcc_violations += 1

    residuals = compute_balance_residuals(solution, grid_case, patch, scenario)
    max_balance_residual = max((abs(value) for value in residuals.values()), default=0.0)
    balance_violations = sum(abs(value) > 1e-4 for value in residuals.values())
    total_count = (
        bounds_count
        + mode_violations
        + pcc_violations
        + charge_discharge_violations
        + storage_violations
        + load_shed_violations
        + generator_availability_violations
        + balance_violations
    )
    total_magnitude = bounds_magnitude + mode_magnitude + charge_discharge_magnitude + max_balance_residual
    return {
        "bounds_violations": int(bounds_count),
        "bounds_violation_magnitude": float(bounds_magnitude),
        "mode_simplex_violations": int(mode_violations),
        "mode_simplex_violation_magnitude": float(mode_magnitude),
        "pcc_availability_violations": int(pcc_violations),
        "charge_discharge_consistency_violations": int(charge_discharge_violations),
        "charge_discharge_violation_magnitude": float(charge_discharge_magnitude),
        "storage_soc_violations": int(storage_violations),
        "load_shedding_limit_violations": int(load_shed_violations),
        "generator_availability_violations": int(generator_availability_violations),
        "power_balance_violations": int(balance_violations),
        "max_power_balance_residual": float(max_balance_residual),
        "total_violation_count": int(total_count),
        "total_violation_magnitude": float(total_magnitude),
        "has_violation": bool(total_count > 0 or total_magnitude > 1e-6),
    }


def _solution_dict(order: list[str], vector: list[float]) -> dict[str, float]:
    return {name: float(vector[index]) for index, name in enumerate(order) if index < len(vector)}


def _evaluate_payload(payload: dict[str, Any], solution: dict[str, float]) -> float:
    total = 0.0
    for term in payload.get("polynomial_terms", []):
        value = float(term.get("coefficient", 0.0))
        for name, exponent in term.get("powers", {}).items():
            value *= float(solution.get(str(name), 0.0)) ** int(exponent)
        total += value
    return float(total)


def _payload_benchmark(payload: dict[str, Any], fallback: str) -> str:
    benchmark = payload.get("cmpo_v2", {}).get("source_benchmark") or payload.get("hybrid_model", {}).get("benchmark")
    if benchmark:
        return str(benchmark)
    source = str(payload.get("hybrid_model", {}).get("source_payload_path", ""))
    for candidate in BENCHMARK_CONFIGS:
        if candidate in source:
            return candidate
    return fallback


def _payload_grid_context(
    payload: dict[str, Any],
    fallback_config: dict[str, Any] | None,
    cache: dict[tuple[str, int], tuple[Any, str, float]],
    data_dir: Path,
) -> tuple[Any, str, float]:
    fallback_name = str((fallback_config or {}).get("name", "phase3_qci"))
    benchmark = _payload_benchmark(payload, fallback_name)
    horizon = int(payload.get("scenario_metadata", {}).get("horizon", 6))
    key = (benchmark, horizon)
    if key in cache:
        return cache[key]
    if benchmark in BENCHMARK_CONFIGS:
        context_config = load_phase3_config(BENCHMARK_CONFIGS[benchmark])
        dataset = benchmark
    elif fallback_config:
        context_config = copy.deepcopy(fallback_config)
        dataset = str(context_config.get("dataset", {}).get("name") or fallback_name)
    else:
        raise ValueError(f"No Phase 3 config can be inferred for payload benchmark {benchmark!r}")
    context_config.setdefault("dataset", {})["horizon_hours"] = horizon
    grid_case = build_grid_case_from_config(context_config, data_dir / benchmark / f"horizon_{horizon}")
    total_upgrade_cost = 0.0
    try:
        manifest = load_phase3_manifest(context_config)
        total_upgrade_cost = float(manifest.get("design_metrics", {}).get("total_upgrade_cost", 0.0))
    except Exception:
        pass
    cache[key] = (grid_case, dataset, total_upgrade_cost)
    return cache[key]


def _load_payload(payload_path: Path | None) -> dict[str, Any] | None:
    if payload_path is None or not payload_path.exists():
        return None
    return _read_json(payload_path)


def _scenario_patch_from_payload(payload: dict[str, Any], request: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    scenario = str(
        payload.get("scenario_metadata", {}).get("scenario")
        or request.get("qci_file", {}).get("cmpo_metadata", {}).get("scenario_metadata", {}).get("scenario")
    )
    patch_ids = (
        payload.get("patch_metadata", {}).get("patch_ids")
        or request.get("qci_file", {}).get("cmpo_metadata", {}).get("patch_metadata", {}).get("patch_ids")
        or []
    )
    patch = tuple(str(item) for item in patch_ids)
    patch_label = str(payload.get("patch_metadata", {}).get("patch") or "-".join(patch))
    return scenario, patch, patch_label


def _decode_success_rows(
    *,
    response_path: Path,
    request_path: Path | None,
    response: dict[str, Any],
    request: dict[str, Any],
    payload_path: Path | None,
    payload: dict[str, Any],
    grid_case,
    dataset: str,
    total_upgrade_cost: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scenario_name, patch, patch_label = _scenario_patch_from_payload(payload, request)
    scenario = next(candidate for candidate in grid_case.scenarios if candidate.name == scenario_name)
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=response_path.parent, write_export=False)
    order = _variable_order(request, payload)
    if not order:
        raise ValueError(f"no variable order available for {response_path}")

    energies = _energies(response)
    solutions = _solutions(response)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    if not solutions:
        failures.append(
            {
                "response_json": str(response_path),
                "request_json": "" if request_path is None else str(request_path),
                "payload": "" if payload_path is None else str(payload_path),
                "job_id": _job_id(response),
                "status": _status(response),
                "repeat": _parse_repeat(response_path),
                "failure_reason": "QCi response completed without solutions.",
            }
        )
        return rows, failures

    for sample_index, vector in enumerate(solutions):
        raw_solution = _solution_dict(order, vector)
        repaired_solution, repair_report = repair_solution(raw_solution, model, grid_case, patch, scenario)
        pre = _violation_report(raw_solution, model, grid_case, patch, scenario)
        post = _violation_report(repaired_solution, model, grid_case, patch, scenario)
        result = _make_result(
            "CMPO + QCi Dirac-3",
            scenario,
            patch,
            model,
            grid_case,
            raw_solution,
            runtime_seconds=_runtime_from_response(response),
            repeats=1,
            notes=f"Decoded from QCi job {_job_id(response)} sample {sample_index}.",
        )
        row = result.to_dict()
        row.update(
            {
                "dataset": dataset,
                "backend": "qci_dirac3",
                "job_id": _job_id(response),
                "status": _status(response),
                "repeat": _parse_repeat(response_path),
                "sample_index": sample_index,
                "payload": "" if payload_path is None else str(payload_path),
                "payload_name": "" if payload_path is None else payload_path.name,
                "response_json": str(response_path),
                "request_json": "" if request_path is None else str(request_path),
                "qci_energy": energies[sample_index] if sample_index < len(energies) else math.nan,
                "decoded_objective": float(model.evaluate(raw_solution)),
                "repaired_objective": float(model.evaluate(repaired_solution)),
                "runtime": _runtime_from_response(response),
                "wall_clock_runtime_seconds": _runtime_from_response(response),
                "pre_repair_violation": bool(pre["has_violation"]),
                "post_repair_violation": bool(post["has_violation"]),
                "pre_repair_violation_count": pre["total_violation_count"],
                "post_repair_violation_count": post["total_violation_count"],
                "pre_repair_violation_magnitude": pre["total_violation_magnitude"],
                "post_repair_violation_magnitude": post["total_violation_magnitude"],
                "repair_feasibility_pass": bool(repair_report["feasibility_pass"]),
                "pre_repair_report": _safe_json(pre),
                "post_repair_report": _safe_json(post),
                "repair_report": _safe_json(repair_report),
                "raw_solution": _safe_json(raw_solution),
                "repaired_solution": _safe_json(repaired_solution),
            }
        )
        rows.append(row)
    rows = add_phase3_columns(rows, grid_case, dataset_name=dataset, total_upgrade_cost=total_upgrade_cost).to_dict("records")
    for row in rows:
        row["expected_operating_cost"] = row["expected_cost_component"]
        row["risk_adjusted_cost"] = row["expected_cost_component"] + 0.25 * max(row["critical_energy_not_served_kwh"], 0.0)
        row["feasibility_after_repair"] = row["feasibility_pass"]
        row["total_critical_infrastructure_unserved_hours_proxy"] = row["total_hours_critical_infrastructure_unserved"]
        row["time_to_good_solution"] = row["runtime_seconds"] if row["feasibility_pass"] else -1.0
    return rows, failures


def _decode_hybrid_rows(
    *,
    response_path: Path,
    request_path: Path | None,
    response: dict[str, Any],
    request: dict[str, Any],
    payload_path: Path,
    payload: dict[str, Any],
    dataset: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Preserve completed hybrid QCi mode vectors for classical projection."""

    order = _variable_order(request, payload)
    if not order:
        raise ValueError(f"no variable order available for {response_path}")
    energies = _energies(response)
    solutions = _solutions(response)
    if not solutions:
        return [], [
            {
                "response_json": str(response_path),
                "request_json": "" if request_path is None else str(request_path),
                "payload": str(payload_path),
                "job_id": _job_id(response),
                "status": _status(response),
                "repeat": _parse_repeat(response_path),
                "failure_reason": "QCi response completed without solutions.",
            }
        ]
    scenario, _patch_ids, patch_label = _scenario_patch_from_payload(payload, request)
    runtime = _runtime_from_response(response)
    rows: list[dict[str, Any]] = []
    for sample_index, vector in enumerate(solutions):
        raw_solution = _solution_dict(order, vector)
        rows.append(
            {
                "method_name": "CMPO Hybrid QCi Mode Selection",
                "dataset": dataset,
                "backend": "qci_dirac3_hybrid_mode_selection",
                "scenario": scenario,
                "patch": patch_label,
                "job_id": _job_id(response),
                "status": _status(response),
                "repeat": _parse_repeat(response_path),
                "sample_index": sample_index,
                "payload": str(payload_path),
                "payload_name": payload_path.name,
                "payload_schema": str(payload.get("schema", "")),
                "response_json": str(response_path),
                "request_json": "" if request_path is None else str(request_path),
                "qci_energy": energies[sample_index] if sample_index < len(energies) else math.nan,
                "decoded_objective": _evaluate_payload(payload, raw_solution),
                "runtime": runtime,
                "runtime_seconds": runtime,
                "wall_clock_runtime_seconds": runtime,
                "projection_required": True,
                "decoded_variables": _safe_json(raw_solution),
                "raw_solution": _safe_json(raw_solution),
            }
        )
    return rows, []


def _summarize_hybrid_payloads(repeat_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in repeat_metrics.groupby(["dataset", "payload_name", "scenario", "patch"], sort=True, dropna=False):
        dataset, payload_name, scenario, patch = keys
        energies = pd.to_numeric(group["qci_energy"], errors="coerce")
        runtimes = pd.to_numeric(group["runtime_seconds"], errors="coerce")
        rows.append(
            {
                "dataset": dataset,
                "payload_name": payload_name,
                "scenario": scenario,
                "patch": patch,
                "sample_count": int(len(group)),
                "repeat_count": int(group["repeat"].nunique()),
                "job_count": int(group["job_id"].nunique()),
                "qci_energy_best": float(energies.min()),
                "qci_energy_median": float(energies.median()),
                "decoded_objective_best": float(pd.to_numeric(group["decoded_objective"], errors="coerce").min()),
                "runtime_seconds_total": float(runtimes.sum()),
                "runtime_seconds_median": float(runtimes.median()),
                "projection_status": "pending_classical_projection",
            }
        )
    return pd.DataFrame(rows)


def _summarize_payloads(repeat_metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarize QCi repeat distributions by payload without reweighting repeats."""

    if repeat_metrics.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    group_columns = ["dataset", "payload_name", "scenario", "patch"]
    for keys, group in repeat_metrics.groupby(group_columns, sort=True, dropna=False):
        dataset, payload_name, scenario, patch = keys
        feasible = group[group["feasibility_after_repair"].astype(bool)]
        cost = group["expected_operating_cost"]
        qci_energy = group["qci_energy"].dropna()
        rows.append(
            {
                "dataset": dataset,
                "payload_name": payload_name,
                "scenario": scenario,
                "patch": patch,
                "sample_count": int(len(group)),
                "repeat_count": int(group["repeat"].nunique()),
                "job_count": int(group["job_id"].nunique()),
                "expected_operating_cost_best": float(cost.min()),
                "expected_operating_cost_median": float(cost.median()),
                "risk_adjusted_cost_best": float(group["risk_adjusted_cost"].min()),
                "risk_adjusted_cost_median": float(group["risk_adjusted_cost"].median()),
                "critical_load_served_fraction_best": float(group["critical_load_served_fraction"].max()),
                "critical_load_served_fraction_median": float(group["critical_load_served_fraction"].median()),
                "critical_energy_not_served_best": float(group["critical_energy_not_served_kwh"].min()),
                "total_energy_not_served_best": float(group["energy_not_served_kwh"].min()),
                "max_fraction_customers_unserved_per_hour_best": float(
                    group["max_fraction_customers_unserved_per_hour"].min()
                ),
                "total_critical_infrastructure_unserved_hours_proxy_best": float(
                    group["total_critical_infrastructure_unserved_hours_proxy"].min()
                ),
                "feasibility_after_repair_rate": float(group["feasibility_after_repair"].mean()),
                "pre_repair_violation_rate": float(group["pre_repair_violation"].mean()),
                "post_repair_violation_rate": float(group["post_repair_violation"].mean()),
                "pre_repair_violation_median": float(group["pre_repair_violation_magnitude"].median()),
                "post_repair_violation_median": float(group["post_repair_violation_magnitude"].median()),
                "qci_energy_best": float(qci_energy.min()) if not qci_energy.empty else math.nan,
                "qci_energy_median": float(qci_energy.median()) if not qci_energy.empty else math.nan,
                "decoded_objective_best": float(group["decoded_objective"].min()),
                "runtime_seconds_total": float(group["runtime_seconds"].sum()),
                "runtime_seconds_median": float(group["runtime_seconds"].median()),
                "time_to_good_solution": float(feasible["runtime_seconds"].min()) if not feasible.empty else -1.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "payload_name"]).reset_index(drop=True)


def _failure_row(response_path: Path, request_path: Path | None, response: dict[str, Any], payload_path: Path | None) -> dict[str, Any]:
    reason = response.get("failure_reason") or response.get("message") or response.get("error") or "QCi job did not complete."
    return {
        "response_json": str(response_path),
        "request_json": "" if request_path is None else str(request_path),
        "payload": "" if payload_path is None else str(payload_path),
        "job_id": _job_id(response),
        "status": _status(response),
        "repeat": _parse_repeat(response_path),
        "failure_reason": reason,
    }


def decode_qci_experiment(
    *,
    experiment_dir: Path | str,
    config: dict[str, Any] | None,
    input_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    payload_manifest: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, str | int | bool]:
    """Decode all QCi response JSON files for one Phase 3 experiment."""

    exp_dir = Path(experiment_dir)
    source_dir = Path(input_dir) if input_dir is not None else exp_dir
    decoded_dir = Path(output_dir) if output_dir is not None else exp_dir / "decoded"
    response_files = _discover_response_files(source_dir)
    plan = {
        "experiment_dir": str(exp_dir),
        "input_dir": str(source_dir),
        "response_files": len(response_files),
        "output_dir": str(decoded_dir),
        "dry_run": dry_run,
    }
    if dry_run:
        return plan
    manifest: dict[str, Any] = {}
    if config:
        try:
            manifest = load_phase3_manifest(config)
        except Exception:
            pass
    manifest_paths = _payload_manifest_paths(exp_dir, None if payload_manifest is None else Path(payload_manifest))
    for payload in manifest.get("payloads", []):
        path = Path(payload)
        manifest_paths.setdefault(path.name, path)

    decoded_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    grid_cache: dict[tuple[str, int], tuple[Any, str, float]] = {}
    for response_path in response_files:
        request_path = _request_for_response(response_path)
        request = _read_json(request_path) if request_path is not None else {}
        response = _read_json(response_path)
        payload_path = _payload_path_from_context(request, response, response_path, manifest_paths)
        payload = _load_payload(payload_path)
        status = _status(response).upper()
        if status not in {"COMPLETED", "COMPLETE"}:
            failure_rows.append(_failure_row(response_path, request_path, response, payload_path))
            continue
        if payload is None:
            failure_rows.append(_failure_row(response_path, request_path, response | {"failure_reason": "payload JSON not found"}, payload_path))
            continue
        try:
            _grid_case, dataset, total_upgrade_cost = _payload_grid_context(
                payload,
                config,
                grid_cache,
                decoded_dir / "data",
            )
            if str(payload.get("schema", "")).startswith("cmpo.hybrid_qci_mode_payload"):
                rows, failures = _decode_hybrid_rows(
                    response_path=response_path,
                    request_path=request_path,
                    response=response,
                    request=request,
                    payload_path=payload_path,
                    payload=payload,
                    dataset=dataset,
                )
            else:
                rows, failures = _decode_success_rows(
                    response_path=response_path,
                    request_path=request_path,
                    response=response,
                    request=request,
                    payload_path=payload_path,
                    payload=payload,
                    grid_case=_grid_case,
                    dataset=dataset,
                    total_upgrade_cost=total_upgrade_cost,
                )
            decoded_rows.extend(rows)
            failure_rows.extend(failures)
        except Exception as exc:  # noqa: BLE001 - keep failed decodes in the report.
            failure_rows.append(_failure_row(response_path, request_path, response | {"failure_reason": str(exc)}, payload_path))

    repeat_metrics = pd.DataFrame(decoded_rows)
    failure_report = pd.DataFrame(failure_rows, columns=FAILURE_COLUMNS)
    if repeat_metrics.empty:
        repeat_metrics = pd.DataFrame(columns=REPEAT_METRIC_COLUMNS)
        payload_summary = pd.DataFrame(columns=PAYLOAD_SUMMARY_COLUMNS)
        best_solutions = pd.DataFrame(columns=BEST_SOLUTION_COLUMNS)
    elif repeat_metrics.get("projection_required", pd.Series(False, index=repeat_metrics.index)).fillna(False).astype(bool).all():
        payload_summary = _summarize_hybrid_payloads(repeat_metrics)
        best_solutions = (
            repeat_metrics.sort_values(["payload_name", "qci_energy"], ascending=[True, True])
            .groupby("payload_name", as_index=False)
            .head(1)
            .reset_index(drop=True)
        )
    else:
        payload_summary = _summarize_payloads(repeat_metrics)
        best_index = (
            repeat_metrics.assign(_feasible=repeat_metrics["feasibility_pass"].astype(bool))
            .sort_values(["payload_name", "_feasible", "expected_cost_component"], ascending=[True, False, True])
            .groupby("payload_name", as_index=False)
            .head(1)
            .drop(columns=["_feasible"])
        )
        best_solutions = best_index[[column for column in BEST_SOLUTION_COLUMNS if column in best_index.columns]]

    paths = {
        "qci_repeat_metrics_csv": decoded_dir / "qci_repeat_metrics.csv",
        "qci_payload_summary_csv": decoded_dir / "qci_payload_summary.csv",
        "qci_best_solutions_csv": decoded_dir / "qci_best_solutions.csv",
        "qci_failure_report_csv": decoded_dir / "qci_failure_report.csv",
    }
    _write_csv(repeat_metrics, paths["qci_repeat_metrics_csv"])
    _write_csv(payload_summary, paths["qci_payload_summary_csv"])
    _write_csv(best_solutions, paths["qci_best_solutions_csv"])
    _write_csv(failure_report, paths["qci_failure_report_csv"])
    return {key: str(value) for key, value in paths.items()} | {
        "decoded_rows": len(repeat_metrics),
        "failed_rows": len(failure_report),
    }


def decode_qci_results(config: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    """Compatibility wrapper that decodes the configured Phase 3 output directory."""

    return decode_qci_experiment(experiment_dir=phase3_output_dir(config), config=config, dry_run=dry_run)


def read_decoded_qci_results(config: dict[str, Any]) -> pd.DataFrame:
    """Read decoded QCi repeat metrics if available."""

    out_dir = phase3_output_dir(config)
    for path in [out_dir / "decoded" / "qci_repeat_metrics.csv", out_dir / "qci_decoded" / "qci_decoded_results.csv"]:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()
