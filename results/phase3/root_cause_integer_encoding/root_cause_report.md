# QCi integer-encoding root-cause report

This bundle is generated from preserved QCi request and response JSON. It does not modify, relabel, or replace historical results. All affected results remain available as a **continuous-solver misconfiguration ablation** and must not be presented as native integer IRC-CMPO evidence.

## Finding

The historical adapter submitted `sample-hamiltonian`, which selected QCi's `normalized_qudit_hamiltonian_optimization` problem with the `dirac-3_normalized_qudit` device. That workflow carried a `sum_constraint` and returned continuous coordinates. It did not exercise `qudit_hamiltonian_optimization` / `dirac-3_qudit` with declared `num_levels`.

Source evidence: `src/cmpo/qci_client_adapter.py` hard-coded `job_type="sample-hamiltonian"`. The installed historical transport version was `qci-client==5.0.0`, whose generated job bodies disclose the normalized problem/device pair.

The qci-client job body persisted in these artifacts does not retain a literal `job_type` field. Where absent, `job_type` in the CSV is explicitly marked as inferred from the disclosed normalized or integer problem config; the pinned legacy adapter source supplies the independent hard-coded `sample-hamiltonian` evidence.

Response-mode counts derived from `response_mode_audit.csv`:

- normalized continuous qudit jobs: 1007
- integer qudit jobs: 0
- unknown-mode response artifacts: 8
- raw samples in normalized continuous responses: 9845
- integral raw samples in normalized continuous responses: 0

Submission-mode counts derived from preserved requests plus response-only artifacts:

- normalized continuous qudit jobs submitted: 1382
- integer qudit jobs submitted: 0
- unknown-mode jobs: 8

Request-only evidence is retained: 375 requests have no sibling response. Request configurations alone classify 1381 normalized-continuous, 0 integer, and 9 unknown.

The Budget Master V2 subset contains 18 jobs, 540 raw samples, and 67140 raw coordinates. Natively integral samples: 0/540. Fractional or invalid coordinates: 54208/67140. These projected portfolios are ablation inputs only, not native integer solutions.

No preserved request explicitly supplied `sum_constraint` (0 requests); the server-reported normalized responses supplied it in 1007 responses, with the historical effective value 10000. No response disclosed integer `num_levels`.

Across submitted polynomials the smallest observed nonzero magnitude is 2.09805e-20, the largest is 25000, and the largest within-job max/min ratio is 4.76633e+19. 18 submitted jobs contain a nonzero coefficient at or below 1e-13. These are measured artifact values, not reconstructed coefficients.

The integer count is based only on responses disclosing `qudit_hamiltonian_optimization` or `dirac-3_qudit`. Unknown responses are never assumed integer.

## Consequences

1. Projected or rounded portfolios are post-processing products and are never counted as natively feasible QCi samples.
2. Continuous responses containing `normalized_qudit_hamiltonian_optimization`, `dirac-3_normalized_qudit`, or `sum_constraint` are rejected for integer experiments.
3. The former hard-budget squared penalty compressed other coefficient families; the exact submitted extrema and ratios are recorded in `coefficient_dynamic_range_audit.csv`.
4. The former technology-weighted `log1p(capacity)` benefit is a heuristic. IRC-CMPO gates hardware use on a degree-at-most-three surrogate fitted to common-recourse outcomes.

## Artifact contract

- `response_mode_audit.csv` contains every discoverable QCi response and the inspected problem/device mode, job type, constraint/domain declarations, native integrality, bounds, and solution extrema.
- `affected_qci_runs.csv` is the exact normalized-continuous subset.
- `coefficient_dynamic_range_audit.csv` traces coefficient extrema to each sibling raw request when present.

Integer-mode rows: 0. Unknown-mode rows: 8. No historical artifact was overwritten.
