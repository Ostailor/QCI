#!/usr/bin/env python
"""Plan or explicitly execute only the three gated IRC-CMPO smoke jobs."""

from __future__ import annotations

import argparse
from copy import deepcopy
import itertools
import json
import math
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_decode import decode_native_sample  # noqa: E402
from cmpo.irc_cmpo_lagrangian import run_three_job_smoke  # noqa: E402
from cmpo.irc_cmpo_constraints import audit_coefficients  # noqa: E402
from cmpo.irc_cmpo_master import (  # noqa: E402
    IRCAsset,
    build_irc_master,
    build_scalarized_irc_master,
)


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
DEFAULT_FINAL_SUMMARY = Path("results/phase3/irc_cmpo/final_prequeue_summary_v4.json")
DEFAULT_PAYLOAD_MANIFEST = Path("results/phase3/irc_cmpo/payload_manifest_final_prequeue_v3.csv")


def generate_approved_commands(
    final_summary: Mapping[str, Any],
    payload_paths: Mapping[str, str | Path],
    *,
    config_path: str | Path = DEFAULT_CONFIG,
) -> list[str]:
    """Return only the three paid smoke commands after an offline YES gate.

    This function performs no QCi operation.  The separate integer runner still
    requires its explicit ``--execute`` switch when a human later runs a printed
    command.
    """

    readiness = str(final_summary.get("IRC_CMPO_READY_FOR_QCI", "NO")).upper()
    if readiness != "YES":
        raise ValueError("IRC-CMPO is not ready for QCi smoke commands")
    expected = ("toy", "reduced_ieee123", "full_ieee123")
    if set(payload_paths) != set(expected):
        raise ValueError(f"smoke payloads must be exactly {list(expected)}")
    commands: list[str] = []
    for name in expected:
        payload = shlex.quote(str(payload_paths[name]))
        output = shlex.quote(f"results/phase3/irc_cmpo/smoke/{name}")
        job_name = shlex.quote(f"phase3-irc-cmpo-smoke-{name}")
        config = shlex.quote(str(config_path))
        commands.append(
            " ".join(
                (
                    "python",
                    "scripts/phase3_run_qci_integer.py",
                    payload,
                    "--output-dir",
                    output,
                    "--num-samples 30",
                    "--relaxation-schedule 2",
                    "--job-name",
                    job_name,
                    "--job-tag phase3",
                    "--job-tag irc-cmpo",
                    f"--job-tag {name}",
                    "--max-total-num-levels 954",
                    f"--limit-source {config}",
                    "--execute",
                )
            )
        )
    return commands


def _energy(payload: Mapping[str, Any], values: Sequence[int]) -> float:
    by_name = {str(v["name"]): int(value) for v, value in zip(payload["variables"], values, strict=True)}
    return sum(
        float(term["coefficient"])
        * (1.0 if not term["powers"] else float(math.prod(by_name[name] ** int(power) for name, power in term["powers"].items())))
        for term in payload["polynomial_terms"]
    )


def _exact_optimum(payload: Mapping[str, Any]) -> dict[str, Any]:
    if len(payload["variables"]) > 12:
        raise ValueError("exact smoke reference is limited to reduced masters")
    best: tuple[float, tuple[int, ...], Any] | None = None
    for values in itertools.product((0, 1), repeat=len(payload["variables"])):
        try:
            portfolio = decode_native_sample(payload, values)
        except ValueError:
            continue
        candidate = (_energy(payload, values), tuple(values), portfolio)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise ValueError("smoke master has no exact coverage- and budget-feasible portfolio")
    return {"energy": best[0], "coordinates": list(best[1]), "selected_asset_keys": list(best[2].selected_asset_keys)}


def _toy_assets() -> tuple[IRCAsset, ...]:
    return tuple(
        IRCAsset(f"toy::{anchor}::{tech}", anchor, tech, cost)
        for anchor in ("north", "south")
        for tech, cost in (("pv", 4.0), ("bess", 5.0), ("dispatchable_generation", 3.0))
    )


