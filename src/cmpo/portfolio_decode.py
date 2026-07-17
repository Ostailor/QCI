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
