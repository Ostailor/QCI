#!/usr/bin/env python
"""Judge-facing autorunner for final IRC-CMPO Phase 3 GPU baselines."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "results/phase3/irc_cmpo/payload_manifest.csv"
DEFAULT_PAYLOAD_DIR = ROOT / "results/phase3/irc_cmpo/payloads"
DEFAULT_ARTIFACT_DIR = ROOT / "results/phase3/irc_cmpo/baselines/gpu"
DEFAULT_OUTPUT_DIR = ROOT / "results/phase3/reproduced/irc_cmpo/gpu_baselines"
DEFAULT_CONFIG = ROOT / "configs/phase3_irc_cmpo_ieee123.yaml"
DEFAULT_GPU_PROFILE = "gpu-l4"
EXPECTED_METHODS = (
    "gpu_simulated_annealing",
    "gpu_random_restart",
    "gpu_parallel_local_search",
)
SUMMARY_NAME = "gpu_baseline_summary.json"
METRICS_NAME = "gpu_baseline_metrics.csv"
EXACT_NAME = "exact_milp_references.json"


class InstanceRun:
    def __init__(self, *, profile: str, instance_id: str, url: str) -> None:
        self.profile = profile
        self.instance_id = instance_id
        self.url = url
        self.result_archive: Path | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "instance_id": self.instance_id,
            "url": self.url,
            "result_archive": None if self.result_archive is None else str(self.result_archive),
        }


class JupyterRemote:
    """Minimal Jupyter REST/kernel client for qBraid Lab instances."""

    def __init__(self, lab_url: str) -> None:
        parsed = urllib.parse.urlparse(lab_url)
        params = urllib.parse.parse_qs(parsed.query)
        token = params.get("token", [""])[0]
        if not token:
            raise ValueError("qBraid instance URL does not include a Jupyter token")
        base_path = parsed.path.split("/lab", 1)[0].rstrip("/") + "/"
        self.base_http = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, base_path, "", "", ""))
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self.base_ws = urllib.parse.urlunparse((ws_scheme, parsed.netloc, base_path, "", "", ""))
        self.token = token
        self.context = ssl.create_default_context()

    def _request(self, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base_http + path,
            data=body,
            method=method,
            headers={"Authorization": f"token {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120, context=self.context) as response:
            raw = response.read()
        return json.loads(raw or b"{}")

    def wait_ready(self, timeout: int = 300) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self._request("api/status")
                return
            except Exception:
                time.sleep(5)
        raise TimeoutError("qBraid Jupyter API did not become ready")

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        encoded = base64.b64encode(local_path.read_bytes()).decode("utf-8")
        self._request(
            f"api/contents/{remote_path}",
            method="PUT",
            payload={"type": "file", "format": "base64", "content": encoded},
        )

    def download_file(self, remote_path: str, local_path: Path) -> None:
        obj = self._request(f"api/contents/{remote_path}?content=1")
        content = obj.get("content", "")
        data = base64.b64decode(content) if obj.get("format") == "base64" else content.encode("utf-8")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

    def execute(self, code: str, *, timeout: int = 7200, echo_prefix: str = "") -> None:
        try:
            import websocket
        except ImportError as exc:  # pragma: no cover - depends on optional local package
            raise SystemExit(
                "Missing qBraid autorun dependencies. Install with: "
                "python -m pip install qbraid-core websocket-client"
            ) from exc

        kernel = self._request("api/kernels", method="POST", payload={"name": "python3"})
        kernel_id = kernel["id"]
        ws = websocket.create_connection(
            self.base_ws + f"api/kernels/{kernel_id}/channels?session_id={uuid.uuid4()}",
            header=[f"Authorization: token {self.token}"],
            timeout=120,
            sslopt={"cert_reqs": ssl.CERT_REQUIRED},
        )
        try:
            msg_id = uuid.uuid4().hex
            message = {
                "header": {
                    "msg_id": msg_id,
                    "username": "cmpo",
                    "session": uuid.uuid4().hex,
                    "msg_type": "execute_request",
                    "version": "5.3",
                },
                "parent_header": {},
                "metadata": {},
                "content": {
                    "code": code,
                    "silent": False,
                    "store_history": False,
                    "user_expressions": {},
                    "allow_stdin": False,
                    "stop_on_error": True,
                },
                "channel": "shell",
            }
            ws.send(json.dumps(message))
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ws.recv()
                reply = json.loads(raw)
                if reply.get("parent_header", {}).get("msg_id") != msg_id:
                    continue
                msg_type = reply.get("msg_type") or reply.get("header", {}).get("msg_type")
                content = reply.get("content", {})
                if msg_type == "stream":
                    text = content.get("text", "")
                    if text:
                        print(f"{echo_prefix}{text}", end="", flush=True)
                elif msg_type == "error":
                    traceback = "\n".join(content.get("traceback", []))
                    raise RuntimeError(f"{content.get('ename')}: {content.get('evalue')}\n{traceback}")
                elif msg_type == "status" and content.get("execution_state") == "idle":
                    return
            raise TimeoutError("remote qBraid execution timed out")
        finally:
            ws.close()
            try:
                self._request(f"api/kernels/{kernel_id}", method="DELETE")
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Execute or verify the final IRC-CMPO Phase 3 NVIDIA GPU baselines. "
            "The full rebuild selects qBraid L4 mode explicitly."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "local", "qbraid", "verify"),
        default="auto",
        help="Execution mode; the documented full rebuild uses 'qbraid'.",
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Final IRC-CMPO payload manifest CSV.")
    parser.add_argument("--payload-dir", default=str(DEFAULT_PAYLOAD_DIR), help="Directory with six final payload JSON files.")
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Directory containing checked-in GPU baseline artifacts for verification mode.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for new GPU baseline runs.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Final IRC-CMPO config for the GPU baseline runner.")
    parser.add_argument("--candidate-count", type=int, default=10_000, help="Native binary candidates per lambda/method.")
    parser.add_argument("--gpu-profile", default=DEFAULT_GPU_PROFILE, help="qBraid GPU profile slug for remote mode.")
    parser.add_argument("--start-timeout", type=int, default=900, help="Seconds to wait for the qBraid L4 instance.")
    parser.add_argument("--run-timeout", type=int, default=14_400, help="Seconds to wait for the remote GPU baseline run.")
    parser.add_argument("--keep-instance", action="store_true", help="Do not stop the qBraid instance after a remote run.")
    parser.add_argument(
        "--env-file",
        default=str(ROOT / ".env"),
        help="Local .env file containing QBRAID_API_KEY and optional QBRAID_API_URL.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the selected plan and exit without running anything.")
    return parser


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return ROOT / value


def detect_local_cuda() -> bool:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False
    try:
        probe = subprocess.run(
            [nvidia_smi, "-L"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return probe.returncode == 0 and bool(probe.stdout.strip())


def _parse_env_value(value: str) -> str:
    parsed = value.strip()
    if (
        len(parsed) >= 2
        and parsed[0] == parsed[-1]
        and parsed[0] in {"'", '"'}
    ):
        return parsed[1:-1]
    return parsed


def load_qbraid_dotenv(path: str | Path = ROOT / ".env") -> dict[str, str]:
    """Load qBraid settings from .env without replacing process values."""

    env_path = Path(path)
    if not env_path.is_file():
        return {}
    loaded: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in {"QBRAID_API_KEY", "QBRAID_API_URL"}:
            continue
        parsed = _parse_env_value(value)
        loaded[key] = parsed
        os.environ.setdefault(key, parsed)
    return loaded


def get_qbraid_api_key(*, required: bool) -> str:
    api_key = os.environ.get("QBRAID_API_KEY") or os.environ.get("QBRAID_APIKEY") or ""
    if required and not api_key:
        raise SystemExit("Set QBRAID_API_KEY before running qBraid remote mode.")
    return api_key


def choose_mode(requested_mode: str, *, has_cuda: bool, has_api_key: bool) -> str:
    if requested_mode == "auto":
        if has_cuda:
            return "local"
        if has_api_key:
            return "qbraid"
        return "verify"
    if requested_mode == "local" and not has_cuda:
        raise SystemExit("Local GPU mode requires a visible CUDA device; CPU fallback is forbidden.")
    if requested_mode == "qbraid" and not has_api_key:
        raise SystemExit("qBraid mode requires QBRAID_API_KEY.")
    return requested_mode


def _read_manifest_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: int(row["lambda_index"]))
    if len(rows) != 6 or [int(row["lambda_index"]) for row in rows] != list(range(6)):
        raise ValueError("final IRC-CMPO Phase 3 requires exactly six ordered lambda payloads")
    return rows


def write_portable_manifest(manifest_path: str | Path, payload_dir: str | Path, target_path: str | Path) -> Path:
    source = resolve_path(manifest_path)
    payload_root = resolve_path(payload_dir)
    target = Path(target_path)
    rows = _read_manifest_rows(source)
    rewritten: list[dict[str, str]] = []
    for row in rows:
        index = int(row["lambda_index"])
        payload_path = payload_root / f"lambda_{index:02d}.json"
        rewritten_row = dict(row)
        rewritten_row["scaled_payload_path"] = str(payload_path)
        rewritten.append(rewritten_row)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rewritten[0]))
        writer.writeheader()
        writer.writerows(rewritten)
    return target


def verify_checked_in_artifacts(
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    payload_dir: str | Path = DEFAULT_PAYLOAD_DIR,
    artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Any]:
    manifest = resolve_path(manifest_path)
    payload_root = resolve_path(payload_dir)
    artifacts = resolve_path(artifact_dir)
    rows = _read_manifest_rows(manifest)
    for row in rows:
        payload = payload_root / f"lambda_{int(row['lambda_index']):02d}.json"
        if not payload.is_file():
            raise FileNotFoundError(f"Missing final payload: {payload}")
    summary_path = artifacts / SUMMARY_NAME
    metrics_path = artifacts / METRICS_NAME
    exact_path = artifacts / EXACT_NAME
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if bool(summary.get("cpu_fallback_used", False)):
        raise ValueError("CPU fallback cannot be labeled as a GPU baseline result")
    if int(summary.get("lambda_count", 0)) != 6:
        raise ValueError("checked-in GPU summary must report exactly six lambdas")
    if bool(summary.get("projection_used", True)):
        raise ValueError("checked-in GPU summary must record projection_used=false")
    metrics_rows = list(csv.DictReader(metrics_path.open(encoding="utf-8", newline="")))
    if len(metrics_rows) != 18:
        raise ValueError("checked-in GPU metrics must contain 18 rows")
    methods = {row["method"] for row in metrics_rows}
    if methods != set(EXPECTED_METHODS):
        raise ValueError(f"checked-in GPU metrics must include {EXPECTED_METHODS}")
    if any(str(row.get("projection_used", "")).strip().lower() != "false" for row in metrics_rows):
        raise ValueError("checked-in GPU metrics must record projection_used=false")
    if any(not str(row.get("gpu_model", "")).strip() or not str(row.get("gpu_backend", "")).strip() for row in metrics_rows):
        raise ValueError("checked-in GPU metrics must identify the GPU model and backend")
    json.loads(exact_path.read_text(encoding="utf-8"))
    return {
        "status": "verified",
        "mode": "verify",
        "manifest_path": str(manifest),
        "payload_dir": str(payload_root),
        "artifact_dir": str(artifacts),
        "lambda_count": 6,
        "metrics_rows": len(metrics_rows),
        "cpu_fallback_used": False,
    }


def _relative_to_root(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Remote qBraid mode requires repository-local paths, got {path}") from exc


def _should_skip(rel_path: Path, excluded_prefixes: Sequence[Path]) -> bool:
    if any(part in {".git", ".env", ".omx", ".pytest_cache", "__pycache__"} or part.endswith(".pyc") for part in rel_path.parts):
        return True
    return any(rel_path == prefix or prefix in rel_path.parents for prefix in excluded_prefixes)


def make_workspace_archive(*, exclude_paths: Sequence[Path]) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="cmpo-qbraid-"))
    archive = tmpdir / "qci_phase3_workspace.tgz"
    excluded_prefixes = tuple(_relative_to_root(path) for path in exclude_paths if path.exists())
    with tarfile.open(archive, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            if _should_skip(rel, excluded_prefixes):
                continue
            tar.add(path, arcname=Path("QCI") / rel)
    return archive


def _run_subprocess(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(list(command), cwd=cwd, check=True)


def run_local_final_gpu(
    *,
    manifest_path: str | Path,
    payload_dir: str | Path,
    output_dir: str | Path,
    candidate_count: int,
    config_path: str | Path,
) -> dict[str, Any]:
    output = resolve_path(output_dir)
    with tempfile.TemporaryDirectory(prefix="irc-cmpo-final-gpu-") as tmpdir:
        portable_manifest = write_portable_manifest(
            manifest_path,
            payload_dir,
            Path(tmpdir) / "payload_manifest_portable.csv",
        )
        _run_subprocess(
            [
                "bash",
                str(ROOT / "scripts/qbraid_run_phase3_gpu.sh"),
                str(portable_manifest),
                str(output),
                str(candidate_count),
                str(resolve_path(config_path)),
            ]
        )
    return {
        "status": "completed",
        "mode": "local",
        "output_dir": str(output),
        "cpu_fallback_used": False,
    }


def _load_qbraid_dependencies() -> tuple[Any, Any, Any]:
    try:
        from qbraid_core.services.compute import ComputeClient
        from qbraid_core.services.compute.schemas import BMAStatus
        from qbraid_core.sessions import QbraidSessionV1
    except ImportError as exc:  # pragma: no cover - depends on optional local package
        raise SystemExit(
            "Missing qBraid autorun dependencies. Install with: "
            "python -m pip install qbraid-core websocket-client"
        ) from exc
    return ComputeClient, BMAStatus, QbraidSessionV1


def _start_instance(client: Any, target_status: Any, profile: str, timeout: int) -> InstanceRun:
    instance = client.provision_bma_instance(profile)
    instance = client.wait_for_bma_instance(instance.instance_id, target_status=target_status.RUNNING, timeout=timeout)
    if not instance.url:
        raise RuntimeError("qBraid instance reached RUNNING without a Jupyter URL")
    return InstanceRun(profile=profile, instance_id=instance.instance_id, url=instance.url)


def _stop_instance(client: Any, target_status: Any, run: InstanceRun, timeout: int = 300) -> None:
    try:
        client.stop_bma_instance(run.instance_id)
        client.wait_for_bma_instance(run.instance_id, target_status=target_status.STOPPED, timeout=timeout)
    except Exception as exc:
        print(f"WARNING: failed to stop qBraid instance {run.instance_id}: {exc}", file=sys.stderr)


def _remote_script(
    *,
    manifest_rel: Path,
    payload_dir_rel: Path,
    portable_manifest_rel: Path,
    output_rel: Path,
    config_rel: Path,
    candidate_count: int,
) -> str:
    return f"""
