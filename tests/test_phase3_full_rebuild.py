from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "phase3_full_rebuild.py"
    spec = importlib.util.spec_from_file_location("phase3_full_rebuild", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_rebuild_plan_covers_complete_hardware_and_reporting_pipeline(
    tmp_path: Path,
) -> None:
    module = _load_module()
    plan = module.build_rebuild_plan(tmp_path / "full_rebuild")
    commands = [" ".join(stage.command) for stage in plan]

    assert len(plan) >= 20
    assert any("phase3_fetch_public_benchmarks.py" in command for command in commands)
    assert any("phase3_build_sc_cmpo_payloads.py" in command for command in commands)
    assert any(
        "phase3_run_qci.py" in command and "--repeats 30" in command
        for command in commands
    )
    assert any(
        "phase3_run_matched_baselines.py" in command and "--repeats 50" in command
        for command in commands
    )
    assert any("qbraid_phase3_autorun.py" in command for command in commands)
    assert any("phase3_submit_irc_cmpo_final_batch.py" in command for command in commands)
    assert any("phase3_monitor_irc_cmpo_final_batch.py" in command for command in commands)
    assert not any("phase3_build_paper_assets.py" in command for command in commands)
    assert not any("phase3_build_paper_figures.py" in command for command in commands)
    assert not any("submission/paper" in command for command in commands)
    assert sum(stage.expected_qci_jobs for stage in plan) == 51
    assert sum(stage.expected_qci_samples for stage in plan) == 1950
    assert all(stage.expected_outputs for stage in plan)
    assert all(stage.expected_minutes[0] >= 0 for stage in plan)
    assert all(stage.expected_minutes[1] >= stage.expected_minutes[0] for stage in plan)


def test_full_rebuild_dry_run_is_read_only_and_machine_readable(
    tmp_path: Path, capsys
) -> None:
    module = _load_module()
    run_dir = tmp_path / "full_rebuild"

    exit_code = module.main(["--run-dir", str(run_dir), "--dry-run", "--json"])

    assert exit_code == 0
    assert not run_dir.exists()
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "dry-run"
    assert report["scope"]["sc_cmpo_payloads"] == 43
    assert report["scope"]["sc_cmpo_qci_jobs"] == 43
    assert report["scope"]["irc_cmpo_qci_jobs"] == 8
    assert report["scope"]["total_qci_samples"] == 1950
    assert report["estimated_elapsed_time"] == "2.5-4 hours"


def test_runtime_config_uses_fresh_sc_payloads_for_public_assets() -> None:
    module = _load_module()
    reproduced = ROOT / "results/phase3/reproduced"
    reproduced.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="full-rebuild-config-", dir=reproduced
    ) as temporary:
        run_dir = Path(temporary)
        path = module.prepare_runtime_config(run_dir)
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        expected = (run_dir / "sc_cmpo/qci_payloads").relative_to(ROOT).as_posix()

        assert config["source_payload_dir"] == expected
        assert config["source_asset_catalog"] == expected
        assert config["output_dir"] == (
            run_dir / "irc_cmpo"
        ).relative_to(ROOT).as_posix()
        assert config["qci"]["submission_permitted"] is True
        assert config["qci"]["full_experiment_permitted"] is True
