"""Small statistical summaries for Phase 3 result comparisons."""

from __future__ import annotations

from itertools import combinations

import pandas as pd


def pairwise_method_deltas(frame: pd.DataFrame, metric: str = "expected_cost_component") -> pd.DataFrame:
    """Return paired median deltas for every method pair by scenario/patch/repeat."""

    if frame.empty or metric not in frame.columns:
        return pd.DataFrame()
    key_columns = ["dataset", "scenario", "patch", "repeat"]
    rows = []
    for dataset, group in frame.groupby("dataset", sort=True):
        methods = sorted(group["method_name"].unique())
        for left, right in combinations(methods, 2):
            left_frame = group[group["method_name"] == left][key_columns + [metric]]
            right_frame = group[group["method_name"] == right][key_columns + [metric]]
            merged = left_frame.merge(right_frame, on=key_columns, suffixes=("_left", "_right"))
            if merged.empty:
                continue
            delta = merged[f"{metric}_left"] - merged[f"{metric}_right"]
            rows.append(
                {
                    "dataset": dataset,
                    "left_method": left,
                    "right_method": right,
                    "metric": metric,
                    "paired_count": int(len(delta)),
                    "median_delta_left_minus_right": float(delta.median()),
                    "mean_delta_left_minus_right": float(delta.mean()),
                    "left_better_fraction": float((delta < 0).mean()),
                }
            )
    return pd.DataFrame(rows)
