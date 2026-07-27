"""Configuration dataclasses and CLI parsing helpers for CMPO."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetConfig:
    """Synthetic microgrid dataset shape used by reproduction workflows."""

    n_microgrids: int = 4
    horizon_hours: int = 6
    seed: int = 42


@dataclass(frozen=True)
class SolverConfig:
    """Iteration controls shared by the baseline and CMPO-local optimizers."""

    max_iterations: int = 100
    random_restarts: int = 8


@dataclass(frozen=True)
class OutputConfig:
    """Filesystem output locations for generated artifacts."""

    results_dir: Path = Path("results")
    data_dir: Path = Path("data")


@dataclass(frozen=True)
class ExperimentConfig:
    """Top-level configuration object passed across CMPO workflows."""

    dataset: DatasetConfig = DatasetConfig()
    solver: SolverConfig = SolverConfig()
    output: OutputConfig = OutputConfig()


def build_parser(description: str) -> argparse.ArgumentParser:
    """Create a common parser for repository scripts."""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--seed", type=int, default=42, help="Reproducibility seed.")
    parser.add_argument("--results-dir", default="results", help="Directory for generated outputs.")
    parser.add_argument("--data-dir", default="data", help="Directory for generated synthetic case files.")
    parser.add_argument("--n-microgrids", type=int, default=4, help="Synthetic microgrid count.")
    parser.add_argument("--horizon-hours", type=int, default=6, help="Optimization horizon length.")
    return parser


def config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    """Convert parsed CLI arguments into an immutable experiment config."""

    return ExperimentConfig(
        dataset=DatasetConfig(
            n_microgrids=args.n_microgrids,
            horizon_hours=args.horizon_hours,
            seed=args.seed,
        ),
        output=OutputConfig(results_dir=Path(args.results_dir), data_dir=Path(args.data_dir)),
    )
