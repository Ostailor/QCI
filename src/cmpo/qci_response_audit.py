"""Forensic audit helpers for preserved QCi request and response artifacts."""

from __future__ import annotations

import json
import math
import csv
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


INTEGER_PROBLEM = "qudit_hamiltonian_optimization"
CONTINUOUS_PROBLEM = "normalized_qudit_hamiltonian_optimization"
INTEGER_DEVICE = "dirac-3_qudit"
CONTINUOUS_DEVICE = "dirac-3_normalized_qudit"
INTEGER_PROBLEM_MARKERS = frozenset(
    {
        INTEGER_PROBLEM,
        "qudit_hamiltonian_optimization_results",
        "normalized_qudit_hamiltonian_optimization_integer",
        "normalized_qudit_hamiltonian_optimization_integer_results",
    }
)
CONTINUOUS_PROBLEM_MARKERS = frozenset(
    {
        CONTINUOUS_PROBLEM,
        "normalized_qudit_hamiltonian_optimization_continuous",
        "normalized_qudit_hamiltonian_optimization_results",
        "normalized_qudit_hamiltonian_optimization_continuous_results",
    }
)


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _walk(item)


def _values_for_key(value: Any, key: str) -> list[Any]:
    return [item for candidate, item in _walk(value) if candidate == key]


def _contains_key(value: Any, key: str) -> bool:
    return any(candidate == key for candidate, _ in _walk(value))


def _first_scalar(value: Any, key: str) -> Any:
    for item in _values_for_key(value, key):
        if not isinstance(item, (Mapping, list, tuple)):
            return item
    return None


def classify_response_mode(response: Mapping[str, Any]) -> str:
    """Classify the native problem/device mode disclosed by a QCi response."""

    has_integer = any(_contains_key(response, marker) for marker in INTEGER_PROBLEM_MARKERS) or _contains_key(
        response, INTEGER_DEVICE
    )
    has_continuous = any(
        _contains_key(response, marker) for marker in CONTINUOUS_PROBLEM_MARKERS
    ) or _contains_key(response, CONTINUOUS_DEVICE)
    if has_integer and has_continuous:
        return "unknown"
    if has_continuous:
        return "normalized_continuous_qudit"
    if has_integer:
        return "integer_qudit"
    return "unknown"


def coefficient_dynamic_range(qci_file_or_request: Mapping[str, Any]) -> dict[str, float | int | None]:
    """Return the nonzero coefficient extrema for the submitted polynomial."""

    coefficients: list[float] = []
    for key, item in _walk(qci_file_or_request):
        if key != "data" or not isinstance(item, list):
            continue
        for entry in item:
            if not isinstance(entry, Mapping) or "idx" not in entry or "val" not in entry:
                continue
            try:
                coefficient = abs(float(entry["val"]))
            except (TypeError, ValueError):
                continue
            if coefficient > 0.0 and math.isfinite(coefficient):
                coefficients.append(coefficient)
    if not coefficients:
        return {
            "nonzero_coefficient_count": 0,
            "maximum_nonzero_coefficient": None,
            "minimum_nonzero_coefficient": None,
            "coefficient_dynamic_range": None,
        }
    maximum = max(coefficients)
    minimum = min(coefficients)
    return {
        "nonzero_coefficient_count": len(coefficients),
        "maximum_nonzero_coefficient": maximum,
        "minimum_nonzero_coefficient": minimum,
        "coefficient_dynamic_range": maximum / minimum,
    }


def _raw_solutions(response: Mapping[str, Any]) -> list[list[Any]]:
    results = response.get("results")
    if not isinstance(results, Mapping):
        return []
    samples = results.get("solutions", results.get("samples", []))
    if not isinstance(samples, list):
        return []
    return [list(sample) for sample in samples if isinstance(sample, (list, tuple))]


def _integer_coordinate(value: Any, tolerance: float = 1.0e-9) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and abs(number - round(number)) <= tolerance


