from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "phase3_prepare_irc_cmpo_preflight.py"
    spec = importlib.util.spec_from_file_location(
        "phase3_prepare_irc_cmpo_preflight", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_builder_accepts_complete_fresh_artifact_tree(tmp_path: Path) -> None:
    module = _load_module()
    source = ROOT / "results/phase3/irc_cmpo"
    artifact_root = tmp_path / "irc_cmpo"
    for relative in (
        "dataset/portfolio_labels.csv",
        "dataset/split_manifest.csv",
        "surrogate/fit_manifest.json",
        "surrogate/metrics.csv",
        "payload_manifest.csv",
        "validation/exact_validation.json",
        "validation/stochastic_validation.json",
        "validation/manifest.json",
    ):
        target = artifact_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)

    summary = module.prepare_preflight(artifact_root)

    assert summary["IRC_CMPO_READY_FOR_QCI"] == "YES"
    assert summary["dataset"]["successful_labels"] == 3000
    assert summary["payloads"]["payload_count"] == 6
    assert summary["payloads"]["maximum_variables"] == 33
    assert summary["payloads"]["maximum_degree"] == 3
    assert summary["offline_validation"]["projection_used"] is False
    assert (artifact_root / "preflight_summary.json").is_file()
    assert (artifact_root / "preflight_report.md").is_file()
