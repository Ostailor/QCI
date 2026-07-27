"""Classical baselines and pre-QCi local polynomial search."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from importlib.util import find_spec
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


class BaselineSkipped(RuntimeError):
    """Raised when an optional baseline dependency or solver is unavailable."""

    def __init__(self, method_name: str, reason: str) -> None:
        super().__init__(reason)
        self.method_name = method_name
        self.reason = reason


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


def _generator_cost(microgrid: Microgrid, p_gen: float) -> float:
    return float(
        microgrid.generator.cost_a * p_gen**3
        + microgrid.generator.cost_b * p_gen**2
        + microgrid.generator.cost_c * p_gen
    )


def _set_mode(solution: dict[str, float], scenario: Scenario, grid_case: GridCase, microgrid_id: str, hour: int) -> None:
    mode = _mode_for(scenario, _microgrid_index(grid_case, microgrid_id), hour)
    solution[_var("z_grid", microgrid_id, hour)] = 1.0 if mode == "grid" else 0.0
    solution[_var("z_island", microgrid_id, hour)] = 1.0 if mode == "island" else 0.0
    solution[_var("z_restore", microgrid_id, hour)] = 1.0 if mode == "restore" else 0.0


def _pyomo_solver_name() -> str | None:
    if find_spec("pyomo") is None:
        return None
    try:
        import pyomo.environ as pyo  # noqa: PLC0415
    except Exception:
        return None
    for name in ("gurobi", "appsi_highs", "highs"):
        try:
            if pyo.SolverFactory(name).available(exception_flag=False):
                return name
        except Exception:
            continue
    return None


def _ipopt_solver_name() -> str | None:
    if find_spec("pyomo") is None:
        return None
    try:
        import pyomo.environ as pyo  # noqa: PLC0415
    except Exception:
        return None
    for name in ("ipopt", "cyipopt"):
        try:
            if pyo.SolverFactory(name).available(exception_flag=False):
                return name
        except Exception:
            continue
    return None


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
    residual_pass = report["max_balance_residual"] <= 1e-4
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


class PiecewiseLinearMILPBaseline:
    """Pyomo piecewise-linear dispatch baseline with optional commercial/open solvers."""

    method_name = "Piecewise-linear MILP baseline"

    def __init__(self, breakpoints: int = 5) -> None:
        self.breakpoints = max(2, int(breakpoints))
        self.last_metadata: dict[str, Any] = {}

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        del config
        solver_name = _pyomo_solver_name()
        if solver_name is None:
            raise BaselineSkipped(self.method_name, "Pyomo plus HiGHS/Gurobi is not available.")
        try:
            import pyomo.environ as pyo  # noqa: PLC0415
        except Exception as exc:
            raise BaselineSkipped(self.method_name, f"Pyomo import failed: {exc}") from exc

        start = time.perf_counter()
        microgrids = _microgrid_map(grid_case)
        hours = range(grid_case.horizon_hours)
        pyo_model = pyo.ConcreteModel()
        pyo_model.MH = pyo.Set(initialize=[(microgrid_id, hour) for microgrid_id in patch for hour in hours], dimen=2)
        pyo_model.K = pyo.Set(initialize=list(range(self.breakpoints)))
        pyo_model.pg = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.charge = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.discharge = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.soc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.import_pcc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.export_pcc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.shed_critical = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.shed_noncritical = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.lam = pyo.Var(pyo_model.MH, pyo_model.K, bounds=(0.0, 1.0))
        pyo_model.S = pyo.Set(initialize=list(range(self.breakpoints - 1)))
        pyo_model.segment_active = pyo.Var(pyo_model.MH, pyo_model.S, domain=pyo.Binary)

        def bp(microgrid_id: str, index: int) -> float:
            return microgrids[microgrid_id].generator.p_max_kw * index / max(self.breakpoints - 1, 1)

        constraints = []
        for microgrid_id in patch:
            microgrid = microgrids[microgrid_id]
            mg_index = _microgrid_index(grid_case, microgrid_id)
            eta = microgrid.battery.round_trip_efficiency**0.5
            for hour in hours:
                key = (microgrid_id, hour)
                load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
                critical = load * microgrid.load_profile.critical_fraction
                noncritical = max(0.0, load - critical)
                pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
                tie_available = scenario.tie_availability[mg_index][hour] and not scenario.forced_islanding[mg_index][hour]
                gen_available = scenario.generator_availability[mg_index][hour]
                constraints.extend(
                    [
                        pyo_model.pg[key] == sum(bp(microgrid_id, k) * pyo_model.lam[key, k] for k in pyo_model.K),
                        sum(pyo_model.lam[key, k] for k in pyo_model.K) == 1.0,
                        sum(pyo_model.segment_active[key, s] for s in pyo_model.S) == 1.0,
                        pyo_model.lam[key, 0] <= pyo_model.segment_active[key, 0],
                        pyo_model.lam[key, self.breakpoints - 1] <= pyo_model.segment_active[key, self.breakpoints - 2],
                        pyo_model.pg[key] <= (microgrid.generator.p_max_kw if gen_available else 0.0),
                        pyo_model.charge[key] <= microgrid.battery.max_charge_kw,
                        pyo_model.discharge[key] <= microgrid.battery.max_discharge_kw,
                        pyo_model.soc[key] <= microgrid.battery.capacity_kwh,
                        pyo_model.import_pcc[key] <= (microgrid.pcc.import_limit_kw if tie_available else 0.0),
                        pyo_model.export_pcc[key] <= (microgrid.pcc.export_limit_kw if tie_available else 0.0),
                        pyo_model.shed_critical[key] <= critical,
                        pyo_model.shed_noncritical[key] <= noncritical,
                        pyo_model.pg[key]
                        + pv
                        + pyo_model.discharge[key]
                        + pyo_model.import_pcc[key]
                        + pyo_model.shed_critical[key]
                        + pyo_model.shed_noncritical[key]
                        == load + pyo_model.charge[key] + pyo_model.export_pcc[key],
                    ]
                )
                for k in range(1, self.breakpoints - 1):
                    constraints.append(
                        pyo_model.lam[key, k]
                        <= pyo_model.segment_active[key, k - 1] + pyo_model.segment_active[key, k]
                    )
                previous_soc = microgrid.battery.initial_soc_kwh if hour == 0 else pyo_model.soc[microgrid_id, hour - 1]
                constraints.append(
                    pyo_model.soc[key]
                    == previous_soc + eta * pyo_model.charge[key] - pyo_model.discharge[key] / max(eta, 1e-12)
                )
        pyo_model.constraints = pyo.ConstraintList()
        for constraint in constraints:
            pyo_model.constraints.add(constraint)

        pyo_model.objective = pyo.Objective(
            expr=sum(
                sum(_generator_cost(microgrids[microgrid_id], bp(microgrid_id, k)) * pyo_model.lam[microgrid_id, hour, k] for k in pyo_model.K)
                + 0.015 * (pyo_model.charge[microgrid_id, hour] + pyo_model.discharge[microgrid_id, hour])
                + 0.18 * pyo_model.import_pcc[microgrid_id, hour]
                - 0.06 * pyo_model.export_pcc[microgrid_id, hour]
                + 10_000.0 * pyo_model.shed_critical[microgrid_id, hour]
                + 700.0 * pyo_model.shed_noncritical[microgrid_id, hour]
                for microgrid_id in patch
                for hour in hours
            ),
            sense=pyo.minimize,
        )
        result = pyo.SolverFactory(solver_name).solve(pyo_model, tee=False)
        status = str(result.solver.termination_condition)
        if status.lower() not in {"optimal", "locallyoptimal", "feasible"}:
            raise BaselineSkipped(self.method_name, f"{solver_name} did not return a usable solution: {status}")

        solution = _empty_solution(model)
        for microgrid_id in patch:
            for hour in hours:
                key = (microgrid_id, hour)
                _set_mode(solution, scenario, grid_case, microgrid_id, hour)
                solution[_var("P_gen", microgrid_id, hour)] = float(pyo.value(pyo_model.pg[key]))
                solution[_var("charge", microgrid_id, hour)] = float(pyo.value(pyo_model.charge[key]))
                solution[_var("discharge", microgrid_id, hour)] = float(pyo.value(pyo_model.discharge[key]))
                solution[_var("soc", microgrid_id, hour)] = float(pyo.value(pyo_model.soc[key]))
                solution[_var("import_pcc", microgrid_id, hour)] = float(pyo.value(pyo_model.import_pcc[key]))
                solution[_var("export_pcc", microgrid_id, hour)] = float(pyo.value(pyo_model.export_pcc[key]))
                solution[_var("shed_critical", microgrid_id, hour)] = float(pyo.value(pyo_model.shed_critical[key]))
                solution[_var("shed_noncritical", microgrid_id, hour)] = float(pyo.value(pyo_model.shed_noncritical[key]))

        runtime = time.perf_counter() - start
        self.last_metadata = {
            "solver": solver_name,
            "breakpoints": self.breakpoints,
            "piecewise_segments": self.breakpoints - 1,
            "piecewise_binary_variables": len(tuple(patch)) * grid_case.horizon_hours * (self.breakpoints - 1),
            "skip_reason": "",
        }
        return _make_result(
            self.method_name,
            scenario,
            patch,
            model,
            grid_case,
            solution,
            runtime,
            1,
            f"Pyomo piecewise-linear generator cost solved with {solver_name}; breakpoints={self.breakpoints}.",
        )


class PyomoIPOPTNonlinearBaseline:
    """Pyomo IPOPT nonlinear dispatch baseline with SLSQP fallback."""

    method_name = "IPOPT/Pyomo nonlinear baseline"

    def __init__(self, maxiter: int | None = None) -> None:
        self.maxiter = maxiter
        self.last_metadata: dict[str, Any] = {}

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        solver_name = _ipopt_solver_name()
        if solver_name is None:
            fallback = SLSQPDispatchOptimizer(maxiter=self.maxiter)
            result = fallback.run(grid_case, scenario, patch, model, config)
            self.last_metadata = {"solver": "scipy_slsqp_fallback", "skip_reason": "IPOPT/cyipopt not available."}
            return Result(
                method_name=self.method_name,
                scenario=result.scenario,
                patch=result.patch,
                raw_energy=result.raw_energy,
                repaired_energy=result.repaired_energy,
                expected_cost_component=result.expected_cost_component,
                critical_load_served_fraction=result.critical_load_served_fraction,
                noncritical_load_served_fraction=result.noncritical_load_served_fraction,
                energy_not_served_kwh=result.energy_not_served_kwh,
                critical_energy_not_served_kwh=result.critical_energy_not_served_kwh,
                feasibility_pass=result.feasibility_pass,
                runtime_seconds=result.runtime_seconds,
                repeats=result.repeats,
                notes="IPOPT/cyipopt unavailable; used SciPy SLSQP fallback with same repair and metrics.",
            )
        try:
            import pyomo.environ as pyo  # noqa: PLC0415
        except Exception as exc:
            raise BaselineSkipped(self.method_name, f"Pyomo import failed: {exc}") from exc

        start = time.perf_counter()
        microgrids = _microgrid_map(grid_case)
        hours = range(grid_case.horizon_hours)
        pyo_model = pyo.ConcreteModel()
        pyo_model.MH = pyo.Set(initialize=[(microgrid_id, hour) for microgrid_id in patch for hour in hours], dimen=2)
        pyo_model.pg = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.charge = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.discharge = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.soc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.import_pcc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.export_pcc = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.shed_critical = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)
        pyo_model.shed_noncritical = pyo.Var(pyo_model.MH, domain=pyo.NonNegativeReals)

        warm = build_greedy_solution(grid_case, scenario, patch, model)
        for microgrid_id in patch:
            for hour in hours:
                key = (microgrid_id, hour)
                pyo_model.pg[key].set_value(warm.get(_var("P_gen", microgrid_id, hour), 0.0))
                pyo_model.charge[key].set_value(warm.get(_var("charge", microgrid_id, hour), 0.0))
                pyo_model.discharge[key].set_value(warm.get(_var("discharge", microgrid_id, hour), 0.0))
                pyo_model.soc[key].set_value(warm.get(_var("soc", microgrid_id, hour), 0.0))
                pyo_model.import_pcc[key].set_value(warm.get(_var("import_pcc", microgrid_id, hour), 0.0))
                pyo_model.export_pcc[key].set_value(warm.get(_var("export_pcc", microgrid_id, hour), 0.0))
                pyo_model.shed_critical[key].set_value(warm.get(_var("shed_critical", microgrid_id, hour), 0.0))
                pyo_model.shed_noncritical[key].set_value(warm.get(_var("shed_noncritical", microgrid_id, hour), 0.0))

        pyo_model.constraints = pyo.ConstraintList()
        for microgrid_id in patch:
            microgrid = microgrids[microgrid_id]
            mg_index = _microgrid_index(grid_case, microgrid_id)
            eta = microgrid.battery.round_trip_efficiency**0.5
            for hour in hours:
                key = (microgrid_id, hour)
                load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
                critical = load * microgrid.load_profile.critical_fraction
                noncritical = max(0.0, load - critical)
                pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
                tie_available = scenario.tie_availability[mg_index][hour] and not scenario.forced_islanding[mg_index][hour]
                gen_available = scenario.generator_availability[mg_index][hour]
                previous_soc = microgrid.battery.initial_soc_kwh if hour == 0 else pyo_model.soc[microgrid_id, hour - 1]
                pyo_model.constraints.add(pyo_model.pg[key] <= (microgrid.generator.p_max_kw if gen_available else 0.0))
                pyo_model.constraints.add(pyo_model.charge[key] <= microgrid.battery.max_charge_kw)
                pyo_model.constraints.add(pyo_model.discharge[key] <= microgrid.battery.max_discharge_kw)
                pyo_model.constraints.add(pyo_model.soc[key] <= microgrid.battery.capacity_kwh)
                pyo_model.constraints.add(pyo_model.import_pcc[key] <= (microgrid.pcc.import_limit_kw if tie_available else 0.0))
                pyo_model.constraints.add(pyo_model.export_pcc[key] <= (microgrid.pcc.export_limit_kw if tie_available else 0.0))
                pyo_model.constraints.add(pyo_model.shed_critical[key] <= critical)
                pyo_model.constraints.add(pyo_model.shed_noncritical[key] <= noncritical)
                pyo_model.constraints.add(
                    pyo_model.pg[key]
                    + pv
                    + pyo_model.discharge[key]
                    + pyo_model.import_pcc[key]
                    + pyo_model.shed_critical[key]
                    + pyo_model.shed_noncritical[key]
                    == load + pyo_model.charge[key] + pyo_model.export_pcc[key]
                )
                pyo_model.constraints.add(
                    pyo_model.soc[key]
                    == previous_soc + eta * pyo_model.charge[key] - pyo_model.discharge[key] / max(eta, 1e-12)
                )

        pyo_model.objective = pyo.Objective(
            expr=sum(
                microgrids[microgrid_id].generator.cost_a * pyo_model.pg[microgrid_id, hour] ** 3
                + microgrids[microgrid_id].generator.cost_b * pyo_model.pg[microgrid_id, hour] ** 2
                + microgrids[microgrid_id].generator.cost_c * pyo_model.pg[microgrid_id, hour]
                + 0.015 * (pyo_model.charge[microgrid_id, hour] + pyo_model.discharge[microgrid_id, hour])
                + 0.18 * pyo_model.import_pcc[microgrid_id, hour]
                - 0.06 * pyo_model.export_pcc[microgrid_id, hour]
                + 10_000.0 * pyo_model.shed_critical[microgrid_id, hour]
                + 700.0 * pyo_model.shed_noncritical[microgrid_id, hour]
                for microgrid_id in patch
                for hour in hours
            ),
            sense=pyo.minimize,
        )
        result = pyo.SolverFactory(solver_name).solve(pyo_model, tee=False)
        status = str(result.solver.termination_condition)
        if status.lower() not in {"optimal", "locallyoptimal", "feasible"}:
            raise BaselineSkipped(self.method_name, f"{solver_name} did not return a usable solution: {status}")

        solution = _empty_solution(model)
        for microgrid_id in patch:
            for hour in hours:
                key = (microgrid_id, hour)
                _set_mode(solution, scenario, grid_case, microgrid_id, hour)
                solution[_var("P_gen", microgrid_id, hour)] = float(pyo.value(pyo_model.pg[key]))
                solution[_var("charge", microgrid_id, hour)] = float(pyo.value(pyo_model.charge[key]))
                solution[_var("discharge", microgrid_id, hour)] = float(pyo.value(pyo_model.discharge[key]))
                solution[_var("soc", microgrid_id, hour)] = float(pyo.value(pyo_model.soc[key]))
                solution[_var("import_pcc", microgrid_id, hour)] = float(pyo.value(pyo_model.import_pcc[key]))
                solution[_var("export_pcc", microgrid_id, hour)] = float(pyo.value(pyo_model.export_pcc[key]))
                solution[_var("shed_critical", microgrid_id, hour)] = float(pyo.value(pyo_model.shed_critical[key]))
                solution[_var("shed_noncritical", microgrid_id, hour)] = float(pyo.value(pyo_model.shed_noncritical[key]))
        runtime = time.perf_counter() - start
        self.last_metadata = {"solver": solver_name, "skip_reason": ""}
        return _make_result(
            self.method_name,
            scenario,
            patch,
            model,
            grid_case,
            solution,
            runtime,
            1,
            f"Pyomo nonlinear dispatch solved with {solver_name}.",
        )


class QUBOQuadratizedBaseline:
    """Low-resolution QUBO/quadratized proxy with simulated annealing local search."""

    method_name = "QUBO/quadratized local search baseline"

    def __init__(self, levels: int = 4, sweeps: int = 48) -> None:
        self.levels = max(2, int(levels))
        self.sweeps = max(1, int(sweeps))
        self.last_metadata: dict[str, Any] = {}

    def _quantize_solution(self, model: PolynomialModel, solution: dict[str, float]) -> dict[str, float]:
        quantized = {}
        for name, variable in model.variables.items():
            lower, upper = variable.lower_bound, variable.upper_bound
            if upper <= lower:
                quantized[name] = lower
                continue
            grid = np.linspace(lower, upper, self.levels)
            value = float(solution.get(name, lower))
            quantized[name] = float(grid[int(np.argmin(np.abs(grid - value)))])
        return quantized

    @staticmethod
    def _expanded_powers(powers: dict[str, int]) -> list[str]:
        expanded: list[str] = []
        for var_name, exponent in powers.items():
            expanded.extend([var_name] * int(exponent))
        return expanded

    def _quadratized_energy(self, model: PolynomialModel, solution: dict[str, float]) -> float:
        """Evaluate through an explicit cubic-to-quadratic auxiliary representation."""

        energy = 0.0
        for term in model.terms:
            variables = self._expanded_powers(term.powers)
            if len(variables) <= 2:
                value = term.coefficient
                for var_name in variables:
                    value *= solution.get(var_name, 0.0)
                energy += value
                continue
            if len(variables) == 3:
                aux_value = solution.get(variables[0], 0.0) * solution.get(variables[1], 0.0)
                energy += term.coefficient * aux_value * solution.get(variables[2], 0.0)
                continue
            raise ValueError(f"QUBO/quadratized baseline only supports degree <= 3, got {len(variables)}")
        return float(energy)

    def _auxiliary_count(self, model: PolynomialModel) -> int:
        auxiliaries: set[tuple[str, str]] = set()
        for term in model.terms:
            variables = self._expanded_powers(term.powers)
            if len(variables) == 3:
                auxiliaries.add(tuple(sorted((variables[0], variables[1]))))
        return len(auxiliaries)

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
        greedy_continuous = build_greedy_solution(grid_case, scenario, patch, model)
        current = self._quantize_solution(model, greedy_continuous)
        current_energy = self._quadratized_energy(model, current)
        best = dict(current)
        best_energy = current_energy
        variable_names = list(model.variables)
        for sweep in range(self.sweeps):
            temperature = max(1e-6, 1.0 - sweep / max(self.sweeps - 1, 1))
            rng.shuffle(variable_names)
            for name in variable_names:
                variable = model.variables[name]
                if variable.upper_bound <= variable.lower_bound:
                    continue
                grid = np.linspace(variable.lower_bound, variable.upper_bound, self.levels)
                trial = dict(current)
                trial[name] = float(rng.choice(grid))
                energy = self._quadratized_energy(model, trial)
                acceptance = np.exp(min(50.0, (current_energy - energy) / max(abs(current_energy), 1.0) / temperature))
                if energy < current_energy or rng.random() < acceptance:
                    current, current_energy = trial, energy
                    if energy < best_energy:
                        best, best_energy = dict(trial), energy
        runtime = time.perf_counter() - start
        binary_bits = int(np.ceil(np.log2(self.levels)))
        cubic_terms = sum(term.degree == 3 for term in model.terms)
        binary_variable_count = model.variable_count() * binary_bits
        auxiliary_variable_count = self._auxiliary_count(model)
        approximation_error = abs(model.evaluate(greedy_continuous) - model.evaluate(self._quantize_solution(model, greedy_continuous)))
        self.last_metadata = {
            "discrete_levels": self.levels,
            "binary_variable_count": binary_variable_count,
            "auxiliary_variable_count": auxiliary_variable_count,
            "cubic_term_count": int(cubic_terms),
            "quadratized_term_count": int(model.term_count() + cubic_terms),
            "variable_blowup": (binary_variable_count + auxiliary_variable_count) / max(model.variable_count(), 1),
            "approximation_error": float(approximation_error),
        }
        notes = (
            "Low-resolution discretized polynomial search with cubic quadratization accounting; "
            f"binary_variables={binary_variable_count}, auxiliary_variables={auxiliary_variable_count}, "
            f"approximation_error={approximation_error:.6f}."
        )
        return _make_result(self.method_name, scenario, patch, model, grid_case, best, runtime, 1, notes)


class GPUParallelRandomRestartBaseline:
    """Many-restart polynomial search using CUDA when available.

    CPU fallback is only allowed when no CUDA backend is visible. On qBraid GPU
    instances this baseline must use CUDA rather than silently dropping to NumPy.
    """

    method_name = "GPU-parallel random restart baseline"

    def __init__(self, restarts: int = 128, local_steps: int = 2) -> None:
        self.restarts = max(1, int(restarts))
        self.local_steps = max(0, int(local_steps))
        self.last_metadata: dict[str, Any] = {}

    def _backend_samples(self, bounds: list[tuple[float, float]], seed: int) -> tuple[Any, str]:
        lowers = np.array([lower for lower, _upper in bounds], dtype=float)
        uppers = np.array([upper for _lower, upper in bounds], dtype=float)
        spans = uppers - lowers
        cuda_seen = False
        cuda_errors: list[str] = []
        if find_spec("cupy") is not None:
            try:
                import cupy as cp  # noqa: PLC0415

                if int(cp.cuda.runtime.getDeviceCount()) > 0:
                    cuda_seen = True
                    rng = cp.random.default_rng(seed)
                    samples = rng.random((self.restarts, len(bounds)), dtype=cp.float64)
                    samples = samples * cp.asarray(spans, dtype=cp.float64) + cp.asarray(lowers, dtype=cp.float64)
                    device_id = int(cp.cuda.runtime.getDevice())
                    return samples, f"cupy_cuda:device_{device_id}"
            except Exception as exc:
                cuda_errors.append(f"CuPy error: {exc}")
        if find_spec("torch") is not None:
            try:
                import torch  # noqa: PLC0415

                if torch.cuda.is_available():
                    cuda_seen = True
                    device = torch.device("cuda")
                    generator = torch.Generator(device=device)
                    generator.manual_seed(seed)
                    samples = torch.rand((self.restarts, len(bounds)), generator=generator, device=device, dtype=torch.float64)
                    samples = samples * torch.tensor(uppers - lowers, device=device, dtype=torch.float64) + torch.tensor(
                        lowers,
                        device=device,
                        dtype=torch.float64,
                    )
                    device_name = torch.cuda.get_device_name(0)
                    return samples, f"torch_cuda:{device_name}"
            except Exception as exc:
                cuda_errors.append(f"Torch CUDA error: {exc}")
        if find_spec("numba") is not None:
            try:
                from numba import cuda  # noqa: PLC0415
                from numba.cuda.random import create_xoroshiro128p_states, xoroshiro128p_uniform_float64  # noqa: PLC0415

                if cuda.is_available():
                    cuda_seen = True

                    @cuda.jit
                    def fill_samples(states, lower_values, span_values, out, n_cols):  # type: ignore[no-untyped-def]
                        idx = cuda.grid(1)
                        if idx < out.size:
                            col = idx % n_cols
                            out.flat[idx] = lower_values[col] + span_values[col] * xoroshiro128p_uniform_float64(states, idx)

                    out_device = cuda.device_array((self.restarts, len(bounds)), dtype=np.float64)
                    states = create_xoroshiro128p_states(out_device.size, seed=seed)
                    threads = 128
                    blocks = (out_device.size + threads - 1) // threads
                    fill_samples[blocks, threads](
                        states,
                        cuda.to_device(lowers),
                        cuda.to_device(spans),
                        out_device,
                        len(bounds),
                    )
                    return out_device.copy_to_host(), "numba_cuda"
            except Exception as exc:
                cuda_errors.append(f"Numba CUDA error: {exc}")
        if cuda_seen:
            detail = "; ".join(cuda_errors) if cuda_errors else "CUDA backend failed after device discovery."
            raise BaselineSkipped(self.method_name, f"CUDA is available, refusing CPU fallback. {detail}")
        rng = np.random.default_rng(seed)
        samples = rng.random((self.restarts, len(bounds))) * spans + lowers
        return samples, "numpy_cpu_no_cuda"

    @staticmethod
    def _evaluate_sample_batch(model: PolynomialModel, variable_names: list[str], samples: np.ndarray) -> np.ndarray:
        """Evaluate a sampled vector batch with NumPy array operations."""

        index = {name: idx for idx, name in enumerate(variable_names)}
        energies = np.zeros(samples.shape[0], dtype=float)
        for term in model.terms:
            values = np.full(samples.shape[0], term.coefficient, dtype=float)
            for var_name, exponent in term.powers.items():
                values *= samples[:, index[var_name]] ** exponent
            energies += values
        return energies

    @staticmethod
    def _evaluate_sample_batch_cupy(model: PolynomialModel, variable_names: list[str], samples: Any) -> Any:
        """Evaluate a sampled vector batch on CUDA with CuPy array operations."""

        import cupy as cp  # noqa: PLC0415

        index = {name: idx for idx, name in enumerate(variable_names)}
        energies = cp.zeros(samples.shape[0], dtype=cp.float64)
        for term in model.terms:
            values = cp.full(samples.shape[0], term.coefficient, dtype=cp.float64)
            for var_name, exponent in term.powers.items():
                values *= samples[:, index[var_name]] ** exponent
            energies += values
        return energies

    @staticmethod
    def _evaluate_sample_batch_torch(model: PolynomialModel, variable_names: list[str], samples: Any) -> Any:
        """Evaluate a sampled vector batch on CUDA with torch tensor operations."""

        import torch  # noqa: PLC0415

        index = {name: idx for idx, name in enumerate(variable_names)}
        energies = torch.zeros(samples.shape[0], dtype=torch.float64, device=samples.device)
        for term in model.terms:
            values = torch.full((samples.shape[0],), term.coefficient, dtype=torch.float64, device=samples.device)
            for var_name, exponent in term.powers.items():
                values *= samples[:, index[var_name]] ** exponent
            energies += values
        return energies

    def _batch_best(
        self,
        model: PolynomialModel,
        variable_names: list[str],
        samples: Any,
        greedy: np.ndarray,
        backend: str,
    ) -> tuple[np.ndarray, float, float, float, float]:
        if backend.startswith("cupy_cuda"):
            import cupy as cp  # noqa: PLC0415

            samples[0, :] = cp.asarray(greedy, dtype=cp.float64)
            energies = self._evaluate_sample_batch_cupy(model, variable_names, samples)
            best_index = int(cp.asnumpy(cp.argmin(energies)))
            return (
                cp.asnumpy(samples[best_index]),
                float(cp.asnumpy(cp.min(energies))),
                float(cp.asnumpy(cp.median(energies))),
                float(cp.asnumpy(cp.mean(energies))),
                float(cp.asnumpy(cp.std(energies))),
            )
        if backend.startswith("torch_cuda"):
            import torch  # noqa: PLC0415

            samples[0, :] = torch.as_tensor(greedy, dtype=torch.float64, device=samples.device)
            energies = self._evaluate_sample_batch_torch(model, variable_names, samples)
            best_index = int(torch.argmin(energies).detach().cpu().item())
            return (
                samples[best_index].detach().cpu().numpy(),
                float(torch.min(energies).detach().cpu().item()),
                float(torch.median(energies).detach().cpu().item()),
                float(torch.mean(energies).detach().cpu().item()),
                float(torch.std(energies, unbiased=False).detach().cpu().item()),
            )
        samples[0, :] = greedy
        energies = self._evaluate_sample_batch(model, variable_names, samples)
        best_index = int(np.argmin(energies))
        return (
            samples[best_index],
            float(energies.min()),
            float(np.median(energies)),
            float(np.mean(energies)),
            float(np.std(energies)),
        )

    @staticmethod
    def _samples_to_numpy(samples: Any) -> np.ndarray:
        if isinstance(samples, np.ndarray):
            return samples
        if find_spec("cupy") is not None:
            try:
                import cupy as cp  # noqa: PLC0415

                if isinstance(samples, cp.ndarray):
                    return cp.asnumpy(samples)
            except Exception:
                pass
        if hasattr(samples, "detach"):
            return samples.detach().cpu().numpy()
        return np.asarray(samples)

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        start = time.perf_counter()
        bounds = _bounds(model)
        samples, backend = self._backend_samples(bounds, config.dataset.seed)
        greedy = _vector_from_solution(model, build_greedy_solution(grid_case, scenario, patch, model))
        variable_names = list(model.variables)
        if self.local_steps == 0:
            best_sample, best_energy, median_energy, mean_energy, std_energy = self._batch_best(
                model,
                variable_names,
                samples,
                greedy,
                backend,
            )
            runtime = time.perf_counter() - start
            self.last_metadata = {
                "restart_count": self.restarts,
                "gpu_backend": backend,
                "best_energy": best_energy,
                "median_energy": median_energy,
                "mean_energy": mean_energy,
                "std_energy": std_energy,
                "candidate_batch_size": self.restarts,
                "gpu_local_steps": self.local_steps,
            }
            mode = "CUDA" if backend.startswith(("cupy_cuda", "torch_cuda", "numba_cuda")) else "no-CUDA CPU fallback"
            notes = (
                f"{mode} batch random restart baseline using {backend}; restarts={self.restarts}, "
                f"local_steps=0, median_energy={median_energy:.6f}, std_energy={std_energy:.6f}."
            )
            return _make_result(
                self.method_name,
                scenario,
                patch,
                model,
                grid_case,
                _solution_from_vector(model, best_sample),
                runtime,
                self.restarts,
                notes,
            )
        samples = self._samples_to_numpy(samples)
        samples[0, :] = greedy
        rng = np.random.default_rng(config.dataset.seed + 7919)
        search = RandomRestartPolynomialSearch(n_restarts=1, local_steps=self.local_steps)
        improved = [search._local_improve(model, sample, rng) for sample in samples]
        energies = np.array([model.evaluate(_solution_from_vector(model, sample)) for sample in improved], dtype=float)
        best_index = int(np.argmin(energies))
        runtime = time.perf_counter() - start
        self.last_metadata = {
            "restart_count": self.restarts,
            "gpu_backend": backend,
            "best_energy": float(energies.min()),
            "median_energy": float(np.median(energies)),
            "mean_energy": float(np.mean(energies)),
            "std_energy": float(np.std(energies)),
        }
        mode = "CUDA" if backend.startswith(("cupy_cuda", "torch_cuda", "numba_cuda")) else "no-CUDA CPU fallback"
        notes = (
            f"{mode} random restart baseline using {backend}; restarts={self.restarts}, "
            f"median_energy={np.median(energies):.6f}, std_energy={np.std(energies):.6f}."
        )
        return _make_result(
            self.method_name,
            scenario,
            patch,
            model,
            grid_case,
            _solution_from_vector(model, improved[best_index]),
            runtime,
            self.restarts,
            notes,
        )


class StressReserveHeuristicBaseline:
    """Outage-specialized critical-load heuristic that preserves reserve before noncritical load."""

    method_name = "Stress-only reserve heuristic baseline"

    def __init__(self, reserve_fraction: float = 0.35) -> None:
        self.reserve_fraction = float(reserve_fraction)
        self.last_metadata: dict[str, Any] = {}

    def run(
        self,
        grid_case: GridCase,
        scenario: Scenario,
        patch: tuple[str, ...] | list[str],
        model: PolynomialModel,
        config: ExperimentConfig,
    ) -> Result:
        del config
        start = time.perf_counter()
        solution = _empty_solution(model)
        microgrids = _microgrid_map(grid_case)
        for microgrid_id in patch:
            microgrid = microgrids[microgrid_id]
            mg_index = _microgrid_index(grid_case, microgrid_id)
            soc = microgrid.battery.initial_soc_kwh
            reserve_target = microgrid.battery.capacity_kwh * self.reserve_fraction
            for hour in range(grid_case.horizon_hours):
                _set_mode(solution, scenario, grid_case, microgrid_id, hour)
                load = microgrid.load_profile.base_kw[hour] * scenario.load_multiplier_by_hour[hour]
                critical = load * microgrid.load_profile.critical_fraction
                noncritical = max(0.0, load - critical)
                pv = microgrid.pv_availability_kw[hour] * scenario.pv_multiplier_by_hour[hour]
                tie_available = scenario.tie_availability[mg_index][hour] and not scenario.forced_islanding[mg_index][hour]
                outage = scenario.forced_islanding[mg_index][hour] or not scenario.tie_availability[mg_index][hour]
                remaining_critical = max(0.0, critical - min(pv, critical))
                remaining_noncritical = max(0.0, noncritical - max(pv - critical, 0.0))
                gen = 0.0
                if scenario.generator_availability[mg_index][hour]:
                    gen_to_critical = min(microgrid.generator.p_max_kw, remaining_critical)
                    gen += gen_to_critical
                    remaining_critical -= gen_to_critical
                import_pcc = 0.0
                if tie_available and not outage:
                    import_pcc = min(microgrid.pcc.import_limit_kw, remaining_critical)
                    remaining_critical -= import_pcc
                available_discharge = max(0.0, soc - (reserve_target if not outage else 0.0)) * microgrid.battery.round_trip_efficiency**0.5
                discharge = min(microgrid.battery.max_discharge_kw, available_discharge, remaining_critical)
                remaining_critical -= discharge
                soc = max(0.0, soc - discharge / max(microgrid.battery.round_trip_efficiency**0.5, 1e-12))
                if gen < microgrid.generator.p_max_kw and remaining_noncritical > 0.0 and not outage:
                    gen_to_noncritical = min(microgrid.generator.p_max_kw - gen, remaining_noncritical)
                    gen += gen_to_noncritical
                    remaining_noncritical -= gen_to_noncritical
                solution[_var("P_gen", microgrid_id, hour)] = gen
                solution[_var("charge", microgrid_id, hour)] = 0.0
                solution[_var("discharge", microgrid_id, hour)] = discharge
                solution[_var("soc", microgrid_id, hour)] = soc
                solution[_var("import_pcc", microgrid_id, hour)] = import_pcc
                solution[_var("export_pcc", microgrid_id, hour)] = 0.0
                solution[_var("shed_critical", microgrid_id, hour)] = remaining_critical
                solution[_var("shed_noncritical", microgrid_id, hour)] = remaining_noncritical
        runtime = time.perf_counter() - start
        self.last_metadata = {"reserve_fraction": self.reserve_fraction, "stress_label": scenario.severity_label}
        return _make_result(
            self.method_name,
            scenario,
            patch,
            model,
            grid_case,
            solution,
            runtime,
            1,
            f"Reserve-prioritized outage heuristic; reserve_fraction={self.reserve_fraction:.2f}.",
        )


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
