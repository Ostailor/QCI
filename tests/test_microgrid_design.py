from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.microgrid_design import (
    choose_min_cost_upgrades,
    estimate_islanding_feasibility,
    generate_candidate_patches,
    save_design_outputs,
)


def test_design_covers_every_microgrid_and_has_nonnegative_cost(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    patches = generate_candidate_patches(grid_case, max_patch_size=3)
    design = choose_min_cost_upgrades(grid_case, patches)

    covered = {microgrid_id for patch in design["selected_patches"] for microgrid_id in patch}

    assert covered == {microgrid.name for microgrid in grid_case.microgrids}
    assert design["total_upgrade_cost"] >= 0.0
    assert design["metrics"]["customers_covered_fraction"] == 1.0
    assert design["metrics"]["selected_patch_count"] >= 1


def test_upgrade_plan_improves_feasibility(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    patches = generate_candidate_patches(grid_case, max_patch_size=3)
    selected_patch = patches[0]
    before = estimate_islanding_feasibility(grid_case, selected_patch)
    design = choose_min_cost_upgrades(grid_case, [selected_patch])
    after = design["feasibility_summary"][tuple(selected_patch)]["after"]["coverage_fraction"]

    assert after >= before["coverage_fraction"]


def test_save_design_outputs_writes_required_files(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42), output_dir=tmp_path / "data")
    design = choose_min_cost_upgrades(grid_case, generate_candidate_patches(grid_case))
    save_design_outputs(design, tmp_path / "results")

    assert (tmp_path / "results" / "microgrid_design.csv").exists()
    assert (tmp_path / "results" / "upgrade_plan.csv").exists()
    assert (tmp_path / "results" / "design_summary.json").exists()
