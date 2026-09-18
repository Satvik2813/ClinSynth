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
        <div className="card" style={{ borderLeft: "4px solid var(--danger)", marginBottom: "1rem" }}>
          <p style={{ color: "var(--danger)", margin: 0 }}>{error}</p>
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
                <th>ID</th>
                <th>Timestamp</th>
                <th>Model</th>
                <th>Patients</th>
                <th>Days</th>
                <th>Privacy</th>
                <th>Seed</th>
                <th>Fidelity</th>
                <th>Privacy Status</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <>
                  <tr
                    key={exp.experiment_id}
                    onClick={() => toggleExpand(exp.experiment_id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td style={{ fontFamily: "var(--font-geist-mono, monospace)", fontSize: "0.8125rem" }}>
                      {exp.experiment_id.slice(0, 8)}...
                    </td>
                    <td>{new Date(exp.timestamp).toLocaleString()}</td>
                    <td>
                      <span className="badge badge-info">{exp.model}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>{exp.num_patients}</td>
                    <td style={{ textAlign: "right" }}>{exp.timeline_days}</td>
                    <td>
                      <span className="badge badge-warning">{exp.privacy_mode}</span>
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "var(--font-geist-mono, monospace)" }}>
                      {exp.seed}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {exp.fidelity_summary ? (
                        <span style={{ fontWeight: 600 }}>
                          {(exp.fidelity_summary.overall_fidelity * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span style={{ color: "var(--muted)" }}>--</span>
                      )}
                    </td>
                    <td>
                      {exp.privacy_summary ? (
                        <span className={exp.privacy_summary.status === "PASS" ? "badge badge-success" : "badge badge-warning"}>
                          {exp.privacy_summary.status}
                        </span>
                      ) : (
                        <span style={{ color: "var(--muted)" }}>--</span>
                      )}
                    </td>
                  </tr>

                  {expandedId === exp.experiment_id && (
                    <tr key={`${exp.experiment_id}-details`}>
                      <td colSpan={9} style={{ padding: "1rem 1.5rem", backgroundColor: "var(--mint)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                          <div>
                            <h4 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Constraints</h4>
                            {exp.constraints && Object.keys(exp.constraints).length > 0 ? (
                              <pre style={{ fontSize: "0.8rem", overflow: "auto", margin: 0, whiteSpace: "pre-wrap" }}>
                                {JSON.stringify(exp.constraints, null, 2)}
                              </pre>
                            ) : (
                              <p style={{ color: "var(--muted)", margin: 0 }}>No constraints recorded</p>
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
                              <p style={{ color: "var(--muted)", margin: 0 }}>No distribution recorded</p>
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
