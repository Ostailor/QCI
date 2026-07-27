# Team Restorers: QCi Phase 3

- **Team:** Team Restorers
- **Project:** Native Cubic Optimization for Resilient Microgrid Investment on QCi Dirac-3
- **Challenge track:** QCi Energy Infrastructure Challenge, Phase 3

This repository is the reproducible artifact for Team Restorers' Phase 3
submission to the QCi Energy Infrastructure Challenge. It contains:

- **IRC-CMPO**, the final focused experiment: a 33-variable native cubic
  resilient-capacity master solved on QCi Dirac-3 and compared with exact MILP
  and NVIDIA L4 search.
- **SC-CMPO**, the public benchmark ladder: scenario-coupled consensus planning
  on PGLib case14/case30, ARPA-E GO, and the IEEE 123-bus feeder.

The repository includes the submitted raw hardware responses, public inputs,
provenance, final tables, figures, and a complete create-only rebuild path.

[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_white.png" width="150" alt="Launch on qBraid">](https://account.qbraid.com?gitHubUrl=https://github.com/Ostailor/QCI.git&redirectUrl=README.md)

The button opens this repository in qBraid Lab. After adding `.env`, the full
rebuild command below provisions an NVIDIA L4 through the qBraid API, runs the
GPU experiment, downloads its artifacts, and stops the instance.

## Result Summary

- The retained IRC-CMPO hardware distribution contains **600 production
  samples** across six cost scalarizations; **575 (95.8%)** attain exact MILP
  ground-state energy.
- All 600 production vectors are native integer and locally feasible without
  portfolio repair or projection. Every positive cost weight contains exact
  ground-state samples.
- The native degree-3 encoding uses **33 logical variables and no
  auxiliaries**. The matched quadratized encoding uses **52 variables**,
  including 19 auxiliaries.
- For the five positive cost weights, QCi matches the exact MILP reference at
  the reported full-recourse point: **$2.032M upgrade cost, 17.62% maximum
  customers unserved, 9.0 total critical-infrastructure unserved-hours across
  eight scenario snapshots (1.125 expected hours), 50.625 kWh critical ENS,
  and 230.625 kWh total ENS**.
- The retained QUBO comparator reports **$2.438M, 18.39%, 15.0 total
  critical-infrastructure unserved-hours, 60.625 kWh critical ENS, and 240.625
  kWh total ENS** on the same metrics.
- The SC-CMPO ladder reconstructs four complete public systems from **43
  scenario-coupled degree-3 patches**, with 30 Dirac-3 samples per patch.

These data demonstrate high-fidelity native cubic hardware recovery and a
36.5% encoding reduction relative to the matched quadratized formulation;
runtime is reported separately for each platform.

Primary evidence:

- [Compiled paper](submission/TheRestorers__Phase3_Version1.pdf)
- [IRC-CMPO final results](results/phase3/irc_cmpo/final/final_results.md)
- [QCi versus exact and L4 methods](results/phase3/irc_cmpo/final/table1_qci_vs_exact_and_gpu.csv)
- [Cost-resilience sweep](results/phase3/irc_cmpo/final/table2_cost_resilience_lambda_sweep.csv)
- [Encoding comparison](results/phase3/irc_cmpo/final/table6_encoding_comparison.csv)
- [SC-CMPO public benchmark ladder](results/phase3/sc_cmpo/final/table4_public_benchmark_ladder.csv)
- [Checksum inventory](results/phase3/artifact_manifest.csv)

## Submitted Evidence Check

This short command validates the immutable submitted evidence. It is not the
full computational rebuild described below.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,qbraid]"

python scripts/phase3_reproduce.py --verify-only
python scripts/phase3_reproduce.py --overwrite
pytest -q
```

Expected time is 5-10 minutes. Regenerated files go under
`results/phase3/reproduced/`; submitted raw responses are not modified.

## Submission ZIP

Build the complete judge archive, including the write-up, source, pinned public
inputs, retained results, tests, and immutable QCi request/response evidence:

```bash
python scripts/phase3_package_submission.py \
  --zip-output submission/TheRestorers_QCI_Phase3.zip \
  --include-raw \
  --overwrite
