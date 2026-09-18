"""Clinical plausibility guardrails.

Configurable bounds and consistency checks for synthetic data.
These are plausibility checks, not clinical validation.
"""
import numpy as np
import pandas as pd

from src.utils.config import BOUNDS


def check_plausibility(
    profiles: pd.DataFrame,
    longitudinal: pd.DataFrame | None = None,
) -> dict:
    stats = {"total_checked": 0, "repairs": {}, "violations_found": 0}

    if profiles is not None:
        stats["total_checked"] += len(profiles)
        for col, (lo, hi) in BOUNDS.items():
            if col in profiles.columns and pd.api.types.is_numeric_dtype(profiles[col]):
                violations = (~profiles[col].between(lo, hi)).sum()
                if violations > 0:
                    stats["repairs"][f"profile_{col}_bounds"] = int(violations)
                    stats["violations_found"] += int(violations)

        if "diabetes" in profiles.columns:
            bad = (~profiles["diabetes"].isin([0, 1])).sum()
            if bad > 0:
                stats["repairs"]["profile_diabetes_binary"] = int(bad)
                stats["violations_found"] += int(bad)

        if "hypertension" in profiles.columns:
            bad = (~profiles["hypertension"].isin([0, 1])).sum()
            if bad > 0:
                stats["repairs"]["profile_hypertension_binary"] = int(bad)
                stats["violations_found"] += int(bad)

    if longitudinal is not None and len(longitudinal) > 0:
        stats["total_checked"] += len(longitudinal)

        if "systolic_bp" in longitudinal.columns and "diastolic_bp" in longitudinal.columns:
            bp_violation = (longitudinal["diastolic_bp"] >= longitudinal["systolic_bp"]).sum()
            if bp_violation > 0:
                stats["repairs"]["systolic_gt_diastolic"] = int(bp_violation)
                stats["violations_found"] += int(bp_violation)

        for col, (lo, hi) in BOUNDS.items():
            if col in longitudinal.columns and pd.api.types.is_numeric_dtype(longitudinal[col]):
                violations = (~longitudinal[col].between(lo, hi)).sum()
                if violations > 0:
                    stats["repairs"][f"longitudinal_{col}_bounds"] = int(violations)
                    stats["violations_found"] += int(violations)

    stats["pass"] = stats["violations_found"] == 0
    return stats


def repair_profiles(profiles: pd.DataFrame) -> pd.DataFrame:
    df = profiles.copy()
    for col, (lo, hi) in BOUNDS.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].clip(lo, hi)
    for col in ["diabetes", "hypertension"]:
        if col in df.columns:
            df[col] = df[col].clip(0, 1).round().astype(int)
    return df


def repair_longitudinal(longitudinal: pd.DataFrame) -> pd.DataFrame:
    df = longitudinal.copy()

    for col, (lo, hi) in BOUNDS.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].clip(lo, hi)

    if "systolic_bp" in df.columns and "diastolic_bp" in df.columns:
        mask = df["diastolic_bp"] >= df["systolic_bp"]
        if mask.any():
            rng = np.random.default_rng(42)
            gap = rng.uniform(5, 15, size=mask.sum())
            df.loc[mask, "diastolic_bp"] = (df.loc[mask, "systolic_bp"] - gap).clip(*BOUNDS["diastolic_bp"]).round(1)

    return df
