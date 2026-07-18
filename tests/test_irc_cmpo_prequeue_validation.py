from __future__ import annotations

import importlib.util
import itertools

import numpy as np
import pytest

import cmpo.irc_cmpo_scaling as scaling_module
import cmpo.irc_cmpo_validation as validation_module
from cmpo.irc_cmpo_scaling import (
    ScalingError,
    evaluate_polynomial,
    recompute_surrogate_gates,
    scale_for_dirac3,
)
from cmpo.irc_cmpo_validation import (
    assess_exact_suite,
    assess_exact_true_recourse,
    run_local_stochastic_proxy,
    solve_binary_hamiltonian_exact,
)


def test_prequeue_scaling_and_validation_modules_exist() -> None:
    assert importlib.util.find_spec("cmpo.irc_cmpo_scaling") is not None
    assert importlib.util.find_spec("cmpo.irc_cmpo_validation") is not None


def _term(coefficient: float, *names: str, component: str = "surrogate") -> dict[str, object]:
    return {
        "coefficient": coefficient,
        "powers": {name: 1 for name in names},
        "degree": len(names),
        "component": component,
    }


def test_scaling_combines_monomials_and_excludes_constants_and_zeros() -> None:
    scaled = scale_for_dirac3(
        [
            _term(10.0, component="constant"),
            _term(2.0, "x"),
            _term(3.0, "x", component="cost"),
            _term(-1.0, "y"),
            _term(0.0, "z"),
            _term(4.0, "x", "y"),
        ]
    )

    assert scaled.constant_offset == pytest.approx(10.0)
    assert len(scaled.terms) == 3
    assert all(isinstance(term["powers"], dict) for term in scaled.terms)
    by_powers = {tuple(term["powers"]): term for term in scaled.terms}
    assert by_powers[("x",)]["coefficient"] == pytest.approx(1.0)
    assert scaled.audit.maximum_material_coefficient == pytest.approx(1.0)
    assert scaled.audit.dynamic_range <= 200.0
    assert scaled.audit.minimum_distinct_level_separation + 1e-12 >= 1 / 200
    assert scaled.audit.material_term_count == 3
    assert scaled.audit.constant_term_count == 1
    assert scaled.audit.removed_zero_monomial_count == 1
    assert scaled.audit.degree_distribution == {1: 2, 2: 1}
    assert scaled.audit.component_statistics["surrogate"]["material_monomial_count"] == 3
    assert scaled.audit.distinct_coefficient_level_count == 3
    assert set(by_powers[("x",)]["source_components"]) == {"cost", "surrogate"}


def test_scaling_uses_resolvable_grid_and_preserves_predictions_in_original_units() -> None:
    original = [_term(8.0, component="constant"), _term(10.0, "x"), _term(0.01, "y")]
    scaled = scale_for_dirac3(original)

    levels = sorted({abs(float(term["coefficient"])) for term in scaled.terms})
    assert all(level * 200 == pytest.approx(round(level * 200)) for level in levels)
    assert min(levels) >= 1 / 200
    assert evaluate_polynomial(original, {"x": 1, "y": 1}) == pytest.approx(18.01)
    assert scaled.predict_original_units({"x": 1, "y": 1}) == pytest.approx(18.05)
    assert scaled.energy({"x": 1, "y": 1}) == pytest.approx(1.005)


@pytest.mark.parametrize("coefficient", [1e-13, 1e-14, 1e-15, 1e-16])
def test_scaling_rejects_collapsed_material_coefficients(coefficient: float) -> None:
    with pytest.raises(ScalingError, match="collapsed material coefficient"):
        scale_for_dirac3([_term(1.0, "x"), _term(coefficient, "y")])


