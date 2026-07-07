"""Build QCi-executable decompositions of public benchmark payloads."""

from __future__ import annotations

import csv
import json
import shutil
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cmpo.baseline_orchestrator import build_grid_case_from_config, load_phase3_config, phase3_output_dir
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.qci_export import build_polynomial_model_payload


DEFAULT_MAX_VARIABLES = 132
DEFAULT_MAX_DEGREE = 3
VARIABLES_PER_MICROGRID_HOUR = 11
HARD_SCENARIO_ORDER = [
    "pcc_failure",
    "storm_forced_islanding",
    "local_generator_failure",
    "demand_surge",
    "renewable_shortfall",
    "combined_high_stress",
    "restoration",
    "normal",
]

BENCHMARK_CONFIGS = {
    "pglib_case5_pjm": "configs/phase3_pglib_case5.yaml",
    "pglib_case14_ieee": "configs/phase3_pglib_case14.yaml",
    "pglib_case30_ieee": "configs/phase3_pglib_case30.yaml",
    "pglib_case57_ieee": "configs/phase3_pglib_case57.yaml",
}

BENCHMARK_RESULT_DIRS = {
    "pglib_case5_pjm": Path("results/phase3/public_benchmarks/pglib_case5_pjm"),
    "pglib_case14_ieee": Path("results/phase3/public_benchmarks/pglib_case14_ieee"),
    "pglib_case30_ieee": Path("results/phase3/public_benchmarks/pglib_case30_ieee"),
    "pglib_case57_ieee": Path("results/phase3/public_benchmarks/pglib_case57_ieee"),
}


@dataclass(frozen=True)
class DecompositionSettings:
    """QCi-fit decomposition settings."""

    benchmark: str
    max_variables: int = DEFAULT_MAX_VARIABLES
    max_degree: int = DEFAULT_MAX_DEGREE
    seed: int | None = None
    scenario_filter: str = "all"
    max_scenarios: int | None = None
    rolling_horizon: int | None = None


def _safe_slug(value: str) -> str:
    return value.replace(" ", "_").replace("/", "_").replace("|", "-")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_payloads(case_dir: Path) -> list[Path]:
    return sorted((case_dir / "qci_payloads").glob("*.json"))


def _scenario_selected(name: str, settings: DecompositionSettings) -> bool:
    raw = settings.scenario_filter.strip()
    if raw == "all":
        return True
    if raw == "hardest":
        selected = HARD_SCENARIO_ORDER[: settings.max_scenarios or len(HARD_SCENARIO_ORDER)]
        return name in selected
    selected = {item.strip() for item in raw.split(",") if item.strip()}
    return name in selected


def _rank_payload(path: Path) -> tuple[int, str]:
    payload = _read_json(path)
    scenario = str(payload.get("scenario_metadata", {}).get("scenario", ""))
    try:
        rank = HARD_SCENARIO_ORDER.index(scenario)
    except ValueError:
        rank = len(HARD_SCENARIO_ORDER)
    return rank, path.name


def _filtered_payloads(paths: list[Path], settings: DecompositionSettings) -> list[Path]:
    selected = [
        path
        for path in paths
        if _scenario_selected(str(_read_json(path).get("scenario_metadata", {}).get("scenario", "")), settings)
    ]
    selected = sorted(selected, key=_rank_payload)
    if settings.scenario_filter == "hardest" and settings.max_scenarios is not None:
        seen: set[str] = set()
        scenario_order: list[str] = []
        for path in selected:
            scenario = str(_read_json(path).get("scenario_metadata", {}).get("scenario", ""))
            if scenario not in seen:
                seen.add(scenario)
                scenario_order.append(scenario)
        allowed = set(scenario_order[: settings.max_scenarios])
        selected = [path for path in selected if str(_read_json(path).get("scenario_metadata", {}).get("scenario", "")) in allowed]
    return selected


def _config_for_benchmark(settings: DecompositionSettings) -> dict[str, Any]:
    if settings.benchmark not in BENCHMARK_CONFIGS:
        known = ", ".join(sorted(BENCHMARK_CONFIGS))
        raise ValueError(f"unsupported QCi-fit benchmark {settings.benchmark!r}; known: {known}")
    config = load_phase3_config(BENCHMARK_CONFIGS[settings.benchmark])
    if settings.seed is not None:
        config["seed"] = settings.seed
        config.setdefault("dataset", {})["seed"] = settings.seed
    return config


