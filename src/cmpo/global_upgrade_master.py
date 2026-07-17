"""One global, deduplicated IEEE123 upgrade master per hard budget."""

from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from cmpo.budget_encoding import (
    BudgetEncoding,
    add_squared_equality_terms,
    encode_budget,
)
from cmpo.budget_penalty_certificate import build_penalty_certificate
from cmpo.upgrade_budget import BudgetLevel, UpgradeAssetOption


SCENARIOS = (
    "normal",
    "renewable_shortfall",
    "demand_surge",
    "pcc_loss",
    "local_generator_loss",
    "forced_islanding",
    "restoration",
    "combined_high_stress",
)


@dataclass(frozen=True)
class GlobalMasterBuild:
    payload: dict[str, Any]
    budget_encoding: BudgetEncoding
    local_validation: dict[str, Any]


@dataclass(frozen=True)
class BruteForceOptimum:
    selected_asset_keys: tuple[str, ...]
    actual_cost: float
    energy: float


def _variable(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "lower_bound": 0.0,
        "upper_bound": 1.0,
        "bounds": [0.0, 1.0],
        "encoding_type": "integer",
    }


def _term(coefficient: float, powers: Mapping[str, int], component: str) -> dict[str, Any]:
    compact = {str(name): int(power) for name, power in powers.items() if int(power)}
    return {
        "coefficient": float(coefficient),
        "powers": compact,
        "degree": sum(compact.values()),
        "component": component,
    }


def _asset_record(asset: UpgradeAssetOption, benefit: float) -> dict[str, Any]:
    return {
        **asdict(asset),
        "source_payload_ids": list(asset.source_payload_ids),
        "source_patch_ids": list(asset.source_patch_ids),
        "local_benefit": float(benefit),
    }


def _benefit(asset: UpgradeAssetOption) -> float:
    technology = {
        "dispatchable_generation": 5.0,
        "bess": 4.0,
        "pv": 3.0,
    }[asset.technology]
    scale = max(asset.capacity_kw, asset.power_kw, asset.energy_kwh / 4.0, 1.0)
    return technology * math.log1p(scale)


def _source_checksums(catalog: Sequence[UpgradeAssetOption], source_root: Path | None) -> list[dict[str, str]]:
    names = sorted({name for asset in catalog for name in asset.source_payload_ids})
    rows: list[dict[str, str]] = []
    for name in names:
        path = (source_root / name) if source_root is not None else Path(name)
        rows.append(
            {
                "payload_name": name,
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "unavailable",
            }
        )
    return rows


def _normalize_terms(terms: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float, float]:
    terms = [term for term in terms if term["powers"]]
    nonconstant = [abs(float(term["coefficient"])) for term in terms]
    maximum = max(nonconstant, default=1.0)
    scale = 1.0 / maximum if maximum > 1.0 else 1.0
    normalized = [{**term, "coefficient": float(term["coefficient"] * scale)} for term in terms]
    return normalized, maximum, scale


