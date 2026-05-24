# Restorers CMPO Phase 2 Prototype

This repository is Team Restorers' Phase 2 prototype for the QCi Energy Infrastructure challenge, **Cost Optimization in Resilient Power Grids**. It implements a reproducible pre-QCi workflow for the Cubic Microgrid Patch Optimizer (CMPO): generate synthetic resilient microgrid cases, form islandable patch designs, evaluate disruption scenarios, build degree-3 Hamiltonian/polynomial models, compare classical baselines, and export QCi/Dirac-3-ready payload artifacts for Phase 3 review.

## What This Repo Demonstrates

- A deterministic synthetic microgrid patch dataset with generation, PV, battery storage, PCC/tie availability, critical load, flexible load, and disruption scenarios.
- A simple microgrid design stage that selects overlapping islandable patches and records upgrade feasibility/cost evidence.
- Scenario-level dispatch experiments across normal and stressed grid conditions.
- Native cubic generator-cost terms in a bounded polynomial model.
- Classical baseline comparisons and a pre-QCi CMPO-local polynomial-search proxy.
- Offline QCi payload exports suitable for later adaptation to QCi Dirac-3 / `eqc-models`.
- Reproducible result files, plots, and tests that a judge can run locally.

## What This Repo Does Not Claim

- No live QCi hardware run has been performed yet.
- No quantum advantage is claimed.
- This is a reproducible pre-QCi benchmark and Hamiltonian export harness, not a production grid optimizer.
- Synthetic data is used for research evidence; it is not utility operational data.

## Challenge Alignment

**Microgrid design:** `src/cmpo/microgrid_design.py` identifies candidate overlapping patches, estimates islanding feasibility, and writes `results/microgrid_design.csv`, `results/upgrade_plan.csv`, and `results/design_summary.json`.

**Contingency handling:** `src/cmpo/scenarios.py` defines renewable shortfall, demand surge, PCC failure, generator failure, forced islanding, restoration, and combined stress cases.

**Scenario evaluation:** `scripts/run_all.py` evaluates selected patches across scenarios and writes `results/scenario_results.csv`.

**Hamiltonian/polynomial formulation:** `src/cmpo/polynomial.py` and `src/cmpo/hamiltonian_builder.py` build bounded degree-3 polynomial models with cubic generation cost, balance penalties, storage transition penalties, mode penalties, and outage penalties.

**Classical baselines:** `src/cmpo/baselines.py` implements greedy critical-load-first dispatch, SLSQP local optimization, differential evolution when enabled, and CMPO-local polynomial search.

**QCi/Dirac-3 resource request:** `src/cmpo/qci_export.py` exports main-run offline payloads and model statistics under `results/qci_payloads/` and `results/model_stats.csv`. `scripts/export_qci_payloads.py` writes standalone export-only payloads under `results/qci_export/` so it does not overwrite main-run evidence. `results/phase3_resource_estimate.md` summarizes resource needs.

## Quick Start

```bash
pip install -r requirements.txt
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8 --quick
pytest -q
```

The `--quick` flag keeps runtime laptop-friendly by lowering optimizer iterations and skipping differential evolution.

## Reproduce Headline Results

Run:

```bash
python scripts/run_all.py --seed 42 --n-microgrids 4 --horizon 6 --n-scenarios 8 --quick
```

Primary generated evidence:

- Headline narrative: `results/phase2_headlines.md`
- Paper-style draft: `results/phase2_paper.md`
- Summary metrics: `results/summary_metrics.csv`
- Scenario-level results: `results/scenario_results.csv`
- Scaling metrics: `results/scaling_results.csv`
- Model statistics: `results/model_stats.csv`
- QCi payloads: `results/qci_payloads/*.json`
- Figures: `results/figures/*.png`
- Run manifest: `results/run_manifest.json`

Additional evidence commands:

```bash
python scripts/run_scaling.py --seed 42 --quick
python scripts/run_cubic_vs_quadratic.py --seed 42 --quick
python scripts/run_benchmark.py --seed 42 --quick
python scripts/build_phase2_paper.py
python scripts/export_qci_payloads.py --seed 42
python scripts/run_all.py --seed 42 --n-microgrids 3 --horizon 4 --n-scenarios 8 --quick --output-dir results/qci_small
```

Those commands write `results/phase3_resource_estimate.md`, `results/cubic_vs_quadratic.csv`, `results/benchmarks/pglib_case5_pjm/benchmark_report.md`, `results/phase2_paper.md`, `analysis/paper/`, `submission_package/`, main QCi payload files, standalone export-only payloads under `results/qci_export/`, and conservative hardware-start payloads under `results/qci_small/`.

## Directory Structure