def test_post_quantization_recomputes_prediction_gates() -> None:
    states = [{"x": x, "y": y} for x, y in itertools.product((0, 1), repeat=2)]
    actual = np.asarray([3.0 * state["x"] + state["y"] for state in states])
    scaled = scale_for_dirac3([_term(3.0, "x"), _term(1.0, "y")])

    report = recompute_surrogate_gates(
        scaled,
        states,
        actual,
        costs=[0.0, 1.0, 1.0, 2.0],
        minimum_spearman=0.8,
        maximum_normalized_rmse=0.2,
        minimum_top_decile_recall=0.7,
        minimum_pareto_recall=0.7,
    )

    assert report["gates_passed"] is True
    assert report["quantized"]["spearman_rank_correlation"] == pytest.approx(1.0)
    assert report["quantized"]["r2"] >= 0.999
    assert report["quantized"]["pareto_front_recall"] == pytest.approx(1.0)


def test_post_quantization_top_decile_recall_is_tie_stable_and_equal_cardinality() -> None:
    states = [
        dict(zip(("a", "b", "c", "d"), bits, strict=True))
        for bits in itertools.product((0, 1), repeat=4)
    ]
    actual = [0.0] * len(states)
    scaled = scale_for_dirac3([_term(1.0, "a")])

    forward = recompute_surrogate_gates(scaled, states, actual)
    reverse = recompute_surrogate_gates(scaled, list(reversed(states)), list(reversed(actual)))

    assert forward["quantized"]["top_decile_count"] == 2
    assert reverse["quantized"]["top_decile_count"] == 2
    assert forward["quantized"]["top_decile_recall"] == pytest.approx(
        reverse["quantized"]["top_decile_recall"]
    )


def test_failed_post_quantization_gate_is_explicitly_rejected() -> None:
    assert hasattr(scaling_module, "require_quantized_surrogate_gates")
    with pytest.raises(ScalingError, match="post-quantization surrogate gate failed"):
        scaling_module.require_quantized_surrogate_gates({"gates_passed": False})


def test_payload_scaling_is_nonmutating_and_requires_post_quantization_validation() -> None:
    assert hasattr(scaling_module, "scale_payload_for_dirac3")
    payload = {
        "schema": "toy",
        "variables": [{"name": "x"}, {"name": "y"}],
        "polynomial_terms": [_term(3.0, "x"), _term(1.0, "y")],
        "max_degree": 1,
    }
    states = [{"x": x, "y": y} for x, y in itertools.product((0, 1), repeat=2)]
    actual = [3.0 * state["x"] + state["y"] for state in states]

    scaled_payload = scaling_module.scale_payload_for_dirac3(
        payload,
        validation_states=states,
        validation_actual_values=actual,
        validation_costs=[0.0, 1.0, 1.0, 2.0],
    )

    assert payload["polynomial_terms"][0]["coefficient"] == 3.0
    assert max(abs(term["coefficient"]) for term in scaled_payload["polynomial_terms"]) == 1.0
    assert scaled_payload["dirac3_scaling"]["post_quantization_validation"]["gates_passed"] is True
    assert scaled_payload["objective_constant_offset_original_units"] == 0.0


def test_exact_milp_returns_known_top_ten_for_cubic_binary_hamiltonian() -> None:
    terms = [
        _term(-5.0, "a"),
        _term(-4.0, "b"),
        _term(-3.0, "c"),
        _term(9.0, "a", "b", "c"),
        _term(0.2, "d"),
        _term(0.3, "e"),
        _term(0.4, "f"),
    ]
    variables = list("abcdef")
    expected = sorted(
        (
            evaluate_polynomial(terms, dict(zip(variables, bits, strict=True))),
            bits,
        )
        for bits in itertools.product((0, 1), repeat=len(variables))
    )[:10]

    result = solve_binary_hamiltonian_exact(terms, variables, top_k=10)

    assert result.backend == "scipy.optimize.milp (HiGHS exact linearization)"
    assert [solution.energy for solution in result.solutions] == pytest.approx(
        [item[0] for item in expected]
    )
    assert result.solutions[0].state == dict(zip(variables, expected[0][1], strict=True))
    assert result.projection_used is False


