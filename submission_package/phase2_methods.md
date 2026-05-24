# Phase 2 Methods

CMPO is a pre-QCi local prototype for resilient microgrid cost optimization. It generates deterministic synthetic microgrid cases, selects overlapping islandable patches, builds per-scenario degree-3 polynomial Hamiltonians, repairs decoded dispatches, and aggregates cost/resilience metrics.

Classical baselines are greedy critical-load-first dispatch, SLSQP local optimization, differential evolution when enabled, and CMPO-local polynomial search. CMPO-local is a CPU-only local polynomial-search proxy and is not a QCi hardware result.

The polynomial model preserves cubic generator costs and higher-order mode-selection terms directly. Payloads are exported for later QCi Dirac-3 / `eqc-models` adaptation, but no live QCi execution has been performed yet.
