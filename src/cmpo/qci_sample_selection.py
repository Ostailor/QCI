"""Offline QCi repeat sample selection for Phase 3 diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from cmpo.challenge_score import add_lexicographic_scores, add_weighted_scores
from cmpo.system_level_projection import project_sc_cmpo_payload


SELECTION_REASONS = (
    "best_by_qci_energy",
    "best_by_risk_adjusted_cost",
    "best_by_critical_ENS",
    "best_by_challenge_score",
    "median_by_challenge_score",
)

METRIC_COLUMNS = [
    "critical_energy_not_served_kwh",
    "energy_not_served_kwh",
    "max_fraction_customers_unserved_per_hour",
    "total_hours_critical_infrastructure_unserved",
    "total_critical_infrastructure_unserved_hours_proxy",
    "critical_load_served_fraction",
    "feasibility_after_repair",
    "risk_adjusted_cost",
    "expected_operating_cost",
    "runtime",
    "runtime_seconds",
    "time_to_good_solution",
    "qci_energy",
    "pre_repair_violation",
    "post_repair_violation",
    "pre_repair_violation_count",
    "post_repair_violation_count",
    "pre_repair_violation_magnitude",
    "post_repair_violation_magnitude",
]


def discover_qci_repeat_metric_paths(phase3_root: Path | str, *, include_non_public: bool = False) -> list[Path]:
    """Return decoded QCi repeat-metric CSVs under the Phase 3 result tree."""

    root = Path(phase3_root)
    public_paths = sorted((root / "public_benchmarks").glob("*/decoded/qci_repeat_metrics.csv"))
    if not include_non_public:
        return public_paths
    all_paths = sorted(root.glob("**/decoded/qci_repeat_metrics.csv"))
    return sorted(set(public_paths + all_paths))


def load_qci_repeat_metrics(paths: Iterable[Path | str]) -> pd.DataFrame:
    """Load decoded QCi repeat metrics and annotate each row with its source benchmark."""

    frames: list[pd.DataFrame] = []
    for item in paths:
        path = Path(item)
        try:
            frame = pd.read_csv(path)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            continue
        if frame.empty:
            continue
        frame = frame.copy()
        if "public_benchmarks" in path.parts:
            idx = path.parts.index("public_benchmarks")
            benchmark = path.parts[idx + 1]
        else:
            benchmark = path.parent.parent.name
        frame["source_qci_repeat_metrics_csv"] = str(path)
        frame["benchmark"] = benchmark
        if "dataset" not in frame.columns:
            frame["dataset"] = benchmark
        if "payload_name" not in frame.columns:
            frame["payload_name"] = frame.get("payload", "unknown_payload").astype(str).map(lambda value: Path(value).name)
        frame = _project_sc_cmpo_rows(frame)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _project_sc_cmpo_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Add challenge metrics to decoded SC-CMPO vectors before selection."""

    if "payload_schema" not in frame.columns or "decoded_variables" not in frame.columns:
        return frame
    result = frame.copy()
    payload_cache: dict[str, dict] = {}
    for index, row in result.iterrows():
        if not str(row.get("payload_schema", "")).startswith("cmpo.sc_cmpo"):
            continue
        payload_path = Path(str(row.get("payload", "")))
        if not payload_path.exists():
            continue
        try:
            payload = payload_cache.setdefault(
                str(payload_path), json.loads(payload_path.read_text(encoding="utf-8"))
            )
            decoded = json.loads(str(row["decoded_variables"]))
            if not isinstance(decoded, dict):
                continue
            projection = project_sc_cmpo_payload(payload, decoded)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        repaired = dict(projection["repaired_first_stage"])
        for scenario in projection["scenario_results"]:
            repaired.update(scenario["projected_recourse"])
        upgrade_cost = float(projection["upgrade_cost"])
        critical_ens = float(projection["critical_energy_not_served_kwh"])
        runtime = pd.to_numeric(pd.Series([row.get("runtime_seconds", row.get("runtime"))]), errors="coerce").iloc[0]
        feasible = bool(projection["feasibility_after_projection"])
        updates = {
            "critical_energy_not_served_kwh": critical_ens,
            "energy_not_served_kwh": critical_ens,
            "total_energy_not_served": critical_ens,
            "max_fraction_customers_unserved_per_hour": float(
                projection["max_fraction_customers_unserved_per_hour"]
            ),
            "total_hours_critical_infrastructure_unserved": float(
                projection["total_hours_critical_infrastructure_unserved"]
            ),
            "total_critical_infrastructure_unserved_hours_proxy": float(
                projection["total_hours_critical_infrastructure_unserved"]
            ),
            "critical_load_served_fraction": float(
                projection["critical_load_served_fraction"]
            ),
            "feasibility_after_repair": float(feasible),
            "risk_adjusted_cost": upgrade_cost,
            "expected_operating_cost": np.nan,
            "time_to_good_solution": float(runtime) if feasible and pd.notna(runtime) else -1.0,
            "pre_repair_violation": float(projection["pre_repair_violation"]),
            "post_repair_violation": float(projection["post_repair_violation"]),
            "repaired_solution": json.dumps(repaired, sort_keys=True, separators=(",", ":")),
            "selection_projection_scope": "SC-CMPO patch projection before overlap consensus",
            "risk_adjusted_cost_is_upgrade_only_proxy": True,
        }
        for column, value in updates.items():
            result.at[index, column] = value
    return result


