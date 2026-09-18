"""All ClinSynth API routes."""
from __future__ import annotations

import io
import time
import traceback

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from backend.app.schemas.models import (
    HealthResponse, DataSummary, TrainRequest, TrainStatus,
    CohortRequest, CohortSummary, ModelCompareRequest, ErrorResponse,
    UtilityRequest, UtilityResponse,
)
from backend.app.services.state import state

from src.data.loader import load_demo_dataset, detect_dataset_type, map_schema, get_data_summary
from src.preprocessing.pipeline import preprocess_profiles, preprocess_longitudinal, get_quality_report
from src.preprocessing.guardrails import check_plausibility, repair_profiles, repair_longitudinal
from src.synthesis.synthesizer import train_synthesizer, save_synthesizer, generate_samples
from src.synthesis.comparison import compare_models, format_comparison_table
from src.cohort.builder import build_cohort
from src.temporal.generator import TemporalEngine
from src.validation.engine import (
    validate_profiles, validate_longitudinal, compute_fidelity_summary,
    compute_per_column_quality, compute_all_subgroup_fidelity,
)
from src.privacy.evaluator import (
    privacy_screening, apply_privacy_mode, nearest_neighbor_analysis, detect_exact_duplicates,
)
from src.research.utility import compute_tstr_utility
from src.research.subgroups import compute_source_subgroups, compute_rare_cohort_amplification
from src.utils.export import export_csv, export_json, create_export_zip, create_quality_report
from src.utils.config import RESEARCH_PRESETS, PRIVACY_MODES, DEFAULT_TRAJECTORY_DIST, RANDOM_SEED
from src.utils.experiments import save_experiment, list_experiments, load_experiment

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


# ── Data ──────────────────────────────────────────────────────────────────

@router.post("/data/demo")
def load_demo():
    profiles, longitudinal = load_demo_dataset()
    state.profiles = profiles
    state.longitudinal = longitudinal
    state.profiles_processed = preprocess_profiles(profiles)
    state.longitudinal_processed = preprocess_longitudinal(longitudinal)
    state.synthesizer = None
    state.train_info = None
    state.synthetic_profiles = None
    state.synthetic_longitudinal = None
    state.model_comparison_results = None
    state.clear_cohort_results()
    return _data_summary()


@router.post("/data/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are accepted")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse CSV: {e}")

    dtype = detect_dataset_type(df)
    df = map_schema(df, dtype)

    if dtype == "profile":
        state.profiles = df
        state.profiles_processed = preprocess_profiles(df)
        if state.longitudinal is None:
            return {**_data_summary(), "warning": "No longitudinal data loaded yet. Temporal features will use generated data."}
    elif dtype == "longitudinal":
        state.longitudinal = df
        state.longitudinal_processed = preprocess_longitudinal(df)
        if state.profiles is None:
            return {**_data_summary(), "warning": "No profile data loaded yet. Please also upload a profile dataset."}
    else:
        raise HTTPException(400, "Could not determine dataset type. Ensure columns match the expected schema.")

    return _data_summary()


@router.get("/data/summary")
def data_summary():
    if not state.data_loaded:
        raise HTTPException(404, "No dataset loaded")
    return _data_summary()


def _data_summary() -> dict:
    profiles = state.profiles_processed
    longitudinal = state.longitudinal_processed
    quality = get_quality_report(profiles) if profiles is not None else {}

    return {
        "n_patients": len(profiles) if profiles is not None else 0,
        "n_longitudinal_records": len(longitudinal) if longitudinal is not None else 0,
        "profile_columns": list(profiles.columns) if profiles is not None else [],
        "longitudinal_columns": list(longitudinal.columns) if longitudinal is not None else [],
        "profile_missing": profiles.isnull().sum().to_dict() if profiles is not None else {},
        "longitudinal_missing": longitudinal.isnull().sum().to_dict() if longitudinal is not None else {},
        "profile_dtypes": profiles.dtypes.astype(str).to_dict() if profiles is not None else {},
        "longitudinal_dtypes": longitudinal.dtypes.astype(str).to_dict() if longitudinal is not None else {},
        "column_types": quality.get("column_types"),
        "profile_stats": profiles.describe().to_dict() if profiles is not None else None,
        "profile_preview": profiles.head(20).to_dict(orient="records") if profiles is not None else [],
        "longitudinal_preview": longitudinal.head(20).to_dict(orient="records") if longitudinal is not None else [],
    }


