#!/usr/bin/env python
"""Build non-destructive IEEE123 SC-CMPO payload variants with common hard budgets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.upgrade_budget import derive_ieee123_budget_sweep, load_ieee123_upgrade_catalog  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123_budget_sweep.yaml")


def _resolve(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _load_config(path: Path | str) -> dict[str, Any]:
    return yaml.safe_load(_resolve(path).read_text(encoding="utf-8"))


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _qci_jobs(config: dict[str, Any], source_payload_names: set[str]) -> list[dict[str, Any]]:
    status_path = _resolve(config["source_qci_status"])
    rows: list[dict[str, Any]] = []
    if not status_path.exists():
        return rows
    with status_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            payload_name = Path(str(row["payload"])).name
            if payload_name not in source_payload_names:
                continue
            raw_solutions = json.loads(row.get("raw_solutions") or "[]")
            rows.append(
                {
                    "payload_name": payload_name,
                    "repeat": row.get("repeat", "0"),
                    "job_id": row.get("job_id", ""),
                    "status": row.get("status", "FAILED"),
                    "sample_count": len(raw_solutions),
                    "selection_rule": config["qci"]["sample_selection"],
                    "request_json": str(row.get("request_json", "")),
                    "response_json": str(row.get("response_json", "")),
                    "failure_reason": row.get("failure_reason", ""),
                }
            )
    return rows


def build_budgeted_ieee123_payloads(
    config_path: Path | str,
    output_dir: Path | str | None = None,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = _load_config(config_path)
    source_dir = _resolve(config["source_payload_dir"])
    output = _resolve(output_dir or config["output_dir"])
    source_paths = sorted(source_dir.glob("*.json"))
    if len(source_paths) != int(config["experiment"]["patch_count"]):
        raise ValueError(f"expected exactly 12 IEEE123 source payloads, found {len(source_paths)}")
    catalog = load_ieee123_upgrade_catalog(source_dir)
    system_dir = _resolve(config["source_system_dir"])
    budgets = derive_ieee123_budget_sweep(
        catalog,
        qci_metrics_path=system_dir / "qci_system_metrics.csv",
        baseline_metrics_path=system_dir / "baseline_system_metrics.csv",
    )
    jobs = _qci_jobs(config, {path.name for path in source_paths})
    completed = sum(str(row["status"]).upper() == "COMPLETED" for row in jobs)
    failed = len(jobs) - completed
    plan = {
        "config": str(config_path),
        "output_dir": str(output),
        "budget_count": len(budgets),
        "source_payload_count": len(source_paths),
        "budgeted_payload_count": len(source_paths) * len(budgets),
        "qci_jobs_completed": completed,
        "qci_jobs_failed": failed,
    }
    if dry_run:
        return {"dry_run": True, **plan}
    targets = [output / "budget_derivation.json", output / "budget_manifest.csv", output / "qci_job_status.csv"]
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError(f"budget-frontier build outputs already exist under {output}")
    output.mkdir(parents=True, exist_ok=True)
    payload_rows: list[dict[str, Any]] = []
    for level in budgets:
        budget_dir = output / "payloads" / level.budget_id
        budget_dir.mkdir(parents=True, exist_ok=True)
        for source_path in source_paths:
            target = budget_dir / source_path.name
            if target.exists() and not overwrite:
                raise FileExistsError(f"budgeted payload already exists: {target}")
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            payload["budget_constraint"] = {
                **level.to_dict(),
                "hard_constraint": True,
                "common_across_all_methods": True,
                "samples_per_payload": int(config["qci"]["samples_per_payload"]),
                "sample_selection": str(config["qci"]["sample_selection"]),
                "physical_asset_deduplication": config["experiment"]["physical_asset_deduplication"],
                "reject_over_budget_reconstruction": True,
                "enforcement": (
                    "reconstruct the complete 12-patch overlap consensus, deduplicate physical assets by "
                    "benchmark/anchor/technology, and reject cost above amount before projection or reporting"
                ),
            }
            payload["source_payload"] = str(source_path)
            payload["source_payload_sha256"] = _sha256(source_path)
            target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            payload_rows.append(
                {
                    "budget_id": level.budget_id,
                    "budget": level.amount,
                    "source_payload": str(source_path),
                    "source_payload_sha256": payload["source_payload_sha256"],
                    "budgeted_payload": str(target),
                    "scenario_count": payload["sc_cmpo"]["scenario_count"],
                    "hard_constraint": True,
                }
            )
    (output / "budget_derivation.json").write_text(
        json.dumps(
            {
                "schema": "cmpo.ieee123_budget_sweep.v1",
                "catalog_asset_count": len(catalog),
                "physical_anchor_count": len({asset.anchor_node for asset in catalog}),
                "budgets": [level.to_dict() for level in budgets],
                "construction_policy": config["budget_construction"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(payload_rows, output / "budget_manifest.csv")
    _write_csv(jobs, output / "qci_job_status.csv")
    (output / "build_summary.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = build_budgeted_ieee123_payloads(
        args.config,
        args.output_dir,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
