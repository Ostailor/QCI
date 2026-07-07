# Challenge Score Summary

Lower challenge scores are better. Weighted scores normalize every metric within each benchmark dataset; lexicographic scores follow feasibility, critical ENS, critical infrastructure outage hours, max customers unserved, critical-load served, risk cost, and runtime in that order.

| score_mode | dataset | method_name | challenge_score | challenge_rank | best_method_by_challenge_score | qci_minus_best_challenge_score | qci_outcome_by_challenge_score | critical_energy_not_served_kwh | total_hours_critical_infrastructure_unserved | max_fraction_customers_unserved_per_hour | critical_load_served_fraction | risk_adjusted_cost | runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic | pglib_case14_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 9 | qci_loss | 23134.8 | 600 | 0.496372 | 0.965659 | 15539.8 | 0.0210873 |
| lexicographic | pglib_case14_adapted | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | 9 | qci_loss | 23134.8 | 600 | 0.572846 | 0.965659 | 20202.4 | 5.1667e-05 |
| lexicographic | pglib_case14_adapted | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | 9 | qci_loss | 23165.9 | 600 | 0.496372 | 0.965613 | 25940.1 | 0 |
| lexicographic | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | Piecewise-linear MILP baseline | 9 | qci_loss | 23177 | 1200 | 0.502364 | 0.965597 | 25480.5 | 0.095955 |
| lexicographic | pglib_case14_adapted | SLSQPDispatchOptimizer | 4 | 5 | Piecewise-linear MILP baseline | 9 | qci_loss | 23177 | 1200 | 0.502364 | 0.965597 | 25480.5 | 0.124834 |
| lexicographic | pglib_case14_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 9 | qci_loss | 26037.1 | 600 | 0.565812 | 0.961351 | 26006.6 | 3.76055 |
| lexicographic | pglib_case14_adapted | CMPO-local polynomial search | 6 | 7 | Piecewise-linear MILP baseline | 9 | qci_loss | 28228.4 | 600 | 0.580519 | 0.958099 | 25834.5 | 0.730537 |
| lexicographic | pglib_case14_adapted | GPU-parallel random restart baseline | 7 | 8 | Piecewise-linear MILP baseline | 9 | qci_loss | 33725.9 | 600 | 0.610203 | 0.949938 | 25699.2 | 0.002767 |
| lexicographic | pglib_case14_adapted | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | 9 | qci_loss | 164249 | 7200 | 0.61199 | 0.577829 | 24822.2 | 0.0821458 |
| lexicographic | pglib_case14_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 9 | qci_loss | 169070 | 8508 | 0.656371 | 0.29057 | 30167.7 | 30 |
| lexicographic | pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 1 | GreedyCriticalLoadFirst | 8 | qci_loss | 23933.7 | 600 | 0.405713 | 0.969315 | 27601.1 | 0 |
| lexicographic | pglib_case30_adapted | Stress-only reserve heuristic baseline | 1 | 2 | GreedyCriticalLoadFirst | 8 | qci_loss | 23933.7 | 600 | 0.520588 | 0.969315 | 22754.9 | 2.48749e-05 |
| lexicographic | pglib_case30_adapted | Piecewise-linear MILP baseline | 2 | 3 | GreedyCriticalLoadFirst | 8 | qci_loss | 23933.7 | 600 | 0.405713 | 0.969315 | 13101.4 | 0.0161598 |
| lexicographic | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | GreedyCriticalLoadFirst | 8 | qci_loss | 23934.8 | 1200 | 0.405719 | 0.969314 | 27124.2 | 0.00828513 |
| lexicographic | pglib_case30_adapted | SLSQPDispatchOptimizer | 4 | 5 | GreedyCriticalLoadFirst | 8 | qci_loss | 23934.8 | 1200 | 0.405719 | 0.969314 | 27124.2 | 0.00913613 |
| lexicographic | pglib_case30_adapted | QUBO/quadratized local search baseline | 5 | 6 | GreedyCriticalLoadFirst | 8 | qci_loss | 25616 | 600 | 0.468481 | 0.967159 | 27423.9 | 0.439572 |
| lexicographic | pglib_case30_adapted | CMPO-local polynomial search | 6 | 7 | GreedyCriticalLoadFirst | 8 | qci_loss | 28775.6 | 600 | 0.508662 | 0.963108 | 27338.5 | 0.110088 |
| lexicographic | pglib_case30_adapted | GPU-parallel random restart baseline | 7 | 8 | GreedyCriticalLoadFirst | 8 | qci_loss | 30377.6 | 600 | 0.532099 | 0.961054 | 27218.3 | 0.00109763 |
| lexicographic | pglib_case30_adapted | CMPO + QCi Dirac-3 | 8 | 9 | GreedyCriticalLoadFirst | 8 | qci_loss | 112761 | 6882 | 0.550011 | 0.225179 | 28423.2 | 20 |
| lexicographic | pglib_case30_adapted | DifferentialEvolutionOptimizer | 9 | 10 | GreedyCriticalLoadFirst | 8 | qci_loss | 135630 | 10800 | 0.532983 | 0.640106 | 30451.8 | 0.014648 |
| lexicographic | pglib_case57_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 3344.14 | 0.0213422 |
| lexicographic | pglib_case57_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0 |
| lexicographic | pglib_case57_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0.00190467 |
| lexicographic | pglib_case57_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0.221177 |
| lexicographic | pglib_case57_adapted | QUBO/quadratized local search baseline | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12464.3 | 2.70259 |
| lexicographic | pglib_case57_adapted | Stress-only reserve heuristic baseline | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0.103372 | 1 | 11912.2 | 5.0833e-05 |
| lexicographic | pglib_case57_adapted | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0.00285585 | 36 | 8.58397e-08 | 1 | 12042.2 | 0.0723787 |
| lexicographic | pglib_case57_adapted | SLSQPDispatchOptimizer | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0.00285585 | 36 | 8.58397e-08 | 1 | 12042.2 | 0.0743063 |
| lexicographic | pglib_case57_adapted | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 19273.3 | 288 | 0.221949 | 0.662854 | 6994.62 | 0.0810401 |
| lexicographic | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 8 | qci_loss | 0 | 0 | 0.00390406 | 1 | 77693.5 | 0.0208893 |
| lexicographic | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | 8 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0 |
| lexicographic | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | 8 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0.00188546 |
| lexicographic | pglib_case5_pjm_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | 8 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0.295145 |
| lexicographic | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 4 | 5 | Piecewise-linear MILP baseline | 8 | qci_loss | 0 | 0 | 0.200946 | 1 | 163601 | 4.5666e-05 |
| lexicographic | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 5 | 6 | Piecewise-linear MILP baseline | 8 | qci_loss | 1.3092 | 1200 | 0.0137756 | 0.999999 | 188785 | 0.045297 |
| lexicographic | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | 8 | qci_loss | 1.3092 | 1200 | 0.0137756 | 0.999999 | 188785 | 0.0458798 |
| lexicographic | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 7 | 8 | Piecewise-linear MILP baseline | 8 | qci_loss | 207.715 | 24 | 0.0317229 | 0.999745 | 190688 | 1.37831 |
| lexicographic | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 8 | 9 | Piecewise-linear MILP baseline | 8 | qci_loss | 137738 | 1638 | 0.277744 | 0.746105 | 69918.4 | 15 |
| lexicographic | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 9 | 10 | Piecewise-linear MILP baseline | 8 | qci_loss | 359790 | 4800 | 0.283516 | 0.701302 | 107963 | 0.0356285 |
| lexicographic | qci_small_synthetic | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 1139.11 | 8 | 0.420453 | 0.989505 | 16458.1 | 0.0153801 |
| lexicographic | qci_small_synthetic | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 1469.27 | 8 | 0.530693 | 0.986463 | 42539.2 | 3.0542e-05 |
| lexicographic | qci_small_synthetic | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 0 |
| lexicographic | qci_small_synthetic | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 0.259419 |
| lexicographic | qci_small_synthetic | GPU-parallel random restart baseline | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 2.09913 |
| lexicographic | qci_small_synthetic | SLSQPDispatchOptimizer | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.64 | 56 | 0.453172 | 0.977334 | 41805.8 | 0.0825901 |
| lexicographic | qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.64 | 56 | 0.453172 | 0.977334 | 41805.8 | 0.0833488 |
| lexicographic | qci_small_synthetic | QUBO/quadratized local search baseline | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2857.87 | 16 | 0.50907 | 0.973656 | 48096.2 | 1.00059 |
| lexicographic | qci_small_synthetic | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 26201 | 64 | 0.568221 | 0.717811 | 21976.8 | 0.0321998 |
| lexicographic | qci_small_synthetic | qBraid GPU-parallel random restart baseline | 9 | 10 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 61462.1 | 400 | 0.451655 | 0.977336 | 1.07566e+06 | 0.00556062 |
| lexicographic | synthetic_smoke | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 508.446 | 0.00953071 |
| lexicographic | synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 8149.35 | 0.00916692 |
| lexicographic | synthetic_smoke | SLSQPDispatchOptimizer | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 8149.35 | 0.00924075 |
| lexicographic | synthetic_smoke | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.33 | 0.0115674 |
| lexicographic | synthetic_smoke | GreedyCriticalLoadFirst | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.78 | 0 |
| lexicographic | synthetic_smoke | GPU-parallel random restart baseline | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.78 | 0.0945442 |
| lexicographic | synthetic_smoke | QUBO/quadratized local search baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9051.02 | 0.142056 |
| lexicographic | synthetic_smoke | Stress-only reserve heuristic baseline | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0.0890736 | 1 | 8997.16 | 1.45411e-05 |
| lexicographic | synthetic_smoke | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 738.944 | 16 | 0.110927 | 0.874059 | 3398.79 | 0.00498875 |
| weighted | pglib_case14_adapted | Piecewise-linear MILP baseline | 0.00070291 | 1 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 23134.8 | 600 | 0.496372 | 0.965659 | 15539.8 | 0.0210873 |
| weighted | pglib_case14_adapted | GreedyCriticalLoadFirst | 7.54057 | 2 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 23165.9 | 600 | 0.496372 | 0.965613 | 25940.1 | 0 |
| weighted | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 102.156 | 3 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 23177 | 1200 | 0.502364 | 0.965597 | 25480.5 | 0.095955 |
| weighted | pglib_case14_adapted | SLSQPDispatchOptimizer | 102.157 | 4 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 23177 | 1200 | 0.502364 | 0.965597 | 25480.5 | 0.124834 |
| weighted | pglib_case14_adapted | QUBO/quadratized local search baseline | 245.55 | 5 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 26037.1 | 600 | 0.565812 | 0.961351 | 26006.6 | 3.76055 |
| weighted | pglib_case14_adapted | CMPO-local polynomial search | 306.359 | 6 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 28228.4 | 600 | 0.580519 | 0.958099 | 25834.5 | 0.730537 |
| weighted | pglib_case14_adapted | Stress-only reserve heuristic baseline | 317.87 | 7 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 23134.8 | 600 | 0.572846 | 0.965659 | 20202.4 | 5.1667e-05 |
| weighted | pglib_case14_adapted | GPU-parallel random restart baseline | 438.568 | 8 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 33725.9 | 600 | 0.610203 | 0.949938 | 25699.2 | 0.002767 |
| weighted | pglib_case14_adapted | DifferentialEvolutionOptimizer | 2269.22 | 9 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 164249 | 7200 | 0.61199 | 0.577829 | 24822.2 | 0.0821458 |
| weighted | pglib_case14_adapted | CMPO + QCi Dirac-3 | 2598.21 | 10 | Piecewise-linear MILP baseline | 2598.21 | qci_loss | 169070 | 8508 | 0.656371 | 0.29057 | 30167.7 | 30 |
| weighted | pglib_case30_adapted | Piecewise-linear MILP baseline | 0.00080799 | 1 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 23933.7 | 600 | 0.405713 | 0.969315 | 13101.4 | 0.0161598 |
| weighted | pglib_case30_adapted | GreedyCriticalLoadFirst | 9.3165 | 2 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 23933.7 | 600 | 0.405713 | 0.969315 | 27601.1 | 0 |
| weighted | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 67.8979 | 3 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 23934.8 | 1200 | 0.405719 | 0.969314 | 27124.2 | 0.00828513 |
| weighted | pglib_case30_adapted | SLSQPDispatchOptimizer | 67.898 | 4 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 23934.8 | 1200 | 0.405719 | 0.969314 | 27124.2 | 0.00913613 |
| weighted | pglib_case30_adapted | QUBO/quadratized local search baseline | 244.633 | 5 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 25616 | 600 | 0.468481 | 0.967159 | 27423.9 | 0.439572 |
| weighted | pglib_case30_adapted | CMPO-local polynomial search | 412.593 | 6 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 28775.6 | 600 | 0.508662 | 0.963108 | 27338.5 | 0.110088 |
| weighted | pglib_case30_adapted | Stress-only reserve heuristic baseline | 467.353 | 7 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 23933.7 | 600 | 0.520588 | 0.969315 | 22754.9 | 2.48749e-05 |
| weighted | pglib_case30_adapted | GPU-parallel random restart baseline | 509.503 | 8 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 30377.6 | 600 | 0.532099 | 0.961054 | 27218.3 | 0.00109763 |
| weighted | pglib_case30_adapted | CMPO + QCi Dirac-3 | 1983.21 | 9 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 112761 | 6882 | 0.550011 | 0.225179 | 28423.2 | 20 |
| weighted | pglib_case30_adapted | DifferentialEvolutionOptimizer | 2551 | 10 | Piecewise-linear MILP baseline | 1983.21 | qci_loss | 135630 | 10800 | 0.532983 | 0.640106 | 30451.8 | 0.014648 |
| weighted | pglib_case57_adapted | Piecewise-linear MILP baseline | 0.00789695 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 3344.14 | 0.0213422 |
| weighted | pglib_case57_adapted | GreedyCriticalLoadFirst | 9.95979 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0 |
| weighted | pglib_case57_adapted | GPU-parallel random restart baseline | 9.9605 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0.00190467 |
| weighted | pglib_case57_adapted | CMPO-local polynomial search | 10.0416 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12427.7 | 0.221177 |
| weighted | pglib_case57_adapted | QUBO/quadratized local search baseline | 11 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 12464.3 | 2.70259 |
| weighted | pglib_case57_adapted | IPOPT/Pyomo nonlinear baseline | 134.564 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0.00285585 | 36 | 8.58397e-08 | 1 | 12042.2 | 0.0723787 |
| weighted | pglib_case57_adapted | SLSQPDispatchOptimizer | 134.565 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0.00285585 | 36 | 8.58397e-08 | 1 | 12042.2 | 0.0743063 |
| weighted | pglib_case57_adapted | Stress-only reserve heuristic baseline | 280.848 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0.103372 | 1 | 11912.2 | 5.0833e-05 |
| weighted | pglib_case57_adapted | DifferentialEvolutionOptimizer | 2604.03 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 19273.3 | 288 | 0.221949 | 0.662854 | 6994.62 | 0.0810401 |
| weighted | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0.645188 | 1 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 0 | 0 | 0.00390406 | 1 | 77693.5 | 0.0208893 |
| weighted | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 30.4402 | 2 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0 |
| weighted | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 30.4403 | 3 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0.00188546 |
| weighted | pglib_case5_pjm_adapted | CMPO-local polynomial search | 30.4598 | 4 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 0 | 0 | 0.0149649 | 1 | 188995 | 0.295145 |
| weighted | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 66.8298 | 5 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 207.715 | 24 | 0.0317229 | 0.999745 | 190688 | 1.37831 |
| weighted | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 278.217 | 6 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 1.3092 | 1200 | 0.0137756 | 0.999999 | 188785 | 0.045297 |
| weighted | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 278.217 | 7 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 1.3092 | 1200 | 0.0137756 | 0.999999 | 188785 | 0.0458798 |
| weighted | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 437.863 | 8 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 0 | 0 | 0.200946 | 1 | 163601 | 4.5666e-05 |
| weighted | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 1244.87 | 9 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 137738 | 1638 | 0.277744 | 0.746105 | 69918.4 | 15 |
| weighted | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 2603.15 | 10 | Piecewise-linear MILP baseline | 1244.22 | qci_loss | 359790 | 4800 | 0.283516 | 0.701302 | 107963 | 0.0356285 |
| weighted | qci_small_synthetic | Piecewise-linear MILP baseline | 0.00732689 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 1139.11 | 8 | 0.420453 | 0.989505 | 16458.1 | 0.0153801 |
| weighted | qci_small_synthetic | GreedyCriticalLoadFirst | 148.371 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 0 |
| weighted | qci_small_synthetic | CMPO-local polynomial search | 148.494 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 0.259419 |
| weighted | qci_small_synthetic | GPU-parallel random restart baseline | 149.371 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.49 | 16 | 0.451655 | 0.977336 | 48483.9 | 2.09913 |
| weighted | qci_small_synthetic | SLSQPDispatchOptimizer | 255.573 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.64 | 56 | 0.453172 | 0.977334 | 41805.8 | 0.0825901 |
| weighted | qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 255.574 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2458.64 | 56 | 0.453172 | 0.977334 | 41805.8 | 0.0833488 |
| weighted | qci_small_synthetic | QUBO/quadratized local search baseline | 350.196 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 2857.87 | 16 | 0.50907 | 0.973656 | 48096.2 | 1.00059 |
| weighted | qci_small_synthetic | Stress-only reserve heuristic baseline | 387.779 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 1469.27 | 8 | 0.530693 | 0.986463 | 42539.2 | 3.0542e-05 |
| weighted | qci_small_synthetic | DifferentialEvolutionOptimizer | 1070.99 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 26201 | 64 | 0.568221 | 0.717811 | 21976.8 | 0.0321998 |
| weighted | qci_small_synthetic | qBraid GPU-parallel random restart baseline | 2215.58 | 10 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 61462.1 | 400 | 0.451655 | 0.977336 | 1.07566e+06 | 0.00556062 |
| weighted | synthetic_smoke | Piecewise-linear MILP baseline | 0.067091 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 508.446 | 0.00953071 |
| weighted | synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 9.00903 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 8149.35 | 0.00916692 |
| weighted | synthetic_smoke | SLSQPDispatchOptimizer | 9.00955 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 8149.35 | 0.00924075 |
| weighted | synthetic_smoke | GreedyCriticalLoadFirst | 9.99855 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.78 | 0 |
| weighted | synthetic_smoke | CMPO-local polynomial search | 10.0795 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.33 | 0.0115674 |
| weighted | synthetic_smoke | GPU-parallel random restart baseline | 10.6641 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9049.78 | 0.0945442 |
| weighted | synthetic_smoke | QUBO/quadratized local search baseline | 11 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0 | 1 | 9051.02 | 0.142056 |
| weighted | synthetic_smoke | Stress-only reserve heuristic baseline | 472.712 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 0 | 0 | 0.0890736 | 1 | 8997.16 | 1.45411e-05 |
| weighted | synthetic_smoke | DifferentialEvolutionOptimizer | 2603.42 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci | 738.944 | 16 | 0.110927 | 0.874059 | 3398.79 | 0.00498875 |
