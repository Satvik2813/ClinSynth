"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { ValidationResult } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard, SkeletonTable } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";

export default function ValidationPage() {
  const { data, error, isLoading, mutate } = useApi<ValidationResult>("/validation", { errorRetryCount: 0 });
  const { data: currentCohort } = useApi<unknown>("/cohort/current", { errorRetryCount: 0 });
  const { mutate: globalMutate } = useSWRConfig();
  const [running, setRunning] = useState(false);

  const handleRunValidation = async () => {
    if (!currentCohort) {
      toast.error("Validation unavailable", {
        id: "validation-run",
        description: "Generate a synthetic cohort before running validation.",
      });
      return;
    }
    const toastId = "validation-run";
    toast.loading("Running fidelity validation...", { id: toastId });
    setRunning(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await fetch(`${API_BASE}/validation?recompute=true`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `Validation failed: ${res.status}`);
      }
      const freshData: ValidationResult = await res.json();
      mutate(freshData, false);
      const fidelity = freshData.fidelity_summary?.overall_fidelity;
      toast.success("Validation completed", {
        id: toastId,
        description: fidelity != null ? `Overall fidelity: ${(fidelity * 100).toFixed(1)}%` : undefined,
      });
      globalMutate("/overview");
      globalMutate("/research/readiness");
    } catch (err: unknown) {
      toast.error("Validation failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setRunning(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Validation Report</h1>
        <p className="page-subtitle">Statistical fidelity analysis of synthetic data</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonTable rows={6} cols={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={8} /></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <h1 className="page-title">Validation Report</h1>
        <p className="page-subtitle">Statistical fidelity analysis of synthetic data</p>
        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Validation" status="not_evaluated" />
        </div>
        <div className="card" style={{ maxWidth: 480, margin: "1rem auto", padding: "2rem", textAlign: "center" }}>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            {error ? friendlyError(error) : "Validation data not available. Generate a cohort first."}
          </p>
          <button className="btn-primary" onClick={handleRunValidation} disabled={running} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {running && <span className="spinner" />}
            {running ? "Validating..." : "Run Validation"}
          </button>
        </div>
      </div>
    );
  }

  const { fidelity_summary, per_column_quality, subgroup_fidelity } = data;

  const qualityBadgeClass = (q: string) => {
    switch (q.toLowerCase()) {
      case "excellent":
      case "good":
        return "badge badge-success";
      case "fair":
      case "moderate":
        return "badge badge-warning";
      case "poor":
        return "badge badge-danger";
      default:
        return "badge badge-info";
    }
  };

  const chartData = per_column_quality.map((col) => {
    const score =
      col.type === "numerical" && col.ks_statistic != null
        ? 1 - col.ks_statistic
        : col.type === "categorical" && col.tvd != null
          ? 1 - col.tvd
          : 0;
    return {
      column: col.column,
      score: Math.round(score * 1000) / 1000,
      quality: col.quality,
    };
  });

  const barColor = (quality: string) => {
    switch (quality.toLowerCase()) {
      case "excellent":
        return "#4FAE8A";
      case "good":
        return "#2F6B5F";
      case "fair":
      case "moderate":
        return "#D4A843";
      case "poor":
        return "#C45B52";
      default:
        return "#66756F";
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h1 className="page-title">Validation Report</h1>
          <p className="page-subtitle">Statistical fidelity analysis of synthetic data against the original dataset</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button className="btn-secondary" onClick={handleRunValidation} disabled={running} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {running && <span className="spinner" />}
            {running ? "Validating..." : "Re-run Validation"}
          </button>
          <StatusBadge label="Validation" status="evaluated" />
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem", padding: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Overall Fidelity</h2>
        <div style={{ textAlign: "center", margin: "1rem 0" }}>
          <span className="metric-value" style={{ fontSize: "3rem" }}>
            {(fidelity_summary.overall_fidelity * 100).toFixed(1)}%
          </span>
          <div className="metric-label" style={{ marginTop: "0.5rem" }}>
            {fidelity_summary.interpretation}
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: "2rem", marginTop: "1rem", flexWrap: "wrap" }}>
          <div style={{ textAlign: "center" }}>
            <span className="metric-label">Formula</span>
            <div style={{ fontFamily: "monospace", fontSize: "0.85rem", marginTop: "0.25rem" }}>
              {fidelity_summary.formula}
            </div>
          </div>
          <div style={{ textAlign: "center" }}>
            <span className="metric-label">Components</span>
            <div className="metric-value">{fidelity_summary.component_count}</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem", padding: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Per-Column Quality</h2>
        <div className="table-container">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Column</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Type</th>
                <th style={{ textAlign: "right", padding: "0.5rem" }}>KS Statistic / TVD</th>
                <th style={{ textAlign: "center", padding: "0.5rem" }}>Quality</th>
              </tr>
            </thead>
            <tbody>
              {per_column_quality.map((col) => (
                <tr key={col.column}>
                  <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.9rem" }}>
                    {col.column}
                  </td>
                  <td style={{ padding: "0.5rem" }}>{col.type}</td>
                  <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "monospace" }}>
                    {col.type === "numerical"
                      ? col.ks_statistic?.toFixed(4) ?? "N/A"
                      : col.tvd?.toFixed(4) ?? "N/A"}
                  </td>
                  <td style={{ padding: "0.5rem", textAlign: "center" }}>
                    <span className={qualityBadgeClass(col.quality)}>{col.quality}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem", padding: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Column Quality Scores</h2>
        <p className="metric-label" style={{ marginBottom: "1rem" }}>
          Score = 1 - KS statistic (numerical) or 1 - TVD (categorical). Higher is better.
        </p>
        <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 32)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 120, right: 20, top: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
            <YAxis type="category" dataKey="column" width={110} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value: unknown) => `${(Number(value) * 100).toFixed(1)}%`} />
            <Bar dataKey="score" name="Quality Score">
              {chartData.map((entry, idx) => (
                <Cell key={idx} fill={barColor(entry.quality)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {subgroup_fidelity.length > 0 && (
        <div className="card" style={{ padding: "1.5rem" }}>
          <h2 style={{ marginTop: 0 }}>Subgroup Fidelity</h2>
          <div className="table-container">
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Subgroup</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Label</th>
                  <th style={{ textAlign: "right", padding: "0.5rem" }}>Original N</th>
                  <th style={{ textAlign: "right", padding: "0.5rem" }}>Synthetic N</th>
                  <th style={{ textAlign: "right", padding: "0.5rem" }}>Fidelity</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Warning</th>
                </tr>
              </thead>
              <tbody>
                {subgroup_fidelity.map((sg, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: "0.5rem" }}>{sg.subgroup}</td>
                    <td style={{ padding: "0.5rem" }}>{sg.label}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right" }}>{sg.original_n}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right" }}>{sg.synthetic_n}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right" }}>
                      {sg.fidelity != null ? `${(sg.fidelity * 100).toFixed(1)}%` : "N/A"}
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      {sg.warning ? (
                        <span className="badge badge-warning">{sg.warning}</span>
                      ) : (
                        <span className="badge badge-success">OK</span>
                      )}
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
