"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface ExportOption {
  key: string;
  label: string;
  description: string;
  format: string;
}

const EXPORT_OPTIONS: ExportOption[] = [
  {
    key: "profiles_csv",
    label: "Profiles CSV",
    description: "Patient demographic and baseline profiles in comma-separated format. One row per patient with columns for age, gender, BMI, conditions, and trajectory type.",
    format: "CSV",
  },
  {
    key: "longitudinal_csv",
    label: "Longitudinal CSV",
    description: "Time-series clinical records in comma-separated format. Multiple rows per patient with timestamped lab values, vitals, and clinical measurements.",
    format: "CSV",
  },
  {
    key: "profiles_json",
    label: "Profiles JSON",
    description: "Patient demographic and baseline profiles in JSON format. Suitable for programmatic access and integration with APIs or data pipelines.",
    format: "JSON",
  },
  {
    key: "longitudinal_json",
    label: "Longitudinal JSON",
    description: "Time-series clinical records in JSON format. Nested structure with patient journeys organized by patient ID for easy traversal.",
    format: "JSON",
  },
  {
    key: "quality_report",
    label: "Quality Report",
    description: "Plain-text fidelity and privacy evaluation report. Includes distribution comparisons, correlation preservation metrics, and privacy check results.",
    format: "TXT",
  },
  {
    key: "zip",
    label: "Full ZIP",
    description: "Complete export bundle containing all CSV and JSON files plus the quality report. Best option for archiving or sharing a full experiment snapshot.",
    format: "ZIP",
  },
];

export default function ExportPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = (key: string) => {
    setDownloading(key);
    // The download is handled by the browser via the <a> tag,
    // so we just briefly show the downloading state.
    setTimeout(() => setDownloading(null), 2000);
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 className="page-title">Export Data</h1>
        <p className="page-subtitle">Download generated cohort data in various formats</p>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem", borderLeft: "4px solid var(--primary)", padding: "1rem 1.25rem" }}>
        <p style={{ margin: 0, fontSize: "0.9rem" }}>
          <strong>Note:</strong> Exports require a generated cohort. If you have not yet generated
          a cohort, go to the Cohort page first to create one. Downloads will fail with an error
          if no data is available.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1rem" }}>
        {EXPORT_OPTIONS.map((opt) => (
          <div className="card" key={opt.key} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h3 style={{ margin: 0 }}>{opt.label}</h3>
                <span className="badge badge-info">{opt.format}</span>
              </div>
              <p style={{ color: "var(--muted)", fontSize: "0.875rem", lineHeight: 1.5, marginBottom: "1rem" }}>
                {opt.description}
              </p>
            </div>
            <a
              href={api.getExportUrl(opt.key)}
              download
              className="btn-secondary"
              onClick={() => handleDownload(opt.key)}
              style={{ textAlign: "center", textDecoration: "none", display: "block" }}
            >
              {downloading === opt.key ? "Downloading..." : `Download ${opt.format}`}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
