import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from cmpo.benchmarks import PGLIB_CASE5_PJM_PROVENANCE, build_pglib_case5_pjm_microgrid_case


def test_pglib_case5_benchmark_adapter_builds_offline_case(tmp_path: Path) -> None:
    case = build_pglib_case5_pjm_microgrid_case(horizon_hours=4, scenario_count=2, output_dir=tmp_path)

    assert len(case.microgrids) == 5
    assert len(case.tie_lines) == 6
    assert len(case.scenarios) == 2
    assert all(max(microgrid.load_profile.base_kw) > 0.0 for microgrid in case.microgrids)
    assert (tmp_path / "pglib_case5_pjm_manifest.json").exists()
    assert (tmp_path / "pglib_case5_pjm_adapted.yaml").exists()


def test_pglib_case5_manifest_pins_public_provenance() -> None:
    manifest_path = Path("manifests/upstream/pglib-opf-case5-pjm.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["upstream"]["version"] == PGLIB_CASE5_PJM_PROVENANCE["upstream"]["version"]
    assert manifest["upstream"]["license"] == "Creative Commons Attribution 4.0 International"
    assert manifest["upstream"]["checksum"].startswith("sha256:")
    assert manifest["local_adapter"]["adapter_module"] == "src/cmpo/benchmarks.py"


def test_run_benchmark_cli_writes_benchmark_evidence(tmp_path: Path) -> None:
    output_dir = tmp_path / "results" / "benchmarks" / "pglib_case5_pjm"
    data_dir = tmp_path / "data" / "benchmarks"
    result = subprocess.run(
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
            str(output_dir),
            "--data-dir",
            str(data_dir),
            "--skip-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Benchmark run complete" in result.stdout
    assert (output_dir / "summary_metrics.csv").exists()
    assert (output_dir / "scenario_results.csv").exists()
    assert (output_dir / "model_stats.csv").exists()
    assert (output_dir / "benchmark_report.md").exists()
    assert (output_dir / "benchmark_manifest.json").exists()
    assert list((output_dir / "qci_payloads").glob("*.json"))

    summary = pd.read_csv(output_dir / "summary_metrics.csv")
    stats = pd.read_csv(output_dir / "model_stats.csv")
    assert not summary.isna().any().any()
    assert (stats["degree"] <= 3).all()