def _build_master(
    catalog: Sequence[UpgradeAssetOption],
    budget: BudgetLevel,
    *,
    currency_unit: float,
    safety_multiplier: float,
    source_payload_dir: Path | None,
    benefit_overrides: Mapping[str, float] | None = None,
    include_policy: bool = True,
) -> GlobalMasterBuild:
    assets = sorted(catalog, key=lambda item: item.asset_key)
    if len({asset.asset_key for asset in assets}) != len(assets):
        raise ValueError("global master catalog must be deduplicated before costing")
    costs = {asset.asset_key: asset.total_cost for asset in assets}
    encoding = encode_budget(costs, budget.amount, currency_unit)
    variables: list[dict[str, Any]] = []
    terms: list[dict[str, Any]] = []
    one_hot_groups: list[dict[str, Any]] = []

    for asset in assets:
        selected = f"upgrade::{asset.asset_key}::selected"
        unselected = f"upgrade::{asset.asset_key}::not_selected"
        variables.extend((_variable(selected), _variable(unselected)))
        one_hot_groups.append(
            {
                "group_id": asset.asset_key,
                "variables": [selected, unselected],
                "semantics": "exactly one of installed/not-installed for this independent physical asset",
            }
        )
        add_squared_equality_terms(
            terms,
            {selected: 1, unselected: 1},
            1,
            12.0,
            component="upgrade_one_hot",
        )
        benefit = float((benefit_overrides or {}).get(asset.asset_key, _benefit(asset)))
        cost_fraction = asset.total_cost / max(budget.amount, 1.0)
        terms.append(_term(0.5 * cost_fraction - benefit, {selected: 1}, "upgrade_value"))

    coverage_constraints: list[dict[str, Any]] = []
    for anchor in sorted({asset.anchor_node for asset in assets}):
        anchor_assets = [asset for asset in assets if asset.anchor_node == anchor]
        slack_zero = f"anchor_coverage_slack::{anchor}::bit0"
        slack_one = f"anchor_coverage_slack::{anchor}::bit1"
        variables.extend((_variable(slack_zero), _variable(slack_one)))
        weights = {
            **{f"upgrade::{asset.asset_key}::selected": 1 for asset in anchor_assets},
            slack_zero: -1,
            slack_one: -2,
        }
        add_squared_equality_terms(
            terms,
            weights,
            1,
            30.0,
            component="anchor_coverage",
        )
        coverage_constraints.append(
            {
                "anchor_node": anchor,
                "upgrade_variables": [
                    f"upgrade::{asset.asset_key}::selected" for asset in anchor_assets
                ],
                "excess_selection_slack_variables": [slack_zero, slack_one],
                "equality": "sum(selected upgrades) - bit0 - 2*bit1 = 1",
                "semantics": "at least one upgrade at the physical anchor; two or three technologies may coexist",
            }
        )

    policy_names: list[str] = []
    if include_policy:
        policy_names = [
            "islanding_eligibility",
            "policy_activation",
            "critical_service_target",
            "reserve_level_low",
            "reserve_level_medium",
            "reserve_level_high",
            *(f"scenario_response::{scenario}" for scenario in SCENARIOS),
        ]
        variables.extend(_variable(name) for name in policy_names)
        reserve = ("reserve_level_low", "reserve_level_medium", "reserve_level_high")
        add_squared_equality_terms(
            terms,
            {name: 1 for name in reserve},
            1,
            10.0,
            component="reserve_one_hot",
        )
        terms.extend(
            [
                _term(-4.0, {"islanding_eligibility": 1}, "islanding_coverage"),
                _term(-2.0, {"policy_activation": 1}, "preparedness"),
                _term(-3.0, {"critical_service_target": 1}, "critical_service_proxy"),
                _term(-0.5, {"reserve_level_medium": 1}, "reserve_preparedness"),
                _term(-1.0, {"reserve_level_high": 1}, "reserve_preparedness"),
            ]
        )
        for scenario_index, scenario in enumerate(SCENARIOS):
            response = f"scenario_response::{scenario}"
            severity = 1.0 + scenario_index / max(len(SCENARIOS) - 1, 1)
            terms.append(_term(-severity, {response: 1}, "scenario_preparedness"))
            for asset in assets:
                selected = f"upgrade::{asset.asset_key}::selected"
                if asset.technology == "dispatchable_generation" or scenario not in {
                    "renewable_shortfall",
                    "combined_high_stress",
                }:
                    terms.append(
                        _term(
                            -0.02 * severity,
                            {selected: 1, "islanding_eligibility": 1, response: 1},
                            "native_cubic_preparedness",
                        )
                    )

    slack_names: list[str] = []
    budget_weights: dict[str, int] = {}
    for asset in assets:
        name = f"upgrade::{asset.asset_key}::selected"
        budget_weights[name] = encoding.encoded_costs[asset.asset_key]
    for index, weight in enumerate(encoding.slack_bit_weights):
        name = f"budget_slack_bit_{index}"
        variables.append(_variable(name))
        slack_names.append(name)
        budget_weights[name] = weight

    certificate = build_penalty_certificate(terms, safety_multiplier=safety_multiplier)
    add_squared_equality_terms(
        terms,
        budget_weights,
        encoding.encoded_budget,
        certificate.rho_budget,
        component="hard_budget",
    )
    normalized_terms, raw_max, scale = _normalize_terms(terms)
    maximum_degree = max((term["degree"] for term in normalized_terms), default=0)
    if len(variables) > 132:
        raise ValueError(f"global master has {len(variables)} variables > 132")
    if maximum_degree > 3:
        raise ValueError(f"global master degree {maximum_degree} > 3")
    if any(abs(float(term["coefficient"])) > 1.0 + 1e-12 for term in normalized_terms):
        raise ValueError("normalized coefficient exceeds one")

    asset_rows = [
        _asset_record(asset, float((benefit_overrides or {}).get(asset.asset_key, _benefit(asset))))
        for asset in assets
    ]
    payload: dict[str, Any] = {
        "schema": "cmpo.budget_master.v2",
        "objective_sense": "minimize",
        "max_degree": maximum_degree,
        "variables": variables,
        "polynomial_terms": normalized_terms,
        "budget_constraint": {
            "budget_id": budget.budget_id,
            "amount": budget.amount,
            "hard_constraint": True,
            "component": "hard_budget",
            "scope": "one deduplicated full IEEE123 physical upgrade portfolio",
        },
        "budget_encoding": encoding.to_dict(),
        "budget_penalty_certificate": {
            **certificate.to_dict(),
            "normalization_scale": scale,
            "normalized_minimum_violation_penalty": certificate.minimum_violation_penalty * scale,
            "normalized_nonbudget_variation_bound": (
                certificate.maximum_nonbudget_objective_variation * scale
            ),
        },
        "budget_derivation": budget.to_dict(),
        "scenario_metadata": {
            "scenario": f"budget_master_v2_{budget.budget_id}",
            "scenario_count": 8,
            "scenarios": list(SCENARIOS),
        },
        "patch_metadata": {
            "patch": f"global_ieee123_upgrade_master_{budget.budget_id}",
            "patch_ids": ["all_12_ieee123_patches"],
        },
        "catalog_assets": asset_rows,
        "one_hot_groups": one_hot_groups,
        "anchor_coverage_constraints": coverage_constraints,
        "shared_first_stage": {
            "asset_selection_variables": [
                f"upgrade::{asset.asset_key}::selected" for asset in assets
            ],
            "policy_variables": policy_names,
            "scope": "one portfolio fixed across all twelve patch recourse problems",
        },
        "recourse_contract": {
            "patch_count": 12,
            "training_scenario_count": 8,
            "heldout_n_1_count": 10,
            "consensus_algorithm": "overlap_consensus_admm",
            "projection": "full_public_system_active_power",
            "ac_validation": "existing pinned IEEE123 OpenDSS replay, reported separately",
            "top_unique_portfolios_per_budget": 10,
        },
        "provenance": {
            "public_asset_count": len(assets),
            "physical_anchor_count": len({asset.anchor_node for asset in assets}),
            "source_payload_checksums": _source_checksums(assets, source_payload_dir),
            "cost_sources": sorted({asset.source_row for asset in assets}),
        },
        "model_statistics": {
            "variable_count": len(variables),
            "integer_variable_count": len(variables),
            "continuous_variable_count": 0,
            "term_count": len(normalized_terms),
            "degree": maximum_degree,
            "raw_max_abs_nonconstant_coefficient": raw_max,
            "coefficient_scaling_factor": scale,
            "max_abs_coefficient": max(
                (abs(float(term["coefficient"])) for term in normalized_terms if term["powers"]),
                default=0.0,
            ),
        },
        "execution_provenance": {
            "qci_submission_performed": False,
            "qci_file_id": None,
            "qci_job_id": None,
        },
    }
    optimum = brute_force_master(payload) if len(assets) <= 20 else greedy_feasible_master(payload)
    selected_set = set(optimum.selected_asset_keys)
    encoded_selected_cost = sum(
        encoding.encoded_costs[key]
        for key in selected_set
        if key in encoding.encoded_costs
    )
    covered_anchors = {
        asset.anchor_node for asset in assets if asset.asset_key in selected_set
    }
    local = {
        "selected_asset_keys": list(optimum.selected_asset_keys),
        "actual_cost": optimum.actual_cost,
        "energy": optimum.energy,
        "budget": budget.amount,
        "encoded_selected_cost": encoded_selected_cost,
        "encoded_budget": encoding.encoded_budget,
        "exact_encoded_budget_check": encoded_selected_cost <= encoding.encoded_budget,
        "exact_actual_budget_check": optimum.actual_cost <= budget.amount + 1e-9,
        "covered_anchor_count": len(covered_anchors),
        "required_anchor_count": len({asset.anchor_node for asset in assets}),
        "coverage_check": len(covered_anchors) == len({asset.anchor_node for asset in assets}),
        "passed": (
            optimum.actual_cost <= budget.amount + 1e-9
            and encoded_selected_cost <= encoding.encoded_budget
            and len(covered_anchors) == len({asset.anchor_node for asset in assets})
        ),
        "method": "exact_brute_force" if len(assets) <= 20 else "deterministic_feasible_local_search",
    }
    payload["local_validation"] = local
    return GlobalMasterBuild(payload=payload, budget_encoding=encoding, local_validation=local)


