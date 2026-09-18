"""Cohort conditioning engine.

Applies demographic constraints to generated synthetic profiles
using stratified quota construction with iterative proportional fitting.

Supports nested/conditional constraints such as:
- 40% age >= 60
- 30% diabetic
- among diabetic patients, 50% hypertensive
- among age >= 60 patients, 45% diabetic
"""
import numpy as np
import pandas as pd

from src.utils.config import BOUNDS, RANDOM_SEED
from src.preprocessing.pipeline import validate_bounds


def build_cohort(
    raw_synthetic: pd.DataFrame,
    num_patients: int = 1000,
    elderly_pct: float = 0.30,
    diabetes_pct: float = 0.25,
    hypertension_pct: float = 0.20,
    htn_among_diabetic_pct: float | None = None,
    diabetes_among_elderly_pct: float | None = None,
    seed: int = RANDOM_SEED,
    max_attempts: int = 20,
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    pool_size = max(num_patients * 5, 5000)

    synth_source = raw_synthetic
    if len(synth_source) < pool_size:
        repeats = (pool_size // len(synth_source)) + 1
        synth_source = pd.concat([synth_source] * repeats, ignore_index=True)

    best_cohort = None
    best_score = float("inf")

    for attempt in range(max_attempts):
        pool = synth_source.sample(n=pool_size, replace=True, random_state=seed + attempt).copy()

        n_elderly = int(num_patients * elderly_pct)
        n_young = num_patients - n_elderly

        elderly_pool = pool[pool["age"] >= 60]
        young_pool = pool[pool["age"] < 60]

        if len(elderly_pool) < n_elderly:
            elderly_pool = pd.concat([elderly_pool] * ((n_elderly // max(1, len(elderly_pool))) + 1))
        if len(young_pool) < n_young:
            young_pool = pd.concat([young_pool] * ((n_young // max(1, len(young_pool))) + 1))

        elderly_sample = elderly_pool.sample(n=n_elderly, replace=True, random_state=seed + attempt)
        young_sample = young_pool.sample(n=n_young, replace=True, random_state=seed + attempt)

        cohort = pd.concat([elderly_sample, young_sample], ignore_index=True)

        if "diabetes" in cohort.columns:
            cohort = _adjust_binary_column(cohort, "diabetes", diabetes_pct, rng)
        if "hypertension" in cohort.columns:
            cohort = _adjust_binary_column(cohort, "hypertension", hypertension_pct, rng)

        if htn_among_diabetic_pct is not None and "diabetes" in cohort.columns and "hypertension" in cohort.columns:
            cohort = _adjust_conditional(cohort, "hypertension", "diabetes", 1, htn_among_diabetic_pct, rng)
            cohort = _adjust_binary_column(cohort, "hypertension", hypertension_pct, rng, mask=(cohort["diabetes"] == 0))

        if diabetes_among_elderly_pct is not None and "diabetes" in cohort.columns:
            elderly_mask = cohort["age"] >= 60
            cohort = _adjust_conditional_mask(cohort, "diabetes", elderly_mask, diabetes_among_elderly_pct, rng)
            cohort = _adjust_binary_column(cohort, "diabetes", diabetes_pct, rng, mask=(cohort["age"] < 60))

        score = _compute_constraint_score(
            cohort, elderly_pct, diabetes_pct, hypertension_pct,
            htn_among_diabetic_pct, diabetes_among_elderly_pct,
        )

        if score < best_score:
            best_score = score
            best_cohort = cohort.copy()

        if score < 0.02:
            break

    cohort = best_cohort.head(num_patients).copy()
    cohort = validate_bounds(cohort)
    cohort["patient_id"] = [f"SYN-{i+1:06d}" for i in range(len(cohort))]
    cohort = cohort.reset_index(drop=True)

    actual_stats = _compute_actual_stats(
        cohort, elderly_pct, diabetes_pct, hypertension_pct,
        htn_among_diabetic_pct, diabetes_among_elderly_pct,
    )

    return cohort, actual_stats


def _compute_constraint_score(
    cohort, elderly_pct, diabetes_pct, hypertension_pct,
    htn_among_diabetic_pct, diabetes_among_elderly_pct,
):
    score = 0.0
    score += abs((cohort["age"] >= 60).mean() - elderly_pct)
    if "diabetes" in cohort.columns:
        score += abs(cohort["diabetes"].mean() - diabetes_pct)
    if "hypertension" in cohort.columns:
        score += abs(cohort["hypertension"].mean() - hypertension_pct)
    if htn_among_diabetic_pct is not None and "diabetes" in cohort.columns and "hypertension" in cohort.columns:
        diabetic = cohort[cohort["diabetes"] == 1]
        if len(diabetic) > 0:
            score += abs(diabetic["hypertension"].mean() - htn_among_diabetic_pct)
    if diabetes_among_elderly_pct is not None and "diabetes" in cohort.columns:
        elderly = cohort[cohort["age"] >= 60]
        if len(elderly) > 0:
            score += abs(elderly["diabetes"].mean() - diabetes_among_elderly_pct)
    return score


def _compute_actual_stats(
    cohort, elderly_pct, diabetes_pct, hypertension_pct,
    htn_among_diabetic_pct, diabetes_among_elderly_pct,
):
    actual_elderly = round((cohort["age"] >= 60).mean(), 4)
    actual_diabetes = round(cohort["diabetes"].mean(), 4) if "diabetes" in cohort.columns else None
    actual_hypertension = round(cohort["hypertension"].mean(), 4) if "hypertension" in cohort.columns else None

    actual_htn_among_dm = None
    if "diabetes" in cohort.columns and "hypertension" in cohort.columns:
        dm_patients = cohort[cohort["diabetes"] == 1]
        if len(dm_patients) > 0:
            actual_htn_among_dm = round(dm_patients["hypertension"].mean(), 4)

    actual_dm_among_elderly = None
    if "diabetes" in cohort.columns:
        elderly = cohort[cohort["age"] >= 60]
        if len(elderly) > 0:
            actual_dm_among_elderly = round(elderly["diabetes"].mean(), 4)

    constraints = [
        {"constraint": "Age >= 60", "requested": elderly_pct, "actual": actual_elderly,
         "error": round(abs(actual_elderly - elderly_pct), 4)},
        {"constraint": "Diabetes", "requested": diabetes_pct, "actual": actual_diabetes,
         "error": round(abs(actual_diabetes - diabetes_pct), 4) if actual_diabetes is not None else None},
        {"constraint": "Hypertension", "requested": hypertension_pct, "actual": actual_hypertension,
         "error": round(abs(actual_hypertension - hypertension_pct), 4) if actual_hypertension is not None else None},
    ]

    if htn_among_diabetic_pct is not None:
        constraints.append({
            "constraint": "HTN among Diabetic",
            "requested": htn_among_diabetic_pct,
            "actual": actual_htn_among_dm,
            "error": round(abs(actual_htn_among_dm - htn_among_diabetic_pct), 4) if actual_htn_among_dm is not None else None,
        })

    if diabetes_among_elderly_pct is not None:
        constraints.append({
            "constraint": "DM among Age >= 60",
            "requested": diabetes_among_elderly_pct,
            "actual": actual_dm_among_elderly,
            "error": round(abs(actual_dm_among_elderly - diabetes_among_elderly_pct), 4) if actual_dm_among_elderly is not None else None,
        })

    return {
        "total_patients": len(cohort),
        "actual_elderly_pct": actual_elderly,
        "actual_diabetes_pct": actual_diabetes,
        "actual_hypertension_pct": actual_hypertension,
        "actual_htn_among_diabetic_pct": actual_htn_among_dm,
        "actual_diabetes_among_elderly_pct": actual_dm_among_elderly,
        "requested_elderly_pct": elderly_pct,
        "requested_diabetes_pct": diabetes_pct,
        "requested_hypertension_pct": hypertension_pct,
        "requested_htn_among_diabetic_pct": htn_among_diabetic_pct,
        "requested_diabetes_among_elderly_pct": diabetes_among_elderly_pct,
        "constraints": constraints,
    }


def _adjust_binary_column(
    df: pd.DataFrame, col: str, target_pct: float, rng: np.random.Generator,
    mask: pd.Series | None = None,
) -> pd.DataFrame:
    df = df.copy()
    if mask is not None:
        subset = df[mask]
    else:
        subset = df

    n = len(subset)
    if n == 0:
        return df

    target_count = int(round(n * target_pct))
    current_count = int(subset[col].sum())

    if current_count < target_count:
        zeros_idx = subset[subset[col] == 0].index.tolist()
        flip_count = min(target_count - current_count, len(zeros_idx))
        if flip_count > 0:
            flip_idx = rng.choice(zeros_idx, size=flip_count, replace=False)
            df.loc[flip_idx, col] = 1
    elif current_count > target_count:
        ones_idx = subset[subset[col] == 1].index.tolist()
        flip_count = min(current_count - target_count, len(ones_idx))
        if flip_count > 0:
            flip_idx = rng.choice(ones_idx, size=flip_count, replace=False)
            df.loc[flip_idx, col] = 0

    return df


def _adjust_conditional(
    df: pd.DataFrame, target_col: str, condition_col: str, condition_val: int,
    target_pct: float, rng: np.random.Generator,
) -> pd.DataFrame:
    df = df.copy()
    subset_mask = df[condition_col] == condition_val
    subset = df[subset_mask]
    n = len(subset)
    if n == 0:
        return df

    target_count = int(round(n * target_pct))
    current_count = int(subset[target_col].sum())

    if current_count < target_count:
        zeros_idx = subset[subset[target_col] == 0].index.tolist()
        flip_count = min(target_count - current_count, len(zeros_idx))
        if flip_count > 0:
            flip_idx = rng.choice(zeros_idx, size=flip_count, replace=False)
            df.loc[flip_idx, target_col] = 1
    elif current_count > target_count:
        ones_idx = subset[subset[target_col] == 1].index.tolist()
        flip_count = min(current_count - target_count, len(ones_idx))
        if flip_count > 0:
            flip_idx = rng.choice(ones_idx, size=flip_count, replace=False)
            df.loc[flip_idx, target_col] = 0

    return df


def _adjust_conditional_mask(
    df: pd.DataFrame, target_col: str, mask: pd.Series,
    target_pct: float, rng: np.random.Generator,
) -> pd.DataFrame:
    df = df.copy()
    subset = df[mask]
    n = len(subset)
    if n == 0:
        return df

    target_count = int(round(n * target_pct))
    current_count = int(subset[target_col].sum())

    if current_count < target_count:
        zeros_idx = subset[subset[target_col] == 0].index.tolist()
        flip_count = min(target_count - current_count, len(zeros_idx))
        if flip_count > 0:
            flip_idx = rng.choice(zeros_idx, size=flip_count, replace=False)
            df.loc[flip_idx, target_col] = 1
    elif current_count > target_count:
        ones_idx = subset[subset[target_col] == 1].index.tolist()
        flip_count = min(current_count - target_count, len(ones_idx))
        if flip_count > 0:
            flip_idx = rng.choice(ones_idx, size=flip_count, replace=False)
            df.loc[flip_idx, target_col] = 0

    return df
