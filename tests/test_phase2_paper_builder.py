import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_phase2_paper_builder_uses_saved_artifacts(tmp_path: Path) -> None:
    results = tmp_path / "results"
    data = tmp_path / "data"
    analysis = tmp_path / "analysis" / "paper"

    subprocess.run(
        [
            sys.executable,
            "scripts/run_all.py",
            "--seed",
            "42",
            "--n-microgrids",
            "3",
            "--horizon",
            "4",
            "--n-scenarios",
            "2",
            "--quick",
            "--output-dir",
            str(results),
            "--data-dir",
            str(data),
            "--skip-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/run_scaling.py",
            "--seed",
            "42",
            "--quick",
            "--output-dir",
            str(results),
            "--data-dir",
            str(data),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/run_cubic_vs_quadratic.py",
            "--seed",
            "42",
            "--quick",
            "--output-dir",
            str(results),
            "--data-dir",
            str(data),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--seed",
            "42",
            "--quick",
            "--n-scenarios",
            "1",
            "--horizon",
            "4",
            "--output-dir",
            str(results / "benchmarks" / "pglib_case5_pjm"),
            "--data-dir",
            str(data / "benchmarks"),
            "--skip-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_phase2_paper.py",
            "--results-dir",
            str(results),
            "--analysis-dir",
            str(analysis),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Phase 2 paper artifacts built" in result.stdout
    paper = results / "phase2_paper.md"
    assert paper.exists()
    assert "does not claim live QCi hardware execution" in paper.read_text(encoding="utf-8")
    assert (analysis / "manifest_rows.csv").exists()
    assert (analysis / "artifact_index.md").exists()
    assert (analysis / "tables" / "main_results.csv").exists()
    assert (analysis / "tables" / "benchmark_results.csv").exists()
    assert (results / "submission_tables.md").exists()
    assert (results / "submission_key_findings.md").exists()
    assert (results / "submission_limitations.md").exists()
    assert (tmp_path / "submission_package" / "phase2_methods.md").exists()
    assert (tmp_path / "submission_package" / "phase2_results_summary.md").exists()
    assert (tmp_path / "submission_package" / "phase2_platform_request.md").exists()
    assert (tmp_path / "submission_package" / "artifacts_manifest.md").exists()
    assert "Judge Risk Checklist" in (results / "submission_limitations.md").read_text(encoding="utf-8")

    manifest_rows = pd.read_csv(analysis / "manifest_rows.csv")
    assert set(manifest_rows["run_name"]) == {"synthetic_default", "pglib_case5_pjm_adapted"}
