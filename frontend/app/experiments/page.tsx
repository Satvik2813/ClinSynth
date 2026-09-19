"use client";

import { useState } from "react";
import { api, Experiment } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonTable } from "@/components/skeleton";
import { toast } from "sonner";

export default function ExperimentsPage() {
  const { data: expData, error, isLoading, mutate } = useApi<{ experiments: Experiment[] }>("/experiments", { errorRetryCount: 0 });
  const experiments = expData?.experiments ?? [];

  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleSave = async () => {
    const toastId = "experiment-save";
    toast.loading("Saving current experiment...", { id: toastId });
    setSaving(true);
    try {
      const saved = await api.saveExperiment();
      toast.success("Experiment saved successfully", {
        id: toastId,
        description: `Experiment ID: ${saved.experiment_id}`,
      });
      mutate();
    } catch (err: unknown) {
      toast.error("Failed to save experiment", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setSaving(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Experiments</h1>
        <p className="page-subtitle">Track and compare cohort generation runs</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonTable rows={5} cols={8} /></div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title">Experiments</h1>
          <p className="page-subtitle">Track and compare cohort generation runs</p>
        </div>
        <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
          {saving && <span className="spinner" />}
          {saving ? "Saving..." : "Save Current Experiment"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: "4px solid var(--danger)", marginBottom: "1rem" }}>
          <p style={{ color: "var(--danger)", margin: 0 }}>{friendlyError(error)}</p>
        </div>
      )}

      {experiments.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <p style={{ margin: 0, color: "var(--muted)" }}>No experiments saved yet. Generate a cohort and save it as an experiment.</p>
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
                <tbody key={exp.experiment_id}>
                  <tr
                    onClick={() => toggleExpand(exp.experiment_id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td style={{ fontFamily: "var(--font-geist-mono, monospace)", fontSize: "0.8125rem" }}>
                      {exp.experiment_id.slice(0, 8)}...
                    </td>
                    <td>{new Date(exp.timestamp).toLocaleString()}</td>
                    <td><span className="badge badge-info">{exp.model}</span></td>
                    <td style={{ textAlign: "right" }}>{exp.num_patients}</td>
                    <td style={{ textAlign: "right" }}>{exp.timeline_days}</td>
                    <td><span className="badge badge-warning">{exp.privacy_mode}</span></td>
                    <td style={{ textAlign: "right", fontFamily: "var(--font-geist-mono, monospace)" }}>{exp.seed}</td>
                    <td style={{ textAlign: "right" }}>
                      {exp.fidelity_summary ? (
                        <span style={{ fontWeight: 600 }}>{(exp.fidelity_summary.overall_fidelity * 100).toFixed(1)}%</span>
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
                    <tr>
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
                </tbody>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
