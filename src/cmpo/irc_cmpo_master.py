"""Build the 33-binary Integer Recourse-Calibrated CMPO master."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from cmpo.irc_cmpo_constraints import audit_coefficients, coverage_penalty_terms
from cmpo.upgrade_budget import load_ieee123_upgrade_catalog


@dataclass(frozen=True)
class IRCAsset:
    asset_key: str
    anchor_node: str
    technology: str
    total_cost: float
    capacity_kw: float = 0.0
    power_kw: float = 0.0
    energy_kwh: float = 0.0
    source_row: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_catalog(path: Path | str) -> tuple[IRCAsset, ...]:
    """Load the existing charge-once IEEE123 catalog from CSV or payload directory."""

    source = Path(path)
    if source.is_dir():
        rows = [asdict(item) for item in load_ieee123_upgrade_catalog(source)]
    else:
        rows = pd.read_csv(source).to_dict("records")
    assets = tuple(
        IRCAsset(
            asset_key=str(row["asset_key"]),
            anchor_node=str(row["anchor_node"]),
            technology=str(row["technology"]),
            total_cost=float(row["total_cost"]),
            capacity_kw=float(row.get("capacity_kw", 0.0) or 0.0),
            power_kw=float(row.get("power_kw", 0.0) or 0.0),
            energy_kwh=float(row.get("energy_kwh", 0.0) or 0.0),
            source_row=str(row.get("source_row", "")),
        )
        for row in sorted(rows, key=lambda item: str(item["asset_key"]))
    )
    if len({asset.asset_key for asset in assets}) != len(assets):
        raise ValueError("catalog contains duplicate physical asset keys")
    anchors: dict[str, set[str]] = {}
    for asset in assets:
        if not math.isfinite(asset.total_cost) or asset.total_cost <= 0.0:
            raise ValueError(f"invalid public cost for {asset.asset_key}")
        anchors.setdefault(asset.anchor_node, set()).add(asset.technology)
    expected = {"pv", "bess", "dispatchable_generation"}
    incomplete = [anchor for anchor, technologies in anchors.items() if technologies != expected]
    if incomplete:
        raise ValueError(f"incomplete technology coverage at anchors: {incomplete}")
    return assets


def _surrogate_polynomial_terms(
    surrogate_terms: Sequence[Mapping[str, Any]], variable_by_asset: Mapping[str, str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for term in surrogate_terms:
        keys = tuple(str(key) for key in term.get("asset_keys", ()))
        if len(keys) > 3:
            raise ValueError("IRC-CMPO surrogate degree exceeds 3")
        missing = set(keys) - set(variable_by_asset)
        if missing:
            raise ValueError(f"surrogate references unknown assets: {sorted(missing)}")
        coefficient = float(term["coefficient"])
        if not math.isfinite(coefficient):
            raise ValueError("surrogate coefficients must be finite")
        component = "surrogate" if len(keys) <= 1 else "interaction"
        rows.append(
            {
                "coefficient": coefficient,
                "powers": {variable_by_asset[key]: 1 for key in keys},
                "degree": len(keys),
                "component": component,
                "surrogate_feature": "*".join(keys) if keys else "intercept",
            }
        )
    return rows


def _local_feasibility_polynomial_terms(
    constraints: Sequence[Mapping[str, Any]], variable_by_asset: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Expand exact three-bit no-good indicators without auxiliary variables."""

    rows: list[dict[str, Any]] = []
    for constraint in constraints:
        keys = tuple(str(key) for key in constraint.get("asset_keys", ()))
        pattern = tuple(constraint.get("pattern", ()))
        if len(keys) != 3 or len(pattern) != 3 or any(value not in {0, 1} for value in pattern):
            raise ValueError("local feasibility constraints require three asset keys and a binary pattern")
        if len(set(keys)) != 3 or set(keys) - set(variable_by_asset):
            raise ValueError("local feasibility constraint references duplicate or unknown assets")
        rho = float(constraint["coefficient"])
        if not math.isfinite(rho) or rho <= 0.0:
            raise ValueError("local feasibility penalty must be finite and positive")
        selected = [key for key, bit in zip(keys, pattern, strict=True) if bit == 1]
        zero = [key for key, bit in zip(keys, pattern, strict=True) if bit == 0]
        for mask in range(1 << len(zero)):
            subset = [zero[index] for index in range(len(zero)) if mask & (1 << index)]
            monomial = [*selected, *subset]
            rows.append(
                {
                    "coefficient": rho * (-1.0 if len(subset) % 2 else 1.0),
                    "powers": {variable_by_asset[key]: 1 for key in monomial},
                    "degree": len(monomial),
                    "component": "local_feasibility",
                    "anchor_node": str(constraint["anchor_node"]),
                    "invalid_pattern": list(pattern),
                }
            )
    return rows