def score_qci_samples(frame: pd.DataFrame) -> pd.DataFrame:
    """Add weighted and lexicographic challenge scores to QCi sample rows."""

    if frame.empty:
        return frame.copy()
    scored = add_weighted_scores(frame)
    scored = add_lexicographic_scores(scored)
    scored["challenge_score"] = pd.to_numeric(scored["lexicographic_challenge_score"], errors="coerce")
    scored["challenge_rank"] = pd.to_numeric(scored["lexicographic_challenge_rank"], errors="coerce")
    return scored


def _sort_for_reason(group: pd.DataFrame, reason: str) -> pd.DataFrame:
    sort_columns: list[str]
    ascending: list[bool]
    challenge_tiebreakers = [
        "feasibility_after_repair",
        "critical_energy_not_served_kwh",
        "total_hours_critical_infrastructure_unserved",
        "total_critical_infrastructure_unserved_hours_proxy",
        "max_fraction_customers_unserved_per_hour",
        "critical_load_served_fraction",
        "risk_adjusted_cost",
        "runtime",
        "qci_energy",
        "repeat",
        "sample_index",
    ]
    challenge_ascending = [False, True, True, True, True, False, True, True, True, True, True]

    if reason == "best_by_qci_energy":
        sort_columns = ["qci_energy"] + challenge_tiebreakers
        ascending = [True] + challenge_ascending
    elif reason == "best_by_risk_adjusted_cost":
        sort_columns = ["risk_adjusted_cost"] + challenge_tiebreakers
        ascending = [True] + challenge_ascending
    elif reason == "best_by_critical_ENS":
        sort_columns = ["critical_energy_not_served_kwh"] + challenge_tiebreakers
        ascending = [True] + challenge_ascending
    elif reason in {"best_by_challenge_score", "median_by_challenge_score"}:
        sort_columns = ["challenge_score", "weighted_challenge_score"] + challenge_tiebreakers
        ascending = [True, True] + challenge_ascending
    else:
        raise ValueError(f"Unknown QCi sample selection reason: {reason}")

    sort_frame = group.copy()
    for column, asc in zip(sort_columns, ascending):
        if column not in sort_frame.columns:
            sort_frame[column] = np.nan
        values = pd.to_numeric(sort_frame[column], errors="coerce")
        fill = np.inf if asc else -np.inf
        sort_frame[column] = values.fillna(fill)
    return sort_frame.sort_values(sort_columns, ascending=ascending, kind="mergesort")


