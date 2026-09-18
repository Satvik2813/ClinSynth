"""Temporal / longitudinal patient journey generator.

Generates realistic daily health measurements for synthetic patients
based on statistical patterns learned from source longitudinal data.

Supports trajectory archetypes:
- Stable: small variance around baseline
- Improving: gradual simulated improvement
- Worsening: gradual simulated deterioration
- Fluctuating: larger bounded oscillations

Simulation assumptions — not validated clinical models.
"""
import numpy as np
import pandas as pd

from src.utils.config import BOUNDS, RANDOM_SEED, DEFAULT_TRAJECTORY_DIST, TRAJECTORY_TYPES


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
        self,
        cohort: pd.DataFrame,
        days: int = 30,
        trajectory_dist: dict | None = None,
    ) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)

        if trajectory_dist is None:
            trajectory_dist = DEFAULT_TRAJECTORY_DIST

        n = len(cohort)
        types = list(trajectory_dist.keys())
        probs = np.array([trajectory_dist.get(t, 0) for t in types], dtype=float)
        probs = probs / probs.sum()
        assignments = rng.choice(types, size=n, p=probs)

        all_records = []

        for idx, (_, row) in enumerate(cohort.iterrows()):
            pid = row["patient_id"]
            age = row.get("age", 55)
            bmi = row.get("bmi", 26)
            has_diabetes = int(row.get("diabetes", 0))
            has_hypertension = int(row.get("hypertension", 0))
            traj_type = assignments[idx]

            baselines = self._compute_baselines(age, bmi, has_diabetes, has_hypertension, rng)
            day_noise = self._get_daily_noise_params()

            trajectory = self._generate_trajectory(
                baselines, day_noise, days, rng, has_hypertension, traj_type,
            )

            for day_idx, day_vals in enumerate(trajectory):
                all_records.append({
                    "patient_id": pid,
                    "day": day_idx + 1,
                    "trajectory_type": traj_type,
                    **day_vals,
                })

        return pd.DataFrame(all_records)

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

    def _get_trajectory_trends(self, traj_type: str, has_hypertension: int):
        if traj_type == "stable":
            return {
                "systolic_bp": -0.02 if has_hypertension else 0.0,
                "diastolic_bp": 0.0,
                "steps": 0.0,
                "medication_adherence": 0.001,
                "pain_score": 0.0,
                "noise_scale": 0.8,
            }
        elif traj_type == "improving":
            return {
                "systolic_bp": -0.15 if has_hypertension else -0.05,
                "diastolic_bp": -0.03,
                "steps": 15.0,
                "medication_adherence": 0.004,
                "pain_score": -0.015,
                "noise_scale": 0.7,
            }
        elif traj_type == "worsening":
            return {
                "systolic_bp": 0.12,
                "diastolic_bp": 0.04,
                "steps": -20.0,
                "medication_adherence": -0.003,
                "pain_score": 0.02,
                "noise_scale": 0.9,
            }
        elif traj_type == "fluctuating":
            return {
                "systolic_bp": -0.03 if has_hypertension else 0.0,
                "diastolic_bp": 0.0,
                "steps": 0.0,
                "medication_adherence": 0.001,
                "pain_score": 0.0,
                "noise_scale": 1.6,
            }
        return {
            "systolic_bp": 0.0, "diastolic_bp": 0.0, "steps": 0.0,
            "medication_adherence": 0.0, "pain_score": 0.0, "noise_scale": 1.0,
        }

    def _generate_trajectory(self, baselines, noise_params, days, rng, has_hypertension, traj_type="stable"):
        trajectory = []
        current = dict(baselines)

        trends = self._get_trajectory_trends(traj_type, has_hypertension)
        noise_scale = trends["noise_scale"]

        for day in range(days):
            current["systolic_bp"] += trends["systolic_bp"] + rng.normal(0, noise_params["systolic_bp"]["std"] * noise_scale)
            current["diastolic_bp"] += trends["diastolic_bp"] + rng.normal(0, noise_params["diastolic_bp"]["std"] * noise_scale)
            current["steps"] += trends["steps"] + rng.normal(0, noise_params["steps"]["std"] * noise_scale) * 0.3
            current["medication_adherence"] += trends["medication_adherence"] + rng.normal(0, noise_params["medication_adherence"]["std"] * noise_scale)
            current["pain_score"] += trends["pain_score"] + rng.normal(0, noise_params["pain_score"]["std"] * noise_scale) * 0.3

            if traj_type == "fluctuating" and day > 0:
                period = rng.uniform(5, 10)
                amp = rng.uniform(0.3, 0.8)
                current["systolic_bp"] += amp * np.sin(2 * np.pi * day / period) * 2
                current["steps"] += amp * np.sin(2 * np.pi * day / (period + 2)) * 200

            sys_val = round(float(np.clip(current["systolic_bp"], *BOUNDS["systolic_bp"])), 1)
            dia_val = round(float(np.clip(current["diastolic_bp"], *BOUNDS["diastolic_bp"])), 1)

            if dia_val >= sys_val:
                dia_val = sys_val - rng.uniform(5, 15)
                dia_val = round(float(np.clip(dia_val, *BOUNDS["diastolic_bp"])), 1)
                current["diastolic_bp"] = dia_val

            vals = {
                "systolic_bp": sys_val,
                "diastolic_bp": dia_val,
                "steps": int(np.clip(current["steps"], *BOUNDS["steps"])),
                "medication_adherence": round(float(np.clip(current["medication_adherence"], *BOUNDS["medication_adherence"])), 3),
                "pain_score": round(float(np.clip(current["pain_score"], *BOUNDS["pain_score"])), 1),
            }

            trajectory.append(vals)

        return trajectory
