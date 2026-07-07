"""Registry for Phase 3 public-benchmark-derived CMPO cases."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PHASE3_PUBLIC_ROOT = Path("results/phase3/public_benchmarks")
DATA_PUBLIC_ROOT = Path("data/public_benchmarks")


@dataclass(frozen=True)
class BenchmarkCase:
    """Benchmark case metadata used by fetch/build/validation scripts."""

    key: str
    family: str
    config_path: str | None
    results_dir: str
    data_dir: str
    source_name: str
    upstream_url: str
    required_for_ladder: bool = True
    qci_required: bool = False
    transformation_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BENCHMARK_CASES: dict[str, BenchmarkCase] = {
    "pglib_case5_pjm": BenchmarkCase(
        key="pglib_case5_pjm",
        family="pglib",
        config_path="configs/phase3_pglib_case5.yaml",
        results_dir=str(PHASE3_PUBLIC_ROOT / "pglib_case5_pjm"),
        data_dir=str(DATA_PUBLIC_ROOT / "pglib"),
        source_name="PGLib-OPF pglib_opf_case5_pjm",
        upstream_url="https://github.com/power-grid-lib/pglib-opf",
        qci_required=True,
        transformation_notes="Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction.",
    ),
    "pglib_case14_ieee": BenchmarkCase(
        key="pglib_case14_ieee",
        family="pglib",
        config_path="configs/phase3_pglib_case14.yaml",
        results_dir=str(PHASE3_PUBLIC_ROOT / "pglib_case14_ieee"),
        data_dir=str(DATA_PUBLIC_ROOT / "pglib"),
        source_name="PGLib-OPF pglib_opf_case14_ieee",
        upstream_url="https://github.com/power-grid-lib/pglib-opf",
        qci_required=True,
        transformation_notes="Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction.",
    ),
    "pglib_case30_ieee": BenchmarkCase(
        key="pglib_case30_ieee",
        family="pglib",
        config_path="configs/phase3_pglib_case30.yaml",
        results_dir=str(PHASE3_PUBLIC_ROOT / "pglib_case30_ieee"),
        data_dir=str(DATA_PUBLIC_ROOT / "pglib"),
        source_name="PGLib-OPF pglib_opf_case30_ieee",
        upstream_url="https://github.com/power-grid-lib/pglib-opf",
        transformation_notes="Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction.",
    ),
    "pglib_case57_ieee": BenchmarkCase(
        key="pglib_case57_ieee",
        family="pglib",
        config_path="configs/phase3_pglib_case57.yaml",
        results_dir=str(PHASE3_PUBLIC_ROOT / "pglib_case57_ieee"),
        data_dir=str(DATA_PUBLIC_ROOT / "pglib"),
        source_name="PGLib-OPF pglib_opf_case57_ieee",
        upstream_url="https://github.com/power-grid-lib/pglib-opf",
        required_for_ladder=False,
        transformation_notes="Public-benchmark-derived microgrid resilience adapter; QCi may be infeasible if payloads exceed limits.",
    ),
    "arpae_go": BenchmarkCase(
        key="arpae_go",
        family="arpae_go",
        config_path=None,
        results_dir=str(PHASE3_PUBLIC_ROOT / "arpae_go"),
        data_dir=str(DATA_PUBLIC_ROOT / "arpae_go"),
        source_name="ARPA-E Grid Optimization Challenge public data",
        upstream_url="https://data.openei.org/submissions/6153",
        transformation_notes="ARPA-E GO-derived microgrid stress adapter feasibility path.",
    ),
    "ieee_distribution": BenchmarkCase(
        key="ieee_distribution",
        family="ieee_distribution",
        config_path=None,
        results_dir=str(PHASE3_PUBLIC_ROOT / "ieee_distribution"),
        data_dir=str(DATA_PUBLIC_ROOT / "ieee_distribution"),
        source_name="IEEE distribution feeder public data",
        upstream_url="https://github.com/tshort/OpenDSS",
        transformation_notes="Distribution-feeder-derived CMPO bridge path with PowerModelsDistribution compatibility notes.",
    ),
}


PGLIB_LEGACY_RESULT_DIRS = {
    "pglib_case5_pjm": PHASE3_PUBLIC_ROOT / "pglib_case5",
    "pglib_case14_ieee": PHASE3_PUBLIC_ROOT / "pglib_case14",
    "pglib_case30_ieee": PHASE3_PUBLIC_ROOT / "pglib_case30",
    "pglib_case57_ieee": PHASE3_PUBLIC_ROOT / "pglib_case57",
}


def benchmark_cases(family: str | None = None) -> list[BenchmarkCase]:
    """Return registered benchmark cases, optionally filtered by family."""

    cases = list(BENCHMARK_CASES.values())
    if family is not None:
        cases = [case for case in cases if case.family == family]
    return cases


def case_by_key(key: str) -> BenchmarkCase:
    """Look up a registered benchmark case."""

    if key not in BENCHMARK_CASES:
        known = ", ".join(sorted(BENCHMARK_CASES))
        raise KeyError(f"unknown benchmark case {key!r}; known cases: {known}")
    return BENCHMARK_CASES[key]
