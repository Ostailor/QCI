#!/usr/bin/env python
"""Run matched classical portfolio reconstructions at every common IEEE123 budget."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budgeted_portfolio import (  # noqa: E402
    allocate_shared_fractions,
    enforce_hard_budget,
)
from cmpo.full_system_dispatch import evaluate_full_system, evaluate_full_system_heldout  # noqa: E402
from cmpo.matched_problem_baselines import solve_matched_payload  # noqa: E402
from cmpo.overlap_consensus import reconstruct_patch_values, run_method_consensus  # noqa: E402
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402
from cmpo.upgrade_budget import (  # noqa: E402
    BudgetLevel,
    derive_ieee123_budget_sweep,
    load_ieee123_upgrade_catalog,
    technology_cost_totals,
)


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_sweep.yaml")
QCI_METHOD = "QCi SC-CMPO"


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _config(path: Path | str) -> dict[str, Any]:
    return yaml.safe_load(_resolve(path).read_text(encoding="utf-8"))


def _payloads(directory: Path) -> dict[str, dict[str, Any]]:
    rows = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))}
    rows = {name: payload for name, payload in rows.items() if payload.get("sc_cmpo", {}).get("public_benchmark") == "ieee123_opendss"}
    if len(rows) != 12:
        raise ValueError(f"budget experiment requires the same 12 IEEE123 patches, found {len(rows)}")
    if {int(payload["sc_cmpo"]["scenario_count"]) for payload in rows.values()} != {8}:
        raise ValueError("budget experiment requires the same eight training scenarios in every patch")
    return rows


def _budgets(config: dict[str, Any], output_dir: Path) -> list[BudgetLevel]:
    derivation_path = output_dir / "budget_derivation.json"
    if derivation_path.exists():
        raw = json.loads(derivation_path.read_text(encoding="utf-8"))["budgets"]
        return [
            BudgetLevel(
                budget_id=str(row["budget_id"]),
                amount=float(row["amount"]),
                discrete_portfolio_cost=float(row["discrete_portfolio_cost"]),
                derivation=str(row["derivation"]),
                source_refs=tuple(str(item) for item in row["source_refs"]),
            )
            for row in raw
        ]
    source = _resolve(config["source_payload_dir"])
    system = _resolve(config["source_system_dir"])
    return derive_ieee123_budget_sweep(
        load_ieee123_upgrade_catalog(source),
        qci_metrics_path=system / "qci_system_metrics.csv",
        baseline_metrics_path=system / "baseline_system_metrics.csv",
    )


def _method_preferences(
    config: dict[str, Any],
    methods: Iterable[str],
    totals: Mapping[str, float],
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    path = _resolve(config["source_system_dir"]) / "upgrade_plan_comparison.csv"
    frame = pd.read_csv(path)
    frame = frame[frame["benchmark"] == "ieee123_opendss"].copy()
    preferences: dict[str, dict[str, float]] = {}
    sources: dict[str, str] = {}
    for method in methods:
        rows = frame[frame["method"] == method].copy()
        if rows.empty:
            raise ValueError(f"no existing IEEE123 portfolio evidence for method {method}")
        headline = rows[rows["headline_selection"].astype(str).str.lower().isin({"true", "1"})]
        if not headline.empty:
            rows = headline
            source = "existing challenge/headline-selected reconstructed portfolio"
        else:
            first_replicate = sorted(rows["consensus_replicate"].astype(str).unique())[0]
            rows = rows[rows["consensus_replicate"].astype(str) == first_replicate]
            source = f"existing reconstructed portfolio {first_replicate}"
        technology_cost = rows.groupby("technology")["installed_cost"].sum().to_dict()
        preferences[method] = {
            technology: min(1.0, max(0.0, float(technology_cost.get(technology, 0.0)) / total))
            for technology, total in totals.items()
        }
        sources[method] = f"{source}: {path}"
    return preferences, sources


def _apply_budget_fractions(
    payload: Mapping[str, Any],
    source_values: Mapping[str, float],
    fractions: Mapping[str, float],
) -> dict[str, float]:
    """Replace only upgrade decisions while retaining the method's recourse policy."""

    variable_names = {str(variable["name"]) for variable in payload["variables"]}
    missing = variable_names - set(source_values)
    if missing:
        raise ValueError(f"source solution is incomplete: {sorted(missing)}")
    values = {name: float(source_values[name]) for name in variable_names}
    mapping = {
        "pv_capacity_fraction": float(fractions.get("pv", 0.0)),
        "bess_energy_fraction": float(fractions.get("bess", 0.0)),
        "bess_power_fraction": float(fractions.get("bess", 0.0)),
        "dispatchable_capacity_fraction": float(fractions.get("dispatchable_generation", 0.0)),
    }
    values.update({name: min(1.0, max(0.0, value)) for name, value in mapping.items()})
    values["upgrade_select_pv"] = float(values["pv_capacity_fraction"] > 1e-12)
    values["upgrade_select_bess"] = float(values["bess_energy_fraction"] > 1e-12)
    values["upgrade_select_dispatchable"] = float(values["dispatchable_capacity_fraction"] > 1e-12)
    return values


