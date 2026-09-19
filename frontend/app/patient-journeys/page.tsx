"use client";

import { useState, useEffect } from "react";
import { api, JourneyResult } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard, SkeletonTable } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = ["#2F6B5F", "#4FAE8A", "#D4A843", "#C45B52", "#0F2F2C", "#66756F"];

export default function PatientJourneysPage() {
  const { data: patientsData, error: listError, isLoading } = useApi<{ patient_ids: string[] }>("/journeys", { errorRetryCount: 0 });
  const patientIds = patientsData?.patient_ids ?? [];

  const [selectedId, setSelectedId] = useState("");
  const [journey, setJourney] = useState<JourneyResult | null>(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [journeyError, setJourneyError] = useState("");

  const firstId = patientIds[0] ?? "";
  useEffect(() => {
    if (firstId && !selectedId) {
      setSelectedId(firstId);
    }
  }, [firstId, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setJourneyLoading(true);
    setJourneyError("");
    api.getJourney(selectedId)
      .then((d) => { if (!cancelled) setJourney(d); })
      .catch((e) => { if (!cancelled) setJourneyError(friendlyError(e)); })
      .finally(() => { if (!cancelled) setJourneyLoading(false); });
    return () => { cancelled = true; };
  }, [selectedId]);

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Patient Journeys</h1>
        <p className="page-subtitle">Explore individual synthetic patient trajectories over time</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={2} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={6} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonTable rows={5} cols={6} /></div>
      </div>
    );
  }

  if (listError || patientIds.length === 0) {
    return (
      <div>
        <h1 className="page-title">Patient Journeys</h1>
        <p className="page-subtitle">Explore individual synthetic patient trajectories over time</p>
        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Cohort" status="not_generated" />
        </div>
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: "3rem", marginTop: "1rem" }}>
          No cohort generated yet. Generate a cohort first to view patient journeys.
        </div>
      </div>
    );
  }

  const demo = journey?.demographics;
  const chartData = (journey?.journey || []).map((r) => {
    const row = r as Record<string, string | number | null | undefined>;
    return {
      ...row,
      day: row.day != null ? Number(row.day) : undefined,
      systolic_bp: row.systolic_bp != null ? Number(row.systolic_bp) : undefined,
      diastolic_bp: row.diastolic_bp != null ? Number(row.diastolic_bp) : undefined,
      steps: row.steps != null ? Number(row.steps) : undefined,
      medication_adherence: row.medication_adherence != null ? Number(row.medication_adherence) : undefined,
      pain_score: row.pain_score != null ? Number(row.pain_score) : undefined,
    };
  });

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

      {journeyLoading && (
        <div style={{ marginTop: "1rem" }}>
          <SkeletonCard lines={4} />
          <div style={{ marginTop: "1rem" }}><SkeletonCard lines={8} /></div>
        </div>
      )}

      {journeyError && (
        <div className="card" style={{ borderLeft: "4px solid var(--danger)", marginTop: "1rem" }}>
          <strong>Error:</strong> {journeyError}
        </div>
      )}

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
                  <div style={{ fontWeight: 600 }}>{Math.round(Number(demo.age))}</div>
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

          {journey.journey && journey.journey.length === 0 ? (
            <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: "3rem", marginBottom: "1rem" }}>
              No longitudinal records available for this patient.
            </div>
          ) : chartData.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "1rem" }}>
              <div className="card">
                <h2 className="section-title">Blood Pressure Over Time</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="day" label={{ value: "Visit Day", position: "insideBottom", offset: -5 }} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="systolic_bp" stroke={COLORS[0]} strokeWidth={2} dot={{ r: 3 }} name="Systolic BP" />
                    <Line type="monotone" dataKey="diastolic_bp" stroke={COLORS[1]} strokeWidth={2} dot={{ r: 3 }} name="Diastolic BP" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <h2 className="section-title">Activity Over Time</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="day" label={{ value: "Visit Day", position: "insideBottom", offset: -5 }} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="steps" stroke={COLORS[2]} strokeWidth={2} dot={{ r: 3 }} name="Steps" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <h2 className="section-title">Medication Adherence & Pain</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="day" label={{ value: "Visit Day", position: "insideBottom", offset: -5 }} tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 12 }} domain={[0, 1]} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} domain={[0, 10]} />
                    <Tooltip />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="medication_adherence" stroke={COLORS[3]} strokeWidth={2} dot={{ r: 3 }} name="Medication Adherence" />
                    <Line yAxisId="right" type="monotone" dataKey="pain_score" stroke={COLORS[4]} strokeWidth={2} dot={{ r: 3 }} name="Pain Score" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
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
