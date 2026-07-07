"""Phase 3 orchestration helpers for payloads and classical baselines."""

from __future__ import annotations

import csv
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from cmpo.baselines import (
    BaselineSkipped,
    DifferentialEvolutionOptimizer,
    GPUParallelRandomRestartBaseline,
    GreedyCriticalLoadFirst,
    PiecewiseLinearMILPBaseline,
    PyomoIPOPTNonlinearBaseline,
    QUBOQuadratizedBaseline,
    RandomRestartPolynomialSearch,
    SLSQPDispatchOptimizer,
    StressReserveHeuristicBaseline,
)
from cmpo.config import DatasetConfig, ExperimentConfig, OutputConfig, SolverConfig
from cmpo.data import GridCase, generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.microgrid_design import choose_min_cost_upgrades, generate_candidate_patches, save_design_outputs
from cmpo.phase3_metrics import add_phase3_columns, summarize_phase3_results
from cmpo.public_benchmarks import build_public_benchmark_case, build_stress_case
from cmpo.qci_export import export_polynomial_model_payload, model_statistics

PHASE3_ROOT = Path("results") / "phase3"
BASELINE_SKIP_COLUMNS = ["method_name", "payload_name", "scenario", "patch", "repeat", "status", "skip_reason"]


def load_phase3_config(path: Path | str) -> dict[str, Any]:
    """Load a Phase 3 YAML config."""

    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data.setdefault("name", config_path.stem)
    data.setdefault("config_path", str(config_path))
    return data


def phase3_output_dir(config: dict[str, Any]) -> Path:
    """Return the output directory for a Phase 3 config."""

    path = Path(config.get("output_dir") or PHASE3_ROOT / str(config["name"]))
    root = PHASE3_ROOT.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Phase 3 outputs must stay under {PHASE3_ROOT}: {path}")
    return path


def dataset_name(config: dict[str, Any]) -> str:
    """Return a stable dataset name for result tables."""

    dataset = config.get("dataset", {})
    return str(dataset.get("name") or dataset.get("source") or config["name"])


def build_grid_case_from_config(config: dict[str, Any], output_dir: Path | None = None) -> GridCase:
    """Build the deterministic grid case described by a Phase 3 config."""

    dataset = config.get("dataset", {})
    source = str(dataset.get("source", "synthetic"))
    seed = int(dataset.get("seed", config.get("seed", 42)))
    horizon = int(dataset.get("horizon_hours", 6))
    n_scenarios = int(dataset.get("n_scenarios", 8))
    data_dir = output_dir or phase3_output_dir(config) / "data"

    if source.startswith("pglib_case"):
        return build_public_benchmark_case(
            source,
            horizon_hours=horizon,
            seed=seed,
            scenario_count=n_scenarios,
            output_dir=data_dir,
        )
    if source == "stress":
        return build_stress_case(
            n_microgrids=int(dataset.get("n_microgrids", 5)),
            horizon_hours=horizon,
            seed=seed,
            scenario_count=n_scenarios,
            output_dir=data_dir,
        )
    return generate_synthetic_dataset(
        DatasetConfig(seed=seed, n_microgrids=int(dataset.get("n_microgrids", 4)), horizon_hours=horizon),
        output_dir=data_dir,
    )


def _selected_scenarios(grid_case: GridCase, config: dict[str, Any]):
    count = int(config.get("dataset", {}).get("n_scenarios", len(grid_case.scenarios)))
    return grid_case.scenarios[: max(1, min(count, len(grid_case.scenarios)))]