def test_exact_solver_rejects_invalid_binary_powers() -> None:
    with pytest.raises(ValueError, match="nonnegative integers"):
        solve_binary_hamiltonian_exact(
            [{"coefficient": 1.0, "powers": {"x": -1}, "degree": -1}],
            ["x"],
        )


def test_exact_solver_handles_structured_33_variable_master_without_enumeration() -> None:
    variables = [f"a{anchor}_{tech}" for anchor in range(11) for tech in range(3)]
    terms: list[dict[str, object]] = []
    for anchor in range(11):
        x, y, z = [f"a{anchor}_{tech}" for tech in range(3)]
        terms.extend(
            [
                _term(-1.0, x),
                _term(-0.5, y),
                _term(-0.25, z),
                _term(2.0, x, y),
                _term(2.0, x, z),
                _term(2.0, y, z),
            ]
        )

    result = solve_binary_hamiltonian_exact(terms, variables, top_k=10)

    assert len(result.solutions) == 10
    assert sum(result.solutions[0].state.values()) == 11
    assert all(result.solutions[0].state[f"a{anchor}_0"] == 1 for anchor in range(11))


def test_quantized_and_unquantized_top_portfolio_overlap_is_reported() -> None:
    assert hasattr(validation_module, "compare_exact_top_portfolios")
    variables = ["x", "y", "z", "u", "v", "w"]
    original_terms = [_term(-float(index + 1), name) for index, name in enumerate(variables)]
    quantized_terms = scale_for_dirac3(original_terms).terms
    original = solve_binary_hamiltonian_exact(original_terms, variables, top_k=10)
    quantized = solve_binary_hamiltonian_exact(quantized_terms, variables, top_k=10)

    comparison = validation_module.compare_exact_top_portfolios(original, quantized)

    assert comparison["top_ten_overlap_count"] == 10
    assert comparison["same_optimum_portfolio"] is True
    assert comparison["near_same_top_portfolios"] is True


def test_exact_true_recourse_and_six_lambda_suite_gates() -> None:
    variables = ["x", "y", "z", "u", "v", "w"]
    terms = [
        _term(-6.0, "x"),
        _term(-5.0, "y"),
        _term(-4.0, "z"),
        _term(-3.0, "u"),
        _term(-2.0, "v"),
        _term(-1.0, "w"),
    ]
    dataset = []
    for bits in itertools.product((0, 1), repeat=6):
        state = dict(zip(variables, bits, strict=True))
        score = 10.0 + evaluate_polynomial(terms, state)
        dataset.append(
            {
                "state": state,
                "true_score": score,
                "upgrade_cost": sum(bits),
            }
        )
    exact = solve_binary_hamiltonian_exact(
        terms,
        variables,
        top_k=10,
        feasibility=lambda state: bool(sum(state.values())),
    )
    report = assess_exact_true_recourse(
        exact,
        dataset,
        hamiltonian_terms=terms,
        recourse_evaluator=lambda state: {
            "true_score": 10.0 + evaluate_polynomial(terms, state),
            "upgrade_cost": sum(state.values()),
        },
    )

    assert report["optimum_natively_feasible"] is True
    assert report["projection_used"] is False
    assert report["true_recourse_regret"] == pytest.approx(0.0)
    assert report["energy_to_true_recourse_spearman"] == pytest.approx(1.0)
    assert report["top_ten_true_top_decile_count"] >= 5
    suite = assess_exact_suite(
        [report] * 6,
        quantization_comparisons=[{"near_same_top_portfolios": True}] * 6,
    )
    assert suite["gates_passed"] is True
    assert suite["lambda_optima_near_pareto"] == 6


