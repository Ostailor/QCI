#!/usr/bin/env python
"""Exactly and stochastically validate six IRC-CMPO payloads offline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_master import IRCAsset, load_catalog  # noqa: E402
from cmpo.irc_cmpo_recourse import (  # noqa: E402
    FixedRecourseCache,
    evaluate_fixed_upgrade_recourse,
)
from cmpo.irc_cmpo_validation import (  # noqa: E402
    assess_exact_suite,
    assess_exact_true_recourse,
    assess_stochastic_suite,
    compare_exact_top_portfolios,
    run_local_stochastic_proxy,
    solve_binary_hamiltonian_exact,
)
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
DEFAULT_PUBLIC_CONFIG = Path("configs/phase3_sc_cmpo_ieee123.yaml")
DEFAULT_MANIFEST = Path("results/phase3/irc_cmpo/payload_manifest_final_prequeue_v3.csv")
DEFAULT_OUTPUT_DIRECTORY = "offline_validation_final_prequeue_v4"
EXACT_JSON = "exact_validation_final_prequeue_v4.json"
EXACT_CSV = "exact_candidates_final_prequeue_v4.csv"
STOCHASTIC_JSON = "stochastic_validation_final_prequeue_v4.json"
STOCHASTIC_CSV = "stochastic_samples_final_prequeue_v4.csv"
MANIFEST_JSON = "offline_validation_manifest_final_prequeue_v4.json"


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _load_public_payloads(path: Path) -> dict[str, dict[str, Any]]:
    payloads = {
        item.stem: json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json"))
    }
    if len(payloads) != 12:
        raise ValueError(f"expected 12 pinned IEEE123 payloads, found {len(payloads)}")
    return payloads


def _state_from_selected(selected: Sequence[str], assets: Sequence[IRCAsset]) -> dict[str, int]:
    selected_set = set(map(str, selected))
    known = {asset.asset_key for asset in assets}
    if unknown := selected_set - known:
        raise ValueError(f"portfolio contains unknown public assets: {sorted(unknown)}")
    return {f"y::{asset.asset_key}": int(asset.asset_key in selected_set) for asset in assets}


def _selected_from_state(state: Mapping[str, int], assets: Sequence[IRCAsset]) -> tuple[str, ...]:
    result: list[str] = []
    for asset in assets:
        name = f"y::{asset.asset_key}"
        value = state.get(name)
        if type(value) is not int or value not in {0, 1}:
            raise ValueError(f"state coordinate {name} is not natively binary")
        if value:
            result.append(asset.asset_key)
    return tuple(result)


def _local_feasibility(payload: Mapping[str, Any], state: Mapping[str, int]) -> bool:
    for constraint in payload.get("local_feasibility_constraints", ()):
        pattern = tuple(
            int(state[f"y::{key}"])
            for key in constraint["asset_keys"]
        )
        if pattern == tuple(map(int, constraint["pattern"])):
            return False
    return True


def _dataset_rows(
    dataset_path: Path,
    assets: Sequence[IRCAsset],
    *,
    cost_weight: float,
    maximum_catalog_cost: float,
    resilience_offset: float = 0.0,
    resilience_scale: float = 1.0,
) -> list[dict[str, Any]]:
    frame = pd.read_csv(dataset_path)
    required = {"selected_asset_keys", "upgrade_cost", "total_ens", "portfolio_signature"}
    if missing := required - set(frame):
        raise ValueError(f"true-recourse dataset lacks fields: {sorted(missing)}")
    if frame["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("offline validation dataset contains duplicate portfolio signatures")
    rows: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        selected = json.loads(row["selected_asset_keys"])
        cost = float(row["upgrade_cost"])
        total_ens = float(row["total_ens"])
        if not math.isfinite(cost) or not math.isfinite(total_ens):
            raise ValueError("offline validation dataset contains non-finite metrics")
        rows.append(
            {
                "portfolio_signature": str(row["portfolio_signature"]),
                "state": _state_from_selected(selected, assets),
                "upgrade_cost": cost,
                "total_ens": total_ens,
                "true_score": (total_ens - resilience_offset) / resilience_scale
                + cost_weight * cost / maximum_catalog_cost,
            }
        )
    if len(rows) < 2:
        raise ValueError("offline validation requires at least two true-recourse portfolios")
    return rows


def _result_metrics(
    result: Any,
    *,
    cost_weight: float,
    maximum_catalog_cost: float,
    resilience_offset: float = 0.0,
    resilience_scale: float = 1.0,
) -> dict[str, float]:
    if not bool(getattr(result, "feasibility", False)):
        raise ValueError("true fixed-upgrade recourse returned an infeasible system plan")
    required = (
        "total_ens",
        "critical_ens",
        "maximum_customers_unserved",
        "critical_infrastructure_outage_hours",
        "heldout_total_ens",
        "heldout_critical_ens",
        "upgrade_cost",
    )
    values = {name: float(getattr(result, name)) for name in required}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("true recourse returned a non-finite headline metric")
    if not math.isfinite(resilience_offset) or not math.isfinite(resilience_scale) or resilience_scale <= 0.0:
        raise ValueError("true score normalization requires finite offset and positive scale")
    values["true_score"] = (
        (values["total_ens"] - resilience_offset) / resilience_scale
        + cost_weight * values["upgrade_cost"] / maximum_catalog_cost
    )
    values["feasibility"] = float(bool(getattr(result, "feasibility")))
    return values


def _write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv_new(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        pd.DataFrame(rows).to_csv(handle, index=False)


def validate_offline(
    config_path: Path | str = DEFAULT_CONFIG,
    *,
    manifest_path: Path | str,
    dataset_path: Path | str,
    output_dir: Path | str | None = None,
    stochastic_samples_per_method: int = 30,
    stochastic_sweeps: int = 200,
) -> dict[str, Any]:
    """Run exact and stochastic gates with one shared fixed-recourse cache."""

    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or Path(config["output_dir"]) / DEFAULT_OUTPUT_DIRECTORY)
    targets = {
        "exact_json": output / EXACT_JSON,
        "exact_csv": output / EXACT_CSV,
        "stochastic_json": output / STOCHASTIC_JSON,
        "stochastic_csv": output / STOCHASTIC_CSV,
        "manifest_json": output / MANIFEST_JSON,
    }
    if existing := [str(path) for path in targets.values() if path.exists()]:
        raise FileExistsError(f"offline validation artifacts are create-only: {existing}")

    manifest = pd.read_csv(_resolve(manifest_path)).sort_values("lambda_index")
    if len(manifest) != 6 or manifest["lambda_index"].astype(int).tolist() != list(range(6)):
        raise ValueError("offline validation requires exactly the six ordered lambda payloads")
    if not manifest["post_quantization_gates_passed"].astype(bool).all():
        raise ValueError("offline validation refuses a payload with failed quantization gates")
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    public_payloads = _load_public_payloads(_resolve(config["source_payload_dir"]))
    public_config = _resolve(config.get("source_sc_cmpo_config", DEFAULT_PUBLIC_CONFIG))
    grid = load_public_grid(load_sc_cmpo_config(public_config))
    solver_cache = FixedRecourseCache()
    result_cache: dict[tuple[int, ...], Any] = {}
    names = tuple(f"y::{asset.asset_key}" for asset in assets)
    maximum_catalog_cost = math.fsum(asset.total_cost for asset in assets)
    if maximum_catalog_cost <= 0.0:
        raise ValueError("public catalog cost denominator must be positive")

    exact_reports: list[dict[str, Any]] = []
    quantization_reports: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    stochastic_reports: list[dict[str, Any]] = []
    stochastic_rows: list[dict[str, Any]] = []
    for manifest_row in manifest.to_dict("records"):
        index = int(manifest_row["lambda_index"])
        cost_weight = float(manifest_row["cost_weight"])
        scaled = json.loads(Path(manifest_row["scaled_payload_path"]).read_text(encoding="utf-8"))
        unquantized = json.loads(
            Path(manifest_row["unquantized_payload_path"]).read_text(encoding="utf-8")
        )
        if scaled["num_variables"] != len(assets) or scaled["num_levels"] != [2] * len(assets):
            raise ValueError("offline payload variable domains differ from the physical asset catalog")
        normalization = scaled.get("resilience_normalization", {})
        resilience_offset = float(normalization.get("offset", 0.0))
        resilience_scale = float(normalization.get("scale", 1.0))
        if not math.isfinite(resilience_offset) or not math.isfinite(resilience_scale) or resilience_scale <= 0.0:
            raise ValueError("offline payload has invalid resilience normalization")
        feasible = lambda state, payload=scaled: _local_feasibility(payload, state)  # noqa: E731
        exact_scaled = solve_binary_hamiltonian_exact(
            scaled["polynomial_terms"], names, top_k=10, feasibility=feasible
        )
        exact_raw = solve_binary_hamiltonian_exact(
            unquantized["polynomial_terms"], names, top_k=10, feasibility=feasible
        )
        quantization = compare_exact_top_portfolios(
            exact_raw,
            exact_scaled,
            unquantized_terms=unquantized["polynomial_terms"],
            quantized_terms=scaled["polynomial_terms"],
        )
        quantization_reports.append({"lambda_index": index, "cost_weight": cost_weight, **quantization})

        def recourse(state: Mapping[str, int]) -> dict[str, float]:
            signature = tuple(int(state[name]) for name in names)
            if signature not in result_cache:
                selected = _selected_from_state(state, assets)
                result_cache[signature] = evaluate_fixed_upgrade_recourse(
                    public_payloads,
                    assets,
                    selected,
                    grid=grid,
                    heldout_limit=10,
                    solver_cache=solver_cache,
                )
            return _result_metrics(
                result_cache[signature],
                cost_weight=cost_weight,
                maximum_catalog_cost=maximum_catalog_cost,
                resilience_offset=resilience_offset,
                resilience_scale=resilience_scale,
            )

        dataset = _dataset_rows(
            _resolve(dataset_path),
            assets,
            cost_weight=cost_weight,
            maximum_catalog_cost=maximum_catalog_cost,
            resilience_offset=resilience_offset,
            resilience_scale=resilience_scale,
        )
        exact_report = assess_exact_true_recourse(
            exact_scaled,
            dataset,
            hamiltonian_terms=scaled["polynomial_terms"],
            recourse_evaluator=recourse,
        )
        exact_report.update({"lambda_index": index, "cost_weight": cost_weight})
        exact_reports.append(exact_report)
        for row in exact_report["top_ten"]:
            exact_rows.append(
                {
                    "lambda_index": index,
                    "cost_weight": cost_weight,
                    **{key: value for key, value in row.items() if key != "state"},
                    "state": json.dumps(row["state"], sort_keys=True),
                    "selected_asset_keys": json.dumps(_selected_from_state(row["state"], assets)),
                    "projection_used": False,
                }
            )
        best_dataset = min(float(row["true_score"]) for row in dataset)
        stochastic = run_local_stochastic_proxy(
            terms=scaled["polynomial_terms"],
            variable_names=names,
            exact_optimum_energy=exact_scaled.optimum_energy,
            feasibility=feasible,
            recourse_evaluator=recourse,
            best_true_recourse=best_dataset,
            samples_per_method=stochastic_samples_per_method,
            annealing_sweeps=stochastic_sweeps,
            random_seed=2026 + index,
            nontrivial_lambda=cost_weight > 0.0,
        )
        samples = stochastic.pop("samples")
        stochastic.update({"lambda_index": index, "cost_weight": cost_weight})
        stochastic_reports.append(stochastic)
        stochastic_rows.extend(
            {
                "lambda_index": index,
                "cost_weight": cost_weight,
                **{key: value for key, value in row.items() if key != "state"},
                "state": json.dumps(row["state"], sort_keys=True),
                "selected_asset_keys": json.dumps(_selected_from_state(row["state"], assets)),
                "projection_used": False,
            }
            for row in samples
        )

    exact_suite = assess_exact_suite(
        exact_reports,
        quantization_comparisons=quantization_reports,
    )
    stochastic_suite = assess_stochastic_suite(stochastic_reports)
    exact_artifact = {
        "schema": "cmpo.irc_cmpo.exact_offline.final_prequeue.v4",
        "reports": exact_reports,
        "quantization_comparisons": quantization_reports,
        "suite": exact_suite,
        "projection_used": False,
        "qci_jobs_submitted": 0,
    }
    stochastic_artifact = {
        "schema": "cmpo.irc_cmpo.stochastic_offline.final_prequeue.v4",
        "reports": stochastic_reports,
        "suite": stochastic_suite,
        "projection_used": False,
        "qci_jobs_submitted": 0,
    }
    output_manifest = {
        "schema": "cmpo.irc_cmpo.offline_validation_manifest.final_prequeue.v4",
        "lambda_count": 6,
        "exact_hamiltonian_valid": bool(exact_suite["gates_passed"]),
        "local_stochastic_valid": bool(stochastic_suite["gates_passed"]),
        "fixed_recourse_cache_hits": solver_cache.hits,
        "fixed_recourse_cache_misses": solver_cache.misses,
        "unique_portfolios_recourse_evaluated": len(result_cache),
        "projection_used": False,
        "qci_jobs_submitted": 0,
        "readiness_decision_deferred_to_final_audit": True,
    }
    _write_json_new(targets["exact_json"], exact_artifact)
    _write_csv_new(targets["exact_csv"], exact_rows)
    _write_json_new(targets["stochastic_json"], stochastic_artifact)
    _write_csv_new(targets["stochastic_csv"], stochastic_rows)
    _write_json_new(targets["manifest_json"], output_manifest)
    return {
        **output_manifest,
        "exact_validation_path": str(targets["exact_json"]),
        "stochastic_validation_path": str(targets["stochastic_json"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
    )
    parser.add_argument(
        "--dataset", default="results/phase3/irc_cmpo/dataset/portfolio_labels.csv"
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--samples-per-method", type=int, default=30)
    parser.add_argument("--annealing-sweeps", type=int, default=200)
    args = parser.parse_args()
    print(
        json.dumps(
            validate_offline(
                args.config,
                manifest_path=args.manifest,
                dataset_path=args.dataset,
                output_dir=args.output_dir,
                stochastic_samples_per_method=args.samples_per_method,
                stochastic_sweeps=args.annealing_sweeps,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