# ── Train ─────────────────────────────────────────────────────────────────

@router.post("/train")
def train_model(req: TrainRequest):
    if not state.data_loaded:
        raise HTTPException(400, "No dataset loaded")

    profiles = state.profiles_processed
    train_df = profiles.drop(columns=["patient_id"], errors="ignore")

    epoch_map = {"Demo (fast)": 50, "Standard": 150, "High Quality": 300}
    epochs = epoch_map.get(req.mode, req.epochs)
    if req.mode not in epoch_map:
        epochs = req.epochs

    try:
        synthesizer, info = train_synthesizer(
            train_df, synth_type=req.synth_type,
            epochs=epochs, batch_size=req.batch_size,
        )
        save_synthesizer(synthesizer)
        state.synthesizer = synthesizer
        state.train_info = info
        state.synthetic_profiles = None
        state.synthetic_longitudinal = None
        state.clear_cohort_results()
        return {"status": "success", **info}
    except Exception as e:
        if req.synth_type == "CTGANSynthesizer":
            try:
                synthesizer, info = train_synthesizer(train_df, synth_type="GaussianCopulaSynthesizer")
                save_synthesizer(synthesizer)
                state.synthesizer = synthesizer
                state.train_info = info
                return {"status": "fallback", "message": f"CTGAN failed ({e}), used Gaussian Copula", **info}
            except Exception as e2:
                raise HTTPException(500, f"Training failed: {e2}")
        raise HTTPException(500, f"Training failed: {e}")


@router.get("/train/status")
def train_status():
    return {
        "trained": state.model_trained,
        "info": state.train_info,
    }


# ── Model Comparison ──────────────────────────────────────────────────────

