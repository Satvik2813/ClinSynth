"""Deterministic demo seed dataset generator.

Generates synthetic sample data with realistic clinical relationships.
All records are purely synthetic and do not represent real patients.
"""
import numpy as np
import pandas as pd

from src.utils.config import RANDOM_SEED, DATA_DIR, BOUNDS


def generate_demo_profiles(n_patients: int = 500, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    ages = rng.normal(55, 18, n_patients).clip(*BOUNDS["age"]).round().astype(int)
    genders = rng.choice(["M", "F"], n_patients, p=[0.48, 0.52])

    bmis = np.where(
        ages > 60,
        rng.normal(28.5, 5.0, n_patients),
        rng.normal(26.0, 4.5, n_patients),
    ).clip(*BOUNDS["bmi"]).round(1)

    diabetes_prob = np.where(ages > 60, 0.35, 0.15) + np.where(bmis > 30, 0.15, 0.0)
    diabetes_prob = diabetes_prob.clip(0, 0.85)
    diabetes = rng.binomial(1, diabetes_prob).astype(int)

    hypertension_prob = np.where(ages > 60, 0.45, 0.18) + np.where(bmis > 30, 0.10, 0.0)
    hypertension_prob = hypertension_prob.clip(0, 0.85)
    hypertension = rng.binomial(1, hypertension_prob).astype(int)

    patient_ids = [f"DEMO-{i+1:06d}" for i in range(n_patients)]

    return pd.DataFrame({
        "patient_id": patient_ids,
        "age": ages,
        "gender": genders,
        "bmi": bmis,
        "diabetes": diabetes,
        "hypertension": hypertension,
    })


def generate_demo_longitudinal(
    profiles: pd.DataFrame, days: int = 30, seed: int = RANDOM_SEED
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []

    for _, row in profiles.iterrows():
        pid = row["patient_id"]
        age = row["age"]
        has_diabetes = row["diabetes"]
        has_hypertension = row["hypertension"]
        bmi = row["bmi"]

        base_systolic = 115 + (age - 50) * 0.4 + has_hypertension * 18 + has_diabetes * 5
        base_diastolic = 72 + (age - 50) * 0.15 + has_hypertension * 10
        base_steps = max(2000, 8000 - (age - 40) * 60 - has_diabetes * 800 + rng.normal(0, 500))
        base_adherence = 0.7 + rng.normal(0, 0.1)
        base_pain = 2.0 + has_diabetes * 0.8 + (bmi - 25) * 0.05 + max(0, (age - 65) * 0.05)

        sys_trend = rng.normal(-0.05, 0.02) if has_hypertension else rng.normal(0, 0.01)
        adh_trend = rng.normal(0.002, 0.001)

        for day in range(1, days + 1):
            systolic = base_systolic + sys_trend * day + rng.normal(0, 5)
            diastolic = base_diastolic + rng.normal(0, 3.5)
            steps = base_steps + rng.normal(0, 800) + rng.normal(0, 200) * np.sin(day / 7 * np.pi)
            adherence = base_adherence + adh_trend * day + rng.normal(0, 0.05)
            pain = base_pain + rng.normal(0, 0.8)

            records.append({
                "patient_id": pid,
                "day": day,
                "systolic_bp": round(float(np.clip(systolic, *BOUNDS["systolic_bp"])), 1),
                "diastolic_bp": round(float(np.clip(diastolic, *BOUNDS["diastolic_bp"])), 1),
                "steps": int(np.clip(steps, *BOUNDS["steps"])),
                "medication_adherence": round(float(np.clip(adherence, *BOUNDS["medication_adherence"])), 3),
                "pain_score": round(float(np.clip(pain, *BOUNDS["pain_score"])), 1),
            })

    return pd.DataFrame(records)


def create_demo_dataset(n_patients: int = 500, days: int = 30, seed: int = RANDOM_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    profiles = generate_demo_profiles(n_patients, seed)
    longitudinal = generate_demo_longitudinal(profiles, days, seed)
    profiles.to_csv(DATA_DIR / "demo_profiles.csv", index=False)
    longitudinal.to_csv(DATA_DIR / "demo_longitudinal.csv", index=False)
    return profiles, longitudinal


if __name__ == "__main__":
    p, l = create_demo_dataset()
    print(f"Generated {len(p)} profiles, {len(l)} longitudinal records")
