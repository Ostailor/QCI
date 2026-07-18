#!/usr/bin/env python
"""Decode, evaluate, compare, and report the IEEE123 global budget-master V2 run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
import pandas as pd
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_frontier import frontier_hypervolume, pareto_frontier  # noqa: E402
from cmpo.budget_master_recourse import (  # noqa: E402
    fix_portfolio_across_patches,
    run_fixed_portfolio_consensus,
)
from cmpo.classical_budget_masters import solve_classical_master  # noqa: E402
from cmpo.full_system_dispatch import (  # noqa: E402
    evaluate_full_system,
    evaluate_full_system_heldout,
)
from cmpo.portfolio_decode import (  # noqa: E402
    DecodedPortfolio,
    decode_challenge_aligned_sample,
)
from cmpo.portfolio_diversity import (  # noqa: E402
    ScoredPortfolio,
    hamming_distance,
    select_scored_diverse_portfolios,
)
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml")
DEFAULT_RAW = Path("results/phase3/sc_cmpo/budget_master_v2/qci")
QCI_METHOD = "QCi global budget master V2"
RECOURSE_EVALUATOR = "ieee123_global_master_shared_recourse_v2"


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _write_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _job_id(response: Mapping[str, Any], request: Mapping[str, Any]) -> str:
    return str(
        response.get("job_id")
        or response.get("job_info", {}).get("job_id")
        or request.get("submit_response", {}).get("job_id")
        or ""
    )


def _job_status(response: Mapping[str, Any]) -> str:
    return str(
        response.get("status")
        or response.get("job_status")
        or response.get("job_info", {}).get("status")
        or "UNKNOWN"
    )


def _solutions(response: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    results = response.get("results") or {}
    return (
        list(results.get("solutions") or results.get("samples") or []),
        list(results.get("energies") or results.get("energy") or []),
    )


def _raw_map(payload: Mapping[str, Any], sample: Mapping[str, Any] | Sequence[float]) -> dict[str, float]:
    names = [str(variable["name"]) for variable in payload["variables"]]
    if isinstance(sample, Mapping):
        return {name: float(sample.get(name, 0.0)) for name in names}
    return {
        name: float(sample[index]) if index < len(sample) else 0.0
        for index, name in enumerate(names)
    }


def _candidate_scores(
    payload: Mapping[str, Any],
    sample: Mapping[str, Any] | Sequence[float],
    portfolio: DecodedPortfolio,
) -> tuple[float, float, float, float]:
    values = _raw_map(payload, sample)
    critical = float(values.get("critical_service_target", 0.0) > 0.5)
    reserve_values = [
        values.get("reserve_level_low", 0.0),
        values.get("reserve_level_medium", 0.0),
        values.get("reserve_level_high", 0.0),
    ]
    reserve = (0.0, 0.5, 1.0)[int(max(range(3), key=lambda index: reserve_values[index]))]
    scenario_bits = [
        float(value > 0.5)
        for name, value in values.items()
        if name.startswith("scenario_response::")
    ]
    dispatchable = sum(
        float(row.get("installed_capacity_kw", 0.0))
        for row in portfolio.upgrade_rows
        if row.get("technology") == "dispatchable_generation"
    )
    estimated_recourse = sum(scenario_bits) + math.log1p(dispatchable) / 10.0
    utilization = portfolio.total_upgrade_cost / max(portfolio.actual_budget, 1.0)
    return critical, reserve, estimated_recourse, utilization


def decode_qci_results(
    raw_dir: Path,
    *,
    expected_jobs: int,
    samples_per_job: int,
    retain_per_budget: int,
) -> tuple[list[dict[str, Any]], dict[str, list[ScoredPortfolio]], dict[str, Any]]:
    requests = sorted(raw_dir.glob("**/request.json"))
    responses = sorted(raw_dir.glob("**/response.json"))
    if len(requests) != expected_jobs or len(responses) != expected_jobs:
        raise ValueError(
            f"QCi raw set incomplete: requests={len(requests)}, responses={len(responses)}, expected={expected_jobs}"
        )
    status_path = raw_dir / "job_status.csv"
    if not status_path.is_file():
        raise FileNotFoundError(f"QCi job status ledger is missing: {status_path}")
    with status_path.open(newline="", encoding="utf-8") as handle:
        status_rows = list(csv.DictReader(handle))
    if len(status_rows) != expected_jobs:
        raise ValueError(
            f"QCi status ledger has {len(status_rows)} rows, expected {expected_jobs}"
        )
    runtime_by_job = {
        str(row["job_id"]): float(row.get("runtime_seconds") or 0.0)
        for row in status_rows
        if str(row.get("job_id", ""))
    }
    response_by_dir = {path.parent: path for path in responses}
    rows: list[dict[str, Any]] = []
    grouped: dict[str, list[ScoredPortfolio]] = defaultdict(list)
    completed = 0
    failed = 0
    returned_samples = 0
    seen_job_ids: set[str] = set()
    for request_path in requests:
        response_path = response_by_dir.get(request_path.parent)
        if response_path is None:
            raise FileNotFoundError(f"missing response for {request_path}")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        status = _job_status(response).upper()
        job_id = _job_id(response, request)
        if not job_id or job_id in seen_job_ids:
            raise ValueError(f"missing or duplicate QCi job ID at {response_path}")
        seen_job_ids.add(job_id)
        if status in {"COMPLETED", "COMPLETE"}:
            completed += 1
        else:
            failed += 1
        ledger_runtime = runtime_by_job.get(job_id, 0.0)
        device_runtime = float(
            response.get("job_info", {}).get("job_result", {}).get("device_usage_s", 0.0)
            or 0.0
        )
        qci_runtime = ledger_runtime if ledger_runtime > 0.0 else device_runtime
        payload_path = _resolve(request["payload_path"])
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        budget_id = str(payload["budget_constraint"]["budget_id"])
        solutions, energies = _solutions(response)
        device_config = (
            response.get("job_info", {})
            .get("job_submission", {})
            .get("device_config", {})
            .get("dirac-3_normalized_qudit", {})
        )
        effective_sum_constraint = device_config.get("sum_constraint", "unavailable")
        if status in {"COMPLETED", "COMPLETE"} and len(solutions) != samples_per_job:
            raise ValueError(
                f"completed QCi job {job_id} returned {len(solutions)} samples, expected {samples_per_job}"
            )
        returned_samples += len(solutions)
        for sample_index, sample in enumerate(solutions):
            energy = float(energies[sample_index]) if sample_index < len(energies) else math.nan
            base = {
                "source": "QCi",
                "budget_id": budget_id,
                "budget": float(payload["budget_constraint"]["amount"]),
                "job_id": job_id,
                "repeat_start": int(request.get("repeat_start", 0)),
                "sample_index": sample_index,
                "global_sample_index": int(request.get("repeat_start", 0)) + sample_index,
                "native_qci_energy": energy,
                "raw_sample_sum": math.fsum(_raw_map(payload, sample).values()),
                "qci_effective_sum_constraint": effective_sum_constraint,
                "request_path": str(request_path.relative_to(ROOT)),
                "response_path": str(response_path.relative_to(ROOT)),
                "payload_path": str(payload_path.relative_to(ROOT)),
                "job_status": status,
                "qci_job_runtime_seconds": qci_runtime,
                "admission_status": "rejected",
                "retained": False,
            }
            try:
                portfolio, diagnostics = decode_challenge_aligned_sample(
                    payload, sample, energy=energy
                )
                critical, reserve, recourse, utilization = _candidate_scores(
                    payload, sample, portfolio
                )
                candidate = ScoredPortfolio(
                    portfolio,
                    critical_service_proxy=critical,
                    reserve_preparedness=reserve,
                    estimated_recourse_score=recourse,
                    upgrade_utilization=utilization,
                    provenance={
                        "job_id": job_id,
                        "sample_index": sample_index,
                        "global_sample_index": base["global_sample_index"],
                        "request_path": base["request_path"],
                        "response_path": base["response_path"],
                        "runtime_seconds": base["qci_job_runtime_seconds"],
                    },
                )
                grouped[budget_id].append(candidate)
                rows.append(
                    base
                    | diagnostics
                    | {
                        "admission_status": (
                            "native_feasible"
                            if diagnostics["raw_one_hot_valid"]
                            and diagnostics["raw_coverage_valid"]
                            and diagnostics["raw_pairwise_budget_valid"]
                            and diagnostics["coverage_repair_count"] == 0
                            else "projected_feasible"
                        ),
                        "rejection_reason": "",
                        "portfolio_signature": portfolio.signature,
                        "selected_asset_keys": json.dumps(portfolio.selected_asset_keys),
                        "selected_asset_count": len(portfolio.selected_asset_keys),
                        "total_upgrade_cost": portfolio.total_upgrade_cost,
                        "encoded_upgrade_cost": portfolio.encoded_upgrade_cost,
                        "encoded_budget": portfolio.encoded_budget,
                        "critical_service_proxy": critical,
                        "reserve_preparedness": reserve,
                        "estimated_recourse_score": recourse,
                        "upgrade_utilization": utilization,
                    }
                )
            except (KeyError, TypeError, ValueError) as exc:
                rows.append(base | {"rejection_reason": str(exc)})

    selected: dict[str, list[ScoredPortfolio]] = {}
    for budget_id, candidates in grouped.items():
        chosen = select_scored_diverse_portfolios(candidates, limit=retain_per_budget)
        selected[budget_id] = chosen
        for rank, candidate in enumerate(chosen, start=1):
            provenance = candidate.provenance
            for row in rows:
                if (
                    row["job_id"] == provenance["job_id"]
                    and row["budget_id"] == budget_id
                    and int(row["sample_index"]) == int(provenance["sample_index"])
                ):
                    row["retained"] = True
                    row["retained_rank"] = rank
                    break
    summary = {
        "completed_qci_jobs": completed,
        "failed_qci_jobs": failed,
        "returned_samples": returned_samples,
        "raw_one_hot_valid_sample_count": sum(
            bool(row.get("raw_one_hot_valid", False)) for row in rows
        ),
        "raw_coverage_valid_sample_count": sum(
            bool(row.get("raw_coverage_valid", False)) for row in rows
        ),
        "raw_pairwise_budget_valid_sample_count": sum(
            bool(row.get("raw_pairwise_budget_valid", False)) for row in rows
        ),
        "challenge_projection_repaired_sample_count": sum(
            int(row.get("coverage_repair_count", 0) or 0) > 0 for row in rows
        ),
        "unique_feasible_portfolios_per_budget": {
            budget_id: len({candidate.portfolio.signature for candidate in candidates})
            for budget_id, candidates in sorted(grouped.items())
        },
        "retained_portfolios_per_budget": {
            budget_id: len(candidates) for budget_id, candidates in sorted(selected.items())
        },
    }
    return rows, selected, summary


def _patch_payloads(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    directory = _resolve(config["source_payload_dir"])
    payloads = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }
    if len(payloads) != 12:
        raise ValueError(f"shared recourse requires exactly 12 patches, found {len(payloads)}")
    return payloads


def _evaluate_portfolio(
    *,
    method: str,
    portfolio: DecodedPortfolio,
    master_runtime: float,
    master_backend: str,
    master_metadata: Mapping[str, Any],
    portfolio_rank: int,
    payloads: Mapping[str, Mapping[str, Any]],
    grid: Any,
    trace_dir: Path,
    provenance: Mapping[str, Any],
    heldout_limit: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fixed = fix_portfolio_across_patches(portfolio, payloads)
    consensus, patch_values = run_fixed_portfolio_consensus(
        portfolio, payloads, fixed, method=method
    )
    system = evaluate_full_system(method, grid, payloads, patch_values, consensus)
    heldout = evaluate_full_system_heldout(
        method, grid, payloads, patch_values, consensus, limit=heldout_limit
    )
    if system.get("status") != "completed" or heldout.get("status") != "completed":
        raise ValueError(
            f"shared recourse failed for {method}/{portfolio.budget_id}/{portfolio.signature}: "
            f"system={system.get('status')} heldout={heldout.get('status')}"
        )
    metrics = dict(system["system_metrics"])
    heldout_metrics = dict(heldout["heldout_summary"])
    reconstructed_cost = float(metrics["total_upgrade_cost"])
    if reconstructed_cost > portfolio.actual_budget + 1e-6:
        raise ValueError("reconstructed system plan exceeds its actual dollar budget")
    safe_method = hashlib.sha256(method.encode("utf-8")).hexdigest()[:10]
    trace_path = trace_dir / (
        f"{portfolio.budget_id}__{safe_method}__rank_{portfolio_rank:02d}__{portfolio.signature}.json"
    )
    consensus_json = json.dumps(_json_safe(consensus), sort_keys=True, separators=(",", ":"))
    consensus_summary = {
        key: consensus.get(key)
        for key in (
            "status",
            "converged",
            "benchmark",
            "method",
            "payload_count",
            "solution_row_count",
            "consensus_key_count",
            "local_copy_count",
            "tolerance",
            "rho",
            "iteration_count",
            "primal_residual",
            "dual_residual",
            "consensus_residual",
            "raw_conflict_count",
            "unresolved_conflicts",
            "consensus_trace_id",
            "fixed_portfolio_excluded_from_patch_admm",
            "upgrade_cost_charged_once",
        )
    }
    consensus_summary["complete_consensus_sha256"] = hashlib.sha256(
        consensus_json.encode("utf-8")
    ).hexdigest()
    trace = {
        "schema": "cmpo.budget_master_v2.system_trace",
        "method": method,
        "budget_id": portfolio.budget_id,
        "budget": portfolio.actual_budget,
        "portfolio_rank": portfolio_rank,
        "portfolio_signature": portfolio.signature,
        "portfolio": {
            "selected_asset_keys": list(portfolio.selected_asset_keys),
            "total_upgrade_cost": portfolio.total_upgrade_cost,
            "encoded_upgrade_cost": portfolio.encoded_upgrade_cost,
            "encoded_budget": portfolio.encoded_budget,
            "native_master_energy": portfolio.energy,
        },
        "master_backend": master_backend,
        "master_runtime_seconds": master_runtime,
        "master_metadata": _json_safe(dict(master_metadata)),
        "provenance": _json_safe(dict(provenance)),
        "recourse_contract": {
            "patch_count": len(payloads),
            "training_scenario_count": int(metrics["scenario_count"]),
            "heldout_n_1_count": int(heldout_metrics["heldout_count"]),
            "consensus_algorithm": "overlap_consensus_admm",
            "projection": "full_public_system_active_power",
            "recourse_evaluator": RECOURSE_EVALUATOR,
        },
        "consensus": consensus_summary,
        "system": system,
        "heldout": heldout,
    }
    trace_path.write_text(json.dumps(_json_safe(trace), indent=2), encoding="utf-8")
    relative_trace = str(trace_path.relative_to(ROOT))
    common = {
        "method": method,
        "budget_id": portfolio.budget_id,
        "budget": portfolio.actual_budget,
        "portfolio_rank": portfolio_rank,
        "portfolio_signature": portfolio.signature,
        "selected_asset_count": len(portfolio.selected_asset_keys),
        "selected_asset_keys": json.dumps(portfolio.selected_asset_keys),
        "total_upgrade_cost": portfolio.total_upgrade_cost,
        "reconstructed_upgrade_cost": reconstructed_cost,
        "budget_utilization": portfolio.total_upgrade_cost / max(portfolio.actual_budget, 1.0),
        "feasibility": bool(metrics["full_system_feasibility"]),
        "native_master_energy": portfolio.energy,
        "master_runtime_seconds": master_runtime,
        "master_backend": master_backend,
        "recourse_evaluator": RECOURSE_EVALUATOR,
        "trace_path": relative_trace,
        "system_trace_id": metrics["system_trace_id"],
    }
    system_row = common | {
        "critical_ens": float(metrics["critical_energy_not_served_kwh"]),
        "total_ens": float(metrics["total_energy_not_served_kwh"]),
        "critical_load_served_fraction": float(metrics["critical_load_served_fraction"]),
        "max_fraction_customers_unserved_per_hour": float(
            metrics["max_fraction_customers_unserved_per_hour"]
        ),
        "critical_infrastructure_outage_hours": float(
            metrics["total_hours_critical_infrastructure_unserved"]
        ),
        "runtime_seconds": master_runtime + float(metrics["runtime_seconds"]),
    }
    heldout_row = common | {
        "heldout_critical_ens": float(heldout_metrics["critical_energy_not_served_kwh"]),
        "heldout_total_ens": float(heldout_metrics["total_energy_not_served_kwh"]),
        "heldout_critical_load_served_fraction": float(
            heldout_metrics["critical_load_served_fraction"]
        ),
        "heldout_max_fraction_customers_unserved_per_hour": float(
            heldout_metrics["max_fraction_customers_unserved_per_hour"]
        ),
        "heldout_critical_infrastructure_outage_hours": float(
            heldout_metrics["total_hours_critical_infrastructure_unserved"]
        ),
        "heldout_contingency_count": int(heldout_metrics["heldout_count"]),
    }
    return system_row, heldout_row


def _headline_rows(system: pd.DataFrame, heldout: pd.DataFrame) -> pd.DataFrame:
    merged = system.merge(
        heldout[
            [
                "method",
                "budget_id",
                "portfolio_signature",
                "heldout_critical_ens",
                "heldout_total_ens",
                "heldout_critical_load_served_fraction",
            ]
        ],
        on=["method", "budget_id", "portfolio_signature"],
        how="inner",
        validate="one_to_one",
    )
    rows = []
    for (_method, _budget), group in merged.groupby(["method", "budget_id"], sort=True):
        ordered = group.sort_values(
            [
                "feasibility",
                "critical_ens",
                "total_ens",
                "max_fraction_customers_unserved_per_hour",
                "heldout_total_ens",
                "total_upgrade_cost",
                "portfolio_rank",
            ],
            ascending=[False, True, True, True, True, True, True],
        )
        rows.append(ordered.iloc[0])
    return pd.DataFrame(rows).reset_index(drop=True)


def _win_tie_loss(headline: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in ("total_ens", "critical_ens", "heldout_total_ens"):
        for budget_id, group in headline.groupby("budget_id", sort=True):
            qci = group[group["method"] == QCI_METHOD]
            classical = group[group["method"] != QCI_METHOD]
            if len(qci) != 1 or classical.empty:
                raise ValueError(f"incomplete method coverage at budget {budget_id}")
            qci_value = float(qci.iloc[0][metric])
            best_value = float(classical[metric].min())
            best_methods = ";".join(
                sorted(classical.loc[classical[metric] == best_value, "method"].astype(str))
            )
            tolerance = max(1e-9, 1e-9 * max(abs(qci_value), abs(best_value), 1.0))
            outcome = (
                "win"
                if qci_value < best_value - tolerance
                else "loss"
                if qci_value > best_value + tolerance
                else "tie"
            )
            rows.append(
                {
                    "budget_id": budget_id,
                    "budget": float(qci.iloc[0]["budget"]),
                    "metric": metric,
                    "qci_value": qci_value,
                    "best_classical_value": best_value,
                    "best_classical_methods": best_methods,
                    "outcome": outcome,
                }
            )
    return pd.DataFrame(rows)


def _frontiers(headline: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    frames = []
    hypervolumes: dict[str, dict[str, float]] = {}
    for objective, metric in (
        ("training_total_ens", "total_ens"),
        ("training_critical_ens", "critical_ens"),
        ("heldout_total_ens", "heldout_total_ens"),
    ):
        reference_cost = float(headline["budget"].max()) * 1.01
        reference_resilience = float(headline[metric].max()) * 1.01 + 1e-9
        hypervolumes[objective] = {}
        for method, group in headline.groupby("method", sort=True):
            frontier = pareto_frontier(
                group, cost_col="total_upgrade_cost", resilience_col=metric
            )
            volume = frontier_hypervolume(
                group,
                cost_col="total_upgrade_cost",
                resilience_col=metric,
                reference_cost=reference_cost,
                reference_resilience=reference_resilience,
            )
            hypervolumes[objective][method] = volume
            frames.append(
                frontier.assign(
                    frontier_objective=objective,
                    frontier_metric=metric,
                    method_hypervolume=volume,
                    hypervolume_reference_cost=reference_cost,
                    hypervolume_reference_resilience=reference_resilience,
                )
            )
    return pd.concat(frames, ignore_index=True), hypervolumes


def _plot_lines(
    frame: pd.DataFrame, metric: str, ylabel: str, path: Path, *, ylog: bool = False
) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    for method, group in frame.groupby("method", sort=True):
        ordered = group.sort_values("budget")
        ax.plot(ordered["budget"], ordered[metric], marker="o", linewidth=1.5, label=method)
    ax.set_xlabel("Hard upgrade budget ($)")
    ax.set_ylabel(ylabel)
    if ylog and (frame[metric] > 0).all():
        ax.set_yscale("log")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_diversity(
    selected: Mapping[str, Sequence[ScoredPortfolio]],
    unique_counts: Mapping[str, int],
    budgets: Mapping[str, float],
    path: Path,
) -> None:
    budget_ids = sorted(budgets, key=budgets.get)
    retained = [len(selected.get(budget_id, ())) for budget_id in budget_ids]
    unique = [int(unique_counts.get(budget_id, 0)) for budget_id in budget_ids]
    mean_hamming = []
    for budget_id in budget_ids:
        portfolios = [item.portfolio for item in selected.get(budget_id, ())]
        distances = [
            hamming_distance(left, right)
            for index, left in enumerate(portfolios)
            for right in portfolios[index + 1 :]
        ]
        mean_hamming.append(float(sum(distances) / len(distances)) if distances else 0.0)
    x = range(len(budget_ids))
    fig, ax = plt.subplots(figsize=(9.0, 5.5))
    ax.bar([value - 0.2 for value in x], unique, width=0.4, label="Unique feasible")
    ax.bar([value + 0.2 for value in x], retained, width=0.4, label="Retained")
    ax.set_ylabel("Portfolio count")
    ax.set_xticks(list(x), budget_ids, rotation=25, ha="right")
    twin = ax.twinx()
    twin.plot(list(x), mean_hamming, color="black", marker="D", label="Mean retained Hamming distance")
    twin.set_ylabel("Mean Hamming distance")
    ax.legend(loc="upper left")
    twin.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_native_vs_qubo(payloads: Mapping[str, Mapping[str, Any]], path: Path) -> None:
    rows = []
    for budget_id, payload in payloads.items():
        native = int(payload["model_statistics"]["variable_count"])
        cubic = sum(int(term.get("degree", 0)) == 3 for term in payload["polynomial_terms"])
        rows.append((budget_id, float(payload["budget_constraint"]["amount"]), native, native + cubic))
    rows.sort(key=lambda row: row[1])
    x = range(len(rows))
    fig, ax = plt.subplots(figsize=(9.0, 5.5))
    ax.bar([value - 0.2 for value in x], [row[2] for row in rows], width=0.4, label="Native degree-3 master")
    ax.bar([value + 0.2 for value in x], [row[3] for row in rows], width=0.4, label="Estimated quadratized size")
    ax.set_ylabel("Binary variables (native or estimated)")
    ax.set_xticks(list(x), [row[0] for row in rows], rotation=25, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_experiment(
    config_path: Path | str,
    *,
    raw_dir: Path | str = DEFAULT_RAW,
    output_dir: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config_file = _resolve(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    output = _resolve(output_dir or config["output_dir"])
    raw = _resolve(raw_dir)
    payload_paths = sorted((output / "qci_master_payloads").glob("*.json"))
    if len(payload_paths) != 6:
        raise ValueError(f"expected six global master payloads, found {len(payload_paths)}")
    payloads = {
        str(payload["budget_constraint"]["budget_id"]): payload
        for path in payload_paths
        for payload in [json.loads(path.read_text(encoding="utf-8"))]
    }
    plan = {
        "qci_submission_performed": False,
        "raw_dir": str(raw),
        "output_dir": str(output),
        "budget_count": len(payloads),
        "expected_qci_jobs": len(payloads) * 3,
        "samples_per_job": int(config["qci"]["samples_per_job"]),
        "retained_per_budget": int(config["recourse"]["top_unique_portfolios_per_budget"]),
        "classical_methods": list(config["classical_master_methods"]),
    }
    if dry_run:
        return {"dry_run": True, **plan}

    output.mkdir(parents=True, exist_ok=True)
    trace_dir = output / "system_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    decoded_rows, selected, qci_summary = decode_qci_results(
        raw,
        expected_jobs=plan["expected_qci_jobs"],
        samples_per_job=plan["samples_per_job"],
        retain_per_budget=plan["retained_per_budget"],
    )
    if set(selected) != set(payloads):
        missing = sorted(set(payloads) - set(selected))
        raise ValueError(f"no feasible retained QCi portfolio for budgets: {missing}")
    decoded_path = output / "decoded_portfolios.csv"
    _write_csv(decoded_rows, decoded_path)

    patch_payloads = _patch_payloads(config)
    public_config = load_sc_cmpo_config(_resolve("configs/phase3_sc_cmpo_ieee123.yaml"))
    grid = load_public_grid(public_config)
    system_rows: list[dict[str, Any]] = []
    heldout_rows: list[dict[str, Any]] = []

    for budget_id, candidates in sorted(
        selected.items(), key=lambda item: float(payloads[item[0]]["budget_constraint"]["amount"])
    ):
        for rank, candidate in enumerate(candidates, start=1):
            system_row, heldout_row = _evaluate_portfolio(
                method=QCI_METHOD,
                portfolio=candidate.portfolio,
                master_runtime=float(candidate.provenance.get("runtime_seconds", 0.0)),
                master_backend="QCi Dirac-3 sample-hamiltonian",
                master_metadata={
                    "critical_service_proxy": candidate.critical_service_proxy,
                    "reserve_preparedness": candidate.reserve_preparedness,
                    "estimated_recourse_score": candidate.estimated_recourse_score,
                    "upgrade_utilization": candidate.upgrade_utilization,
                },
                portfolio_rank=rank,
                payloads=patch_payloads,
                grid=grid,
                trace_dir=trace_dir,
                provenance=candidate.provenance,
                heldout_limit=int(config["recourse"]["heldout_n_1_count"]),
            )
            system_rows.append(system_row)
            heldout_rows.append(heldout_row)

    for budget_index, (budget_id, payload) in enumerate(
        sorted(payloads.items(), key=lambda item: float(item[1]["budget_constraint"]["amount"]))
    ):
        for method_index, method in enumerate(config["classical_master_methods"]):
            result = solve_classical_master(
                payload, str(method), seed=1701 + budget_index * 101 + method_index
            )
            system_row, heldout_row = _evaluate_portfolio(
                method=str(method),
                portfolio=result.portfolio,
                master_runtime=result.runtime_seconds,
                master_backend=result.backend,
                master_metadata=result.metadata,
                portfolio_rank=1,
                payloads=patch_payloads,
                grid=grid,
                trace_dir=trace_dir,
                provenance={"payload_budget_id": budget_id, "seed": 1701 + budget_index * 101 + method_index},
                heldout_limit=int(config["recourse"]["heldout_n_1_count"]),
            )
            system_rows.append(system_row)
            heldout_rows.append(heldout_row)

    system = pd.DataFrame(system_rows)
    heldout = pd.DataFrame(heldout_rows)
    if (system["total_upgrade_cost"] > system["budget"] + 1e-6).any():
        raise ValueError("over-budget portfolio reached the recourse result table")
    if not system["feasibility"].astype(bool).all() or not heldout["feasibility"].astype(bool).all():
        raise ValueError("infeasible portfolio reached the final result tables")
    system_path = output / "portfolio_recourse_metrics.csv"
    heldout_path = output / "heldout_metrics.csv"
    system.to_csv(system_path, index=False)
    heldout.to_csv(heldout_path, index=False)

    headline = _headline_rows(system, heldout)
    expected_methods = {QCI_METHOD, *map(str, config["classical_master_methods"])}
    for budget_id, group in headline.groupby("budget_id"):
        if set(group["method"]) != expected_methods:
            raise ValueError(f"headline method coverage mismatch at {budget_id}")
    comparison_path = output / "master_comparison.csv"
    headline.to_csv(comparison_path, index=False)
    outcomes = _win_tie_loss(headline)
    outcomes_path = output / "win_tie_loss.csv"
    outcomes.to_csv(outcomes_path, index=False)
    frontiers, hypervolumes = _frontiers(headline)
    frontier_path = output / "pareto_frontier.csv"
    frontiers.to_csv(frontier_path, index=False)

    _plot_lines(
        headline,
        "total_ens",
        "Expected total ENS (kWh)",
        output / "upgrade_budget_vs_total_ens.png",
    )
    _plot_lines(
        headline,
        "critical_ens",
        "Expected critical ENS (kWh)",
        output / "upgrade_budget_vs_critical_ens.png",
    )
    _plot_lines(
        headline,
        "heldout_total_ens",
        "Held-out expected total ENS (kWh)",
        output / "heldout_budget_vs_ens.png",
    )
    budget_amounts = {
        budget_id: float(payload["budget_constraint"]["amount"])
        for budget_id, payload in payloads.items()
    }
    _plot_diversity(
        selected,
        qci_summary["unique_feasible_portfolios_per_budget"],
        budget_amounts,
        output / "portfolio_diversity.png",
    )
    _plot_native_vs_qubo(payloads, output / "native_master_vs_qubo_size.png")

    best_total = sorted(
        outcomes.loc[
            (outcomes["metric"] == "total_ens") & (outcomes["outcome"] != "loss"),
            "budget_id",
        ].astype(str)
    )
    best_critical = sorted(
        outcomes.loc[
            (outcomes["metric"] == "critical_ens") & (outcomes["outcome"] != "loss"),
            "budget_id",
        ].astype(str)
    )
    best_heldout = sorted(
        outcomes.loc[
            (outcomes["metric"] == "heldout_total_ens") & (outcomes["outcome"] != "loss"),
            "budget_id",
        ].astype(str)
    )
    totals = outcomes.groupby(["metric", "outcome"]).size().to_dict()
    total_counts = {
        outcome: int(totals.get(("total_ens", outcome), 0))
        for outcome in ("win", "tie", "loss")
    }
    all_outcome_counts = {
        metric: {
            outcome: int(totals.get((metric, outcome), 0))
            for outcome in ("win", "tie", "loss")
        }
        for metric in ("total_ens", "critical_ens", "heldout_total_ens")
    }
    total_win_count = int(totals.get(("total_ens", "win"), 0))
    heldout_win_count = int(totals.get(("heldout_total_ens", "win"), 0))
    native_feasible_samples = sum(
        row.get("admission_status") == "native_feasible" for row in decoded_rows
    )
    if native_feasible_samples == 0:
        claim = (
            "None of the 540 native Dirac coordinate samples was directly binary and coverage-feasible; "
            "after challenge-aligned hard-feasible projection, QCi tied the best classical total ENS at "
            f"{total_counts['tie']} of six budgets and won at {total_win_count}, so no matched-budget "
            "QCi ENS advantage is supported."
        )
    elif total_win_count and heldout_win_count:
        claim = (
            "After challenge-aligned hard-feasible portfolio projection, the QCi global master "
            "attains lower total ENS than "
            f"every classical master at {total_win_count} of six training-budget levels and retains "
            f"a held-out total-ENS advantage at {heldout_win_count} levels."
        )
    elif total_win_count:
        claim = (
            "After challenge-aligned hard-feasible portfolio projection, the QCi global master "
            "attains lower in-sample total ENS "
            f"than every classical master at {total_win_count} of six evaluated budget levels; no "
            "held-out superiority claim is supported."
        )
    else:
        claim = (
            "The challenge-aligned, hard-feasible matched-budget experiment does not support a claim that the QCi global "
            "master reduces total ENS versus the best classical master."
        )
    hv_vs_classical = {
        objective: {
            method: {
                "qci": values[QCI_METHOD],
                "classical": value,
                "difference": values[QCI_METHOD] - value,
            }
            for method, value in values.items()
            if method != QCI_METHOD
        }
        for objective, values in hypervolumes.items()
    }
    summary = {
        **plan,
        **qci_summary,
        "qci_best_budget_levels_by_total_ens": best_total,
        "qci_best_budget_levels_by_critical_ens": best_critical,
        "qci_best_heldout_budget_levels": best_heldout,
        "qci_vs_classical_master_total_ens_win_tie_loss": total_counts,
        "qci_vs_classical_master_wins_ties_losses": all_outcome_counts,
        "native_feasible_qci_sample_count": native_feasible_samples,
        "hypervolumes": hypervolumes,
        "qci_pareto_hypervolume_versus_classical": hv_vs_classical,
        "strongest_supported_final_paper_claim": claim,
        "system_evaluation_count": len(system),
        "heldout_evaluation_count": len(heldout),
    }
    summary_path = output / "experiment_summary.json"
    summary_path.write_text(json.dumps(_json_safe(summary), indent=2), encoding="utf-8")
    artifacts = [
        decoded_path,
        system_path,
        heldout_path,
        comparison_path,
        frontier_path,
        outcomes_path,
        output / "upgrade_budget_vs_total_ens.png",
        output / "upgrade_budget_vs_critical_ens.png",
        output / "heldout_budget_vs_ens.png",
        output / "portfolio_diversity.png",
        output / "native_master_vs_qubo_size.png",
        summary_path,
    ]
    manifest = {
        "schema": "cmpo.paper_artifact_manifest.v1",
        "config_path": str(config_file.relative_to(ROOT)),
        "validation_summary_path": str(
            (output / "validation_summary.json").relative_to(ROOT)
        ),
        "master_payload_paths": [str(path.relative_to(ROOT)) for path in payload_paths],
        "raw_request_paths": [str(path.relative_to(ROOT)) for path in sorted(raw.glob("**/request.json"))],
        "raw_response_paths": [str(path.relative_to(ROOT)) for path in sorted(raw.glob("**/response.json"))],
        "artifacts": [
            {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path)} for path in artifacts
        ],
        "regeneration_command": (
            "python scripts/phase3_evaluate_budget_master_v2_experiment.py "
            "--config configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml "
            "--raw-dir results/phase3/sc_cmpo/budget_master_v2/qci"
        ),
        "qci_submission_performed": False,
    }
    (output / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = evaluate_experiment(
        args.config,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(json.dumps(result, indent=2))
        return
    print(f"completed/failed QCi jobs: {result['completed_qci_jobs']}/{result['failed_qci_jobs']}")
    print(
        "unique feasible portfolios per budget: "
        + json.dumps(result["unique_feasible_portfolios_per_budget"], sort_keys=True)
    )
    print(
        "QCi best budget levels by total ENS: "
        + json.dumps(result["qci_best_budget_levels_by_total_ens"])
    )
    print(
        "QCi best budget levels by critical ENS: "
        + json.dumps(result["qci_best_budget_levels_by_critical_ens"])
    )
    print(
        "QCi best held-out budget levels: "
        + json.dumps(result["qci_best_heldout_budget_levels"])
    )
    print(
        "QCi versus classical-master wins/ties/losses: "
        + json.dumps(result["qci_vs_classical_master_wins_ties_losses"], sort_keys=True)
    )
    print(
        "QCi Pareto hypervolume versus every classical master: "
        + json.dumps(result["qci_pareto_hypervolume_versus_classical"], sort_keys=True)
    )
    print("strongest supported final-paper claim: " + result["strongest_supported_final_paper_claim"])


if __name__ == "__main__":
    main()
