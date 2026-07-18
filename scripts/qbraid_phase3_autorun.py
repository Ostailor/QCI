#!/usr/bin/env python
"""qBraid API autorunner for judge-facing Phase 3 CPU/GPU baselines."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import ssl
import sys
import tarfile
import tempfile
import time
import uuid
import urllib.parse
import urllib.request
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    import websocket
    from qbraid_core.services.compute import ComputeClient
    from qbraid_core.services.compute.schemas import BMAStatus
    from qbraid_core.sessions import QbraidSessionV1
except ImportError as exc:  # pragma: no cover - exercised by wrapper script
    raise SystemExit(
        "Missing qBraid autorun dependencies. Install with: "
        "python -m pip install qbraid-core websocket-client"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "configs/phase3_qci_small.yaml"
DEFAULT_OUTPUT = Path("results/phase3/qbraid_autorun")


@dataclass
class InstanceRun:
    role: str
    profile: str
    instance_id: str
    url: str
    result_archive: Path | None = None


class JupyterRemote:
    """Small Jupyter REST/kernel client for qBraid Lab instances."""

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
        body = json.dumps(payload).encode() if payload is not None else None
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
        encoded = base64.b64encode(local_path.read_bytes()).decode()
        self._request(
            f"api/contents/{remote_path}",
            method="PUT",
            payload={"type": "file", "format": "base64", "content": encoded},
        )

    def download_file(self, remote_path: str, local_path: Path) -> None:
        obj = self._request(f"api/contents/{remote_path}?content=1")
        content = obj.get("content", "")
        data = base64.b64decode(content) if obj.get("format") == "base64" else content.encode()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

    def execute(self, code: str, *, timeout: int = 7200, echo_prefix: str = "") -> None:
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
            "Create qBraid CPU and GPU instances through the qBraid API, run Phase 3 "
            "CPU/GPU baselines, collect results, and stop the instances."
        )
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Phase 3 config to run on both qBraid instances.")
    parser.add_argument("--cpu-profile", default="cpu-8v-32g", help="qBraid CPU profile slug.")
    parser.add_argument("--gpu-profile", default="gpu-l4", help="qBraid GPU profile slug.")
    parser.add_argument("--cpu-repeats", type=int, default=10, help="CPU baseline repeats.")
    parser.add_argument("--gpu-repeats", type=int, default=50, help="GPU baseline repeats.")
    parser.add_argument("--gpu-restarts", type=int, default=8192, help="CUDA random-restart candidates per repeat.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Local output directory for collected archives.")
    parser.add_argument("--start-timeout", type=int, default=900, help="Seconds to wait for each qBraid instance.")
    parser.add_argument("--run-timeout", type=int, default=14400, help="Seconds to wait for each remote run.")
    parser.add_argument("--keep-instances", action="store_true", help="Do not stop qBraid instances after the run.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without creating qBraid instances.")
    return parser


def _check_environment() -> str:
    api_key = os.environ.get("QBRAID_API_KEY") or os.environ.get("QBRAID_APIKEY")
    if not api_key:
        raise SystemExit("Set QBRAID_API_KEY before running qBraid autorun.")
    return api_key


def _make_workspace_archive() -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="cmpo-qbraid-"))
    archive = tmpdir / "qci_phase3_workspace.tgz"
    excludes = {
        ".git",
        ".env",
        ".omx",
        ".pytest_cache",
        "__pycache__",
        "results",
    }
    with tarfile.open(archive, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            if any(part in excludes or part.endswith(".pyc") for part in rel.parts):
                continue
            tar.add(path, arcname=Path("QCI") / rel)
    return archive


def _remote_script(role: str, config: str, repeats: int, gpu_restarts: int) -> str:
    disabled = [
        "include_greedy",
        "include_slsqp",
        "include_differential_evolution",
        "include_cmpo_local",
        "include_piecewise_milp",
        "include_qubo_quadratized",
        "include_ipopt_pyomo",
        "include_stress_reserve",
    ]
    if role == "cpu":
        disabled = ["include_gpu_random_restart"]
    return f"""
import json
import subprocess
import sys
from pathlib import Path

