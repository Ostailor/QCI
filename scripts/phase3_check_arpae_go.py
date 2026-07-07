#!/usr/bin/env python
"""Download and inspect ARPA-E GO data for Phase 3 bonus benchmarks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


OEDI_BASE_URL = "https://data.openei.org"
DEFAULT_DATA_DIR = Path("data/upstream/arpae-go")
DEFAULT_REPORT_PATH = Path("results/phase3/public_benchmarks/arpae_go_feasibility.md")
DEFAULT_INSTRUCTIONS_PATH = Path("data/README_ARPAE_GO.md")

RESOURCE_CATALOG: dict[str, dict[str, str]] = {
    "challenge1_original_dataset_2": {
        "challenge": "Challenge 1",
        "submission_id": "6153",
        "title": "Challenge 1 Original Dataset 2 Scenarios.zip",
        "url": f"{OEDI_BASE_URL}/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip",
        "expected_size": "9.96 MB",
        "doi": "10.25984/2437761",
    },
    "challenge1_original_dataset_1": {
        "challenge": "Challenge 1",
        "submission_id": "6153",
        "title": "Challenge 1 Original Dataset 1 Scenarios.zip",
        "url": f"{OEDI_BASE_URL}/files/6153/Challenge_1_Original_Dataset_1_Scenarios.zip",
        "expected_size": "14.01 MB",
        "doi": "10.25984/2437761",
    },
    "challenge2_sandbox_617": {
        "challenge": "Challenge 2",
        "submission_id": "6197",
        "title": "Challenge 2 Sandbox Data C2S6N00617 Scenarios.zip",
        "url": f"{OEDI_BASE_URL}/files/6197/Challenge_2_Sandbox_Data_C2S6N00617_Scenarios.zip",
        "expected_size": "see OEDI resource page",
        "doi": "10.25984/2448433",
    },
    "challenge3_sandbox0": {
        "challenge": "Challenge 3",
        "submission_id": "5997",
        "title": "Challenge 3 Sandbox 0 Synthetic Dataset Scenarios.zip",
        "url": f"{OEDI_BASE_URL}/files/5997/C3S0.1_20230804.zip",
        "expected_size": "see OEDI resource page",
        "doi": "10.25984/2426334",
    },
}

PARSEABLE_EXTENSIONS = {".raw", ".rop", ".con", ".inl", ".m", ".json", ".csv"}
ARCHIVE_EXTENSIONS = {".zip", ".gz", ".tgz", ".tar"}


@dataclass
class DownloadRecord:
    key: str
    title: str
    url: str
    local_path: Path
    sha256: str
    bytes_downloaded: int
    status: str
    message: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check and optionally download public ARPA-E Grid Optimization Challenge data "
            "for Phase 3 bonus benchmark feasibility."
        )
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing or receiving ARPA-E GO data.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Markdown feasibility report path.")
    parser.add_argument(
        "--instructions",
        default=str(DEFAULT_INSTRUCTIONS_PATH),
        help="README path for ARPA-E GO download/provenance instructions.",
    )
    parser.add_argument(
        "--resource-key",
        default="challenge1_original_dataset_2",
        help=f"Resource key to download if data is missing. Known keys: {', '.join(sorted(RESOURCE_CATALOG))}.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not download data when the local ARPA-E GO directory is empty.",
    )
    parser.add_argument("--no-extract", action="store_true", help="Do not extract downloaded archives.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing downloaded archives/extractions.")
    parser.add_argument("--download-only", action="store_true", help="Download/extract data and skip report parsing.")
    parser.add_argument("--list-resources", action="store_true", help="Print the built-in ARPA-E GO resource catalog and exit.")
    parser.add_argument(
        "--discover-submission",
        choices=["6153", "6197", "5997"],
        help="Fetch and print current downloadable resources from an OEDI GO submission page, then exit.",
    )
    parser.add_argument(
        "--max-download-mb",
        type=float,
        default=250.0,
        help="Maximum allowed download size before the script skips the resource cleanly.",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Network timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without downloading or writing files.")
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_content_length(url: str, timeout: float) -> int | None:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        length = response.headers.get("content-length")
    return int(length) if length and length.isdigit() else None


def _download_url(url: str, path: Path, timeout: float) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "cmpo-phase3-arpae-go-checker/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response, path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return path.stat().st_size


def _filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = urllib.parse.unquote(Path(parsed.path).name)
    return name or "arpae_go_download.bin"


def discover_oedi_resources(submission_id: str, timeout: float = 30.0) -> list[dict[str, str]]:
    """Return downloadable OEDI resources from a submission page."""

    url = f"{OEDI_BASE_URL}/submissions/{submission_id}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        text = response.read().decode("utf-8", "ignore")
    resources: list[dict[str, str]] = []
    for block in text.split('<div class="sub-resource"')[1:]:
        title_match = re.search(r'<div class="resource-name" title="([^"]+)"', block)
        href_match = re.search(r"<a class='downloadlink[^']*' href='([^']+)'", block)
        if not title_match or not href_match:
            continue
        href = html.unescape(href_match.group(1)).strip()
        if href.startswith("/"):
            href = f"{OEDI_BASE_URL}{href}"
        resources.append(
            {
                "title": html.unescape(title_match.group(1)).strip(),
                "url": href,
                "submission_id": submission_id,
            }
        )
    return resources


def write_instructions(path: Path, default_resource_key: str = "challenge1_original_dataset_2", dry_run: bool = False) -> None:
    default = RESOURCE_CATALOG[default_resource_key]
    body = f"""# ARPA-E GO Public Dataset Setup

