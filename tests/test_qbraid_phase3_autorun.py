from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "qbraid_phase3_autorun.py"
    spec = importlib.util.spec_from_file_location("qbraid_phase3_autorun", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, payload_dir: Path) -> Path:
    payload_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(6):
        payload_path = payload_dir / f"lambda_{index:02d}.json"
        payload_path.write_text("{}", encoding="utf-8")
        rows.append(
            {
                "lambda_index": index,
                "cost_weight": float(index),
                "scaled_payload_path": f"/stale/results/phase3/irc_cmpo/payloads_final_prequeue_v3/lambda_{index:02d}.json",
                "post_quantization_gates_passed": True,
                "projection_used": False,
                "qci_jobs_submitted": 0,
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_verified_artifacts(root: Path, *, cpu_fallback_used: bool = False) -> tuple[Path, Path, Path]:
    manifest = _write_manifest(root / "payload_manifest.csv", root / "payloads")
    artifacts = root / "baselines" / "gpu"
    artifacts.mkdir(parents=True, exist_ok=True)
    summary = artifacts / "gpu_baseline_summary.json"
    summary.write_text(
        json.dumps(
            {
                "lambda_count": 6,
                "cpu_fallback_used": cpu_fallback_used,
                "projection_used": False,
                "qci_jobs_submitted": 0,
            }
        ),
        encoding="utf-8",
    )
    metrics = artifacts / "gpu_baseline_metrics.csv"
    with metrics.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["lambda_index", "method", "gpu_model", "gpu_backend", "projection_used"],
        )
        writer.writeheader()
        for index in range(6):
            for method in (
                "gpu_simulated_annealing",
                "gpu_random_restart",
                "gpu_parallel_local_search",
            ):
                writer.writerow(
                    {
                        "lambda_index": index,
                        "method": method,
                        "gpu_model": "NVIDIA L4",
                        "gpu_backend": "cupy_cuda",
                        "projection_used": False,
                    }
                )
    exact = artifacts / "exact_milp_references.json"
    exact.write_text("[]", encoding="utf-8")
    return manifest, root / "payloads", artifacts


def test_module_import_does_not_require_qbraid_packages() -> None:
    module = _load_module()

    assert module.DEFAULT_GPU_PROFILE == "gpu-l4"


def test_build_parser_help_mentions_auto_verify_and_dry_run(capsys) -> None:
    module = _load_module()

    with pytest.raises(SystemExit, match="0"):
        module.build_parser().parse_args(["--help"])

    help_text = capsys.readouterr().out
    assert "--mode {auto,local,qbraid,verify}" in help_text
    assert "--dry-run" in help_text


def test_load_qbraid_dotenv_uses_local_file_without_overriding_environment(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_module()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QBRAID_API_KEY=from-file\n"
        "QBRAID_API_URL='https://example.invalid/api'\n"
        "IGNORED=value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QBRAID_API_KEY", "from-process")
    monkeypatch.delenv("QBRAID_API_URL", raising=False)

    loaded = module.load_qbraid_dotenv(env_file)

    assert loaded == {
        "QBRAID_API_KEY": "from-file",
        "QBRAID_API_URL": "https://example.invalid/api",
    }
    assert module.os.environ["QBRAID_API_KEY"] == "from-process"
    assert module.os.environ["QBRAID_API_URL"] == "https://example.invalid/api"


def test_write_portable_manifest_retargets_payload_dir(tmp_path: Path) -> None:
    module = _load_module()
    source_manifest = _write_manifest(tmp_path / "payload_manifest.csv", tmp_path / "source-payloads")
    payload_dir = tmp_path / "payloads"
    for index in range(6):
        (payload_dir / f"lambda_{index:02d}.json").parent.mkdir(parents=True, exist_ok=True)
        (payload_dir / f"lambda_{index:02d}.json").write_text("{}", encoding="utf-8")

    rewritten = module.write_portable_manifest(
        source_manifest,
        payload_dir,
        tmp_path / "portable_manifest.csv",
    )

    rows = list(csv.DictReader(rewritten.open(encoding="utf-8", newline="")))
    assert len(rows) == 6
    assert {Path(row["scaled_payload_path"]) for row in rows} == {
        payload_dir / f"lambda_{index:02d}.json" for index in range(6)
    }


def test_verify_checked_in_artifacts_accepts_final_gpu_bundle(tmp_path: Path) -> None:
    module = _load_module()
    manifest, payload_dir, artifacts = _write_verified_artifacts(tmp_path)

    result = module.verify_checked_in_artifacts(
        manifest_path=manifest,
        payload_dir=payload_dir,
        artifact_dir=artifacts,
    )

    assert result["status"] == "verified"
    assert result["lambda_count"] == 6
    assert result["metrics_rows"] == 18
    assert result["cpu_fallback_used"] is False


def test_verify_checked_in_artifacts_rejects_cpu_fallback_labels(tmp_path: Path) -> None:
    module = _load_module()
    manifest, payload_dir, artifacts = _write_verified_artifacts(tmp_path, cpu_fallback_used=True)

    with pytest.raises(ValueError, match="CPU fallback"):
        module.verify_checked_in_artifacts(
            manifest_path=manifest,
            payload_dir=payload_dir,
            artifact_dir=artifacts,
        )


def test_main_dry_run_defaults_to_verify_without_cuda_or_key(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "detect_local_cuda", lambda: False)
    monkeypatch.delenv("QBRAID_API_KEY", raising=False)
    monkeypatch.delenv("QBRAID_APIKEY", raising=False)

    exit_code = module.main(
        ["--dry-run", "--env-file", str(tmp_path / "missing.env")]
    )

    assert exit_code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "verify"


def test_main_auto_prefers_local_cuda(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(module, "detect_local_cuda", lambda: True)
    monkeypatch.setattr(
        module,
        "run_local_final_gpu",
        lambda **kwargs: calls.append(kwargs) or {"status": "completed", "mode": "local"},
    )

    exit_code = module.main(
        [
            "--env-file",
            str(tmp_path / "missing.env"),
            "--manifest",
            str(tmp_path / "payload_manifest.csv"),
            "--payload-dir",
            str(tmp_path / "payloads"),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1


def test_main_auto_uses_qbraid_when_no_cuda_and_key_present(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_module()
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(module, "detect_local_cuda", lambda: False)
    monkeypatch.setenv("QBRAID_API_KEY", "secret")
    monkeypatch.setattr(
        module,
        "run_qbraid_final_gpu",
        lambda **kwargs: calls.append(kwargs) or {"status": "completed", "mode": "qbraid"},
    )

    exit_code = module.main(
        [
            "--env-file",
            str(tmp_path / "missing.env"),
            "--manifest",
            str(tmp_path / "payload_manifest.csv"),
            "--payload-dir",
            str(tmp_path / "payloads"),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1


def test_main_auto_verifies_checked_in_artifacts_when_no_cuda_or_key(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_module()
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(module, "detect_local_cuda", lambda: False)
    monkeypatch.delenv("QBRAID_API_KEY", raising=False)
    monkeypatch.delenv("QBRAID_APIKEY", raising=False)
    monkeypatch.setattr(
        module,
        "verify_checked_in_artifacts",
        lambda **kwargs: calls.append(kwargs) or {"status": "verified", "mode": "verify"},
    )

    exit_code = module.main(
        [
            "--env-file",
            str(tmp_path / "missing.env"),
            "--manifest",
            str(tmp_path / "payload_manifest.csv"),
            "--payload-dir",
            str(tmp_path / "payloads"),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1
