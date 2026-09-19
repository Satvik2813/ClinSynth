"use client";

import { useState } from "react";
import { toast } from "sonner";
import { friendlyError } from "@/lib/errors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface ExportOption {
  key: string;
  label: string;
  description: string;
  format: string;
  filename: string;
}

const EXPORT_OPTIONS: ExportOption[] = [
  {
    key: "profiles_csv",
    label: "Profiles CSV",
    description: "Patient demographic and baseline profiles in comma-separated format. One row per patient with columns for age, gender, BMI, conditions, and trajectory type.",
    format: "CSV",
    filename: "profiles.csv",
  },
  {
    key: "longitudinal_csv",
    label: "Longitudinal CSV",
    description: "Time-series clinical records in comma-separated format. Multiple rows per patient with timestamped lab values, vitals, and clinical measurements.",
    format: "CSV",
    filename: "longitudinal.csv",
  },
  {
    key: "profiles_json",
    label: "Profiles JSON",
    description: "Patient demographic and baseline profiles in JSON format. Suitable for programmatic access and integration with APIs or data pipelines.",
    format: "JSON",
    filename: "profiles.json",
  },
  {
    key: "longitudinal_json",
    label: "Longitudinal JSON",
    description: "Time-series clinical records in JSON format. Nested structure with patient journeys organized by patient ID for easy traversal.",
    format: "JSON",
    filename: "longitudinal.json",
  },
  {
    key: "quality_report",
    label: "Quality Report",
    description: "Plain-text fidelity and privacy evaluation report. Includes distribution comparisons, correlation preservation metrics, and privacy check results.",
    format: "TXT",
    filename: "quality_report.json",
  },
  {
    key: "zip",
    label: "Full ZIP",
    description: "Complete export bundle containing all CSV and JSON files plus the quality report. Best option for archiving or sharing a full experiment snapshot.",
    format: "ZIP",
    filename: "clinsynth_export.zip",
  },
];

function extractFilename(response: Response, fallback: string): string {
  const disposition = response.headers.get("Content-Disposition");
  if (disposition) {
    const match = disposition.match(/filename="?([^";\n]+)"?/);
    if (match?.[1]) return match[1];
  }
  return fallback;
}

export default function ExportPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (opt: ExportOption) => {
    const isZip = opt.key === "zip";
    const toastId = toast.loading(isZip ? "Preparing research bundle..." : "Preparing export...");
    setDownloading(opt.key);
    try {
      const res = await fetch(`${API_BASE}/export/${opt.key}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `Export failed: ${res.status}`);
      }
      const blob = await res.blob();
      const filename = extractFilename(res, opt.filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Download started", { id: toastId });
    } catch (err: unknown) {
      toast.error("Export failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setDownloading(null);
    }
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
            <button
              className="btn-secondary"
              onClick={() => handleDownload(opt)}
              disabled={downloading === opt.key}
              style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}
            >
              {downloading === opt.key && <span className="spinner" />}
              {downloading === opt.key ? "Preparing..." : `Download ${opt.format}`}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