This repository can use public ARPA-E Grid Optimization (GO) Challenge data as a bonus Phase 3 benchmark path.
The checker downloads from the Open Energy Data Initiative (OEDI) records rather than vendoring large archives.

Official dataset records:
- Challenge 1: https://data.openei.org/submissions/6153, DOI {RESOURCE_CATALOG["challenge1_original_dataset_2"]["doi"]}
- Challenge 2: https://data.openei.org/submissions/6197, DOI {RESOURCE_CATALOG["challenge2_sandbox_617"]["doi"]}
- Challenge 3: https://data.openei.org/submissions/5997, DOI {RESOURCE_CATALOG["challenge3_sandbox0"]["doi"]}

Default lightweight download:
- Resource key: `{default_resource_key}`
- Title: {default["title"]}
- URL: {default["url"]}
- Expected size: {default["expected_size"]}

Run:

```bash
python scripts/phase3_check_arpae_go.py
```

To choose a different public resource:

```bash
python scripts/phase3_check_arpae_go.py --list-resources
python scripts/phase3_check_arpae_go.py --discover-submission 5997
python scripts/phase3_check_arpae_go.py --resource-key challenge3_sandbox0 --max-download-mb 1000
```

Downloaded archives are stored in `data/upstream/arpae-go/archives/`, extracted cases in
`data/upstream/arpae-go/extracted/`, and SHA-256 provenance in `data/upstream/arpae-go/download_manifest.csv`.

For manual downloads, preserve the source archive name and record:
- source URL,
- challenge and dataset title,
- OEDI DOI or version/date,
- license or terms shown on the source page,
- SHA-256 checksum,
- local path,
- transformation notes.