import csv
import json
import subprocess
import sys
import tarfile
from pathlib import Path

home = Path.home()
archive = home / "qci_phase3_workspace.tgz"
repo = home / "QCI"
if repo.exists():
    subprocess.run(["rm", "-rf", str(repo)], check=True)
with tarfile.open(archive, "r:gz") as tar:
    tar.extractall(home)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "--no-input", "--progress-bar", "off", "--break-system-packages", "-r", str(repo / "requirements.txt")],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "--no-input", "--progress-bar", "off", "--break-system-packages", "cupy-cuda12x[ctk]"],
    check=True,
)
manifest = repo / {manifest_rel.as_posix()!r}
payload_dir = repo / {payload_dir_rel.as_posix()!r}
portable = repo / {portable_manifest_rel.as_posix()!r}
rows = []
with manifest.open(encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        index = int(row["lambda_index"])
        row["scaled_payload_path"] = str(payload_dir / f"lambda_{{index:02d}}.json")
        rows.append(row)
portable.parent.mkdir(parents=True, exist_ok=True)
with portable.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
output_dir = repo / {output_rel.as_posix()!r}
subprocess.run(
    [
        sys.executable,
        str(repo / "scripts/phase3_run_irc_cmpo_gpu_final.py"),
        "--manifest",
        str(portable),
        "--output-dir",
        str(output_dir),
        "--candidate-count",
        str({candidate_count}),
        "--config",
        str(repo / {config_rel.as_posix()!r}),
    ],
    cwd=repo,
    check=True,
)
bundle = home / "qci_phase3_gpu_results.tgz"
with tarfile.open(bundle, "w:gz") as tar:
    tar.add(output_dir, arcname={output_rel.as_posix()!r})
print(json.dumps({{"output_dir": str(output_dir), "archive": str(bundle)}}, indent=2), flush=True)
"""


def _run_remote_qbraid_job(
    *,
    run: InstanceRun,
    archive: Path,
    manifest_path: Path,
    payload_dir: Path,
    output_dir: Path,
    config_path: Path,
    candidate_count: int,
    timeout: int,
) -> None:
    remote = JupyterRemote(run.url)
    remote.wait_ready()
    remote.upload_file(archive, "qci_phase3_workspace.tgz")
    remote.execute(
        _remote_script(
            manifest_rel=_relative_to_root(manifest_path),
            payload_dir_rel=_relative_to_root(payload_dir),
            portable_manifest_rel=Path("results/phase3/irc_cmpo/payload_manifest_qbraid_portable.csv"),
            output_rel=_relative_to_root(output_dir),
            config_rel=_relative_to_root(config_path),
            candidate_count=candidate_count,
        ),
        timeout=timeout,
        echo_prefix="[qbraid] ",
    )
    local_archive = output_dir.parent / "qbraid_final_gpu_results.tgz"
    remote.download_file("qci_phase3_gpu_results.tgz", local_archive)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    with tarfile.open(local_archive, "r:gz") as tar:
        tar.extractall(ROOT)
    run.result_archive = local_archive


def run_qbraid_final_gpu(
    *,
    manifest_path: str | Path,
    payload_dir: str | Path,
    output_dir: str | Path,
    config_path: str | Path,
    candidate_count: int,
    gpu_profile: str,
    start_timeout: int,
    run_timeout: int,
    keep_instance: bool,
) -> dict[str, Any]:
    ComputeClient, BMAStatus, QbraidSessionV1 = _load_qbraid_dependencies()
    manifest = resolve_path(manifest_path)
    payload_root = resolve_path(payload_dir)
    output = resolve_path(output_dir)
    config = resolve_path(config_path)
    archive = make_workspace_archive(exclude_paths=(output,))
    api_url = os.environ.get("QBRAID_API_URL", "https://api-v2.qbraid.com/api/v1")
    api_key = get_qbraid_api_key(required=True)
    client = ComputeClient(session=QbraidSessionV1(api_key=api_key, base_url=api_url))
    run: InstanceRun | None = None
    try:
        print(f"Starting qBraid GPU instance with profile {gpu_profile}", flush=True)
        run = _start_instance(client, BMAStatus, gpu_profile, start_timeout)
        _run_remote_qbraid_job(
            run=run,
            archive=archive,
            manifest_path=manifest,
            payload_dir=payload_root,
            output_dir=output,
            config_path=config,
            candidate_count=candidate_count,
            timeout=run_timeout,
        )
        return {
            "status": "completed",
            "mode": "qbraid",
            "output_dir": str(output),
            "cpu_fallback_used": False,
            "instance": run.as_dict(),
        }
    finally:
        if run is not None and not keep_instance:
            print(f"Stopping qBraid instance {run.instance_id}", flush=True)
            _stop_instance(client, BMAStatus, run)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_qbraid_dotenv(args.env_file)
    manifest = resolve_path(args.manifest)
    payload_dir = resolve_path(args.payload_dir)
    artifact_dir = resolve_path(args.artifact_dir)
    output_dir = resolve_path(args.output_dir)
    config = resolve_path(args.config)
    has_cuda = detect_local_cuda()
    has_api_key = bool(get_qbraid_api_key(required=False))
    mode = choose_mode(args.mode, has_cuda=has_cuda, has_api_key=has_api_key)
    plan = {
        "mode": mode,
        "requested_mode": args.mode,
        "has_local_cuda": has_cuda,
        "has_qbraid_api_key": has_api_key,
        "manifest": str(manifest),
        "payload_dir": str(payload_dir),
        "artifact_dir": str(artifact_dir),
        "output_dir": str(output_dir),
        "config": str(config),
        "candidate_count": args.candidate_count,
        "gpu_profile": args.gpu_profile,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0

    if mode == "local":
        result = run_local_final_gpu(
            manifest_path=manifest,
            payload_dir=payload_dir,
            output_dir=output_dir,
            candidate_count=args.candidate_count,
            config_path=config,
        )
    elif mode == "qbraid":
        result = run_qbraid_final_gpu(
            manifest_path=manifest,
            payload_dir=payload_dir,
            output_dir=output_dir,
            config_path=config,
            candidate_count=args.candidate_count,
            gpu_profile=args.gpu_profile,
            start_timeout=args.start_timeout,
            run_timeout=args.run_timeout,
            keep_instance=args.keep_instance,
        )
    else:
        try:
            result = verify_checked_in_artifacts(
                manifest_path=manifest,
                payload_dir=payload_dir,
                artifact_dir=artifact_dir,
            )
        except Exception as exc:
            if args.mode == "auto":
                raise SystemExit(
                    "No local CUDA detected and QBRAID_API_KEY is not set. "
                    f"Checked-in artifact verification failed: {exc}"
                ) from exc
            raise

    print(json.dumps({**plan, **result}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
