# Artifacts Manifest

All listed artifacts are generated from repository scripts and saved CSV/JSON manifests.

| artifact | purpose |
| --- | --- |
| results/run_manifest.json | main synthetic run manifest |
| results/summary_metrics.csv | main method metrics |
| results/scenario_results.csv | scenario-level metrics |
| results/model_stats.csv | main Hamiltonian sizes |
| results/qci_small/summary_metrics.csv | small QCi-friendly method metrics |
| results/qci_small/model_stats.csv | small QCi-friendly Hamiltonian sizes |
| results/submission_tables.md | judge-ready tables |
| results/submission_key_findings.md | concise findings and claim boundaries |
| results/submission_limitations.md | judge risk checklist |
| results/phase3_resource_estimate.md | main/scaling/qci_small resource comparison |
| results/final_tables/table1_method_comparison.csv | polished rounded method table; proves the cost, resilience, feasibility, and runtime tradeoff by method |
| results/final_tables/table1_method_comparison.md | Markdown version of polished method comparison for paper drafting |
| results/final_tables/table2_scenario_stress.csv | polished rounded scenario stress table; proves which scenarios drive unserved energy and feasibility stress |
| results/final_tables/table2_scenario_stress.md | Markdown version of polished scenario stress summary for paper drafting |
| results/final_tables/table3_resource_request.csv | polished rounded resource table; proves main, qci_small, scaling, and benchmark payload sizes |
| results/final_tables/table3_resource_request.md | Markdown version of polished QCi resource request table for paper drafting |
| results/final_tables/table4_limitations.csv | limitations table; proves the submission boundaries on hardware status, repair quality, model realism, and payload scale |
| results/final_tables/table4_limitations.md | Markdown version of limitations table for paper drafting |
| results/final_tables/table5_phase3_plan.csv | Phase 3 plan table; proves the proposed adapter, small sweep, main sweep, baseline, and report sequence |
| results/final_tables/table5_phase3_plan.md | Markdown version of Phase 3 plan table for paper drafting |
| results/final_figures/cost_vs_resilience.png | publication figure; proves the main cost/resilience tradeoff across methods |
| results/final_figures/critical_load_by_method.png | publication figure; proves critical-load served fraction by method |
| results/final_figures/runtime_by_method.png | publication figure; proves median runtime by method |
| results/final_figures/model_size_by_payload.png | publication figure; proves variable and term counts across main-run payloads |
| analysis/paper/artifact_index.md | derived paper artifact index |

## Reproduction Commands

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8
python scripts/run_scaling.py --seed 42
python scripts/run_cubic_vs_quadratic.py --seed 42
python scripts/run_benchmark.py --seed 42 --quick
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
python scripts/build_phase2_paper.py
pytest -q
```

The standalone export command writes to `results/qci_export/` so it does not overwrite main-run `results/model_stats.csv` or `results/qci_payloads/`.