The Phase 3 paper should describe any use of this path as an "ARPA-E GO-derived microgrid stress adapter",
not as a reproduction of the original AC OPF/SCOPF challenge.
"""
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_download_manifest(record: DownloadRecord, data_dir: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    manifest_path = data_dir / "download_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if manifest_path.exists():
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    rows = [row for row in rows if row.get("local_path") != str(record.local_path)]
    rows.append(
        {
            "resource_key": record.key,
            "title": record.title,
            "url": record.url,
            "local_path": str(record.local_path),
            "sha256": record.sha256,
            "bytes": record.bytes_downloaded,
            "status": record.status,
            "message": record.message,
        }
    )
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _load_download_manifest_record(data_dir: Path, resource_key: str) -> DownloadRecord | None:
    manifest_path = data_dir / "download_manifest.csv"
    if not manifest_path.exists():
        return None
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in reversed(rows):
        if row.get("resource_key") != resource_key:
            continue
        local_path = Path(row.get("local_path", ""))
        bytes_value = row.get("bytes", "0")
        try:
            bytes_downloaded = int(bytes_value)
        except ValueError:
            bytes_downloaded = 0
        return DownloadRecord(
            key=row.get("resource_key", resource_key),
            title=row.get("title", RESOURCE_CATALOG[resource_key]["title"]),
            url=row.get("url", RESOURCE_CATALOG[resource_key]["url"]),
            local_path=local_path,
            sha256=row.get("sha256", ""),
            bytes_downloaded=bytes_downloaded,
            status=f"manifest_{row.get('status', 'recorded')}",
            message=row.get("message", ""),
        )
    return None


def download_resource(
    resource_key: str,
    data_dir: Path,
    *,
    overwrite: bool,
    dry_run: bool,
    timeout: float,
    max_download_mb: float,
) -> DownloadRecord:
    if resource_key not in RESOURCE_CATALOG:
        known = ", ".join(sorted(RESOURCE_CATALOG))
        raise ValueError(f"unknown ARPA-E GO resource key: {resource_key}. Known keys: {known}")
    resource = RESOURCE_CATALOG[resource_key]
    url = resource["url"]
    local_path = data_dir / "archives" / _filename_from_url(url)
    if dry_run:
        return DownloadRecord(resource_key, resource["title"], url, local_path, "", 0, "planned")
    if local_path.exists() and not overwrite:
        record = DownloadRecord(
            resource_key,
            resource["title"],
            url,
            local_path,
            _sha256(local_path),
            local_path.stat().st_size,
            "already_exists",
        )
        _write_download_manifest(record, data_dir)
        return record
    try:
        content_length = _head_content_length(url, timeout)
        if content_length is not None and content_length > max_download_mb * 1024 * 1024:
            return DownloadRecord(
                resource_key,
                resource["title"],
                url,
                local_path,
                "",
                0,
                "skipped_size_limit",
                f"content length {content_length} exceeds {max_download_mb:.1f} MB limit",
            )
        bytes_downloaded = _download_url(url, local_path, timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return DownloadRecord(resource_key, resource["title"], url, local_path, "", 0, "failed", str(exc))
    record = DownloadRecord(
        resource_key,
        resource["title"],
        url,
        local_path,
        _sha256(local_path),
        bytes_downloaded,
        "downloaded",
    )
    _write_download_manifest(record, data_dir)
    return record


def _safe_target(base_dir: Path, member_name: str) -> Path:
    target = base_dir / member_name
    resolved_base = base_dir.resolve()
    resolved_target = target.resolve()
    if resolved_base != resolved_target and resolved_base not in resolved_target.parents:
        raise ValueError(f"unsafe archive member path: {member_name}")
    return target


def extract_archive(path: Path, data_dir: Path, *, overwrite: bool, dry_run: bool) -> Path | None:
    archive_name = path.name
    stem = archive_name
    for suffix in (".tar.gz", ".tar", ".tgz", ".zip", ".gz"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    output_dir = data_dir / "extracted" / stem
    if dry_run:
        return output_dir
    if output_dir.exists() and not overwrite:
        return output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    lower_name = path.name.lower()
    if lower_name.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target = _safe_target(output_dir, member.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
        return output_dir
    if lower_name.endswith((".tar.gz", ".tgz", ".tar")):
        mode = "r:gz" if lower_name.endswith((".tar.gz", ".tgz")) else "r:"
        with tarfile.open(path, mode) as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                target = _safe_target(output_dir, member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    continue
                with source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
        return output_dir
    return None


def _non_comment_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "%", "//")):
            continue
        lines.append(stripped)
    return lines


def parse_matpower(path: Path) -> dict[str, Any]:
    try:
        from cmpo.benchmarks import parse_pglib_matpower_case

        parsed = parse_pglib_matpower_case(path)
        return {
            "type": "matpower",
            "path": str(path),
            "can_parse": True,
            "counts": {key: len(value) for key, value in parsed.items()},
        }
    except Exception as exc:
        return {"type": "matpower", "path": str(path), "can_parse": False, "error": str(exc)}


RAW_SECTION_ORDER = [
    "bus",
    "load",
    "fixed_shunt",
    "generator",
    "non_transformer_branch",
    "transformer",
    "area",
    "two_terminal_dc",
    "vsc_dc",
    "transformer_impedance",
    "multi_terminal_dc",
    "multi_section_line",
    "zone",
    "interarea",
    "owner",
    "facts",
    "switched_shunt",
    "gne",
    "induction",
]


def _parse_psse_raw_section_counts(lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    section_index = 0
    current_count = 0
    for line in lines[3:]:
        upper = line.upper()
        if re.match(r"^0\s*(/.*)?$", line) and "END" in upper:
            if section_index < len(RAW_SECTION_ORDER):
                counts[RAW_SECTION_ORDER[section_index]] = current_count
            section_index += 1
            current_count = 0
            continue
        if section_index < len(RAW_SECTION_ORDER):
            current_count += 1
    return counts


def parse_go_text_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = _non_comment_lines(text)
    markers = [
        line
        for line in lines
        if "BEGIN" in line.upper() or "END" in line.upper() or line.upper().startswith("BEGIN ")
    ][:30]
    result: dict[str, Any] = {
        "type": path.suffix.lower().lstrip("."),
        "path": str(path),
        "can_parse": bool(lines),
        "records_or_lines": len(lines),
        "section_markers": markers,
    }
    if path.suffix.lower() == ".raw" and len(lines) > 3:
        result["section_counts"] = _parse_psse_raw_section_counts(lines)
    if path.suffix.lower() == ".con":
        result["contingency_count"] = sum(1 for line in lines if line.upper().startswith("CONTINGENCY "))
    return result


def parse_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"type": "json", "path": str(path), "can_parse": False, "error": str(exc)}
    if isinstance(data, dict):
        keys = sorted(str(key) for key in data.keys())[:50]
        count = len(data)
    elif isinstance(data, list):
        keys = []
        count = len(data)
    else:
        keys = []
        count = 1
    return {"type": "json", "path": str(path), "can_parse": True, "top_level_count": count, "top_level_keys": keys}


def parse_csv_file(path: Path) -> dict[str, Any]:
    try:
        with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            rows = sum(1 for _, _row in zip(range(10000), reader))
    except csv.Error as exc:
        return {"type": "csv", "path": str(path), "can_parse": False, "error": str(exc)}
    return {"type": "csv", "path": str(path), "can_parse": bool(header), "header": header[:50], "sampled_rows": rows}


def parse_archive_index(path: Path) -> dict[str, Any]:
    lower_name = path.name.lower()
    try:
        if lower_name.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                names = [info.filename for info in archive.infolist() if not info.is_dir()]
        elif lower_name.endswith((".tar.gz", ".tgz", ".tar")):
            mode = "r:gz" if lower_name.endswith((".tar.gz", ".tgz")) else "r:"
            with tarfile.open(path, mode) as archive:
                names = [member.name for member in archive.getmembers() if member.isfile()]
        else:
            names = []
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        return {"type": "archive", "path": str(path), "can_parse": False, "error": str(exc)}
    extension_counts: dict[str, int] = {}
    for name in names:
        suffix = Path(name).suffix.lower() or "<none>"
        extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
    parseable = [name for name in names if Path(name).suffix.lower() in PARSEABLE_EXTENSIONS]
    return {
        "type": "archive",
        "path": str(path),
        "can_parse": bool(names),
        "member_count": len(names),
        "parseable_member_count": len(parseable),
        "extension_counts": extension_counts,
        "sample_members": names[:20],
    }


def parse_sample_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".m":
        return parse_matpower(path)
    if suffix in {".raw", ".rop", ".con", ".inl"}:
        return parse_go_text_file(path)
    if suffix == ".json":
        return parse_json_file(path)
    if suffix == ".csv":
        return parse_csv_file(path)
    if suffix in ARCHIVE_EXTENSIONS or path.name.lower().endswith((".tar.gz", ".tgz")):
        return parse_archive_index(path)
    return {"type": suffix.lstrip(".") or "unknown", "path": str(path), "can_parse": False, "error": "unsupported file type"}


def find_local_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    files = [
        path
        for path in data_dir.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.parts)
        and (path.suffix.lower() in PARSEABLE_EXTENSIONS or path.suffix.lower() in ARCHIVE_EXTENSIONS or path.name.lower().endswith((".tar.gz", ".tgz")))
    ]
    return sorted(files, key=lambda item: (0 if item.suffix.lower() in PARSEABLE_EXTENSIONS else 1, len(item.parts), str(item)))


def choose_sample_file(files: list[Path]) -> Path | None:
    preferred_order = [".raw", ".m", ".json", ".csv", ".rop", ".con", ".inl", ".zip", ".gz", ".tgz", ".tar"]
    for suffix in preferred_order:
        for path in files:
            if path.suffix.lower() == suffix or path.name.lower().endswith(suffix):
                return path
    return files[0] if files else None


def _field_mapping() -> tuple[list[str], list[str]]:
    maps = [
        "network buses -> candidate microgrid/PCC nodes",
        "loads and demand snapshots -> base load profiles and stress multipliers",
        "generators and dispatch limits -> local generator capacity and operating limits",
        "generator cost data or ROP records -> generator operating cost approximations",
        "branches/transformers -> tie-line candidates and PCC availability stress inputs",
        "contingency files -> outage scenario templates",
        "renewable or scenario availability fields -> PV/resource stress factors when present",
    ]
    gaps = [
        "native AC voltage, reactive power, tap, phase-shifter, and shunt controls are outside the CMPO microgrid abstraction",
        "critical infrastructure labels are not supplied and must be synthesized or joined from another source",
        "customer counts, outage priority classes, PV, BESS, and islanding policy fields are not first-class GO fields",
        "full SCOPF feasibility semantics do not map directly to the Phase 3 repair feasibility metric",
        "multi-period market and unit-commitment details need reduction before CMPO payload export",
    ]
    return maps, gaps


def build_report(
    *,
    data_dir: Path,
    report_path: Path,
    resource_key: str,
    download_record: DownloadRecord | None,
    local_files: list[Path],
    sample_result: dict[str, Any] | None,
    dry_run: bool,
) -> str:
    resource = RESOURCE_CATALOG[resource_key]
    can_parse = bool(sample_result and sample_result.get("can_parse"))
    maps, gaps = _field_mapping()
    should_use = (
        "Yes, as an ARPA-E GO-derived microgrid stress adapter after synthetic microgrid overlays are generated."
        if can_parse
        else "Not yet for final experiments; keep it as a documented bonus path until a public archive is downloaded and parsed."
    )
    download_lines = []
    if download_record is None:
        download_lines.append("- Download: not attempted")
    else:
        download_lines.extend(
            [
                f"- Download status: {download_record.status}",
                f"- Download URL: {download_record.url}",
                f"- Local archive: {download_record.local_path}",
                f"- SHA-256: {download_record.sha256 or 'not available'}",
                f"- Bytes: {download_record.bytes_downloaded}",
            ]
        )
        if download_record.message:
            download_lines.append(f"- Download note: {download_record.message}")
    sample_json = json.dumps(sample_result or {}, indent=2, sort_keys=True)
    body = f"""# ARPA-E GO Feasibility Check

