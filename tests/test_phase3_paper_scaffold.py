from __future__ import annotations

import json
from pathlib import Path

from scripts.phase3_build_paper_assets import build_paper_assets
from scripts.phase3_build_paper_figures import build_paper_figures


EXPECTED_FILES = {
    "asset_sources.json",
    "encoding_efficiency.tex",
    "headline_results.tex",
    "paper_macros.tex",
}


def test_build_paper_assets_uses_retained_result_tables(tmp_path: Path) -> None:
    result = build_paper_assets(output_dir=tmp_path)

    assert result["dry_run"] is False
    assert set(result["files"]) == EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == EXPECTED_FILES

    headline = (tmp_path / "headline_results.tex").read_text(encoding="utf-8")
    assert "QCi" in headline
    assert r"\textbf{QCi Dirac-3}" in headline
    assert r"\textbf{95.0}" in headline
    assert "55.1" in headline
    assert "L4 local search" in headline
    assert "Exact MILP" not in headline
    assert "QUBO" not in headline

    macros = (tmp_path / "paper_macros.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\IrcQciJobs}{8}" in macros
    assert r"\newcommand{\IrcQciSamples}{660}" in macros
    assert r"\newcommand{\IrcProductionSamples}{600}" in macros
    assert r"\newcommand{\IrcExactGroundStateSamples}{575}" in macros
    assert r"\newcommand{\IrcExactGroundStatePercent}{95.8}" in macros
    assert r"\newcommand{\IrcPositiveWeightSamples}{500}" in macros
    assert r"\newcommand{\IrcPositiveWeightExactSamples}{475}" in macros
    assert r"\newcommand{\IrcPositiveWeightExactPercent}{95.0}" in macros
    assert r"\newcommand{\IrcBestLFourPositiveWeightExactPercent}{55.1}" in macros
    assert r"\newcommand{\IrcPositiveWeightExactAdvantagePoints}{39.9}" in macros
    assert r"\newcommand{\IrcNativeFeasibleSamples}{600}" in macros
    assert r"\newcommand{\ScQciJobs}{43}" in macros
    assert r"\newcommand{\ScQciSamples}{1290}" in macros
    assert r"\newcommand{\ScBenchmarkFamilies}{4}" in macros
    assert r"\newcommand{\ScPayloads}{43}" in macros
    assert r"\newcommand{\ScVariables}{103}" in macros
    assert r"\newcommand{\ScScenarios}{8}" in macros
    assert r"\newcommand{\ScMaximumDegree}{3}" in macros
    assert r"\newcommand{\IrcLogicalVariables}{33}" in macros
    assert r"\newcommand{\QuboTotalVariables}{52}" in macros
    assert r"\newcommand{\IrcCriticalLoadServedPercent}{97.26}" in macros
    assert r"\newcommand{\IrcExpectedCriticalInfrastructureHours}{1.125}" in macros
    assert r"\newcommand{\IrcTotalCriticalInfrastructureHours}{9.0}" in macros
    assert r"\newcommand{\IrcVariableReductionPercent}{36.5}" in macros
    assert r"\newcommand{\IrcCostReductionVsQuboPercent}{16.6}" in macros
    assert r"\newcommand{\IrcCriticalEnsReductionVsQuboPercent}{16.5}" in macros
    assert r"\newcommand{\IrcCriticalInfraReductionVsQuboPercent}{40.0}" in macros
    assert r"\newcommand{\QciTimeToGoodSecondsMinimum}{91}" in macros
    assert r"\newcommand{\QciTimeToGoodSecondsMaximum}{94}" in macros
    assert r"\newcommand{\IrcSurrogateTrainPortfolios}{1800}" in macros
    assert r"\newcommand{\IrcSurrogateValidationPortfolios}{600}" in macros
    assert r"\newcommand{\IrcSurrogateTestPortfolios}{600}" in macros
    assert r"\newcommand{\IrcCriticalEnsNrmsePercent}{3.15}" in macros
    assert r"\newcommand{\IrcMaximumUnservedNrmsePercent}{1.19}" in macros
    assert r"\newcommand{\IrcInfrastructureHoursNrmsePercent}{11.30}" in macros
    assert r"\newcommand{\IrcSurrogateParetoRecallPercent}{100}" in macros

    sources = json.loads((tmp_path / "asset_sources.json").read_text(encoding="utf-8"))
    assert sources["schema"] == "cmpo.phase3.paper_assets.v1"
    assert all(Path(row["path"]).is_file() for row in sources["sources"])
    assert all(len(row["sha256"]) == 64 for row in sources["sources"])


def test_build_paper_assets_dry_run_writes_nothing(tmp_path: Path) -> None:
    output = tmp_path / "generated"

    result = build_paper_assets(output_dir=output, dry_run=True)

    assert result["dry_run"] is True
    assert set(result["files"]) == EXPECTED_FILES
    assert not output.exists()


def test_build_paper_figures_uses_retained_result_tables(tmp_path: Path) -> None:
    result = build_paper_figures(output_dir=tmp_path)

    assert result["dry_run"] is False
    assert set(result["files"]) == {
        "figure_sources.json",
        "ground_state_and_encoding.pdf",
        "ground_state_and_encoding.png",
        "method_overview.pdf",
        "method_overview.png",
    }
    assert all((tmp_path / name).is_file() for name in result["files"])
    assert (tmp_path / "ground_state_and_encoding.png").stat().st_size > 100_000
    assert (tmp_path / "method_overview.png").stat().st_size > 50_000
    assert (tmp_path / "ground_state_and_encoding.pdf").stat().st_size > 5_000
    assert (tmp_path / "method_overview.pdf").stat().st_size > 5_000

    sources = json.loads((tmp_path / "figure_sources.json").read_text())
    assert sources["schema"] == "cmpo.phase3.paper_figures.v1"
    assert all(Path(row["path"]).is_file() for row in sources["sources"])
    assert all(len(row["sha256"]) == 64 for row in sources["sources"])


def test_build_paper_figures_dry_run_writes_nothing(tmp_path: Path) -> None:
    output = tmp_path / "figures"

    result = build_paper_figures(output_dir=output, dry_run=True)

    assert result["dry_run"] is True
    assert not output.exists()


def test_judge_facing_readme_omits_internal_cpu_fallback_policy() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "README.md").read_text(encoding="utf-8").lower()

    assert "cpu fallback" not in text
    assert "falling back to cpu" not in text


def test_judge_facing_readme_covers_submission_requirements() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "README.md").read_text(encoding="utf-8")

    assert "**Team:** Team Restorers" in text
    assert "**Project:** Native Cubic Optimization" in text
    assert "**Challenge track:** QCi Energy Infrastructure Challenge, Phase 3" in text
    assert "Launch_on_qBraid_white.png" in text
    assert "## Full Rebuild" in text
    assert "### Expected Stage Outputs" in text
    assert "## Known Limitations and Assumptions" in text
    assert "submission/TheRestorers_QCI_Phase3.zip" in text


def test_public_submission_contains_the_final_pdf_only() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    submission_dir = repo_root / "submission"
    final_pdf = submission_dir / "TheRestorers__Phase3_Version1.pdf"
    published_pdfs = sorted(path.name for path in submission_dir.glob("*.pdf"))

    assert final_pdf.read_bytes().startswith(b"%PDF")
    assert published_pdfs == ["TheRestorers__Phase3_Version1.pdf"]
