"use client";

import { useEffect, useState } from "react";
import { api, Overview } from "@/lib/api";

const PIPELINE_STEPS = [
  "Source Data",
  "Model",
  "Cohort",
  "Clinical Guardian",
  "Research Utility",
  "Validation",
  "Privacy",
  "Export",
];

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const fetchOverview = async () => {
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
  };

  useEffect(() => {
    fetchOverview();
  }, []);

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
          <div style={{ width: 40, height: 40, border: "3px solid var(--border)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 1rem" }} />
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>Loading...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div>
        <h1 className="page-title">ClinSynth</h1>
        <p className="page-subtitle">Clinical Research Twin Engine</p>
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

  const pipelineProgress = overview.data_loaded
    ? overview.model_trained
      ? overview.cohort_generated
        ? 3
        : 2
      : 1
    : 0;

  return (
    <div>
      {/* Hero */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--primary-dark)" }}>
              ClinSynth
            </h1>
            <p style={{ fontSize: "1rem", fontWeight: 500, color: "var(--primary)", marginTop: "0.125rem" }}>
              Clinical Research Twin Engine
            </p>
            <p style={{ fontSize: "0.875rem", color: "var(--muted)", marginTop: "0.5rem", maxWidth: "600px" }}>
              From scarce patient data to research-ready synthetic cohorts.
            </p>
          </div>
          <button className="btn-primary" onClick={handleLoadDemo} disabled={demoLoading}>
            {demoLoading ? "Loading Demo..." : "Load Demo Data"}
          </button>
        </div>
        <p style={{ fontSize: "0.8125rem", color: "var(--muted)", marginTop: "0.5rem", maxWidth: "720px", lineHeight: 1.5 }}>
          Generate privacy-screened synthetic patient cohorts, validate statistical fidelity,
          test subgroup preservation, and measure downstream research utility.
        </p>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: "1rem", background: "var(--danger-light)", borderColor: "var(--danger)" }}>
          <p style={{ color: "#8B2E26", fontSize: "0.875rem", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Pipeline */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 className="section-title">Pipeline</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flexWrap: "wrap" }}>
          {PIPELINE_STEPS.map((step, i) => {
            const done = i < pipelineProgress;
            const active = i === pipelineProgress;
            let cls = "pipeline-step pipeline-step-pending";
            if (done) cls = "pipeline-step pipeline-step-done";
            else if (active) cls = "pipeline-step pipeline-step-active";
            return (
              <div key={step} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <span className={cls}>{step}</span>
                {i < PIPELINE_STEPS.length - 1 && (
                  <span className="pipeline-arrow" style={{ fontSize: "0.875rem" }}>&#8250;</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Key Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <MetricCard label="Source Patients" value={overview.source_patients > 0 ? overview.source_patients.toLocaleString() : "—"} />
        <MetricCard label="Source Records" value={overview.source_records > 0 ? overview.source_records.toLocaleString() : "—"} />
        <MetricCard label="Active Model" value={overview.active_model || "—"} small />
        <MetricCard label="Synthetic Patients" value={overview.generated_patients > 0 ? overview.generated_patients.toLocaleString() : "—"} accent />
        <MetricCard label="Synthetic Records" value={overview.generated_records > 0 ? overview.generated_records.toLocaleString() : "—"} accent />
        <MetricCard
          label="Overall Fidelity"
          value={overview.fidelity_score != null ? `${(overview.fidelity_score * 100).toFixed(1)}%` : "Not evaluated"}
        />
        <MetricCard
          label="Privacy Screening"
          value={overview.privacy_status || "Not evaluated"}
          badge={overview.privacy_status ? (overview.privacy_status.toLowerCase().includes("pass") ? "success" : "warning") : undefined}
        />
      </div>

      {/* Configuration */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card">
          <p style={{ fontSize: "0.8125rem", color: "var(--muted)", marginBottom: "0.25rem" }}>Seed</p>
          <p style={{ fontSize: "1.125rem", fontWeight: 600, fontFamily: "var(--font-geist-mono, monospace)" }}>
            {overview.seed}
          </p>
        </div>
      </div>

      {/* Constraints Table */}
      {overview.constraints && overview.constraints.length > 0 && (
        <div className="card">
          <h2 className="section-title">Cohort Constraints</h2>
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
                    <td>{c.requested != null ? `${(c.requested * 100).toFixed(1)}%` : "—"}</td>
                    <td>{c.actual != null ? `${(c.actual * 100).toFixed(1)}%` : "—"}</td>
                    <td>
                      {c.error != null ? (
                        <span style={{ color: Math.abs(c.error) > 0.05 ? "var(--danger)" : "var(--accent)" }}>
                          {(c.error * 100).toFixed(2)}%
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tagline */}
      {!overview.data_loaded && (
        <div className="mint-card" style={{ marginTop: "1.5rem", textAlign: "center" }}>
          <p style={{ fontSize: "0.9375rem", color: "var(--primary)", fontWeight: 500, lineHeight: 1.6 }}>
            Most tools ask whether synthetic patients can be generated.
            <br />
            ClinSynth asks whether researchers can actually trust and use them.
          </p>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, accent, small, badge }: {
  label: string;
  value: string;
  accent?: boolean;
  small?: boolean;
  badge?: "success" | "warning" | "danger";
}) {
  return (
    <div className="card">
      {badge ? (
        <span className={`badge badge-${badge}`} style={{ marginBottom: "0.5rem" }}>{value}</span>
      ) : (
        <p
          className={small ? "" : "metric-value"}
          style={
            small
              ? { fontSize: "1.125rem", fontWeight: 600, color: "var(--foreground)" }
              : accent
                ? { color: "var(--primary)" }
                : undefined
          }
        >
          {value}
        </p>
      )}
      <p className="metric-label">{label}</p>
    </div>
  );
}
