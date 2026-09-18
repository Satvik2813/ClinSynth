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


def create_export_zip(
    profiles: pd.DataFrame,
    longitudinal: pd.DataFrame,
    validation_report: dict | None = None,
    privacy_report: dict | None = None,
    n_patients: int = 0,
    days: int = 0,
) -> bytes:
    buf = io.BytesIO()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"clinsynth_profiles_{n_patients}.csv",
            profiles.to_csv(index=False),
        )
        zf.writestr(
            f"clinsynth_longitudinal_{n_patients}_{days}d.csv",
            longitudinal.to_csv(index=False),
        )

        combined = longitudinal.merge(
            profiles, on="patient_id", how="left", suffixes=("", "_profile"),
        )
        zf.writestr(
            f"clinsynth_combined_{n_patients}_{days}d.csv",
            combined.to_csv(index=False),
        )

        if validation_report:
            zf.writestr(
                "clinsynth_validation_report.json",
                json.dumps(validation_report, indent=2, default=str),
            )
        if privacy_report:
            report_safe = {k: v for k, v in privacy_report.items() if k != "nearest_neighbor"}
            if "nearest_neighbor" in privacy_report:
                nn = dict(privacy_report["nearest_neighbor"])
                nn.pop("distances", None)
                report_safe["nearest_neighbor"] = nn
            zf.writestr(
                "clinsynth_privacy_report.json",
                json.dumps(report_safe, indent=2, default=str),
            )

        zf.writestr(
            "README.txt",
            f"ClinSynth Export — {timestamp}\n"
            f"Patients: {n_patients}\n"
            f"Timeline: {days} days\n\n"
            "DISCLAIMER: This data is synthetically generated for research purposes.\n"
            "It does not represent real patients. Statistical properties approximate\n"
            "the source dataset but are not clinically validated.\n",
        )

    buf.seek(0)
    return buf.read()