def build_final_smoke_jobs(full_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build toy/reduced/full smoke payloads from a validated middle lambda."""

    toy_assets = _toy_assets()
    toy_constraints = [
        {
            "coefficient": 2.0,
            "asset_keys": [asset.asset_key for asset in toy_assets if asset.anchor_node == anchor],
            "pattern": [0, 0, 0],
            "anchor_node": anchor,
        }
        for anchor in ("north", "south")
    ]
    toy = build_scalarized_irc_master(
        toy_assets,
        cost_weight=0.1,
        surrogate_terms=[
            {"coefficient": coefficient, "asset_keys": [asset.asset_key]}
            for coefficient, asset in zip(
                (-1.0, -0.5, -2.0, -1.0, -0.5, -2.0), toy_assets, strict=True
            )
        ],
        local_feasibility_terms=toy_constraints,
    )

    catalog = list(full_payload["catalog_assets"])
    anchors = sorted({str(asset["anchor_node"]) for asset in catalog})[:3]
    reduced_assets = [asset for asset in catalog if str(asset["anchor_node"]) in anchors]
    reduced_keys = {str(asset["asset_key"]) for asset in reduced_assets}
    reduced_names = {f"y::{key}" for key in reduced_keys}
    reduced = deepcopy(dict(full_payload))
    reduced["schema"] = "cmpo.irc_cmpo.scalarized_integer_master.reduced_smoke.v1"
    reduced["variables"] = [
        variable
        for variable in full_payload["variables"]
        if str(variable["physical_asset_key"]) in reduced_keys
    ]
    reduced["catalog_assets"] = reduced_assets
    reduced["polynomial_terms"] = [
        term
        for term in full_payload["polynomial_terms"]
        if set(map(str, term.get("powers", {}))) <= reduced_names
    ]
    reduced["local_feasibility_constraints"] = [
        constraint
        for constraint in full_payload.get("local_feasibility_constraints", ())
        if set(map(str, constraint["asset_keys"])) <= reduced_keys
    ]
    reduced["num_variables"] = len(reduced["variables"])
    reduced["num_levels"] = [2] * reduced["num_variables"]
    degrees = [int(term["degree"]) for term in reduced["polynomial_terms"]]
    reduced["min_degree"] = min(degrees)
    reduced["max_degree"] = max(degrees)
    reduced["coefficient_audit"] = audit_coefficients(
        reduced["polynomial_terms"], collapsed_threshold=1e-12
    ).to_dict()

    jobs = []
    for name, test, payload, exact in (
        ("toy", "A", toy, True),
        ("reduced_ieee123", "B", reduced, True),
        ("full_ieee123", "C", deepcopy(dict(full_payload)), False),
    ):
        jobs.append(
            {
                "name": name,
                "test": test,
                "num_samples": 30,
                "payload": payload,
                "known_exact_optimum": _exact_optimum(payload) if exact else None,
            }
        )
    return jobs


def build_smoke_jobs(
    *,
    assets: Sequence[IRCAsset],
    full_assets: Sequence[IRCAsset],
    budget: float,
    surrogate_terms: Sequence[Mapping[str, Any]],
    lagrange_lambda: float,
    coverage_rho: float = 2.0,
) -> list[dict[str, Any]]:
    toy_assets = _toy_assets()
    toy_terms = [
        {"coefficient": coefficient, "asset_keys": [asset.asset_key]}
        for coefficient, asset in zip((-1.0, -0.5, -2.0, -1.0, -0.5, -2.0), toy_assets, strict=True)
    ]
    toy = build_irc_master(toy_assets, budget=6.0, lagrange_lambda=0.1, surrogate_terms=toy_terms, coverage_rho=coverage_rho)
    anchors = sorted({asset.anchor_node for asset in assets})[:3]
    reduced_assets = tuple(asset for asset in assets if asset.anchor_node in anchors)
    reduced_keys = {asset.asset_key for asset in reduced_assets}
    reduced_terms = [term for term in surrogate_terms if set(term.get("asset_keys", ())) <= reduced_keys]
    reduced_budget = min(float(budget), sum(max(row.total_cost for row in reduced_assets if row.anchor_node == anchor) for anchor in anchors))
    minimum_reduced = sum(min(row.total_cost for row in reduced_assets if row.anchor_node == anchor) for anchor in anchors)
    reduced_budget = max(reduced_budget, minimum_reduced)
    reduced = build_irc_master(
        reduced_assets,
        budget=reduced_budget,
        lagrange_lambda=lagrange_lambda,
        surrogate_terms=reduced_terms,
        coverage_rho=coverage_rho,
    )
    full = build_irc_master(
        full_assets,
        budget=budget,
        lagrange_lambda=lagrange_lambda,
        surrogate_terms=surrogate_terms,
        coverage_rho=coverage_rho,
    )
    if not surrogate_terms:
        raise ValueError("full IRC-CMPO smoke payload requires a fitted recourse surrogate")
    for name, payload in (("toy", toy), ("reduced_ieee123", reduced), ("full_ieee123", full)):
        if not payload["coefficient_audit"]["passed"]:
            raise ValueError(f"{name} smoke payload fails coefficient dynamic-range audit")
    return [
        {"name": "toy", "test": "A", "num_samples": 30, "payload": toy, "known_exact_optimum": _exact_optimum(toy)},
        {"name": "reduced_ieee123", "test": "B", "num_samples": 30, "payload": reduced, "known_exact_optimum": _exact_optimum(reduced)},
        {"name": "full_ieee123", "test": "C", "num_samples": 30, "payload": full, "known_exact_optimum": None},
    ]


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--surrogate", help="Legacy hard-budget smoke input; no longer required.")
    parser.add_argument("--final-summary", default=str(DEFAULT_FINAL_SUMMARY))
    parser.add_argument("--payload-manifest", default=str(DEFAULT_PAYLOAD_MANIFEST))
    parser.add_argument("--output-dir")
    parser.add_argument("--execute", action="store_true", help="Submit exactly A/B/C with strict-stop gates.")
    args = parser.parse_args()
    config = yaml.safe_load(_resolve(args.config).read_text(encoding="utf-8"))
    if args.execute and not bool(config.get("qci", {}).get("submission_permitted", False)):
        raise SystemExit(
            "QCi submission is disabled by the final pre-queue configuration; "
            "use only commands emitted after IRC_CMPO_READY_FOR_QCI=YES"
        )
    summary = json.loads(_resolve(args.final_summary).read_text(encoding="utf-8"))
    if str(summary.get("IRC_CMPO_READY_FOR_QCI", "NO")).upper() != "YES":
        raise SystemExit("final offline gate is not YES; no QCi smoke job may be planned")
    manifest = __import__("pandas").read_csv(_resolve(args.payload_manifest)).sort_values(
        "lambda_index"
    )
    if len(manifest) != 6:
        raise SystemExit("final smoke planning requires the six validated lambda payloads")
    middle = manifest.iloc[3]
    full_payload = json.loads(Path(middle["scaled_payload_path"]).read_text(encoding="utf-8"))
    jobs = build_final_smoke_jobs(full_payload)
    output = _resolve(args.output_dir or Path(config["output_dir"]) / "smoke")
    if not args.execute:
        output.mkdir(parents=True, exist_ok=True)
        payload_dir = output / "payloads_final_prequeue_v4"
        payload_dir.mkdir(parents=True, exist_ok=True)
        payload_paths: dict[str, Path] = {}
        for job in jobs:
            payload_path = payload_dir / f"{job['name']}.json"
            with payload_path.open("x", encoding="utf-8") as handle:
                json.dump(job["payload"], handle, indent=2, sort_keys=True)
                handle.write("\n")
            payload_paths[str(job["name"])] = payload_path
        path = output / "smoke_plan_final_prequeue_v4.json"
        with path.open("x", encoding="utf-8") as handle:
            json.dump(
                {
                    "jobs": jobs,
                    "approved_commands": generate_approved_commands(summary, payload_paths),
                    "qci_jobs_submitted": 0,
                    "full_experiment_run": False,
                },
                handle,
                indent=2,
            )
        print(
            json.dumps(
                {
                    "planned_jobs": [job["name"] for job in jobs],
                    "approved_commands": generate_approved_commands(summary, payload_paths),
                    "qci_jobs_submitted": 0,
                },
                indent=2,
            )
        )
        return
    from cmpo.qci_client_adapter import _client_from_environment, validate_qci_environment
    from cmpo.qci_integer_adapter import (
        build_integer_job_body,
        installed_qci_versions,
        native_integer_samples,
        validate_integer_response,
    )

    validate_qci_environment()
    client = _client_from_environment()
    allocation = client.get_allocations().get("allocations", {}).get("dirac", {})
    if not isinstance(allocation, Mapping):
        raise SystemExit("QCi Dirac allocation record is unavailable; no smoke job submitted")
    if allocation.get("metered", True) and float(allocation.get("seconds", 0.0)) <= 0.0:
        raise SystemExit("QCi Dirac allocation has no remaining seconds; no smoke job submitted")

    def write_new(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")

    def submit(job: Mapping[str, Any]) -> dict[str, Any]:
        payload = job["payload"]
        from cmpo.qci_client_adapter import convert_cmpo_payload_to_qci_file
        qci_file = convert_cmpo_payload_to_qci_file(payload)
        versions = installed_qci_versions()
        file_response = client.upload_file(file=qci_file)
        job_body = build_integer_job_body(
            client,
            polynomial_file_id=str(file_response["file_id"]),
            job_name=f"phase3-irc-cmpo-smoke-{job['name']}",
            job_tags=["phase3", "irc-cmpo", "smoke", str(job["name"])],
            num_samples=30,
            relaxation_schedule=int(config["qci"]["relaxation_schedule"]),
            num_levels=payload["num_levels"],
            max_total_num_levels=int(config["qci"]["maximum_total_num_levels"]),
            limit_source=str(config["qci"]["num_levels_limit_source"]),
        )
        job_dir = output / str(job["name"])
        write_new(
            job_dir / "transport_request.json",
            {
                "qci_file": qci_file,
                "file_response": file_response,
                "job_body": job_body,
                "requested_job_type": "sample-hamiltonian-integer",
                "requested_job_params": {
                    "device_type": "dirac-3",
                    "num_samples": 30,
                    "relaxation_schedule": int(config["qci"]["relaxation_schedule"]),
                    "num_levels": list(payload["num_levels"]),
                },
                "allocation_before_submission": dict(allocation),
                "versions": versions,
                "num_levels_limit_source": str(config["qci"]["num_levels_limit_source"]),
            },
        )
        raw_response = client.process_job(job_body=job_body)
        write_new(job_dir / "raw_server_response.json", raw_response)
        validation = validate_integer_response(raw_response, expected_num_levels=payload["num_levels"])
        samples = (
            native_integer_samples(raw_response, expected_num_levels=payload["num_levels"])
            if validation.valid
            else []
        )
        coverage_feasible = []
        combined_feasible = []
        exact_budget_count = 0
        energies = []
        for sample in samples:
            try:
                coverage_feasible.append(decode_native_sample(payload, sample, require_budget=False))
            except ValueError:
                pass
            selected_cost = math.fsum(
                float(asset["total_cost"])
                for variable, asset, value in zip(
                    payload["variables"], payload["catalog_assets"], sample, strict=True
                )
                if int(value) == 1 and variable["physical_asset_key"] == asset["asset_key"]
            )
            if selected_cost <= float(payload["exact_budget_constraint"]["amount_dollars"]) + 1e-9:
                exact_budget_count += 1
            try:
                combined_feasible.append(decode_native_sample(payload, sample))
                energies.append(_energy(payload, sample))
            except ValueError:
                pass
        optimum = job.get("known_exact_optimum")
        optimum_found = optimum is None or any(list(sample) == optimum["coordinates"] for sample in samples)
        competitive = optimum is None or (energies and min(energies) <= float(optimum["energy"]) + 1e-8)
        budget_gate = job["name"] == "toy" or exact_budget_count > 0
        passed = bool(
            validation.valid
            and coverage_feasible
            and budget_gate
            and (job["name"] != "toy" or optimum_found)
            and (job["name"] != "reduced_ieee123" or competitive)
        )
        return {
            "qci_file": qci_file,
            "file_response": file_response,
            "job_body": job_body,
            "requested_job_type": "sample-hamiltonian-integer",
            "response": raw_response,
            "validation": validation,
            "versions": versions,
            "passed": passed,
            "job_id": raw_response.get("job_info", {}).get("job_id"),
            "raw_returned_count": validation.native_sample_count,
            "native_integer_in_domain_count": validation.native_integer_in_domain_count,
            "native_coverage_feasible_count": len(coverage_feasible),
            "native_exact_budget_feasible_count": exact_budget_count,
            "native_combined_feasible_count": len(combined_feasible),
            "native_feasible_rate": len(combined_feasible) / max(validation.native_sample_count, 1),
            "optimum_found": optimum_found,
            "competitive_with_exact_optimum": competitive,
            "projection_used": False,
        }

    results = run_three_job_smoke(jobs, submit, output_dir=output)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
