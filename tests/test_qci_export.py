import json
import subprocess
import sys
from pathlib import Path

from cmpo.config import DatasetConfig
from cmpo.data import generate_synthetic_dataset
from cmpo.hamiltonian_builder import build_scenario_hamiltonian
from cmpo.qci_export import export_polynomial_model_payload, try_import_eqc_models


def test_payload_json_is_valid_and_terms_reference_known_variables(tmp_path: Path) -> None:
    grid_case = generate_synthetic_dataset(DatasetConfig(seed=42, n_microgrids=3, horizon_hours=4), output_dir=tmp_path / "data")
    model, metadata = build_scenario_hamiltonian(
        grid_case,
        grid_case.scenarios[0],
        ("MG1",),
        output_dir=tmp_path / "results",
        write_export=False,
    )
    payload_path = export_polynomial_model_payload(model, metadata, tmp_path / "results")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    variables = {item["name"] for item in payload["variables"]}
    assert payload["objective_sense"] == "minimize"
    assert payload["max_degree"] <= 3
    assert payload["model_statistics"]["degree"] <= 3
    assert payload["model_statistics"]["variable_count"] == len(payload["variables"])
    assert payload["model_statistics"]["term_count"] == len(payload["polynomial_terms"])
    for term in payload["polynomial_terms"]:
        assert set(term["powers"]).issubset(variables)


def test_try_import_eqc_models_is_optional() -> None:
    module = try_import_eqc_models()
    assert module is None or hasattr(module, "__name__")


def test_export_script_runs_from_cli(tmp_path: Path) -> None:
    script = Path("scripts/export_qci_payloads.py")
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--seed",
            "42",
            "--n-microgrids",
            "3",
            "--horizon-hours",
            "4",
            "--data-dir",
            str(tmp_path / "data"),
            "--results-dir",
            str(tmp_path / "results"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payloads = sorted((tmp_path / "results" / "qci_export" / "qci_payloads").glob("*.json"))
    assert "Wrote" in result.stdout
    assert len(payloads) >= 8
    assert (tmp_path / "results" / "qci_export" / "model_stats.csv").exists()
    assert not (tmp_path / "results" / "model_stats.csv").exists()
    assert not (tmp_path / "results" / "qci_payloads").exists()
