"""Classical baselines and pre-QCi local polynomial search."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.optimize import differential_evolution, minimize

from cmpo.config import ExperimentConfig
from cmpo.data import GridCase, Microgrid
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.polynomial import PolynomialModel
from cmpo.repair import repair_solution
from cmpo.scenarios import Scenario


@dataclass(frozen=True)
class Result:
    """Computed baseline result for one scenario/patch/model."""

    method_name: str
    scenario: str
    patch: str
    raw_energy: float
    repaired_energy: float
    expected_cost_component: float
    critical_load_served_fraction: float
    noncritical_load_served_fraction: float
    energy_not_served_kwh: float
    critical_energy_not_served_kwh: float
    feasibility_pass: bool
    runtime_seconds: float
    repeats: int
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly result dictionary."""

        return asdict(self)


def _var(prefix: str, microgrid_id: str, hour: int) -> str:
    return f"{prefix}[{microgrid_id},{hour}]"


def _microgrid_map(grid_case: GridCase) -> dict[str, Microgrid]:
    return {microgrid.name: microgrid for microgrid in grid_case.microgrids}


def _microgrid_index(grid_case: GridCase, microgrid_id: str) -> int:
    for index, microgrid in enumerate(grid_case.microgrids):
        if microgrid.name == microgrid_id:
            return index
    raise KeyError(microgrid_id)


def _bounds(model: PolynomialModel) -> list[tuple[float, float]]:
    return [(variable.lower_bound, variable.upper_bound) for variable in model.variables.values()]


def _solution_from_vector(model: PolynomialModel, vector: np.ndarray) -> dict[str, float]:
    return {name: float(value) for name, value in zip(model.variables, vector, strict=True)}


def _vector_from_solution(model: PolynomialModel, solution: dict[str, float]) -> np.ndarray:
    return np.array([float(solution.get(name, 0.0)) for name in model.variables], dtype=float)


def _mode_for(scenario: Scenario, microgrid_index: int, hour: int) -> str:
    if scenario.forced_islanding[microgrid_index][hour] or not scenario.tie_availability[microgrid_index][hour]:
        return "island"
    if scenario.name == "restoration":
        return "restore"
    return "grid"


def _empty_solution(model: PolynomialModel) -> dict[str, float]:
    return {name: 0.0 for name in model.variables}