def _fix_payload_upgrade_fractions(
    payload: Mapping[str, Any],
    fractions: Mapping[str, float],
) -> dict[str, Any]:
    """Clone a payload and impose upgrade decisions as exact solver bounds."""

    fixed = copy.deepcopy(dict(payload))
    pv = min(1.0, max(0.0, float(fractions.get("pv", 0.0))))
    bess = min(1.0, max(0.0, float(fractions.get("bess", 0.0))))
    dispatch = min(1.0, max(0.0, float(fractions.get("dispatchable_generation", 0.0))))
    targets = {
        "pv_capacity_fraction": pv,
        "bess_energy_fraction": bess,
        "bess_power_fraction": bess,
        "dispatchable_capacity_fraction": dispatch,
        "upgrade_select_pv": float(pv > 1e-12),
        "upgrade_select_bess": float(bess > 1e-12),
        "upgrade_select_dispatchable": float(dispatch > 1e-12),
    }
    seen = set()
    for variable in fixed["variables"]:
        name = str(variable["name"])
        if name in targets:
            variable["lower_bound"] = targets[name]
            variable["upper_bound"] = targets[name]
            seen.add(name)
    missing = set(targets) - seen
    if missing:
        raise ValueError(f"SC-CMPO payload is missing upgrade variables: {sorted(missing)}")
    fixed["budget_fixed_upgrade_fractions"] = targets
    return fixed


