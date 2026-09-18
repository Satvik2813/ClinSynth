"use client";

import { useEffect, useState, useCallback } from "react";
import { api, Overview } from "@/lib/api";

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const fetchOverview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getOverview();
      setOverview(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load overview";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const handleLoadDemo = async () => {
    try {
      setDemoLoading(true);
      setError(null);
      await api.loadDemo();
      await fetchOverview();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load demo data";
      setError(message);
    } finally {
      setDemoLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 40, height: 40, border: "3px solid var(--card-border)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 1rem" }} />
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>Loading dashboard...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div>
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">ClinSynth pipeline overview</p>
        <div className="card" style={{ marginTop: "1.5rem", textAlign: "center", padding: "3rem 1.5rem" }}>
          <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>
          <button className="btn-primary" onClick={fetchOverview}>Retry</button>
          <button className="btn-secondary" onClick={handleLoadDemo} disabled={demoLoading} style={{ marginLeft: "0.75rem" }}>
            {demoLoading ? "Loading..." : "Load Demo Data"}
          </button>
        </div>
      </div>
    );
  }

  if (!overview) return null;

  const pipelineSteps = [
    { label: "Data Loaded", done: overview.data_loaded },
    { label: "Model Trained", done: overview.model_trained },
    { label: "Cohort Generated", done: overview.cohort_generated },
  ];

  const metrics = [
    { label: "Source Patients", value: overview.source_patients.toLocaleString() },
    { label: "Generated Patients", value: overview.generated_patients.toLocaleString() },
    {
      label: "Fidelity Score",
      value: overview.fidelity_score != null ? `${(overview.fidelity_score * 100).toFixed(1)}%` : "--",
    },
    {
      label: "Privacy Status",
      value: overview.privacy_status || "--",
      badge: overview.privacy_status
        ? overview.privacy_status.toLowerCase().includes("pass")
          ? "badge-success"
          : overview.privacy_status.toLowerCase().includes("fail")
            ? "badge-danger"
            : "badge-warning"
        : null,
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">ClinSynth pipeline overview</p>
        </div>
        <button className="btn-primary" onClick={handleLoadDemo} disabled={demoLoading}>
          {demoLoading ? "Loading Demo..." : "Load Demo Data"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: "1rem", background: "var(--danger-light)", borderColor: "var(--danger)" }}>
          <p style={{ color: "#991b1b", fontSize: "0.875rem", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Pipeline Status */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
          Pipeline Status
        </h2>
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          {pipelineSteps.map((step) => (
            <div key={step.label} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className={`status-dot ${step.done ? "status-dot-success" : ""}`} style={!step.done ? { background: "var(--card-border)" } : undefined} />
              <span style={{ fontSize: "0.875rem", color: step.done ? "var(--foreground)" : "var(--muted)" }}>
                {step.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        {metrics.map((m) => (
          <div className="card" key={m.label}>
            {m.badge ? (
              <span className={`badge ${m.badge}`} style={{ marginBottom: "0.5rem" }}>{m.value}</span>
            ) : (
              <p className="metric-value">{m.value}</p>
            )}
            <p className="metric-label">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Model Info */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card">
          <p style={{ fontSize: "0.875rem", color: "var(--muted)", marginBottom: "0.25rem" }}>Active Model</p>
          <p style={{ fontSize: "1.125rem", fontWeight: 600 }}>
            {overview.active_model || <span style={{ color: "var(--muted)" }}>None</span>}
          </p>
        </div>
        <div className="card">
          <p style={{ fontSize: "0.875rem", color: "var(--muted)", marginBottom: "0.25rem" }}>Seed</p>
          <p style={{ fontSize: "1.125rem", fontWeight: 600, fontFamily: "var(--font-geist-mono, monospace)" }}>
            {overview.seed}
          </p>
        </div>
      </div>

      {/* Constraints Table */}
      {overview.constraints && overview.constraints.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            Constraints
          </h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Constraint</th>
                  <th>Requested</th>
                  <th>Actual</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {overview.constraints.map((c, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{c.constraint}</td>
                    <td>{c.requested != null ? `${(c.requested * 100).toFixed(1)}%` : "--"}</td>
                    <td>{c.actual != null ? `${(c.actual * 100).toFixed(1)}%` : "--"}</td>
                    <td>
                      {c.error != null ? (
                        <span style={{ color: Math.abs(c.error) > 0.05 ? "var(--danger)" : "var(--success)" }}>
                          {(c.error * 100).toFixed(2)}%
                        </span>
                      ) : "--"}
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
