#!/usr/bin/env python
"""Fit IRC-CMPO only from portfolios relabeled by the common recourse oracle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_master import IRCAsset, load_catalog  # noqa: E402
from cmpo.irc_cmpo_surrogate import fit_recourse_surrogate  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
ACTUAL_RECOURSE_METRICS = (
    "upgrade_cost",
    "critical_ens",
    "total_ens",
    "maximum_customers_unserved",
    "critical_infrastructure_outage_hours",
    "critical_load_served",
    "heldout_critical_ens",
    "heldout_total_ens",
    "feasibility",
)


def evaluate_recourse_candidates(
    candidates: pd.DataFrame,
    *,
    output_dir: Path | str,
    evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Freshly label candidates, appending one durable row after each complete replay."""

    required = {"portfolio_signature", "selected_asset_keys", "upgrade_cost", "budget", "generation_method"}
    if missing := required - set(candidates.columns):
        raise ValueError(f"candidate dataset is missing fields: {sorted(missing)}")
    if candidates["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("candidate portfolio signatures must be unique")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "portfolio_recourse_dataset.csv"
    completed: set[str] = set()
    if path.exists():
        completed = set(pd.read_csv(path)["portfolio_signature"].astype(str))
    written = 0
    for rank, row in enumerate(candidates.to_dict("records"), start=1):
        signature = str(row["portfolio_signature"])
        if signature in completed:
            continue
        if float(row["upgrade_cost"]) > float(row["budget"]) + 1e-9:
            raise ValueError(f"candidate {signature} exceeds its exact dollar budget")
        metrics = dict(evaluator(row, rank=rank))
        if int(metrics.get("training_scenario_count", -1)) != 8:
            raise ValueError(f"candidate {signature} did not use all eight training scenarios")
        if int(metrics.get("heldout_contingency_count", -1)) != 10:
            raise ValueError(f"candidate {signature} did not use all ten held-out contingencies")
        record = {
            "portfolio_signature": signature,
            "selected_asset_keys": row["selected_asset_keys"],
            "upgrade_cost": float(row["upgrade_cost"]),
            "budget": float(row["budget"]),
            "generation_method": str(row["generation_method"]),
            "candidate_provenance_sources": row.get(
                "candidate_provenance_sources", json.dumps([str(row["generation_method"])])
            ),
            **metrics,
            "recourse_evaluated": True,
        }
        pd.DataFrame([record]).to_csv(
            path,
            mode="a",
            header=not path.exists(),
            index=False,
        )
        completed.add(signature)
        written += 1
    return {
        "dataset_path": str(path),
        "freshly_evaluated": written,
        "total_evaluated": len(completed),
        "minimum_required": 3000,
        "minimum_met": len(completed) >= 3000,
    }


def _load_evaluation_module() -> Any:
    path = ROOT / "scripts/phase3_evaluate_budget_master_v2_experiment.py"
    spec = importlib.util.spec_from_file_location("irc_common_recourse_evaluator", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load common recourse evaluator {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def common_recourse_evaluator(config: dict[str, Any], output_dir: Path) -> Callable[..., dict[str, Any]]:
    """Bind the existing 12-patch consensus/full-system/held-out evaluator."""

    module = _load_evaluation_module()
    from cmpo.portfolio_decode import DecodedPortfolio
    from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config

    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    asset_by_key = {asset.asset_key: asset for asset in assets}
    budget_manifest = pd.read_csv(_resolve(config["source_budget_manifest"]))
    patch_payloads = module._patch_payloads(config)
    config_sha256 = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    payload_bundle_sha256 = hashlib.sha256(
        "".join(
            hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            for _, payload in sorted(patch_payloads.items())
        ).encode("utf-8")
    ).hexdigest()
    grid = load_public_grid(load_sc_cmpo_config(_resolve("configs/phase3_sc_cmpo_ieee123.yaml")))
    def evaluate(row: Mapping[str, Any], *, rank: int) -> dict[str, Any]:
        keys = tuple(sorted(json.loads(row["selected_asset_keys"]) if isinstance(row["selected_asset_keys"], str) else row["selected_asset_keys"]))
        budget = float(row["budget"])
        budget_row = budget_manifest.iloc[(budget_manifest["actual_budget"].astype(float) - budget).abs().argsort()[:1]].iloc[0]
        if abs(float(budget_row["actual_budget"]) - budget) > 1e-6:
            raise ValueError(f"candidate budget {budget} is not a common IEEE123 budget")
        upgrade_rows = tuple(
            {
                "asset_key": key,
                "anchor_node": asset_by_key[key].anchor_node,
                "technology": asset_by_key[key].technology,
                "installed_cost": asset_by_key[key].total_cost,
                "installed_capacity_kw": asset_by_key[key].capacity_kw,
                "installed_power_kw": asset_by_key[key].power_kw,
                "installed_energy_kwh": asset_by_key[key].energy_kwh,
                "source_row": asset_by_key[key].source_row,
                "source_payload_ids": [],
            }
            for key in keys
        )
        portfolio = DecodedPortfolio(
            budget_id=str(budget_row["budget_id"]),
            selected_asset_keys=keys,
            total_upgrade_cost=float(row["upgrade_cost"]),
            encoded_upgrade_cost=0,
            encoded_budget=0,
            actual_budget=budget,
            energy=0.0,
            upgrade_rows=upgrade_rows,
        )
        fixed = module.fix_portfolio_across_patches(portfolio, patch_payloads)
        consensus, patch_values = module.run_fixed_portfolio_consensus(
            portfolio,
            patch_payloads,
            fixed,
            method="IRC-CMPO recourse-surrogate dataset",
        )
        system_result = module.evaluate_full_system(
            "IRC-CMPO recourse-surrogate dataset", grid, patch_payloads, patch_values, consensus
        )
        heldout_result = module.evaluate_full_system_heldout(
            "IRC-CMPO recourse-surrogate dataset",
            grid,
            patch_payloads,
            patch_values,
            consensus,
            limit=10,
        )
        if system_result.get("status") != "completed" or heldout_result.get("status") != "completed":
            raise ValueError(f"fresh common-recourse evaluation failed for {portfolio.signature}")
        system = system_result["system_metrics"]
        heldout = heldout_result["heldout_summary"]
        return {
            "critical_ens": float(system["critical_energy_not_served_kwh"]),
            "total_ens": float(system["total_energy_not_served_kwh"]),
            "maximum_customers_unserved": float(system["max_fraction_customers_unserved_per_hour"]),
            "critical_infrastructure_outage_hours": float(system["total_hours_critical_infrastructure_unserved"]),
            "critical_load_served": float(system["critical_load_served_fraction"]),
            "heldout_critical_ens": float(heldout["critical_energy_not_served_kwh"]),
            "heldout_total_ens": float(heldout["total_energy_not_served_kwh"]),
            "feasibility": bool(system["full_system_feasibility"] and heldout["full_system_feasibility"]),
            "training_scenario_count": int(system["scenario_count"]),
            "heldout_contingency_count": int(heldout["heldout_count"]),
            "patch_count": len(patch_payloads),
            "consensus_algorithm": "overlap_consensus_admm",
            "projection": "full_public_system_active_power",
            "recourse_evaluator": "ieee123_global_master_shared_recourse_v2",
            "irc_config_sha256": config_sha256,
            "patch_payload_bundle_sha256": payload_bundle_sha256,
            "system_trace_id": str(system["system_trace_id"]),
            "consensus_trace_id": str(consensus.get("consensus_trace_id", "unavailable")),
            "full_trace_json_written": False,
        }

    return evaluate


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def physical_interactions(
    assets: Sequence[IRCAsset],
    *,
    related_anchor_pairs: Sequence[tuple[str, str]] = (),
) -> tuple[
    list[tuple[str, str]],
    list[tuple[str, str, str]],
    dict[tuple[str, ...], dict[str, Any]],
]:
    """Build bounded complementarity/preparedness interactions with rationale."""

    anchors: dict[str, list[str]] = {}
    for asset in assets:
        anchors.setdefault(asset.anchor_node, []).append(asset.asset_key)
    pairs: list[tuple[str, str]] = []
    cubics: list[tuple[str, str, str]] = []
    metadata: dict[tuple[str, ...], dict[str, Any]] = {}
    by_anchor_technology = {
        (asset.anchor_node, asset.technology): asset.asset_key for asset in assets
    }
    for anchor, keys in anchors.items():
        keys = sorted(keys)
        for left in range(3):
            for right in range(left + 1, 3):
                pair = (keys[left], keys[right])
                pairs.append(pair)
                metadata[pair] = {
                    "anchor_nodes": [anchor],
                    "technologies": [
                        next(asset.technology for asset in assets if asset.asset_key == key)
                        for key in pair
                    ],
                    "stress_preparedness_category": "single_anchor_der_complementarity",
                    "physical_rationale": "same-anchor DER technologies jointly alter island reserve and service recourse",
                }
    for left_anchor, right_anchor in sorted({tuple(sorted(pair)) for pair in related_anchor_pairs}):
        left_gen = by_anchor_technology[(left_anchor, "dispatchable_generation")]
        left_bess = by_anchor_technology[(left_anchor, "bess")]
        right_gen = by_anchor_technology[(right_anchor, "dispatchable_generation")]
        right_bess = by_anchor_technology[(right_anchor, "bess")]
        for cubic, category in (
            ((left_gen, left_bess, right_gen), "pcc_loss_and_forced_islanding_reserve"),
            ((left_gen, right_bess, right_gen), "local_generator_loss_and_restoration_support"),
        ):
            cubics.append(cubic)
            metadata[cubic] = {
                "anchor_nodes": [left_anchor, right_anchor],
                "technologies": [
                    next(asset.technology for asset in assets if asset.asset_key == key)
                    for key in cubic
                ],
                "stress_preparedness_category": category,
                "physical_rationale": "DER mix across overlapping IEEE123 patches couples reserve preparedness under shared feeder stress",
            }
    return pairs, cubics, metadata


def related_anchor_pairs_from_payloads(path: Path | str) -> list[tuple[str, str]]:
    from cmpo.upgrade_budget import _physical_anchor

    patches = []
    for payload_path in sorted(Path(path).glob("*.json")):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        anchor = _physical_anchor(payload)
        nodes = {str(row["node_id"]) for row in payload["sc_cmpo"].get("patch_public_nodes", ())}
        patches.append((anchor, nodes))
    return sorted(
        {
            tuple(sorted((left_anchor, right_anchor)))
            for index, (left_anchor, left_nodes) in enumerate(patches)
            for right_anchor, right_nodes in patches[index + 1 :]
            if left_anchor != right_anchor and left_nodes & right_nodes
        }
    )


def _prepare_dataset(
    frame: pd.DataFrame,
    assets: Sequence[IRCAsset],
    config: dict[str, Any],
    *,
    enforce_recourse_contract: bool,
) -> pd.DataFrame:
    frame = frame.copy()
    if enforce_recourse_contract:
        missing = set(ACTUAL_RECOURSE_METRICS) - set(frame.columns)
        if missing:
            raise ValueError(f"recourse-labeled dataset is missing actual metrics: {sorted(missing)}")
        if "recourse_evaluated" not in frame or not frame["recourse_evaluated"].astype(bool).all():
            raise ValueError("every surrogate label must come from a fresh common-recourse evaluation")
        if not frame["feasibility"].astype(bool).all():
            raise ValueError("infeasible recourse outcomes cannot train the headline surrogate")
        required_sources = set(config["surrogate"]["required_candidate_sources"])
        present_sources = set(frame["generation_method"].astype(str))
        if "candidate_provenance_sources" in frame:
            for value in frame["candidate_provenance_sources"]:
                present_sources.update(json.loads(value) if isinstance(value, str) else value)
        if missing_sources := required_sources - present_sources:
            raise ValueError(f"surrogate candidate-source coverage is incomplete: {sorted(missing_sources)}")
    if not set(asset.asset_key for asset in assets) <= set(frame.columns):
        if "selected_asset_keys" not in frame:
            raise ValueError("dataset needs binary asset columns or selected_asset_keys")
        selections = frame["selected_asset_keys"].map(
            lambda value: set(json.loads(value)) if isinstance(value, str) else set(value)
        )
        for asset in assets:
            frame[asset.asset_key] = selections.map(lambda keys, key=asset.asset_key: int(key in keys))
    target = str(config["surrogate"]["target_column"])
    if target not in frame:
        weights = config["surrogate"]["target_weights"]
        frame[target] = sum(float(weight) * frame[metric].astype(float) for metric, weight in weights.items())
    frame["heldout_recourse_objective"] = (
        frame.get("heldout_critical_ens", frame[target]).astype(float)
        + 0.25 * frame.get("heldout_total_ens", 0.0)
    )
    return frame


def fit_surrogate_file(
    config_path: Path | str,
    dataset_path: Path | str,
    *,
    output_dir: Path | str | None = None,
    minimum_portfolios: int | None = None,
    enforce_recourse_contract: bool = True,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or Path(config["output_dir"]) / "surrogate")
    targets = [output / "surrogate_model.json", output / "surrogate_metrics.csv"]
    if existing := [str(path) for path in targets if path.exists()]:
        raise FileExistsError(f"surrogate fit never overwrites artifacts: {existing}")
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    frame = _prepare_dataset(
        pd.read_csv(_resolve(dataset_path)), assets, config, enforce_recourse_contract=enforce_recourse_contract
    )
    pairs, cubics, interaction_metadata = physical_interactions(
        assets,
        related_anchor_pairs=related_anchor_pairs_from_payloads(_resolve(config["source_payload_dir"])),
    )
    fit = fit_recourse_surrogate(
        frame,
        asset_columns=[asset.asset_key for asset in assets],
        pair_interactions=pairs,
        cubic_interactions=cubics,
        target_column=str(config["surrogate"]["target_column"]),
        group_column=str(config["surrogate"]["group_column"]),
        heldout_target_column="heldout_recourse_objective",
        cost_column="upgrade_cost",
        random_seed=int(config["surrogate"]["random_seed"]),
        minimum_portfolios=int(minimum_portfolios or config["surrogate"]["minimum_unique_portfolios"]),
        interaction_prune_threshold=float(config["surrogate"]["interaction_prune_threshold"]),
        interaction_metadata=interaction_metadata,
    )
    output.mkdir(parents=True, exist_ok=True)
    model = fit.to_dict()
    model["candidate_sources"] = sorted(set(frame.get("generation_method", pd.Series(dtype=str)).astype(str)))
    model["labels"] = "fresh common-recourse outcomes; no heuristic benefit/proxy labels"
    model["old_log_capacity_benefit_used"] = False
    with (output / "surrogate_model.json").open("x", encoding="utf-8") as handle:
        json.dump(model, handle, indent=2, sort_keys=True)
        handle.write("\n")
    pd.DataFrame([fit.metrics]).to_csv(output / "surrogate_metrics.csv", index=False)
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dataset", help="CSV containing fresh common-recourse labels.")
    parser.add_argument("--evaluate-candidates", help="Unlabeled candidate CSV to replay before fitting.")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    if bool(args.dataset) == bool(args.evaluate_candidates):
        raise SystemExit("provide exactly one of --dataset or --evaluate-candidates")
    config = yaml.safe_load(_resolve(args.config).read_text(encoding="utf-8"))
    output = _resolve(args.output_dir or Path(config["output_dir"]) / "surrogate")
    dataset = args.dataset
    if args.evaluate_candidates:
        evaluation = evaluate_recourse_candidates(
            pd.read_csv(_resolve(args.evaluate_candidates)),
            output_dir=output,
            evaluator=common_recourse_evaluator(config, output),
        )
        dataset = evaluation["dataset_path"]
        if not evaluation["minimum_met"]:
            raise SystemExit("fewer than 3000 portfolios have fresh recourse labels: STOP; readiness remains NO")
    result = fit_surrogate_file(args.config, dataset, output_dir=output)
    print(json.dumps(result["metrics"], indent=2))
    if not result["metrics"]["gates_passed"]:
        raise SystemExit("surrogate gates failed: STOP; do not submit QCi jobs")


if __name__ == "__main__":
    main()
