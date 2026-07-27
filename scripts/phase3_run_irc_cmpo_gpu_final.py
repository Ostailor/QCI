#!/usr/bin/env python
"""Run create-only GPU publication baselines for six quantized IRC-CMPO payloads."""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.irc_cmpo_validation import solve_binary_hamiltonian_exact  # noqa: E402


DEFAULT_MANIFEST = ROOT / "results/phase3/irc_cmpo/payload_manifest.csv"
DEFAULT_OUTPUT = ROOT / "results/phase3/reproduced/irc_cmpo/gpu_baselines"
DEFAULT_CONFIG = ROOT / "configs/phase3_irc_cmpo_ieee123.yaml"
DEFAULT_PUBLIC_CONFIG = ROOT / "configs/phase3_sc_cmpo_ieee123.yaml"
MINIMUM_CANDIDATES = 10_000
METHODS = (
    "gpu_simulated_annealing",
    "gpu_random_restart",
    "gpu_parallel_local_search",
)
SUMMARY_NAME = "gpu_baseline_summary.json"
METRICS_NAME = "gpu_baseline_metrics.csv"
EXACT_NAME = "exact_milp_references.json"
RecourseEvaluator = Callable[[Mapping[str, Any], Mapping[str, int]], Any]


def _as_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"{field} must be explicitly true or false")


def _resolve_input(path: str | Path, *, relative_to: Path | None = None) -> Path:
    value = Path(path)
    if value.is_absolute() and value.exists():
        return value
    if value.is_absolute():
        try:
            results_index = value.parts.index("results")
        except ValueError:
            pass
        else:
            portable = ROOT.joinpath(*value.parts[results_index:])
            if portable.exists():
                return portable
    if relative_to is not None and (relative_to / value).exists():
        return relative_to / value
    return ROOT / value


def _evaluate_batch(
    terms: Sequence[Mapping[str, Any]], names: Sequence[str], candidates: np.ndarray
) -> np.ndarray:
    indices = {name: index for index, name in enumerate(names)}
    energies = np.zeros(len(candidates), dtype=np.float64)
    for term in terms:
        coefficient = float(term["coefficient"])
        powers = term.get("powers", {})
        if not powers:
            energies += coefficient
            continue
        columns = [indices[str(name)] for name, power in powers.items() if int(power) > 0]
        if unknown := [str(name) for name in powers if str(name) not in indices]:
            raise ValueError(f"Hamiltonian references undeclared variables: {unknown}")
        energies += coefficient * np.prod(candidates[:, columns], axis=1)
    return energies


def _native_feasibility(payload: Mapping[str, Any], candidates: np.ndarray) -> np.ndarray:
    names = [str(variable["name"]) for variable in payload["variables"]]
    indices = {name: index for index, name in enumerate(names)}
    feasible = np.ones(len(candidates), dtype=bool)
    for constraint in payload.get("local_feasibility_constraints", ()):
        asset_names = [f"y::{key}" for key in constraint["asset_keys"]]
        try:
            columns = [indices[name] for name in asset_names]
        except KeyError as exc:
            raise ValueError(f"local-feasibility constraint references undeclared asset {exc.args[0]}") from exc
        pattern = np.asarray(constraint["pattern"], dtype=np.int8)
        if pattern.shape != (len(columns),) or np.any((pattern != 0) & (pattern != 1)):
            raise ValueError("local-feasibility patterns must be native binary vectors")
        feasible &= ~np.all(candidates[:, columns] == pattern, axis=1)
    return feasible


