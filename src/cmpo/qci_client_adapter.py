"""QCi Dirac-3 qci-client workflow for Phase 3 payload execution."""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from cmpo.budget_encoding import validate_budget_payload


def _parse_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_qci_dotenv(path: Path | str = Path(".env")) -> dict[str, str]:
    """Load QCi variables from a local .env file without overriding the process environment."""

    env_path = Path(path)
    if not env_path.exists():
        return {}
    loaded: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in {"QCI_API_URL", "QCI_TOKEN"}:
            continue
        parsed = _parse_env_value(value)
        loaded[key] = parsed
        os.environ.setdefault(key, parsed)
    return loaded


def validate_qci_environment() -> dict[str, str]:
    """Validate QCi environment variables and qci-client availability."""

    load_qci_dotenv(os.environ.get("QCI_ENV_FILE", ".env"))
    missing = [name for name in ("QCI_API_URL", "QCI_TOKEN") if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required QCi settings: {', '.join(missing)}. Put them in .env or set QCI_ENV_FILE.")
    try:
        import qci_client as qc  # noqa: F401, PLC0415
    except ImportError as exc:
        raise RuntimeError("qci-client is required for live QCi execution. Install with `pip install qci-client`.") from exc
    return {"QCI_API_URL": os.environ["QCI_API_URL"], "QCI_TOKEN": "***"}


def load_cmpo_payload(path: Path | str) -> dict[str, Any]:
    """Load and lightly validate a CMPO payload JSON file."""

    payload_path = Path(path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    required = {"variables", "polynomial_terms", "objective_sense", "max_degree"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"CMPO payload missing required keys {missing}: {payload_path}")
    if payload["objective_sense"] != "minimize":
        raise ValueError(f"QCi adapter expects minimize payloads: {payload_path}")
    return payload


def _declares_integer_domain(payload: dict[str, Any]) -> bool:
    integer_encodings = {"binary", "integer", "int", "qudit"}
    return any(
        str(variable.get("encoding_type", "")).lower() in integer_encodings or "num_levels" in variable
        for variable in payload.get("variables", [])
    )


def _term_to_qci_idx(term: dict[str, Any], variable_index: dict[str, int]) -> list[int]:
    idx: list[int] = []
    for name, exponent in term.get("powers", {}).items():
        if name not in variable_index:
            raise ValueError(f"term references unknown variable: {name}")
        idx.extend([variable_index[name]] * int(exponent))
    return sorted(idx)


def convert_cmpo_payload_to_qci_file(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a CMPO polynomial payload into qci-client polynomial file format."""

    variables = payload["variables"]
    variable_index = {str(variable["name"]): index for index, variable in enumerate(variables, start=1)}
    terms: list[tuple[list[int], float]] = []
    min_degree: int | None = None
    max_degree = 0
    for term in payload["polynomial_terms"]:
        idx = _term_to_qci_idx(term, variable_index)
        if not idx:
            continue
        degree = len(idx)
        min_degree = degree if min_degree is None else min(min_degree, degree)
        max_degree = max(max_degree, degree)
        terms.append((idx, float(term["coefficient"])))
    if not terms:
        raise ValueError("CMPO payload contains no non-constant polynomial terms")
    data = [{"idx": [0] * (max_degree - len(idx)) + idx, "val": coefficient} for idx, coefficient in terms]

    scenario = payload.get("scenario_metadata", {}).get("scenario", "scenario")
    patch = payload.get("patch_metadata", {}).get("patch", "patch")
    return {
        "file_name": f"cmpo_{scenario}_{patch}",
        "file_config": {
            "polynomial": {
                "num_variables": len(variables),
                "min_degree": int(min_degree or 1),
                "max_degree": int(max_degree),
                "data": data,
            }
        },
        "cmpo_metadata": {
            "schema": payload.get("schema"),
            "scenario_metadata": payload.get("scenario_metadata", {}),
            "patch_metadata": payload.get("patch_metadata", {}),
            "variable_order": [variable["name"] for variable in variables],
            "variable_bounds": {
                variable["name"]: [variable.get("lower_bound"), variable.get("upper_bound")] for variable in variables
            },
            "model_statistics": payload.get("model_statistics", {}),
        },
    }


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(item) for item in value]
        return str(value)


def _job_id(response: dict[str, Any]) -> str:
    return str(
        response.get("job_id")
        or response.get("job_info", {}).get("job_id")
        or response.get("job_info", {}).get("job_submission_id")
        or ""
    )


def _submit_job_id(response: dict[str, Any]) -> str:
    return str(response.get("job_id") or response.get("job_info", {}).get("job_id") or "")


def _job_status(response: dict[str, Any]) -> str:
    return str(response.get("status") or response.get("job_status") or response.get("job_info", {}).get("status") or "UNKNOWN")


def _is_completed_response(path: Path, *, minimum_solutions: int = 1) -> bool:
    if not path.exists():
        return False
    try:
        response = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    status = _job_status(response).upper()
    return status in {"COMPLETED", "COMPLETE"} and len(_raw_solutions(response)) >= minimum_solutions


def _raw_energies(response: dict[str, Any]) -> list[Any]:
    results = response.get("results") or {}
    return list(results.get("energies") or results.get("energy") or [])


def _raw_solutions(response: dict[str, Any]) -> list[Any]:
    results = response.get("results") or {}
    return list(results.get("solutions") or results.get("samples") or [])


def _final_status(status: str) -> bool:
    return status.upper() in {"COMPLETED", "COMPLETE", "FAILED", "ERROR", "CANCELED", "CANCELLED"}


def submit_dirac3_job(
    client: Any,
    qci_file: dict[str, Any],
    job_name: str,
    job_tags: list[str],
    job_params: dict[str, Any],
) -> dict[str, Any]:
    """Upload a polynomial file, build a sample-hamiltonian job, and process it."""

    allocation = client.get_allocations()["allocations"]["dirac"]
    seconds = float(allocation.get("seconds", 0.0))
    if allocation.get("metered", True) and seconds <= 0.0:
        raise RuntimeError("QCi Dirac allocation has no remaining seconds.")
    file_response = client.upload_file(file=qci_file)
    job_body = client.build_job_body(
        job_type="sample-hamiltonian",
        job_name=job_name,
        job_tags=job_tags,
        job_params=job_params,
        polynomial_file_id=file_response["file_id"],
    )
    response = client.process_job(job_body=job_body)
    return {
        "allocation": allocation,
        "file_response": file_response,
        "job_body": job_body,
        "response": response,
    }


def _submit_dirac3_job_async(
    client: Any,
    qci_file: dict[str, Any],
    job_name: str,
    job_tags: list[str],
    job_params: dict[str, Any],
) -> dict[str, Any]:
    allocation = client.get_allocations()["allocations"]["dirac"]
    seconds = float(allocation.get("seconds", 0.0))
    if allocation.get("metered", True) and seconds <= 0.0:
        raise RuntimeError("QCi Dirac allocation has no remaining seconds.")
    file_response = client.upload_file(file=qci_file)
    job_body = client.build_job_body(
        job_type="sample-hamiltonian",
        job_name=job_name,
        job_tags=job_tags,
        job_params=job_params,
        polynomial_file_id=file_response["file_id"],
    )
    if not hasattr(client, "submit_job") or not hasattr(client, "get_job_results"):
        response = client.process_job(job_body=job_body)
        return {
            "allocation": allocation,
            "file_response": file_response,
            "job_body": job_body,
            "submit_response": {"job_id": _job_id(response), "status": _job_status(response)},
            "response": response,
            "completed_inline": True,
        }
    submit_response = client.submit_job(job_body=job_body)
    return {
        "allocation": allocation,
        "file_response": file_response,
        "job_body": job_body,
        "submit_response": submit_response,
        "response": None,
        "completed_inline": False,
    }


def _record_from_response(
    *,
    payload_file: Path,
    repeat: int,
    request_path: Path,
    response_path: Path,
    response: dict[str, Any],
    runtime: float,
) -> dict[str, Any]:
    failure_reason = "" if _job_status(response).upper() in {"COMPLETED", "COMPLETE"} else "QCi job did not complete"
    return {
        "payload": str(payload_file),
        "repeat": repeat,
        "job_id": _job_id(response),
        "status": _job_status(response),
        "raw_energies": json.dumps(_raw_energies(response)),
        "raw_solutions": json.dumps(_raw_solutions(response)),
        "runtime_seconds": runtime,
        "failure_reason": failure_reason,
        "request_json": str(request_path),
        "response_json": str(response_path),
    }


def _job_params_from_config(config: dict[str, Any]) -> dict[str, Any]:
    qci_config = config.get("qci", {})
    job_params = dict(qci_config.get("job_params", {}))
    job_params["device_type"] = "dirac-3"
    if "relaxation_schedule" in qci_config:
        job_params["relaxation_schedule"] = qci_config["relaxation_schedule"]
    if qci_config.get("sum_constraint") is not None:
        job_params["sum_constraint"] = qci_config["sum_constraint"]
    return job_params


def _client_from_environment() -> Any:
    import qci_client as qc  # noqa: PLC0415

    return qc.QciClient()


def _repeat_dir(output_dir: Path, payload_path: Path, repeat: int) -> Path:
    return output_dir / payload_path.stem / f"repeat_{repeat:03d}"


def _sample_batches(repeats: int, samples_per_job: int) -> list[tuple[int, int]]:
    return [(start, min(samples_per_job, repeats - start)) for start in range(0, repeats, samples_per_job)]


def _pending_job_id_from_request(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return _submit_job_id(request.get("submit_response", {}))


def run_payload_repeats(
    payload_path: Path | str,
    repeats: int,
    output_dir: Path | str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run one CMPO payload on QCi Dirac-3 for ``repeats`` attempts."""

    out_dir = Path(output_dir)
    payload_file = Path(payload_path)
    payload = load_cmpo_payload(payload_file)
    if payload.get("budget_constraint") or payload.get("budget_encoding"):
        budget_validation = validate_budget_payload(payload)
        if not budget_validation.passed:
            raise ValueError(
                "budget constraint is metadata only; QCi submission refused before environment, upload, or client setup: "
                f"{budget_validation.failure_reason}"
            )
    if _declares_integer_domain(payload):
        raise ValueError(
            "integer payload refused by the legacy continuous adapter; use the "
            "sample-hamiltonian-integer path in cmpo.qci_integer_adapter"
        )
    validate_qci_environment()
    client = _client_from_environment()
    out_dir.mkdir(parents=True, exist_ok=True)
    qci_file = convert_cmpo_payload_to_qci_file(payload)
    overwrite = bool(config.get("overwrite", False))
    job_params = _job_params_from_config(config)
    qci_config = config.get("qci", {})
    tags = [str(tag) for tag in qci_config.get("job_tags", ["cmpo", "phase3", "qci"])]
    records: list[dict[str, Any]] = []
    max_inflight = max(1, int(qci_config.get("max_inflight_jobs", os.environ.get("QCI_MAX_INFLIGHT_JOBS", 4))))
    poll_interval = max(1.0, float(qci_config.get("poll_interval_seconds", os.environ.get("QCI_POLL_INTERVAL_SECONDS", 15))))
    samples_per_job = max(1, int(qci_config.get("samples_per_job", os.environ.get("QCI_SAMPLES_PER_JOB", 1))))
    sample_batches = _sample_batches(repeats, samples_per_job)

    pending: list[dict[str, Any]] = []
    batches_to_submit: list[tuple[int, int]] = []

    for repeat, batch_samples in sample_batches:
        repeat_dir = _repeat_dir(out_dir, payload_file, repeat)
        request_path = repeat_dir / "request.json"
        response_path = repeat_dir / "response.json"
        if repeat_dir.exists() and not overwrite and _is_completed_response(response_path, minimum_solutions=batch_samples):
            existing = json.loads(response_path.read_text(encoding="utf-8"))
            records.append(
                {
                    "payload": str(payload_file),
                    "repeat": repeat,
                    "job_id": _job_id(existing),
                    "status": "SKIPPED_COMPLETED",
                    "raw_energies": "[]",
                    "raw_solutions": "[]",
                    "runtime_seconds": 0.0,
                    "failure_reason": f"Existing completed QCi result not overwritten: {response_path}",
                    "request_json": str(request_path),
                    "response_json": str(response_path),
                }
            )
            continue
        repeat_dir.mkdir(parents=True, exist_ok=True)
        pending_job_id = "" if overwrite else _pending_job_id_from_request(request_path)
        if pending_job_id and not response_path.exists():
            pending.append(
                {
                    "repeat": repeat,
                    "batch_samples": batch_samples,
                    "job_id": pending_job_id,
                    "started": time.perf_counter(),
                    "request_path": request_path,
                    "response_path": response_path,
                }
            )
        else:
            batches_to_submit.append((repeat, batch_samples))

    submit_index = 0
    while submit_index < len(batches_to_submit) or pending:
        while submit_index < len(batches_to_submit) and len(pending) < max_inflight:
            repeat, batch_samples = batches_to_submit[submit_index]
            submit_index += 1
            repeat_dir = _repeat_dir(out_dir, payload_file, repeat)
            request_path = repeat_dir / "request.json"
            response_path = repeat_dir / "response.json"
            job_name = f"{config.get('name', 'cmpo_phase3')}_{payload_file.stem}_r{repeat:03d}_n{batch_samples}"
            started = time.perf_counter()
            batch_job_params = dict(job_params)
            batch_job_params["num_samples"] = batch_samples
            request_record = {
                "payload_path": str(payload_file),
                "qci_file": qci_file,
                "job_name": job_name,
                "job_tags": tags,
                "job_params": batch_job_params,
                "repeat_start": repeat,
                "repeat_count": batch_samples,
                "requested_repeats": repeats,
                "samples_per_job": samples_per_job,
            }
            try:
                result = _submit_dirac3_job_async(client, qci_file, job_name, tags, batch_job_params)
                request_record["allocation"] = result["allocation"]
                request_record["file_response"] = result["file_response"]
                request_record["job_body"] = result["job_body"]
                request_record["submit_response"] = result["submit_response"]
                request_path.write_text(json.dumps(_json_safe(request_record), indent=2), encoding="utf-8")
                if result.get("completed_inline"):
                    response = _json_safe(result["response"])
                    response_path.write_text(json.dumps(response, indent=2), encoding="utf-8")
                    records.append(
                        _record_from_response(
                            payload_file=payload_file,
                            repeat=repeat,
                            request_path=request_path,
                            response_path=response_path,
                            response=response,
                            runtime=time.perf_counter() - started,
                        )
                    )
                else:
                    pending.append(
                        {
                            "repeat": repeat,
                            "batch_samples": batch_samples,
                            "job_id": _submit_job_id(result["submit_response"]),
                            "started": started,
                            "request_path": request_path,
                            "response_path": response_path,
                        }
                    )
            except Exception as exc:  # noqa: BLE001 - each repeat must record failures.
                runtime = time.perf_counter() - started
                response = {"status": "FAILED", "failure_reason": str(exc)}
                request_path.write_text(json.dumps(_json_safe(request_record), indent=2), encoding="utf-8")
                response_path.write_text(json.dumps(_json_safe(response), indent=2), encoding="utf-8")
                records.append(
                    {
                        "payload": str(payload_file),
                        "repeat": repeat,
                        "job_id": "",
                        "status": "FAILED",
                        "raw_energies": "[]",
                        "raw_solutions": "[]",
                        "runtime_seconds": runtime,
                        "failure_reason": str(exc),
                        "request_json": str(request_path),
                        "response_json": str(response_path),
                    }
                )

        if not pending:
            continue

        still_pending: list[dict[str, Any]] = []
        for item in pending:
            try:
                status = str(client.get_job_status(job_id=item["job_id"])["status"])
                if not _final_status(status):
                    still_pending.append(item)
                    continue
                response = _json_safe(client.get_job_results(job_id=item["job_id"]))
                item["response_path"].write_text(json.dumps(response, indent=2), encoding="utf-8")
                records.append(
                    _record_from_response(
                        payload_file=payload_file,
                        repeat=int(item["repeat"]),
                        request_path=item["request_path"],
                        response_path=item["response_path"],
                        response=response,
                        runtime=time.perf_counter() - float(item["started"]),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - keep polling recoverable API waits.
                if "last_error" not in item:
                    item["last_error"] = str(exc)
                still_pending.append(item)
        pending = still_pending
        if pending:
            time.sleep(poll_interval)
    return records


def write_job_status_csv(records: list[dict[str, Any]], path: Path | str) -> Path:
    """Write a QCi repeat status CSV."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "payload",
        "repeat",
        "job_id",
        "status",
        "raw_energies",
        "raw_solutions",
        "runtime_seconds",
        "failure_reason",
        "request_json",
        "response_json",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fieldnames})
    return output_path


class QciClientAdapter:
    """Compatibility wrapper around the live QCi repeat runner."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def submit(self, *, repeats: int, dry_run: bool = False) -> dict[str, Any]:
        if dry_run:
            return {"config": self.config.get("name"), "repeats": repeats, "dry_run": True}
        payloads = self.config.get("payloads", [])
        output_dir = self.config.get("output_dir", Path("results") / "phase3" / "qci")
        records: list[dict[str, Any]] = []
        for payload in payloads:
            records.extend(run_payload_repeats(payload, repeats, output_dir, self.config))
        status_path = write_job_status_csv(records, Path(output_dir) / "job_status.csv")
        return {"status_csv": str(status_path), "rows": len(records)}