```

The archive opens with this layout:

```text
README.md
Write-Up/TheRestorers__Phase3_Version1.pdf
Source_Code/
```

The root README contains the qBraid launch path and tells judges to run commands
from `Source_Code/`. No source edit or path substitution is required.

## Full Rebuild

The full rebuild executes the complete computational workflow that produced
the paper evidence. It does not select a smoke subset:

- 4 public benchmark families;
- 43 SC-CMPO payloads and 43 QCi Dirac-3 jobs;
- 30 QCi samples per SC-CMPO payload, totaling 1,290 samples;
- 7 matched classical methods and 50 repeats for stochastic methods;
- 6,622 expected matched baseline solver calls;
- full overlap consensus, system projection, and held-out evaluation;
- 3,000 IEEE123 true-recourse portfolio labels;
- 6 IRC-CMPO scalarizations;
- 3 NVIDIA L4 methods, 10,000 candidates per lambda and method;
- 8 IRC-CMPO QCi jobs, totaling 660 samples;
- 51 QCi jobs and 1,950 requested QCi samples overall;
- fresh tables, figures, tests, checksums, and archive.

The expected elapsed time after environment setup is **2.5-4 hours**. The
dominant stage is the 43-payload SC-CMPO Dirac-3 run. The estimate is grounded
in the retained execution records: 101.5 minutes of aggregate SC-CMPO QCi
runtime, 42.8 seconds for 6,622 matched baseline solves with eight workers,
2.1-4.4 minutes for the recorded L4 kernels, and 91-94 seconds of device
runtime per full IRC scalarization. Shared hardware service availability and
local download speed can change elapsed time.

### Requirements

- Python 3.10 or newer;
- 8 GB RAM, 4 or more CPU cores, and 2 GB free disk space;
- `git`;
- a QCi account with Dirac-3 allocation;
- a qBraid account able to provision the `gpu-l4` profile;
- a qBraid API key.

On Ubuntu, `git` can be installed with:

```bash
sudo apt-get update
sudo apt-get install -y git
```

Create the environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,qbraid]"
```

Create `.env` in the repository root. It is ignored by Git:

```dotenv
QCI_API_URL=https://api.qci-prod.com
QCI_TOKEN=<your-qci-token>
QBRAID_API_KEY=<your-qbraid-api-key>
```

Create the qBraid key under **qBraid Account > API Keys**. The runner uses that
key to create and stop the L4 instance. Credentials are read from `.env`; no
credential is written to a result artifact.

### Preview Every Step

The dry run is read-only and prints every command, expected output, and time
estimate:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir results/phase3/reproduced/full_rebuild \
  --dry-run
```

For machine-readable output:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir results/phase3/reproduced/full_rebuild \
  --dry-run --json
```

The preview begins like this:

```text
Full Phase 3 rebuild: 24 stages
Output tree: .../results/phase3/reproduced/full_rebuild
Expected elapsed time: 2.5-4 hours
Expected hardware workload: 51 QCi jobs / 1,950 samples and one qBraid L4 run
```

### Run Everything

Use a new output directory. The full rebuild is create-only:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir results/phase3/reproduced/full_rebuild \
  --execute
```

The runner prints the stage number, exact command, expected result, live child
output, and measured duration. Progress is written after every stage to:

```text
results/phase3/reproduced/full_rebuild/full_rebuild_status.json
```

### Expected Stage Outputs

| Step | Operation | Expected result | Typical time |
|---:|---|---|---:|
| 1 | Environment gate | QCi, qBraid, qci-client, Python, and Git pass | <1 min |
| 2 | Public input fetch/check | PGLib, ARPA-E GO, and IEEE123 checksums pass | 1-3 min |
| 3 | SC-CMPO build | 43 payloads: 9 case14, 14 case30, 8 ARPA-E, 12 IEEE123 | <2 min |
| 4 | IEEE123 power flow | Parser/engine parity, convergence, load, and voltage gates pass | <2 min |
| 5 | SC-CMPO validation | All 43 payloads have at least 6 scenarios, <=132 variables, degree <=3 | <1 min |
| 6 | SC-CMPO Dirac-3 | 43 completed jobs and 1,290 samples | 95-120 min |
| 7 | SC-CMPO decode | 1,290 decoded samples with before/after repair metrics | <2 min |
| 8 | Matched baselines | 7 methods, 6,622 solver calls, 0 expected failures | <3 min |
| 9 | Overlap consensus | Primal/dual residuals and convergence records | <2 min |
| 10 | Full-system projection | QCi and baseline system metrics plus held-out results | 1-4 min |
| 11 | SC-CMPO reporting | 8 tables and 7 figures | <2 min |
| 12 | IRC runtime config | Fresh config linked to rebuilt IEEE123 payloads | <1 min |
| 13 | True-recourse dataset | 3,000 successful labels and 0 failures | 5-15 min |
| 14 | Cubic surrogate | 5 targets pass error, rank, recall, and degree gates | 1-3 min |
| 15 | IRC payload build | 6 payloads, 33 variables, degree 3, dynamic range <=200 | <1 min |
| 16 | IRC offline validation | 6/6 exact and stochastic suites pass without projection | 3-10 min |
| 17 | IRC preflight | `IRC_CMPO_READY_FOR_QCI: YES` | <1 min |
| 18 | IRC smoke payload build | Toy, reduced, and full payloads plus exact references | <1 min |
| 19 | qBraid L4 baselines | 6 lambdas x 3 methods x 10,000 candidates | 5-15 min |
| 20 | IRC QCi submission | 8 job IDs: 2 smoke/canary and 6 full jobs | <2 min |
| 21 | IRC QCi evaluation | 8 completed jobs, 660 samples, 6 tables, 7 figures | 15-30 min |
| 22 | Tests | Full `pytest` suite passes | <2 min |
| 23 | Static analysis | `ruff check .` passes | <1 min |
| 24 | Final verification/package | Counts pass, manifest and `.tar.gz` are created | 1-3 min |

### Exact Manual Command Sequence

The one-command runner executes the sequence below. These commands are shown
for auditability and for resuming a fresh manual run at a known stage.

```bash
RUN=results/phase3/reproduced/full_rebuild
SC="$RUN/sc_cmpo"
IRC="$RUN/irc_cmpo"
CFG="$RUN/phase3_irc_cmpo_ieee123.yaml"
```

1. Validate `.env`, qci-client, qBraid, and the local toolchain:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir "$RUN" --check-environment-only
```

