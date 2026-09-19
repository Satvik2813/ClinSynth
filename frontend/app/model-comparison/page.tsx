"use client";

import { useState } from "react";
import { api, CompareResult, ModelEntry } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
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
import { useApi } from "@/lib/swr";

export default function ModelComparisonPage() {
  const { mutate: globalMutate } = useSWRConfig();
  const [epochs, setEpochs] = useState(50);
  const [nEvalSamples, setNEvalSamples] = useState(200);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const { data: dataSummary } = useApi<unknown>("/data/summary", { errorRetryCount: 0 });

  const handleCompare = async () => {
    if (!dataSummary) {
      toast.error("Comparison unavailable", {
        id: "model-compare-run",
        description: "Load a dataset before comparing models.",
      });
      return;
    }
    const toastId = "model-compare-run";
    toast.loading("Comparing models...", { id: toastId });
    setLoading(true);
    setResult(null);
    try {
      const data = await api.compareModels({ epochs, n_eval_samples: nEvalSamples });
      setResult(data);
      const modelCount = Object.keys(data.comparison).length;
      toast.success("Model comparison complete", {
        id: toastId,
        description: `${modelCount} models evaluated`,
      });
    } catch (err: unknown) {
      toast.error("Model comparison failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (name: string) => {
    const toastId = "model-select";
    toast.loading(`Selecting ${name}...`, { id: toastId });
    setSelecting(name);
    try {
      const data = await api.selectModel(name);
      toast.success(`${name} selected as active model`, {
        id: toastId,
        description: data.status,
      });
      globalMutate("/overview");
      globalMutate("/train/status");
    } catch (err: unknown) {
      toast.error("Model selection failed", {
        id: toastId,
        description: friendlyError(err),
      });
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
      <p className="page-subtitle">Train and evaluate multiple synthesizer models side by side.</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Epochs</label>
            <input className="input-field" type="number" value={epochs} onChange={(e) => setEpochs(Number(e.target.value))} min={1} disabled={loading} style={{ width: "120px" }} />
          </div>
          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Eval Samples</label>
            <input className="input-field" type="number" value={nEvalSamples} onChange={(e) => setNEvalSamples(Number(e.target.value))} min={10} disabled={loading} style={{ width: "120px" }} />
          </div>
          <button className="btn-primary" onClick={handleCompare} disabled={loading} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {loading && <span className="spinner" />}
            {loading ? "Comparing Models..." : "Compare Models"}
          </button>
        </div>
      </div>

      {result && (
        <>
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
                              ? val % 1 !== 0 ? val.toFixed(4) : val
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

          <h2 style={{ marginBottom: "1rem" }}>Model Details</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
            {comparisonEntries.map(([name, m]) => (
              <div className="card" key={name} style={{ position: "relative" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <h3 style={{ margin: 0 }}>{name}</h3>
                  <span className={m.training_success ? "badge badge-success" : "badge badge-warning"}>
                    {m.training_success ? "Success" : "Failed"}
                  </span>
                </div>

                {m.error ? (
                  <p style={{ color: "var(--danger)" }}>{m.error}</p>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                    <div><span className="metric-label">Synth Type</span><div className="metric-value" style={{ fontSize: "0.85rem" }}>{m.synth_type}</div></div>
                    <div><span className="metric-label">Train Time</span><div className="metric-value">{m.train_time_seconds?.toFixed(2) ?? "N/A"}s</div></div>
                    <div><span className="metric-label">Generation Time</span><div className="metric-value">{m.generation_time_seconds?.toFixed(2) ?? "N/A"}s</div></div>
                    <div><span className="metric-label">Model Size</span><div className="metric-value">{m.model_size_kb != null ? `${m.model_size_kb} KB` : "N/A"}</div></div>
                    <div><span className="metric-label">Fidelity Score</span><div className="metric-value">{m.fidelity_score?.toFixed(4) ?? "N/A"}</div></div>
                    <div><span className="metric-label">Correlation</span><div className="metric-value">{m.correlation_preservation?.toFixed(4) ?? "N/A"}</div></div>
                    <div><span className="metric-label">KS Similarity</span><div className="metric-value">{m.ks_similarity?.toFixed(4) ?? "N/A"}</div></div>
                    <div><span className="metric-label">Exact Duplicates</span><div className="metric-value"><span className={m.exact_duplicates === 0 ? "badge badge-success" : "badge badge-warning"}>{m.exact_duplicates ?? "N/A"}</span></div></div>
                    <div><span className="metric-label">Near Copies</span><div className="metric-value"><span className={m.near_copy_count === 0 ? "badge badge-success" : "badge badge-warning"}>{m.near_copy_count ?? "N/A"}</span></div></div>
                    <div><span className="metric-label">Median NN Dist</span><div className="metric-value">{m.median_nn_distance?.toFixed(4) ?? "N/A"}</div></div>
                  </div>
                )}

                {m.training_success && (
                  <button
                    className="btn-secondary"
                    style={{ marginTop: "1rem", width: "100%", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}
                    onClick={() => handleSelect(name)}
                    disabled={selecting === name}
                  >
                    {selecting === name && <span className="spinner" />}
                    {selecting === name ? "Selecting..." : `Select ${name}`}
                  </button>
                )}
              </div>
            ))}
          </div>

          {chartData.length > 0 && (
            <div className="card" style={{ marginTop: "1.5rem" }}>
              <h2 style={{ marginBottom: "1rem" }}>Fidelity Score and Train Time</h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={chartData} margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis yAxisId="left" label={{ value: "Fidelity Score", angle: -90, position: "insideLeft" }} />
                  <YAxis yAxisId="right" orientation="right" label={{ value: "Train Time (s)", angle: 90, position: "insideRight" }} />
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
                  <Bar yAxisId="left" dataKey="fidelity_score" name="Fidelity Score" fill="#2F6B5F" />
                  <Bar yAxisId="right" dataKey="train_time" name="Train Time (s)" fill="#D4A843" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