def _num_levels(response: Mapping[str, Any], request: Mapping[str, Any], width: int) -> list[int]:
    candidates = _values_for_key(response, "num_levels") + _values_for_key(request, "num_levels")
    for candidate in candidates:
        if isinstance(candidate, (list, tuple)):
            try:
                levels = [int(value) for value in candidate]
            except (TypeError, ValueError):
                continue
        else:
            try:
                levels = [int(candidate)]
            except (TypeError, ValueError):
                continue
        if len(levels) == 1 and width > 1:
            levels *= width
        if width == 0 or len(levels) == width:
            return levels
    return []


def _request_for_response(response_path: Path) -> tuple[Path | None, dict[str, Any]]:
    candidates = [
        response_path.with_name("request.json"),
        response_path.with_name(response_path.name.replace("response", "request")),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            return path, json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return path, {}
    return None, {}


def audit_response_file(response_path: Path | str) -> dict[str, Any]:
    """Audit one preserved response without rounding, projecting, or modifying it."""

    path = Path(response_path)
    response = json.loads(path.read_text(encoding="utf-8"))
    request_path, request = _request_for_response(path)
    samples = _raw_solutions(response)
    width = max((len(sample) for sample in samples), default=0)
    levels = _num_levels(response, request, width)
    upper_bounds = [level - 1 for level in levels]

    integral_flags = [all(_integer_coordinate(value) for value in sample) for sample in samples]
    in_domain_flags: list[bool] = []
    for sample, integral in zip(samples, integral_flags, strict=True):
        in_domain_flags.append(
            bool(integral)
            and bool(upper_bounds)
            and len(sample) == len(upper_bounds)
            and all(0 <= int(round(float(value))) <= upper for value, upper in zip(sample, upper_bounds, strict=True))
        )
    raw_coordinates = [value for sample in samples for value in sample]
    coordinates = [
        float(value)
        for value in raw_coordinates
        if not isinstance(value, bool) and isinstance(value, (int, float))
    ]
    integral_coordinate_count = sum(_integer_coordinate(value) for value in raw_coordinates)
    in_bounds_coordinate_count = 0
    if upper_bounds:
        for sample in samples:
            if len(sample) != len(upper_bounds):
                continue
            in_bounds_coordinate_count += sum(
                _integer_coordinate(value) and 0 <= int(round(float(value))) <= upper
                for value, upper in zip(sample, upper_bounds, strict=True)
            )
    submission = response.get("job_info", {}).get("job_submission", response.get("job_submission", {}))
    mode = classify_response_mode(response)
    request_mode = classify_response_mode(request)
    job_type = _first_scalar(request, "job_type") or _first_scalar(submission, "job_type") or ""
    job_type_source = "declared_in_artifact" if job_type else "unavailable"
    if not job_type and mode == "normalized_continuous_qudit":
        job_type = "sample-hamiltonian"
        job_type_source = "inferred_from_normalized_problem_config"
    elif not job_type and mode == "integer_qudit":
        job_type = "sample-hamiltonian-integer"
        job_type_source = "inferred_from_integer_problem_config"
    sum_constraint = _first_scalar(response, "sum_constraint")
    response_sum_constraint = sum_constraint
    request_sum_constraint = _first_scalar(request, "sum_constraint")
    if sum_constraint is None:
        sum_constraint = request_sum_constraint
    stats = coefficient_dynamic_range(request)
    native_integral = sum(integral_flags)
    native_in_domain = sum(in_domain_flags)
    native_feasible = native_in_domain if mode == "integer_qudit" else 0
    problem_configs = [
        key
        for key in sorted(INTEGER_PROBLEM_MARKERS | CONTINUOUS_PROBLEM_MARKERS)
        if _contains_key(response, key)
    ]
    device_configs = [key for key in (INTEGER_DEVICE, CONTINUOUS_DEVICE) if _contains_key(response, key)]
    job_id = (
        response.get("job_id")
        or response.get("job_info", {}).get("job_id")
        or response.get("job_info", {}).get("job_submission_id")
        or ""
    )
    return {
        "response_path": str(path),
        "request_path": str(request_path or ""),
        "job_id": str(job_id),
        "status": str(response.get("status", response.get("job_status", "UNKNOWN"))),
        "request_mode": request_mode,
        "response_mode": mode,
        "effective_mode": mode if mode != "unknown" else request_mode,
        "problem_config": ";".join(problem_configs),
        "device_config": ";".join(device_configs),
        "job_type": str(job_type),
        "job_type_source": job_type_source,
        "sum_constraint": sum_constraint,
        "request_sum_constraint": request_sum_constraint,
        "response_sum_constraint": response_sum_constraint,
        "num_levels": json.dumps(levels),
        "declared_upper_bounds": json.dumps(upper_bounds),
        "raw_sample_count": len(samples),
        "native_integral_sample_count": native_integral,
        "native_in_domain_sample_count": native_in_domain,
        "native_feasible_sample_count": native_feasible,
        "raw_coordinate_count": len(raw_coordinates),
        "integral_coordinate_count": integral_coordinate_count,
        "fractional_or_invalid_coordinate_count": len(raw_coordinates) - integral_coordinate_count,
        "in_bounds_coordinate_count": in_bounds_coordinate_count,
        "bounds_check_available": bool(upper_bounds),
        "all_raw_coordinates_integral": bool(samples) and native_integral == len(samples),
        "all_raw_coordinates_in_bounds": bool(samples) and native_in_domain == len(samples),
        "solution_minimum": min(coordinates) if coordinates else None,
        "solution_maximum": max(coordinates) if coordinates else None,
        "projected_sample_counted_native": False,
        **stats,
    }


def response_candidates(root: Path | str) -> list[Path]:
    """Find response artifacts using names and QCi response schema markers."""

    candidates: list[Path] = []
    for path in Path(root).rglob("*.json"):
        lower = path.name.lower()
        if "response" not in lower and lower not in {"result.json", "results.json"}:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, Mapping):
            continue
        if lower == "response.json" or (
            any(_contains_key(payload, marker) for marker in INTEGER_PROBLEM_MARKERS)
            or any(_contains_key(payload, marker) for marker in CONTINUOUS_PROBLEM_MARKERS)
            or _contains_key(payload, INTEGER_DEVICE)
            or _contains_key(payload, CONTINUOUS_DEVICE)
            or ("job_info" in payload and "results" in payload)
        ):
            candidates.append(path)
    return sorted(set(candidates))


