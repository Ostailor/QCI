import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_cubic_vs_quadratic_cli_generates_comparison_outputs(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_cubic_vs_quadratic.py",
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

    csv_path = tmp_path / "results" / "cubic_vs_quadratic.csv"
    frame = pd.read_csv(csv_path)

    assert "Cubic vs quadratic experiment complete" in result.stdout
    assert csv_path.exists()
    assert (tmp_path / "results" / "figures" / "cubic_vs_quadratic_dispatch.png").exists()
    assert (tmp_path / "results" / "figures" / "cubic_vs_quadratic_cost_error.png").exists()
    assert set(frame["model_variant"]) == {"cubic", "quadratic_approximation"}
    assert "true_cubic_cost" in frame.columns
    assert "true_cubic_cost_difference_vs_cubic" in frame.columns
