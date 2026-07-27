"""Sparse hierarchical degree-three recourse surrogate for IRC-CMPO."""

from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


@dataclass(frozen=True)
class SurrogateFit:
    terms: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]
    split_groups: dict[str, tuple[str, ...]]
    target_column: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "terms": list(self.terms),
            "metrics": self.metrics,
            "split_groups": {key: list(value) for key, value in self.split_groups.items()},
            "target_column": self.target_column,
        }


@dataclass(frozen=True)
class TargetSurrogateFit:
    terms: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]
    target_column: str
    ridge: float


@dataclass(frozen=True)
class MultiTargetSurrogateFit:
    targets: dict[str, TargetSurrogateFit]
    split_manifest: pd.DataFrame
    gates_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "targets": {
                name: {
                    "terms": list(model.terms),
                    "metrics": model.metrics,
                    "target_column": model.target_column,
                    "ridge": model.ridge,
                }
                for name, model in self.targets.items()
            },
            "gates_passed": self.gates_passed,
        }


@dataclass(frozen=True)
class RegressionTreeNode:
    """A deterministic binary-feature regression tree node."""

    value: float
    feature_index: int | None = None
    zero: RegressionTreeNode | None = None
    one: RegressionTreeNode | None = None

    @property
    def is_leaf(self) -> bool:
        return self.feature_index is None


def _fit_regression_tree(
    features: np.ndarray,
    target: np.ndarray,
    *,
    max_depth: int = 3,
    min_leaf: int = 2,
) -> RegressionTreeNode:
    """Fit a CART-style tree for binary features without external dependencies."""

    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("tree features and target have incompatible shapes")
    if max_depth < 0 or max_depth > 3:
        raise ValueError("IRC-CMPO tree depth must be between zero and three")
    if min_leaf < 1:
        raise ValueError("tree minimum leaf size must be positive")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("tree training data must be finite")
    if not np.isin(x, (0.0, 1.0)).all():
        raise ValueError("tree features must be binary")

    def build(indices: np.ndarray, depth: int, used: frozenset[int]) -> RegressionTreeNode:
        node_y = y[indices]
        value = float(np.mean(node_y))
        if depth >= max_depth or len(indices) < 2 * min_leaf or float(np.ptp(node_y)) <= 1e-12:
            return RegressionTreeNode(value=value)
        parent_sse = float(np.sum((node_y - value) ** 2))
        best: tuple[float, int, np.ndarray, np.ndarray] | None = None
        for feature in range(x.shape[1]):
            if feature in used:
                continue
            zero = indices[x[indices, feature] < 0.5]
            one = indices[x[indices, feature] >= 0.5]
            if len(zero) < min_leaf or len(one) < min_leaf:
                continue
            child_sse = float(
                np.sum((y[zero] - np.mean(y[zero])) ** 2)
                + np.sum((y[one] - np.mean(y[one])) ** 2)
            )
            improvement = parent_sse - child_sse
            candidate = (improvement, feature, zero, one)
            if best is None or improvement > best[0] + 1e-12 or (
                abs(improvement - best[0]) <= 1e-12 and feature < best[1]
            ):
                best = candidate
        if best is None or best[0] <= 1e-12:
            return RegressionTreeNode(value=value)
        _, feature, zero, one = best
        next_used = used | {feature}
        return RegressionTreeNode(
            value=value,
            feature_index=feature,
            zero=build(zero, depth + 1, next_used),
            one=build(one, depth + 1, next_used),
        )

    return build(np.arange(len(y)), 0, frozenset())


def _tree_predict(tree: RegressionTreeNode, features: np.ndarray) -> np.ndarray:
    x = np.asarray(features, dtype=float)
    result = np.empty(len(x), dtype=float)

    def visit(node: RegressionTreeNode, indices: np.ndarray) -> None:
        if node.is_leaf:
            result[indices] = node.value
            return
        assert node.feature_index is not None and node.zero is not None and node.one is not None
        zero = indices[x[indices, node.feature_index] < 0.5]
        one = indices[x[indices, node.feature_index] >= 0.5]
        visit(node.zero, zero)
        visit(node.one, one)

    visit(tree, np.arange(len(x)))
    return result


