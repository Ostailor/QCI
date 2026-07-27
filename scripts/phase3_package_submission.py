#!/usr/bin/env python
"""Package the canonical Phase 3 judge/paper artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "submission" / "phase3_final_artifact"
DEFAULT_ZIP_OUTPUT = ROOT / "submission" / "TheRestorers_QCI_Phase3.zip"
EXCLUDED_RUNTIME_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
ARCHIVE_SOURCE_ROOT = Path("Source_Code")
ARCHIVE_WRITEUP_ROOT = Path("Write-Up")
ARPAE_ROOT = Path(
    "data/upstream/arpae-go/extracted/Challenge_1_Original_Dataset_2_Scenarios/"
    "Original_Dataset_Offline_Edition_2/Network_01O-020"
)
CANONICAL_SCRIPT_PATHS = (
    "scripts/fetch_pglib_benchmarks.py",
    "scripts/phase3_build_arpae_sc_cmpo.py",
    "scripts/phase3_build_artifact_manifest.py",
    "scripts/phase3_build_ieee123_sc_cmpo.py",
    "scripts/phase3_build_irc_cmpo.py",
    "scripts/phase3_build_irc_cmpo_dataset.py",
    "scripts/phase3_build_irc_cmpo_payloads.py",
    "scripts/phase3_build_paper_assets.py",
    "scripts/phase3_build_paper_figures.py",
    "scripts/phase3_build_sc_cmpo_payloads.py",
    "scripts/phase3_check_arpae_go.py",
    "scripts/phase3_compare_system_level.py",
    "scripts/phase3_decode_qci.py",
    "scripts/phase3_evaluate_sc_cmpo.py",
    "scripts/phase3_fetch_public_benchmarks.py",
    "scripts/phase3_finalize_sc_cmpo.py",
    "scripts/phase3_fit_irc_cmpo_surrogate.py",
    "scripts/phase3_full_rebuild.py",
    "scripts/phase3_monitor_irc_cmpo_final_batch.py",
    "scripts/phase3_package_submission.py",
    "scripts/phase3_prepare_irc_cmpo_preflight.py",
    "scripts/phase3_reproduce.py",
    "scripts/phase3_run_irc_cmpo_gpu_final.py",
    "scripts/phase3_run_irc_cmpo_smoke.py",
    "scripts/phase3_run_matched_baselines.py",
    "scripts/phase3_run_overlap_consensus.py",
    "scripts/phase3_run_qci.py",
    "scripts/phase3_run_qci_integer.py",
    "scripts/phase3_run_sc_cmpo_baselines.py",
    "scripts/phase3_submit_irc_cmpo_final_batch.py",
    "scripts/phase3_validate_distribution_powerflow.py",
    "scripts/phase3_validate_irc_cmpo_offline.py",
    "scripts/phase3_validate_sc_cmpo.py",
    "scripts/qbraid_phase3_autorun.py",
    "scripts/qbraid_phase3_autorun.sh",
    "scripts/qbraid_run_phase3_gpu.sh",
)
CANONICAL_SRC_PATHS = (
    "src/cmpo/__init__.py",
    "src/cmpo/arpae_sc_cmpo_adapter.py",
    "src/cmpo/baseline_orchestrator.py",
    "src/cmpo/baselines.py",
    "src/cmpo/benchmarks.py",
    "src/cmpo/budget_encoding.py",
    "src/cmpo/challenge_score.py",
    "src/cmpo/config.py",
    "src/cmpo/data.py",
    "src/cmpo/full_system_dispatch.py",
    "src/cmpo/hamiltonian_builder.py",
    "src/cmpo/heldout_evaluation.py",
    "src/cmpo/ieee123_sc_cmpo_adapter.py",
    "src/cmpo/irc_cmpo_batch.py",
    "src/cmpo/irc_cmpo_constraints.py",
    "src/cmpo/irc_cmpo_decode.py",
    "src/cmpo/irc_cmpo_feasibility.py",
    "src/cmpo/irc_cmpo_lagrangian.py",
    "src/cmpo/irc_cmpo_master.py",
    "src/cmpo/irc_cmpo_recourse.py",
    "src/cmpo/irc_cmpo_scaling.py",
    "src/cmpo/irc_cmpo_surrogate.py",
    "src/cmpo/irc_cmpo_validation.py",
    "src/cmpo/matched_problem_baselines.py",
    "src/cmpo/microgrid_design.py",
    "src/cmpo/overlap_consensus.py",
    "src/cmpo/phase3_metrics.py",
    "src/cmpo/polynomial.py",
    "src/cmpo/public_benchmarks.py",
    "src/cmpo/qci_client_adapter.py",
    "src/cmpo/qci_export.py",
    "src/cmpo/qci_integer_adapter.py",
    "src/cmpo/qci_result_decode.py",
    "src/cmpo/repair.py",
    "src/cmpo/sc_cmpo_reporting.py",
    "src/cmpo/scenario_coupled_model.py",
    "src/cmpo/scenarios.py",
    "src/cmpo/system_level_projection.py",
    "src/cmpo/upgrade_budget.py",
    "src/cmpo/upgrade_planning.py",
)
CANONICAL_PAPER_PATHS = (
    "submission/TheRestorers__Phase3_Version1.pdf",
)


@dataclass(frozen=True)
class PackageGroup:
    name: str
    role: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class ZipMember:
    archive_path: str
    role: str
    source: Path | None = None
    content: bytes | None = None
    mode: int = 0o644

    def read_bytes(self) -> bytes:
        if self.content is not None:
            return self.content
        if self.source is None:
            raise ValueError(f"ZIP member has no source or content: {self.archive_path}")
        return self.source.read_bytes()


def _sc_raw_qci_paths() -> tuple[str, ...]:
    qci_root = ROOT / "results/phase3/sc_cmpo/qci"
    names = sorted(
        path.relative_to(ROOT).as_posix()
        for path in qci_root.iterdir()
        if path.is_dir()
    )
    return tuple(names)


def _package_groups(include_raw: bool) -> tuple[PackageGroup, ...]:
    groups = [
        PackageGroup(
            name="project",
            role="Judge quick start, Python package metadata, dependency pins, and tests.",
            paths=(
                "README.md",
                "pyproject.toml",
                "requirements.txt",
                ".gitattributes",
                ".gitignore",
                "tests",
            ),
        ),
        PackageGroup(
            name="docs",
            role="Public-data notes and result-retention documentation.",
            paths=(
                "data/README.md",
                "data/README_ARPAE_GO.md",
                "results/README.md",
                "results/phase3/README.md",
            ),
        ),
        PackageGroup(
            name="paper",
            role="Final compiled Phase 3 manuscript.",
            paths=CANONICAL_PAPER_PATHS,
        ),
        PackageGroup(
            name="public_data",
            role="Canonical retained public benchmark and cost inputs used by the final Phase 3 artifact.",
            paths=(
                "data/upstream/arpae-go/download_manifest.csv",
                f"{ARPAE_ROOT.as_posix()}/case.inl",
                f"{ARPAE_ROOT.as_posix()}/case.rop",
                f"{ARPAE_ROOT.as_posix()}/scenario_1/case.con",
                f"{ARPAE_ROOT.as_posix()}/scenario_1/case.raw",
                "data/upstream/ieee123/manifest.json",
                "data/upstream/ieee123/IEEELineCodes.DSS",
                "data/upstream/ieee123/opendss",
                "data/upstream/nrel-atb/ATBe_2024_v3_selected_costs.csv",
                "data/upstream/nrel-atb/manifest.json",
                "data/upstream/pglib-opf/manifest.csv",
                "data/upstream/pglib-opf/v23.07/pglib_opf_case14_ieee.m",
                "data/upstream/pglib-opf/v23.07/pglib_opf_case30_ieee.m",
            ),
        ),
        PackageGroup(
            name="configs",
            role="Pinned final IRC-CMPO and SC-CMPO configuration files.",
            paths=(
                "configs/phase3_irc_cmpo_ieee123.yaml",
                "configs/phase3_sc_cmpo_arpae.yaml",
                "configs/phase3_sc_cmpo_case14.yaml",
                "configs/phase3_sc_cmpo_case30.yaml",
                "configs/phase3_sc_cmpo_ieee123.yaml",
            ),
        ),
        PackageGroup(
            name="code",
            role="Canonical Phase 3 source and CLI entrypoints only.",
            paths=CANONICAL_SCRIPT_PATHS + CANONICAL_SRC_PATHS,
        ),
        PackageGroup(
            name="irc_cmpo_provenance",
            role="Final IRC-CMPO payload, surrogate, validation, and execution provenance.",
            paths=(
                "results/phase3/irc_cmpo/baselines/qbraid_gpu_recourse_run.json",
                "results/phase3/irc_cmpo/baselines/qbraid_gpu_run.json",
                "results/phase3/irc_cmpo/baselines/gpu",
                "results/phase3/irc_cmpo/coefficient_audit.csv",
                "results/phase3/irc_cmpo/coefficient_audit.md",
                "results/phase3/irc_cmpo/dataset/portfolio_labels.csv",
                "results/phase3/irc_cmpo/dataset/split_manifest.csv",
                "results/phase3/irc_cmpo/inputs/budget_master_manifest.csv",
                "results/phase3/irc_cmpo/inputs/decoded_portfolios.csv",
                "results/phase3/irc_cmpo/inputs/master_comparison.csv",
                "results/phase3/irc_cmpo/inputs/public_asset_catalog.csv",
                "results/phase3/irc_cmpo/payload_manifest.csv",
                "results/phase3/irc_cmpo/payloads",
                "results/phase3/irc_cmpo/preflight_report.md",
                "results/phase3/irc_cmpo/preflight_summary.json",
                "results/phase3/irc_cmpo/qci/allocation_snapshot.json",
                "results/phase3/irc_cmpo/qci/batch_manifest.json",
                "results/phase3/irc_cmpo/qci/job_status.csv",
                "results/phase3/irc_cmpo/qci/native_evaluation_summary.json",
                "results/phase3/irc_cmpo/smoke/payloads",
                "results/phase3/irc_cmpo/smoke/smoke_plan.json",
                "results/phase3/irc_cmpo/surrogate/calibration.csv",
                "results/phase3/irc_cmpo/surrogate/fit_manifest.json",
                "results/phase3/irc_cmpo/surrogate/fit_split_manifest.csv",
                "results/phase3/irc_cmpo/surrogate/metrics.csv",
                "results/phase3/irc_cmpo/surrogate/model.json",
                "results/phase3/irc_cmpo/unquantized_payloads",
                "results/phase3/irc_cmpo/validation/exact_candidates.csv",
                "results/phase3/irc_cmpo/validation/exact_validation.json",
                "results/phase3/irc_cmpo/validation/manifest.json",
                "results/phase3/irc_cmpo/validation/stochastic_samples.csv",
                "results/phase3/irc_cmpo/validation/stochastic_validation.json",
            ),
        ),
        PackageGroup(
            name="irc_cmpo_final",
            role="Judge-facing and paper-facing final IRC-CMPO tables, figures, and summary markdown.",
            paths=("results/phase3/irc_cmpo/final",),
        ),
        PackageGroup(
            name="sc_cmpo_provenance",
            role="Final SC-CMPO build metadata, payload provenance, and system-summary traces.",
            paths=(
                "results/phase3/sc_cmpo/build_summary.json",
                "results/phase3/sc_cmpo/distribution_validation.json",
                "results/phase3/sc_cmpo/distribution_validation.md",
                "results/phase3/sc_cmpo/model_stats.csv",
                "results/phase3/sc_cmpo/payload_manifest.csv",
                "results/phase3/sc_cmpo/provenance_manifest.csv",
                "results/phase3/sc_cmpo/public_benchmark_provenance.csv",
                "results/phase3/sc_cmpo/qci/job_status.csv",
                "results/phase3/sc_cmpo/qci/qci_run_manifest.json",
                "results/phase3/sc_cmpo/qci_payloads",
                "results/phase3/sc_cmpo/scenario_coupling_manifest.csv",
                "results/phase3/sc_cmpo/system_summary/README_COMPRESSED_ARTIFACTS.md",
                "results/phase3/sc_cmpo/system_summary/baseline_system_metrics.csv",
                "results/phase3/sc_cmpo/system_summary/compressed_artifact_manifest.csv",
                "results/phase3/sc_cmpo/system_summary/consensus_convergence.csv",
                "results/phase3/sc_cmpo/system_summary/consensus_manifest.json.gz",
                "results/phase3/sc_cmpo/system_summary/consensus_values.csv.gz",
                "results/phase3/sc_cmpo/system_summary/heldout_summary.csv",
                "results/phase3/sc_cmpo/system_summary/matched_baseline_run.json",
                "results/phase3/sc_cmpo/system_summary/qci_repeat_system_metrics.csv",
                "results/phase3/sc_cmpo/system_summary/qci_system_metrics.csv",
                "results/phase3/sc_cmpo/upgrade_options.csv",
                "results/phase3/sc_cmpo/validation_report.md",
            ),
        ),
        PackageGroup(
            name="artifact_inventory",
            role="SHA-256 inventory for the canonical judge and paper artifacts.",
            paths=("results/phase3/artifact_manifest.csv",),
        ),
        PackageGroup(
            name="sc_cmpo_final",
            role="Judge-facing and paper-facing final SC-CMPO tables and figures.",
            paths=("results/phase3/sc_cmpo/final",),
        ),
    ]
    if include_raw:
        groups.extend(
            (
                PackageGroup(
                    name="irc_cmpo_raw_qci",
                    role="Immutable IRC-CMPO QCi request, response, and validation snapshots.",
                    paths=(
                        "results/phase3/irc_cmpo/qci/requests",
                        "results/phase3/irc_cmpo/qci/responses",
                        "results/phase3/irc_cmpo/qci/validations",
                    ),
                ),
                PackageGroup(
                    name="sc_cmpo_raw_qci",
                    role="Immutable SC-CMPO per-payload QCi request and response snapshots.",
                    paths=_sc_raw_qci_paths(),
                ),
            )
        )
    return tuple(groups)


def _files_for_path(relative_path: str) -> list[Path]:
    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"missing canonical artifact: {relative_path}")
    if path.is_file():
        return [path]
    return sorted(
        child
        for child in path.rglob("*")
        if child.is_file()
        and child.suffix not in {".pyc", ".pyo"}
        and not any(part in EXCLUDED_RUNTIME_PARTS for part in child.relative_to(ROOT).parts)
    )


def _group_files(group: PackageGroup) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for relative_path in group.paths:
        for path in _files_for_path(relative_path):
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _manifest(output: Path, include_raw: bool, groups: Iterable[PackageGroup]) -> dict[str, object]:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "include_raw": include_raw,
        "output_dir": str(output),
        "groups": [],
    }
    total_files = 0
    for group in groups:
        files = _group_files(group)
        total_files += len(files)
        payload["groups"].append(
            {
                "name": group.name,
                "role": group.role,
                "file_count": len(files),
                "files": [path.relative_to(ROOT).as_posix() for path in files],
            }
        )
    payload["file_count"] = total_files
    return payload


def _copy_files(output: Path, manifest: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for group in manifest["groups"]:
        assert isinstance(group, dict)
        files = group["files"]
        assert isinstance(files, list)
        for relative_name in files:
            assert isinstance(relative_name, str)
            source = ROOT / relative_name
            target = output / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    manifest_path = output / "package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _archive_readme() -> bytes:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    zip_instructions = """## ZIP Quick Start

