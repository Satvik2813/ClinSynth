"""Dataset loading and schema mapping."""
import pandas as pd
from pathlib import Path

from src.utils.config import DATA_DIR, PROFILE_COLUMNS, LONGITUDINAL_COLUMNS
from src.data.demo_generator import create_demo_dataset


def load_demo_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    profiles_path = DATA_DIR / "demo_profiles.csv"
    longitudinal_path = DATA_DIR / "demo_longitudinal.csv"

    if profiles_path.exists() and longitudinal_path.exists():
        profiles = pd.read_csv(profiles_path)
        longitudinal = pd.read_csv(longitudinal_path)
    else:
        profiles, longitudinal = create_demo_dataset()

    return profiles, longitudinal


def load_uploaded_csv(file_content, filename: str = "uploaded.csv") -> pd.DataFrame:
    df = pd.read_csv(file_content)
    return df


def detect_dataset_type(df: pd.DataFrame) -> str:
    cols_lower = [c.lower() for c in df.columns]
    profile_signals = {"age", "gender", "bmi", "diabetes", "hypertension"}
    long_signals = {"day", "systolic_bp", "diastolic_bp", "steps"}

    profile_match = len(profile_signals & set(cols_lower))
    long_match = len(long_signals & set(cols_lower))

    if long_match >= 3:
        return "longitudinal"
    if profile_match >= 3:
        return "profile"
    return "unknown"


def map_schema(df: pd.DataFrame, dataset_type: str) -> pd.DataFrame:
    col_map = {}
    for col in df.columns:
        lower = col.lower().strip().replace(" ", "_")
        col_map[col] = lower
    df = df.rename(columns=col_map)

    if dataset_type == "profile":
        for col in PROFILE_COLUMNS:
            if col not in df.columns and col != "patient_id":
                df[col] = None
    elif dataset_type == "longitudinal":
        for col in LONGITUDINAL_COLUMNS:
            if col not in df.columns and col != "patient_id":
                df[col] = None

    return df


def get_data_summary(profiles: pd.DataFrame, longitudinal: pd.DataFrame) -> dict:
    return {
        "n_patients": len(profiles),
        "n_longitudinal_records": len(longitudinal),
        "profile_columns": list(profiles.columns),
        "longitudinal_columns": list(longitudinal.columns),
        "profile_missing": profiles.isnull().sum().to_dict(),
        "longitudinal_missing": longitudinal.isnull().sum().to_dict(),
        "profile_dtypes": profiles.dtypes.astype(str).to_dict(),
        "longitudinal_dtypes": longitudinal.dtypes.astype(str).to_dict(),
    }
