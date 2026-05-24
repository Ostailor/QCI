#!/usr/bin/env python
"""Run classical baseline methods for the default synthetic CMPO case."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cmpo.baselines import run_baselines  # noqa: E402
from cmpo.config import build_parser, config_from_args  # noqa: E402
from cmpo.data import generate_synthetic_dataset  # noqa: E402
from cmpo.scenarios import list_default_scenarios  # noqa: E402


def main() -> None:
    """Parse CLI arguments and print computed baseline records."""

    parser = build_parser("Run CMPO baseline methods.")
    config = config_from_args(parser.parse_args())
    records = run_baselines(
        config,
        generate_synthetic_dataset(config.dataset, output_dir=config.output.data_dir),
        list_default_scenarios(),
    )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
