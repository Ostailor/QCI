#!/usr/bin/env python
"""Build the create-only public IEEE123 IRC-CMPO true-recourse dataset.

This command is deliberately offline: it constructs portfolios from the pinned
public catalog and evaluates every accepted label with the fixed-upgrade
SLSQP/MILP recourse oracle.  It contains no QCi client or submission path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_feasibility import (  # noqa: E402
    AnchorFeasibility,
    derive_local_feasibility,
    verify_local_feasibility_encoding,
)
from cmpo.irc_cmpo_master import IRCAsset, load_catalog  # noqa: E402
from cmpo.irc_cmpo_recourse import (  # noqa: E402
    FixedRecourseCache,
    evaluate_fixed_upgrade_recourse,
)
from cmpo.irc_cmpo_surrogate import stratified_portfolio_split  # noqa: E402
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_irc_cmpo_ieee123.yaml")
DEFAULT_PUBLIC_CONFIG = Path("configs/phase3_sc_cmpo_ieee123.yaml")
REQUIRED_PROVENANCE_FAMILIES = (
    "exact_milp_or_cp_sat",
    "classical_benders",
    "greedy_cost_resilience",
    "gpu_random_feasible",
    "qubo",
    "technology_anchor_ablation",
    "pareto_neighborhood_mutation",
)
FAILURE_COLUMNS = (
    "portfolio_signature",
    "generation_method",
    "selected_asset_keys",
    "error_type",
    "error_message",
    "runtime_seconds",
)


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _signature(keys: Sequence[str]) -> str:
    encoded = json.dumps(sorted(set(map(str, keys))), separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _adequate_patterns(anchor: AnchorFeasibility) -> tuple[tuple[int, int, int], ...]:
    patterns = tuple(row.pattern for row in anchor.patterns if row.adequate)
    if not patterns:
        raise ValueError(f"anchor {anchor.anchor_node} has no locally feasible public-catalog pattern")
    return patterns


def _selected_keys(
    anchors: Sequence[AnchorFeasibility], patterns: Sequence[tuple[int, int, int]]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            key
            for anchor, pattern in zip(anchors, patterns, strict=True)
            for key, bit in zip(anchor.asset_keys, pattern, strict=True)
            if bit
        )
    )


def generate_candidate_portfolios(
    assets: Sequence[IRCAsset],
    local_feasibility: Sequence[AnchorFeasibility],
    *,
    minimum_unique: int = 3000,
    random_seed: int = 2026,
) -> pd.DataFrame:
    """Generate public-catalog candidates with all seven required provenances.

    Candidate construction uses only catalog costs and directly enumerated local
    adequacy.  It does not create synthetic grid observations or recourse labels.
    """

    if minimum_unique < len(REQUIRED_PROVENANCE_FAMILIES):
        raise ValueError("minimum_unique must allow every required provenance family")
    assets = tuple(sorted(assets, key=lambda item: item.asset_key))
    anchors = tuple(sorted(local_feasibility, key=lambda item: item.anchor_node))
    if not assets or not anchors:
        raise ValueError("public assets and local feasibility records are required")
    if any(not verify_local_feasibility_encoding(anchor) and anchor.penalty_terms for anchor in anchors):
        raise ValueError("a local-feasibility polynomial failed direct enumeration")
    if {asset.asset_key for asset in assets} != {
        key for anchor in anchors for key in anchor.asset_keys
    }:
        raise ValueError("local-feasibility anchors do not cover the physical asset catalog exactly")

    valid = tuple(_adequate_patterns(anchor) for anchor in anchors)
    possible = math.prod(len(rows) for rows in valid)
    if possible < minimum_unique:
        raise ValueError(
            f"only {possible} locally feasible public portfolios exist; requested {minimum_unique}"
        )
    asset_by_key = {asset.asset_key: asset for asset in assets}
    maximum_cost = math.fsum(asset.total_cost for asset in assets)
    technology_score = {"pv": 0.45, "bess": 0.75, "dispatchable_generation": 1.0}
    rng = np.random.default_rng(random_seed)
    rows: dict[str, dict[str, Any]] = {}

    def admit(
        patterns: Sequence[tuple[int, int, int]],
        family: str,
        detail: str,
        **audit: Any,
    ) -> None:
        keys = _selected_keys(anchors, patterns)
        signature = _signature(keys)
        if signature in rows:
            sources = set(json.loads(rows[signature]["candidate_provenance_sources"]))
            sources.add(family)
            rows[signature]["candidate_provenance_sources"] = json.dumps(sorted(sources))
            rows[signature].update(audit)
            return
        cost = math.fsum(asset_by_key[key].total_cost for key in keys)
        technologies = sorted({asset_by_key[key].technology for key in keys})
        rows[signature] = {
            "portfolio_signature": signature,
            "selected_asset_keys": json.dumps(keys),
            "upgrade_cost": cost,
            "generation_method": family,
            "candidate_provenance_sources": json.dumps([family]),
            "generation_detail": detail,
            "technology_mix": "+".join(technologies) if technologies else "existing_resources_only",
            "selected_asset_count": len(keys),
            **{asset.asset_key: int(asset.asset_key in keys) for asset in assets},
            **audit,
        }

    def local_objective(anchor: AnchorFeasibility, pattern: tuple[int, int, int], weight: float) -> float:
        selected = [asset_by_key[key] for key, bit in zip(anchor.asset_keys, pattern, strict=True) if bit]
        cost = math.fsum(asset.total_cost for asset in selected) / maximum_cost
        preparedness = math.fsum(technology_score[asset.technology] for asset in selected)
        return weight * cost - preparedness

    def exact_pattern_milp(weight: float) -> tuple[tuple[tuple[int, int, int], ...], str]:
        offsets: list[tuple[int, int]] = []
        objective: list[float] = []
        cursor = 0
        for anchor, patterns in zip(anchors, valid, strict=True):
            start = cursor
            objective.extend(local_objective(anchor, pattern, weight) for pattern in patterns)
            cursor += len(patterns)
            offsets.append((start, cursor))
        matrix = np.zeros((len(anchors), cursor), dtype=float)
        for anchor_index, (start, stop) in enumerate(offsets):
            matrix[anchor_index, start:stop] = 1.0
        result = milp(
            np.asarray(objective, dtype=float),
            integrality=np.ones(cursor, dtype=int),
            bounds=Bounds(np.zeros(cursor), np.ones(cursor)),
            constraints=LinearConstraint(matrix, np.ones(len(anchors)), np.ones(len(anchors))),
            options={"presolve": True},
        )
        if not result.success or result.x is None or not np.isfinite(result.x).all():
            raise RuntimeError(
                f"exact MILP/HiGHS portfolio master failed for lambda={weight:g}: {result.message}"
            )
        solution: list[tuple[int, int, int]] = []
        for patterns, (start, stop) in zip(valid, offsets, strict=True):
            block = np.asarray(result.x[start:stop], dtype=float)
            selected_index = int(np.argmax(block))
            if block[selected_index] < 1.0 - 1e-7 or abs(float(block.sum()) - 1.0) > 1e-7:
                raise RuntimeError("exact MILP returned a nonintegral or non-one-hot anchor pattern")
            solution.append(patterns[selected_index])
        enumerated = tuple(
            min(patterns, key=lambda pattern: (local_objective(anchor, pattern, weight), pattern))
            for anchor, patterns in zip(anchors, valid, strict=True)
        )
        if not math.isclose(
            math.fsum(local_objective(anchor, pattern, weight) for anchor, pattern in zip(anchors, solution, strict=True)),
            math.fsum(local_objective(anchor, pattern, weight) for anchor, pattern in zip(anchors, enumerated, strict=True)),
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise RuntimeError("exact MILP objective disagrees with independent pattern enumeration")
        return tuple(solution), str(result.message)

    # Literal binary MILP master solves for deterministic scalar weights.
    exact_seeds: list[tuple[tuple[int, int, int], ...]] = []
    for weight in (0.0, 0.05, 0.10, 0.25, 0.50, 1.0):
        solution, solver_message = exact_pattern_milp(weight)
        exact_seeds.append(solution)
        admit(
            solution,
            REQUIRED_PROVENANCE_FAMILIES[0],
            f"exact scipy.optimize.milp/HiGHS pattern master, lambda={weight:g}",
            exact_solver_success=True,
            exact_solver_status=solver_message,
        )

    cheapest = tuple(
        min(
            patterns,
            key=lambda pattern: (
                math.fsum(
                    asset_by_key[key].total_cost
                    for key, bit in zip(anchor.asset_keys, pattern, strict=True)
                    if bit
                ),
                pattern,
            ),
        )
        for anchor, patterns in zip(anchors, valid, strict=True)
    )
    # Benders-style anchor cuts: replace one local subproblem solution at a time.
    for index, (anchor, patterns) in enumerate(zip(anchors, valid, strict=True)):
        alternatives = sorted(patterns, key=lambda pattern: (sum(pattern), pattern))
        candidate = list(cheapest)
        candidate[index] = alternatives[min(1, len(alternatives) - 1)]
        admit(candidate, REQUIRED_PROVENANCE_FAMILIES[1], f"anchor subproblem cut at {anchor.anchor_node}")

    # Greedy marginal preparedness additions from the cheapest feasible portfolio.
    greedy = list(cheapest)
    for index, (anchor, patterns) in enumerate(zip(anchors, valid, strict=True)):
        current = greedy[index]
        replacements = sorted(
            patterns,
            key=lambda pattern: (
                -sum(pattern),
                local_objective(anchor, pattern, 0.25),
                pattern,
            ),
        )
        if replacements:
            greedy[index] = replacements[0]
            admit(tuple(greedy), REQUIRED_PROVENANCE_FAMILIES[2], f"greedy preparedness addition at {anchor.anchor_node}")
            greedy[index] = current

    # QUBO candidates come from exact local quadratic-score enumeration.
    for beta in (0.10, 0.25, 0.50, 0.75, 1.0):
        solution = []
        for anchor, patterns in zip(anchors, valid, strict=True):
            solution.append(
                min(
                    patterns,
                    key=lambda pattern: (
                        local_objective(anchor, pattern, beta)
                        - 0.05 * (pattern[0] * pattern[1] + pattern[1] * pattern[2]),
                        pattern,
                    ),
                )
            )
        admit(solution, REQUIRED_PROVENANCE_FAMILIES[4], f"exact local QUBO score, beta={beta:g}")

    # Technology/anchor ablations begin at the maximum locally adequate plan.
    fullest = tuple(max(patterns, key=lambda pattern: (sum(pattern), pattern)) for patterns in valid)
    for index, (anchor, patterns) in enumerate(zip(anchors, valid, strict=True)):
        for pattern in sorted(patterns, key=lambda item: (sum(item), item)):
            if pattern == fullest[index]:
                continue
            candidate = list(fullest)
            candidate[index] = pattern
            admit(candidate, REQUIRED_PROVENANCE_FAMILIES[5], f"technology ablation at {anchor.anchor_node}")

    # Pareto-neighborhood mutations alter one or two anchors around exact seeds.
    for seed_index, seed in enumerate(exact_seeds or [cheapest]):
        for left in range(len(anchors)):
            for right in range(left, min(len(anchors), left + 2)):
                candidate = list(seed)
                candidate[left] = valid[left][(seed_index + left + 1) % len(valid[left])]
                candidate[right] = valid[right][(seed_index + right + 2) % len(valid[right])]
                admit(candidate, REQUIRED_PROVENANCE_FAMILIES[6], f"one/two-anchor mutation of exact seed {seed_index}")

    # Preserve a distinct representative for every provenance when two search
    # families identify the same optimum.  The fallback is a deterministic
    # mixed-radix continuation of that family's feasible search, not a relabel of
    # an existing portfolio.
    for family_index, family in enumerate(REQUIRED_PROVENANCE_FAMILIES):
        if any(row["generation_method"] == family for row in rows.values()):
            continue
        for offset in range(possible):
            value = (offset * 17 + family_index * 29) % possible
            solution = []
            for patterns in valid:
                solution.append(patterns[value % len(patterns)])
                value //= len(patterns)
            before = len(rows)
            admit(solution, family, "deterministic feasible continuation after an optimum collision")
            if len(rows) > before:
                break

    # NumPy-vectorized random feasible sampling is the deterministic CPU fallback
    # for the GPU-compatible discrete sampler; it samples only enumerated valid rows.
    while len(rows) < minimum_unique:
        batch = max(256, minimum_unique - len(rows))
        draws = np.column_stack([rng.integers(0, len(patterns), size=batch) for patterns in valid])
        before = len(rows)
        for draw in draws:
            solution = tuple(patterns[int(index)] for patterns, index in zip(valid, draw, strict=True))
            family = REQUIRED_PROVENANCE_FAMILIES[3]
            if len(rows) % 5 == 0 and exact_seeds:
                family = REQUIRED_PROVENANCE_FAMILIES[6]
            admit(solution, family, "vectorized feasible discrete search")
            if len(rows) >= minimum_unique:
                break
        if len(rows) == before:
            # Deterministic mixed-radix enumeration guarantees completion if
            # random draws saturate near the requested population size.
            for code in range(possible):
                value = code
                solution = []
                for patterns in valid:
                    solution.append(patterns[value % len(patterns)])
                    value //= len(patterns)
                admit(solution, REQUIRED_PROVENANCE_FAMILIES[3], "mixed-radix feasible enumeration")
                if len(rows) >= minimum_unique:
                    break
    frame = pd.DataFrame(list(rows.values())[:minimum_unique])
    present = set(frame["generation_method"])
    if missing := set(REQUIRED_PROVENANCE_FAMILIES) - present:
        # A provenance can collide with an earlier identical portfolio.  Promote
        # a portfolio whose merged provenance includes it, without changing its
        # physical signature or label.
        claimed = {
            int(group.index[0])
            for method, group in frame.groupby("generation_method", sort=False)
            if method in REQUIRED_PROVENANCE_FAMILIES
        }
        for family in sorted(missing):
            candidates = frame[frame["candidate_provenance_sources"].map(lambda value: family in json.loads(value))]
            candidates = candidates[~candidates.index.isin(claimed)]
            if candidates.empty:
                raise ValueError(f"candidate generation produced no {family} portfolio")
            selected_index = int(candidates.index[0])
            frame.loc[selected_index, "generation_method"] = family
            claimed.add(selected_index)
    return frame.sort_values("portfolio_signature").reset_index(drop=True)


def _result_record(result: Any) -> dict[str, Any]:
    names = (
        "critical_ens",
        "total_ens",
        "maximum_customers_unserved",
        "critical_infrastructure_outage_hours",
        "critical_load_served_fraction",
        "operating_cost",
        "upgrade_cost",
        "heldout_critical_ens",
        "heldout_total_ens",
        "feasibility",
        "solver_status",
        "selected_solver",
        "runtime_seconds",
        "patch_count",
        "training_scenario_count",
        "heldout_contingency_count",
        "consensus_algorithm",
        "projection_scope",
        "consensus_trace_id",
        "system_trace_id",
        "heldout_trace_id",
        "solver_paths",
        "open_dss_replay",
    )
    missing = [name for name in names if not hasattr(result, name)]
    if missing:
        raise ValueError(f"true recourse result is missing fields: {missing}")
    return {name: getattr(result, name) for name in names}


def _write_csv_new(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, index=False)


def write_labeled_dataset(
    candidates: pd.DataFrame,
    *,
    assets: Sequence[IRCAsset],
    evaluator: Callable[[tuple[str, ...]], Any],
    output_dir: Path | str,
    minimum_required: int,
    random_seed: int,
) -> dict[str, Any]:
    """Evaluate every candidate and atomically create the three dataset tables."""

    output = Path(output_dir)
    targets = (
        output / "portfolio_labels.csv",
        output / "split_manifest.csv",
        output / "recourse_failures.csv",
    )
    if existing := [str(path) for path in targets if path.exists()]:
        raise FileExistsError(f"IRC-CMPO dataset artifacts are create-only: {existing}")
    if candidates["portfolio_signature"].astype(str).duplicated().any():
        raise ValueError("candidate portfolio signatures must be unique")
    asset_by_key = {asset.asset_key: asset for asset in assets}
    labels: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for candidate in candidates.to_dict("records"):
        signature = str(candidate["portfolio_signature"])
        selected = tuple(sorted(json.loads(candidate["selected_asset_keys"])))
        unknown = set(selected) - set(asset_by_key)
        if unknown:
            raise ValueError(f"candidate {signature} contains unknown assets: {sorted(unknown)}")
        expected_cost = math.fsum(asset_by_key[key].total_cost for key in selected)
        started = time.perf_counter()
        try:
            result = evaluator(selected)
            metrics = _result_record(result)
            if not bool(metrics["feasibility"]):
                raise RuntimeError("true fixed-upgrade recourse reported infeasible")
            if int(metrics["patch_count"]) != 12:
                raise ValueError("true recourse did not evaluate all 12 public patches")
            if int(metrics["training_scenario_count"]) != 8:
                raise ValueError("true recourse did not evaluate all 8 training scenarios")
            if int(metrics["heldout_contingency_count"]) != 10:
                raise ValueError("true recourse did not evaluate all 10 held-out contingencies")
            if str(metrics["consensus_algorithm"]) != "overlap_consensus_admm":
                raise ValueError("true recourse did not use the common overlap-consensus algorithm")
            if str(metrics["projection_scope"]) != "full_system_active_power_projection":
                raise ValueError("true recourse did not use the common full-system projection")
            if not math.isclose(float(metrics["upgrade_cost"]), expected_cost, rel_tol=1e-9, abs_tol=1e-6):
                raise ValueError("true recourse upgrade cost disagrees with the charge-once catalog cost")
            solver_paths = metrics.pop("solver_paths")
            path_text = " | ".join(map(str, solver_paths))
            if "SLSQP nonlinear recourse" not in path_text or "piecewise-linear MILP recourse" not in path_text:
                raise ValueError("true recourse did not execute both required solver paths")
            labels.append(
                {
                    **candidate,
                    **metrics,
                    "solver_paths": json.dumps(list(solver_paths)),
                    "critical_load_served": metrics["critical_load_served_fraction"],
                    "true_fixed_upgrade_recourse": True,
                    "used_fraction_completion": False,
                    "recourse_label_source": "evaluate_fixed_upgrade_recourse",
                }
            )
        except Exception as exc:  # noqa: BLE001 - failures are an explicit durable output
            failures.append(
                {
                    "portfolio_signature": signature,
                    "generation_method": candidate["generation_method"],
                    "selected_asset_keys": candidate["selected_asset_keys"],
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "runtime_seconds": time.perf_counter() - started,
                }
            )
    label_frame = pd.DataFrame(labels)
    if label_frame.empty:
        manifest = pd.DataFrame(columns=["portfolio_signature", "split"])
    else:
        manifest = stratified_portfolio_split(label_frame, random_seed=random_seed)
    failure_frame = pd.DataFrame(failures, columns=FAILURE_COLUMNS)
    _write_csv_new(targets[0], label_frame)
    _write_csv_new(targets[1], manifest)
    _write_csv_new(targets[2], failure_frame)
    result = {
        "candidate_portfolios_evaluated": len(candidates),
        "successful_true_recourse_labels": len(label_frame),
        "recourse_failures": len(failure_frame),
        "minimum_required": int(minimum_required),
        "minimum_met": len(label_frame) >= minimum_required,
        "qci_jobs_submitted": 0,
    }
    if not result["minimum_met"]:
        raise RuntimeError(
            f"only {len(label_frame)} true-recourse labels succeeded; {minimum_required} are required"
        )
    return result


def _load_payloads(path: Path) -> dict[str, dict[str, Any]]:
    payloads = {
        item.stem: json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json"))
    }
    if len(payloads) != 12:
        raise ValueError(f"expected 12 pinned IEEE123 payloads, found {len(payloads)}")
    return payloads


def build_dataset(
    config_path: Path | str = DEFAULT_CONFIG,
    *,
    output_dir: Path | str | None = None,
    minimum_unique: int | None = None,
    evaluator: Callable[[tuple[str, ...]], Any] | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    assets = load_catalog(_resolve(config["source_asset_catalog"]))
    payloads = _load_payloads(_resolve(config["source_payload_dir"]))
    feasibility = derive_local_feasibility(
        payloads,
        assets,
        # Adequate/inadequate pattern enumeration is independent of penalty
        # magnitude.  The payload builder derives the final data-scaled rho.
        rho_feasibility=1.0,
    )
    required = int(minimum_unique or config["surrogate"]["minimum_unique_portfolios"])
    candidates = generate_candidate_portfolios(
        assets,
        feasibility,
        minimum_unique=required,
        random_seed=int(config["surrogate"]["random_seed"]),
    )
    solver_cache: FixedRecourseCache | None = None
    if evaluator is None:
        public_config = _resolve(config.get("source_sc_cmpo_config", DEFAULT_PUBLIC_CONFIG))
        grid = load_public_grid(load_sc_cmpo_config(public_config))
        solver_cache = FixedRecourseCache()
        evaluator = lambda selected: evaluate_fixed_upgrade_recourse(  # noqa: E731
            payloads,
            assets,
            selected,
            grid=grid,
            heldout_limit=10,
            solver_cache=solver_cache,
        )
    output = _resolve(output_dir or Path(config["output_dir"]) / "dataset")
    result = write_labeled_dataset(
        candidates,
        assets=assets,
        evaluator=evaluator,
        output_dir=output,
        minimum_required=required,
        random_seed=int(config["surrogate"]["random_seed"]),
    )
    if solver_cache is not None:
        result["fixed_recourse_cache_hits"] = solver_cache.hits
        result["fixed_recourse_cache_misses"] = solver_cache.misses
        result["fixed_recourse_cache_entries"] = len(solver_cache.solutions)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    parser.add_argument("--minimum-unique", type=int)
    args = parser.parse_args()
    print(
        json.dumps(
            build_dataset(
                args.config,
                output_dir=args.output_dir,
                minimum_unique=args.minimum_unique,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
