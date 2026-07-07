# QCi Metric Mismatch Diagnostic

This diagnostic reads only existing Phase 3 result artifacts. It does not run new QCi jobs, does not edit raw results, and does not fabricate missing metrics.

## Inputs Read

- `results/phase3/final_tables/final_tables.md`
- `results/phase3/final_tables/pareto_frontier.csv`
- `results/phase3/final_tables/win_tie_loss_matrix.csv`
- `results/phase3/final_tables/encoding_efficiency.csv`
- `results/phase3/public_benchmarks/pglib_case5_pjm/decoded/qci_repeat_metrics.csv`
- `results/phase3/public_benchmarks/pglib_case5/baselines/payload_summary.csv`
- `results/phase3/public_benchmarks/pglib_case14_ieee/decoded/qci_repeat_metrics.csv`
- `results/phase3/public_benchmarks/pglib_case14/baselines/payload_summary.csv`
- `results/phase3/public_benchmarks/pglib_case30_ieee/decoded/qci_repeat_metrics.csv`
- `results/phase3/public_benchmarks/pglib_case30/baselines/payload_summary.csv`
- `results/phase3/public_benchmarks/pglib_case57/baselines/payload_summary.csv` was inspected as a classical-only reference; it is not included in QCi-executed comparisons because no matching QCi decoded metrics exist.

## Executive Diagnosis

The current QCi results do not showcase CMPO because the hardware energy ranking is not aligned with the repaired Phase 3 resilience metrics. Every QCi raw sample is infeasible before repair, repair makes all decoded samples feasible, and the QCi objective is therefore optimizing a pre-repair surrogate that does not reliably rank repaired critical-load service, critical ENS, customer-unserved, or infrastructure-outage metrics. case5 is reported as a final scalar risk-cost win, but the same final artifacts show it loses critical-load served fraction, critical ENS, max customers unserved, and infrastructure outage proxy against MILP or other classical baselines. case14 and case30 are dominated by two compounding issues: QCi-fit decomposition breaks full 198-variable benchmark payloads into smaller single/two-patch subproblems, and the sample chosen by QCi energy often favors low-cost/high-shed repaired states. The smallest CMPO improvement is a V2 scoring layer: rebalance critical-load/max-unserved penalties, improve coefficient scaling, repair-then-rerank all QCi samples by the final Phase 3 metrics, and rebuild QCi-fit decomposition to prefer 132-variable two-patch/full-horizon cuts over 66-variable single-bus cuts.

## Final Table Risk-Cost Context

| Dataset | Final QCi Risk Cost | Best Baseline | Best Baseline Risk Cost | Final Outcome |
| --- | ---: | --- | ---: | --- |
| `pglib_case5_pjm_adapted` | 69,918.36 | Piecewise-linear MILP baseline | 77,693.48 | QCi win |
| `pglib_case14_adapted` | 30,167.73 | Piecewise-linear MILP baseline | 15,539.83 | QCi loss |
| `pglib_case30_adapted` | 28,423.21 | Piecewise-linear MILP baseline | 13,101.35 | QCi loss |

The final scalar table is not the same as resilience dominance. It is a single risk-adjusted cost view; the diagnostic below compares each required metric directly against the best baseline for that metric.

## Metric-by-Metric Comparison Against Best Baseline

Values come from `table3_scenario_stress.csv` aggregated across scenarios, except feasibility after repair, which comes from decoded QCi and baseline payload summaries. Additive outage/ENS metrics are summed across scenarios; max-unserved is the worst scenario; fraction/cost metrics are averaged across scenarios for this diagnostic table.

### pglib_case5_pjm_adapted

| Metric | Direction | QCi | Best Baseline | Best Baseline Method | Verdict | Relative Worse |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `critical_load_served_fraction` | high | 0.7985 | 1 | CMPO-local polynomial search | loss | 0.2015 |
| `critical_energy_not_served_kwh` | low | 862.4 | 0 | CMPO-local polynomial search | loss | n/a |
| `max_fraction_customers_unserved_per_hour` | low | 0.1093 | 0.001952 | Piecewise-linear MILP baseline | loss | 54.99 |
| `total_critical_infrastructure_unserved_hours_proxy` | low | 24 | 0 | CMPO-local polynomial search | loss | n/a |
| `feasibility_after_repair` | high | 1 | 1 | CMPO-local polynomial search | tie | 0 |
| `risk_adjusted_cost` | low | 883.5 | 590.4 | Piecewise-linear MILP baseline | loss | 0.4965 |
| `expected_operating_cost` | low | 764 | 590.4 | Piecewise-linear MILP baseline | loss | 0.2942 |