def build_global_upgrade_master(
    catalog: Sequence[UpgradeAssetOption],
    budget: BudgetLevel,
    *,
    currency_unit: float,
    safety_multiplier: float = 2.0,
    source_payload_dir: Path | None = None,
) -> GlobalMasterBuild:
    return _build_master(
        catalog,
        budget,
        currency_unit=currency_unit,
        safety_multiplier=safety_multiplier,
        source_payload_dir=source_payload_dir,
    )


def _evaluate(payload: Mapping[str, Any], sample: Mapping[str, int]) -> float:
    values: list[float] = []
    for term in payload["polynomial_terms"]:
        value = float(term["coefficient"])
        for name, exponent in term["powers"].items():
            value *= int(sample.get(name, 0)) ** int(exponent)
        values.append(value)
    return float(math.fsum(values))


def _sample_for_subset(payload: Mapping[str, Any], selected: set[str]) -> dict[str, int] | None:
    sample = {str(variable["name"]): 0 for variable in payload["variables"]}
    encoded_costs = payload["budget_encoding"]["encoded_costs"]
    spent = 0
    for asset in payload["catalog_assets"]:
        key = str(asset["asset_key"])
        active = key in selected
        sample[f"upgrade::{key}::selected"] = int(active)
        sample[f"upgrade::{key}::not_selected"] = int(not active)
        if active:
            spent += int(encoded_costs[key])
    budget = int(payload["budget_encoding"]["encoded_budget"])
    if spent > budget:
        return None
    remaining = budget - spent
    for index, weight in enumerate(payload["budget_encoding"]["slack_bit_weights"]):
        sample[f"budget_slack_bit_{index}"] = int(bool(remaining & int(weight)))
    for coverage in payload.get("anchor_coverage_constraints", []):
        count = sum(
            sample.get(str(variable), 0)
            for variable in coverage["upgrade_variables"]
        )
        excess = max(0, count - 1)
        slack = coverage["excess_selection_slack_variables"]
        sample[str(slack[0])] = int(bool(excess & 1))
        sample[str(slack[1])] = int(bool(excess & 2))
    if "reserve_level_low" in sample:
        sample["reserve_level_low"] = 1
    return sample


