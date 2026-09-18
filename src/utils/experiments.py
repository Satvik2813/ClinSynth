"""Lightweight experiment history using JSON files."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.config import EXPERIMENTS_DIR


def _ensure_dir():
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


def save_experiment(
    model: str,
    num_patients: int,
    timeline_days: int,
    constraints: dict,
    privacy_mode: str,
    seed: int,
    trajectory_dist: dict,
    fidelity_summary: dict | None = None,
    privacy_summary: dict | None = None,
    model_comparison: dict | None = None,
) -> dict:
    _ensure_dir()
    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    experiment = {
        "experiment_id": exp_id,
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "num_patients": num_patients,
        "timeline_days": timeline_days,
        "constraints": constraints,
        "privacy_mode": privacy_mode,
        "seed": seed,
        "trajectory_dist": trajectory_dist,
        "fidelity_summary": fidelity_summary,
        "privacy_summary": privacy_summary,
        "model_comparison": model_comparison,
    }

    path = EXPERIMENTS_DIR / f"{exp_id}.json"
    with open(path, "w") as f:
        json.dump(experiment, f, indent=2, default=str)

    return experiment


def list_experiments() -> list[dict]:
    _ensure_dir()
    experiments = []
    for p in sorted(EXPERIMENTS_DIR.glob("exp_*.json"), reverse=True):
        try:
            with open(p) as f:
                exp = json.load(f)
                experiments.append(exp)
        except (json.JSONDecodeError, IOError):
            continue
    return experiments


def load_experiment(exp_id: str) -> dict | None:
    _ensure_dir()
    path = EXPERIMENTS_DIR / f"{exp_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def delete_experiment(exp_id: str) -> bool:
    path = EXPERIMENTS_DIR / f"{exp_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
