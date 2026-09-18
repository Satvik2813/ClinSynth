"""Privacy evaluation metrics.

Evaluates potential privacy leakage between original and synthetic data.
These are screening metrics, not formal privacy guarantees.

Privacy modes (low/balanced/high) control the strictness of near-copy
rejection and noise injection. They do NOT implement formal differential
privacy.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder

from src.utils.config import PRIVACY_MODES


def detect_exact_duplicates(original: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    compare_cols = [c for c in original.columns if c in synthetic.columns and c != "patient_id"]
    if not compare_cols:
        return {"exact_duplicates": 0, "columns_compared": [], "total_synthetic_records": len(synthetic),
                "total_original_records": len(original), "duplicate_rate": 0.0}

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


def _prepare_scaled_data(original, synthetic):
    compare_cols = [c for c in original.columns if c in synthetic.columns and c != "patient_id"]
    if not compare_cols:
        return None, None, compare_cols

    orig = original[compare_cols].copy()
    synth = synthetic[compare_cols].copy()

    for col in compare_cols:
        if not pd.api.types.is_numeric_dtype(orig[col]):
            le = LabelEncoder()
            combined = pd.concat([orig[col].astype(str), synth[col].astype(str)])
            le.fit(combined)
            orig[col] = le.transform(orig[col].astype(str))
            synth[col] = le.transform(synth[col].astype(str))
        else:
            orig[col] = orig[col].fillna(orig[col].median())
            synth[col] = synth[col].fillna(synth[col].median())

    scaler = StandardScaler()
    orig_scaled = scaler.fit_transform(orig.values.astype(float))
    synth_scaled = scaler.transform(synth.values.astype(float))

    return orig_scaled, synth_scaled, compare_cols


def _compute_nn_distances(source, target, sample_size, rng):
    if len(source) > sample_size:
        indices = rng.choice(len(source), size=sample_size, replace=False)
        source_sample = source[indices]
    else:
        source_sample = source

    distances = []
    batch_size = 100
    for i in range(0, len(source_sample), batch_size):
        batch = source_sample[i:i + batch_size]
        dists = np.linalg.norm(batch[:, np.newaxis] - target[np.newaxis, :], axis=2)
        min_dists = dists.min(axis=1)
        distances.extend(min_dists.tolist())

    return np.array(distances)


def nearest_neighbor_analysis(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    sample_size: int = 500,
    seed: int = 42,
    near_copy_threshold: float = 0.1,
) -> dict:
    orig_scaled, synth_scaled, compare_cols = _prepare_scaled_data(original, synthetic)
    if orig_scaled is None:
        return {"error": "No common columns for nearest neighbor analysis"}

    rng = np.random.default_rng(seed)
    distances = _compute_nn_distances(synth_scaled, orig_scaled, sample_size, rng)

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
        "near_copy_count": int((distances < near_copy_threshold).sum()),
        "near_copy_threshold": near_copy_threshold,
        "distances": distances.tolist(),
    }


def real_to_real_baseline(
    original: pd.DataFrame,
    sample_size: int = 300,
    seed: int = 42,
) -> dict:
    orig_scaled, _, _ = _prepare_scaled_data(original, original)
    if orig_scaled is None or len(orig_scaled) < 3:
        return {"error": "Not enough data for real-to-real baseline"}

    rng = np.random.default_rng(seed)
    n = len(orig_scaled)
    actual_sample = min(sample_size, n)

    if n > actual_sample:
        indices = rng.choice(n, size=actual_sample, replace=False)
        sample = orig_scaled[indices]
    else:
        sample = orig_scaled

    distances = []
    batch_size = 50
    for i in range(0, len(sample), batch_size):
        batch = sample[i:i + batch_size]
        dists = np.linalg.norm(batch[:, np.newaxis] - orig_scaled[np.newaxis, :], axis=2)
        for j in range(len(batch)):
            row_dists = dists[j]
            row_dists_sorted = np.sort(row_dists)
            if len(row_dists_sorted) > 1:
                distances.append(float(row_dists_sorted[1]))

    distances = np.array(distances)
    if len(distances) == 0:
        return {"error": "Could not compute real-to-real distances"}

    return {
        "sample_size": len(distances),
        "mean_distance": round(float(distances.mean()), 6),
        "median_distance": round(float(np.median(distances)), 6),
        "min_distance": round(float(distances.min()), 6),
        "q5_distance": round(float(np.percentile(distances, 5)), 6),
        "q25_distance": round(float(np.percentile(distances, 25)), 6),
        "q75_distance": round(float(np.percentile(distances, 75)), 6),
    }


def synth_to_synth_distances(
    synthetic: pd.DataFrame,
    sample_size: int = 300,
    seed: int = 42,
) -> dict:
    orig_scaled, _, _ = _prepare_scaled_data(synthetic, synthetic)
    if orig_scaled is None or len(orig_scaled) < 3:
        return {"error": "Not enough data"}

    rng = np.random.default_rng(seed)
    n = len(orig_scaled)
    actual_sample = min(sample_size, n)

    if n > actual_sample:
        indices = rng.choice(n, size=actual_sample, replace=False)
        sample = orig_scaled[indices]
    else:
        sample = orig_scaled

    distances = []
    batch_size = 50
    for i in range(0, len(sample), batch_size):
        batch = sample[i:i + batch_size]
        dists = np.linalg.norm(batch[:, np.newaxis] - orig_scaled[np.newaxis, :], axis=2)
        for j in range(len(batch)):
            row_dists = dists[j]
            row_dists_sorted = np.sort(row_dists)
            if len(row_dists_sorted) > 1:
                distances.append(float(row_dists_sorted[1]))

    distances = np.array(distances)
    if len(distances) == 0:
        return {"error": "Could not compute synth-to-synth distances"}

    return {
        "sample_size": len(distances),
        "mean_distance": round(float(distances.mean()), 6),
        "median_distance": round(float(np.median(distances)), 6),
        "min_distance": round(float(distances.min()), 6),
    }


def apply_privacy_mode(
    synthetic: pd.DataFrame,
    original: pd.DataFrame,
    mode: str = "balanced",
    seed: int = 42,
) -> tuple[pd.DataFrame, dict]:
    config = PRIVACY_MODES.get(mode, PRIVACY_MODES["balanced"])
    rng = np.random.default_rng(seed)

    result = synthetic.copy()
    stats = {"mode": mode, "records_rejected": 0, "records_noised": 0, "total_records": len(result)}

    rejection_threshold = config["rejection_threshold"]
    noise_scale = config["noise_scale"]

    if rejection_threshold > 0 and len(original) > 0:
        orig_scaled, synth_scaled, compare_cols = _prepare_scaled_data(original, result)
        if orig_scaled is not None and synth_scaled is not None:
            keep_mask = np.ones(len(synth_scaled), dtype=bool)
            batch_size = 200
            for i in range(0, len(synth_scaled), batch_size):
                batch = synth_scaled[i:i + batch_size]
                dists = np.linalg.norm(batch[:, np.newaxis] - orig_scaled[np.newaxis, :], axis=2)
                min_dists = dists.min(axis=1)
                keep_mask[i:i + len(batch)] = min_dists >= rejection_threshold

            rejected_count = int((~keep_mask).sum())
            stats["records_rejected"] = rejected_count

            if rejected_count < len(result) * 0.5:
                result = result[keep_mask].reset_index(drop=True)
            else:
                stats["rejection_capped"] = True

    if noise_scale > 0:
        numeric_cols = result.select_dtypes(include=[np.number]).columns.tolist()
        noise_cols = [c for c in numeric_cols if c not in ("patient_id", "day")]
        for col in noise_cols:
            col_std = result[col].std()
            if col_std > 0:
                noise = rng.normal(0, col_std * noise_scale, size=len(result))
                result[col] = result[col] + noise
                stats["records_noised"] = len(result)

    if "patient_id" in result.columns:
        result["patient_id"] = [f"SYN-{i+1:06d}" for i in range(len(result))]

    stats["final_records"] = len(result)
    return result, stats


def membership_inference_screening(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    holdout_fraction: float = 0.3,
    sample_size: int = 200,
    seed: int = 42,
) -> dict:
    """Lightweight membership inference attack based on distance separability.

    Splits the real data into member (training) and non-member (holdout) sets.
    Measures nearest-neighbor distances from each to the synthetic cohort.
    Uses distance as an attack score and computes ROC-AUC.

    An AUC near 0.5 means the attack cannot distinguish members from
    non-members — poor attack separability. Higher values indicate
    potential membership signal.
    """
    if len(original) < 20:
        return {"error": "Too few original records for membership inference screening"}

    rng = np.random.default_rng(seed)
    n = len(original)
    n_holdout = max(5, int(n * holdout_fraction))
    n_member = n - n_holdout

    indices = rng.permutation(n)
    member_idx = indices[:n_member]
    nonmember_idx = indices[n_member:]

    member_df = original.iloc[member_idx]
    nonmember_df = original.iloc[nonmember_idx]

    orig_scaled, synth_scaled, compare_cols = _prepare_scaled_data(original, synthetic)
    if orig_scaled is None:
        return {"error": "Could not prepare data for membership inference"}

    member_scaled = orig_scaled[member_idx]
    nonmember_scaled = orig_scaled[nonmember_idx]

    actual_member_sample = min(sample_size, len(member_scaled))
    actual_nonmember_sample = min(sample_size, len(nonmember_scaled))

    if actual_member_sample < 5 or actual_nonmember_sample < 5:
        return {"error": "Too few samples for reliable membership inference screening"}

    if len(member_scaled) > actual_member_sample:
        m_idx = rng.choice(len(member_scaled), size=actual_member_sample, replace=False)
        member_sample = member_scaled[m_idx]
    else:
        member_sample = member_scaled

    if len(nonmember_scaled) > actual_nonmember_sample:
        nm_idx = rng.choice(len(nonmember_scaled), size=actual_nonmember_sample, replace=False)
        nonmember_sample = nonmember_scaled[nm_idx]
    else:
        nonmember_sample = nonmember_scaled

    member_dists = _compute_nn_distances(member_sample, synth_scaled, len(member_sample), rng)
    nonmember_dists = _compute_nn_distances(nonmember_sample, synth_scaled, len(nonmember_sample), rng)

    labels = np.concatenate([
        np.ones(len(member_dists)),
        np.zeros(len(nonmember_dists)),
    ])
    scores = np.concatenate([-member_dists, -nonmember_dists])

    try:
        from sklearn.metrics import roc_auc_score
        auc = round(float(roc_auc_score(labels, scores)), 4)
    except (ValueError, ImportError):
        auc = None

    return {
        "membership_inference_auc": auc,
        "member_sample_size": len(member_dists),
        "nonmember_sample_size": len(nonmember_dists),
        "member_mean_distance": round(float(member_dists.mean()), 6),
        "nonmember_mean_distance": round(float(nonmember_dists.mean()), 6),
        "interpretation": (
            "AUC near 0.5 indicates poor attack separability (good privacy). "
            "Higher AUC indicates potential membership signal."
        ),
        "disclaimer": (
            "This is a lightweight distance-based screening, not a formal "
            "membership inference resistance guarantee."
        ),
    }


def privacy_screening(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    duplicate_threshold: int = 0,
    near_copy_threshold: float = 0.1,
    max_near_copy_rate: float = 0.01,
) -> dict:
    dup_result = detect_exact_duplicates(original, synthetic)
    nn_result = nearest_neighbor_analysis(
        original,
        synthetic,
        near_copy_threshold=near_copy_threshold,
    )
    rr_result = real_to_real_baseline(original)
    ss_result = synth_to_synth_distances(synthetic)
    mi_result = membership_inference_screening(original, synthetic)

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

    mi_auc = mi_result.get("membership_inference_auc")
    if mi_auc is not None:
        mi_pass = mi_auc < 0.6
        checks.append({
            "check": "Membership Inference Screening",
            "passed": mi_pass,
            "detail": f"Membership inference screening AUC: {mi_auc:.4f} "
                      f"(AUC near 0.5 = poor attack separability = good privacy)",
        })

    all_passed = all(c["passed"] for c in checks)

    return {
        "overall_status": "PASSED" if all_passed else "REVIEW NEEDED",
        "checks": checks,
        "exact_duplicates": dup_result,
        "nearest_neighbor": nn_result,
        "real_to_real_baseline": rr_result,
        "synth_to_synth": ss_result,
        "membership_inference": mi_result,
        "disclaimer": (
            "These metrics provide privacy screening, not formal privacy guarantees. "
            "Synthetic data generated via statistical models can reduce exposure of "
            "original records, but is not automatically equivalent to formal "
            "differential privacy. Consult privacy experts for production use."
        ),
    }
