"""Deterministic budget-targeted Lagrangian and strict smoke orchestration."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from statistics import median
from typing import Any, Callable, Mapping, Sequence

from cmpo.irc_cmpo_decode import NativePortfolio, decode_native_sample


@dataclass(frozen=True)
class LambdaIteration:
    iteration: int
    lagrange_lambda: float
    raw_sample_count: int
    native_integer_coverage_count: int
    exact_budget_feasible_count: int
    median_cost: float | None
    best_cost: float | None
    over_budget_fraction: float
    decision: str


@dataclass(frozen=True)
class LambdaSearchResult:
    trajectory: tuple[LambdaIteration, ...]
    feasible_portfolios: tuple[NativePortfolio, ...]


def target_budget(
    payload_factory: Callable[[float], Mapping[str, Any]],
    sampler: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any] | Sequence[Any]]],
    *,
    bracket: tuple[float, float],
    max_iterations: int = 5,
    underuse_fraction: float = 0.98,
) -> LambdaSearchResult:
    """Target real-dollar budget utilization without modifying native samples."""

    if not 1 <= max_iterations <= 5:
        raise ValueError("IRC-CMPO lambda search must use between one and five iterations")
    lower, upper = map(float, bracket)
    if lower < 0.0 or not lower < upper or not all(map(math.isfinite, (lower, upper))):
        raise ValueError("lambda bracket must be finite, nonnegative, and increasing")
    trajectory: list[LambdaIteration] = []
    feasible_by_signature: dict[str, NativePortfolio] = {}
    for iteration in range(1, max_iterations + 1):
        value = (lower + upper) / 2.0
        payload = payload_factory(value)
        budget = float(payload["exact_budget_constraint"]["amount_dollars"])
        raw_samples = list(sampler(payload))
        decoded: list[NativePortfolio] = []
        for sample in raw_samples:
            try:
                portfolio = decode_native_sample(payload, sample, require_budget=False)
            except ValueError:
                continue
            decoded.append(portfolio)
            if portfolio.total_cost <= budget + 1e-9:
                feasible_by_signature.setdefault(portfolio.signature, portfolio)
        costs = [item.total_cost for item in decoded]
        over_fraction = (
            sum(cost > budget + 1e-9 for cost in costs) / len(costs) if costs else 1.0
        )
        median_cost = median(costs) if costs else None
        best_cost = min(costs) if costs else None
        if over_fraction > 0.5:
            decision = "increase_lambda"
            lower = value
        elif median_cost is not None and median_cost < underuse_fraction * budget:
            decision = "decrease_lambda"
            upper = value
        else:
            decision = "target_reached"
        trajectory.append(
            LambdaIteration(
                iteration,
                value,
                len(raw_samples),
                len(decoded),
                sum(cost <= budget + 1e-9 for cost in costs),
                median_cost,
                best_cost,
                over_fraction,
                decision,
            )
        )
        if decision == "target_reached":
            break
    ordered = tuple(
        sorted(feasible_by_signature.values(), key=lambda item: (-item.total_cost, item.signature))
    )
    return LambdaSearchResult(tuple(trajectory), ordered)


class SmokeGateFailure(RuntimeError):
    pass


def _write_new_json(path: Path, value: Any) -> None:
    def encode(item: Any) -> Any:
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, Path):
            return str(item)
        raise TypeError(f"{type(item).__name__} is not JSON serializable")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, default=encode)
        handle.write("\n")


def run_three_job_smoke(
    jobs: Sequence[Mapping[str, Any]],
    submit: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    output_dir: Path | str,
) -> list[dict[str, Any]]:
    """Run only A/B/C, preserving artifacts and stopping on the first failed gate."""

    expected = ["toy", "reduced_ieee123", "full_ieee123"]
    names = [str(job.get("name")) for job in jobs]
    if names != expected:
        raise ValueError(f"smoke suite must contain exactly {expected}")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "schema": "cmpo.irc_cmpo.smoke.v1",
        "planned_jobs": expected,
        "completed_jobs": [],
        "failed_job": None,
        "job_records": [],
        "strict_stop": True,
        "full_experiment_run": False,
    }
    for job in jobs:
        name = str(job["name"])
        _write_new_json(output / name / "request.json", dict(job))
        try:
            response = dict(submit(job))
        except Exception as exc:
            response = {
                "passed": False,
                "transport_exception": type(exc).__name__,
                "error": str(exc),
            }
            _write_new_json(output / name / "response.json", response)
            manifest["failed_job"] = name
            manifest["transport_exception"] = response
            _write_new_json(output / "smoke_manifest.json", manifest)
            raise SmokeGateFailure(
                f"IRC-CMPO smoke transport failed for {name}; no later job submitted"
            ) from exc
        _write_new_json(output / name / "response.json", response)
        results.append(response)
        if response.get("versions"):
            manifest["versions"] = response["versions"]
        manifest["job_records"].append(
            {
                "name": name,
                "job_id": response.get("job_id"),
                "passed": bool(response.get("passed", False)),
                "raw_returned_count": response.get("raw_returned_count"),
                "native_integer_in_domain_count": response.get("native_integer_in_domain_count"),
                "native_coverage_feasible_count": response.get("native_coverage_feasible_count"),
                "native_exact_budget_feasible_count": response.get("native_exact_budget_feasible_count"),
                "native_combined_feasible_count": response.get("native_combined_feasible_count"),
            }
        )
        if not bool(response.get("passed", False)):
            manifest["failed_job"] = name
            _write_new_json(output / "smoke_manifest.json", manifest)
            raise SmokeGateFailure(f"IRC-CMPO smoke gate failed for {name}; no later job submitted")
        manifest["completed_jobs"].append(name)
    _write_new_json(output / "smoke_manifest.json", manifest)
    return results
