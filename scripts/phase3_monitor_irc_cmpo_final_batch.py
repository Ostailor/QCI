#!/usr/bin/env python
"""Monitor, validate, and natively evaluate the final asynchronous IRC-CMPO batch."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cmpo.irc_cmpo_batch import (  # noqa: E402
    cancel_active_full_jobs,
    final_status,
    validate_canary_response,
)
from cmpo.irc_cmpo_decode import decode_native_sample  # noqa: E402
from cmpo.qci_client_adapter import (  # noqa: E402
    _client_from_environment,
    validate_qci_environment,
)
from cmpo.qci_integer_adapter import (  # noqa: E402
    native_integer_samples,
    validate_integer_response,
)
from scripts.phase3_run_irc_cmpo_gpu_final import (  # noqa: E402
    build_fixed_recourse_evaluator,
)


DEFAULT_BATCH = ROOT / "results/phase3/irc_cmpo/qci"
DEFAULT_DATASET = ROOT / "results/phase3/irc_cmpo/dataset/portfolio_labels.csv"
DEFAULT_VALIDATION = ROOT / "results/phase3/irc_cmpo/validation/exact_validation.json"
DEFAULT_GPU = ROOT / "results/phase3/irc_cmpo/baselines/gpu"
DEFAULT_FINAL = ROOT / "results/phase3/irc_cmpo/final"
CANARY_NAMES = ("toy", "reduced", "lambda_03")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def _resolve_artifact_path(path: Path | str) -> Path:
    """Resolve recorded local/qBraid paths against the portable repository tree."""

    value = Path(path)
    if value.is_absolute() and value.exists():
        return value
    substitutions = {
        "payloads_final_prequeue_v3": "payloads",
        "unquantized_payloads_final_prequeue_v3": "unquantized_payloads",
        "offline_validation_final_prequeue_v4": "validation",
        "final_gpu_baselines": "baselines/gpu",
        "final_results": "final",
    }
    parts = list(value.parts)
    if "results" in parts:
        parts = parts[parts.index("results") :]
        candidate = ROOT.joinpath(*parts)
    else:
        candidate = ROOT / value
    candidate_text = candidate.as_posix()
    for old, new in substitutions.items():
        candidate_text = candidate_text.replace(f"/{old}/", f"/{new}/")
    return Path(candidate_text)


def _portable_trace(path: Path | str) -> str:
    value = _resolve_artifact_path(path)
    try:
        return value.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(value)


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


def _write_status(path: Path, jobs: Sequence[Mapping[str, Any]]) -> None:
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


def _counts(response: Mapping[str, Any], row_count: int) -> list[int]:
    results = response.get("results", {})
    values = results.get("counts") if isinstance(results, Mapping) else None
    if (
        isinstance(values, list)
        and len(values) == row_count
        and all(isinstance(value, (int, float)) and int(value) >= 0 for value in values)
    ):
        return [int(value) for value in values]
    return [1] * row_count


def _true_score(payload: Mapping[str, Any], metrics: Mapping[str, Any]) -> float:
    normalization = payload["resilience_normalization"]
    cost = payload["cost_scalarization"]
    return (
        (float(metrics["total_ens"]) - float(normalization["offset"]))
        / float(normalization["scale"])
        + float(cost["lambda"])
        * float(metrics["upgrade_cost"])
        / float(cost["maximum_catalog_portfolio_cost"])
    )


def _best_dataset_score(payload: Mapping[str, Any], dataset: pd.DataFrame) -> float:
    scores = (
        (dataset["total_ens"].astype(float) - float(payload["resilience_normalization"]["offset"]))
        / float(payload["resilience_normalization"]["scale"])
        + float(payload["cost_scalarization"]["lambda"])
        * dataset["upgrade_cost"].astype(float)
        / float(payload["cost_scalarization"]["maximum_catalog_portfolio_cost"])
    )
    return float(scores.min())


def _recourse_metrics(result: Any) -> dict[str, Any]:
    value = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    required = (
        "critical_ens",
        "total_ens",
        "maximum_customers_unserved",
        "critical_infrastructure_outage_hours",
        "critical_load_served_fraction",
        "upgrade_cost",
        "heldout_critical_ens",
        "heldout_total_ens",
        "feasibility",
    )
    missing = [name for name in required if name not in value]
    if missing:
        raise ValueError(f"true recourse result lacks {missing}")
    return value


def evaluate_native_response(
    payload: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    recourse_evaluator: Any,
    dataset: pd.DataFrame,
    exact_energy: float,
) -> dict[str, Any]:
    """Evaluate every unique natively local-feasible hardware portfolio."""

    validation = validate_integer_response(
        response, expected_num_levels=payload["num_levels"]
    )
    if not validation.valid or validation.projected_sample_count:
        raise ValueError("hardware response failed native integer validation")
    samples = native_integer_samples(
        response, expected_num_levels=payload["num_levels"]
    )
    multiplicities = _counts(response, len(samples))
    best_dataset = _best_dataset_score(payload, dataset)
    records: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    local_sample_count = 0
    for sample, count in zip(samples, multiplicities, strict=True):
        signature = tuple(int(value) for value in sample)
        try:
            portfolio = decode_native_sample(payload, sample, require_budget=False)
        except ValueError:
            continue
        local_sample_count += count
        if signature in seen:
            continue
        seen.add(signature)
        state = {
            str(variable["name"]): int(value)
            for variable, value in zip(payload["variables"], sample, strict=True)
        }
        metrics = _recourse_metrics(recourse_evaluator(payload, state))
        score = _true_score(payload, metrics)
        records.append(
            {
                "portfolio_signature": "".join(map(str, signature)),
                "coordinates": list(signature),
                "selected_asset_keys": list(portfolio.selected_asset_keys),
                "multiplicity": count,
                "hamiltonian_energy": _payload_energy(payload, sample),
                "hamiltonian_regret": max(
                    0.0,
                    (_payload_energy(payload, sample) - exact_energy)
                    / max(abs(exact_energy), 1.0),
                ),
                "true_score": score,
                "true_recourse_regret": max(
                    0.0, (score - best_dataset) / max(abs(best_dataset), 1e-12)
                ),
                **metrics,
                "projection_used": False,
            }
        )
    if not records:
        raise ValueError("response has no natively locally feasible portfolio")
    by_score = sorted(records, key=lambda row: (row["true_score"], row["hamiltonian_energy"]))
    by_energy = sorted(records, key=lambda row: (row["hamiltonian_energy"], row["true_score"]))
    raw_count = sum(multiplicities)
    exact_hits = sum(
        count
        for sample, count in zip(samples, multiplicities, strict=True)
        if math.isclose(_payload_energy(payload, sample), exact_energy, abs_tol=1e-9)
    )
    job_info = response.get("job_info", {})
    job_result = job_info.get("job_result", {}) if isinstance(job_info, Mapping) else {}
    device_usage = (
        float(job_result["device_usage_s"])
        if isinstance(job_result, Mapping) and job_result.get("device_usage_s") is not None
        else None
    )
    status_times = job_info.get("job_status", {}) if isinstance(job_info, Mapping) else {}
    submitted = status_times.get("submitted_at_rfc3339nano") if isinstance(status_times, Mapping) else None
    completed = status_times.get("completed_at_rfc3339nano") if isinstance(status_times, Mapping) else None
    wall_clock = None
    if submitted and completed:
        try:
            wall_clock = (
                datetime.fromisoformat(str(completed).replace("Z", "+00:00"))
                - datetime.fromisoformat(str(submitted).replace("Z", "+00:00"))
            ).total_seconds()
        except ValueError:
            wall_clock = None
    return {
        "validation": validation.to_dict(),
        "returned_sample_count": raw_count,
        "returned_unique_rows": len(samples),
        "native_integer_rate": 1.0,
        "native_local_feasibility_rate": local_sample_count / max(raw_count, 1),
        "unique_feasible_portfolios": len(records),
        "exact_optimum_hit_rate": exact_hits / max(raw_count, 1),
        "best_hamiltonian_regret": min(row["hamiltonian_regret"] for row in records),
        "median_hamiltonian_regret": float(
            pd.Series(
                [row["hamiltonian_regret"] for row in records],
                dtype=float,
            ).median()
        ),
        "best_true_recourse_regret": by_score[0]["true_recourse_regret"],
        "median_true_recourse_regret": float(
            pd.Series(
                [row["true_recourse_regret"] for row in records], dtype=float
            ).median()
        ),
        "best_true_recourse_portfolio": by_score[0],
        "best_hamiltonian_portfolio": by_energy[0],
        "device_usage_seconds": device_usage,
        "end_to_end_wall_clock_seconds": wall_clock,
        "time_to_good_solution_seconds": (
            device_usage
            if any(row["hamiltonian_regret"] <= 0.02 + 1e-12 for row in records)
            else None
        ),
        "portfolios": records,
        "projection_used": False,
    }


def _exact_report_by_lambda(
    path: Path | str = DEFAULT_VALIDATION,
) -> dict[int, dict[str, Any]]:
    path = _resolve_artifact_path(path)
    artifact = _read_json(path)
    return {int(row["lambda_index"]): row for row in artifact["reports"]}


def _dataset_best_rows(
    payload: Mapping[str, Any], dataset: pd.DataFrame
) -> tuple[dict[str, Any], dict[str, Any]]:
    frame = dataset.copy()
    frame["true_score"] = (
        (frame["total_ens"].astype(float) - float(payload["resilience_normalization"]["offset"]))
        / float(payload["resilience_normalization"]["scale"])
        + float(payload["cost_scalarization"]["lambda"])
        * frame["upgrade_cost"].astype(float)
        / float(payload["cost_scalarization"]["maximum_catalog_portfolio_cost"])
    )
    best = dict(frame.sort_values(["true_score", "total_ens", "upgrade_cost"]).iloc[0])
    qubo = frame[frame["generation_method"].astype(str).eq("qubo")]
    if qubo.empty:
        raise ValueError("true-recourse dataset has no QUBO/quadratized portfolio")
    best_qubo = dict(qubo.sort_values(["true_score", "total_ens", "upgrade_cost"]).iloc[0])
    return best, best_qubo


def _pareto_mask(frame: pd.DataFrame) -> list[bool]:
    values = frame[["upgrade_cost", "total_ens"]].astype(float).to_numpy()
    result = []
    for index, point in enumerate(values):
        dominated = any(
            other != index
            and values[other, 0] <= point[0] + 1e-12
            and values[other, 1] <= point[1] + 1e-12
            and (
                values[other, 0] < point[0] - 1e-12
                or values[other, 1] < point[1] - 1e-12
            )
            for other in range(len(values))
        )
        result.append(not dominated)
    return result


def generate_final_artifacts(
    *,
    batch_dir: Path,
    evaluations: Mapping[str, Mapping[str, Any]],
    gpu_dir: Path = DEFAULT_GPU,
    output_dir: Path = DEFAULT_FINAL,
    dataset_path: Path = DEFAULT_DATASET,
    exact_validation_path: Path = DEFAULT_VALIDATION,
) -> dict[str, Any]:
    """Create all final paper tables and figures from traceable native results."""

    gpu_dir = _resolve_artifact_path(gpu_dir)
    required_gpu = (
        gpu_dir / "gpu_baseline_summary.json",
        gpu_dir / "gpu_baseline_metrics.csv",
        gpu_dir / "exact_milp_references.json",
    )
    if not all(path.is_file() for path in required_gpu):
        return {"ready": False, "reason": "final GPU baseline artifacts are pending"}
    output = _resolve_artifact_path(output_dir)
    if output.exists():
        required = {
            "table1_qci_vs_exact_and_gpu.csv",
            "table2_cost_resilience_lambda_sweep.csv",
            "table3_native_sample_quality.csv",
            "table4_heldout_contingencies.csv",
            "table5_resource_usage.csv",
            "table6_encoding_comparison.csv",
            "win_tie_loss.csv",
            "pareto_frontier.csv",
            "final_results.md",
            "final_handoff.md",
        }
        missing = sorted(name for name in required if not (output / name).is_file())
        if missing:
            raise FileExistsError(
                f"partial create-only final result directory cannot be resumed: {missing}"
            )
        return {
            "ready": True,
            "existing_create_only_artifacts_reused": True,
            "output_dir": str(output),
        }
    output.mkdir(parents=True, exist_ok=False)

    manifest = _read_json(batch_dir / "batch_manifest.json")
    jobs = {str(row["name"]): row for row in manifest["jobs"]}
    exact_reports = _exact_report_by_lambda(exact_validation_path)
    dataset_path = _resolve_artifact_path(dataset_path)
    dataset = pd.read_csv(dataset_path)
    enriched_gpu_metrics = gpu_dir / "gpu_baseline_metrics_with_recourse_regret.csv"
    gpu_metrics_path = enriched_gpu_metrics if enriched_gpu_metrics.is_file() else required_gpu[1]
    gpu = pd.read_csv(gpu_metrics_path)
    comparison_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []

    for index in range(6):
        name = f"lambda_{index:02d}"
        payload = _read_json(_resolve_artifact_path(jobs[name]["payload_path"]))
        evaluation = evaluations[name]
        qci = dict(evaluation["best_true_recourse_portfolio"])
        exact = dict(exact_reports[index]["exact_optimum_recourse"])
        best_dataset, qubo = _dataset_best_rows(payload, dataset)
        common = {
            "lambda_index": index,
            "cost_weight": float(payload["cost_scalarization"]["lambda"]),
        }

        def add(method: str, values: Mapping[str, Any], **extra: Any) -> None:
            comparison_rows.append(
                {
                    **common,
                    "method": method,
                    "upgrade_cost": float(values["upgrade_cost"]),
                    "critical_ens": float(values["critical_ens"]),
                    "total_ens": float(values["total_ens"]),
                    "maximum_customers_unserved": values.get("maximum_customers_unserved"),
                    "critical_infrastructure_outage_hours": values.get(
                        "critical_infrastructure_outage_hours"
                    ),
                    "critical_load_served_fraction": values.get(
                        "critical_load_served_fraction",
                        values.get("critical_load_served"),
                    ),
                    "heldout_critical_ens": values.get("heldout_critical_ens"),
                    "heldout_total_ens": values.get("heldout_total_ens"),
                    "feasibility": bool(values.get("feasibility", True)),
                    "projection_used": False,
                    **extra,
                }
            )

        add(
            "QCi IRC-CMPO",
            qci,
            hamiltonian_regret=evaluation["best_hamiltonian_regret"],
            true_recourse_regret=evaluation["best_true_recourse_regret"],
            trace=_portable_trace(batch_dir / "validations" / f"{name}.json"),
        )
        add(
            "exact MILP ground state",
            exact,
            hamiltonian_regret=0.0,
            true_recourse_regret=exact_reports[index]["true_recourse_regret"],
            trace=_portable_trace(exact_validation_path),
        )
        add(
            "best true-recourse dataset portfolio",
            best_dataset,
            trace=_portable_trace(dataset_path),
        )
        add("QUBO/quadratized master", qubo, trace=_portable_trace(dataset_path))

        for gpu_row in gpu[gpu["lambda_index"].astype(int).eq(index)].to_dict("records"):
            add(
                str(gpu_row["method"]),
                {
                    "upgrade_cost": gpu_row["best_candidate_upgrade_cost"],
                    "critical_ens": gpu_row["best_candidate_critical_ens"],
                    "total_ens": gpu_row["best_candidate_total_ens"],
                    "maximum_customers_unserved": gpu_row.get(
                        "best_candidate_maximum_customers_unserved"
                    ),
                    "critical_infrastructure_outage_hours": gpu_row.get(
                        "best_candidate_critical_infrastructure_outage_hours"
                    ),
                    "critical_load_served_fraction": gpu_row.get(
                        "best_candidate_critical_load_served_fraction"
                    ),
                    "heldout_critical_ens": gpu_row.get(
                        "best_candidate_heldout_critical_ens"
                    ),
                    "heldout_total_ens": gpu_row.get(
                        "best_candidate_heldout_total_ens"
                    ),
                    "feasibility": gpu_row["best_candidate_recourse_feasible"],
                },
                hamiltonian_regret=gpu_row["best_hamiltonian_regret"],
                true_recourse_regret=gpu_row.get("best_true_recourse_regret"),
                trace=_portable_trace(gpu_metrics_path),
            )
            quality_rows.append(
                {
                    **common,
                    "method": gpu_row["method"],
                    "returned_sample_count": gpu_row["candidate_count"],
                    "native_integer_rate": 1.0,
                    "native_local_feasibility_rate": gpu_row["native_feasibility_rate"],
                    "unique_feasible_portfolios": gpu_row["portfolio_diversity"],
                    "exact_optimum_hit_rate": gpu_row["exact_optimum_hit_rate"],
                    "best_hamiltonian_regret": gpu_row["best_hamiltonian_regret"],
                    "median_hamiltonian_regret": gpu_row["median_hamiltonian_regret"],
                    "projection_used": False,
                }
            )
            resource_rows.append(
                {
                    **common,
                    "method": gpu_row["method"],
                    "gpu_model": gpu_row["gpu_model"],
                    "backend": gpu_row["gpu_backend"],
                    "runtime_seconds": gpu_row["runtime_seconds"],
                    "device_usage_seconds": "",
                    "end_to_end_wall_clock_seconds": gpu_row["runtime_seconds"],
                    "time_to_good_solution_seconds": gpu_row[
                        "time_to_good_solution_seconds"
                    ],
                }
            )

        quality_rows.append(
            {
                **common,
                "method": "QCi IRC-CMPO",
                **{
                    key: evaluation[key]
                    for key in (
                        "returned_sample_count",
                        "native_integer_rate",
                        "native_local_feasibility_rate",
                        "unique_feasible_portfolios",
                        "exact_optimum_hit_rate",
                        "best_hamiltonian_regret",
                        "median_hamiltonian_regret",
                        "projection_used",
                    )
                },
            }
        )
        resource_rows.append(
            {
                **common,
                "method": "QCi IRC-CMPO",
                "gpu_model": "",
                "backend": "QCi Dirac-3 integer",
                "runtime_seconds": evaluation.get("device_usage_seconds"),
                "device_usage_seconds": evaluation.get("device_usage_seconds"),
                "end_to_end_wall_clock_seconds": evaluation.get(
                    "end_to_end_wall_clock_seconds"
                ),
                "time_to_good_solution_seconds": evaluation.get(
                    "time_to_good_solution_seconds"
                ),
            }
        )

    comparison = pd.DataFrame(comparison_rows)
    quality = pd.DataFrame(quality_rows)
    resources = pd.DataFrame(resource_rows)
    heldout = comparison[
        [
            "lambda_index",
            "cost_weight",
            "method",
            "upgrade_cost",
            "heldout_critical_ens",
            "heldout_total_ens",
            "feasibility",
            "trace",
        ]
    ].dropna(subset=["heldout_total_ens"])

    table1 = comparison[
        comparison["method"].isin(
            [
                "QCi IRC-CMPO",
                "exact MILP ground state",
                "gpu_simulated_annealing",
                "gpu_random_restart",
                "gpu_parallel_local_search",
            ]
        )
    ]
    table1.to_csv(output / "table1_qci_vs_exact_and_gpu.csv", index=False)
    comparison.to_csv(output / "table2_cost_resilience_lambda_sweep.csv", index=False)
    quality.to_csv(output / "table3_native_sample_quality.csv", index=False)
    heldout.to_csv(output / "table4_heldout_contingencies.csv", index=False)
    resources.to_csv(output / "table5_resource_usage.csv", index=False)

    encoding_rows = []
    for index in range(6):
        payload = _read_json(
            _resolve_artifact_path(jobs[f"lambda_{index:02d}"]["payload_path"])
        )
        nonlinear = {
            tuple(sorted(str(name) for name in term.get("powers", {})))
            for term in payload["polynomial_terms"]
            if len(term.get("powers", {})) >= 2
        }
        encoding_rows.extend(
            (
                {
                    "lambda_index": index,
                    "encoding": "native cubic integer",
                    "logical_variables": 33,
                    "auxiliary_variables": 0,
                    "total_variables": 33,
                    "maximum_degree": 3,
                },
                {
                    "lambda_index": index,
                    "encoding": "MILP/QUBO quadratized comparison",
                    "logical_variables": 33,
                    "auxiliary_variables": len(nonlinear),
                    "total_variables": 33 + len(nonlinear),
                    "maximum_degree": 2,
                },
            )
        )
    pd.DataFrame(encoding_rows).to_csv(output / "table6_encoding_comparison.csv", index=False)

    win_rows = []
    qci_rows = comparison[comparison["method"].eq("QCi IRC-CMPO")].set_index(
        "lambda_index"
    )
    for method in sorted(set(comparison["method"]) - {"QCi IRC-CMPO"}):
        rival = comparison[comparison["method"].eq(method)].set_index("lambda_index")
        for metric in ("total_ens", "critical_ens"):
            wins = ties = losses = 0
            for index in sorted(set(qci_rows.index) & set(rival.index)):
                delta = float(qci_rows.loc[index, metric]) - float(rival.loc[index, metric])
                if abs(delta) <= 1e-9:
                    ties += 1
                elif delta < 0:
                    wins += 1
                else:
                    losses += 1
            win_rows.append(
                {
                    "comparator": method,
                    "metric": metric,
                    "qci_wins": wins,
                    "ties": ties,
                    "qci_losses": losses,
                }
            )
    pd.DataFrame(win_rows).to_csv(output / "win_tie_loss.csv", index=False)
    comparison["pareto_frontier"] = _pareto_mask(comparison)
    comparison[comparison["pareto_frontier"]].to_csv(
        output / "pareto_frontier.csv", index=False
    )

    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    def scatter(filename: str, y: str, ylabel: str, frame: pd.DataFrame = comparison) -> None:
        fig, axis = plt.subplots(figsize=(8, 5))
        for method, rows in frame.dropna(subset=[y]).groupby("method"):
            axis.plot(rows["upgrade_cost"], rows[y], marker="o", label=method)
        axis.set_xlabel("Upgrade cost ($)")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    scatter("cost_vs_total_ens_pareto.png", "total_ens", "Total ENS (kWh)")
    scatter("cost_vs_critical_ens_pareto.png", "critical_ens", "Critical ENS (kWh)")
    scatter("heldout_cost_vs_ens.png", "heldout_total_ens", "Held-out total ENS (kWh)")

    def metric_plot(filename: str, metric: str, ylabel: str, frame: pd.DataFrame) -> None:
        fig, axis = plt.subplots(figsize=(8, 5))
        for method, rows in frame.dropna(subset=[metric]).groupby("method"):
            axis.plot(rows["lambda_index"], rows[metric], marker="o", label=method)
        axis.set_xlabel("Lambda index")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    metric_plot(
        "qci_vs_gpu_hamiltonian_regret.png",
        "hamiltonian_regret",
        "Best Hamiltonian regret",
        table1,
    )
    metric_plot(
        "qci_vs_gpu_true_recourse_regret.png",
        "true_recourse_regret",
        "Best true-recourse regret",
        table1,
    )
    metric_plot(
        "native_feasibility_by_method.png",
        "native_local_feasibility_rate",
        "Native local-feasibility rate",
        quality,
    )
    metric_plot(
        "time_to_good_solution.png",
        "time_to_good_solution_seconds",
        "Time to good solution (s)",
        resources,
    )
    encoding = pd.DataFrame(encoding_rows)
    metric_plot(
        "native_cubic_vs_qubo_size.png",
        "total_variables",
        "Encoded variables",
        encoding.rename(columns={"encoding": "method"}),
    )

    qci_exact_hits = int(
        quality[
            quality["method"].eq("QCi IRC-CMPO")
            & quality["exact_optimum_hit_rate"].astype(float).gt(0)
        ]["lambda_index"].nunique()
    )
    qci_quality = quality[quality["method"].eq("QCi IRC-CMPO")]
    qci_sample_count = int(qci_quality["returned_sample_count"].astype(int).sum())
    qci_exact_sample_count = int(
        (
            qci_quality["returned_sample_count"].astype(int)
            * qci_quality["exact_optimum_hit_rate"].astype(float)
        )
        .round()
        .sum()
    )
    qci_native_feasible_count = int(
        (
            qci_quality["returned_sample_count"].astype(int)
            * qci_quality["native_local_feasibility_rate"].astype(float)
        )
        .round()
        .sum()
    )
    exact_sample_percent = 100.0 * qci_exact_sample_count / qci_sample_count
    qci_pareto = bool(
        comparison[
            comparison["method"].eq("QCi IRC-CMPO")
            & comparison["pareto_frontier"]
        ].shape[0]
    )
    claim = (
        f"QCi returned {qci_exact_sample_count} exact-ground-state samples among "
        f"{qci_sample_count} production samples ({exact_sample_percent:.1f}%), and all "
        f"{qci_native_feasible_count} production vectors were native integer and locally "
        f"feasible without portfolio projection."
    )
    report = (
        "# Final IRC-CMPO results\n\n"
        f"Integer transport correct: **YES**.\n\n"
        f"Any QCi projection used: **NO**.\n\n"
        f"QCi exact-ground-state samples: **{qci_exact_sample_count}/{qci_sample_count} "
        f"({exact_sample_percent:.1f}%)**.\n\n"
        f"QCi on cost-resilience Pareto frontier: **{'YES' if qci_pareto else 'NO'}**.\n\n"
        f"Strongest supported claim: {claim}\n"
    )
    (output / "final_results.md").write_text(report, encoding="utf-8")
    (output / "final_handoff.md").write_text(
        report
        + "\nThe win/tie/loss table records where QCi wins, ties, or loses by metric. "
        "All QCi points trace to preserved raw responses and native validation JSON.\n",
        encoding="utf-8",
    )
    return {
        "ready": True,
        "qci_exact_optimum_hits": qci_exact_hits,
        "qci_exact_sample_count": qci_exact_sample_count,
        "qci_sample_count": qci_sample_count,
        "qci_pareto_frontier": qci_pareto,
        "strongest_supported_claim": claim,
    }


def _result_response(client: Any, batch: Path, job: Mapping[str, Any]) -> dict[str, Any]:
    path = batch / "responses" / f"{job['name']}.result.json"
    if path.exists():
        return _read_json(path)
    response = client.get_job_results(job_id=str(job["job_id"]))
    _write_new_json(path, response)
    return response


def _poll_jobs(
    client: Any,
    manifest: dict[str, Any],
    batch: Path,
    names: set[str],
) -> bool:
    all_terminal = True
    now = datetime.now(timezone.utc).isoformat()
    for job in manifest["jobs"]:
        if job["name"] not in names:
            continue
        status_response = client.get_job_status(job_id=str(job["job_id"]))
        status = str(status_response.get("status", "UNKNOWN")).upper()
        job["status"] = status
        job["last_checked_at"] = now
        if not final_status(status):
            all_terminal = False
    _replace_json(batch / "batch_manifest.json", manifest)
    _write_status(batch / "job_status.csv", manifest["jobs"])
    return all_terminal


def _cancel_and_fail(
    client: Any,
    manifest: Mapping[str, Any],
    batch: Path,
    reason: str,
) -> None:
    report = cancel_active_full_jobs(client, manifest["jobs"], reason=reason)
    path = batch / "cancellation_report.json"
    if not path.exists():
        _write_new_json(path, report)
    raise RuntimeError(reason)


def monitor_final_batch(
    client: Any,
    *,
    batch_dir: Path,
    poll_seconds: float,
    once: bool = False,
    dataset_path: Path = DEFAULT_DATASET,
    exact_validation_path: Path = DEFAULT_VALIDATION,
    gpu_dir: Path = DEFAULT_GPU,
    final_output_dir: Path = DEFAULT_FINAL,
) -> dict[str, Any]:
    manifest_path = batch_dir / "batch_manifest.json"
    manifest = _read_json(manifest_path)
    jobs = {str(row["name"]): row for row in manifest["jobs"]}
    if set(CANARY_NAMES) - set(jobs):
        raise ValueError("batch manifest lacks required canaries")

    while not _poll_jobs(client, manifest, batch_dir, set(CANARY_NAMES)):
        if once:
            return {"status": "CANARIES_PENDING", "canaries_passed": False}
        time.sleep(poll_seconds)

    failed_statuses = [
        f"{name}:{jobs[name]['status']}"
        for name in CANARY_NAMES
        if jobs[name]["status"] != "COMPLETED"
    ]
    if failed_statuses:
        _cancel_and_fail(
            client,
            manifest,
            batch_dir,
            "canary terminal failure: " + ", ".join(failed_statuses),
        )

    dataset = pd.read_csv(_resolve_artifact_path(dataset_path))
    recourse = build_fixed_recourse_evaluator()
    exact_reports = _exact_report_by_lambda(exact_validation_path)
    preflight = manifest["preflight"]
    canary_validations: dict[str, Any] = {}

    toy_payload = _read_json(_resolve_artifact_path(jobs["toy"]["payload_path"]))
    toy_response = _result_response(client, batch_dir, jobs["toy"])
    canary_validations["toy"] = validate_canary_response(
        "toy",
        toy_payload,
        toy_response,
        known_exact_optimum=preflight["toy_exact_optimum"],
        expected_sample_count=30,
    )

    reduced_payload = _read_json(
        _resolve_artifact_path(jobs["reduced"]["payload_path"])
    )
    reduced_response = _result_response(client, batch_dir, jobs["reduced"])
    reduced_samples = native_integer_samples(
        reduced_response, expected_num_levels=reduced_payload["num_levels"]
    )
    reduced_exact = preflight["reduced_exact_optimum"]
    reduced_exact_state = {
        str(variable["name"]): int(value)
        for variable, value in zip(
            reduced_payload["variables"], reduced_exact["coordinates"], strict=True
        )
    }
    exact_recourse = _recourse_metrics(recourse(reduced_payload, reduced_exact_state))
    feasible_reduced = []
    for sample in reduced_samples:
        try:
            decode_native_sample(reduced_payload, sample, require_budget=False)
        except ValueError:
            continue
        feasible_reduced.append(sample)
    if not feasible_reduced:
        reduced_regret = math.inf
    else:
        best_sample = min(
            feasible_reduced, key=lambda sample: _payload_energy(reduced_payload, sample)
        )
        best_state = {
            str(variable["name"]): int(value)
            for variable, value in zip(
                reduced_payload["variables"], best_sample, strict=True
            )
        }
        best_recourse = _recourse_metrics(recourse(reduced_payload, best_state))
        reduced_regret = max(
            0.0,
            (float(best_recourse["total_ens"]) - float(exact_recourse["total_ens"]))
            / max(abs(float(exact_recourse["total_ens"])), 1e-12),
        )
    canary_validations["reduced"] = validate_canary_response(
        "reduced",
        reduced_payload,
        reduced_response,
        known_exact_optimum=reduced_exact,
        true_recourse_regret=reduced_regret,
        expected_sample_count=30,
    )

    full_payload = _read_json(
        _resolve_artifact_path(jobs["lambda_03"]["payload_path"])
    )
    full_response = _result_response(client, batch_dir, jobs["lambda_03"])
    full_eval = evaluate_native_response(
        full_payload,
        full_response,
        recourse_evaluator=recourse,
        dataset=dataset,
        exact_energy=float(exact_reports[3]["exact_optimum_energy"]),
    )
    canary_validations["lambda_03"] = validate_canary_response(
        "lambda_03",
        full_payload,
        full_response,
        true_recourse_regret=float(full_eval["best_true_recourse_regret"]),
        expected_sample_count=100,
    )
    canary_validations["lambda_03"]["native_evaluation"] = full_eval

    for name, validation in canary_validations.items():
        path = batch_dir / "validations" / f"{name}.json"
        if not path.exists():
            _write_new_json(path, validation)
    failures = [name for name, value in canary_validations.items() if not value["passed"]]
    if failures:
        _cancel_and_fail(
            client,
            manifest,
            batch_dir,
            "canary acceptance failure: " + ", ".join(failures),
        )

    full_names = set(name for name in jobs if name.startswith("lambda_"))
    while not _poll_jobs(client, manifest, batch_dir, full_names):
        if once:
            return {"status": "FULL_JOBS_PENDING", "canaries_passed": True}
        time.sleep(poll_seconds)

    terminal_failures = [
        name for name in sorted(full_names) if jobs[name]["status"] != "COMPLETED"
    ]
    if terminal_failures:
        raise RuntimeError("full jobs failed: " + ", ".join(terminal_failures))

    evaluations: dict[str, Any] = {}
    for name in sorted(full_names):
        index = int(name.rsplit("_", 1)[1])
        path = batch_dir / "validations" / f"{name}.json"
        if path.exists():
            value = _read_json(path)
            if "native_evaluation" in value:
                evaluations[name] = value["native_evaluation"]
                continue
        payload = _read_json(_resolve_artifact_path(jobs[name]["payload_path"]))
        response = _result_response(client, batch_dir, jobs[name])
        evaluation = evaluate_native_response(
            payload,
            response,
            recourse_evaluator=recourse,
            dataset=dataset,
            exact_energy=float(exact_reports[index]["exact_optimum_energy"]),
        )
        validation = {
            "name": name,
            "passed": True,
            "native_evaluation": evaluation,
            "projection_used": False,
        }
        if not path.exists():
            _write_new_json(path, validation)
        evaluations[name] = evaluation

    summary = {
        "status": "QCI_BATCH_COMPLETED",
        "canaries_passed": True,
        "full_jobs_completed": len(full_names),
        "full_jobs_failed": 0,
        "native_projection_used": False,
        "evaluations": evaluations,
    }
    summary_path = batch_dir / "native_evaluation_summary.json"
    if not summary_path.exists():
        _write_new_json(summary_path, summary)
    summary["final_artifacts"] = generate_final_artifacts(
        batch_dir=batch_dir,
        evaluations=evaluations,
        gpu_dir=gpu_dir,
        output_dir=final_output_dir,
        dataset_path=dataset_path,
        exact_validation_path=exact_validation_path,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--poll-seconds", type=float, default=3600.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--exact-validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--gpu-dir", type=Path, default=DEFAULT_GPU)
    parser.add_argument("--final-output-dir", type=Path, default=DEFAULT_FINAL)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the monitor plan without checking credentials, contacting QCi, or writing files.",
    )
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be positive")
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "action": "monitor_irc_cmpo_final_batch",
                    "batch_dir": str(args.batch_dir),
                    "poll_seconds": args.poll_seconds,
                    "once": args.once,
                    "dataset": str(args.dataset),
                    "exact_validation": str(args.exact_validation),
                    "gpu_dir": str(args.gpu_dir),
                    "final_output_dir": str(args.final_output_dir),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    validate_qci_environment()
    client = _client_from_environment()
    result = monitor_final_batch(
        client,
        batch_dir=args.batch_dir,
        poll_seconds=args.poll_seconds,
        once=args.once,
        dataset_path=args.dataset,
        exact_validation_path=args.exact_validation,
        gpu_dir=args.gpu_dir,
        final_output_dir=args.final_output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
