from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts/phase3_finalize_irc_cmpo_prequeue.py"
    spec = importlib.util.spec_from_file_location("irc_final_prequeue", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readiness_is_yes_only_when_every_offline_gate_passes() -> None:
    module = _module()
    evidence = {
        "historical_mode_audit": True,
        "integer_adapter_dry_run": True,
        "true_recourse_valid": True,
        "surrogate_valid": True,
        "dynamic_range_valid": True,
        "exact_hamiltonian_valid": True,
        "local_stochastic_valid": True,
    }
    assert module.readiness_from_evidence(evidence) == "YES"
    for key in evidence:
        broken = dict(evidence)
        broken[key] = False
        assert module.readiness_from_evidence(broken) == "NO"


def test_summary_lines_are_exact_and_ordered() -> None:
    module = _module()
    evidence = {key.rstrip(":").lower(): True for key in module.SUMMARY_KEYS[:-1]}
    evidence["irc_cmpo_ready_for_qci"] = True
    lines = module.summary_lines(evidence)
    assert len(lines) == 8
    assert [line.split(":", 1)[0] + ":" for line in lines] == list(module.SUMMARY_KEYS)
