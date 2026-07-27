from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from scripts.phase3_package_submission import (
    _challenge_zip_members,
    _files_for_path,
    _group_files,
    _package_groups,
    _write_challenge_zip,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "results/phase3"


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_irc_cmpo_final_payload_contract() -> None:
    irc = PHASE3 / "irc_cmpo"
    rows = list(csv.DictReader((irc / "payload_manifest.csv").open(encoding="utf-8")))

    assert len(rows) == 6
    assert [int(row["lambda_index"]) for row in rows] == list(range(6))
    for row in rows:
        payload = _read_json(irc / "payloads" / f"lambda_{int(row['lambda_index']):02d}.json")
        assert payload["num_variables"] == 33
        assert payload["max_degree"] == 3
        assert payload["num_levels"] == [2] * 33
        assert payload["irc_cmpo"]["projection_permitted"] is False
        assert payload["dirac3_scaling"]["projection_used"] is False
        assert payload["dirac3_scaling"]["audit"]["passed"] is True
        assert payload["dirac3_scaling"]["audit"]["dynamic_range"] <= 200


def test_irc_cmpo_qci_evidence_is_complete_and_native() -> None:
    qci = PHASE3 / "irc_cmpo/qci"
    status_rows = list(csv.DictReader((qci / "job_status.csv").open(encoding="utf-8")))
    summary = _read_json(qci / "native_evaluation_summary.json")

    assert len(status_rows) == 8
    assert all(row["status"] == "COMPLETED" for row in status_rows)
    assert all(not row["failure_reason"] for row in status_rows)
    assert sum(int(row["num_samples"]) for row in status_rows) == 660
    assert summary["canaries_passed"] is True
    assert summary["full_jobs_completed"] == 6
    assert summary["full_jobs_failed"] == 0
    assert summary["native_projection_used"] is False

    for row in status_rows:
        name = row["name"]
        assert (qci / "requests" / f"{name}.json").is_file()
        assert (qci / "responses" / f"{name}.submit.json").is_file()
        assert (qci / "responses" / f"{name}.result.json").is_file()
        assert (qci / "validations" / f"{name}.json").is_file()


def test_sc_cmpo_evidence_and_consensus_archives_are_complete() -> None:
    sc = PHASE3 / "sc_cmpo"
    payloads = sorted((sc / "qci_payloads").glob("*.json"))
    status_rows = list(csv.DictReader((sc / "qci/job_status.csv").open(encoding="utf-8")))

    assert len(payloads) == 43
    assert len(status_rows) == 43
    assert all(row["status"] == "COMPLETED" for row in status_rows)
    assert all(_read_json(path)["max_degree"] <= 3 for path in payloads)
    assert all(len(_read_json(path)["variables"]) <= 132 for path in payloads)

    trace_dir = sc / "system_summary"
    rows = list(
        csv.DictReader((trace_dir / "compressed_artifact_manifest.csv").open(encoding="utf-8"))
    )
    assert {row["original_path"] for row in rows} == {
        "consensus_manifest.json",
        "consensus_values.csv",
    }
    for row in rows:
        archive = trace_dir / row["compressed_path"]
        assert archive.stat().st_size == int(row["compressed_size_bytes"])
        assert _sha256(archive) == row["compressed_sha256"]
        with gzip.open(archive, "rb") as handle:
            digest = hashlib.sha256()
            size = 0
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(block)
                digest.update(block)
        assert size == int(row["original_size_bytes"])
        assert digest.hexdigest() == row["original_sha256"]


def test_final_paper_artifacts_are_present() -> None:
    irc_final = PHASE3 / "irc_cmpo/final"
    sc_final = PHASE3 / "sc_cmpo/final"

    irc_required = {
        "final_results.md",
        "table1_qci_vs_exact_and_gpu.csv",
        "table2_cost_resilience_lambda_sweep.csv",
        "table3_native_sample_quality.csv",
        "table4_heldout_contingencies.csv",
        "table5_resource_usage.csv",
        "table6_encoding_comparison.csv",
        "pareto_frontier.csv",
        "win_tie_loss.csv",
        "cost_vs_critical_ens_pareto.png",
        "native_cubic_vs_qubo_size.png",
        "qci_vs_gpu_true_recourse_regret.png",
    }
    sc_required = {
        "table1_system_level_qci_vs_baselines.csv",
        "table2_upgrade_cost_and_resilience.csv",
        "table3_heldout_contingencies.csv",
        "table4_public_benchmark_ladder.csv",
        "table5_encoding_efficiency.csv",
        "table6_resource_usage.csv",
        "win_tie_loss_system_level.csv",
        "pareto_frontier_system_level.csv",
        "system_cost_vs_resilience_pareto.png",
        "heldout_critical_ens.png",
        "qci_repeat_distribution.png",
    }

    assert not irc_required - {path.name for path in irc_final.iterdir()}
    assert not sc_required - {path.name for path in sc_final.iterdir()}


def test_artifact_manifest_matches_retained_files() -> None:
    manifest = PHASE3 / "artifact_manifest.csv"
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))

    assert rows
    assert all("reproduced" not in Path(row["path"]).parts for row in rows)
    assert all(row["path"] != ".env" for row in rows)
    assert all(
        not {".omx", ".pytest_cache", ".ruff_cache", "tmp"} & set(Path(row["path"]).parts)
        for row in rows
    )
    submission_paths = {
        Path(row["path"])
        for row in rows
        if Path(row["path"]).parts[:1] == ("submission",)
    }
    assert submission_paths == {
        Path("submission/TheRestorers__Phase3_Version1.pdf")
    }
    for row in rows:
        path = ROOT / row["path"]
        assert path.is_file(), row["path"]
        assert path.stat().st_size == int(row["size_bytes"]), row["path"]
        assert _sha256(path) == row["sha256"], row["path"]


