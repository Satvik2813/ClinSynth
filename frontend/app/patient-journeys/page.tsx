"use client";

import { useEffect, useState } from "react";
import { api, JourneyResult } from "@/lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = ["#2F6B5F", "#4FAE8A", "#D4A843", "#C45B52", "#0F2F2C", "#66756F"];

export default function PatientJourneysPage() {
  const [patientIds, setPatientIds] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [journey, setJourney] = useState<JourneyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.listPatients()
      .then((d) => {
        if (cancelled) return;
        setPatientIds(d.patient_ids);
        if (d.patient_ids.length > 0) {
          setSelectedId(d.patient_ids[0]);
        }
      })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setJourneyLoading(true);
    api.getJourney(selectedId)
      .then((d) => { if (!cancelled) setJourney(d); })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setJourneyLoading(false); });
    return () => { cancelled = true; };
  }, [selectedId]);

  if (loading) return <div style={{ padding: "2rem", textAlign: "center", color: "var(--muted)" }}>Loading patients...</div>;
  if (error && patientIds.length === 0) return <div style={{ padding: "2rem", textAlign: "center", color: "var(--danger)" }}>{error}</div>;

  if (patientIds.length === 0) {
    return (
      <div>
        <h1 className="page-title">Patient Journeys</h1>
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: "3rem" }}>
          No cohort generated yet. Generate a cohort first to view patient journeys.
        </div>
      </div>
    );
  }

  const demo = journey?.demographics;
  const vitalsKeys = journey?.journey && journey.journey.length > 0
    ? Object.keys(journey.journey[0]).filter((k) => k !== "visit_day" && k !== "patient_id" && k !== "day")
    : [];

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 className="page-title">Patient Journeys</h1>
        <p className="page-subtitle">Explore individual synthetic patient trajectories over time</p>
      </div>

      <div className="card" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
        <label style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--foreground)" }}>Select Patient:</label>
        <select
          className="select-field"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {patientIds.map((id) => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
        <span style={{ fontSize: "0.8125rem", color: "var(--muted)" }}>{patientIds.length} patients available</span>
      </div>

      {journeyLoading && <div style={{ textAlign: "center", color: "var(--muted)", padding: "2rem" }}>Loading journey...</div>}

      {journey && !journeyLoading && (
        <>
          {demo && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h2 className="section-title">Demographics</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "1rem" }}>
                <div>
                  <div className="metric-label">Patient ID</div>
                  <div style={{ fontWeight: 600 }}>{demo.patient_id}</div>
                </div>
                <div>
                  <div className="metric-label">Age</div>
                  <div style={{ fontWeight: 600 }}>{demo.age}</div>
                </div>
                <div>
                  <div className="metric-label">Gender</div>
                  <div style={{ fontWeight: 600 }}>{demo.gender}</div>
                </div>
                <div>
                  <div className="metric-label">BMI</div>
                  <div style={{ fontWeight: 600 }}>{typeof demo.bmi === "number" ? demo.bmi.toFixed(1) : demo.bmi}</div>
                </div>
                <div>
                  <div className="metric-label">Conditions</div>
                  <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.25rem" }}>
                    {demo.diabetes && <span className="badge badge-warning">Diabetes</span>}
                    {demo.hypertension && <span className="badge badge-danger">HTN</span>}
                    {!demo.diabetes && !demo.hypertension && <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>None</span>}
                  </div>
                </div>
                <div>
                  <div className="metric-label">Trajectory</div>
                  <div style={{ fontWeight: 600 }}>{demo.trajectory_type || "—"}</div>
                </div>
              </div>
            </div>
          )}

          {journey.journey.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h2 className="section-title">Vitals Over Time</h2>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={journey.journey}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="visit_day"
                    label={{ value: "Visit Day", position: "insideBottom", offset: -5 }}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  {vitalsKeys.map((key, i) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={COLORS[i % COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name={key.replace(/_/g, " ")}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {journey.stats.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h2 className="section-title">Journey Statistics</h2>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Baseline</th>
                      <th>Final</th>
                      <th>Change</th>
                      <th>Mean</th>
                      <th>Min</th>
                      <th>Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {journey.stats.map((s) => (
                      <tr key={s.metric}>
                        <td style={{ fontWeight: 500 }}>{s.metric}</td>
                        <td>{s.baseline != null ? s.baseline.toFixed(1) : "—"}</td>
                        <td>{s.final != null ? s.final.toFixed(1) : "—"}</td>
                        <td>
                          {s.change != null ? (
                            <span style={{ color: s.change > 0 ? "var(--danger)" : s.change < 0 ? "var(--accent)" : "var(--foreground)" }}>
                              {s.change > 0 ? "+" : ""}{s.change.toFixed(1)}
                            </span>
                          ) : "—"}
                        </td>
                        <td>{s.mean.toFixed(1)}</td>
                        <td>{s.min.toFixed(1)}</td>
                        <td>{s.max.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {journey.cohort_average && journey.cohort_average.length > 0 && (
            <div className="card">
              <h2 className="section-title">Cohort Average Comparison</h2>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      {Object.keys(journey.cohort_average[0]).map((k) => (
                        <th key={k}>{k.replace(/_/g, " ")}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {journey.cohort_average.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((v, j) => (
                          <td key={j}>{typeof v === "number" ? v.toFixed(2) : String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