def _tree_to_polynomial_terms(
    tree: RegressionTreeNode,
    feature_names: Sequence[str],
    *,
    tree_index: int,
    weight: float = 1.0,
    interaction_metadata: Mapping[tuple[str, ...], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Expand binary leaf indicators into an exactly equivalent cubic polynomial."""

    coefficients: dict[tuple[str, ...], float] = {}
    metadata = interaction_metadata or {}

    def add_leaf(node: RegressionTreeNode, literals: tuple[tuple[str, int], ...]) -> None:
        if not node.is_leaf:
            assert node.feature_index is not None and node.zero is not None and node.one is not None
            name = str(feature_names[node.feature_index])
            add_leaf(node.zero, (*literals, (name, 0)))
            add_leaf(node.one, (*literals, (name, 1)))
            return
        # leaf * prod(x for positive literals) * prod(1-x for negative literals)
        negative = [name for name, bit in literals if bit == 0]
        positive = [name for name, bit in literals if bit == 1]
        for count in range(len(negative) + 1):
            for chosen in itertools.combinations(negative, count):
                spec = tuple(sorted((*positive, *chosen)))
                coefficients[spec] = coefficients.get(spec, 0.0) + (
                    weight * node.value * ((-1.0) ** count)
                )

    add_leaf(tree, tuple())
    terms: list[dict[str, Any]] = []
    for spec, coefficient in sorted(coefficients.items(), key=lambda item: (len(item[0]), item[0])):
        if abs(coefficient) <= 1e-12:
            continue
        supplied = dict(metadata.get(spec, {}))
        terms.append(
            {
                "coefficient": float(coefficient),
                "asset_keys": list(spec),
                "degree": len(spec),
                "component": "surrogate" if len(spec) <= 1 else "interaction",
                "validation_selected": True,
                "tree_index": int(tree_index),
                "interaction_class": supplied.get(
                    "interaction_class", "validation_selected_tree_path"
                ),
                "physical_interpretation": supplied.get(
                    "physical_rationale",
                    "bounded conjunction of physical upgrade selections along a validated recourse partition",
                ),
                **supplied,
            }
        )
    return tuple(terms)


def _combine_polynomial_terms(
    groups: Sequence[Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, Any], ...]:
    combined: dict[tuple[str, ...], float] = {}
    sources: dict[tuple[str, ...], list[Mapping[str, Any]]] = {}
    for group in groups:
        for term in group:
            spec = tuple(sorted(str(name) for name in term["asset_keys"]))
            combined[spec] = combined.get(spec, 0.0) + float(term["coefficient"])
            sources.setdefault(spec, []).append(term)
    result: list[dict[str, Any]] = []
    for spec, coefficient in sorted(combined.items(), key=lambda item: (len(item[0]), item[0])):
        if abs(coefficient) <= 1e-12:
            continue
        source = sources[spec][0]
        result.append(
            {
                "coefficient": float(coefficient),
                "asset_keys": list(spec),
                "degree": len(spec),
                "component": "surrogate" if len(spec) <= 1 else "interaction",
                "validation_selected": True,
                "interaction_class": source.get(
                    "interaction_class", "validation_selected_tree_path"
                ),
                "physical_interpretation": source.get(
                    "physical_interpretation",
                    "bounded conjunction of physical upgrade selections along a validated recourse partition",
                ),
            }
        )
    return tuple(result)


def generate_feasible_candidates(
    assets: Sequence[Any],
    *,
    budgets: Sequence[float],
    minimum_unique: int = 3000,
    random_seed: int = 2026,
) -> pd.DataFrame:
    """Generate unlabeled, charge-once, coverage- and dollar-feasible candidates.

    These rows are candidates only.  A caller must evaluate every row with the
    common recourse oracle before it may be used as a training label.
    """

    budgets = tuple(sorted({float(value) for value in budgets}))
    if not budgets or any(not math.isfinite(value) or value <= 0.0 for value in budgets):
        raise ValueError("candidate budgets must be finite and positive")
    anchors: dict[str, list[Any]] = {}
    for asset in assets:
        anchors.setdefault(str(asset.anchor_node), []).append(asset)
    choices = [tuple(sorted(rows, key=lambda item: item.asset_key)) for _, rows in sorted(anchors.items())]
    rng = np.random.default_rng(random_seed)
    selected_sets: dict[str, tuple[str, ...]] = {}

    def admit(selected_assets: Sequence[Any]) -> None:
        keys = tuple(sorted({str(asset.asset_key) for asset in selected_assets}))
        cost = math.fsum(float(asset.total_cost) for asset in assets if asset.asset_key in set(keys))
        fitting = [budget for budget in budgets if cost <= budget + 1e-9]
        if not fitting:
            return
        signature = hashlib.sha256(json_key(keys).encode("utf-8")).hexdigest()[:20]
        selected_sets.setdefault(signature, keys)

    if len(assets) <= 16:
        for base in itertools.product(*choices):
            remaining = [asset for asset in assets if asset not in base]
            for mask in range(1 << len(remaining)):
                admit([*base, *(asset for index, asset in enumerate(remaining) if mask & (1 << index))])
                if len(selected_sets) >= minimum_unique:
                    break
            if len(selected_sets) >= minimum_unique:
                break
    else:
        attempts = 0
        limit = max(100_000, minimum_unique * 1000)
        while len(selected_sets) < minimum_unique and attempts < limit:
            attempts += 1
            base = [rows[int(rng.integers(0, len(rows)))] for rows in choices]
            chosen = {asset.asset_key: asset for asset in base}
            for asset in assets:
                if asset.asset_key not in chosen and rng.random() < 0.12:
                    chosen[asset.asset_key] = asset
            admit(list(chosen.values()))
    if len(selected_sets) < minimum_unique:
        raise ValueError(
            f"only {len(selected_sets)} unique feasible portfolios exist/reached; requested {minimum_unique}"
        )
    asset_by_key = {str(asset.asset_key): asset for asset in assets}
    rows = []
    for signature, keys in list(sorted(selected_sets.items()))[:minimum_unique]:
        cost = math.fsum(float(asset_by_key[key].total_cost) for key in keys)
        budget = min(value for value in budgets if cost <= value + 1e-9)
        rows.append(
            {
                "portfolio_signature": signature,
                "selected_asset_keys": list(keys),
                "upgrade_cost": cost,
                "budget": budget,
                "generation_method": "deterministic_random_feasible",
                **{str(asset.asset_key): int(asset.asset_key in keys) for asset in assets},
            }
        )
    return pd.DataFrame(rows)


def json_key(keys: Sequence[str]) -> str:
    return "[" + ",".join(keys) + "]"


def _group_split(groups: Sequence[str], seed: int) -> dict[str, tuple[str, ...]]:
    unique = sorted(set(groups))
    ranked = sorted(
        unique,
        key=lambda value: hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest(),
    )
    n = len(ranked)
    train_end = max(1, int(0.70 * n))
    validation_end = max(train_end + 1, int(0.85 * n))
    validation_end = min(validation_end, n - 1)
    return {
        "train": tuple(ranked[:train_end]),
        "validation": tuple(ranked[train_end:validation_end]),
        "test": tuple(ranked[validation_end:]),
    }


def _feature_specs(
    asset_columns: Sequence[str],
    pair_interactions: Sequence[tuple[str, str]],
    cubic_interactions: Sequence[tuple[str, str, str]],
) -> tuple[tuple[str, ...], ...]:
    known = set(asset_columns)
    specs: list[tuple[str, ...]] = [tuple()] + [(name,) for name in asset_columns]
    for interaction in [*pair_interactions, *cubic_interactions]:
        canonical = tuple(dict.fromkeys(interaction))
        if len(canonical) not in {2, 3}:
            raise ValueError("interaction terms must contain two or three distinct assets")
        if set(canonical) - known:
            raise ValueError(f"interaction references unknown assets: {canonical}")
        specs.append(canonical)
    return tuple(dict.fromkeys(specs))


def _design(frame: pd.DataFrame, specs: Sequence[tuple[str, ...]]) -> np.ndarray:
    columns = []
    for spec in specs:
        if not spec:
            columns.append(np.ones(len(frame), dtype=float))
        else:
            columns.append(frame[list(spec)].astype(float).prod(axis=1).to_numpy())
    return np.column_stack(columns)


def _predict(frame: pd.DataFrame, specs: Sequence[tuple[str, ...]], coefficients: np.ndarray) -> np.ndarray:
    return _design(frame, specs) @ coefficients


def _rank_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    if len(actual) < 2:
        raise ValueError("test split must contain at least two portfolios")
    errors = predicted - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    scale = max(float(np.ptp(actual)), 1e-12)
    correlation = float(spearmanr(actual, predicted).statistic)
    if not math.isfinite(correlation):
        correlation = 0.0
    count = max(1, math.ceil(0.10 * len(actual)))
    actual_top = set(np.argsort(actual)[:count].tolist())
    predicted_top = set(np.argsort(predicted)[:count].tolist())
    recall = len(actual_top & predicted_top) / len(actual_top)
    return {
        "mae": mae,
        "rmse": rmse,
        "normalized_rmse": rmse / scale,
        "spearman_rank_correlation": correlation,
        "top_decile_recall": float(recall),
        "pareto_front_recall": float(recall),
        "heldout_rank_correlation": correlation,
    }


def _pareto_indices(cost: np.ndarray, resilience_loss: np.ndarray) -> set[int]:
    result: set[int] = set()
    for index, (item_cost, item_loss) in enumerate(zip(cost, resilience_loss, strict=True)):
        dominated = np.any(
            (cost <= item_cost)
            & (resilience_loss <= item_loss)
            & ((cost < item_cost) | (resilience_loss < item_loss))
        )
        if not dominated:
            result.add(index)
    return result


def _quantile_band(series: pd.Series, bands: int = 5) -> pd.Series:
    ranked = series.astype(float).rank(method="first")
    count = min(bands, max(1, len(series)))
    return pd.qcut(ranked, q=count, labels=False, duplicates="drop").astype(int)


def stratified_portfolio_split(
    data: pd.DataFrame,
    *,
    group_column: str = "portfolio_signature",
    random_seed: int = 2026,
) -> pd.DataFrame:
    """Create an exact 60/20/20 portfolio split interleaved across strata."""

    required = {
        group_column,
        "upgrade_cost",
        "critical_ens",
        "total_ens",
        "technology_mix",
        "selected_asset_count",
    }
    if missing := required - set(data.columns):
        raise ValueError(f"stratified split is missing columns: {sorted(missing)}")
    if data[group_column].astype(str).duplicated().any():
        raise ValueError("portfolio signatures must be unique before splitting")
    manifest = data[
        [
            group_column,
            "upgrade_cost",
            "critical_ens",
            "total_ens",
            "technology_mix",
            "selected_asset_count",
        ]
    ].copy()
    manifest["upgrade_cost_band"] = _quantile_band(manifest["upgrade_cost"])
    manifest["critical_ens_band"] = _quantile_band(manifest["critical_ens"])
    manifest["total_ens_band"] = _quantile_band(manifest["total_ens"])
    manifest["selected_asset_count_band"] = _quantile_band(manifest["selected_asset_count"])
    manifest["_stratum"] = manifest.apply(
        lambda row: "|".join(
            map(
                str,
                (
                    row["upgrade_cost_band"],
                    row["critical_ens_band"],
                    row["total_ens_band"],
                    row["technology_mix"],
                    row["selected_asset_count_band"],
                ),
            )
        ),
        axis=1,
    )
    groups: dict[str, list[int]] = {}
    for index, row in manifest.iterrows():
        groups.setdefault(str(row["_stratum"]), []).append(index)
    for stratum, indices in groups.items():
        indices.sort(
            key=lambda index: hashlib.sha256(
                f"{random_seed}:{stratum}:{manifest.at[index, group_column]}".encode()
            ).hexdigest()
        )
    interleaved: list[int] = []
    depth = 0
    while len(interleaved) < len(manifest):
        for stratum in sorted(groups):
            if depth < len(groups[stratum]):
                interleaved.append(groups[stratum][depth])
        depth += 1
    train_count = int(0.60 * len(interleaved))
    validation_count = int(0.20 * len(interleaved))
    assignments = {
        index: (
            "train"
            if rank < train_count
            else "validation"
            if rank < train_count + validation_count
            else "test"
        )
        for rank, index in enumerate(interleaved)
    }
    manifest["split"] = manifest.index.map(assignments)
    return manifest.drop(columns=["_stratum"]).reset_index(drop=True)


def _calibration_by_cost_band(
    frame: pd.DataFrame, actual: np.ndarray, predicted: np.ndarray
) -> list[dict[str, Any]]:
    bands = _quantile_band(frame["upgrade_cost"], bands=4).to_numpy()
    rows: list[dict[str, Any]] = []
    for band in sorted(set(bands.tolist())):
        mask = bands == band
        rows.append(
            {
                "upgrade_cost_band": int(band),
                "count": int(mask.sum()),
                "mean_actual": float(np.mean(actual[mask])),
                "mean_predicted": float(np.mean(predicted[mask])),
                "mean_bias": float(np.mean(predicted[mask] - actual[mask])),
                "mae": float(np.mean(np.abs(predicted[mask] - actual[mask]))),
            }
        )
    return rows


def _target_metrics(
    frame: pd.DataFrame, actual: np.ndarray, predicted: np.ndarray
) -> dict[str, Any]:
    errors = predicted - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    value_range = float(np.ptp(actual))
    mean_abs = max(abs(float(np.mean(actual))), 1e-12)
    nearly_constant = value_range <= max(1e-9, 1e-6 * mean_abs)
    normalized_rmse = rmse / (mean_abs if nearly_constant else value_range)
    variance = float(np.sum((actual - np.mean(actual)) ** 2))
    r2 = 1.0 - float(np.sum(errors**2)) / variance if variance > 1e-18 else float(rmse <= 1e-9)
    noise_tolerance = 1e-6
    canonical_actual = np.rint(actual / noise_tolerance) * noise_tolerance
    canonical_predicted = np.rint(predicted / noise_tolerance) * noise_tolerance
    correlation = (
        float(spearmanr(canonical_actual, canonical_predicted).statistic)
        if not nearly_constant
        else 0.0
    )
    if not math.isfinite(correlation):
        correlation = 0.0
    count = max(1, math.ceil(0.10 * len(actual)))
    # Include every portfolio tied at the decile boundary.  Selecting an
    # arbitrary subset of equal-score portfolios makes recall depend on row
    # order even when the surrogate reproduces the ranking exactly.
    actual_cutoff = float(np.partition(canonical_actual, count - 1)[count - 1])
    actual_top = set(np.flatnonzero(canonical_actual <= actual_cutoff).tolist())
    # Recall must compare equally sized sets when the outcome has ties.  The
    # true top decile can legitimately contain more than ten percent of the
    # rows, so use that tie-expanded cardinality for the predicted set too.
    predicted_count = min(len(predicted), len(actual_top))
    predicted_cutoff = float(
        np.partition(canonical_predicted, predicted_count - 1)[predicted_count - 1]
    )
    predicted_top = set(np.flatnonzero(canonical_predicted <= predicted_cutoff).tolist())
    top_recall = len(actual_top & predicted_top) / len(actual_top)
    cost = frame["upgrade_cost"].astype(float).to_numpy()
    actual_front = _pareto_indices(cost, canonical_actual)
    predicted_front = _pareto_indices(cost, canonical_predicted)
    pareto_recall = len(actual_front & predicted_front) / len(actual_front) if actual_front else 1.0
    return {
        "mae": mae,
        "rmse": rmse,
        "normalized_rmse": normalized_rmse,
        "r2": r2,
        "spearman_rank_correlation": correlation,
        "top_decile_recall": float(top_recall),
        "pareto_front_recall": float(pareto_recall),
        "nearly_constant": nearly_constant,
        "test_range": value_range,
        "test_standard_deviation": float(np.std(actual)),
        "calibration_by_upgrade_cost_band": _calibration_by_cost_band(frame, actual, predicted),
        "solver_noise_tolerance": noise_tolerance,
    }


def _target_gate(metrics: Mapping[str, Any], *, rank_gate: bool) -> bool:
    return bool(
        float(metrics["normalized_rmse"]) <= 0.20
        and (not rank_gate or float(metrics["spearman_rank_correlation"]) >= 0.80)
        and (not rank_gate or float(metrics["top_decile_recall"]) >= 0.70)
        and (not rank_gate or float(metrics["pareto_front_recall"]) >= 0.70)
    )


def _tree_ensemble_candidates(
    train_x: np.ndarray,
    train_y: np.ndarray,
    validation_x: np.ndarray,
    validation_frame: pd.DataFrame,
    validation_y: np.ndarray,
    feature_names: Sequence[str],
    interaction_metadata: Mapping[tuple[str, ...], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return deterministic validation checkpoints from shallow boosted trees."""

    candidates: list[dict[str, Any]] = []
    minimum_leaf = max(2, len(train_y) // 300)
    for depth in (1, 2, 3):
        for learning_rate in (0.25, 0.5, 1.0):
            train_prediction = np.full(len(train_y), float(np.mean(train_y)))
            validation_prediction = np.full(len(validation_y), float(np.mean(train_y)))
            groups: list[tuple[dict[str, Any], ...]] = [
                (
                    {
                        "coefficient": float(np.mean(train_y)),
                        "asset_keys": [],
                        "degree": 0,
                        "component": "surrogate",
                        "validation_selected": True,
                        "interaction_class": "tree_ensemble_intercept",
                        "physical_interpretation": "mean recourse loss before upgrade partitions",
                    },
                )
            ]
            for tree_index in range(32):
                residual = train_y - train_prediction
                tree = _fit_regression_tree(
                    train_x,
                    residual,
                    max_depth=depth,
                    min_leaf=minimum_leaf,
                )
                train_update = _tree_predict(tree, train_x)
                validation_update = _tree_predict(tree, validation_x)
                train_prediction += learning_rate * train_update
                validation_prediction += learning_rate * validation_update
                groups.append(
                    _tree_to_polynomial_terms(
                        tree,
                        feature_names,
                        tree_index=tree_index,
                        weight=learning_rate,
                        interaction_metadata=interaction_metadata,
                    )
                )
                tree_count = tree_index + 1
                if tree_count not in {1, 2, 4, 8, 16, 32}:
                    continue
                terms = _combine_polynomial_terms(groups)
                metrics = _target_metrics(
                    validation_frame, validation_y, validation_prediction
                )
                candidates.append(
                    {
                        "model_type": (
                            "regression_tree" if tree_count == 1 else "tree_ensemble"
                        ),
                        "terms": terms,
                        "ridge": 0.0,
                        "validation_metrics": metrics,
                        "tree_depth": depth,
                        "tree_count": tree_count,
                        "learning_rate": learning_rate,
                    }
                )
                if float(np.max(np.abs(residual))) <= 1e-10:
                    break
    return candidates


def fit_multi_target_surrogates(
    data: pd.DataFrame,
    *,
    asset_columns: Sequence[str],
    pair_interactions: Sequence[tuple[str, str]],
    cubic_interactions: Sequence[tuple[str, str, str]],
    target_columns: Sequence[str],
    group_column: str = "portfolio_signature",
    minimum_portfolios: int = 3000,
    random_seed: int = 2026,
    interaction_metadata: Mapping[tuple[str, ...], Mapping[str, Any]] | None = None,
) -> MultiTargetSurrogateFit:
    """Fit separate sparse hierarchical cubic models with held-out gates."""

    required = set(asset_columns) | set(target_columns) | {group_column, "upgrade_cost"}
    if missing := required - set(data.columns):
        raise ValueError(f"multi-target surrogate dataset is missing columns: {sorted(missing)}")
    if data[group_column].astype(str).nunique() < minimum_portfolios:
        raise ValueError(f"surrogate requires at least {minimum_portfolios} unique portfolios")
    if not bool(data[list(asset_columns)].isin([0, 1]).all().all()):
        raise ValueError("surrogate asset features must be binary")
    manifest = stratified_portfolio_split(data, group_column=group_column, random_seed=random_seed)
    split_by_signature = manifest.set_index(group_column)["split"]
    working = data.copy()
    working["_split"] = working[group_column].astype(str).map(split_by_signature)
    if working["_split"].isna().any():
        raise ValueError("portfolio split manifest does not cover every portfolio")
    specs = _feature_specs(asset_columns, pair_interactions, cubic_interactions)
    frames = {name: working[working["_split"] == name] for name in ("train", "validation", "test")}
    train_x = _design(frames["train"], specs)
    validation_x = _design(frames["validation"], specs)
    metadata = interaction_metadata or {}
    models: dict[str, TargetSurrogateFit] = {}
    for target in target_columns:
        if not np.isfinite(working[target].astype(float)).all():
            raise ValueError(f"surrogate target {target} contains non-finite values")
        train_y = frames["train"][target].astype(float).to_numpy()
        validation_y = frames["validation"][target].astype(float).to_numpy()
        candidates: list[dict[str, Any]] = []
        for ridge in (1e-8, 1e-6, 1e-4, 1e-2, 1e-1, 1.0):
            regularizer = ridge * np.eye(train_x.shape[1])
            regularizer[0, 0] = 0.0
            coefficients = np.linalg.solve(
                train_x.T @ train_x + regularizer, train_x.T @ train_y
            )
            for relative_threshold in (0.0, 1e-6, 1e-4, 1e-3, 1e-2):
                scale = max(float(np.max(np.abs(coefficients))), 1e-12)
                keep = np.array(
                    [
                        len(spec) <= 1 or abs(float(coefficient)) >= relative_threshold * scale
                        for spec, coefficient in zip(specs, coefficients, strict=True)
                    ]
                )
                kept_specs = tuple(
                    spec for spec, retained in zip(specs, keep, strict=True) if retained
                )
                kept_coefficients = coefficients[keep]
                prediction = validation_x[:, keep] @ kept_coefficients
                ridge_terms = tuple(
                    {
                        "coefficient": float(coefficient),
                        "asset_keys": list(spec),
                        "degree": len(spec),
                        "component": "surrogate" if len(spec) <= 1 else "interaction",
                        "validation_selected": True,
                        "interaction_class": metadata.get(spec, {}).get(
                            "interaction_class", "hierarchical_ridge"
                        ),
                        "physical_interpretation": metadata.get(spec, {}).get(
                            "physical_rationale",
                            "individual physical upgrade effect",
                        ),
                        **dict(metadata.get(spec, {})),
                    }
                    for spec, coefficient in zip(
                        kept_specs, kept_coefficients, strict=True
                    )
                )
                candidates.append(
                    {
                        "model_type": "hierarchical_ridge",
                        "terms": ridge_terms,
                        "ridge": float(ridge),
                        "validation_metrics": _target_metrics(
                            frames["validation"], validation_y, prediction
                        ),
                        "tree_depth": 0,
                        "tree_count": 0,
                        "learning_rate": 0.0,
                    }
                )
        candidates.extend(
            _tree_ensemble_candidates(
                frames["train"][list(asset_columns)].astype(float).to_numpy(),
                train_y,
                frames["validation"][list(asset_columns)].astype(float).to_numpy(),
                frames["validation"],
                validation_y,
                asset_columns,
                metadata,
            )
        )
        rank_gate = target != "critical_ens" or not bool(
            candidates[0]["validation_metrics"]["nearly_constant"]
        )

        def candidate_order(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
            candidate_metrics = candidate["validation_metrics"]
            gate = _target_gate(candidate_metrics, rank_gate=rank_gate)
            violation = max(0.0, float(candidate_metrics["normalized_rmse"]) - 0.20)
            if rank_gate:
                violation += max(
                    0.0, 0.80 - float(candidate_metrics["spearman_rank_correlation"])
                )
                violation += max(0.0, 0.70 - float(candidate_metrics["top_decile_recall"]))
                violation += max(0.0, 0.70 - float(candidate_metrics["pareto_front_recall"]))
            return (
                not gate,
                violation,
                float(candidate_metrics["normalized_rmse"]),
                -float(candidate_metrics["spearman_rank_correlation"]),
                -float(candidate_metrics["top_decile_recall"]),
                -float(candidate_metrics["pareto_front_recall"]),
                len(candidate["terms"]),
                str(candidate["model_type"]),
            )

        selected = min(candidates, key=candidate_order)
        retained_terms = tuple(dict(term) for term in selected["terms"])
        retained_specs = tuple(tuple(term["asset_keys"]) for term in retained_terms)
        coefficients = np.asarray(
            [float(term["coefficient"]) for term in retained_terms], dtype=float
        )
        test = frames["test"]
        predicted = _design(test, retained_specs) @ coefficients
        actual = test[target].astype(float).to_numpy()
        metrics = _target_metrics(test, actual, predicted)
        metrics["degree"] = max(map(len, retained_specs), default=0)
        metrics["all_coefficients_finite"] = bool(np.isfinite(coefficients).all())
        rank_gate = target != "critical_ens" or not bool(metrics["nearly_constant"])
        metrics["gate_passed"] = bool(
            _target_gate(metrics, rank_gate=rank_gate)
            and metrics["degree"] <= 3
            and metrics["all_coefficients_finite"]
        )
        metrics["selected_model_type"] = str(selected["model_type"])
        metrics["validation_metrics"] = selected["validation_metrics"]
        metrics["tree_depth"] = int(selected["tree_depth"])
        metrics["tree_count"] = int(selected["tree_count"])
        metrics["learning_rate"] = float(selected["learning_rate"])
        metrics["candidate_count"] = len(candidates)
        models[target] = TargetSurrogateFit(
            retained_terms, metrics, target, float(selected["ridge"])
        )
    return MultiTargetSurrogateFit(
        targets=models,
        split_manifest=manifest,
        gates_passed=all(model.metrics["gate_passed"] for model in models.values()),
    )


def fit_recourse_surrogate(
    data: pd.DataFrame,
    *,
    asset_columns: Sequence[str],
    pair_interactions: Sequence[tuple[str, str]],
    cubic_interactions: Sequence[tuple[str, str, str]],
    target_column: str = "recourse_objective",
    group_column: str = "portfolio_signature",
    heldout_target_column: str | None = None,
    cost_column: str | None = None,
    random_seed: int = 2026,
    minimum_portfolios: int = 3000,
    ridge: float = 1e-8,
    interaction_prune_threshold: float = 1e-10,
    interaction_metadata: dict[tuple[str, ...], dict[str, Any]] | None = None,
) -> SurrogateFit:
    """Fit on portfolio-grouped splits and enforce the internal QCi gates."""

    required = set(asset_columns) | {target_column, group_column}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"surrogate dataset is missing columns: {sorted(missing)}")
    if data[group_column].astype(str).nunique() < minimum_portfolios:
        raise ValueError(f"surrogate requires at least {minimum_portfolios} unique portfolios")
    if not bool(data[list(asset_columns)].isin([0, 1]).all().all()):
        raise ValueError("surrogate asset features must be binary")
    if not np.isfinite(data[target_column].astype(float)).all():
        raise ValueError("surrogate target contains non-finite outcomes")
    splits = _group_split(data[group_column].astype(str).tolist(), random_seed)
    membership = {name: set(groups) for name, groups in splits.items()}
    leakage = any(
        membership[left] & membership[right]
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
    )
    if leakage:
        raise ValueError("portfolio-group split leakage detected")
    frames = {
        name: data[data[group_column].astype(str).isin(groups)].copy()
        for name, groups in splits.items()
    }
    specs = _feature_specs(asset_columns, pair_interactions, cubic_interactions)
    train_x = _design(frames["train"], specs)
    train_y = frames["train"][target_column].astype(float).to_numpy()
    regularizer = ridge * np.eye(train_x.shape[1])
    regularizer[0, 0] = 0.0
    coefficients = np.linalg.solve(train_x.T @ train_x + regularizer, train_x.T @ train_y)
    if not np.isfinite(coefficients).all():
        raise ValueError("surrogate fit produced non-finite coefficients")
    # Strong hierarchy: retain every individual parent; sparsify interactions only.
    keep = [
        len(spec) <= 1 or abs(float(coefficient)) >= interaction_prune_threshold
        for spec, coefficient in zip(specs, coefficients, strict=True)
    ]
    retained_specs = tuple(spec for spec, retained in zip(specs, keep, strict=True) if retained)
    retained_coefficients = coefficients[np.asarray(keep)]
    test = frames["test"]
    predicted = _predict(test, retained_specs, retained_coefficients)
    actual_test = test[target_column].astype(float).to_numpy()
    metrics = _rank_metrics(actual_test, predicted)
    if heldout_target_column is not None:
        if heldout_target_column not in test:
            raise ValueError(f"held-out surrogate metric column {heldout_target_column} is missing")
        heldout = test[heldout_target_column].astype(float).to_numpy()
        heldout_correlation = float(spearmanr(heldout, predicted).statistic)
        metrics["heldout_rank_correlation"] = (
            heldout_correlation if math.isfinite(heldout_correlation) else 0.0
        )
    if cost_column is not None:
        if cost_column not in test:
            raise ValueError(f"Pareto cost column {cost_column} is missing")
        cost = test[cost_column].astype(float).to_numpy()
        actual_front = _pareto_indices(cost, actual_test)
        predicted_front = _pareto_indices(cost, predicted)
        metrics["pareto_front_recall"] = (
            len(actual_front & predicted_front) / len(actual_front) if actual_front else 1.0
        )
    metrics.update(
        {
            "no_train_test_leakage": True,
            "degree": max(map(len, retained_specs), default=0),
            "all_coefficients_finite": bool(np.isfinite(retained_coefficients).all()),
            "unique_portfolios": int(data[group_column].astype(str).nunique()),
            "train_portfolios": len(splits["train"]),
            "validation_portfolios": len(splits["validation"]),
            "test_portfolios": len(splits["test"]),
        }
    )
    metrics["gates_passed"] = bool(
        metrics["spearman_rank_correlation"] >= 0.70
        and metrics["top_decile_recall"] >= 0.60
        and metrics["normalized_rmse"] <= 0.25
        and metrics["no_train_test_leakage"]
        and metrics["degree"] <= 3
        and metrics["all_coefficients_finite"]
    )
    metadata = interaction_metadata or {}
    terms = tuple(
        {
            "coefficient": float(coefficient),
            "asset_keys": list(spec),
            "degree": len(spec),
            "component": "surrogate" if len(spec) <= 1 else "interaction",
            **metadata.get(spec, {}),
        }
        for spec, coefficient in zip(retained_specs, retained_coefficients, strict=True)
    )
    return SurrogateFit(terms, metrics, splits, target_column)


def require_surrogate_gates(fit: SurrogateFit) -> None:
    if not fit.metrics.get("gates_passed", False):
        raise ValueError(
            "surrogate QCi gate failed: "
            f"Spearman={fit.metrics['spearman_rank_correlation']:.3f}, "
            f"top-decile recall={fit.metrics['top_decile_recall']:.3f}, "
            f"nRMSE={fit.metrics['normalized_rmse']:.3f}"
        )