def build_greedy_solution(
    grid_case: GridCase,
    scenario: Scenario,
    patch: tuple[str, ...] | list[str],
    model: PolynomialModel,
) -> dict[str, float]:
    """Construct a deterministic critical-load-first dispatch warm start."""

    solution = _empty_solution(model)
    microgrids = _microgrid_map(grid_case)
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        mg_index = _microgrid_index(grid_case, microgrid_id)
        soc = microgrid.battery.initial_soc_kwh
        for hour in range(grid_case.horizon_hours):
            base_load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            critical_load = base_load * microgrid.load_profile.critical_fraction
            noncritical_load = max(0.0, base_load - critical_load)
            pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
            tie_available = scenario.tie_availability[mg_index][hour] and not scenario.forced_islanding[mg_index][hour]
            generator_available = scenario.generator_availability[mg_index][hour]
            mode = _mode_for(scenario, mg_index, hour)

            solution[_var("z_grid", microgrid_id, hour)] = 1.0 if mode == "grid" else 0.0
            solution[_var("z_island", microgrid_id, hour)] = 1.0 if mode == "island" else 0.0
            solution[_var("z_restore", microgrid_id, hour)] = 1.0 if mode == "restore" else 0.0

            remaining_critical = critical_load
            remaining_noncritical = noncritical_load
            pv_to_critical = min(pv, remaining_critical)
            remaining_critical -= pv_to_critical
            pv_left = pv - pv_to_critical
            pv_to_noncritical = min(pv_left, remaining_noncritical)
            remaining_noncritical -= pv_to_noncritical

            gen_used = 0.0
            if generator_available:
                gen_capacity = microgrid.generator.p_max_kw
                gen_to_critical = min(gen_capacity, remaining_critical)
                gen_used += gen_to_critical
                remaining_critical -= gen_to_critical
                gen_to_noncritical = min(gen_capacity - gen_used, remaining_noncritical)
                gen_used += gen_to_noncritical
                remaining_noncritical -= gen_to_noncritical
                gen_used = max(gen_used, microgrid.generator.p_min_kw)

            discharge = 0.0
            available_discharge = min(microgrid.battery.max_discharge_kw, soc * microgrid.battery.round_trip_efficiency**0.5)
            discharge_to_critical = min(available_discharge, remaining_critical)
            discharge += discharge_to_critical
            remaining_critical -= discharge_to_critical
            discharge_to_noncritical = min(available_discharge - discharge, remaining_noncritical)
            discharge += discharge_to_noncritical
            remaining_noncritical -= discharge_to_noncritical
            soc = max(0.0, soc - discharge / max(microgrid.battery.round_trip_efficiency**0.5, 1e-12))

            import_pcc = 0.0
            if tie_available:
                import_to_critical = min(microgrid.pcc.import_limit_kw, remaining_critical)
                import_pcc += import_to_critical
                remaining_critical -= import_to_critical
                import_to_noncritical = min(microgrid.pcc.import_limit_kw - import_pcc, remaining_noncritical)
                import_pcc += import_to_noncritical
                remaining_noncritical -= import_to_noncritical

            solution[_var("P_gen", microgrid_id, hour)] = gen_used
            solution[_var("charge", microgrid_id, hour)] = 0.0
            solution[_var("discharge", microgrid_id, hour)] = discharge
            solution[_var("soc", microgrid_id, hour)] = soc
            solution[_var("import_pcc", microgrid_id, hour)] = import_pcc
            solution[_var("export_pcc", microgrid_id, hour)] = 0.0
            solution[_var("shed_critical", microgrid_id, hour)] = max(0.0, remaining_critical)
            solution[_var("shed_noncritical", microgrid_id, hour)] = max(0.0, remaining_noncritical)
    return solution


def _dispatch_metrics(
    solution: dict[str, float],
    grid_case: GridCase,
    scenario: Scenario,
    patch: tuple[str, ...] | list[str],
) -> dict[str, float]:
    microgrids = _microgrid_map(grid_case)
    critical_total = 0.0
    noncritical_total = 0.0
    critical_shed = 0.0
    noncritical_shed = 0.0
    operating_cost = 0.0
    for microgrid_id in patch:
        microgrid = microgrids[microgrid_id]
        for hour in range(grid_case.horizon_hours):
            base_load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
            critical = base_load * microgrid.load_profile.critical_fraction
            noncritical = max(0.0, base_load - critical)
            p_gen = float(solution.get(_var("P_gen", microgrid_id, hour), 0.0))
            charge = float(solution.get(_var("charge", microgrid_id, hour), 0.0))
            discharge = float(solution.get(_var("discharge", microgrid_id, hour), 0.0))
            import_pcc = float(solution.get(_var("import_pcc", microgrid_id, hour), 0.0))
            export_pcc = float(solution.get(_var("export_pcc", microgrid_id, hour), 0.0))
            shed_critical = min(max(float(solution.get(_var("shed_critical", microgrid_id, hour), 0.0)), 0.0), critical)
            shed_noncritical = min(max(float(solution.get(_var("shed_noncritical", microgrid_id, hour), 0.0)), 0.0), noncritical)
            critical_total += critical
            noncritical_total += noncritical
            critical_shed += shed_critical
            noncritical_shed += shed_noncritical
            operating_cost += (
                microgrid.generator.cost_a * p_gen**3
                + microgrid.generator.cost_b * p_gen**2
                + microgrid.generator.cost_c * p_gen
                + 0.015 * (charge + discharge)
                + 0.18 * import_pcc
                - 0.06 * export_pcc
            )
    return {
        "expected_cost_component": float(operating_cost),
        "critical_load_served_fraction": float(1.0 - critical_shed / max(critical_total, 1e-12)),
        "noncritical_load_served_fraction": float(1.0 - noncritical_shed / max(noncritical_total, 1e-12)),
        "energy_not_served_kwh": float(critical_shed + noncritical_shed),
        "critical_energy_not_served_kwh": float(critical_shed),
    }


