from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset


def test_deterministic_seed_produces_identical_data(tmp_path: Path) -> None:
    config = DatasetConfig(seed=7, n_microgrids=4, horizon_hours=6)

    first = generate_synthetic_dataset(config, output_dir=tmp_path / "first")
    second = generate_synthetic_dataset(config, output_dir=tmp_path / "second")

    assert first.to_dict() == second.to_dict()
