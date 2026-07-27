from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def _evaluate_terms(terms: tuple[dict[str, object], ...], row: dict[str, int]) -> float:
    value = 0.0
    for term in terms:
        product = 1.0
        for name in term["asset_keys"]:  # type: ignore[union-attr]
            product *= row[str(name)]
        value += float(term["coefficient"]) * product
    return value


def test_depth_three_tree_is_exported_as_exact_cubic_polynomial() -> None:
    from cmpo.irc_cmpo_surrogate import _fit_regression_tree, _tree_to_polynomial_terms

    states = list(itertools.product((0, 1), repeat=4))
    x = np.asarray(states, dtype=float)
    y = np.asarray(
        [20.0 if a == 0 else 9.0 if b == 0 else 3.0 if c == 0 else 1.0 for a, b, c, _ in states]
    )
    tree = _fit_regression_tree(x, y, max_depth=3, min_leaf=1)
    terms = _tree_to_polynomial_terms(tree, ("a", "b", "c", "d"), tree_index=0)

    assert max(int(term["degree"]) for term in terms) <= 3
    assert all(term["validation_selected"] is True for term in terms)
    assert all(term["physical_interpretation"] for term in terms if int(term["degree"]) > 1)
    predictions = [_evaluate_terms(terms, dict(zip(("a", "b", "c", "d"), state))) for state in states]
    assert np.allclose(predictions, y)


def test_solver_noise_is_canonicalized_before_rank_and_pareto_metrics() -> None:
    from cmpo.irc_cmpo_surrogate import _target_metrics

    actual = np.asarray([1.0, 1.0 + 4e-7, 2.0, 3.0])
    predicted = np.asarray([1.0 + 3e-7, 1.0, 2.0, 3.0])
    frame = pd.DataFrame({"upgrade_cost": [1.0, 2.0, 3.0, 4.0]})
    metrics = _target_metrics(frame, actual, predicted)

    assert metrics["spearman_rank_correlation"] == 1.0
    assert metrics["pareto_front_recall"] == 1.0
    assert metrics["solver_noise_tolerance"] == 1e-6


def test_validation_selected_tree_ensemble_fits_discrete_plateaus_as_cubic() -> None:
    from cmpo.irc_cmpo_surrogate import fit_multi_target_surrogates

    rng = np.random.default_rng(812)
    rows = []
    for index in range(600):
        bits = rng.integers(0, 2, size=8)
        plateau = (
            100.0
            - 35.0 * (bits[0] * bits[1] * bits[2])
            - 22.0 * (bits[3] * bits[4])
            - 11.0 * bits[5]
        )
        rows.append(
            {
                "portfolio_signature": f"p-{index}",
                **{f"x{i}": int(value) for i, value in enumerate(bits)},
                "upgrade_cost": float(10 + np.dot(bits, np.arange(1, 9))),
                "technology_mix": f"{bits[0]}{bits[3]}{bits[5]}",
                "selected_asset_count": int(bits.sum()),
                "critical_ens": plateau,
                "total_ens": plateau,
                "maximum_customers_unserved": plateau / 100.0,
                "critical_infrastructure_outage_hours": plateau / 10.0,
                "heldout_total_ens": plateau + 5.0 * bits[6] * bits[7],
            }
        )
    frame = pd.DataFrame(rows)
    fit = fit_multi_target_surrogates(
        frame,
        asset_columns=[f"x{i}" for i in range(8)],
        pair_interactions=[],
        cubic_interactions=[],
        target_columns=[
            "critical_ens",
            "total_ens",
            "maximum_customers_unserved",
            "critical_infrastructure_outage_hours",
            "heldout_total_ens",
        ],
        minimum_portfolios=100,
        random_seed=17,
    )

    assert fit.gates_passed is True
    for model in fit.targets.values():
        assert model.metrics["selected_model_type"] in {"regression_tree", "tree_ensemble"}
        assert max(int(term["degree"]) for term in model.terms) <= 3
        assert all(bool(term.get("validation_selected")) for term in model.terms)
