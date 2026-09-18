"use client";

import { useEffect, useState } from "react";
import { api, Experiment } from "@/lib/api";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchExperiments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getExperiments();
      setExperiments(data.experiments);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load experiments";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await api.saveExperiment();
      await fetchExperiments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save experiment";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title">Experiments</h1>
          <p className="page-subtitle">Track and compare cohort generation runs</p>
        </div>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Current Experiment"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: "4px solid #ef4444", marginBottom: "1rem" }}>
          <p style={{ color: "#ef4444", margin: 0 }}>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <p>Loading experiments...</p>
        </div>
      ) : experiments.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <p style={{ margin: 0 }}>No experiments saved yet. Generate a cohort and save it as an experiment.</p>
        </div>
      ) : (
        <div className="table-container">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>ID</th>
                <th style={{ textAlign: "left", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Timestamp</th>
                <th style={{ textAlign: "left", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Model</th>
                <th style={{ textAlign: "right", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Patients</th>
                <th style={{ textAlign: "right", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Days</th>
                <th style={{ textAlign: "left", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Privacy</th>
                <th style={{ textAlign: "right", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Seed</th>
                <th style={{ textAlign: "right", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Fidelity</th>
                <th style={{ textAlign: "left", padding: "0.75rem", borderBottom: "2px solid var(--border-color, #e5e7eb)" }}>Privacy Status</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <>
                  <tr
                    key={exp.experiment_id}
                    onClick={() => toggleExpand(exp.experiment_id)}
                    style={{ cursor: "pointer", borderBottom: "1px solid var(--border-color, #e5e7eb)" }}
                  >
                    <td style={{ padding: "0.75rem", fontFamily: "monospace", fontSize: "0.85rem" }}>
                      {exp.experiment_id.slice(0, 8)}...
                    </td>
                    <td style={{ padding: "0.75rem" }}>
                      {new Date(exp.timestamp).toLocaleString()}
                    </td>
                    <td style={{ padding: "0.75rem" }}>
                      <span className="badge-info">{exp.model}</span>
                    </td>
                    <td style={{ padding: "0.75rem", textAlign: "right" }}>
                      <span className="metric-value">{exp.num_patients}</span>
                    </td>
                    <td style={{ padding: "0.75rem", textAlign: "right" }}>
                      <span className="metric-value">{exp.timeline_days}</span>
                    </td>
                    <td style={{ padding: "0.75rem" }}>
                      <span className="badge-warning">{exp.privacy_mode}</span>
                    </td>
                    <td style={{ padding: "0.75rem", textAlign: "right", fontFamily: "monospace" }}>
                      {exp.seed}
                    </td>
                    <td style={{ padding: "0.75rem", textAlign: "right" }}>
                      {exp.fidelity_summary ? (
                        <span className="metric-value">
                          {(exp.fidelity_summary.overall_fidelity * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span style={{ color: "#9ca3af" }}>--</span>
                      )}
                    </td>
                    <td style={{ padding: "0.75rem" }}>
                      {exp.privacy_summary ? (
                        <span className={exp.privacy_summary.status === "PASS" ? "badge-success" : "badge-warning"}>
                          {exp.privacy_summary.status}
                        </span>
                      ) : (
                        <span style={{ color: "#9ca3af" }}>--</span>
                      )}
                    </td>
                  </tr>

                  {expandedId === exp.experiment_id && (
                    <tr key={`${exp.experiment_id}-details`}>
                      <td colSpan={9} style={{ padding: "1rem 1.5rem", backgroundColor: "var(--bg-secondary, #f9fafb)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                          <div>
                            <h4 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Constraints</h4>
                            {exp.constraints && Object.keys(exp.constraints).length > 0 ? (
                              <pre style={{ fontSize: "0.8rem", overflow: "auto", margin: 0, whiteSpace: "pre-wrap" }}>
                                {JSON.stringify(exp.constraints, null, 2)}
                              </pre>
                            ) : (
                              <p style={{ color: "#9ca3af", margin: 0 }}>No constraints recorded</p>
                            )}
                          </div>
                          <div>
                            <h4 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Trajectory Distribution</h4>
                            {exp.trajectory_dist && Object.keys(exp.trajectory_dist).length > 0 ? (
                              <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                                {Object.entries(exp.trajectory_dist).map(([key, val]) => (
                                  <li key={key}>
                                    <span className="metric-label">{key}:</span>{" "}
                                    <span className="metric-value">{(val * 100).toFixed(0)}%</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p style={{ color: "#9ca3af", margin: 0 }}>No distribution recorded</p>
                            )}
                          </div>
                          {exp.privacy_summary && (
                            <div>
                              <h4 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Privacy Details</h4>
                              <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                                <li>
                                  <span className="metric-label">Exact Duplicates:</span>{" "}
                                  <span className="metric-value">{exp.privacy_summary.exact_duplicates}</span>
                                </li>
                                <li>
                                  <span className="metric-label">Median NN Distance:</span>{" "}
                                  <span className="metric-value">
                                    {exp.privacy_summary.median_nn_distance != null
                                      ? exp.privacy_summary.median_nn_distance.toFixed(4)
                                      : "--"}
                                  </span>
                                </li>
                              </ul>
                            </div>
                          )}
                          <div>
                            <h4 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Full Experiment ID</h4>
                            <code style={{ fontSize: "0.8rem", wordBreak: "break-all" }}>{exp.experiment_id}</code>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
