# Restorers CMPO Phase 2 Paper Draft

## Abstract

Restorers proposes the Cubic Microgrid Patch Optimizer (CMPO) as a Phase 2 pre-QCi workflow for resilient microgrid cost optimization. The prototype generates deterministic synthetic microgrid patch cases, evaluates contingencies, builds degree-3 Hamiltonian/polynomial models with native cubic generator costs, compares classical baselines, and exports QCi/Dirac-3-ready JSON payloads. The main synthetic run used seed 42, four microgrids, a six-hour horizon, eight scenarios, two selected overlapping patches, and 16 exported payloads. No proprietary grid data is used, no live QCi hardware execution has been performed, and no quantum advantage is claimed. A public-benchmark-derived PGLib case5-PJM adapter adds an external reference stress case without claiming AC OPF reproduction.

## Contributions

1. A reproducible resilient microgrid dataset and scenario generator covering normal operation, renewable shortfall, demand surge, PCC failure, local generator failure, forced islanding, restoration, and combined stress.
2. A microgrid design stage that selects overlapping islandable patches and records upgrade-cost and coverage metrics.
3. A bounded polynomial/Hamiltonian builder that preserves cubic generation costs while keeping exported instances at degree <= 3.
4. Classical baselines and a clearly labeled pre-QCi CMPO-local polynomial search proxy.
5. A QCi export layer with model statistics, coefficient-scaling metadata, and a documented Phase 3 `eqc-models` adapter path.
6. A PGLib-OPF case5-PJM-derived benchmark adapter with pinned provenance and benchmark-specific results.

## Experimental Setup

The main case is deterministic synthetic research data. It does not use private utility data. The benchmark case adapts public PGLib-OPF case5-PJM anchors into the CMPO microgrid contract: bus active loads, generator capacities/cost slopes, and branch ratings are reused as anchors; PV, BESS, PCC, critical-load, and upgrade fields are deterministic synthetic additions. The benchmark provenance is recorded in `manifests/upstream/pglib-opf-case5-pjm.json`.

The compared methods are GreedyCriticalLoadFirst, SLSQPDispatchOptimizer, DifferentialEvolutionOptimizer on the main non-quick run, and CMPO-local polynomial search. CMPO-local is a CPU-only pre-QCi local polynomial-search proxy, not QCi hardware execution.

## Main Results

| method_name | expected_operating_cost | risk_adjusted_cost | critical_load_served_fraction | energy_not_served_kwh | feasibility_rate | median_runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| DifferentialEvolutionOptimizer | 1.544e+04 | 1.786e+04 | 0.6507 | 7.968e+04 | 1 | 0.2561 |
| SLSQPDispatchOptimizer | 2.687e+04 | 3.269e+04 | 0.9668 | 1.413e+04 | 0.4375 | 1.183 |
| CMPO-local polynomial search | 4.179e+04 | 4.787e+04 | 0.9773 | 1.601e+04 | 0.4375 | 1.742 |
| GreedyCriticalLoadFirst | 4.18e+04 | 4.787e+04 | 0.9662 | 2.14e+04 | 1 | 0 |

Best expected operating cost in the main run is `DifferentialEvolutionOptimizer` at `15437.7` computed cost units. Best average critical-load served fraction is `CMPO-local polynomial search` at `0.9773`. Results are mixed: differential evolution is strongest on expected cost in the main non-quick run, while CMPO-local is strongest on critical-load-served fraction but needs better feasibility repair. This separation is useful for Phase 3: the cheapest repaired dispatch is not automatically the best resilience outcome, so QCi evaluation should compare both cost and resilience metrics.

## Scenario Stress Summary

| scenario | critical_load_served_fraction | energy_not_served_kwh | critical_energy_not_served_kwh | feasibility_rate |
| --- | --- | --- | --- | --- |
| combined_high_stress | 0.7326 | 4.597e+04 | 1.68e+04 | 1 |
| storm_forced_islanding | 0.8903 | 2.545e+04 | 6249 | 1 |
| restoration | 0.8798 | 1.176e+04 | 5726 | 0.625 |
| pcc_failure | 0.8981 | 1.167e+04 | 5163 | 0.75 |
| local_generator_failure | 0.9045 | 1.057e+04 | 4790 | 0.75 |
| normal | 0.9349 | 8832 | 3142 | 0.625 |
| demand_surge | 0.9538 | 8549 | 2723 | 0.5 |
| renewable_shortfall | 0.9282 | 8418 | 3531 | 0.5 |

The scenario table is derived from `results/scenario_results.csv`. It highlights where unserved energy and critical-energy-not-served appear after repair, rather than relying only on aggregate expected cost.

## Public Benchmark Result

| method_name | expected_operating_cost | risk_adjusted_cost | critical_load_served_fraction | energy_not_served_kwh | feasibility_rate | median_runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| SLSQPDispatchOptimizer | 3038 | 3857 | 1 | 0.1888 | 0.25 | 0.1399 |
| CMPO-local polynomial search | 3053 | 3886 | 1 | 61.75 | 1 | 0.2244 |
| GreedyCriticalLoadFirst | 3053 | 3886 | 1 | 116 | 1 | 0 |

