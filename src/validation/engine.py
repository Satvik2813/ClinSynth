"""Statistical validation engine for comparing original and synthetic data."""
import numpy as np
import pandas as pd
from scipy import stats


def compute_numerical_stats(original: pd.Series, synthetic: pd.Series) -> dict:
    return {
        "original_mean": round(float(original.mean()), 4),
        "synthetic_mean": round(float(synthetic.mean()), 4),
        "original_median": round(float(original.median()), 4),
        "synthetic_median": round(float(synthetic.median()), 4),
        "original_std": round(float(original.std()), 4),
        "synthetic_std": round(float(synthetic.std()), 4),
        "original_min": round(float(original.min()), 4),
        "synthetic_min": round(float(synthetic.min()), 4),
        "original_max": round(float(original.max()), 4),
        "synthetic_max": round(float(synthetic.max()), 4),
        "original_q25": round(float(original.quantile(0.25)), 4),
        "synthetic_q25": round(float(synthetic.quantile(0.25)), 4),
        "original_q75": round(float(original.quantile(0.75)), 4),
        "synthetic_q75": round(float(synthetic.quantile(0.75)), 4),
    }


def ks_test(original: pd.Series, synthetic: pd.Series) -> dict:
    stat, pvalue = stats.ks_2samp(original.dropna(), synthetic.dropna())
    return {"ks_statistic": round(float(stat), 6), "p_value": round(float(pvalue), 6)}


def wasserstein_distance(original: pd.Series, synthetic: pd.Series) -> float:
    return round(float(stats.wasserstein_distance(original.dropna(), synthetic.dropna())), 6)


def categorical_comparison(original: pd.Series, synthetic: pd.Series) -> dict:
    orig_counts = original.value_counts(normalize=True).sort_index()
    synth_counts = synthetic.value_counts(normalize=True).sort_index()

    all_categories = sorted(set(orig_counts.index) | set(synth_counts.index))
    orig_probs = np.array([orig_counts.get(c, 0) for c in all_categories])
    synth_probs = np.array([synth_counts.get(c, 0) for c in all_categories])

    tvd = 0.5 * np.sum(np.abs(orig_probs - synth_probs))

    return {
        "categories": [str(c) for c in all_categories],
        "original_proportions": orig_probs.round(4).tolist(),
        "synthetic_proportions": synth_probs.round(4).tolist(),
        "total_variation_distance": round(float(tvd), 6),
    }


