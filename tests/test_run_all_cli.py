import subprocess
import sys
from pathlib import Path


def test_run_all_quick_cli_generates_phase2_artifacts(tmp_path: Path) -> None:
    result = subprocess.run(
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
            str(tmp_path / "results"),
            "--data-dir",
            str(tmp_path / "data"),
            "--skip-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Best method by expected cost" in result.stdout
    assert "Payloads exported" in result.stdout
    assert (tmp_path / "results" / "summary_metrics.csv").exists()
    assert (tmp_path / "results" / "scenario_results.csv").exists()
    assert (tmp_path / "results" / "scaling_results.csv").exists()
    assert (tmp_path / "results" / "model_stats.csv").exists()
    assert (tmp_path / "results" / "phase2_headlines.md").exists()
    assert list((tmp_path / "results" / "qci_payloads").glob("*.json"))


def test_run_all_custom_output_defaults_data_under_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "qci_small"
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
            str(output_dir),
            "--skip-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "data" / "generated_case.yaml").exists()
    assert not (tmp_path / "data").exists()
