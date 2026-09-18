"""Privacy evaluation metrics.

Evaluates potential privacy leakage between original and synthetic data.
These are screening metrics, not formal privacy guarantees.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder


def detect_exact_duplicates(original: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    compare_cols = [c for c in original.columns if c in synthetic.columns and c != "patient_id"]
    if not compare_cols:
        return {"exact_duplicates": 0, "columns_compared": []}

    orig_normalized = original[compare_cols].copy()
    synth_normalized = synthetic[compare_cols].copy()

    for col in compare_cols:
        if pd.api.types.is_numeric_dtype(orig_normalized[col]):
            orig_normalized[col] = orig_normalized[col].round(2)
            synth_normalized[col] = synth_normalized[col].round(2)
        else:
            orig_normalized[col] = orig_normalized[col].astype(str).str.lower().str.strip()
            synth_normalized[col] = synth_normalized[col].astype(str).str.lower().str.strip()

    orig_tuples = set(orig_normalized.itertuples(index=False, name=None))
    synth_tuples = set(synth_normalized.itertuples(index=False, name=None))

    duplicates = orig_tuples & synth_tuples

    return {
        "exact_duplicates": len(duplicates),
        "total_synthetic_records": len(synthetic),
        "total_original_records": len(original),
        "duplicate_rate": round(len(duplicates) / max(len(synthetic), 1), 6),
        "columns_compared": compare_cols,
    }


def nearest_neighbor_analysis(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    sample_size: int = 500,
    seed: int = 42,
) -> dict:
    compare_cols = [c for c in original.columns if c in synthetic.columns and c != "patient_id"]
    if not compare_cols:
        return {"error": "No common columns for nearest neighbor analysis"}

    orig = original[compare_cols].copy()
    synth = synthetic[compare_cols].copy()

    label_encoders = {}
    for col in compare_cols:
        if not pd.api.types.is_numeric_dtype(orig[col]):
            le = LabelEncoder()
            combined = pd.concat([orig[col].astype(str), synth[col].astype(str)])
            le.fit(combined)
            orig[col] = le.transform(orig[col].astype(str))
            synth[col] = le.transform(synth[col].astype(str))
            label_encoders[col] = le
        else:
            orig[col] = orig[col].fillna(orig[col].median())
            synth[col] = synth[col].fillna(synth[col].median())

    scaler = StandardScaler()
    orig_scaled = scaler.fit_transform(orig.values.astype(float))
    synth_scaled = scaler.transform(synth.values.astype(float))

    rng = np.random.default_rng(seed)
    if len(synth_scaled) > sample_size:
        indices = rng.choice(len(synth_scaled), size=sample_size, replace=False)
        synth_sample = synth_scaled[indices]
    else:
        synth_sample = synth_scaled

    distances = []
    batch_size = 100
    for i in range(0, len(synth_sample), batch_size):
        batch = synth_sample[i:i + batch_size]
        dists = np.linalg.norm(batch[:, np.newaxis] - orig_scaled[np.newaxis, :], axis=2)
        min_dists = dists.min(axis=1)
        distances.extend(min_dists.tolist())

    distances = np.array(distances)

    return {
        "sample_size": len(distances),
        "mean_distance": round(float(distances.mean()), 6),
        "median_distance": round(float(np.median(distances)), 6),
        "min_distance": round(float(distances.min()), 6),
        "max_distance": round(float(distances.max()), 6),
        "std_distance": round(float(distances.std()), 6),
        "q5_distance": round(float(np.percentile(distances, 5)), 6),
        "q25_distance": round(float(np.percentile(distances, 25)), 6),
        "q75_distance": round(float(np.percentile(distances, 75)), 6),
        "q95_distance": round(float(np.percentile(distances, 95)), 6),
        "near_copy_count": int((distances < 0.1).sum()),
        "near_copy_threshold": 0.1,
        "distances": distances.tolist(),
    }


def privacy_screening(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    duplicate_threshold: int = 0,
    near_copy_threshold: float = 0.1,
    max_near_copy_rate: float = 0.01,
) -> dict:
    dup_result = detect_exact_duplicates(original, synthetic)
    nn_result = nearest_neighbor_analysis(original, synthetic)

    checks = []

    dup_pass = dup_result["exact_duplicates"] <= duplicate_threshold
    checks.append({
        "check": "Exact Duplicate Detection",
        "passed": dup_pass,
        "detail": f"{dup_result['exact_duplicates']} exact duplicates found "
                  f"(threshold: {duplicate_threshold})",
    })

    if "near_copy_count" in nn_result:
        near_copy_rate = nn_result["near_copy_count"] / max(nn_result["sample_size"], 1)
        nn_pass = near_copy_rate <= max_near_copy_rate
        checks.append({
            "check": "Near-Copy Detection",
            "passed": nn_pass,
            "detail": f"{nn_result['near_copy_count']} records below distance threshold "
                      f"{near_copy_threshold} ({near_copy_rate:.4%} of sample, "
                      f"max allowed: {max_near_copy_rate:.2%})",
        })

    dist_pass = nn_result.get("median_distance", 0) > 0.5
    checks.append({
        "check": "Distance Distribution",
        "passed": dist_pass,
        "detail": f"Median nearest-neighbor distance: {nn_result.get('median_distance', 'N/A')} "
                  f"(expected > 0.5 for good privacy)",
    })

    all_passed = all(c["passed"] for c in checks)

    return {
        "overall_status": "PASSED" if all_passed else "REVIEW NEEDED",
        "checks": checks,
        "exact_duplicates": dup_result,
        "nearest_neighbor": nn_result,
        "disclaimer": (
            "These metrics provide privacy screening, not formal privacy guarantees. "
            "Synthetic data generated via statistical models can reduce exposure of "
            "original records, but is not automatically equivalent to formal "
            "differential privacy. Consult privacy experts for production use."
        ),
    }
