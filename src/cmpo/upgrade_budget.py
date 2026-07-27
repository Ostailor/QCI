"""Evidence-derived common upgrade budgets for the IEEE 123 SC-CMPO study."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


@dataclass(frozen=True)
class UpgradeAssetOption:
    """One deduplicated physical upgrade option backed by the pinned ATB catalog."""

    asset_key: str
    benchmark: str
    anchor_node: str
    technology: str
    total_cost: float
    capacity_kw: float
    power_kw: float
    energy_kwh: float
    source_row: str
    source_payload_ids: tuple[str, ...]
    source_patch_ids: tuple[str, ...]


@dataclass(frozen=True)
class BudgetLevel:
    """A common hard budget and an auditable derivation record."""

    budget_id: str
    amount: float
    discrete_portfolio_cost: float
    derivation: str
    source_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "amount": self.amount,
            "discrete_portfolio_cost": self.discrete_portfolio_cost,
            "derivation": self.derivation,
            "source_refs": list(self.source_refs),
        }


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    nodes = list(payload["sc_cmpo"].get("patch_public_nodes", ()))
    if nodes:
        candidates = [
            (
                float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                float(node.get("load_kw", 0.0)),
                str(node["node_id"]),
            )
            for node in nodes
        ]
        return sorted(candidates, key=lambda item: (-item[0], -item[1], item[2]))[0][2]
    node_ids = [str(item) for item in payload["sc_cmpo"]["upgrade_patch"].get("node_ids", ())]
    if not node_ids:
        raise ValueError("SC-CMPO payload has no physical upgrade anchor")
    return sorted(node_ids)[0]


def load_ieee123_upgrade_catalog(payload_dir: Path | str) -> list[UpgradeAssetOption]:
    """Read and deduplicate all public-cost IEEE 123 options from existing payloads.

    Overlapping patches may propose the same physical anchor/technology.  The
    maximum sized option is retained, matching the full-system projection's
    charge-once rule.
    """

    directory = Path(payload_dir)
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sc = payload.get("sc_cmpo", {})
        benchmark = str(sc.get("public_benchmark", ""))
        if benchmark != "ieee123_opendss":
            continue
        anchor = _physical_anchor(payload)
        patch_id = str(sc["upgrade_patch"]["patch_id"])
        for option in sc.get("upgrade_options", ()):
            technology = str(option["technology"])
            asset_key = f"{benchmark}::{anchor}::{technology}"
            candidate = {
                "asset_key": asset_key,
                "benchmark": benchmark,
                "anchor_node": anchor,
                "technology": technology,
                "total_cost": float(option["total_cost"]),
                "capacity_kw": float(option.get("capacity_kw", 0.0)),
                "power_kw": float(option.get("power_kw", 0.0)),
                "energy_kwh": float(option.get("energy_kwh", 0.0)),
                "source_row": str(option["source_row"]),
                "source_payload_ids": {path.name},
                "source_patch_ids": {patch_id},
            }
            existing = merged.get(asset_key)
            if existing is None:
                merged[asset_key] = candidate
                continue
            existing["source_payload_ids"].add(path.name)
            existing["source_patch_ids"].add(patch_id)
            if candidate["total_cost"] > existing["total_cost"]:
                for field in ("total_cost", "capacity_kw", "power_kw", "energy_kwh", "source_row"):
                    existing[field] = candidate[field]
    if not merged:
        raise FileNotFoundError(f"no IEEE 123 SC-CMPO payloads found under {directory}")
    assets = [
        UpgradeAssetOption(
            **{
                **row,
                "source_payload_ids": tuple(sorted(row["source_payload_ids"])),
                "source_patch_ids": tuple(sorted(row["source_patch_ids"])),
            }
        )
        for _, row in sorted(merged.items())
    ]
    technologies = {asset.technology for asset in assets}
    if technologies != {"pv", "bess", "dispatchable_generation"}:
        raise ValueError(f"IEEE 123 upgrade catalog is incomplete: {sorted(technologies)}")
    if any(not math.isfinite(asset.total_cost) or asset.total_cost <= 0.0 for asset in assets):
        raise ValueError("IEEE 123 upgrade costs must be finite and positive")
    return assets


def technology_cost_totals(catalog: Iterable[UpgradeAssetOption]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for asset in catalog:
        totals[asset.technology] = math.fsum((totals.get(asset.technology, 0.0), asset.total_cost))
    return totals


def _reference_cost(path: Path | str, method: str) -> float:
    frame = pd.read_csv(path)
    rows = frame[(frame["benchmark"] == "ieee123_opendss") & (frame["method"] == method)]
    if "headline_selection" in rows:
        headline = rows[rows["headline_selection"].astype(str).str.lower().isin({"true", "1"})]
        if not headline.empty:
            rows = headline
    if rows.empty:
        raise ValueError(f"no IEEE 123 {method} reference row in {path}")
    costs = pd.to_numeric(rows["total_upgrade_cost"], errors="raise")
    return float(costs.iloc[0])


def _prefix_nearest(options: Sequence[UpgradeAssetOption], target: float) -> float:
    running = 0.0
    candidates = [0.0]
    for asset in sorted(options, key=lambda item: (item.total_cost, item.asset_key)):
        running = math.fsum((running, asset.total_cost))
        candidates.append(running)
    return min(candidates, key=lambda value: (abs(value - target), value > target, value))


def derive_ieee123_budget_sweep(
    catalog: Sequence[UpgradeAssetOption],
    *,
    qci_metrics_path: Path | str,
    baseline_metrics_path: Path | str,
) -> list[BudgetLevel]:
    """Derive common catalog-backed budgets from observed Phase 3 anchors.

    Intermediate points are cumulative costs of actual physical options, not
    hand-entered dollar amounts.  The final QCi budget is the observed selected
    portfolio cost; its ``discrete_portfolio_cost`` records the closest catalog
    prefix that fits beneath that cap.
    """

    assets = list(catalog)
    totals = technology_cost_totals(assets)
    dispatch = totals["dispatchable_generation"]
    pv_assets = [asset for asset in assets if asset.technology == "pv"]
    bess_assets = [asset for asset in assets if asset.technology == "bess"]
    slsqp = _reference_cost(baseline_metrics_path, "SLSQP")
    qci = _reference_cost(qci_metrics_path, "QCi SC-CMPO")
    if not dispatch <= slsqp <= qci:
        raise ValueError("reference costs do not span minimum islanding through selected QCi")

    pv_total = totals["pv"]
    low_add = min(asset.total_cost for asset in pv_assets)
    middle_add = _prefix_nearest(pv_assets, pv_total / 2.0)
    qci_mid_target = (slsqp + qci) / 2.0
    bess_mid_add = _prefix_nearest(bess_assets, max(0.0, qci_mid_target - slsqp))
    qci_discrete_add = max(
        (
            _prefix_nearest(bess_assets, target)
            for target in [max(0.0, qci - slsqp), max(0.0, qci - dispatch)]
        ),
        key=lambda value: value if slsqp + value <= qci + 1e-6 else -1.0,
    )
    refs = (
        str(Path(qci_metrics_path)),
        str(Path(baseline_metrics_path)),
        "embedded upgrade_options in the 12 IEEE123 SC-CMPO payloads",
    )
    candidates = [
        BudgetLevel(
            "minimum_feasible_islanding",
            dispatch,
            dispatch,
            "Sum of one full ATB dispatchable-generation option at every deduplicated physical anchor; "
            "dispatchable generation is the least-cost option available in PV-shortfall islanding scenarios.",
            refs,
        ),
        BudgetLevel(
            "low_cost_catalog_step",
            dispatch + low_add,
            dispatch + low_add,
            "Minimum feasible islanding portfolio plus the least-cost full PV option in the discrete catalog.",
            refs,
        ),
        BudgetLevel(
            "pv_catalog_midpoint",
            dispatch + middle_add,
            dispatch + middle_add,
            "Minimum feasible islanding portfolio plus the cumulative cheapest PV options nearest one-half "
            "of the catalog-wide PV add-on cost.",
            refs,
        ),
        BudgetLevel(
            "slsqp_selected_cost",
            slsqp,
            min(slsqp, dispatch + pv_total),
            "Observed IEEE123 SLSQP selected cost; it equals the deduplicated full dispatchable+PV catalog portfolio.",
            refs,
        ),
        BudgetLevel(
            "post_slsqp_catalog_step",
            slsqp + bess_mid_add,
            slsqp + bess_mid_add,
            "SLSQP portfolio plus cumulative cheapest full BESS options nearest the midpoint between the "
            "observed SLSQP and QCi costs.",
            refs,
        ),
        BudgetLevel(
            "qci_selected_cost",
            qci,
            min(qci, slsqp + qci_discrete_add),
            "Observed challenge-selected IEEE123 QCi SC-CMPO portfolio cost; the discrete field records the "
            "largest derived catalog prefix used to audit feasibility beneath this cap.",
            refs,
        ),
    ]
    unique: dict[float, BudgetLevel] = {round(level.amount, 6): level for level in candidates}
    result = sorted(unique.values(), key=lambda level: level.amount)
    if len(result) < 6:
        raise ValueError("catalog/reference derivation produced fewer than six distinct budgets")
    return result