def _make_result(
    method_name: str,
    scenario: Scenario,
    patch: tuple[str, ...] | list[str],
    model: PolynomialModel,
    grid_case: GridCase,
    raw_solution: dict[str, float],
    runtime_seconds: float,
    repeats: int,
    notes: str,
) -> Result:
    repaired_solution, report = repair_solution(raw_solution, model, grid_case, patch, scenario)
    metrics = _dispatch_metrics(repaired_solution, grid_case, scenario, patch)
    residual_pass = report["max_balance_residual"] <= 1e-4 + metrics["energy_not_served_kwh"]
    return Result(
        method_name=method_name,
        scenario=scenario.name,
        patch="-".join(patch),
        raw_energy=float(model.evaluate(raw_solution)),
        repaired_energy=float(model.evaluate(repaired_solution)),
        expected_cost_component=metrics["expected_cost_component"],
        critical_load_served_fraction=metrics["critical_load_served_fraction"],
        noncritical_load_served_fraction=metrics["noncritical_load_served_fraction"],
        energy_not_served_kwh=metrics["energy_not_served_kwh"],
        critical_energy_not_served_kwh=metrics["critical_energy_not_served_kwh"],
        feasibility_pass=bool(report["feasibility_pass"] and residual_pass),
        runtime_seconds=float(max(runtime_seconds, 0.0)),
        repeats=int(repeats),
        notes=notes,
    )


class GreedyCriticalLoadFirst:
    """Critical-load-first deterministic dispatch heuristic."""

    method_name = "GreedyCriticalLoadFirst"

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        del config
        raw_solution = build_greedy_solution(grid_case, scenario, patch, model)
        return _make_result(
            self.method_name,
            scenario,
            patch,
            model,
            grid_case,
            raw_solution,
            runtime_seconds=0.0,
            repeats=1,
            notes="Deterministic critical-load-first heuristic.",
        )


class SLSQPDispatchOptimizer:
    """SciPy SLSQP local optimizer over the polynomial model."""

    method_name = "SLSQPDispatchOptimizer"

    def __init__(self, maxiter: int | None = None) -> None:
        self.maxiter = maxiter

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        start = time.perf_counter()
        warm = build_greedy_solution(grid_case, scenario, patch, model)
        x0 = _vector_from_solution(model, warm)
        notes = "SLSQP completed."
        try:
            result = minimize(
                lambda vector: model.evaluate(_solution_from_vector(model, np.asarray(vector, dtype=float))),
                x0,
                method="SLSQP",
                bounds=_bounds(model),
                options={"maxiter": int(self.maxiter or config.solver.max_iterations), "ftol": 1e-6, "disp": False},
            )
            raw_solution = _solution_from_vector(model, np.asarray(result.x if result.x is not None else x0, dtype=float))
            if not result.success:
                notes = f"SLSQP reported failure gracefully: {result.message}"
        except Exception as exc:  # pragma: no cover - defensive graceful failure path
            raw_solution = warm
            notes = f"SLSQP failed gracefully and returned greedy warm start: {exc}"
        runtime = time.perf_counter() - start
        return _make_result(self.method_name, scenario, patch, model, grid_case, raw_solution, runtime, 1, notes)