@router.post("/models/compare")
def compare_models_endpoint(req: ModelCompareRequest):
    if not state.data_loaded:
        raise HTTPException(400, "No dataset loaded")

    profiles = state.profiles_processed
    train_df = profiles.drop(columns=["patient_id"], errors="ignore")

    try:
        results = compare_models(
            train_df, profiles,
            model_types=["CTGANSynthesizer", "GaussianCopulaSynthesizer"],
            n_eval_samples=req.n_eval_samples,
            epochs=req.epochs,
            seed=state.current_seed,
        )

        serializable = {}
        for k, v in results.items():
            entry = {key: val for key, val in v.items() if key not in ("synthesizer", "synthetic_sample")}
            serializable[k] = entry

        state.model_comparison_results = results
        comp_df = format_comparison_table(results)

        return {
            "comparison": serializable,
            "table": comp_df.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(500, f"Model comparison failed: {e}")


@router.post("/models/select/{model_name}")
def select_model(model_name: str):
    if state.model_comparison_results is None:
        raise HTTPException(400, "Run model comparison first")

    full_name = model_name if model_name.endswith("Synthesizer") else f"{model_name}Synthesizer"
    entry = state.model_comparison_results.get(full_name)
    if not entry or not entry.get("training_success"):
        raise HTTPException(404, f"Model {model_name} not found or failed training")

    state.synthesizer = entry["synthesizer"]
    state.train_info = entry["train_info"]
    state.synthetic_profiles = None
    state.synthetic_longitudinal = None
    state.clear_cohort_results()
    save_synthesizer(entry["synthesizer"])
    return {"status": "selected", "model": full_name}


# ── Cohort Generation ─────────────────────────────────────────────────────

@router.post("/cohort/generate")
def generate_cohort(req: CohortRequest):
    if not state.model_trained:
        raise HTTPException(400, "No model trained")

    state.current_seed = req.seed
    state.privacy_mode = req.privacy_mode
    state.trajectory_dist = req.trajectory_dist

    if req.preset and req.preset in RESEARCH_PRESETS:
        preset = RESEARCH_PRESETS[req.preset]
        req.elderly_pct = preset["elderly_pct"]
        req.diabetes_pct = preset["diabetes_pct"]
        req.hypertension_pct = preset["hypertension_pct"]
        req.htn_among_diabetic_pct = preset["htn_among_diabetic_pct"]
        req.diabetes_among_elderly_pct = preset["diabetes_among_elderly_pct"]
        req.trajectory_dist = preset["trajectory_dist"]
        state.trajectory_dist = preset["trajectory_dist"]

    raw = generate_samples(state.synthesizer, req.num_patients * 5)
    cohort, stats = build_cohort(
        raw, num_patients=req.num_patients,
        elderly_pct=req.elderly_pct, diabetes_pct=req.diabetes_pct,
        hypertension_pct=req.hypertension_pct,
        htn_among_diabetic_pct=req.htn_among_diabetic_pct,
        diabetes_among_elderly_pct=req.diabetes_among_elderly_pct,
        seed=req.seed,
    )

    if req.privacy_mode != "low":
        orig = state.profiles_processed
        cohort, priv_stats = apply_privacy_mode(cohort, orig, mode=req.privacy_mode, seed=req.seed)
        if len(cohort) < req.num_patients:
            stats["privacy_filter_note"] = f"Privacy filtering reduced cohort from {req.num_patients} to {len(cohort)}"
        cohort["patient_id"] = [f"SYN-{i+1:06d}" for i in range(len(cohort))]
        stats["privacy_filter_stats"] = priv_stats

    cohort = repair_profiles(cohort)

    engine = TemporalEngine(seed=req.seed)
    if state.profiles_processed is not None and state.longitudinal_processed is not None:
        engine.learn_from_data(state.profiles_processed, state.longitudinal_processed)
    synth_long = engine.generate_journeys(cohort, days=req.timeline_days, trajectory_dist=req.trajectory_dist)
    synth_long = repair_longitudinal(synth_long)

    plaus = check_plausibility(cohort, synth_long)

    cohort_config = {
        "num_patients": len(cohort),
        "timeline_days": req.timeline_days,
        "elderly_pct": req.elderly_pct,
        "diabetes_pct": req.diabetes_pct,
        "hypertension_pct": req.hypertension_pct,
        "htn_among_diabetic_pct": req.htn_among_diabetic_pct,
        "diabetes_among_elderly_pct": req.diabetes_among_elderly_pct,
        "privacy_mode": req.privacy_mode,
        "seed": req.seed,
        "trajectory_dist": req.trajectory_dist,
        "preset": req.preset,
    }

    state.synthetic_profiles = cohort
    state.synthetic_longitudinal = synth_long
    state.cohort_stats = stats
    state.cohort_config = cohort_config
    state.plausibility_stats = plaus
    state.clear_cohort_results()

    traj_counts = {}
    if "trajectory_type" in synth_long.columns:
        traj_series = synth_long.groupby("patient_id")["trajectory_type"].first().value_counts()
        traj_counts = traj_series.to_dict()

    return {
        "total_patients": stats["total_patients"],
        "timeline_days": req.timeline_days,
        "longitudinal_records": len(synth_long),
        "constraints": stats.get("constraints", []),
        "trajectory_distribution": traj_counts,
        "plausibility_stats": plaus,
        "cohort_config": cohort_config,
        "profile_preview": cohort.head(20).to_dict(orient="records"),
    }


@router.get("/cohort/current")
def get_current_cohort():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")
    cohort = state.synthetic_profiles
    synth_long = state.synthetic_longitudinal
    stats = state.cohort_stats

    traj_counts = {}
    if "trajectory_type" in synth_long.columns:
        traj_series = synth_long.groupby("patient_id")["trajectory_type"].first().value_counts()
        traj_counts = traj_series.to_dict()

    return {
        "total_patients": len(cohort),
        "timeline_days": int(synth_long["day"].max()),
        "longitudinal_records": len(synth_long),
        "constraints": stats.get("constraints", []),
        "trajectory_distribution": traj_counts,
        "plausibility_stats": state.plausibility_stats,
        "cohort_config": state.cohort_config,
        "profile_preview": cohort.head(20).to_dict(orient="records"),
    }


# ── Patient Journeys ──────────────────────────────────────────────────────

@router.get("/journeys/{patient_id}")
def get_journey(patient_id: str):
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")

    cohort = state.synthetic_profiles
    synth_long = state.synthetic_longitudinal

    p_row = cohort[cohort["patient_id"] == patient_id]
    if len(p_row) == 0:
        raise HTTPException(404, f"Patient {patient_id} not found")
    p_row = p_row.iloc[0]

    p_data = synth_long[synth_long["patient_id"] == patient_id].sort_values("day")

    demographics = {
        "patient_id": patient_id,
        "age": _to_native(p_row.get("age")),
        "gender": str(p_row.get("gender", "N/A")),
        "bmi": _to_native(p_row.get("bmi")),
        "diabetes": bool(p_row.get("diabetes", 0)),
        "hypertension": bool(p_row.get("hypertension", 0)),
        "trajectory_type": str(p_data["trajectory_type"].iloc[0]).title() if "trajectory_type" in p_data.columns and len(p_data) > 0 else None,
    }

    journey = p_data.to_dict(orient="records")
    for row in journey:
        for k, v in row.items():
            row[k] = _to_native(v)

    metrics = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]
    available = [m for m in metrics if m in p_data.columns]
    stats = []
    for m in available:
        vals = p_data[m]
        stats.append({
            "metric": m.replace("_", " ").title(),
            "baseline": round(float(vals.iloc[0]), 2) if len(vals) > 0 else None,
            "final": round(float(vals.iloc[-1]), 2) if len(vals) > 0 else None,
            "change": round(float(vals.iloc[-1] - vals.iloc[0]), 2) if len(vals) > 1 else None,
            "mean": round(float(vals.mean()), 2),
            "min": round(float(vals.min()), 2),
            "max": round(float(vals.max()), 2),
        })

    cohort_daily = synth_long.groupby("day")[available].mean().reset_index()
    cohort_avg = cohort_daily.to_dict(orient="records")
    for row in cohort_avg:
        for k, v in row.items():
            row[k] = _to_native(v)

    return {
        "demographics": demographics,
        "journey": journey,
        "stats": stats,
        "cohort_average": cohort_avg,
    }


