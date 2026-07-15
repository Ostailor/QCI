#!/usr/bin/env python
"""Submit CMPO Phase 3 payloads to QCi Dirac-3 through qci-client."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baseline_orchestrator import load_phase3_config, phase3_output_dir, prepare_phase3_payloads  # noqa: E402
from cmpo.qci_client_adapter import run_payload_repeats, write_job_status_csv  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CMPO polynomial payloads on QCi Dirac-3 using qci-client. Reads QCI_API_URL and QCI_TOKEN from .env by default."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a Phase 3 YAML config. Optional when --payload-dir and --output-dir are supplied.",
    )
    parser.add_argument(
        "--payload-dir",
        default=None,
        help="Directory of CMPO payload JSON files. Defaults to the prepared config payload directory.",
    )
    parser.add_argument(
        "--payload-list",
        default=None,
        help="Text file containing one payload JSON path per line. Blank lines and lines beginning with # are ignored.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for raw QCi request/response artifacts. Defaults under results/phase3/<config>/qci.",
    )
    parser.add_argument("--repeats", type=int, default=30, help="Number of QCi repeats per payload.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing per-repeat QCi result directories.")
    parser.add_argument("--dry-run", action="store_true", help="Print the QCi run plan without submitting jobs.")
    return parser


def _payload_dir(config: dict, payload_dir_arg: str | None) -> Path:
    if payload_dir_arg:
        return Path(payload_dir_arg)
    manifest = prepare_phase3_payloads(config, dry_run=False)
    return Path(manifest["payload_dir"])


def resolve_payload_paths(*, payload_dir: Path | None, payload_list: Path | None) -> list[Path]:
    """Resolve an exact, deterministic payload set from a directory or list file."""

    if payload_dir is not None and payload_list is not None:
        raise ValueError("Use only one of --payload-dir or --payload-list.")
    if payload_list is not None:
        if not payload_list.is_file():
            raise FileNotFoundError(f"Payload list not found: {payload_list}")
        payloads: list[Path] = []
        seen: set[Path] = set()
        for line_number, line in enumerate(payload_list.read_text(encoding="utf-8").splitlines(), start=1):
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            path = Path(raw)
            if not path.is_absolute() and not path.exists():
                path = payload_list.parent / path
            if path.suffix.lower() != ".json":
                raise ValueError(f"Payload list line {line_number} is not JSON: {raw}")
            if not path.is_file():
                raise FileNotFoundError(f"Payload list line {line_number} not found: {path}")
            canonical = path.resolve()
            if canonical in seen:
                raise ValueError(f"Duplicate payload in {payload_list}: {path}")
            seen.add(canonical)
            payloads.append(path)
        if not payloads:
            raise ValueError(f"Payload list contains no JSON payloads: {payload_list}")
        return payloads
    if payload_dir is None:
        return []
    if not payload_dir.is_dir():
        raise FileNotFoundError(f"Payload directory not found: {payload_dir}")
    return sorted(payload_dir.glob("*.json"))


def main() -> None:
    args = build_parser().parse_args()
    if args.config:
        config = load_phase3_config(args.config)
    elif (args.payload_dir or args.payload_list) and args.output_dir:
        config = {
            "name": Path(args.output_dir).parent.name,
            "qci": {
                "relaxation_schedule": 1,
                "sum_constraint": None,
                "job_tags": ["cmpo", "phase3", "dirac3", "qci_fit"],
            },
        }
    else:
        raise SystemExit("--config is required unless --output-dir and either --payload-dir or --payload-list are supplied.")
    if args.payload_dir and args.payload_list:
        raise SystemExit("Use only one of --payload-dir or --payload-list.")
    config["overwrite"] = bool(args.overwrite)
    payload_dir = Path(args.payload_dir) if args.payload_dir else (None if args.payload_list else phase3_output_dir(config) / "qci_payloads")
    payload_list = Path(args.payload_list) if args.payload_list else None
    output_dir = Path(args.output_dir) if args.output_dir else phase3_output_dir(config) / "qci"
    plan = {
        "config": config["name"],
        "payload_dir": None if payload_dir is None else str(payload_dir),
        "payload_list": None if payload_list is None else str(payload_list),
        "output_dir": str(output_dir),
        "repeats": args.repeats,
        "overwrite": args.overwrite,
    }
    if not args.payload_dir and payload_list is None and payload_dir is not None and not payload_dir.exists() and not args.dry_run:
        payload_dir = _payload_dir(config, None)
        plan["payload_dir"] = str(payload_dir)
    try:
        payloads = resolve_payload_paths(payload_dir=payload_dir, payload_list=payload_list)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.dry_run:
        print(
            json.dumps(
                plan | {"payload_count": len(payloads), "payloads": [str(path) for path in payloads], "dry_run": True},
                indent=2,
            )
        )
        return
    if not payloads:
        raise SystemExit(f"No payload JSON files found in {payload_dir or payload_list}")

    records = []
    payload_workers = max(1, int(os.environ.get("QCI_PAYLOAD_WORKERS", "1")))
    if payload_workers > 1 and len(payloads) > 1:
        with ThreadPoolExecutor(max_workers=payload_workers) as executor:
            futures = [
                executor.submit(run_payload_repeats, payload_path, args.repeats, output_dir, config)
                for payload_path in payloads
            ]
            for future in as_completed(futures):
                records.extend(future.result())
    else:
        for payload_path in payloads:
            records.extend(run_payload_repeats(payload_path, args.repeats, output_dir, config))
    status_path = write_job_status_csv(records, output_dir / "job_status.csv")
    manifest_path = output_dir / "qci_run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(plan | {"payload_count": len(payloads), "status_csv": str(status_path)}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"status_csv": str(status_path), "manifest": str(manifest_path), "rows": len(records)}, indent=2))


if __name__ == "__main__":
    main()
