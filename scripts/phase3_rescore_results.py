#!/usr/bin/env python
"""Apply challenge-aligned derived scores to existing Phase 3 results."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.challenge_score import (  # noqa: E402
    build_phase3_method_summary,
    challenge_score_markdown,
    markdown_table,
    score_challenge_summary,
)


PHASE3_ROOT = Path("results") / "phase3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a derived Phase 3 challenge-aligned scoring layer from existing result CSVs. "
            "No QCi jobs or raw metric files are modified."
        )
    )
    parser.add_argument("--phase3-root", default=str(PHASE3_ROOT), help="Root directory containing Phase 3 outputs.")
    parser.add_argument(
        "--output-dir",
        default=str(PHASE3_ROOT / "final_tables"),
        help="Directory for challenge_score_summary.csv and challenge_score_summary.md.",
    )
    parser.add_argument(
        "--mode",
        choices=["weighted", "lexicographic", "both"],
        default="both",
        help="Challenge score mode to emit. 'both' writes one row per method and score mode.",
    )
    parser.add_argument(
        "--update-final-tables-md",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Append or replace the challenge_score_summary section in final_tables.md.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned inputs/outputs without writing files.")
    return parser


def _update_final_tables_md(path: Path, scored) -> None:
    section = "## challenge_score_summary\n\n" + markdown_table(
        scored[
            [
                column
                for column in [
                    "score_mode",
                    "dataset",
                    "method_name",
                    "challenge_score",
                    "challenge_rank",
                    "best_method_by_challenge_score",
                    "qci_minus_best_challenge_score",
                    "qci_outcome_by_challenge_score",
                ]
                if column in scored.columns
            ]
        ]
    )
    if path.exists():
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(r"\n## challenge_score_summary\n\n.*\\Z", re.DOTALL)
        if pattern.search(text):
            text = pattern.sub("\n" + section, text)
        else:
            text = text.rstrip() + "\n\n" + section
    else:
        text = "# Phase 3 Final Tables\n\n" + section
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    phase3_root = Path(args.phase3_root)
    output_dir = Path(args.output_dir)
    summary = build_phase3_method_summary(phase3_root)
    scored = score_challenge_summary(summary, mode=args.mode) if not summary.empty else summary

    outputs = {
        "challenge_score_summary_csv": str(output_dir / "challenge_score_summary.csv"),
        "challenge_score_summary_md": str(output_dir / "challenge_score_summary.md"),
        "final_tables_md": str(output_dir / "final_tables.md"),
    }
    payload = {
        "phase3_root": str(phase3_root),
        "output_dir": str(output_dir),
        "mode": args.mode,
        "method_summary_rows": int(len(summary)),
        "challenge_score_rows": int(len(scored)),
        "outputs": outputs,
        "dry_run": bool(args.dry_run),
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_dir / "challenge_score_summary.csv", index=False)
    (output_dir / "challenge_score_summary.md").write_text(challenge_score_markdown(scored), encoding="utf-8")
    if args.update_final_tables_md:
        _update_final_tables_md(output_dir / "final_tables.md", scored)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
