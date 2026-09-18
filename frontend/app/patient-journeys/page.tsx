"use client";

import { useEffect, useState } from "react";
import { api, JourneyResult } from "@/lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = ["#0d9488", "#0ea5e9", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function PatientJourneysPage() {
  const [patientIds, setPatientIds] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [journey, setJourney] = useState<JourneyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listPatients()
      .then((d) => {
        setPatientIds(d.patient_ids);
        if (d.patient_ids.length > 0) {
          setSelectedId(d.patient_ids[0]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setJourneyLoading(true);
    api.getJourney(selectedId)
      .then(setJourney)
      .catch((e) => setError(e.message))
      .finally(() => setJourneyLoading(false));
  }, [selectedId]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading patients...</div>;
  if (error && patientIds.length === 0) return <div className="p-8 text-center text-red-500">{error}</div>;

  if (patientIds.length === 0) {
    return (
      <div className="max-w-4xl space-y-6">
        <h1 className="page-title">Patient Journeys</h1>
        <div className="card text-center text-slate-500 py-12">
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
    <div className="max-w-6xl space-y-6">
      <div>
        <h1 className="page-title">Patient Journeys</h1>
        <p className="page-subtitle">Explore individual synthetic patient trajectories over time</p>
      </div>

      <div className="card">
        <label className="text-sm font-medium text-slate-600 mr-3">Select Patient:</label>
        <select
          className="select-field"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {patientIds.map((id) => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
        <span className="ml-3 text-sm text-slate-400">{patientIds.length} patients available</span>
      </div>

      {journeyLoading && <div className="text-center text-slate-500 py-8">Loading journey...</div>}

      {journey && !journeyLoading && (
        <>
          {demo && (
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Demographics</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div>
                  <div className="text-xs text-slate-400">Patient ID</div>
                  <div className="font-semibold">{demo.patient_id}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">Age</div>
                  <div className="font-semibold">{demo.age}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">Gender</div>
                  <div className="font-semibold">{demo.gender}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">BMI</div>
                  <div className="font-semibold">{typeof demo.bmi === "number" ? demo.bmi.toFixed(1) : demo.bmi}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">Conditions</div>
                  <div className="flex gap-1 mt-0.5">
                    {demo.diabetes && <span className="badge badge-warning">Diabetes</span>}
                    {demo.hypertension && <span className="badge badge-danger">HTN</span>}
                    {!demo.diabetes && !demo.hypertension && <span className="text-sm text-slate-400">None</span>}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">Trajectory</div>
                  <div className="font-semibold">{demo.trajectory_type || "—"}</div>
                </div>
              </div>
            </div>
          )}

          {journey.journey.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Vitals Over Time</h2>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={journey.journey}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
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
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Journey Statistics</h2>
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
                        <td className="font-medium">{s.metric}</td>
                        <td>{s.baseline != null ? s.baseline.toFixed(1) : "—"}</td>
                        <td>{s.final != null ? s.final.toFixed(1) : "—"}</td>
                        <td>
                          {s.change != null ? (
                            <span className={s.change > 0 ? "text-red-500" : s.change < 0 ? "text-green-500" : ""}>
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
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Cohort Average Comparison</h2>
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
