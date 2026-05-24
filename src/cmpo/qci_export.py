"""QCi-ready JSON export helpers for CMPO polynomial models.

These exports are offline Phase 2 artifacts. They do not require live QCi
credentials and do not submit jobs to QCi services.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from cmpo.polynomial import PolynomialModel


def try_import_eqc_models() -> ModuleType | None:
    """Attempt to import ``eqc_models`` without making it a hard dependency."""

    try:
        return importlib.import_module("eqc_models")
    except ImportError:
        return None


def _max_abs_coefficient(model: PolynomialModel) -> float:
    return max((abs(term.coefficient) for term in model.terms), default=0.0)


def _coefficient_scaling_factor(model: PolynomialModel) -> float:
    max_abs = _max_abs_coefficient(model)
    return 1.0 / max_abs if max_abs > 1.0 else 1.0


def _payload_name(metadata: dict[str, Any]) -> str:
    scenario = str(metadata.get("scenario", "scenario")).replace(" ", "_").replace("/", "_")
    patch = str(metadata.get("patch", "patch")).replace(" ", "_").replace("/", "_").replace("|", "-")
    return f"{scenario}_{patch}.json"


def model_statistics(model: PolynomialModel) -> dict[str, float | int]:
    """Compute model statistics useful for QCi readiness review."""

    continuous_count = sum(variable.encoding_type == "quasi_continuous" for variable in model.variables.values())
    integer_count = sum(variable.encoding_type == "integer" for variable in model.variables.values())
    return {
        "variable_count": model.variable_count(),
        "term_count": model.term_count(),
        "degree": model.degree(),
        "continuous_variable_count": continuous_count,
        "integer_variable_count": integer_count,
        "max_abs_coefficient": _max_abs_coefficient(model),
        "coefficient_scaling_factor": _coefficient_scaling_factor(model),
    }


def build_polynomial_model_payload(model: PolynomialModel, metadata: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-serializable CMPO payload for later Dirac-3 adaptation."""

    variable_payloads = [
        {
            "name": variable.name,
            "lower_bound": variable.lower_bound,
            "upper_bound": variable.upper_bound,
            "bounds": [variable.lower_bound, variable.upper_bound],
            "encoding_type": variable.encoding_type,
        }
        for variable in model.variables.values()
    ]
    term_payloads = [
        {
            "coefficient": term.coefficient,
            "powers": dict(term.powers),
            "degree": term.degree,
        }
        for term in model.terms
    ]
    statistics = model_statistics(model)
    return {
        "schema": "cmpo.qci_payload.v1",
        "target": "qci_dirac_3",
        "objective_sense": "minimize",
        "max_degree": model.degree(),
        "variables": variable_payloads,
        "polynomial_terms": term_payloads,
        "scenario_metadata": {
            "scenario": metadata.get("scenario"),
            "horizon": metadata.get("horizon"),
            "penalty_weights": metadata.get("penalty_weights", {}),
        },
        "patch_metadata": {
            "patch": metadata.get("patch"),
            "patch_ids": metadata.get("patch_ids", []),
        },
        "scaling_information": {
            "coefficient_scaling_factor": statistics["coefficient_scaling_factor"],
            "max_abs_coefficient": statistics["max_abs_coefficient"],
            "note": "Scaling is metadata only in Phase 2; Phase 3 adapters may rescale coefficients for QCi APIs.",
        },
        "model_statistics": statistics,
        "phase2_notice": "Pre-QCi artifact generated without live QCi credentials; no hardware quantum advantage is claimed.",
    }


def export_polynomial_model_payload(
    model: PolynomialModel,
    metadata: dict[str, Any],
    output_dir: Path | str = Path("results"),
) -> Path:
    """Write a clean QCi-ready JSON payload for one polynomial model."""

    model.validate_degree(3)
    payload_dir = Path(output_dir) / "qci_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    output_path = payload_dir / _payload_name(metadata)
    output_path.write_text(json.dumps(build_polynomial_model_payload(model, metadata), indent=2), encoding="utf-8")
    return output_path


def convert_to_eqc_models_format(model: PolynomialModel) -> dict[str, Any]:
    """Placeholder adapter for Phase 3 ``eqc_models`` integration.

    TODO(Phase 3): Replace this dictionary with native eqc-models objects once
    the target API version and credential flow are confirmed.

    TODO(Phase 3): Decide whether coefficient scaling should happen before
    adapter construction or through an eqc-models normalization utility.
    """

    return {
        "status": "todo_phase3_adapter",
        "model_name": model.name,
        "variable_count": model.variable_count(),
        "term_count": model.term_count(),
        "degree": model.degree(),
    }


def build_qci_payload(hamiltonian: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for existing scripts that already have payloads."""

    return {
        "target": "qci_dirac_3",
        "format": "cmpo.qci_payload.v1",
        "hamiltonian": hamiltonian,
        "status": "not_submitted",
        "phase2_notice": "Offline pre-QCi payload only.",
    }
