#!/usr/bin/env python3
"""Build publication figures for the Phase 3 paper from a selected result tree.

The result figure reads immutable Phase 3 CSV artifacts. The method figure is
schematic and documents the evaluated pipeline; neither path changes raw data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHASE3_ROOT = REPO_ROOT / "results" / "phase3"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "submission" / "paper" / "generated" / "figures"
SAMPLE_QUALITY_PATH = Path(
    "results/phase3/irc_cmpo/final/table3_native_sample_quality.csv"
)
ENCODING_PATH = Path(
    "results/phase3/irc_cmpo/final/table6_encoding_comparison.csv"
)
OUTPUT_FILES = (
    "figure_sources.json",
    "ground_state_and_encoding.pdf",
    "ground_state_and_encoding.png",
    "method_overview.pdf",
    "method_overview.png",
)

NAVY = "#183B66"
GREEN = "#4D7C6A"
GOLD = "#A77A2D"
RED = "#8F5A58"
PALE_BLUE = "#EAF1F8"
PALE_GREEN = "#EAF5EC"
PALE_GOLD = "#FBF3DE"
GRAY = "#6A6A6A"
LIGHT_GRAY = "#D9D9D9"
TEXT = "#151515"


def _source_path(relative_path: Path, phase3_root: Path) -> Path:
    prefix = Path("results/phase3")
    try:
        suffix = relative_path.relative_to(prefix)
    except ValueError as exc:
        raise ValueError(f"figure source is not under {prefix}: {relative_path}") from exc
    return phase3_root / suffix


def _read_csv(
    relative_path: Path, phase3_root: Path = DEFAULT_PHASE3_ROOT
) -> list[dict[str, str]]:
    path = _source_path(relative_path, phase3_root)
    if not path.is_file():
        raise FileNotFoundError(f"Required figure source is missing: {relative_path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 13,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 14,
            "axes.edgecolor": "#A8A8A8",
            "axes.linewidth": 0.8,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _style_axis(axis: plt.Axes) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", color="#E4E4E4", linewidth=0.7)
    axis.set_axisbelow(True)


def _save_figure(figure: plt.Figure, output_stem: Path) -> None:
    figure.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(figure)


def _plot_ground_state_and_encoding(
    sample_rows: list[dict[str, str]],
    encoding_rows: list[dict[str, str]],
    output_stem: Path,
) -> None:
    method_specs = (
        ("QCi IRC-CMPO", "QCi", NAVY, 2.8, "o", "-"),
        (
            "gpu_parallel_local_search",
            "L4 local",
            GREEN,
            2.0,
            "s",
            "--",
        ),
        ("gpu_random_restart", "L4 restart", GOLD, 2.0, "^", "-."),
        ("gpu_simulated_annealing", "L4 annealing", RED, 2.0, "D", ":"),
    )
    positive = [
        row
        for row in sample_rows
        if int(row["lambda_index"]) > 0
    ]
    weights = sorted({float(row["cost_weight"]) for row in positive})
    x = list(range(len(weights)))

    figure, (left, right) = plt.subplots(
        1,
        2,
        figsize=(10.4, 4.0),
        gridspec_kw={"width_ratios": [1.62, 1.0]},
    )
    for method, label, color, linewidth, marker, linestyle in method_specs:
        method_rows = sorted(
            (row for row in positive if row["method"] == method),
            key=lambda row: float(row["cost_weight"]),
        )
        if len(method_rows) != len(weights):
            raise ValueError(f"Incomplete exact-hit-rate series for {method}")
        rates = [100.0 * float(row["exact_optimum_hit_rate"]) for row in method_rows]
        left.plot(
            x,
            rates,
            label=label,
            color=color,
            linewidth=linewidth,
            marker=marker,
            markersize=5.5,
            linestyle=linestyle,
        )
        if method == "QCi IRC-CMPO":
            for x_value, rate in zip(x, rates, strict=True):
                left.text(
                    x_value,
                    rate + 3.0,
                    f"{rate:.0f}%",
                    ha="center",
                    va="bottom",
                    color=color,
                    fontsize=10.5,
                    fontweight="bold",
                )
        label_y = rates[-1]
        if method == "gpu_simulated_annealing":
            label_y = 3.0
        left.text(
            x[-1] + 0.16,
            label_y,
            f"{label}  {rates[-1]:.0f}%",
            ha="left",
            va="center",
            color=color,
            fontsize=12,
            fontweight="bold" if method == "QCi IRC-CMPO" else "normal",
        )

    left.set_title("(a) Exact ground-state yield")
    left.set_xlabel(r"Cost weight $\lambda$")
    left.set_ylabel("Exact ground-state yield (%)")
    left.set_xticks(x, [f"{weight:.2f}" for weight in weights])
    left.set_xlim(-0.2, 5.0)
    left.set_ylim(-3, 113)
    left.set_yticks((0, 25, 50, 75, 100))
    _style_axis(left)

    native = next(
        row
        for row in encoding_rows
        if row["lambda_index"] == "1" and row["encoding"] == "native cubic integer"
    )
    quadratized = next(
        row
        for row in encoding_rows
        if row["lambda_index"] == "1"
        and row["encoding"] == "MILP/QUBO quadratized comparison"
    )
    logical = int(native["logical_variables"])
    native_aux = int(native["auxiliary_variables"])
    quadratized_aux = int(quadratized["auxiliary_variables"])
    y = (1, 0)
    right.barh(y, (logical, logical), color=NAVY, height=0.48, label="Physical")
    right.barh(
        y,
        (native_aux, quadratized_aux),
        left=(logical, logical),
        color=GOLD,
        height=0.48,
        label="Auxiliary",
    )
    totals = (logical + native_aux, logical + quadratized_aux)
    for y_value, total in zip(y, totals, strict=True):
        right.text(
            total + 1.2,
            y_value,
            str(total),
            va="center",
            ha="left",
            fontsize=13,
            fontweight="bold",
            color=TEXT,
        )
    right.text(
        logical / 2,
        1,
        f"{logical} physical",
        ha="center",
        va="center",
        color="white",
        fontsize=12,
    )
    right.text(
        logical / 2,
        0,
        f"{logical} physical",
        ha="center",
        va="center",
        color="white",
        fontsize=12,
    )
    right.text(
        logical + quadratized_aux / 2,
        0,
        f"+{quadratized_aux} auxiliary",
        ha="center",
        va="center",
        color=TEXT,
        fontsize=11,
    )
    right.set_title("(b) Encoding size")
    right.set_xlabel("Variables")
    right.set_yticks(y, ("Native cubic", "Quadratized"))
    right.set_xlim(0, 59)
    right.set_xticks((0, 10, 20, 30, 40, 50))
    _style_axis(right)

    figure.subplots_adjust(left=0.075, right=0.985, top=0.87, bottom=0.19, wspace=0.3)
    _save_figure(figure, output_stem)


def _box(
    axis: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    facecolor: str,
    edgecolor: str,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=1.4,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height * 0.66,
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=TEXT,
    )
    axis.text(
        x + width / 2,
        y + height * 0.34,
        body,
        ha="center",
        va="center",
        fontsize=10,
        color=TEXT,
        linespacing=1.15,
    )


def _arrow(
    axis: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = GRAY,
) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color=color,
            shrinkA=2,
            shrinkB=2,
        )
    )


def _plot_method_overview(output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(10.2, 2.7))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    boxes = (
        (
            0.01,
            "Public inputs",
            "IEEE 123-bus\n+ NREL ATB",
            PALE_BLUE,
            NAVY,
        ),
        (
            0.21,
            "Exact recourse",
            "8 scenarios\n+ held-out N-1",
            PALE_BLUE,
            NAVY,
        ),
        (
            0.41,
            "Cubic master",
            "33 decisions\nmaximum degree 3",
            PALE_GOLD,
            GOLD,
        ),
        (
            0.61,
            "Matched solvers",
            "Dirac-3\nMILP · L4 · QUBO",
            PALE_GREEN,
            GREEN,
        ),
        (
            0.81,
            "Common scoring",
            "unchanged portfolio\nfull-system recourse",
            PALE_BLUE,
            NAVY,
        ),
    )
    for x, title, body, facecolor, edgecolor in boxes:
        _box(axis, x, 0.34, 0.18, 0.42, title, body, facecolor, edgecolor)
    for x in (0.19, 0.39, 0.59, 0.79):
        _arrow(axis, (x, 0.55), (x + 0.02, 0.55))

    axis.text(
        0.5,
        0.15,
        "The sampled investment vector is decoded directly; repair never changes the selected portfolio.",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=TEXT,
    )

    figure.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
    _save_figure(figure, output_path)


def build_paper_figures(
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    *,
    phase3_root: Path | str = DEFAULT_PHASE3_ROOT,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, object]:
    """Build paper figures and return their paths."""

    output_dir = Path(output_dir)
    phase3_root = Path(phase3_root)
    sample_rows = _read_csv(SAMPLE_QUALITY_PATH, phase3_root)
    encoding_rows = _read_csv(ENCODING_PATH, phase3_root)

    if dry_run:
        return {
            "dry_run": True,
            "output_dir": str(output_dir),
            "files": list(OUTPUT_FILES),
        }

    existing = [output_dir / name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not overwrite:
        paths = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Refusing to overwrite generated paper figures: {paths}")

    output_dir.mkdir(parents=True, exist_ok=True)
    _configure_matplotlib()
    _plot_ground_state_and_encoding(
        sample_rows,
        encoding_rows,
        output_dir / "ground_state_and_encoding",
    )
    _plot_method_overview(output_dir / "method_overview")

    manifest = {
        "schema": "cmpo.phase3.paper_figures.v1",
        "generation_rule": (
            "Result values are read from selected CSV artifacts; raw results are "
            "never modified. The method overview is a schematic of the evaluated "
            "pipeline."
        ),
        "sources": [
            {
                "path": SAMPLE_QUALITY_PATH.as_posix(),
                "sha256": _sha256(_source_path(SAMPLE_QUALITY_PATH, phase3_root)),
                "role": "exact-ground-state recovery rates",
            },
            {
                "path": ENCODING_PATH.as_posix(),
                "sha256": _sha256(_source_path(ENCODING_PATH, phase3_root)),
                "role": "native and quadratized variable counts",
            },
        ],
    }
    (output_dir / "figure_sources.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "dry_run": False,
        "output_dir": str(output_dir),
        "files": list(OUTPUT_FILES),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate publication figures for the Phase 3 paper from selected "
            "result artifacts without modifying raw results."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory for generated figures "
            "(default: submission/paper/generated/figures)."
        ),
    )
    parser.add_argument(
        "--phase3-root",
        type=Path,
        default=DEFAULT_PHASE3_ROOT,
        help="Phase 3 result root containing irc_cmpo/ and sc_cmpo/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate figure inputs and report outputs without writing files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace previously generated paper figures.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = build_paper_figures(
        output_dir=args.output_dir,
        phase3_root=args.phase3_root,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
