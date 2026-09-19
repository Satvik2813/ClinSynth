"use client";

import { useState, useCallback } from "react";
import { api, TrainResult, TrainInfo } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { getSection, setSection } from "@/lib/pipeline-session";

function getInitialTrainForm() {
  const saved = getSection("train");
  return {
    synthType: saved?.synthType ?? "GaussianCopulaSynthesizer",
    mode: saved?.mode ?? "demo",
    epochs: saved?.epochs ?? 100,
    batchSize: saved?.batchSize ?? 500,
  };
}

export default function TrainPage() {
  const { data: status, error, isLoading, mutate } = useApi<{ trained: boolean; info: TrainInfo | null }>("/train/status");
  const { mutate: globalMutate } = useSWRConfig();

  const initial = getInitialTrainForm();
  const [synthType, setSynthType] = useState(initial.synthType);
  const [mode, setMode] = useState(initial.mode);
  const [epochs, setEpochs] = useState(initial.epochs);
  const [batchSize, setBatchSize] = useState(initial.batchSize);

  const persistForm = useCallback((patch: Partial<{ synthType: string; mode: string; epochs: number; batchSize: number }>) => {
    const current = getSection("train") ?? {};
    setSection("train", { ...current, ...patch });
  }, []);

  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const { data: dataSummary } = useApi<unknown>("/data/summary", { errorRetryCount: 0 });

  const modelLabel = synthType === "CTGANSynthesizer" ? "CTGAN" : "Gaussian Copula";

  const handleTrain = async () => {
    if (!dataSummary) {
      toast.error("Training unavailable", {
        id: "model-train-run",
        description: "Load a dataset before training a model.",
      });
      return;
    }
    const toastId = "model-train-run";
    toast.loading(`Training ${modelLabel}...`, { id: toastId });
    setTraining(true);
    setTrainResult(null);
    try {
      const body: { synth_type: string; mode: string; epochs?: number; batch_size?: number } = { synth_type: synthType, mode };
      if (synthType === "CTGANSynthesizer") {
        body.epochs = epochs;
        body.batch_size = batchSize;
      }
      const result = await api.train(body);
      setTrainResult(result);

      if (result.status === "fallback") {
        toast.warning("CTGAN training failed — Gaussian Copula fallback activated", {
          id: toastId,
          description: result.message || `Trained in ${result.duration_seconds.toFixed(1)}s`,
          duration: 6000,
        });
      } else {
        toast.success("Model training completed", {
          id: toastId,
          description: `${result.synth_type} · ${result.duration_seconds.toFixed(1)}s`,
        });
      }

      mutate({ trained: true, info: { synth_type: result.synth_type, training_rows: result.training_rows, epochs: result.epochs, duration_seconds: result.duration_seconds } }, false);
      globalMutate("/overview");
      globalMutate("/cohort/current");
      globalMutate("/validation");
      globalMutate("/privacy");
      globalMutate("/research/readiness");
    } catch (err: unknown) {
      toast.error("Model training failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setTraining(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Train Model</h1>
        <p className="page-subtitle">Train a synthesizer on loaded patient data</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={4} /></div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={6} /></div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Train Model</h1>
        <div className="card" style={{ borderLeft: "4px solid var(--danger)", padding: "1.5rem", marginTop: "1.5rem" }}>
          <strong>Error:</strong> {friendlyError(error)}
        </div>
      </div>
    );
  }

  const trained = status?.trained ?? false;
  const trainInfo = status?.info ?? null;

  return (
    <div>
      <h1 className="page-title">Train Model</h1>
      <p className="page-subtitle">Train a synthesizer on loaded patient data</p>

      {/* Current Status */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: 0 }}>Current Status</h2>
          <StatusBadge label="Model" status={trained ? "trained" : "not_trained"} />
        </div>
        {trained && trainInfo ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <div className="metric-label">Synthesizer</div>
              <div className="metric-value">{trainInfo.synth_type}</div>
            </div>
            <div>
              <div className="metric-label">Training Rows</div>
              <div className="metric-value">{trainInfo.training_rows.toLocaleString()}</div>
            </div>
            <div>
              <div className="metric-label">Epochs</div>
              <div className="metric-value">{trainInfo.epochs ?? "N/A"}</div>
            </div>
            <div>
              <div className="metric-label">Duration</div>
              <div className="metric-value">{trainInfo.duration_seconds.toFixed(1)}s</div>
            </div>
          </div>
        ) : (
          <p style={{ color: "var(--muted)", fontSize: "0.875rem" }}>No model has been trained yet. Load data first, then train a model.</p>
        )}
      </div>

      {/* Training Form */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>Train New Model</h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Synthesizer Type</label>
            <select className="select-field" value={synthType} onChange={(e) => { setSynthType(e.target.value); persistForm({ synthType: e.target.value }); }} disabled={training}>
              <option value="GaussianCopulaSynthesizer">GaussianCopulaSynthesizer</option>
              <option value="CTGANSynthesizer">CTGANSynthesizer</option>
            </select>
          </div>

          <div>
            <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Mode</label>
            <select className="select-field" value={mode} onChange={(e) => { setMode(e.target.value); persistForm({ mode: e.target.value }); }} disabled={training}>
              <option value="demo">Demo (fast)</option>
              <option value="full">Full</option>
            </select>
          </div>

          {synthType === "CTGANSynthesizer" && (
            <>
              <div>
                <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Epochs: {epochs}</label>
                <input type="range" min={10} max={500} step={10} value={epochs} onChange={(e) => { const v = Number(e.target.value); setEpochs(v); persistForm({ epochs: v }); }} disabled={training} style={{ width: "100%" }} />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--muted)" }}>
                  <span>10</span><span>250</span><span>500</span>
                </div>
              </div>
              <div>
                <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Batch Size</label>
                <input className="input-field" type="number" min={50} max={5000} step={50} value={batchSize} onChange={(e) => { const v = Number(e.target.value); setBatchSize(v); persistForm({ batchSize: v }); }} disabled={training} />
              </div>
            </>
          )}

          <button className="btn-primary" onClick={handleTrain} disabled={training} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
            {training && <span className="spinner" />}
            {training ? "Training..." : "Start Training"}
          </button>
        </div>
      </div>

      {/* Training Result */}
      {trainResult && (
        <div className="card" style={{ borderLeft: `4px solid ${trainResult.status === "fallback" ? "var(--warning)" : "var(--success)"}` }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>Training Complete</h2>
          <span className={`badge ${trainResult.status === "fallback" ? "badge-warning" : "badge-success"}`} style={{ marginBottom: "1rem", display: "inline-block" }}>
            {trainResult.status}
          </span>
          {trainResult.message && (
            <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: "0.5rem 0" }}>{trainResult.message}</p>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.75rem" }}>
            <div><div className="metric-label">Synthesizer</div><div className="metric-value">{trainResult.synth_type}</div></div>
            <div><div className="metric-label">Training Rows</div><div className="metric-value">{trainResult.training_rows.toLocaleString()}</div></div>
            <div><div className="metric-label">Epochs</div><div className="metric-value">{trainResult.epochs ?? "N/A"}</div></div>
            <div><div className="metric-label">Duration</div><div className="metric-value">{trainResult.duration_seconds.toFixed(1)}s</div></div>
          </div>
        </div>
      )}
    </div>
  );
}