### pglib_case14_adapted

| Metric | Direction | QCi | Best Baseline | Best Baseline Method | Verdict | Relative Worse |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `critical_load_served_fraction` | high | 0 | 0.9657 | Piecewise-linear MILP baseline | loss | 1 |
| `critical_energy_not_served_kwh` | low | 344.8 | 115.7 | Piecewise-linear MILP baseline | loss | 1.981 |
| `max_fraction_customers_unserved_per_hour` | low | 0.1364 | 0.2482 | CMPO-local polynomial search | win | -0.4506 |
| `total_critical_infrastructure_unserved_hours_proxy` | low | 36 | 3 | CMPO-local polynomial search | loss | 11 |
| `feasibility_after_repair` | high | 1 | 1 | CMPO-local polynomial search | tie | 0 |
| `risk_adjusted_cost` | low | 133.4 | 103.1 | Piecewise-linear MILP baseline | loss | 0.2938 |
| `expected_operating_cost` | low | 111.5 | 98.29 | Piecewise-linear MILP baseline | loss | 0.1345 |

### pglib_case30_adapted

| Metric | Direction | QCi | Best Baseline | Best Baseline Method | Verdict | Relative Worse |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `critical_load_served_fraction` | high | 0 | 1 | CMPO-local polynomial search | loss | 1 |
| `critical_energy_not_served_kwh` | low | 344.8 | 0 | CMPO-local polynomial search | loss | n/a |
| `max_fraction_customers_unserved_per_hour` | low | 0.102 | 0 | CMPO-local polynomial search | loss | n/a |
| `total_critical_infrastructure_unserved_hours_proxy` | low | 36 | 0 | CMPO-local polynomial search | loss | n/a |
| `feasibility_after_repair` | high | 1 | 1 | CMPO-local polynomial search | tie | 0 |
| `risk_adjusted_cost` | low | 153.7 | 33.44 | Piecewise-linear MILP baseline | loss | 3.595 |
| `expected_operating_cost` | low | 112.6 | 33.44 | Piecewise-linear MILP baseline | loss | 2.369 |

## Sample Selection and Repair Evidence

