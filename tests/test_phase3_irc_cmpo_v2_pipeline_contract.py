from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corrected_pipeline_defaults_are_create_only_v2() -> None:
    fit = _load_script("phase3_fit_irc_cmpo_surrogate.py")
    build = _load_script("phase3_build_irc_cmpo_payloads.py")
    validate = _load_script("phase3_validate_irc_cmpo_offline.py")
    finalize = _load_script("phase3_finalize_irc_cmpo_prequeue.py")

    assert all("final_prequeue_v2" in name for name in fit.ARTIFACT_NAMES)
    assert build.PAYLOAD_DIRECTORY == "payloads_final_prequeue_v3"
    assert build.UNQUANTIZED_DIRECTORY == "unquantized_payloads_final_prequeue_v3"
    assert build.MANIFEST_NAME == "payload_manifest_final_prequeue_v3.csv"
    assert build.AUDIT_CSV_NAME == "coefficient_audit_final_prequeue_v3.csv"
    assert build.AUDIT_MD_NAME == "coefficient_audit_final_prequeue_v3.md"
    assert validate.DEFAULT_MANIFEST.name == "payload_manifest_final_prequeue_v3.csv"
    assert validate.DEFAULT_OUTPUT_DIRECTORY == "offline_validation_final_prequeue_v4"
    assert validate.EXACT_JSON == "exact_validation_final_prequeue_v4.json"
    assert validate.STOCHASTIC_JSON == "stochastic_validation_final_prequeue_v4.json"
    assert finalize.REPORT_NAME == "final_prequeue_report_v4.md"
    assert finalize.SUMMARY_NAME == "final_prequeue_summary_v4.json"


def test_finalizer_prefers_v2_and_marks_strict_stop_downstream_not_run(tmp_path: Path) -> None:
    module = _load_script("phase3_finalize_irc_cmpo_prequeue.py")
    (tmp_path / "final_prequeue_report.md").write_text("v1 report\n", encoding="utf-8")
    (tmp_path / "final_prequeue_summary.json").write_text("{}\n", encoding="utf-8")
    surrogate_dir = tmp_path / "surrogate"
    surrogate_dir.mkdir(parents=True)
    passing_target = {"metrics": {"gate_passed": True}}
    (surrogate_dir / "surrogate_model_final_prequeue_v1.json").write_text(
        json.dumps(
            {
                "gates_passed": True,
                "targets": {f"target-{index}": passing_target for index in range(5)},
            }
        ),
        encoding="utf-8",
    )
    (surrogate_dir / "surrogate_model_final_prequeue_v2.json").write_text(
        json.dumps(
            {
                "gates_passed": False,
                "targets": {f"target-{index}": passing_target for index in range(5)},
            }
        ),
        encoding="utf-8",
    )

    evidence = module.collect_evidence(tmp_path)

    assert evidence["surrogate_valid"] is False
    assert evidence["evidence_sources"]["surrogate"].endswith(
        "surrogate_model_final_prequeue_v2.json"
    )
    assert evidence["prior_v1_evidence"]["surrogate_present"] is True
    assert evidence["prior_v1_evidence"]["final_report_present"] is True
    assert evidence["prior_v1_evidence"]["final_summary_present"] is True
    assert evidence["gate_status"]["surrogate_valid"] == "FAIL"
    assert evidence["gate_status"]["dynamic_range_valid"] == "NOT RUN"
    assert evidence["gate_status"]["exact_hamiltonian_valid"] == "NOT RUN"
    assert evidence["gate_status"]["local_stochastic_valid"] == "NOT RUN"
    assert "DYNAMIC_RANGE_VALID: NOT RUN" in module.summary_lines(evidence)


def test_final_report_v2_preserves_prior_v1_report(tmp_path: Path) -> None:
    module = _load_script("phase3_finalize_irc_cmpo_prequeue.py")
    v1_report = tmp_path / "final_prequeue_report.md"
    v1_summary = tmp_path / "final_prequeue_summary.json"
    v1_report.write_text("failed v1 report\n", encoding="utf-8")
    v1_summary.write_text('{"version": 1}\n', encoding="utf-8")
    evidence = {
        **{key: True for key in module.GATE_KEYS},
        "IRC_CMPO_READY_FOR_QCI": "YES",
        "historical_counts": {},
        "dataset": {},
        "surrogate_metrics": {},
        "gate_status": {key: "PASS" for key in module.GATE_KEYS},
        "strict_stop_reason": "none",
    }

    report, summary = module.write_final_report(tmp_path, evidence)

    assert report.name == "final_prequeue_report_v4.md"
    assert summary.name == "final_prequeue_summary_v4.json"
    assert v1_report.read_text(encoding="utf-8") == "failed v1 report\n"
    assert v1_summary.read_text(encoding="utf-8") == '{"version": 1}\n'
    assert "DYNAMIC_RANGE_VALID: PASS" in report.read_text(encoding="utf-8")


def test_missing_v2_surrogate_is_reported_as_not_run(tmp_path: Path) -> None:
    module = _load_script("phase3_finalize_irc_cmpo_prequeue.py")
    evidence = module.collect_evidence(tmp_path)

    report, _ = module.write_final_report(tmp_path, evidence)

    text = report.read_text(encoding="utf-8")
    assert "surrogate artifacts are unavailable; gate `NOT RUN`" in text
    assert "DYNAMIC_RANGE_VALID: NOT RUN" in text


def test_offline_pipeline_scripts_have_no_qci_transport_or_network_imports() -> None:
    forbidden = ("qci_client", "qci_integer_adapter", "requests", "urllib", "httpx")
    for name in (
        "phase3_fit_irc_cmpo_surrogate.py",
        "phase3_build_irc_cmpo_payloads.py",
        "phase3_validate_irc_cmpo_offline.py",
        "phase3_finalize_irc_cmpo_prequeue.py",
    ):
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert not any(f"import {token}" in source or f"from {token}" in source for token in forbidden)