@router.get("/journeys")
def list_patients():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")
    ids = state.synthetic_profiles["patient_id"].tolist()
    return {"patient_ids": ids[:200]}


# ── Validation ────────────────────────────────────────────────────────────

@router.get("/validation")
def get_validation():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")

    if state.fidelity_summary is None:
        orig_profiles = state.profiles_processed
        synth_profiles = state.synthetic_profiles
        orig_long = state.longitudinal_processed
        synth_long = state.synthetic_longitudinal

        profile_results = validate_profiles(orig_profiles, synth_profiles)
        long_results = validate_longitudinal(orig_long, synth_long)
        fidelity = compute_fidelity_summary(profile_results, long_results)
        per_col = compute_per_column_quality(orig_profiles, synth_profiles)
        subgroup = compute_all_subgroup_fidelity(orig_profiles, synth_profiles)

        state.validation_profile_results = profile_results
        state.validation_long_results = long_results
        state.fidelity_summary = fidelity
        state.per_column_quality = per_col
        state.subgroup_fidelity = subgroup

    return {
        "fidelity_summary": state.fidelity_summary,
        "profile_results": _make_serializable(state.validation_profile_results),
        "longitudinal_results": _make_serializable(state.validation_long_results),
        "per_column_quality": state.per_column_quality,
        "subgroup_fidelity": state.subgroup_fidelity,
    }


# ── Privacy ───────────────────────────────────────────────────────────────

