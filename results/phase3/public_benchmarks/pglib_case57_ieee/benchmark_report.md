# pglib_case57_ieee Benchmark Report

- Source: PGLib-OPF pglib_opf_case57_ieee
- Upstream URL: https://github.com/power-grid-lib/pglib-opf
- QCi execution was run: False
- QCi execution payload type: none
- QCi not executed reason: QCi Dirac-3 rejected/limits degree-3 public payloads above 135 variables; largest full payload has 198 variables. Use qci_fit_payloads for hardware execution.
- Full payload count: 8
- Full payload maximum variables: 198
- QCi-fit payload count: 40
- QCi-fit maximum variables: 132
- QCi-fit maximum degree: 3
- Payload count: 8
- Methods summarized: CMPO-local polynomial search, DifferentialEvolutionOptimizer, GPU-parallel random restart baseline, GreedyCriticalLoadFirst, IPOPT/Pyomo nonlinear baseline, Piecewise-linear MILP baseline, QUBO/quadratized local search baseline, SLSQPDispatchOptimizer, Stress-only reserve heuristic baseline

This is a public-benchmark-derived microgrid resilience adapter, not a raw AC-OPF reproduction.
