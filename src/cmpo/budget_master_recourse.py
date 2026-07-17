"""Shared recourse contract for decoded global upgrade-master portfolios."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from cmpo.matched_problem_baselines import _compile_payload, _fractions_to_values
from cmpo.overlap_consensus import reconstruct_patch_values, run_method_consensus
from cmpo.portfolio_decode import DecodedPortfolio


@dataclass(frozen=True)
class RecourseWorkItem:
    budget_id: str
    portfolio_signature: str
    portfolio_rank: int
    patch_name: str
    evaluation_stage: str
    scenario_or_contingency: str
    gpu_parallel_group: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FIXED_UPGRADE_VARIABLES = frozenset(
    {
        "upgrade_select_pv",
        "upgrade_select_bess",
        "upgrade_select_dispatchable",
        "pv_capacity_fraction",
        "bess_energy_fraction",
        "bess_power_fraction",
        "dispatchable_capacity_fraction",
    }
)


def _physical_anchor(payload: Mapping[str, Any]) -> str:
    nodes = list(payload["sc_cmpo"].get("patch_public_nodes", ()))
    if nodes:
        ranked = sorted(
            (
                (
                    float(node.get("load_kw", 0.0)) - float(node.get("generation_kw", 0.0)),
                    float(node.get("load_kw", 0.0)),
                    str(node["node_id"]),
                )
                for node in nodes
            ),
            key=lambda item: (-item[0], -item[1], item[2]),
        )
        return ranked[0][2]
    return sorted(str(item) for item in payload["sc_cmpo"]["upgrade_patch"]["node_ids"])[0]


def fix_portfolio_across_patches(
    portfolio: DecodedPortfolio,
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Fix one charge-once physical portfolio into every patch recourse model."""

    selected = set(portfolio.selected_asset_keys)
    result: dict[str, dict[str, Any]] = {}
    for name, payload in sorted(payloads.items()):
        benchmark = str(payload["sc_cmpo"]["public_benchmark"])
        anchor = _physical_anchor(payload)
        fractions = tuple(
            float(f"{benchmark}::{anchor}::{technology}" in selected)
            for technology in ("pv", "bess", "dispatchable_generation")
        )
        compiled = _compile_payload(payload)
        values = _fractions_to_values(payload, compiled, fractions)
        result[name] = {
            "portfolio_signature": portfolio.signature,
            "fixed_portfolio_asset_keys": list(portfolio.selected_asset_keys),
            "charge_once_upgrade_cost": portfolio.total_upgrade_cost,
            "physical_anchor": anchor,
            "patch_values": values,
        }
    return result


def build_recourse_work_items(
    portfolios: Sequence[DecodedPortfolio],
    patch_names: Sequence[str],
    training_scenarios: Sequence[str],
    heldout_contingencies: Sequence[str],
) -> list[RecourseWorkItem]:
    rows: list[RecourseWorkItem] = []
    for rank, portfolio in enumerate(portfolios, start=1):
        group = f"{portfolio.budget_id}:{portfolio.signature}"
        for patch in sorted(patch_names):
            for scenario in training_scenarios:
                rows.append(
                    RecourseWorkItem(
                        budget_id=portfolio.budget_id,
                        portfolio_signature=portfolio.signature,
                        portfolio_rank=rank,
                        patch_name=str(patch),
                        evaluation_stage="training_patch_recourse",
                        scenario_or_contingency=str(scenario),
                        gpu_parallel_group=group,
                    )
                )
            for contingency in heldout_contingencies:
                rows.append(
                    RecourseWorkItem(
                        budget_id=portfolio.budget_id,
                        portfolio_signature=portfolio.signature,
                        portfolio_rank=rank,
                        patch_name=str(patch),
                        evaluation_stage="heldout_n_1",
                        scenario_or_contingency=str(contingency),
                        gpu_parallel_group=group,
                    )
                )
    return rows


def run_fixed_portfolio_consensus(
    portfolio: DecodedPortfolio,
    payloads: Mapping[str, Mapping[str, Any]],
    fixed: Mapping[str, Mapping[str, Any]],
    *,
    method: str = "QCi global budget master V2",
) -> tuple[dict[str, Any], dict[str, dict[str, float | int]]]:
    """Run the existing overlap ADMM on recourse while preserving master-fixed assets.

    Upgrade variables are parameters after the global master solve, so they are
    removed from the ADMM variable set and merged back unchanged afterward.
    """

    views: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for name, payload in sorted(payloads.items()):
        view = copy.deepcopy(dict(payload))
        view["variables"] = [
            variable
            for variable in view["variables"]
            if str(variable["name"]) not in FIXED_UPGRADE_VARIABLES
        ]
        shared = view["sc_cmpo"].get("shared_first_stage_variables", [])
        view["sc_cmpo"]["shared_first_stage_variables"] = [
            variable for variable in shared if str(variable) not in FIXED_UPGRADE_VARIABLES
        ]
        views[name] = view
        patch_values = fixed[name]["patch_values"]
        rows.append(
            {
                "payload_name": name,
                "method": method,
                "runtime_seconds": 0.0,
                "solution_values": {
                    key: value
                    for key, value in patch_values.items()
                    if key not in FIXED_UPGRADE_VARIABLES
                },
            }
        )
    consensus = run_method_consensus(views, rows)
    if consensus.get("status") != "completed" or not consensus.get("converged"):
        raise ValueError(f"fixed-portfolio recourse consensus failed: {consensus.get('failure_reason', '')}")
    reconstructed = reconstruct_patch_values(views, consensus["consensus_values"])
    for name in reconstructed:
        reconstructed[name].update(
            {
                key: value
                for key, value in fixed[name]["patch_values"].items()
                if key in FIXED_UPGRADE_VARIABLES
            }
        )
    consensus["global_master_portfolio_signature"] = portfolio.signature
    consensus["fixed_portfolio_asset_keys"] = list(portfolio.selected_asset_keys)
    consensus["fixed_portfolio_excluded_from_patch_admm"] = True
    consensus["upgrade_cost_charged_once"] = portfolio.total_upgrade_cost
    return consensus, reconstructed
