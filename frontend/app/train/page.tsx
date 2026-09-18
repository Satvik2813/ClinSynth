"use client";

import { useState, useEffect } from "react";
import { api, TrainResult, TrainInfo } from "@/lib/api";

export default function TrainPage() {
  const [trained, setTrained] = useState(false);
  const [trainInfo, setTrainInfo] = useState<TrainInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [synthType, setSynthType] = useState("GaussianCopulaSynthesizer");
  const [mode, setMode] = useState("demo");
  const [epochs, setEpochs] = useState(100);
  const [batchSize, setBatchSize] = useState(500);

  // Training state
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [trainError, setTrainError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getTrainStatus()
      .then((data) => {
        setTrained(data.trained);
        setTrainInfo(data.info);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    setTrainError(null);
    setTrainResult(null);
    try {
      const body: {
        synth_type: string;
        mode: string;
        epochs?: number;
        batch_size?: number;
      } = { synth_type: synthType, mode };
      if (synthType === "CTGANSynthesizer") {
        body.epochs = epochs;
        body.batch_size = batchSize;
      }
      const result = await api.train(body);
      setTrainResult(result);
      setTrained(true);
      setTrainInfo({
        synth_type: result.synth_type,
        training_rows: result.training_rows,
        epochs: result.epochs,
        duration_seconds: result.duration_seconds,
      });
    } catch (err: unknown) {
      setTrainError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setTraining(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <div className="spinner" />
        <p style={{ color: "var(--muted)", marginTop: "1rem" }}>
          Loading training status...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "2rem" }}>
        <div
          className="card"
          style={{
            borderLeft: "4px solid var(--danger)",
            padding: "1.5rem",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h1 className="page-title">Train Model</h1>
      <p className="page-subtitle">
        Train a synthesizer on loaded patient data
      </p>

      {/* Current Status */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2
          style={{
            fontSize: "1.1rem",
            fontWeight: 600,
            marginBottom: "1rem",
          }}
        >
          Current Status
        </h2>
        {trained && trainInfo ? (
          <div>
            <span className="badge-success" style={{ marginBottom: "1rem", display: "inline-block" }}>
              Model Trained
            </span>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
                marginTop: "0.75rem",
              }}
            >
              <div>
                <div className="metric-label">Synthesizer</div>
                <div className="metric-value">{trainInfo.synth_type}</div>
              </div>
              <div>
                <div className="metric-label">Training Rows</div>
                <div className="metric-value">
                  {trainInfo.training_rows.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="metric-label">Epochs</div>
                <div className="metric-value">
                  {trainInfo.epochs ?? "N/A"}
                </div>
              </div>
              <div>
                <div className="metric-label">Duration</div>
                <div className="metric-value">
                  {trainInfo.duration_seconds.toFixed(1)}s
                </div>
              </div>
            </div>
          </div>
        ) : (
          <span className="badge-warning">No model trained</span>
        )}
      </div>

      {/* Training Form */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2
          style={{
            fontSize: "1.1rem",
            fontWeight: 600,
            marginBottom: "1rem",
          }}
        >
          Train New Model
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Synthesizer type */}
          <div>
            <label
              className="metric-label"
              style={{ display: "block", marginBottom: "0.25rem" }}
            >
              Synthesizer Type
            </label>
            <select
              className="select-field"
              value={synthType}
              onChange={(e) => setSynthType(e.target.value)}
              disabled={training}
            >
              <option value="GaussianCopulaSynthesizer">
                GaussianCopulaSynthesizer
              </option>
              <option value="CTGANSynthesizer">CTGANSynthesizer</option>
            </select>
          </div>

          {/* Mode */}
          <div>
            <label
              className="metric-label"
              style={{ display: "block", marginBottom: "0.25rem" }}
            >
              Mode
            </label>
            <select
              className="select-field"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              disabled={training}
            >
              <option value="demo">Demo (fast)</option>
              <option value="full">Full</option>
            </select>
          </div>

          {/* CTGAN-specific options */}
          {synthType === "CTGANSynthesizer" && (
            <>
              <div>
                <label
                  className="metric-label"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Epochs: {epochs}
                </label>
                <input
                  type="range"
                  min={10}
                  max={500}
                  step={10}
                  value={epochs}
                  onChange={(e) => setEpochs(Number(e.target.value))}
                  disabled={training}
                  style={{ width: "100%" }}
                />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.75rem",
                    color: "var(--muted)",
                  }}
                >
                  <span>10</span>
                  <span>250</span>
                  <span>500</span>
                </div>
              </div>

              <div>
                <label
                  className="metric-label"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Batch Size
                </label>
                <input
                  className="input-field"
                  type="number"
                  min={50}
                  max={5000}
                  step={50}
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  disabled={training}
                />
              </div>
            </>
          )}

          {/* Submit */}
          <button
            className="btn-primary"
            onClick={handleTrain}
            disabled={training}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              marginTop: "0.5rem",
            }}
          >
            {training && <span className="spinner" />}
            {training ? "Training..." : "Start Training"}
          </button>
        </div>
      </div>

      {/* Training Error */}
      {trainError && (
        <div
          className="card"
          style={{
            borderLeft: "4px solid var(--danger)",
            marginBottom: "1.5rem",
          }}
        >
          <strong>Training Error:</strong> {trainError}
        </div>
      )}

      {/* Training Result */}
      {trainResult && (
        <div
          className="card"
          style={{ borderLeft: "4px solid var(--success)" }}
        >
          <h2
            style={{
              fontSize: "1.1rem",
              fontWeight: 600,
              marginBottom: "1rem",
            }}
          >
            Training Complete
          </h2>
          <span className="badge-success" style={{ marginBottom: "1rem", display: "inline-block" }}>
            {trainResult.status}
          </span>
          {trainResult.message && (
            <p
              style={{
                color: "var(--muted)",
                fontSize: "0.9rem",
                margin: "0.5rem 0",
              }}
            >
              {trainResult.message}
            </p>
          )}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
              marginTop: "0.75rem",
            }}
          >
            <div>
              <div className="metric-label">Synthesizer</div>
              <div className="metric-value">{trainResult.synth_type}</div>
            </div>
            <div>
              <div className="metric-label">Training Rows</div>
              <div className="metric-value">
                {trainResult.training_rows.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="metric-label">Epochs</div>
              <div className="metric-value">
                {trainResult.epochs ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="metric-label">Duration</div>
              <div className="metric-value">
                {trainResult.duration_seconds.toFixed(1)}s
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
