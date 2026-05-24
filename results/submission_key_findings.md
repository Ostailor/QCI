# Submission Key Findings

- The prototype uses deterministic synthetic data and no proprietary grid data.
- No live QCi hardware execution has been performed yet, and no quantum advantage is claimed.
- The repository exports degree-3 polynomial payloads for later Dirac-3 / `eqc-models` adaptation.
- Classical baselines include greedy dispatch, SLSQP, differential evolution when enabled, and CMPO-local search.
- Main-run results are mixed: `DifferentialEvolutionOptimizer` is best by expected operating cost, while `CMPO-local polynomial search` is best by critical-load served fraction.
- The Phase 3 resource request should prioritize QCi Dirac-3 because CMPO preserves cubic generator costs and higher-order mode-selection terms directly.

- The optional `qci_small` run provides a conservative hardware-start payload set; its best expected-cost method is `SLSQPDispatchOptimizer` and its best critical-load method is `SLSQPDispatchOptimizer`.
