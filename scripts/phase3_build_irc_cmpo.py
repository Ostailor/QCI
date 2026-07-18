#!/usr/bin/env python
"""Build the offline 33-binary IRC-CMPO catalog and unlabeled candidate pool."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_master import load_catalog  # noqa: E402
from cmpo.irc_cmpo_surrogate import generate_feasible_candidates  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
LEGACY_BUDGET_MANIFEST = Path(
    "results/phase3/sc_cmpo/budget_master_v2/budget_master_manifest.csv"
)
LEGACY_MASTER_CANDIDATES = Path(
    "results/phase3/sc_cmpo/budget_master_v2/master_comparison.csv"
)
LEGACY_PROJECTED_CANDIDATES = Path(
    "results/phase3/sc_cmpo/budget_master_v2/decoded_portfolios.csv"
)

SOURCE_METHODS = {
    "exact MILP or CP-SAT upgrade master": "exact_milp_or_cp_sat",
    "classical Benders master": "classical_benders",
    "GPU random portfolio search": "gpu_random_feasible",
    "greedy cost-benefit portfolio selection": "greedy",
    "QUBO/quadratized upgrade master": "qubo",
    "QCi global budget master V2": "historical_qci_projected_examples",
}


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _historical_candidate_seeds(config: dict[str, Any], assets: tuple[Any, ...]) -> pd.DataFrame:
    """Import only portfolio coordinates/provenance; old proxy values are never labels."""

    classical = pd.read_csv(
        _resolve(config.get("source_master_candidates", LEGACY_MASTER_CANDIDATES))
    )
    classical = classical[classical["method"].isin(SOURCE_METHODS)].copy()
    classical["selected_asset_keys"] = classical["selected_asset_keys"].map(
        lambda value: tuple(sorted(json.loads(value)))
    )
    classical["generation_method"] = classical["method"].map(SOURCE_METHODS)
    classical["upgrade_cost"] = classical["total_upgrade_cost"].astype(float)
    classical["budget"] = classical["budget"].astype(float)
    projected = pd.read_csv(
        _resolve(config.get("source_projected_qci_candidates", LEGACY_PROJECTED_CANDIDATES))
    )
    projected = projected[
        projected["coverage_valid"].astype(bool)
        & projected["actual_budget_valid"].astype(bool)
        & projected["physical_asset_deduplication_valid"].astype(bool)
    ].copy()
    projected["selected_asset_keys"] = projected["selected_asset_keys"].map(
        lambda value: tuple(sorted(json.loads(value)))
    )
    projected["generation_method"] = "historical_qci_projected_examples"
    projected["upgrade_cost"] = projected["total_upgrade_cost"].astype(float)
    projected["budget"] = projected["budget"].astype(float)
    source = pd.concat([classical, projected], ignore_index=True, sort=False)
    source["portfolio_signature"] = source["selected_asset_keys"].map(
        lambda keys: hashlib.sha256(("[" + ",".join(keys) + "]").encode("utf-8")).hexdigest()[:20]
    )
    source["candidate_provenance_sources"] = source["generation_method"]
    source = source.sort_values(["portfolio_signature", "generation_method"])
    provenance = source.groupby("portfolio_signature")["candidate_provenance_sources"].agg(
        lambda values: json.dumps(sorted(set(values)))
    )
    seeds = source.drop_duplicates("portfolio_signature", keep="first").copy()
    seeds["candidate_provenance_sources"] = seeds["portfolio_signature"].map(provenance)
    present = set(source["generation_method"])
    if missing := set(SOURCE_METHODS.values()) - present:
        raise ValueError(f"historical candidate sources are incomplete: {sorted(missing)}")
    for asset in assets:
        seeds[asset.asset_key] = seeds["selected_asset_keys"].map(lambda keys, key=asset.asset_key: int(key in keys))
    seeds["recourse_evaluated"] = False
    seeds["old_proxy_label_used"] = False
    return seeds[
        [
            "portfolio_signature",
            "selected_asset_keys",
            "upgrade_cost",
            "budget",
            "generation_method",
            "candidate_provenance_sources",
            "recourse_evaluated",
            "old_proxy_label_used",
            *[asset.asset_key for asset in assets],
        ]
    ]


def build_irc_cmpo(
    config_path: Path | str = DEFAULT_CONFIG,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or Path(config["output_dir"]) / "build")
    targets = [output / "asset_catalog.csv", output / "candidate_portfolios.csv", output / "build_manifest.json"]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError(f"IRC-CMPO build never overwrites existing artifacts: {existing}")
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    expected_variables = int(config["model"]["core_binary_variables"])
    if len(assets) != expected_variables:
        raise ValueError(f"IRC-CMPO requires {expected_variables} physical assets; found {len(assets)}")
    budgets = pd.read_csv(
        _resolve(config.get("source_budget_manifest", LEGACY_BUDGET_MANIFEST))
    )["actual_budget"].astype(float).tolist()
    candidates = generate_feasible_candidates(
        assets,
        budgets=budgets,
        minimum_unique=int(config["surrogate"]["minimum_unique_portfolios"]),
        random_seed=int(config["surrogate"]["random_seed"]),
    )
    candidates["recourse_evaluated"] = False
    candidates["old_proxy_label_used"] = False
    candidates["candidate_provenance_sources"] = candidates["generation_method"].map(lambda value: json.dumps([value]))
    seeds = _historical_candidate_seeds(config, assets)
    candidates = (
        pd.concat([seeds, candidates], ignore_index=True)
        .drop_duplicates("portfolio_signature", keep="first")
        .head(int(config["surrogate"]["minimum_unique_portfolios"]))
    )
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asset.to_dict() for asset in assets]).to_csv(output / "asset_catalog.csv", index=False)
    csv_candidates = candidates.copy()
    csv_candidates["selected_asset_keys"] = csv_candidates["selected_asset_keys"].map(json.dumps)
    csv_candidates.to_csv(output / "candidate_portfolios.csv", index=False)
    result = {
        "schema": "cmpo.irc_cmpo.build.v1",
        "formulation": config["formulation"],
        "core_binary_variables": len(assets),
        "physical_anchors": len({asset.anchor_node for asset in assets}),
        "candidate_portfolios": int(candidates["portfolio_signature"].nunique()),
        "candidate_labels_present": False,
        "candidate_label_requirement": "evaluate every candidate with the common IEEE123 recourse oracle before fitting",
        "selected_not_selected_pairs": 0,
        "budget_slack_variables": 0,
        "continuous_policy_variables": 0,
        "qci_jobs_submitted": 0,
        "full_experiment_run": False,
    }
    _write_json_new(output / "build_manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    print(json.dumps(build_irc_cmpo(args.config, output_dir=args.output_dir), indent=2))


if __name__ == "__main__":
    main()