def test_package_expansion_excludes_runtime_caches() -> None:
    relative_paths = [path.relative_to(ROOT) for path in _files_for_path("tests")]

    assert relative_paths
    assert all("__pycache__" not in path.parts for path in relative_paths)
    assert all(path.suffix != ".pyc" for path in relative_paths)


def test_default_package_contains_only_the_final_paper_pdf() -> None:
    packaged = {
        path.relative_to(ROOT).as_posix()
        for group in _package_groups(include_raw=False)
        for path in _group_files(group)
    }

    assert "submission/TheRestorers__Phase3_Version1.pdf" in packaged
    assert not any(path.startswith("submission/paper/") for path in packaged)
    assert not any("/rendered" in path for path in packaged)


def test_obsolete_phase2_entrypoints_are_not_retained() -> None:
    assert not (ROOT / "scripts/build_phase2_paper.py").exists()
    assert not (ROOT / "tests/test_phase2_evidence_outputs.py").exists()
    assert not (ROOT / "tests/test_phase2_paper_builder.py").exists()


def test_raw_package_covers_checksum_inventory() -> None:
    manifest_rows = list(
        csv.DictReader((PHASE3 / "artifact_manifest.csv").open(encoding="utf-8"))
    )
    inventory = {row["path"] for row in manifest_rows}
    packaged = {
        path.relative_to(ROOT).as_posix()
        for group in _package_groups(include_raw=True)
        for path in _group_files(group)
    }

    assert not inventory - packaged


def test_challenge_zip_has_judge_facing_layout(tmp_path: Path) -> None:
    output = tmp_path / "TheRestorers_QCI_Phase3.zip"
    result = _write_challenge_zip(output, include_raw=False, overwrite=False)

    assert result["output_zip"] == str(output)
    assert result["size_bytes"] == output.stat().st_size
    assert len(result["sha256"]) == 64

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "README.md" in names
        assert "PACKAGE_MANIFEST.json" in names
        assert "Write-Up/TheRestorers__Phase3_Version1.pdf" in names
        assert "Source_Code/submission/TheRestorers__Phase3_Version1.pdf" in names
        assert "Source_Code/src/cmpo/scenario_coupled_model.py" in names
        assert "Source_Code/scripts/phase3_full_rebuild.py" in names
        assert "Source_Code/results/phase3/artifact_manifest.csv" in names
        assert "Source_Code/.env.example" in names
        assert not any("submission/paper/" in name for name in names)
        assert not any("__pycache__" in name for name in names)

        readme = archive.read("README.md").decode("utf-8")
        assert "**Team:** Team Restorers" in readme
        assert "**Project:** Native Cubic Optimization" in readme
        assert "**Challenge track:** QCi Energy Infrastructure Challenge, Phase 3" in readme
        assert "Launch_on_qBraid_white.png" in readme
        assert "cd Source_Code" in readme
        assert "## Known Limitations and Assumptions" in readme

        env_example = archive.read("Source_Code/.env.example").decode("utf-8")
        assert "QCI_TOKEN=<your-qci-token>" in env_example
        assert "QBRAID_API_KEY=<your-qbraid-api-key>" in env_example

        shell_info = archive.getinfo("Source_Code/scripts/qbraid_phase3_autorun.sh")
        assert (shell_info.external_attr >> 16) & 0o111


def test_challenge_zip_raw_mode_includes_qci_evidence() -> None:
    names = {
        member.archive_path
        for member in _challenge_zip_members(include_raw=True)
    }

    assert any("/irc_cmpo/qci/responses/" in name for name in names)
    assert any("/sc_cmpo/qci/" in name and name.endswith("/response.json") for name in names)
    assert not any(name.endswith(".env") for name in names)


def test_all_judge_facing_scripts_expose_dry_run() -> None:
    scripts = sorted((ROOT / "scripts").glob("*.py"))

    assert scripts
    for script in scripts:
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, (script.name, completed.stderr)
        assert "--dry-run" in completed.stdout, script.name
