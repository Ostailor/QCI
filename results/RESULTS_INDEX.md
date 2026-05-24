# CMPO Phase 2 Results Index

This file lists the generated result artifacts for the Restorers CMPO Phase 2 prototype. The files are produced by the repository scripts, not hand-entered result tables.

## Primary Phase 2 Reports

| File | Purpose |
| --- | --- |
| `results/phase2_paper.md` | Paper-style Phase 2 draft built from saved manifests and CSV outputs. |
| `results/phase2_headlines.md` | Judge-facing headline summary generated from main run metrics. |
| `results/phase3_resource_estimate.md` | Phase 3 QCi Dirac-3 resource estimate from scaling evidence. |
| `results/submission_tables.md` | Judge-ready Markdown tables for the final 3-page write-up. |
| `results/submission_key_findings.md` | Concise findings and claim boundaries for the write-up. |
| `results/submission_limitations.md` | Limitations and judge risk checklist. |
| `results/run_manifest.json` | Main run manifest with seed, horizon, scenarios, selected patches, output paths, and payload list. |
| `results/README.md` | Notes for the generated results directory. |

## Main Synthetic Case Metrics

| File | Purpose |
| --- | --- |
| `results/summary_metrics.csv` | Method-level aggregate metrics: expected cost, risk-adjusted cost, load served, energy not served, feasibility, runtime, and model-size summary. |
| `results/scenario_results.csv` | Scenario/patch/method-level raw and repaired result metrics. |
| `results/scaling_results.csv` | Scaling-study rows for scenario count, horizon, microgrid count, method, runtime, cost, and model size. |
| `results/model_stats.csv` | Hamiltonian export statistics: variable count, term count, degree, encoding counts, and coefficient scaling. |
| `results/cubic_vs_quadratic.csv` | Cubic-vs-quadratic generator-cost experiment with true-cubic evaluation columns. |
| `results/microgrid_design.csv` | Candidate/selected patch design and feasibility records. |
| `results/upgrade_plan.csv` | Selected upgrade actions and costs from the design stage. |
| `results/design_summary.json` | Design-stage summary metrics and selected patches. |

## Main Synthetic Case Figures

| File | Purpose |
| --- | --- |
| `results/figures/cost_by_method.png` | Expected operating cost by method. |
| `results/figures/critical_load_served_by_method.png` | Critical load served fraction by method. |
| `results/figures/energy_not_served_by_scenario.png` | Energy not served by scenario. |
| `results/figures/feasibility_rate_by_method.png` | Feasibility rate by method. |
| `results/figures/runtime_by_method.png` | Runtime by method. |
| `results/figures/scenario_scaling.png` | Scenario scaling plot. |
| `results/figures/runtime_scaling.png` | Runtime scaling plot from `run_scaling.py`. |
| `results/figures/cubic_vs_quadratic_dispatch.png` | Dispatch profile difference for cubic-vs-quadratic experiment. |
| `results/figures/cubic_vs_quadratic_cost_error.png` | True cubic cost error for cubic-vs-quadratic experiment. |

## Main QCi Payload Exports

There are 16 main synthetic-case QCi payload JSON files in `results/qci_payloads/`.

| File |
| --- |
| `results/qci_payloads/normal_MG1-MG2-MG3.json` |
| `results/qci_payloads/renewable_shortfall_MG1-MG2-MG3.json` |
| `results/qci_payloads/demand_surge_MG1-MG2-MG3.json` |
| `results/qci_payloads/pcc_failure_MG1-MG2-MG3.json` |
| `results/qci_payloads/local_generator_failure_MG1-MG2-MG3.json` |
| `results/qci_payloads/storm_forced_islanding_MG1-MG2-MG3.json` |
| `results/qci_payloads/restoration_MG1-MG2-MG3.json` |
| `results/qci_payloads/combined_high_stress_MG1-MG2-MG3.json` |
| `results/qci_payloads/normal_MG1-MG2-MG4.json` |
| `results/qci_payloads/renewable_shortfall_MG1-MG2-MG4.json` |
| `results/qci_payloads/demand_surge_MG1-MG2-MG4.json` |
| `results/qci_payloads/pcc_failure_MG1-MG2-MG4.json` |
| `results/qci_payloads/local_generator_failure_MG1-MG2-MG4.json` |
| `results/qci_payloads/storm_forced_islanding_MG1-MG2-MG4.json` |
| `results/qci_payloads/restoration_MG1-MG2-MG4.json` |
| `results/qci_payloads/combined_high_stress_MG1-MG2-MG4.json` |

## Conservative QCi-Friendly Payloads

The optional `qci_small` run writes a smaller self-contained experiment under `results/qci_small/`.

| File | Purpose |
| --- | --- |
| `results/qci_small/run_manifest.json` | Small-run manifest. |
| `results/qci_small/summary_metrics.csv` | Small-run method metrics. |
| `results/qci_small/model_stats.csv` | Small-run Hamiltonian statistics. |
| `results/qci_small/qci_payloads/*.json` | Conservative initial Phase 3 QCi payloads. |
| `results/qci_small/data/` | Generated synthetic data used by the small run. |

## Standalone Export-Only Payloads

`scripts/export_qci_payloads.py` writes export-only artifacts under `results/qci_export/` so it does not overwrite the main run's `results/model_stats.csv` or `results/qci_payloads/`.

| File | Purpose |
| --- | --- |
| `results/qci_export/model_stats.csv` | Standalone export-only Hamiltonian statistics. |
| `results/qci_export/qci_payloads/*.json` | Standalone export-only payload files. |

## Public Benchmark Results

These files are generated by the adapted PGLib case5-PJM benchmark path.