This archive is ready to run without source or path edits. The complete
repository-shaped artifact is under `Source_Code/`; the submitted manuscript is
also exposed separately under `Write-Up/`.

```bash
cd Source_Code
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,qbraid]"
python scripts/phase3_reproduce.py --verify-only
```

For a fresh hardware rebuild, copy `.env.example` to `.env` and add only the
judge-owned QCi and qBraid credentials. Then run the documented full rebuild
command. No code, configuration path, benchmark input, or model parameter needs
to be edited.

"""
    marker = "## Result Summary\n"
    if marker not in readme:
        raise ValueError("README.md is missing the Result Summary insertion point")
    readme = readme.replace(marker, zip_instructions + marker, 1)
    readme = readme.replace(
        "(submission/TheRestorers__Phase3_Version1.pdf)",
        "(Write-Up/TheRestorers__Phase3_Version1.pdf)",
    )
    readme = readme.replace("](results/", "](Source_Code/results/")
    return readme.encode("utf-8")


def _environment_example() -> bytes:
    return (
        "QCI_API_URL=https://api.qci-prod.com\n"
        "QCI_TOKEN=<your-qci-token>\n"
        "QBRAID_API_KEY=<your-qbraid-api-key>\n"
    ).encode("utf-8")


def _challenge_zip_members(include_raw: bool) -> list[ZipMember]:
    members: dict[str, ZipMember] = {}
    for group in _package_groups(include_raw=include_raw):
        for source in _group_files(group):
            relative = source.relative_to(ROOT)
            archive_path = (ARCHIVE_SOURCE_ROOT / relative).as_posix()
            mode = stat.S_IMODE(source.stat().st_mode)
            if relative.parts[:1] == ("scripts",) and source.suffix in {".py", ".sh"}:
                mode = 0o755
            members[archive_path] = ZipMember(
                archive_path=archive_path,
                role=group.role,
                source=source,
                mode=mode,
            )

    paper = ROOT / CANONICAL_PAPER_PATHS[0]
    writeup_path = (ARCHIVE_WRITEUP_ROOT / paper.name).as_posix()
    members[writeup_path] = ZipMember(
        archive_path=writeup_path,
        role="Final Phase 3 write-up: official cover, five-page body, and references.",
        source=paper,
    )
    members["README.md"] = ZipMember(
        archive_path="README.md",
        role="Judge-facing archive instructions and complete reproducibility guide.",
        content=_archive_readme(),
    )
    env_path = (ARCHIVE_SOURCE_ROOT / ".env.example").as_posix()
    members[env_path] = ZipMember(
        archive_path=env_path,
        role="Credential template containing placeholders only.",
        content=_environment_example(),
    )
    return sorted(members.values(), key=lambda member: member.archive_path)


def _challenge_zip_manifest(members: Iterable[ZipMember], *, include_raw: bool) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    total_size = 0
    for member in members:
        content = member.read_bytes()
        total_size += len(content)
        rows.append(
            {
                "path": member.archive_path,
                "size_bytes": len(content),
                "sha256": _sha256_bytes(content),
                "role": member.role,
            }
        )
    return {
        "schema": "cmpo.phase3.challenge_submission.v1",
        "team": "Team Restorers",
        "project_title": "Native Cubic Optimization for Resilient Microgrid Investment on QCi Dirac-3",
        "challenge_track": "QCi Energy Infrastructure Challenge, Phase 3",
        "include_raw_qci_evidence": include_raw,
        "write_up": "Write-Up/TheRestorers__Phase3_Version1.pdf",
        "source_root": "Source_Code",
        "file_count": len(rows),
        "uncompressed_size_bytes": total_size,
        "files": rows,
    }


def _zip_info(path: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _write_challenge_zip(
    output: Path,
    *,
    include_raw: bool,
    overwrite: bool,
) -> dict[str, object]:
    if output.exists() and not overwrite:
        raise FileExistsError(f"submission ZIP already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    members = _challenge_zip_members(include_raw=include_raw)
    package_manifest = _challenge_zip_manifest(members, include_raw=include_raw)
    manifest_content = (json.dumps(package_manifest, indent=2) + "\n").encode("utf-8")
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as archive:
            for member in members:
                archive.writestr(
                    _zip_info(member.archive_path, member.mode),
                    member.read_bytes(),
                )
            archive.writestr(
                _zip_info("PACKAGE_MANIFEST.json"),
                manifest_content,
            )
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()

    content = output.read_bytes()
    return {
        "output_zip": str(output),
        "file_count": len(members) + 1,
        "include_raw": include_raw,
        "size_bytes": len(content),
        "sha256": _sha256_bytes(content),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Create-only package directory for the final Phase 3 artifact.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the canonical package manifest without copying files.",
    )
    parser.add_argument(
        "--zip-output",
        type=Path,
        help=(
            "Build the judge-facing ZIP with README.md, Write-Up/, and Source_Code/ "
            f"(recommended: {DEFAULT_ZIP_OUTPUT.relative_to(ROOT)})."
        ),
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include immutable raw QCi request/response evidence in addition to final provenance and results.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing --zip-output archive; directory packages remain create-only.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.zip_output is not None:
        zip_output = args.zip_output if args.zip_output.is_absolute() else ROOT / args.zip_output
        members = _challenge_zip_members(include_raw=args.include_raw)
        if args.dry_run:
            manifest = _challenge_zip_manifest(members, include_raw=args.include_raw)
            print(
                json.dumps(
                    {
                        "output_zip": str(zip_output),
                        "dry_run": True,
                        **manifest,
                    },
                    indent=2,
                )
            )
            return 0
        result = _write_challenge_zip(
            zip_output,
            include_raw=args.include_raw,
            overwrite=args.overwrite,
        )
        print(json.dumps(result, indent=2))
        return 0

    output = args.output if args.output.is_absolute() else ROOT / args.output
    groups = _package_groups(include_raw=args.include_raw)
    manifest = _manifest(output=output, include_raw=args.include_raw, groups=groups)
    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0
    _copy_files(output=output, manifest=manifest)
    print(json.dumps({"output_dir": str(output), "file_count": manifest["file_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