def build_scalarized_irc_master(
    assets: Sequence[IRCAsset],
    *,
    cost_weight: float,
    surrogate_terms: Sequence[Mapping[str, Any]],
    local_feasibility_terms: Sequence[Mapping[str, Any]],
    audit_collapsed_threshold: float = 1e-12,
) -> dict[str, Any]:
    """Build the final cost--resilience master without a hard budget.

    Upgrade cost is normalized by the cost of selecting the complete public
    catalog.  Local island adequacy is represented only by data-derived no-good
    patterns supplied by :mod:`cmpo.irc_cmpo_feasibility`.
    """

    if not math.isfinite(cost_weight) or cost_weight < 0.0:
        raise ValueError("cost weight must be finite and nonnegative")
    assets = tuple(sorted(assets, key=lambda item: item.asset_key))
    maximum_catalog_cost = math.fsum(asset.total_cost for asset in assets)
    if maximum_catalog_cost <= 0.0:
        raise ValueError("maximum catalog portfolio cost must be positive")
    variable_by_asset = {asset.asset_key: f"y::{asset.asset_key}" for asset in assets}
    variables = [
        {
            "name": variable_by_asset[asset.asset_key],
            "encoding_type": "binary",
            "lower_bound": 0,
            "upper_bound": 1,
            "num_levels": 2,
            "physical_asset_key": asset.asset_key,
        }
        for asset in assets
    ]
    terms = _surrogate_polynomial_terms(surrogate_terms, variable_by_asset)
    terms.extend(
        {
            "coefficient": cost_weight * asset.total_cost / maximum_catalog_cost,
            "powers": {variable_by_asset[asset.asset_key]: 1},
            "degree": 1,
            "component": "normalized_cost",
            "physical_asset_key": asset.asset_key,
        }
        for asset in assets
        if cost_weight > 0.0
    )
    terms.extend(_local_feasibility_polynomial_terms(local_feasibility_terms, variable_by_asset))
    maximum_degree = max((int(term["degree"]) for term in terms), default=0)
    if maximum_degree > 3:
        raise ValueError("IRC-CMPO polynomial exceeds Dirac-3 degree limit")
    audit = audit_coefficients(terms, collapsed_threshold=audit_collapsed_threshold)
    return {
        "schema": "cmpo.irc_cmpo.scalarized_integer_master.v1",
        "formulation": "Integer, Recourse-Calibrated Cubic Microgrid Patch Optimizer",
        "abbreviation": "IRC-CMPO",
        "objective_sense": "minimize",
        "variables": variables,
        "num_variables": len(variables),
        "num_levels": [2] * len(variables),
        "min_degree": min((int(term["degree"]) for term in terms), default=0),
        "max_degree": maximum_degree,
        "polynomial_terms": terms,
        "catalog_assets": [asset.to_dict() for asset in assets],
        "local_feasibility_constraints": [dict(item) for item in local_feasibility_terms],
        "cost_scalarization": {
            "lambda": float(cost_weight),
            "denominator": "maximum_catalog_portfolio_cost",
            "maximum_catalog_portfolio_cost": maximum_catalog_cost,
            "hard_budget": False,
            "projection_permitted": False,
        },
        "irc_cmpo": {
            "projection_permitted": False,
            "selected_not_selected_pairs": False,
            "budget_slack_variables": 0,
            "continuous_policy_variables": 0,
        },
        "coefficient_audit": audit.to_dict(),
    }


