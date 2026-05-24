import subprocess
import sys
from pathlib import Path


def test_run_scaling_cli_generates_resource_evidence(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_scaling.py",
            "--seed",
            "42",
            "--output-dir",
            str(tmp_path / "results"),
            "--data-dir",
            str(tmp_path / "data"),
            "--quick",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Scaling study complete" in result.stdout
    assert (tmp_path / "results" / "scaling_results.csv").exists()
    assert (tmp_path / "results" / "figures" / "scenario_scaling.png").exists()
    assert (tmp_path / "results" / "figures" / "runtime_scaling.png").exists()
    assert (tmp_path / "results" / "phase3_resource_estimate.md").exists()
