"""CMPO Phase 2 prototype package.

This package implements a reproducible pre-QCi microgrid optimization harness:
synthetic data generation, disruption scenarios, microgrid patch design,
degree-3 polynomial model construction, classical baselines, result metrics,
and offline QCi payload exports for later Dirac-3 adaptation.
"""

from cmpo.config import ExperimentConfig

__all__ = ["ExperimentConfig", "__version__"]

__version__ = "0.1.0"
