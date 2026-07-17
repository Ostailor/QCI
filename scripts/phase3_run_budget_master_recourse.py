#!/usr/bin/env python
"""Decode approved QCi global-master results and run the common IEEE123 recourse."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_master_recourse import (  # noqa: E402
    fix_portfolio_across_patches,
    run_fixed_portfolio_consensus,
)
from cmpo.full_system_dispatch import evaluate_full_system, evaluate_full_system_heldout  # noqa: E402
from cmpo.portfolio_decode import decode_master_sample  # noqa: E402
from cmpo.portfolio_diversity import select_unique_feasible_portfolios  # noqa: E402
from cmpo.scenario_coupled_model import load_public_grid, load_sc_cmpo_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml")


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _write_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _payloads(directory: Path) -> dict[str, dict[str, Any]]:
    rows = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }
    if len(rows) != 12:
        raise ValueError(f"shared IEEE123 recourse requires 12 patch payloads, found {len(rows)}")
    return rows


def _decoded_qci_portfolios(raw_dir: Path, limit: int) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    response_paths = sorted(raw_dir.glob("**/response.json"))
    if not response_paths:
        raise FileNotFoundError(
            f"no approved QCi master responses found under {raw_dir}; this runner never submits jobs"
        )
    for response_path in response_paths:
        request_path = response_path.with_name("request.json")
        if not request_path.is_file():
            raise FileNotFoundError(f"QCi response lacks preserved request: {response_path}")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        payload_path = _resolve(request["payload_path"])
        if "budget_master_v2/qci_master_payloads" not in str(payload_path):
            raise ValueError(f"response does not trace to a V2 global master: {response_path}")
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        solutions = response.get("results", {}).get("solutions", [])
        energies = response.get("results", {}).get("energies", [])
        for index, solution in enumerate(solutions):
            try:
                decoded = decode_master_sample(
                    payload,
                    solution,
                    energy=float(energies[index]) if index < len(energies) else 0.0,
                )
            except ValueError:
                continue
            grouped[decoded.budget_id].append(decoded)
    return {
        budget_id: select_unique_feasible_portfolios(portfolios, limit=limit)
        for budget_id, portfolios in grouped.items()
    }


def run_budget_master_recourse(
    config_path: Path | str,
    *,
    raw_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    output = _resolve(output_dir or Path(config["output_dir"]) / "recourse_results")
    qci_raw = _resolve(raw_dir or config["qci"]["raw_output_dir"])
    patch_payloads = _payloads(_resolve(config["source_payload_dir"]))
    plan = {
        "qci_submission_performed": False,
        "qci_raw_dir": str(qci_raw),
        "output_dir": str(output),
        "patch_count": len(patch_payloads),
        "top_unique_portfolios_per_budget": config["recourse"]["top_unique_portfolios_per_budget"],
        "training_scenario_count": config["recourse"]["training_scenario_count"],
        "heldout_n_1_count": config["recourse"]["heldout_n_1_count"],
        "gpu_parallel_dimensions": config["recourse"]["gpu_parallel_dimensions"],
    }
    if dry_run:
        return {"dry_run": True, **plan}
    grouped = _decoded_qci_portfolios(
        qci_raw,
        int(config["recourse"]["top_unique_portfolios_per_budget"]),
    )
    if len(grouped) != 6:
        raise ValueError(f"recourse requires decoded portfolios for all six budgets, found {len(grouped)}")
    public_config = load_sc_cmpo_config(_resolve("configs/phase3_sc_cmpo_ieee123.yaml"))
    grid = load_public_grid(public_config)
    system_rows: list[dict[str, Any]] = []
    heldout_rows: list[dict[str, Any]] = []
    consensus_rows: list[dict[str, Any]] = []
    upgrade_rows: list[dict[str, Any]] = []
    output.mkdir(parents=True, exist_ok=True)
    trace_dir = output / "system_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for budget_id, portfolios in sorted(grouped.items()):
        for rank, portfolio in enumerate(portfolios, start=1):
            fixed = fix_portfolio_across_patches(portfolio, patch_payloads)
            consensus, patch_values = run_fixed_portfolio_consensus(portfolio, patch_payloads, fixed)
            method = "QCi global budget master V2"
            system = evaluate_full_system(method, grid, patch_payloads, patch_values, consensus)
            heldout = evaluate_full_system_heldout(
                method,
                grid,
                patch_payloads,
                patch_values,
                consensus,
                limit=int(config["recourse"]["heldout_n_1_count"]),
            )
            trace_path = trace_dir / f"{budget_id}__rank_{rank:02d}.json"
            trace_path.write_text(
                json.dumps(
                    {
                        "budget_id": budget_id,
                        "portfolio_rank": rank,
                        "portfolio_signature": portfolio.signature,
                        "portfolio": {
                            "selected_asset_keys": list(portfolio.selected_asset_keys),
                            "total_upgrade_cost": portfolio.total_upgrade_cost,
                            "encoded_upgrade_cost": portfolio.encoded_upgrade_cost,
                            "actual_budget": portfolio.actual_budget,
                        },
                        "consensus": consensus,
                        "system": system,
                        "heldout": heldout,
                        "ac_validation": "run existing pinned IEEE123 OpenDSS replay separately",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            if system.get("status") == "completed":
                system_rows.append(
                    {
                        **system["system_metrics"],
                        "budget_id": budget_id,
                        "budget": portfolio.actual_budget,
                        "portfolio_rank": rank,
                        "portfolio_signature": portfolio.signature,
                        "trace_path": str(trace_path),
                    }
                )
                upgrade_rows.extend(
                    {
                        **row,
                        "budget_id": budget_id,
                        "portfolio_rank": rank,
                        "portfolio_signature": portfolio.signature,
                    }
                    for row in portfolio.upgrade_rows
                )
            if heldout.get("status") == "completed":
                heldout_rows.append(
                    {
                        **heldout["heldout_summary"],
                        "budget_id": budget_id,
                        "budget": portfolio.actual_budget,
                        "portfolio_rank": rank,
                        "portfolio_signature": portfolio.signature,
                        "trace_path": str(trace_path),
                    }
                )
            consensus_rows.append(
                {
                    "budget_id": budget_id,
                    "portfolio_rank": rank,
                    "portfolio_signature": portfolio.signature,
                    "converged": consensus.get("converged", False),
                    "iteration_count": consensus.get("iteration_count", 0),
                    "primal_residual": consensus.get("primal_residual", ""),
                    "dual_residual": consensus.get("dual_residual", ""),
                    "fixed_portfolio_excluded_from_patch_admm": True,
                }
            )
    _write_csv(system_rows, output / "system_results.csv")
    _write_csv(heldout_rows, output / "heldout_results.csv")
    _write_csv(consensus_rows, output / "consensus_convergence.csv")
    _write_csv(upgrade_rows, output / "upgrade_plans.csv")
    result = {**plan, "budget_count": len(grouped), "system_result_count": len(system_rows)}
    (output / "run_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--raw-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_budget_master_recourse(
        args.config,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
