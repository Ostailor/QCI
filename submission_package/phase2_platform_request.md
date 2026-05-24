# Phase 2 Platform Request

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

Phase 3 should prioritize QCi Dirac-3 because the CMPO model preserves cubic generator costs and higher-order mode-selection terms directly. The conservative request is to start with `results/qci_small/qci_payloads/*.json`, then expand to the full main-run payloads after job behavior is understood.

The main run reaches `198` variables and `1260` terms per Hamiltonian. Smaller `qci_small` payload sizes should be described as conservative initial hardware requests, not as the maximum observed model size.
