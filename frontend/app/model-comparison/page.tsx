"use client";

import { useState } from "react";
import { api, CompareResult, ModelEntry } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function ModelComparisonPage() {
  const [epochs, setEpochs] = useState(50);
  const [nEvalSamples, setNEvalSamples] = useState(200);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [selectMsg, setSelectMsg] = useState<string | null>(null);

  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectMsg(null);
    try {
      const data = await api.compareModels({ epochs, n_eval_samples: nEvalSamples });
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (name: string) => {
    setSelecting(name);
    setSelectMsg(null);
    try {
      const data = await api.selectModel(name);
      setSelectMsg(`${name}: ${data.status}`);
    } catch (err: unknown) {
      setSelectMsg(err instanceof Error ? err.message : "Selection failed");
    } finally {
      setSelecting(null);
    }
  };

  const comparisonEntries = result
    ? Object.entries(result.comparison) as [string, ModelEntry][]
    : [];

  const chartData = comparisonEntries
    .filter(([, m]) => m.training_success)
    .map(([name, m]) => ({
      name,
      fidelity_score: m.fidelity_score ?? 0,
      train_time: m.train_time_seconds ?? 0,
    }));

  return (
    <div>
      <h1 className="page-title">Model Comparison</h1>
      <p className="page-subtitle">
        Train and evaluate multiple synthesizer models side by side.
      </p>

      {/* Form */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>
              Epochs
            </label>
            <input
              type="number"
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              min={1}
              style={{
                padding: "0.5rem",
                borderRadius: "6px",
                border: "1px solid #d1d5db",
                width: "120px",
              }}
            />
          </div>
          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>
              Eval Samples
            </label>
            <input
              type="number"
              value={nEvalSamples}
              onChange={(e) => setNEvalSamples(Number(e.target.value))}
              min={10}
              style={{
                padding: "0.5rem",
                borderRadius: "6px",
                border: "1px solid #d1d5db",
                width: "120px",
              }}
            />
          </div>
          <button className="btn-primary" onClick={handleCompare} disabled={loading}>
            {loading ? "Comparing Models..." : "Compare Models"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: "4px solid #ef4444", color: "#ef4444" }}>
          {error}
        </div>
      )}

      {selectMsg && (
        <div className="card" style={{ borderLeft: "4px solid #10b981", marginBottom: "1rem" }}>
          {selectMsg}
        </div>
      )}

      {result && (
        <>
          {/* Comparison Table */}
          {result.table.length > 0 && (
            <div className="card" style={{ marginBottom: "1.5rem" }}>
              <h2 style={{ marginBottom: "1rem" }}>Comparison Table</h2>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      {Object.keys(result.table[0]).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.table.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val, j) => (
                          <td key={j}>
                            {typeof val === "number"
                              ? val % 1 !== 0
                                ? val.toFixed(4)
                                : val
                              : typeof val === "boolean"
                                ? val ? "Yes" : "No"
                                : String(val ?? "N/A")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Model Cards */}
          <h2 style={{ marginBottom: "1rem" }}>Model Details</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
            {comparisonEntries.map(([name, m]) => (
              <div className="card" key={name} style={{ position: "relative" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <h3 style={{ margin: 0 }}>{name}</h3>
                  <span className={m.training_success ? "badge-success" : "badge-warning"}>
                    {m.training_success ? "Success" : "Failed"}
                  </span>
                </div>

                {m.error ? (
                  <p style={{ color: "#ef4444" }}>{m.error}</p>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                    <div>
                      <span className="metric-label">Synth Type</span>
                      <div className="metric-value" style={{ fontSize: "0.85rem" }}>{m.synth_type}</div>
                    </div>
                    <div>
                      <span className="metric-label">Train Time</span>
                      <div className="metric-value">{m.train_time_seconds?.toFixed(2) ?? "N/A"}s</div>
                    </div>
                    <div>
                      <span className="metric-label">Generation Time</span>
                      <div className="metric-value">{m.generation_time_seconds?.toFixed(2) ?? "N/A"}s</div>
                    </div>
                    <div>
                      <span className="metric-label">Model Size</span>
                      <div className="metric-value">{m.model_size_kb != null ? `${m.model_size_kb} KB` : "N/A"}</div>
                    </div>
                    <div>
                      <span className="metric-label">Fidelity Score</span>
                      <div className="metric-value">{m.fidelity_score?.toFixed(4) ?? "N/A"}</div>
                    </div>
                    <div>
                      <span className="metric-label">Correlation</span>
                      <div className="metric-value">{m.correlation_preservation?.toFixed(4) ?? "N/A"}</div>
                    </div>
                    <div>
                      <span className="metric-label">KS Similarity</span>
                      <div className="metric-value">{m.ks_similarity?.toFixed(4) ?? "N/A"}</div>
                    </div>
                    <div>
                      <span className="metric-label">Exact Duplicates</span>
                      <div className="metric-value">
                        <span className={m.exact_duplicates === 0 ? "badge-success" : "badge-warning"}>
                          {m.exact_duplicates ?? "N/A"}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="metric-label">Near Copies</span>
                      <div className="metric-value">
                        <span className={m.near_copy_count === 0 ? "badge-success" : "badge-warning"}>
                          {m.near_copy_count ?? "N/A"}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="metric-label">Median NN Dist</span>
                      <div className="metric-value">{m.median_nn_distance?.toFixed(4) ?? "N/A"}</div>
                    </div>
                  </div>
                )}

                {m.training_success && (
                  <button
                    className="btn-secondary"
                    style={{ marginTop: "1rem", width: "100%" }}
                    onClick={() => handleSelect(name)}
                    disabled={selecting === name}
                  >
                    {selecting === name ? "Selecting..." : `Select ${name}`}
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Bar Chart */}
          {chartData.length > 0 && (
            <div className="card" style={{ marginTop: "1.5rem" }}>
              <h2 style={{ marginBottom: "1rem" }}>Fidelity Score and Train Time</h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={chartData} margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis yAxisId="left" label={{ value: "Fidelity Score", angle: -90, position: "insideLeft" }} />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    label={{ value: "Train Time (s)", angle: 90, position: "insideRight" }}
                  />
                  <Tooltip
                    formatter={(value: unknown, name: unknown) => {
                      const v = Number(value);
                      const n = String(name ?? "");
                      return [
                        n === "fidelity_score" ? v.toFixed(4) : `${v.toFixed(2)}s`,
                        n === "fidelity_score" ? "Fidelity Score" : "Train Time",
                      ];
                    }}
                  />
                  <Legend />
                  <Bar yAxisId="left" dataKey="fidelity_score" name="Fidelity Score" fill="#6366f1" />
                  <Bar yAxisId="right" dataKey="train_time" name="Train Time (s)" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
