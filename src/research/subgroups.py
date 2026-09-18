"""Source and synthetic subgroup analysis for Rare Cohort Amplifier."""
from __future__ import annotations

import pandas as pd


def compute_source_subgroups(profiles: pd.DataFrame) -> dict:
    n = len(profiles)
    result: dict = {"total_patients": n, "subgroups": []}

    if n == 0:
        return result

    elderly_mask = profiles["age"] >= 60 if "age" in profiles.columns else pd.Series([False] * n)
    diabetes_mask = profiles["diabetes"] == 1 if "diabetes" in profiles.columns else pd.Series([False] * n)
    htn_mask = profiles["hypertension"] == 1 if "hypertension" in profiles.columns else pd.Series([False] * n)

    groups = [
        ("Elderly (age >= 60)", elderly_mask),
        ("Diabetic", diabetes_mask),
        ("Hypertensive", htn_mask),
        ("Elderly + Diabetic", elderly_mask & diabetes_mask),
        ("Diabetic + Hypertensive", diabetes_mask & htn_mask),
        ("Elderly + Hypertensive", elderly_mask & htn_mask),
        ("Elderly + Diabetic + Hypertensive", elderly_mask & diabetes_mask & htn_mask),
    ]

    for label, mask in groups:
        count = int(mask.sum())
        result["subgroups"].append({
            "label": label,
            "count": count,
            "percentage": round(count / n * 100, 2) if n > 0 else 0,
        })

    return result


def compute_rare_cohort_amplification(
    source_profiles: pd.DataFrame,
    synthetic_profiles: pd.DataFrame,
) -> list[dict]:
    source_subgroups = compute_source_subgroups(source_profiles)
    synth_subgroups = compute_source_subgroups(synthetic_profiles)

    source_map = {s["label"]: s for s in source_subgroups["subgroups"]}
    synth_map = {s["label"]: s for s in synth_subgroups["subgroups"]}

    results = []
    for label in source_map:
        src = source_map[label]
        syn = synth_map.get(label, {"count": 0, "percentage": 0})
        amplification = round(syn["count"] / src["count"], 2) if src["count"] > 0 else None
        results.append({
            "subgroup": label,
            "source_count": src["count"],
            "source_pct": src["percentage"],
            "synthetic_count": syn["count"],
            "synthetic_pct": syn["percentage"],
            "amplification_factor": amplification,
        })

    return results
