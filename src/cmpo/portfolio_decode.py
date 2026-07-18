"""Decode global-master samples with encoded and exact-dollar budget gates."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cmpo.budgeted_portfolio import deduplicate_upgrade_assets


@dataclass(frozen=True)
class DecodedPortfolio:
    budget_id: str
    selected_asset_keys: tuple[str, ...]
    total_upgrade_cost: float
    encoded_upgrade_cost: int
    encoded_budget: int
    actual_budget: float
    energy: float
    upgrade_rows: tuple[dict[str, Any], ...]
    feasible: bool = True

    @property
    def signature(self) -> str:
        payload = json.dumps(self.selected_asset_keys, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def charge_once_cost(self, rows: Sequence[Mapping[str, Any]]) -> float:
        return float(math.fsum(float(row["installed_cost"]) for row in deduplicate_upgrade_assets(rows)))

    @classmethod
    def testing(
        cls,
        selected_asset_keys: tuple[str, ...],
        cost: float,
        *,
        energy: float = 0.0,
    ) -> "DecodedPortfolio":
        rows = tuple(
            {
                "asset_key": key,
                "installed_cost": float(cost) / max(len(selected_asset_keys), 1),
                "source_payload_ids": [],
            }
            for key in selected_asset_keys
        )
        return cls(
            budget_id="test",
            selected_asset_keys=tuple(sorted(selected_asset_keys)),
            total_upgrade_cost=float(cost),
            encoded_upgrade_cost=0,
            encoded_budget=0,
            actual_budget=float(cost),
            energy=float(energy),
            upgrade_rows=rows,
        )


def _sample_map(payload: Mapping[str, Any], sample: Mapping[str, Any] | Sequence[float]) -> dict[str, int]:
    names = [str(variable["name"]) for variable in payload["variables"]]
    if isinstance(sample, Mapping):
        values = {name: sample.get(name, 0) for name in names}
    else:
        values = {name: sample[index] if index < len(sample) else 0 for index, name in enumerate(names)}
    result: dict[str, int] = {}
    for name, raw in values.items():
        value = float(raw)
        rounded = int(round(value))
        if not math.isfinite(value) or abs(value - rounded) > 1e-6 or rounded not in {0, 1}:
            raise ValueError(f"master sample has non-binary value for {name}: {raw}")
        result[name] = rounded
    return result


def _raw_sample_map(
    payload: Mapping[str, Any], sample: Mapping[str, Any] | Sequence[float]
) -> dict[str, float]:
    names = [str(variable["name"]) for variable in payload["variables"]]
    if isinstance(sample, Mapping):
        values = {name: sample.get(name, 0.0) for name in names}
    else:
        values = {
            name: sample[index] if index < len(sample) else 0.0
            for index, name in enumerate(names)
        }
    result = {name: float(raw) for name, raw in values.items()}
    if any(not math.isfinite(value) for value in result.values()):
        raise ValueError("master sample contains a non-finite value")
    return result


def _decoded_portfolio(
    payload: Mapping[str, Any], selected: Sequence[str], *, energy: float
) -> DecodedPortfolio:
    assets = {str(row["asset_key"]): row for row in payload["catalog_assets"]}
    encoding = payload["budget_encoding"]
    encoded_cost = sum(int(encoding["encoded_costs"][key]) for key in selected)
    encoded_budget = int(encoding["encoded_budget"])
    if encoded_cost > encoded_budget:
        raise ValueError(
            f"encoded portfolio cost {encoded_cost} exceeds hard budget {encoded_budget}"
        )
    rows = [
        {
            "asset_key": key,
            "benchmark": assets[key].get("benchmark", ""),
            "anchor_node": assets[key].get("anchor_node", ""),
            "technology": assets[key].get("technology", ""),
            "installed_cost": float(assets[key]["total_cost"]),
            "installed_capacity_kw": float(assets[key].get("capacity_kw", 0.0)),
            "installed_power_kw": float(assets[key].get("power_kw", 0.0)),
            "installed_energy_kwh": float(assets[key].get("energy_kwh", 0.0)),
            "source_row": assets[key].get("source_row", ""),
            "source_payload_ids": list(assets[key].get("source_payload_ids", ())),
            "deduplication_rule": "physical asset key charged once",
        }
        for key in sorted(selected)
    ]
    unique = deduplicate_upgrade_assets(rows)
    actual_cost = math.fsum(float(row["installed_cost"]) for row in unique)
    actual_budget = float(payload["budget_constraint"]["amount"])
    if actual_cost > actual_budget + 1e-9:
        raise ValueError(
            f"actual-dollar portfolio cost {actual_cost} exceeds hard budget {actual_budget}"
        )
    return DecodedPortfolio(
        budget_id=str(payload["budget_constraint"]["budget_id"]),
        selected_asset_keys=tuple(sorted(selected)),
        total_upgrade_cost=float(actual_cost),
        encoded_upgrade_cost=encoded_cost,
        encoded_budget=encoded_budget,
        actual_budget=actual_budget,
        energy=float(energy),
        upgrade_rows=tuple(unique),
    )


def portfolio_from_selected_assets(
    payload: Mapping[str, Any],
    selected_asset_keys: Sequence[str],
    *,
    energy: float = 0.0,
) -> DecodedPortfolio:
    """Build and hard-validate a portfolio selected by a classical master."""

    known = {str(row["asset_key"]) for row in payload["catalog_assets"]}
    selected = tuple(sorted(str(key) for key in selected_asset_keys))
    if len(selected) != len(set(selected)):
        raise ValueError("physical asset deduplication failed")
    unknown = sorted(set(selected) - known)
    if unknown:
        raise ValueError(f"unknown physical upgrade assets: {unknown}")
    covered = {
        str(row["anchor_node"])
        for row in payload["catalog_assets"]
        if str(row["asset_key"]) in selected
    }
    required = {
        str(row["anchor_node"])
        for row in payload["catalog_assets"]
    }
    if covered != required:
        raise ValueError(
            "islanding coverage requirement failed for anchors: "
            + ", ".join(sorted(required - covered))
        )
    return _decoded_portfolio(payload, selected, energy=energy)


def decode_challenge_aligned_sample(
    payload: Mapping[str, Any],
    sample: Mapping[str, Any] | Sequence[float],
    *,
    energy: float = 0.0,
) -> tuple[DecodedPortfolio, dict[str, Any]]:
    """Project a Dirac sample to asset states, then recheck every hard constraint.

    Dirac returns continuous coordinates even for a binary polynomial model.  The
    challenge-aligned decoder therefore uses the coordinate difference in each
    selected/not-selected pair as a preference score, solves a small binary
    projection with the exact budget and coverage constraints, and admits the
    physical portfolio only after independent encoded-dollar, actual-dollar,
    charge-once, and islanding-coverage checks.
    """

    values = _raw_sample_map(payload, sample)
    raw_selected: list[str] = []
    asset_scores: dict[str, float] = {}
    pair_margins: list[float] = []
    raw_residuals: list[float] = []
    for asset in payload["catalog_assets"]:
        key = str(asset["asset_key"])
        on = values.get(f"upgrade::{key}::selected", 0.0)
        off = values.get(f"upgrade::{key}::not_selected", 0.0)
        if math.isclose(on, off, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"ambiguous upgrade one-hot pair for {key}")
        if on > off:
            raw_selected.append(key)
        asset_scores[key] = on - off
        pair_margins.append(abs(on - off))
        raw_residuals.append(abs(on + off - 1.0))

    raw_selected_set = set(raw_selected)
    required_anchors = {
        str(row["anchor_node"]) for row in payload["catalog_assets"]
    }
    raw_covered_anchors = {
        str(row["anchor_node"])
        for row in payload["catalog_assets"]
        if str(row["asset_key"]) in raw_selected_set
    }
    raw_coverage_valid = raw_covered_anchors == required_anchors
    raw_asset_rows = {
        str(row["asset_key"]): row for row in payload["catalog_assets"]
    }
    raw_pairwise_actual_cost = math.fsum(
        float(raw_asset_rows[key]["total_cost"]) for key in raw_selected_set
    )
    raw_pairwise_encoded_cost = sum(
        int(payload["budget_encoding"]["encoded_costs"][key])
        for key in raw_selected_set
    )

    # Project the continuous Dirac coordinates to the closest hard-feasible
    # physical portfolio. This is the challenge-aligned reconstruction step;
    # its result is still passed through the independent exact-dollar decoder.
    from scipy.optimize import Bounds, LinearConstraint, milp  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    assets = sorted(payload["catalog_assets"], key=lambda row: str(row["asset_key"]))
    keys = [str(row["asset_key"]) for row in assets]
    scores = np.asarray([asset_scores[key] for key in keys], dtype=float)
    score_scale = max(float(np.max(np.abs(scores))), 1.0)
    objective = -scores / score_scale
    actual_costs = np.asarray([float(row["total_cost"]) for row in assets], dtype=float)
    encoding = payload["budget_encoding"]
    encoded_costs = np.asarray(
        [int(encoding["encoded_costs"][key]) for key in keys], dtype=float
    )
    rows = [encoded_costs, actual_costs]
    lower = [-np.inf, -np.inf]
    upper = [
        float(encoding["encoded_budget"]),
        float(payload["budget_constraint"]["amount"]),
    ]
    for anchor in sorted(required_anchors):
        row = np.asarray(
            [float(str(asset["anchor_node"]) == anchor) for asset in assets], dtype=float
        )
        rows.append(row)
        lower.append(1.0)
        upper.append(np.inf)
    projection = milp(
        objective,
        integrality=np.ones(len(keys), dtype=int),
        bounds=Bounds(np.zeros(len(keys)), np.ones(len(keys))),
        constraints=LinearConstraint(
            np.vstack(rows), np.asarray(lower), np.asarray(upper)
        ),
        options={"presolve": True, "time_limit": 30.0, "mip_rel_gap": 0.0},
    )
    if not projection.success or projection.x is None:
        raise ValueError(
            "challenge-aligned projection could not satisfy budget, one-hot, "
            "deduplication, and islanding coverage requirements"
        )
    selected = [key for key, value in zip(keys, projection.x, strict=True) if value >= 0.5]
    portfolio = portfolio_from_selected_assets(payload, selected, energy=energy)
    diagnostics = {
        "projection_rule": "pairwise_preference_then_hard_feasible_binary_milp_projection",
        "one_hot_valid": True,
        "raw_one_hot_valid": max(raw_residuals, default=0.0) <= 1e-6,
        "coverage_valid": True,
        "raw_coverage_valid": raw_coverage_valid,
        "raw_pairwise_actual_cost": raw_pairwise_actual_cost,
        "raw_pairwise_encoded_cost": raw_pairwise_encoded_cost,
        "raw_pairwise_budget_valid": (
            raw_pairwise_actual_cost <= float(payload["budget_constraint"]["amount"]) + 1e-9
            and raw_pairwise_encoded_cost
            <= int(payload["budget_encoding"]["encoded_budget"])
        ),
        "coverage_repair_count": len(set(selected) ^ raw_selected_set),
        "raw_pairwise_selected_asset_count": len(raw_selected_set),
        "projection_solver": "scipy.optimize.milp (HiGHS)",
        "projection_solver_status": int(projection.status),
        "physical_asset_deduplication_valid": (
            len(portfolio.selected_asset_keys) == len(set(portfolio.selected_asset_keys))
        ),
        "encoded_budget_valid": portfolio.encoded_upgrade_cost <= portfolio.encoded_budget,
        "actual_budget_valid": portfolio.total_upgrade_cost <= portfolio.actual_budget + 1e-9,
        "minimum_pair_margin": min(pair_margins, default=0.0),
        "maximum_raw_one_hot_residual": max(raw_residuals, default=0.0),
    }
    return portfolio, diagnostics


def decode_master_sample(
    payload: Mapping[str, Any],
    sample: Mapping[str, Any] | Sequence[float],
    *,
    energy: float = 0.0,
) -> DecodedPortfolio:
    values = _sample_map(payload, sample)
    assets = {str(row["asset_key"]): row for row in payload["catalog_assets"]}
    selected: list[str] = []
    for key in assets:
        on = values.get(f"upgrade::{key}::selected", 0)
        off = values.get(f"upgrade::{key}::not_selected", 0)
        if on + off != 1:
            raise ValueError(f"upgrade one-hot constraint failed for {key}")
        if on:
            selected.append(key)
    encoding = payload["budget_encoding"]
    encoded_cost = sum(int(encoding["encoded_costs"][key]) for key in selected)
    encoded_budget = int(encoding["encoded_budget"])
    slack = sum(
        int(weight) * values.get(f"budget_slack_bit_{index}", 0)
        for index, weight in enumerate(encoding["slack_bit_weights"])
    )
    if encoded_cost > encoded_budget:
        raise ValueError(
            f"encoded portfolio cost {encoded_cost} exceeds hard budget {encoded_budget}"
        )
    if encoded_cost + slack != encoded_budget:
        raise ValueError("budget slack equality is not satisfied")
    return _decoded_portfolio(payload, selected, energy=energy)