```text
.
├── analysis/paper/        # Manifest-derived paper tables and artifact index
├── data/                  # Generated synthetic case files
├── manifests/upstream/    # Public benchmark provenance manifests
├── results/               # Generated CSVs, figures, payloads, and Markdown summaries
├── scripts/               # Reproduction and experiment entrypoints
├── src/cmpo/              # Importable CMPO prototype package
└── tests/                 # Pytest suite for data, models, repair, exports, and end-to-end runs
```

Key source modules:

- `data.py`: deterministic synthetic grid case generation
- `benchmarks.py`: offline public-benchmark adapters and provenance
- `scenarios.py`: disruption scenario definitions
- `microgrid_design.py`: patch and upgrade planning heuristics
- `polynomial.py`: degree-3 polynomial model object
- `hamiltonian_builder.py`: per-scenario/per-patch Hamiltonian construction
- `repair.py`: repair and decode raw continuous solutions
- `baselines.py`: classical baselines and pre-QCi local search
- `metrics.py`: aggregation and report writers
- `plotting.py`: result figures
- `qci_export.py`: offline QCi payload export helpers

## Methods Implemented

- **GreedyCriticalLoadFirst:** deterministic dispatch that serves critical load first, then noncritical load.
- **SLSQPDispatchOptimizer:** SciPy SLSQP local nonlinear optimization over the polynomial model.
- **DifferentialEvolutionOptimizer:** SciPy global heuristic, enabled in non-quick runs or selected scaling cases.
- **CMPO-local polynomial search:** random-restart local polynomial search used only as a pre-QCi simulation proxy.
- **Microgrid design heuristic:** selects overlapping patches and estimates upgrade needs for islanding feasibility.
- **Cubic-vs-quadratic experiment:** compares native cubic generator costs against fitted quadratic approximations in `results/cubic_vs_quadratic.csv`.
- **PGLib case5-PJM adapted benchmark:** maps a public PGLib-OPF case into the CMPO microgrid contract and writes benchmark-specific evidence under `results/benchmarks/pglib_case5_pjm/`.

## Metrics Produced

The pipeline writes computed metrics, not hand-entered values:

- Expected operating cost
- Best and median cost by method
- Risk-adjusted cost with CVaR-style tail term
- Total upgrade cost
- Critical and noncritical load served fractions
- Energy not served and critical energy not served
- Customer-load unserved proxy
- Critical infrastructure unserved hours
- Feasibility rate
- Median runtime and time-to-good-solution
- Scenario scaling runtime and cost degradation
- Hamiltonian variable count, term count, degree, coefficient statistics

See `results/summary_metrics.csv`, `results/scenario_results.csv`, `results/scaling_results.csv`, and `results/model_stats.csv`.

## Paper Artifact Bundle

The command:

```bash
python scripts/build_phase2_paper.py
```

builds `results/phase2_paper.md` plus reproducible tables under `analysis/paper/` from saved manifests and CSV outputs. It does not hand-enter result numbers; it reads `results/run_manifest.json`, `results/benchmarks/pglib_case5_pjm/benchmark_manifest.json`, and linked metric files.

## Public Benchmark Adapter

The optional benchmark command:

```bash
python scripts/run_benchmark.py --seed 42 --quick
```

uses a local adapter for PGLib-OPF `pglib_opf_case5_pjm.m` version `v23.07`. Provenance is pinned in `manifests/upstream/pglib-opf-case5-pjm.json`, including upstream URL, license, version, and SHA-256 checksum. The adapter uses PGLib bus loads, generator capacities/cost slopes, and branch ratings as anchors, then adds deterministic PV, BESS, PCC, critical-load, and upgrade fields required by CMPO. This benchmark is a stress-test bridge to a public OPF case; it is not an AC OPF reproduction.

## How To Interpret `results/phase2_headlines.md`

`results/phase2_headlines.md` is the judge-facing narrative generated from current run artifacts. It summarizes what was solved, what data was used, which baselines were compared, preliminary result tables, resilience findings, the cubic-cost rationale, and why QCi Dirac-3 access is justified for Phase 3. Treat it as a generated summary of the CSV outputs, not as an independent source of results.

## Phase 3 Plan

Phase 3 would use the exported payloads in `results/qci_payloads/` as the starting point for QCi Dirac-3 / `eqc-models` execution. Planned work:

- Adapt `cmpo.qci_export.convert_to_eqc_models_format()` to the confirmed QCi API.
- Run repeated stochastic QCi solves per scenario/patch payload.
- Re-run classical baselines with identical seeds, scenarios, patch sets, repair logic, and metrics.
- Compare QCi outputs against greedy, SLSQP, differential evolution, and CMPO-local search.
- Expand patch sizes and scenario counts guided by `results/phase3_resource_estimate.md`.

## Citation / Disclaimer

This repository uses synthetic data for research prototyping and challenge evaluation. It is not operational grid-planning advice, does not represent proprietary utility data, and should not be used to operate real infrastructure without independent engineering validation.
