"""Strict native integer decoding for IRC-CMPO samples."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cmpo.irc_cmpo_constraints import uncovered_anchors


@dataclass(frozen=True)
class NativePortfolio:
    selected_asset_keys: tuple[str, ...]
    total_cost: float
    budget: float | None
    signature: str
    projection_used: bool = False


def _coordinates(payload: Mapping[str, Any], sample: Mapping[str, Any] | Sequence[Any]) -> list[Any]:
    names = [str(variable["name"]) for variable in payload["variables"]]
    if isinstance(sample, Mapping):
        missing = set(names) - set(sample)
        if missing:
            raise ValueError(f"integer sample is missing coordinates: {sorted(missing)}")
        return [sample[name] for name in names]
    values = list(sample)
    if len(values) != len(names):
        raise ValueError(f"integer sample has {len(values)} coordinates; expected {len(names)}")
    return values


def decode_native_sample(
    payload: Mapping[str, Any],
    sample: Mapping[str, Any] | Sequence[Any],
    *,
    require_budget: bool = True,
) -> NativePortfolio:
    """Decode without rounding, repair, projection, or duplicate charging."""

    values = _coordinates(payload, sample)
    selected: list[str] = []
    for variable, raw in zip(payload["variables"], values, strict=True):
        if isinstance(raw, bool):
            raise ValueError(f"native coordinate {variable['name']} is boolean, not an integer sample value")
        value = float(raw)
        lower = int(variable["lower_bound"])
        upper = int(variable["upper_bound"])
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"native coordinate {variable['name']} is not an integer")
        integer = int(value)
        if integer < lower or integer > upper:
            raise ValueError(f"native coordinate {variable['name']} is outside its declared domain")
        if integer == 1:
            selected.append(str(variable["physical_asset_key"]))
    assets = list(payload["catalog_assets"])
    asset_by_key = {str(asset["asset_key"]): asset for asset in assets}
    local_constraints = payload.get("local_feasibility_constraints")
    if isinstance(local_constraints, list):
        selected_set = set(selected)
        for constraint in local_constraints:
            keys = [str(key) for key in constraint["asset_keys"]]
            actual = [int(key in selected_set) for key in keys]
            if actual == list(constraint["pattern"]):
                raise ValueError(
                    "native portfolio violates local feasibility at anchor "
                    f"{constraint['anchor_node']}: pattern {actual}"
                )
    else:
        missing_coverage = uncovered_anchors(selected, assets)
        if missing_coverage:
            raise ValueError(f"native portfolio violates coverage at anchors: {missing_coverage}")
    total_cost = math.fsum(float(asset_by_key[key]["total_cost"]) for key in set(selected))
    budget_constraint = payload.get("exact_budget_constraint")
    budget = (
        float(budget_constraint["amount_dollars"])
        if isinstance(budget_constraint, Mapping)
        else None
    )
    if require_budget and budget is not None and total_cost > budget + 1e-9:
        raise ValueError(f"native portfolio cost {total_cost} exceeds exact dollar budget {budget}")
    canonical = json.dumps(sorted(set(selected)), separators=(",", ":"))
    signature = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return NativePortfolio(tuple(sorted(set(selected))), total_cost, budget, signature, False)