class DifferentialEvolutionOptimizer:
    """SciPy differential-evolution global heuristic."""

    method_name = "DifferentialEvolutionOptimizer"

    def __init__(self, maxiter: int = 4, popsize: int = 4) -> None:
        self.maxiter = maxiter
        self.popsize = popsize

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        start = time.perf_counter()
        rng_seed = config.dataset.seed
        result = differential_evolution(
            lambda vector: model.evaluate(_solution_from_vector(model, np.asarray(vector, dtype=float))),
            bounds=_bounds(model),
            seed=rng_seed,
            maxiter=max(1, self.maxiter),
            popsize=max(1, self.popsize),
            polish=False,
            workers=1,
            tol=0.05,
        )
        raw_solution = _solution_from_vector(model, np.asarray(result.x, dtype=float))
        runtime = time.perf_counter() - start
        notes = "Differential evolution global heuristic; no QCi hardware used."
        if not result.success:
            notes = f"Differential evolution ended without convergence: {result.message}"
        return _make_result(self.method_name, scenario, patch, model, grid_case, raw_solution, runtime, 1, notes)


class RandomRestartPolynomialSearch:
    """Pre-QCi CMPO-local polynomial search simulation proxy."""

    method_name = "CMPO-local polynomial search"

    def __init__(self, n_restarts: int | None = None, local_steps: int = 8) -> None:
        self.n_restarts = n_restarts
        self.local_steps = local_steps

    def _local_improve(self, model: PolynomialModel, vector: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        bounds = _bounds(model)
        current = vector.copy()
        current_energy = model.evaluate(_solution_from_vector(model, current))
        for _ in range(self.local_steps):
            for index, (lower, upper) in enumerate(bounds):
                if upper <= lower:
                    continue
                span = upper - lower
                candidates = [
                    current[index],
                    min(upper, max(lower, current[index] + rng.normal(0.0, 0.12 * span))),
                    min(upper, max(lower, current[index] - rng.normal(0.0, 0.12 * span))),
                ]
                for candidate in candidates:
                    trial = current.copy()
                    trial[index] = candidate
                    energy = model.evaluate(_solution_from_vector(model, trial))
                    if energy < current_energy:
                        current = trial
                        current_energy = energy
        return current

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        start = time.perf_counter()
        rng = np.random.default_rng(config.dataset.seed)
        repeats = int(self.n_restarts or config.solver.random_restarts)
        bounds = _bounds(model)
        warm = _vector_from_solution(model, build_greedy_solution(grid_case, scenario, patch, model))
        candidates = [warm]
        for _ in range(max(0, repeats - 1)):
            candidates.append(np.array([rng.uniform(lower, upper) for lower, upper in bounds], dtype=float))
        improved = [self._local_improve(model, candidate, rng) for candidate in candidates]
        energies = [model.evaluate(_solution_from_vector(model, candidate)) for candidate in improved]
        best_index = int(np.argmin(energies))
        median_energy = float(np.median(energies))
        raw_solution = _solution_from_vector(model, improved[best_index])
        runtime = time.perf_counter() - start
        notes = f"Pre-QCi polynomial search proxy; best energy from {len(improved)} repeats, median_energy={median_energy:.6f}."
        return _make_result(self.method_name, scenario, patch, model, grid_case, raw_solution, runtime, len(improved), notes)


def run_baselines(config: ExperimentConfig, dataset: GridCase, scenarios: list[str]) -> list[dict[str, Any]]:
    """Run all baseline methods for the first requested scenario and a small patch."""

    scenario_name = scenarios[0] if scenarios else dataset.scenarios[0].name
    scenario = next((candidate for candidate in dataset.scenarios if candidate.name == scenario_name), dataset.scenarios[0])
    patch = tuple(microgrid.name for microgrid in dataset.microgrids[:1])
    model, _metadata = build_scenario_hamiltonian(dataset, scenario, patch, output_dir=config.output.results_dir, write_export=False)
    optimizers = [
        GreedyCriticalLoadFirst(),
        SLSQPDispatchOptimizer(maxiter=min(config.solver.max_iterations, 25)),
        DifferentialEvolutionOptimizer(maxiter=2, popsize=2),
        RandomRestartPolynomialSearch(n_restarts=min(config.solver.random_restarts, 5), local_steps=3),
    ]
    return [optimizer.run(dataset, scenario, patch, model, config).to_dict() for optimizer in optimizers]
