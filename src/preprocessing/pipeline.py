"""Data preprocessing and quality validation."""
import pandas as pd
import numpy as np

from src.utils.config import BOUNDS


def validate_bounds(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col, (lo, hi) in BOUNDS.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].clip(lo, hi)
    return df


def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    types = {}
    for col in df.columns:
        if col == "patient_id":
            types[col] = "id"
        elif pd.api.types.is_numeric_dtype(df[col]):
            if df[col].dropna().nunique() <= 2 and set(df[col].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                types[col] = "boolean"
            elif pd.api.types.is_integer_dtype(df[col]) and df[col].dropna().nunique() < 10:
                types[col] = "categorical"
            else:
                types[col] = "numerical"
        else:
            types[col] = "categorical"
    return types


def preprocess_profiles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "gender" in df.columns:
        df["gender"] = df["gender"].astype(str).str.strip().str.upper().str[0]
        df["gender"] = df["gender"].map(lambda x: x if x in ("M", "F") else "M")
    for col in ["diabetes", "hypertension"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(0, 1)
    if "age" in df.columns:
        df["age"] = df["age"].fillna(df["age"].median())
    if "bmi" in df.columns:
        df["bmi"] = df["bmi"].fillna(df["bmi"].median())
    df = validate_bounds(df)
    return df


def preprocess_longitudinal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    numeric_cols = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())
    df = validate_bounds(df)
    return df


def get_quality_report(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_total": int(df.isnull().sum().sum()),
        "missing_by_column": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "column_types": detect_column_types(df),
    }