@router.get("/privacy")
def get_privacy():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")

    if state.privacy_results is None:
        orig = state.profiles_processed
        synth = state.synthetic_profiles
        state.privacy_results = privacy_screening(orig, synth)

    results = state.privacy_results
    safe = dict(results)
    if "nearest_neighbor" in safe:
        nn = dict(safe["nearest_neighbor"])
        nn.pop("distances", None)
        safe["nearest_neighbor"] = nn

    return safe


@router.post("/privacy/compare")
def privacy_fidelity_compare():
    if not state.cohort_generated:
        raise HTTPException(400, "No cohort generated")

    orig = state.profiles_processed
    synth = state.synthetic_profiles
    seed = state.current_seed

    pf_results = []
    for mode in ["low", "balanced", "high"]:
        filtered, filter_stats = apply_privacy_mode(synth.copy(), orig, mode=mode, seed=seed)
        profile_results = validate_profiles(orig, filtered)
        fidelity = compute_fidelity_summary(profile_results, {"numerical": {}})
        nn = nearest_neighbor_analysis(orig, filtered, sample_size=min(200, len(filtered)))

        pf_results.append({
            "mode": mode,
            "fidelity_score": fidelity["overall_fidelity"],
            "median_nn_distance": nn.get("median_distance", 0),
            "exact_duplicates": detect_exact_duplicates(orig, filtered)["exact_duplicates"],
            "near_copy_count": nn.get("near_copy_count", 0),
            "correlation_diff": profile_results.get("correlation", {}).get(
                "mean_absolute_correlation_difference", None),
            "records_after_filter": len(filtered),
            "records_rejected": filter_stats.get("records_rejected", 0),
        })

    state.privacy_fidelity_results = pf_results
    return {"results": pf_results}


# ── Source Subgroups / Rare Cohort ────────────────────────────────────────

@router.get("/cohort/source-subgroups")
def get_source_subgroups():
    if not state.data_loaded:
        raise HTTPException(404, "No dataset loaded")
    return compute_source_subgroups(state.profiles_processed)


@router.get("/cohort/rare-amplification")
def get_rare_amplification():
    if not state.data_loaded:
        raise HTTPException(404, "No dataset loaded")
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")
    return {
        "amplification": compute_rare_cohort_amplification(
            state.profiles_processed, state.synthetic_profiles,
        )
    }


# ── Research Utility ─────────────────────────────────────────────────────

