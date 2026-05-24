# PGLib Case5-PJM Adapted Benchmark

## Benchmark Source

This benchmark adapts PGLib-OPF `pglib_opf_case5_pjm.m` version `v23.07` into the CMPO microgrid data contract. The upstream case is public and licensed under Creative Commons Attribution 4.0 International. The local adapter records provenance in `manifests/upstream/pglib-opf-case5-pjm.json`.

## Adaptation Scope

The adapter uses PGLib bus active loads, generator capacities, generator linear cost slopes, and branch endpoints/ratings as anchors. CMPO-specific fields such as PV, BESS, PCC limits, critical-load fractions, and upgrade options are deterministic synthetic additions. This is a benchmark-derived stress case, not an AC OPF reproduction.

## Result Table

| method | expected_cost | critical_load_served | feasibility_rate | median_runtime_seconds |
| --- | ---: | ---: | ---: | ---: |
| SLSQPDispatchOptimizer | 3038.49 | 1.0000 | 0.2500 | 0.139935 |
| CMPO-local polynomial search | 3052.61 | 1.0000 | 1.0000 | 0.224431 |
| GreedyCriticalLoadFirst | 3052.61 | 1.0000 | 1.0000 | 0 |

## Benchmark Interpretation

Best expected operating cost in this benchmark run: `SLSQPDispatchOptimizer` at `3038.49` computed cost units. Payloads exported: `8`.

## Non-Claims

This is still a CPU-only pre-QCi run. It does not claim live QCi hardware execution or quantum advantage.