| Dataset | Payloads | Lowest QCi Energy = Best Risk | Lowest QCi Energy = Best Critical-Served | Mean Low-E Critical Served | Mean Best Critical Served | Corr(QCi Energy, Critical Served) | Pre-Repair Violation Rate | Post-Repair Violation Rate | Median Pre-Repair Violation Magnitude |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pglib_case5_pjm_adapted` | 8 | 0 | 0 | 0.4637 | 0.9936 | 0.08593 | 1 | 0 | 4,681.41 |
| `pglib_case14_adapted` | 60 | 19 | 36 | 0.003648 | 0.3887 | 0.7562 | 1 | 0 | 11,071.67 |
| `pglib_case30_adapted` | 66 | 27 | 43 | 0.03351 | 0.3376 | 0.7195 | 1 | 0 | 11,525.98 |

Interpretation: the decoded repaired solutions are feasible, but they are not natively feasible from the QCi sample. The repair layer is doing all feasibility work after the hardware objective has already ranked samples, so post-repair resilience can diverge from QCi energy.

## Coefficient Scaling and Encoding Evidence

| Dataset | Payloads | Vars Min/Median/Max | Degree | Median Terms | Coef Min | Coef Max | Median abs(coef) | P95 abs(coef) | Scale Min/Median/Max |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `pglib_case5_pjm_adapted` | 8 | 132/132/132 | 3 | 816 | -3,832.88 | 918,185.57 | 8 | 2,932.00 | 1.089e-06/1.903e-06/3.364e-06 |
| `pglib_case14_adapted` | 60 | 66/66/132 | 3 | 420 | -898.3 | 50,439.03 | 8 | 700 | 1.983e-05/0.0001/0.0001 |
| `pglib_case30_adapted` | 66 | 66/66/132 | 3 | 412 | -902.6 | 50,922.37 | 8 | 700 | 1.964e-05/0.0001/0.0001 |

The coefficient ranges are highly compressed by scaling. case5 full payloads use scale factors near 1e-6 while case14/case30 QCi-fit payloads use roughly 2e-5 to 1e-4. Combined with large positive/negative polynomial terms and repair-after-sampling, this is consistent with the observed objective mismatch.

## Why pglib_case5 Is a Risk-Cost Win But a Resilience Loss

The final table marks `pglib_case5_pjm_adapted` as a QCi risk-adjusted-cost win: QCi risk-adjusted cost is 69,918.36 versus 77,693.48 for the piecewise-linear MILP baseline. That scalar win does not mean QCi is more resilient. The direct metric table shows QCi has lower critical-load service and higher critical ENS, max customers unserved, and infrastructure outage proxy than the best baseline. The likely mechanism is objective mismatch: QCi finds repaired states that are cheap under the current scalar cost, but the scalar risk penalty does not dominate the cost savings from shedding or underserving load. Evidence: on case5, the lowest QCi-energy sample is best risk for 0 of 8 payloads and best critical-load-served for 0 of 8 payloads, while mean critical-load served at the lowest-energy sample is only 0.464 versus 0.994 for the best repaired sample within each payload.

## case14 and case30 Closest QCi-Fit Scenarios/Patches

Closest means smallest critical-load-served gap first, then critical ENS gap and risk ratio, against the best baseline for the corresponding source full payload. These are the best places to test a CMPO V2 reranking/reweighting change before spending more QCi budget.

### pglib_case14_adapted

| Rank | Scenario | QCi Patch | Source Full Payload | Vars | QCi Critical Served | Best Baseline Critical Served | Critical Served Gap | QCi Critical ENS | Best Baseline Critical ENS | Risk Ratio |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | storm_forced_islanding | `BUS4_MG-BUS9_MG` | `storm_forced_islanding_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 0.9984 | 0.5879 | -0.4105 | 0.4227 | 231.3 | 0.5591 |
| 2 | storm_forced_islanding | `BUS1_MG-BUS2_MG` | `storm_forced_islanding_BUS14_MG-BUS1_MG-BUS2_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 0.8024 |
| 3 | storm_forced_islanding | `BUS14_MG-BUS1_MG` | `storm_forced_islanding_BUS14_MG-BUS1_MG-BUS2_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 0.9232 |
| 4 | local_generator_failure | `BUS3_MG-BUS4_MG` | `local_generator_failure_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.053 |
| 5 | demand_surge | `BUS4_MG-BUS9_MG` | `demand_surge_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.078 |
| 6 | pcc_failure | `BUS3_MG-BUS4_MG` | `pcc_failure_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.084 |
| 7 | normal | `BUS3_MG-BUS4_MG` | `normal_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.15 |
| 8 | renewable_shortfall | `BUS4_MG-BUS9_MG` | `renewable_shortfall_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.265 |
| 9 | pcc_failure | `BUS4_MG-BUS9_MG` | `pcc_failure_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.288 |
| 10 | normal | `BUS4_MG-BUS9_MG` | `normal_BUS3_MG-BUS4_MG-BUS9_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.321 |

### pglib_case30_adapted

| Rank | Scenario | QCi Patch | Source Full Payload | Vars | QCi Critical Served | Best Baseline Critical Served | Critical Served Gap | QCi Critical ENS | Best Baseline Critical ENS | Risk Ratio |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | storm_forced_islanding | `BUS1_MG-BUS2_MG` | `storm_forced_islanding_BUS1_MG-BUS2_MG-BUS30_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 0.9104 |
| 2 | renewable_shortfall | `BUS5_MG-BUS7_MG` | `renewable_shortfall_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.079 |
| 3 | storm_forced_islanding | `BUS2_MG-BUS30_MG` | `storm_forced_islanding_BUS1_MG-BUS2_MG-BUS30_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.178 |
| 4 | pcc_failure | `BUS5_MG-BUS7_MG` | `pcc_failure_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.208 |
| 5 | local_generator_failure | `BUS5_MG-BUS7_MG` | `local_generator_failure_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.245 |
| 6 | normal | `BUS5_MG-BUS7_MG` | `normal_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.251 |
| 7 | pcc_failure | `BUS2_MG-BUS5_MG` | `pcc_failure_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.635 |
| 8 | renewable_shortfall | `BUS2_MG-BUS5_MG` | `renewable_shortfall_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 1.914 |
| 9 | normal | `BUS2_MG-BUS5_MG` | `normal_BUS2_MG-BUS5_MG-BUS7_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 2.026 |
| 10 | local_generator_failure | `BUS1_MG-BUS2_MG` | `local_generator_failure_BUS1_MG-BUS2_MG-BUS30_MG` | 132 | 1 | 1 | 0 | 0 | 0 | 6.229 |