def _stable_seed(method: str, budget_id: str, payload_name: str) -> int:
    digest = hashlib.sha256(f"{method}:{budget_id}:{payload_name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _challenge_selected_qci_values(
    config: dict[str, Any],
    payloads: Mapping[str, Mapping[str, Any]],
    budget: float,
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    """Select one of the 30 preserved QCi system samples under the hard cap."""

    system_dir = _resolve(config["source_system_dir"])
    metrics = pd.read_csv(system_dir / "qci_repeat_system_metrics.csv")
    metrics = metrics[(metrics["benchmark"] == "ieee123_opendss") & (metrics["total_upgrade_cost"] <= budget + 1e-6)].copy()
    if metrics.empty:
        raise ValueError(f"no preserved QCi system sample fits budget {budget}")
    metrics["_feasible_rank"] = ~metrics["full_system_feasibility"].map(
        lambda value: value if isinstance(value, bool) else str(value).lower() in {"true", "1"}
    )
    metrics["_critical_served_rank"] = -pd.to_numeric(metrics["critical_load_served_fraction"], errors="raise")
    order = [
        "_feasible_rank",
        "critical_energy_not_served_kwh",
        "expected_critical_infrastructure_unserved_hours",
        "max_fraction_customers_unserved_per_hour",
        "_critical_served_rank",
        "risk_adjusted_cost",
        "runtime_seconds",
        "consensus_replicate",
    ]
    selected = metrics.sort_values(order, kind="stable").iloc[0]
    replicate = str(selected["consensus_replicate"])
    patches = pd.read_csv(system_dir / "qci_patch_solutions.csv")
    patches = patches[
        (patches["benchmark"] == "ieee123_opendss")
        & (patches["consensus_replicate"].astype(str) == replicate)
    ]
    values: dict[str, dict[str, float]] = {}
    for row in patches.to_dict("records"):
        name = str(row["payload_name"])
        if name in payloads:
            values[name] = {
                str(key): float(value)
                for key, value in json.loads(str(row["solution_values_json"])).items()
            }
    missing = sorted(set(payloads) - set(values))
    if missing:
        raise ValueError(f"QCi sample {replicate} is missing patches: {missing}")
    metadata = {
        "consensus_replicate": replicate,
        "sample_index": int(replicate.removeprefix("qci_sample_")),
        "sample_pool_size": 30,
        "raw_sample_portfolio_cost": float(selected["total_upgrade_cost"]),
        "selection_rule": (
            "among the 30 preserved system-aligned QCi samples that fit the hard budget: lexicographic "
            "full-system feasibility, critical ENS, critical-infrastructure outage hours, maximum customers "
            "unserved, critical-load served, risk-adjusted cost, runtime, sample index"
        ),
        "source": str(system_dir / "qci_repeat_system_metrics.csv"),
    }
    return values, metadata


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def evaluate_budgeted_methods(
    config_path: Path | str,
    output_dir: Path | str,
    *,
    methods: list[str],
    result_prefix: str,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    config = _config(config_path)
    output = _resolve(output_dir)
    payload_dir = _resolve(config["source_payload_dir"])
    payloads = _payloads(payload_dir)
    catalog = load_ieee123_upgrade_catalog(payload_dir)
    budgets = _budgets(config, output)
    totals = technology_cost_totals(catalog)
    preferences, preference_sources = _method_preferences(config, methods, totals)
    plan = {
        "budget_count": len(budgets),
        "method_count": len(methods),
        "comparison_point_count": len(budgets) * len(methods),
        "methods": methods,
        "patch_count": len(payloads),
        "training_scenario_count": 8,
        "heldout_contingency_count": int(config["experiment"]["heldout_contingencies"]),
    }
    if dry_run:
        return {"dry_run": True, **plan}
    target = output / f"{result_prefix}_budgeted_results.csv"
    if target.exists() and not overwrite:
        raise FileExistsError(f"budgeted method results already exist: {target}")
    base_config = load_sc_cmpo_config(_resolve(config["base_config"]))
    grid = load_public_grid(base_config)
    system_rows: list[dict[str, Any]] = []
    heldout_rows: list[dict[str, Any]] = []
    upgrade_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    trace_dir = output / "traces" / result_prefix
    trace_dir.mkdir(parents=True, exist_ok=True)
    for level in budgets:
        for method in methods:
            started = time.perf_counter()
            try:
                fractions = allocate_shared_fractions(
                    catalog,
                    level.amount,
                    preference=preferences[method],
                )
                patch_solver_trace: list[dict[str, Any]] = []
                if method == QCI_METHOD:
                    qci_values, qci_selection = _challenge_selected_qci_values(config, payloads, level.amount)
                    proposal_values = {
                        name: _apply_budget_fractions(payload, qci_values[name], fractions)
                        for name, payload in payloads.items()
                    }
                    solution_rows = [
                        {
                            "method": method,
                            "benchmark": "ieee123_opendss",
                            "payload_name": name,
                            "solution_id": f"budget::{level.budget_id}::{method}::{name}",
                            "solution_values": values,
                            "runtime_seconds": 0.0,
                        }
                        for name, values in proposal_values.items()
                    ]
                    method_solution_source = qci_selection["source"]
                else:
                    qci_selection = None
                    solution_rows = []
                    for name, payload in payloads.items():
                        fixed_payload = _fix_payload_upgrade_fractions(payload, fractions)
                        solved = solve_matched_payload(
                            name,
                            fixed_payload,
                            method,
                            _stable_seed(method, level.budget_id, name),
                        )
                        if solved["status"] != "completed":
                            raise ValueError(f"{name} budget-constrained solve failed: {solved['failure_reason']}")
                        solution_rows.append(solved)
                        patch_solver_trace.append(
                            {
                                key: value
                                for key, value in solved.items()
                                if key not in {"solution_values"}
                            }
                        )
                    method_solution_source = "fresh matched classical solve with upgrade variables fixed to the hard-budget portfolio"
                consensus = run_method_consensus(payloads, solution_rows)
                if consensus.get("status") != "completed" or not consensus.get("converged"):
                    raise ValueError(f"overlap consensus failed: {consensus.get('failure_reason', '')}")
                patch_values = reconstruct_patch_values(payloads, consensus["consensus_values"])
                projected = evaluate_full_system(
                    method,
                    grid,
                    payloads,
                    patch_values,
                    consensus,
                    patch_runtime_seconds=sum(float(row.get("runtime_seconds", 0.0)) for row in solution_rows),
                )
                if projected.get("status") != "completed":
                    raise ValueError(f"full-system projection failed: {projected.get('failure_reason', '')}")
                heldout = evaluate_full_system_heldout(
                    method,
                    grid,
                    payloads,
                    patch_values,
                    consensus,
                    limit=int(config["experiment"]["heldout_contingencies"]),
                )
                if heldout.get("status") != "completed":
                    raise ValueError(f"held-out projection failed: {heldout.get('failure_reason', '')}")
                charged_cost = enforce_hard_budget(projected["upgrade_plan"], level.amount)
                metrics = projected["system_metrics"]
                runtime = time.perf_counter() - started
                trace_path = trace_dir / f"{level.budget_id}__{method.replace('/', '_').replace(' ', '_')}.json"
                trace = {
                    "schema": "cmpo.ieee123_budget_trace.v1",
                    "budget": level.to_dict(),
                    "method": method,
                    "method_preference": preferences[method],
                    "preference_source": preference_sources[method],
                    "method_solution_source": method_solution_source,
                    "qci_sample_selection": qci_selection,
                    "classical_patch_solver_trace": patch_solver_trace,
                    "shared_fractions": fractions,
                    "consensus": consensus,
                    "system": projected,
                    "heldout": heldout,
                    "hard_budget_check": {"charged_cost": charged_cost, "budget": level.amount, "passed": True},
                }
                trace_path.write_text(json.dumps(trace, indent=2, default=_json_default), encoding="utf-8")
                system_rows.append(
                    {
                        "budget_id": level.budget_id,
                        "budget": level.amount,
                        "budget_derivation": level.derivation,
                        "method": method,
                        "total_upgrade_cost": charged_cost,
                        "budget_utilization": charged_cost / level.amount,
                        "critical_ens": metrics["critical_energy_not_served_kwh"],
                        "total_ens": metrics["total_energy_not_served_kwh"],
                        "critical_load_served_fraction": metrics["critical_load_served_fraction"],
                        "maximum_customers_unserved_per_hour": metrics["max_fraction_customers_unserved_per_hour"],
                        "critical_infrastructure_outage_hours": metrics["expected_critical_infrastructure_unserved_hours"],
                        "feasibility": metrics["full_system_feasibility"],
                        "runtime": runtime,
                        "system_trace_id": metrics["system_trace_id"],
                        "trace_path": str(trace_path),
                        "patch_count": metrics["payload_count"],
                        "training_scenario_count": metrics["scenario_count"],
                        "consensus_algorithm": "existing overlap_consensus.run_method_consensus",
                        "projection": metrics["projection_scope"],
                        "physical_asset_deduplication": metrics["upgrade_cost_scored_once_per_physical_asset"],
                        "preference_source": preference_sources[method],
                        "method_solution_source": method_solution_source,
                        "qci_sample_index": "" if qci_selection is None else qci_selection["sample_index"],
                        "qci_sample_pool_size": "" if qci_selection is None else qci_selection["sample_pool_size"],
                        "qci_sample_selection_rule": "" if qci_selection is None else qci_selection["selection_rule"],
                    }
                )
                summary = heldout["heldout_summary"]
                heldout_rows.append(
                    {
                        "budget_id": level.budget_id,
                        "budget": level.amount,
                        "method": method,
                        "total_upgrade_cost": charged_cost,
                        "budget_utilization": charged_cost / level.amount,
                        "heldout_critical_ens": summary["critical_energy_not_served_kwh"],
                        "heldout_total_ens": summary["total_energy_not_served_kwh"],
                        "heldout_critical_load_served_fraction": summary["critical_load_served_fraction"],
                        "heldout_maximum_customers_unserved_per_hour": summary["max_fraction_customers_unserved_per_hour"],
                        "heldout_critical_infrastructure_outage_hours": summary["total_hours_critical_infrastructure_unserved"],
                        "heldout_count": summary["heldout_count"],
                        "feasibility": summary["full_system_feasibility"],
                        "runtime": runtime,
                        "system_trace_id": metrics["system_trace_id"],
                        "heldout_trace_id": summary["heldout_trace_id"],
                        "trace_path": str(trace_path),
                    }
                )
                upgrade_rows.extend(
                    {
                        "budget_id": level.budget_id,
                        "budget": level.amount,
                        "method": method,
                        "system_trace_id": metrics["system_trace_id"],
                        **asset,
                    }
                    for asset in projected["upgrade_plan"]
                )
            except Exception as exc:
                failures.append(
                    {
                        "budget_id": level.budget_id,
                        "budget": level.amount,
                        "method": method,
                        "failure_reason": f"{type(exc).__name__}: {exc}",
                    }
                )
    _write_csv(system_rows, target)
    _write_csv(heldout_rows, output / f"{result_prefix}_budgeted_heldout_results.csv")
    _write_csv(upgrade_rows, output / f"{result_prefix}_budgeted_upgrade_plan.csv")
    _write_csv(failures, output / f"{result_prefix}_budgeted_failures.csv")
    summary = {
        **plan,
        "completed": len(system_rows),
        "failed": len(failures),
        "results_csv": str(target),
    }
    (output / f"{result_prefix}_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_budgeted_baselines(
    config_path: Path | str,
    output_dir: Path | str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = _config(config_path)
    methods = [str(method) for method in config["methods"] if str(method) != QCI_METHOD]
    return evaluate_budgeted_methods(
        config_path,
        output_dir,
        methods=methods,
        result_prefix="classical",
        overwrite=overwrite,
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default="results/phase3/sc_cmpo/budget_frontier")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_budgeted_baselines(args.config, args.output_dir, overwrite=args.overwrite, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
