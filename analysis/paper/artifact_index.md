# Phase 2 Paper Artifact Index

## Manifest Rows

| run_name | manifest_path | dataset_source | seed | horizon | n_scenarios | quick | payload_count | summary_metrics_csv | scenario_results_csv | model_stats_csv | phase2_headlines_md |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic_default | results/run_manifest.json | deterministic synthetic CMPO case | 42 | 6 | 8 | False | 16 | results/summary_metrics.csv | results/scenario_results.csv | results/model_stats.csv | results/phase2_headlines.md |
| pglib_case5_pjm_adapted | results/benchmarks/pglib_case5_pjm/benchmark_manifest.json | PGLib-OPF case5-PJM adapted CMPO benchmark | 42 | 6 | 4 | True | 8 | results/benchmarks/pglib_case5_pjm/summary_metrics.csv | results/benchmarks/pglib_case5_pjm/scenario_results.csv | results/benchmarks/pglib_case5_pjm/model_stats.csv | results/benchmarks/pglib_case5_pjm/phase2_headlines.md |

## Generated Tables

- `benchmark_results_csv`: `analysis/paper/tables/benchmark_results.csv`
- `benchmark_results_md`: `analysis/paper/tables/benchmark_results.md`
- `cubic_vs_quadratic_csv`: `analysis/paper/tables/cubic_vs_quadratic.csv`
- `cubic_vs_quadratic_md`: `analysis/paper/tables/cubic_vs_quadratic.md`
- `main_results_csv`: `analysis/paper/tables/main_results.csv`
- `main_results_md`: `analysis/paper/tables/main_results.md`
- `scaling_resource_summary_csv`: `analysis/paper/tables/scaling_resource_summary.csv`
- `scaling_resource_summary_md`: `analysis/paper/tables/scaling_resource_summary.md`
- `scenario_stress_summary_csv`: `analysis/paper/tables/scenario_stress_summary.csv`
- `scenario_stress_summary_md`: `analysis/paper/tables/scenario_stress_summary.md`
- `submission_method_comparison_csv`: `analysis/paper/tables/submission_method_comparison.csv`
- `submission_method_comparison_md`: `analysis/paper/tables/submission_method_comparison.md`
- `submission_platform_comparison_csv`: `analysis/paper/tables/submission_platform_comparison.csv`
- `submission_platform_comparison_md`: `analysis/paper/tables/submission_platform_comparison.md`
- `submission_resource_summary_csv`: `analysis/paper/tables/submission_resource_summary.csv`
- `submission_resource_summary_md`: `analysis/paper/tables/submission_resource_summary.md`
- `submission_scenario_stress_csv`: `analysis/paper/tables/submission_scenario_stress.csv`
- `submission_scenario_stress_md`: `analysis/paper/tables/submission_scenario_stress.md`

## Primary Result Files

- `results/summary_metrics.csv`
- `results/scenario_results.csv`
- `results/model_stats.csv`
- `results/scaling_results.csv`
- `results/cubic_vs_quadratic.csv`
- `results/phase2_headlines.md`
- `results/phase3_resource_estimate.md`
- `results/benchmarks/pglib_case5_pjm/benchmark_report.md`

## Regeneration Command

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
python scripts/build_phase2_paper.py
```

All tables in `analysis/paper` are derived from manifests and CSV outputs under `results`.
