"""Reproducible ClinSynth benchmark runner.

Run from repository root:
    python scripts/run_benchmarks.py

Outputs:
    artifacts/reports/benchmark_results.json
"""
from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from src.data.loader import load_demo_dataset
from src.preprocessing.pipeline import preprocess_profiles, preprocess_longitudinal
from src.synthesis.synthesizer import train_synthesizer, generate_samples
from src.temporal.generator import TemporalEngine
from src.validation.engine import validate_profiles
from src.privacy.evaluator import privacy_screening
from src.cohort.builder import build_cohort

OUT = Path("artifacts/reports/benchmark_results.json")


def measure(fn):
    tracemalloc.start()
    start = time.perf_counter()
    result = fn()
    wall = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, {"wall_seconds": round(wall, 3), "peak_memory_mb": round(peak / 1024 / 1024, 2)}


def main():
    profiles, longitudinal = load_demo_dataset()
    profiles = preprocess_profiles(profiles)
    longitudinal = preprocess_longitudinal(longitudinal)
    train_df = profiles.drop(columns=["patient_id"], errors="ignore")

    results = {}

    gaussian, metrics = measure(lambda: train_synthesizer(train_df, synth_type="GaussianCopulaSynthesizer"))
    gaussian_model, gaussian_info = gaussian
    results["gaussian_train"] = {**metrics, **gaussian_info}

    for n in (1000, 5000):
        _, m = measure(lambda n=n: generate_samples(gaussian_model, n))
        results[f"gaussian_generate_{n}"] = m

    ctgan, metrics = measure(lambda: train_synthesizer(train_df, synth_type="CTGANSynthesizer", epochs=50))
    ctgan_model, ctgan_info = ctgan
    results["ctgan_demo_train"] = {**metrics, **ctgan_info}
    _, m = measure(lambda: generate_samples(ctgan_model, 1000))
    results["ctgan_generate_1000"] = m

    raw = generate_samples(gaussian_model, 25000)
    for n in (1000, 5000):
        cohort, _ = build_cohort(raw, num_patients=n, seed=42)
        engine = TemporalEngine(seed=42)
        engine.learn_from_data(profiles, longitudinal)
        synth_long, m = measure(lambda cohort=cohort: engine.generate_journeys(cohort, days=30))
        results[f"temporal_{n}x30"] = {**m, "rows": len(synth_long)}

        _, m = measure(lambda cohort=cohort: validate_profiles(profiles, cohort))
        results[f"validation_{n}"] = m

        _, m = measure(lambda cohort=cohort: privacy_screening(profiles, cohort))
        results[f"privacy_{n}"] = m

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
