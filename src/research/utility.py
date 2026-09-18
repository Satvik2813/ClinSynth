"""Downstream Research Utility — Train on Synthetic, Test on Real (TSTR).

Evaluates whether models trained on synthetic data preserve useful
statistical signal when evaluated on held-out real data. This is a
measure of downstream utility, not clinical equivalence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler


def _prepare_features(
    df: pd.DataFrame, target: str, exclude: tuple[str, ...] = ("patient_id",)
) -> tuple[pd.DataFrame, pd.Series]:
    feature_cols = [
        c for c in df.columns
        if c != target and c not in exclude and c != "patient_id"
    ]
    X = df[feature_cols].copy()
    y = df[target].copy()

    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
        else:
            X[col] = X[col].fillna(X[col].median())

    y = y.fillna(0).astype(int)
    return X, y


def _evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = model.predict(X_test)

    metrics: dict = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
    }

    try:
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)
            if y_proba.shape[1] == 2:
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_proba[:, 1])), 4)
            else:
                metrics["roc_auc"] = None
        else:
            metrics["roc_auc"] = None
    except (ValueError, IndexError):
        metrics["roc_auc"] = None

    return metrics


def compute_tstr_utility(
    real_profiles: pd.DataFrame,
    synthetic_profiles: pd.DataFrame,
    target: str = "hypertension",
    model_type: str = "logistic_regression",
    test_size: float = 0.3,
    seed: int = 42,
) -> dict:
    if target not in real_profiles.columns:
        return {"error": f"Target column '{target}' not found in real data"}
    if target not in synthetic_profiles.columns:
        return {"error": f"Target column '{target}' not found in synthetic data"}

    real_target_vals = real_profiles[target].dropna().astype(int)
    if len(real_target_vals.unique()) < 2:
        return {"error": f"Target '{target}' has fewer than 2 classes in real data"}

    synth_target_vals = synthetic_profiles[target].dropna().astype(int)
    if len(synth_target_vals.unique()) < 2:
        return {"error": f"Target '{target}' has fewer than 2 classes in synthetic data"}

    if len(real_profiles) < 20:
        return {"error": "Too few real samples for reliable evaluation (need >= 20)"}

    X_real, y_real = _prepare_features(real_profiles, target)
    X_synth, y_synth = _prepare_features(synthetic_profiles, target)

    common_cols = sorted(set(X_real.columns) & set(X_synth.columns))
    if len(common_cols) == 0:
        return {"error": "No common feature columns between real and synthetic data"}

    X_real = X_real[common_cols]
    X_synth = X_synth[common_cols]

    X_real_train, X_real_test, y_real_train, y_real_test = train_test_split(
        X_real, y_real, test_size=test_size, random_state=seed, stratify=y_real,
    )

    scaler = StandardScaler()
    X_real_train_scaled = scaler.fit_transform(X_real_train)
    X_real_test_scaled = scaler.transform(X_real_test)
    X_synth_scaled = scaler.transform(X_synth)

    if model_type == "random_forest":
        real_model = RandomForestClassifier(
            n_estimators=50, max_depth=5, random_state=seed, n_jobs=1,
        )
        synth_model = RandomForestClassifier(
            n_estimators=50, max_depth=5, random_state=seed, n_jobs=1,
        )
    else:
        real_model = LogisticRegression(
            max_iter=500, random_state=seed, solver="lbfgs",
        )
        synth_model = LogisticRegression(
            max_iter=500, random_state=seed, solver="lbfgs",
        )

    real_model.fit(X_real_train_scaled, y_real_train)
    real_metrics = _evaluate_model(real_model, X_real_test_scaled, y_real_test)

    synth_model.fit(X_synth_scaled, y_synth)
    synth_metrics = _evaluate_model(synth_model, X_real_test_scaled, y_real_test)

    utility_retention = None
    if real_metrics.get("roc_auc") and synth_metrics.get("roc_auc"):
        if real_metrics["roc_auc"] > 0:
            utility_retention = round(
                float(synth_metrics["roc_auc"] / real_metrics["roc_auc"]), 4
            )
    elif real_metrics.get("f1") and real_metrics["f1"] > 0:
        utility_retention = round(
            float(synth_metrics["f1"] / real_metrics["f1"]), 4
        )

    return {
        "target": target,
        "model_type": model_type,
        "real_train_size": len(X_real_train),
        "real_test_size": len(X_real_test),
        "synthetic_train_size": len(X_synth),
        "features_used": common_cols,
        "real_trained_metrics": real_metrics,
        "synthetic_trained_metrics": synth_metrics,
        "utility_retention": utility_retention,
        "methodology": (
            "Train on Synthetic, Test on Real (TSTR): A baseline model is trained "
            "on real data and a comparison model on synthetic data. Both are "
            "evaluated on the same held-out real test set. Utility retention "
            "measures how much predictive signal the synthetic data preserves."
        ),
        "disclaimer": (
            "Downstream utility measures whether models trained on synthetic data "
            "preserve useful statistical signal when evaluated on held-out real data. "
            "This does not imply that synthetic data is clinically equivalent to real data."
        ),
    }