class CuPyBinaryBackend:
    """CuPy-only binary search backend; construction requires a visible CUDA device."""

    def __init__(self, cupy: Any) -> None:
        self.cp = cupy
        runtime = cupy.cuda.runtime
        self.backend_name = "cupy_cuda"
        device_id = int(runtime.getDevice())
        properties = runtime.getDeviceProperties(device_id)
        model = properties.get("name", f"CUDA device {device_id}")
        if isinstance(model, bytes):
            model = model.decode("utf-8", errors="replace")
        self.gpu_model = str(model)
        version = int(runtime.runtimeGetVersion())
        self.cuda_runtime = f"{version // 1000}.{(version % 1000) // 10}"

    def _energies(self, terms: Sequence[Mapping[str, Any]], names: Sequence[str], states: Any) -> Any:
        cp = self.cp
        indices = {name: index for index, name in enumerate(names)}
        energies = cp.zeros(states.shape[0], dtype=cp.float64)
        for term in terms:
            coefficient = float(term["coefficient"])
            powers = term.get("powers", {})
            if not powers:
                energies += coefficient
                continue
            columns = [indices[str(name)] for name, power in powers.items() if int(power) > 0]
            energies += coefficient * cp.prod(states[:, columns], axis=1)
        return energies

    def _coordinate_search(
        self, terms: Sequence[Mapping[str, Any]], names: Sequence[str], states: Any, *, sweeps: int
    ) -> Any:
        cp = self.cp
        energies = self._energies(terms, names, states)
        for _ in range(sweeps):
            changed = False
            for column in range(len(names)):
                states[:, column] = 1 - states[:, column]
                proposed = self._energies(terms, names, states)
                accept = proposed < energies - 1e-12
                states[:, column] = cp.where(accept, states[:, column], 1 - states[:, column])
                energies = cp.where(accept, proposed, energies)
                changed = changed or bool(cp.any(accept).item())
            if not changed:
                break
        return states

    def generate_candidates(
        self,
        method: str,
        terms: Sequence[Mapping[str, Any]],
        variable_names: Sequence[str],
        *,
        candidate_count: int,
        seed: int,
    ) -> np.ndarray:
        cp = self.cp
        rng = cp.random.RandomState(seed)
        states = rng.randint(0, 2, size=(candidate_count, len(variable_names)), dtype=cp.int8)
        if method == "gpu_random_restart":
            # Every row is an independent native-binary restart, followed by
            # one Hamiltonian-only improving pass. No feasibility oracle is
            # consulted during search.
            result = self._coordinate_search(terms, variable_names, states, sweeps=1)
        elif method == "gpu_parallel_local_search":
            result = self._coordinate_search(terms, variable_names, states, sweeps=4)
        elif method == "gpu_simulated_annealing":
            energies = self._energies(terms, variable_names, states)
            rows = cp.arange(candidate_count)
            temperatures = np.geomspace(2.0, 0.01, 200)
            for temperature in temperatures:
                columns = rng.randint(0, len(variable_names), size=candidate_count)
                states[rows, columns] = 1 - states[rows, columns]
                proposed = self._energies(terms, variable_names, states)
                delta = proposed - energies
                accept = (delta <= 0.0) | (rng.random_sample(candidate_count) < cp.exp(-delta / temperature))
                rejected = ~accept
                states[rows[rejected], columns[rejected]] = 1 - states[rows[rejected], columns[rejected]]
                energies = cp.where(accept, proposed, energies)
            result = states
        else:
            raise ValueError(f"unknown GPU method {method!r}")
        cp.cuda.Stream.null.synchronize()
        return cp.asnumpy(result)


def require_cupy_backend() -> CuPyBinaryBackend:
    """Return the mandatory CUDA backend or fail without trying a CPU implementation."""

    try:
        cupy = importlib.import_module("cupy")
        if int(cupy.cuda.runtime.getDeviceCount()) < 1:
            raise RuntimeError("no CUDA devices are visible")
        return CuPyBinaryBackend(cupy)
    except Exception as exc:
        raise RuntimeError(
            f"CUDA/CuPy backend unavailable ({exc}); CPU fallback is forbidden for final GPU baselines"
        ) from exc


def build_fixed_recourse_evaluator(
    config_path: str | Path = DEFAULT_CONFIG,
) -> RecourseEvaluator:
    """Bind the existing shared IEEE123 fixed-upgrade recourse interface."""

    from cmpo.irc_cmpo_master import load_catalog  # noqa: PLC0415
    from cmpo.irc_cmpo_recourse import (  # noqa: PLC0415
        FixedRecourseCache,
        evaluate_fixed_upgrade_recourse,
    )
    from cmpo.scenario_coupled_model import (  # noqa: PLC0415
        load_public_grid,
        load_sc_cmpo_config,
    )

    config = yaml.safe_load(_resolve_input(config_path).read_text(encoding="utf-8"))
    assets = load_catalog(_resolve_input(config["source_asset_catalog"]))
    payload_directory = _resolve_input(config["source_payload_dir"])
    payload_glob = str(config.get("source_payload_glob", "*.json"))
    public_payloads = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(payload_directory.glob(payload_glob))
    }
    if len(public_payloads) != 12:
        raise ValueError(f"shared IEEE123 recourse requires 12 patch payloads, found {len(public_payloads)}")
    public_config = _resolve_input(config.get("source_sc_cmpo_config", DEFAULT_PUBLIC_CONFIG))
    grid = load_public_grid(load_sc_cmpo_config(public_config))
    solver_cache = FixedRecourseCache()

    def evaluate(payload: Mapping[str, Any], state: Mapping[str, int]) -> Any:
        selected = tuple(
            str(variable.get("physical_asset_key", str(variable["name"]).removeprefix("y::")))
            for variable in payload["variables"]
            if int(state[str(variable["name"])]) == 1
        )
        return evaluate_fixed_upgrade_recourse(
            public_payloads,
            assets,
            selected,
            grid=grid,
            heldout_limit=10,
            solver_cache=solver_cache,
        )

    return evaluate


