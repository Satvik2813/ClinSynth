"""Synthetic data generation using SDV synthesizers."""
import time
import warnings
from pathlib import Path

import pandas as pd
from sdv.metadata import SingleTableMetadata
from sdv.single_table import CTGANSynthesizer, GaussianCopulaSynthesizer

from src.utils.config import MODELS_DIR, RANDOM_SEED

warnings.filterwarnings("ignore", category=FutureWarning, module="sdv")


def build_metadata(df: pd.DataFrame) -> SingleTableMetadata:
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(df)

    if "patient_id" in df.columns:
        metadata.update_column("patient_id", sdtype="id")
        metadata.set_primary_key("patient_id")

    for col in ["gender"]:
        if col in df.columns:
            metadata.update_column(col, sdtype="categorical")
    for col in ["diabetes", "hypertension"]:
        if col in df.columns:
            metadata.update_column(col, sdtype="categorical")

    return metadata


def train_synthesizer(
    df: pd.DataFrame,
    synth_type: str = "CTGANSynthesizer",
    epochs: int = 100,
    batch_size: int = 500,
    seed: int = RANDOM_SEED,
) -> tuple:
    metadata = build_metadata(df)
    start_time = time.time()

    if synth_type == "CTGANSynthesizer":
        synthesizer = CTGANSynthesizer(
            metadata,
            epochs=epochs,
            batch_size=min(batch_size, len(df)),
            verbose=True,
        )
    else:
        synthesizer = GaussianCopulaSynthesizer(metadata)

    synthesizer.fit(df)
    duration = time.time() - start_time

    info = {
        "synth_type": synth_type,
        "epochs": epochs if synth_type == "CTGANSynthesizer" else None,
        "training_rows": len(df),
        "training_columns": len(df.columns),
        "duration_seconds": round(duration, 2),
    }

    return synthesizer, info


def save_synthesizer(synthesizer, filename: str = "synthesizer.pkl") -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / filename
    synthesizer.save(str(path))
    return path


def load_synthesizer(filename: str = "synthesizer.pkl"):
    path = MODELS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")

    try:
        return CTGANSynthesizer.load(str(path))
    except Exception:
        return GaussianCopulaSynthesizer.load(str(path))


def generate_samples(synthesizer, n_samples: int, seed: int = RANDOM_SEED) -> pd.DataFrame:
    return synthesizer.sample(num_rows=n_samples)
