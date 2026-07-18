# IRC-CMPO Final Pre-Queue Root-Cause Repair and Go/No-Go Audit

**IRC_CMPO_READY_FOR_QCI: YES**

No QCi job was submitted during this audit. Historical artifacts remain untouched.

## Historical mode and integer transport

- Historical response modes: `{"integer_qudit": 0, "normalized_continuous_qudit": 1007, "unknown": 8}`.
- Integer adapter dry run: `PASS`.
- Final master domains: `33` binary variables, `66` total num_levels.
- Requested integer mode: `sample-hamiltonian-integer` / `dirac-3`; no `sum_constraint`.

## True recourse dataset

- Evidence: `{"failures": 0, "successful_labels": 3000, "unique_signatures": 3000}`.
- Gate: `PASS`.
- Labels use fixed public upgrades, both SLSQP and piecewise-linear MILP paths, overlap consensus, full-system active-power projection, eight training scenarios, and ten held-out contingencies.

## Surrogate gates

- `critical_ens`: nRMSE `0.03148215711532562`, Spearman `0.8140945642191901`, top-decile recall `1.0`, Pareto recall `1.0`, gate `PASS`.
- `critical_infrastructure_outage_hours`: nRMSE `0.11300478811435767`, Spearman `0.8083944094507041`, top-decile recall `1.0`, Pareto recall `1.0`, gate `PASS`.
- `heldout_total_ens`: nRMSE `0.005360475017589203`, Spearman `0.994713483858839`, top-decile recall `0.9942857142857143`, Pareto recall `1.0`, gate `PASS`.
- `maximum_customers_unserved`: nRMSE `0.01189204657005113`, Spearman `0.8145620847749091`, top-decile recall `1.0`, Pareto recall `1.0`, gate `PASS`.
- `total_ens`: nRMSE `0.03148215711532563`, Spearman `0.8140945642191901`, top-decile recall `1.0`, Pareto recall `1.0`, gate `PASS`.

## Hardware scaling and offline ground-state validation

- Dynamic-range gate: `PASS`.
- Exact Hamiltonian gate: `PASS`.
- Local stochastic gate: `PASS`.
- Strict-stop disposition: `none`.
- No returned or local sample was rounded, repaired, or projected into a binary portfolio.

## Remaining known limitations

- Paid Dirac-3 integer behavior remains untested until the three smoke jobs are explicitly run after a YES decision.
- OpenDSS unbalanced-AC replay is recorded separately from this active-power recourse dataset and is not a surrogate label.
- The GPU-compatible random feasible generator used its deterministic NumPy CPU path on this workstation.
- Earlier normalized-continuous QCi results remain valid only as a continuous-solver misconfiguration ablation.

## Gate summary

```text
HISTORICAL_MODE_AUDIT: PASS
INTEGER_ADAPTER_DRY_RUN: PASS
TRUE_RECOURSE_VALID: PASS
SURROGATE_VALID: PASS
DYNAMIC_RANGE_VALID: PASS
EXACT_HAMILTONIAN_VALID: PASS
LOCAL_STOCHASTIC_VALID: PASS
IRC_CMPO_READY_FOR_QCI: YES
```
