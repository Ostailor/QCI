#!/usr/bin/env python
"""Compare global-master methods only after the identical IEEE123 recourse evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.budget_frontier import (  # noqa: E402
    add_marginal_ens_reduction,
    budget_win_tie_loss,
    pareto_frontier,
)


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml")
QCI_METHOD = "QCi global budget master V2"
RECOURSE_EVALUATOR = "ieee123_global_master_shared_recourse_v2"


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def compare_budget_masters(
    config_path: Path | str,
    input_csvs: Sequence[Path | str],
    *,
    output_dir: Path | str,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(config_path).read_text(encoding="utf-8"))
    inputs = [_resolve(path) for path in input_csvs]
    plan = {
        "inputs": [str(path) for path in inputs],
        "output_dir": str(_resolve(output_dir)),
        "required_classical_methods": config["classical_master_methods"],
        "qci_method": QCI_METHOD,
        "shared_recourse_evaluator": RECOURSE_EVALUATOR,
        "qci_submission_performed": False,
    }
    if dry_run:
        return {"dry_run": True, **plan}
    if not inputs or any(not path.is_file() for path in inputs):
        raise FileNotFoundError("comparison requires completed master-level result CSVs")
    frame = pd.concat([pd.read_csv(path).assign(source_csv=str(path)) for path in inputs], ignore_index=True)
    required = {
        "method",
        "budget_id",
        "budget",
        "total_upgrade_cost",
        "total_ens",
        "critical_ens",
        "recourse_evaluator",
        "trace_path",
    }
    missing = required - set(frame)
    if missing:
        raise ValueError(f"master comparison input missing columns: {sorted(missing)}")
    if set(frame["recourse_evaluator"].astype(str)) != {RECOURSE_EVALUATOR}:
        raise ValueError("all global-master methods must use the identical shared recourse evaluator")
    if frame.astype(str).apply(lambda column: column.str.contains("posthoc_existing_sample_budget_filter").any()).any():
        raise ValueError("V1 post-hoc rows are forbidden in the V2 master comparison")
    if (pd.to_numeric(frame["total_upgrade_cost"]) > pd.to_numeric(frame["budget"]) + 1e-6).any():
        raise ValueError("master comparison contains an over-budget portfolio")
    for trace in frame["trace_path"].astype(str):
        path = _resolve(trace)
        if not path.is_file():
            raise FileNotFoundError(f"master comparison trace is missing: {path}")
    expected = {QCI_METHOD, *config["classical_master_methods"]}
    budgets = set(frame["budget_id"].astype(str))
    for budget_id, group in frame.groupby("budget_id"):
        if set(group["method"].astype(str)) != expected:
            raise ValueError(f"method coverage mismatch at budget {budget_id}")
    if len(budgets) != 6:
        raise ValueError(f"master comparison requires six budgets, found {len(budgets)}")
    output = _resolve(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    matched = add_marginal_ens_reduction(frame)
    matched.to_csv(output / "table_budget_master_results.csv", index=False)
    outcomes = pd.concat(
        [
            budget_win_tie_loss(matched, qci_method=QCI_METHOD, metric=metric).assign(metric=metric)
            for metric in ("total_ens", "critical_ens")
        ],
        ignore_index=True,
    )
    outcomes.to_csv(output / "table_budget_master_win_tie_loss.csv", index=False)
    frontiers = pd.concat(
        [
            pareto_frontier(group, resilience_col="total_ens").assign(method=method)
            for method, group in matched.groupby("method")
        ],
        ignore_index=True,
    )
    frontiers.to_csv(output / "budget_master_pareto_frontier.csv", index=False)
    result = {
        **plan,
        "budget_count": len(budgets),
        "method_count": len(expected),
        "comparison_row_count": len(matched),
        "qci_submission_performed": False,
    }
    (output / "comparison_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument(
        "--output-dir",
        default="results/phase3/sc_cmpo/budget_master_v2/master_comparison",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = compare_budget_masters(
        args.config,
        args.inputs,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
