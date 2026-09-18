"""Cohort conditioning engine.

Applies demographic constraints to generated synthetic profiles
using stratified resampling with rejection sampling.
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
    seed: int = RANDOM_SEED,
    max_attempts: int = 20,
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    pool_size = max(num_patients * 5, 5000)

    from src.synthesis.synthesizer import generate_samples
    synth_source = raw_synthetic

    if len(synth_source) < pool_size:
        extra_needed = pool_size - len(synth_source)
        repeats = (extra_needed // len(synth_source)) + 1
        synth_source = pd.concat([synth_source] * (repeats + 1), ignore_index=True)

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

        current_diabetes = cohort["diabetes"].mean() if "diabetes" in cohort.columns else 0
        current_hypertension = cohort["hypertension"].mean() if "hypertension" in cohort.columns else 0

        if "diabetes" in cohort.columns:
            cohort = _adjust_binary_column(cohort, "diabetes", diabetes_pct, rng)
        if "hypertension" in cohort.columns:
            cohort = _adjust_binary_column(cohort, "hypertension", hypertension_pct, rng)

        actual_elderly = (cohort["age"] >= 60).mean()
        actual_diabetes = cohort["diabetes"].mean() if "diabetes" in cohort.columns else 0
        actual_hypertension = cohort["hypertension"].mean() if "hypertension" in cohort.columns else 0

        score = (
            abs(actual_elderly - elderly_pct) +
            abs(actual_diabetes - diabetes_pct) +
            abs(actual_hypertension - hypertension_pct)
        )

        if score < best_score:
            best_score = score
            best_cohort = cohort.copy()

        if score < 0.03:
            break

    cohort = best_cohort.head(num_patients).copy()
    cohort = validate_bounds(cohort)

    cohort["patient_id"] = [f"SYN-{i+1:06d}" for i in range(len(cohort))]
    cohort = cohort.reset_index(drop=True)

    actual_stats = {
        "total_patients": len(cohort),
        "actual_elderly_pct": round((cohort["age"] >= 60).mean(), 4),
        "actual_diabetes_pct": round(cohort["diabetes"].mean(), 4) if "diabetes" in cohort.columns else None,
        "actual_hypertension_pct": round(cohort["hypertension"].mean(), 4) if "hypertension" in cohort.columns else None,
        "requested_elderly_pct": elderly_pct,
        "requested_diabetes_pct": diabetes_pct,
        "requested_hypertension_pct": hypertension_pct,
    }

    return cohort, actual_stats


def _adjust_binary_column(
    df: pd.DataFrame, col: str, target_pct: float, rng: np.random.Generator
) -> pd.DataFrame:
    df = df.copy()
    current_pct = df[col].mean()
    n = len(df)
    target_count = int(round(n * target_pct))
    current_count = int(df[col].sum())

    if current_count < target_count:
        zeros_idx = df[df[col] == 0].index.tolist()
        flip_count = min(target_count - current_count, len(zeros_idx))
        if flip_count > 0:
            flip_idx = rng.choice(zeros_idx, size=flip_count, replace=False)
            df.loc[flip_idx, col] = 1
    elif current_count > target_count:
        ones_idx = df[df[col] == 1].index.tolist()
        flip_count = min(current_count - target_count, len(ones_idx))
        if flip_count > 0:
            flip_idx = rng.choice(ones_idx, size=flip_count, replace=False)
            df.loc[flip_idx, col] = 0

    return df