@router.post("/research/utility")
def research_utility(req: UtilityRequest):
    if not state.data_loaded:
        raise HTTPException(400, "No dataset loaded")
    if not state.cohort_generated:
        raise HTTPException(400, "No cohort generated")

    result = compute_tstr_utility(
        real_profiles=state.profiles_processed,
        synthetic_profiles=state.synthetic_profiles,
        target=req.target,
        model_type=req.model_type,
        seed=req.seed,
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    state.utility_results = result
    return result


# ── Research Readiness ───────────────────────────────────────────────────

@router.get("/research/readiness")
def research_readiness():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")

    readiness: dict = {}

    if state.fidelity_summary is not None:
        readiness["statistical_fidelity"] = {
            "value": state.fidelity_summary["overall_fidelity"],
            "status": "evaluated",
            "detail": state.fidelity_summary.get("interpretation", ""),
        }
    else:
        readiness["statistical_fidelity"] = {"value": None, "status": "not_evaluated"}

    if state.utility_results is not None:
        readiness["research_utility"] = {
            "value": state.utility_results.get("utility_retention"),
            "synthetic_metrics": state.utility_results.get("synthetic_trained_metrics"),
            "real_metrics": state.utility_results.get("real_trained_metrics"),
            "target": state.utility_results.get("target"),
            "status": "evaluated",
        }
    else:
        readiness["research_utility"] = {"value": None, "status": "not_evaluated"}

    if state.subgroup_fidelity is not None and len(state.subgroup_fidelity) > 0:
        valid_scores = [
            s["fidelity"] for s in state.subgroup_fidelity
            if s.get("fidelity") is not None
        ]
        mean_subgroup = round(float(np.mean(valid_scores)), 4) if valid_scores else None
        readiness["subgroup_preservation"] = {
            "value": mean_subgroup,
            "subgroup_count": len(valid_scores),
            "status": "evaluated" if mean_subgroup is not None else "not_evaluated",
            "detail": "Average statistical fidelity across evaluated demographic and condition subgroups.",
        }
    else:
        readiness["subgroup_preservation"] = {"value": None, "status": "not_evaluated"}

    plaus = state.plausibility_stats
    if plaus is not None:
        total = plaus.get("total_checked", 0)
        violations = plaus.get("violations_found", 0)
        valid_rate = round((total - violations) / total, 4) if total > 0 else None
        readiness["clinical_validity"] = {
            "value": valid_rate,
            "total_checked": total,
            "violations_found": violations,
            "repairs": plaus.get("repairs", {}),
            "status": "evaluated",
            "detail": "Proportion of records passing clinical plausibility checks after guardrail repair.",
        }
    else:
        readiness["clinical_validity"] = {"value": None, "status": "not_evaluated"}

    if state.privacy_results is not None:
        readiness["privacy_screening"] = {
            "value": state.privacy_results.get("overall_status"),
            "checks": state.privacy_results.get("checks", []),
            "status": "evaluated",
        }
    else:
        readiness["privacy_screening"] = {"value": None, "status": "not_evaluated"}

    if state.cohort_generated and state.data_loaded:
        amp = compute_rare_cohort_amplification(
            state.profiles_processed, state.synthetic_profiles,
        )
        readiness["rare_cohort_coverage"] = amp

    return readiness


# ── Guardrails Stats ─────────────────────────────────────────────────────

@router.get("/cohort/guardrails")
def get_guardrails():
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")
    plaus = state.plausibility_stats
    if plaus is None:
        raise HTTPException(404, "Plausibility stats not computed")

    total = plaus.get("total_checked", 0)
    violations = plaus.get("violations_found", 0)
    return {
        "total_records_checked": total,
        "violations_found": violations,
        "records_repaired": violations,
        "repairs": plaus.get("repairs", {}),
        "all_passed": plaus.get("pass", False),
        "accepted_patients": len(state.synthetic_profiles) if state.synthetic_profiles is not None else 0,
        "accepted_longitudinal": len(state.synthetic_longitudinal) if state.synthetic_longitudinal is not None else 0,
    }


# ── Experiments ───────────────────────────────────────────────────────────

@router.get("/experiments")
def get_experiments():
    experiments = list_experiments()
    return {"experiments": experiments[:50]}


@router.get("/experiments/{exp_id}")
def get_experiment(exp_id: str):
    exp = load_experiment(exp_id)
    if not exp:
        raise HTTPException(404, f"Experiment {exp_id} not found")
    return exp


@router.post("/experiments/save")
def save_current_experiment():
    if not state.cohort_generated:
        raise HTTPException(400, "No cohort generated")
    if state.fidelity_summary is None:
        raise HTTPException(400, "Run validation before saving an experiment")

    cohort_config = state.cohort_config or {}
    fid = state.fidelity_summary
    priv = state.privacy_results
    priv_summary = None
    if priv:
        priv_summary = {
            "status": priv["overall_status"],
            "exact_duplicates": priv["exact_duplicates"]["exact_duplicates"],
            "median_nn_distance": priv["nearest_neighbor"].get("median_distance"),
        }

    exp = save_experiment(
        model=state.train_info["synth_type"] if state.train_info else "unknown",
        num_patients=len(state.synthetic_profiles),
        timeline_days=int(state.synthetic_longitudinal["day"].max()),
        constraints=cohort_config,
        privacy_mode=state.privacy_mode,
        seed=state.current_seed,
        trajectory_dist=state.trajectory_dist,
        fidelity_summary=fid,
        privacy_summary=priv_summary,
    )
    state.current_experiment_id = exp["experiment_id"]
    return exp


# ── Export ─────────────────────────────────────────────────────────────────

@router.get("/export/{fmt}")
def export_data(fmt: str):
    if not state.cohort_generated:
        raise HTTPException(404, "No cohort generated")

    cohort = state.synthetic_profiles
    synth_long = state.synthetic_longitudinal

    if fmt == "profiles_csv":
        return StreamingResponse(
            io.BytesIO(export_csv(cohort)),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=profiles.csv"},
        )
    elif fmt == "longitudinal_csv":
        return StreamingResponse(
            io.BytesIO(export_csv(synth_long)),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=longitudinal.csv"},
        )
    elif fmt == "profiles_json":
        return StreamingResponse(
            io.BytesIO(export_json(cohort)),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=profiles.json"},
        )
    elif fmt == "longitudinal_json":
        return StreamingResponse(
            io.BytesIO(export_json(synth_long)),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=longitudinal.json"},
        )
    elif fmt == "quality_report":
        src_summary = None
        if state.profiles_processed is not None:
            src_summary = {
                "n_patients": len(state.profiles_processed),
                "n_longitudinal": len(state.longitudinal_processed) if state.longitudinal_processed is not None else 0,
            }
        report = create_quality_report(
            source_summary=src_summary,
            synthesizer_type=state.train_info["synth_type"] if state.train_info else None,
            seed=state.current_seed,
            cohort_constraints=state.cohort_config,
            cohort_stats=state.cohort_stats,
            trajectory_dist=state.trajectory_dist,
            fidelity_summary=state.fidelity_summary,
            privacy_metrics=state.privacy_results,
            privacy_mode=state.privacy_mode,
            plausibility_stats=state.plausibility_stats,
        )
        return StreamingResponse(
            io.BytesIO(export_json(report)),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=quality_report.json"},
        )
    elif fmt == "zip":
        n_patients = len(cohort)
        days = int(synth_long["day"].max()) if len(synth_long) > 0 else 0
        zip_bytes = create_export_zip(
            cohort, synth_long,
            validation_report=state.fidelity_summary,
            privacy_report=state.privacy_results,
            cohort_config=state.cohort_config,
            experiment_metadata={
                "seed": state.current_seed,
                "privacy_mode": state.privacy_mode,
                "trajectory_dist": state.trajectory_dist,
                "model": state.train_info["synth_type"] if state.train_info else None,
                "experiment_id": state.current_experiment_id,
            },
            quality_report=None,
            n_patients=n_patients, days=days,
        )
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=clinsynth_export.zip"},
        )
    else:
        raise HTTPException(400, f"Unknown export format: {fmt}")


