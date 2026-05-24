"""Hamiltonian builders for per-scenario CMPO patch instances."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cmpo.config import ExperimentConfig
from cmpo.data import GridCase, Microgrid
from cmpo.polynomial import PolynomialModel
from cmpo.qci_export import export_polynomial_model_payload
from cmpo.scenarios import Scenario


@dataclass(frozen=True)
class PenaltyWeights:
    """Transparent penalty weights for Phase 2 Hamiltonian construction."""

    critical_shed: float = 10_000.0
    noncritical_shed: float = 700.0
    battery_degradation: float = 0.015
    import_cost: float = 0.18
    export_credit: float = 0.06
    rho_balance: float = 4.0
    rho_soc: float = 1.5
    rho_mode: float = 25.0
    kappa_mode: float = 1.2
    pcc_failure: float = 2_500.0
    generator_unavailable: float = 2_500.0


def _microgrid_map(grid_case: GridCase) -> dict[str, Microgrid]:
    return {microgrid.name: microgrid for microgrid in grid_case.microgrids}


def _var(prefix: str, microgrid_id: str, hour: int) -> str:
    return f"{prefix}[{microgrid_id},{hour}]"


def _add_squared_affine(
    model: PolynomialModel,
    coefficient: float,
    linear: dict[str, float],
    constant: float = 0.0,
) -> None:
    """Add ``coefficient * (sum(a_i x_i) + constant)^2`` to the model."""

    if constant:
        model.add_term(coefficient * constant * constant, {})
    items = list(linear.items())
    for var_name, scale in items:
        if constant:
            model.add_linear(2.0 * coefficient * constant * scale, var_name)
        model.add_quadratic(coefficient * scale * scale, var_name, var_name)
    for left_index, (left_var, left_scale) in enumerate(items):
        for right_var, right_scale in items[left_index + 1 :]:
            model.add_quadratic(2.0 * coefficient * left_scale * right_scale, left_var, right_var)


def _add_variables_for_microgrid_hour(model: PolynomialModel, microgrid: Microgrid, hour: int) -> dict[str, str]:
    names = {
        "p_gen": _var("P_gen", microgrid.name, hour),
        "charge": _var("charge", microgrid.name, hour),
        "discharge": _var("discharge", microgrid.name, hour),
        "soc": _var("soc", microgrid.name, hour),
        "import_pcc": _var("import_pcc", microgrid.name, hour),
        "export_pcc": _var("export_pcc", microgrid.name, hour),
        "shed_noncritical": _var("shed_noncritical", microgrid.name, hour),
        "shed_critical": _var("shed_critical", microgrid.name, hour),
        "z_grid": _var("z_grid", microgrid.name, hour),
        "z_island": _var("z_island", microgrid.name, hour),
        "z_restore": _var("z_restore", microgrid.name, hour),
    }
    base_load = microgrid.load_profile.base_kw[hour]
    critical_load = base_load * microgrid.load_profile.critical_fraction
    noncritical_load = max(0.0, base_load - critical_load)

    model.add_variable(names["p_gen"], microgrid.generator.p_min_kw, microgrid.generator.p_max_kw)
    model.add_variable(names["charge"], 0.0, microgrid.battery.max_charge_kw)
    model.add_variable(names["discharge"], 0.0, microgrid.battery.max_discharge_kw)
    model.add_variable(names["soc"], 0.0, microgrid.battery.capacity_kwh)
    model.add_variable(names["import_pcc"], 0.0, microgrid.pcc.import_limit_kw)
    model.add_variable(names["export_pcc"], 0.0, microgrid.pcc.export_limit_kw)
    model.add_variable(names["shed_noncritical"], 0.0, noncritical_load)
    model.add_variable(names["shed_critical"], 0.0, critical_load)
    model.add_variable(names["z_grid"], 0.0, 1.0)
    model.add_variable(names["z_island"], 0.0, 1.0)
    model.add_variable(names["z_restore"], 0.0, 1.0)
    return names


def _add_objective_terms(
    model: PolynomialModel,
    microgrid: Microgrid,
    scenario: Scenario,
    microgrid_index: int,
    hour: int,
    names: dict[str, str],
    weights: PenaltyWeights,
) -> None:
    generator = microgrid.generator
    model.add_cubic(generator.cost_a, names["p_gen"], names["p_gen"], names["p_gen"])
    model.add_quadratic(generator.cost_b, names["p_gen"], names["p_gen"])
    model.add_linear(generator.cost_c, names["p_gen"])

    model.add_linear(weights.critical_shed, names["shed_critical"])
    model.add_linear(weights.noncritical_shed, names["shed_noncritical"])
    model.add_linear(weights.battery_degradation, names["charge"])
    model.add_linear(weights.battery_degradation, names["discharge"])
    model.add_linear(weights.import_cost, names["import_pcc"])
    model.add_linear(-weights.export_credit, names["export_pcc"])

    load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
    pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
    _add_squared_affine(
        model,
        weights.rho_balance,
        {
            names["p_gen"]: 1.0,
            names["discharge"]: 1.0,
            names["import_pcc"]: 1.0,
            names["shed_noncritical"]: 1.0,
            names["shed_critical"]: 1.0,
            names["charge"]: -1.0,
            names["export_pcc"]: -1.0,
        },
        constant=pv - load,
    )

    previous_soc_name = _var("soc", microgrid.name, hour - 1)
    eta_c = microgrid.battery.round_trip_efficiency**0.5
    eta_d = microgrid.battery.round_trip_efficiency**0.5
    soc_linear = {
        names["soc"]: 1.0,
        names["charge"]: -eta_c,
        names["discharge"]: 1.0 / eta_d,
    }
    soc_constant = 0.0
    if hour == 0:
        soc_constant = -microgrid.battery.initial_soc_kwh
    else:
        soc_linear[previous_soc_name] = -1.0
    _add_squared_affine(model, weights.rho_soc, soc_linear, constant=soc_constant)

    _add_squared_affine(
        model,
        weights.rho_mode,
        {names["z_grid"]: 1.0, names["z_island"]: 1.0, names["z_restore"]: 1.0},
        constant=-1.0,
    )
    for mode_name in ("z_grid", "z_island", "z_restore"):
        model.add_cubic(-weights.kappa_mode, names[mode_name], names[mode_name], names[mode_name])

    unavailable_tie = not scenario.tie_availability[microgrid_index][hour]
    forced_islanding = scenario.forced_islanding[microgrid_index][hour]
    if unavailable_tie or forced_islanding:
        model.add_quadratic(weights.pcc_failure, names["import_pcc"], names["import_pcc"])
        model.add_quadratic(weights.pcc_failure, names["export_pcc"], names["export_pcc"])
    if not scenario.generator_availability[microgrid_index][hour]:
        model.add_quadratic(weights.generator_unavailable, names["p_gen"], names["p_gen"])


def build_scenario_hamiltonian(
    grid_case: GridCase,
    scenario: Scenario,
    patch_ids: tuple[str, ...] | list[str],
    output_dir: Path | str = Path("results"),
    penalty_weights: PenaltyWeights | None = None,
    write_export: bool = True,
) -> tuple[PolynomialModel, dict[str, Any]]:
    """Build and optionally export one scenario/patch Hamiltonian."""

    weights = penalty_weights or PenaltyWeights()
    microgrids = _microgrid_map(grid_case)
    patch = tuple(patch_ids)
    missing = [microgrid_id for microgrid_id in patch if microgrid_id not in microgrids]
    if missing:
        raise ValueError(f"patch contains unknown microgrid IDs: {missing}")

    patch_label = "-".join(patch)
    model = PolynomialModel(name=f"{scenario.name}_{patch_label}")
    for microgrid_index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name not in patch:
            continue
        for hour in range(grid_case.horizon_hours):
            names = _add_variables_for_microgrid_hour(model, microgrid, hour)
            _add_objective_terms(model, microgrid, scenario, microgrid_index, hour, names, weights)

    model.validate_degree(3)
    metadata = {
        "scenario": scenario.name,
        "patch_ids": list(patch),
        "patch": patch_label,
        "horizon": grid_case.horizon_hours,
        "variable_count": model.variable_count(),
        "term_count": model.term_count(),
        "degree": model.degree(),
        "penalty_weights": asdict(weights),
    }
    if write_export:
        save_qci_payload(model, metadata, output_dir)
        save_model_stats([metadata], output_dir)
    return model, metadata


def save_qci_payload(model: PolynomialModel, metadata: dict[str, Any], output_dir: Path | str = Path("results")) -> Path:
    """Write a QCi-ready JSON payload for one scenario/patch model."""

    return export_polynomial_model_payload(model, metadata, output_dir)


def save_model_stats(metadata_records: list[dict[str, Any]], output_dir: Path | str = Path("results")) -> Path:
    """Write model statistics for generated Hamiltonian instances."""

    output_path = Path(output_dir) / "model_stats.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["scenario", "patch", "horizon", "variable_count", "term_count", "degree"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in metadata_records:
            writer.writerow({field: record[field] for field in fieldnames})
    return output_path


def build_hamiltonian(config: ExperimentConfig, dataset: GridCase, scenarios: list[str]) -> dict[str, Any]:
    """Compatibility wrapper that builds the first requested scenario model."""

    scenario_name = scenarios[0] if scenarios else dataset.scenarios[0].name
    scenario = next((candidate for candidate in dataset.scenarios if candidate.name == scenario_name), dataset.scenarios[0])
    patch = tuple(microgrid.name for microgrid in dataset.microgrids[: min(3, len(dataset.microgrids))])
    model, metadata = build_scenario_hamiltonian(
        dataset,
        scenario,
        patch,
        output_dir=config.output.results_dir,
    )
    return {
        "target": "qci_dirac_3",
        "schema": "cmpo.polynomial_model.v1",
        "metadata": metadata,
        "model": model.to_json_dict(),
    }
