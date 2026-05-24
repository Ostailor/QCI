# Phase 2 Results Summary

The prototype uses synthetic, reproducible data and no proprietary grid data. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.

## Main Benchmark Method Comparison

| method | expected operating cost | risk-adjusted cost | critical-load served fraction | energy not served | feasibility rate | median runtime |
| --- | --- | --- | --- | --- | --- | --- |
| DifferentialEvolutionOptimizer | 1.544e+04 | 1.786e+04 | 0.6507 | 7.968e+04 | 1 | 0.2561 |
| SLSQPDispatchOptimizer | 2.687e+04 | 3.269e+04 | 0.9668 | 1.413e+04 | 0.4375 | 1.183 |
| CMPO-local polynomial search | 4.179e+04 | 4.787e+04 | 0.9773 | 1.601e+04 | 0.4375 | 1.742 |
| GreedyCriticalLoadFirst | 4.18e+04 | 4.787e+04 | 0.9662 | 2.14e+04 | 1 | 0 |

Main-run results are mixed: `DifferentialEvolutionOptimizer` is strongest by expected operating cost, while `CMPO-local polynomial search` is strongest by critical-load served fraction. CMPO-local needs better feasibility repair before any stronger performance claim.

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

## Conservative QCi-Friendly Run

`qci_small` was generated with `8` payloads, max `132` variables, max `840` terms, max degree `3`. Its best expected-cost method is `SLSQPDispatchOptimizer` and its best critical-load method is `SLSQPDispatchOptimizer`.