# ── Config ────────────────────────────────────────────────────────────────

@router.get("/config/presets")
def get_presets():
    return {"presets": RESEARCH_PRESETS}


@router.get("/config/privacy_modes")
def get_privacy_modes():
    return {"modes": PRIVACY_MODES}


# ── Overview ──────────────────────────────────────────────────────────────

@router.get("/overview")
def get_overview():
    n_src = len(state.profiles_processed) if state.profiles_processed is not None else 0
    n_long = len(state.longitudinal_processed) if state.longitudinal_processed is not None else 0
    model_name = None
    if state.train_info:
        model_name = state.train_info["synth_type"].replace("Synthesizer", "")
    n_synth = len(state.synthetic_profiles) if state.synthetic_profiles is not None else 0
    n_synth_long = len(state.synthetic_longitudinal) if state.synthetic_longitudinal is not None else 0
    fid = state.fidelity_summary
    fid_score = fid["overall_fidelity"] if fid else None
    priv = state.privacy_results
    priv_status = priv["overall_status"] if priv else None

    return {
        "data_loaded": state.data_loaded,
        "model_trained": state.model_trained,
        "cohort_generated": state.cohort_generated,
        "source_patients": n_src,
        "source_records": n_long,
        "active_model": model_name,
        "generated_patients": n_synth,
        "generated_records": n_synth_long,
        "fidelity_score": fid_score,
        "privacy_status": priv_status,
        "seed": state.current_seed,
        "constraints": state.cohort_stats.get("constraints", []) if state.cohort_stats else [],
    }


# ── Helpers ───────────────────────────────────────────────────────────────

def _to_native(val):
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val


def _make_serializable(obj):
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    return obj
