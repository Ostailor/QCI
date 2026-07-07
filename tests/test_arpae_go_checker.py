import subprocess
import sys
from pathlib import Path


def test_arpae_go_checker_writes_nonblocking_report_without_data(tmp_path: Path) -> None:
    report = tmp_path / "results" / "arpae_go_feasibility.md"
    instructions = tmp_path / "data" / "README_ARPAE_GO.md"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/phase3_check_arpae_go.py",
            "--data-dir",
            str(tmp_path / "missing_arpae_go"),
            "--report",
            str(report),
            "--instructions",
            str(instructions),
            "--no-download",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "local_file_count" in result.stdout
    assert report.exists()
    assert instructions.exists()
    body = report.read_text(encoding="utf-8")
    assert "Can be parsed: no" in body
    assert "not as an AC OPF or SCOPF reproduction" in body
    assert "https://data.openei.org/submissions/6153" in instructions.read_text(encoding="utf-8")


def test_arpae_go_checker_parses_local_go_case(tmp_path: Path) -> None:
    data_dir = tmp_path / "arpae_go"
    case_dir = data_dir / "extracted" / "tiny_case"
    case_dir.mkdir(parents=True)
    (case_dir / "case.raw").write_text(
        "\n".join(
            [
                "0, 100.0, 33, 0, 0, 60.0 / PSS/E-33",
                "1,'BUS1',138,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
                "0 / END OF BUS DATA, BEGIN LOAD DATA",
                "1,'L1',1,1,1,10.0,2.0,0,0,0,0,1,1,0",
                "0 / END OF LOAD DATA, BEGIN GENERATOR DATA",
                "1,'G1',5.0,0.0,10.0,-10.0,1.0,0,100.0,1,20.0,0.0",
                "0 / END OF GENERATOR DATA",
            ]
        ),
        encoding="utf-8",
    )
    (case_dir / "case.con").write_text("CONTINGENCY BRANCH_OUTAGE\nEND\n", encoding="utf-8")
    report = tmp_path / "report.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/phase3_check_arpae_go.py",
            "--data-dir",
            str(data_dir),
            "--report",
            str(report),
            "--instructions",
            str(tmp_path / "README_ARPAE_GO.md"),
            "--no-download",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    body = report.read_text(encoding="utf-8")
    assert "Can be parsed: yes" in body
    assert "case.raw" in body
    assert '"section_counts"' in body
    assert '"bus": 1' in body
    assert "contingency files -> outage scenario templates" in body
    assert "ARPA-E GO-derived microgrid stress adapter" in body
