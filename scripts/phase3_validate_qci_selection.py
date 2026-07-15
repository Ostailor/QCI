#!/usr/bin/env python
"""Validate Phase 3 QCi selected-sample traceability artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.qci_sample_selection import SELECTION_REASONS  # noqa: E402


DEFAULT_DIR = Path("results") / "phase3" / "qci_selection"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate nonempty and internally consistent QCi sample selection outputs.")
    parser.add_argument("--selection-dir", default=str(DEFAULT_DIR), help="Directory containing QCi selection artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="Report validation inputs without failing on content.")
    return parser


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _extract_effect_counts(text: str) -> dict[str, float]:
    patterns = {
        "ens_improved": r"improved on (\d+)/(\d+) payloads, with aggregate critical ENS delta ([^ ]+) kWh",
        "max_improved": r"reduced on (\d+)/(\d+) payloads, with aggregate max-unserved delta ([^.\n]+(?:\.\d+)?)",
    }
    out: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            out[f"{key}_count"] = float(match.group(1))
            out[f"{key}_total"] = float(match.group(2))
            out[f"{key}_delta"] = float(match.group(3))
    return out


def validate(selection_dir: Path) -> dict[str, object]:
    selected_path = selection_dir / "qci_selected_samples.csv"
    summary_path = selection_dir / "qci_selection_summary.csv"
    effect_path = selection_dir / "qci_selection_effect.md"
    selected = _read_csv(selected_path)
    summary = _read_csv(summary_path)
    errors: list[str] = []
    if selected.empty:
        errors.append(f"{selected_path} has zero rows or is missing")
    if summary.empty:
        errors.append(f"{summary_path} has zero rows or is missing")
    if not effect_path.exists() or effect_path.stat().st_size == 0:
        errors.append(f"{effect_path} is missing or empty")

    if not selected.empty and not summary.empty:
        key_cols = ["selection_benchmark", "selection_dataset", "selection_payload_name"]
        summary_key_cols = ["benchmark", "dataset", "payload_name"]
        grouped = selected.groupby(key_cols)["selection_reason"].apply(lambda values: set(values.astype(str))).reset_index()
        summary_keys = {
            tuple(row[col] for col in summary_key_cols)
            for row in summary.to_dict("records")
        }
        for row in grouped.to_dict("records"):
            key = tuple(row[col] for col in key_cols)
            reasons = row["selection_reason"]
            if key in summary_keys and set(SELECTION_REASONS) != reasons:
                errors.append(f"payload {key} has selection reasons {sorted(reasons)} instead of {list(SELECTION_REASONS)}")
        selected_keys = {tuple(row[col] for col in key_cols) for row in grouped.to_dict("records")}
        missing = sorted(summary_keys - selected_keys)
        if missing:
            errors.append(f"{len(missing)} summary payloads have no selected rows; first={missing[0]}")

    if effect_path.exists() and not summary.empty:
        text = effect_path.read_text(encoding="utf-8")
        parsed = _extract_effect_counts(text)
        expected_total = float(len(summary))
        expected_ens_count = float(summary["challenge_improves_critical_ENS"].sum())
        expected_max_count = float(summary["challenge_reduces_max_customers_unserved"].sum())
        expected_ens_delta = float(pd.to_numeric(summary["critical_ENS_delta_challenge_minus_energy"], errors="coerce").sum())
        expected_max_delta = float(pd.to_numeric(summary["max_customers_unserved_delta_challenge_minus_energy"], errors="coerce").sum())
        tolerances = [
            ("ens_improved_total", parsed.get("ens_improved_total"), expected_total, 0.0),
            ("ens_improved_count", parsed.get("ens_improved_count"), expected_ens_count, 0.0),
            ("max_improved_total", parsed.get("max_improved_total"), expected_total, 0.0),
            ("max_improved_count", parsed.get("max_improved_count"), expected_max_count, 0.0),
            ("ens_improved_delta", parsed.get("ens_improved_delta"), expected_ens_delta, max(1e-3, abs(expected_ens_delta) * 1e-5)),
            ("max_improved_delta", parsed.get("max_improved_delta"), expected_max_delta, max(1e-6, abs(expected_max_delta) * 1e-5)),
        ]
        for name, actual, expected, tol in tolerances:
            if actual is None or abs(actual - expected) > tol:
                errors.append(f"effect markdown mismatch for {name}: actual={actual}, expected={expected}")

    tracked = False
    committed_nonempty = False
    try:
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(selected_path)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        tracked = result.returncode == 0
        if tracked:
            blob = subprocess.run(
                ["git", "show", f"HEAD:{selected_path}"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            committed_nonempty = blob.returncode == 0 and len(blob.stdout.strip()) > 0
    except Exception:
        tracked = False
        committed_nonempty = False
    if not tracked:
        errors.append(f"{selected_path} is not tracked by git")
    if not committed_nonempty:
        errors.append(f"{selected_path} is not present and nonempty in HEAD")

    return {
        "selected_samples_csv": str(selected_path),
        "selection_summary_csv": str(summary_path),
        "selection_effect_md": str(effect_path),
        "selected_rows": int(len(selected)),
        "summary_rows": int(len(summary)),
        "tracked_selected_samples_csv": tracked,
        "committed_nonempty_selected_samples_csv": committed_nonempty,
        "valid": not errors,
        "errors": errors,
    }


def main() -> None:
    args = build_parser().parse_args()
    result = validate(Path(args.selection_dir))
    print(json.dumps(result, indent=2))
    if not args.dry_run and not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
