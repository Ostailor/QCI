#!/usr/bin/env python
"""Fit create-only sparse multi-target IRC-CMPO true-recourse surrogates."""

from __future__ import annotations

import argparse
import json
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
from cmpo.irc_cmpo_surrogate import fit_multi_target_surrogates  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
REQUIRED_TARGETS = (
    "critical_ens",
    "total_ens",
    "maximum_customers_unserved",
    "critical_infrastructure_outage_hours",
    "heldout_total_ens",
)
ARTIFACT_NAMES = (
    "surrogate_model_final_prequeue_v2.json",
    "surrogate_metrics_final_prequeue_v2.csv",
    "surrogate_calibration_final_prequeue_v2.csv",
    "split_manifest_final_prequeue_v2.csv",
    "surrogate_fit_manifest_final_prequeue_v2.json",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    nodes = payload["sc_cmpo"].get("patch_public_nodes", ())
    if nodes:
        return sorted(
            (
                (
                    float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                    float(node.get("load_kw", 0.0)),
                    str(node["node_id"]),
                )
                for node in nodes
            ),
            key=lambda row: (-row[0], -row[1], row[2]),
        )[0][2]
    return sorted(str(node) for node in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])[0]


def adjacent_anchor_pairs_from_payloads(path: Path | str) -> tuple[tuple[str, str], ...]:
    """Derive neighboring master anchors from overlapping public feeder patches."""

    records: list[tuple[str, set[str]]] = []
    for payload_path in sorted(Path(path).glob("*.json")):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        anchor = _physical_anchor(payload)
        nodes = {
            str(row["node_id"])
            for row in payload["sc_cmpo"].get("patch_public_nodes", ())
        } or {str(node) for node in payload["sc_cmpo"]["upgrade_patch"]["node_ids"]}
        records.append((anchor, nodes))
    return tuple(
        sorted(
            {
                tuple(sorted((left_anchor, right_anchor)))
                for index, (left_anchor, left_nodes) in enumerate(records)
                for right_anchor, right_nodes in records[index + 1 :]
                if left_anchor != right_anchor and left_nodes & right_nodes
            }
        )
    )


def physical_interactions(
    assets: Sequence[IRCAsset],
    payload_dir: Path | str,
) -> tuple[
    tuple[tuple[str, str], ...],
    tuple[tuple[str, str, str], ...],
    dict[tuple[str, ...], dict[str, Any]],
]:
    """Return only same-anchor and public-topology-adjacent interactions."""

    by_anchor: dict[str, dict[str, str]] = {}
    technology_by_key: dict[str, str] = {}
    for asset in assets:
        by_anchor.setdefault(asset.anchor_node, {})[asset.technology] = asset.asset_key
        technology_by_key[asset.asset_key] = asset.technology
    pairs: list[tuple[str, str]] = []
    cubics: list[tuple[str, str, str]] = []
    metadata: dict[tuple[str, ...], dict[str, Any]] = {}
    for anchor, technologies in sorted(by_anchor.items()):
        keys = tuple(sorted(technologies.values()))
        for left in range(len(keys)):
            for right in range(left + 1, len(keys)):
                pair = (keys[left], keys[right])
                pairs.append(pair)
                metadata[pair] = {
                    "interaction_class": "same_anchor_technology",
                    "anchor_nodes": [anchor],
                    "technologies": [technology_by_key[key] for key in pair],
                    "physical_rationale": "co-located DER technologies jointly alter island service and reserve recourse",
                }
        cubic = tuple(
            technologies[name] for name in ("pv", "bess", "dispatchable_generation")
        )
        cubics.append(cubic)
        metadata[cubic] = {
            "interaction_class": "same_anchor_three_technology",
            "anchor_nodes": [anchor],
            "technologies": ["pv", "bess", "dispatchable_generation"],
            "physical_rationale": "the complete local DER mix couples renewable supply, storage reserve, and firm generation",
        }
    for left_anchor, right_anchor in adjacent_anchor_pairs_from_payloads(payload_dir):
        left = by_anchor[left_anchor]
        right = by_anchor[right_anchor]
        for technologies in (
            ("pv", "pv"),
            ("bess", "bess"),
            ("dispatchable_generation", "dispatchable_generation"),
            ("bess", "dispatchable_generation"),
            ("dispatchable_generation", "bess"),
        ):
            pair = (left[technologies[0]], right[technologies[1]])
            pairs.append(pair)
            metadata[pair] = {
                "interaction_class": "adjacent_anchor",
                "anchor_nodes": [left_anchor, right_anchor],
                "technologies": list(technologies),
                "physical_rationale": "overlapping public feeder patches couple reserve and service decisions",
            }
        for cubic in (
            (left["bess"], left["dispatchable_generation"], right["dispatchable_generation"]),
            (left["dispatchable_generation"], right["bess"], right["dispatchable_generation"]),
        ):
            cubics.append(cubic)
            metadata[cubic] = {
                "interaction_class": "adjacent_anchor_preparedness",
                "anchor_nodes": [left_anchor, right_anchor],
                "technologies": [technology_by_key[key] for key in cubic],
                "physical_rationale": "storage and firm generation across overlapping islands affect stress preparedness",
            }
    return tuple(dict.fromkeys(pairs)), tuple(dict.fromkeys(cubics)), metadata


