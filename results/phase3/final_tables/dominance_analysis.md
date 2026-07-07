# Phase 3 Dominance Analysis

- QCi wins: 1
- QCi ties: 0
- QCi losses: 2
- Inconclusive datasets: 3
- QCi/CMPO appears on cost-resilience Pareto frontier: True

## Dataset Outcomes

| dataset | qci_method | best_baseline_method | qci_risk_adjusted_cost | best_baseline_risk_adjusted_cost | qci_minus_best_baseline | outcome | qci_on_pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | CMPO + QCi Dirac-3 | Piecewise-linear MILP baseline | 30167.7 | 15539.8 | 14627.9 | qci_loss | False |
| pglib_case30_adapted | CMPO + QCi Dirac-3 | Piecewise-linear MILP baseline | 28423.2 | 13101.4 | 15321.9 | qci_loss | False |
| pglib_case57_adapted | nan | Piecewise-linear MILP baseline | nan | 3344.14 | nan | inconclusive | False |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | Piecewise-linear MILP baseline | 69918.4 | 77693.5 | -7775.12 | qci_win | True |
| qci_small_synthetic | nan | Piecewise-linear MILP baseline | nan | 16458.1 | nan | inconclusive | False |
| synthetic_smoke | nan | Piecewise-linear MILP baseline | nan | 508.446 | nan | inconclusive | False |