def _write_model_stats(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare_phase3_payloads(config: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    """Generate Phase 3 payloads under results/phase3 without touching Phase 2 outputs."""

    out_dir = phase3_output_dir(config)
    payload_cfg = config.get("payloads", {})
    plan = {
        "config": config["name"],
        "output_dir": str(out_dir),
        "payload_dir": str(out_dir / "qci_payloads"),
        "dry_run": dry_run,
    }
    if dry_run:
        return plan

    out_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = out_dir / "qci_payloads"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)

    grid_case = build_grid_case_from_config(config, out_dir / "data")
    candidate_patches = generate_candidate_patches(grid_case, max_patch_size=int(payload_cfg.get("max_patch_size", 3)))
    design = choose_min_cost_upgrades(grid_case, candidate_patches)
    max_patches = int(payload_cfg.get("max_patches", len(design["selected_patches"])))
    selected_patches = design["selected_patches"][:max_patches]
    design = dict(design)
    design["selected_patches"] = selected_patches
    design_paths = save_design_outputs(design, out_dir)

    payloads: list[Path] = []
    stat_rows: list[dict[str, Any]] = []
    for patch in selected_patches:
        for scenario in _selected_scenarios(grid_case, config):
            model, metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=out_dir, write_export=False)
            payloads.append(export_polynomial_model_payload(model, metadata, out_dir))
            stat_rows.append(metadata | model_statistics(model))

    _write_model_stats(stat_rows, out_dir / "model_stats.csv")
    manifest = {
        "phase": 3,
        "config": config["name"],
        "config_path": config.get("config_path"),
        "dataset": dataset_name(config),
        "output_dir": str(out_dir),
        "payload_dir": str(payload_dir),
        "payload_count": len(payloads),
        "payloads": [str(path) for path in payloads],
        "selected_patches": [list(patch) for patch in selected_patches],
        "scenario_count": len(_selected_scenarios(grid_case, config)),
        "design_outputs": {key: str(path) for key, path in design_paths.items()},
        "design_metrics": design["metrics"],
    }
    (out_dir / "phase3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_phase3_manifest(config: dict[str, Any]) -> dict[str, Any]:
    """Load a prepared Phase 3 manifest."""

    path = phase3_output_dir(config) / "phase3_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Phase 3 payload manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _optimizers(config: dict[str, Any], repeat_seed: int):
    baseline_cfg = config.get("baselines", {})
    max_iterations = int(baseline_cfg.get("max_iterations", 8))
    random_restarts = int(baseline_cfg.get("random_restarts", 4))
    optimizers = []
    if bool(baseline_cfg.get("include_greedy", True)):
        optimizers.append(GreedyCriticalLoadFirst())
    if bool(baseline_cfg.get("include_slsqp", True)):
        optimizers.append(SLSQPDispatchOptimizer(maxiter=max_iterations))
    if bool(baseline_cfg.get("include_differential_evolution", True)):
        optimizers.append(
            DifferentialEvolutionOptimizer(
                maxiter=int(baseline_cfg.get("de_maxiter", 1)),
                popsize=int(baseline_cfg.get("de_popsize", 1)),
            )
        )
    if bool(baseline_cfg.get("include_cmpo_local", True)):
        optimizers.append(
            RandomRestartPolynomialSearch(n_restarts=random_restarts, local_steps=int(baseline_cfg.get("local_steps", 2)))
        )
    if bool(baseline_cfg.get("include_piecewise_milp", True)):
        optimizers.append(PiecewiseLinearMILPBaseline(breakpoints=int(baseline_cfg.get("milp_breakpoints", 5))))
    if bool(baseline_cfg.get("include_qubo_quadratized", True)):
        optimizers.append(
            QUBOQuadratizedBaseline(
                levels=int(baseline_cfg.get("qubo_levels", 4)),
                sweeps=int(baseline_cfg.get("qubo_sweeps", 48)),
            )
        )
    if bool(baseline_cfg.get("include_gpu_random_restart", True)):
        optimizers.append(
            GPUParallelRandomRestartBaseline(
                restarts=int(baseline_cfg.get("gpu_restarts", max(16, random_restarts * 8))),
                local_steps=int(baseline_cfg.get("gpu_local_steps", 0)),
            )
        )
    if bool(baseline_cfg.get("include_ipopt_pyomo", True)):
        optimizers.append(PyomoIPOPTNonlinearBaseline(maxiter=max_iterations))
    if bool(baseline_cfg.get("include_stress_reserve", True)):
        optimizers.append(StressReserveHeuristicBaseline(reserve_fraction=float(baseline_cfg.get("reserve_fraction", 0.35))))
    solver = SolverConfig(max_iterations=max_iterations, random_restarts=random_restarts)
    dataset = config.get("dataset", {})
    experiment_config = ExperimentConfig(
        dataset=DatasetConfig(
            seed=repeat_seed,
            n_microgrids=int(dataset.get("n_microgrids", 4)),
            horizon_hours=int(dataset.get("horizon_hours", 6)),
        ),
        solver=solver,
        output=OutputConfig(results_dir=phase3_output_dir(config), data_dir=phase3_output_dir(config) / "data"),
    )
    return optimizers, experiment_config


def _payload_jobs_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for raw_path in manifest.get("payloads", []):
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        scenario = payload.get("scenario_metadata", {}).get("scenario")
        patch_ids = payload.get("patch_metadata", {}).get("patch_ids", [])
        if not scenario or not patch_ids:
            continue
        jobs.append(
            {
                "payload": str(path),
                "payload_name": path.name,
                "scenario": str(scenario),
                "patch": tuple(str(item) for item in patch_ids),
            }
        )
    return jobs


def _run_baseline_payload_repeat_task(
    config: dict[str, Any],
    manifest_dataset: str,
    job: dict[str, Any],
    repeat: int,
    base_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run every enabled baseline for one repeat/payload pair.

    This worker is intentionally top-level so public benchmark sweeps can use
    process-level parallelism on qBraid GPU instances and multi-core CPUs.
    """

    out_dir = phase3_output_dir(config)
    grid_case = build_grid_case_from_config(config, out_dir / "data")
    scenarios = {scenario.name: scenario for scenario in _selected_scenarios(grid_case, config)}
    optimizers, experiment_config = _optimizers(config, base_seed + repeat)
    rows: list[dict[str, Any]] = []
    skip_rows: list[dict[str, Any]] = []
    scenario = scenarios.get(job["scenario"])
    if scenario is None:
        skip_rows.append(
            {
                "method_name": "all",
                "payload_name": job["payload_name"],
                "repeat": repeat,
                "status": "SKIPPED",
                "skip_reason": f"Scenario not selected by config: {job['scenario']}",
            }
        )
        return rows, skip_rows

    patch = tuple(job["patch"])
    model, _metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=out_dir, write_export=False)
    for optimizer in optimizers:
        try:
            row = optimizer.run(grid_case, scenario, patch, model, experiment_config).to_dict()
            row.update(
                {
                    "repeat": repeat,
                    "backend": "classical",
                    "dataset": manifest_dataset,
                    "payload": job["payload"],
                    "payload_name": job["payload_name"],
                }
            )
            rows.append(_row_with_baseline_metadata(row, optimizer))
        except BaselineSkipped as exc:
            skip_rows.append(
                {
                    "method_name": exc.method_name,
                    "payload_name": job["payload_name"],
                    "scenario": scenario.name,
                    "patch": "-".join(patch),
                    "repeat": repeat,
                    "status": "SKIPPED",
                    "skip_reason": exc.reason,
                }
            )
    return rows, skip_rows


def _row_with_baseline_metadata(row: dict[str, Any], optimizer: Any) -> dict[str, Any]:
    metadata = getattr(optimizer, "last_metadata", {}) or {}
    for key, value in metadata.items():
        row[key] = value
    row.setdefault("qci_energy", float("nan"))
    row["decoded_objective"] = row.get("raw_energy", float("nan"))
    row["runtime"] = row.get("runtime_seconds", 0.0)
    row["wall_clock_runtime_seconds"] = row.get("runtime_seconds", 0.0)
    row["expected_operating_cost"] = row.get("expected_cost_component", float("nan"))
    row["risk_adjusted_cost"] = row.get("expected_cost_component", 0.0) + 0.25 * max(
        row.get("critical_energy_not_served_kwh", 0.0),
        0.0,
    )
    row["feasibility_after_repair"] = bool(row.get("feasibility_pass", False))
    row["pre_repair_violation"] = False
    row["post_repair_violation"] = not bool(row.get("feasibility_pass", False))
    row["pre_repair_violation_count"] = 0
    row["post_repair_violation_count"] = 0 if row["feasibility_after_repair"] else 1
    row["pre_repair_violation_magnitude"] = 0.0
    row["post_repair_violation_magnitude"] = 0.0 if row["feasibility_after_repair"] else 1.0
    row["time_to_good_solution"] = row.get("runtime_seconds", 0.0) if row["feasibility_after_repair"] else -1.0
    row["status"] = "COMPLETED"
    return row


def _summarize_baseline_payloads(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "dataset",
                "method_name",
                "payload_name",
                "scenario",
                "patch",
                "sample_count",
                "repeat_count",
                "expected_operating_cost_best",
                "expected_operating_cost_median",
                "expected_operating_cost_mean",
                "expected_operating_cost_std",
                "risk_adjusted_cost_best",
                "risk_adjusted_cost_median",
                "risk_adjusted_cost_mean",
                "risk_adjusted_cost_std",
                "runtime_seconds_median",
                "runtime_seconds_mean",
                "runtime_seconds_std",
                "feasibility_rate",
                "feasibility_after_repair_rate",
                "critical_load_served_fraction_best",
                "critical_load_served_fraction_median",
                "critical_energy_not_served_best",
                "total_energy_not_served_best",
                "max_fraction_customers_unserved_per_hour_best",
                "total_critical_infrastructure_unserved_hours_proxy_best",
                "pre_repair_violation_rate",
                "post_repair_violation_rate",
                "pre_repair_violation_median",
                "post_repair_violation_median",
                "decoded_objective_best",
                "runtime_seconds_total",
                "time_to_good_solution",
            ]
        )
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(["dataset", "method_name", "payload_name", "scenario", "patch"], sort=True):
        dataset, method, payload_name, scenario, patch = keys
        rows.append(
            {
                "dataset": dataset,
                "method_name": method,
                "payload_name": payload_name,
                "scenario": scenario,
                "patch": patch,
                "sample_count": int(len(group)),
                "repeat_count": int(group["repeat"].nunique()),
                "expected_operating_cost_best": float(group["expected_operating_cost"].min()),
                "expected_operating_cost_median": float(group["expected_operating_cost"].median()),
                "expected_operating_cost_mean": float(group["expected_operating_cost"].mean()),
                "expected_operating_cost_std": float(group["expected_operating_cost"].std(ddof=0)),
                "risk_adjusted_cost_best": float(group["risk_adjusted_cost"].min()),
                "risk_adjusted_cost_median": float(group["risk_adjusted_cost"].median()),
                "risk_adjusted_cost_mean": float(group["risk_adjusted_cost"].mean()),
                "risk_adjusted_cost_std": float(group["risk_adjusted_cost"].std(ddof=0)),
                "runtime_seconds_median": float(group["runtime_seconds"].median()),
                "runtime_seconds_mean": float(group["runtime_seconds"].mean()),
                "runtime_seconds_std": float(group["runtime_seconds"].std(ddof=0)),
                "feasibility_rate": float(group["feasibility_after_repair"].mean()),
                "feasibility_after_repair_rate": float(group["feasibility_after_repair"].mean()),
                "critical_load_served_fraction_best": float(group["critical_load_served_fraction"].max()),
                "critical_load_served_fraction_median": float(group["critical_load_served_fraction"].median()),
                "critical_energy_not_served_best": float(group["critical_energy_not_served_kwh"].min()),
                "energy_not_served_kwh_best": float(group["energy_not_served_kwh"].min()),
                "total_energy_not_served_best": float(group["energy_not_served_kwh"].min()),
                "max_fraction_customers_unserved_per_hour_best": float(
                    group["max_fraction_customers_unserved_per_hour"].min()
                ),
                "total_critical_infrastructure_unserved_hours_proxy_best": float(
                    group["total_critical_infrastructure_unserved_hours_proxy"].min()
                ),
                "pre_repair_violation_rate": float(group["pre_repair_violation"].mean()),
                "post_repair_violation_rate": float(group["post_repair_violation"].mean()),
                "pre_repair_violation_median": float(group["pre_repair_violation_magnitude"].median()),
                "post_repair_violation_median": float(group["post_repair_violation_magnitude"].median()),
                "decoded_objective_best": float(group["decoded_objective"].min()),
                "runtime_seconds_total": float(group["runtime_seconds"].sum()),
                "time_to_good_solution": float(
                    group.loc[group["feasibility_after_repair"].astype(bool), "runtime_seconds"].min()
                )
                if group["feasibility_after_repair"].astype(bool).any()
                else -1.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "method_name", "payload_name"]).reset_index(drop=True)


def _write_per_method_outputs(frame: pd.DataFrame, baseline_dir: Path) -> None:
    if frame.empty:
        return
    for method_name, group in frame.groupby("method_name", sort=True):
        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(method_name)).strip("_")
        method_dir = baseline_dir / slug
        method_dir.mkdir(parents=True, exist_ok=True)
        group.to_csv(method_dir / "repeat_metrics.csv", index=False)
        _summarize_baseline_payloads(group).to_csv(method_dir / "payload_summary.csv", index=False)


def run_classical_baseline_sweep(config: dict[str, Any], *, repeats: int, dry_run: bool = False) -> dict[str, Any]:
    """Run repeated classical baseline sweeps for the prepared Phase 3 payload set."""

    out_dir = phase3_output_dir(config)
    plan = {"config": config["name"], "output_dir": str(out_dir), "repeats": repeats, "dry_run": dry_run}
    if dry_run:
        return plan

    manifest = load_phase3_manifest(config)
    grid_case = build_grid_case_from_config(config, out_dir / "data")
    scenarios = {scenario.name: scenario for scenario in _selected_scenarios(grid_case, config)}
    payload_jobs = _payload_jobs_from_manifest(manifest)
    rows: list[dict[str, Any]] = []
    skip_rows: list[dict[str, Any]] = []
    base_seed = int(config.get("seed", config.get("dataset", {}).get("seed", 42)))
    tasks = [(repeat, job) for repeat in range(repeats) for job in payload_jobs]
    baseline_cfg = config.get("baselines", {})
    parallel_workers = max(1, int(baseline_cfg.get("parallel_workers", os.environ.get("CMPO_BASELINE_WORKERS", 1))))
    if parallel_workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
            futures = [
                executor.submit(
                    _run_baseline_payload_repeat_task,
                    config,
                    manifest["dataset"],
                    job,
                    repeat,
                    base_seed,
                )
                for repeat, job in tasks
            ]
            for future in as_completed(futures):
                task_rows, task_skips = future.result()
                rows.extend(task_rows)
                skip_rows.extend(task_skips)
    else:
        for repeat, job in tasks:
            task_rows, task_skips = _run_baseline_payload_repeat_task(
                config,
                manifest["dataset"],
                job,
                repeat,
                base_seed,
            )
            rows.extend(task_rows)
            skip_rows.extend(task_skips)

    frame = add_phase3_columns(
        rows,
        grid_case,
        dataset_name=manifest["dataset"],
        total_upgrade_cost=float(manifest.get("design_metrics", {}).get("total_upgrade_cost", 0.0)),
    )
    if not frame.empty:
        frame["total_critical_infrastructure_unserved_hours_proxy"] = frame["total_hours_critical_infrastructure_unserved"]
        frame = frame.sort_values(["dataset", "method_name", "payload_name", "repeat"]).reset_index(drop=True)
    baseline_dir = out_dir / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    repeat_metrics_path = baseline_dir / "repeat_metrics.csv"
    payload_summary_path = baseline_dir / "payload_summary.csv"
    result_path = baseline_dir / "baseline_results.csv"
    summary_path = baseline_dir / "baseline_summary.csv"
    skip_path = baseline_dir / "baseline_skip_report.csv"
    frame.to_csv(repeat_metrics_path, index=False)
    frame.to_csv(result_path, index=False)
    _summarize_baseline_payloads(frame).to_csv(payload_summary_path, index=False)
    summarize_phase3_results(frame).to_csv(summary_path, index=False)
    pd.DataFrame(skip_rows, columns=BASELINE_SKIP_COLUMNS).to_csv(skip_path, index=False)
    _write_per_method_outputs(frame, baseline_dir)
    return {
        "repeat_metrics": str(repeat_metrics_path),
        "payload_summary": str(payload_summary_path),
        "result_path": str(result_path),
        "summary_path": str(summary_path),
        "skip_report": str(skip_path),
        "rows": len(frame),
        "skipped": len(skip_rows),
    }


def read_optional_csv(path: Path) -> pd.DataFrame:
    """Read a CSV if it exists, otherwise return an empty frame."""

    return pd.read_csv(path) if path.exists() else pd.DataFrame()
