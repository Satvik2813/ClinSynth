"""Export utilities for synthetic data and reports."""
import json
import io
import zipfile
from datetime import datetime

import pandas as pd


def export_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def export_json(data) -> bytes:
    if isinstance(data, pd.DataFrame):
        return data.to_json(orient="records", indent=2).encode("utf-8")
    return json.dumps(data, indent=2, default=str).encode("utf-8")


def create_quality_report(
    generation_timestamp: str | None = None,
    source_summary: dict | None = None,
    synthesizer_type: str | None = None,
    seed: int | None = None,
    cohort_constraints: dict | None = None,
    cohort_stats: dict | None = None,
    trajectory_dist: dict | None = None,
    fidelity_summary: dict | None = None,
    longitudinal_metrics: dict | None = None,
    privacy_metrics: dict | None = None,
    privacy_mode: str | None = None,
    plausibility_stats: dict | None = None,
) -> dict:
    return {
        "report_type": "ClinSynth Cohort Quality Report",
        "generation_timestamp": generation_timestamp or datetime.now().isoformat(),
        "source_dataset_summary": source_summary,
        "synthesizer": synthesizer_type,
        "seed": seed,
        "requested_constraints": cohort_constraints,
        "actual_composition": cohort_stats,
        "trajectory_distribution": trajectory_dist,
        "fidelity_metrics": fidelity_summary,
        "longitudinal_metrics": longitudinal_metrics,
        "privacy_mode": privacy_mode,
        "privacy_metrics": privacy_metrics,
        "plausibility_stats": plausibility_stats,
        "warnings": [],
        "limitations": [
            "Synthetic data is not clinically validated.",
            "Privacy screening provides screening metrics, not formal guarantees.",
            "Statistical fidelity does not ensure clinical validity.",
            "Trajectory archetypes are simulation assumptions.",
        ],
    }


def create_export_zip(
    profiles: pd.DataFrame,
    longitudinal: pd.DataFrame,
    validation_report: dict | None = None,
    privacy_report: dict | None = None,
    cohort_config: dict | None = None,
    experiment_metadata: dict | None = None,
    quality_report: dict | None = None,
    n_patients: int = 0,
    days: int = 0,
) -> bytes:
    buf = io.BytesIO()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("profiles.csv", profiles.to_csv(index=False))
        zf.writestr("longitudinal.csv", longitudinal.to_csv(index=False))

        combined = longitudinal.merge(
            profiles, on="patient_id", how="left", suffixes=("", "_profile"),
        )
        zf.writestr("combined.csv", combined.to_csv(index=False))

        if validation_report:
            zf.writestr(
                "validation_report.json",
                json.dumps(validation_report, indent=2, default=str),
            )
        if privacy_report:
            report_safe = {k: v for k, v in privacy_report.items() if k != "nearest_neighbor"}
            if "nearest_neighbor" in privacy_report:
                nn = dict(privacy_report["nearest_neighbor"])
                nn.pop("distances", None)
                report_safe["nearest_neighbor"] = nn
            zf.writestr(
                "privacy_report.json",
                json.dumps(report_safe, indent=2, default=str),
            )
        if cohort_config:
            zf.writestr(
                "cohort_config.json",
                json.dumps(cohort_config, indent=2, default=str),
            )
        if experiment_metadata:
            zf.writestr(
                "experiment_metadata.json",
                json.dumps(experiment_metadata, indent=2, default=str),
            )
        if quality_report:
            zf.writestr(
                "quality_report.json",
                json.dumps(quality_report, indent=2, default=str),
            )

        zf.writestr(
            "README.txt",
            f"ClinSynth Export — {timestamp}\n"
            f"Patients: {n_patients}\n"
            f"Timeline: {days} days\n\n"
            "Files:\n"
            "  profiles.csv             — Synthetic patient profiles\n"
            "  longitudinal.csv         — Daily longitudinal health records\n"
            "  combined.csv             — Profiles merged with longitudinal data\n"
            "  cohort_config.json       — Cohort constraint configuration\n"
            "  validation_report.json   — Statistical fidelity metrics\n"
            "  privacy_report.json      — Privacy screening results\n"
            "  experiment_metadata.json — Experiment settings and metadata\n"
            "  quality_report.json      — Comprehensive quality report\n\n"
            "DISCLAIMER: This data is synthetically generated for research purposes.\n"
            "It does not represent real patients. Statistical properties approximate\n"
            "the source dataset but are not clinically validated.\n",
        )

    buf.seek(0)
    return buf.read()
