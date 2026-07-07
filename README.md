# Restorers CMPO Phase 3 Benchmark-First Submission

[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_black.png" width="150" alt="Launch on qBraid">](https://account.qbraid.com?gitHubUrl=https://github.com/Ostailor/QCI.git&redirectUrl=scripts/qbraid_phase3_autorun.sh)

This repository is Team Restorers' Phase 3 benchmark-first submission for the QCi Energy Infrastructure challenge, **Cost Optimization in Resilient Power Grids**. It implements a reproducible workflow for the Cubic Microgrid Patch Optimizer (CMPO): derive public benchmark microgrid-resilience adapters, form islandable patch designs, evaluate disruption scenarios, build native degree-3 Hamiltonian/polynomial models, compare strong classical and QUBO baselines, and execute QCi Dirac-3 where payload size permits.

## What This Repo Demonstrates

- Public-benchmark-derived microgrid resilience adapters for PGLib-OPF case5-PJM, case14 IEEE, case30 IEEE, and case57 IEEE.
- ARPA-E Grid Optimization public dataset download/check/provenance path.
- IEEE distribution feeder bridge/status path with an explicit benchmark_missing report when feeder files are not present.
- Synthetic CMPO cases retained only for smoke tests, debugging, controlled ablations, and sanity checks.
- A simple microgrid design stage that selects overlapping islandable patches and records upgrade feasibility/cost evidence.
- Scenario-level dispatch experiments across normal and stressed grid conditions.
- Native cubic generator-cost terms in a bounded polynomial model.
- Classical baseline comparisons and a pre-QCi CMPO-local polynomial-search proxy.
- Offline QCi payload exports suitable for later adaptation to QCi Dirac-3 / `eqc-models`.
- Reproducible result files, plots, and tests that a judge can run locally.

## What This Repo Does Not Claim

- No unsupported quantum advantage is claimed.
- This is a reproducible benchmark and Hamiltonian export/execution harness, not a production grid optimizer.
- Synthetic data is not the main Phase 3 evidence base when public benchmark-derived results are present.
- Public PGLib/ARPA-E adapters are public-benchmark-derived microgrid resilience adapters, not raw AC-OPF/SCOPF reproductions.

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

## Phase 3 Benchmark-First Reproduction

The judge-facing Phase 3 path prioritizes public benchmark-derived cases. Synthetic cases are smoke/control/ablation evidence only.

```bash
python scripts/phase3_fetch_public_benchmarks.py
python scripts/phase3_build_public_benchmark_payloads.py
python scripts/phase3_run_public_benchmarks.py \
  --suite pglib_case5_pjm,pglib_case14_ieee,pglib_case30_ieee,pglib_case57_ieee \
  --repeats 3
python scripts/phase3_build_qci_fit_public_payloads.py --benchmark pglib_case14_ieee --max-variables 132
python scripts/phase3_build_qci_fit_public_payloads.py --benchmark pglib_case30_ieee --max-variables 132
python scripts/phase3_build_qci_fit_public_payloads.py --benchmark pglib_case57_ieee --max-variables 132
python scripts/phase3_run_qci.py \
  --config configs/phase3_pglib_case5.yaml \
  --payload-dir results/phase3/public_benchmarks/pglib_case5_pjm/qci_payloads \
  --output-dir results/phase3/public_benchmarks/pglib_case5_pjm/qci \
  --repeats 1
python scripts/phase3_decode_qci.py \
  --config configs/phase3_pglib_case5.yaml \
  --experiment-dir results/phase3/public_benchmarks/pglib_case5_pjm
python scripts/phase3_make_tables.py
python scripts/phase3_make_figures.py
python scripts/phase3_validate_benchmark_ladder.py
```

Primary Phase 3 outputs:

- Public benchmark manifest: `results/phase3/public_benchmarks/benchmark_manifest.csv`
- Benchmark status report: `results/phase3/public_benchmarks/benchmark_status.md`
- Public benchmark summary: `results/phase3/public_benchmarks/public_benchmark_summary.md`
- Final tables: `results/phase3/final_tables/`
- Final figures: `results/phase3/final_figures/`
- QCi raw request/response artifacts: `results/phase3/public_benchmarks/pglib_case5_pjm/qci/`
- QCi decoded metrics: `results/phase3/public_benchmarks/pglib_case5_pjm/decoded/`

QCi credentials are read from `.env` through `QCI_API_URL` and `QCI_TOKEN`. The case5 public adapter uses two-microgrid patches so degree-3 payloads fit the current Dirac-3 135-variable limit reported by QCi. Case14, case30, and case57 retain their full 198-variable reference payloads and additionally provide decomposed `qci_fit_payloads/` capped at 132 variables.

Prepared QCi-fit run commands:

```bash
python scripts/phase3_run_qci.py \
  --payload-dir results/phase3/public_benchmarks/pglib_case14_ieee/qci_fit_payloads \
  --output-dir results/phase3/public_benchmarks/pglib_case14_ieee/qci \
  --repeats 30

python scripts/phase3_run_qci.py \
  --payload-dir results/phase3/public_benchmarks/pglib_case30_ieee/qci_fit_payloads \
  --output-dir results/phase3/public_benchmarks/pglib_case30_ieee/qci \
  --repeats 20
```

Do not report QCi results for these qci-fit payloads until the commands above have actually completed and `scripts/phase3_decode_qci.py` has decoded the raw responses.

## Launch on qBraid Autorun

The Launch on qBraid button above uses qBraid's public repository clone flow:

```markdown
[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_black.png" width="150">](https://account.qbraid.com?gitHubUrl=https://github.com/Ostailor/QCI.git&redirectUrl=scripts/qbraid_phase3_autorun.sh)
```

Before running the autorun, create a qBraid API key in the qBraid account dashboard and set it in the qBraid terminal:

```bash
export QBRAID_API_KEY="paste-your-qbraid-api-key"
```

Then run the full qBraid autorun:

```bash
bash scripts/qbraid_phase3_autorun.sh \
  --config configs/phase3_qci_small.yaml \
  --cpu-repeats 10 \
  --gpu-repeats 50
```

The autorun uses the qBraid API to create two on-demand instances:

- `gpu-l4` for the CUDA-only GPU random-restart baseline.
- `cpu-8v-32g` for CPU solver baselines: greedy, SLSQP, differential evolution, CMPO-local search, piecewise-linear MILP, QUBO/quadratized search, IPOPT/Pyomo fallback, and stress heuristic.

It uploads a sanitized copy of this repository to each instance, runs the matching baseline suite, downloads result archives to `results/phase3/qbraid_autorun/`, writes `results/phase3/qbraid_autorun/autorun_manifest.json`, and stops both qBraid instances in cleanup. Pass `--keep-instances` only for debugging.

For a plan without creating instances:

```bash
python scripts/qbraid_phase3_autorun.py --dry-run
```

The qBraid launcher intentionally exits on CPU-only qBraid Lab instances so credits are not spent on the wrong hardware. When CUDA is visible, the GPU-parallel random-restart baseline refuses NumPy CPU fallback and records `cupy_cuda:*`, `torch_cuda:*`, or `numba_cuda` in `gpu_backend`.

The GPU-only helper remains available for targeted debugging:

```bash
bash scripts/qbraid_run_phase3_gpu.sh configs/phase3_qci_small.yaml 50
```

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

## Public Benchmark Adapters

The benchmark-first public adapter command:

```bash
python scripts/phase3_run_public_benchmarks.py --suite pglib_case5_pjm,pglib_case14_ieee,pglib_case30_ieee,pglib_case57_ieee --repeats 3
```

uses local adapters for PGLib-OPF `pglib_opf_case5_pjm`, `pglib_opf_case14_ieee`, `pglib_opf_case30_ieee`, and `pglib_opf_case57_ieee` version `v23.07`. Provenance is pinned under `data/public_benchmarks/provenance/`, `manifests/upstream/`, and each `results/phase3/public_benchmarks/*/benchmark_provenance.json`, including upstream URL, license, version/commit where available, local path, and SHA-256 checksum. The adapters use PGLib bus loads, generator capacities/cost data, and branch ratings as anchors, then add deterministic PV, BESS, PCC/tie, critical-load, islanding, and restoration fields required by CMPO. These are public-benchmark-derived microgrid resilience adapters; they are not AC OPF reproductions.

ARPA-E GO data is fetched and checked with:

```bash
python scripts/phase3_check_arpae_go.py
```

The IEEE distribution path writes a PowerModelsDistribution bridge script and an explicit `benchmark_missing` report if IEEE feeder files are not present locally.

## Phase 3 Evidence Status

`results/phase2_headlines.md` remains a historical Phase 2 artifact. Phase 3 evidence is generated from the benchmark-first commands above and summarized by `results/phase3/final_tables/final_tables.md`, `results/phase3/public_benchmarks/public_benchmark_summary.md`, and `results/phase3/public_benchmarks/benchmark_status.md`.

The current Phase 3 pipeline:

- fetches/checks public benchmark data with provenance,
- builds public-benchmark-derived CMPO payloads,
- runs the required classical, QUBO, MILP/Pyomo, GPU/random-restart, and stress heuristic baselines,
- runs QCi Dirac-3 on public PGLib case5-derived payloads that fit the current device constraint,
- decodes QCi responses through the same repair and metric computation path,
- generates final tables and figures from CSV results,
- validates readiness with `python scripts/phase3_validate_benchmark_ladder.py`.

## Citation / Disclaimer

This repository uses synthetic data for research prototyping and challenge evaluation. It is not operational grid-planning advice, does not represent proprietary utility data, and should not be used to operate real infrastructure without independent engineering validation.
