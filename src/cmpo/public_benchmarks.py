"""Phase 3 public-benchmark case registry."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from cmpo.benchmarks import PGLIB_CASES, _case_provenance, build_pglib_microgrid_case
from cmpo.config import DatasetConfig
from cmpo.data import GridCase, generate_synthetic_dataset
from cmpo.scenarios import build_default_scenarios


PUBLIC_BENCHMARKS: dict[str, dict[str, Any]] = {
    name: {
        "source": f"{case['label']} PGLib-derived microgrid stress adapter",
        "provenance": _case_provenance(name),
        "default_microgrids": int(case["default_microgrids"]),
    }
    for name, case in PGLIB_CASES.items()
}


def available_public_benchmarks() -> list[str]:
    """Return benchmark names supported by the Phase 3 registry."""

    return sorted(PUBLIC_BENCHMARKS)


def _write_provenance(name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}_manifest.json"
    path.write_text(json.dumps(PUBLIC_BENCHMARKS[name], indent=2), encoding="utf-8")
    return path


def build_public_benchmark_case(
    name: str,
    *,
    horizon_hours: int,
    seed: int,
    scenario_count: int,
    output_dir: Path | str | None = None,
) -> GridCase:
    """Build a deterministic public-benchmark-derived CMPO case."""

    if name not in PUBLIC_BENCHMARKS:
        raise ValueError(f"unsupported public benchmark: {name}")
    out_dir = None if output_dir is None else Path(output_dir)
    case = build_pglib_microgrid_case(
        name,
        horizon_hours=horizon_hours,
        seed=seed,
        scenario_count=scenario_count,
        output_dir=out_dir,
        max_microgrids=int(PUBLIC_BENCHMARKS[name]["default_microgrids"]),
    )
    if out_dir is not None:
        _write_provenance(name, out_dir)
    return case


def build_stress_case(
    *,
    n_microgrids: int,
    horizon_hours: int,
    seed: int,
    scenario_count: int,
    output_dir: Path | str,
) -> GridCase:
    """Build a deterministic high-stress synthetic Phase 3 case."""

    case = generate_synthetic_dataset(
        DatasetConfig(seed=seed, n_microgrids=n_microgrids, horizon_hours=horizon_hours),
        output_dir=output_dir,
    )
    scenarios = build_default_scenarios(n_microgrids, horizon_hours)[:scenario_count]
    return replace(case, scenarios=scenarios, documentation=f"Phase 3 stress case. {case.documentation}")
