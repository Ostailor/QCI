| dataset | method_name | expected_operating_cost | best_cost_by_method | median_cost_by_method | risk_adjusted_cost | total_upgrade_cost | max_fraction_customers_unserved_per_hour | total_hours_critical_infrastructure_unserved | critical_load_served_fraction | critical_energy_not_served_kwh | energy_not_served_kwh | feasibility_after_repair | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | scenario_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qci_small_synthetic | Piecewise-linear MILP baseline | 10869.1 | 1084.8 | 4958.49 | 16458.1 | 0 | 0.420453 | 8 | 0.989505 | 1139.11 | 17148.5 | 1 | 0.302311 | 0.0164094 | 0.0153801 | 2 | 8 |
| qci_small_synthetic | DifferentialEvolutionOptimizer | 18108 | 5317.64 | 9568.12 | 21976.8 | 0 | 0.568221 | 64 | 0.717811 | 26201 | 71901.4 | 1 | 0.596684 | 0.0373953 | 0.0321998 | 2 | 8 |
| qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 36216.8 | 14769.6 | 18345.4 | 41805.8 | 0 | 0.453172 | 56 | 0.977334 | 2458.64 | 18283.1 | 1 | 1.50374 | 0.0973785 | 0.0833488 | 2 | 8 |
| qci_small_synthetic | SLSQPDispatchOptimizer | 36216.8 | 14769.6 | 18345.4 | 41805.8 | 0 | 0.453172 | 56 | 0.977334 | 2458.64 | 18283.1 | 1 | 1.49791 | 0.0961873 | 0.0825901 | 2 | 8 |
| qci_small_synthetic | Stress-only reserve heuristic baseline | 36954.4 | 9506.06 | 15550.4 | 42539.2 | 0 | 0.530693 | 8 | 0.986463 | 1469.27 | 56433.1 | 1 | 0.000560126 | 3.3542e-05 | 3.0542e-05 | 2 | 8 |
| qci_small_synthetic | QUBO/quadratized local search baseline | 42410.3 | 13909.3 | 22031.5 | 48096.2 | 0 | 0.50907 | 16 | 0.973656 | 2857.87 | 20042.8 | 1 | 18.2064 | 1.1679 | 1.00059 | 2 | 8 |
| qci_small_synthetic | CMPO-local polynomial search | 42799 | 15242.7 | 22382.5 | 48483.9 | 0 | 0.451655 | 16 | 0.977336 | 2458.49 | 18064.7 | 1 | 4.79872 | 0.300699 | 0.259419 | 2 | 8 |
| qci_small_synthetic | GPU-parallel random restart baseline | 42799 | 15242.7 | 22382.5 | 48483.9 | 0 | 0.451655 | 16 | 0.977336 | 2458.49 | 18064.7 | 1 | 39.1909 | 2.44823 | 2.09913 | 2 | 8 |
| qci_small_synthetic | GreedyCriticalLoadFirst | 42799 | 15242.7 | 22382.5 | 48483.9 | 0 | 0.451655 | 16 | 0.977336 | 2458.49 | 18064.7 | 1 | 0 | 0 | 0 | 2 | 8 |
| qci_small_synthetic | qBraid GPU-parallel random restart baseline | 1.06997e+06 | 15242.7 | 22382.5 | 1.07566e+06 | 0 | 0.451655 | 400 | 0.977336 | 61462.1 | 451618 | 1 | 4.44598 | 0.00796263 | 0.00556062 | 50 | 8 |
| synthetic_smoke | Piecewise-linear MILP baseline | 386.789 | 353.51 | 420.068 | 508.446 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.0393034 | 0.00961394 | 0.00953071 | 2 | 2 |
| synthetic_smoke | DifferentialEvolutionOptimizer | 2543.72 | 1530.56 | 2451.71 | 3398.79 | 0 | 0.110927 | 16 | 0.874059 | 738.944 | 3721.56 | 1 | 0.0211613 | 0.00518373 | 0.00498875 | 2 | 2 |
| synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 6419.65 | 6253.25 | 6586.04 | 8149.35 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.0375373 | 0.0093964 | 0.00916692 | 2 | 2 |
| synthetic_smoke | SLSQPDispatchOptimizer | 6419.65 | 6253.25 | 6586.04 | 8149.35 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.0372775 | 0.00932027 | 0.00924075 | 2 | 2 |
| synthetic_smoke | Stress-only reserve heuristic baseline | 7156.84 | 7088.71 | 7224.98 | 8997.16 | 0 | 0.0890736 | 0 | 1 | 0 | 2280.46 | 1 | 8.76661e-05 | 1.93125e-05 | 1.45411e-05 | 2 | 2 |
| synthetic_smoke | CMPO-local polynomial search | 7183.95 | 7090.83 | 7276.77 | 9049.33 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.0468662 | 0.0116993 | 0.0115674 | 2 | 2 |
| synthetic_smoke | GPU-parallel random restart baseline | 7184.39 | 7092.01 | 7276.77 | 9049.78 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1.11263 | 0.095622 | 0.0945442 | 2 | 2 |
| synthetic_smoke | GreedyCriticalLoadFirst | 7184.39 | 7092.01 | 7276.77 | 9049.78 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 2 | 2 |
| synthetic_smoke | QUBO/quadratized local search baseline | 7185.09 | 7092.21 | 7277.97 | 9051.02 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.590145 | 0.144023 | 0.142056 | 2 | 2 |