## Failure Mode Assessment

| Failure Mode | Diagnosis | Evidence |
| --- | --- | --- |
| Poor sample selection | Primary | Lowest QCi-energy samples usually do not match best repaired risk/resilience samples; case5 is 0/8 for best risk and 0/8 for best critical served, and case14/case30 energy ranking is positively correlated with critical-load served, so minimizing energy can select worse resilience. |
| Weak repair/projection | Primary interface issue | Pre-repair violation rate is 100% for all QCi-executed datasets, while post-repair violation rate is 0%; repair makes samples feasible but the QCi objective does not optimize the repaired solution. |
| Underweighted critical load | Primary | QCi loses critical-load served fraction and critical ENS on every QCi-executed dataset in the metric comparison. case14/case30 scenario-stress QCi critical-load served is 0 across all six scenarios. |
| Underweighted max-unserved constraint | Primary for case5/case30, secondary for case14 | QCi max fraction customers unserved is materially worse than the best baseline on case5 and case30. case14 is not the max-unserved failure case in this scenario-stress comparison, but the current objective still lets critical-load and infrastructure-outage losses dominate the result. |
| Bad coefficient scaling | Likely | Coefficients span from single digits to tens/hundreds of thousands before scaling; scale factors range from about 1e-6 to 1e-4, and QCi energy is not a reliable repaired-metric score. |
| Decomposition quality | Primary for case14/case30 | QCi-fit decomposes 198-variable full cases into mostly 66-variable single-bus or 132-variable two-bus patches; this loses full-patch coordination and produces many zero-critical-served subpatch results. |
| Objective mismatch | Primary | The cost scalar can reward low operating cost while still allowing critical ENS/infrastructure outage penalties that are too small relative to cost terms. |
| Runtime/repeat budget | Secondary | More samples could help only if reranked by repaired metrics; without reranking, more low-energy samples can continue selecting the wrong objective. |

## Smallest Experiment Changes Likely To Improve CMPO

1. Add repaired-metric postselection before new QCi jobs are run again: decode every returned sample, repair it, then choose the submitted repeat winner by lexicographic resilience first (`feasibility`, critical-load served, critical ENS, max-unserved, infrastructure outage proxy) and risk-adjusted cost second.
2. Reweight the CMPO objective so critical shedding and max-unserved penalties dominate ordinary operating cost. The current scalar lets a risk-cost win coexist with poor resilience, which is not the intended Phase 3 story.
3. Rebuild QCi-fit decomposition to prefer full 132-variable two-patch cuts and avoid 66-variable single-bus patches unless they are the only feasible decomposition; rank patches by critical-load mass and outage severity.
4. Normalize/scalably clip polynomial coefficients per objective block instead of one global coefficient scale; keep critical-load and max-unserved terms visible after scaling.
5. Add a no-new-QCi offline reranking experiment using the already completed QCi samples to estimate the gain from postselection before spending more Dirac-3 budget.

## Exact Files To Modify For CMPO V2

- `src/cmpo/hamiltonian_builder.py`
- `src/cmpo/qci_result_decode.py`
- `src/cmpo/repair.py`
- `src/cmpo/qci_fit_decomposition.py`
- `src/cmpo/phase3_metrics.py`
- `scripts/phase3_decode_qci.py`
- `scripts/phase3_build_qci_fit_public_payloads.py`
- `configs/phase3_qci_small.yaml`
- `configs/phase3_pglib_case14.yaml`
- `configs/phase3_pglib_case30.yaml`

## Output Artifact

- Detailed CSV: `results/phase3/diagnostics/qci_failure_modes.csv`

CMPO_V2_NEEDED: YES

Exact files to modify are listed in the section above.
