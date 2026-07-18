#!/usr/bin/env python
"""Build six create-only, quantized IRC-CMPO payloads without contacting QCi."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_feasibility import (  # noqa: E402
    derive_local_feasibility,
    verify_local_feasibility_encoding,
)
from cmpo.irc_cmpo_master import (  # noqa: E402
    IRCAsset,
    build_scalarized_irc_master,
    load_catalog,
)
from cmpo.irc_cmpo_scaling import scale_payload_for_dirac3  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
REQUIRED_TARGETS = (
    "critical_ens",
    "total_ens",
    "maximum_customers_unserved",
    "critical_infrastructure_outage_hours",
    "heldout_total_ens",
)
PAYLOAD_DIRECTORY = "payloads_final_prequeue_v3"
UNQUANTIZED_DIRECTORY = "unquantized_payloads_final_prequeue_v3"
MANIFEST_NAME = "payload_manifest_final_prequeue_v3.csv"
AUDIT_CSV_NAME = "coefficient_audit_final_prequeue_v3.csv"
AUDIT_MD_NAME = "coefficient_audit_final_prequeue_v3.md"


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


def _validate_surrogate(
    model: Mapping[str, Any], gate_config: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    """Require every fitted target gate before returning total-ENS terms."""

    if not bool(model.get("gates_passed", False)):
        raise ValueError("all surrogate gates must pass before IRC-CMPO payload construction")
    targets = model.get("targets")
    if not isinstance(targets, Mapping) or set(targets) != set(REQUIRED_TARGETS):
        raise ValueError(f"surrogate targets must be exactly {list(REQUIRED_TARGETS)}")
    maximum_nrmse = float(gate_config["normalized_rmse_maximum"])
    minimum_top = float(gate_config["top_decile_recall_minimum"])
    minimum_pareto = float(gate_config["pareto_front_recall_minimum"])
    default_rank = float(gate_config["total_ens_spearman_minimum"])
    critical_rank = float(gate_config.get("critical_ens_spearman_minimum", default_rank))
    for name in REQUIRED_TARGETS:
        target = targets[name]
        metrics = target.get("metrics", {})
        rank_required = not (
            name == "critical_ens" and bool(metrics.get("nearly_constant", False))
        )
        minimum_rank = critical_rank if name == "critical_ens" else default_rank
        metric_gate = bool(
            float(metrics.get("normalized_rmse", math.inf)) <= maximum_nrmse
            and (
                not rank_required
                or float(metrics.get("spearman_rank_correlation", -math.inf)) >= minimum_rank
            )
            and (
                not rank_required
                or float(metrics.get("top_decile_recall", -math.inf)) >= minimum_top
            )
            and (
                not rank_required
                or float(metrics.get("pareto_front_recall", -math.inf)) >= minimum_pareto
            )
            and bool(metrics.get("all_coefficients_finite", False))
            and int(metrics.get("degree", 4)) <= 3
        )
        if not bool(metrics.get("gate_passed", False)) or not metric_gate:
            raise ValueError(f"surrogate gates failed for {name}")
        terms = target.get("terms", ())
        if any(
            int(term.get("degree", len(term.get("asset_keys", ())))) > 3
            or not math.isfinite(float(term["coefficient"]))
            for term in terms
        ):
            raise ValueError(f"surrogate {name} contains invalid degree or coefficient")
    total_terms = tuple(dict(term) for term in targets["total_ens"].get("terms", ()))
    if not total_terms:
        raise ValueError("the total_ens surrogate contains no polynomial terms")
    return total_terms


def derive_training_target_normalization(
    dataset_path: Path | str,
    split_manifest_path: Path | str,
    *,
    target: str = "total_ens",
) -> dict[str, float | str | int]:
    """Derive an affine target normalization using training portfolios only."""

    labels = pd.read_csv(dataset_path)
    split = pd.read_csv(split_manifest_path)
    required_labels = {"portfolio_signature", target}
    if missing := required_labels - set(labels):
        raise ValueError(f"dataset lacks normalization fields: {sorted(missing)}")
    if {"portfolio_signature", "split"} - set(split):
        raise ValueError("split manifest lacks portfolio_signature or split")
    if labels["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("normalization dataset contains duplicate portfolio signatures")
    if split["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("normalization split contains duplicate portfolio signatures")
    joined = labels[["portfolio_signature", target]].merge(
        split[["portfolio_signature", "split"]],
        on="portfolio_signature",
        how="inner",
        validate="one_to_one",
    )
    training = joined.loc[joined["split"].astype(str) == "train", target].astype(float)
    if training.empty or not np.isfinite(training.to_numpy()).all():
        raise ValueError("training normalization requires finite training target values")
    offset = float(training.min())
    scale = float(training.max() - offset)
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("training target range must be finite and positive")
    return {
        "target": target,
        "offset": offset,
        "scale": scale,
        "training_count": int(len(training)),
        "derivation": "training_min_and_range_only",
    }


def normalize_surrogate_terms(
    terms: Sequence[Mapping[str, Any]], *, offset: float, scale: float
) -> tuple[dict[str, Any], ...]:
    """Return terms for ``(J_hat - offset) / scale`` without changing degree."""

    if not math.isfinite(offset) or not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("surrogate normalization requires finite offset and positive scale")
    normalized: list[dict[str, Any]] = []
    found_constant = False
    for raw in terms:
        term = dict(raw)
        keys = tuple(term.get("asset_keys", ()))
        coefficient = float(term["coefficient"])
        if not keys:
            coefficient -= offset
            found_constant = True
        term["coefficient"] = coefficient / scale
        normalized.append(term)
    if not found_constant:
        normalized.append(
            {
                "coefficient": -offset / scale,
                "asset_keys": [],
                "degree": 0,
                "physical_interpretation": "training-target normalization offset",
            }
        )
    return tuple(normalized)


def derive_hardware_resolvable_cost_weights(
    assets: Sequence[IRCAsset],
    *,
    effective_dynamic_range: int,
    multipliers: Sequence[float],
) -> dict[str, Any]:
    """Derive six deterministic lambdas from the cheapest catalog asset.

    The first positive lambda places the cheapest asset's normalized cost on
    two Dirac-3 coefficient levels before feasibility penalties are added;
    one level proved too tie-prone in the preserved v2 stochastic audit.
    Quantized payload gates and exact solves remain authoritative afterward.
    """

    if effective_dynamic_range < 2:
        raise ValueError("effective dynamic range must be at least two")
    if len(multipliers) != 6 or tuple(multipliers) != (0, 2, 4, 8, 16, 32):
        raise ValueError("cost-weight multipliers must be [0, 2, 4, 8, 16, 32]")
    costs = [float(asset.total_cost) for asset in assets]
    if not costs or any(not math.isfinite(cost) or cost <= 0.0 for cost in costs):
        raise ValueError("cost-weight derivation requires finite positive catalog costs")
    maximum_catalog_cost = math.fsum(costs)
    minimum_asset_cost = min(costs)
    minimum_lambda = maximum_catalog_cost / (effective_dynamic_range * minimum_asset_cost)
    weights = [float(multiplier) * minimum_lambda for multiplier in multipliers]
    return {
        "weights": weights,
        "minimum_resolvable_lambda": minimum_lambda,
        "minimum_asset_cost": minimum_asset_cost,
        "maximum_catalog_cost": maximum_catalog_cost,
        "effective_dynamic_range": int(effective_dynamic_range),
        "multipliers": list(multipliers),
        "derivation": "lambda_min = catalog_sum / (dynamic_range * minimum_asset_cost)",
    }


def derive_anchor_feasibility_penalties(
    assets: Sequence[IRCAsset],
    surrogate_terms: Sequence[Mapping[str, Any]],
    local_rows: Sequence[Any],
    *,
    cost_weight: float,
    effective_dynamic_range: int,
) -> dict[str, Any]:
    """Derive the smallest documented repair bound for each physical anchor.

    For every invalid local pattern, this computes the cheapest *objective
    change bound* among its directly enumerated adequate patterns.  Any
    monomial touching a changed bit can change by at most its absolute
    coefficient.  The maximum of those minimum repair bounds, plus a strict
    hardware-grid margin, is sufficient to dominate the invalid indicator
    without applying one destructive global penalty to every anchor.
    """

    if not math.isfinite(cost_weight) or cost_weight < 0.0:
        raise ValueError("cost weight must be finite and nonnegative")
    if effective_dynamic_range < 2:
        raise ValueError("effective dynamic range must be at least two")
    by_key = {asset.asset_key: asset for asset in assets}
    maximum_catalog_cost = math.fsum(asset.total_cost for asset in assets)
    if maximum_catalog_cost <= 0.0:
        raise ValueError("feasibility penalty requires positive catalog cost")
    rows: dict[str, dict[str, Any]] = {}
    for anchor in local_rows:
        keys = tuple(map(str, anchor.asset_keys))
        if len(keys) != 3 or set(keys) - set(by_key):
            raise ValueError("local feasibility row references an invalid asset triple")
        invalid = [item for item in anchor.patterns if not bool(item.adequate)]
        adequate = [item for item in anchor.patterns if bool(item.adequate)]
        if invalid and not adequate:
            raise ValueError(f"anchor {anchor.anchor_node} has no feasible repair pattern")
        repair_bounds: list[float] = []
        for bad in invalid:
            alternatives: list[float] = []
            for good in adequate:
                changed = {
                    key
                    for key, before, after in zip(keys, bad.pattern, good.pattern, strict=True)
                    if int(before) != int(after)
                }
                surrogate_bound = math.fsum(
                    abs(float(term["coefficient"]))
                    for term in surrogate_terms
                    if changed & set(map(str, term.get("asset_keys", ())))
                )
                cost_bound = cost_weight * math.fsum(
                    by_key[key].total_cost for key in changed
                ) / maximum_catalog_cost
                alternatives.append(surrogate_bound + cost_bound)
            repair_bounds.append(min(alternatives))
        worst_repair_bound = max(repair_bounds, default=0.0)
        strict_margin = max(1.0 / effective_dynamic_range, 0.05 * worst_repair_bound)
        rho = worst_repair_bound + strict_margin if invalid else 0.0
        rows[str(anchor.anchor_node)] = {
            "rho_feasibility": rho,
            "worst_minimum_repair_bound": worst_repair_bound,
            "strict_margin": strict_margin if invalid else 0.0,
            "invalid_pattern_count": len(invalid),
        }
    return {
        "by_anchor": rows,
        "maximum_rho_feasibility": max(
            (float(row["rho_feasibility"]) for row in rows.values()), default=0.0
        ),
        "cost_weight": float(cost_weight),
        "derivation": (
            "max_invalid_pattern(min_adequate_repair(sum_abs_touched_surrogate_terms + "
            "lambda*changed_catalog_cost/catalog_sum)) + strict_grid_margin"
        ),
    }


def _local_constraints(
    local_rows: Sequence[Any], penalties_by_anchor: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    constraints = [
        {
            "coefficient": float(penalties_by_anchor[str(anchor.anchor_node)]["rho_feasibility"]),
            "asset_keys": list(anchor.asset_keys),
            "pattern": list(pattern),
            "anchor_node": str(anchor.anchor_node),
            "source_patch_ids": list(anchor.source_patch_ids),
        }
        for anchor in local_rows
        for pattern in anchor.invalid_patterns
        if float(penalties_by_anchor[str(anchor.anchor_node)]["rho_feasibility"]) > 0.0
    ]
    if not constraints:
        # This is valid only when public existing resources make every local
        # pattern adequate.  The empty list deliberately adds no blanket rule.
        return []
    return constraints


def _validation_rows(
    dataset_path: Path,
    split_manifest_path: Path,
    assets: Sequence[IRCAsset],
) -> tuple[list[dict[str, int]], list[float], list[float]]:
    frame = pd.read_csv(dataset_path)
    manifest = pd.read_csv(split_manifest_path)
    if {"portfolio_signature", "split"} - set(manifest):
        raise ValueError("split manifest lacks portfolio_signature or split")
    if manifest["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("split manifest contains duplicate portfolio signatures")
    test_signatures = set(
        manifest.loc[manifest["split"].astype(str) == "test", "portfolio_signature"].astype(str)
    )
    if not test_signatures:
        raise ValueError("post-quantization validation requires a nonempty test split")
    if {"portfolio_signature", "selected_asset_keys", "total_ens", "upgrade_cost"} - set(frame):
        raise ValueError("true-recourse dataset lacks required validation fields")
    frame = frame[frame["portfolio_signature"].astype(str).isin(test_signatures)].copy()
    if len(frame) != len(test_signatures):
        raise ValueError("test split contains signatures absent from the true-recourse dataset")
    asset_keys = [asset.asset_key for asset in assets]
    states: list[dict[str, int]] = []
    signatures: set[tuple[int, ...]] = set()
    for row in frame.to_dict("records"):
        selected = set(json.loads(row["selected_asset_keys"]))
        if selected - set(asset_keys):
            raise ValueError("validation portfolio references an unknown physical asset")
        state = {f"y::{key}": int(key in selected) for key in asset_keys}
        signature = tuple(state.values())
        if signature in signatures:
            raise ValueError("post-quantization validation requires unique portfolio states")
        signatures.add(signature)
        states.append(state)
    actual = frame["total_ens"].astype(float).tolist()
    costs = frame["upgrade_cost"].astype(float).tolist()
    if len(states) < 2 or not all(math.isfinite(value) for value in (*actual, *costs)):
        raise ValueError("post-quantization validation requires at least two finite observations")
    return states, actual, costs


def _scalarized_validation_actual(
    total_ens: Sequence[float],
    costs: Sequence[float],
    *,
    cost_weight: float,
    maximum_catalog_cost: float,
    resilience_offset: float = 0.0,
    resilience_scale: float = 1.0,
) -> list[float]:
    """Return the true feasible-state target represented by ``H_lambda``."""

    if (
        len(total_ens) != len(costs)
        or maximum_catalog_cost <= 0.0
        or not math.isfinite(resilience_offset)
        or not math.isfinite(resilience_scale)
        or resilience_scale <= 0.0
    ):
        raise ValueError("scalarized validation values require matched rows and positive catalog cost")
    return [
        (float(ens) - resilience_offset) / resilience_scale
        + float(cost_weight) * float(cost) / maximum_catalog_cost
        for ens, cost in zip(total_ens, costs, strict=True)
    ]


def _write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv_new(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, index=False)


def build_payloads(
    config_path: Path | str = DEFAULT_CONFIG,
    *,
    dataset_path: Path | str,
    split_manifest_path: Path | str,
    surrogate_model_path: Path | str,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Build exactly six offline payloads after all surrogate/scaling gates pass."""

    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    model = json.loads(_resolve(surrogate_model_path).read_text(encoding="utf-8"))
    raw_surrogate_terms = _validate_surrogate(model, config["surrogate"]["gates"])
    if bool(config["scalarization"].get("hard_budget", True)):
        raise ValueError("final IRC-CMPO payloads cannot contain a hard budget")

    output = _resolve(output_dir or config["output_dir"])
    payload_dir = output / PAYLOAD_DIRECTORY
    unquantized_dir = output / UNQUANTIZED_DIRECTORY
    manifest_path = output / MANIFEST_NAME
    audit_csv = output / AUDIT_CSV_NAME
    audit_md = output / AUDIT_MD_NAME
    scaled_paths = [payload_dir / f"lambda_{index:02d}.json" for index in range(6)]
    unquantized_paths = [unquantized_dir / f"lambda_{index:02d}.json" for index in range(6)]
    targets = [manifest_path, audit_csv, audit_md, *scaled_paths, *unquantized_paths]
    if existing := [str(path) for path in targets if path.exists()]:
        raise FileExistsError(f"final prequeue payload artifacts are create-only: {existing}")

    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    expected_variables = int(config.get("model", {}).get("core_binary_variables", len(assets)))
    if len(assets) != expected_variables:
        raise ValueError(f"expected {expected_variables} deduplicated physical assets, found {len(assets)}")
    normalization = derive_training_target_normalization(
        _resolve(dataset_path), _resolve(split_manifest_path)
    )
    surrogate_terms = normalize_surrogate_terms(
        raw_surrogate_terms,
        offset=float(normalization["offset"]),
        scale=float(normalization["scale"]),
    )
    weight_derivation = derive_hardware_resolvable_cost_weights(
        assets,
        effective_dynamic_range=int(config["scaling"]["maximum_dynamic_range"]),
        multipliers=config["scalarization"]["cost_weight_multipliers"],
    )
    lambdas = tuple(float(value) for value in weight_derivation["weights"])
    configured_lambdas = tuple(float(value) for value in config["scalarization"]["cost_weights"])
    if len(configured_lambdas) != 6 or not np.allclose(configured_lambdas, lambdas, rtol=1e-12, atol=1e-12):
        raise ValueError("configured cost weights do not match their public-catalog derivation")
    if len(lambdas) != 6 or len(set(lambdas)) != 6 or any(value < 0.0 for value in lambdas):
        raise ValueError("final IRC-CMPO payload build requires six distinct nonnegative lambdas")
    public_payloads = _load_public_payloads(_resolve(config["source_payload_dir"]))
    local_rows = derive_local_feasibility(public_payloads, assets, rho_feasibility=1.0)
    if any(not verify_local_feasibility_encoding(anchor) for anchor in local_rows):
        raise ValueError("a data-derived local-feasibility encoding failed direct enumeration")
    states, actual, costs = _validation_rows(
        _resolve(dataset_path), _resolve(split_manifest_path), assets
    )
    maximum_catalog_cost = math.fsum(asset.total_cost for asset in assets)
    gate_config = config["surrogate"]["gates"]
    thresholds = {
        "minimum_spearman": float(gate_config["total_ens_spearman_minimum"]),
        "maximum_normalized_rmse": float(gate_config["normalized_rmse_maximum"]),
        "minimum_top_decile_recall": float(gate_config["top_decile_recall_minimum"]),
        "minimum_pareto_recall": float(gate_config["pareto_front_recall_minimum"]),
    }

    built: list[tuple[dict[str, Any], dict[str, Any]]] = []
    manifest_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    penalty_derivations: list[dict[str, Any]] = []
    for index, cost_weight in enumerate(lambdas):
        penalty = derive_anchor_feasibility_penalties(
            assets,
            surrogate_terms,
            local_rows,
            cost_weight=cost_weight,
            effective_dynamic_range=int(config["scaling"]["maximum_dynamic_range"]),
        )
        constraints = _local_constraints(local_rows, penalty["by_anchor"])
        penalty_derivations.append(penalty)
        raw = build_scalarized_irc_master(
            assets,
            cost_weight=cost_weight,
            surrogate_terms=surrogate_terms,
            local_feasibility_terms=constraints,
        )
        raw["resilience_normalization"] = dict(normalization)
        raw["cost_weight_derivation"] = dict(weight_derivation)
        raw["feasibility_penalty_derivation"] = dict(penalty)
        raw["qci_submission"] = {"permitted": False, "jobs_submitted": 0}
        scalarized_actual = _scalarized_validation_actual(
            actual,
            costs,
            cost_weight=cost_weight,
            maximum_catalog_cost=maximum_catalog_cost,
            resilience_offset=float(normalization["offset"]),
            resilience_scale=float(normalization["scale"]),
        )
        scaled = scale_payload_for_dirac3(
            raw,
            validation_states=states,
            validation_actual_values=scalarized_actual,
            validation_costs=costs,
            gate_thresholds=thresholds,
        )
        audit = scaled["dirac3_scaling"]["audit"]
        post = scaled["dirac3_scaling"]["post_quantization_validation"]
        if float(audit["dynamic_range"]) > 200.0 + 1e-12:
            raise ValueError("scaled payload exceeds the confirmed 200:1 dynamic-range gate")
        if not bool(post["gates_passed"]):
            raise ValueError("post-quantization total_ens surrogate gates failed")
        built.append((raw, scaled))
        manifest_rows.append(
            {
                "lambda_index": index,
                "cost_weight": cost_weight,
                "scaled_payload_path": str(scaled_paths[index]),
                "unquantized_payload_path": str(unquantized_paths[index]),
                "num_variables": int(scaled["num_variables"]),
                "total_num_levels": int(sum(scaled["num_levels"])),
                "maximum_degree": int(scaled["max_degree"]),
                "local_invalid_pattern_count": len(constraints),
                "maximum_rho_feasibility": penalty["maximum_rho_feasibility"],
                "rho_feasibility_by_anchor": json.dumps(
                    {
                        anchor: values["rho_feasibility"]
                        for anchor, values in penalty["by_anchor"].items()
                    },
                    sort_keys=True,
                ),
                "resilience_offset": normalization["offset"],
                "resilience_scale": normalization["scale"],
                "cost_weight_derivation": weight_derivation["derivation"],
                "dynamic_range": audit["dynamic_range"],
                "minimum_level_separation": audit["minimum_distinct_level_separation"],
                "post_quantization_gates_passed": bool(post["gates_passed"]),
                "projection_used": False,
                "qci_jobs_submitted": 0,
            }
        )
        audit_rows.append(
            {
                **manifest_rows[-1],
                "maximum_material_coefficient": audit["maximum_material_coefficient"],
                "minimum_material_coefficient": audit["minimum_material_coefficient"],
                "quantization_grid": audit["quantization_grid"],
                "material_term_count": audit["material_term_count"],
                "degree_distribution": json.dumps(audit["degree_distribution"], sort_keys=True),
                "component_statistics": json.dumps(audit["component_statistics"], sort_keys=True),
                **{f"post_{key}": value for key, value in post["quantized"].items()},
            }
        )

    for index, (raw, scaled) in enumerate(built):
        _write_json_new(unquantized_paths[index], raw)
        _write_json_new(scaled_paths[index], scaled)
    manifest = pd.DataFrame(manifest_rows)
    audit_frame = pd.DataFrame(audit_rows)
    _write_csv_new(manifest_path, manifest)
    _write_csv_new(audit_csv, audit_frame)
    audit_markdown = "\n".join(
        (
            "# IRC-CMPO Final Prequeue Coefficient Audit",
            "",
            "This versioned audit preserves the earlier coefficient_audit artifacts.",
            "No QCi job was submitted. Constants and removed zeros are not material coefficients.",
            "",
            f"Feasibility penalty derivation: `{penalty_derivations[0]['derivation']}`.",
            "Each lambda and anchor uses its own strict minimum-repair objective bound; values are in the CSV.",
            "",
            "```csv",
            audit_frame.to_csv(index=False).rstrip(),
            "```",
            "",
        )
    )
    audit_md.parent.mkdir(parents=True, exist_ok=True)
    with audit_md.open("x", encoding="utf-8") as handle:
        handle.write(audit_markdown)
    return {
        "payload_count": len(built),
        "manifest_path": str(manifest_path),
        "coefficient_audit_csv": str(audit_csv),
        "coefficient_audit_markdown": str(audit_md),
        "feasibility_penalty_derivations": penalty_derivations,
        "resilience_normalization": normalization,
        "cost_weight_derivation": weight_derivation,
        "post_quantization_gates_passed": True,
        "qci_jobs_submitted": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--dataset", default="results/phase3/irc_cmpo/dataset/portfolio_labels.csv"
    )
    parser.add_argument(
        "--split-manifest", default="results/phase3/irc_cmpo/dataset/split_manifest.csv"
    )
    parser.add_argument(
        "--surrogate-model",
        default="results/phase3/irc_cmpo/surrogate/surrogate_model_final_prequeue_v2.json",
    )
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    print(
        json.dumps(
            build_payloads(
                args.config,
                dataset_path=args.dataset,
                split_manifest_path=args.split_manifest,
                surrogate_model_path=args.surrogate_model,
                output_dir=args.output_dir,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
