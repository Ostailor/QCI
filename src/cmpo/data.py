"""Deterministic synthetic microgrid data generation.

The generated case is designed for Phase 2 evidence and reproducibility. It is
synthetic, uses plausible engineering ranges, and does not encode proprietary
grid data.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from cmpo.config import DatasetConfig
from cmpo.scenarios import Scenario, build_default_scenarios


@dataclass(frozen=True)
class Generator:
    """Dispatchable thermal generator with cubic cost coefficients."""

    name: str
    p_min_kw: float
    p_max_kw: float
    cost_a: float
    cost_b: float
    cost_c: float


@dataclass(frozen=True)
class Battery:
    """Battery energy storage parameters."""

    name: str
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    initial_soc_kwh: float
    round_trip_efficiency: float


@dataclass(frozen=True)
class PCC:
    """Point of common coupling import/export limits."""

    name: str
    import_limit_kw: float
    export_limit_kw: float


@dataclass(frozen=True)
class TieLine:
    """Patch-level tie-line connecting adjacent microgrids."""

    name: str
    source_microgrid: str
    target_microgrid: str
    capacity_kw: float


@dataclass(frozen=True)
class LoadProfile:
    """Base, critical, and flexible load description for one microgrid."""

    base_kw: list[float]
    critical_fraction: float
    flexible_fraction: float


@dataclass(frozen=True)
class UpgradeOptions:
    """Optional design upgrades with simple documented capital-cost estimates."""

    added_pv_kw: float
    added_pv_cost: float
    added_bess_kwh: float
    added_bess_cost: float
    added_generator_kw: float
    added_generator_cost: float


@dataclass(frozen=True)
class Microgrid:
    """Synthetic microgrid asset bundle for optimization experiments."""

    name: str
    load_profile: LoadProfile
    pv_availability_kw: list[float]
    generator: Generator
    battery: Battery
    pcc: PCC
    upgrade_options: UpgradeOptions


@dataclass(frozen=True)
class GridCase:
    """Complete synthetic microgrid patch case."""

    seed: int
    horizon_hours: int
    microgrids: list[Microgrid]
    tie_lines: list[TieLine]
    scenarios: list[Scenario]
    documentation: str

    def to_dict(self) -> dict[str, Any]:
        """Return a nested dictionary suitable for YAML serialization."""

        return asdict(self)


def _round_series(values: np.ndarray) -> list[float]:
    return [round(float(value), 3) for value in values]


def _build_microgrid(index: int, horizon_hours: int, rng: np.random.Generator) -> Microgrid:
    name = f"MG{index + 1}"
    hours = np.arange(horizon_hours, dtype=float)
    load_shape = 0.92 + 0.17 * np.sin((hours + 0.5) / horizon_hours * math.pi)
    pickup = np.linspace(0.0, 0.08, horizon_hours)
    base_peak_kw = rng.uniform(420.0, 920.0)
    base_kw = _round_series(base_peak_kw * (load_shape + pickup) * rng.uniform(0.97, 1.04, horizon_hours))

    pv_shape = np.maximum(0.0, np.sin((hours + 0.25) / horizon_hours * math.pi))
    pv_peak_kw = base_peak_kw * rng.uniform(0.28, 0.58)
    pv_kw = _round_series(pv_peak_kw * pv_shape * rng.uniform(0.92, 1.04, horizon_hours))

    p_max_kw = round(float(base_peak_kw * rng.uniform(0.55, 0.86)), 3)
    p_min_kw = round(float(p_max_kw * rng.uniform(0.08, 0.18)), 3)
    battery_capacity = round(float(base_peak_kw * rng.uniform(0.65, 1.15)), 3)
    max_battery_power = round(float(base_peak_kw * rng.uniform(0.18, 0.32)), 3)
    pcc_import = round(float(base_peak_kw * rng.uniform(0.72, 1.05)), 3)

    return Microgrid(
        name=name,
        load_profile=LoadProfile(
            base_kw=base_kw,
            critical_fraction=round(float(rng.uniform(0.35, 0.65)), 4),
            flexible_fraction=round(float(rng.uniform(0.10, 0.28)), 4),
        ),
        pv_availability_kw=pv_kw,
        generator=Generator(
            name=f"{name}_thermal",
            p_min_kw=p_min_kw,
            p_max_kw=p_max_kw,
            cost_a=round(float(rng.uniform(0.000001, 0.000006)), 8),
            cost_b=round(float(rng.uniform(0.0015, 0.0060)), 6),
            cost_c=round(float(rng.uniform(0.12, 0.32)), 5),
        ),
        battery=Battery(
            name=f"{name}_bess",
            capacity_kwh=battery_capacity,
            max_charge_kw=max_battery_power,
            max_discharge_kw=round(float(max_battery_power * rng.uniform(0.95, 1.08)), 3),
            initial_soc_kwh=round(float(battery_capacity * rng.uniform(0.45, 0.65)), 3),
            round_trip_efficiency=round(float(rng.uniform(0.88, 0.94)), 4),
        ),
        pcc=PCC(
            name=f"{name}_pcc",
            import_limit_kw=pcc_import,
            export_limit_kw=round(float(pcc_import * rng.uniform(0.35, 0.70)), 3),
        ),
        upgrade_options=UpgradeOptions(
            added_pv_kw=round(float(base_peak_kw * 0.25), 3),
            added_pv_cost=round(float(base_peak_kw * 0.25 * 980.0), 2),
            added_bess_kwh=round(float(base_peak_kw * 0.35), 3),
            added_bess_cost=round(float(base_peak_kw * 0.35 * 430.0), 2),
            added_generator_kw=round(float(base_peak_kw * 0.18), 3),
            added_generator_cost=round(float(base_peak_kw * 0.18 * 720.0), 2),
        ),
    )


def _build_tie_lines(microgrids: list[Microgrid], rng: np.random.Generator) -> list[TieLine]:
    tie_lines: list[TieLine] = []
    for index in range(len(microgrids) - 1):
        average_load = (
            sum(microgrids[index].load_profile.base_kw) / len(microgrids[index].load_profile.base_kw)
            + sum(microgrids[index + 1].load_profile.base_kw) / len(microgrids[index + 1].load_profile.base_kw)
        ) / 2.0
        tie_lines.append(
            TieLine(
                name=f"TIE_{microgrids[index].name}_{microgrids[index + 1].name}",
                source_microgrid=microgrids[index].name,
                target_microgrid=microgrids[index + 1].name,
                capacity_kw=round(float(average_load * rng.uniform(0.18, 0.34)), 3),
            )
        )
    return tie_lines


def _write_case_files(case: GridCase, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "generated_case.yaml").write_text(
        yaml.safe_dump(case.to_dict(), sort_keys=False),
        encoding="utf-8",
    )

    with (output_dir / "microgrids.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "avg_base_load_kw",
                "critical_fraction",
                "flexible_fraction",
                "pv_peak_kw",
                "generator_p_max_kw",
                "battery_capacity_kwh",
                "pcc_import_limit_kw",
            ],
        )
        writer.writeheader()
        for microgrid in case.microgrids:
            writer.writerow(
                {
                    "name": microgrid.name,
                    "avg_base_load_kw": round(sum(microgrid.load_profile.base_kw) / len(microgrid.load_profile.base_kw), 3),
                    "critical_fraction": microgrid.load_profile.critical_fraction,
                    "flexible_fraction": microgrid.load_profile.flexible_fraction,
                    "pv_peak_kw": max(microgrid.pv_availability_kw),
                    "generator_p_max_kw": microgrid.generator.p_max_kw,
                    "battery_capacity_kwh": microgrid.battery.capacity_kwh,
                    "pcc_import_limit_kw": microgrid.pcc.import_limit_kw,
                }
            )

    with (output_dir / "scenarios.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["name", "probability", "severity_label", "critical_load_requirement"],
        )
        writer.writeheader()
        for scenario in case.scenarios:
            writer.writerow(
                {
                    "name": scenario.name,
                    "probability": scenario.probability,
                    "severity_label": scenario.severity_label,
                    "critical_load_requirement": scenario.critical_load_requirement,
                }
            )


def generate_synthetic_dataset(
    config: DatasetConfig | None = None,
    output_dir: Path | str = Path("data"),
) -> GridCase:
    """Generate and persist the default deterministic synthetic grid case.

    Parameters are intentionally small by default: four microgrids, six hours,
    eight scenarios, and seed 42. The output files are reproducible and are
    written to ``generated_case.yaml``, ``scenarios.csv``, and
    ``microgrids.csv`` in ``output_dir``.
    """

    cfg = config or DatasetConfig()
    if cfg.n_microgrids <= 0:
        raise ValueError("n_microgrids must be positive")
    if cfg.horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")

    rng = np.random.default_rng(cfg.seed)
    microgrids = [_build_microgrid(index, cfg.horizon_hours, rng) for index in range(cfg.n_microgrids)]
    case = GridCase(
        seed=cfg.seed,
        horizon_hours=cfg.horizon_hours,
        microgrids=microgrids,
        tie_lines=_build_tie_lines(microgrids, rng),
        scenarios=build_default_scenarios(cfg.n_microgrids, cfg.horizon_hours),
        documentation=(
            "Synthetic Phase 2 CMPO case. Values use plausible ranges for small "
            "microgrid patches and do not represent proprietary grid data."
        ),
    )
    _write_case_files(case, Path(output_dir))
    return case
