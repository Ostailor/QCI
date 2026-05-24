#!/usr/bin/env python
"""Export offline QCi Dirac-3-ready polynomial payloads for Phase 2."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.config import build_parser, config_from_args  # noqa: E402
from cmpo.data import generate_synthetic_dataset  # noqa: E402
from cmpo.hamiltonian_builder import build_scenario_hamiltonian  # noqa: E402
from cmpo.microgrid_design import generate_candidate_patches  # noqa: E402
from cmpo.qci_export import export_polynomial_model_payload, model_statistics, try_import_eqc_models  # noqa: E402


def _write_model_stats(rows: list[dict[str, object]], results_dir: Path) -> Path:
    path = results_dir / "model_stats.csv"
    if not rows:
        return path
    fieldnames = [
        "scenario",
        "patch",
        "horizon",
        "variable_count",
        "term_count",
        "degree",
        "continuous_variable_count",
        "integer_variable_count",
        "max_abs_coefficient",
        "coefficient_scaling_factor",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    """Generate payloads for all default scenarios and selected patches."""

    parser = build_parser("Export CMPO QCi-ready Phase 2 payloads.")
    parser.add_argument("--max-patch-size", type=int, default=1, help="Maximum candidate patch size to export.")
    parser.add_argument("--max-patches", type=int, default=1, help="Limit exported patches for runtime control.")
    parser.add_argument(
        "--export-subdir",
        default="qci_export",
        help="Subdirectory under results-dir for standalone exports so main-run evidence is not overwritten.",
    )
    args = parser.parse_args()
    config = config_from_args(args)
    config.output.results_dir.mkdir(parents=True, exist_ok=True)
    export_dir = config.output.results_dir / args.export_subdir
    export_dir.mkdir(parents=True, exist_ok=True)

    eqc_models = try_import_eqc_models()
    dataset = generate_synthetic_dataset(config.dataset, output_dir=config.output.data_dir)
    patches = generate_candidate_patches(dataset, max_patch_size=args.max_patch_size)[: args.max_patches]
    if not patches:
        raise SystemExit("No candidate patches available for export.")
    payload_dir = export_dir / "qci_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    for old_payload in payload_dir.glob("*.json"):
        old_payload.unlink()

    exported: list[Path] = []
    stat_rows: list[dict[str, object]] = []
    for scenario in dataset.scenarios:
        for patch in patches:
            model, metadata = build_scenario_hamiltonian(
                dataset,
                scenario,
                patch,
                output_dir=export_dir,
                write_export=False,
            )
            output_path = export_polynomial_model_payload(model, metadata, export_dir)
            stats = model_statistics(model)
            stat_rows.append(
                {
                    "scenario": metadata["scenario"],
                    "patch": metadata["patch"],
                    "horizon": metadata["horizon"],
                    **stats,
                }
            )
            exported.append(output_path)

    stats_path = _write_model_stats(stat_rows, export_dir)
    availability = "available" if eqc_models is not None else "not installed"
    print(f"eqc_models optional dependency: {availability}")
    print(f"Wrote {len(exported)} QCi payloads to {payload_dir}")
    print(f"Wrote model statistics to {stats_path}")


if __name__ == "__main__":
    main()
