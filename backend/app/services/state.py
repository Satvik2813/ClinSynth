"""In-memory application state for the ClinSynth backend.

Holds loaded data, trained models, generated cohorts, and computed results
across API calls within a single server process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AppState:
    profiles: pd.DataFrame | None = None
    longitudinal: pd.DataFrame | None = None
    profiles_processed: pd.DataFrame | None = None
    longitudinal_processed: pd.DataFrame | None = None

    synthesizer: Any = None
    train_info: dict | None = None

    synthetic_profiles: pd.DataFrame | None = None
    synthetic_longitudinal: pd.DataFrame | None = None
    cohort_stats: dict | None = None
    cohort_config: dict | None = None
    plausibility_stats: dict | None = None

    validation_profile_results: dict | None = None
    validation_long_results: dict | None = None
    fidelity_summary: dict | None = None
    per_column_quality: list | None = None
    subgroup_fidelity: list | None = None

    privacy_results: dict | None = None
    privacy_fidelity_results: list | None = None

    model_comparison_results: dict | None = None

    current_seed: int = 42
    privacy_mode: str = "balanced"
    trajectory_dist: dict = field(default_factory=lambda: {
        "stable": 0.50, "improving": 0.20, "worsening": 0.15, "fluctuating": 0.15,
    })
    current_experiment_id: str | None = None

    @property
    def data_loaded(self) -> bool:
        return self.profiles_processed is not None

    @property
    def model_trained(self) -> bool:
        return self.synthesizer is not None

    @property
    def cohort_generated(self) -> bool:
        return self.synthetic_profiles is not None

    def clear_cohort_results(self):
        self.validation_profile_results = None
        self.validation_long_results = None
        self.fidelity_summary = None
        self.per_column_quality = None
        self.subgroup_fidelity = None
        self.privacy_results = None
        self.privacy_fidelity_results = None


state = AppState()
