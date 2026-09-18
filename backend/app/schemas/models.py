"""Pydantic request/response models for the ClinSynth API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    project: str = "ClinSynth"


class DataSummary(BaseModel):
    n_patients: int
    n_longitudinal_records: int
    profile_columns: list[str]
    longitudinal_columns: list[str]
    profile_missing: dict[str, int]
    longitudinal_missing: dict[str, int]
    profile_dtypes: dict[str, str]
    longitudinal_dtypes: dict[str, str]
    column_types: dict[str, str] | None = None
    profile_stats: dict | None = None


class TrainRequest(BaseModel):
    synth_type: str = "GaussianCopulaSynthesizer"
    mode: str = "Demo (fast)"
    epochs: int = 50
    batch_size: int = 500


class TrainStatus(BaseModel):
    trained: bool
    synth_type: str | None = None
    training_rows: int | None = None
    epochs: int | None = None
    duration_seconds: float | None = None


class CohortRequest(BaseModel):
    num_patients: int = 1000
    timeline_days: int = 30
    elderly_pct: float = 0.30
    diabetes_pct: float = 0.25
    hypertension_pct: float = 0.20
    htn_among_diabetic_pct: float | None = 0.40
    diabetes_among_elderly_pct: float | None = 0.30
    privacy_mode: str = "balanced"
    seed: int = 42
    trajectory_dist: dict[str, float] = Field(
        default_factory=lambda: {"stable": 0.50, "improving": 0.20, "worsening": 0.15, "fluctuating": 0.15}
    )
    preset: str | None = None


class CohortSummary(BaseModel):
    total_patients: int
    timeline_days: int
    longitudinal_records: int
    constraints: list[dict]
    trajectory_distribution: dict[str, int] | None = None
    plausibility_stats: dict | None = None
    cohort_config: dict | None = None


class ModelCompareRequest(BaseModel):
    epochs: int = 50
    n_eval_samples: int = 500


class ExperimentSaveRequest(BaseModel):
    pass


class ErrorResponse(BaseModel):
    detail: str
    error_type: str = "error"