| File | Purpose |
| --- | --- |
| `results/benchmarks/pglib_case5_pjm/benchmark_report.md` | Benchmark-specific report and non-claims. |
| `results/benchmarks/pglib_case5_pjm/benchmark_manifest.json` | Benchmark run manifest with provenance and output paths. |
| `results/benchmarks/pglib_case5_pjm/summary_metrics.csv` | Benchmark method-level aggregate metrics. |
| `results/benchmarks/pglib_case5_pjm/scenario_results.csv` | Benchmark scenario/patch/method-level metrics. |
| `results/benchmarks/pglib_case5_pjm/scaling_results.csv` | Benchmark run scaling-style rows. |
| `results/benchmarks/pglib_case5_pjm/model_stats.csv` | Benchmark Hamiltonian statistics. |
| `results/benchmarks/pglib_case5_pjm/phase2_headlines.md` | Benchmark generated headline summary. |
| `results/benchmarks/pglib_case5_pjm/microgrid_design.csv` | Benchmark patch design records. |
| `results/benchmarks/pglib_case5_pjm/upgrade_plan.csv` | Benchmark upgrade plan records. |
| `results/benchmarks/pglib_case5_pjm/design_summary.json` | Benchmark design-stage summary. |

## Public Benchmark Figures

| File | Purpose |
| --- | --- |
| `results/benchmarks/pglib_case5_pjm/figures/cost_by_method.png` | Benchmark expected cost by method. |
| `results/benchmarks/pglib_case5_pjm/figures/critical_load_served_by_method.png` | Benchmark critical load served by method. |
| `results/benchmarks/pglib_case5_pjm/figures/energy_not_served_by_scenario.png` | Benchmark energy not served by scenario. |
| `results/benchmarks/pglib_case5_pjm/figures/feasibility_rate_by_method.png` | Benchmark feasibility rate by method. |
| `results/benchmarks/pglib_case5_pjm/figures/runtime_by_method.png` | Benchmark runtime by method. |
| `results/benchmarks/pglib_case5_pjm/figures/scenario_scaling.png` | Benchmark scenario scaling plot. |
| `results/benchmarks/pglib_case5_pjm/figures/cubic_vs_quadratic_dispatch.png` | Benchmark cubic-vs-quadratic dispatch reference plot. |

## Public Benchmark QCi Payload Exports

There are 8 adapted PGLib case5-PJM benchmark QCi payload JSON files in `results/benchmarks/pglib_case5_pjm/qci_payloads/`.

| File |
| --- |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/normal_PGLIB5_MG1-PGLIB5_MG2-PGLIB5_MG3.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/renewable_shortfall_PGLIB5_MG1-PGLIB5_MG2-PGLIB5_MG3.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/demand_surge_PGLIB5_MG1-PGLIB5_MG2-PGLIB5_MG3.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/pcc_failure_PGLIB5_MG1-PGLIB5_MG2-PGLIB5_MG3.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/normal_PGLIB5_MG1-PGLIB5_MG4-PGLIB5_MG5.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/renewable_shortfall_PGLIB5_MG1-PGLIB5_MG4-PGLIB5_MG5.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/demand_surge_PGLIB5_MG1-PGLIB5_MG4-PGLIB5_MG5.json` |
| `results/benchmarks/pglib_case5_pjm/qci_payloads/pcc_failure_PGLIB5_MG1-PGLIB5_MG4-PGLIB5_MG5.json` |

## Paper Artifact Tables

These files are generated by `python scripts/build_phase2_paper.py`.

| File | Purpose |
| --- | --- |
| `analysis/paper/artifact_index.md` | Index of paper artifact inputs, generated tables, and reproduction commands. |
| `analysis/paper/manifest_rows.csv` | Flattened manifest dataset for the paper artifacts. |
| `analysis/paper/tables/main_results.csv` | Paper-ready main synthetic-case result table. |
| `analysis/paper/tables/main_results.md` | Markdown version of main results. |
| `analysis/paper/tables/benchmark_results.csv` | Paper-ready public benchmark result table. |
| `analysis/paper/tables/benchmark_results.md` | Markdown version of benchmark results. |
| `analysis/paper/tables/scenario_stress_summary.csv` | Paper-ready scenario stress table. |
| `analysis/paper/tables/scenario_stress_summary.md` | Markdown version of scenario stress summary. |
| `analysis/paper/tables/cubic_vs_quadratic.csv` | Paper-ready cubic-vs-quadratic summary table. |
| `analysis/paper/tables/cubic_vs_quadratic.md` | Markdown version of cubic-vs-quadratic summary. |
| `analysis/paper/tables/scaling_resource_summary.csv` | Paper-ready scaling/resource summary table. |
| `analysis/paper/tables/scaling_resource_summary.md` | Markdown version of scaling/resource summary. |
| `analysis/paper/tables/submission_method_comparison.md` | Markdown main benchmark method comparison. |
| `analysis/paper/tables/submission_scenario_stress.md` | Markdown scenario stress table. |
| `analysis/paper/tables/submission_resource_summary.md` | Markdown QCi payload/resource summary. |
| `analysis/paper/tables/submission_platform_comparison.md` | Markdown platform comparison. |

## Submission Package

These files are generated by `python scripts/build_phase2_paper.py`.

| File | Purpose |
| --- | --- |
| `submission_package/phase2_methods.md` | Methods text for the final write-up. |
| `submission_package/phase2_results_summary.md` | Results summary for the final write-up. |
| `submission_package/phase2_platform_request.md` | Phase 3 platform request text. |
| `submission_package/artifacts_manifest.md` | Artifact handoff manifest. |

## Regeneration Commands

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
python scripts/build_phase2_paper.py
```

## Claim Boundaries

These files document CPU-only Phase 2 prototype evidence. They do not claim live QCi hardware execution, hardware quantum advantage, operational grid readiness, or private/proprietary utility data.