def _validate_dataset_contract(
    frame: pd.DataFrame,
    assets: Sequence[IRCAsset],
    *,
    group_column: str,
    targets: Sequence[str],
    minimum_portfolios: int,
    required_sources: Sequence[str],
) -> pd.DataFrame:
    required = {
        group_column,
        "selected_asset_keys",
        "upgrade_cost",
        "technology_mix",
        "selected_asset_count",
        "true_fixed_upgrade_recourse",
        "used_fraction_completion",
        "feasibility",
        *targets,
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"surrogate dataset is missing required fields: {sorted(missing)}")
    if frame[group_column].astype(str).duplicated().any():
        raise ValueError("portfolio signatures must be unique before surrogate fitting")
    if frame[group_column].astype(str).nunique() < minimum_portfolios:
        raise ValueError(f"surrogate requires at least {minimum_portfolios} unique portfolios")
    if not frame["true_fixed_upgrade_recourse"].astype(bool).all():
        raise ValueError("every label must come from true fixed-upgrade recourse")
    if frame["used_fraction_completion"].astype(bool).any():
        raise ValueError("_fractions_to_values completion cannot label the IRC-CMPO surrogate")
    if not frame["feasibility"].astype(bool).all():
        raise ValueError("infeasible recourse outcomes cannot enter the headline surrogate")
    present_sources: set[str] = set()
    if "generation_method" in frame:
        present_sources.update(frame["generation_method"].astype(str))
    if "candidate_provenance_sources" in frame:
        for value in frame["candidate_provenance_sources"]:
            present_sources.update(json.loads(value) if isinstance(value, str) else value)
    if missing_sources := set(required_sources) - present_sources:
        raise ValueError(f"portfolio provenance coverage is incomplete: {sorted(missing_sources)}")
    working = frame.copy()
    selected = working["selected_asset_keys"].map(
        lambda value: set(json.loads(value)) if isinstance(value, str) else set(value)
    )
    for asset in assets:
        if asset.asset_key not in working:
            working[asset.asset_key] = selected.map(lambda keys, key=asset.asset_key: int(key in keys))
    asset_columns = [asset.asset_key for asset in assets]
    if not working[asset_columns].isin([0, 1]).all().all():
        raise ValueError("asset-selection surrogate features must be natively binary")
    return working


def _validate_split_contract(
    manifest: pd.DataFrame,
    signatures: Sequence[str],
    *,
    group_column: str,
) -> None:
    if {group_column, "split"} - set(manifest.columns):
        raise ValueError("split manifest must contain portfolio_signature and split")
    if manifest[group_column].astype(str).duplicated().any():
        raise ValueError("a portfolio signature appears more than once in the split manifest")
    if set(manifest[group_column].astype(str)) != set(map(str, signatures)):
        raise ValueError("split manifest does not cover exactly the labeled portfolios")
    if set(manifest["split"].astype(str)) != {"train", "validation", "test"}:
        raise ValueError("split manifest must contain train, validation, and test partitions")
    total = len(manifest)
    expected = {"train": int(0.60 * total), "validation": int(0.20 * total)}
    expected["test"] = total - expected["train"] - expected["validation"]
    actual = manifest["split"].value_counts().to_dict()
    if any(int(actual.get(name, 0)) != count for name, count in expected.items()):
        raise ValueError(f"split manifest is not exact 60/20/20: expected {expected}, found {actual}")


def _write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv_new(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, index=False)


