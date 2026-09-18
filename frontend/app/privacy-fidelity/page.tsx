"use client";

import { useState } from "react";
import { api, PrivacyFidelityEntry } from "@/lib/api";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  LabelList,
  Legend,
} from "recharts";

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"];

export default function PrivacyFidelityPage() {
  const [results, setResults] = useState<PrivacyFidelityEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.comparePrivacy();
      setResults(data.results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Privacy vs Fidelity Tradeoff</h1>
      <p className="page-subtitle">
        Compare how different privacy modes affect data fidelity and privacy guarantees.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <button className="btn-primary" onClick={runComparison} disabled={loading}>
          {loading ? "Running Comparison..." : "Run Comparison"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: "4px solid #ef4444", color: "#ef4444" }}>
          {error}
        </div>
      )}

      {results.length > 0 && (
        <>
          {/* Results Table */}
          <div className="card">
            <h2 style={{ marginBottom: "1rem" }}>Comparison Results</h2>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Mode</th>
                    <th>Fidelity Score</th>
                    <th>Median NN Distance</th>
                    <th>Exact Duplicates</th>
                    <th>Near Copies</th>
                    <th>Correlation Diff</th>
                    <th>Records After Filter</th>
                    <th>Records Rejected</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.mode}>
                      <td>
                        <span className="badge-info">{r.mode}</span>
                      </td>
                      <td className="metric-value">
                        {r.fidelity_score.toFixed(4)}
                      </td>
                      <td className="metric-value">
                        {r.median_nn_distance.toFixed(4)}
                      </td>
                      <td>
                        <span className={r.exact_duplicates === 0 ? "badge-success" : "badge-warning"}>
                          {r.exact_duplicates}
                        </span>
                      </td>
                      <td>
                        <span className={r.near_copy_count === 0 ? "badge-success" : "badge-warning"}>
                          {r.near_copy_count}
                        </span>
                      </td>
                      <td className="metric-value">
                        {r.correlation_diff !== null ? r.correlation_diff.toFixed(4) : "N/A"}
                      </td>
                      <td>{r.records_after_filter}</td>
                      <td>
                        <span className={r.records_rejected === 0 ? "badge-success" : "badge-warning"}>
                          {r.records_rejected}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Scatter Chart: Fidelity vs Privacy */}
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <h2 style={{ marginBottom: "1rem" }}>Fidelity vs Privacy (Nearest-Neighbor Distance)</h2>
            <p className="metric-label" style={{ marginBottom: "1rem" }}>
              Higher fidelity means closer to real data; higher NN distance means better privacy.
            </p>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="fidelity_score"
                  name="Fidelity Score"
                  label={{ value: "Fidelity Score", position: "insideBottom", offset: -5 }}
                />
                <YAxis
                  type="number"
                  dataKey="median_nn_distance"
                  name="Median NN Distance"
                  label={{ value: "Median NN Distance", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  formatter={(value: unknown) => Number(value).toFixed(4)}
                  labelFormatter={() => ""}
                  content={({ payload }) => {
                    if (!payload || payload.length === 0) return null;
                    const d = payload[0].payload as PrivacyFidelityEntry;
                    return (
                      <div style={{ background: "#fff", border: "1px solid #ccc", padding: "8px", borderRadius: "4px" }}>
                        <strong>{d.mode}</strong>
                        <div>Fidelity: {d.fidelity_score.toFixed(4)}</div>
                        <div>NN Distance: {d.median_nn_distance.toFixed(4)}</div>
                      </div>
                    );
                  }}
                />
                <Scatter data={results} fill="#6366f1">
                  <LabelList dataKey="mode" position="top" />
                  {results.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {/* Bar Chart: Fidelity Scores */}
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <h2 style={{ marginBottom: "1rem" }}>Fidelity Scores by Privacy Mode</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={results} margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mode" />
                <YAxis label={{ value: "Fidelity Score", angle: -90, position: "insideLeft" }} />
                <Tooltip formatter={(value: unknown) => Number(value).toFixed(4)} />
                <Legend />
                <Bar dataKey="fidelity_score" name="Fidelity Score">
                  {results.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Interpretation */}
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <h2 style={{ marginBottom: "0.5rem" }}>Interpretation</h2>
            <p style={{ lineHeight: 1.7 }}>
              The privacy-fidelity tradeoff is fundamental to synthetic data generation.
              Stricter privacy modes (higher noise, lower rejection thresholds) produce data
              that is harder to link back to real patients, but at the cost of reduced
              statistical fidelity. Key observations:
            </p>
            <ul style={{ marginTop: "0.75rem", lineHeight: 1.8 }}>
              <li>
                <strong>Fidelity Score</strong> measures how closely synthetic distributions
                match real data. Values closer to 1.0 indicate higher similarity.
              </li>
              <li>
                <strong>Median Nearest-Neighbor Distance</strong> quantifies how far each
                synthetic record is from the closest real record. Higher values indicate
                stronger privacy protection.
              </li>
              <li>
                <strong>Records Rejected</strong> shows how many generated records were
                filtered out for being too similar to real data. More rejections mean
                stricter privacy but potentially lower output volume.
              </li>
              <li>
                Modes with zero exact duplicates and near copies while maintaining
                reasonable fidelity represent the best balance for your use case.
              </li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
