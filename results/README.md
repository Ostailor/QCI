# Results

This directory is reserved for generated metrics, figures, manifests, and QCi payload exports.

The reproduction command `python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8` writes CSV metrics,
figures, model statistics, QCi payload JSON files, and `run_manifest.json` here. Generated
values are produced by the code paths in `src/cmpo/` and should be refreshed before using
the repository for Phase 2 reporting.

The optional public-benchmark adapter command `python scripts/run_benchmark.py --seed 42 --quick`
writes benchmark-derived evidence under `results/benchmarks/pglib_case5_pjm/`.

The paper-artifact command `python scripts/build_phase2_paper.py` writes
`results/phase2_paper.md`, submission-facing Markdown files, `submission_package/`, and
derived tables under `analysis/paper/`.

The conservative hardware-start command
`python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small`
writes self-contained small-run metrics, payloads, and generated data under `results/qci_small/`.
The standalone export command writes to `results/qci_export/` so it does not overwrite
main-run `results/model_stats.csv` or `results/qci_payloads/`.