def brute_force_master(payload: Mapping[str, Any]) -> BruteForceOptimum:
    assets = [str(asset["asset_key"]) for asset in payload["catalog_assets"]]
    if len(assets) > 20:
        raise ValueError("brute-force master is restricted to reduced test instances")
    costs = {str(asset["asset_key"]): float(asset["total_cost"]) for asset in payload["catalog_assets"]}
    best: BruteForceOptimum | None = None
    for bits in itertools.product((0, 1), repeat=len(assets)):
        selected = {key for key, bit in zip(assets, bits, strict=True) if bit}
        sample = _sample_for_subset(payload, selected)
        if sample is None:
            continue
        actual = math.fsum(costs[key] for key in selected)
        if actual > float(payload["budget_constraint"]["amount"]) + 1e-9:
            continue
        candidate = BruteForceOptimum(tuple(sorted(selected)), actual, _evaluate(payload, sample))
        if best is None or (candidate.energy, candidate.selected_asset_keys) < (
            best.energy,
            best.selected_asset_keys,
        ):
            best = candidate
    if best is None:
        raise ValueError("master has no budget-feasible binary portfolio")
    return best


def greedy_feasible_master(payload: Mapping[str, Any]) -> BruteForceOptimum:
    rows = sorted(
        payload["catalog_assets"],
        key=lambda row: (
            -float(row["local_benefit"]) / max(float(row["total_cost"]), 1.0),
            str(row["asset_key"]),
        ),
    )
    by_anchor: dict[str, list[Mapping[str, Any]]] = {}
    for row in payload["catalog_assets"]:
        by_anchor.setdefault(str(row["anchor_node"]), []).append(row)
    selected: set[str] = {
        str(min(rows, key=lambda row: (float(row["total_cost"]), str(row["asset_key"])))["asset_key"])
        for rows in by_anchor.values()
    }
    best_sample = _sample_for_subset(payload, selected)
    if best_sample is None:
        raise ValueError("minimum anchor-covering portfolio is infeasible in encoded units")
    best_energy = _evaluate(payload, best_sample)
    changed = True
    while changed:
        changed = False
        for row in rows:
            key = str(row["asset_key"])
            if key in selected:
                continue
            candidate_selected = selected | {key}
            sample = _sample_for_subset(payload, candidate_selected)
            if sample is None:
                continue
            actual = math.fsum(
                float(asset["total_cost"])
                for asset in payload["catalog_assets"]
                if str(asset["asset_key"]) in candidate_selected
            )
            if actual > float(payload["budget_constraint"]["amount"]) + 1e-9:
                continue
            energy = _evaluate(payload, sample)
            if energy < best_energy:
                selected = candidate_selected
                best_energy = energy
                changed = True
    actual = math.fsum(
        float(asset["total_cost"])
        for asset in payload["catalog_assets"]
        if str(asset["asset_key"]) in selected
    )
    return BruteForceOptimum(tuple(sorted(selected)), actual, best_energy)


def build_toy_master(
    *, costs: Mapping[str, float], benefits: Mapping[str, float], budget: float
) -> dict[str, Any]:
    catalog = [
        UpgradeAssetOption(
            asset_key=str(key),
            benchmark="toy",
            anchor_node=str(index),
            technology="dispatchable_generation",
            total_cost=float(cost),
            capacity_kw=1.0,
            power_kw=1.0,
            energy_kwh=0.0,
            source_row=f"toy:{key}",
            source_payload_ids=(),
            source_patch_ids=(),
        )
        for index, (key, cost) in enumerate(sorted(costs.items()))
    ]
    level = BudgetLevel("toy", float(budget), float(budget), "toy exact budget", ("toy",))
    return _build_master(
        catalog,
        level,
        currency_unit=0.01,
        safety_multiplier=2.0,
        source_payload_dir=None,
        benefit_overrides=benefits,
        include_policy=False,
    ).payload
