# SC-CMPO Matched Full-System Comparison

Every row below is produced after the same public benchmark, eight-scenario set, patch decomposition, overlap consensus, and classical active-power network projection. Patch-level resilience metrics are not averaged and payload counts are not treated as performance measurements. Upgrade assets are deduplicated and charged once per reconstructed system.

## System Results

| Benchmark | Method | Feasible | Critical ENS (kWh) | Total ENS (kWh) | Critical served | Max unserved | Upgrade cost | Risk-adjusted cost | Consensus residual |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| arpae_go_network_01o_020 | coordinated first-stage MILP + full-system projection reference | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | greedy resilience heuristic | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | coordinated first-stage NLP + full-system projection reference | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | piecewise-linear MILP | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | differential evolution | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | QUBO/quadratized search | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | CMPO-local polynomial search | True | 0 | 81072 | 1 | 0.0169813 | 9.38271e+08 | 9.38271e+08 | 0 |
| arpae_go_network_01o_020 | SLSQP/IPOPT | True | 0 | 30402 | 1 | 0.0169813 | 2.09303e+09 | 2.09303e+09 | 5.73847e-07 |
| ieee123_opendss | SLSQP/IPOPT | True | 50.625 | 297.709 | 0.972635 | 0.176218 | 4.53291e+06 | 4.53291e+06 | 7.36439e-16 |
| ieee123_opendss | coordinated first-stage MILP + full-system projection reference | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | coordinated first-stage NLP + full-system projection reference | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | greedy resilience heuristic | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | piecewise-linear MILP | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | differential evolution | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | QUBO/quadratized search | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| ieee123_opendss | CMPO-local polynomial search | True | 135 | 615 | 0.927027 | 0.176218 | 2.03203e+06 | 2.03203e+06 | 0 |
| pglib_case14_ieee | SLSQP/IPOPT | True | 9825 | 9825 | 0.958597 | 0.101158 | 8.21125e+08 | 8.21126e+08 | 2.88444e-16 |
| pglib_case14_ieee | coordinated first-stage NLP + full-system projection reference | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | coordinated first-stage MILP + full-system projection reference | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | greedy resilience heuristic | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | piecewise-linear MILP | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | differential evolution | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | QUBO/quadratized search | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case14_ieee | CMPO-local polynomial search | True | 26200 | 26200 | 0.889591 | 0.101158 | 3.68098e+08 | 3.68098e+08 | 0 |
| pglib_case30_ieee | SLSQP/IPOPT | True | 11812.5 | 11812.5 | 0.954862 | 0.11115 | 6.33121e+08 | 6.33122e+08 | 8.92081e-07 |
| pglib_case30_ieee | coordinated first-stage NLP + full-system projection reference | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | greedy resilience heuristic | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | coordinated first-stage MILP + full-system projection reference | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | piecewise-linear MILP | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | differential evolution | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | QUBO/quadratized search | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |
| pglib_case30_ieee | CMPO-local polynomial search | True | 31500 | 31500 | 0.879633 | 0.11115 | 2.83818e+08 | 2.83819e+08 | 0 |

## QCi Versus Matched Classical

- `arpae_go_network_01o_020`: inconclusive; no complete decoded SC-CMPO QCi patch set passed consensus, so no QCi system score was produced.
- `ieee123_opendss`: inconclusive; no complete decoded SC-CMPO QCi patch set passed consensus, so no QCi system score was produced.
- `pglib_case14_ieee`: inconclusive; no complete decoded SC-CMPO QCi patch set passed consensus, so no QCi system score was produced.
- `pglib_case30_ieee`: inconclusive; no complete decoded SC-CMPO QCi patch set passed consensus, so no QCi system score was produced.

## Failure Gate

No metric row is written when patch coverage is incomplete, ADMM does not converge, unresolved consensus conflicts remain, scenario probabilities do not sum to one, or any scenario projection fails.
- No consensus or projection failures.

## Traceability

- Payload source: `results/phase3/sc_cmpo/qci_payloads`
- Patch solution IDs, consensus run IDs, projection run IDs, public source checksums, scenario probabilities, and upgrade asset source payloads are retained in the CSV artifacts.
- The projection is a bounded active-power network-flow feasibility reconstruction, not an AC OPF reproduction.
