"use client";

import { useEffect, useState } from "react";
import { api, PrivacyResult } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function PrivacyPage() {
  const [data, setData] = useState<PrivacyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getPrivacy()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: "2rem", textAlign: "center", color: "var(--muted)" }}>Loading privacy analysis...</div>;

  if (error) {
    return (
      <div>
        <h1 className="page-title">Privacy Analysis</h1>
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: "3rem" }}>
          Privacy analysis not available. Generate a cohort first.
        </div>
      </div>
    );
  }

  if (!data) return null;

  const distanceData = [
    {
      name: "Real-to-Real",
      mean: data.real_to_real_baseline?.mean_distance ?? 0,
      median: data.real_to_real_baseline?.median_distance ?? 0,
    },
    {
      name: "Synth-to-Real",
      mean: data.nearest_neighbor.mean_distance,
      median: data.nearest_neighbor.median_distance,
    },
    {
      name: "Synth-to-Synth",
      mean: data.synth_to_synth?.mean_distance ?? 0,
      median: data.synth_to_synth?.median_distance ?? 0,
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 className="page-title">Privacy Analysis</h1>
        <p className="page-subtitle">Evaluate privacy protection of synthetic data</p>
      </div>

      <div className="card" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "1rem" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--foreground)" }}>Overall Status:</span>
        <span className={`badge ${data.overall_status === "PASS" ? "badge-success" : "badge-danger"}`}>
          {data.overall_status}
        </span>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2 className="section-title">Privacy Checks</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {data.checks.map((c, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", padding: "0.75rem", borderRadius: "0.5rem", background: "var(--mint)" }}>
              <span className={`status-dot ${c.passed ? "status-dot-success" : "status-dot-danger"}`} style={{ marginTop: "0.375rem" }} />
              <div>
                <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{c.check}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.125rem" }}>{c.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card">
          <h2 className="section-title">Exact Duplicates</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Duplicates Found</span>
              <span style={{ fontWeight: 600 }}>{data.exact_duplicates.exact_duplicates}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Duplicate Rate</span>
              <span style={{ fontWeight: 600 }}>{(data.exact_duplicates.duplicate_rate * 100).toFixed(2)}%</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Total Synthetic Records</span>
              <span style={{ fontWeight: 600 }}>{data.exact_duplicates.total_synthetic_records}</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
              Columns compared: {data.exact_duplicates.columns_compared.join(", ")}
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="section-title">Nearest Neighbor Analysis</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Mean Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.mean_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Median Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.median_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Min Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.min_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Near Copies</span>
              <span style={{ fontWeight: 600, color: data.nearest_neighbor.near_copy_count > 0 ? "var(--warning)" : "var(--accent)" }}>
                {data.nearest_neighbor.near_copy_count}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Threshold</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.near_copy_threshold}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2 className="section-title">Distance Comparison</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="mean" fill="#2F6B5F" name="Mean Distance" />
            <Bar dataKey="median" fill="#4FAE8A" name="Median Distance" />
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.5rem" }}>
          Higher synth-to-real distances indicate better privacy. Synth-to-real should be comparable to or higher than real-to-real baseline.
        </p>
      </div>

      <div className="card">
        <h2 className="section-title">Disclaimer</h2>
        <p style={{ fontSize: "0.875rem", color: "var(--muted)" }}>{data.disclaimer}</p>
      </div>
    </div>
  );
}
