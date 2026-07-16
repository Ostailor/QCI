# Final Challenge-Aligned Dominance Analysis

Comparisons use repeat-balanced, per-benchmark normalization. Lower challenge scores are better.
The Pareto flag uses risk-adjusted cost and critical energy not served.

## Lexicographic Score

- QCi wins: 0
- QCi ties: 0
- QCi losses: 3

## Weighted Score

- QCi wins: 0
- QCi ties: 0
- QCi losses: 3

## Dataset Outcomes

| score_mode | dataset | best_qci_method | best_classical_method | qci_challenge_score | best_classical_challenge_score | qci_minus_best_classical_challenge_score | outcome | qci_on_cost_critical_ens_pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | Piecewise-linear MILP baseline | 8 | 0 | 8 | qci_loss | False |
| lexicographic | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | GreedyCriticalLoadFirst | 8 | 0 | 8 | qci_loss | False |
| lexicographic | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | Piecewise-linear MILP baseline | 4 | 0 | 4 | qci_loss | False |
| weighted | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | Piecewise-linear MILP baseline | 1304.53 | 0.0011545 | 1304.53 | qci_loss | False |
| weighted | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | Piecewise-linear MILP baseline | 1441.03 | 0.000801966 | 1441.03 | qci_loss | False |
| weighted | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | Piecewise-linear MILP baseline | 34.892 | 6.22075e-05 | 34.8919 | qci_loss | False |
