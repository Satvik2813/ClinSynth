"use client";

import { CohortResult } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { SkeletonCard, SkeletonMetrics, SkeletonTable } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const PIE_COLORS = [
  "#2F6B5F",
  "#4FAE8A",
  "#D4A843",
  "#C45B52",
  "#0F2F2C",
  "#66756F",
  "#3A8A6E",
  "#8CB4A5",
];

export default function SyntheticCohortPage() {
  const { data: cohort, error, isLoading, mutate } = useApi<CohortResult>("/cohort/current", { errorRetryCount: 0 });

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Synthetic Cohort</h1>
        <p className="page-subtitle">Inspect the generated synthetic patient cohort</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonMetrics count={3} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonTable rows={5} cols={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={6} /></div>
      </div>
    );
  }

  if (error || !cohort) {
    return (
      <div>
        <h1 className="page-title">Synthetic Cohort</h1>
        <p className="page-subtitle">Inspect the generated synthetic patient cohort</p>
        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Cohort" status="not_generated" />
        </div>
        <div className="card" style={{ marginTop: "1rem", textAlign: "center", padding: "3rem 1.5rem" }}>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            No cohort has been generated yet. Generate one from the Cohort Builder page first.
          </p>
          <button className="btn-primary" onClick={() => mutate()}>Retry</button>
        </div>
      </div>
    );
  }

  const summaryMetrics = [
    { label: "Total Patients", value: cohort.total_patients.toLocaleString() },
    { label: "Timeline Days", value: cohort.timeline_days.toLocaleString() },
    { label: "Longitudinal Records", value: cohort.longitudinal_records.toLocaleString() },
  ];

  const trajectoryData = Object.entries(cohort.trajectory_distribution).map(
    ([name, value]) => ({ name, value })
  );

  const profileColumns =
    cohort.profile_preview.length > 0
      ? Object.keys(cohort.profile_preview[0])
      : [];
  const previewRows = cohort.profile_preview.slice(0, 10);

  const plausibilityEntries = Object.entries(cohort.plausibility_stats);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h1 className="page-title">Synthetic Cohort</h1>
          <p className="page-subtitle">Inspect the generated synthetic patient cohort</p>
        </div>
        <StatusBadge label="Cohort" status="generated" />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
          marginTop: "1rem",
        }}
      >
        {summaryMetrics.map((m) => (
          <div className="card" key={m.label} style={{ textAlign: "center", padding: "1.5rem" }}>
            <div className="metric-value">{m.value}</div>
            <div className="metric-label">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>Constraints</h2>
        <div className="table-container">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={thStyle}>Constraint</th>
                <th style={thStyle}>Requested %</th>
                <th style={thStyle}>Actual %</th>
                <th style={thStyle}>Error %</th>
              </tr>
            </thead>
            <tbody>
              {cohort.constraints.map((c, i) => (
                <tr key={i}>
                  <td style={tdStyle}>{c.constraint}</td>
                  <td style={tdStyle}>
                    {c.requested != null ? `${(c.requested * 100).toFixed(1)}%` : "—"}
                  </td>
                  <td style={tdStyle}>
                    {c.actual != null ? `${(c.actual * 100).toFixed(1)}%` : "—"}
                  </td>
                  <td style={tdStyle}>
                    {c.error != null ? (
                      <span
                        className={
                          Math.abs(c.error) < 0.02
                            ? "badge-success"
                            : Math.abs(c.error) < 0.05
                            ? "badge-warning"
                            : "badge-info"
                        }
                      >
                        {(c.error * 100).toFixed(2)}%
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {trajectoryData.length > 0 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
            Trajectory Distribution
          </h2>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={trajectoryData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={110}
                  label={({ name, percent }: { name?: string; percent?: number }) =>
                    `${name ?? ""} (${((percent ?? 0) * 100).toFixed(0)}%)`
                  }
                >
                  {trajectoryData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: unknown) => Number(value).toLocaleString()} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {plausibilityEntries.length > 0 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
            Plausibility Statistics
          </h2>
          <div className="table-container">
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Statistic</th>
                  <th style={thStyle}>Value</th>
                </tr>
              </thead>
              <tbody>
                {plausibilityEntries.map(([key, val]) => (
                  <tr key={key}>
                    <td style={tdStyle}>{formatKey(key)}</td>
                    <td style={tdStyle}>{formatValue(val)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {previewRows.length > 0 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
            Profile Preview{" "}
            <span style={{ fontWeight: 400, color: "var(--muted)", fontSize: "0.85rem" }}>
              (first {previewRows.length} rows)
            </span>
          </h2>
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr>
                  {profileColumns.map((col) => (
                    <th key={col} style={thStyle}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, ri) => (
                  <tr key={ri}>
                    {profileColumns.map((col) => (
                      <td key={col} style={tdStyle}>{formatCell(row[col])}</td>
                    ))}
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

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.75rem 1rem",
  borderBottom: "2px solid var(--border)",
  fontWeight: 600,
  fontSize: "0.75rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  color: "var(--muted)",
};

const tdStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  borderBottom: "1px solid var(--border)",
};

function formatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(val: unknown): string {
  if (val == null) return "—";
  if (typeof val === "number") {
    return Number.isInteger(val) ? val.toLocaleString() : val.toFixed(4);
  }
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

function formatCell(val: unknown): string {
  if (val == null) return "—";
  if (typeof val === "number") {
    return Number.isInteger(val) ? val.toLocaleString() : val.toFixed(2);
  }
  if (typeof val === "boolean") return val ? "Yes" : "No";
  return String(val);
}