Expected: a JSON record with `"status": "PASS"`.

2. Fetch or checksum every pinned public input:

```bash
python scripts/phase3_fetch_public_benchmarks.py --family all
```

Expected: verified PGLib, ARPA-E GO, IEEE123, and NREL-backed source records
under `data/upstream/`.

3. Build all four SC-CMPO benchmark families:

```bash
python scripts/phase3_build_sc_cmpo_payloads.py \
  --output-dir "$SC" --overwrite
```

Expected: `43` JSON files under `$SC/qci_payloads/` and a
`$SC/payload_manifest.csv` with benchmark counts `9, 14, 8, 12`.

4. Validate the published IEEE123 feeder:

```bash
python scripts/phase3_validate_distribution_powerflow.py \
  --output "$SC/distribution_validation.md"
```

Expected: `"passed": true` and both Markdown and JSON validation reports.

5. Validate every SC-CMPO Hamiltonian:

```bash
python scripts/phase3_validate_sc_cmpo.py --result-dir "$SC"
```

Expected: `$SC/validation_report.md` and `$SC/validation_report.json`, with no
payload over 132 variables or degree 3.

6. Run all 43 SC-CMPO payloads on Dirac-3:

```bash
QCI_SAMPLES_PER_JOB=30 \
QCI_PAYLOAD_WORKERS=4 \
QCI_MAX_INFLIGHT_JOBS=1 \
python scripts/phase3_run_qci.py \
  --payload-dir "$SC/qci_payloads" \
  --output-dir "$SC/qci" \
  --repeats 30
```

Expected: `$SC/qci/job_status.csv` has 43 `COMPLETED` rows; each response
contains 30 samples, totaling 1,290.

7. Decode and repair every SC-CMPO sample:

```bash
python scripts/phase3_decode_qci.py \
  --input-dir "$SC/qci" \
  --output-dir "$SC/decoded"
```

Expected: `$SC/decoded/qci_repeat_metrics.csv` contains all returned samples
and both pre-repair and post-repair violations.

8. Run all seven matched methods:

```bash
python scripts/phase3_run_matched_baselines.py \
  --payload-dir "$SC/qci_payloads" \
  --output-dir "$SC/system_level" \
  --repeats 50 \
  --workers 8 \
  --overwrite
```

Expected: `$SC/system_level/matched_baseline_run.json` reports 7 methods, 43
payloads, 6,622 completed solver calls, and zero failures.

9. Reconstruct each full system through matched overlap consensus:

```bash
python scripts/phase3_run_overlap_consensus.py \
  --payload-dir "$SC/qci_payloads" \
  --baseline-patch-solutions "$SC/system_level/baseline_patch_solutions.csv" \
  --qci-decoded "$SC/decoded/qci_repeat_metrics.csv" \
  --output-dir "$SC/system_level" \
  --overwrite
```

Expected: consensus manifests and convergence CSVs with primal residual, dual
residual, iteration count, and unresolved conflicts.