def _recourse_record(result: Any) -> dict[str, Any]:
    fields = (
        "feasibility",
        "selected_solver",
        "total_ens",
        "critical_ens",
        "upgrade_cost",
        "maximum_customers_unserved",
        "critical_infrastructure_outage_hours",
        "critical_load_served_fraction",
        "heldout_critical_ens",
        "heldout_total_ens",
    )
    if isinstance(result, Mapping):
        record = {field: result[field] for field in fields}
    else:
        record = {field: getattr(result, field) for field in fields}
    for field in fields[2:]:
        record[field] = float(record[field])
        if not math.isfinite(record[field]):
            raise ValueError(f"fixed-upgrade recourse returned non-finite {field}")
    record["feasibility"] = bool(record["feasibility"])
    record["selected_solver"] = str(record["selected_solver"])
    return record


def _true_score(payload: Mapping[str, Any], recourse: Mapping[str, Any]) -> float:
    normalization = payload["resilience_normalization"]
    scalarization = payload["cost_scalarization"]
    return (
        (float(recourse["total_ens"]) - float(normalization["offset"]))
        / float(normalization["scale"])
        + float(scalarization["lambda"])
        * float(recourse["upgrade_cost"])
        / float(scalarization["maximum_catalog_portfolio_cost"])
    )


def _relative_regret(score: float, reference: float) -> float:
    return max(0.0, (score - reference) / max(abs(reference), 1e-12))


def _validate_payload(payload: Mapping[str, Any], manifest_row: Mapping[str, Any]) -> tuple[str, ...]:
    if not _as_bool(manifest_row["post_quantization_gates_passed"], field="quantization gate"):
        raise ValueError("final GPU baseline refuses a payload with a failed quantization gate")
    if _as_bool(manifest_row["projection_used"], field="projection_used"):
        raise ValueError("final GPU baseline payload manifest must record projection_used=false")
    if int(manifest_row.get("qci_jobs_submitted", 0)) != 0:
        raise ValueError("final GPU baseline refuses a manifest associated with a QCi submission")
    scaling = payload.get("dirac3_scaling", {})
    if not _as_bool(
        scaling.get("post_quantization_validation", {}).get("gates_passed", False),
        field="payload quantization gate",
    ):
        raise ValueError("final GPU baseline refuses a payload with a failed quantization gate")
    if _as_bool(scaling.get("projection_used", False), field="payload projection_used"):
        raise ValueError("final GPU baseline requires unprojected payloads")
    variables = payload.get("variables", ())
    names = tuple(str(variable["name"]) for variable in variables)
    if len(names) != int(payload.get("num_variables", -1)) or len(set(names)) != len(names):
        raise ValueError("payload has inconsistent or duplicate variables")
    if payload.get("num_levels") != [2] * len(names) or any(
        int(variable.get("lower_bound", -1)) != 0
        or int(variable.get("upper_bound", -1)) != 1
        or int(variable.get("num_levels", -1)) != 2
        for variable in variables
    ):
        raise ValueError("final GPU baseline requires native binary payload variables")
    terms = payload.get("polynomial_terms", ())
    if not terms or any(
        int(term.get("degree", len(term.get("powers", {})))) > 3
        or not math.isfinite(float(term["coefficient"]))
        for term in terms
    ):
        raise ValueError("payload Hamiltonian must be finite and degree at most three")
    return names


def _load_six_payloads(manifest_path: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: int(row["lambda_index"]))
    if len(rows) != 6 or [int(row["lambda_index"]) for row in rows] != list(range(6)):
        raise ValueError("final GPU baselines require exactly the six ordered v3 lambda payloads")
    loaded = []
    for row in rows:
        payload_path = _resolve_input(row["scaled_payload_path"], relative_to=manifest_path.parent)
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        _validate_payload(payload, row)
        loaded.append((dict(row), payload))
    return loaded


