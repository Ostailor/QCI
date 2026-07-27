# IRC-CMPO Offline Validation Gate

**IRC_CMPO_READY_FOR_QCI: YES**

This report records the offline gate that preceded the paid Dirac-3 run. The
subsequent execution completed successfully; final execution evidence is in
`qci/job_status.csv`, `qci/native_evaluation_summary.json`, and `final/`.

## Validated Before Submission

- The final master contains 33 bounded binary variables and 66 total levels.
- Every submitted Hamiltonian has maximum degree 3.
- The true-recourse dataset, surrogate quality, coefficient dynamic range,
  exact Hamiltonian checks, and local stochastic checks passed.
- Native integer samples are decoded directly. No rounding, repair, or
  projection is used for the reported IRC-CMPO portfolios.
- The readiness gate is retained in `preflight_summary.json` because the live
  submission command checks it before allowing paid execution.

## Completed Execution

- Platform: QCi Dirac-3 integer sample-Hamiltonian workflow.
- Jobs: 8 completed, 0 failed.
- Samples: 660 native integer samples.
- Final lambda sweep: 6 of 6 reported levels reached the exact Hamiltonian
  optimum.
- GPU comparator: qBraid NVIDIA L4 with CuPy/CUDA, recorded under
  `baselines/gpu/`.

## Gate Summary

```text
TRUE_RECOURSE_VALID: PASS
SURROGATE_VALID: PASS
DYNAMIC_RANGE_VALID: PASS
EXACT_HAMILTONIAN_VALID: PASS
LOCAL_STOCHASTIC_VALID: PASS
IRC_CMPO_READY_FOR_QCI: YES
QCI_EXECUTION: 8 COMPLETED / 0 FAILED
```