def test_exact_suite_rejects_quantization_top_portfolio_drift() -> None:
    report = {
        "optimum_natively_feasible": True,
        "projection_used": False,
        "on_or_within_5pct_pareto": True,
        "true_recourse_regret": 0.0,
        "energy_to_true_recourse_spearman": 1.0,
        "top_ten_true_top_decile_count": 10,
    }
    comparisons = [{"near_same_top_portfolios": True}] * 6
    comparisons[-1] = {"near_same_top_portfolios": False}
    suite = assess_exact_suite([report] * 6, quantization_comparisons=comparisons)
    assert suite["quantization_top_portfolio_gates_passed"] is False
    assert suite["gates_passed"] is False


def test_local_stochastic_proxy_is_deterministic_native_and_reports_required_metrics() -> None:
    variables = ["x", "y", "z", "u", "v", "w"]
    terms = [_term(-float(index + 1), name) for index, name in enumerate(variables)]
    exact = solve_binary_hamiltonian_exact(terms, variables, top_k=10)
    kwargs = {
        "terms": terms,
        "variable_names": variables,
        "exact_optimum_energy": exact.optimum_energy,
        "feasibility": lambda state: sum(state.values()) >= 1,
        "recourse_evaluator": lambda state: -sum(
            (index + 1) * state[name] for index, name in enumerate(variables)
        ),
        "best_true_recourse": -21.0,
        "samples_per_method": 12,
        "annealing_sweeps": 30,
        "random_seed": 9,
    }
    first = run_local_stochastic_proxy(**kwargs)
    second = run_local_stochastic_proxy(**kwargs)

    assert first["samples"] == second["samples"]
    assert first["projection_used"] is False
    assert first["native_feasibility_rate"] >= 0.8
    assert first["within_two_percent_optimum_count"] >= 1
    assert first["median_true_recourse_regret"] <= 0.1
    assert first["unique_feasible_portfolios"] >= 5
    assert first["gates_passed"] is True
    assert set(first["by_method"]) == {
        "integer_simulated_annealing",
        "random_restart",
        "local_coordinate_search",
    }
    for method in first["by_method"].values():
        assert {
            "native_feasibility_rate",
            "exact_optimum_hit_rate",
            "best_energy",
            "median_energy",
            "true_recourse_regret",
            "portfolio_diversity",
            "time_to_good_solution_seconds",
        } <= set(method)


def test_stochastic_six_lambda_suite_rejects_any_failed_lambda() -> None:
    assert hasattr(validation_module, "assess_stochastic_suite")
    reports = [{"gates_passed": True}] * 6
    assert validation_module.assess_stochastic_suite(reports)["gates_passed"] is True
    reports[-1] = {"gates_passed": False}
    assert validation_module.assess_stochastic_suite(reports)["gates_passed"] is False


def test_random_restart_is_a_search_not_unoptimized_random_draws() -> None:
    variables = [f"a{anchor}_{tech}" for anchor in range(11) for tech in ("pv", "bess", "gen")]
    terms = []
    for anchor in range(11):
        bess = f"a{anchor}_bess"
        gen = f"a{anchor}_gen"
        # 10 * (1-bess) * (1-gen): PV alone is inadequate.
        terms.extend(
            [
                {"coefficient": 10.0, "powers": {}, "degree": 0},
                _term(-10.0, bess),
                _term(-10.0, gen),
                {"coefficient": 10.0, "powers": {bess: 1, gen: 1}, "degree": 2},
            ]
        )
    exact = solve_binary_hamiltonian_exact(terms, variables, top_k=1)

    def feasible(state):
        return all(state[f"a{i}_bess"] or state[f"a{i}_gen"] for i in range(11))

    report = run_local_stochastic_proxy(
        terms=terms,
        variable_names=variables,
        exact_optimum_energy=exact.optimum_energy,
        feasibility=feasible,
        recourse_evaluator=lambda state: {"true_score": evaluate_polynomial(terms, state)},
        best_true_recourse=0.0,
        samples_per_method=12,
        annealing_sweeps=30,
        random_seed=7,
    )
    assert report["by_method"]["random_restart"]["native_feasibility_rate"] >= 0.8
