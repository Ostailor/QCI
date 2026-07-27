"""Strict QCi Dirac-3 integer transport and native-sample validation.

This module is intentionally separate from the historical continuous adapter.  It
never applies rounding or a hard-feasibility projection: a sample is usable only
when the hardware response is the integer qudit mode and every raw coordinate is
already integral and inside its declared domain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Mapping, Sequence

from cmpo.qci_client_adapter import convert_cmpo_payload_to_qci_file

INTEGER_JOB_TYPE = "sample-hamiltonian-integer"
INTEGER_PROBLEM_TYPE = "qudit_hamiltonian_optimization"
INTEGER_DEVICE_TYPE = "dirac-3_qudit"
FORBIDDEN_INTEGER_RESPONSE_KEYS = (
    "normalized_qudit_hamiltonian_optimization",
    "dirac-3_normalized_qudit",
    "sum_constraint",
)


@dataclass(frozen=True)
class IntegerResponseValidation:
    """Audit result for an integer QCi response."""

    valid: bool
    errors: tuple[str, ...]
    problem_type: str
    device_type: str
    declared_num_levels: tuple[int, ...]
    native_sample_count: int
    native_integer_in_domain_count: int
    projected_sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "problem_type": self.problem_type,
            "device_type": self.device_type,
            "declared_num_levels": list(self.declared_num_levels),
            "native_sample_count": self.native_sample_count,
            "native_integer_in_domain_count": self.native_integer_in_domain_count,
            "projected_sample_count": self.projected_sample_count,
            "projection_used": False,
        }


def installed_qci_versions() -> dict[str, str]:
    """Return exact installed transport package versions without importing them."""

    versions: dict[str, str] = {}
    for distribution in ("qci-client", "eqc-models"):
        try:
            versions[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[distribution] = "not-installed"
    return versions


def _integer_upper_bound(variable: Mapping[str, Any]) -> int:
    name = str(variable.get("name", "<unnamed>"))
    encoding = variable.get("encoding_type", variable.get("variable_type", variable.get("type")))
    if str(encoding).lower() not in {"binary", "integer", "int"}:
        raise ValueError(f"variable {name!r} must declare an integer or binary encoding_type")
    lower = variable.get("lower_bound")
    if isinstance(lower, bool) or not isinstance(lower, (int, float)) or float(lower) != 0.0:
        raise ValueError(f"integer variable {name!r} must have lower_bound=0")
    upper = variable.get("upper_bound")
    if (
        isinstance(upper, bool)
        or not isinstance(upper, (int, float))
        or not math.isfinite(float(upper))
        or not float(upper).is_integer()
        or int(upper) < 1
    ):
        raise ValueError(f"integer variable {name!r} must have a positive integral upper_bound")
    upper_int = int(upper)
    if str(encoding).lower() == "binary" and upper_int != 1:
        raise ValueError(f"binary variable {name!r} must have upper_bound=1")
    return upper_int


def derive_num_levels(variables: Sequence[Mapping[str, Any]]) -> list[int]:
    """Derive each zero-based integer domain size as ``upper_bound + 1``."""

    if not variables:
        raise ValueError("integer payload must contain at least one variable")
    return [_integer_upper_bound(variable) + 1 for variable in variables]


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and float(value).is_integer() and int(value) > 0:
        return int(value)
    return None


def _find_limit(value: Any, path: str) -> tuple[int, str] | None:
    names = {"dirac3_num_levels_limit", "dirac_3_num_levels_limit", "max_total_num_levels"}
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if str(key) in names and (limit := _positive_int(item)) is not None:
                return limit, child_path
        for key, item in value.items():
            if isinstance(item, Mapping) and (found := _find_limit(item, f"{path}.{key}")) is not None:
                return found
    return None


def resolve_dirac3_num_levels_limit(
    *,
    client: Any | None = None,
    max_total_num_levels: int | None = None,
    limit_source: str | None = None,
) -> tuple[int, str]:
    """Resolve the device capacity from explicit or discoverable configuration.

    qci-client 5.0.0 validates that ``num_levels`` is present but ships no
    hardware-capacity constant.  Consequently this function refuses to guess a
    limit.  Callers may supply a value read from a pinned experiment/device
    configuration, or expose it on their client/configuration object.
    """

    if max_total_num_levels is not None:
        limit = _positive_int(max_total_num_levels)
        if limit is None:
            raise ValueError("max_total_num_levels must be a positive integer")
        return limit, limit_source or "caller.max_total_num_levels"
    if client is not None:
        for attribute in ("dirac3_num_levels_limit", "dirac_3_num_levels_limit", "max_total_num_levels"):
            limit = _positive_int(getattr(client, attribute, None))
            if limit is not None:
                return limit, f"client.{attribute}"
        for attribute in ("config", "configuration", "device_config"):
            if (found := _find_limit(getattr(client, attribute, None), f"client.{attribute}")) is not None:
                return found
    raise RuntimeError(
        "Dirac-3 num_levels limit is unavailable from the installed/client configuration; "
        "refusing to invent a hardware capacity"
    )


def validate_num_levels(
    num_levels: Sequence[int],
    *,
    client: Any | None = None,
    max_total_num_levels: int | None = None,
    limit_source: str | None = None,
) -> dict[str, Any]:
    """Validate level domains and their aggregate device usage."""

    if not isinstance(num_levels, (list, tuple)) or not num_levels:
        raise ValueError("num_levels must be a non-empty list")
    levels: list[int] = []
    for index, value in enumerate(num_levels):
        level = _positive_int(value)
        if level is None or level < 2:
            raise ValueError(f"num_levels[{index}] must be an integer >= 2")
        levels.append(level)
    limit, source = resolve_dirac3_num_levels_limit(
        client=client,
        max_total_num_levels=max_total_num_levels,
        limit_source=limit_source,
    )
    total = sum(levels)
    if total > limit:
        raise ValueError(f"total num_levels {total} exceed configured Dirac-3 limit {limit} ({source})")
    return {"num_levels": levels, "total_num_levels": total, "limit": limit, "limit_source": source}


def build_integer_job_body(
    client: Any,
    *,
    polynomial_file_id: str,
    job_name: str,
    job_tags: Sequence[str],
    num_samples: int,
    relaxation_schedule: int,
    num_levels: Sequence[int],
    max_total_num_levels: int | None = None,
    limit_source: str | None = None,
) -> dict[str, Any]:
    """Build the documented qci-client integer job body."""

    if not polynomial_file_id:
        raise ValueError("polynomial_file_id is required")
    samples = _positive_int(num_samples)
    schedule = _positive_int(relaxation_schedule)
    if samples is None:
        raise ValueError("num_samples must be a positive integer")
    if schedule is None or schedule > 4:
        raise ValueError("relaxation_schedule must be between 1 and 4")
    level_audit = validate_num_levels(
        num_levels,
        client=client,
        max_total_num_levels=max_total_num_levels,
        limit_source=limit_source,
    )
    job_params = {
        "device_type": "dirac-3",
        "num_samples": samples,
        "relaxation_schedule": schedule,
        "num_levels": level_audit["num_levels"],
    }
    return client.build_job_body(
        job_type=INTEGER_JOB_TYPE,
        job_name=job_name,
        job_tags=list(job_tags),
        job_params=job_params,
        polynomial_file_id=polynomial_file_id,
    )


def _job_submission(response: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = response.get("job_submission")
    if isinstance(direct, Mapping):
        return direct
    job_info = response.get("job_info")
    if isinstance(job_info, Mapping) and isinstance(job_info.get("job_submission"), Mapping):
        return job_info["job_submission"]
    return {}


def _config_entry(config: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(config, Mapping) and isinstance(config.get(key), Mapping):
        return config[key]
    return None


def _solution_rows(response: Mapping[str, Any]) -> list[Any]:
    results = response.get("results")
    if not isinstance(results, Mapping):
        return []
    raw = results.get("solutions", results.get("samples", []))
    return list(raw) if isinstance(raw, list) else []


def _projected_count(response: Mapping[str, Any]) -> int:
    values: Any = response.get("projected_solutions", response.get("repaired_solutions"))
    if values is None and isinstance(response.get("results"), Mapping):
        results = response["results"]
        values = results.get("projected_solutions", results.get("repaired_solutions"))
    return len(values) if isinstance(values, list) else 0


def _sample_is_native_integer(sample: Any, levels: Sequence[int]) -> bool:
    if not isinstance(sample, (list, tuple)) or len(sample) != len(levels):
        return False
    for value, level in zip(sample, levels, strict=True):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        number = float(value)
        if not math.isfinite(number) or not number.is_integer() or number < 0 or number >= level:
            return False
    return True


def validate_integer_response(
    response: Mapping[str, Any],
    *,
    expected_num_levels: Sequence[int],
) -> IntegerResponseValidation:
    """Reject any response that is not natively integer and in-domain."""

    if not isinstance(expected_num_levels, (list, tuple)) or not expected_num_levels:
        raise ValueError("expected_num_levels must contain integers >= 2")
    expected_values: list[int] = []
    for value in expected_num_levels:
        level = _positive_int(value)
        if level is None or level < 2:
            raise ValueError("expected_num_levels must contain integers >= 2")
        expected_values.append(level)
    expected = tuple(expected_values)
    errors: list[str] = []
    status = str(response.get("status", "UNKNOWN")).upper()
    if status not in {"COMPLETED", "COMPLETE"}:
        errors.append(f"integer response status must be COMPLETED, got {status}")
    submission = _job_submission(response)
    problem_config = submission.get("problem_config", {})
    device_config = submission.get("device_config", {})

    problem_type = INTEGER_PROBLEM_TYPE if _config_entry(problem_config, INTEGER_PROBLEM_TYPE) is not None else "unknown"
    device_type = INTEGER_DEVICE_TYPE if _config_entry(device_config, INTEGER_DEVICE_TYPE) is not None else "unknown"
    serialized_keys = _mapping_keys(response)
    declared_job_type = submission.get("job_type")
    if declared_job_type is not None and declared_job_type != INTEGER_JOB_TYPE:
        errors.append(f"integer response job_type must be {INTEGER_JOB_TYPE}, got {declared_job_type}")
    for forbidden in FORBIDDEN_INTEGER_RESPONSE_KEYS:
        if forbidden in serialized_keys:
            errors.append(f"integer response contains forbidden {forbidden}")
    if problem_type != INTEGER_PROBLEM_TYPE:
        errors.append(f"integer response must contain {INTEGER_PROBLEM_TYPE}")
    integer_device = _config_entry(device_config, INTEGER_DEVICE_TYPE)
    if device_type != INTEGER_DEVICE_TYPE or integer_device is None:
        errors.append(f"integer response must contain {INTEGER_DEVICE_TYPE}")
        declared: tuple[int, ...] = ()
    else:
        raw_levels = integer_device.get("num_levels")
        if not isinstance(raw_levels, list):
            declared = ()
            errors.append("integer response must contain num_levels as a list")
        else:
            try:
                declared = tuple(int(value) for value in raw_levels)
            except (TypeError, ValueError):
                declared = ()
                errors.append("integer response num_levels contains non-integer values")
        if declared != expected:
            errors.append(f"integer response num_levels {list(declared)} do not match expected {list(expected)}")

    samples = _solution_rows(response)
    native_count = sum(_sample_is_native_integer(sample, expected) for sample in samples)
    if not samples:
        errors.append("integer response contains no native samples")
    elif native_count != len(samples):
        errors.append(f"only {native_count}/{len(samples)} raw samples are native integer and in-domain")

    return IntegerResponseValidation(
        valid=not errors,
        errors=tuple(errors),
        problem_type=problem_type,
        device_type=device_type,
        declared_num_levels=declared,
        native_sample_count=len(samples),
        native_integer_in_domain_count=native_count,
        projected_sample_count=_projected_count(response),
    )


def _mapping_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_mapping_keys(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys.update(_mapping_keys(item))
    return keys


def native_integer_samples(
    response: Mapping[str, Any],
    *,
    expected_num_levels: Sequence[int],
) -> list[list[int | float]]:
    """Return untouched native samples, or fail if any response gate is unmet."""

    validation = validate_integer_response(response, expected_num_levels=expected_num_levels)
    if not validation.valid:
        raise ValueError("response has no trustworthy native integer sample set: " + "; ".join(validation.errors))
    return [list(sample) for sample in _solution_rows(response)]


def _allocation(client: Any) -> Mapping[str, Any]:
    allocations = client.get_allocations().get("allocations", {})
    allocation = allocations.get("dirac", {}) if isinstance(allocations, Mapping) else {}
    if not isinstance(allocation, Mapping):
        raise RuntimeError("QCi Dirac allocation record is unavailable")
    if allocation.get("metered", True) and float(allocation.get("seconds", 0.0)) <= 0.0:
        raise RuntimeError("QCi Dirac allocation has no remaining seconds")
    return allocation


def submit_integer_job(
    client: Any,
    *,
    qci_file: Mapping[str, Any],
    job_name: str,
    job_tags: Sequence[str],
    num_samples: int,
    relaxation_schedule: int,
    num_levels: Sequence[int],
    max_total_num_levels: int | None = None,
    limit_source: str | None = None,
) -> dict[str, Any]:
    """Upload, submit, and strictly validate one direct qci-client integer job."""

    allocation = _allocation(client)
    file_response = client.upload_file(file=dict(qci_file))
    job_body = build_integer_job_body(
        client,
        polynomial_file_id=str(file_response["file_id"]),
        job_name=job_name,
        job_tags=job_tags,
        num_samples=num_samples,
        relaxation_schedule=relaxation_schedule,
        num_levels=num_levels,
        max_total_num_levels=max_total_num_levels,
        limit_source=limit_source,
    )
    response = client.process_job(job_body=job_body)
    validation = validate_integer_response(response, expected_num_levels=num_levels)
    if not validation.valid:
        raise ValueError("QCi integer response rejected: " + "; ".join(validation.errors))
    return {
        "allocation": dict(allocation),
        "file_response": file_response,
        "job_body": job_body,
        "requested_job_type": INTEGER_JOB_TYPE,
        "requested_job_params": {
            "device_type": "dirac-3",
            "num_samples": int(num_samples),
            "relaxation_schedule": int(relaxation_schedule),
            "num_levels": list(num_levels),
        },
        "response": response,
        "validation": validation,
        "versions": installed_qci_versions(),
    }


def solve_with_eqc_models(
    model: Any,
    *,
    num_samples: int,
    relaxation_schedule: int,
    num_levels: Sequence[int],
    job_name: str,
    job_tags: Sequence[str],
    api_url: str | None = None,
    api_token: str | None = None,
    max_total_num_levels: int | None = None,
    limit_source: str | None = None,
    solver_class: Any | None = None,
) -> dict[str, Any]:
    """Run an EQC model through ``Dirac3IntegerCloudSolver``.

    The model's zero-based upper bounds are checked against ``num_levels``.
    No ``sum_constraint`` argument is accepted or forwarded.
    """

    if solver_class is None:
        try:
            from eqc_models.solvers import Dirac3IntegerCloudSolver  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "eqc-models is not installed; install the pinned experiment version before using this backend"
            ) from exc
        solver_class = Dirac3IntegerCloudSolver
    solver = solver_class(url=api_url, api_token=api_token)
    level_audit = validate_num_levels(
        num_levels,
        client=solver,
        max_total_num_levels=max_total_num_levels,
        limit_source=limit_source,
    )
    upper_bound = getattr(model, "upper_bound", None)
    try:
        upper_values = [int(value) for value in upper_bound]
    except (TypeError, ValueError) as exc:
        raise ValueError("eqc model must expose integer upper_bound values") from exc
    expected_upper = [level - 1 for level in level_audit["num_levels"]]
    if upper_values != expected_upper:
        raise ValueError(f"eqc model upper_bound {upper_values} does not match num_levels {level_audit['num_levels']}")
    solver_result = solver.solve(
        model,
        name=job_name,
        tags=list(job_tags),
        num_samples=int(num_samples),
        relaxation_schedule=int(relaxation_schedule),
        wait=True,
    )
    if isinstance(solver_result, Mapping):
        response = solver_result
    elif isinstance(getattr(solver_result, "response", None), Mapping):
        # eqc-models 0.20.2 returns SolutionResults.  Its ``response`` member is
        # the untouched cloud response and is the only representation suitable
        # for strict response-mode and native-coordinate validation.
        response = solver_result.response
    else:
        raise ValueError("eqc-models integer solver returned no raw mapping response")
    validation = validate_integer_response(response, expected_num_levels=num_levels)
    if not validation.valid:
        raise ValueError("EQC integer response rejected: " + "; ".join(validation.errors))
    return {
        "response": response,
        "validation": validation,
        "versions": installed_qci_versions(),
        "backend": "eqc_models.solvers.Dirac3IntegerCloudSolver",
    }


def load_integer_payload(path: Path | str) -> tuple[dict[str, Any], dict[str, Any], list[int]]:
    """Load an integer CMPO payload and produce its qci polynomial file."""

    import json

    payload_path = Path(path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if payload.get("objective_sense") != "minimize":
        raise ValueError("integer QCi payload objective_sense must be minimize")
    levels = derive_num_levels(payload.get("variables", []))
    return payload, convert_cmpo_payload_to_qci_file(payload), levels
