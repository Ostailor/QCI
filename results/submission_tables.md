# Submission Tables

## Main Benchmark Method Comparison

| method | expected operating cost | risk-adjusted cost | critical-load served fraction | energy not served | feasibility rate | median runtime |
| --- | --- | --- | --- | --- | --- | --- |
| DifferentialEvolutionOptimizer | 1.544e+04 | 1.786e+04 | 0.6507 | 7.968e+04 | 1 | 0.2561 |
| SLSQPDispatchOptimizer | 2.687e+04 | 3.269e+04 | 0.9668 | 1.413e+04 | 0.4375 | 1.183 |
| CMPO-local polynomial search | 4.179e+04 | 4.787e+04 | 0.9773 | 1.601e+04 | 0.4375 | 1.742 |
| GreedyCriticalLoadFirst | 4.18e+04 | 4.787e+04 | 0.9662 | 2.14e+04 | 1 | 0 |

## Scenario Stress Summary

| scenario | critical-load served fraction | energy not served | critical energy not served | feasibility rate |
| --- | --- | --- | --- | --- |
| combined_high_stress | 0.7326 | 4.597e+04 | 1.68e+04 | 1 |
| storm_forced_islanding | 0.8903 | 2.545e+04 | 6249 | 1 |
| restoration | 0.8798 | 1.176e+04 | 5726 | 0.625 |
| pcc_failure | 0.8981 | 1.167e+04 | 5163 | 0.75 |
| local_generator_failure | 0.9045 | 1.057e+04 | 4790 | 0.75 |
| normal | 0.9349 | 8832 | 3142 | 0.625 |
| demand_surge | 0.9538 | 8549 | 2723 | 0.5 |
| renewable_shortfall | 0.9282 | 8418 | 3531 | 0.5 |

## QCi Payload/Resource Summary

| experiment | payload count | max variables | median variables | max terms | max degree | intended Phase 3 use |
| --- | --- | --- | --- | --- | --- | --- |
| main synthetic run | 16 | 198 | 198 | 1260 | 3 | full synthetic evidence sweep; larger honest Hamiltonian reference |
| scaling study | 8 | 66 | 55 | 424 | 3 | size trend only; smaller than the main selected-patch run when patch sizes differ |
| PGLib case5-PJM adapted benchmark | 8 | 198 | 198 | 1236 | 3 | public-benchmark-derived stress case; not an AC OPF reproduction |
| qci_small conservative payload | 8 | 132 | 132 | 840 | 3 | initial QCi Dirac-3 smoke test before full main-run payloads |

## Platform Comparison

| platform | fit for cubic continuous model | encoding overhead | Phase 2 role | Phase 3 role |
| --- | --- | --- | --- | --- |
| QCi Dirac-3 | Strong: accepts bounded degree-3 polynomial structure directly after eqc-models adaptation. | Low to moderate: preserve quasi-continuous variables and cubic terms. | offline payload target only; no hardware execution yet. | priority platform for repeated stochastic solves on exported payloads. |
| classical NLP/MILP | Strong for NLP heuristics; exact MILP would need linearization or approximation. | Low for SLSQP/differential evolution; higher for MILP linearization. | baseline evidence and feasibility repair comparison. | fair rerun baseline with identical seeds, scenarios, patches, and metrics. |
| D-Wave/QUBO | Weaker fit because cubic and continuous terms require reduction and discretization. | High: binary expansion plus quadratization introduces auxiliary variables. | not used. | secondary comparator only if a reduced QUBO formulation is created. |
| IBM gate-based | Research fit, but needs circuit ansatz, encoding, and measurement design. | High: discretization and circuit resources are not yet estimated. | not used. | not the initial request; possible future algorithmic comparison. |
