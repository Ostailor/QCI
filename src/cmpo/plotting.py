"""Matplotlib plots for Phase 2 outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cmpo.data import GridCase


def _save_bar(frame: pd.DataFrame, x: str, y: str, path: Path, title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    frame.plot(kind="bar", x=x, y=y, ax=ax, legend=False)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_cubic_vs_quadratic(grid_case: GridCase, path: Path) -> None:
    microgrid = grid_case.microgrids[0]
    generator = microgrid.generator
    p_values = np.linspace(generator.p_min_kw, generator.p_max_kw, 80)
    cubic = generator.cost_a * p_values**3 + generator.cost_b * p_values**2 + generator.cost_c * p_values
    quadratic = generator.cost_b * p_values**2 + generator.cost_c * p_values

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(p_values, cubic, label="Cubic cost")
    ax.plot(p_values, quadratic, label="Quadratic approximation")
    ax.set_title("Cubic vs Quadratic Generator Cost")
    ax.set_xlabel("Dispatch kW")
    ax.set_ylabel("Cost units")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_phase2_plots(tables: dict[str, pd.DataFrame], grid_case: GridCase, output_dir: Path | str = Path("results")) -> dict[str, Path]:
    """Write all requested Phase 2 figures to ``results/figures``."""

    figures_dir = Path(output_dir) / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary = tables["summary_metrics"]
    scenarios = tables["scenario_results"]
    scaling = tables["scaling_results"]

    paths = {
        "cost_by_method": figures_dir / "cost_by_method.png",
        "critical_load_served_by_method": figures_dir / "critical_load_served_by_method.png",
        "energy_not_served_by_scenario": figures_dir / "energy_not_served_by_scenario.png",
        "feasibility_rate_by_method": figures_dir / "feasibility_rate_by_method.png",
        "runtime_by_method": figures_dir / "runtime_by_method.png",
        "scenario_scaling": figures_dir / "scenario_scaling.png",
        "cubic_vs_quadratic_dispatch": figures_dir / "cubic_vs_quadratic_dispatch.png",
    }

    _save_bar(summary, "method_name", "expected_operating_cost", paths["cost_by_method"], "Expected Cost By Method", "Cost")
    _save_bar(
        summary,
        "method_name",
        "critical_load_served_fraction",
        paths["critical_load_served_by_method"],
        "Critical Load Served By Method",
        "Fraction",
    )
    ens_by_scenario = scenarios.groupby("scenario", as_index=False)["energy_not_served_kwh"].sum()
    _save_bar(
        ens_by_scenario,
        "scenario",
        "energy_not_served_kwh",
        paths["energy_not_served_by_scenario"],
        "Energy Not Served By Scenario",
        "kWh",
    )
    _save_bar(
        summary,
        "method_name",
        "feasibility_rate",
        paths["feasibility_rate_by_method"],
        "Feasibility Rate By Method",
        "Rate",
    )
    _save_bar(
        summary,
        "method_name",
        "median_runtime_seconds",
        paths["runtime_by_method"],
        "Median Runtime By Method",
        "Seconds",
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    for method, group in scaling.groupby("method_name"):
        ordered = group.sort_values(["scenario", "patch"])
        ax.plot(ordered["scenario"], ordered["scenario_scaling_runtime"], marker="o", label=method)
    ax.set_title("Scenario Scaling Runtime")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Seconds")
    ax.tick_params(axis="x", rotation=30)
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["scenario_scaling"], dpi=160)
    plt.close(fig)

    _plot_cubic_vs_quadratic(grid_case, paths["cubic_vs_quadratic_dispatch"])
    return paths


def expected_figure_paths(results_dir: Path) -> list[Path]:
    """Return the requested Phase 2 figure paths."""

    figures_dir = results_dir / "figures"
    return [
        figures_dir / "cost_by_method.png",
        figures_dir / "critical_load_served_by_method.png",
        figures_dir / "energy_not_served_by_scenario.png",
        figures_dir / "feasibility_rate_by_method.png",
        figures_dir / "runtime_by_method.png",
        figures_dir / "scenario_scaling.png",
        figures_dir / "cubic_vs_quadratic_dispatch.png",
    ]
