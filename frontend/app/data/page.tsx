"use client";

import { useState, useRef } from "react";
import { api, DataSummary } from "@/lib/api";
import { useApi, isExpected404 } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonMetrics, SkeletonCard, SkeletonTable } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { clearDownstream } from "@/lib/pipeline-session";

export default function DataPage() {
  const { data: summary, error, isLoading, mutate } = useApi<DataSummary>("/data/summary", {
    errorRetryCount: 0,
  });
  const { mutate: globalMutate } = useSWRConfig();
  const [demoLoading, setDemoLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const noData = error && isExpected404(error);

  const handleLoadDemo = async () => {
    const toastId = "data-demo-load";
    toast.loading("Loading demo dataset...", { id: toastId });
    try {
      setDemoLoading(true);
      const data = await api.loadDemo();
      toast.success("Demo dataset loaded successfully", {
        id: toastId,
        description: `${data.n_patients} patients and ${data.n_longitudinal_records.toLocaleString()} longitudinal records are ready.`,
      });
      setLastAction("Demo dataset loaded");
      mutate(data, false);
      globalMutate("/overview");
      globalMutate("/train/status");
      globalMutate("/cohort/current");
      globalMutate("/validation");
      globalMutate("/privacy");
      globalMutate("/research/readiness");
      clearDownstream();
    } catch (err: unknown) {
      toast.error("Dataset loading failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setDemoLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      toast.error("Please upload a CSV file.");
      return;
    }
    const toastId = "data-upload";
    toast.loading("Uploading dataset...", { id: toastId });
    try {
      setUploadLoading(true);
      const data = await api.uploadCsv(file);
      const dtype = data.n_patients > 0 && data.n_longitudinal_records === 0
        ? "Profile"
        : data.n_patients === 0 && data.n_longitudinal_records > 0
          ? "Longitudinal"
          : "Combined";

      if (data.warning) {
        toast.warning(`${dtype} dataset loaded`, {
          id: toastId,
          description: data.warning,
          duration: 6000,
        });
      } else {
        toast.success("Dataset uploaded successfully", {
          id: toastId,
          description: `${dtype} dataset loaded`,
        });
      }
      setLastAction(`${dtype} dataset uploaded`);
      mutate(data, false);
      globalMutate("/overview");
      globalMutate("/train/status");
      globalMutate("/cohort/current");
      globalMutate("/validation");
      globalMutate("/privacy");
      globalMutate("/research/readiness");
      clearDownstream();
    } catch (err: unknown) {
      toast.error("Dataset upload failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setUploadLoading(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Data</h1>
        <p className="page-subtitle">Dataset summary and exploration</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonMetrics count={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonTable rows={5} cols={4} /></div>
      </div>
    );
  }

  if (noData || (!summary && !error)) {
    return (
      <div>
        <h1 className="page-title">Data</h1>
        <p className="page-subtitle">Load or upload a patient dataset</p>

        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Dataset" status="not_ready" />
        </div>

        <div style={{ marginTop: "1.5rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
          <div className="card" style={{ textAlign: "center", padding: "2.5rem 1.5rem" }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--primary)", marginBottom: "1rem" }}>DEMO</div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.5rem" }}>Demo Dataset</h3>
            <p style={{ color: "var(--muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
              Load a sample synthetic patient dataset to explore ClinSynth features.
            </p>
            <button className="btn-primary" onClick={handleLoadDemo} disabled={demoLoading} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              {demoLoading && <span className="spinner" />}
              {demoLoading ? "Loading Dataset..." : "Load Demo Dataset"}
            </button>
          </div>

          <div
            className="card"
            style={{
              textAlign: "center",
              padding: "2.5rem 1.5rem",
              border: dragging ? "2px dashed var(--primary)" : undefined,
              background: dragging ? "var(--mint)" : undefined,
              transition: "border 0.15s, background 0.15s",
            }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--primary)", marginBottom: "1rem" }}>CSV</div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.5rem" }}>Upload CSV</h3>
            <p style={{ color: "var(--muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
              Drag and drop a CSV file here, or click to browse.
            </p>
            <input ref={fileInputRef} type="file" accept=".csv" onChange={onFileChange} style={{ display: "none" }} />
            <button className="btn-secondary" onClick={() => fileInputRef.current?.click()} disabled={uploadLoading} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              {uploadLoading && <span className="spinner" />}
              {uploadLoading ? "Uploading..." : "Choose File"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div>
        <h1 className="page-title">Data</h1>
        <p className="page-subtitle">Load or upload a patient dataset</p>
        <div className="card" style={{ marginTop: "1.5rem", textAlign: "center", padding: "3rem 1.5rem" }}>
          <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{friendlyError(error)}</p>
          <button className="btn-primary" onClick={() => mutate()}>Retry</button>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  const missingEntries = [
    ...Object.entries(summary.profile_missing || {}).map(([col, pct]) => ({ column: col, pct, source: "Profile" })),
    ...Object.entries(summary.longitudinal_missing || {}).map(([col, pct]) => ({ column: col, pct, source: "Longitudinal" })),
  ].filter((e) => e.pct > 0);

  const previewRows = summary.profile_preview || [];
  const previewCols = previewRows.length > 0 ? Object.keys(previewRows[0]) : [];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title">Data</h1>
          <p className="page-subtitle">Dataset summary and exploration</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn-secondary" onClick={handleLoadDemo} disabled={demoLoading} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {demoLoading && <span className="spinner" />}
            {demoLoading ? "Loading..." : "Load Demo Dataset"}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv" onChange={onFileChange} style={{ display: "none" }} />
          <button className="btn-secondary" onClick={() => fileInputRef.current?.click()} disabled={uploadLoading} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {uploadLoading && <span className="spinner" />}
            {uploadLoading ? "Uploading..." : "Upload CSV"}
          </button>
        </div>
      </div>

      {/* Dataset Status Badge */}
      <div className="card" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <StatusBadge label="Dataset" status="ready" />
        <span style={{ fontSize: "0.8125rem", color: "var(--muted)" }}>
          {summary.n_patients.toLocaleString()} patients, {summary.n_longitudinal_records.toLocaleString()} longitudinal records
        </span>
        {lastAction && (
          <span style={{ fontSize: "0.8125rem", color: "var(--muted)", marginLeft: "auto" }}>
            Last action: {lastAction}
          </span>
        )}
      </div>

      {summary.warning && (
        <div className="card" style={{ marginBottom: "1rem", background: "var(--warning-light)", borderColor: "var(--warning)" }}>
          <p style={{ color: "#92400e", fontSize: "0.875rem", margin: 0 }}>{summary.warning}</p>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card">
          <p className="metric-value">{summary.n_patients.toLocaleString()}</p>
          <p className="metric-label">Patients</p>
        </div>
        <div className="card">
          <p className="metric-value">{summary.n_longitudinal_records.toLocaleString()}</p>
          <p className="metric-label">Longitudinal Records</p>
        </div>
        <div className="card">
          <p className="metric-value">{summary.profile_columns.length}</p>
          <p className="metric-label">Profile Columns</p>
        </div>
        <div className="card">
          <p className="metric-value">{summary.longitudinal_columns.length}</p>
          <p className="metric-label">Longitudinal Columns</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card">
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
            Profile Columns
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
            {summary.profile_columns.map((col) => (
              <span key={col} className="badge badge-info">{col}</span>
            ))}
          </div>
        </div>
        <div className="card">
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
            Longitudinal Columns
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
            {summary.longitudinal_columns.map((col) => (
              <span key={col} className="badge badge-info">{col}</span>
            ))}
          </div>
        </div>
      </div>

      {summary.profile_stats && Object.keys(summary.profile_stats).length > 0 && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            Profile Statistics
          </h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  {(() => {
                    const firstKey = Object.keys(summary.profile_stats!)[0];
                    const statKeys = firstKey ? Object.keys(summary.profile_stats![firstKey]) : [];
                    return statKeys.map((sk) => <th key={sk}>{sk}</th>);
                  })()}
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.profile_stats!).map(([col, stats]) => (
                  <tr key={col}>
                    <td style={{ fontWeight: 500 }}>{col}</td>
                    {Object.values(stats).map((v, i) => (
                      <td key={i} style={{ fontFamily: "var(--font-geist-mono, monospace)", fontSize: "0.8125rem" }}>
                        {typeof v === "number" ? v.toFixed(2) : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {previewRows.length > 0 && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            Profile Preview <span style={{ fontWeight: 400, textTransform: "none" }}>({previewRows.length} rows)</span>
          </h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  {previewCols.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, ri) => (
                  <tr key={ri}>
                    {previewCols.map((col) => (
                      <td key={col} style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
                        {row[col] != null ? String(row[col]) : <span style={{ color: "var(--muted)" }}>null</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {missingEntries.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            Missing Data
          </h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Source</th>
                  <th>Missing %</th>
                  <th style={{ width: "40%" }}>Bar</th>
                </tr>
              </thead>
              <tbody>
                {missingEntries
                  .sort((a, b) => b.pct - a.pct)
                  .map((entry) => (
                    <tr key={`${entry.source}-${entry.column}`}>
                      <td style={{ fontWeight: 500 }}>{entry.column}</td>
                      <td>
                        <span className="badge badge-info">{entry.source}</span>
                      </td>
                      <td style={{ fontFamily: "var(--font-geist-mono, monospace)", fontSize: "0.8125rem" }}>
                        {(entry.pct * 100).toFixed(1)}%
                      </td>
                      <td>
                        <div style={{ background: "var(--mint)", borderRadius: "4px", height: "0.5rem", overflow: "hidden" }}>
                          <div
                            style={{
                              width: `${Math.min(entry.pct * 100, 100)}%`,
                              height: "100%",
                              background: entry.pct > 0.3 ? "var(--danger)" : entry.pct > 0.1 ? "var(--warning)" : "var(--primary)",
                              borderRadius: "4px",
                              transition: "width 0.3s",
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
