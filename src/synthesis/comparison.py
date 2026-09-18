"""Model comparison lab — trains and evaluates multiple synthesizers."""
import time
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.synthesis.synthesizer import train_synthesizer, save_synthesizer, generate_samples
from src.validation.engine import validate_profiles, compute_fidelity_summary, validate_longitudinal
from src.privacy.evaluator import detect_exact_duplicates, nearest_neighbor_analysis
from src.utils.config import MODELS_DIR, RANDOM_SEED

warnings.filterwarnings("ignore", category=FutureWarning, module="sdv")


def compare_models(
    train_df: pd.DataFrame,
    original_profiles: pd.DataFrame,
    model_types: list[str] | None = None,
    n_eval_samples: int = 500,
    epochs: int = 50,
    batch_size: int = 500,
    seed: int = RANDOM_SEED,
) -> dict:
    if model_types is None:
        model_types = ["CTGANSynthesizer", "GaussianCopulaSynthesizer"]

    results = {}

    for synth_type in model_types:
        entry = {
            "synth_type": synth_type,
            "training_success": False,
            "error": None,
        }

        try:
            start = time.time()
            synthesizer, info = train_synthesizer(
                train_df, synth_type=synth_type,
                epochs=epochs, batch_size=batch_size, seed=seed,
            )
            train_time = round(time.time() - start, 2)
            entry["train_time_seconds"] = train_time

            model_filename = f"comparison_{synth_type.lower()}.pkl"
            model_path = save_synthesizer(synthesizer, filename=model_filename)
            try:
                entry["model_size_kb"] = round(os.path.getsize(model_path) / 1024, 1)
            except OSError:
                entry["model_size_kb"] = None

            gen_start = time.time()
            synthetic = generate_samples(synthesizer, n_eval_samples, seed=seed)
            gen_time = round(time.time() - gen_start, 2)
            entry["generation_time_seconds"] = gen_time
            entry["training_success"] = True

            profile_results = validate_profiles(original_profiles, synthetic)
            fidelity = compute_fidelity_summary(profile_results, {"numerical": {}})

            entry["fidelity_score"] = fidelity["overall_fidelity"]

            corr_data = profile_results.get("correlation", {})
            entry["correlation_preservation"] = round(
                1.0 - corr_data.get("mean_absolute_correlation_difference", 1.0), 4
            ) if isinstance(corr_data.get("mean_absolute_correlation_difference"), (int, float)) else None

            ks_values = []
            for col, data in profile_results.get("numerical", {}).items():
                ks_values.append(data["ks_test"]["ks_statistic"])
            entry["mean_ks_statistic"] = round(float(np.mean(ks_values)), 4) if ks_values else None
            entry["ks_similarity"] = round(1.0 - float(np.mean(ks_values)), 4) if ks_values else None

            dup_result = detect_exact_duplicates(original_profiles, synthetic)
            entry["exact_duplicates"] = dup_result["exact_duplicates"]

            nn_result = nearest_neighbor_analysis(original_profiles, synthetic, sample_size=min(200, n_eval_samples))
            entry["median_nn_distance"] = nn_result.get("median_distance")
            entry["near_copy_count"] = nn_result.get("near_copy_count", 0)

            entry["synthesizer"] = synthesizer
            entry["synthetic_sample"] = synthetic
            entry["train_info"] = info

        except Exception as e:
            entry["error"] = str(e)
            entry["synthesizer"] = None
            entry["synthetic_sample"] = None

        results[synth_type] = entry

    return results


def format_comparison_table(results: dict) -> pd.DataFrame:
    rows = []
    for synth_type, data in results.items():
        label = synth_type.replace("Synthesizer", "")
        if not data["training_success"]:
            rows.append({
                "Model": label,
                "Status": f"Failed: {data.get('error', 'Unknown')}",
            })
            continue

        rows.append({
            "Model": label,
            "Status": "Trained",
            "KS Similarity": data.get("ks_similarity"),
            "Corr Preservation": data.get("correlation_preservation"),
            "Fidelity Score": data.get("fidelity_score"),
            "Train Time (s)": data.get("train_time_seconds"),
            "Gen Time (s)": data.get("generation_time_seconds"),
            "Model Size (KB)": data.get("model_size_kb"),
            "Exact Duplicates": data.get("exact_duplicates"),
            "Near Copies": data.get("near_copy_count"),
            "Median NN Dist": data.get("median_nn_distance"),
        })

    return pd.DataFrame(rows)
