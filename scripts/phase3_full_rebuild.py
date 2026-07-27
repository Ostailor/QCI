#!/usr/bin/env python
"""Run the complete Phase 3 computational rebuild in one fresh tree."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "results/phase3/reproduced/full_rebuild"
ESTIMATED_ELAPSED = "2.5-4 hours"
SC_CONFIGS = (
    "configs/phase3_sc_cmpo_case14.yaml",
    "configs/phase3_sc_cmpo_case30.yaml",
    "configs/phase3_sc_cmpo_arpae.yaml",
    "configs/phase3_sc_cmpo_ieee123.yaml",
)


class RebuildStage:
    """One visible, executable stage in the full rebuild."""

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        expected_outputs: Sequence[str],
        expected_minutes: tuple[float, float],
        *,
        expected_console: str,
        environment: Mapping[str, str] | None = None,
        expected_qci_jobs: int = 0,
        expected_qci_samples: int = 0,
    ) -> None:
        self.name = name
        self.command = tuple(map(str, command))
        self.expected_outputs = tuple(map(str, expected_outputs))
        self.expected_minutes = expected_minutes
        self.expected_console = expected_console
        self.environment = dict(environment or {})
        self.expected_qci_jobs = expected_qci_jobs
        self.expected_qci_samples = expected_qci_samples

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": format_command(self.command, self.environment),
            "expected_outputs": list(self.expected_outputs),
            "expected_console": self.expected_console,
            "expected_minutes": list(self.expected_minutes),
            "expected_qci_jobs": self.expected_qci_jobs,
            "expected_qci_samples": self.expected_qci_samples,
        }


def _inside_repo(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"full rebuild output must be inside the repository: {path}") from exc
    return resolved


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def format_command(
    command: Sequence[str], environment: Mapping[str, str] | None = None
) -> str:
    prefix = [f"{key}={shlex.quote(value)}" for key, value in (environment or {}).items()]
    return " ".join([*prefix, *(shlex.quote(part) for part in command)])


def build_rebuild_plan(
    run_dir: Path | str,
    *,
    workers: int = 8,
    qci_workers: int = 4,
    poll_seconds: int = 60,
    gpu_profile: str = "gpu-l4",
    candidate_count: int = 10_000,
) -> list[RebuildStage]:
    """Return every command in the complete public-data-to-results rebuild."""

    run = Path(run_dir).resolve()
    sc = run / "sc_cmpo"
    irc = run / "irc_cmpo"
    config = run / "phase3_irc_cmpo_ieee123.yaml"
    script = "scripts/phase3_full_rebuild.py"
    sc_environment = {
        "QCI_SAMPLES_PER_JOB": "30",
        "QCI_PAYLOAD_WORKERS": str(qci_workers),
        "QCI_MAX_INFLIGHT_JOBS": "1",
    }
    return [
        RebuildStage(
            "Validate credentials and local toolchain",
            ("python", script, "--run-dir", str(run), "--check-environment-only"),
            (".env validation in console",),
            (0.0, 1.0),
            expected_console="QCi, qBraid, Python, qci-client, and Git: PASS",
        ),
        RebuildStage(
            "Fetch and checksum all pinned public benchmark inputs",
            ("python", "scripts/phase3_fetch_public_benchmarks.py", "--family", "all"),
            (
                "data/upstream/pglib/",
                "data/upstream/arpae_go/",
                "data/upstream/ieee123/",
            ),
            (1.0, 3.0),
            expected_console="PGLib, ARPA-E GO, and IEEE123 sources resolve to pinned checksums",
        ),
        RebuildStage(
            "Build all SC-CMPO public benchmark payloads",
            (
                "python",
                "scripts/phase3_build_sc_cmpo_payloads.py",
                "--output-dir",
                str(sc),
                "--overwrite",
            ),
            (
                str(sc / "payload_manifest.csv"),
                str(sc / "model_stats.csv"),
                str(sc / "qci_payloads/"),
            ),
            (0.5, 2.0),
            expected_console="43 payloads: 9 case14, 14 case30, 8 ARPA-E GO, and 12 IEEE123",
        ),
        RebuildStage(
            "Validate the IEEE 123-bus distribution power flow",
            (
                "python",
                "scripts/phase3_validate_distribution_powerflow.py",
                "--output",
                str(sc / "distribution_validation.md"),
            ),
            (str(sc / "distribution_validation.md"),),
            (0.5, 2.0),
            expected_console="OpenDSS parser/engine counts, load totals, convergence, and voltage bounds pass",
        ),
        RebuildStage(
            "Validate scenario coupling and Dirac-3 limits",
            (
                "python",
                "scripts/phase3_validate_sc_cmpo.py",
                "--result-dir",
                str(sc),
            ),
            (str(sc / "validation_report.md"),),
            (0.1, 1.0),
            expected_console="All 43 payloads have >=6 scenarios, <=132 variables, and degree <=3",
        ),
        RebuildStage(
            "Run all SC-CMPO payloads on QCi Dirac-3",
            (
                "python",
                "scripts/phase3_run_qci.py",
                "--payload-dir",
                str(sc / "qci_payloads"),
                "--output-dir",
                str(sc / "qci"),
                "--repeats",
                "30",
            ),
            (
                str(sc / "qci/job_status.csv"),
                str(sc / "qci/*/repeat_000/request.json"),
                str(sc / "qci/*/repeat_000/response.json"),
            ),
            (95.0, 120.0),
            expected_console="43 COMPLETED jobs and 1,290 returned samples",
            environment=sc_environment,
            expected_qci_jobs=43,
            expected_qci_samples=1290,
        ),
        RebuildStage(
            "Decode and repair all SC-CMPO QCi samples",
            (
                "python",
                "scripts/phase3_decode_qci.py",
                "--input-dir",
                str(sc / "qci"),
                "--output-dir",
                str(sc / "decoded"),
            ),
            (
                str(sc / "decoded/qci_repeat_metrics.csv"),
                str(sc / "decoded/qci_payload_summary.csv"),
            ),
            (0.5, 2.0),
            expected_console="1,290 samples decoded with pre/post-repair metrics retained",
        ),
        RebuildStage(
            "Run all seven matched SC-CMPO baseline methods",
            (
                "python",
                "scripts/phase3_run_matched_baselines.py",
                "--payload-dir",
                str(sc / "qci_payloads"),
                "--output-dir",
                str(sc / "system_level"),
                "--repeats",
                "50",
                "--workers",
                str(workers),
                "--overwrite",
            ),
            (
                str(sc / "system_level/baseline_patch_solutions.csv"),
                str(sc / "system_level/matched_baseline_run.json"),
            ),
            (0.5, 3.0),
            expected_console="7 methods, 43 payloads, 6,622 completed solver calls, 0 failures",
        ),
        RebuildStage(
            "Run matched overlap consensus for QCi and every baseline",
            (
                "python",
                "scripts/phase3_run_overlap_consensus.py",
                "--payload-dir",
                str(sc / "qci_payloads"),
                "--baseline-patch-solutions",
                str(sc / "system_level/baseline_patch_solutions.csv"),
                "--qci-decoded",
                str(sc / "decoded/qci_repeat_metrics.csv"),
                "--output-dir",
                str(sc / "system_level"),
                "--overwrite",
            ),
            (
                str(sc / "system_level/consensus_manifest.json"),
                str(sc / "system_level/consensus_convergence.csv"),
            ),
            (0.5, 2.0),
            expected_console="Consensus traces report converged primal/dual residuals or explicit failures",
        ),
        RebuildStage(
            "Project and score complete public benchmark systems",
            (
                "python",
                "scripts/phase3_compare_system_level.py",
                "--payload-dir",
                str(sc / "qci_payloads"),
                "--consensus-manifest",
                str(sc / "system_level/consensus_manifest.json"),
                "--configs",
                *SC_CONFIGS,
                "--output-dir",
                str(sc / "system_level"),
                "--overwrite",
            ),
            (
                str(sc / "system_level/qci_system_metrics.csv"),
                str(sc / "system_level/baseline_system_metrics.csv"),
                str(sc / "system_level/heldout_summary.csv"),
            ),
            (1.0, 4.0),
            expected_console="System metrics are emitted only for successful consensus and projection records",
        ),
        RebuildStage(
            "Create the eight SC-CMPO tables and seven figures",
            (
                "python",
                "scripts/phase3_finalize_sc_cmpo.py",
                "--system-level-dir",
                str(sc / "system_level"),
                "--payload-dir",
                str(sc / "qci_payloads"),
                "--output-dir",
                str(sc / "final"),
            ),
            (
                str(sc / "final/table1_system_level_qci_vs_baselines.csv"),
                str(sc / "final/table4_public_benchmark_ladder.csv"),
                str(sc / "final/system_cost_vs_resilience_pareto.png"),
            ),
            (0.5, 2.0),
            expected_console="8 CSV tables and 7 PNG figures written",
        ),
        RebuildStage(
            "Create an IRC-CMPO config linked to the rebuilt IEEE123 payloads",
            (
                "python",
                script,
                "--run-dir",
                str(run),
                "--prepare-config-only",
            ),
            (str(config),),
            (0.0, 0.5),
            expected_console="Runtime config points to the rebuilt 12-patch IEEE123 source tree",
        ),
        RebuildStage(
            "Generate the full 3,000-portfolio true-recourse dataset",
            (
                "python",
                "scripts/phase3_build_irc_cmpo_dataset.py",
                "--config",
                str(config),
                "--output-dir",
                str(irc / "dataset"),
                "--minimum-unique",
                "3000",
            ),
            (
                str(irc / "dataset/portfolio_labels.csv"),
                str(irc / "dataset/split_manifest.csv"),
                str(irc / "dataset/recourse_failures.csv"),
            ),
            (5.0, 15.0),
            expected_console="3,000 successful fixed-upgrade recourse labels and 0 failures",
        ),
        RebuildStage(
            "Fit and validate the cubic recourse surrogate",
            (
                "python",
                "scripts/phase3_fit_irc_cmpo_surrogate.py",
                "--config",
                str(config),
                "--dataset",
                str(irc / "dataset/portfolio_labels.csv"),
                "--split-manifest",
                str(irc / "dataset/split_manifest.csv"),
                "--output-dir",
                str(irc / "surrogate"),
                "--minimum-portfolios",
                "3000",
            ),
            (
                str(irc / "surrogate/model.json"),
                str(irc / "surrogate/metrics.csv"),
                str(irc / "surrogate/fit_manifest.json"),
            ),
            (1.0, 3.0),
            expected_console="All five surrogate targets pass rank, recall, error, and degree gates",
        ),
        RebuildStage(
            "Build all six native cubic IRC-CMPO scalarizations",
            (
                "python",
                "scripts/phase3_build_irc_cmpo_payloads.py",
                "--config",
                str(config),
                "--dataset",
                str(irc / "dataset/portfolio_labels.csv"),
                "--split-manifest",
                str(irc / "dataset/split_manifest.csv"),
                "--surrogate-model",
                str(irc / "surrogate/model.json"),
                "--output-dir",
                str(irc),
            ),
            (
                str(irc / "payload_manifest.csv"),
                str(irc / "payloads/lambda_00.json"),
                str(irc / "payloads/lambda_05.json"),
            ),
            (0.2, 1.0),
            expected_console="6 payloads, 33 variables each, degree 3, coefficient dynamic range <=200",
        ),
        RebuildStage(
            "Run exact and stochastic IRC-CMPO validation",
            (
                "python",
                "scripts/phase3_validate_irc_cmpo_offline.py",
                "--config",
                str(config),
                "--manifest",
                str(irc / "payload_manifest.csv"),
                "--dataset",
                str(irc / "dataset/portfolio_labels.csv"),
                "--output-dir",
                str(irc / "validation"),
                "--samples-per-method",
                "30",
                "--annealing-sweeps",
                "200",
            ),
            (
                str(irc / "validation/exact_validation.json"),
                str(irc / "validation/stochastic_validation.json"),
                str(irc / "validation/manifest.json"),
            ),
            (3.0, 10.0),
            expected_console="6/6 exact and local stochastic validation gates pass without projection",
        ),
        RebuildStage(
            "Generate the fresh IRC-CMPO preflight decision",
            (
                "python",
                "scripts/phase3_prepare_irc_cmpo_preflight.py",
                "--artifact-root",
                str(irc),
            ),
            (
                str(irc / "preflight_summary.json"),
                str(irc / "preflight_report.md"),
            ),
            (0.1, 0.5),
            expected_console="IRC_CMPO_READY_FOR_QCI: YES",
        ),
        RebuildStage(
            "Generate the exact toy/reduced/full IRC smoke payloads",
            (
                "python",
                "scripts/phase3_run_irc_cmpo_smoke.py",
                "--config",
                str(config),
                "--final-summary",
                str(irc / "preflight_summary.json"),
                "--payload-manifest",
                str(irc / "payload_manifest.csv"),
                "--output-dir",
                str(irc / "smoke"),
            ),
            (
                str(irc / "smoke/smoke_plan.json"),
                str(irc / "smoke/payloads/toy.json"),
                str(irc / "smoke/payloads/reduced_ieee123.json"),
            ),
            (0.1, 1.0),
            expected_console="3 smoke payloads built; toy and reduced exact optima recorded",
        ),
        RebuildStage(
            "Run the complete IRC-CMPO NVIDIA L4 baseline suite on qBraid",
            (
                "python",
                "scripts/qbraid_phase3_autorun.py",
                "--mode",
                "qbraid",
                "--manifest",
                str(irc / "payload_manifest.csv"),
                "--payload-dir",
                str(irc / "payloads"),
                "--output-dir",
                str(irc / "baselines/gpu"),
                "--config",
                str(config),
                "--candidate-count",
                str(candidate_count),
                "--gpu-profile",
                gpu_profile,
            ),
            (
                str(irc / "baselines/gpu/gpu_baseline_summary.json"),
                str(irc / "baselines/gpu/gpu_baseline_metrics.csv"),
                str(irc / "baselines/gpu/exact_milp_references.json"),
            ),
            (5.0, 15.0),
            expected_console="6 lambdas x 3 L4 methods x 10,000 candidates; instance stops after download",
        ),
        RebuildStage(
            "Submit the complete eight-job IRC-CMPO QCi batch",
            (
                "python",
                "scripts/phase3_submit_irc_cmpo_final_batch.py",
                "--artifact-root",
                str(irc),
                "--output-dir",
                str(irc / "qci"),
                "--execute",
            ),
            (
                str(irc / "qci/batch_manifest.json"),
                str(irc / "qci/job_status.csv"),
                str(irc / "qci/requests/"),
            ),
            (0.5, 2.0),
            expected_console="8 job IDs: 2 smoke/canary jobs and 6 full scalarization jobs",
            expected_qci_jobs=8,
            expected_qci_samples=660,
        ),
        RebuildStage(
            "Monitor, decode, evaluate, and report the IRC-CMPO batch",
            (
                "python",
                "scripts/phase3_monitor_irc_cmpo_final_batch.py",
                "--batch-dir",
                str(irc / "qci"),
                "--dataset",
                str(irc / "dataset/portfolio_labels.csv"),
                "--exact-validation",
                str(irc / "validation/exact_validation.json"),
                "--gpu-dir",
                str(irc / "baselines/gpu"),
                "--final-output-dir",
                str(irc / "final"),
                "--poll-seconds",
                str(poll_seconds),
            ),
            (
                str(irc / "qci/native_evaluation_summary.json"),
                str(irc / "final/table1_qci_vs_exact_and_gpu.csv"),
                str(irc / "final/table6_encoding_comparison.csv"),
            ),
            (15.0, 30.0),
            expected_console="8 COMPLETED jobs, 660 samples, native validation, 6 tables, and 7 figures",
        ),
        RebuildStage(
            "Run the complete test suite",
            ("python", "-m", "pytest", "-q"),
            ("pytest PASS summary in console",),
            (0.5, 2.0),
            expected_console="All repository tests pass",
        ),
        RebuildStage(
            "Run static analysis",
            ("python", "-m", "ruff", "check", "."),
            ("Ruff PASS summary in console",),
            (0.1, 1.0),
            expected_console="All checks passed",
        ),
        RebuildStage(
            "Verify counts, checksum the fresh tree, and package it",
            (
                "python",
                script,
                "--run-dir",
                str(run),
                "--verify-package-only",
            ),
            (
                str(run / "rebuild_summary.json"),
                str(run / "rebuild_manifest.csv"),
                str(run) + ".tar.gz",
            ),
            (0.5, 3.0),
            expected_console="43 SC jobs + 8 IRC jobs complete; fresh rebuild archive created",
        ),
    ]


def _dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"missing credential file: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed = value.strip().strip("'\"")
        if key.strip() in {"QCI_API_URL", "QCI_TOKEN", "QBRAID_API_KEY", "QBRAID_API_URL"}:
            values[key.strip()] = parsed
            os.environ.setdefault(key.strip(), parsed)
    return values


def check_environment() -> dict[str, Any]:
    values = _dotenv(ROOT / ".env")
    required = ("QCI_API_URL", "QCI_TOKEN", "QBRAID_API_KEY")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise RuntimeError(f".env is missing required settings: {', '.join(missing)}")
    required_commands = ("git",)
    missing_commands = [
        command for command in required_commands if shutil.which(command) is None
    ]
    if missing_commands:
        raise RuntimeError(f"missing required commands: {', '.join(missing_commands)}")
    packages = {}
    for package in ("qci_client", "qbraid_core"):
        try:
            module = __import__(package)
        except ImportError as exc:
            raise RuntimeError(
                f"{package} is not installed; run python -m pip install -e '.[dev,qbraid]'"
            ) from exc
        packages[package] = getattr(module, "__version__", "installed")
    return {
        "status": "PASS",
        "credential_file": str(ROOT / ".env"),
        "credentials_present": list(required),
        "commands": {command: "PASS" for command in required_commands},
        "packages": packages,
    }


def prepare_runtime_config(run_dir: Path) -> Path:
    run = _inside_repo(run_dir)
    target = run / "phase3_irc_cmpo_ieee123.yaml"
    if target.exists():
        raise FileExistsError(f"runtime config is create-only: {target}")
    source = ROOT / "configs/phase3_irc_cmpo_ieee123.yaml"
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload_dir = run / "sc_cmpo/qci_payloads"
    config["source_payload_dir"] = _relative(payload_dir)
    config["source_asset_catalog"] = _relative(payload_dir)
    config["output_dir"] = _relative(run / "irc_cmpo")
    config["qci"]["submission_permitted"] = True
    config["qci"]["full_experiment_permitted"] = True
    config["qci"]["checked_in_full_experiment_completed"] = False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return target


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_and_package(run_dir: Path) -> dict[str, Any]:
    run = _inside_repo(run_dir)
    sc_payloads = sorted((run / "sc_cmpo/qci_payloads").glob("*.json"))
    sc_jobs = _csv_rows(run / "sc_cmpo/qci/job_status.csv")
    irc_jobs = _csv_rows(run / "irc_cmpo/qci/job_status.csv")
    labels = _csv_rows(run / "irc_cmpo/dataset/portfolio_labels.csv")
    irc_payloads = _csv_rows(run / "irc_cmpo/payload_manifest.csv")
    failures = []
    failure_path = run / "irc_cmpo/dataset/recourse_failures.csv"
    if failure_path.is_file():
        failures = _csv_rows(failure_path)
    baseline_summary = json.loads(
        (run / "sc_cmpo/system_level/matched_baseline_run.json").read_text(
            encoding="utf-8"
        )
    )
    gpu_summary = json.loads(
        (run / "irc_cmpo/baselines/gpu/gpu_baseline_summary.json").read_text(
            encoding="utf-8"
        )
    )
    native_summary = json.loads(
        (run / "irc_cmpo/qci/native_evaluation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    sc_final_files = {
        "table1_system_level_qci_vs_baselines.csv",
        "table2_upgrade_cost_and_resilience.csv",
        "table3_heldout_contingencies.csv",
        "table4_public_benchmark_ladder.csv",
        "table5_encoding_efficiency.csv",
        "table6_resource_usage.csv",
        "win_tie_loss_system_level.csv",
        "pareto_frontier_system_level.csv",
        "system_cost_vs_resilience_pareto.png",
        "upgrade_cost_vs_outage_reduction.png",
        "heldout_critical_ens.png",
        "customer_unserved_by_scenario.png",
        "consensus_convergence.png",
        "native_cubic_vs_qubo_encoding.png",
        "qci_repeat_distribution.png",
    }
    irc_final_files = {
        "table1_qci_vs_exact_and_gpu.csv",
        "table2_cost_resilience_lambda_sweep.csv",
        "table3_native_sample_quality.csv",
        "table4_heldout_contingencies.csv",
        "table5_resource_usage.csv",
        "table6_encoding_comparison.csv",
        "win_tie_loss.csv",
        "pareto_frontier.csv",
    }
    sc_samples = sum(
        len(json.loads(row.get("raw_solutions", "[]"))) for row in sc_jobs
    )
    checks = {
        "sc_payloads": len(sc_payloads) == 43,
        "sc_qci_jobs": len(sc_jobs) == 43
        and all(row.get("status") == "COMPLETED" for row in sc_jobs),
        "sc_qci_samples": sc_samples == 1290,
        "sc_matched_baselines": (
            baseline_summary.get("payload_count") == 43
            and baseline_summary.get("method_count") == 7
            and baseline_summary.get("completed") == 6622
            and baseline_summary.get("failed") == 0
        ),
        "sc_final_outputs": all(
            (run / "sc_cmpo/final" / name).is_file() for name in sc_final_files
        ),
        "irc_labels": len(labels) >= 3000 and not failures,
        "irc_payloads": len(irc_payloads) == 6,
        "irc_gpu": (
            gpu_summary.get("lambda_count") == 6
            and gpu_summary.get("candidate_count_per_lambda_method") == 10_000
            and len(gpu_summary.get("methods", ())) == 3
        ),
        "irc_qci_jobs": len(irc_jobs) == 8
        and all(row.get("status") == "COMPLETED" for row in irc_jobs),
        "irc_native_evaluation": (
            native_summary.get("canaries_passed") is True
            and native_summary.get("full_jobs_completed") == 6
            and native_summary.get("full_jobs_failed") == 0
            and native_summary.get("native_projection_used") is False
        ),
        "irc_final_outputs": all(
            (run / "irc_cmpo/final" / name).is_file() for name in irc_final_files
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"full rebuild verification failed: {checks}")
    summary = {
        "status": "PASS",
        "checks": checks,
        "sc_cmpo": {
            "payloads": len(sc_payloads),
            "qci_jobs_completed": len(sc_jobs),
            "qci_samples_requested": 1290,
            "qci_samples_returned": sc_samples,
            "matched_baseline_solver_calls": int(
                baseline_summary.get("completed", 0)
            ),
        },
        "irc_cmpo": {
            "true_recourse_labels": len(labels),
            "payloads": len(irc_payloads),
            "qci_jobs_completed": len(irc_jobs),
            "qci_samples_requested": sum(int(row["num_samples"]) for row in irc_jobs),
        },
        "total_qci_jobs_completed": len(sc_jobs) + len(irc_jobs),
        "total_qci_samples_requested": 1290
        + sum(int(row["num_samples"]) for row in irc_jobs),
    }
    (run / "rebuild_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    files = sorted(
        path
        for path in run.rglob("*")
        if path.is_file()
        and path.name not in {"rebuild_manifest.csv", "full_rebuild_status.json"}
    )
    with (run / "rebuild_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("path", "size_bytes", "sha256"), lineterminator="\n"
        )
        writer.writeheader()
        for path in files:
            writer.writerow(
                {
                    "path": path.relative_to(run).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    archive = Path(
        shutil.make_archive(str(run), "gztar", root_dir=run.parent, base_dir=run.name)
    )
    summary["archive"] = str(archive)
    return summary


def _plan_report(plan: Sequence[RebuildStage], run_dir: Path) -> dict[str, Any]:
    return {
        "mode": "dry-run",
        "run_dir": str(run_dir),
        "estimated_elapsed_time": ESTIMATED_ELAPSED,
        "scope": {
            "public_benchmark_families": 4,
            "sc_cmpo_payloads": 43,
            "sc_cmpo_qci_jobs": 43,
            "sc_cmpo_samples_per_job": 30,
            "matched_baseline_methods": 7,
            "stochastic_baseline_repeats": 50,
            "irc_cmpo_true_recourse_labels": 3000,
            "irc_cmpo_payloads": 6,
            "irc_cmpo_qci_jobs": 8,
            "irc_cmpo_qci_samples": 660,
            "total_qci_jobs": sum(stage.expected_qci_jobs for stage in plan),
            "total_qci_samples": sum(stage.expected_qci_samples for stage in plan),
        },
        "stages": [stage.as_dict() for stage in plan],
    }


def _print_plan(plan: Sequence[RebuildStage], run_dir: Path) -> None:
    print(f"Full Phase 3 rebuild: {len(plan)} stages")
    print(f"Output tree: {run_dir}")
    print(f"Expected elapsed time: {ESTIMATED_ELAPSED}")
    print("Expected hardware workload: 51 QCi jobs / 1,950 samples and one qBraid L4 run")
    for index, stage in enumerate(plan, start=1):
        low, high = stage.expected_minutes
        print(f"\n{index}. {stage.name} ({low:g}-{high:g} min)")
        print(f"   Run: {format_command(stage.command, stage.environment)}")
        print(f"   Expect: {stage.expected_console}")
        print("   Writes:")
        for output in stage.expected_outputs:
            print(f"     - {output}")


def _run_command(stage: RebuildStage) -> None:
    command = list(stage.command)
    if command and command[0] == "python":
        command[0] = sys.executable
    environment = os.environ.copy()
    environment.update(stage.environment)
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def execute_rebuild(plan: Sequence[RebuildStage], run_dir: Path) -> dict[str, Any]:
    if run_dir.exists():
        raise FileExistsError(
            f"full rebuild is create-only; choose a new --run-dir: {run_dir}"
        )
    run_dir.mkdir(parents=True)
    status_path = run_dir / "full_rebuild_status.json"
    status: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "estimated_elapsed_time": ESTIMATED_ELAPSED,
        "status": "RUNNING",
        "stages": [
            {**stage.as_dict(), "status": "PENDING", "runtime_seconds": None}
            for stage in plan
        ],
    }
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    for index, stage in enumerate(plan):
        print(f"\n[{index + 1}/{len(plan)}] {stage.name}", flush=True)
        print(f"Run: {format_command(stage.command, stage.environment)}", flush=True)
        print(f"Expected: {stage.expected_console}", flush=True)
        status["stages"][index]["status"] = "RUNNING"
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        started = time.perf_counter()
        try:
            _run_command(stage)
        except Exception:
            status["stages"][index]["status"] = "FAILED"
            status["stages"][index]["runtime_seconds"] = time.perf_counter() - started
            status["status"] = "FAILED"
            status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
            raise
        status["stages"][index]["status"] = "COMPLETED"
        status["stages"][index]["runtime_seconds"] = time.perf_counter() - started
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    status["status"] = "COMPLETED"
    status["completed_at"] = datetime.now(timezone.utc).isoformat()
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    # Refresh the archive so it contains the final COMPLETED status record.
    archive = Path(
        shutil.make_archive(str(run_dir), "gztar", root_dir=run_dir.parent, base_dir=run_dir.name)
    )
    return {
        "status": "COMPLETED",
        "run_dir": str(run_dir),
        "archive": str(archive),
        "stage_count": len(plan),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--qci-workers", type=int, default=4)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--gpu-profile", default="gpu-l4")
    parser.add_argument("--candidate-count", type=int, default=10_000)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Execute the entire public-data, QCi, qBraid, reconstruction, and reporting pipeline.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every command, expected output, and elapsed-time estimate without writing.",
    )
    parser.add_argument("--json", action="store_true", help="Print the dry-run plan as JSON.")
    parser.add_argument(
        "--check-environment-only",
        action="store_true",
        help="Run only the .env, package, and command preflight used by stage 1.",
    )
    parser.add_argument(
        "--prepare-config-only",
        action="store_true",
        help="Create only the run-local IRC-CMPO configuration used by stage 12.",
    )
    parser.add_argument(
        "--verify-package-only",
        action="store_true",
        help="Run only final count checks, checksums, and archive creation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir = args.run_dir.resolve()
    if args.check_environment_only:
        _inside_repo(run_dir)
        result = check_environment()
    elif args.prepare_config_only:
        result = {"runtime_config": str(prepare_runtime_config(_inside_repo(run_dir)))}
    elif args.verify_package_only:
        result = verify_and_package(_inside_repo(run_dir))
    else:
        plan = build_rebuild_plan(
            run_dir,
            workers=args.workers,
            qci_workers=args.qci_workers,
            poll_seconds=args.poll_seconds,
            gpu_profile=args.gpu_profile,
            candidate_count=args.candidate_count,
        )
        if not args.execute:
            report = _plan_report(plan, run_dir)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                _print_plan(plan, run_dir)
            return 0
        result = execute_rebuild(plan, _inside_repo(run_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
