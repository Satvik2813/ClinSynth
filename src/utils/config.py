"""Centralized configuration for ClinSynth."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
EXPERIMENTS_DIR = ARTIFACTS_DIR / "experiments"

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
    "heart_rate": (30, 220),
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

TRAJECTORY_TYPES = ["stable", "improving", "worsening", "fluctuating"]
DEFAULT_TRAJECTORY_DIST = {
    "stable": 0.50,
    "improving": 0.20,
    "worsening": 0.15,
    "fluctuating": 0.15,
}

PRIVACY_MODES = {
    "low": {
        "label": "Low",
        "near_copy_threshold": 0.05,
        "noise_scale": 0.0,
        "rejection_threshold": 0.0,
        "description": "Minimal privacy filtering. Highest fidelity but lowest privacy protection.",
    },
    "balanced": {
        "label": "Balanced",
        "near_copy_threshold": 0.1,
        "noise_scale": 0.02,
        "rejection_threshold": 0.1,
        "description": "Moderate filtering. Good balance of fidelity and privacy.",
    },
    "high": {
        "label": "High",
        "near_copy_threshold": 0.3,
        "noise_scale": 0.05,
        "rejection_threshold": 0.3,
        "description": "Strict filtering. Lower fidelity but stronger privacy protection.",
    },
}

RESEARCH_PRESETS = {
    "general_population": {
        "name": "General Population",
        "description": "Broad demographic mix reflecting a general adult population. Simulation preset for research.",
        "elderly_pct": 0.25,
        "diabetes_pct": 0.15,
        "hypertension_pct": 0.20,
        "htn_among_diabetic_pct": 0.40,
        "diabetes_among_elderly_pct": 0.25,
        "trajectory_dist": {"stable": 0.55, "improving": 0.20, "worsening": 0.10, "fluctuating": 0.15},
    },
    "older_adult": {
        "name": "Older Adult Cohort",
        "description": "Predominantly older adults (age 60+). Simulation preset for geriatric research.",
        "elderly_pct": 0.70,
        "diabetes_pct": 0.25,
        "hypertension_pct": 0.45,
        "htn_among_diabetic_pct": 0.55,
        "diabetes_among_elderly_pct": 0.30,
        "trajectory_dist": {"stable": 0.40, "improving": 0.15, "worsening": 0.25, "fluctuating": 0.20},
    },
    "older_diabetic": {
        "name": "Older Diabetic Cohort",
        "description": "Older adults with high diabetes prevalence. Simulation preset for diabetes research.",
        "elderly_pct": 0.40,
        "diabetes_pct": 0.30,
        "hypertension_pct": 0.25,
        "htn_among_diabetic_pct": 0.50,
        "diabetes_among_elderly_pct": 0.45,
        "trajectory_dist": {"stable": 0.50, "improving": 0.20, "worsening": 0.15, "fluctuating": 0.15},
    },
    "hypertension_heavy": {
        "name": "Hypertension-Heavy Cohort",
        "description": "High hypertension prevalence for cardiovascular research. Simulation preset.",
        "elderly_pct": 0.35,
        "diabetes_pct": 0.20,
        "hypertension_pct": 0.55,
        "htn_among_diabetic_pct": 0.65,
        "diabetes_among_elderly_pct": 0.30,
        "trajectory_dist": {"stable": 0.35, "improving": 0.20, "worsening": 0.25, "fluctuating": 0.20},
    },
    "low_adherence": {
        "name": "Low Medication Adherence Cohort",
        "description": "Cohort with lower medication adherence patterns. Simulation preset for adherence research.",
        "elderly_pct": 0.30,
        "diabetes_pct": 0.25,
        "hypertension_pct": 0.30,
        "htn_among_diabetic_pct": 0.45,
        "diabetes_among_elderly_pct": 0.35,
        "trajectory_dist": {"stable": 0.30, "improving": 0.10, "worsening": 0.35, "fluctuating": 0.25},
    },
    "high_pain_low_activity": {
        "name": "High Pain / Low Activity Cohort",
        "description": "Higher pain scores and reduced activity. Simulation preset for pain/mobility research.",
        "elderly_pct": 0.45,
        "diabetes_pct": 0.30,
        "hypertension_pct": 0.30,
        "htn_among_diabetic_pct": 0.50,
        "diabetes_among_elderly_pct": 0.40,
        "trajectory_dist": {"stable": 0.25, "improving": 0.15, "worsening": 0.35, "fluctuating": 0.25},
    },
    "recovery_monitoring": {
        "name": "Recovery Monitoring Cohort",
        "description": "Cohort biased toward improving trajectories. Simulation preset for recovery/rehab research.",
        "elderly_pct": 0.30,
        "diabetes_pct": 0.20,
        "hypertension_pct": 0.25,
        "htn_among_diabetic_pct": 0.40,
        "diabetes_among_elderly_pct": 0.30,
        "trajectory_dist": {"stable": 0.25, "improving": 0.45, "worsening": 0.10, "fluctuating": 0.20},
    },
}
