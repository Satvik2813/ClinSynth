"""Test suite for ClinSynth."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import numpy as np

from src.data.demo_generator import generate_demo_profiles, generate_demo_longitudinal
from src.data.loader import detect_dataset_type, get_data_summary
from src.preprocessing.pipeline import (
    preprocess_profiles, preprocess_longitudinal, validate_bounds, detect_column_types,
)
from src.cohort.builder import build_cohort, _adjust_binary_column
from src.temporal.generator import TemporalEngine
from src.validation.engine import (
    compute_numerical_stats, ks_test, wasserstein_distance,
    categorical_comparison, correlation_comparison, validate_profiles,
    validate_longitudinal, compute_fidelity_summary,
)
from src.privacy.evaluator import detect_exact_duplicates, nearest_neighbor_analysis, privacy_screening
from src.utils.export import export_csv, export_json, create_export_zip
from src.utils.config import BOUNDS


# --- Demo Data Generation ---

class TestDemoDataGeneration:
    def test_generate_profiles_count(self):
        df = generate_demo_profiles(100)
        assert len(df) == 100

    def test_generate_profiles_columns(self):
        df = generate_demo_profiles(50)
        assert set(df.columns) == {"patient_id", "age", "gender", "bmi", "diabetes", "hypertension"}

    def test_generate_profiles_deterministic(self):
        df1 = generate_demo_profiles(50, seed=42)
        df2 = generate_demo_profiles(50, seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_profile_bounds(self):
        df = generate_demo_profiles(200)
        assert df["age"].between(*BOUNDS["age"]).all()
        assert df["bmi"].between(*BOUNDS["bmi"]).all()
        assert set(df["diabetes"].unique()).issubset({0, 1})
        assert set(df["hypertension"].unique()).issubset({0, 1})
        assert set(df["gender"].unique()).issubset({"M", "F"})

    def test_generate_longitudinal(self):
        profiles = generate_demo_profiles(20)
        long = generate_demo_longitudinal(profiles, days=10)
        assert len(long) == 20 * 10
        assert "patient_id" in long.columns
        assert "day" in long.columns

    def test_longitudinal_bounds(self):
        profiles = generate_demo_profiles(30)
        long = generate_demo_longitudinal(profiles, days=5)
        assert long["systolic_bp"].between(*BOUNDS["systolic_bp"]).all()
        assert long["diastolic_bp"].between(*BOUNDS["diastolic_bp"]).all()
        assert long["steps"].between(*BOUNDS["steps"]).all()
        assert long["medication_adherence"].between(*BOUNDS["medication_adherence"]).all()
        assert long["pain_score"].between(*BOUNDS["pain_score"]).all()

    def test_unique_patient_ids(self):
        df = generate_demo_profiles(100)
        assert df["patient_id"].nunique() == 100


# --- Preprocessing ---

class TestPreprocessing:
    def test_validate_bounds(self):
        df = pd.DataFrame({"age": [150, -5, 50], "bmi": [100, 5, 25]})
        result = validate_bounds(df)
        assert result["age"].max() <= BOUNDS["age"][1]
        assert result["age"].min() >= BOUNDS["age"][0]

    def test_detect_column_types(self):
        df = pd.DataFrame({
            "patient_id": ["A", "B"],
            "age": [30, 40],
            "gender": ["M", "F"],
            "diabetes": [0, 1],
        })
        types = detect_column_types(df)
        assert types["patient_id"] == "id"
        assert types["age"] in ("numerical", "categorical")
        assert types["gender"] == "categorical"
        assert types["diabetes"] == "boolean"

    def test_preprocess_profiles(self):
        df = pd.DataFrame({
            "patient_id": ["P1"],
            "age": [None],
            "gender": ["male"],
            "bmi": [25.0],
            "diabetes": [None],
            "hypertension": [1],
        })
        result = preprocess_profiles(df)
        assert result["diabetes"].iloc[0] == 0
        assert result["gender"].iloc[0] == "M"


# --- Dataset Detection ---

class TestDatasetDetection:
    def test_detect_profile(self):
        df = pd.DataFrame({"age": [1], "gender": ["M"], "bmi": [25], "diabetes": [0], "hypertension": [0]})
        assert detect_dataset_type(df) == "profile"

    def test_detect_longitudinal(self):
        df = pd.DataFrame({"patient_id": [1], "day": [1], "systolic_bp": [120], "diastolic_bp": [80], "steps": [5000]})
        assert detect_dataset_type(df) == "longitudinal"


# --- Cohort Builder ---

class TestCohortBuilder:
    @pytest.fixture
    def raw_profiles(self):
        return generate_demo_profiles(300)

    def test_cohort_size(self, raw_profiles):
        cohort, stats = build_cohort(raw_profiles, num_patients=100)
        assert len(cohort) == 100

    def test_cohort_unique_ids(self, raw_profiles):
        cohort, _ = build_cohort(raw_profiles, num_patients=100)
        assert cohort["patient_id"].nunique() == 100
        assert all(pid.startswith("SYN-") for pid in cohort["patient_id"])

    def test_cohort_constraints_approximate(self, raw_profiles):
        cohort, stats = build_cohort(
            raw_profiles, num_patients=200,
            elderly_pct=0.40, diabetes_pct=0.30, hypertension_pct=0.25,
        )
        assert abs(stats["actual_elderly_pct"] - 0.40) < 0.10
        assert abs(stats["actual_diabetes_pct"] - 0.30) < 0.10
        assert abs(stats["actual_hypertension_pct"] - 0.25) < 0.10

    def test_adjust_binary_column(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"col": [0] * 80 + [1] * 20})
        result = _adjust_binary_column(df, "col", 0.50, rng)
        assert abs(result["col"].mean() - 0.50) < 0.05


# --- Temporal Engine ---

class TestTemporalEngine:
    def test_generate_journeys(self):
        cohort = pd.DataFrame({
            "patient_id": ["SYN-000001", "SYN-000002"],
            "age": [65, 30],
            "gender": ["M", "F"],
            "bmi": [28, 22],
            "diabetes": [1, 0],
            "hypertension": [1, 0],
        })
        engine = TemporalEngine(seed=42)
        result = engine.generate_journeys(cohort, days=10)
        assert len(result) == 20
        assert set(result["patient_id"].unique()) == {"SYN-000001", "SYN-000002"}
        assert result["day"].min() == 1
        assert result["day"].max() == 10

    def test_journey_bounds(self):
        cohort = pd.DataFrame({
            "patient_id": [f"SYN-{i:06d}" for i in range(10)],
            "age": [50] * 10, "gender": ["M"] * 10,
            "bmi": [25] * 10, "diabetes": [0] * 10, "hypertension": [0] * 10,
        })
        engine = TemporalEngine(seed=42)
        result = engine.generate_journeys(cohort, days=30)
        assert result["systolic_bp"].between(*BOUNDS["systolic_bp"]).all()
        assert result["diastolic_bp"].between(*BOUNDS["diastolic_bp"]).all()
        assert result["steps"].between(*BOUNDS["steps"]).all()
        assert result["medication_adherence"].between(*BOUNDS["medication_adherence"]).all()
        assert result["pain_score"].between(*BOUNDS["pain_score"]).all()

    def test_learn_from_data(self):
        profiles = generate_demo_profiles(50)
        long = generate_demo_longitudinal(profiles, days=5)
        engine = TemporalEngine()
        engine.learn_from_data(profiles, long)
        assert engine.learned_params is not None
        assert "systolic_bp" in engine.learned_params


# --- Validation ---

class TestValidation:
    def test_compute_numerical_stats(self):
        orig = pd.Series(np.random.normal(120, 10, 100))
        synth = pd.Series(np.random.normal(121, 11, 100))
        result = compute_numerical_stats(orig, synth)
        assert "original_mean" in result
        assert "synthetic_mean" in result

    def test_ks_test(self):
        orig = pd.Series(np.random.normal(0, 1, 500))
        synth = pd.Series(np.random.normal(0, 1, 500))
        result = ks_test(orig, synth)
        assert 0 <= result["ks_statistic"] <= 1

    def test_categorical_comparison(self):
        orig = pd.Series(["M", "F", "M", "F", "M"])
        synth = pd.Series(["M", "F", "F", "F", "M"])
        result = categorical_comparison(orig, synth)
        assert "total_variation_distance" in result
        assert result["total_variation_distance"] >= 0

    def test_correlation_comparison(self):
        df1 = pd.DataFrame({"a": np.random.randn(100), "b": np.random.randn(100)})
        df2 = pd.DataFrame({"a": np.random.randn(100), "b": np.random.randn(100)})
        result = correlation_comparison(df1, df2)
        assert "mean_absolute_correlation_difference" in result

    def test_fidelity_summary(self):
        profile_r = {
            "numerical": {"age": {"ks_test": {"ks_statistic": 0.05}}},
            "categorical": {"gender": {"total_variation_distance": 0.02}},
            "correlation": {"mean_absolute_correlation_difference": 0.03},
        }
        long_r = {
            "numerical": {"systolic_bp": {"ks_test": {"ks_statistic": 0.08}}},
        }
        result = compute_fidelity_summary(profile_r, long_r)
        assert 0 <= result["overall_fidelity"] <= 1
        assert result["component_count"] > 0


# --- Privacy ---

class TestPrivacy:
    def test_detect_exact_duplicates_none(self):
        orig = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        synth = pd.DataFrame({"a": [7, 8, 9], "b": [10, 11, 12]})
        result = detect_exact_duplicates(orig, synth)
        assert result["exact_duplicates"] == 0

    def test_detect_exact_duplicates_found(self):
        orig = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        synth = pd.DataFrame({"a": [1, 8, 9], "b": [4, 11, 12]})
        result = detect_exact_duplicates(orig, synth)
        assert result["exact_duplicates"] == 1

    def test_nearest_neighbor_analysis(self):
        orig = pd.DataFrame({"a": np.random.randn(50), "b": np.random.randn(50)})
        synth = pd.DataFrame({"a": np.random.randn(30), "b": np.random.randn(30)})
        result = nearest_neighbor_analysis(orig, synth, sample_size=20)
        assert "mean_distance" in result
        assert result["mean_distance"] > 0

    def test_privacy_screening(self):
        orig = pd.DataFrame({"a": np.random.randn(50), "b": np.random.randn(50)})
        synth = pd.DataFrame({"a": np.random.randn(30) + 5, "b": np.random.randn(30) + 5})
        result = privacy_screening(orig, synth)
        assert "overall_status" in result
        assert len(result["checks"]) >= 2


# --- Export ---

class TestExport:
    def test_export_csv(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = export_csv(df)
        assert isinstance(result, bytes)
        assert b"a,b" in result

    def test_export_json(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = export_json(df)
        assert isinstance(result, bytes)

    def test_create_export_zip(self):
        profiles = pd.DataFrame({"patient_id": ["SYN-1"], "age": [50]})
        long = pd.DataFrame({"patient_id": ["SYN-1"], "day": [1], "systolic_bp": [120]})
        result = create_export_zip(profiles, long, n_patients=1, days=1)
        assert isinstance(result, bytes)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
