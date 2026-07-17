#!/usr/bin/env python
"""Validate the pinned IEEE 123-bus feeder with OpenDSS before optimization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.ieee123_sc_cmpo_adapter import (  # noqa: E402
    parse_ieee123_sc_cmpo_case,
    validate_ieee123_powerflow,
)
from cmpo.scenario_coupled_model import load_sc_cmpo_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/phase3_sc_cmpo_ieee123.yaml")
DEFAULT_OUTPUT = Path("results/phase3/sc_cmpo/distribution_validation.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and solve the pinned IEEE 123-bus OpenDSS feeder, then verify parser/engine "
            "count parity, published load totals, convergence, and voltage bounds."
        )
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="IEEE123 SC-CMPO YAML config.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown validation report path.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the OpenDSS validation and print its result without writing report files.",
    )
    return parser


def _display(value: Any) -> str:
    if value is None:
        return "not available"
    if isinstance(value, float):
        return f"{value:.9g}"
    if isinstance(value, (list, tuple)):
        return f"{len(value)} exact values"
    return str(value)


def _render_report(config: dict[str, Any], report: dict[str, Any]) -> str:
    status = "PASS" if report.get("passed") else "FAIL"
    source = config["source"]
    lines = [
        "# IEEE 123-Bus Distribution Validation",
        "",
        f"**Status:** {status}",
        "",
        "This is a pre-optimization gate. No SC-CMPO payload is considered validated unless the "
        "published OpenDSS feeder compiles, converges, and agrees with the repository parser on "
        "the checks below.",
        "",
        "## Source",
        "",
        f"- Benchmark: `{config['benchmark']['id']}`",
        f"- Version: {source['version']}",
        f"- URL: {source['url']}",
        f"- Master file: `{source['local_path']}`",
        f"- Master SHA-256: `{source['sha256']}`",
        f"- Engine: {report.get('engine', 'OpenDSSDirect.py')} "
        f"{report.get('opendssdirect_version', '')}".rstrip(),
        f"- Backend: DSS-Python {report.get('dss_python_version', 'not available')}",
        "",
        "## Electrical Solve",
        "",
        f"- Converged: `{bool(report.get('solver_converged'))}`",
        f"- Solver iterations: `{_display(report.get('solver_iterations'))}`",
        f"- Minimum bus voltage: `{_display(report.get('minimum_voltage_pu'))}` pu",
        f"- Maximum bus voltage: `{_display(report.get('maximum_voltage_pu'))}` pu",
        f"- Published load represented: `{_display(report.get('engine_total_load_kw'))}` kW / "
        f"`{_display(report.get('engine_total_load_kvar'))}` kvar",
        f"- Source power: `{_display(report.get('source_active_power_kw'))}` kW / "
        f"`{_display(report.get('source_reactive_power_kvar'))}` kvar",
        f"- Active loss: `{_display(report.get('active_losses_kw'))}` kW",
        f"- Reactive loss: `{_display(report.get('reactive_losses_kvar'))}` kvar",
        "",
        "## Parser/Engine Checks",
        "",
        "| Check | Observed | Expected | Pass |",
        "|---|---:|---:|:---:|",
    ]
    for check in report.get("checks", []):
        lines.append(
            f"| {check.get('name', check.get('check', 'unnamed'))} | "
            f"{_display(check.get('observed', check.get('actual')))} | "
            f"{_display(check.get('expected'))} | {'yes' if check.get('passed') else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "The validation uses the published unbalanced feeder, phase connections, line-code "
            "impedances, loads, transformers, regulator controls, and capacitors. Published line "
            "codes contain no ampacity values, so optimization artifacts preserve line ratings as "
            "unavailable instead of substituting OpenDSS defaults. PV and BESS are introduced only "
            "later as upgrade choices priced from the pinned NREL ATB catalog.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_distribution_powerflow(
    config_path: Path,
    output_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the IEEE123 OpenDSS gate and optionally persist Markdown and JSON evidence."""

    config = load_sc_cmpo_config(config_path)
    case = parse_ieee123_sc_cmpo_case(config)
    report = validate_ieee123_powerflow(case)
    report = {
        **report,
        "benchmark": str(config["benchmark"]["id"]),
        "config_path": str(config_path),
        "validation_gate": "pre_optimization",
        "qci_was_run": False,
    }
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render_report(config, report), encoding="utf-8")
        output_path.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    args = build_parser().parse_args()
    result = validate_distribution_powerflow(Path(args.config), Path(args.output), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if not result.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
