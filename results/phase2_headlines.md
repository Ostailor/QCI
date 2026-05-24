# Phase 2 Headlines

## Evidence Boundary

The prototype uses synthetic, reproducible data and no proprietary grid data. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed. CMPO-local is a pre-QCi local polynomial-search proxy only.

## Main Benchmark Method Comparison

| method | expected operating cost | risk-adjusted cost | critical-load served fraction | energy not served | feasibility rate | median runtime |
| --- | --- | --- | --- | --- | --- | --- |
| DifferentialEvolutionOptimizer | 1.544e+04 | 1.786e+04 | 0.6507 | 7.968e+04 | 1 | 0.2561 |
| SLSQPDispatchOptimizer | 2.687e+04 | 3.269e+04 | 0.9668 | 1.413e+04 | 0.4375 | 1.183 |
| CMPO-local polynomial search | 4.179e+04 | 4.787e+04 | 0.9773 | 1.601e+04 | 0.4375 | 1.742 |
| GreedyCriticalLoadFirst | 4.18e+04 | 4.787e+04 | 0.9662 | 2.14e+04 | 1 | 0 |

## Current Main-Run Finding

Best expected operating cost is `DifferentialEvolutionOptimizer` at `15437.7`. Best critical-load served fraction is `CMPO-local polynomial search` at `0.9773`.

The main result is mixed: differential evolution is strongest on expected cost in the full main run when enabled, while CMPO-local is strongest on critical-load-served fraction but still needs better feasibility repair before any hardware-performance claim.

## Hamiltonian Size And Export Readiness

The main run exports degree-3 polynomial payloads for later QCi Dirac-3 / `eqc-models` adaptation. Main-run Hamiltonians reach `198` variables and `1260` terms, so those larger sizes should be stated honestly and not replaced by smaller scaling-study figures.

## Phase 3 Direction

The Phase 3 resource request should prioritize QCi Dirac-3 because the model preserves cubic generator costs and higher-order mode-selection terms directly. Classical baselines for fair comparison include greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search.