def select_qci_samples(frame: pd.DataFrame) -> pd.DataFrame:
    """Select representative QCi repeat samples for every benchmark/payload."""

    scored = score_qci_samples(frame)
    if scored.empty:
        return scored

    selected_rows: list[pd.Series] = []
    group_columns = ["benchmark", "dataset", "payload_name"]
    for keys, group in scored.groupby(group_columns, sort=True, dropna=False):
        benchmark, dataset, payload_name = keys
        for reason in SELECTION_REASONS:
            ordered = _sort_for_reason(group, reason)
            if ordered.empty:
                continue
            if reason == "median_by_challenge_score":
                selected = ordered.iloc[len(ordered) // 2].copy()
                rank = len(ordered) // 2 + 1
            else:
                selected = ordered.iloc[0].copy()
                rank = 1
            selected["selection_reason"] = reason
            selected["selection_rank_within_payload"] = rank
            selected["selection_payload_sample_count"] = len(group)
            selected["selection_benchmark"] = benchmark
            selected["selection_dataset"] = dataset
            selected["selection_payload_name"] = payload_name
            selected_rows.append(selected)

    selected_frame = pd.DataFrame(selected_rows).reset_index(drop=True)
    preferred = [
        "selection_reason",
        "selection_benchmark",
        "selection_dataset",
        "selection_payload_name",
        "selection_rank_within_payload",
        "selection_payload_sample_count",
        "benchmark",
        "dataset",
        "payload_name",
        "scenario",
        "patch",
        "repeat",
        "sample_index",
        "job_id",
        "qci_energy",
        "challenge_score",
        "challenge_rank",
        "weighted_challenge_score",
        "lexicographic_challenge_rank",
        "raw_solution",
        "repaired_solution",
    ]
    remaining = [column for column in selected_frame.columns if column not in preferred]
    return selected_frame[[column for column in preferred if column in selected_frame.columns] + remaining]


def _first_metric(frame: pd.DataFrame, reason: str, metric: str) -> float:
    rows = frame[frame["selection_reason"].eq(reason)]
    if rows.empty or metric not in rows.columns:
        return float("nan")
    return float(pd.to_numeric(rows[metric], errors="coerce").iloc[0])


def summarize_qci_selection(selected: pd.DataFrame) -> pd.DataFrame:
    """Build payload-level selector effect summary."""

    if selected.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    group_columns = ["selection_benchmark", "selection_dataset", "selection_payload_name"]
    for keys, group in selected.groupby(group_columns, sort=True, dropna=False):
        benchmark, dataset, payload_name = keys
        energy_ens = _first_metric(group, "best_by_qci_energy", "critical_energy_not_served_kwh")
        challenge_ens = _first_metric(group, "best_by_challenge_score", "critical_energy_not_served_kwh")
        energy_max = _first_metric(group, "best_by_qci_energy", "max_fraction_customers_unserved_per_hour")
        challenge_max = _first_metric(group, "best_by_challenge_score", "max_fraction_customers_unserved_per_hour")
        energy_infra = _first_metric(
            group,
            "best_by_qci_energy",
            "total_critical_infrastructure_unserved_hours_proxy",
        )
        challenge_infra = _first_metric(
            group,
            "best_by_challenge_score",
            "total_critical_infrastructure_unserved_hours_proxy",
        )
        energy_served = _first_metric(group, "best_by_qci_energy", "critical_load_served_fraction")
        challenge_served = _first_metric(group, "best_by_challenge_score", "critical_load_served_fraction")
        energy_risk = _first_metric(group, "best_by_qci_energy", "risk_adjusted_cost")
        challenge_risk = _first_metric(group, "best_by_challenge_score", "risk_adjusted_cost")
        challenge_feasible = _first_metric(group, "best_by_challenge_score", "feasibility_after_repair")

        fail_reasons: list[str] = []
        if not np.isfinite(challenge_feasible) or challenge_feasible < 1.0:
            fail_reasons.append("infeasible_after_repair")
        if np.isfinite(challenge_ens) and challenge_ens > 1e-9:
            fail_reasons.append("critical_ENS_positive")
        if np.isfinite(challenge_infra) and challenge_infra > 0:
            fail_reasons.append("critical_infra_unserved_hours_positive")
        if np.isfinite(challenge_max) and challenge_max > 1e-9:
            fail_reasons.append("max_customers_unserved_positive")
        if np.isfinite(challenge_served) and challenge_served < 1.0 - 1e-9:
            fail_reasons.append("critical_load_not_fully_served")

        rows.append(
            {
                "benchmark": benchmark,
                "dataset": dataset,
                "payload_name": payload_name,
                "scenario": group["scenario"].dropna().iloc[0] if "scenario" in group and group["scenario"].notna().any() else "",
                "patch": group["patch"].dropna().iloc[0] if "patch" in group and group["patch"].notna().any() else "",
                "sample_count": int(group["selection_payload_sample_count"].max()),
                "energy_selector_critical_ENS": energy_ens,
                "challenge_selector_critical_ENS": challenge_ens,
                "critical_ENS_delta_challenge_minus_energy": challenge_ens - energy_ens,
                "challenge_improves_critical_ENS": bool(challenge_ens < energy_ens),
                "energy_selector_max_customers_unserved": energy_max,
                "challenge_selector_max_customers_unserved": challenge_max,
                "max_customers_unserved_delta_challenge_minus_energy": challenge_max - energy_max,
                "challenge_reduces_max_customers_unserved": bool(challenge_max < energy_max),
                "energy_selector_infra_hours": energy_infra,
                "challenge_selector_infra_hours": challenge_infra,
                "infra_hours_delta_challenge_minus_energy": challenge_infra - energy_infra,
                "energy_selector_critical_load_served": energy_served,
                "challenge_selector_critical_load_served": challenge_served,
                "critical_load_served_delta_challenge_minus_energy": challenge_served - energy_served,
                "energy_selector_risk_adjusted_cost": energy_risk,
                "challenge_selector_risk_adjusted_cost": challenge_risk,
                "risk_adjusted_cost_delta_challenge_minus_energy": challenge_risk - energy_risk,
                "best_selector_still_fails": bool(fail_reasons),
                "best_selector_failure_reasons": "|".join(fail_reasons),
            }
        )
    return pd.DataFrame(rows)


def selection_effect_markdown(selected: pd.DataFrame, summary: pd.DataFrame) -> str:
    """Render a concise Markdown narrative for the QCi selector effect."""

    if selected.empty or summary.empty:
        return "# QCi Selection Effect\n\n_No QCi selected samples were available._\n"

    lines = [
        "# QCi Selection Effect",
        "",
        "This is a derived offline analysis over existing decoded QCi repeats. No new QCi jobs were run.",
        "",
        "## Overall Answers",
        "",
    ]

    total_payloads = len(summary)
    ens_improved = int(summary["challenge_improves_critical_ENS"].sum())
    max_improved = int(summary["challenge_reduces_max_customers_unserved"].sum())
    still_fail = int(summary["best_selector_still_fails"].sum())
    ens_delta = float(summary["critical_ENS_delta_challenge_minus_energy"].sum())
    max_delta = float(summary["max_customers_unserved_delta_challenge_minus_energy"].sum())
    risk_delta = float(summary["risk_adjusted_cost_delta_challenge_minus_energy"].sum())

    lines.append(
        f"- Does choosing by challenge_score improve critical ENS versus raw QCi energy? "
        f"{'YES' if ens_improved > 0 and ens_delta < 0 else 'NO'}: improved on {ens_improved}/{total_payloads} payloads, "
        f"with aggregate critical ENS delta {ens_delta:.6g} kWh."
    )
    lines.append(
        f"- Does choosing by challenge_score reduce max customers unserved? "
        f"{'YES' if max_improved > 0 and max_delta < 0 else 'NO'}: reduced on {max_improved}/{total_payloads} payloads, "
        f"with aggregate max-unserved delta {max_delta:.6g}."
    )
    lines.append(
        f"- Does QCi look better under the challenge-aligned selector? "
        f"{'YES' if ens_delta < 0 or max_delta < 0 else 'NO'} relative to raw-energy selection, "
        f"but risk-adjusted cost changes by {risk_delta:.6g}; compare against baselines separately."
    )
    lines.append(
        f"- Which payloads still fail even under the best selector? {still_fail}/{total_payloads} payloads have at least one "
        "positive critical ENS, critical infrastructure outage, positive max-unserved, infeasibility, or not-fully-served critical load condition."
    )
    lines.append("")

    by_dataset = (
        summary.groupby(["benchmark", "dataset"], dropna=False)
        .agg(
            payload_count=("payload_name", "count"),
            ens_improved_payloads=("challenge_improves_critical_ENS", "sum"),
            max_unserved_reduced_payloads=("challenge_reduces_max_customers_unserved", "sum"),
            critical_ENS_delta=("critical_ENS_delta_challenge_minus_energy", "sum"),
            max_unserved_delta=("max_customers_unserved_delta_challenge_minus_energy", "sum"),
            risk_cost_delta=("risk_adjusted_cost_delta_challenge_minus_energy", "sum"),
            still_failing_payloads=("best_selector_still_fails", "sum"),
        )
        .reset_index()
    )
    lines.extend(["## Dataset Summary", ""])
    lines.append(_markdown_table(by_dataset))
    lines.append("")

    failures = summary[summary["best_selector_still_fails"]].copy()
    failures = failures.sort_values(
        [
            "challenge_selector_critical_ENS",
            "challenge_selector_max_customers_unserved",
            "challenge_selector_risk_adjusted_cost",
        ],
        ascending=[False, False, False],
    ).head(25)
    lines.extend(["## Payloads Still Failing Under Best Challenge Selector", ""])
    if failures.empty:
        lines.append("_No payloads fail under the best challenge selector._")
    else:
        display_columns = [
            "benchmark",
            "dataset",
            "payload_name",
            "challenge_selector_critical_ENS",
            "challenge_selector_max_customers_unserved",
            "challenge_selector_infra_hours",
            "challenge_selector_critical_load_served",
            "best_selector_failure_reasons",
        ]
        lines.append(_markdown_table(failures[display_columns]))
    lines.append("")
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows available._"
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_qci_selection_outputs(
    selected: pd.DataFrame,
    summary: pd.DataFrame,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write selected samples, payload summary, and narrative effect markdown."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "selected_samples_csv": out_dir / "qci_selected_samples.csv",
        "selection_summary_csv": out_dir / "qci_selection_summary.csv",
        "selection_effect_md": out_dir / "qci_selection_effect.md",
    }
    selected.to_csv(paths["selected_samples_csv"], index=False)
    summary.to_csv(paths["selection_summary_csv"], index=False)
    paths["selection_effect_md"].write_text(selection_effect_markdown(selected, summary), encoding="utf-8")
    return paths