10. Run the common full-system projection and held-out evaluation:

```bash
python scripts/phase3_compare_system_level.py \
  --payload-dir "$SC/qci_payloads" \
  --consensus-manifest "$SC/system_level/consensus_manifest.json" \
  --configs configs/phase3_sc_cmpo_case14.yaml \
            configs/phase3_sc_cmpo_case30.yaml \
            configs/phase3_sc_cmpo_arpae.yaml \
            configs/phase3_sc_cmpo_ieee123.yaml \
  --output-dir "$SC/system_level" \
  --overwrite
```

Expected: QCi and baseline system metrics, upgrade plans, scenario results,
held-out contingencies, and no metric row for a failed reconstruction.

11. Generate the complete SC-CMPO result set:

```bash
python scripts/phase3_finalize_sc_cmpo.py \
  --system-level-dir "$SC/system_level" \
  --payload-dir "$SC/qci_payloads" \
  --output-dir "$SC/final"
```

Expected: 8 CSV tables and 7 PNG figures under `$SC/final/`.

12. Build a runtime IRC config from the newly rebuilt IEEE123 artifacts:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir "$RUN" --prepare-config-only
```

Expected: `$CFG`, with both the source payload path and public upgrade catalog
linked to `$SC/qci_payloads`.

13. Generate the full 3,000-portfolio true-recourse dataset:

```bash
python scripts/phase3_build_irc_cmpo_dataset.py \
  --config "$CFG" \
  --output-dir "$IRC/dataset" \
  --minimum-unique 3000
```

Expected JSON:

```json
{
  "candidate_portfolios_evaluated": 3000,
  "successful_true_recourse_labels": 3000,
  "recourse_failures": 0,
  "minimum_met": true
}
```

14. Fit the five-target cubic surrogate:

```bash
python scripts/phase3_fit_irc_cmpo_surrogate.py \
  --config "$CFG" \
  --dataset "$IRC/dataset/portfolio_labels.csv" \
  --split-manifest "$IRC/dataset/split_manifest.csv" \
  --output-dir "$IRC/surrogate" \
  --minimum-portfolios 3000
```

Expected: `"surrogate_valid": true`, `"payload_build_permitted": true`, and
split counts of 1,800 train, 600 validation, and 600 test portfolios.

15. Build all six native cubic scalarizations:

```bash
python scripts/phase3_build_irc_cmpo_payloads.py \
  --config "$CFG" \
  --dataset "$IRC/dataset/portfolio_labels.csv" \
  --split-manifest "$IRC/dataset/split_manifest.csv" \
  --surrogate-model "$IRC/surrogate/model.json" \
  --output-dir "$IRC"
```

Expected: `"payload_count": 6`, `"post_quantization_gates_passed": true`, 33
variables per payload, degree 3, and no portfolio projection.

16. Run exact and stochastic offline validation:

```bash
python scripts/phase3_validate_irc_cmpo_offline.py \
  --config "$CFG" \
  --manifest "$IRC/payload_manifest.csv" \
  --dataset "$IRC/dataset/portfolio_labels.csv" \
  --output-dir "$IRC/validation" \
  --samples-per-method 30 \
  --annealing-sweeps 200
```

Expected: 6/6 exact and stochastic lambda gates pass, with
`"projection_used": false`.

17. Generate the QCi preflight decision from the fresh artifacts:

```bash
python scripts/phase3_prepare_irc_cmpo_preflight.py \
  --artifact-root "$IRC"
```

Expected:

```json
{
  "IRC_CMPO_READY_FOR_QCI": "YES"
}
```

18. Generate the three preflight payloads and exact references:

```bash
python scripts/phase3_run_irc_cmpo_smoke.py \
  --config "$CFG" \
  --final-summary "$IRC/preflight_summary.json" \
  --payload-manifest "$IRC/payload_manifest.csv" \
  --output-dir "$IRC/smoke"
```

Expected: toy, reduced IEEE123, and full IEEE123 payloads under
`$IRC/smoke/payloads/`.

19. Provision qBraid L4 and run every GPU baseline:

```bash
python scripts/qbraid_phase3_autorun.py \
  --mode qbraid \
  --manifest "$IRC/payload_manifest.csv" \
  --payload-dir "$IRC/payloads" \
  --output-dir "$IRC/baselines/gpu" \
  --config "$CFG" \
  --candidate-count 10000 \
  --gpu-profile gpu-l4