def build_irc_master(
    assets: Sequence[IRCAsset],
    *,
    budget: float,
    lagrange_lambda: float,
    surrogate_terms: Sequence[Mapping[str, Any]],
    coverage_rho: float = 2.0,
    audit_collapsed_threshold: float = 1e-12,
) -> dict[str, Any]:
    """Construct an integer Hamiltonian with no budget slack or policy variables."""

    if not math.isfinite(budget) or budget <= 0.0:
        raise ValueError("budget must be finite and positive")
    if not math.isfinite(lagrange_lambda) or lagrange_lambda < 0.0:
        raise ValueError("lagrange lambda must be finite and nonnegative")
    assets = tuple(sorted(assets, key=lambda item: item.asset_key))
    variable_by_asset = {asset.asset_key: f"y::{asset.asset_key}" for asset in assets}
    variables = [
        {
            "name": variable_by_asset[asset.asset_key],
            "encoding_type": "binary",
            "lower_bound": 0,
            "upper_bound": 1,
            "num_levels": 2,
            "physical_asset_key": asset.asset_key,
        }
        for asset in assets
    ]
    terms = _surrogate_polynomial_terms(surrogate_terms, variable_by_asset)
    terms.extend(
        {
            "coefficient": lagrange_lambda * asset.total_cost / budget,
            "powers": {variable_by_asset[asset.asset_key]: 1},
            "degree": 1,
            "component": "normalized_cost",
            "physical_asset_key": asset.asset_key,
        }
        for asset in assets
    )
    anchors: dict[str, dict[str, str]] = {}
    for asset in assets:
        anchors.setdefault(asset.anchor_node, {})[asset.technology] = variable_by_asset[asset.asset_key]
    for anchor, technology_variables in sorted(anchors.items()):
        terms.extend(coverage_penalty_terms(anchor, technology_variables, coverage_rho))
    maximum_degree = max((int(term["degree"]) for term in terms), default=0)
    audit = audit_coefficients(terms, collapsed_threshold=audit_collapsed_threshold)
    payload = {
        "schema": "cmpo.irc_cmpo.integer_master.v1",
        "formulation": "Integer Recourse-Calibrated CMPO",
        "abbreviation": "IRC-CMPO",
        "objective_sense": "minimize",
        "variables": variables,
        "num_variables": len(variables),
        "num_levels": [2] * len(variables),
        "min_degree": min((int(term["degree"]) for term in terms), default=0),
        "max_degree": maximum_degree,
        "polynomial_terms": terms,
        "catalog_assets": [asset.to_dict() for asset in assets],
        "exact_budget_constraint": {
            "amount_dollars": float(budget),
            "enforcement": "native-sample exact filter; never projection",
        },
        "anchor_coverage_constraints": [
            {
                "anchor_node": anchor,
                "semantics": "at_least_one",
                "variables": list(technology_variables.values()),
                "native_cubic_penalty": True,
            }
            for anchor, technology_variables in sorted(anchors.items())
        ],
        "irc_cmpo": {
            "lagrange_lambda": float(lagrange_lambda),
            "normalized_cost_denominator_dollars": float(budget),
            "coverage_rho": float(coverage_rho),
            "projection_permitted": False,
            "selected_not_selected_pairs": False,
            "budget_slack_variables": 0,
            "continuous_policy_variables": 0,
        },
        "coefficient_audit": audit.to_dict(),
    }
    if maximum_degree > 3:
        raise ValueError("IRC-CMPO polynomial exceeds Dirac-3 degree limit")
    return payload


def write_payload_exclusive(payload: Mapping[str, Any], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return target
