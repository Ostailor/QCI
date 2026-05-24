# Phase 3 Resource Estimate

## Evidence Boundary

This is a pre-QCi local evidence package. It uses synthetic, reproducible data; no proprietary grid data is used. No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.

## Main Run Versus Scaling Study

The main Phase 2 run generated `16` scenario/patch payloads with max `198` variables, median `198` variables, max `1260` polynomial terms, and max degree `3`.

The largest scaling-study row generated `8` payloads with up to `66` variables and `424` terms per Hamiltonian. If the scaling study reports `66` variables, that number refers to the scaling-study one-patch cases only; it is not the largest observed main-run Hamiltonian when the main selected patches use more microgrids.

## Conservative Initial QCi Request

The conservative `qci_small` run exports `8` payloads with max `132` variables, median `132` variables, max `840` terms, and max degree `3`. On `qci_small`, best expected cost is `SLSQPDispatchOptimizer` (17770) and best critical-load served fraction is `SLSQPDispatchOptimizer` (1.0000).

## Platform Request

Phase 3 should prioritize QCi Dirac-3 because the CMPO formulation preserves cubic generator costs and higher-order mode-selection terms directly as degree-3 polynomial payloads. The first hardware request should run repeated stochastic solves on `qci_small` payloads, then expand to the full main-run payload set if job limits and runtime behavior are acceptable.

## Fair Classical Comparison

Classical baselines should be rerun with identical seeds, scenarios, patches, repair logic, and metric aggregation. The comparison set is greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search. CMPO-local remains a pre-QCi local polynomial-search proxy, not a quantum result.