def correlation_comparison(original: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    num_cols = original.select_dtypes(include=[np.number]).columns.tolist()
    common_cols = [c for c in num_cols if c in synthetic.columns and c != "patient_id"]

    if len(common_cols) < 2:
        return {"error": "Not enough numerical columns for correlation comparison"}

    orig_corr = original[common_cols].corr()
    synth_corr = synthetic[common_cols].corr()

    diff = (orig_corr - synth_corr).abs()
    mean_diff = float(diff.values[np.triu_indices_from(diff.values, k=1)].mean())

    return {
        "columns": common_cols,
        "original_correlation": orig_corr.round(4).to_dict(),
        "synthetic_correlation": synth_corr.round(4).to_dict(),
        "mean_absolute_correlation_difference": round(mean_diff, 6),
    }


def validate_profiles(original: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    results = {"numerical": {}, "categorical": {}, "correlation": {}}

    num_cols = ["age", "bmi"]
    cat_cols = ["gender", "diabetes", "hypertension"]

    for col in num_cols:
        if col in original.columns and col in synthetic.columns:
            orig_vals = original[col].dropna()
            synth_vals = synthetic[col].dropna()
            if len(orig_vals) > 0 and len(synth_vals) > 0:
                results["numerical"][col] = {
                    "stats": compute_numerical_stats(orig_vals, synth_vals),
                    "ks_test": ks_test(orig_vals, synth_vals),
                    "wasserstein": wasserstein_distance(orig_vals, synth_vals),
                }

    for col in cat_cols:
        if col in original.columns and col in synthetic.columns:
            results["categorical"][col] = categorical_comparison(original[col], synthetic[col])

    results["correlation"] = correlation_comparison(original, synthetic)

    return results


def validate_longitudinal(original: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    results = {"numerical": {}, "trend": {}}

    value_cols = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]

    for col in value_cols:
        if col in original.columns and col in synthetic.columns:
            orig_vals = original[col].dropna()
            synth_vals = synthetic[col].dropna()
            if len(orig_vals) > 0 and len(synth_vals) > 0:
                results["numerical"][col] = {
                    "stats": compute_numerical_stats(orig_vals, synth_vals),
                    "ks_test": ks_test(orig_vals, synth_vals),
                }

    if "day" in original.columns and "day" in synthetic.columns:
        for col in value_cols:
            if col in original.columns and col in synthetic.columns:
                orig_daily = original.groupby("day")[col].mean()
                synth_daily = synthetic.groupby("day")[col].mean()
                common_days = sorted(set(orig_daily.index) & set(synth_daily.index))
                if len(common_days) > 1:
                    orig_trend = orig_daily.loc[common_days].values
                    synth_trend = synth_daily.loc[common_days].values
                    corr = np.corrcoef(orig_trend, synth_trend)[0, 1] if len(orig_trend) > 1 else 0
                    results["trend"][col] = {
                        "days": common_days,
                        "original_daily_mean": orig_trend.round(4).tolist(),
                        "synthetic_daily_mean": synth_trend.round(4).tolist(),
                        "trend_correlation": round(float(corr), 4) if not np.isnan(corr) else 0.0,
                    }

    return results


def compute_fidelity_summary(profile_results: dict, longitudinal_results: dict) -> dict:
    scores = []

    for col, data in profile_results.get("numerical", {}).items():
        ks_stat = data.get("ks_test", {}).get("ks_statistic", 1.0)
        scores.append(1.0 - min(ks_stat, 1.0))

    for col, data in profile_results.get("categorical", {}).items():
        tvd = data.get("total_variation_distance", 1.0)
        scores.append(1.0 - min(tvd, 1.0))

    corr_diff = profile_results.get("correlation", {}).get("mean_absolute_correlation_difference", 1.0)
    if isinstance(corr_diff, (int, float)):
        scores.append(1.0 - min(corr_diff, 1.0))

    for col, data in longitudinal_results.get("numerical", {}).items():
        ks_stat = data.get("ks_test", {}).get("ks_statistic", 1.0)
        scores.append(1.0 - min(ks_stat, 1.0))

    if len(scores) == 0:
        return {"overall_fidelity": 0.0, "component_count": 0, "formula": "N/A"}

    overall = round(float(np.mean(scores)), 4)

    return {
        "overall_fidelity": overall,
        "component_count": len(scores),
        "formula": "mean(1 - KS_statistic for numerical, 1 - TVD for categorical, 1 - mean_corr_diff)",
        "interpretation": "Score from 0 to 1 where 1 means perfect distributional match. "
                          "Based on KS statistics, total variation distance, and correlation preservation.",
    }


def compute_per_column_quality(original: pd.DataFrame, synthetic: pd.DataFrame) -> list[dict]:
    cards = []
    num_cols = original.select_dtypes(include=[np.number]).columns.tolist()
    common_num = [c for c in num_cols if c in synthetic.columns and c != "patient_id"]

    for col in common_num:
        orig = original[col].dropna()
        synth = synthetic[col].dropna()
        if len(orig) == 0 or len(synth) == 0:
            continue

        ks = ks_test(orig, synth)
        ks_val = ks["ks_statistic"]
        if ks_val < 0.05:
            quality = "Excellent (KS < 0.05)"
        elif ks_val < 0.10:
            quality = "Good (KS < 0.10)"
        elif ks_val < 0.20:
            quality = "Fair (KS < 0.20)"
        else:
            quality = "Poor (KS >= 0.20)"

        cards.append({
            "column": col,
            "type": "numerical",
            "mean_diff": round(abs(float(orig.mean()) - float(synth.mean())), 4),
            "std_diff": round(abs(float(orig.std()) - float(synth.std())), 4),
            "ks_statistic": ks_val,
            "quality": quality,
        })

    cat_cols = original.select_dtypes(exclude=[np.number]).columns.tolist()
    common_cat = [c for c in cat_cols if c in synthetic.columns and c != "patient_id"]
    for col in common_cat:
        cmp = categorical_comparison(original[col], synthetic[col])
        tvd = cmp["total_variation_distance"]
        if tvd < 0.03:
            quality = "Excellent (TVD < 0.03)"
        elif tvd < 0.08:
            quality = "Good (TVD < 0.08)"
        elif tvd < 0.15:
            quality = "Fair (TVD < 0.15)"
        else:
            quality = "Poor (TVD >= 0.15)"

        cards.append({
            "column": col,
            "type": "categorical",
            "tvd": tvd,
            "quality": quality,
        })

    return cards


def compute_subgroup_fidelity(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    subgroup_col: str,
    subgroup_val,
) -> dict:
    orig_sub = original[original[subgroup_col] == subgroup_val]
    synth_sub = synthetic[synthetic[subgroup_col] == subgroup_val]

    if len(orig_sub) < 5 or len(synth_sub) < 5:
        return {
            "subgroup": f"{subgroup_col}={subgroup_val}",
            "original_n": len(orig_sub),
            "synthetic_n": len(synth_sub),
            "warning": "Sample too small for reliable comparison",
            "fidelity": None,
        }

    num_cols = orig_sub.select_dtypes(include=[np.number]).columns.tolist()
    common = [c for c in num_cols if c in synth_sub.columns and c != "patient_id"]

    scores = []
    details = {}
    for col in common:
        o = orig_sub[col].dropna()
        s = synth_sub[col].dropna()
        if len(o) > 0 and len(s) > 0:
            k = ks_test(o, s)
            scores.append(1.0 - min(k["ks_statistic"], 1.0))
            details[col] = k["ks_statistic"]

    fidelity = round(float(np.mean(scores)), 4) if scores else None

    return {
        "subgroup": f"{subgroup_col}={subgroup_val}",
        "original_n": len(orig_sub),
        "synthetic_n": len(synth_sub),
        "fidelity": fidelity,
        "column_ks": details,
    }


def compute_all_subgroup_fidelity(original: pd.DataFrame, synthetic: pd.DataFrame) -> list[dict]:
    results = []
    subgroups = [
        ("diabetes", 0, "Non-Diabetic"),
        ("diabetes", 1, "Diabetic"),
        ("hypertension", 0, "Non-Hypertensive"),
        ("hypertension", 1, "Hypertensive"),
    ]

    for col, val, label in subgroups:
        if col in original.columns and col in synthetic.columns:
            r = compute_subgroup_fidelity(original, synthetic, col, val)
            r["label"] = label
            results.append(r)

    if "age" in original.columns and "age" in synthetic.columns:
        for label, mask_fn in [("Elderly (age >= 60)", lambda df: df["age"] >= 60),
                                ("Non-Elderly (age < 60)", lambda df: df["age"] < 60)]:
            orig_sub = original[mask_fn(original)]
            synth_sub = synthetic[mask_fn(synthetic)]
            if len(orig_sub) >= 5 and len(synth_sub) >= 5:
                num_cols = orig_sub.select_dtypes(include=[np.number]).columns.tolist()
                common = [c for c in num_cols if c in synth_sub.columns and c != "patient_id"]
                scores = []
                details = {}
                for col in common:
                    o = orig_sub[col].dropna()
                    s = synth_sub[col].dropna()
                    if len(o) > 0 and len(s) > 0:
                        k = ks_test(o, s)
                        scores.append(1.0 - min(k["ks_statistic"], 1.0))
                        details[col] = k["ks_statistic"]
                results.append({
                    "subgroup": label,
                    "label": label,
                    "original_n": len(orig_sub),
                    "synthetic_n": len(synth_sub),
                    "fidelity": round(float(np.mean(scores)), 4) if scores else None,
                    "column_ks": details,
                })

    return results