def _config_with_horizon(config: dict[str, Any], horizon: int) -> dict[str, Any]:
    copy = deepcopy(config)
    copy.setdefault("dataset", {})["horizon_hours"] = horizon
    return copy


def _rolling_windows(items: list[str], size: int) -> list[tuple[str, ...]]:
    if size <= 0:
        return []
    if len(items) <= size:
        return [tuple(items)]
    windows = [tuple(items[index : index + size]) for index in range(0, len(items) - size + 1)]
    if size > 1 and len(items) > size:
        tail = tuple(items[-size:])
        if tail not in windows:
            windows.append(tail)
    return windows


def _candidate_patch_windows(patch_ids: list[str], horizon: int, max_variables: int) -> list[tuple[str, ...]]:
    max_patch_size = max(1, max_variables // max(VARIABLES_PER_MICROGRID_HOUR * horizon, 1))
    max_patch_size = min(max_patch_size, len(patch_ids))
    candidates: list[tuple[str, ...]] = []
    for size in range(max_patch_size, 0, -1):
        for window in _rolling_windows(patch_ids, size):
            if window not in candidates:
                candidates.append(window)
    return candidates


def _write_payload(payload: dict[str, Any], output_dir: Path, source_path: Path, patch: tuple[str, ...]) -> Path:
    scenario = str(payload.get("scenario_metadata", {}).get("scenario", "scenario"))
    patch_slug = "-".join(patch)
    source_slug = source_path.stem
    output_path = output_dir / f"{_safe_slug(scenario)}_{_safe_slug(patch_slug)}__from__{_safe_slug(source_slug)}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def _manifest_row(payload_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    decomposition = payload["qci_fit_decomposition"]
    stats = payload.get("model_statistics", {})
    scaling = payload.get("scaling_information", {})
    return {
        "payload_name": payload_path.name,
        "payload_path": str(payload_path),
        "source_benchmark_name": decomposition["source_benchmark_name"],
        "source_full_payload_id": decomposition["source_full_payload_id"],
        "source_full_payload_path": decomposition["source_full_payload_path"],
        "decomposition_rule": decomposition["decomposition_rule"],
        "patch_ids": json.dumps(decomposition["patch_ids"]),
        "scenario": decomposition["scenario"],
        "horizon": decomposition["horizon"],
        "variable_count": int(stats.get("variable_count", len(payload.get("variables", [])))),
        "term_count": int(stats.get("term_count", len(payload.get("polynomial_terms", [])))),
        "degree": int(stats.get("degree", payload.get("max_degree", 0))),
        "coefficient_scaling_factor": float(scaling.get("coefficient_scaling_factor", 1.0)),
        "reason_qci_executable": decomposition["reason_qci_executable"],
    }


def _failure_row(source_path: Path, reason: str) -> dict[str, Any]:
    payload = _read_json(source_path)
    return {
        "source_full_payload_id": source_path.stem,
        "source_full_payload_path": str(source_path),
        "scenario": payload.get("scenario_metadata", {}).get("scenario", ""),
        "patch_ids": json.dumps(payload.get("patch_metadata", {}).get("patch_ids", [])),
        "reason": reason,
    }


def build_qci_fit_payloads(
    settings: DecompositionSettings,
    *,
    output_dir: Path | None = None,
    overwrite: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build QCi-fit decomposed payloads for a public benchmark."""

    config = _config_for_benchmark(settings)
    case_dir = BENCHMARK_RESULT_DIRS[settings.benchmark]
    full_payloads = _filtered_payloads(_source_payloads(case_dir), settings)
    fit_dir = output_dir or case_dir / "qci_fit_payloads"
    failure_path = case_dir / "qci_fit_failure_report.csv"
    manifest_path = case_dir / "qci_fit_payload_manifest.csv"
    provenance_path = case_dir / "qci_fit_provenance.json"
    plan = {
        "benchmark": settings.benchmark,
        "source_payload_count": len(full_payloads),
        "output_dir": str(fit_dir),
        "max_variables": settings.max_variables,
        "max_degree": settings.max_degree,
        "dry_run": dry_run,
    }
    if dry_run:
        return plan
    if overwrite and fit_dir.exists():
        shutil.rmtree(fit_dir)
    fit_dir.mkdir(parents=True, exist_ok=True)

    original_horizon = int(config.get("dataset", {}).get("horizon_hours", 6))
    max_horizon = min(settings.rolling_horizon or original_horizon, original_horizon)
    grids_by_horizon: dict[int, Any] = {}
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for source_path in full_payloads:
        source_payload = _read_json(source_path)
        source_patch_ids = [str(item) for item in source_payload.get("patch_metadata", {}).get("patch_ids", [])]
        scenario_name = str(source_payload.get("scenario_metadata", {}).get("scenario", ""))
        source_variable_count = len(source_payload.get("variables", []))
        built_for_source = False
        for horizon in range(max_horizon, 0, -1):
            if horizon not in grids_by_horizon:
                horizon_config = _config_with_horizon(config, horizon)
                grids_by_horizon[horizon] = build_grid_case_from_config(horizon_config, phase3_output_dir(config) / "data")
            grid_case = grids_by_horizon[horizon]
            scenario = next((item for item in grid_case.scenarios if item.name == scenario_name), None)
            if scenario is None:
                continue
            for patch in _candidate_patch_windows(source_patch_ids, horizon, settings.max_variables):
                model, metadata = build_scenario_hamiltonian(grid_case, scenario, patch, output_dir=phase3_output_dir(config), write_export=False)
                payload = build_polynomial_model_payload(model, metadata)
                variable_count = len(payload["variables"])
                degree = int(payload["max_degree"])
                if variable_count > settings.max_variables or degree > settings.max_degree:
                    continue
                rule = (
                    f"source variables={source_variable_count}; selected rolling patch {list(patch)} "
                    f"at horizon {horizon} under max_variables={settings.max_variables}, max_degree={settings.max_degree}"
                )
                reason = (
                    f"QCi executable because variable_count={variable_count} <= {settings.max_variables} "
                    f"and degree={degree} <= {settings.max_degree}."
                )
                stats = payload.get("model_statistics", {})
                payload["qci_fit_decomposition"] = {
                    "source_benchmark_name": settings.benchmark,
                    "source_full_payload_id": source_path.stem,
                    "source_full_payload_path": str(source_path),
                    "source_full_variable_count": source_variable_count,
                    "decomposition_rule": rule,
                    "patch_ids": list(patch),
                    "scenario": scenario_name,
                    "horizon": horizon,
                    "variable_count": variable_count,
                    "term_count": int(stats.get("term_count", len(payload.get("polynomial_terms", [])))),
                    "degree": degree,
                    "coefficient_scaling_factor": payload.get("scaling_information", {}).get("coefficient_scaling_factor", 1.0),
                    "reason_qci_executable": reason,
                    "deterministic_seed": settings.seed if settings.seed is not None else config.get("seed"),
                }
                output_path = _write_payload(payload, fit_dir, source_path, patch)
                rows.append(_manifest_row(output_path, payload))
                built_for_source = True
            if built_for_source:
                break
        if not built_for_source:
            failures.append(
                _failure_row(
                    source_path,
                    (
                        f"No decomposition met max_variables={settings.max_variables}, max_degree={settings.max_degree}, "
                        f"rolling_horizon<={max_horizon}."
                    ),
                )
            )

    _write_csv(rows, manifest_path)
    _write_csv(failures, failure_path)
    max_variables = max((int(row["variable_count"]) for row in rows), default=0)
    max_degree = max((int(row["degree"]) for row in rows), default=0)
    provenance = {
        "benchmark": settings.benchmark,
        "qci_fit_payload_dir": str(fit_dir),
        "qci_fit_payload_manifest": str(manifest_path),
        "qci_fit_failure_report": str(failure_path),
        "source_full_payload_dir": str(case_dir / "qci_payloads"),
        "source_payload_count": len(full_payloads),
        "qci_fit_payload_count": len(rows),
        "failure_count": len(failures),
        "max_variables": max_variables,
        "max_degree": max_degree,
        "settings": settings.__dict__,
        "status": "available" if rows else "decomposition_failed",
    }
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
