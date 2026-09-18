"""Centralized configuration for ClinSynth."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
REPORTS_DIR = ARTIFACTS_DIR / "reports"

RANDOM_SEED = 42

PROFILE_COLUMNS = ["patient_id", "age", "gender", "bmi", "diabetes", "hypertension"]
LONGITUDINAL_COLUMNS = [
    "patient_id", "day", "systolic_bp", "diastolic_bp",
    "steps", "medication_adherence", "pain_score",
]

BOUNDS = {
    "age": (0, 110),
    "bmi": (10.0, 60.0),
    "systolic_bp": (70, 220),
    "diastolic_bp": (40, 140),
    "steps": (0, 40000),
    "medication_adherence": (0.0, 1.0),
    "pain_score": (0, 10),
}

DEFAULT_COHORT = {
    "num_patients": 1000,
    "elderly_pct": 0.30,
    "diabetes_pct": 0.25,
    "hypertension_pct": 0.20,
    "timeline_days": 30,
}

SYNTHESIZER_TYPES = ["CTGANSynthesizer", "GaussianCopulaSynthesizer"]

DEMO_DATASET_PROFILES = "demo_profiles.csv"
DEMO_DATASET_LONGITUDINAL = "demo_longitudinal.csv"
