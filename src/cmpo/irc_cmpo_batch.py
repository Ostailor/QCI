"""Create-only asynchronous orchestration for the final IRC-CMPO QCi batch."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from cmpo.qci_client_adapter import convert_cmpo_payload_to_qci_file
from cmpo.qci_integer_adapter import (
    INTEGER_JOB_TYPE,
    build_integer_job_body,
    derive_num_levels,
    native_integer_samples,
    validate_integer_response,
)
from cmpo.irc_cmpo_decode import decode_native_sample


FINAL_EVIDENCE_TAG = "evidence-31e8c858"
EXPECTED_VERSIONS = {"qci-client": "5.0.0", "eqc-models": "0.20.2"}
FULL_NAMES = tuple(f"lambda_{index:02d}" for index in range(6))


@dataclass(frozen=True)
class FinalBatchJobSpec:
    """One immutable final-batch submission specification."""

    name: str
    payload_path: Path
    num_samples: int
    tags: tuple[str, ...]
    canary: bool = False


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def _replace_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_artifact_root(
    repo_root: Path, artifact_root: Path | str | None
) -> Path:
    if artifact_root is None:
        return repo_root / "results/phase3/irc_cmpo"
    value = Path(artifact_root)
    return value if value.is_absolute() else repo_root / value


def build_final_job_specs(
    repo_root: Path | str,
    *,
    artifact_root: Path | str | None = None,
    evidence_tag: str = FINAL_EVIDENCE_TAG,
) -> tuple[FinalBatchJobSpec, ...]:
    """Return the mandated eight jobs in their exact submission order."""

    root = Path(repo_root).resolve()
    artifacts = _resolve_artifact_root(root, artifact_root)
    smoke = artifacts / "smoke/payloads"
    full = artifacts / "payloads"
    ordered = (
        ("toy", smoke / "toy.json", 30, True),
        ("reduced", smoke / "reduced_ieee123.json", 30, True),
        ("lambda_03", full / "lambda_03.json", 100, True),
        ("lambda_00", full / "lambda_00.json", 100, False),
        ("lambda_01", full / "lambda_01.json", 100, False),
        ("lambda_02", full / "lambda_02.json", 100, False),
        ("lambda_04", full / "lambda_04.json", 100, False),
        ("lambda_05", full / "lambda_05.json", 100, False),
    )
    specs = []
    for name, path, samples, canary in ordered:
        tags = ["phase3", "irc-cmpo", "integer", "final", evidence_tag, name]
        if canary:
            tags.append("canary")
        specs.append(FinalBatchJobSpec(name, path, samples, tuple(tags), canary))
    return tuple(specs)


def _validate_full_payload(path: Path) -> list[str]:
    errors: list[str] = []
    payload = _read_json(path)
    levels = payload.get("num_levels")
    if payload.get("num_variables") != 33 or len(payload.get("variables", ())) != 33:
        errors.append("must contain exactly 33 variables")
    if levels != [2] * 33:
        errors.append("num_levels must equal [2] * 33")
    if not isinstance(levels, list) or sum(levels) != 66:
        errors.append("total_num_levels must equal 66")
    if int(payload.get("max_degree", 99)) > 3:
        errors.append("maximum degree exceeds 3")
    scaling = payload.get("dirac3_scaling", {})
    audit = scaling.get("audit", {}) if isinstance(scaling, Mapping) else {}
    if not bool(audit.get("passed", False)):
        errors.append("Dirac-3 coefficient audit did not pass")
    if float(audit.get("dynamic_range", float("inf"))) > 200.0:
        errors.append("Dirac-3 coefficient dynamic range exceeds 200")
    post = scaling.get("post_quantization_validation", {}) if isinstance(scaling, Mapping) else {}
    if not bool(post.get("gates_passed", False)):
        errors.append("post-quantization validation did not pass")
    irc = payload.get("irc_cmpo", {})
    if not isinstance(irc, Mapping) or irc.get("projection_permitted") is not False:
        errors.append("projection_permitted must be false")
    if isinstance(scaling, Mapping) and scaling.get("projection_used") is not False:
        errors.append("payload scaling reports projection")
    try:
        derived = derive_num_levels(payload["variables"])
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"integer domains are invalid: {exc}")
    else:
        if derived != levels:
            errors.append("declared num_levels do not match variable domains")
    return errors


def _allocation_available(allocation: Mapping[str, Any]) -> bool:
    if not allocation:
        return False
    if not bool(allocation.get("metered", True)):
        return True
    try:
        return float(allocation.get("seconds", 0.0)) > 0.0
    except (TypeError, ValueError):
        return False


def validate_final_preflight(
    repo_root: Path | str,
    *,
    artifact_root: Path | str | None = None,
    output_dir: Path | str,
    environ: Mapping[str, str] | None = None,
    versions: Mapping[str, str],
    allocation: Mapping[str, Any],
) -> dict[str, Any]:
    """Run every offline and transport gate without mutating the output tree."""

    root = Path(repo_root).resolve()
    artifacts = _resolve_artifact_root(root, artifact_root)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"final output directory already exists: {output}")
    environment = os.environ if environ is None else environ
    errors: list[str] = []
    summary_path = artifacts / "preflight_summary.json"
    summary = _read_json(summary_path)
    if str(summary.get("IRC_CMPO_READY_FOR_QCI", "NO")).upper() != "YES":
        errors.append("preflight_summary.json is not ready for QCi")

    specs = build_final_job_specs(root, artifact_root=artifacts)
    missing = [str(spec.payload_path) for spec in specs if not spec.payload_path.is_file()]
    if missing:
        errors.append(f"missing payloads: {missing}")
    full_specs = [spec for spec in specs if spec.name in FULL_NAMES]
    if len(full_specs) != 6:
        errors.append("exactly six full lambda payloads are required")
    full_errors = {
        spec.name: _validate_full_payload(spec.payload_path)
        for spec in full_specs
        if spec.payload_path.is_file()
    }
    if any(full_errors.values()):
        errors.append(f"full payload validation failed: {full_errors}")

    smoke_plan_path = artifacts / "smoke/smoke_plan.json"
    smoke_plan = _read_json(smoke_plan_path)
    exact_by_name = {
        str(row.get("name")): row.get("known_exact_optimum")
        for row in smoke_plan.get("jobs", ())
        if isinstance(row, Mapping)
    }
    if not exact_by_name.get("toy") or not exact_by_name.get("reduced_ieee123"):
        errors.append("toy and reduced exact optima must be present")
    for package, expected in EXPECTED_VERSIONS.items():
        if versions.get(package) != expected:
            errors.append(
                f"{package} must be {expected}, found {versions.get(package, 'missing')}"
            )
    for variable in ("QCI_API_URL", "QCI_TOKEN"):
        if not str(environment.get(variable, "")).strip():
            errors.append(f"{variable} is not present")
    if not _allocation_available(allocation):
        errors.append("Dirac allocation is unavailable or depleted")
    if errors:
        raise ValueError("final QCi preflight failed: " + "; ".join(errors))
    return {
        "passed": True,
        "checked_at": _utc_now(),
        "summary_path": str(summary_path),
        "artifact_root": str(artifacts),
        "full_payload_count": len(full_specs),
        "full_payload_gates_passed": True,
        "toy_exact_optimum": exact_by_name["toy"],
        "reduced_exact_optimum": exact_by_name["reduced_ieee123"],
        "versions": dict(versions),
        "allocation": dict(allocation),
        "output_dir_was_absent": True,
    }


def _job_id(response: Mapping[str, Any]) -> str:
    value = response.get("job_id")
    if value is None and isinstance(response.get("job_info"), Mapping):
        value = response["job_info"].get("job_id")
    if not value:
        raise ValueError(f"QCi submit response has no job_id: {response}")
    return str(value)


def _write_status_csv(path: Path, jobs: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "name",
        "job_id",
        "status",
        "canary",
        "num_samples",
        "submitted_at",
        "last_checked_at",
        "failure_reason",
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for job in jobs:
            writer.writerow({field: job.get(field, "") for field in fields})
    temporary.replace(path)


def submit_final_batch(
    client: Any,
    specs: Sequence[FinalBatchJobSpec],
    *,
    output_dir: Path | str,
    preflight: Mapping[str, Any],
    git_commit: str,
    relaxation_schedule: int = 2,
    maximum_total_num_levels: int = 954,
    num_levels_limit_source: str = "pinned IRC-CMPO configuration",
) -> dict[str, Any]:
    """Upload and asynchronously queue all eight jobs, preserving every exchange."""

    if preflight.get("passed") is not True:
        raise ValueError("a passing final preflight record is required")
    if len(str(git_commit).strip()) < 7:
        raise ValueError("a concrete git commit is required for live submission provenance")
    if [spec.name for spec in specs] != [
        "toy",
        "reduced",
        "lambda_03",
        "lambda_00",
        "lambda_01",
        "lambda_02",
        "lambda_04",
        "lambda_05",
    ]:
        raise ValueError("final batch submission order is invalid")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    for name in ("requests", "responses", "validations"):
        (output / name).mkdir()

    allocation_snapshots: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "schema": "cmpo.irc_cmpo.final_qci_batch.v1",
        "git_commit": git_commit,
        "created_at": _utc_now(),
        "preflight": dict(preflight),
        "jobs": [],
        "projection_permitted": False,
    }
    _write_new_json(output / "batch_manifest.json", manifest)
    _write_new_json(output / "allocation_snapshot.json", allocation_snapshots)

    for spec in specs:
        payload = _read_json(spec.payload_path)
        levels = list(payload["num_levels"])
        allocation = client.get_allocations().get("allocations", {}).get("dirac", {})
        if not isinstance(allocation, Mapping) or not _allocation_available(allocation):
            raise RuntimeError(f"Dirac allocation unavailable before submitting {spec.name}")
        allocation_record = {
            "job_name": spec.name,
            "captured_at": _utc_now(),
            "allocation": dict(allocation),
        }
        allocation_snapshots.append(allocation_record)
        _replace_json(output / "allocation_snapshot.json", allocation_snapshots)

        qci_file = convert_cmpo_payload_to_qci_file(payload)
        file_response = client.upload_file(file=qci_file)
        job_body = build_integer_job_body(
            client,
            polynomial_file_id=str(file_response["file_id"]),
            job_name=f"phase3-irc-cmpo-final-{spec.name}",
            job_tags=spec.tags,
            num_samples=spec.num_samples,
            relaxation_schedule=relaxation_schedule,
            num_levels=levels,
            max_total_num_levels=maximum_total_num_levels,
            limit_source=num_levels_limit_source,
        )
        if "sum_constraint" in json.dumps(job_body):
            raise ValueError(f"integer request {spec.name} contains forbidden sum_constraint")
        request_record = {
            "payload_path": str(spec.payload_path),
            "payload_sha256": _sha256(spec.payload_path),
            "qci_file": qci_file,
            "uploaded_file_response": file_response,
            "job_body": job_body,
            "allocation_before_submission": dict(allocation),
        }
        _write_new_json(output / "requests" / f"{spec.name}.json", request_record)
        submitted_at = _utc_now()
        submit_response = client.submit_job(job_body=job_body)
        _write_new_json(
            output / "responses" / f"{spec.name}.submit.json", submit_response
        )
        record = {
            "name": spec.name,
            "payload_path": str(spec.payload_path),
            "payload_sha256": request_record["payload_sha256"],
            "uploaded_qci_file_id": str(file_response["file_id"]),
            "job_id": _job_id(submit_response),
            "job_type": INTEGER_JOB_TYPE,
            "device_type": "dirac-3",
            "num_samples": spec.num_samples,
            "relaxation_schedule": relaxation_schedule,
            "num_levels": levels,
            "total_num_levels": sum(levels),
            "submission_timestamp": submitted_at,
            "submitted_at": submitted_at,
            "qci_package_versions": dict(preflight["versions"]),
            "allocation_before_submission": dict(allocation),
            "tags": list(spec.tags),
            "canary": spec.canary,
            "status": str(submit_response.get("status", "SUBMITTED")),
            "last_checked_at": submitted_at,
            "failure_reason": "",
            "projection_permitted": False,
        }
        manifest["jobs"].append(record)
        _replace_json(output / "batch_manifest.json", manifest)
        _write_status_csv(output / "job_status.csv", manifest["jobs"])
    return manifest


def final_status(status: str) -> bool:
    """Return whether a QCi 5.0.0 status is terminal."""

    return str(status).upper() in {"COMPLETED", "ERRORED", "CANCELLED", "FAILED"}


def cancellable_status(status: str) -> bool:
    """Return whether QCi documents cancellation for this state."""

    return str(status).upper() in {"SUBMITTED", "QUEUED", "RUNNING"}


def _payload_energy(payload: Mapping[str, Any], sample: Sequence[int | float]) -> float:
    values = {
        str(variable["name"]): int(value)
        for variable, value in zip(payload["variables"], sample, strict=True)
    }
    return math.fsum(
        float(term["coefficient"])
        * (
            1.0
            if not term.get("powers")
            else math.prod(
                values[str(name)] ** int(power)
                for name, power in term["powers"].items()
            )
        )
        for term in payload["polynomial_terms"]
    )


def validate_canary_response(
    name: str,
    payload: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    known_exact_optimum: Mapping[str, Any] | None = None,
    true_recourse_regret: float | None = None,
    expected_sample_count: int | None = None,
) -> dict[str, Any]:
    """Apply native-only transport and quality gates to a final response."""

    validation = validate_integer_response(
        response, expected_num_levels=payload["num_levels"]
    )
    results = response.get("results", {})
    counts = results.get("counts", []) if isinstance(results, Mapping) else []
    rows = results.get("solutions", []) if isinstance(results, Mapping) else []
    if not isinstance(rows, list):
        rows = []
    if (
        isinstance(counts, list)
        and len(counts) == len(rows)
        and all(isinstance(value, (int, float)) and int(value) >= 0 for value in counts)
    ):
        multiplicities = [int(value) for value in counts]
    else:
        multiplicities = [1] * len(rows)
    raw_sample_count = sum(multiplicities)
    samples = (
        native_integer_samples(response, expected_num_levels=payload["num_levels"])
        if validation.valid and validation.projected_sample_count == 0
        else []
    )
    locally_feasible: list[tuple[list[int | float], float, int]] = []
    for index, sample in enumerate(samples):
        try:
            decode_native_sample(payload, sample, require_budget=False)
        except ValueError:
            continue
        locally_feasible.append(
            (sample, _payload_energy(payload, sample), multiplicities[index])
        )
    locally_feasible_count = sum(row[2] for row in locally_feasible)
    best_energy = min((row[1] for row in locally_feasible), default=None)
    optimum_energy = (
        float(known_exact_optimum["energy"])
        if known_exact_optimum is not None
        else None
    )
    hamiltonian_regret = (
        max(0.0, (float(best_energy) - optimum_energy) / max(abs(optimum_energy), 1.0))
        if best_energy is not None and optimum_energy is not None
        else None
    )
    optimum_coordinates = (
        list(known_exact_optimum["coordinates"])
        if known_exact_optimum is not None
        else None
    )
    optimum_hits = sum(
        multiplicity
        for sample, _energy, multiplicity in locally_feasible
        if optimum_coordinates is not None and list(sample) == optimum_coordinates
    )
    sample_count_gate = (
        expected_sample_count is None or raw_sample_count >= expected_sample_count
    )
    passed = bool(
        validation.valid
        and validation.native_integer_in_domain_count == validation.native_sample_count
        and validation.projected_sample_count == 0
        and sample_count_gate
        and locally_feasible_count > 0
    )
    if name == "toy":
        passed = passed and optimum_hits > 0
    elif name == "reduced":
        passed = bool(
            passed
            and hamiltonian_regret is not None
            and hamiltonian_regret <= 0.02 + 1e-12
            and true_recourse_regret is not None
            and true_recourse_regret <= 0.10 + 1e-12
        )
    elif name == "lambda_03":
        passed = bool(
            passed
            and true_recourse_regret is not None
            and true_recourse_regret <= 0.15 + 1e-12
        )
    return {
        "name": name,
        "passed": passed,
        "validation": validation.to_dict(),
        "raw_unique_row_count": len(rows),
        "raw_sample_count": raw_sample_count,
        "native_integer_rate": (
            validation.native_integer_in_domain_count
            / max(validation.native_sample_count, 1)
        ),
        "native_locally_feasible_count": locally_feasible_count,
        "native_local_feasibility_rate": locally_feasible_count
        / max(raw_sample_count, 1),
        "best_hamiltonian_energy": best_energy,
        "exact_optimum_energy": optimum_energy,
        "hamiltonian_regret": hamiltonian_regret,
        "exact_optimum_hits": optimum_hits,
        "true_recourse_regret": true_recourse_regret,
        "projection_used": False,
        "sample_count_gate": sample_count_gate,
    }


def cancel_active_full_jobs(
    client: Any,
    jobs: Sequence[Mapping[str, Any]],
    *,
    reason: str,
) -> dict[str, Any]:
    """Cancel each still-active full job after a failed canary."""

    cancelled: list[str] = []
    records: list[dict[str, Any]] = []
    for job in jobs:
        if not str(job.get("name", "")).startswith("lambda_"):
            continue
        job_id = str(job["job_id"])
        status = str(client.get_job_status(job_id=job_id).get("status", "UNKNOWN"))
        record: dict[str, Any] = {
            "name": job["name"],
            "job_id": job_id,
            "status_before": status,
            "cancel_requested": False,
        }
        if cancellable_status(status):
            try:
                record["cancel_response"] = client.cancel_job(job_id=job_id)
                record["cancel_requested"] = True
                cancelled.append(job_id)
            except Exception as exc:  # noqa: BLE001 - completion may race cancellation.
                refreshed = str(
                    client.get_job_status(job_id=job_id).get("status", "UNKNOWN")
                )
                record["cancel_error"] = str(exc)
                record["status_after_error"] = refreshed
                if not final_status(refreshed):
                    raise
        records.append(record)
    return {
        "reason": reason,
        "created_at": _utc_now(),
        "cancelled_job_ids": cancelled,
        "jobs": records,
    }
