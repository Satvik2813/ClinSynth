"""Temporal / longitudinal patient journey generator.

Generates realistic daily health measurements for synthetic patients
based on statistical patterns learned from source longitudinal data.

Simulation assumptions:
- Baseline vitals are influenced by age, BMI, diabetes, and hypertension status.
- Day-to-day variation follows learned or estimated distributions.
- Medication adherence may trend upward slightly over time.
- BP in hypertensive patients may show slight downward trends (treatment effect).
These are simulation assumptions for demonstration, not validated clinical models.
"""
import numpy as np
import pandas as pd

from src.utils.config import BOUNDS, RANDOM_SEED


class TemporalEngine:
    def __init__(self, seed: int = RANDOM_SEED):
        self.seed = seed
        self.learned_params = None

    def learn_from_data(self, profiles: pd.DataFrame, longitudinal: pd.DataFrame):
        params = {}

        if len(longitudinal) > 0:
            for col in ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]:
                if col in longitudinal.columns:
                    vals = longitudinal[col].dropna()
                    params[col] = {
                        "mean": float(vals.mean()),
                        "std": float(vals.std()),
                        "median": float(vals.median()),
                        "q25": float(vals.quantile(0.25)),
                        "q75": float(vals.quantile(0.75)),
                    }

            merged = longitudinal.merge(
                profiles[["patient_id", "age", "diabetes", "hypertension"]],
                on="patient_id", how="left",
            )

            for subgroup_col in ["diabetes", "hypertension"]:
                if subgroup_col in merged.columns:
                    for val in [0, 1]:
                        sub = merged[merged[subgroup_col] == val]
                        key = f"{subgroup_col}_{val}"
                        params[key] = {}
                        for col in ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]:
                            if col in sub.columns:
                                v = sub[col].dropna()
                                if len(v) > 0:
                                    params[key][col] = {"mean": float(v.mean()), "std": float(v.std())}

            if "patient_id" in longitudinal.columns and "day" in longitudinal.columns:
                patient_groups = longitudinal.groupby("patient_id")
                daily_changes = {}
                for col in ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]:
                    if col in longitudinal.columns:
                        diffs = patient_groups[col].diff().dropna()
                        daily_changes[col] = {
                            "mean_change": float(diffs.mean()),
                            "std_change": float(diffs.std()),
                        }
                params["daily_changes"] = daily_changes

        self.learned_params = params

    def generate_journeys(
        self, cohort: pd.DataFrame, days: int = 30
    ) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        records = []

        for idx, row in cohort.iterrows():
            pid = row["patient_id"]
            age = row.get("age", 55)
            bmi = row.get("bmi", 26)
            has_diabetes = int(row.get("diabetes", 0))
            has_hypertension = int(row.get("hypertension", 0))

            baselines = self._compute_baselines(age, bmi, has_diabetes, has_hypertension, rng)
            day_noise = self._get_daily_noise_params()

            trajectory = self._generate_trajectory(baselines, day_noise, days, rng, has_hypertension)

            for day_idx, day_vals in enumerate(trajectory):
                records.append({
                    "patient_id": pid,
                    "day": day_idx + 1,
                    **day_vals,
                })

        return pd.DataFrame(records)

    def _compute_baselines(self, age, bmi, has_diabetes, has_hypertension, rng):
        p = self.learned_params or {}

        base_sys = p.get("systolic_bp", {}).get("mean", 120)
        base_dia = p.get("diastolic_bp", {}).get("mean", 75)
        base_steps = p.get("steps", {}).get("mean", 6000)
        base_adh = p.get("medication_adherence", {}).get("mean", 0.72)
        base_pain = p.get("pain_score", {}).get("mean", 2.5)

        age_offset = (age - 55) * 0.35
        bmi_offset = (bmi - 26) * 0.15

        sys = base_sys + age_offset + has_hypertension * 15 + has_diabetes * 4 + rng.normal(0, 4)
        dia = base_dia + age_offset * 0.3 + has_hypertension * 8 + rng.normal(0, 3)
        steps = base_steps - (age - 45) * 40 - has_diabetes * 500 + rng.normal(0, 600)
        adh = base_adh + rng.normal(0, 0.08)
        pain = base_pain + has_diabetes * 0.6 + bmi_offset * 0.3 + max(0, (age - 65) * 0.04) + rng.normal(0, 0.5)

        return {
            "systolic_bp": sys,
            "diastolic_bp": dia,
            "steps": steps,
            "medication_adherence": adh,
            "pain_score": pain,
        }

    def _get_daily_noise_params(self):
        p = self.learned_params or {}
        dc = p.get("daily_changes", {})

        return {
            "systolic_bp": {"std": dc.get("systolic_bp", {}).get("std_change", 5.0)},
            "diastolic_bp": {"std": dc.get("diastolic_bp", {}).get("std_change", 3.5)},
            "steps": {"std": dc.get("steps", {}).get("std_change", 900)},
            "medication_adherence": {"std": dc.get("medication_adherence", {}).get("std_change", 0.05)},
            "pain_score": {"std": dc.get("pain_score", {}).get("std_change", 0.7)},
        }

    def _generate_trajectory(self, baselines, noise_params, days, rng, has_hypertension):
        trajectory = []
        current = dict(baselines)

        sys_trend = -0.08 if has_hypertension else 0.0
        adh_trend = 0.002

        for day in range(days):
            vals = {}
            current["systolic_bp"] += sys_trend + rng.normal(0, noise_params["systolic_bp"]["std"])
            current["diastolic_bp"] += rng.normal(0, noise_params["diastolic_bp"]["std"])
            current["steps"] += rng.normal(0, noise_params["steps"]["std"]) * 0.3
            current["medication_adherence"] += adh_trend + rng.normal(0, noise_params["medication_adherence"]["std"])
            current["pain_score"] += rng.normal(0, noise_params["pain_score"]["std"]) * 0.3

            vals["systolic_bp"] = round(float(np.clip(current["systolic_bp"], *BOUNDS["systolic_bp"])), 1)
            vals["diastolic_bp"] = round(float(np.clip(current["diastolic_bp"], *BOUNDS["diastolic_bp"])), 1)
            vals["steps"] = int(np.clip(current["steps"], *BOUNDS["steps"]))
            vals["medication_adherence"] = round(float(np.clip(current["medication_adherence"], *BOUNDS["medication_adherence"])), 3)
            vals["pain_score"] = round(float(np.clip(current["pain_score"], *BOUNDS["pain_score"])), 1)

            trajectory.append(vals)

        return trajectory