def fit_surrogate_file(
    config_path: Path | str,
    dataset_path: Path | str,
    *,
    split_manifest_path: Path | str,
    output_dir: Path | str | None = None,
    minimum_portfolios: int | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or Path(config["output_dir"]) / "surrogate")
    targets = tuple(output / name for name in ARTIFACT_NAMES)
    if existing := [str(path) for path in targets if path.exists()]:
        raise FileExistsError(f"surrogate artifacts are create-only: {existing}")
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    surrogate_config = config["surrogate"]
    target_columns = tuple(surrogate_config.get("targets", REQUIRED_TARGETS))
    if target_columns != REQUIRED_TARGETS:
        raise ValueError(f"headline surrogate targets must be exactly {list(REQUIRED_TARGETS)}")
    minimum = int(minimum_portfolios or surrogate_config["minimum_unique_portfolios"])
    frame = _validate_dataset_contract(
        pd.read_csv(_resolve(dataset_path)),
        assets,
        group_column=str(surrogate_config["group_column"]),
        targets=target_columns,
        minimum_portfolios=minimum,
        required_sources=tuple(surrogate_config.get("required_candidate_sources", ())),
    )
    supplied_manifest = pd.read_csv(_resolve(split_manifest_path))
    group_column = str(surrogate_config["group_column"])
    _validate_split_contract(
        supplied_manifest,
        frame[group_column].astype(str).tolist(),
        group_column=group_column,
    )
    pairs, cubics, metadata = physical_interactions(
        assets,
        _resolve(config["source_payload_dir"]),
    )
    fit = fit_multi_target_surrogates(
        frame,
        asset_columns=[asset.asset_key for asset in assets],
        pair_interactions=pairs,
        cubic_interactions=cubics,
        target_columns=target_columns,
        group_column=group_column,
        minimum_portfolios=minimum,
        random_seed=int(surrogate_config["random_seed"]),
        interaction_metadata=metadata,
    )
    fitted_membership = fit.split_manifest.set_index(group_column)["split"].astype(str).to_dict()
    supplied_membership = supplied_manifest.set_index(group_column)["split"].astype(str).to_dict()
    if fitted_membership != supplied_membership:
        raise ValueError("fit split differs from the create-only public dataset split manifest")

    model = {
        "schema": "cmpo.irc_cmpo.multi_target_surrogate.final_prequeue.v2",
        "targets": {
            name: {
                "terms": list(fit.targets[name].terms),
                "metrics": fit.targets[name].metrics,
                "ridge": fit.targets[name].ridge,
            }
            for name in target_columns
        },
        "gates_passed": bool(fit.gates_passed),
        "maximum_degree": max(
            (
                int(term["degree"])
                for target in target_columns
                for term in fit.targets[target].terms
            ),
            default=0,
        ),
        "label_contract": "true fixed-upgrade SLSQP/MILP recourse only",
        "old_fraction_completion_used": False,
        "old_log_capacity_benefit_used": False,
        "qci_jobs_submitted": 0,
    }
    metric_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for target in target_columns:
        metrics = fit.targets[target].metrics
        metric_rows.append(
            {
                "target": target,
                **{
                    key: value
                    for key, value in metrics.items()
                    if key != "calibration_by_upgrade_cost_band"
                },
                "ridge": fit.targets[target].ridge,
                "term_count": len(fit.targets[target].terms),
            }
        )
        calibration_rows.extend(
            {"target": target, **row}
            for row in metrics.get("calibration_by_upgrade_cost_band", ())
        )
    fit_manifest = {
        "schema": "cmpo.irc_cmpo.surrogate_fit_manifest.final_prequeue.v2",
        "unique_portfolios": int(frame[group_column].nunique()),
        "split_counts": supplied_manifest["split"].value_counts().sort_index().to_dict(),
        "same_or_adjacent_physical_pair_terms": len(pairs),
        "physically_interpretable_cubic_terms": len(cubics),
        "surrogate_valid": bool(fit.gates_passed),
        "payload_build_permitted": bool(fit.gates_passed),
        "qci_jobs_submitted": 0,
    }
    _write_json_new(targets[0], model)
    _write_csv_new(targets[1], pd.DataFrame(metric_rows))
    _write_csv_new(targets[2], pd.DataFrame(calibration_rows))
    _write_csv_new(targets[3], supplied_manifest)
    _write_json_new(targets[4], fit_manifest)
    return fit_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dataset", default="results/phase3/irc_cmpo/dataset/portfolio_labels.csv")
    parser.add_argument("--split-manifest", default="results/phase3/irc_cmpo/dataset/split_manifest.csv")
    parser.add_argument("--output-dir")
    parser.add_argument("--minimum-portfolios", type=int)
    args = parser.parse_args()
    print(
        json.dumps(
            fit_surrogate_file(
                args.config,
                args.dataset,
                split_manifest_path=args.split_manifest,
                output_dir=args.output_dir,
                minimum_portfolios=args.minimum_portfolios,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