## Dataset Checked
- Source family: ARPA-E Grid Optimization (GO) Competition public datasets on OEDI
- Selected resource key: `{resource_key}`
- Selected challenge: {resource["challenge"]}
- Selected title: {resource["title"]}
- OEDI submission: https://data.openei.org/submissions/{resource["submission_id"]}
- DOI: {resource["doi"]}
- Local data directory: {data_dir}

## Download And Local Availability
{os.linesep.join(download_lines)}
- Local parseable/archive files found: {len(local_files)}

## Parse Result
- Can be parsed: {'yes' if can_parse else 'no'}
- Sample parsed: {(sample_result or {}).get('path', 'none')}

```json
{sample_json}
```

## Fields That Map To CMPO
{os.linesep.join(f"- {item}" for item in maps)}

## Fields That Do Not Map Cleanly
{os.linesep.join(f"- {item}" for item in gaps)}

## Recommendation
{should_use}

Use this benchmark path only as an ARPA-E GO-derived microgrid stress adapter, not as an AC OPF or SCOPF reproduction.
"""
    if not dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(body, encoding="utf-8")
    return body


def run_check(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    report_path = Path(args.report)
    instructions_path = Path(args.instructions)
    if args.resource_key not in RESOURCE_CATALOG:
        raise SystemExit(f"unknown resource key {args.resource_key!r}; run with --list-resources")
    write_instructions(instructions_path, args.resource_key, dry_run=args.dry_run)

    initial_files = find_local_files(data_dir)
    download_record: DownloadRecord | None = None
    extracted_dir: Path | None = None
    if not initial_files and not args.no_download:
        download_record = download_resource(
            args.resource_key,
            data_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            timeout=args.timeout,
            max_download_mb=args.max_download_mb,
        )
        if download_record.local_path and download_record.status in {"downloaded", "already_exists", "planned"} and not args.no_extract:
            extracted_dir = extract_archive(download_record.local_path, data_dir, overwrite=args.overwrite, dry_run=args.dry_run)
    if download_record is None:
        download_record = _load_download_manifest_record(data_dir, args.resource_key)

    local_files = find_local_files(data_dir)
    if not local_files and download_record is not None and download_record.local_path.exists():
        local_files = [download_record.local_path]
    sample_result = None
    if not args.download_only:
        sample_file = choose_sample_file(local_files)
        sample_result = parse_sample_file(sample_file) if sample_file is not None and not args.dry_run else None
        build_report(
            data_dir=data_dir,
            report_path=report_path,
            resource_key=args.resource_key,
            download_record=download_record,
            local_files=local_files,
            sample_result=sample_result,
            dry_run=args.dry_run,
        )
    return {
        "data_dir": str(data_dir),
        "report": str(report_path),
        "instructions": str(instructions_path),
        "resource_key": args.resource_key,
        "local_file_count": len(local_files),
        "download": None if download_record is None else download_record.__dict__ | {"local_path": str(download_record.local_path)},
        "extracted_dir": None if extracted_dir is None else str(extracted_dir),
        "sample": sample_result,
        "dry_run": bool(args.dry_run),
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.list_resources:
        print(json.dumps(RESOURCE_CATALOG, indent=2, sort_keys=True))
        return
    if args.discover_submission:
        resources = discover_oedi_resources(args.discover_submission, timeout=args.timeout)
        print(json.dumps(resources, indent=2, sort_keys=True))
        return
    result = run_check(args)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