The adapted PGLib case5-PJM run exports `8` benchmark payloads. Best expected operating cost on the benchmark is `SLSQPDispatchOptimizer` at `3038.49` computed cost units. This strengthens Phase 2 by showing the CMPO workflow can ingest a public benchmark-derived case while preserving the same metrics and export contract.

## Cubic Cost Evidence

| method_name | model_variant | true_cubic_cost | true_cubic_cost_difference_vs_cubic | dispatch_profile_l1_difference_vs_cubic | critical_load_served_fraction | energy_not_served_kwh |
| --- | --- | --- | --- | --- | --- | --- |
| CMPO-local polynomial search | cubic | 7089 | 0 | 0 | 1 | 0 |
| CMPO-local polynomial search | quadratic_approximation | 7089 | 0 | 0 | 1 | 0 |
| GreedyCriticalLoadFirst | cubic | 7089 | 0 | 0 | 1 | 0 |
| GreedyCriticalLoadFirst | quadratic_approximation | 7089 | 0 | 0 | 1 | 0 |
| SLSQPDispatchOptimizer | cubic | 412.7 | 0 | 0 | 1 | 0.003023 |
| SLSQPDispatchOptimizer | quadratic_approximation | 405 | -7.708 | 5.882 | 1 | 0 |

The cubic-vs-quadratic experiment produced nonzero true-cubic cost differences for at least one optimized solution, showing that approximation choice can change dispatch economics under the true cubic objective. Final comparisons evaluate both variants under the true cubic objective in `results/cubic_vs_quadratic.csv`.

## Scaling And Phase 3 Resource Need

| n_microgrids | horizon | n_scenarios | payload_count | max_variables | max_terms | max_median_runtime_seconds | best_expected_cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 6 | 4 | 4 | 66 | 420 | 0.04714 | 6968 |
| 3 | 6 | 8 | 8 | 66 | 424 | 0.04807 | 8063 |
| 4 | 4 | 2 | 2 | 44 | 272 | 0.02143 | 2861 |
| 4 | 4 | 4 | 4 | 44 | 280 | 0.02154 | 3895 |
| 4 | 4 | 8 | 8 | 44 | 283 | 0.02233 | 4225 |
| 4 | 6 | 2 | 2 | 66 | 408 | 0.04702 | 4373 |
| 4 | 6 | 4 | 4 | 66 | 420 | 0.04755 | 6968 |
| 4 | 6 | 8 | 8 | 66 | 424 | 0.04768 | 8063 |

The largest scaling case in `results/scaling_results.csv` uses `8` scenario/patch payloads with up to `66` variables and `424` polynomial terms per Hamiltonian. That `66`-variable figure is a scaling-study one-patch figure, not the maximum main-run Hamiltonian if the main selected patches are larger. The main run reaches `198` variables and `1260` terms per Hamiltonian. The resource estimate in `results/phase3_resource_estimate.md` recommends one Dirac-3 job per scenario/patch payload and repeated stochastic solves per payload for fair comparison.

## QCi Payload Resource Summary

| experiment | payload count | max variables | median variables | max terms | max degree | intended Phase 3 use |
| --- | --- | --- | --- | --- | --- | --- |
| main synthetic run | 16 | 198 | 198 | 1260 | 3 | full synthetic evidence sweep; larger honest Hamiltonian reference |
| scaling study | 8 | 66 | 55 | 424 | 3 | size trend only; smaller than the main selected-patch run when patch sizes differ |
| PGLib case5-PJM adapted benchmark | 8 | 198 | 198 | 1236 | 3 | public-benchmark-derived stress case; not an AC OPF reproduction |
| qci_small conservative payload | 8 | 132 | 132 | 840 | 3 | initial QCi Dirac-3 smoke test before full main-run payloads |

The optional `qci_small` conservative hardware-start run is included in the resource summary and has its own metrics under `results/qci_small/`.

## Hamiltonian And Export Readiness

The main run exported `16` payloads with max degree `3`, max `198` variables, max `1260` terms, median `198` variables, and median `1232` terms. The public-benchmark run exported `8` payloads with max degree `3`. Payload terms reference declared variables and include bounds, encoding type, objective sense, scaling metadata, and scenario/patch metadata.

## Phase 3 Plan

Phase 3 should prioritize QCi Dirac-3 because CMPO preserves cubic generator costs and higher-order mode-selection terms directly. The implementation path is to connect `cmpo.qci_export.convert_to_eqc_models_format()` to the confirmed QCi `eqc-models` API, run repeated Dirac-3 solves per scenario/patch payload, and rerun the same classical baselines with identical seeds, scenarios, patches, repair logic, and metrics. The primary success criterion should be multi-metric: expected cost, critical load served, energy not served, feasibility rate, runtime, and model size.

## Non-Claims

This paper draft does not claim live QCi hardware execution, hardware quantum advantage, operational grid readiness, or private/proprietary data use. All reported numbers are generated by repository scripts and trace back to CSV files and manifests.

## Reproduction

```bash
pip install -r requirements.txt
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/build_phase2_paper.py
pytest -q
```