role = {role!r}
repo = Path.home() / "QCI"
archive = Path.home() / "qci_phase3_workspace.tgz"
subprocess.run(["bash", "-lc", "rm -rf ~/QCI && cd ~ && tar -xzf ~/qci_phase3_workspace.tgz"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-input", "--progress-bar", "off", "--break-system-packages", "-r", str(repo / "requirements.txt")], check=True)
extra = ["pyomo", "highspy"]
if role == "gpu":
    extra.append("cupy-cuda12x[ctk]")
subprocess.run([sys.executable, "-m", "pip", "install", "--no-input", "--progress-bar", "off", "--break-system-packages", *extra], check=True)
sys.path.insert(0, str(repo / "src"))
import yaml
from cmpo.baseline_orchestrator import load_phase3_config

config_path = repo / {config!r}
config_data = load_phase3_config(config_path)
config_data["name"] = f"{{config_data.get('name', config_path.stem)}}_qbraid_{{role}}"
base_output = Path(config_data.get("output_dir", f"results/phase3/{{config_path.stem}}"))
config_data["output_dir"] = str(base_output.with_name(f"{{base_output.name}}_qbraid_{{role}}"))
baselines = config_data.setdefault("baselines", {{}})
for key in {disabled!r}:
    baselines[key] = False
if role == "gpu":
    baselines["include_gpu_random_restart"] = True
    baselines["gpu_restarts"] = max(int(baselines.get("gpu_restarts", 0) or 0), {gpu_restarts})
    baselines["gpu_local_steps"] = 0
if role == "cpu":
    baselines.setdefault("parallel_workers", 4)
generated = repo / "results/phase3" / f"qbraid_{{role}}_config.yaml"
generated.parent.mkdir(parents=True, exist_ok=True)
generated.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
subprocess.run([sys.executable, str(repo / "scripts/phase3_prepare_payloads.py"), "--config", str(generated)], cwd=repo, check=True)
subprocess.run([sys.executable, str(repo / "scripts/phase3_run_gpu_baselines.py"), "--config", str(generated), "--repeats", str({repeats})], cwd=repo, check=True)
subprocess.run([sys.executable, str(repo / "scripts/phase3_make_tables.py")], cwd=repo, check=True)
subprocess.run([sys.executable, str(repo / "scripts/phase3_make_figures.py")], cwd=repo, check=True)
subprocess.run(["bash", "-lc", f"cd {{repo}} && tar -czf ~/qci_phase3_{{role}}_results.tgz results/phase3"], check=True)
print(json.dumps({{"role": role, "config": str(generated), "archive": f"qci_phase3_{{role}}_results.tgz"}}, indent=2), flush=True)
"""


def _start_instance(client: ComputeClient, role: str, profile: str, timeout: int) -> InstanceRun:
    instance = client.provision_bma_instance(profile)
    instance = client.wait_for_bma_instance(instance.instance_id, target_status=BMAStatus.RUNNING, timeout=timeout)
    if not instance.url:
        raise RuntimeError(f"qBraid {role} instance reached running without a URL")
    return InstanceRun(role=role, profile=profile, instance_id=instance.instance_id, url=instance.url)


def _stop_instance(client: ComputeClient, run: InstanceRun, timeout: int = 300) -> None:
    try:
        client.stop_bma_instance(run.instance_id)
        client.wait_for_bma_instance(run.instance_id, target_status=BMAStatus.STOPPED, timeout=timeout)
    except Exception as exc:
        print(f"WARNING: failed to stop {run.role} instance {run.instance_id}: {exc}", file=sys.stderr)


def _run_remote(run: InstanceRun, archive: Path, config: str, repeats: int, gpu_restarts: int, output_dir: Path, timeout: int) -> None:
    remote = JupyterRemote(run.url)
    remote.wait_ready()
    remote.upload_file(archive, "qci_phase3_workspace.tgz")
    remote.execute(_remote_script(run.role, config, repeats, gpu_restarts), timeout=timeout, echo_prefix=f"[{run.role}] ")
    local_archive = output_dir / f"{run.role}_results.tgz"
    remote.download_file(f"qci_phase3_{run.role}_results.tgz", local_archive)
    extract_dir = output_dir / run.role
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(local_archive, "r:gz") as tar:
        tar.extractall(extract_dir)
    run.result_archive = local_archive


def main() -> None:
    args = build_parser().parse_args()
    plan = {
        "cpu_profile": args.cpu_profile,
        "gpu_profile": args.gpu_profile,
        "config": args.config,
        "cpu_repeats": args.cpu_repeats,
        "gpu_repeats": args.gpu_repeats,
        "gpu_restarts": args.gpu_restarts,
        "output_dir": args.output_dir,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return

    api_key = _check_environment()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = _make_workspace_archive()
    api_url = os.environ.get("QBRAID_API_URL", "https://api-v2.qbraid.com/api/v1")
    client = ComputeClient(session=QbraidSessionV1(api_key=api_key, base_url=api_url))
    runs: list[InstanceRun] = []
    try:
        for role, profile in (("gpu", args.gpu_profile), ("cpu", args.cpu_profile)):
            print(f"Starting qBraid {role} instance with profile {profile}", flush=True)
            runs.append(_start_instance(client, role, profile, args.start_timeout))
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(
                    _run_remote,
                    run,
                    archive,
                    args.config,
                    args.gpu_repeats if run.role == "gpu" else args.cpu_repeats,
                    args.gpu_restarts,
                    output_dir,
                    args.run_timeout,
                ): run
                for run in runs
            }
            for future in as_completed(futures):
                future.result()
        manifest = {
            **plan,
            "instances": [run.__dict__ for run in runs],
            "status": "completed",
        }
        (output_dir / "autorun_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        print(json.dumps(manifest, indent=2, default=str))
    finally:
        if args.keep_instances:
            print("Keeping qBraid instances because --keep-instances was passed.", flush=True)
        else:
            for run in runs:
                print(f"Stopping qBraid {run.role} instance {run.instance_id}", flush=True)
                _stop_instance(client, run)


if __name__ == "__main__":
    main()