def audit_tree(root: Path | str) -> list[dict[str, Any]]:
    """Audit every discoverable QCi response under ``root``."""

    return [audit_response_file(path) for path in response_candidates(root)]


def request_candidates(root: Path | str) -> list[Path]:
    """Find persisted QCi request records."""

    return sorted(path for path in Path(root).rglob("request.json") if path.is_file())


def audit_request_file(request_path: Path | str) -> dict[str, Any]:
    """Audit one submission request and its response, when one exists."""

    path = Path(request_path)
    request = json.loads(path.read_text(encoding="utf-8"))
    response_path = path.with_name("response.json")
    response_row: dict[str, Any] = {}
    if response_path.exists():
        try:
            response_row = audit_response_file(response_path)
        except (OSError, json.JSONDecodeError):
            response_row = {}
    request_mode = classify_response_mode(request)
    response_mode = str(response_row.get("response_mode", "unknown"))
    effective_mode = response_mode if response_mode != "unknown" else request_mode
    problem_configs = [
        key
        for key in sorted(INTEGER_PROBLEM_MARKERS | CONTINUOUS_PROBLEM_MARKERS)
        if _contains_key(request, key)
    ]
    device_configs = [
        key for key in (INTEGER_DEVICE, CONTINUOUS_DEVICE) if _contains_key(request, key)
    ]
    job_type = _first_scalar(request, "job_type") or ""
    job_type_source = "declared_in_artifact" if job_type else "unavailable"
    if not job_type and request_mode == "normalized_continuous_qudit":
        job_type = "sample-hamiltonian"
        job_type_source = "inferred_from_normalized_problem_config"
    elif not job_type and request_mode == "integer_qudit":
        job_type = "sample-hamiltonian-integer"
        job_type_source = "inferred_from_integer_problem_config"
    levels = _num_levels({}, request, 0)
    stats = coefficient_dynamic_range(request)
    row = {
        "response_path": str(response_path) if response_path.exists() else "",
        "request_path": str(path),
        "job_id": str(_first_scalar(request, "job_id") or ""),
        "status": str(_first_scalar(request, "status") or "NO_RESPONSE"),
        "request_mode": request_mode,
        "response_mode": response_mode,
        "effective_mode": effective_mode,
        "problem_config": ";".join(problem_configs),
        "device_config": ";".join(device_configs),
        "job_type": str(job_type),
        "job_type_source": job_type_source,
        "sum_constraint": _first_scalar(request, "sum_constraint"),
        "request_sum_constraint": _first_scalar(request, "sum_constraint"),
        "response_sum_constraint": response_row.get("response_sum_constraint"),
        "num_levels": json.dumps(levels),
        "declared_upper_bounds": json.dumps([level - 1 for level in levels]),
        "raw_sample_count": 0,
        "native_integral_sample_count": 0,
        "native_in_domain_sample_count": 0,
        "native_feasible_sample_count": 0,
        "raw_coordinate_count": 0,
        "integral_coordinate_count": 0,
        "fractional_or_invalid_coordinate_count": 0,
        "in_bounds_coordinate_count": 0,
        "bounds_check_available": False,
        "all_raw_coordinates_integral": False,
        "all_raw_coordinates_in_bounds": False,
        "solution_minimum": None,
        "solution_maximum": None,
        "projected_sample_counted_native": False,
        **stats,
    }
    if response_row:
        for key in (
            "job_id",
            "status",
            "sum_constraint",
            "num_levels",
            "declared_upper_bounds",
            "raw_sample_count",
            "native_integral_sample_count",
            "native_in_domain_sample_count",
            "native_feasible_sample_count",
            "raw_coordinate_count",
            "integral_coordinate_count",
            "fractional_or_invalid_coordinate_count",
            "in_bounds_coordinate_count",
            "bounds_check_available",
            "all_raw_coordinates_integral",
            "all_raw_coordinates_in_bounds",
            "solution_minimum",
            "solution_maximum",
        ):
            row[key] = response_row.get(key, row[key])
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_root_cause_artifacts(results_root: Path | str, output_dir: Path | str) -> dict[str, Any]:
    """Regenerate the integer-encoding root-cause bundle from raw artifacts."""

    root = Path(results_root)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = audit_tree(root)
    mode_counts = Counter(str(row["response_mode"]) for row in rows)
    request_rows = [audit_request_file(path) for path in request_candidates(root)]
    request_mode_counts = Counter(str(row["request_mode"]) for row in request_rows)
    paired_response_paths = {
        str(Path(row["response_path"])) for row in request_rows if row.get("response_path")
    }
    response_only_rows = [row for row in rows if str(Path(row["response_path"])) not in paired_response_paths]
    job_rows = request_rows + [
        dict(row, request_mode="unknown", effective_mode=row["response_mode"])
        for row in response_only_rows
    ]
    job_mode_counts = Counter(str(row["effective_mode"]) for row in job_rows)
    common_fields = [
        "response_path",
        "request_path",
        "job_id",
        "status",
        "request_mode",
        "response_mode",
        "effective_mode",
        "problem_config",
        "device_config",
        "job_type",
        "job_type_source",
        "sum_constraint",
        "request_sum_constraint",
        "response_sum_constraint",
        "num_levels",
        "declared_upper_bounds",
        "raw_sample_count",
        "native_integral_sample_count",
        "native_in_domain_sample_count",
        "native_feasible_sample_count",
        "raw_coordinate_count",
        "integral_coordinate_count",
        "fractional_or_invalid_coordinate_count",
        "in_bounds_coordinate_count",
        "bounds_check_available",
        "all_raw_coordinates_integral",
        "all_raw_coordinates_in_bounds",
        "solution_minimum",
        "solution_maximum",
        "projected_sample_counted_native",
        "nonzero_coefficient_count",
        "maximum_nonzero_coefficient",
        "minimum_nonzero_coefficient",
        "coefficient_dynamic_range",
    ]
    _write_csv(output / "response_mode_audit.csv", rows, common_fields)
    affected = [
        row for row in job_rows if row["effective_mode"] == "normalized_continuous_qudit"
    ]
    _write_csv(output / "affected_qci_runs.csv", affected, common_fields)
    coefficient_fields = [
        "response_path",
        "request_path",
        "job_id",
        "response_mode",
        "nonzero_coefficient_count",
        "maximum_nonzero_coefficient",
        "minimum_nonzero_coefficient",
        "coefficient_dynamic_range",
    ]
    _write_csv(output / "coefficient_dynamic_range_audit.csv", job_rows, coefficient_fields)

    continuous_raw = sum(int(row["raw_sample_count"]) for row in affected)
    continuous_integral = sum(int(row["native_integral_sample_count"]) for row in affected)
    budget_v2_rows = [
        row
        for row in affected
        if "sc_cmpo/budget_master_v2/qci" in str(row.get("request_path") or row.get("response_path"))
    ]
    budget_v2_samples = sum(int(row["raw_sample_count"]) for row in budget_v2_rows)
    budget_v2_integral_samples = sum(int(row["native_integral_sample_count"]) for row in budget_v2_rows)
    budget_v2_coordinates = sum(int(row["raw_coordinate_count"]) for row in budget_v2_rows)
    budget_v2_fractional = sum(
        int(row["fractional_or_invalid_coordinate_count"]) for row in budget_v2_rows
    )
    coefficient_rows = [
        row
        for row in job_rows
        if row.get("minimum_nonzero_coefficient") is not None
        and row.get("maximum_nonzero_coefficient") is not None
    ]
    minimum_submitted = min(
        (float(row["minimum_nonzero_coefficient"]) for row in coefficient_rows),
        default=math.nan,
    )
    maximum_submitted = max(
        (float(row["maximum_nonzero_coefficient"]) for row in coefficient_rows),
        default=math.nan,
    )
    maximum_ratio = max(
        (float(row["coefficient_dynamic_range"]) for row in coefficient_rows),
        default=math.nan,
    )
    collapsed_rows = sum(
        float(row["minimum_nonzero_coefficient"]) <= 1.0e-13 for row in coefficient_rows
    )
    request_sum_constraint_count = sum(
        row.get("request_sum_constraint") is not None for row in request_rows
    )
    response_sum_constraint_count = sum(
        row.get("response_sum_constraint") is not None for row in rows
    )
    integer_rows = [row for row in rows if row["response_mode"] == "integer_qudit"]
    unknown_rows = [row for row in rows if row["response_mode"] == "unknown"]
    report = f"""# QCi integer-encoding root-cause report

This bundle is generated from preserved QCi request and response JSON. It does not modify, relabel, or replace historical results. All affected results remain available as a **continuous-solver misconfiguration ablation** and must not be presented as native integer IRC-CMPO evidence.

## Finding

The historical adapter submitted `sample-hamiltonian`, which selected QCi's `normalized_qudit_hamiltonian_optimization` problem with the `dirac-3_normalized_qudit` device. That workflow carried a `sum_constraint` and returned continuous coordinates. It did not exercise `qudit_hamiltonian_optimization` / `dirac-3_qudit` with declared `num_levels`.

Source evidence: `src/cmpo/qci_client_adapter.py` hard-coded `job_type="sample-hamiltonian"`. The installed historical transport version was `qci-client==5.0.0`, whose generated job bodies disclose the normalized problem/device pair.

The qci-client job body persisted in these artifacts does not retain a literal `job_type` field. Where absent, `job_type` in the CSV is explicitly marked as inferred from the disclosed normalized or integer problem config; the pinned legacy adapter source supplies the independent hard-coded `sample-hamiltonian` evidence.

Response-mode counts derived from `response_mode_audit.csv`:

- normalized continuous qudit jobs: {mode_counts['normalized_continuous_qudit']}
- integer qudit jobs: {mode_counts['integer_qudit']}
- unknown-mode response artifacts: {mode_counts['unknown']}
- raw samples in normalized continuous responses: {continuous_raw}
- integral raw samples in normalized continuous responses: {continuous_integral}

Submission-mode counts derived from preserved requests plus response-only artifacts:

- normalized continuous qudit jobs submitted: {job_mode_counts['normalized_continuous_qudit']}
- integer qudit jobs submitted: {job_mode_counts['integer_qudit']}
- unknown-mode jobs: {job_mode_counts['unknown']}

Request-only evidence is retained: {sum(not bool(row.get('response_path')) for row in request_rows)} requests have no sibling response. Request configurations alone classify {request_mode_counts['normalized_continuous_qudit']} normalized-continuous, {request_mode_counts['integer_qudit']} integer, and {request_mode_counts['unknown']} unknown.

The Budget Master V2 subset contains {len(budget_v2_rows)} jobs, {budget_v2_samples} raw samples, and {budget_v2_coordinates} raw coordinates. Natively integral samples: {budget_v2_integral_samples}/{budget_v2_samples}. Fractional or invalid coordinates: {budget_v2_fractional}/{budget_v2_coordinates}. These projected portfolios are ablation inputs only, not native integer solutions.

No preserved request explicitly supplied `sum_constraint` ({request_sum_constraint_count} requests); the server-reported normalized responses supplied it in {response_sum_constraint_count} responses, with the historical effective value 10000. No response disclosed integer `num_levels`.

Across submitted polynomials the smallest observed nonzero magnitude is {minimum_submitted:.6g}, the largest is {maximum_submitted:.6g}, and the largest within-job max/min ratio is {maximum_ratio:.6g}. {collapsed_rows} submitted jobs contain a nonzero coefficient at or below 1e-13. These are measured artifact values, not reconstructed coefficients.

The integer count is based only on responses disclosing `qudit_hamiltonian_optimization` or `dirac-3_qudit`. Unknown responses are never assumed integer.

## Consequences

1. Projected or rounded portfolios are post-processing products and are never counted as natively feasible QCi samples.
2. Continuous responses containing `normalized_qudit_hamiltonian_optimization`, `dirac-3_normalized_qudit`, or `sum_constraint` are rejected for integer experiments.
3. The former hard-budget squared penalty compressed other coefficient families; the exact submitted extrema and ratios are recorded in `coefficient_dynamic_range_audit.csv`.
4. The former technology-weighted `log1p(capacity)` benefit is a heuristic. IRC-CMPO gates hardware use on a degree-at-most-three surrogate fitted to common-recourse outcomes.

## Artifact contract

- `response_mode_audit.csv` contains every discoverable QCi response and the inspected problem/device mode, job type, constraint/domain declarations, native integrality, bounds, and solution extrema.
- `affected_qci_runs.csv` is the exact normalized-continuous subset.
- `coefficient_dynamic_range_audit.csv` traces coefficient extrema to each sibling raw request when present.

Integer-mode rows: {len(integer_rows)}. Unknown-mode rows: {len(unknown_rows)}. No historical artifact was overwritten.
"""
    (output / "root_cause_report.md").write_text(report, encoding="utf-8")
    return {
        "historical_continuous_mode_qci_job_count": job_mode_counts["normalized_continuous_qudit"],
        "historical_integer_mode_qci_job_count": job_mode_counts["integer_qudit"],
        "historical_unknown_mode_job_count": job_mode_counts["unknown"],
        "historical_unknown_mode_response_count": mode_counts["unknown"],
        "historical_continuous_raw_sample_count": continuous_raw,
        "historical_continuous_integral_raw_sample_count": continuous_integral,
        "response_count": len(rows),
    }