def _write_json_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv_new(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_final_gpu_baselines(
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    output_dir: str | Path = DEFAULT_OUTPUT,
    candidate_count: int = MINIMUM_CANDIDATES,
    backend: Any | None = None,
    recourse_evaluator: RecourseEvaluator | None = None,
    config_path: str | Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Run all three native-binary methods against an exact reference for six lambdas."""

    if candidate_count < MINIMUM_CANDIDATES:
        raise ValueError("final GPU baselines require at least 10,000 native binary candidates per lambda/method")
    manifest = _resolve_input(manifest_path)
    output = Path(output_dir)
    if not output.is_absolute():
        output = ROOT / output
    targets = (output / SUMMARY_NAME, output / METRICS_NAME, output / EXACT_NAME)
    if output.exists() or any(path.exists() for path in targets):
        raise FileExistsError(f"final GPU baseline artifacts are create-only: {output}")
    payloads = _load_six_payloads(manifest)
    gpu = backend if backend is not None else require_cupy_backend()
    evaluate_recourse = recourse_evaluator or build_fixed_recourse_evaluator(config_path)
    for attribute in ("backend_name", "gpu_model", "cuda_runtime", "generate_candidates"):
        if not hasattr(gpu, attribute):
            raise TypeError(f"GPU backend lacks required attribute {attribute}")

    metric_rows: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    for row, payload in payloads:
        index = int(row["lambda_index"])
        names = _validate_payload(payload, row)
        terms = payload["polynomial_terms"]
        feasibility = lambda state, p=payload: bool(  # noqa: E731
            _native_feasibility(
                p, np.asarray([[state[name] for name in names]], dtype=np.int8)
            )[0]
        )
        exact_started = time.perf_counter()
        exact = solve_binary_hamiltonian_exact(terms, names, top_k=1, feasibility=feasibility)
        exact_runtime = time.perf_counter() - exact_started
        if not exact.solutions[0].natively_feasible:
            raise RuntimeError(f"lambda {index} exact Hamiltonian optimum is not natively feasible")
        exact_recourse = _recourse_record(evaluate_recourse(payload, exact.solutions[0].state))
        exact_true_score = _true_score(payload, exact_recourse)
        exact_rows.append(
            {
                "lambda_index": index,
                "cost_weight": float(row["cost_weight"]),
                "backend": exact.backend,
                "runtime_seconds": exact_runtime,
                "optimum_energy": exact.optimum_energy,
                "optimum_state": exact.solutions[0].state,
                "optimum_natively_feasible": exact.solutions[0].natively_feasible,
                "fixed_upgrade_recourse": exact_recourse,
                "true_score": exact_true_score,
                "projection_used": False,
            }
        )
        good_limit = exact.optimum_energy + 0.02 * max(abs(exact.optimum_energy), 1.0)
        for method_index, method in enumerate(METHODS):
            started = time.perf_counter()
            candidates = np.asarray(
                gpu.generate_candidates(
                    method,
                    terms,
                    names,
                    candidate_count=candidate_count,
                    seed=2026 + index * len(METHODS) + method_index,
                )
            )
            runtime = time.perf_counter() - started
            if candidates.shape != (candidate_count, len(names)):
                raise RuntimeError(
                    f"{method} returned shape {candidates.shape}, expected {(candidate_count, len(names))}"
                )
            if not np.issubdtype(candidates.dtype, np.integer) or np.any(
                (candidates != 0) & (candidates != 1)
            ):
                raise RuntimeError(f"{method} returned a non-native-binary candidate")
            candidates = candidates.astype(np.int8, copy=False)
            energies = _evaluate_batch(terms, names, candidates)
            feasible = _native_feasibility(payload, candidates)
            regrets = np.maximum(0.0, energies - exact.optimum_energy)
            feasible_signatures = np.unique(candidates[feasible], axis=0)
            feasible_indices = np.flatnonzero(feasible)
            if not len(feasible_indices):
                raise RuntimeError(f"{method} produced no natively feasible candidate for lambda {index}")
            best_index = int(feasible_indices[np.argmin(energies[feasible_indices])])
            best_state = {
                name: int(candidates[best_index, column])
                for column, name in enumerate(names)
            }
            best_recourse = _recourse_record(evaluate_recourse(payload, best_state))
            ordered_feasible = feasible_indices[np.argsort(energies[feasible_indices])]
            median_index = int(ordered_feasible[len(ordered_feasible) // 2])
            median_state = {
                name: int(candidates[median_index, column])
                for column, name in enumerate(names)
            }
            median_recourse = _recourse_record(evaluate_recourse(payload, median_state))
            best_true_regret = _relative_regret(
                _true_score(payload, best_recourse), exact_true_score
            )
            median_true_regret = _relative_regret(
                _true_score(payload, median_recourse), exact_true_score
            )
            good_indices = np.flatnonzero(energies <= good_limit + 1e-12)
            # GPU candidates are evaluated concurrently, so the first
            # observable good solution is available when the synchronized
            # batch completes rather than at a fabricated serial fraction.
            time_to_good = runtime if len(good_indices) else None
            metric_rows.append(
                {
                    "lambda_index": index,
                    "cost_weight": float(row["cost_weight"]),
                    "method": method,
                    "gpu_model": str(gpu.gpu_model),
                    "gpu_backend": str(gpu.backend_name),
                    "cuda_runtime": str(gpu.cuda_runtime),
                    "runtime_seconds": runtime,
                    "candidate_count": candidate_count,
                    "native_feasibility_rate": float(np.mean(feasible)),
                    "exact_optimum_hit_rate": float(
                        np.mean(np.isclose(energies, exact.optimum_energy, atol=1e-9))
                    ),
                    "best_hamiltonian_regret": float(np.min(regrets)),
                    "median_hamiltonian_regret": float(np.median(regrets)),
                    "portfolio_diversity": int(len(feasible_signatures)),
                    "time_to_good_solution_seconds": time_to_good,
                    "best_candidate_recourse_feasible": best_recourse["feasibility"],
                    "best_candidate_recourse_solver": best_recourse["selected_solver"],
                    "best_candidate_total_ens": best_recourse["total_ens"],
                    "best_candidate_critical_ens": best_recourse["critical_ens"],
                    "best_candidate_upgrade_cost": best_recourse["upgrade_cost"],
                    "best_candidate_maximum_customers_unserved": best_recourse[
                        "maximum_customers_unserved"
                    ],
                    "best_candidate_critical_infrastructure_outage_hours": best_recourse[
                        "critical_infrastructure_outage_hours"
                    ],
                    "best_candidate_critical_load_served_fraction": best_recourse[
                        "critical_load_served_fraction"
                    ],
                    "best_candidate_heldout_critical_ens": best_recourse[
                        "heldout_critical_ens"
                    ],
                    "best_candidate_heldout_total_ens": best_recourse[
                        "heldout_total_ens"
                    ],
                    "best_true_recourse_regret": best_true_regret,
                    "median_true_recourse_regret": median_true_regret,
                    "median_candidate_total_ens": median_recourse["total_ens"],
                    "median_candidate_critical_ens": median_recourse["critical_ens"],
                    "median_candidate_upgrade_cost": median_recourse["upgrade_cost"],
                    "projection_used": False,
                }
            )

    summary = {
        "schema": "cmpo.irc_cmpo.final_gpu_baselines.v1",
        "lambda_count": len(payloads),
        "methods": list(METHODS),
        "candidate_count_per_lambda_method": candidate_count,
        "gpu_model": str(gpu.gpu_model),
        "gpu_backend": str(gpu.backend_name),
        "cuda_runtime": str(gpu.cuda_runtime),
        "exact_backend": exact_rows[0]["backend"],
        "recourse_interface": "cmpo.irc_cmpo_recourse.evaluate_fixed_upgrade_recourse",
        "projection_used": False,
        "cpu_fallback_used": False,
        "qci_jobs_submitted": 0,
        "manifest_path": str(manifest),
        "metrics_path": str(targets[1]),
        "exact_references_path": str(targets[2]),
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json_new(targets[0], summary)
    _write_csv_new(targets[1], metric_rows)
    _write_json_new(
        targets[2],
        {
            "schema": "cmpo.irc_cmpo.exact_milp_references.v1",
            "references": exact_rows,
            "projection_used": False,
        },
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--candidate-count", type=int, default=MINIMUM_CANDIDATES)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the GPU baseline plan without requiring CUDA or writing artifacts.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "action": "run_irc_cmpo_gpu_baselines",
                    "manifest": args.manifest,
                    "output_dir": args.output_dir,
                    "candidate_count": args.candidate_count,
                    "config": args.config,
                    "cpu_fallback_permitted": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(
        json.dumps(
            run_final_gpu_baselines(
                manifest_path=args.manifest,
                output_dir=args.output_dir,
                candidate_count=args.candidate_count,
                config_path=args.config,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