```

Expected: 18 metric rows, covering six lambdas and three L4 methods. The
result identifies the NVIDIA L4 and CUDA backend, downloads the result bundle,
and stops the instance.

20. Submit the two preflight and six production QCi jobs:

```bash
python scripts/phase3_submit_irc_cmpo_final_batch.py \
  --artifact-root "$IRC" \
  --output-dir "$IRC/qci" \
  --execute
```

Expected: 8 job IDs and immutable request/submit-response JSONs. Requested
samples are 30 toy, 30 reduced, and 100 for each of six lambdas.

21. Monitor, decode, evaluate, and generate IRC-CMPO results:

```bash
python scripts/phase3_monitor_irc_cmpo_final_batch.py \
  --batch-dir "$IRC/qci" \
  --dataset "$IRC/dataset/portfolio_labels.csv" \
  --exact-validation "$IRC/validation/exact_validation.json" \
  --gpu-dir "$IRC/baselines/gpu" \
  --final-output-dir "$IRC/final" \
  --poll-seconds 60
```

Expected: 8 `COMPLETED` rows in `$IRC/qci/job_status.csv`, 660 returned
samples, native integer validation JSON for every job, 6 final tables, and 7
figures.

22. Run every test:

```bash
python -m pytest -q
```

Expected: all tests pass.

23. Run static analysis:

```bash
python -m ruff check .
```

Expected: `All checks passed!`

24. Verify counts, checksum every fresh artifact, and build the archive:

```bash
python scripts/phase3_full_rebuild.py \
  --run-dir "$RUN" --verify-package-only
```

Expected final summary:

```json
{
  "status": "PASS",
  "sc_cmpo": {
    "payloads": 43,
    "qci_jobs_completed": 43,
    "qci_samples_requested": 1290
  },
  "irc_cmpo": {
    "true_recourse_labels": 3000,
    "payloads": 6,
    "qci_jobs_completed": 8,
    "qci_samples_requested": 660
  },
  "total_qci_jobs_completed": 51,
  "total_qci_samples_requested": 1950
}
```

The final files are:

```text
results/phase3/reproduced/full_rebuild/rebuild_summary.json
results/phase3/reproduced/full_rebuild/rebuild_manifest.csv
results/phase3/reproduced/full_rebuild.tar.gz
```

A fresh hardware run receives new job IDs and measured runtimes. The rebuild
does not force a result value to match the retained artifact; it reports the
new samples exactly as returned and provides the retained paper result as the
reference comparison.

## Public Inputs

All topology, load, generation, branch, and contingency inputs are pinned
public sources. Upgrade costs derive from the pinned NREL ATB source. Source
URL, version, checksum, license, and transformation are recorded under
`data/upstream/` and `results/phase3/sc_cmpo/`.

The benchmark labels in the paper are **PGLib-derived microgrid stress
adapters**, not AC OPF reproductions.

## Known Limitations and Assumptions

- The archive is self-contained for submitted-evidence verification, table and
  figure regeneration, public-input validation, and the complete classical
  workflow. A fresh hardware rebuild requires judge-owned QCi and qBraid
  credentials in `.env`; credentials are the only runtime values not bundled.
- All commands run without source edits from the repository root, or from
  `Source_Code/` after extracting the submission ZIP. Public benchmark files,
  cost assumptions, configurations, payloads, and retained result evidence are
  included.
- QCi Dirac-3 is a sampling service. A fresh run receives new job identifiers
  and measured runtimes, while the pipeline preserves every returned sample and
  evaluates it with the same decoder, consensus, and full-system projection.
- PGLib cases are used as published-network-derived microgrid stress adapters,
  not as AC OPF reproductions. IEEE 123-bus unbalanced power-flow feasibility is
  checked separately with OpenDSS.
- The reported planning horizon consists of eight operational and contingency
  snapshots plus held-out N-1 events. Longer chronological restoration studies
  use the same recourse interface but are outside this submission's runtime
  budget.

## Repository Layout

```text
configs/                         final IRC-CMPO and SC-CMPO configurations
data/upstream/                   pinned PGLib, ARPA-E GO, IEEE123, NREL inputs
src/cmpo/                        models, adapters, consensus, and projection
scripts/                         full build, execution, validation, and package tools
tests/                           formulation, adapter, integrity, and CLI tests
results/phase3/irc_cmpo/         submitted IRC payloads, raw QCi, L4, and tables
results/phase3/sc_cmpo/          submitted public ladder evidence and system results
submission/TheRestorers__Phase3_Version1.pdf   final compiled paper
```

No credential is stored in the repository. `.env` is ignored by Git.
