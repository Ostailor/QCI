# IRC-CMPO Final Pre-Queue Root-Cause Repair and Go/No-Go Audit

**IRC_CMPO_READY_FOR_QCI: NO**

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

- `critical_ens`: nRMSE `0.0989024595656845`, Spearman `0.7338203586930439`, top-decile recall `0.9848156182212582`, Pareto recall `1.0`, gate `FAIL`.
- `critical_infrastructure_outage_hours`: nRMSE `0.13554144935770526`, Spearman `0.7345640097278865`, top-decile recall `0.9956616052060737`, Pareto recall `1.0`, gate `FAIL`.
- `heldout_total_ens`: nRMSE `0.005360475017589203`, Spearman `0.98975936305977`, top-decile recall `0.8852459016393442`, Pareto recall `0.3333333333333333`, gate `FAIL`.
- `maximum_customers_unserved`: nRMSE `0.015817784832539757`, Spearman `0.7366460494216607`, top-decile recall `0.9956616052060737`, Pareto recall `1.0`, gate `FAIL`.
- `total_ens`: nRMSE `0.09890245956568475`, Spearman `0.7338203586930439`, top-decile recall `0.9848156182212582`, Pareto recall `1.0`, gate `FAIL`.

## Hardware scaling and offline ground-state validation

- Dynamic-range gate: `NOT RUN (reported as FAIL for readiness)`.
- Exact Hamiltonian gate: `NOT RUN (reported as FAIL for readiness)`.
- Local stochastic gate: `NOT RUN (reported as FAIL for readiness)`.
- Strict-stop disposition: `surrogate_test_gates_failed; payload construction, coefficient quantization, exact Hamiltonian solving, and stochastic proxy were not run`.
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
SURROGATE_VALID: FAIL
DYNAMIC_RANGE_VALID: FAIL
EXACT_HAMILTONIAN_VALID: FAIL
LOCAL_STOCHASTIC_VALID: FAIL
IRC_CMPO_READY_FOR_QCI: NO
```
